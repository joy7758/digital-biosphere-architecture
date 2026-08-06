"""Unified evidence package builder for the method-v2 experiment.

Executes the full pipeline IN ORDER and refuses to package on any failure:

 1. capability-matrix commitment check;
 2. experiment run (run_experiment.py);
 3. post-run system verifier (verify_run_records.py);
 4. shadow protocol validator (validate_shadow_protocol.py);
 5. evidence reference verifier (verify_evidence_references.py);
 6. generated-object validation (analysis/generated-object-validation.json
    must report PASS);
 7. metric analysis (analyze_experiment.py);
 8. test-output collection (unittest discover over tests/);
 9. unified manifest generation (SHA-256 of every packaged file except the
    manifest itself);
10. ZIP creation.

Package layout mirrors the repository (AHRP/ + docs/ + experiments/) so the
package is self-contained and re-verifiable in isolation.
"""

import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from contextlib import redirect_stderr, redirect_stdout

import analyze_experiment
import run_experiment
import validate_shadow_protocol
import verify_evidence_references
import verify_run_records

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
AHRP_DIR = os.path.join(REPO_ROOT, "AHRP")
EXPERIMENT_REL = os.path.relpath(HERE, REPO_ROOT)
OUTPUT_ZIP = os.path.join(REPO_ROOT, "experiments",
                          "AHRP-pilot-readiness-method-v2-evidence.zip")
MANIFEST_NAME = "MANIFEST.sha256"

TRUTH_BOUNDARY = """\
CONTROLLED_INTERNAL_EXPERIMENT=true
SYNTHETIC_AGENT_ROSTER=true
REAL_EXTERNAL_AGENT=false
REAL_WORLD_ADOPTION_VALIDATED=false
AHRP_PRODUCTION_READY=false
AHRP_STANDARD_PUBLISHED=false
NETWORK_SERVICE_RECOMMENDATION=DEFER
PR12_EXPERIMENT_RESULT=INVALIDATED
CLEANROOM_EXPERIMENT_RESULT=INCONCLUSIVE
REAL_INDEPENDENT_VERIFICATION=false
SYNTHETIC_SYSTEM_VERIFICATION=true
POST_RUN_RECOMPUTATION_VERIFIED=true
AHRP_V0_1_MODIFIED=false
"""


def file_sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def step(label: str, func, *args) -> None:
    print(f"[build] {label}", flush=True)
    result = func(*args)
    if isinstance(result, int) and result != 0:
        raise SystemExit(f"BUILD_ABORTED at step: {label} (rc={result})")


def collect_test_output(staging_experiment_dir: str) -> None:
    print("[build] 8. collecting test output", flush=True)
    loader = unittest.TestLoader()
    suite = loader.discover(
        start_dir=os.path.join(staging_experiment_dir, "tests"),
        top_level_dir=os.path.join(staging_experiment_dir, "tests"))
    buffer = io.StringIO()
    runner = unittest.TextTestRunner(stream=buffer, verbosity=2)
    sys.path.insert(0, staging_experiment_dir)
    try:
        with redirect_stdout(buffer), redirect_stderr(buffer):
            result = runner.run(suite)
    finally:
        sys.path.remove(staging_experiment_dir)
    if not result.wasSuccessful():
        raise SystemExit("BUILD_ABORTED: test collection reported failures")
    with open(os.path.join(staging_experiment_dir, "evidence",
                           "test-output.txt"), "w",
              encoding="utf-8") as handle:
        handle.write(buffer.getvalue())


def git_baseline_text() -> str:
    def git(*args):
        completed = subprocess.run(["git", *args], cwd=REPO_ROOT,
                                   capture_output=True, text=True, check=True)
        return completed.stdout.strip()

    head = git("rev-parse", "HEAD")
    base = "06126fffaaf3072b91ed211fa88ba9d202025003"
    ahrp_tree = git("rev-parse", f"{head}:AHRP")
    lines = [
        "# Git baseline - AHRP PR#13 trust-boundary fix",
        f"REPOSITORY=joy7758/digital-biosphere-architecture",
        f"BASE_COMMIT={base}",
        f"BASE_AHRP_TREE={git('rev-parse', base + ':AHRP')}",
        f"BRANCH={git('rev-parse', '--abbrev-ref', 'HEAD')}",
        f"HEAD={head}",
        f"HEAD_AHRP_TREE={ahrp_tree}",
        f"AHRP_TREE_UNCHANGED="
        f"{'true' if ahrp_tree == git('rev-parse', base + ':AHRP') else 'false'}",
        "",
        "## Commits since base",
    ]
    lines += git("log", "--format=%H %s", f"{base}..{head}").splitlines()
    return "\n".join(lines) + "\n"


def copy_tree_without_cache(src: str, dst: str) -> None:
    def ignore(_dir, names):
        return [n for n in names if n == "__pycache__" or
                n.endswith(".pyc")]
    shutil.copytree(src, dst, ignore=ignore)


def main() -> int:
    # 1. commitment
    step("1. capability-matrix commitment",
         run_experiment.check_capability_commitment)
    # 2. experiment run
    step("2. experiment run", run_experiment.main)
    # 3. post-run verifier
    step("3. post-run system verifier", verify_run_records.main)
    # 4. shadow protocol validator
    step("4. shadow protocol validator", validate_shadow_protocol.main)
    # 5. evidence reference verifier
    step("5. evidence reference verifier", verify_evidence_references.main)
    # 6. generated-object validation must be PASS
    print("[build] 6. generated-object validation", flush=True)
    report = json.load(open(os.path.join(HERE, "analysis",
                                         "generated-object-validation.json"),
                            encoding="utf-8"))
    if report["status"] != "PASS":
        raise SystemExit("BUILD_ABORTED: generated-object validation FAIL")
    # 7. analysis
    step("7. metric analysis", analyze_experiment.main)

    # Assemble staging package.
    staging = tempfile.mkdtemp(prefix="ahrp-mv2-package-")
    try:
        copy_tree_without_cache(AHRP_DIR, os.path.join(staging, "AHRP"))
        docs_dir = os.path.join(staging, "docs", "review")
        os.makedirs(docs_dir, exist_ok=True)
        shutil.copy(os.path.join(REPO_ROOT, "docs", "review",
                                 "PR-012-post-merge-integrity-audit.md"),
                    docs_dir)
        staging_experiment = os.path.join(staging, EXPERIMENT_REL)
        copy_tree_without_cache(HERE, staging_experiment)

        # 8. test output (collected into the staging copy)
        collect_test_output(staging_experiment)

        with open(os.path.join(staging, "TRUTH_BOUNDARY.txt"), "w",
                  encoding="utf-8") as handle:
            handle.write(TRUTH_BOUNDARY)
        with open(os.path.join(staging, "git-baseline.txt"), "w",
                  encoding="utf-8") as handle:
            handle.write(git_baseline_text())

        # 9. unified manifest over every packaged file except itself.
        print("[build] 9. unified manifest", flush=True)
        manifest_lines = []
        for root, dirs, files in os.walk(staging):
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for name in sorted(files):
                if name.endswith(".pyc"):
                    continue
                path = os.path.join(root, name)
                rel = os.path.relpath(path, staging)
                if rel == MANIFEST_NAME or rel.endswith(".pyc"):
                    continue
                manifest_lines.append(f"{file_sha256(path)}  {rel}")
        manifest_lines.sort(key=lambda line: line.split("  ", 1)[1])
        manifest_path = os.path.join(staging, MANIFEST_NAME)
        with open(manifest_path, "w", encoding="utf-8") as handle:
            handle.write("\n".join(manifest_lines) + "\n")

        # 10. zip (temp file lives OUTSIDE staging so it is never packaged)
        print("[build] 10. zip", flush=True)
        tmp_zip = OUTPUT_ZIP + ".tmp"
        with zipfile.ZipFile(tmp_zip, "w", zipfile.ZIP_DEFLATED) as bundle:
            for root, dirs, files in os.walk(staging):
                dirs[:] = [d for d in dirs if d != "__pycache__"]
                for name in sorted(files):
                    if name.endswith(".pyc"):
                        continue
                    path = os.path.join(root, name)
                    bundle.write(path, os.path.relpath(path, staging))
        shutil.move(tmp_zip, OUTPUT_ZIP)
    finally:
        shutil.rmtree(staging, ignore_errors=True)

    digest = file_sha256(OUTPUT_ZIP)
    print(json.dumps({
        "status": "PACKAGE_BUILT",
        "package": os.path.relpath(OUTPUT_ZIP, REPO_ROOT),
        "sha256": digest,
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

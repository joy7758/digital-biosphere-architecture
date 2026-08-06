"""Programmatic worker components (executable role implementations) for the
AHRP internal orchestrator integration trial (AHRP 内部编排器集成试验 v0.1).

程序化 Worker 组件（可执行角色实现）。

Each worker component is a genuine executor: it reads its task, produces
real artifact files on disk, and its result is determined ONLY by the task
requirements versus its own declared capability boundary.

Worker components never see the experiment phase, the orchestrator's
decision, any decision-change flag, or any AHRP record. This keeps
execution independent of delegation decisions.

These executable components are not evidence of autonomous,
model-based, or externally operated agent adoption.
这些可执行组件不能证明自主智能体、模型型智能体或外部智能体采用了 AHRP。
"""

import ast
import hashlib
from pathlib import Path

SUCCESS = "SUCCESS"
FAILURE = "FAILURE"


class WorkerAgent:
    """Base worker: identity + declared boundary + artifact writing."""

    def __init__(self, registration: dict):
        self.agent_id = registration["agent_id"]
        self.agent_version = registration["agent_version"]
        self.role = registration["role"]
        self.capabilities = registration["capabilities"]
        self.boundary = registration["boundary"]

    # -- real execution ----------------------------------------------------
    def _write_artifact(self, out_dir: Path, name: str, content: str) -> str:
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / name
        path.write_text(content, encoding="utf-8")
        return str(path.relative_to(out_dir.parent.parent))

    def execute(self, task: dict, out_dir: Path) -> dict:
        raise NotImplementedError


class CodingWorker(WorkerAgent):
    """worker-alpha: writes real Python code and compiles it."""

    CODE_TEMPLATES = {
        "default": (
            "def deliver(task_id: str) -> str:\n"
            "    \"\"\"Deterministic deliverable produced by worker-alpha.\"\"\"\n"
            "    return f\"delivered:{task_id}\"\n"
        ),
    }

    def execute(self, task: dict, out_dir: Path) -> dict:
        req = task["requirements"]
        if req.get("requires_dependency_resolution"):
            attempt = out_dir / "dependency-resolution-attempt.log"
            out_dir.mkdir(parents=True, exist_ok=True)
            attempt.write_text(
                f"task_id: {task['task_id']}\n"
                "step: resolve third-party dependency\n"
                "outcome: BLOCKED - no package-index access (declared boundary)\n",
                encoding="utf-8",
            )
            return {
                "status": FAILURE,
                "failure_category": "CAPABILITY_LIMIT",
                "reason": "dependency resolution outside declared boundary",
                "artifact_paths": [str(attempt.name)],
            }
        module_path = self._write_artifact(
            out_dir, "module.py", self.CODE_TEMPLATES["default"]
        )
        # real smoke test: the produced code must parse and compile
        source = (out_dir / "module.py").read_text(encoding="utf-8")
        ast.parse(source)
        compile(source, "module.py", "exec")
        digest = hashlib.sha256(source.encode("utf-8")).hexdigest()
        return {
            "status": SUCCESS,
            "failure_category": None,
            "reason": "module written, parsed and compiled",
            "artifact_paths": [module_path],
            "artifact_sha256": digest,
        }


class ResearchWorker(WorkerAgent):
    """worker-beta: writes real research notes from local material."""

    def execute(self, task: dict, out_dir: Path) -> dict:
        req = task["requirements"]
        if req.get("requires_external_sources"):
            return {
                "status": FAILURE,
                "failure_category": "POLICY_RESTRICTION",
                "reason": "policy forbids live external source access",
                "artifact_paths": [],
            }
        note = (
            f"# Research note: {task['title']}\n\n"
            f"task_id: {task['task_id']}\n"
            "method: structured reading of locally available documents\n"
            "findings:\n"
            "- the requested topic is covered by local material only\n"
            "- no external sources were consulted (policy boundary)\n"
        )
        note_path = self._write_artifact(out_dir, "research-note.md", note)
        return {
            "status": SUCCESS,
            "failure_category": None,
            "reason": "research note produced from local material",
            "artifact_paths": [note_path],
        }


class ReviewWorker(WorkerAgent):
    """worker-gamma: reads a target text and writes real review findings."""

    REVIEW_TARGET = (
        "Section 1 Introduction.\n"
        "Section 2 Terminology.\n"
        "section 3 results.\n"  # intentional casing drift for the reviewer
    )

    def execute(self, task: dict, out_dir: Path) -> dict:
        req = task["requirements"]
        if req.get("requires_security_review"):
            return {
                "status": FAILURE,
                "failure_category": "CAPABILITY_LIMIT",
                "reason": "security auditing outside declared boundary",
                "artifact_paths": [],
            }
        findings = [
            line
            for line in self.REVIEW_TARGET.splitlines()
            if not line[0:7].startswith("Section")
        ]
        report = (
            f"# Review findings: {task['title']}\n\n"
            f"task_id: {task['task_id']}\n"
            f"lines_inspected: {len(self.REVIEW_TARGET.splitlines())}\n"
            f"inconsistencies_found: {len(findings)}\n"
            "details:\n"
            + "".join(f"- {item}\n" for item in findings)
        )
        report_path = self._write_artifact(out_dir, "review-findings.md", report)
        return {
            "status": SUCCESS,
            "failure_category": None,
            "reason": "review performed, findings recorded",
            "artifact_paths": [report_path],
        }


class DataProcessingWorker(WorkerAgent):
    """Fallback executor for data_processing tasks: real transformation."""

    def execute(self, task: dict, out_dir: Path) -> dict:
        columns = ["TaskID", "ResultStatus", "queryCount"]

        def snake(name: str) -> str:
            out = []
            for ch in name:
                out.append("_" + ch.lower() if ch.isupper() and out else ch.lower())
            return "".join(out)

        normalized = [snake(c) for c in columns]
        csv_body = ",".join(normalized) + "\n"
        csv_path = self._write_artifact(out_dir, "normalized.csv", csv_body)
        return {
            "status": SUCCESS,
            "failure_category": None,
            "reason": "column names normalized to snake_case",
            "artifact_paths": [csv_path],
        }

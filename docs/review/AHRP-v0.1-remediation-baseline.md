# AHRP v0.1 Remediation — Baseline Record (Phase 1)

This document freezes the baseline state for the AHRP v0.1 remediation
work (independent audit round 2). It is the reference point for all
subsequent phases; nothing in this record may be altered retroactively.

## 1. Baseline Establishment

| Field | Value |
|---|---|
| Date of baseline establishment | 2026-08-05 |
| Original HEAD commit SHA | `1d0c3ba2d750b6a1d0606b49250960b3584bb478` |
| Original HEAD subject | Add AI agent discovery surface for execution evidence bridge (#10) |
| Branch name | `fix/ahrp-v0.1-independent-audit-r2` |
| Isolated worktree | `<local-isolated-worktree>` (machine-local path redacted) |
| Original (untouched) worktree | `<original-repository-worktree>` (machine-local path redacted) |
| Known original ZIP SHA-256 | `8cf571fc050ecb0635c4158c4690d3bd6fc08501e3c2644c3942377cf33d5833` |

## 2. Original Dirty Status Summary

Captured via `git status --short` in the original worktree at baseline time.
The original worktree was NOT modified during this phase.

Modified (tracked):

```
 M .gitignore
 M AGENTS.md
 M README.md
 M README.zh-CN.md
 M docs/ai-citation-map.json
 M docs/ai-discovery-index.md
 M docs/repository-map.md
 M llms.txt
```

Untracked:

```
?? .qoder/
?? .review-staging/
?? RELEASE_READINESS.md
?? experiments/
?? figures/
?? paper/
?? references/
?? research-manifest.yaml
?? review/
?? scripts/render_paper_figures.py
?? theory/
```

Recent commits (`git log --oneline -5`):

```
1d0c3ba (HEAD -> main) Add AI agent discovery surface for execution evidence bridge (#10)
3c6dbf8 Add execution evidence bridge one-page reviewer brief (#9)
6721e34 Add execution evidence bridge reviewer announcement (#8)
22f3942 Map execution evidence bridge across architecture stack (#7)
b23baf8 docs: add outbound text pack (#6)
```

## 3. AHRP Source Location

No `AHRP/` directory exists at the original repository root. Per the
Phase 1 contingency rule, the AHRP sources were located inside the
review staging area:

```
.review-staging/AHRP-v0.1-independent-review-package/AHRP/
```

The extracted staging package also contains the governance docs
(ADR-001, AHRP Constitution, architecture review, agent acceptance
report, development-loop review, review closure), `REVIEW_MANIFEST.json`,
`INDEPENDENT_REVIEW_REPORT.md`, evidence files, and `file-hashes.sha256`.

Total AHRP source files: **26** (all hashes below).

## 4. AHRP Source File SHA-256 Hashes (Baseline)

Computed from the original worktree before any copy operation.

```
b497b4abe4b2dcf42849cceb32c05b2f68e357a18a2ee78b2382879ac7bf53e2  ./AHRP/README.md
af6f85f87051277327053cf08e7616eeb9f4a9921a2ab3bac381f19db7c6c679  ./AHRP/STATUS.md
b2197189a6da933a07786c28d267483f2ebbb74d8d3ce3e31ce68e71a965ba7f  ./AHRP/demo/run_demo.py
e2c0ee6f9dc2314f4e1f85ea30d02f3eae2430a3c0a5ac7d7384ff9978c0527f  ./AHRP/examples/01-event-success-verified.json
2fd9136258d4fbc528b0b975c47b38099f609e90758d787957fd55afc09b9714  ./AHRP/examples/01-verification-verified.json
e403d5d838673af108ecc18f556689dc1faa68f2274f72bc6d8873b4ce7d9bfc  ./AHRP/examples/02-event-insufficient-evidence.json
0839cd4beeae06ea6c639af7d106e30de568bc137f0698c38a37dc7317c11661  ./AHRP/examples/03-event-version-conflict.json
6d05a6f311e07238e20be95f69b81c385bd4bf4e5592c1c4a0697f1f16cda3a0  ./AHRP/examples/04-event-verification-conflict.json
1122718b19840b5b601180c472c0024c77e7571dfd87d816ff53ced3fbf94ea0  ./AHRP/examples/04-verification-conflicted.json
f5ccd7fac1d3a484fe9ca4e9b6df1bd730f209e34e6e2bd53f38c97136517801  ./AHRP/examples/05-event-withheld.json
4d70ba8d9fea5a9ecb7fb346952b6a78feda1dcdeb4b0f58bf8efd26400600c5  ./AHRP/examples/05-selective-disclosure-query.json
77a9ab437873795ff588367f1f9e1b6d4936cb5f2d06248968c55fddbabe1530  ./AHRP/query/__init__.py
22ab1d5498b70b86d9b5aaf181d164ae6fe9e71ab70a87143cf14cfe9193657b  ./AHRP/query/consumer.py
b2fdac2ddba1c0b7361bb84d172dd01b3463358e57c071688f74c83fc30d68d6  ./AHRP/query/engine.py
1fd9aa088bfd13d7f1c0ba697521459d8267752e50c7b643099308f8e400c2ea  ./AHRP/schema/experience-event.schema.json
e9a8d96af66a0d0a70b7c54d9f6b9e2ed80db66196efabe68ad60c6e1586dde2  ./AHRP/schema/verification.schema.json
78c6d4c39af0aceabf697fc10451c6dc3d79e134a7b7e67ded37a7683be50dd6  ./AHRP/spec/AHRP_SPEC_v0.1.md
7634ed316433159a6bbcfbb1be9b8808541c8599b1adf6a43f7f775a1b872bf4  ./AHRP/tests/__init__.py
09db9f94be2d31879bb74cfa7217c90403fae865cafab30306ec4d93229ff2b2  ./AHRP/tests/_helpers.py
b7685adfff95b6b86cfb4c5c0de3a473bab32558098f12003d31a0233ddee621  ./AHRP/tests/test_failure_cases.py
369c85d82e2ea3c5ba4aaa8270551033ba828ec9989255eb7c5eeeb2b255dd46  ./AHRP/tests/test_query.py
de26d5213d2f4e5ec2c3d3b075737e7e852708421726f5862db5ecd131f71ca3  ./AHRP/tests/test_schema.py
8c5d98f6f4d86dfb61676941b74b2637eac1eac67a9de9ea5a38eba75bf62cec  ./AHRP/tests/test_validator.py
8b1f1ec82747b5749ab7265477cbd9019d95ce33137a8909e78299461c660828  ./AHRP/validator/__init__.py
e71d159ecdabb5df8cb3ba2a02bd9fddff4ac2f5fa81656eea247f3fe0f57ce5  ./AHRP/validator/core.py
2a7de56ea765225ee450df5a14e4df5052ecd6182392500379b09b9cda82af40  ./AHRP/validator/jsonschema_subset.py
```

## 5. Artifacts Copied into the Isolated Worktree

| Artifact | Destination in worktree | Notes |
|---|---|---|
| `AHRP/` (26 files) | `./AHRP/` | Root-level working copy for remediation |
| Full review package incl. governance docs, REVIEW_MANIFEST.json, INDEPENDENT_REVIEW_REPORT.md, evidence/, file-hashes.sha256 | `./.review-staging/AHRP-v0.1-independent-review-package/` | Unmodified provenance copy |
| Original ZIP | `./.review-staging/AHRP-v0.1-independent-review-package.zip` | SHA-256 re-verified after copy |

Not copied: `.git`, caches, virtual environments (none present).

## 6. Copy Verification Results

- Root `AHRP/` copy vs. baseline: `shasum -a 256` output identical for
  all 26 files — **PASS**.
- Staging-package `AHRP/` copy vs. baseline: identical — **PASS**.
- ZIP SHA-256 in worktree:
  `8cf571fc050ecb0635c4158c4690d3bd6fc08501e3c2644c3942377cf33d5833`
  — matches the known original ZIP hash — **PASS**.

## 7. Governance Notes

- The original dirty worktree must remain untouched throughout the
  remediation phases.
- No commits are made in Phase 1; commits are reserved for Phase 8.
- This baseline document itself lives only in the isolated worktree and
  is not yet committed.

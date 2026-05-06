# Execution Evidence Bridge — Reviewer Brief

This is a runnable cross-repository bridge showing how AI execution integrity
proof can become portable, independently verifiable evidence artifacts. It
connects execution proof, evidence packaging, offline verification, and a guided
reviewer walkthrough without collapsing the layer boundaries. The goal is to
make the handoff inspectable by reviewers, hiring managers, technical
evaluators, and collaborators.

## One-line positioning

MVK proves what happened; Agent Evidence packages and verifies the proof; Verifiable Agent Demo gives reviewers the shortest walkthrough across the stack.

## What it demonstrates

- deterministic execution artifact generation
- replay / integrity verification
- tamper-evident audit bundle
- AEP-compatible evidence handoff
- offline verification
- reviewer-facing walkthrough

## Repository roles

| Repository | Role | What to inspect |
| --- | --- | --- |
| digital-biosphere-architecture | Architecture hub | `docs/execution-evidence-bridge-map.md` and `docs/announcements/execution-evidence-bridge.md` |
| fdo-kernel-mvk | Execution integrity kernel | `make demo`, `make verify-demo`, `make export-aep`, `make verify-aep` |
| agent-evidence | Evidence packaging and verification | `verify-bundle`, signed export, receipts, review pack |
| verifiable-agent-demo | Guided walkthrough | `make mvk-aep-bridge-demo` |

## Fastest runnable path

```bash
cd ../fdo-kernel-mvk
make demo
make verify-demo
make export-aep
make verify-aep

cd ../agent-evidence
agent-evidence verify-bundle --bundle-dir ../fdo-kernel-mvk/mvk-aep-bundle

cd ../verifiable-agent-demo
make mvk-aep-bridge-demo
```

## Why reviewers should care

Ordinary logs and traces are useful for debugging. This bridge focuses on
handoff: evidence that another party can inspect and verify later.

Execution integrity and evidence packaging are separated cleanly, so the proof
of what happened is not confused with the portable package used to review it.
The demo makes the chain understandable without requiring reviewers to read the
full architecture first.

## What this is not

- not legal non-repudiation
- not compliance certification
- not AI Act approval
- not official FDO standard adoption
- not production forensic timestamping
- not a substitute for legal, compliance, or security review

## Links

- Execution evidence bridge map: [../execution-evidence-bridge-map.md](../execution-evidence-bridge-map.md)
- Reviewer announcement: [../announcements/execution-evidence-bridge.md](../announcements/execution-evidence-bridge.md)
- fdo-kernel-mvk PR: [https://github.com/joy7758/fdo-kernel-mvk/pull/8](https://github.com/joy7758/fdo-kernel-mvk/pull/8)
- agent-evidence PR: [https://github.com/joy7758/agent-evidence/pull/73](https://github.com/joy7758/agent-evidence/pull/73)
- verifiable-agent-demo PR: [https://github.com/joy7758/verifiable-agent-demo/pull/26](https://github.com/joy7758/verifiable-agent-demo/pull/26)
- architecture map PR: [https://github.com/joy7758/digital-biosphere-architecture/pull/7](https://github.com/joy7758/digital-biosphere-architecture/pull/7)
- announcement PR: [https://github.com/joy7758/digital-biosphere-architecture/pull/8](https://github.com/joy7758/digital-biosphere-architecture/pull/8)

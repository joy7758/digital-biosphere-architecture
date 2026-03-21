# Layer Boundaries

Digital Biosphere Architecture is the architecture narrative hub. It explains how the repositories fit together, but it is not where runtime logic, benchmark code, or production demo code should live.

## Canonical layer map

| Surface | Role |
| --- | --- |
| `digital-biosphere-architecture` | architecture narrative hub |
| POP / `persona-object-protocol` | persona layer |
| AIP / `agent-intent-protocol` | interaction layer |
| `token-governor` | governance layer |
| `fdo-kernel-mvk` | execution integrity layer |
| `aro-audit` | audit verification and control plane |

## Adjacent repositories

| Surface | Role |
| --- | --- |
| `agent-evidence` | semantic evidence substrate and capture-side SDK |
| `verifiable-agent-demo` | guided walkthrough demo across the stack |
| `agent-governance-benchmark` | evaluation repo for scenarios, metrics, and results |
| `agent-object-protocol` | adjacent interoperability annex |

## Boundary rules

- This repository owns explanation, repository-role mapping, terminology, and long-form architecture context.
- POP owns persona portability. It does not own governance, audit, or benchmark logic.
- AIP owns interaction semantics. It does not own runtime orchestration or transport.
- Token Governor owns governance decisions about what should be allowed.
- MVK owns execution truth and replay-verifiable integrity.
- ARO-Audit owns post-execution review, verification, and export.
- Agent Evidence is a capture substrate that can feed the broader audit story, but it is not the audit control plane.
- Demo, benchmark, and legacy repositories are part of the ecosystem, but they are not part of this repository's canonical entry path.

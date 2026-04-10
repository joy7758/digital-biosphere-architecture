# FDO Profile Proposal Entry

This document defines how the Digital Biosphere Architecture should be read as a
set of candidate FDO-facing layer artifacts.

For public routing, start with
`digital-biosphere-architecture` as the architecture hub. From there, route to
`agent-evidence` for the concrete execution-evidence entry,
`verifiable-agent-demo` for the shortest walkthrough, and `aro-audit` for the
post-execution audit control plane.

## Purpose

The goal is not to claim a full FDO standard, but to identify which parts of the architecture can be discussed in FDO terms such as:

- object
- profile
- conformance surface
- provenance reference
- integrity reference
- validation fixture

## Candidate Layer Artifacts

| Architecture Layer | Repository | Candidate FDO-facing Role |
|---|---|---|
| Persona Layer | persona-object-protocol | persona object profile candidate |
| Interaction Layer | agent-intent-protocol | interaction semantics profile candidate |
| Governance Layer | token-governor | runtime governance reference implementation |
| Execution Integrity Layer | fdo-kernel-mvk | conformance and verification surface |
| Audit Evidence Layer | aro-audit | audit evidence profile candidate |

## Interpretation Rule

These repositories should be interpreted as a coordinated architecture rather than isolated projects.

The public entry sequence is:

1. Digital Biosphere Architecture
2. Agent Evidence
3. Verifiable Agent Demo
4. ARO-Audit
5. layer repositories such as POP, AIP, Token Governor, and MVK

## Scope Boundary

This is a proposal entry note for architectural interpretation and discussion readiness.

It does not claim formal endorsement by the FDO Forum or any official standards body.

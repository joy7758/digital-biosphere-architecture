# FDO Profile Proposal Entry

This document defines how the Digital Biosphere Architecture should be read as a set of candidate FDO-facing entry artifacts.

## Purpose

The goal is not to claim a full FDO standard, but to identify which parts of the architecture can be discussed in FDO terms such as:

- object
- profile
- conformance surface
- provenance reference
- integrity reference
- validation fixture

## Candidate Entry Artifacts

| Architecture Layer | Repository | Candidate FDO-facing Role |
|---|---|---|
| Persona Layer | persona-object-protocol | persona object profile candidate |
| Interaction Layer | agent-intent-protocol | interaction semantics profile candidate |
| Governance Layer | token-governor | runtime governance reference implementation |
| Execution Integrity Layer | fdo-kernel-mvk | conformance and verification surface |
| Audit Evidence Layer | aro-audit | audit evidence profile candidate |

## Interpretation Rule

These repositories should be interpreted as a coordinated architecture rather than isolated projects.

The standard entry sequence is:

1. Digital Biosphere Architecture
2. POP
3. AIP
4. ARO-Audit
5. MVK
6. Token Governor

## Scope Boundary

This is a proposal entry note for architectural interpretation and discussion readiness.

It does not claim formal endorsement by the FDO Forum or any official standards body.

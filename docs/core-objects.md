# Core Objects

These object names are narrative-level definitions for the Digital Biosphere
Architecture ecosystem. They align the stack without changing protocol
semantics in the component repositories.

## Persona Object

- Role: carries the identity-facing object for an autonomous system.
- Minimal meaning: a portable representation of who or what is acting.
- Where it appears in the ecosystem: the Persona Layer, primarily in [joy7758/persona-object-protocol](https://github.com/joy7758/persona-object-protocol).

## Governance Control

- Role: constrains what the system is allowed to do under explicit policy.
- Minimal meaning: a runtime-facing control surface for permissions, budgets, and policy boundaries.
- Where it appears in the ecosystem: the Governance Layer, primarily in [joy7758/token-governor](https://github.com/joy7758/token-governor).

## Execution Integrity Record

- Role: preserves the runtime facts needed to evaluate execution claims.
- Minimal meaning: a minimal record of what actually happened during execution.
- Where it appears in the ecosystem: the Execution Integrity Layer, primarily in [joy7758/fdo-kernel-mvk](https://github.com/joy7758/fdo-kernel-mvk).

## Audit Evidence Bundle

- Role: packages execution-relevant outputs for verification, review, and export.
- Minimal meaning: a portable evidence artifact that supports independent inspection.
- Where it appears in the ecosystem: the Audit Evidence Layer, primarily in [joy7758/aro-audit](https://github.com/joy7758/aro-audit).

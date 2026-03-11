# Architecture Map

Digital Biosphere Architecture is a layered model for verifiable AI systems. Each repository has a focused job. The architecture becomes legible when the layers are read together instead of collapsed into one framework.

## Persona Layer

- Purpose: define the identity-bearing object that can travel across runtimes.
- Output: a portable persona object that can be attached to an agent context.
- Linked repo: [joy7758/persona-object-protocol](https://github.com/joy7758/persona-object-protocol)

## Interaction Layer

- Purpose: define machine-readable intent, action, and result objects.
- Output: semantic interaction objects that can be evaluated before execution and referenced after execution.
- Linked repo: [joy7758/agent-intent-protocol](https://github.com/joy7758/agent-intent-protocol)

## Governance Layer

- Purpose: apply policy, budget, and control constraints before behavior is accepted.
- Output: governance controls that bound what the system is allowed to do.
- Linked repo: [joy7758/token-governor](https://github.com/joy7758/token-governor)

## Execution Integrity Layer

- Purpose: preserve runtime truth about what actually happened during execution.
- Output: integrity-relevant runtime facts and verification surfaces for execution claims.
- Linked repo: [joy7758/fdo-kernel-mvk](https://github.com/joy7758/fdo-kernel-mvk)

## Audit Evidence Layer

- Purpose: turn execution-relevant activity into reviewable and exportable evidence.
- Output: audit evidence bundles and verification-ready records.
- Linked repo: [joy7758/aro-audit](https://github.com/joy7758/aro-audit)

## What this is not

Digital Biosphere Architecture is not a monolithic agent framework. It does not replace the component repositories with one runtime or one API surface. It is an architecture-first ecosystem model for identity, interaction, governance, execution integrity, and audit evidence.

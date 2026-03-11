# Ecosystem Status - March 2026

## Current five-layer architecture

Digital Biosphere Architecture is currently presented as a five-layer stack:

1. Persona Layer
2. Interaction Layer
3. Governance Layer
4. Execution Integrity Layer
5. Audit Evidence Layer

## Repository mapping

| Layer | Repository |
| --- | --- |
| Persona Layer | [persona-object-protocol](https://github.com/joy7758/persona-object-protocol) |
| Interaction Layer | [agent-intent-protocol](https://github.com/joy7758/agent-intent-protocol) |
| Governance Layer | [token-governor](https://github.com/joy7758/token-governor) |
| Execution Integrity Layer | [fdo-kernel-mvk](https://github.com/joy7758/fdo-kernel-mvk) |
| Audit Evidence Layer | [aro-audit](https://github.com/joy7758/aro-audit) |
| Cross-layer demonstration | [verifiable-agent-demo](https://github.com/joy7758/verifiable-agent-demo) |

## What each layer does

- Persona Layer: defines who the agent is as a portable persona object.
- Interaction Layer: defines machine-readable intent, action, and result objects.
- Governance Layer: evaluates policy, budget, fallback, and risk before execution.
- Execution Integrity Layer: preserves runtime truth and verification-relevant execution facts.
- Audit Evidence Layer: exports reviewable evidence, receipts, and replay-oriented records.

## What is already implemented

- POP is publicly positioned as the Persona Layer.
- Agent Intent Protocol now exists as a draft Interaction Layer scaffold with schemas and conformance fixtures.
- Token Governor is publicly positioned as the Governance Layer and governance checkpoint.
- MVK remains the execution-integrity reference in the stack narrative.
- ARO-Audit is publicly positioned as the Audit Evidence Layer.
- Verifiable Agent Demo now emits explicit interaction objects and audit artifacts across the stack.

## What is still draft

- Agent Intent Protocol remains an early semantic interaction draft rather than a finalized standard.
- Cross-repository object interoperability is still narrative-first and not yet a locked conformance program.
- Execution Integrity Layer details remain represented primarily through MVK positioning rather than a full cross-repo integration profile.

## Minimal end-to-end flow

Persona Object -> Intent Object -> Governance Check -> Execution Trace -> Audit Receipt

## Suggested citation and reference links

- Architecture hub: https://github.com/joy7758/digital-biosphere-architecture
- POP: https://github.com/joy7758/persona-object-protocol
- Agent Intent Protocol: https://github.com/joy7758/agent-intent-protocol
- Token Governor: https://github.com/joy7758/token-governor
- MVK: https://github.com/joy7758/fdo-kernel-mvk
- ARO-Audit: https://github.com/joy7758/aro-audit
- Verifiable Agent Demo: https://github.com/joy7758/verifiable-agent-demo

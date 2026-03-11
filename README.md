# Digital Biosphere Architecture

A governance-oriented architecture for autonomous AI systems.

## One-Line Definition

Digital Biosphere Architecture is a research architecture for verifiable AI systems.

## Overview

Digital Biosphere Architecture is the parent architecture repository for a set
of core components that describe how autonomous AI systems carry identity,
accept governance constraints, preserve execution integrity, and emit audit
evidence.

It is not a monolithic agent framework. It exists as a narrative hub and
architecture hub that makes identity, governance, execution integrity, and
audit evidence legible as one coordinated stack.

Narrative spine: persona -> governance -> execution integrity -> audit evidence.

## Architecture Diagram

![Digital Biosphere Architecture stack](assets/architecture/digital-biosphere-architecture-stack.svg)

Static reference diagram for the four-layer architecture.

## Why this stack exists

- Persona alone is not enough because identity without control boundaries does not make system behavior trustworthy.
- Governance must precede trust because acceptable behavior needs explicit policy before outputs can be treated as reliable.
- Execution integrity matters because runtime claims need verifiable facts about what actually happened.
- Audit evidence must be exportable because outside reviewers need portable artifacts instead of internal-only assertions.

## Start in 5 Minutes

- [Verifiable Agent Demo](https://github.com/joy7758/verifiable-agent-demo) for a compact end-to-end walkthrough.
- [POP quick trial](https://github.com/joy7758/persona-object-protocol/blob/main/TRY_POP.md) for a minimal persona-layer entry point.
- [ARO-Audit quick demo](https://github.com/joy7758/aro-audit/blob/main/docs/demos/execution-receipt-demo.md) for evidence-oriented outputs.

## Architecture at a Glance

```mermaid
flowchart TD
    P["Persona Layer<br/>POP"] --> G["Governance Layer<br/>Token Governor"]
    G --> E["Execution Integrity Layer<br/>MVK"]
    E --> A["Audit Evidence Layer<br/>ARO-Audit"]
```

## Core Layers

### Persona Layer

Portable persona objects and identity attachment.
This layer defines how a system carries a stable identity-facing object across
tools, runtimes, and interactions.

### Governance Layer

Policy, permissions, budget, and runtime constraints.
This layer decides what an autonomous system is allowed to do before behavior
is treated as acceptable or trusted.

### Execution Integrity Layer

What actually happened during execution.
This layer focuses on runtime truth, integrity checks, and minimal
verification surfaces for execution claims.

### Audit Evidence Layer

Evidence bundles, exportable records, and verifiable audit trails.
This layer turns execution-relevant activity into artifacts that can be
reviewed, exported, and referenced in governance workflows.

## Ecosystem Repositories

- POP — Persona Object Protocol ([joy7758/persona-object-protocol](https://github.com/joy7758/persona-object-protocol))
- Token Governor — runtime governance and token control ([joy7758/token-governor](https://github.com/joy7758/token-governor))
- MVK — execution integrity layer ([joy7758/fdo-kernel-mvk](https://github.com/joy7758/fdo-kernel-mvk))
- ARO-Audit — audit evidence and verification pipeline ([joy7758/aro-audit](https://github.com/joy7758/aro-audit))

## Design Intent

- separation of concerns
- composability
- verifiable operation
- architecture-first ecosystem alignment

## Documents

- [Architecture](docs/architecture.md)
- [Ecosystem Map](docs/ecosystem-map.md)
- [Architecture Map](docs/architecture-map.md)
- [Core Objects](docs/core-objects.md)
- [One-Page Brief](docs/one-page-brief.md)

## Status

- early architecture hub
- working draft
- ecosystem alignment in progress

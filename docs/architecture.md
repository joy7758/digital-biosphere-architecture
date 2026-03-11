# Architecture

## Why This Architecture

Digital Biosphere Architecture exists to solve a framing problem. POP, Agent Intent Protocol, Token Governor, MVK, and ARO-Audit can each be understood on their own, but the ecosystem becomes much clearer when they are read as one governance-oriented stack for autonomous AI systems.

This repository gives readers a single entry point for system shape, layer boundaries, and repository relationships. Its purpose is to explain how the parts fit together without collapsing them into one large framework.

## Scope

This repository defines architectural framing, core layer language, and the relationship between the main repositories in the ecosystem.

It does not define a universal runtime, replace the component repositories, or attempt to become a single all-in-one agent platform. The focus here is the upper-level governance architecture around identity, interaction, control, integrity, and evidence.

## The Five-Layer Stack

### Persona Layer

The Persona Layer provides portable persona objects and identity attachment. Its role is to give autonomous systems a stable identity-facing object that can be referenced across tools, runtimes, and interaction contexts.

In the current ecosystem, POP is the main repository associated with this layer.

### Interaction Layer

The Interaction Layer provides machine-readable intent, action, and result objects. Its role is to declare what is being requested, what action is proposed or taken, and what outcome status is returned.

In the current ecosystem, Agent Intent Protocol is the main repository associated with this layer.

### Governance Layer

The Governance Layer provides policy, permissions, budget control, and runtime constraints. It decides what an autonomous system is authorized to do before execution behavior is accepted as valid.

In the current ecosystem, Token Governor is the main repository associated with this layer.

### Execution Integrity Layer

The Execution Integrity Layer focuses on what actually happened during execution. It establishes the minimal verification surface needed to inspect execution claims, constraint adherence, and integrity-relevant runtime facts.

In the current ecosystem, MVK is the main repository associated with this layer.

### Audit Evidence Layer

The Audit Evidence Layer packages evidence bundles, exportable records, and verifiable audit trails. It preserves the artifacts needed for later review, external reporting, and governance-linked verification workflows.

In the current ecosystem, ARO-Audit is the main repository associated with this layer.

## Design Principles

- Keep layer boundaries explicit.
- Separate persona, interaction, governance, execution integrity, and audit concerns.
- Favor composable repositories over one opaque framework.
- Treat verifiable operation as an architectural requirement, not a later add-on.
- Keep the stack extensible so future repositories can align without changing the core story.

## How the Layers Work Together

The intended reading order is:

1. Persona establishes what identity-bearing object is acting.
2. Interaction establishes what is being requested or attempted.
3. Governance constrains what that actor is allowed to do.
4. Execution integrity checks what actually happened during execution.
5. Audit evidence preserves the resulting records in reviewable form.

This sequence is not a claim that all systems must run as a strict pipeline. It is an architectural model for reasoning about responsibility, trust, and evidence across the ecosystem.

## Relationship Between Existing Repositories

| Repository | Primary role | Relationship to the stack |
| --- | --- | --- |
| [POP](https://github.com/joy7758/persona-object-protocol) | Persona representation and identity attachment | Persona Layer |
| [Agent Intent Protocol](https://github.com/joy7758/agent-intent-protocol) | Semantic intent, action, and result objects | Interaction Layer |
| [Token Governor](https://github.com/joy7758/token-governor) | Governance controls, permissions, and runtime limits | Governance Layer |
| [MVK](https://github.com/joy7758/fdo-kernel-mvk) | Verification kernel for execution integrity | Execution Integrity Layer |
| [ARO-Audit](https://github.com/joy7758/aro-audit) | Audit evidence, exports, and verification support | Audit Evidence Layer |

This repository sits above those repositories as the architecture hub. Its job is to keep the stack readable, preserve consistent language, and provide a shared reference point for ecosystem alignment.

## Current Status

The repository is currently an early architecture hub and working draft.

The core layer model is established, but ecosystem alignment is still in progress. Likely next steps include tighter terminology, clearer cross-repo references, and more explicit shared models where interoperability matters.

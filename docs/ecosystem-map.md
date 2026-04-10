# Ecosystem Map

## Purpose of This Map

This map explains the role of the core repositories in the Digital Biosphere
Architecture ecosystem and shows how they are meant to be read as one
architecture.

It is not a dependency chart for one codebase. It is a system map for identity,
governance, execution integrity, and audit evidence across related
repositories.

## Primary Entry Surfaces

### Digital Biosphere Architecture

Repository: [joy7758/digital-biosphere-architecture](https://github.com/joy7758/digital-biosphere-architecture)

This is the canonical architecture hub for the ecosystem. It is the right place
to start when a reader needs the system view, repository boundaries, and
cross-repo navigation.

### Agent Evidence

Repository: [joy7758/agent-evidence](https://github.com/joy7758/agent-evidence)

Agent Evidence is the concrete execution-evidence entry. It packages
agent/runtime execution into portable evidence bundles for offline
verification.

### Verifiable Agent Demo

Repository: [joy7758/verifiable-agent-demo](https://github.com/joy7758/verifiable-agent-demo)

Verifiable Agent Demo is the shortest walkthrough across the execution-evidence
path. It is a guided demo surface rather than the architecture hub or the
canonical evidence package.

### ARO-Audit

Repository: [joy7758/aro-audit](https://github.com/joy7758/aro-audit)

ARO-Audit is the post-execution audit control plane. It handles receipts,
replay-oriented review, conformance, and export surfaces after evidence has
already been packaged.

## Layer Repositories

### POP

Repository: [joy7758/persona-object-protocol](https://github.com/joy7758/persona-object-protocol)

POP defines portable persona objects and identity-facing attachment points. It
anchors the part of the stack that needs a stable representation of who or what
is acting across runtimes and interaction surfaces.

### AIP

Repository: [joy7758/agent-intent-protocol](https://github.com/joy7758/agent-intent-protocol)

AIP defines bounded intent, action, and result semantics. It provides the
interaction layer that sits between persona identity and runtime governance.

### Token Governor

Repository: [joy7758/token-governor](https://github.com/joy7758/token-governor)

Token Governor defines runtime governance controls such as policy, permissions,
budget awareness, and execution constraints. It provides the layer that decides
what an autonomous system is allowed to do under explicit control conditions.

### MVK

Repository: [joy7758/fdo-kernel-mvk](https://github.com/joy7758/fdo-kernel-mvk)

MVK serves as the execution integrity layer. It focuses on minimal
verification, execution-relevant truth, and the conditions under which runtime
claims can be treated as integrity-bearing.

## How They Fit Together

The ecosystem is intended to be read in the following public order:

1. architecture hub
2. concrete execution-evidence entry
3. shortest walkthrough or direct layer work
4. post-execution audit control plane

In repository terms, that means:

1. Digital Biosphere Architecture explains the whole system.
2. Agent Evidence packages the execution-evidence handoff.
3. Verifiable Agent Demo shows the shortest end-to-end walkthrough.
4. ARO-Audit handles downstream review and conformance.

The coordinated layer order remains:

1. persona
2. interaction
3. governance
4. execution integrity
5. audit evidence

In layer-repository terms, that means:

1. POP defines the identity-bearing object.
2. AIP defines bounded interaction semantics.
3. Token Governor applies runtime policy and control.
4. MVK verifies what actually happened during execution.
5. ARO-Audit handles post-execution review over bounded artifacts.

This ordering is a conceptual stack, not a claim that all repositories must be
deployed together. The point is architectural coordination: each repository has
its own scope, but together they form a coherent governance-oriented model.

## Future Alignment Directions

- shared schemas
- interoperable evidence models
- consistent architecture language
- possible alignment with standards and object models

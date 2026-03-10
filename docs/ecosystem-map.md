# Ecosystem Map

## Purpose of This Map

This map explains the role of the core repositories in the Digital Biosphere
Architecture ecosystem and shows how they are meant to be read as one
architecture.

It is not a dependency chart for one codebase. It is a system map for identity,
governance, execution integrity, and audit evidence across related
repositories.

## Core Repositories

### POP

Repository: [joy7758/persona-object-protocol](https://github.com/joy7758/persona-object-protocol)

POP defines portable persona objects and identity-facing attachment points. It
anchors the part of the stack that needs a stable representation of who or what
is acting across runtimes and interaction surfaces.

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

### ARO-Audit

Repository: [joy7758/aro-audit](https://github.com/joy7758/aro-audit)

ARO-Audit captures evidence bundles, exportable records, and verifiable audit
trails. It supports downstream review, reporting, and verification workflows by
making execution-relevant evidence portable and inspectable.

## How They Fit Together

The ecosystem is intended to be read in the following architectural order:

1. persona
2. governance
3. execution integrity
4. audit evidence

In repository terms, that means:

1. POP defines the identity-bearing object.
2. Token Governor applies runtime policy and control.
3. MVK verifies what actually happened during execution.
4. ARO-Audit packages the evidence trail for later inspection and export.

This ordering is a conceptual stack, not a claim that all repositories must be
deployed together. The point is architectural coordination: each repository has
its own scope, but together they form a coherent governance-oriented model.

## Future Alignment Directions

- shared schemas
- interoperable evidence models
- consistent architecture language
- possible alignment with standards and object models

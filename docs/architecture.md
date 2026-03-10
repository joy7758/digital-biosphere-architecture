# Architecture

## Why This Architecture

Digital Biosphere Architecture exists to solve a framing problem: projects such
as POP, Token Governor, MVK, and ARO-Audit are easier to understand when they
are read as one stack rather than as four unrelated repositories.

The architecture hub gives outside readers, collaborators, and reviewers a
single entry point. Its job is to clarify system shape, layer boundaries, and
the relationship between repositories before they dive into implementation
details.

## The Four-Layer Stack

### Persona Layer

POP defines the identity-facing surface of the system. It is where agent or
persona continuity, representation, and persona-level interfaces are modeled.

### Governance Layer

Token Governor defines how policies, permissions, and governance constraints
are attached to autonomous behavior. This layer determines what is allowed
before execution claims are trusted.

### Execution Integrity Layer

MVK provides the minimal verification surface for integrity-critical execution.
It is responsible for checking whether an execution path or claim satisfies the
system's required verification conditions.

### Audit Evidence Layer

ARO-Audit captures the evidence trail that makes actions inspectable after the
fact. It turns system behavior into audit artifacts that can be reviewed,
replayed, or referenced in governance workflows.

## Design Principles

- Keep layer boundaries explicit.
- Separate persona, governance, execution integrity, and audit concerns.
- Treat governance as a first-class control surface rather than a later add-on.
- Prefer verifiable evidence over informal claims.
- Keep the architecture open to future repositories without rewriting the core
  story.

## Relationship Between Existing Repositories

| Repository | Primary role | Relationship to the stack |
| --- | --- | --- |
| POP | Persona representation and continuity | Persona Layer |
| Token Governor | Policy and governance enforcement | Governance Layer |
| MVK | Verification kernel for execution integrity | Execution Integrity Layer |
| ARO-Audit | Audit evidence and review trail | Audit Evidence Layer |

This repository is the architecture hub above those repositories. It explains
how they connect, what each layer is responsible for, and how they can be read
as a coherent system.

Additional repositories may sit beside or below this stack over time. The goal
is not to freeze the ecosystem, but to keep a stable architectural spine as the
ecosystem grows.

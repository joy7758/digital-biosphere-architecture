# One-Page Brief

## 1. What It Is

Digital Biosphere Architecture is a governance-oriented architecture for
autonomous AI systems. It is not a single agent framework and it is not meant
to absorb every capability into one codebase. Instead, it organizes four
concerns into a clear stack: persona, governance, execution integrity, and
audit evidence.

## 2. Why It Exists

- Many AI systems mix identity, policy, execution behavior, and evidence in
  ad hoc ways.
- Systems can often act, but they do not always make boundaries and
  accountability easy to explain.
- Governance controls and audit records are frequently added late, instead of
  being treated as part of the architecture.
- Useful ecosystem tools already exist, but architecture-level coordination is
  often missing.

## 3. The Four-Layer Model

### Persona Layer

This layer defines the identity-facing object in the system. Its role is to
make persona attachment portable and understandable across runtimes and tools.

### Governance Layer

This layer defines policy, permissions, budget awareness, and runtime control.
Its role is to clarify what a system is allowed to do and under what
constraints.

### Execution Integrity Layer

This layer focuses on what actually happened during execution. Its role is to
provide a verification surface for runtime truth, integrity checks, and
execution-relevant claims.

### Audit Evidence Layer

This layer preserves evidence bundles, exportable records, and verifiable audit
trails. Its role is to keep execution outcomes inspectable after the fact.

## 4. Core Repositories

### [persona-object-protocol](https://github.com/joy7758/persona-object-protocol)

Defines portable persona objects and identity attachment.
It contributes the Persona Layer of the stack.

### [token-governor](https://github.com/joy7758/token-governor)

Defines runtime governance controls such as policy, permissions, and
budget-aware control.
It contributes the Governance Layer of the stack.

### [fdo-kernel-mvk](https://github.com/joy7758/fdo-kernel-mvk)

Explores execution truth, verification surface, and runtime integrity.
It contributes the Execution Integrity Layer of the stack.

### [aro-audit](https://github.com/joy7758/aro-audit)

Defines exportable records, evidence bundles, and audit verification workflows.
It contributes the Audit Evidence Layer of the stack.

## 5. How to Read the Stack

persona -> governance -> execution integrity -> audit evidence

This is an architectural reading order for understanding responsibility,
control, runtime truth, and evidence. It is not a required deployment order,
and it does not assume every repository must be used in the same system.

## 6. What This Repository Does

- provide architecture language
- explain repository relationships
- act as an ecosystem entry point
- support future alignment across related projects

## 7. Current Status

- early architecture hub
- working draft
- ecosystem alignment in progress

## 8. Short Closing

The goal of this architecture is not to force identity, governance, execution
integrity, and audit evidence into one large framework. The goal is to make
their relationship clear, composable, and durable as the ecosystem evolves.

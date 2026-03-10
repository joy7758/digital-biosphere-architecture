# Ecosystem Map

## Core Repositories

- POP
- Token Governor
- MVK
- ARO-Audit

## Role of Each Repository

| Repository | Role |
| --- | --- |
| POP | Defines persona-facing identity and continuity objects. |
| Token Governor | Defines governance rules, permissions, and control points. |
| MVK | Verifies execution integrity claims and minimal trust conditions. |
| ARO-Audit | Records audit evidence and reviewable execution traces. |

## How They Fit Together

The stack is intended to be read from top to bottom:

1. POP presents the persona or identity-facing surface.
2. Token Governor constrains what the system is allowed to do.
3. MVK verifies whether execution-critical claims satisfy required conditions.
4. ARO-Audit preserves the evidence trail for later inspection.

This repository provides the shared map for those components so the ecosystem
can be understood as one architecture rather than as disconnected repositories.

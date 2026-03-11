# Interaction Layer

## Purpose

The Interaction Layer exists to define machine-readable intent, action, and result objects for coordination between agents, runtimes, and governance checkpoints.

## Why interaction must be separate from persona

Persona objects answer who is acting. They do not, by themselves, define the requested task, the proposed action, or the returned result. Keeping interaction separate preserves identity portability without overloading the persona layer with task semantics.

## Why interaction must be separate from evidence

Evidence objects answer what can be reviewed after execution. They are not the same as the semantic object that declared the request before execution or the result status immediately after execution. Conflating interaction with evidence makes it harder to distinguish requested behavior from exported proof artifacts.

## Why governance acts on intent and action before execution

Governance is most effective when it evaluates declared intent and proposed actions before runtime execution occurs. This allows policy, budget, fallback, and risk controls to act on a compact semantic surface instead of reacting only after execution has already happened.

## FDO-style object thinking

The Digital Biosphere Architecture follows FDO-style object thinking by keeping object classes narrow and composable. Persona objects, interaction objects, governance decisions, execution traces, and audit receipts should remain distinct object types with explicit handoff points.

## Interaction-layer repository

The current interaction-layer draft is [Agent Intent Protocol](https://github.com/joy7758/agent-intent-protocol).

# Lifecycle Profile RC1

Lifecycle Profile RC1 is now frozen as a small, reviewable lifecycle governance
surface for autonomous agent instances.

The scope is deliberately narrow. RC1 is about continuity semantics:

- lifecycle object shape
- lifecycle receipt shape
- lineage / fork / merge / terminate review
- executable conformance rather than document-only positioning

What is included in the current RC1 asset set:

- schemas for lifecycle objects and receipts
- valid and invalid fixtures for the minimal state machine
- main conformance checks for cross-object lifecycle semantics
- audit-layer freshness, replay, and protected-boundary verification
- a runnable walkthrough showing `init -> activate -> fork -> merge -> terminate -> verify`

This is not a new agent framework and not a new full runtime. It is also not a
claim about ontology or agent personhood. The goal is much smaller: provide a
portable lifecycle governance profile that can be reviewed, challenged, and
reused across repositories.

Out of scope for RC1:

- distributed finality
- external anchoring
- multi-writer concurrency
- shared verifier unification across every repo

If you want the smallest reading order:

1. protocol definition and lifecycle profile
2. audit-facing conformance gate
3. runnable demo walkthrough

Links:

- AOP RC1: https://github.com/joy7758/agent-object-protocol/releases/tag/lifecycle-profile-v0.1-rc1
- ARO RC1: https://github.com/joy7758/aro-audit/releases/tag/aro-lifecycle-conformance-rc1
- Demo walkthrough: https://github.com/joy7758/verifiable-agent-demo/blob/feat/lifecycle-profile-v0.1/docs/minimal-lifecycle-demo.md

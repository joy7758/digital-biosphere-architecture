# Lifecycle Profile RC1 for Agent Framework Readers

Lifecycle Profile RC1 is a small lifecycle governance and verification layer
for autonomous agents. It is meant to sit next to agent frameworks, not replace
them.

The reason for carving it out this way is simple: tracing and callbacks can
show what happened during a run, but lifecycle governance asks a different set
of questions. Was this instance validly forked? Which lineage does it belong
to? Was a merge actually closed? Did a terminated branch try to become active
again? Those questions need a bounded object and receipt surface, plus a
conformance gate.

RC1 currently includes:

- lifecycle object and receipt schemas
- minimal fixtures for the state machine
- executable lifecycle conformance checks
- audit-layer freshness, replay, and tamper review
- a runnable walkthrough with `fork -> merge -> terminate -> verify`

What this is not:

- not a new framework
- not a replacement for LangChain, OpenAI Agents, or other runtimes
- not a tracing backend
- not a metaphysical identity model

The intended use is external-first. A runtime can stay the same while exporting
reviewable lifecycle artifacts that another system can inspect. That keeps the
integration surface small and makes lifecycle governance more portable than
runtime-specific internal state.

Out-of-scope for RC1 includes distributed consensus, external anchoring, and a
shared cross-repo verifier library. Those can come later. The current point is
to make lifecycle governance enforceable enough that exported branches and
receipts can be reviewed consistently.

Links:

- AOP RC1: https://github.com/joy7758/agent-object-protocol/releases/tag/lifecycle-profile-v0.1-rc1
- ARO RC1: https://github.com/joy7758/aro-audit/releases/tag/aro-lifecycle-conformance-rc1
- Demo walkthrough: https://github.com/joy7758/verifiable-agent-demo/blob/feat/lifecycle-profile-v0.1/docs/minimal-lifecycle-demo.md

# Lifecycle Profile RC1 in an Object-and-Evidence Frame

Lifecycle Profile RC1 is a minimal governance profile for autonomous agent
continuity. It is useful in an object-and-evidence context because it turns
continuity claims into reviewable lifecycle objects and bounded lifecycle
receipts.

The key point is not to claim that an agent is a life form. The key point is to
make lifecycle semantics explicit enough to review: which object instance is in
scope, which lineage it belongs to, which transition is being asserted, and
which evidence or governance decision supports that assertion.

That gives RC1 three distinct surfaces:

- an object surface for current lifecycle state
- a receipt surface for governed transitions
- an evidence or conformance surface for replay, freshness, and boundary review

The current RC1 release candidate includes:

- lifecycle schemas and fixtures in the protocol layer
- executable conformance checks for lineage, terminal-state, and merge or fork rules
- audit-facing verification for receipt freshness, replay, and protected-boundary tamper
- a runnable demo that closes the loop with an actual merge path

This makes RC1 relevant to digital-object discussions where continuity,
lineage, and evidence portability matter. It does not try to become a full FDO
theory, and it does not claim to solve global persistence or universal object
identity. It is a smaller thing: a first reviewable lifecycle governance sample
for autonomous agents.

Out of scope for RC1:

- personhood or ontology claims
- full object registry semantics
- distributed finality
- external anchoring guarantees

Links:

- AOP RC1: https://github.com/joy7758/agent-object-protocol/releases/tag/lifecycle-profile-v0.1-rc1
- ARO RC1: https://github.com/joy7758/aro-audit/releases/tag/aro-lifecycle-conformance-rc1
- Demo walkthrough: https://github.com/joy7758/verifiable-agent-demo/blob/feat/lifecycle-profile-v0.1/docs/minimal-lifecycle-demo.md

# Lifecycle Profile RC1 Entry

Lifecycle Profile RC1 is the first small public release candidate for lifecycle
governance semantics around autonomous agent instances.

Its purpose is narrow: make continuity, lineage, fork, merge, and terminate
claims reviewable across repositories without turning the Digital Biosphere
Architecture into a new monolithic runtime. In practice, RC1 gives external
readers a bounded answer to a limited question set: which agent instance is in
scope, which lifecycle state it is in, which governed transition was issued,
and what evidence or conformance path can be used to review that claim.

This is not a sixth layer in the architecture. The canonical five-layer stack
still stays the same:

- Persona
- Interaction
- Governance
- Execution Integrity
- Audit Evidence

Lifecycle Profile sits across those layers as a cross-layer profile. It uses
persona references, governance decisions, execution evidence, and audit-facing
receipts, but it does not replace any of those layers. That is why RC1 should
be read as a semantic profile above the stack, not as a new stack component.

For first-time readers, the official RC1 entry points are:

- `agent-object-protocol` for the protocol definition, lifecycle schemas,
  fixtures, and main conformance baseline. Canonical RC1 entry:
  `docs/releases/lifecycle-profile-v0.1-rc1.md`
- `aro-audit` for executable lifecycle receipt review, including freshness,
  replay, and protected-boundary checks. Canonical RC1 entry:
  `docs/releases/aro-lifecycle-conformance-rc1.md`
- `verifiable-agent-demo` for the smallest runnable walkthrough showing
  `init -> activate -> fork -> merge -> terminate -> verify`. Walkthrough entry:
  `docs/minimal-lifecycle-demo.md`

Read them in that order if you want the smallest stable picture:

1. define the lifecycle object and receipt shape
2. verify that exported receipts still hold up under review
3. inspect a runnable end-to-end walkthrough

RC1 is intentionally not the final word on lifecycle governance. It does not
claim distributed finality, ontology, or a complete runtime. Its role is much
smaller and more useful than that: provide a first public, reviewable, and
reusable lifecycle governance profile that external readers can actually cite.

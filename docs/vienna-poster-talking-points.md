# Vienna Poster Talking Points

## 30-Second Version

Digital Biosphere Architecture is a governance-oriented architecture for autonomous AI systems.

It organizes five layers:

- persona object
- interaction protocol
- runtime governance
- execution integrity
- audit evidence

The key claim is that autonomous AI systems need not only identity and metadata, but also verifiable execution and exportable audit evidence.

## 90-Second Version

Most current AI agent systems emphasize capability, orchestration, and tool use.

Our work focuses on the missing governance path:

- who the agent is
- how agents interact
- what runtime constraints apply
- what actually happened during execution
- what evidence can be exported for review

This is why the architecture is split into POP, AIP, Token Governor, MVK, and ARO-Audit.

We are not claiming a full FDO standard.

Publicly, readers should enter through the architecture hub first, then branch
to Agent Evidence for the concrete execution-evidence package, Verifiable Agent
Demo for the shortest walkthrough, and ARO-Audit for post-execution review.

Within that routing, we are identifying candidate FDO-facing layer artifacts:
- POP as persona object profile candidate
- AIP as interaction semantics profile candidate
- ARO-Audit as audit evidence profile candidate
- MVK as conformance and verification surface
- Token Governor as governance reference implementation

## 3-Minute Version

The Digital Biosphere Architecture is not a single product and not just an AI demo.

It is a layered governance architecture for autonomous AI systems.

The architecture starts with the persona layer, where POP defines a structured persona object.

It continues with the interaction layer, where AIP defines bounded semantics for intent, action, and result exchange.

At runtime, Token Governor provides governance controls such as policy and budget constraints.

MVK provides deterministic execution verification, replay checks, and tamper-detection surfaces.

ARO-Audit defines bounded and reviewable audit evidence artifacts with integrity and provenance-oriented references.

The contribution to FDO discussion is not that we already have a finalized standard.

The contribution is that we now have a minimal architecture matrix for
discussing autonomous AI systems in terms of:
- object
- profile
- conformance
- evidence
- reference implementation

This helps move the conversation from generic AI capability toward structured governance and verifiable evidence.

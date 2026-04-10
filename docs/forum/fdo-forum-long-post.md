# FDO Forum Long Post

## Title

Toward FDO-Facing Entry Artifacts for Autonomous AI Governance

## Draft

We have been refining the public structure of the Digital Biosphere Architecture as a layered architecture for autonomous AI systems.

The goal is not to propose a full new standard all at once.

Instead, we are trying to identify which parts of the architecture are mature enough to be discussed in FDO-facing terms such as:
- object
- profile
- conformance surface
- evidence artifact
- reference implementation

The architecture is currently organized into five coordinated layers:

- POP: persona object standard entry
- AIP: interaction protocol standard entry
- Token Governor: governance runtime entry
- MVK: execution integrity verification entry
- ARO-Audit: audit-layer control plane and profile-discussion surface

Publicly, readers should start with
`digital-biosphere-architecture` as the canonical architecture hub. From there,
`agent-evidence` is the concrete execution-evidence entry,
`verifiable-agent-demo` is the shortest walkthrough, and `aro-audit` is the
post-execution audit control plane.

Our current working interpretation is:

- POP may be discussed as a persona object profile candidate
- AIP may be discussed as an interaction semantics profile candidate
- ARO-Audit may be discussed as an audit evidence profile candidate
- MVK may be discussed as a verification and conformance surface
- Token Governor may be discussed as a runtime governance reference implementation

We are not claiming official FDO endorsement or final normative status.

What we are trying to contribute is a clearer architectural discussion boundary for autonomous AI systems:
not only who the system is, but how it interacts, how it is governed, what actually happened, and what evidence can be reviewed.

We would welcome feedback on three specific questions:

1. Are the profile boundaries currently clear enough?
2. Is audit evidence best discussed as a profile candidate?
3. Does the current crosswalk align reasonably with FDO terminology and conformance expectations?

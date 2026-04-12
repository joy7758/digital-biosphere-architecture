# Short Intros

## 1. GitHub / issue / PR

Digital Biosphere Architecture is the canonical architecture hub for the
project. Agent Evidence Profile (AEP) is the concrete execution-evidence entry,
`verifiable-agent-demo` is the shortest walkthrough, and `aro-audit` is the
audit plane for post-execution review and conformance. When a reader only needs
the main entry path, the stable route is Architecture -> Evidence -> Demo ->
Audit.

## 2. FDO / dataspace

This work separates architecture, evidence, demo, and audit surfaces instead of
collapsing them into a single repo. Digital Biosphere Architecture is the
architecture hub, Agent Evidence Profile (AEP) is the concrete evidence entry,
and the EDC Java spike should be treated only as a frozen augmentation-layer
validation artifact. In this context, EDC is a scenario-specific augmentation
environment, not the research mainline.

## 3. Academic / research collaboration

The current line is organized around a canonical architecture hub, a concrete
execution-evidence entry, a walkthrough demo, and an audit plane. Digital
Biosphere Architecture defines repository boundaries; Agent Evidence Profile
(AEP) carries the concrete execution-evidence path; `verifiable-agent-demo`
provides a compact walkthrough; and `aro-audit` focuses on post-execution
review, receipts, and conformance. The goal is not to claim a complete platform
stack, but to keep the architecture and verification surfaces explicit.

## 4. General technical introduction

The project is structured so different readers can enter from the right layer.
Digital Biosphere Architecture is the system-level hub, Agent Evidence Profile
(AEP) is the concrete evidence entry for portable, independently verifiable
execution evidence, `verifiable-agent-demo` shows the shortest end-to-end path,
and `aro-audit` handles audit-facing review and conformance workflows. This
keeps architecture, implementation, demo, and audit from being conflated.

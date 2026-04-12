# GitHub Outreach Texts

## 1. GitHub issue / discussion 开场版

We use a four-part entry path so readers do not have to infer repository roles
from implementation details. Digital Biosphere Architecture is the architecture
hub, Agent Evidence Profile (AEP) is the concrete execution-evidence entry,
`verifiable-agent-demo` is the walkthrough, and `aro-audit` is the audit
plane. Stable reference links are collected here:
<https://github.com/joy7758/digital-biosphere-architecture/tree/main/docs/reference-pack>.

## 2. GitHub PR 描述版

This change should be read within the current repository boundary. The
architecture hub remains `digital-biosphere-architecture`; AEP remains the
concrete evidence entry in `agent-evidence`; the demo remains
`verifiable-agent-demo`; and audit-facing review remains in `aro-audit`. The
EDC Java line should still be described only as a frozen augmentation-layer
validation artifact, not as an EDC replacement or product line.

## 3. GitHub repo / profile 简短引用版

If you only need the main route, start here:
Architecture -> <https://github.com/joy7758/digital-biosphere-architecture>,
Evidence -> <https://github.com/joy7758/agent-evidence>,
Demo -> <https://github.com/joy7758/verifiable-agent-demo>,
Audit -> <https://github.com/joy7758/aro-audit>.

## 4. “别人问这是什么” 的 3 段式回答版

First, this is not one monolithic repo. Digital Biosphere Architecture is the
canonical architecture hub, and it points outward to the concrete entry points.

Second, Agent Evidence Profile (AEP) in `agent-evidence` is the concrete
execution-evidence entry for portable, independently verifiable execution
evidence. `verifiable-agent-demo` is the shortest walkthrough of that path, and
`aro-audit` is the audit plane for post-execution review and conformance.

Third, the EDC Java spike should be described narrowly. It is a frozen
augmentation-layer validation artifact for a dataspace / control-plane
scenario, not a better tracing tool, not a logging format, and not an EDC
replacement.

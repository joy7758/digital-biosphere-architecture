# FDO Forum Post Draft

I am preparing a discussion-ready architecture surface for AI runtime
governance and would like feedback from the FDO community on whether this is a
useful object-facing direction.

Architecture overview:

- Persona Layer
- Interaction Layer
- Governance Layer
- Execution Integrity Layer
- Audit Evidence Layer

Public routing starts from the architecture hub. From there, `agent-evidence`
is the concrete execution-evidence entry, `verifiable-agent-demo` is the
shortest walkthrough, and `aro-audit` is the post-execution audit control
plane.

For FDO-facing discussion, the current concrete execution-evidence package
centers:

- agent identity
- persona identity
- interaction trace
- policy decisions
- tool calls
- integrity hash
- timestamp
- bounded result summary

Public links:

- Architecture repo: `https://github.com/joy7758/digital-biosphere-architecture`
- Benchmark repo: `https://github.com/joy7758/agent-governance-benchmark`
- Agent Evidence repo: `https://github.com/joy7758/agent-evidence`
- ARO-Audit repo: `https://github.com/joy7758/aro-audit`

The immediate goal is not to claim a finalized standard, but to offer a
portable governance evidence package that can be discussed in terms of PID,
metadata, provenance, and integrity reference.

Questions for feedback:

1. Is this profile shape legible in FDO terms?
2. Which profile elements should be mandatory versus optional?
3. What would be the most credible path for community review of such an object type?

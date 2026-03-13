# FDO Forum Post Draft

I am preparing an Evidence Object profile for AI runtime governance and would
like feedback from the FDO community on whether this is a useful object class
for discussion.

Architecture overview:

- Persona Layer
- Interaction Layer
- Governance Layer
- Execution Integrity Layer
- Audit Evidence Layer

The key artifact for FDO discussion is the Evidence Object defined in
`aro-audit`, which captures:

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
- Evidence Object spec: `https://github.com/joy7758/aro-audit/blob/main/docs/evidence-object-spec.md`
- FDO profile draft: `https://github.com/joy7758/aro-audit/tree/main/fdo-profile`

The immediate goal is not to claim a finalized standard, but to offer a
portable governance evidence object that can be discussed in terms of PID,
metadata, provenance, and integrity reference.

Questions for feedback:

1. Is this profile shape legible in FDO terms?
2. Which profile elements should be mandatory versus optional?
3. What would be the most credible path for community review of such an object type?

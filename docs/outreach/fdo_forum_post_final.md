# Evidence Objects for AI Runtime Governance in FDO-based Systems

I want to share an Evidence Object profile for AI runtime governance and ask
whether this looks like a useful digital object type for FDO-oriented systems.

## Evidence Object concept

The core idea is to treat post-run governance evidence as a portable object
rather than as runtime-local logs.

The object captures:

- `agent_id`
- `persona_id`
- `interaction_trace`
- `policy_decisions`
- `execution_hash`
- `timestamp`
- `tool_calls`
- `result_summary`

This is meant to preserve a bounded record of what happened, what governance
decision was taken, and what integrity reference can be checked later.

## Mapping to FDO identifiers

The current profile draft maps the Evidence Object into four FDO-facing parts:

- `PID`
- `metadata`
- `provenance`
- `integrity_reference`

Profile draft:

- `https://github.com/joy7758/aro-audit/blob/main/fdo-profile/evidence_object_profile.md`

Example object:

- `https://github.com/joy7758/aro-audit/blob/main/fdo-profile/example_evidence_object.json`

Schema:

- `https://github.com/joy7758/aro-audit/blob/main/schema/evidence.schema.json`

Narrative specification:

- `https://github.com/joy7758/aro-audit/blob/main/docs/evidence-object-spec.md`

## Audit artifacts as digital objects

The motivation is straightforward:

- logs are not portable enough
- audit artifacts need durable identity
- provenance and integrity should remain explicit after the runtime ends

In that sense, the Evidence Object is not proposed as a generic observability
record. It is proposed as a reviewable governance artifact with a clear object
boundary.

Related architecture context:

- `https://github.com/joy7758/digital-biosphere-architecture`
- `https://github.com/joy7758/digital-biosphere-architecture/blob/main/docs/governance_architecture_whitepaper.pdf`

Questions for feedback:

1. Is this profile shape legible in FDO terms?
2. Which elements should be mandatory versus optional in an FDO-oriented profile?
3. Would an Evidence Object be a useful object class for governance and audit exchange across systems?

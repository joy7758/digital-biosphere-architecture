# A Governance Architecture for Autonomous AI Agents

## Problem

Autonomous agents increasingly combine persona, tool use, planning, and partial
delegation. Most stacks can demonstrate capability, but far fewer can clearly
show:

- who acted
- what was allowed
- what happened during execution
- what evidence remains after the run

This leaves a practical gap between autonomy and accountability.

## Architecture

Digital Biosphere Architecture organizes this problem into five layers:

1. Persona Layer
2. Interaction Layer
3. Governance Layer
4. Execution Integrity Layer
5. Audit Evidence Layer

Reference implementations:

- POP for persona
- AIP for interaction
- Token Governor for runtime governance
- MVK for execution integrity
- Agent Evidence for concrete execution-evidence packaging
- ARO-Audit for post-execution review and evidence export

## Public routing

Start with `digital-biosphere-architecture` as the canonical architecture hub.
From there:

- use `agent-evidence` for the concrete execution-evidence entry
- use `verifiable-agent-demo` for the shortest walkthrough
- use `aro-audit` for post-execution review

## Concrete execution-evidence package

Agent Evidence provides the current concrete execution-evidence package surface.
ARO-Audit remains the downstream audit control plane for review and conformance.

The current package centers these core fields:

- `agent_id`
- `persona_id`
- `interaction_trace`
- `policy_decisions`
- `execution_hash`
- `timestamp`
- `tool_calls`
- `result_summary`

This package is meant to stay small enough to move across systems while still
supporting audit reconstruction and external review.

## Benchmark results

The current governance benchmark compares a fair baseline agent against a
governed agent across seven deterministic scenarios.

Current results:

- Baseline `policy_violation_rate`: 66.7%
- Governed `policy_violation_rate`: 0.0%
- Baseline `token_overspend_rate`: 50.0%
- Governed `token_overspend_rate`: 0.0%
- Baseline `persona_drift_rate`: 50.0%
- Governed `persona_drift_rate`: 0.0%
- Baseline `false_positive_rate`: 50.0%
- Governed `false_positive_rate`: 0.0%
- Baseline `task_success_rate`: 85.7%
- Governed `task_success_rate`: 100.0%

The governed path does add decision latency, but it also reduces policy
violations and audit reconstruction time substantially.

## Integration examples

Two external integration surfaces are now documented:

- LangChain integration via Token Governor middleware
- CrewAI integration via Agent Evidence packaging and ARO-Audit review

Relevant repositories:

- `digital-biosphere-architecture`
- `agent-evidence`
- `verifiable-agent-demo`
- `token-governor`
- `aro-audit`
- `agent-governance-benchmark`

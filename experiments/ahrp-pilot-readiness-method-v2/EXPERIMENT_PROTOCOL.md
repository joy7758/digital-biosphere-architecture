# EXPERIMENT_PROTOCOL — method-v2

Frozen protocol description. Any deviation between this document and the
code is a defect in the code.

## 1. Roster and capability matrix

Three fixed synthetic worker agents at version `1.0.0`:

```text
worker-alpha@1.0.0   worker-beta@1.0.0   worker-gamma@1.0.0
```

`config/capability-matrix.json` declares per-task-type capability levels,
per-agent input capacity, policy-compliance certification, and the
controlled environment (including one deliberately unavailable service).
Its SHA-256 is written to `config/capability-matrix.commitment` BEFORE the
experiment run; the runner fails closed on any mismatch.

## 2. Tasks

32 tasks in `config/tasks.jsonl`. Each task declares ONLY requirements:
`task_type`, `risk_level`, `requirements` (min capability level, input
size, policy-compliance need, required services), and candidate agents.
LOW-risk cold-start candidates additionally declare four experiment-level
sandbox flags (`cold_start_candidate`, `reversible`, `sandboxed`,
`limited_permissions`); these flags live in the experiment configuration
only and never enter the AHRP Schema. One task (`task-m2-032`) carries a
deliberately invalid `task_type` to inject a controlled query error
(`Q_INVALID_ENUM`) at the HIGH risk level.
The fields `expected_outcome`, `forced_result`, `desired_result` are
forbidden and rejected at load time.

Coverage constraints: >=3 task types (6 used), >=5 HIGH-risk tasks (8),
>=5 failure-boundary probes (8), >=5 cold-start candidate scenarios (7),
>=1 controlled query-error injection (1).

## 3. Arm allocation (fixed before any result exists)

```text
task sequence odd  -> No-AHRP arm        (16 tasks)
task sequence even -> AHRP-assisted arm  (16 tasks)
```

Allocation reads only `sequence`. It never reads results, decisions, or
history.

## 4. Execution model

`worker.execute_task(task, agent, capability_matrix)` is a pure function.
Its result depends ONLY on task requirements, the selected agent, the
capability matrix, and the environment — never on the arm or on any
decision flag. Results are one of SUCCESS / FAILURE / TIMEOUT / CANCELLED
with an enumerated failure category. Both arms execute through the same
worker; only the decision procedure differs.

## 5. History seed

`config/history-events.jsonl` + `config/history-verifications.jsonl` are
explicitly synthetic. Every routing-relevant seed event:

- passes the real AHRP Validator (enforced at ingest, fail-closed);
- references a real evidence file under `evidence/history/` whose SHA-256
  is embedded in the event (no shared placeholder hashes);
- is explicitly referenced by a verification record binding event ID,
  agent ID, agent version, and covered aspect;
- treats SELF verification as non-independent (one seed event is
  SELF-verified only and must never satisfy an independence filter);
- binds failure categories to the task type of the event.

One seed event is declared WITHHELD to exercise three-state null semantics.

## 6. HistoryStore usage (correct envelope discipline)

```python
store = HistoryStore()
store.ingest_event(event)                 # validator-checked, fail-closed
store.ingest_verification(record)
envelope = store.query_events(...)
events = envelope.get("result", {}).get("events", [])
```

Mandatory checks: `ok`, `error`, `null_semantics` (NONE / NO_RECORD /
WITHHELD), `result.events`. Iterating the envelope top level is forbidden.
There is NO branch that forces a decision change when history is empty.

## 7. Decision rules and fail-closed dispatch (AHRP-assisted arm)

Every AHRP-arm decision produces an experiment-layer `DispatchDecision`
(not part of the AHRP Schema):

```python
@dataclass(frozen=True)
class DispatchDecision:
    disposition: str                       # DISPATCH / LOW_RISK_EXPLORATION
                                           # / BLOCK / MANUAL_REVIEW
    selected_agent: Optional[str]          # None unless dispatchable
    reason: str
    supporting_event_references: list[str]
```

Veto rules, applied strictly to disclosed, independently verified summary
projections:

- `RULE_A_CAPABILITY_LIMIT_VETO` — >=2 independently verified failure-class
  events with `failure_category=CAPABILITY_LIMIT` for the same agent,
  version, and task type;
- `RULE_B_POLICY_RESTRICTION_BLOCK` — HIGH-risk task and any independently
  verified failure-class event with `failure_category=POLICY_RESTRICTION`.

Trust-boundary semantics (fail-closed):

- `NO_RECORD` means UNKNOWN / COLD_START; `WITHHELD` means
  RECORD_EXISTS_BUT_NOT_DISCLOSED; a query error means QUERY_ERROR. None of
  the three may ever be read as CLEAN, SAFE, or TRUSTED, and none of them
  permits dispatch of the affected agent.
- An alternative candidate is dispatchable ONLY when its own query returns
  status `OK` with disclosed events AND it carries no veto evidence
  (`KNOWN_NON_VETOED_ALTERNATIVE`). Alternatives answering NO_RECORD,
  WITHHELD, or QUERY_ERROR are unknown and never selectable
  (`NO_KNOWN_ALTERNATIVE`).
- HIGH risk with no known non-vetoed candidate: `disposition=BLOCK`,
  `selected_agent=None`; the worker is never invoked.
- MEDIUM risk with no known non-vetoed candidate:
  `disposition=MANUAL_REVIEW`. This controlled experiment has no real human
  approver, so MANUAL_REVIEW never auto-executes.
- LOW risk with an unknown initial candidate may explore cold start ONLY
  when all four sandbox flags are true (`disposition=LOW_RISK_EXPLORATION`);
  otherwise BLOCK.

BLOCK and MANUAL_REVIEW tasks are recorded in `data/allocations.jsonl`,
`data/post-query-decisions.jsonl`, and `data/non-dispatched-tasks.jsonl`.
They never produce execution evidence, Experience Events, or Verification
Records, and are never disguised as FAILURE or CANCELLED.

## 8. Two-phase shadow protocol

Before any query, the pre-query decision is appended to
`data/pre-query-decisions.jsonl`, flushed, `os.fsync()`-ed, and hashed.
Fields: `task_id`, `candidate_agents`, `selected_agent_before_query`,
`selection_reason_before_query`, `recorded_at`, `monotonic_sequence`,
`record_hash`.

Post-query records bind `pre_query_record_hash`, list the query IDs in the
window, record `selected_agent_after_query`, the final `disposition`,
`decision_changed`, and `supporting_event_references`. Every query itself
is logged with latency,
character count, token estimate, mode, `ok` / `null_semantics` / error
code, and is bound to the pre-query hash.

`validate_shadow_protocol.py` verifies existence, hash recomputation,
binding, temporal order (pre <= query window <= post), monotonic sequence,
supporting-reference existence, and proves via tamper self-tests that any
single-record mutation or deletion is detected.

## 9. Evidence

Every controlled execution writes a real file
`evidence/executions/<task-id>.json` (task, selected agent, requirements,
capability match, environment, result, timestamps). The resulting
Experience Event references that file's recomputed SHA-256.
`verify_evidence_references.py` re-reads every referenced file, recomputes
its hash, blocks path traversal, and rejects placeholder/duplicate hashes.

## 10. Verification independence

The runner (`run_experiment.py`) writes ONLY
`data/experience-events-unverified.jsonl`; every runner-emitted event
carries `verification_references=[]` and no VERIFIED status of any kind.
The runner contains no verifier class, no verification writer, and never
claims `INDEPENDENT_AGENT` verification.

`verify_run_records.py` runs separately AFTER the runner and:

1. re-reads the frozen tasks, the frozen capability matrix (against its
   pre-run SHA-256 commitment), and every controlled execution evidence
   file;
2. recomputes the deterministic worker result and compares
   `selected_agent`, `result_status`, `failure_category`, the capability
   matrix hash, and every evidence file SHA-256;
3. validates every final Experience Event and Verification Record through
   the real AHRP Validator and checks complete event/verification binding
   (`subject_event_id`, `agent_ref`, `agent_version`, `covered_aspect`);
4. only on PASS writes `data/experience-events.jsonl` and
   `data/verification-records.jsonl`, plus
   `analysis/generated-object-validation.json`; any failure exits non-zero.

Verification records use `verifier_class=SYSTEM_BENCHMARK` and
`verifier_name=method-v2-post-run-verifier`. This is a deterministic
post-run recomputation, NOT independent verification:
`REAL_INDEPENDENT_VERIFICATION=false`,
`SYNTHETIC_SYSTEM_VERIFICATION=true`,
`POST_RUN_RECOMPUTATION_VERIFIED=true`.

## 11. Metrics

`analyze_experiment.py` recomputes everything from raw JSONL (never from a
prior summary). It reports the task flow honestly:
`submitted_tasks`, `dispatched_tasks`, `low_risk_exploration_tasks`,
`blocked_tasks`, `manual_review_tasks`, `executed_tasks`,
`experience_event_count`, `verification_record_count`, and
`non_dispatched_record_count`. Per arm: task counts, result distribution,
decision time,
human overrides (honestly zero in a controlled run), and repeat selection
of agents with known failure boundaries. AHRP arm additionally: query
counts by mode, NO_RECORD / WITHHELD / disclosure-denial / error counts,
decision changes, supporting references, character and token estimates,
p50/p95 latency.

The repeat-selection metric is reported strictly as a
`ROUTING_POLICY_CONFORMANCE_OBSERVATION`:

> This metric is mechanically related to the configured veto policy.
> It is not independent evidence of improved real-world outcomes.

It is never reported as `AHRP_VALUE_IMPROVEMENT`, `RELIABILITY_IMPROVEMENT`,
or `FAILURE_PREVENTED`.

## 12. Claim ceiling

The protocol permits only:

```text
AHRP_HISTORY_WAS_USED
AHRP_ASSOCIATED_WITH_DIFFERENT_DECISION
```

and forbids `AHRP_PROVED_TO_IMPROVE_SUCCESS_RATE` and `FAILURE_PREVENTED`.
Final result vocabulary: INCONCLUSIVE / READY_WITH_CONDITIONS / NOT_READY;
with 32 synthetic tasks the default is INCONCLUSIVE.

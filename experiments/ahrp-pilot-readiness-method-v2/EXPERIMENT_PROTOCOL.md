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

30 tasks in `config/tasks.jsonl`. Each task declares ONLY requirements:
`task_type`, `risk_level`, `requirements` (min capability level, input
size, policy-compliance need, required services), and candidate agents.
The fields `expected_outcome`, `forced_result`, `desired_result` are
forbidden and rejected at load time.

Coverage constraints: >=3 task types (6 used), >=5 HIGH-risk tasks (7),
>=5 failure-boundary probes (8), >=5 cold-start candidate scenarios (7).

## 3. Arm allocation (fixed before any result exists)

```text
task sequence odd  -> No-AHRP arm        (15 tasks)
task sequence even -> AHRP-assisted arm  (15 tasks)
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

## 7. Decision rules (AHRP-assisted arm only)

Applied strictly to disclosed, independently verified summary projections:

- `RULE_A_CAPABILITY_LIMIT_VETO` — >=2 independently verified failure-class
  events with `failure_category=CAPABILITY_LIMIT` for the same agent,
  version, and task type;
- `RULE_B_POLICY_RESTRICTION_BLOCK` — HIGH-risk task and any independently
  verified failure-class event with `failure_category=POLICY_RESTRICTION`.

On veto, the first alternative candidate (declared order) without veto
evidence is selected; alternatives whose answer is WITHHELD or a query
error are unknown and therefore NOT selectable (fail-closed). If no clean
alternative exists, the initial selection is kept.
NO_RECORD and WITHHELD answers for the initial agent keep the initial
selection (conservative). Query errors keep the initial selection and are
logged.

## 8. Two-phase shadow protocol

Before any query, the pre-query decision is appended to
`data/pre-query-decisions.jsonl`, flushed, `os.fsync()`-ed, and hashed.
Fields: `task_id`, `candidate_agents`, `selected_agent_before_query`,
`selection_reason_before_query`, `recorded_at`, `monotonic_sequence`,
`record_hash`.

Post-query records bind `pre_query_record_hash`, list the query IDs in the
window, record `selected_agent_after_query`, `decision_changed`, and
`supporting_event_references`. Every query itself is logged with latency,
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

## 10. Metrics

`analyze_experiment.py` recomputes everything from raw JSONL (never from a
prior summary). Per arm: task counts, result distribution, decision time,
human overrides (honestly zero in a controlled run), and repeat selection
of agents with known failure boundaries. AHRP arm additionally: query
counts by mode, NO_RECORD / WITHHELD / disclosure-denial / error counts,
decision changes, supporting references, character and token estimates,
p50/p95 latency.

## 11. Claim ceiling

The protocol permits only:

```text
AHRP_HISTORY_WAS_USED
AHRP_ASSOCIATED_WITH_DIFFERENT_DECISION
```

and forbids `AHRP_PROVED_TO_IMPROVE_SUCCESS_RATE` and `FAILURE_PREVENTED`.
Final result vocabulary: INCONCLUSIVE / READY_WITH_CONDITIONS / NOT_READY;
with 30 synthetic tasks the default is INCONCLUSIVE.

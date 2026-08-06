# Limitations — method-v2

These limitations are binding. None of them can be removed by re-running the
analysis; they are properties of the experiment design itself.

## 1. Synthetic-only population

- The roster consists of exactly three synthetic agents
  (`worker-alpha/beta/gamma@1.0.0`) with a hand-written capability matrix.
- `REAL_EXTERNAL_AGENT=false`. No real agent, real framework, or real
  operator participated.
- Any observed difference between arms reflects the controlled simulation,
  not agent behavior in the wild.

## 2. Sample size

- 30 tasks total (15 per arm). Arm allocation is a fixed parity rule over
  `sequence`, not randomization.
- With n=15 per arm, no statistical inference is possible. The identical
  result distributions (8/4/2/1 in both arms) are exactly the expected
  consequence of a deterministic worker and carry no signal about AHRP's
  effect on outcomes.

## 3. Deterministic execution model

- `worker.execute_task` is a pure function of task requirements, selected
  agent, capability matrix, and environment. By construction, changing the
  decision procedure can only change WHICH agent runs, never the mapping
  from (task, agent) to result.
- Therefore this experiment can measure decision differences and protocol
  mechanics, but it CANNOT measure whether different decisions lead to
  better real-world outcomes. `FAILURE_PREVENTED` is not observable here.

## 4. Synthetic history seed

- The seven seed events and six verification records are authored for this
  experiment. They exercise validator, disclosure, and null-semantics
  mechanics; they are not a corpus of accumulated operational experience.
- Cold-start dominance (11 of 34 queries returned NO_RECORD) is a property
  of the sparse seed, not a prediction about production traffic.

## 5. Overhead numbers are local and uncalibrated

- Latencies (p50 ~0.008 ms, p95 ~0.025 ms) are in-process function calls on
  a single machine; no network, no persistence layer, no concurrency.
- Token estimates use the documented `ceil(chars/4)` heuristic against a
  synthetic projection format; they do not reflect any specific model or
  provider.

## 6. No adversarial or multi-party conditions

- No conflicting verifiers, no disputed records, no retention/redaction
  pressure beyond one deliberately WITHHELD seed event.

## Consequence

Within these boundaries the experiment supports only:

```text
AHRP_HISTORY_WAS_USED
AHRP_ASSOCIATED_WITH_DIFFERENT_DECISION
```

and nothing beyond. `EXPERIMENT_RESULT=INCONCLUSIVE` is the correct final
state for this design; `READY_WITH_CONDITIONS` or `NOT_READY` require
evidence this experiment cannot produce.

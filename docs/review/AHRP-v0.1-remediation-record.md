# AHRP v0.1 — Remediation Record (Independent-Audit Round 2)

- Date recorded: `2026-08-05`
- Branch: `fix/ahrp-v0.1-independent-audit-r2`
- Scope: reference-implementation remediation of five audit defects. This record
  documents root causes, modified files, added tests, whether protocol
  semantics changed, and pre/post-fix reproduction evidence.
- Truth boundary: `SYNTHETIC_ONLY=true`. This is a reference-implementation
  remediation, **not** a conformance certification, **not** production ready.
  `REFERENCE_IMPLEMENTATION_NE_STANDARD=true`.

## 1. Defects, Root Causes, and Fixes

### Defect 1 — Selective Disclosure had no real enforcement

- Symptom: `WITHHELD` was only a flag; `RESTRICTED` events returned full
  content with a bare `capability="detail"`; expired `PUBLIC` events still
  returned details; `expires_at` and revocation were not enforced.
- Root cause: `HistoryStore.get_event()` gated detail only on
  `capability == "detail"` and a `WITHHELD` check. It treated the plain string
  `"detail"` as sufficient authorization and never evaluated scope tier,
  expiry, revocation, or any external policy decision.
- Fix: introduced a disclosure truth table
  (`_evaluate_detail_disclosure`) keyed on the four real disclosure scopes
  `{PUBLIC, FEDERATED, RESTRICTED, WITHHELD}`. `PUBLIC`/`FEDERATED` are the
  open federation-readable tiers; `RESTRICTED` additionally requires a valid,
  scope-matching machine-readable **Disclosure Context** carrying an external
  policy decision; `WITHHELD` never returns content. Record-level `revoked`
  and `expires_at`, and permission-level `revocation_status`/`expiry`/
  `policy_version`, are all enforced fail-closed. Unauthorized reads return
  stable `Q_*` codes and never silently return details. AHRP validates only
  the format/status/scope of the decision; it does **not** become a second
  AuthZEN/ODRL/identity system.

### Defect 2 — Verification ↔ Event weak association

- Symptom: events were upgraded to `VERIFIED` from verification records in
  storage even when `verification_references` was empty or did not match.
- Root cause: `event_verification_status()` scanned **all** stored
  verifications and matched by `scope.subject_event_id == event_id` (weak
  association), ignoring whether the event explicitly referenced the record.
- Fix: effective verification now derives **only** from verification objects
  explicitly listed in `verification_references`
  (`_resolve_event_verification`). Each reference is checked for: reference-id
  resolution, object existence, target-event match, agent reference/version
  match, verification schema-version support, status legality, and verifier-name
  match. Empty references → `NOT_ASSESSED`; unresolved/malformed/mismatched →
  `INVALID` (fail-closed); conflicting → `CONFLICTED`. Unreferenced records no
  longer affect event status, summary counts, query filters, or trust. Weak
  association paths (event_id / agent / time scanning, name inference) are
  prohibited.

### Defect 3 — Self-verification indistinguishable from independent

- Symptom: self-only verification displayed as `VERIFIED` and was counted in
  `verified_events`.
- Root cause: the summary counted every event with effective status `VERIFIED`
  regardless of verifier independence; no self/independent split existed.
- Fix: kept `verifier_class` and expanded the independence classification
  (`SELF` is the only non-independent class). Summary `verified_events` now
  counts **independently** verified events only; added machine-readable split
  fields `independently_verified_events` / `self_verified_events` /
  `partially_verified_events` / `not_assessed_events` / `conflicted_events`.
  Event detail/projection reports verifier classes, independence class,
  whether third-party verification exists, and whether it is self-only. Pure
  SELF never satisfies an independent-verification filter, and is retained as
  an explicitly downgraded weak signal (never deleted, never treated as
  no-record).

### Defect 4 — Query request validation & unstable error semantics

- Symptom: invalid enum `BOGUS` was treated as `NO_RECORD`; invalid time threw
  a raw Python `ValueError`; callers could not distinguish "invalid request"
  from "no records".
- Root cause: `query_events()`/`get_event()` did no parameter validation and
  called `_parse_instant()` unguarded on user-supplied time strings.
- Fix: all query parameters (agent reference/version, task/action type,
  verification status, verifier class, time format/range, disclosure scope,
  capability, protocol version, limit) are validated **before** the engine
  runs (`_validate_query_params`). Invalid parameters never reach the engine,
  are never mapped to `NO_RECORD`, and never surface raw exceptions. A unified
  `{ "ok": false, "error": { code, field, message, retryable } }` envelope
  carries stable codes: `Q_INVALID_ENUM`, `Q_INVALID_TIME_FORMAT`,
  `Q_INVALID_TIME_RANGE`, `Q_INVALID_REFERENCE`, `Q_UNSUPPORTED_VERSION`,
  `Q_DISCLOSURE_DENIED`, `Q_DISCLOSURE_EXPIRED`, `Q_DISCLOSURE_REVOKED`,
  `Q_POLICY_DECISION_REQUIRED`, `Q_NO_RECORD`. `Q_NO_RECORD` is returned only
  when the request is fully valid but genuinely matches nothing.

### Defect 5 — SPEC/STATUS documentation drift & regression-coverage gap

- Symptom: the SPEC stated fail-closed selective-disclosure and verification
  discipline in prose, but did not specify the enforcement truth table, the
  strong-binding rule, the self/independent split, or the query error codes;
  the suite had no regression tests for any of these behaviors.
- Root cause: documentation/coverage lag behind normative intent.
- Fix: minimal SPEC clarifications (§6.2, §6.4, §7, §9, §11) documenting the
  already-intended semantics, plus the new `tests/test_remediation.py`
  regression suite (43 tests). STATUS truth boundaries preserved.

## 2. Modified Files

- `AHRP/schema/verification.schema.json` — expanded `verifier_class` enum with
  independent classes; added optional `scope.agent_ref` / `scope.agent_version`
  for strong agent/version binding.
- `AHRP/schema/experience-event.schema.json` — added optional
  `disclosure.revoked` boolean.
- `AHRP/query/engine.py` — disclosure truth table + Disclosure Context
  validation; strong verification binding; self/independent split + summary
  split fields; query parameter validation + stable `Q_*` error envelopes.
- `AHRP/tests/test_query.py`, `AHRP/tests/test_failure_cases.py` — fixture
  updates only: added explicit `verification_references` where a verification
  is meant to bind an event (required by Defect 2 strong binding). **No test
  was deleted, skipped, or weakened; every original assertion is preserved.**
- `AHRP/spec/AHRP_SPEC_v0.1.md` — minimal clarifications + changelog entry.
- `AHRP/STATUS.md` — updated test evidence and date; truth boundaries kept.

## 3. New Files

- `AHRP/tests/test_remediation.py` — 43 regression tests covering selective
  disclosure, verification strong binding, self/independent separation, query
  validation errors, and security regression.
- `docs/review/AHRP-v0.1-remediation-record.md` — this record.

## 4. New Tests Added

43 tests across five classes:

- `TestSelectiveDisclosure` (13): PUBLIC/FEDERATED valid → allow; PUBLIC
  expired/revoked → deny; RESTRICTED no-permission / wrong-scope /
  unsupported-version / revoked-permission / expired-permission → deny;
  RESTRICTED valid permission → allow; WITHHELD with normal permission → deny;
  capability string `"detail"` is not authorization; default query stays
  summary-only.
- `TestVerificationStrongBinding` (9): empty refs + stored verification →
  `NOT_ASSESSED`; unreferenced record has no effect; missing / malformed /
  target-mismatch / agent-version-mismatch / verifier-name-mismatch references
  → `INVALID`; multiple conflicts → `CONFLICTED`; exact complete binding works.
- `TestSelfVsIndependent` (5): pure SELF not counted as independent; SELF
  retained as weak signal; independent counted normally; SELF + independent
  counted separately; independent filter not satisfied by SELF.
- `TestQueryValidationErrors` (9): invalid enum / task type; invalid time
  (no exception); start-after-end; unsupported version; empty reference;
  invalid capability; valid-but-empty → `Q_NO_RECORD` only; invalid never
  becomes `NO_RECORD`.
- `TestSecurityRegression` (7): prompt injection rejected; forbidden fields
  blocked; cross-version merging blocked; disclosure not bypassable via missing
  field or case variants; record expiry dominates a permission; consumer path
  still strips restricted text.

## 5. Did Protocol Semantics Change?

**No constitutional/ADR semantics changed.** All fixes implement the existing
normative intent (fail-closed, Selective Disclosure First, Verification ≠
Authorization, self-verification as a distinct weaker signal, DATA ≠
INSTRUCTION). The SPEC received only minimal clarifications (§6.2, §6.4, §7,
§9, §11). No ADR-001, Constitution, or TITMAS/DBOS/SAEE/POP/ARO/EEOAP document
was modified. No rankings, scores, recommendation, marketplace, payment, social
graph, auto-learning, auto-growth, fitness, mutation, or digital-life protocol
was added.

One interface note: query success envelopes now include `"ok": true` and error
envelopes `"ok": false` (additive; pre-existing consumers of `result` /
`null_semantics` / `selective_disclosure` are unaffected).

## 6. Pre-fix Reproduction Results (original code)

Reproduced against the pre-fix reference implementation:

| Defect | Reproduction | Pre-fix result |
|---|---|---|
| D1 | `get_event(RESTRICTED, capability="detail")` | returned `structured_facts` (leak) |
| D1 | `get_event(PUBLIC with past expires_at, "detail")` | returned `structured_facts` (leak) |
| D2 | event `verification_references=[]` + stored verification scoped to it | effective status `VERIFIED` (weak upgrade) |
| D3 | pure SELF verification | counted in `verified_events` (=1); no split fields |
| D4 | `query_events(verification_status="BOGUS")` | `null_semantics = NO_RECORD` (coerced) |
| D4 | `query_events(time_start="not-a-date")` | raised raw Python `ValueError` |

## 7. Post-fix Results (remediated code)

| Defect | Reproduction | Post-fix result |
|---|---|---|
| D1 | RESTRICTED detail, no permission | `Q_POLICY_DECISION_REQUIRED` (denied) |
| D1 | RESTRICTED detail, valid permission | `ok=true` (allowed) |
| D1 | PUBLIC expired detail | `Q_DISCLOSURE_EXPIRED` (denied) |
| D2 | empty refs + stored verification | effective status `NOT_ASSESSED` |
| D3 | pure SELF verification | `verified_events=0`, `self_verified_events=1`, split fields present |
| D4 | `verification_status="BOGUS"` | `Q_INVALID_ENUM` |
| D4 | `time_start="not-a-date"` | `Q_INVALID_TIME_FORMAT` (no exception) |

Test suite: **131 tests, all passing** (88 pre-existing preserved + 43 new).

```text
Ran 131 tests
OK
```

## 8. Independent Verifier

To be filled after independent re-verification:

- Verifier reference: `NOT_ASSIGNED`
- Verification date: `NOT_ASSESSED`
- Verification result: `NOT_ASSESSED`
- `AHRP_INDEPENDENT_ADVERSARIAL_REVIEW`: not set to `PASS` here (pending
  independent re-verification per STATUS discipline).

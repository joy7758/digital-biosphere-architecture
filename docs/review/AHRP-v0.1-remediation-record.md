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

Test suite at round-1 remediation closure: **131 tests, all passing**
(88 pre-existing preserved + 43 new). Superseded by later rounds: audit r2
raised the suite to 168 tests and trust-boundary hardening r3 to 208 tests
(see Section 10); every round remained fully additive.

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

## 9. Independent Review Findings (Audit Round 2) and Fixes

Four independent reviewers (Eric / Alex / Sam / fourth reviewer) identified
3 Critical + 7 Major + minor issues against the round-2 remediation. All were
fixed in this branch; this section records them.

### Critical fixes

| ID | Finding | Fix |
|---|---|---|
| CF-1 | Every `value in FROZENSET` check raised a bare `TypeError` for unhashable inputs (list/dict/set/number) | Added `_is_enum_member()` type guard; applied to every enum membership check in `_validate_query_params`, `_validate_disclosure_context`, `_evaluate_detail_disclosure` (scope + policy_version) and the `get_event` capability check. Non-string values now yield stable `Q_INVALID_ENUM` / `Q_POLICY_DECISION_REQUIRED` / `Q_UNSUPPORTED_VERSION` codes. |
| CF-2 | `summary()` had zero parameter validation; empty/invalid refs mapped to NO_RECORD | `summary()` now validates `identity_ref` (non-empty string) and `agent_version` (non-empty string when present) BEFORE any lookup → `Q_INVALID_REFERENCE`. |
| CF-3 | `get_event()` / `get_failure_category()` did not validate `event_id`; invalid `capability` was masked by the existence check | Both methods validate `event_id` (non-empty string) BEFORE any lookup → `Q_INVALID_REFERENCE`; `get_event` validates `capability` BEFORE the existence check → `Q_INVALID_ENUM`. |

### Major fixes

| ID | Finding | Fix |
|---|---|---|
| MF-1 | `saw_independent` was set for ANY resolved reference, including bounded-scope ones (e.g. EVIDENCE_BINDING), allowing a SELF event-level VERIFIED to be laundered into `independently_verified_events` | Self/independent classification in `_resolve_event_verification` now happens ONLY inside the `event_level` block, i.e. only for records that actually confer event-level status. |
| MF-2 | A referenced verification with `verification_status="NOT_ASSESSED"` entered `conferring_statuses` but is absent from `_STATUS_PRIORITY`, raising a bare `StopIteration` | NOT_ASSESSED ("asserts nothing") is filtered out before conferring; if nothing conferring remains the result is `NOT_ASSESSED`. |
| MF-3 | `verifications_for_event()` / `event_verification_status()` leaked WITHHELD event content | Both now check `_event_is_withheld()`: `[]` and `"WITHHELD"` respectively. |
| MF-4 | `get_event(..., now=...)` let callers inject a clock and bypass expiry | `now` parameter removed; expiry uses module-level `_clock` (defaults to `_now_instant()`), monkey-patchable in tests only. |
| MF-5 | `query_events` validated but never applied `disclosure_scope` | `_select` now filters on `event.disclosure.disclosure_scope`; WITHHELD events never enter content filtering. |
| MF-6 | SPEC said `Q_NO_RECORD` should be emitted, implementation used `ok=true, null_semantics="NO_RECORD"` (constant was dead code) | Kept the three-state design (the query succeeded, just no results); SPEC §7.3/§11.5 updated to state that `Q_NO_RECORD` is expressed via the three-state `null_semantics` field and the error code is reserved. |
| MF-7 | Invalid `limit` returned the semantically wrong `Q_INVALID_REFERENCE` | New `Q_INVALID_PARAM` code added to `QUERY_ERROR_CODES` and used for limit validation; SPEC §11.5 updated. |

### Additional fixes

| ID | Finding | Fix |
|---|---|---|
| AF-1 | Malformed `expires_at` skipped the expiry check | Present but malformed `expires_at` now fails closed → `Q_DISCLOSURE_EXPIRED`. |
| AF-2 | `_resolve_event_verification` docstring claimed expiry/revocation checks that verification records do not have | Docstring corrected. |
| AF-3 | Remediation record needed the independent-review round recorded | This section. |

### Round-2 files and tests

- `AHRP/query/engine.py` — all CF/MF/AF fixes above.
- `AHRP/tests/test_audit_r2.py` — new additive regression suite
  (unhashable inputs across every enum field; summary/get_event/
  get_failure_category validation gates; independence-laundering;
  NOT_ASSESSED conferring; WITHHELD auxiliary guards; clock-injection
  rejection; disclosure_scope filtering; limit error code; malformed
  expiry fail-closed).
- `AHRP/spec/AHRP_SPEC_v0.1.md` — §7.3 / §11.5 clarifications (MF-6, MF-7).

No pre-existing test was deleted, skipped, or weakened. No rankings, scores,
recommendations, marketplace, payment, social graph, auto-learning, fitness,
or mutation concepts were added. STATUS.md truth gates unchanged.

## 10. Trust Boundary Hardening (Audit Round r3)

- Branch: `fix/ahrp-v0.1-audit-r3` (from `fix/ahrp-v0.1-independent-audit-r2`
  @ `1fb9bf7`).
- Date: `2026-08-05`.

Round r3 hardened four trust-boundary weaknesses found after the r2 fixes:

| ID | Finding | Fix |
|---|---|---|
| R3-1 | `_validate_disclosure_context` only checked format/enum/version; any caller could fabricate a disclosure_context and bypass RESTRICTED | `HistoryStore` now accepts an optional `policy_decision_resolver` hook. For RESTRICTED detail, after format validation the context's `external_policy_decision_reference` must be confirmed by the resolver. **No resolver configured -> every RESTRICTED detail access fails closed with `Q_POLICY_DECISION_REQUIRED`** (format-only validation is never sufficient). The context additionally requires `issuer` and `decision_id`. A `SyntheticPolicyResolver` (configurable whitelist) is provided for testing/simulation. |
| R3-2 | `get_failure_category`, `verifications_for_event`, `event_verification_status` bypassed RESTRICTED disclosure checks | New shared guard `_require_detail_disclosure(event, disclosure_context)` routes ALL data-access paths through the same disclosure truth table. The three methods accept `disclosure_context=None`; for RESTRICTED events without a confirmed context they return `[]` / `"RESTRICTED"` / a denial envelope respectively. WITHHELD keeps its three-state response; PUBLIC/FEDERATED are unchanged. |
| R3-3 | `scope.agent_ref` / `scope.agent_version` were optional; a verification could bind to an event without declaring which agent/version it verifies | Event-level resolution now requires BOTH fields (`BINDING_INCOMPLETE` -> INVALID, fail-closed) and both must match the subject event. The validator enforces conditional-required at protocol level for `subject_type=EXPERIENCE_EVENT` (schema descriptions updated; the JSON-Schema subset has no conditional-required). Examples, demo and fixtures declare the complete binding. |
| R3-4 | A NOT_ASSESSED independent record still set `saw_independent=True`, laundering SELF-verified events into appearing independently verified | Independence classification moved inside the combined `event_level AND status != NOT_ASSESSED` condition: only records that actually assert something can set `saw_self` / `saw_independent`. |

Fix 5 (truth gate unification): STATUS.md test evidence updated to the actual
suite result; `AHRP_INDEPENDENT_ADVERSARIAL_REVIEW=PENDING_R3` (deliberately
NOT `PASS` -- the independent re-verification has not yet happened);
README.md test count aligned; a new consistency test
(`test_audit_r3.py::TestR35TruthConsistency`) parses STATUS.md / README.md,
verifies the truth gates do not contradict each other, verifies the schema
files are valid draft-07 JSON, and asserts the documented test counts equal
the actual discovery count (> 168).

### r3 files and tests

- `AHRP/query/engine.py` -- R3-1/R3-2/R3-3/R3-4 (resolver hook +
  `SyntheticPolicyResolver`, `_require_detail_disclosure`, mandatory agent
  binding, NOT_ASSESSED independence filter).
- `AHRP/validator/core.py` -- R3-3 protocol-level conditional-required.
- `AHRP/schema/verification.schema.json` -- scope.agent_ref / agent_version
  descriptions (required when EXPERIENCE_EVENT).
- `AHRP/examples/01-verification-verified.json`,
  `AHRP/examples/04-verification-conflicted.json`, `AHRP/demo/run_demo.py`,
  `AHRP/tests/_helpers.py` -- fixtures declare the complete agent/version
  binding.
- `AHRP/tests/test_remediation.py`, `AHRP/tests/test_audit_r2.py`,
  `AHRP/tests/test_query.py` -- fixture updates only (resolver injection,
  complete binding); no assertion deleted or weakened.
- `AHRP/tests/test_audit_r3.py` -- 40 new additive tests (disclosure
  anti-forgery incl. fake/expired/revoked/missing-issuer/missing-decision-id/
  scope-mismatch/no-resolver/valid paths; unified guard across all three
  auxiliary methods; agent/version binding incl. validator enforcement;
  NOT_ASSESSED independence; query stable-error regression; truth-gate
  consistency).
- `AHRP/STATUS.md`, `AHRP/README.md` -- truth-gate unification (test counts,
  `AHRP_INDEPENDENT_ADVERSARIAL_REVIEW=PENDING_R3`, last-update date).

Test suite after r3: **208 tests, all passing** (168 pre-r3 preserved +
40 new).

```text
Ran 208 tests
OK
```

No Constitution, ADR-001, or v0.2 semantics were introduced. No rankings,
scores, marketplace, payment, social graph, or auto-learning concepts were
added. `SYNTHETIC_ONLY=true` remains in force.

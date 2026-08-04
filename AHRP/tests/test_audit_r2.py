"""Independent-review regression tests (audit round 2 fixes).

Covers every Critical / Major / Additional fix from the four independent
reviewers:

* CF-1 -- type guards for unhashable query inputs (no bare TypeError).
* CF-2 -- summary() validation gate (before any lookup).
* CF-3 -- get_event() / get_failure_category() validation gates.
* MF-1 -- independence counting limited to event-level conferring records.
* MF-2 -- NOT_ASSESSED filtered from conferring statuses (no StopIteration).
* MF-3 -- WITHHELD guard on verifications_for_event / event_verification_status.
* MF-4 -- no caller-injectable clock on public methods.
* MF-5 -- disclosure_scope is a real query filter.
* MF-7 -- Q_INVALID_PARAM for limit validation failures.
* AF-1 -- malformed expires_at fails closed (treated as expired).

These tests are additive; they do not delete, skip or weaken any pre-existing
test. All data is SYNTHETIC_ONLY.
"""

from __future__ import annotations

import inspect
import unittest

from tests._helpers import make_event, make_verification

from query import HistoryStore, NullSemantics
from query import engine as engine_module
from query.engine import (
    Q_DISCLOSURE_EXPIRED,
    Q_INVALID_ENUM,
    Q_INVALID_PARAM,
    Q_INVALID_REFERENCE,
    Q_POLICY_DECISION_REQUIRED,
    Q_UNSUPPORTED_VERSION,
    SyntheticPolicyResolver,
)

AGENT = "did:example:test-agent"
LONG_PAST = "2000-01-01T00:00:00Z"

UNHASHABLE_VALUES = (["VERIFIED"], {"k": 1}, {"a"}, 42)


def event_scope(event_id, aspect="FULL_EVENT", subject_type="EXPERIENCE_EVENT",
                agent_ref=AGENT, agent_version="1.0.0"):
    # R3-3: default fixture declares the complete agent/version binding.
    scope = {
        "subject_event_id": event_id,
        "subject_type": subject_type,
        "covered_aspect": aspect,
    }
    if agent_ref is not None:
        scope["agent_ref"] = agent_ref
    if agent_version is not None:
        scope["agent_version"] = agent_version
    return scope


def ref(verification_id, verifier_name="named-verifier-1"):
    return {"verification_id": verification_id, "verifier_name": verifier_name}


def make_disclosure_context(**overrides):
    ctx = {
        "requester_reference": "did:example:requester",
        "requested_disclosure_scope": "RESTRICTED",
        "granted_scope": "RESTRICTED",
        "external_policy_decision_reference": "policy-decision-0001",
        "policy_version": "0.1",
        "evaluated_at": "2026-08-01T00:00:00Z",
        "expiry": "2099-01-01T00:00:00Z",
        "revocation_status": "ACTIVE",
        "issuer": "did:example:policy-authority",
        "decision_id": "decision-0001",
    }
    ctx.update(overrides)
    return ctx


class TestCF1UnhashableInputs(unittest.TestCase):
    """CF-1: unhashable / non-string inputs get stable Q_* codes, never a
    bare TypeError from frozenset membership checks."""

    def setUp(self):
        # R3-1: the RESTRICTED disclosure-context cases below need a
        # configured resolver (fail-closed otherwise); the default synthetic
        # context cites "policy-decision-0001".
        self.store = HistoryStore(
            policy_decision_resolver=SyntheticPolicyResolver(
                {"policy-decision-0001"}))
        self.store.ingest_event(make_event(event_id="evt-u1"))

    def test_unhashable_query_enum_filters_are_invalid_enum(self):
        for field in ("task_type", "action_type", "verification_status",
                      "verifier_class", "disclosure_scope"):
            for bad in UNHASHABLE_VALUES:
                env = self.store.query_events(identity_ref=AGENT,
                                              **{field: bad})
                self.assertFalse(env["ok"], f"{field}={bad!r}")
                self.assertEqual(env["error"]["code"], Q_INVALID_ENUM,
                                 f"{field}={bad!r}")
                self.assertEqual(env["error"]["field"], field)

    def test_unhashable_protocol_version_is_unsupported_version(self):
        for bad in UNHASHABLE_VALUES:
            env = self.store.query_events(identity_ref=AGENT,
                                          protocol_version=bad)
            self.assertFalse(env["ok"], repr(bad))
            self.assertEqual(env["error"]["code"], Q_UNSUPPORTED_VERSION)

    def test_unhashable_capability_is_invalid_enum(self):
        for bad in UNHASHABLE_VALUES:
            env = self.store.get_event("evt-u1", capability=bad)
            self.assertFalse(env["ok"], repr(bad))
            self.assertEqual(env["error"]["code"], Q_INVALID_ENUM)
            self.assertEqual(env["error"]["field"], "capability")

    def test_unhashable_disclosure_context_scopes_never_raise(self):
        self.store.ingest_event(make_event(
            event_id="evt-rest",
            disclosure={"disclosure_scope": "RESTRICTED", "declared_by": "h"}))
        for field in ("requested_disclosure_scope", "granted_scope",
                      "revocation_status"):
            env = self.store.get_event(
                "evt-rest", capability="detail",
                disclosure_context=make_disclosure_context(**{field: ["X"]}))
            self.assertFalse(env["ok"], field)
            self.assertEqual(env["error"]["code"], Q_POLICY_DECISION_REQUIRED)

    def test_unhashable_policy_version_is_unsupported_version(self):
        self.store.ingest_event(make_event(
            event_id="evt-rest2",
            disclosure={"disclosure_scope": "RESTRICTED", "declared_by": "h"}))
        env = self.store.get_event(
            "evt-rest2", capability="detail",
            disclosure_context=make_disclosure_context(policy_version=["0.1"]))
        self.assertFalse(env["ok"])
        self.assertEqual(env["error"]["code"], Q_UNSUPPORTED_VERSION)

    def test_unhashable_summary_identity_ref_is_invalid_reference(self):
        for bad in UNHASHABLE_VALUES:
            env = self.store.summary(bad)
            self.assertFalse(env["ok"], repr(bad))
            self.assertEqual(env["error"]["code"], Q_INVALID_REFERENCE)


class TestCF2SummaryValidationGate(unittest.TestCase):
    """CF-2: summary() validates references BEFORE any lookup."""

    def setUp(self):
        self.store = HistoryStore()
        self.store.ingest_event(make_event(event_id="evt-s1"))

    def test_empty_identity_ref_is_invalid_reference(self):
        env = self.store.summary("")
        self.assertFalse(env["ok"])
        self.assertEqual(env["error"]["code"], Q_INVALID_REFERENCE)
        self.assertEqual(env["error"]["field"], "identity_ref")

    def test_empty_agent_version_is_invalid_reference(self):
        env = self.store.summary(AGENT, agent_version="")
        self.assertFalse(env["ok"])
        self.assertEqual(env["error"]["code"], Q_INVALID_REFERENCE)
        self.assertEqual(env["error"]["field"], "agent_version")

    def test_none_identity_ref_is_invalid_reference(self):
        env = self.store.summary(None)
        self.assertFalse(env["ok"])
        self.assertEqual(env["error"]["code"], Q_INVALID_REFERENCE)

    def test_invalid_reference_not_coerced_to_no_record(self):
        env = self.store.summary("")
        self.assertNotEqual(env.get("null_semantics"),
                            NullSemantics.NO_RECORD.value)


class TestCF3DrillDownValidationGates(unittest.TestCase):
    """CF-3: get_event / get_failure_category validate BEFORE existence."""

    def setUp(self):
        self.store = HistoryStore()
        self.store.ingest_event(make_event(event_id="evt-d1"))

    def test_get_event_none_event_id_is_invalid_reference(self):
        env = self.store.get_event(None)
        self.assertFalse(env["ok"])
        self.assertEqual(env["error"]["code"], Q_INVALID_REFERENCE)
        self.assertEqual(env["error"]["field"], "event_id")

    def test_get_event_empty_event_id_is_invalid_reference(self):
        env = self.store.get_event("")
        self.assertFalse(env["ok"])
        self.assertEqual(env["error"]["code"], Q_INVALID_REFERENCE)

    def test_get_event_invalid_capability_on_missing_event(self):
        # Validation must run BEFORE the existence check: an unknown event_id
        # with an invalid capability is an invalid request, not NO_RECORD.
        env = self.store.get_event("evt-does-not-exist", capability="invalid")
        self.assertFalse(env["ok"])
        self.assertEqual(env["error"]["code"], Q_INVALID_ENUM)
        self.assertEqual(env["error"]["field"], "capability")

    def test_get_failure_category_invalid_reference(self):
        for bad in (None, "", ["evt-d1"]):
            env = self.store.get_failure_category(bad)
            self.assertFalse(env["ok"], repr(bad))
            self.assertEqual(env["error"]["code"], Q_INVALID_REFERENCE)

    def test_get_failure_category_still_three_state_for_valid_refs(self):
        na = self.store.get_failure_category("evt-d1")
        norec = self.store.get_failure_category("evt-missing")
        self.assertEqual(na["null_semantics"],
                         NullSemantics.NOT_APPLICABLE.value)
        self.assertEqual(norec["null_semantics"],
                         NullSemantics.NO_RECORD.value)


class TestMF1IndependenceOnlyFromConferring(unittest.TestCase):
    """MF-1: bounded-scope independent records cannot launder SELF events."""

    def _launder_store(self):
        store = HistoryStore()
        store.ingest_verification(make_verification(
            verification_id="ver-self",
            verifier={"verifier_name": "self-agent", "verifier_class": "SELF"},
            self_verification=True,
            scope=event_scope("evt-launder")))
        store.ingest_verification(make_verification(
            verification_id="ver-bounded",
            verifier={"verifier_name": "indep-1",
                      "verifier_class": "INDEPENDENT_AGENT"},
            scope=event_scope("evt-launder", aspect="EVIDENCE_BINDING")))
        store.ingest_event(make_event(
            event_id="evt-launder",
            verification_references=[ref("ver-self", "self-agent"),
                                     ref("ver-bounded", "indep-1")]))
        return store

    def test_self_event_level_not_laundered_by_bounded_independent(self):
        store = self._launder_store()
        # The SELF record confers VERIFIED at event level; the bounded
        # independent record must NOT flip the independence classification.
        self.assertEqual(store.event_verification_status("evt-launder"),
                         "VERIFIED")
        v1 = store.summary(AGENT)["result"]["by_version"]["1.0.0"]
        self.assertEqual(v1["independently_verified_events"], 0)
        self.assertEqual(v1["self_verified_events"], 1)

    def test_detail_independence_metadata_not_laundered(self):
        store = self._launder_store()
        env = store.get_event("evt-launder", capability="detail")
        indep = env["result"]["structured_facts"]["verification_independence"]
        self.assertFalse(indep["has_independent_verification"])
        self.assertTrue(indep["self_only"])
        self.assertEqual(indep["independence_class"], "SELF")

    def test_independent_filter_not_satisfied_by_bounded_record(self):
        store = self._launder_store()
        env = store.query_events(identity_ref=AGENT,
                                 require_independent_verification=True)
        self.assertEqual(env["result"]["count"], 0)

    def test_event_level_independent_still_counts(self):
        store = HistoryStore()
        store.ingest_verification(make_verification(
            verification_id="ver-ind", scope=event_scope("evt-ind")))
        store.ingest_event(make_event(
            event_id="evt-ind", verification_references=[ref("ver-ind")]))
        v1 = store.summary(AGENT)["result"]["by_version"]["1.0.0"]
        self.assertEqual(v1["independently_verified_events"], 1)


class TestMF2NotAssessedFiltering(unittest.TestCase):
    """MF-2: NOT_ASSESSED conferring records must not crash the precedence
    derivation (absent from _STATUS_PRIORITY -> bare StopIteration)."""

    def test_referenced_not_assessed_record_no_crash(self):
        store = HistoryStore()
        store.ingest_verification(make_verification(
            verification_id="ver-na", verification_status="NOT_ASSESSED",
            scope=event_scope("evt-na")))
        store.ingest_event(make_event(
            event_id="evt-na", verification_references=[ref("ver-na")]))
        self.assertEqual(store.event_verification_status("evt-na"),
                         "NOT_ASSESSED")

    def test_not_assessed_summary_and_query_paths_stable(self):
        store = HistoryStore()
        store.ingest_verification(make_verification(
            verification_id="ver-na", verification_status="NOT_ASSESSED",
            scope=event_scope("evt-na")))
        store.ingest_event(make_event(
            event_id="evt-na", verification_references=[ref("ver-na")]))
        v1 = store.summary(AGENT)["result"]["by_version"]["1.0.0"]
        self.assertEqual(v1["not_assessed_events"], 1)
        self.assertEqual(v1["verified_events"], 0)
        env = store.query_events(identity_ref=AGENT,
                                 verification_status="NOT_ASSESSED")
        self.assertEqual(env["result"]["count"], 1)

    def test_not_assessed_alongside_verified_does_not_dominate(self):
        store = HistoryStore()
        store.ingest_verification(make_verification(
            verification_id="ver-na", verification_status="NOT_ASSESSED",
            scope=event_scope("evt-mix")))
        store.ingest_verification(make_verification(
            verification_id="ver-ok", verification_status="VERIFIED",
            scope=event_scope("evt-mix")))
        store.ingest_event(make_event(
            event_id="evt-mix",
            verification_references=[ref("ver-na"), ref("ver-ok")]))
        self.assertEqual(store.event_verification_status("evt-mix"),
                         "VERIFIED")


class TestMF3WithheldAuxiliaryGuard(unittest.TestCase):
    """MF-3: WITHHELD events leak nothing through auxiliary public methods."""

    def _withheld_store(self):
        store = HistoryStore()
        store.ingest_verification(make_verification(
            verification_id="ver-wh", scope=event_scope("evt-wh")))
        store.ingest_event(make_event(
            event_id="evt-wh",
            disclosure={"disclosure_scope": "WITHHELD", "declared_by": "h"},
            verification_references=[ref("ver-wh")]))
        return store

    def test_verifications_for_event_withheld_is_empty(self):
        store = self._withheld_store()
        self.assertEqual(store.verifications_for_event("evt-wh"), [])

    def test_event_verification_status_withheld_reports_withheld(self):
        store = self._withheld_store()
        self.assertEqual(store.event_verification_status("evt-wh"), "WITHHELD")

    def test_non_withheld_auxiliary_methods_unaffected(self):
        store = self._withheld_store()
        store.ingest_verification(make_verification(
            verification_id="ver-vis", scope=event_scope("evt-vis")))
        store.ingest_event(make_event(
            event_id="evt-vis", verification_references=[ref("ver-vis")]))
        self.assertEqual(len(store.verifications_for_event("evt-vis")), 1)
        self.assertEqual(store.event_verification_status("evt-vis"),
                         "VERIFIED")


class TestMF4NoInjectableClock(unittest.TestCase):
    """MF-4: callers cannot bypass expiry enforcement by injecting a clock."""

    def _expired_store(self):
        store = HistoryStore()
        store.ingest_event(make_event(
            event_id="evt-exp",
            disclosure={"disclosure_scope": "PUBLIC",
                        "expires_at": LONG_PAST, "declared_by": "h"}))
        return store

    def test_now_parameter_removed_from_signature(self):
        params = inspect.signature(HistoryStore.get_event).parameters
        self.assertNotIn("now", params)

    def test_injected_now_is_rejected(self):
        store = self._expired_store()
        with self.assertRaises(TypeError):
            store.get_event("evt-exp", capability="detail", now=0.0)

    def test_expired_event_still_denied_without_injection(self):
        store = self._expired_store()
        env = store.get_event("evt-exp", capability="detail")
        self.assertFalse(env["ok"])
        self.assertEqual(env["error"]["code"], Q_DISCLOSURE_EXPIRED)

    def test_clock_monkeypatch_point_is_module_level(self):
        store = HistoryStore()
        store.ingest_event(make_event(
            event_id="evt-fut",
            disclosure={"disclosure_scope": "PUBLIC",
                        "expires_at": "2099-01-01T00:00:00Z",
                        "declared_by": "h"}))
        original = engine_module._clock
        try:
            # A test-only clock far past the expiry instant must deny detail.
            engine_module._clock = lambda: 4102444800.5  # 2100-01-01T00:00:00Z
            env = store.get_event("evt-fut", capability="detail")
            self.assertFalse(env["ok"])
            self.assertEqual(env["error"]["code"], Q_DISCLOSURE_EXPIRED)
        finally:
            engine_module._clock = original


class TestMF5DisclosureScopeFilter(unittest.TestCase):
    """MF-5: disclosure_scope is a real filter, not validated-and-ignored."""

    def setUp(self):
        self.store = HistoryStore()
        self.store.ingest_event(make_event(
            event_id="evt-public",
            disclosure={"disclosure_scope": "PUBLIC", "declared_by": "h"}))
        self.store.ingest_event(make_event(
            event_id="evt-fed", occurred_at="2026-08-02T00:00:00Z"))
        self.store.ingest_event(make_event(
            event_id="evt-hidden", occurred_at="2026-08-03T00:00:00Z",
            disclosure={"disclosure_scope": "WITHHELD", "declared_by": "h"}))

    def test_filter_matches_only_declared_scope(self):
        env = self.store.query_events(identity_ref=AGENT,
                                      disclosure_scope="PUBLIC")
        ids = [e["event_id"] for e in env["result"]["events"]]
        self.assertEqual(ids, ["evt-public"])

    def test_filter_federated(self):
        env = self.store.query_events(identity_ref=AGENT,
                                      disclosure_scope="FEDERATED")
        ids = [e["event_id"] for e in env["result"]["events"]]
        self.assertEqual(ids, ["evt-fed"])

    def test_withheld_scope_never_returns_content(self):
        env = self.store.query_events(identity_ref=AGENT,
                                      disclosure_scope="WITHHELD")
        self.assertEqual(env["result"]["count"], 0)
        self.assertEqual(env["selective_disclosure"]["withheld_count"], 1)
        self.assertEqual(env["null_semantics"], NullSemantics.WITHHELD.value)

    def test_no_filter_still_returns_all_visible(self):
        env = self.store.query_events(identity_ref=AGENT)
        self.assertEqual(env["result"]["count"], 2)


class TestMF7LimitErrorCode(unittest.TestCase):
    """MF-7: invalid limit returns Q_INVALID_PARAM (not Q_INVALID_REFERENCE)."""

    def setUp(self):
        self.store = HistoryStore()
        self.store.ingest_event(make_event(event_id="evt-lim"))

    def test_invalid_limit_values_use_invalid_param(self):
        for bad in (0, -1, -100, "3", 2.5, True, ["1"]):
            env = self.store.query_events(identity_ref=AGENT, limit=bad)
            self.assertFalse(env["ok"], repr(bad))
            self.assertEqual(env["error"]["code"], Q_INVALID_PARAM,
                             repr(bad))
            self.assertEqual(env["error"]["field"], "limit")

    def test_valid_limit_still_works(self):
        self.store.ingest_event(make_event(
            event_id="evt-lim2", occurred_at="2026-08-02T00:00:00Z"))
        env = self.store.query_events(identity_ref=AGENT, limit=1)
        self.assertTrue(env["ok"])
        self.assertEqual(env["result"]["count"], 1)


class TestAF1MalformedExpiryFailClosed(unittest.TestCase):
    """AF-1: malformed expires_at is treated as expired (fail-closed)."""

    def test_malformed_expires_at_denies_detail(self):
        store = HistoryStore()
        event = make_event(
            event_id="evt-badexp",
            disclosure={"disclosure_scope": "PUBLIC",
                        "expires_at": "not-a-date", "declared_by": "h"})
        # Direct hold insertion: this test targets engine-level enforcement,
        # independent of schema format strictness.
        store._events["evt-badexp"] = event
        env = store.get_event("evt-badexp", capability="detail")
        self.assertFalse(env["ok"])
        self.assertEqual(env["error"]["code"], Q_DISCLOSURE_EXPIRED)
        self.assertNotIn("result", env)

    def test_valid_future_expires_at_still_allows(self):
        store = HistoryStore()
        store.ingest_event(make_event(
            event_id="evt-goodexp",
            disclosure={"disclosure_scope": "PUBLIC",
                        "expires_at": "2099-01-01T00:00:00Z",
                        "declared_by": "h"}))
        env = store.get_event("evt-goodexp", capability="detail")
        self.assertTrue(env["ok"])
        self.assertIn("structured_facts", env["result"])


if __name__ == "__main__":
    unittest.main()

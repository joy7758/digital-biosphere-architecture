"""Trust-boundary hardening regression tests (audit round 3).

Covers the four audit-r3 fixes:

* R3-1 -- Disclosure Context anti-forgery: a configured policy decision
  resolver must confirm the external policy decision reference; without a
  resolver EVERY RESTRICTED detail read fails closed
  (Q_POLICY_DECISION_REQUIRED). Contexts must carry issuer and decision_id.
* R3-2 -- unified disclosure guard: verifications_for_event /
  event_verification_status / get_failure_category route through the same
  disclosure truth table as get_event (_require_detail_disclosure).
* R3-3 -- event-level verification binding requires scope.agent_ref AND
  scope.agent_version (validator + engine, fail-closed), both matching the
  subject event.
* R3-4 -- NOT_ASSESSED records never confer independence.

Plus truth-gate consistency checks (STATUS.md / README.md / actual test
discovery). These tests are additive; all data is SYNTHETIC_ONLY.
"""

from __future__ import annotations

import json
import re
import unittest

from tests._helpers import AHRP_ROOT, make_event, make_verification

from query import HistoryStore, NullSemantics
from query.engine import (
    Q_DISCLOSURE_DENIED,
    Q_DISCLOSURE_EXPIRED,
    Q_DISCLOSURE_REVOKED,
    Q_INVALID_ENUM,
    Q_INVALID_PARAM,
    Q_INVALID_TIME_FORMAT,
    Q_POLICY_DECISION_REQUIRED,
    SyntheticPolicyResolver,
)
from validator import validate_verification_record

AGENT = "did:example:test-agent"
FAR_FUTURE = "2099-01-01T00:00:00Z"
LONG_PAST = "2000-01-01T00:00:00Z"
POLICY_REF = "policy-decision-0001"


def make_disclosure_context(**overrides):
    ctx = {
        "requester_reference": "did:example:requester",
        "requested_disclosure_scope": "RESTRICTED",
        "granted_scope": "RESTRICTED",
        "external_policy_decision_reference": POLICY_REF,
        "policy_version": "0.1",
        "evaluated_at": "2026-08-01T00:00:00Z",
        "expiry": FAR_FUTURE,
        "revocation_status": "ACTIVE",
        "issuer": "did:example:policy-authority",
        "decision_id": "decision-0001",
    }
    ctx.update(overrides)
    return ctx


def event_scope(event_id, aspect="FULL_EVENT", subject_type="EXPERIENCE_EVENT",
                agent_ref=AGENT, agent_version="1.0.0"):
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


def restricted_store(with_resolver=True):
    resolver = SyntheticPolicyResolver({POLICY_REF}) if with_resolver else None
    store = HistoryStore(policy_decision_resolver=resolver)
    store.ingest_event(make_event(
        event_id="evt-rest",
        disclosure={"disclosure_scope": "RESTRICTED", "declared_by": "h"}))
    return store


class TestR31DisclosureAntiForgery(unittest.TestCase):
    """R3-1: format-only disclosure contexts can never bypass RESTRICTED."""

    def test_fake_policy_reference_denied(self):
        store = restricted_store()  # resolver whitelists POLICY_REF only
        env = store.get_event(
            "evt-rest", capability="detail",
            disclosure_context=make_disclosure_context(
                external_policy_decision_reference="policy-decision-FAKE"))
        self.assertFalse(env["ok"])
        self.assertEqual(env["error"]["code"], Q_POLICY_DECISION_REQUIRED)

    def test_no_resolver_configured_fails_closed_with_ctx(self):
        store = restricted_store(with_resolver=False)
        env = store.get_event("evt-rest", capability="detail",
                              disclosure_context=make_disclosure_context())
        self.assertFalse(env["ok"])
        self.assertEqual(env["error"]["code"], Q_POLICY_DECISION_REQUIRED)

    def test_no_resolver_configured_fails_closed_without_ctx(self):
        store = restricted_store(with_resolver=False)
        env = store.get_event("evt-rest", capability="detail")
        self.assertFalse(env["ok"])
        self.assertEqual(env["error"]["code"], Q_POLICY_DECISION_REQUIRED)

    def test_valid_resolver_and_reference_allows(self):
        store = restricted_store()
        env = store.get_event("evt-rest", capability="detail",
                              disclosure_context=make_disclosure_context())
        self.assertTrue(env["ok"])
        self.assertIn("structured_facts", env["result"])

    def test_missing_issuer_denied(self):
        store = restricted_store()
        ctx = make_disclosure_context()
        del ctx["issuer"]
        env = store.get_event("evt-rest", capability="detail",
                              disclosure_context=ctx)
        self.assertFalse(env["ok"])
        self.assertEqual(env["error"]["code"], Q_POLICY_DECISION_REQUIRED)

    def test_missing_decision_id_denied(self):
        store = restricted_store()
        ctx = make_disclosure_context()
        del ctx["decision_id"]
        env = store.get_event("evt-rest", capability="detail",
                              disclosure_context=ctx)
        self.assertFalse(env["ok"])
        self.assertEqual(env["error"]["code"], Q_POLICY_DECISION_REQUIRED)

    def test_expired_authorization_denied(self):
        store = restricted_store()
        env = store.get_event(
            "evt-rest", capability="detail",
            disclosure_context=make_disclosure_context(expiry=LONG_PAST))
        self.assertFalse(env["ok"])
        self.assertEqual(env["error"]["code"], Q_DISCLOSURE_EXPIRED)

    def test_revoked_authorization_denied(self):
        store = restricted_store()
        env = store.get_event(
            "evt-rest", capability="detail",
            disclosure_context=make_disclosure_context(
                revocation_status="REVOKED"))
        self.assertFalse(env["ok"])
        self.assertEqual(env["error"]["code"], Q_DISCLOSURE_REVOKED)

    def test_scope_mismatch_denied(self):
        store = restricted_store()
        env = store.get_event(
            "evt-rest", capability="detail",
            disclosure_context=make_disclosure_context(granted_scope="PUBLIC"))
        self.assertFalse(env["ok"])
        self.assertEqual(env["error"]["code"], Q_DISCLOSURE_DENIED)

    def test_resolver_exception_fails_closed(self):
        def exploding_resolver(reference):
            raise RuntimeError("synthetic resolver outage")

        store = HistoryStore(policy_decision_resolver=exploding_resolver)
        store.ingest_event(make_event(
            event_id="evt-rest",
            disclosure={"disclosure_scope": "RESTRICTED", "declared_by": "h"}))
        env = store.get_event("evt-rest", capability="detail",
                              disclosure_context=make_disclosure_context())
        self.assertFalse(env["ok"])
        self.assertEqual(env["error"]["code"], Q_POLICY_DECISION_REQUIRED)

    def test_resolver_non_dict_result_fails_closed(self):
        store = HistoryStore(policy_decision_resolver=lambda r: None)
        store.ingest_event(make_event(
            event_id="evt-rest",
            disclosure={"disclosure_scope": "RESTRICTED", "declared_by": "h"}))
        env = store.get_event("evt-rest", capability="detail",
                              disclosure_context=make_disclosure_context())
        self.assertFalse(env["ok"])
        self.assertEqual(env["error"]["code"], Q_POLICY_DECISION_REQUIRED)


class TestR32UnifiedDisclosureGuard(unittest.TestCase):
    """R3-2: every data-access path walks the same disclosure truth table."""

    def setUp(self):
        self.ctx = make_disclosure_context()
        self.store = HistoryStore(
            policy_decision_resolver=SyntheticPolicyResolver({POLICY_REF}))
        # RESTRICTED event with a bound verification.
        self.store.ingest_verification(make_verification(
            verification_id="ver-r1", scope=event_scope("evt-rest")))
        self.store.ingest_event(make_event(
            event_id="evt-rest",
            disclosure={"disclosure_scope": "RESTRICTED", "declared_by": "h"},
            verification_references=[ref("ver-r1")]))
        # Open-scope control events.
        self.store.ingest_verification(make_verification(
            verification_id="ver-p1", scope=event_scope("evt-pub")))
        self.store.ingest_event(make_event(
            event_id="evt-pub", occurred_at="2026-08-02T00:00:00Z",
            disclosure={"disclosure_scope": "PUBLIC", "declared_by": "h"},
            verification_references=[ref("ver-p1")]))
        self.store.ingest_verification(make_verification(
            verification_id="ver-f1", scope=event_scope("evt-fed")))
        self.store.ingest_event(make_event(
            event_id="evt-fed", occurred_at="2026-08-03T00:00:00Z",
            verification_references=[ref("ver-f1")]))

    def test_restricted_verifications_without_ctx_denied(self):
        self.assertEqual(self.store.verifications_for_event("evt-rest"), [])

    def test_restricted_status_without_ctx_restricted(self):
        self.assertEqual(self.store.event_verification_status("evt-rest"),
                         "RESTRICTED")

    def test_restricted_failure_category_without_ctx_denied(self):
        env = self.store.get_failure_category("evt-rest")
        self.assertFalse(env["ok"])
        self.assertEqual(env["error"]["code"], Q_POLICY_DECISION_REQUIRED)
        self.assertNotIn("failure_category", env.get("result", {}))

    def test_restricted_with_valid_ctx_full_access(self):
        records = self.store.verifications_for_event("evt-rest", self.ctx)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["verification_id"], "ver-r1")
        self.assertEqual(
            self.store.event_verification_status("evt-rest", self.ctx),
            "VERIFIED")
        env = self.store.get_failure_category("evt-rest", self.ctx)
        self.assertTrue(env["ok"])
        self.assertEqual(env["null_semantics"],
                         NullSemantics.NOT_APPLICABLE.value)

    def test_restricted_fake_ctx_denied_on_all_paths(self):
        fake_ctx = make_disclosure_context(
            external_policy_decision_reference="policy-decision-FAKE")
        self.assertEqual(
            self.store.verifications_for_event("evt-rest", fake_ctx), [])
        self.assertEqual(
            self.store.event_verification_status("evt-rest", fake_ctx),
            "RESTRICTED")
        env = self.store.get_failure_category("evt-rest", fake_ctx)
        self.assertFalse(env["ok"])
        self.assertEqual(env["error"]["code"], Q_POLICY_DECISION_REQUIRED)

    def test_public_all_paths_work_without_ctx(self):
        self.assertEqual(len(self.store.verifications_for_event("evt-pub")), 1)
        self.assertEqual(self.store.event_verification_status("evt-pub"),
                         "VERIFIED")
        env = self.store.get_failure_category("evt-pub")
        self.assertTrue(env["ok"])

    def test_federated_all_paths_work_without_ctx(self):
        self.assertEqual(len(self.store.verifications_for_event("evt-fed")), 1)
        self.assertEqual(self.store.event_verification_status("evt-fed"),
                         "VERIFIED")
        env = self.store.get_failure_category("evt-fed")
        self.assertTrue(env["ok"])

    def test_withheld_still_three_state_on_all_paths(self):
        self.store.ingest_event(make_event(
            event_id="evt-wh", occurred_at="2026-08-04T00:00:00Z",
            disclosure={"disclosure_scope": "WITHHELD", "declared_by": "h"}))
        self.assertEqual(self.store.verifications_for_event("evt-wh"), [])
        self.assertEqual(self.store.event_verification_status("evt-wh"),
                         "WITHHELD")
        env = self.store.get_failure_category("evt-wh")
        self.assertEqual(env["null_semantics"], NullSemantics.WITHHELD.value)


class TestR33AgentVersionBinding(unittest.TestCase):
    """R3-3: event-level verification must bind agent AND version."""

    def _engine_store_with_unbound(self, scope):
        """Insert a record directly into the holder to exercise the engine
        binding rules independently of ingest-time schema validation."""
        store = HistoryStore()
        record = make_verification(verification_id="ver-x")
        record["scope"] = scope
        store._verifications["ver-x"] = record
        store.ingest_event(make_event(
            event_id="evt-x", verification_references=[ref("ver-x")]))
        return store

    def test_missing_agent_ref_binding_is_invalid(self):
        store = self._engine_store_with_unbound(
            event_scope("evt-x", agent_ref=None))
        self.assertEqual(store.event_verification_status("evt-x"), "INVALID")
        resolution = store._resolve_event_verification(store._events["evt-x"])
        self.assertTrue(any(
            isinstance(e, dict) and e.get("reason") == "BINDING_INCOMPLETE"
            for e in resolution["binding_errors"]))

    def test_missing_agent_version_binding_is_invalid(self):
        store = self._engine_store_with_unbound(
            event_scope("evt-x", agent_version=None))
        self.assertEqual(store.event_verification_status("evt-x"), "INVALID")

    def test_validator_rejects_event_scope_without_agent_ref(self):
        record = make_verification(scope=event_scope("evt-x", agent_ref=None))
        result = validate_verification_record(record)
        self.assertFalse(result.valid)
        self.assertIn("E_FIELD_MISSING", {e["code"] for e in result.errors})
        self.assertIn("$.scope.agent_ref",
                      {e["path"] for e in result.errors})

    def test_validator_rejects_event_scope_without_agent_version(self):
        record = make_verification(
            scope=event_scope("evt-x", agent_version=None))
        result = validate_verification_record(record)
        self.assertFalse(result.valid)
        self.assertIn("$.scope.agent_version",
                      {e["path"] for e in result.errors})

    def test_wrong_agent_binding_is_invalid(self):
        store = HistoryStore()
        store.ingest_verification(make_verification(
            verification_id="ver-wa",
            scope=event_scope("evt-wa", agent_ref="did:example:someone-else")))
        store.ingest_event(make_event(
            event_id="evt-wa", verification_references=[ref("ver-wa")]))
        self.assertEqual(store.event_verification_status("evt-wa"), "INVALID")

    def test_wrong_version_binding_is_invalid(self):
        store = HistoryStore()
        store.ingest_verification(make_verification(
            verification_id="ver-wv",
            scope=event_scope("evt-wv", agent_version="9.9.9")))
        store.ingest_event(make_event(
            event_id="evt-wv", verification_references=[ref("ver-wv")]))
        self.assertEqual(store.event_verification_status("evt-wv"), "INVALID")

    def test_complete_binding_works(self):
        store = HistoryStore()
        store.ingest_verification(make_verification(
            verification_id="ver-ok", scope=event_scope("evt-ok")))
        store.ingest_event(make_event(
            event_id="evt-ok", verification_references=[ref("ver-ok")]))
        self.assertEqual(store.event_verification_status("evt-ok"), "VERIFIED")

    def test_unreferenced_verification_is_not_assessed(self):
        store = HistoryStore()
        store.ingest_event(make_event(event_id="evt-nb"))
        store.ingest_verification(make_verification(
            verification_id="ver-nb", scope=event_scope("evt-nb")))
        self.assertEqual(store.event_verification_status("evt-nb"),
                         "NOT_ASSESSED")

    def test_conflicting_verifications_are_conflicted(self):
        store = HistoryStore()
        store.ingest_verification(make_verification(
            verification_id="ver-c1", verification_status="VERIFIED",
            scope=event_scope("evt-cf")))
        store.ingest_verification(make_verification(
            verification_id="ver-c2", verification_status="CONFLICTED",
            scope=event_scope("evt-cf")))
        store.ingest_event(make_event(
            event_id="evt-cf",
            verification_references=[ref("ver-c1"), ref("ver-c2")]))
        self.assertEqual(store.event_verification_status("evt-cf"),
                         "CONFLICTED")


class TestR34NotAssessedNeverConfersIndependence(unittest.TestCase):
    """R3-4: independence classification requires event-level AND asserting
    (non-NOT_ASSESSED) records."""

    def _self_record(self, verification_id, event_id, status="VERIFIED"):
        return make_verification(
            verification_id=verification_id,
            verifier={"verifier_name": "self-agent", "verifier_class": "SELF"},
            self_verification=True,
            verification_status=status,
            scope=event_scope(event_id))

    def _independent_record(self, verification_id, event_id,
                            status="VERIFIED"):
        return make_verification(
            verification_id=verification_id,
            verifier={"verifier_name": "indep-1",
                      "verifier_class": "INDEPENDENT_AGENT"},
            verification_status=status,
            scope=event_scope(event_id))

    def test_self_verified_plus_independent_not_assessed_not_independent(self):
        store = HistoryStore()
        store.ingest_verification(self._self_record("ver-s", "evt-mix"))
        store.ingest_verification(self._independent_record(
            "ver-na", "evt-mix", status="NOT_ASSESSED"))
        store.ingest_event(make_event(
            event_id="evt-mix",
            verification_references=[ref("ver-s", "self-agent"),
                                     ref("ver-na", "indep-1")]))
        resolution = store._resolve_event_verification(
            store._events["evt-mix"])
        self.assertFalse(resolution["has_independent"])
        self.assertTrue(resolution["self_only"])
        self.assertEqual(resolution["effective_status"], "VERIFIED")
        v1 = store.summary(AGENT)["result"]["by_version"]["1.0.0"]
        self.assertEqual(v1["independently_verified_events"], 0)
        self.assertEqual(v1["self_verified_events"], 1)

    def test_self_plus_independent_verified_counts_independent(self):
        store = HistoryStore()
        store.ingest_verification(self._self_record("ver-s", "evt-mix"))
        store.ingest_verification(self._independent_record("ver-i", "evt-mix"))
        store.ingest_event(make_event(
            event_id="evt-mix",
            verification_references=[ref("ver-s", "self-agent"),
                                     ref("ver-i", "indep-1")]))
        resolution = store._resolve_event_verification(
            store._events["evt-mix"])
        self.assertTrue(resolution["has_independent"])
        self.assertFalse(resolution["self_only"])
        v1 = store.summary(AGENT)["result"]["by_version"]["1.0.0"]
        self.assertEqual(v1["independently_verified_events"], 1)

    def test_multiple_self_records_stay_self_only(self):
        store = HistoryStore()
        store.ingest_verification(self._self_record("ver-s1", "evt-s"))
        store.ingest_verification(make_verification(
            verification_id="ver-s2",
            verifier={"verifier_name": "self-agent-2",
                      "verifier_class": "SELF"},
            self_verification=True, scope=event_scope("evt-s")))
        store.ingest_event(make_event(
            event_id="evt-s",
            verification_references=[ref("ver-s1", "self-agent"),
                                     ref("ver-s2", "self-agent-2")]))
        resolution = store._resolve_event_verification(store._events["evt-s"])
        self.assertTrue(resolution["self_only"])
        self.assertFalse(resolution["has_independent"])

    def test_mixed_self_and_independent_partially_verified(self):
        store = HistoryStore()
        store.ingest_verification(self._self_record("ver-s", "evt-p"))
        store.ingest_verification(self._independent_record(
            "ver-p", "evt-p", status="PARTIALLY_VERIFIED"))
        store.ingest_event(make_event(
            event_id="evt-p",
            verification_references=[ref("ver-s", "self-agent"),
                                     ref("ver-p", "indep-1")]))
        resolution = store._resolve_event_verification(store._events["evt-p"])
        self.assertEqual(resolution["effective_status"], "PARTIALLY_VERIFIED")
        self.assertTrue(resolution["has_independent"])
        self.assertFalse(resolution["self_only"])
        v1 = store.summary(AGENT)["result"]["by_version"]["1.0.0"]
        self.assertEqual(v1["partially_verified_events"], 1)


class TestR3QueryRegression(unittest.TestCase):
    """Defect-4 stable error semantics must hold after the r3 changes."""

    def setUp(self):
        self.store = HistoryStore()
        self.store.ingest_event(make_event(event_id="evt-q1"))

    def test_unhashable_param_is_stable_error(self):
        env = self.store.query_events(identity_ref=AGENT, task_type=["X"])
        self.assertFalse(env["ok"])
        self.assertEqual(env["error"]["code"], Q_INVALID_ENUM)

    def test_invalid_boolean_limit_is_stable_error(self):
        env = self.store.query_events(identity_ref=AGENT, limit=True)
        self.assertFalse(env["ok"])
        self.assertEqual(env["error"]["code"], Q_INVALID_PARAM)

    def test_invalid_enum_is_stable_error(self):
        env = self.store.query_events(identity_ref=AGENT,
                                      verification_status="BOGUS")
        self.assertFalse(env["ok"])
        self.assertEqual(env["error"]["code"], Q_INVALID_ENUM)

    def test_malformed_time_is_stable_error(self):
        env = self.store.query_events(identity_ref=AGENT,
                                      time_start="not-a-date")
        self.assertFalse(env["ok"])
        self.assertEqual(env["error"]["code"], Q_INVALID_TIME_FORMAT)

    def test_valid_query_without_results_is_no_record(self):
        env = self.store.query_events(identity_ref=AGENT,
                                      task_type="RESEARCH")
        self.assertTrue(env["ok"])
        self.assertEqual(env["null_semantics"], NullSemantics.NO_RECORD.value)


class TestR35TruthConsistency(unittest.TestCase):
    """Fix 5 truth gate: STATUS.md / README.md must match reality and must
    not contradict each other."""

    STATUS_PATH = AHRP_ROOT / "STATUS.md"
    README_PATH = AHRP_ROOT / "README.md"

    def _parse_truth_gates(self, text):
        gates = {}
        for match in re.finditer(r"^([A-Z][A-Z0-9_]*)=(\S+)\s*$", text,
                                 re.MULTILINE):
            gates[match.group(1)] = match.group(2)
        return gates

    def test_manifest_consistency_truth_gates_do_not_contradict(self):
        gates = self._parse_truth_gates(
            self.STATUS_PATH.read_text(encoding="utf-8"))
        self.assertEqual(gates.get("SYNTHETIC_ONLY"), "true")
        self.assertEqual(gates.get("PRODUCTION_READY"), "false")
        self.assertEqual(gates.get("AHRP_PRODUCTION_READY"), "false")
        self.assertEqual(gates.get("AHRP_STANDARD_PUBLISHED"), "false")
        self.assertEqual(gates.get("AHRP_REAL_WORLD_ADOPTION_VALIDATED"),
                         "false")
        self.assertEqual(gates.get("REFERENCE_IMPLEMENTATION_NE_STANDARD"),
                         "true")
        self.assertEqual(gates.get("VALIDATOR_PASS_NE_COMPLIANCE"), "true")
        self.assertEqual(gates.get("AHRP_IS_RATING_SYSTEM"), "false")
        self.assertEqual(gates.get("AHRP_IS_RECOMMENDATION_SYSTEM"), "false")
        self.assertEqual(gates.get("AHRP_IS_LEARNING_SYSTEM"), "false")
        # r3 must not self-declare the independent review as PASS before the
        # independent re-verification actually happened.
        self.assertIn(gates.get("AHRP_INDEPENDENT_ADVERSARIAL_REVIEW"),
                      {"NOT_ASSESSED", "PENDING_R3"})

    def test_hash_consistency_schemas_are_valid_json(self):
        for name in ("experience-event.schema.json",
                     "verification.schema.json"):
            with open(AHRP_ROOT / "schema" / name, encoding="utf-8") as fh:
                schema = json.load(fh)
            self.assertEqual(schema["$schema"],
                             "http://json-schema.org/draft-07/schema#")
            self.assertIn("$id", schema)
            self.assertIn("properties", schema)
            self.assertIn("required", schema)

    def test_status_consistency_test_counts_align(self):
        status_text = self.STATUS_PATH.read_text(encoding="utf-8")
        readme_text = self.README_PATH.read_text(encoding="utf-8")
        status_match = re.search(r"Ran (\d+) tests", status_text)
        readme_match = re.search(
            r"unittest 自动化测试（(\d+) 项）", readme_text)
        self.assertIsNotNone(status_match, "STATUS.md test count missing")
        self.assertIsNotNone(readme_match, "README.md test count missing")
        status_count = int(status_match.group(1))
        readme_count = int(readme_match.group(1))
        loader = unittest.TestLoader()
        suite = loader.discover(str(AHRP_ROOT))
        actual = suite.countTestCases()
        self.assertEqual(status_count, actual,
                         "STATUS.md test count disagrees with discovery")
        self.assertEqual(readme_count, actual,
                         "README.md test count disagrees with discovery")
        self.assertGreater(actual, 168,
                           "r3 must be additive: total tests must exceed 168")


if __name__ == "__main__":
    unittest.main()

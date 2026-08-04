"""Query Interface tests: summary-first disclosure, filters, three-state null
semantics, identity continuity fail-closed, no derived ratios."""

from __future__ import annotations

import unittest

from tests._helpers import make_event, make_verification

from query import HistoryStore, NullSemantics
from query.engine import IngestError

AGENT = "did:example:test-agent"


def build_store():
    store = HistoryStore()
    store.ingest_event(make_event(
        event_id="evt-a1", result_status="SUCCESS",
        verification_references=[{"verification_id": "ver-a1",
                                  "verifier_name": "named-verifier-1"}]))
    store.ingest_event(make_event(event_id="evt-a2", task_type="ANALYSIS",
                                  result_status="FAILURE",
                                  failure_category="CAPABILITY_LIMIT",
                                  occurred_at="2026-08-02T09:00:00Z"))
    store.ingest_event(make_event(event_id="evt-a3", agent_version="2.0.0",
                                  occurred_at="2026-08-03T09:00:00Z"))
    store.ingest_event(make_event(event_id="evt-hidden",
                                  disclosure={"disclosure_scope": "WITHHELD",
                                              "declared_by": "h"},
                                  occurred_at="2026-08-04T09:00:00Z"))
    store.ingest_verification(make_verification(
        verification_id="ver-a1", scope={
            "subject_event_id": "evt-a1",
            "subject_type": "EXPERIENCE_EVENT",
            "covered_aspect": "FULL_EVENT",
            "agent_ref": AGENT,
            "agent_version": "1.0.0"}))
    return store


class TestSummary(unittest.TestCase):
    def setUp(self):
        self.store = build_store()

    def test_summary_returns_raw_counts_only(self):
        env = self.store.summary(AGENT)
        result = env["result"]
        v1 = result["by_version"]["1.0.0"]
        self.assertEqual(v1["total_events"], 2)
        self.assertEqual(v1["verified_events"], 1)
        self.assertEqual(result["withheld_events"], 1)

    def test_summary_never_contains_ratios_or_scores(self):
        env = self.store.summary(AGENT)

        def keys(node):
            if isinstance(node, dict):
                for k, v in node.items():
                    yield k
                    yield from keys(v)
            elif isinstance(node, list):
                for item in node:
                    yield from keys(item)

        all_keys = {k.lower() for k in keys(env)}
        for forbidden in ("ratio", "score", "rank", "rating", "percent"):
            self.assertFalse(any(forbidden in k for k in all_keys),
                             f"derived-metric key containing {forbidden!r}")

    def test_identity_continuity_fail_closed_no_cross_version_merge(self):
        result = self.store.summary(AGENT)["result"]
        self.assertIn("1.0.0", result["by_version"])
        self.assertIn("2.0.0", result["by_version"])
        self.assertEqual(
            result["identity_continuity"],
            "FAIL_CLOSED_PER_VERSION_COUNTS_ONLY")
        # No merged totals anywhere:
        self.assertNotIn("total_events", result)

    def test_unknown_agent_is_no_record(self):
        env = self.store.summary("did:example:ghost")
        self.assertEqual(env["null_semantics"], NullSemantics.NO_RECORD.value)
        self.assertEqual(env["result"]["total_events"], 0)

    def test_summary_is_default_mode(self):
        env = self.store.summary(AGENT)
        self.assertEqual(env["selective_disclosure"]["mode"], "summary")


class TestFilters(unittest.TestCase):
    def setUp(self):
        self.store = build_store()

    def test_query_by_task_type(self):
        env = self.store.query_events(identity_ref=AGENT, task_type="ANALYSIS")
        self.assertEqual(env["result"]["count"], 1)
        self.assertEqual(env["result"]["events"][0]["event_id"], "evt-a2")

    def test_query_by_time_window(self):
        env = self.store.query_events(identity_ref=AGENT,
                                      time_start="2026-08-02T00:00:00Z",
                                      time_end="2026-08-02T23:59:59Z")
        self.assertEqual(env["result"]["count"], 1)
        self.assertEqual(env["result"]["events"][0]["event_id"], "evt-a2")

    def test_filter_by_verification_status(self):
        env = self.store.query_events(identity_ref=AGENT,
                                      verification_status="VERIFIED")
        ids = [e["event_id"] for e in env["result"]["events"]]
        self.assertEqual(ids, ["evt-a1"])
        env2 = self.store.query_events(identity_ref=AGENT,
                                       verification_status="NOT_ASSESSED")
        self.assertEqual(env2["result"]["count"], 2)

    def test_withheld_events_never_leak_into_results(self):
        env = self.store.query_events(identity_ref=AGENT)
        ids = [e["event_id"] for e in env["result"]["events"]]
        self.assertNotIn("evt-hidden", ids)
        self.assertEqual(env["selective_disclosure"]["withheld_count"], 1)

    def test_withheld_only_match_reports_withheld_semantics(self):
        env = self.store.query_events(identity_ref=AGENT,
                                      time_start="2026-08-04T00:00:00Z")
        self.assertEqual(env["null_semantics"], NullSemantics.WITHHELD.value)


class TestDrillDownAndNullSemantics(unittest.TestCase):
    def setUp(self):
        self.store = build_store()

    def test_get_event_default_is_summary_not_detail(self):
        env = self.store.get_event("evt-a1")
        self.assertEqual(env["selective_disclosure"]["mode"], "summary")
        self.assertNotIn("structured_facts", env["result"])

    def test_detail_requires_explicit_capability(self):
        env = self.store.get_event("evt-a1", capability="detail")
        self.assertEqual(env["selective_disclosure"]["mode"], "detail")
        self.assertIn("structured_facts", env["result"])
        self.assertEqual(env["result"]["structured_facts"]
                         ["verification_status"], "VERIFIED")

    def test_detail_free_text_in_restricted_channel(self):
        event = make_event(event_id="evt-note",
                           notes="harmless data note")
        self.store.ingest_event(event)
        env = self.store.get_event("evt-note", capability="detail")
        self.assertIn("notes", env["content_channel"]["restricted_text"])
        self.assertNotIn("notes", env["result"]["structured_facts"])
        self.assertIn("notes", env["result"]["restricted_text"])

    def test_unknown_event_is_no_record(self):
        env = self.store.get_event("evt-missing", capability="detail")
        self.assertEqual(env["null_semantics"], NullSemantics.NO_RECORD.value)

    def test_withheld_event_detail_is_withheld(self):
        env = self.store.get_event("evt-hidden", capability="detail")
        self.assertEqual(env["null_semantics"], NullSemantics.WITHHELD.value)
        self.assertNotIn("structured_facts", env["result"])

    def test_three_states_are_distinguishable(self):
        na = self.store.get_failure_category("evt-a1")      # SUCCESS event
        none = self.store.get_failure_category("evt-a2")    # FAILURE event
        norec = self.store.get_failure_category("evt-missing")
        self.assertEqual(na["null_semantics"],
                         NullSemantics.NOT_APPLICABLE.value)
        self.assertEqual(none["null_semantics"], NullSemantics.NONE.value)
        self.assertEqual(none["result"]["failure_category"], "CAPABILITY_LIMIT")
        self.assertEqual(norec["null_semantics"], NullSemantics.NO_RECORD.value)
        self.assertEqual(len({na["null_semantics"], none["null_semantics"],
                              norec["null_semantics"]}), 3)


class TestF4NestedFreeTextChannel(unittest.TestCase):
    def test_identity_note_declared_in_restricted_channel(self):
        store = HistoryStore()
        store.ingest_event(make_event(
            event_id="evt-nested",
            agent_reference={"identity_source": "DBOS",
                             "identity_ref": AGENT,
                             "identity_note": "benign nested note"},
            notes="benign top note"))
        env = store.get_event("evt-nested", capability="detail")
        restricted = env["content_channel"]["restricted_text"]
        self.assertIn("agent_reference.identity_note", restricted)
        self.assertIn("notes", restricted)
        facts = env["result"]["structured_facts"]
        self.assertNotIn("identity_note", facts["agent_reference"])
        self.assertNotIn("notes", facts)
        nested = env["result"]["restricted_text"]
        self.assertEqual(nested["agent_reference"]["identity_note"],
                         "benign nested note")


class TestF5InstantTimeWindow(unittest.TestCase):
    def test_mixed_offset_window_filters_by_instant(self):
        store = HistoryStore()
        # 2026-08-02T02:00:00+02:00 == 2026-08-02T00:00:00Z (same instant)
        store.ingest_event(make_event(event_id="evt-off",
                                      occurred_at="2026-08-02T02:00:00+02:00"))
        env = store.query_events(identity_ref=AGENT,
                                 time_start="2026-08-01T23:30:00Z",
                                 time_end="2026-08-02T00:30:00Z")
        ids = [e["event_id"] for e in env["result"]["events"]]
        self.assertIn("evt-off", ids)
        outside = store.query_events(identity_ref=AGENT,
                                     time_start="2026-08-02T01:00:00Z")
        self.assertNotIn("evt-off",
                         [e["event_id"] for e in outside["result"]["events"]])

    def test_ordering_by_instant_not_lexicographic(self):
        store = HistoryStore()
        store.ingest_event(make_event(event_id="evt-z-offset",
                                      occurred_at="2026-08-03T06:00:00+08:00"))
        store.ingest_event(make_event(event_id="evt-utc",
                                      occurred_at="2026-08-02T23:00:00Z"))
        env = store.query_events(identity_ref=AGENT)
        ids = [e["event_id"] for e in env["result"]["events"]]
        # 06:00+08:00 == 22:00Z, which precedes 23:00Z despite sorting after
        # it lexicographically.
        self.assertLess(ids.index("evt-z-offset"), ids.index("evt-utc"))


class TestF6WithheldAddressScoping(unittest.TestCase):
    def test_cross_identity_query_never_sees_withheld_existence(self):
        store = build_store()
        env = store.query_events(identity_ref="did:example:stranger")
        self.assertEqual(env["null_semantics"], NullSemantics.NO_RECORD.value)
        self.assertEqual(env["selective_disclosure"]["withheld_count"], 0)
        summary = store.summary("did:example:stranger")
        self.assertEqual(summary["null_semantics"],
                         NullSemantics.NO_RECORD.value)
        self.assertEqual(summary["result"]["withheld_events"], 0)

    def test_withheld_counted_only_within_addressed_scope(self):
        store = build_store()
        env = store.query_events(identity_ref=AGENT, agent_version="2.0.0")
        self.assertEqual(env["selective_disclosure"]["withheld_count"], 0)
        env1 = store.query_events(identity_ref=AGENT, agent_version="1.0.0")
        self.assertEqual(env1["selective_disclosure"]["withheld_count"], 1)


class TestF9SummaryNullSemantics(unittest.TestCase):
    def test_all_withheld_identity_reports_withheld(self):
        store = HistoryStore()
        store.ingest_event(make_event(
            event_id="evt-only-hidden",
            disclosure={"disclosure_scope": "WITHHELD", "declared_by": "h"}))
        env = store.summary(AGENT)
        self.assertEqual(env["null_semantics"], NullSemantics.WITHHELD.value)
        self.assertEqual(env["result"]["withheld_events"], 1)

    def test_version_scoped_summary_without_matches_is_no_record(self):
        store = build_store()
        env = store.summary(AGENT, agent_version="9.9.9")
        self.assertEqual(env["null_semantics"], NullSemantics.NO_RECORD.value)
        self.assertEqual(env["result"]["by_version"], {})


class TestF10VerificationScopeAggregation(unittest.TestCase):
    def test_evidence_binding_aspect_does_not_verify_event(self):
        store = HistoryStore()
        store.ingest_event(make_event(verification_references=[
            {"verification_id": "ver-test-0001",
             "verifier_name": "named-verifier-1"}]))
        store.ingest_verification(make_verification(scope={
            "subject_event_id": "evt-test-0001",
            "subject_type": "EXPERIENCE_EVENT",
            "covered_aspect": "EVIDENCE_BINDING",
            "agent_ref": AGENT,
            "agent_version": "1.0.0"}))
        self.assertEqual(store.event_verification_status("evt-test-0001"),
                         "NOT_ASSESSED")
        self.assertEqual(
            store.summary(AGENT)["result"]["by_version"]["1.0.0"]
            ["verified_events"], 0)

    def test_evidence_reference_subject_is_not_event_verification(self):
        store = HistoryStore()
        store.ingest_event(make_event(verification_references=[
            {"verification_id": "ver-test-0001",
             "verifier_name": "named-verifier-1"}]))
        store.ingest_verification(make_verification(scope={
            "subject_event_id": "evt-test-0001",
            "subject_type": "EVIDENCE_REFERENCE",
            "covered_aspect": "FULL_EVENT"}))  # R3-3: non-event subject types
        # keep the optional binding (only EXPERIENCE_EVENT requires it).
        self.assertEqual(store.event_verification_status("evt-test-0001"),
                         "NOT_ASSESSED")

    def test_verified_filter_respects_scope(self):
        store = HistoryStore()
        store.ingest_event(make_event(verification_references=[
            {"verification_id": "ver-test-0001",
             "verifier_name": "named-verifier-1"}]))
        store.ingest_verification(make_verification(scope={
            "subject_event_id": "evt-test-0001",
            "subject_type": "EXPERIENCE_EVENT",
            "covered_aspect": "EVIDENCE_BINDING",
            "agent_ref": AGENT,
            "agent_version": "1.0.0"}))
        env = store.query_events(identity_ref=AGENT,
                                 verification_status="VERIFIED")
        self.assertEqual(env["result"]["count"], 0)


class TestIngestFailClosed(unittest.TestCase):
    def test_invalid_event_is_rejected(self):
        store = HistoryStore()
        with self.assertRaises(IngestError):
            store.ingest_event(make_event(score=0.5))
        self.assertEqual(store.summary(AGENT)["null_semantics"],
                         NullSemantics.NO_RECORD.value)

    def test_invalid_verification_is_rejected(self):
        store = HistoryStore()
        bad = make_verification()
        del bad["verifier"]
        with self.assertRaises(IngestError):
            store.ingest_verification(bad)

    def test_duplicate_event_id_rejected(self):
        store = HistoryStore()
        store.ingest_event(make_event())
        with self.assertRaises(ValueError):
            store.ingest_event(make_event())


if __name__ == "__main__":
    unittest.main()

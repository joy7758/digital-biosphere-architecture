"""Trust-boundary and truth-boundary tests for the AHRP internal
orchestrator integration trial (AHRP 内部编排器集成试验 v0.1).

Retained integration coverage (8):
    test_real_orchestrator_queries_history   (programmatic orchestrator
                                              actually calls the query
                                              interface)
    test_decision_change_requires_history_reference
    test_no_history_no_decision_change
    test_query_failure_fail_closed
    test_history_reference_resolves
    test_event_version_binding
    test_verification_binding
    test_no_ahrp_mode_never_reads_history

New truth-boundary coverage (7):
    test_trial_does_not_claim_real_agent
    test_model_based_orchestrator_is_false
    test_autonomous_tool_selection_is_false
    test_voluntary_query_is_not_claimed
    test_real_agent_adoption_remains_false
    test_query_count_is_described_as_configured_behavior
    test_programmatic_integration_claim_is_allowed

Fail-closed query-error coverage (6):
    test_query_error_routes_to_manual_review
    test_query_error_selected_agent_is_none
    test_query_error_does_not_execute_worker
    test_query_error_has_no_execution_artifact
    test_query_error_has_no_experience_event
    test_query_error_has_no_verification_record

History/observation semantic coverage (4):
    test_history_used_requires_real_event_id
    test_no_record_is_query_observation_not_history
    test_query_error_is_query_observation_not_history
    test_history_change_count_excludes_query_error

Total: 25 tests.
"""

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

EXP_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = EXP_ROOT.parent.parent
for path in (str(EXP_ROOT), str(REPO_ROOT), str(REPO_ROOT / "AHRP")):
    if path not in sys.path:
        sys.path.insert(0, path)

import run_trial  # noqa: E402
from orchestrator import (  # noqa: E402
    AhrpAccessForbidden,
    ForbiddenHistoryStore,
    OrchestratorAgent,
)
from validator.core import (  # noqa: E402
    validate_experience_event,
    validate_verification_record,
)

# Unqualified claims that must never appear in trial artifacts
# (assembled from fragments so this test file itself stays clean).
PROHIBITED_CLAIMS = [
    "REAL_AGENT_USED_AHRP" + "=true",
    "REAL_AGENT_TRIAL" + "=true",
    "PHASE1_OBJECTIVE" + "_MET",
    "real agent adoption" + " validated",
]


class IntegrationTrialTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out_root = Path(tempfile.mkdtemp(prefix="integration-trial-test-"))
        cls.summary = run_trial.run_all(out_root=cls.out_root)
        cls.assisted = {}
        for path in sorted((cls.out_root / "decisions" / "ahrp-assisted").glob("*.json")):
            cls.assisted[path.stem] = json.loads(path.read_text(encoding="utf-8"))
        cls.no_ahrp = {}
        for path in sorted((cls.out_root / "decisions" / "no-ahrp").glob("*.json")):
            cls.no_ahrp[path.stem] = json.loads(path.read_text(encoding="utf-8"))
        cls.store = run_trial.build_store()
        for path in sorted((cls.out_root / "events").glob("evt-trial-run-*.json")):
            cls.store.ingest_event(json.loads(path.read_text(encoding="utf-8")))
        for path in sorted((cls.out_root / "events").glob("ver-trial-run-*.json")):
            cls.store.ingest_verification(json.loads(path.read_text(encoding="utf-8")))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.out_root, ignore_errors=True)

    # ------------------------------------------- retained integration tests
    def test_real_orchestrator_queries_history(self):
        """The programmatic orchestrator component actually invokes the AHRP
        query interface on the configured AHRP-assisted path."""
        self.assertGreater(self.summary["counts"]["AHRP_QUERY_COUNT"], 0)
        self.assertTrue(
            self.summary["truth_boundaries"]["PROGRAMMATIC_ORCHESTRATOR_USED_AHRP"])
        for record in self.assisted.values():
            self.assertGreaterEqual(len(record["ahrp_query"]), 1)
            for query in record["ahrp_query"]:
                self.assertIn("ok", query)
                self.assertIn("latency_ms", query)
                self.assertIn("tokens_estimated", query)

    def test_decision_change_requires_history_reference(self):
        """No history-driven programmatic routing change may exist without
        a concrete history reference. Query-error safety overrides are
        excluded: they change the decision without any returned history."""
        changed = [r for r in self.assisted.values()
                   if r["decision_changed"]
                   and not r.get("query_error_safety_override")]
        self.assertGreater(len(changed), 0)
        for record in changed:
            refs = [e for e in record["history_used"] if e["event_id"]]
            self.assertGreater(len(refs), 0,
                               f"{record['task_id']} changed without history")
            veto_reasons = {e["reason"] for e in refs}
            self.assertTrue(
                veto_reasons & {"CAPABILITY_LIMIT_HISTORY",
                                "POLICY_RESTRICTION_HISTORY"},
                f"{record['task_id']} changed without a veto-class reference")

    def test_no_history_no_decision_change(self):
        """All-NO_RECORD queries must never change the delegation decision."""
        record = self.assisted["t-208"]
        semantics = [q["null_semantics"] for q in record["ahrp_query"] if q["ok"]]
        self.assertGreater(len(semantics), 0)
        self.assertTrue(all(s == "NO_RECORD" for s in semantics))
        self.assertFalse(record["decision_changed"])
        for rec in self.assisted.values():
            sem = [q["null_semantics"] for q in rec["ahrp_query"] if q["ok"]]
            if sem and all(s == "NO_RECORD" for s in sem):
                self.assertFalse(rec["decision_changed"],
                                 f"{rec['task_id']} changed on NO_RECORD")

    def test_query_failure_fail_closed(self):
        """A query error envelope blocks automatic delegation entirely
        (fail closed): MANUAL_REVIEW, no selected agent, nothing executed."""
        record = self.assisted["t-210"]
        self.assertTrue(record["ahrp_query"][0]["ok"] is False)
        self.assertTrue(record["ahrp_query"][0]["error_code"].startswith("Q_"))
        self.assertIn("fail_closed", record)
        self.assertTrue(record["query_error_safety_override"])
        self.assertTrue(record["decision_changed"])
        self.assertEqual(record["before_query_decision"]["decision"], "DELEGATE")
        self.assertEqual(record["after_query_decision"]["decision"], "MANUAL_REVIEW")
        self.assertIsNone(record["after_query_decision"]["selected_agent"])
        self.assertEqual(record["result"]["status"], "NOT_EXECUTED")

    def test_history_reference_resolves(self):
        """Every referenced history event resolves in the AHRP store."""
        seen = 0
        for record in self.assisted.values():
            for entry in record["history_used"]:
                if not entry["event_id"]:
                    continue
                envelope = self.store.get_event(entry["event_id"],
                                                capability="summary")
                self.assertTrue(envelope.get("ok"),
                                f"{entry['event_id']} does not resolve")
                self.assertIn("result", envelope)
                seen += 1
        self.assertGreater(seen, 0)

    def test_event_version_binding(self):
        """Verification scope must bind event identity AND agent version."""
        events_dir = self.out_root / "events"
        verifications = sorted(events_dir.glob("ver-trial-run-*.json"))
        self.assertGreater(len(verifications), 0)
        for path in verifications:
            verification = json.loads(path.read_text(encoding="utf-8"))
            scope = verification["scope"]
            event = json.loads(
                (events_dir / f"{scope['subject_event_id']}.json")
                .read_text(encoding="utf-8"))
            self.assertEqual(scope["agent_ref"],
                             event["agent_reference"]["identity_ref"])
            self.assertEqual(scope["agent_version"], event["agent_version"])
            self.assertEqual(scope["covered_aspect"], "FULL_EVENT")
            ref = event["verification_references"][0]
            self.assertEqual(ref["verification_id"],
                             verification["verification_id"])
            self.assertEqual(ref["verifier_name"],
                             verification["verifier"]["verifier_name"])

    def test_verification_binding(self):
        """All produced events and verifications pass the AHRP Validator,
        and no verification claims independent verification."""
        events_dir = self.out_root / "events"
        for path in sorted(events_dir.glob("evt-trial-run-*.json")):
            result = validate_experience_event(
                json.loads(path.read_text(encoding="utf-8")))
            self.assertTrue(result.valid, f"{path.name}: {result.errors}")
        for path in sorted(events_dir.glob("ver-trial-run-*.json")):
            verification = json.loads(path.read_text(encoding="utf-8"))
            result = validate_verification_record(verification)
            self.assertTrue(result.valid, f"{path.name}: {result.errors}")
            self.assertEqual(verification["verifier"]["verifier_class"],
                             "SYSTEM_BENCHMARK")
            self.assertFalse(verification["self_verification"])

    def test_no_ahrp_mode_never_reads_history(self):
        """Baseline records carry no AHRP fields, and any query attempt in
        NO_AHRP_MODE raises."""
        for record in self.no_ahrp.values():
            self.assertNotIn("ahrp_query", record)
            self.assertNotIn("history_used", record)
            for key in ("task_id", "candidate_agents", "selected_agent",
                        "selection_reason", "result"):
                self.assertIn(key, record)
        config = run_trial.load_config()
        registration = next(a for a in config["roster"]["agents"]
                            if a["role"] == "ORCHESTRATOR")
        orchestrator = OrchestratorAgent(
            registration, run_trial.agent_versions(config["roster"]))
        task = next(t for t in config["tasks"]
                    if t["phase"] == "AHRP_ASSISTED_MODE")
        with self.assertRaises(AhrpAccessForbidden):
            orchestrator.select_with_history(task, ForbiddenHistoryStore())

    # ---------------------------------------------- new truth-boundary tests
    def test_trial_does_not_claim_real_agent(self):
        """Full-text scan: no unqualified real-agent claim anywhere in the
        committed trial artifacts (tests/ excluded; this file assembles the
        prohibited strings from fragments)."""
        for path in sorted(EXP_ROOT.rglob("*")):
            if not path.is_file():
                continue
            if "tests" in path.parts or "__pycache__" in path.parts:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore").lower()
            for claim in PROHIBITED_CLAIMS:
                self.assertNotIn(claim.lower(), text,
                                 f"prohibited claim in {path.name}")
        self.assertNotEqual(
            self.summary["truth_boundaries"]["TRIAL_RESULT"],
            "PHASE1_OBJECTIVE" + "_MET")

    def test_model_based_orchestrator_is_false(self):
        self.assertFalse(
            self.summary["truth_boundaries"]["MODEL_BASED_ORCHESTRATOR"])

    def test_autonomous_tool_selection_is_false(self):
        self.assertFalse(
            self.summary["truth_boundaries"]["AUTONOMOUS_TOOL_SELECTION"])

    def test_voluntary_query_is_not_claimed(self):
        self.assertFalse(
            self.summary["truth_boundaries"]["VOLUNTARY_AHRP_QUERY_VALIDATED"])

    def test_real_agent_adoption_remains_false(self):
        truth = self.summary["truth_boundaries"]
        self.assertFalse(truth["REAL_AGENT_ADOPTION_VALIDATED"])
        self.assertFalse(truth["REAL_EXTERNAL_AGENT"])
        self.assertFalse(truth["REAL_HUMAN_ORCHESTRATOR"])
        unsupported = self.summary["unsupported_claims"]
        self.assertFalse(unsupported["REAL_WORLD_ADOPTION_VALIDATED"])
        self.assertFalse(unsupported["AGENT_VOLUNTARILY_ADOPTED_AHRP"])

    def test_query_count_is_described_as_configured_behavior(self):
        note = self.summary["counts"]["AHRP_QUERY_COUNT_NOTE"]
        self.assertIn("configured AHRP-assisted execution path", note)
        self.assertIn("not evidence", note)
        change_note = self.summary["counts"][
            "PROGRAMMATIC_HISTORY_DECISION_CHANGED_NOTE"]
        self.assertIn("PROGRAMMATIC_ROUTING_CHANGE_OBSERVATION", change_note)
        override_note = self.summary["counts"]["QUERY_ERROR_SAFETY_OVERRIDE_NOTE"]
        self.assertIn("NOT a history-driven decision change", override_note)

    def test_programmatic_integration_claim_is_allowed(self):
        truth = self.summary["truth_boundaries"]
        self.assertTrue(truth["INTERNAL_EXECUTABLE_INTEGRATION_TRIAL"])
        self.assertTrue(truth["INTEGRATION_MECHANISM_DEMONSTRATED"])
        self.assertEqual(truth["TRIAL_RESULT"], "INCONCLUSIVE")
        supported = self.summary["supported_findings"]
        self.assertTrue(supported["AHRP_QUERY_INTERFACE_INTEGRATED"])
        self.assertTrue(supported["HISTORY_BOUND_TO_DECISION_RECORD"])
        self.assertTrue(supported["QUERY_FAILURE_FAIL_CLOSED"])

    # --------------------------------------- fail-closed query-error tests
    def test_query_error_routes_to_manual_review(self):
        record = self.assisted["t-210"]
        self.assertEqual(record["after_query_decision"]["decision"],
                         "MANUAL_REVIEW")
        self.assertIn("AHRP_QUERY_ERROR",
                      record["after_query_decision"]["selection_reason"])

    def test_query_error_selected_agent_is_none(self):
        record = self.assisted["t-210"]
        self.assertIsNone(record["after_query_decision"]["selected_agent"])

    def test_query_error_does_not_execute_worker(self):
        record = self.assisted["t-210"]
        self.assertEqual(record["result"]["status"], "NOT_EXECUTED")
        self.assertNotEqual(record["result"]["status"], "SUCCESS")
        self.assertNotEqual(record["result"]["status"], "FAILURE")

    def test_query_error_has_no_execution_artifact(self):
        record = self.assisted["t-210"]
        self.assertEqual(record["result"]["artifact_paths"], [])
        artifact_dir = self.out_root / "evidence" / "artifacts" / "t-210"
        if artifact_dir.exists():
            self.assertEqual(list(artifact_dir.iterdir()), [])

    def test_query_error_has_no_experience_event(self):
        event_path = self.out_root / "events" / "evt-trial-run-t-210.json"
        self.assertFalse(event_path.exists())

    def test_query_error_has_no_verification_record(self):
        ver_path = self.out_root / "events" / "ver-trial-run-t-210.json"
        self.assertFalse(ver_path.exists())

    # ------------------------------------- history/observation semantic tests
    def test_history_used_requires_real_event_id(self):
        """history_used may only contain references to actual Experience
        Events; event_id must never be null."""
        for record in self.assisted.values():
            for entry in record["history_used"]:
                self.assertIsNotNone(
                    entry["event_id"],
                    f"{record['task_id']}: null event_id in history_used")

    def test_no_record_is_query_observation_not_history(self):
        """Queries that returned no event surface as query_observations,
        never as history_used entries."""
        observed = 0
        for record in self.assisted.values():
            for query in record["ahrp_query"]:
                if query.get("ok") and query.get("events_returned") == 0:
                    observed += 1
            reasons = {e.get("reason") for e in record["history_used"]}
            self.assertNotIn("NO_RECORD", reasons,
                             f"{record['task_id']}: NO_RECORD in history_used")
        observations = [o for r in self.assisted.values()
                        for o in r["query_observations"]
                        if o["outcome"] == "NO_RECORD"]
        self.assertGreater(len(observations), 0)

    def test_query_error_is_query_observation_not_history(self):
        record = self.assisted["t-210"]
        self.assertEqual(record["history_used"], [])
        observations = record["query_observations"]
        self.assertGreater(len(observations), 0)
        error_obs = [o for o in observations if o["outcome"] == "QUERY_ERROR"]
        self.assertGreater(len(error_obs), 0)
        self.assertTrue(error_obs[0]["error_code"].startswith("Q_"))

    def test_history_change_count_excludes_query_error(self):
        counts = self.summary["counts"]
        history_tasks = counts["PROGRAMMATIC_HISTORY_DECISION_CHANGED_TASKS"]
        override_tasks = counts["QUERY_ERROR_SAFETY_OVERRIDE_TASKS"]
        self.assertEqual(counts["PROGRAMMATIC_HISTORY_DECISION_CHANGED_COUNT"],
                         len(history_tasks))
        self.assertEqual(counts["QUERY_ERROR_SAFETY_OVERRIDE_COUNT"],
                         len(override_tasks))
        self.assertEqual(counts["TOTAL_POST_QUERY_DECISION_CHANGED_COUNT"],
                         len(history_tasks) + len(override_tasks))
        self.assertNotIn("t-210", history_tasks)
        self.assertIn("t-210", override_tasks)
        self.assertTrue(self.summary["supported_findings"][
            "PROGRAMMATIC_DECISION_CHANGED_BY_HISTORY"])


if __name__ == "__main__":
    unittest.main()

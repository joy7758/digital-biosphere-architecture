"""Trust-boundary regression tests for the PR #13 fix (15 methods).

These tests lock in the fail-closed dispatch semantics:

* NO_RECORD / WITHHELD / QUERY_ERROR are UNKNOWN states, never CLEAN;
* alternatives are dispatchable only when OK and non-vetoed;
* blocked / manual-review tasks never execute the worker and never produce
  experience events or verification records;
* the runner emits no verification of any kind;
* the post-run SYSTEM_BENCHMARK verifier recomputes results and detects
  tampering;
* every generated event / verification passes the real AHRP Validator with
  complete binding.

Run from the experiment directory:

    python3 -m unittest discover -s tests -v     # Ran 35 tests / OK total
"""

import copy
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
EXPERIMENT_DIR = os.path.abspath(os.path.join(HERE, ".."))
if EXPERIMENT_DIR not in sys.path:
    sys.path.insert(0, EXPERIMENT_DIR)

import history_loader  # noqa: E402
import run_experiment  # noqa: E402
import verify_run_records  # noqa: E402
import worker  # noqa: E402
import test_method_v2  # noqa: E402

DATA = test_method_v2.DATA
CONFIG = test_method_v2.CONFIG
ensure_run_data = test_method_v2.ensure_run_data

MATRIX_PATH = os.path.join(CONFIG, "capability-matrix.json")


def setUpModule():  # noqa: N802 (unittest hook)
    ensure_run_data()


def load(name):
    return history_loader.load_jsonl(os.path.join(DATA, name))


def allocation(task_id):
    return next(a for a in load("allocations.jsonl")
                if a["task_id"] == task_id)


def post_record(task_id):
    return next(p for p in load("post-query-decisions.jsonl")
                if p["task_id"] == task_id)


class TrustBoundaryTests(unittest.TestCase):

    # --------------------------------------- 1. HIGH + NO_RECORD -> BLOCK
    def test_high_risk_no_record_is_blocked(self):
        """task-m2-018: HIGH risk, initial agent NO_RECORD, every
        alternative unknown -> BLOCK without execution."""
        alloc = allocation("task-m2-018")
        self.assertEqual(alloc["risk_level"], "HIGH")
        self.assertEqual(alloc["disposition"], "BLOCK")
        self.assertIsNone(alloc["final_agent"])
        self.assertIn("NO_RECORD", alloc["decision_reason"])
        executed = {e["task_id"] for e in load("controlled-executions.jsonl")}
        self.assertNotIn("task-m2-018", executed)

    # --------------------------------------- 2. HIGH + WITHHELD never kept
    def test_high_risk_withheld_is_blocked(self):
        """WITHHELD means RECORD_EXISTS_BUT_NOT_DISCLOSED: the withheld
        initial agent must never be the dispatched agent on a HIGH task."""
        queries = load("queries.jsonl")
        for alloc in load("allocations.jsonl"):
            if alloc["arm"] != "AHRP-assisted" or \
                    alloc["risk_level"] != "HIGH":
                continue
            withheld_initial = any(
                q["task_id"] == alloc["task_id"] and
                q["purpose"] == "initial-agent-screen" and
                q["null_semantics"] == "WITHHELD"
                for q in queries)
            if withheld_initial:
                self.assertNotEqual(
                    alloc["final_agent"], alloc["initial_agent"],
                    f"{alloc['task_id']}: WITHHELD initial agent was kept")

    # --------------------------------------- 3. HIGH + QUERY_ERROR -> BLOCK
    def test_high_risk_query_error_is_blocked(self):
        """task-m2-032: controlled Q_INVALID_ENUM injection. HIGH risk +
        query error must BLOCK; worker invocations do not increase."""
        alloc = allocation("task-m2-032")
        self.assertEqual(alloc["risk_level"], "HIGH")
        self.assertEqual(alloc["disposition"], "BLOCK")
        self.assertIsNone(alloc["final_agent"])
        self.assertIn("QUERY_ERROR", alloc["decision_reason"])
        error_queries = [q for q in load("queries.jsonl")
                         if q["task_id"] == "task-m2-032" and
                         q["query_mode"] == "SummaryList"]
        self.assertTrue(error_queries)
        self.assertTrue(all(not q["ok"] for q in error_queries))
        self.assertTrue(any((q.get("error_code") or "").startswith("Q_")
                            for q in error_queries))
        executed = {e["task_id"] for e in load("controlled-executions.jsonl")}
        self.assertNotIn("task-m2-032", executed)
        evidence_path = os.path.join(EXPERIMENT_DIR, "evidence",
                                     "executions", "task-m2-032.json")
        self.assertFalse(os.path.exists(evidence_path))

    # --------------------------------------- 4. MEDIUM unknown -> REVIEW
    def test_medium_risk_unknown_requires_manual_review(self):
        """task-m2-006 / task-m2-024: MEDIUM risk with no known candidate
        becomes MANUAL_REVIEW and is never auto-executed."""
        for task_id in ("task-m2-006", "task-m2-024"):
            alloc = allocation(task_id)
            self.assertEqual(alloc["risk_level"], "MEDIUM")
            self.assertEqual(alloc["disposition"], "MANUAL_REVIEW")
            self.assertIsNone(alloc["final_agent"])
            self.assertIn("NO_AUTO_EXECUTION_WITHOUT_HUMAN_APPROVAL",
                          alloc["decision_reason"])
        executed = {e["task_id"] for e in load("controlled-executions.jsonl")}
        self.assertNotIn("task-m2-006", executed)
        self.assertNotIn("task-m2-024", executed)

    # --------------------------------------- 5. LOW exploration gating
    def test_low_risk_cold_start_requires_sandbox_flags(self):
        """Complete flags -> LOW_RISK_EXPLORATION; incomplete -> BLOCK."""
        explored = allocation("task-m2-030")
        self.assertEqual(explored["disposition"], "LOW_RISK_EXPLORATION")
        self.assertIsNotNone(explored["final_agent"])
        blocked = allocation("task-m2-028")
        self.assertEqual(blocked["disposition"], "BLOCK")
        self.assertIsNone(blocked["final_agent"])
        self.assertIn("SANDBOX_FLAGS_INCOMPLETE", blocked["decision_reason"])
        tasks = {t["task_id"]: t for t in history_loader.load_jsonl(
            os.path.join(CONFIG, "tasks.jsonl"))}
        for flag in run_experiment.EXPLORATION_FLAGS:
            self.assertTrue(tasks["task-m2-030"].get(flag) is True)
            self.assertFalse(tasks["task-m2-028"].get(flag) is True)

    # --------------------------------------- 6. NO alternative is "clean"
    def test_alternative_no_record_is_not_clean(self):
        """ALTERNATIVE_NO_RECORD_CLEAN must be gone from code and data."""
        with open(os.path.join(EXPERIMENT_DIR, "run_experiment.py"),
                  encoding="utf-8") as handle:
            runner_source = handle.read()
        self.assertNotIn("ALTERNATIVE_NO_RECORD_CLEAN", runner_source)
        self.assertIn("KNOWN_NON_VETOED_ALTERNATIVE", runner_source)
        self.assertIn("NO_KNOWN_ALTERNATIVE", runner_source)
        for name in ("allocations.jsonl", "post-query-decisions.jsonl",
                     "non-dispatched-tasks.jsonl"):
            for record in load(name):
                blob = json.dumps(record)
                self.assertNotIn("ALTERNATIVE_NO_RECORD_CLEAN", blob)
        # Every KNOWN_NON_VETOED_ALTERNATIVE dispatch must rest on a real OK
        # query for the finally selected agent.
        queries = load("queries.jsonl")
        for alloc in load("allocations.jsonl"):
            if "KNOWN_NON_VETOED_ALTERNATIVE" not in alloc["decision_reason"]:
                continue
            ok_queries = [q for q in queries
                          if q["task_id"] == alloc["task_id"] and
                          q["identity_ref"] == alloc["final_agent"] and
                          q["query_mode"] == "SummaryList" and
                          q["ok"] and (q["event_count"] or 0) > 0]
            self.assertTrue(
                ok_queries,
                f"{alloc['task_id']}: alternative dispatched without an OK "
                "query for the selected agent")

    # --------------------------------------- 7. blocked never runs worker
    def test_blocked_task_does_not_execute_worker(self):
        nondispatched = load("non-dispatched-tasks.jsonl")
        self.assertTrue(nondispatched)
        executed = {e["task_id"] for e in load("controlled-executions.jsonl")}
        for record in nondispatched:
            self.assertIn(record["disposition"], ("BLOCK", "MANUAL_REVIEW"))
            self.assertNotIn(record["task_id"], executed)
            evidence_path = os.path.join(
                EXPERIMENT_DIR, "evidence", "executions",
                f"{record['task_id']}.json")
            self.assertFalse(os.path.exists(evidence_path),
                             f"{record['task_id']} has fake execution "
                             "evidence")

    # --------------------------------------- 8. blocked produces no events
    def test_blocked_task_has_no_experience_event(self):
        nondispatched = load("non-dispatched-tasks.jsonl")
        unverified_ids = {e["event_id"] for e in
                          load("experience-events-unverified.jsonl")}
        final_ids = {e["event_id"] for e in load("experience-events.jsonl")}
        verification_ids = {v["scope"]["subject_event_id"] for v in
                            load("verification-records.jsonl")}
        for record in nondispatched:
            event_id = f"evt-run-{record['task_id']}"
            self.assertNotIn(event_id, unverified_ids)
            self.assertNotIn(event_id, final_ids)
            self.assertNotIn(event_id, verification_ids)

    # --------------------------------------- 9. runner emits no verification
    def test_runner_does_not_emit_independent_verification(self):
        with open(os.path.join(EXPERIMENT_DIR, "run_experiment.py"),
                  encoding="utf-8") as handle:
            runner_source = handle.read()
        self.assertNotIn("INDEPENDENT_AGENT", runner_source)
        self.assertNotIn("verification_writer", runner_source)
        self.assertNotIn("verifier_class", runner_source)
        for event in load("experience-events-unverified.jsonl"):
            self.assertEqual(event["verification_references"], [],
                             f"{event['event_id']}: runner must not claim "
                             "verification")

    # --------------------------------------- 10. recomputation agrees
    def test_post_run_verifier_recomputes_worker_result(self):
        matrix = json.load(open(MATRIX_PATH, encoding="utf-8"))
        tasks = {t["task_id"]: t for t in history_loader.load_jsonl(
            os.path.join(CONFIG, "tasks.jsonl"))}
        for execution in load("controlled-executions.jsonl"):
            status, category, _rule = worker.execute_task(
                tasks[execution["task_id"]], execution["selected_agent"],
                matrix)
            self.assertEqual(status, execution["result_status"],
                             f"{execution['task_id']}: recorded result is "
                             "not reproducible")
            self.assertEqual(category, execution["failure_category"])

    # --------------------------------------- 11. result tampering detected
    def test_post_run_verifier_detects_result_tampering(self):
        matrix = json.load(open(MATRIX_PATH, encoding="utf-8"))
        with open(os.path.join(CONFIG, "capability-matrix.commitment"),
                  encoding="utf-8") as handle:
            committed = handle.read().strip().split()[0]
        tasks = {t["task_id"]: t for t in history_loader.load_jsonl(
            os.path.join(CONFIG, "tasks.jsonl"))}
        executions = load("controlled-executions.jsonl")
        events = load("experience-events-unverified.jsonl")
        baseline, _ = verify_run_records.recompute_and_compare(
            tasks, matrix, verify_run_records.file_sha256(MATRIX_PATH),
            committed, executions, events)
        self.assertEqual(baseline, [])
        tampered = copy.deepcopy(executions)
        tampered[0]["result_status"] = \
            "SUCCESS" if tampered[0]["result_status"] != "SUCCESS" \
            else "FAILURE"
        problems, _ = verify_run_records.recompute_and_compare(
            tasks, matrix, verify_run_records.file_sha256(MATRIX_PATH),
            committed, tampered, events)
        self.assertTrue(problems)

    # --------------------------------------- 12. evidence tampering detected
    def test_post_run_verifier_detects_evidence_tampering(self):
        matrix = json.load(open(MATRIX_PATH, encoding="utf-8"))
        with open(os.path.join(CONFIG, "capability-matrix.commitment"),
                  encoding="utf-8") as handle:
            committed = handle.read().strip().split()[0]
        tasks = {t["task_id"]: t for t in history_loader.load_jsonl(
            os.path.join(CONFIG, "tasks.jsonl"))}
        executions = load("controlled-executions.jsonl")
        events = copy.deepcopy(load("experience-events-unverified.jsonl"))
        events[0]["evidence_references"][0]["hash"] = "sha256:" + "0" * 64
        problems, _ = verify_run_records.recompute_and_compare(
            tasks, matrix, verify_run_records.file_sha256(MATRIX_PATH),
            committed, executions, events)
        self.assertTrue(any("hash mismatch" in p for p in problems))

    # --------------------------------------- 13. events pass AHRP validator
    def test_all_generated_events_pass_ahrp_validator(self):
        validate_event, _ = verify_run_records.load_validator()
        events = load("experience-events.jsonl")
        self.assertTrue(events)
        for event in events:
            result = validate_event(event)
            self.assertTrue(result.valid,
                            f"{event['event_id']}: {result.errors}")

    # --------------------------------------- 14. verifications pass validator
    def test_all_generated_verifications_pass_ahrp_validator(self):
        _, validate_verification = verify_run_records.load_validator()
        records = load("verification-records.jsonl")
        self.assertTrue(records)
        for record in records:
            self.assertEqual(record["verifier"]["verifier_class"],
                             "SYSTEM_BENCHMARK")
            self.assertEqual(record["verifier"]["verifier_name"],
                             "method-v2-post-run-verifier")
            result = validate_verification(record)
            self.assertTrue(result.valid,
                            f"{record['verification_id']}: {result.errors}")

    # --------------------------------------- 15. binding complete
    def test_generated_event_verification_binding_complete(self):
        events = {e["event_id"]: e for e in load("experience-events.jsonl")}
        records = load("verification-records.jsonl")
        self.assertEqual(len(events), len(records))
        for record in records:
            scope = record["scope"]
            event = events.get(scope["subject_event_id"])
            self.assertIsNotNone(event,
                                 f"{record['verification_id']}: dangling "
                                 "subject_event_id")
            self.assertEqual(scope["subject_type"], "EXPERIENCE_EVENT")
            self.assertEqual(scope["agent_ref"],
                             event["agent_reference"]["identity_ref"])
            self.assertEqual(scope["agent_version"], event["agent_version"])
            self.assertEqual(scope["covered_aspect"], "FULL_EVENT")
            reference = event["verification_references"][0]
            self.assertEqual(reference["verification_id"],
                             record["verification_id"])
            self.assertEqual(reference["verifier_name"],
                             record["verifier"]["verifier_name"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

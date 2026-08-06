"""Independent enumerable tests for the method-v2 experiment (20 methods).

Run from the experiment directory:

    python3 -m unittest discover -s tests -v

This file keeps the original 20 integrity tests; the 15 trust-boundary
regression tests added by the PR #13 fix live in
``test_trust_boundaries.py`` (35 tests total).
"""

import copy
import hashlib
import inspect
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
EXPERIMENT_DIR = os.path.abspath(os.path.join(HERE, ".."))
if EXPERIMENT_DIR not in sys.path:
    sys.path.insert(0, EXPERIMENT_DIR)

import analyze_experiment  # noqa: E402
import history_loader  # noqa: E402
import run_experiment  # noqa: E402
import validate_shadow_protocol  # noqa: E402
import verify_evidence_references  # noqa: E402
import worker  # noqa: E402

CONFIG = os.path.join(EXPERIMENT_DIR, "config")
DATA = os.path.join(EXPERIMENT_DIR, "data")
FORBIDDEN = ("expected_outcome", "forced_result", "desired_result")


def ensure_run_data():
    executions = os.path.join(DATA, "controlled-executions.jsonl")
    if not (os.path.isfile(executions) and os.path.getsize(executions) > 0):
        run_experiment.main()
    if not os.path.isfile(os.path.join(DATA, "experience-events.jsonl")):
        import verify_run_records
        if verify_run_records.main() != 0:
            raise AssertionError("post-run verifier failed")
    comparison = os.path.join(EXPERIMENT_DIR, "analysis", "comparison.json")
    if not os.path.isfile(comparison):
        analyze_experiment.main()


def setUpModule():  # noqa: N802 (unittest hook)
    ensure_run_data()


class MethodV2IntegrityTests(unittest.TestCase):

    # ------------------------------------------------------------- fixtures
    def _tasks(self):
        return history_loader.load_jsonl(os.path.join(CONFIG, "tasks.jsonl"))

    def _matrix(self):
        with open(os.path.join(CONFIG, "capability-matrix.json"),
                  encoding="utf-8") as handle:
            return json.load(handle)

    def _data(self, name):
        return history_loader.load_jsonl(os.path.join(DATA, name))

    # ------------------------------------------------------- 1. task purity
    def test_tasks_do_not_contain_expected_outcome(self):
        """No task may predetermine its own result."""
        tasks = self._tasks()
        self.assertEqual(len(tasks), 32)
        for task in tasks:
            for field in FORBIDDEN:
                self.assertNotIn(field, task,
                                 f"{task['task_id']} carries {field}")
            self.assertIn("requirements", task)

    # -------------------------------------------------- 2. worker arm-blind
    def test_worker_does_not_read_experiment_arm(self):
        source = inspect.getsource(worker)
        self.assertNotIn("experiment_arm", source)
        self.assertNotIn("ahrp_enabled", source)
        task = self._tasks()[0]
        annotated = copy.deepcopy(task)
        annotated["arm"] = "AHRP-assisted"
        base = worker.execute_task(task, "did:example:worker-alpha",
                                   self._matrix())
        changed = worker.execute_task(annotated, "did:example:worker-alpha",
                                      self._matrix())
        self.assertEqual(base, changed)

    # ------------------------------------------ 3. worker decision-blind
    def test_worker_does_not_read_decision_changed(self):
        source = inspect.getsource(worker)
        self.assertNotIn("decision_changed", source)
        task = self._tasks()[0]
        annotated = copy.deepcopy(task)
        annotated["decision_changed"] = True
        annotated["desired_result"] = "SUCCESS"
        base = worker.execute_task(task, "did:example:worker-alpha",
                                   self._matrix())
        changed = worker.execute_task(annotated, "did:example:worker-alpha",
                                      self._matrix())
        self.assertEqual(base, changed)

    # ------------------------------------------------- 4. no forced success
    def test_no_forced_success_logic(self):
        """No code path may rewrite an execution result after the fact."""
        with open(os.path.join(EXPERIMENT_DIR, "run_experiment.py"),
                  encoding="utf-8") as handle:
            source = handle.read()
        self.assertIn("FORBIDDEN_TASK_FIELDS", source)
        # The PR #12 fabrication pattern must not exist anywhere.
        self.assertNotIn('outcome in ["FAILURE", "TIMEOUT"]', source)
        self.assertNotIn("decision_changed and outcome", source)
        # Functional proof: a capability-insufficient task stays FAILURE.
        task = next(t for t in self._tasks() if t["task_id"] == "task-m2-011")
        status, category, _rule = worker.execute_task(
            task, "did:example:worker-alpha", self._matrix())
        self.assertEqual(status, "FAILURE")
        self.assertEqual(category, "CAPABILITY_LIMIT")

    # --------------------------------------------- 5. envelope parsing
    def test_history_store_envelope_parsing(self):
        store = history_loader.build_store()
        envelope = store.query_events(
            identity_ref="did:example:worker-alpha",
            agent_version="1.0.0", task_type="CODING",
            require_independent_verification=True)
        self.assertTrue(envelope["ok"])
        self.assertIn("null_semantics", envelope)
        events = envelope["result"]["events"]
        self.assertTrue(events)
        for event in events:
            self.assertIsInstance(event, dict)
            self.assertIn("event_id", event)
        outcome = history_loader.query_agent_history(
            store, "did:example:worker-alpha", "1.0.0", "CODING")
        self.assertEqual(outcome.status, "OK")
        self.assertEqual(len(outcome.events), len(events))

    # ------------------------------------------------- 6. error fail-closed
    def test_query_error_fail_closed(self):
        store = history_loader.build_store()
        outcome = history_loader.query_agent_history(
            store, "did:example:worker-alpha", "1.0.0", "NOT_A_TYPE")
        self.assertEqual(outcome.status, "QUERY_ERROR")
        self.assertEqual(outcome.events, [])
        self.assertTrue(outcome.error_code.startswith("Q_"))

    # --------------------------------------------- 7. NO_RECORD is kept
    def test_no_record_not_safe(self):
        """Empty history must NOT trigger a compensating decision change.

        task-m2-030 (LOW, complete sandbox flags) sees NO_RECORD for its
        initial agent; the policy keeps the initial selection as a
        LOW_RISK_EXPLORATION decision -- never an invented alternative.
        """
        store = history_loader.build_store()
        outcome = history_loader.query_agent_history(
            store, "did:example:worker-gamma", "1.0.0", "RESEARCH")
        self.assertEqual(outcome.status, "NO_RECORD")
        post_records = self._data("post-query-decisions.jsonl")
        record = next(r for r in post_records
                      if r["task_id"] == "task-m2-030")
        self.assertIn("NO_RECORD", record["selection_reason_after_query"])
        self.assertIn("LOW_RISK_EXPLORATION",
                      record["selection_reason_after_query"])
        self.assertFalse(record["decision_changed"])

    # --------------------------------------------- 8. commitment intact
    def test_capability_commitment_matches(self):
        matrix_path = os.path.join(CONFIG, "capability-matrix.json")
        with open(os.path.join(CONFIG, "capability-matrix.commitment"),
                  encoding="utf-8") as handle:
            committed = handle.read().strip().split()[0]
        actual = hashlib.sha256(
            open(matrix_path, "rb").read()).hexdigest()
        self.assertEqual(committed, actual)

    # --------------------------------------------- 9. determinism
    def test_same_input_is_deterministic(self):
        matrix = self._matrix()
        for task in self._tasks()[:5]:
            for agent in task["candidate_agents"]:
                first = worker.execute_task(task, agent, matrix)
                second = worker.execute_task(task, agent, matrix)
                self.assertEqual(first, second)

    # --------------------------------------- 10. pre-query persisted first
    def test_pre_query_fsync_before_query(self):
        pre_records = {r["task_id"]: r
                       for r in self._data("pre-query-decisions.jsonl")}
        queries = self._data("queries.jsonl")
        self.assertTrue(queries)
        for query in queries:
            pre = pre_records[query["task_id"]]
            self.assertTrue(query["query_started_after_pre_query"])
            self.assertLessEqual(pre["recorded_at"], query["recorded_at"])

    # --------------------------------------- 11. post binds pre hash
    def test_post_query_binds_pre_hash(self):
        pre_records = {r["task_id"]: r
                       for r in self._data("pre-query-decisions.jsonl")}
        for post in self._data("post-query-decisions.jsonl"):
            pre = pre_records[post["task_id"]]
            recomputed = validate_shadow_protocol.canonical_hash(pre)
            self.assertEqual(recomputed, pre["record_hash"])
            self.assertEqual(post["pre_query_record_hash"],
                             pre["record_hash"])
            self.assertEqual(
                validate_shadow_protocol.canonical_hash(post),
                post["record_hash"])

    # --------------------------------------- 12. tampering detected
    def test_hash_tampering_detected(self):
        pre_records = self._data("pre-query-decisions.jsonl")
        post_records = self._data("post-query-decisions.jsonl")
        queries = self._data("queries.jsonl")
        known = {e["event_id"] for e in history_loader.load_jsonl(
            os.path.join(CONFIG, "history-events.jsonl"))}
        baseline = validate_shadow_protocol.validate(
            pre_records, post_records, queries, self._tasks(), known)
        self.assertEqual(baseline, [])
        mutated = copy.deepcopy(pre_records)
        mutated[0]["selected_agent_before_query"] = "did:example:evil"
        problems = validate_shadow_protocol.validate(
            mutated, post_records, queries, self._tasks(), known)
        self.assertTrue(problems)

    # --------------------------------------- 13. metrics from raw data
    def test_metrics_recomputed_from_raw_data(self):
        executions = self._data("controlled-executions.jsonl")
        allocations = self._data("allocations.jsonl")
        arm_tasks = {"No-AHRP": 0, "AHRP-assisted": 0}
        for allocation in allocations:
            arm_tasks[allocation["arm"]] += 1
        self.assertEqual(arm_tasks["No-AHRP"], 16)
        self.assertEqual(arm_tasks["AHRP-assisted"], 16)
        with open(os.path.join(EXPERIMENT_DIR, "analysis",
                               "no-ahrp-arm.json"),
                  encoding="utf-8") as handle:
            reported = json.load(handle)
        recounted = {}
        for execution in executions:
            if execution["arm"] != "No-AHRP":
                continue
            recounted[execution["result_status"]] = \
                recounted.get(execution["result_status"], 0) + 1
        for status in ("SUCCESS", "FAILURE", "TIMEOUT", "CANCELLED"):
            self.assertEqual(reported.get(status, 0),
                             recounted.get(status, 0))
        # The No-AHRP baseline arm executes every submitted task.
        self.assertEqual(reported["tasks"], arm_tasks["No-AHRP"])

    # --------------------------------------- 14. deletion detected
    def test_missing_record_reduces_completeness(self):
        pre_records = self._data("pre-query-decisions.jsonl")
        post_records = self._data("post-query-decisions.jsonl")
        queries = self._data("queries.jsonl")
        known = {e["event_id"] for e in history_loader.load_jsonl(
            os.path.join(CONFIG, "history-events.jsonl"))}
        deleted = pre_records[1:]
        problems = validate_shadow_protocol.validate(
            deleted, post_records, queries, self._tasks(), known)
        self.assertTrue(problems)

    # --------------------------------------- 15. temporal order enforced
    def test_timestamp_order_violation_detected(self):
        pre_records = self._data("pre-query-decisions.jsonl")
        post_records = self._data("post-query-decisions.jsonl")
        queries = self._data("queries.jsonl")
        known = {e["event_id"] for e in history_loader.load_jsonl(
            os.path.join(CONFIG, "history-events.jsonl"))}
        mutated = copy.deepcopy(post_records)
        target = next(r for r in mutated if r.get("query_window"))
        target["query_window"]["started_at"] = "2020-01-01T00:00:00Z"
        problems = validate_shadow_protocol.validate(
            pre_records, mutated, queries, self._tasks(), known)
        self.assertTrue(any("temporal order" in p for p in problems))

    # --------------------------------------- 16. evidence path resolution
    def test_evidence_path_resolves(self):
        execution_path = verify_evidence_references.resolve_reference(
            "exec-task-m2-001")
        seed_path = verify_evidence_references.resolve_reference(
            "ev-seed-alpha-coding-001")
        self.assertTrue(execution_path.startswith(
            verify_evidence_references.EVIDENCE_ROOT))
        self.assertTrue(seed_path.startswith(
            verify_evidence_references.EVIDENCE_ROOT))
        self.assertTrue(os.path.isfile(execution_path))
        self.assertTrue(os.path.isfile(seed_path))

    # --------------------------------------- 17. evidence hashes match
    def test_evidence_hash_matches(self):
        problems = []
        seen = {}
        seed_events = history_loader.load_jsonl(
            os.path.join(CONFIG, "history-events.jsonl"))
        run_events = self._data("experience-events.jsonl")
        verify_evidence_references.check_events(seed_events, "seed",
                                                problems, seen)
        verify_evidence_references.check_events(run_events, "run",
                                                problems, seen)
        self.assertEqual(problems, [])
        # Exactly one final event per executed task; blocked tasks have none.
        executions = self._data("controlled-executions.jsonl")
        self.assertEqual(len(run_events), len(executions))

    # --------------------------------------- 18. placeholders rejected
    def test_placeholder_hash_rejected(self):
        fake_event = {
            "event_id": "evt-fake-placeholder",
            "evidence_references": [
                {"reference_id": "ev-seed-alpha-coding-001",
                 "hash": "sha256:" + "ab" * 32},
            ],
        }
        shared_event = {
            "event_id": "evt-fake-shared",
            "evidence_references": [
                {"reference_id": "ev-seed-alpha-coding-001",
                 "hash": "sha256:e63214f3aff7b54bdb4353412427b7a5ea9e6194"
                         "93278eb07a3990227a43092b"},
                {"reference_id": "ev-seed-alpha-coding-002",
                 "hash": "sha256:e63214f3aff7b54bdb4353412427b7a5ea9e6194"
                         "93278eb07a3990227a43092b"},
            ],
        }
        problems = []
        seen = {}
        verify_evidence_references.check_events([fake_event], "fake",
                                                problems, seen)
        verify_evidence_references.check_events([shared_event], "shared",
                                                problems, seen)
        self.assertTrue(any("hash mismatch" in p for p in problems))
        self.assertTrue(any("duplicate hash reused" in p for p in problems))

    # --------------------------------------- 19. verification binding
    def test_verification_binding_complete(self):
        verifications = history_loader.load_jsonl(
            os.path.join(CONFIG, "history-verifications.jsonl"))
        self.assertTrue(verifications)
        for record in verifications:
            scope = record["scope"]
            self.assertEqual(scope["subject_type"], "EXPERIENCE_EVENT")
            self.assertIn("agent_ref", scope)
            self.assertIn("agent_version", scope)
            self.assertIn("covered_aspect", scope)
            if record["verifier"]["verifier_class"] == "SELF":
                self.assertTrue(record["self_verification"])
            else:
                self.assertFalse(record["self_verification"])
        # SELF-only event must NOT satisfy independent verification.
        store = history_loader.build_store()
        outcome = history_loader.query_agent_history(
            store, "did:example:worker-gamma", "1.0.0", "RESEARCH")
        self.assertEqual(outcome.status, "NO_RECORD")

    # --------------------------------------- 20. arm cannot change result
    def test_arm_does_not_change_worker_result(self):
        matrix = self._matrix()
        task = next(t for t in self._tasks() if t["task_id"] == "task-m2-012")
        result_no_ahrp = worker.execute_task(
            task, "did:example:worker-gamma", matrix)
        annotated = copy.deepcopy(task)
        annotated["arm"] = "AHRP-assisted"
        annotated["experiment_arm"] = "AHRP-assisted"
        result_ahrp = worker.execute_task(
            annotated, "did:example:worker-gamma", matrix)
        self.assertEqual(result_no_ahrp, result_ahrp)
        self.assertEqual(result_no_ahrp[0], "FAILURE")


if __name__ == "__main__":
    unittest.main(verbosity=2)

import unittest
import json
import os

class TestExperimentIntegrity(unittest.TestCase):
    def setUp(self):
        self.data_dir = "experiments/ahrp-pilot-readiness-v0.2-method-fix/data"

    def test_no_expected_outcome_in_tasks(self):
        with open(f"{self.data_dir}/tasks.jsonl", "r") as f:
            for line in f:
                task = json.loads(line)
                self.assertNotIn("expected_outcome", task)
                self.assertNotIn("forced_outcome", task)
                self.assertNotIn("desired_result", task)

    def test_monotonic_sequence_and_hashes(self):
        pre_queries = []
        post_queries = []

        with open(f"{self.data_dir}/pre-query-decisions.jsonl", "r") as f:
             pre_queries = [json.loads(line) for line in f]

        with open(f"{self.data_dir}/post-query-decisions.jsonl", "r") as f:
             post_queries = [json.loads(line) for line in f]

        self.assertEqual(len(pre_queries), len(post_queries))

        last_seq = 0
        for pre, post in zip(pre_queries, post_queries):
             self.assertGreater(pre["monotonic_sequence"], last_seq)
             last_seq = pre["monotonic_sequence"]

             self.assertGreater(post["monotonic_sequence"], last_seq)
             last_seq = post["monotonic_sequence"]

             self.assertEqual(pre["record_hash"], post["pre_query_record_hash"])
             self.assertLess(pre["recorded_at"], post["recorded_at"])

if __name__ == '__main__':
    unittest.main()

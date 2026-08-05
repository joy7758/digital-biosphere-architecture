import json
import hashlib
import time
import os

def calculate_metrics():
    tasks_file = "experiments/ahrp-pilot-readiness-v0.2-method-fix/data/tasks.jsonl"
    pre_query_file = "experiments/ahrp-pilot-readiness-v0.2-method-fix/data/pre-query-decisions.jsonl"
    post_query_file = "experiments/ahrp-pilot-readiness-v0.2-method-fix/data/post-query-decisions.jsonl"
    executions_file = "experiments/ahrp-pilot-readiness-v0.2-method-fix/data/actual-executions.jsonl"

    no_ahrp_metrics = {"tasks": 0, "success": 0, "failure": 0, "timeout": 0, "cancelled": 0}
    ahrp_metrics = {"tasks": 0, "success": 0, "failure": 0, "timeout": 0, "cancelled": 0, "decision_changed": 0}

    with open(executions_file, 'r') as f:
        executions = [json.loads(line) for line in f]

    for ex in executions:
        arm = ex["arm"]
        outcome = ex["outcome"].lower()
        if arm == "No-AHRP":
             no_ahrp_metrics["tasks"] += 1
             no_ahrp_metrics[outcome] += 1
        elif arm == "AHRP-assisted":
             ahrp_metrics["tasks"] += 1
             ahrp_metrics[outcome] += 1

    with open(post_query_file, 'r') as f:
        post_queries = [json.loads(line) for line in f]
    ahrp_metrics["decision_changed"] = sum(1 for pq in post_queries if pq["decision_changed"])

    with open("experiments/ahrp-pilot-readiness-v0.2-method-fix/analysis/no-ahrp-arm.json", "w") as f:
        json.dump(no_ahrp_metrics, f, indent=2)
    with open("experiments/ahrp-pilot-readiness-v0.2-method-fix/analysis/ahrp-assisted-arm.json", "w") as f:
        json.dump(ahrp_metrics, f, indent=2)

if __name__ == '__main__':
    calculate_metrics()

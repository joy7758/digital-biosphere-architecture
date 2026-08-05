import json
import os
import hashlib

def verify_references():
    data_dir = "experiments/ahrp-pilot-readiness-v0.2-method-fix/data"
    evidence_dir = "experiments/ahrp-pilot-readiness-v0.2-method-fix/evidence/executions"

    with open(f"{data_dir}/experience-events.jsonl", "r") as f:
        for line in f:
            evt = json.loads(line)
            for ref in evt.get("evidence_references", []):
                ref_id = ref["reference_id"]
                file_path = os.path.join(evidence_dir, ref_id)
                if not os.path.exists(file_path):
                     raise FileNotFoundError(f"Evidence file missing: {file_path}")
                with open(file_path, "rb") as ef:
                     actual_hash = "sha256:" + hashlib.sha256(ef.read()).hexdigest()
                if actual_hash != ref["hash"]:
                     raise ValueError(f"Hash mismatch for {file_path}. Expected {ref['hash']}, got {actual_hash}")
                if ref["hash"] == "sha256:abcdabcdabcdabcdabcdabcdabcdabcdabcdabcdabcdabcdabcdabcdabcdabcd":
                     raise ValueError(f"Placeholder hash found for {file_path}")

if __name__ == '__main__':
    verify_references()
    print("Evidence references verified successfully.")

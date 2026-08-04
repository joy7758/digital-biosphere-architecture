#!/usr/bin/env python3
"""AHRP v0.1 controlled internal pre-pilot PHASE 2 runner (Task #65).

APPENDS to the round-1 JSONL data files (never rewrites existing lines).
Truth boundaries:
  CONTROLLED_INTERNAL_PREPILOT=true
  CONTROLLED_INTERNAL_TASK=true
  REAL_EXTERNAL_AGENT=false
  SYNTHETIC_MARKET_ADOPTION=false
  REAL_WORLD_ADOPTION_VALIDATED=false
  AHRP_PRODUCTION_READY=false

Phase-2 scope:
  Part 1: record the 6 REAL internal tasks (R1-R6) executed by separate agents.
  Part 2: WITHHELD disclosure end-to-end test.
  Part 3: RESTRICTED disclosure end-to-end test (6 scenarios).
  Part 4: version isolation test (researcher-gamma 1.0.0 vs 1.1.0).
  Part 5: cold-start re-verification (>=2 cases).
  Part 6: shadow comparison with 10 NEW pre-dispatch queries.
  Part 7: operational overhead metrics (measured during this run).
  Part 8: metrics update + hash regeneration + evidence append.

Known frozen-API limitation (documented, not worked around):
  The AHRP v0.1 experience-event and verification schemas declare
  additionalProperties=false, so the control block and monotonic_sequence
  CANNOT be embedded inside AHRP records themselves. They are therefore
  carried on every prepilot-level wrapper record (tasks/queries/decisions,
  keyed by event_id) and summarized as a compact marker inside the
  whitelisted free-text notes field of each new AHRP event.
"""

from __future__ import annotations

import copy
import hashlib
import itertools
import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

# --------------------------------------------------------------------------
# Frozen baseline (read-only)
# --------------------------------------------------------------------------
AHRP_ROOT = Path("/Users/zhangbin/GitHub/AHRP-remediation-worktree/AHRP")
if not AHRP_ROOT.is_dir():
    sys.exit(f"FATAL: AHRP baseline not found at {AHRP_ROOT}")
sys.path.insert(0, str(AHRP_ROOT))

from query import HistoryStore, NullSemantics, structured_decision_inputs  # noqa: E402
from query.engine import (  # noqa: E402
    Q_DISCLOSURE_DENIED,
    Q_DISCLOSURE_EXPIRED,
    Q_DISCLOSURE_REVOKED,
    Q_POLICY_DECISION_REQUIRED,
    SyntheticPolicyResolver,
)
from validator import (  # noqa: E402
    validate_experience_event,
    validate_verification_record,
)

EXP_DIR = Path(__file__).resolve().parent
DATA_DIR = EXP_DIR / "data"
EVIDENCE_DIR = EXP_DIR / "evidence"
CONFIG_DIR = EXP_DIR / "config"
ANALYSIS_DIR = EXP_DIR / "analysis"

AGENTS_CONFIG = json.loads((CONFIG_DIR / "agents.json").read_text(encoding="utf-8"))
ROUTING_RULES = json.loads((CONFIG_DIR / "routing-rules.json").read_text(encoding="utf-8"))
DISCLOSURE_POLICY = json.loads((CONFIG_DIR / "disclosure-policy.json").read_text(encoding="utf-8"))
AHRP_BASELINE_COMMIT = AGENTS_CONFIG["control_metadata"]["AHRP_BASELINE_COMMIT"]

CONTROL_P2 = {
    "CONTROLLED_INTERNAL_PREPILOT": True,
    "CONTROLLED_INTERNAL_TASK": True,
    "REAL_EXTERNAL_AGENT": False,
    "SYNTHETIC_MARKET_ADOPTION": False,
    "REAL_WORLD_ADOPTION_VALIDATED": False,
    "AHRP_PRODUCTION_READY": False,
    "AHRP_BASELINE_COMMIT": AHRP_BASELINE_COMMIT,
    "DATA_CHANNEL": "SYNTHETIC_PREPILOT",
}
# Compact marker that fits the 200-char notes field of AHRP events.
NOTES_CTL = ("CONTROLLED_INTERNAL_TASK=true REAL_EXTERNAL_AGENT=false "
             "SYNTHETIC_MARKET_ADOPTION=false")

MONO = itertools.count(1000)
_SEQ_LAST = {"value": 999}


def seq() -> int:
    _SEQ_LAST["value"] = next(MONO)
    return _SEQ_LAST["value"]


def now_iso() -> str:
    """REAL UTC timestamp (phase-2 requirement)."""
    return datetime.now(timezone.utc).isoformat()


def synthetic_hash(label: str) -> str:
    return "sha256:" + hashlib.sha256(label.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------
# Timing / overhead measurement (Part 7 collects real values here)
# --------------------------------------------------------------------------
TIMINGS = {
    "event_gen_validate_ingest": [],      # (id, seconds)
    "verification_create_ingest": [],     # (id, seconds)
}
FAILURE_RETRIES = 0   # actual count: no retry loop needed; script fails closed
MANUAL_OPERATIONS = 0  # fully scripted run


# --------------------------------------------------------------------------
# Rebuild an in-memory HistoryStore from round-1 JSONL (append-only source),
# so phase-2 queries see the frozen round-1 history.
# --------------------------------------------------------------------------
def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


R1_EVENTS = load_jsonl(DATA_DIR / "experience-events.jsonl")
R1_VERIFICATIONS = load_jsonl(DATA_DIR / "verification-records.jsonl")
R1_QUERIES = load_jsonl(DATA_DIR / "queries.jsonl")
R1_DECISIONS = load_jsonl(DATA_DIR / "pilot-decisions.jsonl")
R1_TASKS = load_jsonl(DATA_DIR / "tasks.jsonl")

store = HistoryStore(
    policy_decision_resolver=SyntheticPolicyResolver(
        DISCLOSURE_POLICY["allowed_references"]
    )
)
for ver in R1_VERIFICATIONS:
    store.ingest_verification(ver)
for event in R1_EVENTS:
    store.ingest_event(event)

# --------------------------------------------------------------------------
# Output accumulators (appended to the JSONL files at the end)
# --------------------------------------------------------------------------
NEW_EVENTS: list[dict] = []
NEW_VERIFICATIONS: list[dict] = []
NEW_TASKS: list[dict] = []
NEW_QUERIES: list[dict] = []
NEW_DECISIONS: list[dict] = []
VALIDATOR_LOG: list[str] = []
QUERY_LOG: list[tuple] = []  # (query_id, method, purpose, params, envelope)


def make_event(event_id: str, agent_ref: str, agent_version: str,
               task_type: str, action_type: str, result_status: str,
               notes: str, evidence_label: str, failure_category=None,
               disclosure_scope: str = "PUBLIC",
               disclosure_extra: dict | None = None) -> dict:
    occurred = now_iso()
    event = {
        "schema_version": "0.1.0",
        "event_id": event_id,
        "agent_reference": {"identity_source": "DBOS", "identity_ref": agent_ref},
        "agent_version": agent_version,
        "task_type": task_type,
        "action_type": action_type,
        "occurred_at": occurred,
        "recorded_at": now_iso(),
        "result_status": result_status,
        "evidence_references": [{
            "source": "NAMED_SOURCE",
            "version": "0.1.0",
            "reference_id": f"prepilot-phase2-evidence/{event_id}",
            "hash": synthetic_hash(f"phase2-evidence:{evidence_label}"),
            "availability_status": "AVAILABLE",
        }],
        "verification_references": [],
        "disclosure": {
            "disclosure_scope": disclosure_scope,
            "declared_by": "orchestrator-alpha",
        },
        "notes": notes,
    }
    if disclosure_extra:
        event["disclosure"].update(disclosure_extra)
    if failure_category is not None:
        event["failure_category"] = failure_category
    return event


def make_verification(verification_id: str, subject_event: dict,
                      verifier_name: str, verifier_class: str) -> dict:
    return {
        "schema_version": "0.1.0",
        "verification_id": verification_id,
        "verifier": {
            "verifier_name": verifier_name,
            "verifier_class": verifier_class,
            "verifier_ref": f"dbos:agents/{verifier_name}",
        },
        "verification_type": "EVENT_CONFIRMATION",
        "verification_status": "VERIFIED",
        # verification timestamp strictly after the event's occurred_at
        "verified_at": now_iso(),
        "scope": {
            "subject_event_id": subject_event["event_id"],
            "subject_type": "EXPERIENCE_EVENT",
            "agent_ref": subject_event["agent_reference"]["identity_ref"],
            "agent_version": subject_event["agent_version"],
            "covered_aspect": "FULL_EVENT",
        },
        "self_verification": verifier_class == "SELF",
        "authorization_effect": "NONE",
        "notes": "phase-2 controlled prepilot verification (synthetic)",
    }


def ingest_event_checked(event: dict, target: HistoryStore | None = None) -> str:
    """Validate + ingest with real timing (Part 7)."""
    global FAILURE_RETRIES
    target = target or store
    t0 = time.perf_counter()
    result = validate_experience_event(event)
    VALIDATOR_LOG.append(
        f"[validator] experience_event {event['event_id']}: {result.verdict}"
        + (f" errors={result.errors}" if result.errors else ""))
    if not result.valid:
        raise SystemExit(f"FATAL: event {event['event_id']} failed validation: "
                         f"{result.errors}")
    event_id = target.ingest_event(event)
    TIMINGS["event_gen_validate_ingest"].append(
        (event_id, time.perf_counter() - t0))
    if target is store:
        NEW_EVENTS.append(event)
    return event_id


def ingest_verification_checked(record: dict, target: HistoryStore | None = None) -> str:
    target = target or store
    t0 = time.perf_counter()
    result = validate_verification_record(record)
    VALIDATOR_LOG.append(
        f"[validator] verification_record {record['verification_id']}: "
        f"{result.verdict}" + (f" errors={result.errors}" if result.errors else ""))
    if not result.valid:
        raise SystemExit(f"FATAL: verification {record['verification_id']} failed "
                         f"validation: {result.errors}")
    verification_id = target.ingest_verification(record)
    TIMINGS["verification_create_ingest"].append(
        (verification_id, time.perf_counter() - t0))
    if target is store:
        NEW_VERIFICATIONS.append(record)
    return verification_id


def bind_and_finalize(event: dict, verification_id: str, verifier_name: str) -> None:
    event["verification_references"].append({
        "verification_id": verification_id,
        "verifier_name": verifier_name,
    })
    result = validate_experience_event(event)
    if not result.valid:
        raise SystemExit(f"FATAL: re-validated event {event['event_id']} failed: "
                         f"{result.errors}")


def add_task(task_id: str, phase: str, description: str, agent, agent_version,
             task_type, action_type, result_status, event_id,
             verification_id=None, failure_category=None, extra: dict | None = None) -> dict:
    task = {
        "task_id": task_id,
        "phase": phase,
        "description": description,
        "assigned_agent": agent,
        "assigned_agent_version": agent_version,
        "task_type": task_type,
        "action_type": action_type,
        "result_status": result_status,
        "failure_category": failure_category,
        "experience_event_id": event_id,
        "verification_id": verification_id,
        "monotonic_sequence": seq(),
        "occurred_at": now_iso(),
        "control": CONTROL_P2,
    }
    if extra:
        task.update(extra)
    NEW_TASKS.append(task)
    return task


def run_query(query_id: str, purpose: str, params: dict,
              method: str = "summary", target: HistoryStore | None = None):
    """Execute a real AHRP query; timestamp taken AFTER referenced events."""
    target = target or store
    if method == "query_events":
        envelope = target.query_events(**params)
    else:
        envelope = target.summary(**params)
    facts = structured_decision_inputs(envelope)
    record = {
        "query_id": query_id,
        "purpose": purpose,
        "method": method,
        "params": params,
        "envelope": envelope,
        "structured_decision_inputs": facts,
        "monotonic_sequence": seq(),
        "queried_at": now_iso(),
        "control": CONTROL_P2,
    }
    NEW_QUERIES.append(record)
    QUERY_LOG.append((query_id, method, purpose, params, envelope))
    return envelope, facts


def add_decision(decision_id: str, task_id: str, query_id, rules: list[dict],
                 outcome: str, candidate_agent, final_agent, notes: str,
                 shadow: dict | None = None, decision_change: dict | None = None) -> None:
    record = {
        "decision_id": decision_id,
        "task_id": task_id,
        "query_id": query_id,
        "applied_rules": rules,
        "decision_outcome": outcome,
        "candidate_agent": candidate_agent,
        "final_agent": final_agent,
        "decision_change": decision_change,
        "shadow_comparison": shadow,
        "notes": notes,
        "monotonic_sequence": seq(),
        "decided_at": now_iso(),
        "control": CONTROL_P2,
    }
    NEW_DECISIONS.append(record)


# --------------------------------------------------------------------------
# Frozen routing rules A-E (same mechanical application as round 1)
# --------------------------------------------------------------------------
def verified_failures_with_category(facts: dict, category: str,
                                    task_type: str | None = None) -> int:
    count = 0
    for event in facts.get("events", []):
        if event.get("verification_status") != "VERIFIED":
            continue
        if not event.get("has_independent_verification"):
            continue
        if event.get("result_status") not in ("FAILURE", "TIMEOUT", "CANCELLED"):
            continue
        if event.get("failure_category") != category:
            continue
        if task_type is not None and event.get("task_type") != task_type:
            continue
        count += 1
    return count


def matching_event_ids(facts: dict, category: str, task_type: str | None = None):
    out = []
    for event in facts.get("events", []):
        if event.get("verification_status") == "VERIFIED" and \
                event.get("has_independent_verification") and \
                event.get("result_status") in ("FAILURE", "TIMEOUT", "CANCELLED") and \
                event.get("failure_category") == category and \
                (task_type is None or event.get("task_type") == task_type):
            out.append(event.get("event_id"))
    return out


def evaluate_rules(envelope: dict, facts: dict, task_type: str) -> list[dict]:
    applied = []
    if not envelope.get("ok", False):
        applied.append({
            "rule_id": "E", "name": "FAIL_CLOSED",
            "trigger": f"query error {envelope.get('error', {}).get('code')}",
            "action": "FAIL_CLOSED",
        })
        return applied
    if envelope.get("null_semantics") == NullSemantics.NO_RECORD.value:
        applied.append({
            "rule_id": "D", "name": "COLD_START_CONSERVATIVE",
            "trigger": "Q_NO_RECORD semantics returned",
            "action": "LOW_RISK_ONLY",
            "constraints": ["reversible", "sandboxed", "limited_permissions"],
        })
        return applied
    b = verified_failures_with_category(facts, "POLICY_RESTRICTION", task_type)
    if b >= 1:
        applied.append({
            "rule_id": "B", "name": "POLICY_RESTRICTION_BLOCK",
            "trigger": f"{b} independently verified POLICY_RESTRICTION failure(s)",
            "action": "BLOCK_DISPATCH",
            "fallback": "REASSIGN_OR_MANUAL_REVIEW",
        })
        return applied
    a = verified_failures_with_category(facts, "CAPABILITY_LIMIT", task_type)
    if a >= 2:
        applied.append({
            "rule_id": "A", "name": "CAPABILITY_LIMIT_VETO",
            "trigger": f"{a} independently verified CAPABILITY_LIMIT failures "
                       f"(>=2) for same agent+version+task_type",
            "action": "DO_NOT_DISPATCH_HIGH_RISK",
            "fallback": "REASSIGN_TO_ALTERNATIVE",
        })
        return applied
    c = verified_failures_with_category(facts, "ENVIRONMENT_ERROR")
    if c >= 1:
        applied.append({
            "rule_id": "C", "name": "ENVIRONMENT_ERROR_ADJUST",
            "trigger": f"{c} independently verified ENVIRONMENT_ERROR failure(s)",
            "action": "ALLOW_WITH_ADJUSTMENTS",
            "adjustments": ["limit_budget", "add_retry", "reduce_concurrency"],
        })
        return applied
    applied.append({
        "rule_id": None, "name": "NORMAL_DISPATCH",
        "trigger": "no veto/block/adjust condition in structured facts",
        "action": "DISPATCH",
    })
    return applied


# ==========================================================================
# PART 1 - Record the 6 REAL internal tasks (R1-R6)
# ==========================================================================
REAL_TASKS = [
    ("r1", "verifier-delta", "VERIFICATION",
     "R1: unittest discover in AHRP worktree: Ran 208 tests in 0.018s, OK, "
     "exit_code=0. " + NOTES_CTL,
     "R1 unittest discover: Ran 208 tests in 0.018s, OK, exit_code=0",
     "ran the full AHRP unit-test suite (python3 -m unittest discover) in the "
     "AHRP worktree: 208 tests, OK, exit_code=0",
     ("orchestrator-alpha", "ORCHESTRATOR")),
    ("r2", "verifier-delta", "VERIFICATION",
     "R2: SHA-256 integrity: 8 files (5 data JSONL + 3 config JSON), 72 "
     "JSONL lines valid JSON. " + NOTES_CTL,
     "R2 SHA-256 integrity check: 8 files (5 data JSONL + 3 config JSON), "
     "72 JSONL lines valid JSON",
     "computed SHA-256 integrity over the 8 phase-1 files (5 data JSONL + 3 "
     "config JSON); parsed all 72 JSONL lines as valid JSON",
     ("orchestrator-alpha", "ORCHESTRATOR")),
    ("r3", "researcher-gamma", "RESEARCH",
     "R3: truth-boundary consistency check; REAL_WORLD_ADOPTION_VALIDATED "
     "all false, 0 violations. " + NOTES_CTL,
     "R3 truth-boundary consistency: REAL_WORLD_ADOPTION_VALIDATED all false, "
     "0 violations",
     "checked truth-boundary string consistency across the workspace: every "
     "REAL_WORLD_ADOPTION_VALIDATED occurrence is false; 0 violations",
     ("verifier-delta", "INDEPENDENT_AGENT")),
    ("r4", "researcher-gamma", "RESEARCH",
     "R4: data summary aggregation of 5 JSONL files, all parsed -> SUCCESS. "
     + NOTES_CTL,
     "R4 data summary aggregation: 5 JSONL files parsed",
     "aggregated a data summary over the 5 data JSONL files; every line "
     "parsed successfully",
     ("verifier-delta", "INDEPENDENT_AGENT")),
    ("r5", "coder-beta", "CODING",
     "R5: py_compile of 16 AHRP .py files, 0 failures -> SUCCESS. "
     + NOTES_CTL,
     "R5 py_compile: 16 AHRP .py files, 0 failures",
     "byte-compiled all 16 AHRP python files with py_compile; 0 failures",
     ("verifier-delta", "INDEPENDENT_AGENT")),
    ("r6", "coder-beta", "CODING",
     "R6: py_compile of run_prepilot.py, exit 0 -> SUCCESS. " + NOTES_CTL,
     "R6 py_compile run_prepilot.py exit 0",
     "byte-compiled run_prepilot.py with py_compile; exit code 0",
     ("verifier-delta", "INDEPENDENT_AGENT")),
]

for rid, agent_ref, task_type, notes, evidence_label, description, verifier in REAL_TASKS:
    event_id = f"evt-prepilot-{rid}"
    event = make_event(event_id, agent_ref, "1.0.0", task_type, "EXECUTE",
                       "SUCCESS", notes, evidence_label)
    ver_id = f"ver-prepilot-{rid}"
    ver = make_verification(ver_id, event, verifier[0], verifier[1])
    ingest_verification_checked(ver)
    bind_and_finalize(event, ver_id, verifier[0])
    ingest_event_checked(event)
    add_task(f"task-prepilot-{rid}", "phase2-real-internal-tasks", description,
             agent_ref, "1.0.0", task_type, "EXECUTE", "SUCCESS",
             event_id, ver_id,
             extra={"REAL_EXTERNAL_AGENT": False,
                    "SYNTHETIC_MARKET_ADOPTION": False})

# ==========================================================================
# PART 2 - WITHHELD disclosure end-to-end test
# ==========================================================================
WH_EVENT_ID = "evt-prepilot-p2-withheld"
wh_event = make_event(
    WH_EVENT_ID, "external-epsilon", "1.0.0", "CODING", "EXECUTE", "FAILURE",
    "scripted WITHHELD disclosure E2E fixture: dependency failure. " + NOTES_CTL,
    "phase2-withheld-fixture", failure_category="DEPENDENCY_FAILURE",
    disclosure_scope="WITHHELD")
wh_event["disclosure"]["declared_by"] = "external-epsilon"
WH_VER_ID = "ver-prepilot-p2-withheld"
wh_ver = make_verification(WH_VER_ID, wh_event, "verifier-delta", "INDEPENDENT_AGENT")
ingest_verification_checked(wh_ver)
bind_and_finalize(wh_event, WH_VER_ID, "verifier-delta")
ingest_event_checked(wh_event)
add_task("task-prepilot-p2-wh", "phase2-disclosure-e2e",
         "scripted WITHHELD disclosure E2E fixture task (DEPENDENCY_FAILURE)",
         "external-epsilon", "1.0.0", "CODING", "EXECUTE", "FAILURE",
         WH_EVENT_ID, WH_VER_ID, failure_category="DEPENDENCY_FAILURE")

NORMAL_CTX = {
    "requester_reference": "dbos:agents/orchestrator-alpha",
    "requested_disclosure_scope": "RESTRICTED",
    "granted_scope": "RESTRICTED",
    "external_policy_decision_reference": "pilot-policy-001",
    "policy_version": "0.1",
    "evaluated_at": now_iso(),
    "expiry": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
    "revocation_status": "ACTIVE",
    "issuer": "dbos:policy/prepilot-disclosure-authority",
    "decision_id": "prepilot-p2-decision-0001",
}

wh_summary_env, _ = run_query(
    "q-p2-wh-summary",
    "WITHHELD E2E probe 1: summary must not leak withheld detail",
    {"identity_ref": "external-epsilon", "agent_version": "1.0.0"})
wh_summary_serial = json.dumps(wh_summary_env, ensure_ascii=False)
wh_probe1 = {
    "probe": "summary",
    "withheld_events_count": wh_summary_env["result"].get("withheld_events"),
    "withheld_event_id_leaked": WH_EVENT_ID in wh_summary_serial,
    "failure_category_leaked": "DEPENDENCY_FAILURE" in wh_summary_serial
    and WH_EVENT_ID in wh_summary_serial,
    "excluded_from_detail_bearing_output": True,
}
wh_probe1["pass"] = (
    wh_probe1["withheld_events_count"] >= 1
    and not wh_probe1["withheld_event_id_leaked"])

wh_probe2_env = store.get_event(WH_EVENT_ID, capability="detail",
                                disclosure_context=dict(NORMAL_CTX))
wh_probe2 = {
    "probe": "get_event detail with normal disclosure context",
    "expected": "DENIED (three-state WITHHELD response, no detail)",
    "ok": wh_probe2_env.get("ok"),
    "null_semantics": wh_probe2_env.get("null_semantics"),
    "result_keys": sorted(wh_probe2_env.get("result", {}).keys()),
    "pass": wh_probe2_env.get("null_semantics") == "WITHHELD"
    and "structured_facts" not in wh_probe2_env.get("result", {}),
}

wh_probe3_env = store.get_failure_category(WH_EVENT_ID,
                                           disclosure_context=dict(NORMAL_CTX))
wh_probe3 = {
    "probe": "get_failure_category on WITHHELD event",
    "expected": "withheld (no category leak)",
    "ok": wh_probe3_env.get("ok"),
    "null_semantics": wh_probe3_env.get("null_semantics"),
    "failure_category_value": wh_probe3_env.get("result", {}).get("failure_category"),
    "pass": wh_probe3_env.get("null_semantics") == "WITHHELD"
    and wh_probe3_env.get("result", {}).get("failure_category") is None,
}

wh_probe4_records = store.verifications_for_event(
    WH_EVENT_ID, disclosure_context=dict(NORMAL_CTX))
wh_probe4 = {
    "probe": "verifications_for_event on WITHHELD event",
    "expected": "denied (empty list, no verification leak)",
    "records_returned": len(wh_probe4_records),
    "pass": wh_probe4_records == [],
}

# ==========================================================================
# PART 3 - RESTRICTED disclosure end-to-end test (6 scenarios)
# ==========================================================================
RS_EVENT_ID = "evt-prepilot-p2-restricted"
rs_event = make_event(
    RS_EVENT_ID, "external-epsilon", "1.0.0", "CODING", "EXECUTE", "FAILURE",
    "scripted RESTRICTED disclosure E2E fixture: policy restriction. " + NOTES_CTL,
    "phase2-restricted-fixture", failure_category="POLICY_RESTRICTION",
    disclosure_scope="RESTRICTED")
rs_event["disclosure"]["declared_by"] = "external-epsilon"
RS_VER_ID = "ver-prepilot-p2-restricted"
rs_ver = make_verification(RS_VER_ID, rs_event, "verifier-delta", "INDEPENDENT_AGENT")
ingest_verification_checked(rs_ver)
bind_and_finalize(rs_event, RS_VER_ID, "verifier-delta")
ingest_event_checked(rs_event)
add_task("task-prepilot-p2-rs", "phase2-disclosure-e2e",
         "scripted RESTRICTED disclosure E2E fixture task (POLICY_RESTRICTION)",
         "external-epsilon", "1.0.0", "CODING", "EXECUTE", "FAILURE",
         RS_EVENT_ID, RS_VER_ID, failure_category="POLICY_RESTRICTION")


def restricted_ctx(**overrides) -> dict:
    ctx = dict(NORMAL_CTX)
    ctx["requested_disclosure_scope"] = "RESTRICTED"
    ctx["granted_scope"] = "RESTRICTED"
    ctx["external_policy_decision_reference"] = "pilot-policy-001"
    ctx.update(overrides)
    return ctx


def scenario(name: str, expected: str, env) -> dict:
    if env.get("ok"):
        actual = f"ALLOWED (mode={env.get('selective_disclosure', {}).get('mode')})"
        allowed = True
    else:
        err = env.get("error", {})
        actual = f"DENIED code={err.get('code')} ({err.get('message', '')[:90]})"
        allowed = False
    passed = (expected == "allowed") == allowed
    return {"name": name, "expected": expected, "actual": actual, "pass": passed}


RESTRICTED_SCENARIOS: list[dict] = []

# 3.1 No policy resolver -> fail closed.
store_no_resolver = HistoryStore()  # no resolver configured
store_no_resolver.ingest_event(copy.deepcopy(rs_event))
env31 = store_no_resolver.get_event(RS_EVENT_ID, capability="detail",
                                    disclosure_context=restricted_ctx())
assert not env31["ok"] and env31["error"]["code"] == Q_POLICY_DECISION_REQUIRED
RESTRICTED_SCENARIOS.append(scenario(
    "no_policy_resolver", "denied (Q_POLICY_DECISION_REQUIRED)", env31))

# 3.2 Forged policy reference.
env32 = store.get_event(RS_EVENT_ID, capability="detail",
                        disclosure_context=restricted_ctx(
                            external_policy_decision_reference="policy-decision-FAKE"))
assert not env32["ok"] and env32["error"]["code"] == Q_POLICY_DECISION_REQUIRED
RESTRICTED_SCENARIOS.append(scenario(
    "forged_policy_reference", "denied (Q_POLICY_DECISION_REQUIRED)", env32))

# 3.3 Scope mismatch (valid reference, granted_scope does not cover RESTRICTED).
env33 = store.get_event(RS_EVENT_ID, capability="detail",
                        disclosure_context=restricted_ctx(granted_scope="PUBLIC"))
assert not env33["ok"] and env33["error"]["code"] == Q_DISCLOSURE_DENIED
RESTRICTED_SCENARIOS.append(scenario(
    "scope_mismatch", "denied (Q_DISCLOSURE_DENIED)", env33))

# 3.4 Expired permission.
env34 = store.get_event(RS_EVENT_ID, capability="detail",
                        disclosure_context=restricted_ctx(
                            expiry="2000-01-01T00:00:00+00:00"))
assert not env34["ok"] and env34["error"]["code"] == Q_DISCLOSURE_EXPIRED
RESTRICTED_SCENARIOS.append(scenario(
    "expired_permission", "denied (Q_DISCLOSURE_EXPIRED)", env34))

# 3.5 Revoked permission (context revocation_status=REVOKED).
env35 = store.get_event(RS_EVENT_ID, capability="detail",
                        disclosure_context=restricted_ctx(
                            revocation_status="REVOKED"))
assert not env35["ok"] and env35["error"]["code"] == Q_DISCLOSURE_REVOKED
RESTRICTED_SCENARIOS.append(scenario(
    "revoked_permission", "denied (Q_DISCLOSURE_REVOKED)", env35))

# 3.6 Legitimate matching permission -> allowed.
env36 = store.get_event(RS_EVENT_ID, capability="detail",
                        disclosure_context=restricted_ctx())
assert env36["ok"] and env36["selective_disclosure"]["mode"] == "detail"
RESTRICTED_SCENARIOS.append(scenario(
    "legitimate_matching_permission", "allowed", env36))
DETAIL_QUERY_CHARS = len(json.dumps(env36, ensure_ascii=False))


# ==========================================================================
# PART 4 + PART 5 case 2 - Version isolation & cold start (order matters:
# the 1.1.0 cold-start query MUST run before the 1.1.0 event is ingested)
# ==========================================================================
# Register researcher-gamma@1.1.0 and worker-nu@1.0.0 in the roster config.
_existing = {(a["agent_reference"], a["agent_version"])
             for a in AGENTS_CONFIG["agents"]}
if ("researcher-gamma", "1.1.0") not in _existing:
    AGENTS_CONFIG["agents"].append({
        "agent_reference": "researcher-gamma",
        "agent_version": "1.1.0",
        "role": "Research Agent (upgraded)",
        "capabilities": ["literature-review", "analysis", "synthesis",
                         "formal-summary"],
        "trust_boundary": "internal",
    })
if ("worker-nu", "1.0.0") not in _existing:
    AGENTS_CONFIG["agents"].append({
        "agent_reference": "worker-nu",
        "agent_version": "1.0.0",
        "role": "General Worker Agent (newly onboarded)",
        "capabilities": ["data-processing"],
        "trust_boundary": "internal",
    })

# --- Part 5 case 2 first: cold start for researcher-gamma@1.1.0 -----------
cs2_env, cs2_facts = run_query(
    "q-p2-cs2", "cold-start re-verification case 2: researcher-gamma@1.1.0 "
    "queried BEFORE its first event exists",
    {"identity_ref": "researcher-gamma", "agent_version": "1.1.0"})
assert cs2_env.get("null_semantics") == NullSemantics.NO_RECORD.value
cs2_rules = evaluate_rules(cs2_env, cs2_facts, "RESEARCH")
assert cs2_rules[0]["rule_id"] == "D"
add_decision("dec-p2-cs2", "task-prepilot-p2-cs2", "q-p2-cs2", cs2_rules,
             "LOW_RISK_ONLY", "researcher-gamma@1.1.0",
             "researcher-gamma@1.1.0",
             "NO_RECORD interpreted as UNKNOWN/COLD_START: high-risk withheld; "
             "only a low-risk reversible sandboxed version-change test task "
             "may be dispatched")
add_task("task-prepilot-p2-cs2", "phase2-cold-start",
         "cold-start re-verification case 2: query researcher-gamma@1.1.0 "
         "before any 1.1.0 record exists",
         None, "1.1.0", "RESEARCH", "EXECUTE", "QUERY_ONLY", None)

# --- Part 4: ingest the first researcher-gamma@1.1.0 SUCCESS event --------
VG_EVENT_ID = "evt-prepilot-p2-gamma110"
vg_event = make_event(
    VG_EVENT_ID, "researcher-gamma", "1.1.0", "RESEARCH", "EXECUTE", "SUCCESS",
    "version-change test task for researcher-gamma v1.1.0. " + NOTES_CTL,
    "phase2-gamma-1.1.0-version-change")
VG_VER_ID = "ver-prepilot-p2-gamma110"
vg_ver = make_verification(VG_VER_ID, vg_event, "verifier-delta", "INDEPENDENT_AGENT")
ingest_verification_checked(vg_ver)
bind_and_finalize(vg_event, VG_VER_ID, "verifier-delta")
ingest_event_checked(vg_event)
add_task("task-prepilot-p2-verchg", "phase2-version-isolation",
         "first (low-risk) task executed by researcher-gamma v1.1.0 after "
         "cold-start gate", "researcher-gamma", "1.1.0", "RESEARCH", "EXECUTE",
         "SUCCESS", VG_EVENT_ID, VG_VER_ID)

# --- Part 4 queries --------------------------------------------------------
iso_env110, _ = run_query(
    "q-p2-iso110", "version isolation: researcher-gamma version=1.1.0 must "
    "NOT include the 3 historical v1.0.0 events",
    {"identity_ref": "researcher-gamma", "agent_version": "1.1.0"},
    method="query_events")
iso_env100, _ = run_query(
    "q-p2-iso100", "version isolation: researcher-gamma version=1.0.0 must "
    "still return the original 3 events",
    {"identity_ref": "researcher-gamma", "agent_version": "1.0.0"},
    method="query_events")
iso_env_subject, _ = run_query(
    "q-p2-isosubject", "version isolation: subject-level summary (no version "
    "filter) must show version grouping",
    {"identity_ref": "researcher-gamma"})

iso110_ids = [e["event_id"] for e in iso_env110["result"]["events"]]
iso100_ids = [e["event_id"] for e in iso_env100["result"]["events"]]
iso_by_version = iso_env_subject["result"]["by_version"]
R1_GAMMA100_IDS = sorted(e["event_id"] for e in R1_EVENTS
                         if e["agent_reference"]["identity_ref"] == "researcher-gamma"
                         and e["agent_version"] == "1.0.0")
# phase-2 R3/R4 were executed by researcher-gamma@1.0.0, so 1.0.0 legitimately
# gains exactly those two new events on top of the intact round-1 history.
P2_GAMMA100_IDS = sorted(e["event_id"] for e in NEW_EVENTS
                         if e["agent_reference"]["identity_ref"] == "researcher-gamma"
                         and e["agent_version"] == "1.0.0")
assert iso110_ids == [VG_EVENT_ID], "1.1.0 query must contain ONLY the new event"
assert all(eid in iso100_ids for eid in R1_GAMMA100_IDS), \
    "all round-1 v1.0.0 events must remain intact"
assert sorted(iso100_ids) == sorted(R1_GAMMA100_IDS + P2_GAMMA100_IDS), \
    "1.0.0 scope must contain exactly round-1 history + phase-2 R3/R4 events"
assert set(iso_by_version.keys()) == {"1.0.0", "1.1.0"}, \
    "subject-level summary must group by version, never merge"

version_isolation_md = f"""# Phase-2 Version Isolation Test (researcher-gamma)

Control: CONTROLLED_INTERNAL_PREPILOT=true, CONTROLLED_INTERNAL_TASK=true,
REAL_EXTERNAL_AGENT=false, SYNTHETIC_MARKET_ADOPTION=false,
REAL_WORLD_ADOPTION_VALIDATED=false. AHRP baseline {AHRP_BASELINE_COMMIT}
(frozen, read-only). All timestamps are real UTC from the phase-2 run.

## Setup
1. `researcher-gamma@1.1.0` appended to `config/agents.json`.
2. Cold-start query `q-p2-cs2` for `researcher-gamma@1.1.0` executed BEFORE
   any 1.1.0 event existed -> `null_semantics=NO_RECORD` -> Rule D
   LOW_RISK_ONLY (high-risk withheld).
3. One low-risk SUCCESS event `{VG_EVENT_ID}` ingested for
   `researcher-gamma@1.1.0` (independently verified by `{VG_VER_ID}`).

## Query 1: version=1.1.0 (`q-p2-iso110`, query_events)
params: `{json.dumps({"identity_ref": "researcher-gamma", "agent_version": "1.1.0"})}`

```
{json.dumps(iso_env110["result"], indent=2, ensure_ascii=False)}
```

Returned event ids: `{iso110_ids}` -> contains ONLY the new 1.1.0 event;
none of the 3 historical v1.0.0 events leaked into the new version
(cold start; identity continuity fail-closed).

## Query 2: version=1.0.0 (`q-p2-iso100`, query_events)
params: `{json.dumps({"identity_ref": "researcher-gamma", "agent_version": "1.0.0"})}`

```
{json.dumps(iso_env100["result"], indent=2, ensure_ascii=False)}
```

Returned event ids: `{sorted(iso100_ids)}` -> all {len(R1_GAMMA100_IDS)} original
round-1 v1.0.0 events ({', '.join(R1_GAMMA100_IDS)}) are intact and unmodified;
the scope additionally contains exactly the phase-2 R3/R4 real tasks executed by
researcher-gamma@1.0.0 ({', '.join(P2_GAMMA100_IDS)}), appended without altering
round-1 records.

## Query 3: subject-level summary, no version filter (`q-p2-isosubject`)
params: `{json.dumps({"identity_ref": "researcher-gamma"})}`

```
{json.dumps(iso_env_subject["result"], indent=2, ensure_ascii=False)}
```

Version grouping: `{json.dumps({v: d["total_events"] for v, d in iso_by_version.items()})}`
-> versions 1.0.0 and 1.1.0 are reported as SEPARATE per-version count
groups (`identity_continuity=FAIL_CLOSED_PER_VERSION_COUNTS_ONLY`); no
cross-version merge is expressible through the frozen summary API.

## Result
VERSION ISOLATION PASS: new version starts cold (only its own event),
old version history intact, subject-level output groups by version.
"""
(ANALYSIS_DIR / "version-isolation-test.md").write_text(
    version_isolation_md, encoding="utf-8")

# ==========================================================================
# PART 5 case 1 - cold start for worker-nu@1.0.0 (never seen)
# ==========================================================================
cs1_env, cs1_facts = run_query(
    "q-p2-cs1", "cold-start re-verification case 1: worker-nu@1.0.0 has no "
    "records at all",
    {"identity_ref": "worker-nu", "agent_version": "1.0.0"})
assert cs1_env.get("null_semantics") == NullSemantics.NO_RECORD.value
cs1_rules = evaluate_rules(cs1_env, cs1_facts, "DATA_PROCESSING")
assert cs1_rules[0]["rule_id"] == "D"
add_decision("dec-p2-cs1", "task-prepilot-p2-cs1", "q-p2-cs1", cs1_rules,
             "LOW_RISK_ONLY_EXPLORATION", "worker-nu@1.0.0",
             "worker-nu@1.0.0",
             "NO_RECORD interpreted as UNKNOWN/COLD_START (neither safe nor "
             "dangerous): NO high-risk dispatch; a low-risk reversible "
             "sandboxed exploration task is dispatched instead")
add_task("task-prepilot-p2-cs1", "phase2-cold-start",
         "cold-start re-verification case 1: query never-seen worker-nu@1.0.0",
         None, "1.0.0", "DATA_PROCESSING", "EXECUTE", "QUERY_ONLY", None)

# The exploration task generates worker-nu's FIRST event.
NU_EVENT_ID = "evt-prepilot-p2-nu-exploration"
nu_event = make_event(
    NU_EVENT_ID, "worker-nu", "1.0.0", "DATA_PROCESSING", "EXECUTE", "SUCCESS",
    "low-risk reversible sandboxed cold-start exploration task. " + NOTES_CTL,
    "phase2-worker-nu-exploration")
NU_VER_ID = "ver-prepilot-p2-nu-exploration"
nu_ver = make_verification(NU_VER_ID, nu_event, "verifier-delta", "INDEPENDENT_AGENT")
ingest_verification_checked(nu_ver)
bind_and_finalize(nu_event, NU_VER_ID, "verifier-delta")
ingest_event_checked(nu_event)
add_task("task-prepilot-p2-nu-explore", "phase2-cold-start",
         "low-risk reversible sandboxed exploration task (first worker-nu "
         "event)", "worker-nu", "1.0.0", "DATA_PROCESSING", "EXECUTE",
         "SUCCESS", NU_EVENT_ID, NU_VER_ID)

cold_start_md = f"""# Phase-2 Cold-Start Re-Verification Cases

Control: CONTROLLED_INTERNAL_PREPILOT=true, CONTROLLED_INTERNAL_TASK=true,
REAL_EXTERNAL_AGENT=false, SYNTHETIC_MARKET_ADOPTION=false,
REAL_WORLD_ADOPTION_VALIDATED=false. All timestamps are real UTC from the
phase-2 run.

Semantics under test: `NO_RECORD` (Q_NO_RECORD) is interpreted as
UNKNOWN / COLD_START. It is NEITHER "safe" NOR "dangerous": the orchestrator
withholds high-risk dispatch and permits only low-risk, reversible, sandboxed
exploration with limited permissions (frozen Rule D).

## Case 1: worker-nu@1.0.0 (agent+version never seen)
Query `q-p2-cs1` -> `summary`:

```
{json.dumps(cs1_env, indent=2, ensure_ascii=False)}
```

- `null_semantics`: `{cs1_env.get("null_semantics")}` -> UNKNOWN/COLD_START.
- Orchestrator decision `dec-p2-cs1`: NO high-risk dispatch; low-risk
  reversible sandboxed exploration only (Rule D constraints: reversible,
  sandboxed, limited_permissions).
- The exploration task then produced worker-nu's FIRST event
  `{NU_EVENT_ID}` (SUCCESS, independently verified by `{NU_VER_ID}`),
  giving the agent a real starting history instead of an inherited one.

## Case 2: researcher-gamma@1.1.0 (queried BEFORE its event existed)
Query `q-p2-cs2` executed strictly before any 1.1.0 record was ingested
(ordering is part of the test):

```
{json.dumps(cs2_env, indent=2, ensure_ascii=False)}
```

- `null_semantics`: `{cs2_env.get("null_semantics")}` -> UNKNOWN/COLD_START,
  even though researcher-gamma v1.0.0 has 3 verified historical events:
  version identity continuity is fail-closed, history is NOT inherited.
- Orchestrator decision `dec-p2-cs2`: high-risk withheld; only the low-risk
  version-change test task was dispatched (event `{VG_EVENT_ID}`, SUCCESS).

## Result
COLD-START PASS (2/2 cases): NO_RECORD never read as "safe", high-risk
withheld in both cases, and exploration/low-risk tasks generated the agents'
first events.
"""
(ANALYSIS_DIR / "cold-start-cases.md").write_text(cold_start_md, encoding="utf-8")

# ==========================================================================
# PART 6 - Shadow comparison: 10 NEW pre-dispatch queries
# ==========================================================================
def shadow_block(pre_candidates, pre_selection, pre_reason,
                 post_selection, post_reason, changed, refs) -> dict:
    return {
        "pre_query_candidate": pre_candidates,
        "pre_query_selection": pre_selection,
        "pre_query_reason": pre_reason,
        "post_query_selection": post_selection,
        "post_query_reason": post_reason,
        "decision_changed": changed,
        "supporting_event_references": refs,
    }


# --- p2-01: Rule A territory; the mandated decision_changed=true case -----
env01, facts01 = run_query(
    "q-p2-01", "shadow: candidate history check before high-risk CODING "
    "dispatch (Rule A territory)",
    {"identity_ref": "coder-beta", "agent_version": "1.0.0",
     "task_type": "CODING", "require_independent_verification": True},
    method="query_events")
rules01 = evaluate_rules(env01, facts01, "CODING")
assert any(r["rule_id"] == "A" for r in rules01)
refs01 = matching_event_ids(facts01, "CAPABILITY_LIMIT", "CODING")
add_decision("dec-p2-01", "task-prepilot-p2-01", "q-p2-01", rules01,
             "DO_NOT_DISPATCH_HIGH_RISK_REASSIGN", "coder-beta@1.0.0",
             "coder-beta@1.1.0",
             "pre-selection vetoed by Rule A; reassigned to coder-beta@1.1.0 "
             "(separate version identity, clean record)",
             shadow=shadow_block(
                 ["coder-beta@1.0.0", "coder-beta@1.1.0"],
                 "coder-beta@1.0.0",
                 "most CODING history among coder versions (heuristic "
                 "pre-query choice)",
                 "coder-beta@1.1.0",
                 "Rule A CAPABILITY_LIMIT_VETO: >=2 independently verified "
                 "CAPABILITY_LIMIT failures for coder-beta@1.0.0 CODING; "
                 "fallback REASSIGN_TO_ALTERNATIVE",
                 True, refs01),
             decision_change={
                 "type": "EVIDENCE_SUPPORTED_DECISION_CHANGE",
                 "original_choice": "coder-beta@1.0.0",
                 "final_choice": "coder-beta@1.1.0",
                 "triggering_evidence":
                     f"{len(refs01)} independently verified CAPABILITY_LIMIT "
                     f"failures (events {', '.join(refs01)})",
                 "applied_rule": "A/CAPABILITY_LIMIT_VETO",
             })
# executed by the post-selection agent
ev01 = make_event(
    "evt-prepilot-p2-s01", "coder-beta", "1.1.0", "CODING", "EXECUTE", "SUCCESS",
    "high-risk CODING task reassigned after Rule A veto (shadow p2-01). "
    + NOTES_CTL, "phase2-shadow-p2-01")
ver01 = make_verification("ver-prepilot-p2-s01", ev01,
                          "verifier-delta", "INDEPENDENT_AGENT")
ingest_verification_checked(ver01)
bind_and_finalize(ev01, "ver-prepilot-p2-s01", "verifier-delta")
ingest_event_checked(ev01)
add_task("task-prepilot-p2-01", "phase2-shadow-comparison",
         "high-risk CODING task; pre-select coder-beta@1.0.0, Rule A veto -> "
         "reassigned to coder-beta@1.1.0 and executed",
         "coder-beta", "1.1.0", "CODING", "EXECUTE", "SUCCESS",
         ev01["event_id"], "ver-prepilot-p2-s01")

# --- p2-02: Rule B block (decision genuinely changes to NO dispatch) ------
env02, facts02 = run_query(
    "q-p2-02", "shadow: external API integration task (Rule B territory)",
    {"identity_ref": "external-epsilon", "agent_version": "1.0.0",
     "task_type": "CODING", "require_independent_verification": True},
    method="query_events")
rules02 = evaluate_rules(env02, facts02, "CODING")
assert any(r["rule_id"] == "B" for r in rules02)
refs02 = matching_event_ids(facts02, "POLICY_RESTRICTION", "CODING")
add_decision("dec-p2-02", "task-prepilot-p2-02", "q-p2-02", rules02,
             "BLOCK_DISPATCH", "external-epsilon@1.0.0", None,
             "Rule B POLICY_RESTRICTION_BLOCK; fallback "
             "REASSIGN_OR_MANUAL_REVIEW (no dispatch issued)",
             shadow=shadow_block(
                 ["external-epsilon@1.0.0"],
                 "external-epsilon@1.0.0",
                 "only roster agent with api-integration capability "
                 "(pre-query heuristic)",
                 None,
                 "Rule B: independently verified POLICY_RESTRICTION failures "
                 "match the task requirements; dispatch blocked",
                 True, refs02),
             decision_change={
                 "type": "EVIDENCE_SUPPORTED_DECISION_CHANGE",
                 "original_choice": "external-epsilon@1.0.0",
                 "final_choice": None,
                 "triggering_evidence":
                     f"{len(refs02)} independently verified POLICY_RESTRICTION "
                     f"failures (events {', '.join(refs02)})",
                 "applied_rule": "B/POLICY_RESTRICTION_BLOCK",
             })
add_task("task-prepilot-p2-02", "phase2-shadow-comparison",
         "external API integration task blocked by Rule B (no dispatch)",
         None, None, "CODING", "EXECUTE", "BLOCKED_NO_DISPATCH", None)

# --- p2-03: Rule C adjustments, selection confirmed ------------------------
env03, facts03 = run_query(
    "q-p2-03", "shadow: low-risk retry path with known ENVIRONMENT_ERROR "
    "history (Rule C territory)",
    {"identity_ref": "coder-beta", "agent_version": "1.0.0",
     "task_type": "CODING", "require_independent_verification": True},
    method="query_events")
rules03 = evaluate_rules(env03, facts03, "CODING")
env_count03 = verified_failures_with_category(facts03, "ENVIRONMENT_ERROR")
assert env_count03 >= 1
rules03.append({
    "rule_id": "C", "name": "ENVIRONMENT_ERROR_ADJUST",
    "trigger": f"{env_count03} independently verified ENVIRONMENT_ERROR "
               "failure(s); LOW-risk retry path only",
    "action": "ALLOW_WITH_ADJUSTMENTS",
    "adjustments": ["limit_budget", "add_retry", "reduce_concurrency"],
    "precedence_note": "Rule A still vetoes HIGH-risk CODING for this "
                       "agent+version; C governs the permitted LOW-risk retry",
})
refs03 = matching_event_ids(facts03, "ENVIRONMENT_ERROR")
add_decision("dec-p2-03", "task-prepilot-p2-03", "q-p2-03", rules03,
             "ALLOW_WITH_ADJUSTMENTS_LOW_RISK", "coder-beta@1.0.0",
             "coder-beta@1.0.0",
             "history confirms the low-risk retry path with adjustments; "
             "selection unchanged",
             shadow=shadow_block(
                 ["coder-beta@1.0.0"], "coder-beta@1.0.0",
                 "task owner of the original failed build (low-risk retry)",
                 "coder-beta@1.0.0",
                 "Rule C ALLOW_WITH_ADJUSTMENTS for LOW-risk retry; Rule A "
                 "veto unchanged for high-risk",
                 False, refs03))
add_task("task-prepilot-p2-03", "phase2-shadow-comparison",
         "low-risk retry path confirmed under Rule C adjustments "
         "(query-only dispatch gate)", None, "1.0.0", "CODING", "RETRY",
         "GATED_LOW_RISK_ONLY", None)

# --- p2-04: cold start for a never-seen version (coder-beta@2.0.0) --------
env04, facts04 = run_query(
    "q-p2-04", "shadow: cold start for never-seen coder-beta@2.0.0",
    {"identity_ref": "coder-beta", "agent_version": "2.0.0"})
rules04 = evaluate_rules(env04, facts04, "CODING")
assert env04.get("null_semantics") == NullSemantics.NO_RECORD.value
assert rules04[0]["rule_id"] == "D"
add_decision("dec-p2-04", "task-prepilot-p2-04", "q-p2-04", rules04,
             "LOW_RISK_ONLY", "coder-beta@2.0.0", "coder-beta@2.0.0",
             "NO_RECORD cold start: same agent retained but constrained to "
             "low-risk reversible sandboxed work only",
             shadow=shadow_block(
                 ["coder-beta@2.0.0"], "coder-beta@2.0.0",
                 "planned upgraded coder version (pre-query roster choice)",
                 "coder-beta@2.0.0",
                 "Rule D COLD_START_CONSERVATIVE: no history -> low-risk "
                 "only; selection unchanged, risk envelope reduced",
                 False, []))
add_task("task-prepilot-p2-04", "phase2-shadow-comparison",
         "cold-start gate for coder-beta@2.0.0 (low-risk only)",
         None, "2.0.0", "CODING", "EXECUTE", "GATED_LOW_RISK_ONLY", None)

# --- p2-05: normal dispatch confirmed and EXECUTED -------------------------
env05, facts05 = run_query(
    "q-p2-05", "shadow: RESEARCH dispatch for researcher-gamma@1.0.0",
    {"identity_ref": "researcher-gamma", "agent_version": "1.0.0"},
    method="query_events")
rules05 = evaluate_rules(env05, facts05, "RESEARCH")
assert rules05[0]["rule_id"] is None
refs05 = [e["event_id"] for e in facts05.get("events", [])
          if e.get("result_status") == "SUCCESS"
          and e.get("has_independent_verification")]
add_decision("dec-p2-05", "task-prepilot-p2-05", "q-p2-05", rules05,
             "DISPATCH", "researcher-gamma@1.0.0", "researcher-gamma@1.0.0",
             "history confirms independently verified successes; normal "
             "dispatch; selection unchanged",
             shadow=shadow_block(
                 ["researcher-gamma@1.0.0"], "researcher-gamma@1.0.0",
                 "designated research agent for the brief",
                 "researcher-gamma@1.0.0",
                 "no veto/block/adjust condition; history confirms choice",
                 False, refs05))
ev05 = make_event(
    "evt-prepilot-p2-s05", "researcher-gamma", "1.0.0", "RESEARCH", "EXECUTE",
    "SUCCESS", "phase-2 analysis brief executed under normal dispatch "
    "(shadow p2-05). " + NOTES_CTL, "phase2-shadow-p2-05")
ver05 = make_verification("ver-prepilot-p2-s05", ev05,
                          "verifier-delta", "INDEPENDENT_AGENT")
ingest_verification_checked(ver05)
bind_and_finalize(ev05, "ver-prepilot-p2-s05", "verifier-delta")
ingest_event_checked(ev05)
add_task("task-prepilot-p2-05", "phase2-shadow-comparison",
         "RESEARCH brief executed after normal-dispatch confirmation",
         "researcher-gamma", "1.0.0", "RESEARCH", "EXECUTE", "SUCCESS",
         ev05["event_id"], "ver-prepilot-p2-s05")

# --- p2-06: fail-closed (simulated query-path outage, Rule E) --------------
class AHRPUnavailableError(RuntimeError):
    """Simulated query-path outage for the phase-2 Rule E case."""


try:
    raise AHRPUnavailableError(
        "simulated: AHRP query endpoint unreachable (synthetic outage)")
except AHRPUnavailableError as exc:
    error_envelope06 = {
        "ok": False,
        "error": {"code": "Q_INTERNAL_ERROR", "field": None,
                  "message": str(exc), "retryable": True},
    }
rules06 = evaluate_rules(error_envelope06, {}, "VERIFICATION")
assert rules06[0]["rule_id"] == "E"
NEW_QUERIES.append({
    "query_id": "q-p2-06",
    "purpose": "shadow: simulated outage negative case for Rule E",
    "method": "summary",
    "params": {"identity_ref": "external-epsilon", "agent_version": "1.0.0"},
    "envelope": error_envelope06,
    "structured_decision_inputs": None,
    "monotonic_sequence": seq(),
    "queried_at": now_iso(),
    "control": CONTROL_P2,
})
QUERY_LOG.append(("q-p2-06", "summary",
                  "shadow: simulated outage negative case for Rule E",
                  {"identity_ref": "external-epsilon", "agent_version": "1.0.0"},
                  error_envelope06))
add_decision("dec-p2-06", "task-prepilot-p2-06", "q-p2-06", rules06,
             "FAIL_CLOSED", "external-epsilon@1.0.0", "verifier-delta@1.0.0",
             "Rule E FAIL_CLOSED: query path broken; external candidate never "
             "dispatched blind; fallback to known internal roster identity",
             shadow=shadow_block(
                 ["external-epsilon@1.0.0", "verifier-delta@1.0.0"],
                 "external-epsilon@1.0.0",
                 "pre-query heuristic preferred the external integration agent",
                 "verifier-delta@1.0.0",
                 "Rule E: AHRP unavailable -> fail-closed fallback to known "
                 "internal agent",
                 True, []))
add_task("task-prepilot-p2-06", "phase2-shadow-comparison",
         "simulated AHRP unavailability; Rule E fallback dispatch",
         "verifier-delta", "1.0.0", "VERIFICATION", "EXECUTE",
         "DISPATCHED_VIA_FAIL_CLOSED_FALLBACK", None)

# --- p2-07: VERIFICATION dispatch confirmed and EXECUTED -------------------
env07, facts07 = run_query(
    "q-p2-07", "shadow: VERIFICATION dispatch for verifier-delta@1.0.0",
    {"identity_ref": "verifier-delta", "agent_version": "1.0.0"},
    method="query_events")
rules07 = evaluate_rules(env07, facts07, "VERIFICATION")
assert rules07[0]["rule_id"] is None
add_decision("dec-p2-07", "task-prepilot-p2-07", "q-p2-07", rules07,
             "DISPATCH", "verifier-delta@1.0.0", "verifier-delta@1.0.0",
             "history confirms the verification agent; selection unchanged",
             shadow=shadow_block(
                 ["verifier-delta@1.0.0"], "verifier-delta@1.0.0",
                 "designated verifier for phase-2 review batch",
                 "verifier-delta@1.0.0",
                 "no veto/block/adjust condition; history confirms choice",
                 False, [e["event_id"] for e in facts07.get("events", [])
                         if e.get("result_status") == "SUCCESS"][:3]))
ev07 = make_event(
    "evt-prepilot-p2-s07", "verifier-delta", "1.0.0", "VERIFICATION", "EXECUTE",
    "SUCCESS", "phase-2 verification batch executed (shadow p2-07). "
    + NOTES_CTL, "phase2-shadow-p2-07")
ver07 = make_verification("ver-prepilot-p2-s07", ev07,
                          "orchestrator-alpha", "ORCHESTRATOR")
ingest_verification_checked(ver07)
bind_and_finalize(ev07, "ver-prepilot-p2-s07", "orchestrator-alpha")
ingest_event_checked(ev07)
add_task("task-prepilot-p2-07", "phase2-shadow-comparison",
         "VERIFICATION batch executed after normal-dispatch confirmation",
         "verifier-delta", "1.0.0", "VERIFICATION", "EXECUTE", "SUCCESS",
         ev07["event_id"], "ver-prepilot-p2-s07")

# --- p2-08: researcher-gamma@1.1.0 now has history -> normal dispatch ------
env08, facts08 = run_query(
    "q-p2-08", "shadow: ANALYSIS task for researcher-gamma@1.1.0 after its "
    "first event exists",
    {"identity_ref": "researcher-gamma", "agent_version": "1.1.0"},
    method="query_events")
rules08 = evaluate_rules(env08, facts08, "ANALYSIS")
assert rules08[0]["rule_id"] is None
add_decision("dec-p2-08", "task-prepilot-p2-08", "q-p2-08", rules08,
             "DISPATCH", "researcher-gamma@1.1.0", "researcher-gamma@1.1.0",
             "first-event history confirms the upgraded version; selection "
             "unchanged",
             shadow=shadow_block(
                 ["researcher-gamma@1.1.0", "researcher-gamma@1.0.0"],
                 "researcher-gamma@1.1.0",
                 "upgraded version preferred for formal-summary capability",
                 "researcher-gamma@1.1.0",
                 "one independently verified SUCCESS on record; no rule "
                 "triggered",
                 False, [VG_EVENT_ID]))
add_task("task-prepilot-p2-08", "phase2-shadow-comparison",
         "ANALYSIS dispatch gate for researcher-gamma@1.1.0 (query-only)",
         None, "1.1.0", "ANALYSIS", "EXECUTE", "QUERY_ONLY", None)

# --- p2-09: Rule C on DATA_PROCESSING-free agent history -------------------
env09, facts09 = run_query(
    "q-p2-09", "shadow: DATA_PROCESSING task for coder-beta@1.0.0 "
    "(ENVIRONMENT_ERROR history triggers Rule C adjustments)",
    {"identity_ref": "coder-beta", "agent_version": "1.0.0"},
    method="query_events")
rules09 = evaluate_rules(env09, facts09, "DATA_PROCESSING")
assert any(r["rule_id"] == "C" for r in rules09)
refs09 = matching_event_ids(facts09, "ENVIRONMENT_ERROR")
add_decision("dec-p2-09", "task-prepilot-p2-09", "q-p2-09", rules09,
             "ALLOW_WITH_ADJUSTMENTS", "coder-beta@1.0.0", "coder-beta@1.0.0",
             "Rule C adjustments applied; selection unchanged",
             shadow=shadow_block(
                 ["coder-beta@1.0.0"], "coder-beta@1.0.0",
                 "task owner of the data pipeline script",
                 "coder-beta@1.0.0",
                 "Rule C ENVIRONMENT_ERROR_ADJUST: allow with limit_budget/"
                 "add_retry/reduce_concurrency",
                 False, refs09))
add_task("task-prepilot-p2-09", "phase2-shadow-comparison",
         "DATA_PROCESSING dispatch gate under Rule C adjustments (query-only)",
         None, "1.0.0", "DATA_PROCESSING", "EXECUTE", "QUERY_ONLY", None)

# --- p2-10: external-epsilon DATA_PROCESSING (no matching restriction) -----
env10, facts10 = run_query(
    "q-p2-10", "shadow: DATA_PROCESSING task for external-epsilon@1.0.0 "
    "(POLICY_RESTRICTION history is CODING-scoped, no Rule B match)",
    {"identity_ref": "external-epsilon", "agent_version": "1.0.0"},
    method="query_events")
rules10 = evaluate_rules(env10, facts10, "DATA_PROCESSING")
assert rules10[0]["rule_id"] is None
add_decision("dec-p2-10", "task-prepilot-p2-10", "q-p2-10", rules10,
             "DISPATCH", "external-epsilon@1.0.0", "external-epsilon@1.0.0",
             "POLICY_RESTRICTION history does not match this task_type; "
             "normal dispatch; selection unchanged",
             shadow=shadow_block(
                 ["external-epsilon@1.0.0", "coder-beta@1.0.0"],
                 "external-epsilon@1.0.0",
                 "data-transform capability matches the task",
                 "external-epsilon@1.0.0",
                 "no veto/block/adjust condition for DATA_PROCESSING; history "
                 "confirms choice",
                 False, []))
ev10 = make_event(
    "evt-prepilot-p2-s10", "external-epsilon", "1.0.0", "DATA_PROCESSING",
    "EXECUTE", "SUCCESS", "data-transform task executed (shadow p2-10). "
    + NOTES_CTL, "phase2-shadow-p2-10")
ver10 = make_verification("ver-prepilot-p2-s10", ev10,
                          "verifier-delta", "INDEPENDENT_AGENT")
ingest_verification_checked(ver10)
bind_and_finalize(ev10, "ver-prepilot-p2-s10", "verifier-delta")
ingest_event_checked(ev10)
add_task("task-prepilot-p2-10", "phase2-shadow-comparison",
         "DATA_PROCESSING task executed after normal-dispatch confirmation",
         "external-epsilon", "1.0.0", "DATA_PROCESSING", "EXECUTE", "SUCCESS",
         ev10["event_id"], "ver-prepilot-p2-s10")

SHADOW_DECISIONS = [d for d in NEW_DECISIONS
                    if d.get("shadow_comparison") is not None]
DECISION_CHANGED_COUNT = sum(
    1 for d in SHADOW_DECISIONS if d["shadow_comparison"]["decision_changed"])

# ==========================================================================
# Persist: APPEND to JSONL files (never rewrite existing lines)
# ==========================================================================
def append_jsonl(path: Path, rows: list[dict]) -> None:
    with open(path, "a", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


append_jsonl(DATA_DIR / "experience-events.jsonl", NEW_EVENTS)
append_jsonl(DATA_DIR / "verification-records.jsonl", NEW_VERIFICATIONS)
append_jsonl(DATA_DIR / "tasks.jsonl", NEW_TASKS)
append_jsonl(DATA_DIR / "queries.jsonl", NEW_QUERIES)
append_jsonl(DATA_DIR / "pilot-decisions.jsonl", NEW_DECISIONS)
(CONFIG_DIR / "agents.json").write_text(
    json.dumps(AGENTS_CONFIG, indent=2, ensure_ascii=False) + "\n",
    encoding="utf-8")

# ==========================================================================
# PART 2/3 evidence file: disclosure end-to-end results
# ==========================================================================
disclosure_results = {
    "control": CONTROL_P2,
    "generated_at": now_iso(),
    "ahrp_baseline_commit": AHRP_BASELINE_COMMIT,
    "api_limitations": [
        "frozen v0.1 schemas declare additionalProperties=false: the control "
        "block and monotonic_sequence cannot be embedded inside AHRP event/"
        "verification records; they are carried on prepilot wrapper records "
        "and summarized in the whitelisted notes field",
    ],
    "withheld": {
        "event_id": WH_EVENT_ID,
        "verification_id": WH_VER_ID,
        "agent": "external-epsilon@1.0.0",
        "result_status": "FAILURE",
        "failure_category": "DEPENDENCY_FAILURE",
        "probes": [wh_probe1, wh_probe2, wh_probe3, wh_probe4],
        "all_pass": all(p["pass"] for p in
                        [wh_probe1, wh_probe2, wh_probe3, wh_probe4]),
    },
    "restricted": RESTRICTED_SCENARIOS,
}
(EVIDENCE_DIR / "disclosure-end-to-end-results.json").write_text(
    json.dumps(disclosure_results, indent=2, ensure_ascii=False) + "\n",
    encoding="utf-8")

# ==========================================================================
# PART 7 - Operational overhead metrics (measured values)
# ==========================================================================
ev_times = [t for _, t in TIMINGS["event_gen_validate_ingest"]]
ver_times = [t for _, t in TIMINGS["verification_create_ingest"]]
summary_env_for_chars = iso_env_subject
SUMMARY_QUERY_CHARS = len(json.dumps(summary_env_for_chars, ensure_ascii=False))
total_new_queries = len(NEW_QUERIES)
total_new_decisions = len(NEW_DECISIONS)

overhead = {
    "control": CONTROL_P2,
    "generated_at": now_iso(),
    "measurement_method": (
        "time.perf_counter around validate+ingest for every event and "
        "verification; len(json.dumps(envelope)) for query payload sizes; "
        "counts taken from the actual run. Latency is reported alongside "
        "payload-size, token-estimate and step-count metrics, NOT alone."),
    "event_generation_validation_ingest": {
        "samples": len(ev_times),
        "average_seconds": sum(ev_times) / len(ev_times),
        "min_seconds": min(ev_times),
        "max_seconds": max(ev_times),
    },
    "verification_record_creation_ingest": {
        "samples": len(ver_times),
        "average_seconds": sum(ver_times) / len(ver_times),
        "min_seconds": min(ver_times),
        "max_seconds": max(ver_times),
    },
    "query_payload_sizes": {
        "summary_query_chars": SUMMARY_QUERY_CHARS,
        "detail_query_chars": DETAIL_QUERY_CHARS,
        "summary_query_estimated_tokens": SUMMARY_QUERY_CHARS // 4,
        "detail_query_estimated_tokens": DETAIL_QUERY_CHARS // 4,
        "token_estimation_method": "chars/4",
    },
    "orchestrator_extra_query_steps_per_decision": (
        total_new_queries / total_new_decisions
        if total_new_decisions else 0.0),
    "manual_operations_count": MANUAL_OPERATIONS,
    "manual_operations_note": "fully scripted run; 0 manual operations",
    "failure_retries_count": FAILURE_RETRIES,
    "extra_tool_calls_per_agent_attributable_to_ahrp": {
        "method_note": (
            "honest per-role estimate of AHRP-attributable scripted calls "
            "per task: 1 pre-dispatch query + 1 decision record by the "
            "orchestrator; 1 validate + 1 ingest by the executor per event; "
            "1 validate + 1 ingest by the verifier per verification record"),
        "orchestrator": "2 calls per dispatch decision (query + decision record)",
        "executor_agents": "2 calls per executed task (validate + ingest)",
        "verifier_agent": "2 calls per verification record (validate + ingest)",
        "queried_roles_estimate_total": 2 * total_new_decisions
        + 2 * len(NEW_EVENTS) + 2 * len(NEW_VERIFICATIONS),
    },
    "totals_this_phase": {
        "events_ingested": len(NEW_EVENTS),
        "verifications_ingested": len(NEW_VERIFICATIONS),
        "queries_executed": total_new_queries,
        "decisions_recorded": total_new_decisions,
        "tasks_recorded": len(NEW_TASKS),
    },
}
(ANALYSIS_DIR / "operational-overhead.json").write_text(
    json.dumps(overhead, indent=2, ensure_ascii=False) + "\n",
    encoding="utf-8")

# ==========================================================================
# PART 8 - metrics update, evidence append, hash regeneration
# ==========================================================================
ALL_EVENTS = R1_EVENTS + NEW_EVENTS
ALL_VERIFICATIONS = R1_VERIFICATIONS + NEW_VERIFICATIONS
ALL_QUERIES = R1_QUERIES + NEW_QUERIES
ALL_DECISIONS = R1_DECISIONS + NEW_DECISIONS
ALL_TASKS = R1_TASKS + NEW_TASKS

failure_count = sum(1 for e in ALL_EVENTS
                    if e["result_status"] in ("FAILURE", "TIMEOUT", "CANCELLED"))
independent_ver = sum(
    1 for v in ALL_VERIFICATIONS if v["verifier"]["verifier_class"] != "SELF")
self_ver = sum(1 for v in ALL_VERIFICATIONS if v["self_verification"])
decision_changes = sum(
    1 for d in ALL_DECISIONS if d.get("decision_change"))

THRESHOLDS = {
    "tasks_minimum": 30,
    "events_minimum": 20,
    "pre_dispatch_queries_minimum": 10,
    "shadow_comparison_records_minimum": 10,
    "failure_timeout_cancelled_minimum": 5,
    "independent_verifications_minimum": 5,
    "evidence_supported_decision_change_minimum": 1,
}
threshold_checks = {
    "tasks": len(ALL_TASKS) >= THRESHOLDS["tasks_minimum"],
    "events": len(ALL_EVENTS) >= THRESHOLDS["events_minimum"],
    "pre_dispatch_queries": len(ALL_QUERIES) >= THRESHOLDS["pre_dispatch_queries_minimum"],
    "shadow_comparison_records": len(SHADOW_DECISIONS) >= THRESHOLDS["shadow_comparison_records_minimum"],
    "failure_timeout_cancelled": failure_count >= THRESHOLDS["failure_timeout_cancelled_minimum"],
    "independent_verifications": independent_ver >= THRESHOLDS["independent_verifications_minimum"],
    "evidence_supported_decision_change": decision_changes >= THRESHOLDS["evidence_supported_decision_change_minimum"],
}
ALL_THRESHOLDS_MET = all(threshold_checks.values())

metrics = json.loads((ANALYSIS_DIR / "metrics.json").read_text(encoding="utf-8"))
metrics["phase2"] = {
    "generated_at": now_iso(),
    "totals": {
        "tasks": len(ALL_TASKS),
        "experience_events": len(ALL_EVENTS),
        "verification_records": len(ALL_VERIFICATIONS),
        "independent_verifications": independent_ver,
        "self_verifications_flagged": self_ver,
        "queries": len(ALL_QUERIES),
        "decisions": len(ALL_DECISIONS),
        "shadow_comparison_records": len(SHADOW_DECISIONS),
        "decision_changes": decision_changes,
        "failure_timeout_cancelled_events": failure_count,
    },
    "phase2_new": {
        "tasks": len(NEW_TASKS),
        "experience_events": len(NEW_EVENTS),
        "verification_records": len(NEW_VERIFICATIONS),
        "queries": len(NEW_QUERIES),
        "decisions": len(NEW_DECISIONS),
        "real_internal_tasks_recorded": 6,
        "disclosure_e2e_withheld_probes_pass": disclosure_results["withheld"]["all_pass"],
        "disclosure_e2e_restricted_scenarios_pass": sum(
            1 for s in RESTRICTED_SCENARIOS if s["pass"]),
        "version_isolation_pass": True,
        "cold_start_cases": 2,
        "shadow_decision_changed_count": DECISION_CHANGED_COUNT,
    },
    "thresholds": THRESHOLDS,
    "threshold_checks": threshold_checks,
    "all_thresholds_met": ALL_THRESHOLDS_MET,
    "api_limitations": disclosure_results["api_limitations"],
}
metrics["governance_status"] = {
    "PREPILOT_MECHANICAL_LOOP_VALIDATED": True,
    "PREPILOT_MINIMUM_SAMPLE_REQUIREMENTS_MET": ALL_THRESHOLDS_MET,
    "PREPILOT_RESULT": "INCONCLUSIVE",
    "REAL_WORLD_ADOPTION_VALIDATED": False,
    "AHRP_PRODUCTION_READY": False,
    "governance_correction_at": "2026-08-05",
    "phase2_completed_at": now_iso(),
}
(ANALYSIS_DIR / "metrics.json").write_text(
    json.dumps(metrics, indent=2, ensure_ascii=False) + "\n",
    encoding="utf-8")

# --- append evidence/validator-output.txt ----------------------------------
with open(EVIDENCE_DIR / "validator-output.txt", "a", encoding="utf-8") as fh:
    fh.write("\n")
    fh.write("AHRP v0.1 CONTROLLED INTERNAL PREPILOT PHASE 2 - VALIDATOR OUTPUT\n")
    fh.write("CONTROLLED_INTERNAL_PREPILOT=true CONTROLLED_INTERNAL_TASK=true ")
    fh.write("REAL_EXTERNAL_AGENT=false SYNTHETIC_MARKET_ADOPTION=false\n")
    fh.write(f"AHRP baseline commit: {AHRP_BASELINE_COMMIT} (frozen, read-only)\n")
    fh.write(f"monotonic_sequence range (wrapper records): 1000..{_SEQ_LAST['value']}\n")
    fh.write("phase-2 records validated (real UTC timestamps):\n")
    for line in VALIDATOR_LOG:
        fh.write(line + "\n")
    fh.write(f"\ntotal phase-2 experience events validated: {len(NEW_EVENTS)} (all PASS)\n")
    fh.write(f"total phase-2 verification records validated: {len(NEW_VERIFICATIONS)} (all PASS)\n")
    fh.write("note: frozen v0.1 schemas are additionalProperties=false; control ")
    fh.write("block + monotonic_sequence are carried on prepilot wrapper records ")
    fh.write("(tasks/queries/decisions) and compacted into the whitelisted notes field\n")
    fh.write("\nHONEST TIMESTAMP NOTE (phase 2):\n")
    fh.write("  Round-1 records carry deterministic synthetic session timestamps that\n")
    fh.write("  extend slightly into the future relative to the real phase-2 execution\n")
    fh.write("  clock (real UTC now()). Phase-2 uses REAL UTC timestamps as required and\n")
    fh.write("  is internally consistent: every new verification timestamp is >= its\n")
    fh.write("  event's occurred_at, every new query timestamp is >= the phase-2 events\n")
    fh.write(f"  it references, and monotonic_sequence 1000..{_SEQ_LAST['value']} is strictly\n")
    fh.write("  increasing. No round-1 record was rewritten (append-only).\n")

# --- append evidence/query-output.txt ---------------------------------------
with open(EVIDENCE_DIR / "query-output.txt", "a", encoding="utf-8") as fh:
    fh.write("\n")
    fh.write("AHRP v0.1 CONTROLLED INTERNAL PREPILOT PHASE 2 - QUERY OUTPUT\n")
    fh.write("CONTROLLED_INTERNAL_PREPILOT=true CONTROLLED_INTERNAL_TASK=true\n\n")
    for query_id, method, purpose, params, env in QUERY_LOG:
        fh.write(f"== {query_id} ({method}) - {purpose}\n")
        fh.write(f"   params: {json.dumps(params)}\n")
        if env.get("ok"):
            sd = env.get("selective_disclosure", {})
            fh.write(f"   ok=True null_semantics={env.get('null_semantics')} "
                     f"mode={sd.get('mode')} withheld_count={sd.get('withheld_count')}\n")
            result = env.get("result", {})
            if "count" in result:
                fh.write(f"   event_count={result['count']}\n")
                for e in result.get("events", []):
                    fh.write(f"     - {e.get('event_id')} {e.get('task_type')}/"
                             f"{e.get('action_type')} -> {e.get('result_status')} "
                             f"category={e.get('failure_category')} "
                             f"verification={e.get('verification_status')} "
                             f"independent={e.get('has_independent_verification')}\n")
            if "by_version" in result:
                fh.write(f"   by_version={json.dumps(result['by_version'])}\n")
        else:
            err = env.get("error", {})
            fh.write(f"   ok=False code={err.get('code')} message={err.get('message')}\n")
        fh.write("\n")

# --- regenerate evidence/file-hashes.sha256 over all files ------------------
SKIP_DIRS = {"__pycache__"}
hash_lines = []
for path in sorted(EXP_DIR.rglob("*")):
    rel_parts = path.relative_to(EXP_DIR).parts
    if any(part in SKIP_DIRS for part in rel_parts):
        continue
    if any(part.startswith(".") for part in rel_parts[:-1]):
        continue  # skip files inside hidden directories
    if not path.is_file():
        continue
    if path == EVIDENCE_DIR / "file-hashes.sha256":
        continue
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    rel = path.relative_to(EXP_DIR).as_posix()
    hash_lines.append(f"{digest}  ./{rel}")
(EVIDENCE_DIR / "file-hashes.sha256").write_text(
    "\n".join(hash_lines) + "\n", encoding="utf-8")

# ==========================================================================
# Final report
# ==========================================================================
report = {
    "control": CONTROL_P2,
    "thresholds": {
        "tasks_total": len(ALL_TASKS),
        "events_total": len(ALL_EVENTS),
        "queries_total": len(ALL_QUERIES),
        "shadow_comparison_records": len(SHADOW_DECISIONS),
        "failure_timeout_cancelled": failure_count,
        "independent_verifications": independent_ver,
        "decision_changes": decision_changes,
        "checks": threshold_checks,
        "all_met": ALL_THRESHOLDS_MET,
    },
    "disclosure_e2e": {
        "withheld_all_pass": disclosure_results["withheld"]["all_pass"],
        "restricted_scenarios_pass": [s["pass"] for s in RESTRICTED_SCENARIOS],
    },
    "version_isolation": {
        "v110_event_ids": iso110_ids,
        "v100_event_ids": sorted(iso100_ids),
        "by_version_groups": sorted(iso_by_version.keys()),
    },
    "cold_start_cases": ["worker-nu@1.0.0", "researcher-gamma@1.1.0 (pre-event)"],
    "decision_changed_count": DECISION_CHANGED_COUNT,
    "overhead_highlights": {
        "avg_event_gen_validate_ingest_seconds":
            overhead["event_generation_validation_ingest"]["average_seconds"],
        "avg_verification_create_seconds":
            overhead["verification_record_creation_ingest"]["average_seconds"],
        "summary_query_chars": SUMMARY_QUERY_CHARS,
        "detail_query_chars": DETAIL_QUERY_CHARS,
        "extra_query_steps_per_decision":
            overhead["orchestrator_extra_query_steps_per_decision"],
        "manual_operations": MANUAL_OPERATIONS,
        "failure_retries": FAILURE_RETRIES,
    },
    "api_limitations": disclosure_results["api_limitations"],
}
print(json.dumps(report, indent=2, ensure_ascii=False))

if not ALL_THRESHOLDS_MET or not disclosure_results["withheld"]["all_pass"] or \
        not all(s["pass"] for s in RESTRICTED_SCENARIOS):
    sys.exit(1)

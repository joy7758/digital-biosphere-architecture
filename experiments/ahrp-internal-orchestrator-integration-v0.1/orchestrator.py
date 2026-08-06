"""Programmatic orchestrator component for the AHRP internal orchestrator
integration trial (AHRP 内部编排器集成试验 v0.1).

程序化编排器组件。

The component is a deterministic, pre-programmed decision routine: it
receives a task, selects a worker component (or routes to manual review),
and records its delegation rationale. In AHRP_ASSISTED_MODE it issues real
queries against the AHRP HistoryStore (unmodified AHRP v0.1 query engine)
and may change its delegation decision based ONLY on the structured summary
fields returned by the query envelope. It never consumes free text.

These executable components are not evidence of autonomous,
model-based, or externally operated agent adoption.
这些可执行组件不能证明自主智能体、模型型智能体或外部智能体采用了 AHRP。

Decision policy (documented, deterministic):

1. before_query_decision: static type routing (task type -> worker role).
2. For every candidate agent, query AHRP history for the exact
   (identity_ref, agent_version, task_type) triple.
3. A candidate is VETOED when its history shows a failure-class event
   whose failure_category matches a declared risk of the current task:
     * CAPABILITY_LIMIT failure + task carries the capability-risk
       requirement of that task type  -> CAPABILITY_LIMIT_HISTORY
     * POLICY_RESTRICTION failure + task carries the policy-risk
       requirement of that task type   -> POLICY_RESTRICTION_HISTORY
4. On any query error envelope (Q_*), the orchestrator FAILS CLOSED: it
   keeps the before-query decision and performs no further queries.
5. NO_RECORD never produces a decision change.
6. If every candidate is vetoed, the decision becomes MANUAL_REVIEW.

The policy deliberately produces no scores, rankings, trust or reliability
values (AHRP Constitution Section 9 non-goals).
"""

import json
import time
from typing import Any, Dict, List, Optional

TASK_TYPE_MAP = {
    "coding": "CODING",
    "research": "RESEARCH",
    "review": "VERIFICATION",
    "data_processing": "DATA_PROCESSING",
}

CANDIDATES_BY_TYPE = {
    "coding": ["did:example:worker-alpha"],
    "research": ["did:example:worker-beta"],
    "review": ["did:example:worker-gamma"],
    "data_processing": [
        "did:example:worker-alpha",
        "did:example:worker-beta",
        "did:example:worker-gamma",
    ],
}

# requirement key that makes a task risky for a given task type
RISK_REQUIREMENT = {
    "coding": "requires_dependency_resolution",
    "research": "requires_external_sources",
    "review": "requires_security_review",
}

FAILURE_CLASS_STATUSES = {"FAILURE", "TIMEOUT", "CANCELLED", "PARTIAL_SUCCESS"}


class AhrpAccessForbidden(RuntimeError):
    """Raised when any AHRP read is attempted in NO_AHRP_MODE."""


class ForbiddenHistoryStore:
    """Guard passed to the orchestrator in NO_AHRP_MODE. Any query attempt
    raises, proving the baseline phase never reads AHRP history."""

    def query_events(self, **kwargs):
        raise AhrpAccessForbidden(
            "AHRP history read attempted in NO_AHRP_MODE (forbidden)"
        )


class OrchestratorAgent:
    def __init__(self, registration: dict, agent_versions: Dict[str, str]):
        self.agent_id = registration["agent_id"]
        self.agent_version = registration["agent_version"]
        self.capabilities = registration["capabilities"]
        self.boundary = registration["boundary"]
        self._agent_versions = agent_versions

    # ------------------------------------------------------------- routing
    def decide(self, task: dict, history_store) -> Dict[str, Any]:
        """Single entry point. In NO_AHRP_MODE the runner passes a
        ForbiddenHistoryStore: any accidental query attempt raises."""
        if isinstance(history_store, ForbiddenHistoryStore):
            return self.type_routing(task)
        return self.select_with_history(task, history_store)

    def type_routing(self, task: dict) -> Dict[str, Any]:
        """Static capability match, no history consulted."""
        candidates = CANDIDATES_BY_TYPE[task["task_type"]]
        selected = candidates[0]
        return {
            "decision": "DELEGATE",
            "selected_agent": selected,
            "selection_reason": (
                f"TYPE_ROUTING: {task['task_type']} -> {selected} "
                "(static capability match, no history consulted)"
            ),
        }

    # ------------------------------------------------------ history policy
    def _classify(self, task: dict, summaries: List[dict], agent_ref: str,
                  history_used: List[dict]) -> bool:
        """Return True if the candidate must be vetoed."""
        risk_key = RISK_REQUIREMENT.get(task["task_type"])
        task_is_risky = bool(risk_key and task["requirements"].get(risk_key))
        vetoed = False
        for summary in summaries:
            status = summary.get("result_status")
            category = summary.get("failure_category")
            event_id = summary.get("event_id")
            if status in FAILURE_CLASS_STATUSES and task_is_risky:
                if category == "CAPABILITY_LIMIT":
                    history_used.append({
                        "event_id": event_id,
                        "agent_ref": agent_ref,
                        "reason": "CAPABILITY_LIMIT_HISTORY",
                    })
                    vetoed = True
                elif category == "POLICY_RESTRICTION":
                    history_used.append({
                        "event_id": event_id,
                        "agent_ref": agent_ref,
                        "reason": "POLICY_RESTRICTION_HISTORY",
                    })
                    vetoed = True
            elif status == "SUCCESS":
                history_used.append({
                    "event_id": event_id,
                    "agent_ref": agent_ref,
                    "reason": "POSITIVE_HISTORY",
                })
        return vetoed

    def select_with_history(self, task: dict, store) -> Dict[str, Any]:
        """AHRP_ASSISTED_MODE decision: query real history, then decide."""
        before = self.type_routing(task)
        mapped_type = TASK_TYPE_MAP[task["task_type"]]
        candidates = CANDIDATES_BY_TYPE[task["task_type"]]

        queries: List[Dict[str, Any]] = []
        history_used: List[Dict[str, Any]] = []
        vetoed: List[str] = []
        all_no_record = True

        for candidate in candidates:
            params = {
                "identity_ref": candidate,
                "agent_version": self._agent_versions[candidate],
                "task_type": mapped_type,
            }
            if task.get("inject_query_error") and not queries:
                # controlled fail-closed probe: unhashable identity_ref
                # is rejected by the engine's type guard (CF-1)
                params["identity_ref"] = [candidate]
            start = time.perf_counter()
            envelope = store.query_events(**params)
            latency_ms = (time.perf_counter() - start) * 1000.0
            tokens_est = len(json.dumps(envelope, sort_keys=True)) // 4

            entry: Dict[str, Any] = {
                "params": {k: v if not isinstance(v, list) else "<invalid:list>"
                           for k, v in params.items()},
                "ok": envelope.get("ok", False),
                "latency_ms": round(latency_ms, 4),
                "tokens_estimated": tokens_est,
            }
            if not entry["ok"]:
                entry["error_code"] = envelope["error"]["code"]
                entry["events_returned"] = 0
                queries.append(entry)
                history_used.append({
                    "event_id": None,
                    "agent_ref": candidate,
                    "reason": "QUERY_ERROR",
                })
                # FAIL CLOSED: keep before-query decision, stop querying
                return self._finalize(
                    task, before, before, queries, history_used,
                    fail_closed_reason=entry["error_code"])

            semantics = envelope.get("null_semantics")
            events = envelope["result"]["events"] if envelope["result"] else []
            entry["null_semantics"] = semantics
            entry["events_returned"] = len(events)
            queries.append(entry)

            if semantics != "NO_RECORD":
                all_no_record = False
            if not events:
                history_used.append({
                    "event_id": None,
                    "agent_ref": candidate,
                    "reason": "NO_RECORD",
                })
                continue
            if self._classify(task, events, candidate, history_used):
                vetoed.append(candidate)

        eligible = [c for c in candidates if c not in vetoed]
        if not eligible:
            after = {
                "decision": "MANUAL_REVIEW",
                "selected_agent": None,
                "selection_reason": (
                    "HISTORY_VETO: all candidate agents carry matching "
                    "failure history for this task's declared risk; "
                    "route to human manual review"
                ),
            }
        else:
            selected = eligible[0]
            if selected == before["selected_agent"] and len(vetoed) == 0:
                after = dict(before)
            else:
                after = {
                    "decision": "DELEGATE",
                    "selected_agent": selected,
                    "selection_reason": (
                        f"HISTORY_REROUTE: primary candidate vetoed by "
                        f"history; delegate to {selected}"
                    ),
                }
        return self._finalize(task, before, after, queries, history_used)

    def _finalize(self, task: dict, before: Dict[str, Any], after: Dict[str, Any],
                  queries: List[dict], history_used: List[dict],
                  fail_closed_reason: Optional[str] = None) -> Dict[str, Any]:
        changed = (after["decision"] != before["decision"]
                   or after["selected_agent"] != before["selected_agent"])
        record = {
            "task_id": task["task_id"],
            "mode": "AHRP_ASSISTED_MODE",
            "orchestrator_agent_id": self.agent_id,
            "orchestrator_agent_version": self.agent_version,
            "before_query_decision": before,
            "ahrp_query": queries,
            "history_used": history_used,
            "after_query_decision": after,
            "decision_changed": changed,
            "query_count": len(queries),
        }
        if fail_closed_reason is not None:
            record["fail_closed"] = fail_closed_reason
        return record

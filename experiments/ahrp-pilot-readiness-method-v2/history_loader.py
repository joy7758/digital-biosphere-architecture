"""History loading and correct HistoryStore envelope handling.

All queries go through the real ``AHRP.query.engine.HistoryStore``. This
module enforces the envelope discipline that PR #12 violated:

* never iterate the envelope itself -- read ``result.events``;
* always check ``ok`` first; an error envelope fails closed;
* always distinguish ``null_semantics``: NONE / NO_RECORD / WITHHELD;
* no compensating logic that forces a decision change when history is empty.
"""

import json
import os
from typing import Any, Dict, List

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
AHRP_DIR = os.path.join(REPO_ROOT, "AHRP")

import sys  # noqa: E402

for _p in (REPO_ROOT, AHRP_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from query.engine import HistoryStore  # noqa: E402


class QueryOutcome:
    """Normalized view of one HistoryStore query."""

    def __init__(self, status: str, events: List[Dict[str, Any]],
                 withheld_count: int = 0,
                 error_code: str = "") -> None:
        # status: OK / NO_RECORD / WITHHELD / QUERY_ERROR
        self.status = status
        self.events = events
        self.withheld_count = withheld_count
        self.error_code = error_code


def load_jsonl(path: str) -> List[Dict[str, Any]]:
    records = []
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def build_store() -> HistoryStore:
    """Ingest the frozen seed history through the real AHRP validator.

    ``ingest_event`` / ``ingest_verification`` validate every record and
    fail closed (raise) on any schema or binding violation, so reaching the
    end of this function is itself a validation statement.
    """
    store = HistoryStore()
    events_path = os.path.join(HERE, "config", "history-events.jsonl")
    verifications_path = os.path.join(
        HERE, "config", "history-verifications.jsonl")
    # Verifications first: event references must resolve at ingest time for
    # later strong-binding checks (ingest order does not change semantics,
    # but this mirrors a holder that already stores verification records).
    for record in load_jsonl(verifications_path):
        store.ingest_verification(record)
    for event in load_jsonl(events_path):
        store.ingest_event(event)
    return store


def query_agent_history(store: HistoryStore, identity_ref: str,
                        agent_version: str, task_type: str) -> QueryOutcome:
    """Query independently verified events for (agent, version, task_type).

    Correct envelope handling:
    * ``ok == False`` -> QUERY_ERROR (fail closed; caller must not treat
      this as NO_RECORD);
    * ``null_semantics == WITHHELD`` -> WITHHELD (records exist but are not
      disclosed; caller must stay conservative);
    * ``null_semantics == NO_RECORD`` -> NO_RECORD;
    * otherwise events come from ``result.events`` only.
    """
    envelope = store.query_events(
        identity_ref=identity_ref,
        agent_version=agent_version,
        task_type=task_type,
        require_independent_verification=True,
    )
    if not envelope.get("ok", False):
        error = envelope.get("error", {})
        return QueryOutcome("QUERY_ERROR", [], error_code=error.get("code", ""))
    semantics = envelope.get("null_semantics")
    withheld = envelope.get("selective_disclosure", {}).get("withheld_count", 0)
    if semantics == "WITHHELD":
        return QueryOutcome("WITHHELD", [], withheld_count=withheld)
    if semantics == "NO_RECORD":
        return QueryOutcome("NO_RECORD", [], withheld_count=withheld)
    events = envelope.get("result", {}).get("events", [])
    return QueryOutcome("OK", events, withheld_count=withheld)

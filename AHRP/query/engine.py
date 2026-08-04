"""AHRP Query Interface reference engine (Python 3 stdlib only).

Design defaults (SPEC v0.1 Chapter 7):

* Selective Disclosure First: the default query returns an Experience Summary
  (raw counts ``verified_events`` / ``total_events``); detailed events are
  returned only on explicit drill-down. No derived ratios, scores or rankings
  are ever produced (Constitution Section 9 non-goals).
* Three-state null semantics: NO_RECORD / WITHHELD / NOT_APPLICABLE are
  distinct and machine-readable.
* Identity continuity fail-closed: summaries are computed per agent_version;
  cross-version merging is refused by default (Constitution Section 8).
* DATA != INSTRUCTION: free-text fields travel only in the restricted_text
  content channel and are excluded from every summary.

Remediation round (Defects 1/2/3/4):

* Selective Disclosure is now genuinely enforced (Defect 1). The plain string
  ``capability="detail"`` is a *request*, never an authorization. Detail reads
  walk a disclosure truth table (scope x expiry x revocation x external policy
  decision) and fail closed; unauthorized reads return stable ``Q_*`` machine
  error codes and never silently return details.
* Verification <-> Event strong binding (Defect 2). An event's effective
  verification comes ONLY from verification objects explicitly listed in its
  ``verification_references``; weak association (event_id / agent / time
  scanning) is prohibited. No explicit references -> NOT_ASSESSED.
* Self vs independent verification separation (Defect 3). The summary
  ``verified_events`` count includes only independently verified events; pure
  SELF verification is retained as an explicitly downgraded weak signal and is
  reported in dedicated split fields.
* Query request validation & stable error semantics (Defect 4). Every query
  parameter is validated BEFORE the engine runs; invalid requests never reach
  the engine, are never mapped to NO_RECORD, and never surface raw Python
  exceptions.

Independent-review round (audit r2 fixes):

* CF-1: type guards on every frozenset membership check so unhashable query
  inputs (list / dict / set / number) return stable Q_* codes instead of a
  bare TypeError.
* CF-2 / CF-3: validation gates on ``summary()``, ``get_event()`` and
  ``get_failure_category()`` BEFORE any lookup.
* MF-1: independence counting is limited to event-level conferring records.
* MF-2: NOT_ASSESSED is filtered out of conferring statuses.
* MF-3: WITHHELD guard on ``verifications_for_event`` /
  ``event_verification_status``.
* MF-4: no caller-injectable clock on public methods (module-level ``_clock``).
* MF-5: ``disclosure_scope`` is a real query filter.
* MF-7: ``Q_INVALID_PARAM`` for limit/pagination validation failures.
* AF-1: malformed ``expires_at`` fails closed (treated as expired).

Trust-boundary hardening round (audit r3 fixes):

* R3-1: Disclosure Context anti-forgery. Format-only validation is NEVER
  sufficient for RESTRICTED detail: a configured ``policy_decision_resolver``
  hook must confirm the external policy decision reference, and without a
  resolver every RESTRICTED detail read fails closed
  (``Q_POLICY_DECISION_REQUIRED``). The context must additionally carry an
  ``issuer`` and a ``decision_id``.
* R3-2: unified disclosure guard. ``verifications_for_event`` /
  ``event_verification_status`` / ``get_failure_category`` route through the
  same disclosure truth table as ``get_event`` via
  ``_require_detail_disclosure``; RESTRICTED detail-level projections are
  denied without a valid, resolver-confirmed disclosure context.
* R3-3: event-level verification binding MUST declare ``scope.agent_ref``
  AND ``scope.agent_version``, and both must match the subject event
  (fail-closed BINDING_INCOMPLETE / mismatch -> INVALID).
* R3-4: NOT_ASSESSED records never confer independence: the SELF /
  independent classification happens only for records that pass BOTH the
  event-level filter AND the NOT_ASSESSED filter.
"""

from __future__ import annotations

import copy
import re
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from validator.core import (
    FAILURE_CLASS_STATUSES,
    validate_experience_event,
    validate_verification_record,
)

PROTOCOL = "AHRP"
PROTOCOL_VERSION = "0.1.0"
SYNTHETIC_ONLY_NOTE = "Reference implementation; synthetic data only."

# --------------------------------------------------------------------------
# Machine enums (Machine Enumerability First). Used for strict, case-sensitive
# query-parameter validation (Defect 4): any value outside these sets is an
# invalid request, never silently coerced to NO_RECORD.
# --------------------------------------------------------------------------
TASK_TYPE_ENUM = frozenset({
    "RESEARCH", "CODING", "ORCHESTRATION", "DATA_PROCESSING",
    "VERIFICATION", "ANALYSIS", "OTHER",
})
ACTION_TYPE_ENUM = frozenset({
    "EXECUTE", "DELEGATE", "REVIEW", "RETRY", "ABORT", "OTHER",
})
RESULT_STATUS_ENUM = frozenset({
    "SUCCESS", "PARTIAL_SUCCESS", "FAILURE", "TIMEOUT", "CANCELLED",
})
VERIFICATION_STATUS_ENUM = frozenset({
    "VERIFIED", "PARTIALLY_VERIFIED", "NOT_ASSESSED", "INVALID", "CONFLICTED",
})
VERIFIER_CLASS_ENUM = frozenset({
    "DBOS", "NAMED_VERIFIER", "ORCHESTRATOR", "SELF",
    "INDEPENDENT_AGENT", "ORGANIZATION", "HUMAN", "SYSTEM_BENCHMARK",
})
DISCLOSURE_SCOPE_ENUM = frozenset({
    "PUBLIC", "FEDERATED", "RESTRICTED", "WITHHELD",
})
CAPABILITY_ENUM = frozenset({"summary", "detail"})
REVOCATION_STATUS_ENUM = frozenset({"ACTIVE", "REVOKED"})

# Supported protocol / policy versions (fail-closed on anything else).
SUPPORTED_QUERY_PROTOCOL_VERSIONS = frozenset({"0.1", "0.1.0"})
SUPPORTED_POLICY_VERSIONS = frozenset({"0.1"})

# Scopes whose detail is readable without an external policy decision
# (federation-readable tiers). RESTRICTED additionally requires a valid,
# scope-matching external disclosure permission; WITHHELD never returns detail.
OPEN_DISCLOSURE_SCOPES = frozenset({"PUBLIC", "FEDERATED"})

# Independence classification (Defect 3): SELF is the only non-independent
# verifier class; every other class is independent.
SELF_CLASS = "SELF"
INDEPENDENT_VERIFIER_CLASSES = VERIFIER_CLASS_ENUM - {SELF_CLASS}

# Verification-status precedence for deriving an event-level status from its
# referenced verification records (worst-conflict-first, fail-closed).
_STATUS_PRIORITY = ("CONFLICTED", "INVALID", "PARTIALLY_VERIFIED", "VERIFIED")

# F10: only verifications scoped to the experience event itself and covering
# an event-level aspect count toward event-level aggregation. EVIDENCE_BINDING
# verifies an evidence reference, not the event; NOT_ASSESSED asserts nothing.
_EVENT_SCOPE_SUBJECT_TYPE = "EXPERIENCE_EVENT"
_EVENT_LEVEL_ASPECTS = frozenset({"FULL_EVENT", "OCCURRENCE", "RESULT_STATUS"})

# F4: whitelisted free-text (DATA channel) fields, including nested dot paths.
# They must never enter structured_facts or any decision path.
FREE_TEXT_FIELDS = ("notes", "agent_reference.identity_note")

# Summary projection fields for a single event (no free text).
_SUMMARY_FIELDS = (
    "event_id",
    "agent_version",
    "task_type",
    "action_type",
    "result_status",
    "failure_category",
    "occurred_at",
    "verification_status",
    "evidence_availability",
)

# RFC 3339 date-time shape used for query time-window validation (Defect 4).
_DATETIME_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})$"
)

# --------------------------------------------------------------------------
# Stable machine error codes for the query interface (Defect 4 / Defect 1).
# --------------------------------------------------------------------------
Q_INVALID_ENUM = "Q_INVALID_ENUM"
Q_INVALID_TIME_FORMAT = "Q_INVALID_TIME_FORMAT"
Q_INVALID_TIME_RANGE = "Q_INVALID_TIME_RANGE"
Q_INVALID_REFERENCE = "Q_INVALID_REFERENCE"
Q_UNSUPPORTED_VERSION = "Q_UNSUPPORTED_VERSION"
Q_DISCLOSURE_DENIED = "Q_DISCLOSURE_DENIED"
Q_DISCLOSURE_EXPIRED = "Q_DISCLOSURE_EXPIRED"
Q_DISCLOSURE_REVOKED = "Q_DISCLOSURE_REVOKED"
Q_POLICY_DECISION_REQUIRED = "Q_POLICY_DECISION_REQUIRED"
Q_NO_RECORD = "Q_NO_RECORD"
Q_INVALID_PARAM = "Q_INVALID_PARAM"
Q_INTERNAL_ERROR = "Q_INTERNAL_ERROR"

QUERY_ERROR_CODES = (
    Q_INVALID_ENUM, Q_INVALID_TIME_FORMAT, Q_INVALID_TIME_RANGE,
    Q_INVALID_REFERENCE, Q_UNSUPPORTED_VERSION, Q_DISCLOSURE_DENIED,
    Q_DISCLOSURE_EXPIRED, Q_DISCLOSURE_REVOKED, Q_POLICY_DECISION_REQUIRED,
    Q_NO_RECORD, Q_INVALID_PARAM,
)

# Required fields of a machine-readable Disclosure Context (Defect 1 / R3-1).
# AHRP validates only the format / status / scope of an external policy
# decision; it never becomes a second AuthZEN/ODRL/identity system. R3-1 adds
# ``issuer`` and ``decision_id`` so a fabricated context is structurally
# incomplete without naming WHO decided and WHICH decision it cites; the
# decision reference itself is only trusted after the configured policy
# decision resolver confirms it (fail-closed without a resolver).
DISCLOSURE_CONTEXT_FIELDS = (
    "requester_reference",
    "requested_disclosure_scope",
    "granted_scope",
    "external_policy_decision_reference",
    "policy_version",
    "evaluated_at",
    "expiry",
    "revocation_status",
    "issuer",
    "decision_id",
)


class SyntheticPolicyResolver:
    """Test/simulation policy-decision resolver (SYNTHETIC_ONLY).

    Audit fix R3-1: RESTRICTED detail access is granted only when a
    ``policy_decision_resolver`` confirms the context's
    ``external_policy_decision_reference``. This synthetic resolver accepts
    references on a configurable whitelist; anything else is denied. Real
    deployments would inject a resolver that checks the actual external
    policy decision system; AHRP itself never issues decisions.
    """

    def __init__(self, allowed_references=(), default_valid: bool = False):
        self._allowed = set(allowed_references)
        self._default_valid = bool(default_valid)

    def __call__(self, reference: Any) -> Dict[str, Any]:
        if not _is_nonempty_string(reference):
            return {"valid": False, "reason": "MISSING_REFERENCE"}
        if reference in self._allowed:
            return {"valid": True, "reference": reference}
        if self._default_valid:
            return {"valid": True, "reference": reference}
        return {"valid": False, "reason": "UNKNOWN_REFERENCE"}


class NullSemantics(str, Enum):
    """Three distinguishable empty-value states (SPEC v0.1 Chapter 11)."""

    NONE = "NONE"                          # content is present
    NO_RECORD = "NO_RECORD"                # nothing was ever recorded
    WITHHELD = "WITHHELD"                  # record exists, disclosure withheld
    NOT_APPLICABLE = "NOT_APPLICABLE"      # the question does not apply


class IngestError(ValueError):
    """Raised when a document fails reference validation (fail-closed)."""

    def __init__(self, validation_result):
        self.validation_result = validation_result
        super().__init__(f"ingest rejected: {validation_result.to_dict()}")


# --------------------------------------------------------------------------
# Envelope builders
# --------------------------------------------------------------------------
def _envelope(mode: str, null_semantics: NullSemantics, result: Any,
              restricted_fields: Optional[List[str]] = None,
              withheld_count: int = 0) -> Dict[str, Any]:
    return {
        "ok": True,
        "protocol": PROTOCOL,
        "schema_version": PROTOCOL_VERSION,
        "content_channel": {
            "structured_facts": "payload fields not listed in restricted_text",
            "restricted_text": list(restricted_fields or []),
        },
        "selective_disclosure": {"mode": mode, "withheld_count": withheld_count},
        "null_semantics": null_semantics.value,
        "result": result,
    }


def _error_envelope(code: str, field: Optional[str], message: str,
                    retryable: bool = False) -> Dict[str, Any]:
    """Unified machine-readable error envelope (Defect 4). Never raises."""
    return {
        "ok": False,
        "protocol": PROTOCOL,
        "schema_version": PROTOCOL_VERSION,
        "error": {
            "code": code,
            "field": field,
            "message": message,
            "retryable": retryable,
        },
    }


def _is_valid_instant_string(value: Any) -> bool:
    """Strict RFC 3339 shape check (case-sensitive, no coercion)."""
    if not isinstance(value, str):
        return False
    if not _DATETIME_RE.match(value):
        return False
    try:
        _parse_instant(value)
        return True
    except (ValueError, OverflowError):
        return False


def _parse_instant(value: str):
    """F5: parse an RFC 3339 date-time into an absolute instant (UTC epoch).

    Comparisons and ordering use instants, never string lexicographic order,
    so mixed offsets ('Z' vs '+08:00') compare correctly. Callers must have
    validated the shape first (Defect 4) so this never raises on query input.
    """
    candidate = value[:-1] + "+00:00" if value.endswith("Z") else value
    return datetime.fromisoformat(candidate).timestamp()


def _now_instant() -> float:
    return datetime.now(timezone.utc).timestamp()


# Module-level clock (audit fix MF-4): public query methods never accept a
# caller-supplied clock value, so expiry enforcement cannot be bypassed by
# injecting ``now``. Tests monkey-patch this function instead.
_clock = _now_instant


def _get_path(doc: Dict[str, Any], dotted: str) -> Any:
    """Resolve a dotted path (e.g. 'agent_reference.identity_note')."""
    node: Any = doc
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


def _is_nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and len(value) > 0


def _is_enum_member(value: Any, enum: frozenset) -> bool:
    """Type guard (audit fix CF-1): unhashable inputs (list / dict / set /
    ...) must never reach a frozenset membership check, which would raise a
    bare ``TypeError``; any non-string value is simply not a legal enum
    value and yields a stable ``Q_INVALID_ENUM``-class error instead."""
    return isinstance(value, str) and value in enum


# --------------------------------------------------------------------------
# Disclosure Context validation + enforcement (Defect 1)
# --------------------------------------------------------------------------
def _validate_disclosure_context(ctx: Any) -> Optional[Tuple[str, str]]:
    """Validate the format / status of a Disclosure Context.

    Returns ``(error_code, message)`` on failure or ``None`` when the context
    is structurally acceptable. AHRP checks format, enum legality, and version
    support only; it does NOT resolve or re-issue the external policy decision.
    """
    if not isinstance(ctx, dict):
        return (Q_POLICY_DECISION_REQUIRED,
                "disclosure context must be a machine-readable object")
    for field in DISCLOSURE_CONTEXT_FIELDS:
        if field not in ctx or ctx[field] is None:
            return (Q_POLICY_DECISION_REQUIRED,
                    f"disclosure context is missing required field {field!r}")
    if not _is_nonempty_string(ctx["requester_reference"]):
        return (Q_POLICY_DECISION_REQUIRED,
                "requester_reference must be a non-empty string")
    # R3-1: the context must name the decision issuer and the decision id;
    # an anonymous or unidentified permission is never accepted.
    if not _is_nonempty_string(ctx["issuer"]):
        return (Q_POLICY_DECISION_REQUIRED,
                "disclosure context is missing a non-empty 'issuer'")
    if not _is_nonempty_string(ctx["decision_id"]):
        return (Q_POLICY_DECISION_REQUIRED,
                "disclosure context is missing a non-empty 'decision_id'")
    # CF-1 type guards: unhashable scope/status values are invalid contexts,
    # never a bare TypeError.
    if not _is_enum_member(ctx["requested_disclosure_scope"],
                           DISCLOSURE_SCOPE_ENUM):
        return (Q_POLICY_DECISION_REQUIRED,
                "requested_disclosure_scope is not a legal disclosure scope")
    if not _is_enum_member(ctx["granted_scope"], DISCLOSURE_SCOPE_ENUM):
        return (Q_POLICY_DECISION_REQUIRED,
                "granted_scope is not a legal disclosure scope")
    if not _is_nonempty_string(ctx["external_policy_decision_reference"]):
        return (Q_POLICY_DECISION_REQUIRED,
                "external_policy_decision_reference must be a non-empty string")
    if not _is_enum_member(ctx["revocation_status"], REVOCATION_STATUS_ENUM):
        return (Q_POLICY_DECISION_REQUIRED,
                "revocation_status must be ACTIVE or REVOKED")
    for field in ("evaluated_at", "expiry"):
        if not _is_valid_instant_string(ctx[field]):
            return (Q_POLICY_DECISION_REQUIRED,
                    f"disclosure context field {field!r} is not a valid "
                    "RFC 3339 date-time")
    return None


def _evaluate_detail_disclosure(event: Dict[str, Any],
                                disclosure_context: Any,
                                now: float,
                                policy_decision_resolver=None
                                ) -> Optional[Dict[str, Any]]:
    """Decide whether a detail read is permitted (disclosure truth table).

    Returns ``None`` when allowed, otherwise a ready-to-return error envelope.
    Fail-closed everywhere: WITHHELD is handled by the caller; unknown scopes,
    missing / malformed / expired / revoked policy decisions all deny.

    Audit fix R3-1: for RESTRICTED events, passing the format / enum / version
    checks is necessary but NOT sufficient. The context's
    ``external_policy_decision_reference`` must additionally be confirmed by
    the configured ``policy_decision_resolver``; with no resolver configured,
    ALL RESTRICTED detail access is denied (fail-closed). A caller-fabricated
    disclosure context can therefore never bypass RESTRICTED on its own.
    """
    disclosure = event.get("disclosure", {}) or {}
    scope = disclosure.get("disclosure_scope")

    # Unknown / undeclared scope -> fail-closed deny. CF-1 type guard: a
    # non-string scope value is unknown, never a bare TypeError.
    if not _is_enum_member(scope, DISCLOSURE_SCOPE_ENUM):
        return _error_envelope(
            Q_DISCLOSURE_DENIED, "disclosure.disclosure_scope",
            "undeclared or unknown disclosure scope is denied (fail-closed)")

    # Record-level revocation always denies detail.
    if disclosure.get("revoked") is True:
        return _error_envelope(
            Q_DISCLOSURE_REVOKED, "disclosure.revoked",
            "disclosure has been revoked; detail is denied")

    # Record-level expiry always denies detail. Audit fix AF-1: a present but
    # malformed expires_at is treated as expired (fail-closed), never skipped.
    expires_at = disclosure.get("expires_at")
    if expires_at is not None:
        if not _is_valid_instant_string(expires_at):
            return _error_envelope(
                Q_DISCLOSURE_EXPIRED, "disclosure.expires_at",
                "disclosure expiry is malformed; treated as expired "
                "(fail-closed)")
        if _parse_instant(expires_at) <= now:
            return _error_envelope(
                Q_DISCLOSURE_EXPIRED, "disclosure.expires_at",
                "disclosure has expired; detail is denied")

    # Federation-readable tiers need no external policy decision.
    if scope in OPEN_DISCLOSURE_SCOPES:
        return None

    # RESTRICTED: a valid, scope-matching external policy decision is REQUIRED.
    # The plain capability string is never an authorization.
    if scope == "RESTRICTED":
        if disclosure_context is None:
            return _error_envelope(
                Q_POLICY_DECISION_REQUIRED, "disclosure_context",
                "RESTRICTED detail requires a valid external disclosure "
                "permission; none was supplied (fail-closed)")
        ctx_err = _validate_disclosure_context(disclosure_context)
        if ctx_err is not None:
            return _error_envelope(ctx_err[0], "disclosure_context", ctx_err[1])
        ctx = disclosure_context
        # Permission-level revocation denies.
        if ctx["revocation_status"] == "REVOKED":
            return _error_envelope(
                Q_DISCLOSURE_REVOKED, "disclosure_context.revocation_status",
                "the supplied disclosure permission is revoked")
        # Permission-level expiry denies.
        if _parse_instant(ctx["expiry"]) <= now:
            return _error_envelope(
                Q_DISCLOSURE_EXPIRED, "disclosure_context.expiry",
                "the supplied disclosure permission has expired")
        # Unsupported policy version -> fail-closed deny (CF-1 type guard).
        if not _is_enum_member(ctx["policy_version"], SUPPORTED_POLICY_VERSIONS):
            return _error_envelope(
                Q_UNSUPPORTED_VERSION, "disclosure_context.policy_version",
                f"policy version {ctx['policy_version']!r} is not supported "
                "(fail-closed)")
        # Scope matching: the grant must cover RESTRICTED exactly. A grant for
        # a lower (open) scope does NOT authorize restricted detail.
        if ctx["granted_scope"] != "RESTRICTED":
            return _error_envelope(
                Q_DISCLOSURE_DENIED, "disclosure_context.granted_scope",
                "granted_scope does not match the RESTRICTED disclosure scope")
        # R3-1 anti-forgery: the external policy decision reference must be
        # confirmed by the configured resolver. Without a resolver there is
        # no way to confirm the issuer's decision, so access fails closed:
        # format-only validation is never sufficient for RESTRICTED access.
        if policy_decision_resolver is None:
            return _error_envelope(
                Q_POLICY_DECISION_REQUIRED, "disclosure_context",
                "no policy decision resolver is configured; RESTRICTED "
                "detail cannot be verified against the issuing policy system "
                "(fail-closed)")
        try:
            resolution = policy_decision_resolver(
                ctx.get("external_policy_decision_reference"))
        except Exception:
            resolution = None
        if not isinstance(resolution, dict) or not resolution.get("valid",
                                                                  False):
            return _error_envelope(
                Q_POLICY_DECISION_REQUIRED,
                "disclosure_context.external_policy_decision_reference",
                "the external policy decision reference could not be "
                "confirmed by the policy decision resolver (fail-closed)")
        return None

    # WITHHELD (and anything unexpected) -> deny. WITHHELD is usually handled
    # earlier via the three-state response; this is the fail-closed backstop.
    return _error_envelope(
        Q_DISCLOSURE_DENIED, "disclosure.disclosure_scope",
        "detail disclosure denied for this scope (fail-closed)")


class HistoryStore:
    """In-memory federated-holding simulation (one holder's ledger).

    AHRP is NOT a central database; this store simulates a single federated
    holder. All ingestion is validated first and fails closed.
    """

    def __init__(self, policy_decision_resolver=None) -> None:
        # Audit fix R3-1: RESTRICTED detail reads are granted only when this
        # resolver confirms the external policy decision reference; with no
        # resolver configured the store fails closed on every RESTRICTED
        # detail access path.
        self._policy_decision_resolver = policy_decision_resolver
        self._events: Dict[str, Dict[str, Any]] = {}
        self._verifications: Dict[str, Dict[str, Any]] = {}

    # ------------------------------------------------------------- ingest
    def ingest_event(self, event: Dict[str, Any]) -> str:
        result = validate_experience_event(event)
        if not result.valid:
            raise IngestError(result)
        event_id = event["event_id"]
        if event_id in self._events:
            raise ValueError(f"duplicate event_id: {event_id}")
        # F11: deep-copy on ingest so later mutation of the caller's dict
        # (aliasing) can never alter the stored record.
        self._events[event_id] = copy.deepcopy(event)
        return event_id

    def ingest_verification(self, record: Dict[str, Any]) -> str:
        result = validate_verification_record(record)
        if not result.valid:
            raise IngestError(result)
        verification_id = record["verification_id"]
        if verification_id in self._verifications:
            raise ValueError(f"duplicate verification_id: {verification_id}")
        self._verifications[verification_id] = copy.deepcopy(record)
        return verification_id

    # ----------------------------------------- strong verification binding
    def _resolve_event_verification(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Defect 2: effective verification from explicit references ONLY.

        Walks ``event.verification_references`` and validates each binding:
        reference id exact match, object existence, target/event scope match,
        agent reference/version match, verification version support, status
        legality, and verifier-name match. Weak association
        (event_id / agent / time scanning of storage) is never used.
        """
        event_id = event["event_id"]
        event_agent_ref = event.get("agent_reference", {}).get("identity_ref")
        event_agent_version = event.get("agent_version")
        references = event.get("verification_references", []) or []

        resolved: Dict[str, Any] = {
            "referenced_count": len(references),
            "conferring": [],       # verifications that confer event status
            "binding_errors": [],   # malformed / unresolved references
            "verifier_classes": [],
            "has_independent": False,
            "self_only": False,
        }
        if not references:
            resolved["effective_status"] = "NOT_ASSESSED"
            return resolved

        conferring_statuses = []
        saw_self = False
        saw_independent = False
        saw_binding_error = False

        for ref in references:
            if not isinstance(ref, dict):
                saw_binding_error = True
                resolved["binding_errors"].append("malformed reference")
                continue
            verification_id = ref.get("verification_id")
            record = self._verifications.get(verification_id)
            # Reference must resolve to an actually-held verification object.
            if record is None:
                saw_binding_error = True
                resolved["binding_errors"].append(
                    f"verification_id {verification_id!r} not found")
                continue

            scope = record.get("scope", {}) or {}
            verifier = record.get("verifier", {}) or {}
            status = record.get("verification_status")
            verifier_class = verifier.get("verifier_class")
            ok = True

            # Audit fix R3-3: an event-level verification binding MUST
            # declare both scope.agent_ref and scope.agent_version; a
            # verification can no longer bind to an event without naming
            # WHICH agent (and which version of it) it verifies. Missing
            # either -> BINDING_INCOMPLETE (fail-closed).
            if scope.get("subject_type") == _EVENT_SCOPE_SUBJECT_TYPE and \
                    ("agent_ref" not in scope or "agent_version" not in scope):
                resolved["binding_errors"].append({
                    "ref_id": verification_id,
                    "reason": "BINDING_INCOMPLETE",
                    "detail": "agent_ref and agent_version required for "
                              "event-level binding",
                })
                saw_binding_error = True
                continue

            # Target/event scope must match the current event exactly.
            if scope.get("subject_event_id") != event_id:
                ok = False
                resolved["binding_errors"].append(
                    "verification scope.subject_event_id does not match event")
            # Verifier-name binding must match the reference declaration.
            if ok and ref.get("verifier_name") != verifier.get("verifier_name"):
                ok = False
                resolved["binding_errors"].append(
                    "reference verifier_name does not match verification record")
            # Audit fix R3-3: agent reference / version binding must match
            # the subject event (event-level scopes must declare both, see
            # BINDING_INCOMPLETE above); any declared mismatch fails closed.
            if ok and "agent_ref" in scope and \
                    scope.get("agent_ref") != event_agent_ref:
                ok = False
                resolved["binding_errors"].append(
                    "verification scope.agent_ref does not match event agent")
            if ok and "agent_version" in scope and \
                    scope.get("agent_version") != event_agent_version:
                ok = False
                resolved["binding_errors"].append(
                    "verification scope.agent_version does not match event version")
            # Verification schema version must be supported.
            if ok and record.get("schema_version") not in SUPPORTED_QUERY_PROTOCOL_VERSIONS:
                ok = False
                resolved["binding_errors"].append(
                    "verification schema_version is not supported")
            # Verification status must be a legal enum value.
            if ok and status not in VERIFICATION_STATUS_ENUM:
                ok = False
                resolved["binding_errors"].append(
                    "verification_status is not a legal enum value")

            if not ok:
                saw_binding_error = True
                continue

            if verifier_class is not None:
                resolved["verifier_classes"].append(verifier_class)

            # F10 aspect filtering: only event-scoped, event-level aspects
            # confer an event-level verification status.
            event_level = (
                scope.get("subject_type") == _EVENT_SCOPE_SUBJECT_TYPE
                and scope.get("covered_aspect") in _EVENT_LEVEL_ASPECTS
            )
            # Audit fix R3-4 (supersedes the MF-1 / MF-2 ordering): only
            # records that actually assert something -- event-level AND
            # non-NOT_ASSESSED -- can confer status or classify independence.
            # A bounded-scope record (e.g. EVIDENCE_BINDING) can never
            # launder independence into a SELF event-level VERIFIED, and a
            # NOT_ASSESSED record asserts nothing, so neither may set
            # saw_self / saw_independent. NOT_ASSESSED is also absent from
            # _STATUS_PRIORITY and must never enter the conferring statuses
            # (a bare StopIteration would otherwise result); if nothing
            # conferring remains, the result is NOT_ASSESSED.
            if event_level and status != "NOT_ASSESSED":
                resolved["conferring"].append(record)
                conferring_statuses.append(status)
                if verifier_class == SELF_CLASS or \
                        record.get("self_verification") is True:
                    saw_self = True
                else:
                    saw_independent = True

        resolved["has_independent"] = saw_independent
        resolved["self_only"] = saw_self and not saw_independent

        # Effective status: binding errors -> INVALID; else precedence over the
        # conferring statuses; nothing conferring -> NOT_ASSESSED.
        if saw_binding_error and not conferring_statuses:
            resolved["effective_status"] = "INVALID"
        elif saw_binding_error:
            # A malformed reference alongside conferring ones fails closed to
            # INVALID unless a CONFLICTED status already dominates.
            resolved["effective_status"] = "CONFLICTED" \
                if "CONFLICTED" in conferring_statuses else "INVALID"
        elif conferring_statuses:
            present = set(conferring_statuses)
            resolved["effective_status"] = next(
                s for s in _STATUS_PRIORITY if s in present)
        else:
            resolved["effective_status"] = "NOT_ASSESSED"
        return resolved

    def verifications_for_event(self, event_id: str,
                                disclosure_context: Optional[Dict[str, Any]] = None
                                ) -> List[Dict[str, Any]]:
        """Defect 2: only verification objects explicitly referenced by the
        event are returned (strong binding). Output copies prevent mutation.

        Audit fix MF-3: WITHHELD events leak nothing, not even their
        verification records. Audit fix R3-2: RESTRICTED events route through
        the unified disclosure guard; without a valid, resolver-confirmed
        disclosure context the verification list is denied (empty)."""
        event = self._events.get(event_id)
        if event is None:
            return []
        permitted, _withheld, _denial = self._require_detail_disclosure(
            event, disclosure_context)
        if not permitted:
            return []
        out = []
        for ref in event.get("verification_references", []) or []:
            if not isinstance(ref, dict):
                continue
            record = self._verifications.get(ref.get("verification_id"))
            if record is not None:
                out.append(copy.deepcopy(record))
        return out

    def event_verification_status(self, event_id: str,
                                  disclosure_context: Optional[Dict[str, Any]] = None
                                  ) -> str:
        event = self._events.get(event_id)
        if event is None:
            return "NOT_ASSESSED"
        # Audit fix MF-3: WITHHELD disclosure also withholds the effective
        # verification status (consistent with get_event's three-state
        # WITHHELD response). Audit fix R3-2: RESTRICTED events expose the
        # effective status only through a confirmed disclosure context;
        # otherwise the status itself is restricted.
        permitted, withheld, _denial = self._require_detail_disclosure(
            event, disclosure_context)
        if withheld:
            return "WITHHELD"
        if not permitted:
            return "RESTRICTED"
        return self._resolve_event_verification(event)["effective_status"]

    def _verification_resolution(self, event: Dict[str, Any]) -> Dict[str, Any]:
        return self._resolve_event_verification(event)

    def _event_is_withheld(self, event: Dict[str, Any]) -> bool:
        return event.get("disclosure", {}).get("disclosure_scope") == "WITHHELD"

    def _require_detail_disclosure(self, event: Dict[str, Any],
                                   disclosure_context: Any = None
                                   ) -> Tuple[bool, bool,
                                              Optional[Dict[str, Any]]]:
        """Audit fix R3-2: unified detail-disclosure guard for EVERY data
        access path (``get_event`` / ``verifications_for_event`` /
        ``event_verification_status`` / ``get_failure_category``).

        Returns ``(permitted, withheld, error_envelope_or_None)``:

        * ``withheld=True`` -- WITHHELD scope; the caller emits the
          three-state WITHHELD response (existence acknowledged, content
          withheld).
        * ``permitted=True`` -- detail-level access is allowed.
        * otherwise -- an error envelope to return verbatim (fail-closed;
          includes RESTRICTED without a confirmed disclosure context and the
          R3-1 no-resolver denial).
        """
        if self._event_is_withheld(event):
            return False, True, None
        denial = _evaluate_detail_disclosure(
            event, disclosure_context, _clock(),
            self._policy_decision_resolver)
        if denial is not None:
            return False, False, denial
        return True, False, None

    def _event_summary(self, event: Dict[str, Any]) -> Dict[str, Any]:
        entry: Dict[str, Any] = {}
        for field in _SUMMARY_FIELDS:
            if field == "verification_status":
                entry[field] = self.event_verification_status(event["event_id"])
            elif field == "evidence_availability":
                entry[field] = [
                    ref["availability_status"]
                    for ref in event.get("evidence_references", [])
                ]
            elif field == "failure_category":
                # Three-state field projection: NOT_APPLICABLE for non-failure
                # results; a failure-class event without the category would
                # have been rejected at ingest.
                if event["result_status"] in FAILURE_CLASS_STATUSES:
                    entry[field] = event.get("failure_category")
                else:
                    entry[field] = NullSemantics.NOT_APPLICABLE.value
            else:
                entry[field] = event.get(field)
        # Defect 3: even in a summary projection, expose the verification
        # independence classification (no free text, no evidence bodies).
        resolution = self._resolve_event_verification(event)
        entry["verifier_classes"] = sorted(set(resolution["verifier_classes"]))
        entry["has_independent_verification"] = resolution["has_independent"]
        entry["self_only"] = resolution["self_only"]
        entry["independence_class"] = (
            "SELF" if resolution["self_only"]
            else "INDEPENDENT" if resolution["has_independent"]
            else "NONE"
        )
        return entry

    # ------------------------------------------------------ query validation
    def _validate_query_params(self, identity_ref, agent_version, task_type,
                               action_type, time_start, time_end,
                               verification_status, verifier_class,
                               disclosure_scope, protocol_version,
                               limit) -> Optional[Dict[str, Any]]:
        """Defect 4: validate ALL parameters before the query engine runs.

        Returns a ready-to-return error envelope, or ``None`` when the request
        is fully valid. Invalid parameters never reach the engine and are never
        mapped to NO_RECORD. CF-1: every enum check is type-guarded so
        unhashable inputs yield stable Q_* codes, never a bare TypeError.
        """
        if identity_ref is not None and not _is_nonempty_string(identity_ref):
            return _error_envelope(
                Q_INVALID_REFERENCE, "identity_ref",
                "identity_ref must be a non-empty string reference")
        if agent_version is not None and not _is_nonempty_string(agent_version):
            return _error_envelope(
                Q_INVALID_REFERENCE, "agent_version",
                "agent_version must be a non-empty string")
        if task_type is not None and not _is_enum_member(task_type,
                                                         TASK_TYPE_ENUM):
            return _error_envelope(
                Q_INVALID_ENUM, "task_type",
                f"task_type {task_type!r} is not a legal enum value")
        if action_type is not None and not _is_enum_member(action_type,
                                                           ACTION_TYPE_ENUM):
            return _error_envelope(
                Q_INVALID_ENUM, "action_type",
                f"action_type {action_type!r} is not a legal enum value")
        if verification_status is not None and not _is_enum_member(
                verification_status, VERIFICATION_STATUS_ENUM):
            return _error_envelope(
                Q_INVALID_ENUM, "verification_status",
                f"verification_status {verification_status!r} is not a legal "
                "enum value")
        if verifier_class is not None and not _is_enum_member(
                verifier_class, VERIFIER_CLASS_ENUM):
            return _error_envelope(
                Q_INVALID_ENUM, "verifier_class",
                f"verifier_class {verifier_class!r} is not a legal enum value")
        if disclosure_scope is not None and not _is_enum_member(
                disclosure_scope, DISCLOSURE_SCOPE_ENUM):
            return _error_envelope(
                Q_INVALID_ENUM, "disclosure_scope",
                f"disclosure_scope {disclosure_scope!r} is not a legal enum "
                "value")
        for field, value in (("time_start", time_start), ("time_end", time_end)):
            if value is not None and not _is_valid_instant_string(value):
                return _error_envelope(
                    Q_INVALID_TIME_FORMAT, field,
                    f"{field} {value!r} is not a valid RFC 3339 date-time")
        if time_start is not None and time_end is not None and \
                _parse_instant(time_start) > _parse_instant(time_end):
            return _error_envelope(
                Q_INVALID_TIME_RANGE, "time_start",
                "time_start must not be after time_end")
        if protocol_version is not None and not _is_enum_member(
                protocol_version, SUPPORTED_QUERY_PROTOCOL_VERSIONS):
            return _error_envelope(
                Q_UNSUPPORTED_VERSION, "protocol_version",
                f"query protocol version {protocol_version!r} is not supported")
        if limit is not None:
            if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
                # Audit fix MF-7: limit/pagination failures are parameter
                # errors, not reference errors (Q_INVALID_REFERENCE was
                # semantically wrong).
                return _error_envelope(
                    Q_INVALID_PARAM, "limit",
                    "limit must be a positive integer")
        return None

    # ------------------------------------------------------------- queries
    def _select(self, identity_ref: Optional[str], agent_version: Optional[str],
                task_type: Optional[str], action_type: Optional[str],
                time_start: Optional[str], time_end: Optional[str],
                verification_status: Optional[str],
                verifier_class: Optional[str],
                disclosure_scope: Optional[str],
                require_independent: bool):
        # F6: addressing filters (identity_ref, agent_version) are applied
        # FIRST; withheld records are only counted within that addressed
        # scope, so a query for an unrelated identity can never observe the
        # existence of another party's withheld records (existence leak).
        addressed = []
        for event in self._events.values():
            if identity_ref is not None and \
                    event["agent_reference"]["identity_ref"] != identity_ref:
                continue
            if agent_version is not None and event["agent_version"] != agent_version:
                continue
            addressed.append(event)
        withheld = sum(1 for e in addressed if self._event_is_withheld(e))
        selected = []
        start = _parse_instant(time_start) if time_start is not None else None
        end = _parse_instant(time_end) if time_end is not None else None
        for event in addressed:
            if self._event_is_withheld(event):
                # withheld events are counted but never filtered on content
                continue
            if task_type is not None and event["task_type"] != task_type:
                continue
            if action_type is not None and event["action_type"] != action_type:
                continue
            # Audit fix MF-5: disclosure_scope is a real filter, not merely a
            # validated-and-ignored parameter. WITHHELD events never enter
            # content filtering (handled above), so they can never match.
            if disclosure_scope is not None and \
                    event.get("disclosure", {}).get("disclosure_scope") \
                    != disclosure_scope:
                continue
            # F5: absolute-instant comparison, not string lexicographic order.
            instant = _parse_instant(event["occurred_at"])
            if start is not None and instant < start:
                continue
            if end is not None and instant > end:
                continue
            resolution = self._resolve_event_verification(event)
            if verification_status is not None and \
                    resolution["effective_status"] != verification_status:
                continue
            if verifier_class is not None and \
                    verifier_class not in resolution["verifier_classes"]:
                continue
            # Defect 3: a filter requiring independent verification can never
            # be satisfied by pure SELF verification.
            if require_independent and not resolution["has_independent"]:
                continue
            selected.append(event)
        return selected, withheld

    def summary(self, identity_ref: str,
                agent_version: Optional[str] = None) -> Dict[str, Any]:
        """Default query: Experience Summary (Selective Disclosure First).

        Raw counts only; NO derived ratios, scores or rankings. Identity
        continuity fail-closed: without an explicit ``agent_version``, counts
        are reported per version and never merged across versions.

        Defect 3: ``verified_events`` counts ONLY independently verified
        events; dedicated split fields report self / partial / not-assessed /
        conflicted counts separately.
        """
        # Audit fix CF-2: validate BEFORE any lookup. Empty/invalid
        # references are invalid requests, never NO_RECORD.
        if not _is_nonempty_string(identity_ref):
            return _error_envelope(
                Q_INVALID_REFERENCE, "identity_ref",
                "identity_ref must be a non-empty string reference")
        if agent_version is not None and not _is_nonempty_string(agent_version):
            return _error_envelope(
                Q_INVALID_REFERENCE, "agent_version",
                "agent_version must be a non-empty string")
        all_events = [
            e for e in self._events.values()
            if e["agent_reference"]["identity_ref"] == identity_ref
        ]
        if not all_events:
            return _envelope(
                "summary", NullSemantics.NO_RECORD,
                {"agent_identity_ref": identity_ref, "total_events": 0,
                 "verified_events": 0, "withheld_events": 0},
            )
        withheld = sum(1 for e in all_events if self._event_is_withheld(e))
        visible = [e for e in all_events if not self._event_is_withheld(e)]
        # F9: this identity holds records but every one is withheld -> the
        # honest answer is WITHHELD, not an empty NONE summary.
        if not visible:
            return _envelope(
                "summary", NullSemantics.WITHHELD,
                {"agent_identity_ref": identity_ref, "total_events": 0,
                 "verified_events": 0, "withheld_events": withheld,
                 "by_version": {}},
                withheld_count=withheld,
            )
        versions = sorted({e["agent_version"] for e in visible})
        if agent_version is not None:
            versions = [v for v in versions if v == agent_version]
        # F9: the identity has visible records but none in the requested
        # version scope -> NO_RECORD for that scope.
        if not versions:
            return _envelope(
                "summary", NullSemantics.NO_RECORD,
                {"agent_identity_ref": identity_ref,
                 "agent_version": agent_version, "total_events": 0,
                 "verified_events": 0, "withheld_events": 0,
                 "by_version": {}},
            )
        by_version: Dict[str, Dict[str, Any]] = {}
        for version in versions:
            v_events = [e for e in visible if e["agent_version"] == version]
            independent = 0
            self_only = 0
            partial = 0
            not_assessed = 0
            conflicted = 0
            by_task: Dict[str, int] = {}
            by_status: Dict[str, int] = {}
            for e in v_events:
                resolution = self._resolve_event_verification(e)
                eff = resolution["effective_status"]
                # verified_events counts ONLY independently verified events.
                if eff == "VERIFIED" and resolution["has_independent"]:
                    independent += 1
                if resolution["self_only"]:
                    self_only += 1
                if eff == "PARTIALLY_VERIFIED":
                    partial += 1
                if eff == "NOT_ASSESSED":
                    not_assessed += 1
                if eff == "CONFLICTED":
                    conflicted += 1
                by_task[e["task_type"]] = by_task.get(e["task_type"], 0) + 1
                by_status[e["result_status"]] = by_status.get(e["result_status"], 0) + 1
            by_version[version] = {
                "total_events": len(v_events),
                "verified_events": independent,
                "independently_verified_events": independent,
                "self_verified_events": self_only,
                "partially_verified_events": partial,
                "not_assessed_events": not_assessed,
                "conflicted_events": conflicted,
                "events_by_task_type": by_task,
                "events_by_result_status": by_status,
            }
        result = {
            "agent_identity_ref": identity_ref,
            "identity_continuity": "FAIL_CLOSED_PER_VERSION_COUNTS_ONLY",
            "by_version": by_version,
            "withheld_events": withheld,
            "note": "Raw counts only. No derived ratios, scores or rankings "
                    "(AHRP Constitution Section 9 non-goals). verified_events "
                    "counts independently verified events only.",
        }
        return _envelope("summary", NullSemantics.NONE, result,
                         withheld_count=withheld)

    def query_events(self, identity_ref: Optional[str] = None,
                     agent_version: Optional[str] = None,
                     task_type: Optional[str] = None,
                     action_type: Optional[str] = None,
                     time_start: Optional[str] = None,
                     time_end: Optional[str] = None,
                     verification_status: Optional[str] = None,
                     verifier_class: Optional[str] = None,
                     disclosure_scope: Optional[str] = None,
                     require_independent_verification: bool = False,
                     protocol_version: Optional[str] = None,
                     limit: Optional[int] = None) -> Dict[str, Any]:
        """Filtered list query returning summary projections only.

        Defect 4: every parameter is validated BEFORE the engine runs; invalid
        requests return a stable ``Q_*`` error envelope and never reach the
        engine, never map to NO_RECORD, and never raise raw exceptions.
        """
        err = self._validate_query_params(
            identity_ref, agent_version, task_type, action_type,
            time_start, time_end, verification_status, verifier_class,
            disclosure_scope, protocol_version, limit)
        if err is not None:
            return err
        try:
            selected, withheld = self._select(
                identity_ref, agent_version, task_type, action_type,
                time_start, time_end, verification_status, verifier_class,
                disclosure_scope, require_independent_verification)
            if not selected and withheld > 0:
                semantics = NullSemantics.WITHHELD
            elif not selected:
                semantics = NullSemantics.NO_RECORD
            else:
                semantics = NullSemantics.NONE
            ordered = sorted(selected,
                             key=lambda e: _parse_instant(e["occurred_at"]))
            if limit is not None:
                ordered = ordered[:limit]
            return _envelope(
                "summary", semantics,
                {"events": [self._event_summary(e) for e in ordered],
                 "count": len(ordered)},
                withheld_count=withheld,
            )
        except Exception as exc:  # pragma: no cover - defensive fail-closed
            return _error_envelope(
                Q_INTERNAL_ERROR, None,
                f"internal query error: {type(exc).__name__}", retryable=True)

    def get_event(self, event_id: str, capability: str = "summary",
                  disclosure_context: Optional[Dict[str, Any]] = None
                  ) -> Dict[str, Any]:
        """Drill-down. Detail requires explicit capability='detail' AND a
        disclosure truth-table evaluation that permits it; otherwise fail-closed.

        Defect 1: the plain string ``capability="detail"`` is a request, never
        an authorization. RESTRICTED detail additionally requires a valid,
        scope-matching Disclosure Context carrying an external policy decision.

        Audit fix MF-4: this method no longer accepts a caller-supplied clock
        (``now``) value; expiry enforcement always uses the module-level
        ``_clock`` (a test-only monkey-patch point), so callers can never
        inject a clock to bypass expiry.
        """
        # Audit fix CF-3: validate BEFORE any lookup. Invalid references and
        # capabilities are invalid requests, never NO_RECORD, never a bare
        # TypeError (CF-1 type guard on the capability enum check).
        if not _is_nonempty_string(event_id):
            return _error_envelope(
                Q_INVALID_REFERENCE, "event_id",
                "event_id must be a non-empty string reference")
        if capability is not None and not _is_enum_member(capability,
                                                          CAPABILITY_ENUM):
            return _error_envelope(
                Q_INVALID_ENUM, "capability",
                f"capability {capability!r} must be one of "
                f"{sorted(CAPABILITY_ENUM)}")
        event = self._events.get(event_id)
        if event is None:
            return _envelope("detail", NullSemantics.NO_RECORD,
                             {"event_id": event_id})
        if self._event_is_withheld(event):
            return _envelope("detail", NullSemantics.WITHHELD,
                             {"event_id": event_id}, withheld_count=1)
        if capability != "detail":
            return _envelope("summary", NullSemantics.NONE,
                             self._event_summary(event))
        # Detail: enforce the disclosure truth table (fail-closed) through the
        # unified guard, including the R3-1 policy decision resolver gate
        # (RESTRICTED without a configured resolver is always denied).
        _permitted, _withheld, denial = self._require_detail_disclosure(
            event, disclosure_context)
        if denial is not None:
            return denial
        # F4: every whitelisted free-text field (including nested dot paths)
        # is stripped from structured_facts and declared in restricted_text.
        restricted = [f for f in FREE_TEXT_FIELDS
                      if _get_path(event, f) is not None]
        structured = copy.deepcopy(event)
        restricted_payload: Dict[str, Any] = {}
        for dotted in restricted:
            node = structured
            container = restricted_payload
            parts = dotted.split(".")
            for part in parts[:-1]:
                node = node[part]
                container = container.setdefault(part, {})
            container[parts[-1]] = node.pop(parts[-1])
        resolution = self._resolve_event_verification(event)
        structured["verification_status"] = resolution["effective_status"]
        structured["verification_records"] = self.verifications_for_event(
            event_id, disclosure_context)
        # Defect 3: expose verification independence metadata even when the
        # event status is VERIFIED.
        structured["verification_independence"] = {
            "verifier_classes": sorted(set(resolution["verifier_classes"])),
            "independence_class": (
                "SELF" if resolution["self_only"]
                else "INDEPENDENT" if resolution["has_independent"]
                else "NONE"),
            "has_independent_verification": resolution["has_independent"],
            "self_only": resolution["self_only"],
        }
        return _envelope(
            "detail", NullSemantics.NONE,
            {"structured_facts": structured,
             "restricted_text": restricted_payload},
            restricted_fields=restricted,
        )

    def get_failure_category(self, event_id: str,
                             disclosure_context: Optional[Dict[str, Any]] = None
                             ) -> Dict[str, Any]:
        """Dedicated projection demonstrating the three-state null semantics.

        NO_RECORD: event unknown; NOT_APPLICABLE: result is not failure-class;
        otherwise the enumerated failure_category value.

        Audit fix R3-2: RESTRICTED events never leak the failure category
        without a valid, resolver-confirmed disclosure context.
        """
        # Audit fix CF-3: validate BEFORE any lookup; an empty/invalid
        # event_id is an invalid request, never NO_RECORD.
        if not _is_nonempty_string(event_id):
            return _error_envelope(
                Q_INVALID_REFERENCE, "event_id",
                "event_id must be a non-empty string reference")
        event = self._events.get(event_id)
        if event is None:
            return _envelope("detail", NullSemantics.NO_RECORD,
                             {"event_id": event_id})
        # Audit fix R3-2: unified disclosure guard. WITHHELD keeps its
        # three-state response; RESTRICTED without a confirmed disclosure
        # context returns a denial envelope and never the category value.
        _permitted, withheld, denial = self._require_detail_disclosure(
            event, disclosure_context)
        if withheld:
            return _envelope("detail", NullSemantics.WITHHELD,
                             {"event_id": event_id}, withheld_count=1)
        if denial is not None:
            return denial
        if event["result_status"] not in FAILURE_CLASS_STATUSES:
            return _envelope("detail", NullSemantics.NOT_APPLICABLE,
                             {"event_id": event_id, "failure_category": None})
        return _envelope("detail", NullSemantics.NONE,
                         {"event_id": event_id,
                          "failure_category": event["failure_category"]})

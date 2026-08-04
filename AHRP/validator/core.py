"""AHRP reference validator core logic (Python 3 stdlib only).

Validates Experience Events and Verification Records against the AHRP v0.1
schemas plus protocol-level constraints:

  1. Schema legality (JSON Schema subset, see ``jsonschema_subset``).
  2. Field completeness (required fields, conditional failure_category).
  3. Enum legality (Machine Enumerability First).
  4. Evidence Reference format (reference-style, content-addressed hash).
  5. Verification format (named verifier, scope statement, self-flag).
  6. Forbidden-field presence check: score / ranking / fitness /
     learning_result / mutation and rating-derived fields => immediate FAIL.
  7. Injection negative case: free-text (DATA channel) fields carrying
     instruction-like content => E_INJECTION_SUSPECTED => FAIL, so such
     records can never enter a decision path (AHRP_DATA_NE_INSTRUCTION).

Output is PASS/FAIL with machine-readable error codes.

Truth boundary: VALIDATOR_PASS_NE_COMPLIANCE=true. A PASS here is a
reference-implementation check, not a conformance certification.
"""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import jsonschema_subset

SCHEMA_DIR = Path(__file__).resolve().parent.parent / "schema"

ERROR_CODES = (
    "E_SCHEMA_INVALID",
    "E_FIELD_MISSING",
    "E_ENUM_INVALID",
    "E_TYPE_INVALID",
    "E_FORMAT_INVALID",
    "E_CONSTRAINT_VIOLATION",
    "E_FORBIDDEN_FIELD",
    "E_EVIDENCE_REF_MALFORMED",
    "E_INJECTION_SUSPECTED",
)

# Permanent non-goal enforcement: rating/ranking/learning-derived fields are
# forbidden anywhere in an AHRP document (Constitution Section 9).
FORBIDDEN_FIELD_NAMES = frozenset({
    "score",
    "ranking",
    "fitness",
    "learning_result",
    "mutation",
    "rating",
    "reputation",
    "credit_score",
    "success_rate",
    "trust_score",
})

FAILURE_CLASS_STATUSES = frozenset({"FAILURE", "TIMEOUT", "CANCELLED"})

# Whitelisted free-text (DATA channel) fields, addressed as dot paths.
FREE_TEXT_FIELDS = ("notes", "agent_reference.identity_note")

# F8 (review-fix round 2): normalization treats EVERY Unicode Cf (format)
# character as a word separator (space) -- not deletion -- so zero-width or
# invisible format characters used between words cannot fuse adjacent words
# into a single token and evade the injection patterns (bypass A), and the
# coverage is no longer limited to a hand-picked list (bypass B: LRM/RLM,
# invisible operators U+2061-U+2064, bidi isolates U+2066-U+2068, etc.).


def _normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = "".join(
        " " if unicodedata.category(ch) == "Cf" else ch
        for ch in value
        if not unicodedata.combining(ch)
    )
    return re.sub(r"\s+", " ", value).strip().lower()


def _normalize_text_collapsed(value: str) -> str:
    """Companion variant: Cf characters deleted instead of spaced.

    Matching runs against BOTH variants (fail-closed): the spaced variant
    catches Cf used as inter-word separators (fusion bypass), the collapsed
    variant catches Cf used inside a word to split an attack token."""
    value = unicodedata.normalize("NFKD", value)
    value = "".join(
        ch for ch in value
        if not unicodedata.combining(ch)
        and unicodedata.category(ch) != "Cf"
    )
    return re.sub(r"\s+", " ", value).strip().lower()


# Instruction-like markers that must never appear in DATA-channel fields.
# Conservative (fail-closed): any hit fails validation. Text is normalized
# (F8) before matching; instruction-word co-occurrence is required for
# high-false-positive patterns such as "execute the following".
INJECTION_MARKER_PATTERNS = (
    re.compile(r"ignore\s+(?:\w+\s+){0,2}?previous\s+instructions?", re.IGNORECASE),
    re.compile(r"disregard\s+(?:\w+\s+){0,2}?(?:previous|prior|above)\b", re.IGNORECASE),
    re.compile(r"system\s*[:：]\s*prompt", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+(?:\w+\s+){0,2}?(?:agent|assistant|system|admin|root)\b", re.IGNORECASE),
    re.compile(r"execute\s+the\s+following\s+(?:\w+\s+){0,5}?(?:instructions?|commands?|指令|命令|操作)"),
    re.compile(r"new\s+instructions?\s*[:：]", re.IGNORECASE),
    re.compile(r"忽略(之前|以上|所有|先前)(的)?(指令|提示|规则)"),
    re.compile(r"你现在是\s*(?:一个|一名)?\s*(?:不受限制|不受约束|无限制|全能|超级)"),
    re.compile(r"执行以下(指令|命令|操作)"),
    re.compile(r"<\s*script", re.IGNORECASE),
)


class ValidationResult:
    """Machine-readable validation outcome: PASS/FAIL plus error records."""

    def __init__(self, subject_kind: str, errors: Optional[List[Dict[str, str]]] = None):
        self.subject_kind = subject_kind
        self.errors: List[Dict[str, str]] = list(errors or [])

    @property
    def valid(self) -> bool:
        return not self.errors

    @property
    def verdict(self) -> str:
        return "PASS" if self.valid else "FAIL"

    def add(self, code: str, path: str, message: str) -> None:
        assert code in ERROR_CODES, f"unknown error code {code!r}"
        self.errors.append({"code": code, "path": path, "message": message})

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verdict": self.verdict,
            "subject_kind": self.subject_kind,
            "error_count": len(self.errors),
            "errors": list(self.errors),
        }

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"ValidationResult({self.verdict}, errors={len(self.errors)})"


_schema_cache: Dict[str, Dict[str, Any]] = {}


def load_schema(name: str) -> Dict[str, Any]:
    """Load an AHRP schema by basename (cached)."""
    if name not in _schema_cache:
        path = SCHEMA_DIR / name
        with open(path, "r", encoding="utf-8") as fh:
            _schema_cache[name] = json.load(fh)
    return _schema_cache[name]


_EVIDENCE_ITEM_RE = re.compile(r"^\$\.evidence_references\[\d+\][.\[]")


def _map_code(keyword: str, path: str) -> str:
    """Map a schema-subset keyword violation to an AHRP error code.

    F7: the evidence-reference-specific code applies only to true sub-paths
    inside an evidence reference item; the ``evidence_references`` field
    itself (e.g. wrong type, missing required field) keeps its generic code
    so required-field absence still reports E_FIELD_MISSING.
    """
    if keyword == "required":
        return "E_FIELD_MISSING"
    if _EVIDENCE_ITEM_RE.match(path):
        # Any malformation inside an evidence reference item is reported with
        # the dedicated evidence-reference error code.
        return "E_EVIDENCE_REF_MALFORMED"
    if keyword in ("enum", "const"):
        return "E_ENUM_INVALID"
    if keyword == "type":
        return "E_TYPE_INVALID"
    if keyword == "format":
        return "E_FORMAT_INVALID"
    if keyword in ("maxLength", "minLength"):
        return "E_CONSTRAINT_VIOLATION"
    return "E_SCHEMA_INVALID"  # additionalProperties and anything else


def _scan_forbidden_fields(node: Any, path: str, result: ValidationResult) -> None:
    """Recursive presence check for forbidden rating/learning fields."""
    if isinstance(node, dict):
        for key, value in node.items():
            if key.lower() in FORBIDDEN_FIELD_NAMES:
                result.add(
                    "E_FORBIDDEN_FIELD",
                    f"{path}.{key}",
                    f"forbidden field {key!r}: AHRP stores facts only; "
                    "rating/ranking/learning-derived fields are permanent non-goals",
                )
            _scan_forbidden_fields(value, f"{path}.{key}", result)
    elif isinstance(node, list):
        for i, item in enumerate(node):
            _scan_forbidden_fields(item, f"{path}[{i}]", result)


def _get_path(doc: Dict[str, Any], dotted: str) -> Any:
    node: Any = doc
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


def _scan_injection(doc: Dict[str, Any], result: ValidationResult) -> None:
    """Injection negative case: DATA channel must not carry instructions.

    F8: text is normalized (Cf format chars treated as separators or
    deleted, combining chars stripped, whitespace collapsed, case folded)
    before pattern matching; both variants are checked (fail-closed).
    """
    for dotted in FREE_TEXT_FIELDS:
        value = _get_path(doc, dotted)
        if not isinstance(value, str):
            continue
        variants = (_normalize_text(value), _normalize_text_collapsed(value))
        for pattern in INJECTION_MARKER_PATTERNS:
            if any(pattern.search(variant) for variant in variants):
                result.add(
                    "E_INJECTION_SUSPECTED",
                    f"$.{dotted}",
                    "free-text DATA-channel field contains instruction-like content; "
                    "AHRP_DATA_NE_INSTRUCTION=true, record rejected for decision paths",
                )
                break


def validate_experience_event(doc: Any) -> ValidationResult:
    """Validate an Experience Event document. Returns PASS/FAIL with codes."""
    result = ValidationResult("experience_event")
    if not isinstance(doc, dict):
        result.add("E_SCHEMA_INVALID", "$", "document root must be a JSON object")
        return result

    schema = load_schema("experience-event.schema.json")
    for err in jsonschema_subset.validate(doc, schema):
        result.add(_map_code(err["keyword"], err["path"]), err["path"], err["message"])

    # Conditional completeness: failure-class result requires failure_category.
    status = doc.get("result_status")
    if status in FAILURE_CLASS_STATUSES and "failure_category" not in doc:
        result.add(
            "E_FIELD_MISSING",
            "$.failure_category",
            f"failure_category is required when result_status={status!r} (failure class)",
        )

    _scan_forbidden_fields(doc, "$", result)
    _scan_injection(doc, result)
    return result


def validate_verification_record(doc: Any) -> ValidationResult:
    """Validate a Verification Record document. Returns PASS/FAIL with codes."""
    result = ValidationResult("verification_record")
    if not isinstance(doc, dict):
        result.add("E_SCHEMA_INVALID", "$", "document root must be a JSON object")
        return result

    schema = load_schema("verification.schema.json")
    for err in jsonschema_subset.validate(doc, schema):
        result.add(_map_code(err["keyword"], err["path"]), err["path"], err["message"])

    # Audit fix R3-3 (protocol-level enforcement): a verification whose scope
    # targets an EXPERIENCE_EVENT must declare the complete agent binding
    # (scope.agent_ref AND scope.agent_version). The JSON-Schema subset has no
    # conditional-required support, so the rule is enforced here: an
    # event-scoped verification that does not name the verified agent and
    # version is incomplete and rejected (fail-closed).
    scope = doc.get("scope")
    if isinstance(scope, dict) and \
            scope.get("subject_type") == "EXPERIENCE_EVENT":
        for bound_field in ("agent_ref", "agent_version"):
            value = scope.get(bound_field)
            if not isinstance(value, str) or not value:
                result.add(
                    "E_FIELD_MISSING",
                    f"$.scope.{bound_field}",
                    f"scope.{bound_field} is required when scope.subject_type "
                    "is EXPERIENCE_EVENT (event-level verification must bind "
                    "the agent identity and version; fail-closed)",
                )

    # Constitution discipline: SELF verifier class must be explicitly flagged,
    # and self_verification=true must coincide with verifier_class SELF.
    verifier = doc.get("verifier")
    if isinstance(verifier, dict):
        is_self_class = verifier.get("verifier_class") == "SELF"
        self_flag = doc.get("self_verification")
        if is_self_class and self_flag is not True:
            result.add(
                "E_CONSTRAINT_VIOLATION",
                "$.self_verification",
                "verifier_class=SELF requires self_verification=true "
                "(self-verification must be explicitly flagged)",
            )
        if self_flag is True and not is_self_class:
            result.add(
                "E_CONSTRAINT_VIOLATION",
                "$.verifier.verifier_class",
                "self_verification=true requires verifier_class=SELF",
            )

    _scan_forbidden_fields(doc, "$", result)
    _scan_injection(doc, result)
    return result

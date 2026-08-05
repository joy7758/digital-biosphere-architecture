"""AHRP validator package (reference implementation, Python 3 stdlib only).

AHRP v0.1 is a Historical Experience Protocol, NOT a Rating / Recommendation /
Learning System. This validator is PROPOSED reference tooling, not a standard.
"""

from .core import (
    ValidationResult,
    validate_experience_event,
    validate_verification_record,
    FORBIDDEN_FIELD_NAMES,
    ERROR_CODES,
)

__all__ = [
    "ValidationResult",
    "validate_experience_event",
    "validate_verification_record",
    "FORBIDDEN_FIELD_NAMES",
    "ERROR_CODES",
]

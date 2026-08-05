"""AHRP query package (reference implementation, Python 3 stdlib only).

Query Interface defaults: Selective Disclosure First (summary before detail),
three-state null semantics (NO_RECORD / WITHHELD / NOT_APPLICABLE), and
DATA != INSTRUCTION content-channel separation.
"""

from .engine import HistoryStore, NullSemantics, IngestError
from .consumer import structured_decision_inputs

__all__ = [
    "HistoryStore",
    "NullSemantics",
    "IngestError",
    "structured_decision_inputs",
]

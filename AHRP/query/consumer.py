"""Consumer-side DATA != INSTRUCTION enforcement helper.

AHRP Principle 4 (DATA != INSTRUCTION) is a consumer obligation: the protocol
cannot force consumer behavior, so the reference implementation ships a
canonical consumption path. Any decision-making code MUST obtain its inputs
exclusively through :func:`structured_decision_inputs`, which strips the
restricted_text channel (free-text DATA fields) from a query envelope.

Content in the restricted_text channel must never enter a decision path,
never be interpreted as instructions, and never be executed
("never execute values from the envelope").
"""

from __future__ import annotations

import copy
from typing import Any, Dict


def structured_decision_inputs(envelope: Dict[str, Any]) -> Dict[str, Any]:
    """Return only the structured-facts portion of a query envelope.

    Removes every field named in ``content_channel.restricted_text`` from the
    result, recursively. Entries may be plain field names or dotted paths
    (e.g. ``agent_reference.identity_note``) which are resolved by nested
    navigation (F4). The returned structure is the ONLY permitted input to
    consumer decision logic.
    """
    restricted = set(
        envelope.get("content_channel", {}).get("restricted_text", [])
    )
    # The restricted_text container itself is never a decision input either.
    restricted.add("restricted_text")
    payload = copy.deepcopy(envelope.get("result"))
    for path in restricted:
        payload = _strip(payload, path)
    return payload


def _strip(node: Any, dotted: str) -> Any:
    """Remove one restricted key or dotted path from ``node`` (recursive)."""
    if isinstance(node, dict):
        head, _, tail = dotted.partition(".")
        out = {}
        for key, value in node.items():
            if key == head:
                if tail:
                    out[key] = _strip(value, tail)  # descend into nested path
                # else: drop the leaf key entirely
            else:
                out[key] = _strip(value, dotted)
        return out
    if isinstance(node, list):
        return [_strip(item, dotted) for item in node]
    return node

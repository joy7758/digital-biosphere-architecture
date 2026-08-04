"""Minimal JSON Schema (draft-07) subset validator, Python 3 stdlib only.

AHRP v0.1 ships without third-party dependencies. This module implements only
the subset of JSON Schema keywords used by the AHRP schemas:

    type, properties, required, additionalProperties (bool),
    enum, const, items, $ref (local "#/definitions/..." only),
    maxLength, minLength, pattern, format ("date-time" only)

It returns structured error records; mapping to AHRP machine-readable error
codes happens in ``validator.core``.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, List

_TYPE_MAP = {
    "string": str,
    "integer": int,
    "number": (int, float),
    "boolean": bool,
    "array": list,
    "object": dict,
    "null": type(None),
}

_DATETIME_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})$"
)


def _type_ok(instance: Any, expected: str) -> bool:
    py = _TYPE_MAP.get(expected)
    if py is None:
        return True  # unknown type keyword: do not fail hard in subset mode
    if expected == "integer" and isinstance(instance, bool):
        return False
    if expected == "number" and isinstance(instance, bool):
        return False
    return isinstance(instance, py)


def _datetime_ok(value: str) -> bool:
    if not _DATETIME_RE.match(value):
        return False
    candidate = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        datetime.fromisoformat(candidate)
        return True
    except ValueError:
        return False


def _resolve_ref(ref: str, root_schema: Dict[str, Any]) -> Dict[str, Any]:
    if not ref.startswith("#/"):
        raise ValueError(f"unsupported $ref (only local refs): {ref!r}")
    node: Any = root_schema
    for part in ref[2:].split("/"):
        node = node[part]
    return node


def validate(
    instance: Any,
    schema: Dict[str, Any],
    root_schema: Dict[str, Any] | None = None,
    path: str = "$",
) -> List[Dict[str, str]]:
    """Validate ``instance`` against ``schema``.

    Returns a list of error records: ``{"keyword": ..., "path": ..., "message": ...}``.
    An empty list means the instance is valid against this schema subset.
    """
    if root_schema is None:
        root_schema = schema
    errors: List[Dict[str, str]] = []

    if "$ref" in schema:
        return validate(instance, _resolve_ref(schema["$ref"], root_schema), root_schema, path)

    if "const" in schema:
        if instance != schema["const"]:
            errors.append({
                "keyword": "const",
                "path": path,
                "message": f"expected constant {schema['const']!r}, got {instance!r}",
            })
        return errors

    if "enum" in schema:
        if instance not in schema["enum"]:
            errors.append({
                "keyword": "enum",
                "path": path,
                "message": f"value {instance!r} not in enum {schema['enum']!r}",
            })
        return errors

    if "type" in schema:
        types = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        if not any(_type_ok(instance, t) for t in types):
            errors.append({
                "keyword": "type",
                "path": path,
                "message": f"expected type {types}, got {type(instance).__name__}",
            })
            return errors

    if isinstance(instance, str):
        if "maxLength" in schema and len(instance) > schema["maxLength"]:
            errors.append({
                "keyword": "maxLength",
                "path": path,
                "message": f"string length {len(instance)} exceeds maxLength {schema['maxLength']}",
            })
        if "minLength" in schema and len(instance) < schema["minLength"]:
            errors.append({
                "keyword": "minLength",
                "path": path,
                "message": f"string length {len(instance)} below minLength {schema['minLength']}",
            })
        if "pattern" in schema and not re.search(schema["pattern"], instance):
            errors.append({
                "keyword": "pattern",
                "path": path,
                "message": f"string does not match pattern {schema['pattern']!r}",
            })
        if schema.get("format") == "date-time" and not _datetime_ok(instance):
            errors.append({
                "keyword": "format",
                "path": path,
                "message": f"string {instance!r} is not a valid RFC 3339 date-time",
            })

    if isinstance(instance, list) and "items" in schema:
        for i, item in enumerate(instance):
            errors.extend(validate(item, schema["items"], root_schema, f"{path}[{i}]"))

    if isinstance(instance, dict):
        for req in schema.get("required", []):
            if req not in instance:
                errors.append({
                    "keyword": "required",
                    "path": f"{path}.{req}",
                    "message": f"required field {req!r} is missing",
                })
        props = schema.get("properties", {})
        for key, value in instance.items():
            if key in props:
                errors.extend(validate(value, props[key], root_schema, f"{path}.{key}"))
            elif schema.get("additionalProperties") is False:
                errors.append({
                    "keyword": "additionalProperties",
                    "path": f"{path}.{key}",
                    "message": f"additional property {key!r} is not allowed",
                })

    return errors

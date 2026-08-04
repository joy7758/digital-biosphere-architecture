"""Schema tests: schema files exist, are draft-07, contain mandated fields,
and never mention forbidden rating/learning fields as permitted properties.
"""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

from tests._helpers import AHRP_ROOT

SCHEMA_DIR = AHRP_ROOT / "schema"

MANDATORY_EVENT_FIELDS = [
    "event_id", "agent_reference", "agent_version", "task_type",
    "action_type", "result_status", "evidence_references",
    "verification_references", "occurred_at", "failure_category",
    "schema_version", "disclosure",
]
MANDATORY_VERIFICATION_FIELDS = [
    "verifier", "verification_type", "verification_status", "verified_at",
    "scope", "self_verification",
]
FORBIDDEN = ["score", "ranking", "fitness", "learning_result", "mutation"]

EVIDENCE_FAILURE_ENUM = {
    "INVALID", "NOT_ASSESSED", "INSUFFICIENT_EVIDENCE", "CONFLICTED",
    "UNSUPPORTED_VERSION",
}
VERIFICATION_STATUS_ENUM = {
    "VERIFIED", "PARTIALLY_VERIFIED", "NOT_ASSESSED", "INVALID", "CONFLICTED",
}


class TestSchemaFiles(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(SCHEMA_DIR / "experience-event.schema.json", encoding="utf-8") as fh:
            cls.event_schema = json.load(fh)
        with open(SCHEMA_DIR / "verification.schema.json", encoding="utf-8") as fh:
            cls.verification_schema = json.load(fh)

    def test_schemas_are_draft07_and_self_describing(self):
        for schema in (self.event_schema, self.verification_schema):
            self.assertEqual(schema["$schema"],
                             "http://json-schema.org/draft-07/schema#")
            self.assertIn("$id", schema)
            self.assertIn("title", schema)

    def test_event_schema_has_mandatory_fields(self):
        props = self.event_schema["properties"]
        for field in MANDATORY_EVENT_FIELDS:
            self.assertIn(field, props, f"missing mandated field {field}")

    def test_verification_schema_has_mandatory_fields(self):
        props = self.verification_schema["properties"]
        for field in MANDATORY_VERIFICATION_FIELDS:
            self.assertIn(field, props, f"missing mandated field {field}")

    def test_key_states_are_enumerated(self):
        props = self.event_schema["properties"]
        for field in ("task_type", "action_type", "result_status",
                      "failure_category"):
            self.assertIn("enum", props[field],
                          f"{field} must be enum (Machine Enumerability First)")
        self.assertIn("enum", self.verification_schema["properties"]
                      ["verification_status"])

    def test_evidence_failure_enum_complete(self):
        ref = self.event_schema["definitions"]["evidence_reference"]
        statuses = set(ref["properties"]["availability_status"]["enum"])
        self.assertTrue(EVIDENCE_FAILURE_ENUM.issubset(statuses))

    def test_verification_status_enum_complete(self):
        statuses = set(self.verification_schema["properties"]
                       ["verification_status"]["enum"])
        self.assertEqual(statuses, VERIFICATION_STATUS_ENUM)

    def test_no_forbidden_fields_in_schemas(self):
        for schema in (self.event_schema, self.verification_schema):
            text = json.dumps(schema)
            for forbidden in FORBIDDEN:
                self.assertNotIn(f'"{forbidden}"', text,
                                 f"forbidden field {forbidden!r} present in schema")

    def test_free_text_fields_have_length_limits(self):
        props = self.event_schema["properties"]
        self.assertLessEqual(props["notes"]["maxLength"], 200)
        agent_ref = props["agent_reference"]["properties"]
        self.assertLessEqual(agent_ref["identity_note"]["maxLength"], 200)
        v_props = self.verification_schema["properties"]
        self.assertLessEqual(v_props["notes"]["maxLength"], 200)

    def test_free_text_declared_data_channel(self):
        text = json.dumps(self.event_schema)
        self.assertIn("DATA channel", text)
        self.assertIn("MUST NOT be consumed as instructions", text)

    def test_evidence_hash_is_content_addressed(self):
        ref = self.event_schema["definitions"]["evidence_reference"]
        pattern = ref["properties"]["hash"]["pattern"]
        self.assertTrue(re.match(pattern, "sha256:" + "0" * 64))
        self.assertIsNone(re.match(pattern, "md5:" + "0" * 32))

    def test_verification_ne_authorization_machine_enforced(self):
        props = self.verification_schema["properties"]
        self.assertEqual(props["authorization_effect"]["const"], "NONE")
        self.assertIn("authorization_effect",
                      self.verification_schema["required"])


if __name__ == "__main__":
    unittest.main()

from pathlib import Path
import json
import unittest


REQUIRED_CANONICAL_FIELDS = [
    "Type",
    "Labels",
    "Priority",
    "Component",
    "Affects Version/s",
    "Resolution",
    "Status",
    "Fix Version/s",
    "Severity",
    "Report department",
    "Root Cause",
    "How to fix",
    "Action",
    "Frequency",
    "FailRunTime",
]


class JiraFieldAliasesSchemaTest(unittest.TestCase):
    def test_jira_field_aliases_contract_contains_required_labels(self) -> None:
        payload = json.loads(Path("packages/schema/jira-field-aliases.json").read_text(encoding="utf-8"))
        for field in REQUIRED_CANONICAL_FIELDS:
            with self.subTest(field=field):
                self.assertIn(field, payload)
                self.assertIsInstance(payload[field], list)
                self.assertTrue(payload[field])

    def test_jira_field_aliases_fixture_matches_contract_shape(self) -> None:
        payload = json.loads(Path("fixtures/schema/jira-field-aliases-fixture.json").read_text(encoding="utf-8"))
        for field in REQUIRED_CANONICAL_FIELDS:
            with self.subTest(field=field):
                self.assertIn(field, payload)
                self.assertIsInstance(payload[field], list)
                self.assertTrue(all(isinstance(alias, str) and alias.strip() for alias in payload[field]))


if __name__ == "__main__":
    unittest.main()

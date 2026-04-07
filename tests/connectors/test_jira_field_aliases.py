from pathlib import Path
import json
import unittest
from unittest.mock import patch

from services.connectors.jira.field_aliases import load_jira_field_aliases
from services.connectors.jira.connector import load_jira_sync


class JiraFieldAliasesTest(unittest.TestCase):
    def test_default_alias_contract_loads(self) -> None:
        aliases = load_jira_field_aliases()
        self.assertIn("Root Cause", aliases)
        self.assertIn("root_cause", aliases["Root Cause"])

    def test_connector_uses_configured_alias_contract(self) -> None:
        payload = {
            "sync_type": "full",
            "cursor": "jira-alias-001",
            "issues": [
                {
                    "key": "SSD-901",
                    "summary": "Alias driven issue field mapping",
                    "updated_at": "2026-04-07T10:00:00Z",
                    "why_root": "Queue allocation mismatch",
                    "fix_plan": "Increase queue limit",
                }
            ],
        }
        fixture_path = Path(".tmp/jira-alias-fixture.json")
        fixture_path.parent.mkdir(parents=True, exist_ok=True)
        fixture_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        aliases = {
            "Root Cause": ["why_root"],
            "How to fix": ["fix_plan"],
        }
        with patch("services.connectors.jira.connector.load_jira_field_aliases", return_value=aliases):
            result = load_jira_sync(fixture_path)
        self.assertEqual(aliases["Root Cause"], ["why_root"])
        self.assertIn("Root Cause", result["documents"][0]["metadata"]["issue_fields"])
        self.assertEqual(result["documents"][0]["metadata"]["issue_fields"]["How to fix"], "Increase queue limit")


if __name__ == "__main__":
    unittest.main()

from pathlib import Path
import json
import unittest


class OpsProfileSchemaTest(unittest.TestCase):
    def test_ops_profile_schema_defines_required_sections(self) -> None:
        schema = json.loads(Path("packages/schema/ops-profile-schema.json").read_text(encoding="utf-8"))
        self.assertEqual(schema["type"], "object")
        self.assertIn("jira", schema["required"])
        self.assertIn("confluence", schema["required"])
        self.assertIn("jira", schema["properties"])
        self.assertIn("confluence", schema["properties"])

    def test_ops_profile_fixture_contains_required_sections(self) -> None:
        payload = json.loads(Path("fixtures/schema/ops-profile-fixture.json").read_text(encoding="utf-8"))
        self.assertIn("jira", payload)
        self.assertIn("confluence", payload)
        self.assertIn("path", payload["jira"])
        self.assertIn("path", payload["confluence"])


if __name__ == "__main__":
    unittest.main()

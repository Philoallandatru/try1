from __future__ import annotations

from pathlib import Path
import json
import unittest


class JiraAnalysisArtifactSchemasTest(unittest.TestCase):
    def test_confluence_update_proposal_schema_contains_required_fields(self) -> None:
        schema = json.loads(Path("packages/schema/confluence-update-proposal-schema.json").read_text(encoding="utf-8"))
        self.assertEqual(schema["type"], "object")
        required = set(schema["required"])
        self.assertIn("proposal_id", required)
        self.assertIn("source_issue_key", required)
        self.assertIn("candidate_pages", required)
        self.assertIn("knowledge_action", required)
        self.assertIn("supporting_evidence", required)
        self.assertEqual(
            schema["properties"]["knowledge_action"]["enum"],
            ["add", "revise", "append", "no_change"],
        )
        self.assertEqual(schema["properties"]["candidate_pages"]["minItems"], 1)

    def test_confluence_update_proposal_fixture_matches_contract_shape(self) -> None:
        payload = json.loads(Path("fixtures/schema/confluence-update-proposal-fixture.json").read_text(encoding="utf-8"))
        self.assertIn("proposal_id", payload)
        self.assertIn("source_issue_key", payload)
        self.assertEqual(payload["knowledge_action"], "revise")
        self.assertGreaterEqual(len(payload["candidate_pages"]), 1)
        self.assertGreaterEqual(len(payload["supporting_evidence"]), 1)

    def test_concept_cards_schema_contains_required_fields(self) -> None:
        schema = json.loads(Path("packages/schema/concept-cards-schema.json").read_text(encoding="utf-8"))
        self.assertEqual(schema["type"], "object")
        self.assertIn("cards", schema["required"])
        card_schema = schema["properties"]["cards"]["items"]
        required = set(card_schema["required"])
        self.assertIn("card_id", required)
        self.assertIn("label", required)
        self.assertIn("category", required)
        self.assertIn("summary", required)
        self.assertIn("evidence", required)

    def test_concept_cards_fixture_matches_contract_shape(self) -> None:
        payload = json.loads(Path("fixtures/schema/concept-cards-fixture.json").read_text(encoding="utf-8"))
        self.assertIn("cards", payload)
        self.assertGreaterEqual(len(payload["cards"]), 1)
        self.assertEqual(payload["cards"][0]["category"], "terminology")
        self.assertGreaterEqual(len(payload["cards"][0]["evidence"]), 1)


if __name__ == "__main__":
    unittest.main()

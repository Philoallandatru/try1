from pathlib import Path
import json
import unittest


REQUIRED_SCHEMA_FIELDS = [
    "document_id",
    "source_type",
    "authority_level",
    "version",
    "language",
    "title",
    "provenance",
    "acl",
    "structure",
    "terminology",
    "content_blocks",
]


class DocumentSchemaTest(unittest.TestCase):
    def test_document_schema_defines_required_fields(self) -> None:
        schema = json.loads(Path("packages/schema/document-schema.json").read_text(encoding="utf-8"))
        self.assertEqual(schema["type"], "object")
        for field in REQUIRED_SCHEMA_FIELDS:
            self.assertIn(field, schema["required"])
            self.assertIn(field, schema["properties"])

    def test_source_family_fixtures_contain_required_fields(self) -> None:
        for fixture in Path("fixtures/schema").glob("*-sample.json"):
            with self.subTest(fixture=fixture.name):
                payload = json.loads(fixture.read_text(encoding="utf-8"))
                for field in REQUIRED_SCHEMA_FIELDS:
                    self.assertIn(field, payload)

    def test_structure_preserves_first_class_objects(self) -> None:
        payload = json.loads(Path("fixtures/schema/pdf-sample.json").read_text(encoding="utf-8"))
        structure = payload["structure"]
        self.assertIn("pages", structure)
        self.assertIn("sections", structure)
        self.assertIn("tables", structure)
        self.assertIn("figures", structure)


if __name__ == "__main__":
    unittest.main()


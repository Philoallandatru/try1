from pathlib import Path
import json
import unittest


class AclContractTest(unittest.TestCase):
    def test_acl_readme_defines_deny_by_default_and_inheritance(self) -> None:
        text = Path("packages/acl/README.md").read_text(encoding="utf-8")
        self.assertIn("Deny by default", text)
        self.assertIn("inherit", text.lower())
        self.assertIn("reranking", text)

    def test_acl_examples_define_default_deny_and_inheritance(self) -> None:
        payload = json.loads(Path("fixtures/schema/acl-examples.json").read_text(encoding="utf-8"))
        self.assertEqual(payload["rules"]["default_policy"], "deny")
        self.assertTrue(payload["rules"]["inheritance_enabled"])
        docs = {doc["document_id"]: doc["acl"] for doc in payload["documents"]}
        self.assertIsNone(docs["root-doc"]["inherits_from"])
        self.assertEqual(docs["child-doc"]["inherits_from"], "root-doc")
        self.assertEqual(docs["restricted-doc"]["policy"], "deny")


if __name__ == "__main__":
    unittest.main()


import unittest
from pathlib import Path

from services.connectors.confluence.connector import load_confluence_sync


class ConfluenceHierarchyTest(unittest.TestCase):
    def setUp(self):
        self.fixture_path = Path(__file__).parent.parent.parent / "fixtures" / "connectors" / "confluence" / "page_with_hierarchy.json"
        self.sync_result = load_confluence_sync(self.fixture_path)

    def test_extract_ancestors(self):
        """Test that ancestors are extracted correctly."""
        doc = self.sync_result["documents"][0]  # API Documentation page
        self.assertIn("ancestors", doc)
        self.assertEqual(len(doc["ancestors"]), 2)
        self.assertEqual(doc["ancestors"][0]["id"], "10000")
        self.assertEqual(doc["ancestors"][0]["title"], "Documentation Home")
        self.assertEqual(doc["ancestors"][1]["id"], "11000")
        self.assertEqual(doc["ancestors"][1]["title"], "Technical Docs")

    def test_extract_labels(self):
        """Test that labels are extracted correctly."""
        doc = self.sync_result["documents"][0]  # API Documentation page
        self.assertIn("labels", doc)
        self.assertEqual(len(doc["labels"]), 3)
        self.assertIn("api", doc["labels"])
        self.assertIn("rest", doc["labels"])
        self.assertIn("v2", doc["labels"])

    def test_hierarchy_in_markdown(self):
        """Test that page hierarchy appears in markdown."""
        doc = self.sync_result["documents"][0]  # API Documentation page
        markdown = doc["markdown"]
        self.assertIn("## Page Hierarchy", markdown)
        self.assertIn("Documentation Home > Technical Docs > API Documentation", markdown)

    def test_labels_in_markdown(self):
        """Test that labels appear in markdown."""
        doc = self.sync_result["documents"][0]  # API Documentation page
        markdown = doc["markdown"]
        self.assertIn("## Labels", markdown)
        self.assertIn("api, rest, v2", markdown)

    def test_hierarchy_in_content_blocks(self):
        """Test that hierarchy appears in content_blocks with correct section."""
        doc = self.sync_result["documents"][0]  # API Documentation page
        hierarchy_blocks = [
            block for block in doc["content_blocks"]
            if block.get("section") == "Page Hierarchy"
        ]
        self.assertEqual(len(hierarchy_blocks), 1)
        self.assertIn("Documentation Home > Technical Docs > API Documentation", hierarchy_blocks[0]["text"])

    def test_labels_in_content_blocks(self):
        """Test that labels appear in content_blocks with correct section."""
        doc = self.sync_result["documents"][0]  # API Documentation page
        label_blocks = [
            block for block in doc["content_blocks"]
            if block.get("section") == "Labels"
        ]
        self.assertEqual(len(label_blocks), 1)
        self.assertIn("api", label_blocks[0]["text"])

    def test_metadata_includes_hierarchy_info(self):
        """Test that metadata includes hierarchy information."""
        doc = self.sync_result["documents"][0]  # API Documentation page
        metadata = doc["metadata"]
        self.assertEqual(metadata["ancestor_count"], 2)
        self.assertEqual(metadata["parent_id"], "11000")
        self.assertEqual(metadata["parent_title"], "Technical Docs")

    def test_metadata_includes_labels(self):
        """Test that metadata includes label information."""
        doc = self.sync_result["documents"][0]  # API Documentation page
        metadata = doc["metadata"]
        self.assertEqual(metadata["label_count"], 3)
        self.assertEqual(metadata["labels"], ["api", "rest", "v2"])

    def test_child_page_hierarchy(self):
        """Test that child page shows full hierarchy including parent."""
        doc = self.sync_result["documents"][1]  # Authentication Guide (child of API Documentation)
        self.assertEqual(len(doc["ancestors"]), 3)
        self.assertEqual(doc["ancestors"][2]["id"], "12345")
        self.assertEqual(doc["ancestors"][2]["title"], "API Documentation")
        self.assertIn("Documentation Home > Technical Docs > API Documentation > Authentication Guide", doc["markdown"])

    def test_page_without_hierarchy_or_labels(self):
        """Test that pages without ancestors or labels work correctly."""
        doc = self.sync_result["documents"][2]  # Standalone Page
        self.assertEqual(len(doc["ancestors"]), 0)
        self.assertEqual(len(doc["labels"]), 0)
        self.assertNotIn("## Page Hierarchy", doc["markdown"])
        self.assertNotIn("## Labels", doc["markdown"])
        self.assertEqual(doc["metadata"]["ancestor_count"], 0)
        self.assertIsNone(doc["metadata"]["parent_id"])
        self.assertEqual(doc["metadata"]["label_count"], 0)


if __name__ == "__main__":
    unittest.main()

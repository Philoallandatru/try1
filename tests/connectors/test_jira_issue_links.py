"""Test Jira issue links and subtasks extraction."""
import unittest
from pathlib import Path

from services.connectors.jira.connector import load_jira_sync


class JiraIssueLinksTest(unittest.TestCase):
    """Test Jira issue links and subtasks functionality."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.fixture_path = Path(__file__).parent.parent.parent / "fixtures" / "connectors" / "jira" / "issue_with_links.json"

    def test_extract_issue_links(self) -> None:
        """Test that issue links are extracted correctly."""
        result = load_jira_sync(path=str(self.fixture_path))

        self.assertEqual(len(result["documents"]), 2)

        # Check SSD-201 (has 2 links)
        doc_201 = next(doc for doc in result["documents"] if doc["document_id"] == "SSD-201")
        self.assertIn("issue_links", doc_201)
        self.assertEqual(len(doc_201["issue_links"]), 2)

        # Check outward link (blocks SSD-202)
        blocks_link = next(link for link in doc_201["issue_links"] if link["key"] == "SSD-202")
        self.assertEqual(blocks_link["relationship"], "blocks")
        self.assertEqual(blocks_link["direction"], "outward")
        self.assertEqual(blocks_link["summary"], "Deploy authentication service")
        self.assertEqual(blocks_link["status"], "To Do")

        # Check inward link (relates to SSD-200)
        relates_link = next(link for link in doc_201["issue_links"] if link["key"] == "SSD-200")
        self.assertEqual(relates_link["relationship"], "relates to")
        self.assertEqual(relates_link["direction"], "inward")
        self.assertEqual(relates_link["summary"], "Design authentication architecture")
        self.assertEqual(relates_link["status"], "Done")

        # Check metadata
        self.assertEqual(doc_201["metadata"]["issue_link_count"], 2)

    def test_extract_subtasks(self) -> None:
        """Test that subtasks are extracted correctly."""
        result = load_jira_sync(path=str(self.fixture_path))

        # Check SSD-201 (has 2 subtasks)
        doc_201 = next(doc for doc in result["documents"] if doc["document_id"] == "SSD-201")
        self.assertIn("subtasks", doc_201)
        self.assertEqual(len(doc_201["subtasks"]), 2)

        # Check first subtask
        subtask_203 = next(st for st in doc_201["subtasks"] if st["key"] == "SSD-203")
        self.assertEqual(subtask_203["summary"], "Add JWT token generation")
        self.assertEqual(subtask_203["status"], "Done")

        # Check second subtask
        subtask_204 = next(st for st in doc_201["subtasks"] if st["key"] == "SSD-204")
        self.assertEqual(subtask_204["summary"], "Add token validation middleware")
        self.assertEqual(subtask_204["status"], "In Progress")

        # Check metadata
        self.assertEqual(doc_201["metadata"]["subtask_count"], 2)

    def test_issue_links_in_markdown(self) -> None:
        """Test that issue links appear in markdown output."""
        result = load_jira_sync(path=str(self.fixture_path))

        doc_201 = next(doc for doc in result["documents"] if doc["document_id"] == "SSD-201")
        markdown = doc_201["markdown"]

        # Check for Related Issues section
        self.assertIn("## Related Issues", markdown)
        self.assertIn("blocks", markdown)
        self.assertIn("SSD-202", markdown)
        self.assertIn("Deploy authentication service", markdown)
        self.assertIn("relates to", markdown)
        self.assertIn("SSD-200", markdown)
        self.assertIn("Design authentication architecture", markdown)

    def test_subtasks_in_markdown(self) -> None:
        """Test that subtasks appear in markdown output."""
        result = load_jira_sync(path=str(self.fixture_path))

        doc_201 = next(doc for doc in result["documents"] if doc["document_id"] == "SSD-201")
        markdown = doc_201["markdown"]

        # Check for Subtasks section
        self.assertIn("## Subtasks", markdown)
        self.assertIn("SSD-203", markdown)
        self.assertIn("Add JWT token generation", markdown)
        self.assertIn("SSD-204", markdown)
        self.assertIn("Add token validation middleware", markdown)

    def test_issue_without_links_or_subtasks(self) -> None:
        """Test that issues without links/subtasks work correctly."""
        result = load_jira_sync(path=str(self.fixture_path))

        # SSD-202 has only 1 inward link, no subtasks
        doc_202 = next(doc for doc in result["documents"] if doc["document_id"] == "SSD-202")
        self.assertEqual(len(doc_202["issue_links"]), 1)
        self.assertEqual(len(doc_202["subtasks"]), 0)
        self.assertEqual(doc_202["metadata"]["issue_link_count"], 1)
        self.assertEqual(doc_202["metadata"]["subtask_count"], 0)

    def test_issue_links_in_content_blocks(self) -> None:
        """Test that issue links are added as content blocks."""
        result = load_jira_sync(path=str(self.fixture_path))

        doc_201 = next(doc for doc in result["documents"] if doc["document_id"] == "SSD-201")

        # Find Related Issues section
        related_section = next(
            (s for s in doc_201["structure"]["sections"] if s["heading"] == "Related Issues"),
            None
        )
        self.assertIsNotNone(related_section)

        # Check content blocks
        related_blocks = [
            block for block in doc_201["content_blocks"]
            if block.get("section") == "Related Issues"
        ]
        self.assertEqual(len(related_blocks), 2)

        # Verify content
        block_texts = [block["text"] for block in related_blocks]
        self.assertTrue(any("blocks SSD-202" in text for text in block_texts))
        self.assertTrue(any("relates to SSD-200" in text for text in block_texts))


if __name__ == "__main__":
    unittest.main()

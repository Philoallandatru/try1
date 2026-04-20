"""Tests for Analysis API."""
import json
import tempfile
import unittest
from pathlib import Path

from apps.portal_runner.analysis_api import (
    AnalysisAPI,
    deep_analyze_issue_response,
    get_analysis_result_response,
    search_knowledge_base_response,
)


class TestAnalysisAPI(unittest.TestCase):
    """Test Analysis API business logic."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.workspace_dir = Path(self.temp_dir) / "test_workspace"
        self.workspace_dir.mkdir(parents=True)

        # Create snapshot directory with test documents
        snapshot_dir = self.workspace_dir / "snapshot"
        snapshot_dir.mkdir(parents=True)

        # Create test documents with all required fields
        self.test_documents = [
            {
                "document_id": "SSD-777",
                "title": "NVMe flush command failure",
                "source_type": "jira",
                "version": "2026-04-20T10:00:00Z",
                "language": "en",
                "authority_level": "contextual",
                "markdown": "## Description\nNVMe flush command fails intermittently.",
                "provenance": {"source": "jira", "fetched_at": "2026-04-20T10:00:00Z"},
                "acl": {"policy": "public"},
                "structure": {"sections": [], "pages": []},
                "content_blocks": [{"text": "NVMe flush command fails intermittently.", "page": None}],
                "metadata": {
                    "issue_fields": {
                        "Summary": "NVMe flush command failure",
                        "Issue Type": "Bug",
                        "Priority": "P0",
                    }
                },
            },
            {
                "document_id": "CONF-123",
                "title": "NVMe Flush Design",
                "source_type": "confluence",
                "version": "2026-04-15T10:00:00Z",
                "language": "en",
                "authority_level": "supporting",
                "markdown": "## NVMe Flush Implementation\nFlush command implementation details.",
                "provenance": {"source": "confluence", "fetched_at": "2026-04-15T10:00:00Z"},
                "acl": {"policy": "internal"},
                "structure": {"sections": [], "pages": []},
                "content_blocks": [{"text": "Flush command implementation details.", "page": None}],
            },
            {
                "document_id": "nvme-spec-1.4",
                "title": "NVMe Specification 1.4",
                "source_type": "pdf",
                "version": "2021-06-01T00:00:00Z",
                "language": "en",
                "authority_level": "canonical",
                "markdown": "## Flush Command\nThe Flush command is used to flush data.",
                "provenance": {"source": "pdf", "fetched_at": "2021-06-01T00:00:00Z"},
                "acl": {"policy": "public"},
                "structure": {"sections": [], "pages": []},
                "content_blocks": [{"text": "The Flush command is used to flush data.", "page": None}],
            },
        ]

        documents_file = snapshot_dir / "documents.json"
        with open(documents_file, "w", encoding="utf-8") as f:
            json.dump(self.test_documents, f)

    def test_deep_analyze_issue(self):
        """Test deep analysis of a Jira issue."""
        api = AnalysisAPI(workspace_root=Path(self.temp_dir))

        result = api.deep_analyze_issue(
            workspace_dir=str(self.workspace_dir),
            issue_id="SSD-777",
            llm_backend="none",
            prompt_mode="strict",
            top_k=5,
        )

        # Verify result structure
        self.assertEqual(result["issue_id"], "SSD-777")
        self.assertIn("title", result)
        self.assertIn("issue_summary", result)
        self.assertIn("analysis_profile", result)
        self.assertIn("cross_source_citations", result)
        self.assertIn("composite_report", result)

        # Verify knowledge base storage
        issue_dir = self.workspace_dir / "knowledge" / "issues" / "SSD-777"
        self.assertTrue(issue_dir.exists())
        self.assertTrue((issue_dir / "analysis.md").exists())
        self.assertTrue((issue_dir / "metadata.json").exists())

    def test_get_analysis_result(self):
        """Test retrieving saved analysis result."""
        api = AnalysisAPI(workspace_root=Path(self.temp_dir))

        # First perform analysis
        api.deep_analyze_issue(
            workspace_dir=str(self.workspace_dir),
            issue_id="SSD-777",
            llm_backend="none",
        )

        # Then retrieve it
        result = api.get_analysis_result(
            workspace_dir=str(self.workspace_dir),
            issue_id="SSD-777",
        )

        self.assertEqual(result["issue_id"], "SSD-777")
        self.assertIn("content", result)
        self.assertIn("metadata", result)
        self.assertGreater(len(result["content"]), 0)

    def test_get_analysis_result_not_found(self):
        """Test retrieving non-existent analysis."""
        api = AnalysisAPI(workspace_root=Path(self.temp_dir))

        with self.assertRaises(ValueError) as ctx:
            api.get_analysis_result(
                workspace_dir=str(self.workspace_dir),
                issue_id="SSD-999",
            )

        self.assertIn("not found", str(ctx.exception).lower())

    def test_search_knowledge_base(self):
        """Test searching knowledge base."""
        api = AnalysisAPI(workspace_root=Path(self.temp_dir))

        # Perform analysis first
        api.deep_analyze_issue(
            workspace_dir=str(self.workspace_dir),
            issue_id="SSD-777",
            llm_backend="none",
        )

        # Search for it
        result = api.search_knowledge_base(
            workspace_dir=str(self.workspace_dir),
            query="NVMe flush",
            limit=10,
        )

        self.assertEqual(result["query"], "NVMe flush")
        self.assertGreater(result["total"], 0)
        self.assertGreater(len(result["results"]), 0)
        self.assertEqual(result["results"][0]["issue_id"], "SSD-777")

    def test_search_knowledge_base_empty(self):
        """Test searching empty knowledge base."""
        api = AnalysisAPI(workspace_root=Path(self.temp_dir))

        result = api.search_knowledge_base(
            workspace_dir=str(self.workspace_dir),
            query="nonexistent",
            limit=10,
        )

        self.assertEqual(result["query"], "nonexistent")
        self.assertEqual(result["results"], [])


class TestAnalysisAPIResponses(unittest.TestCase):
    """Test Analysis API response functions."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.workspace_dir = Path(self.temp_dir) / "test_workspace"
        self.workspace_dir.mkdir(parents=True)

        # Create snapshot with test documents
        snapshot_dir = self.workspace_dir / "snapshot"
        snapshot_dir.mkdir(parents=True)

        test_documents = [
            {
                "document_id": "SSD-777",
                "title": "Test Issue",
                "source_type": "jira",
                "version": "2026-04-20T10:00:00Z",
                "language": "en",
                "authority_level": "contextual",
                "markdown": "Test content",
                "provenance": {"source": "jira", "fetched_at": "2026-04-20T10:00:00Z"},
                "acl": {"policy": "public"},
                "structure": {"sections": [], "pages": []},
                "content_blocks": [{"text": "Test content", "page": None}],
                "metadata": {"issue_fields": {"Issue Type": "Bug"}},
            }
        ]

        documents_file = snapshot_dir / "documents.json"
        with open(documents_file, "w", encoding="utf-8") as f:
            json.dump(test_documents, f)

    def test_deep_analyze_issue_response(self):
        """Test deep_analyze_issue_response function."""
        payload = {
            "workspace_dir": str(self.workspace_dir),
            "issue_id": "SSD-777",
            "llm_backend": "none",
        }

        result = deep_analyze_issue_response(payload)

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["issue_id"], "SSD-777")
        self.assertIn("result", result)

    def test_deep_analyze_issue_response_missing_workspace(self):
        """Test deep_analyze_issue_response with missing workspace_dir."""
        payload = {"issue_id": "SSD-777"}

        with self.assertRaises(ValueError) as ctx:
            deep_analyze_issue_response(payload)

        self.assertIn("workspace_dir", str(ctx.exception))

    def test_deep_analyze_issue_response_missing_issue_id(self):
        """Test deep_analyze_issue_response with missing issue_id."""
        payload = {"workspace_dir": str(self.workspace_dir)}

        with self.assertRaises(ValueError) as ctx:
            deep_analyze_issue_response(payload)

        self.assertIn("issue_id", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()

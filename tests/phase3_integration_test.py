"""Phase 3 Integration Test - Analysis and Knowledge Base.

Tests the complete analysis workflow:
1. Deep analysis of Jira issues
2. Knowledge base storage and retrieval
3. Cross-source citation and evidence gathering
"""
import json
import tempfile
import unittest
from pathlib import Path


class TestPhase3Integration(unittest.TestCase):
    """Integration tests for Phase 3 analysis functionality."""

    def setUp(self):
        """Set up test workspace with sample documents."""
        self.temp_dir = tempfile.mkdtemp()
        self.workspace_dir = Path(self.temp_dir) / "test_workspace"
        self.workspace_dir.mkdir(parents=True)

        # Create snapshot directory
        snapshot_dir = self.workspace_dir / "snapshot"
        snapshot_dir.mkdir(parents=True)

        # Create comprehensive test documents
        self.test_documents = self._create_test_documents()

        documents_file = snapshot_dir / "documents.json"
        with open(documents_file, "w", encoding="utf-8") as f:
            json.dump(self.test_documents, f)

    def _create_test_documents(self):
        """Create test documents with proper structure."""
        return [
            # Jira Issue
            {
                "document_id": "SSD-777",
                "title": "NVMe flush command failure",
                "source_type": "jira",
                "version": "2026-04-20T10:00:00Z",
                "language": "en",
                "authority_level": "contextual",
                "markdown": "## Description\nNVMe flush command fails intermittently under high load.",
                "provenance": {"source": "jira", "fetched_at": "2026-04-20T10:00:00Z"},
                "acl": {"policy": "public"},
                "structure": {"sections": [], "pages": []},
                "content_blocks": [
                    {"text": "NVMe flush command fails intermittently under high load.", "page": None}
                ],
                "metadata": {
                    "issue_fields": {
                        "Summary": "NVMe flush command failure",
                        "Issue Type": "Bug",
                        "Priority": "P0",
                        "Status": "In Progress",
                    }
                },
            },
            # Confluence Design Doc
            {
                "document_id": "CONF-123",
                "title": "NVMe Flush Command Design",
                "source_type": "confluence",
                "version": "2026-04-15T10:00:00Z",
                "language": "en",
                "authority_level": "supporting",
                "markdown": "## NVMe Flush Implementation\nThe flush command ensures data persistence.",
                "provenance": {"source": "confluence", "fetched_at": "2026-04-15T10:00:00Z"},
                "acl": {"policy": "internal"},
                "structure": {"sections": [], "pages": []},
                "content_blocks": [
                    {"text": "The flush command ensures data persistence.", "page": None}
                ],
            },
            # NVMe Spec
            {
                "document_id": "nvme-spec-1.4",
                "title": "NVMe Specification 1.4",
                "source_type": "pdf",
                "version": "2021-06-01T00:00:00Z",
                "language": "en",
                "authority_level": "canonical",
                "markdown": "## Flush Command (Section 5.3)\nThe Flush command commits data to non-volatile media.",
                "provenance": {"source": "pdf", "fetched_at": "2021-06-01T00:00:00Z"},
                "acl": {"policy": "public"},
                "structure": {"sections": [], "pages": []},
                "content_blocks": [
                    {"text": "The Flush command commits data to non-volatile media.", "page": None}
                ],
            },
        ]

    def test_complete_analysis_workflow(self):
        """Test complete deep analysis workflow."""
        from apps.portal_runner.analysis_api import AnalysisAPI

        api = AnalysisAPI(workspace_root=Path(self.temp_dir))

        # Step 1: Perform deep analysis
        result = api.deep_analyze_issue(
            workspace_dir=str(self.workspace_dir),
            issue_id="SSD-777",
            llm_backend="none",
            prompt_mode="strict",
            top_k=5,
        )

        # Verify analysis result structure
        self.assertEqual(result["issue_id"], "SSD-777")
        self.assertIn("title", result)
        self.assertIn("issue_summary", result)
        self.assertIn("analysis_profile", result)
        self.assertIn("cross_source_citations", result)
        self.assertIn("composite_report", result)

        # Verify cross-source retrieval
        citations = result.get("cross_source_citations", [])
        self.assertGreater(len(citations), 0, "Should have cross-source citations")

        # Verify knowledge base storage
        issue_dir = self.workspace_dir / "knowledge" / "issues" / "SSD-777"
        self.assertTrue(issue_dir.exists(), "Knowledge base directory should exist")
        self.assertTrue((issue_dir / "analysis.md").exists(), "Analysis markdown should exist")
        self.assertTrue((issue_dir / "metadata.json").exists(), "Metadata should exist")

        # Step 2: Retrieve saved analysis
        saved_result = api.get_analysis_result(
            workspace_dir=str(self.workspace_dir),
            issue_id="SSD-777",
        )

        self.assertEqual(saved_result["issue_id"], "SSD-777")
        self.assertIn("content", saved_result)
        self.assertIn("metadata", saved_result)
        self.assertGreater(len(saved_result["content"]), 0)

        # Step 3: Search knowledge base
        search_result = api.search_knowledge_base(
            workspace_dir=str(self.workspace_dir),
            query="NVMe flush",
            limit=10,
        )

        self.assertEqual(search_result["query"], "NVMe flush")
        self.assertGreater(search_result["total"], 0)
        self.assertEqual(search_result["results"][0]["issue_id"], "SSD-777")

    def test_analysis_with_citations(self):
        """Test that analysis includes proper citations."""
        from apps.portal_runner.analysis_api import AnalysisAPI

        api = AnalysisAPI(workspace_root=Path(self.temp_dir))

        result = api.deep_analyze_issue(
            workspace_dir=str(self.workspace_dir),
            issue_id="SSD-777",
            llm_backend="none",
            top_k=5,
        )

        # Verify citations structure
        self.assertIn("confluence_evidence", result)
        self.assertIn("spec_evidence", result)

        confluence_citations = result["confluence_evidence"].get("citations", [])
        spec_citations = result["spec_evidence"].get("citations", [])

        # Should have citations from both sources
        total_citations = len(confluence_citations) + len(spec_citations)
        self.assertGreater(total_citations, 0, "Should have citations from Confluence or Spec")

    def test_knowledge_base_persistence(self):
        """Test that knowledge base persists across API calls."""
        from apps.portal_runner.analysis_api import AnalysisAPI

        api = AnalysisAPI(workspace_root=Path(self.temp_dir))

        # Perform analysis
        api.deep_analyze_issue(
            workspace_dir=str(self.workspace_dir),
            issue_id="SSD-777",
            llm_backend="none",
        )

        # Create new API instance (simulating server restart)
        api2 = AnalysisAPI(workspace_root=Path(self.temp_dir))

        # Should still be able to retrieve analysis
        result = api2.get_analysis_result(
            workspace_dir=str(self.workspace_dir),
            issue_id="SSD-777",
        )

        self.assertEqual(result["issue_id"], "SSD-777")
        self.assertGreater(len(result["content"]), 0)

    def test_metadata_accuracy(self):
        """Test that metadata is accurate and complete."""
        from apps.portal_runner.analysis_api import AnalysisAPI

        api = AnalysisAPI(workspace_root=Path(self.temp_dir))

        result = api.deep_analyze_issue(
            workspace_dir=str(self.workspace_dir),
            issue_id="SSD-777",
            llm_backend="none",
        )

        # Load metadata file
        metadata_file = self.workspace_dir / "knowledge" / "issues" / "SSD-777" / "metadata.json"
        with open(metadata_file, encoding="utf-8") as f:
            metadata = json.load(f)

        # Verify metadata fields
        self.assertEqual(metadata["issue_id"], "SSD-777")
        self.assertEqual(metadata["title"], "NVMe flush command failure")
        self.assertIn("analyzed_at", metadata)
        self.assertIn("analysis_profile", metadata)
        self.assertIn("citation_count", metadata)
        self.assertGreaterEqual(metadata["citation_count"], 0)


if __name__ == "__main__":
    unittest.main()

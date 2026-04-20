"""
Phase 3 E2E Test with Real NVMe Demo Data

Tests deep analysis using realistic SSD firmware bug data from fixtures.
"""

import json
import re
import tempfile
from pathlib import Path

import pytest

from apps.portal_runner.analysis_api import AnalysisAPI


def jira_issue_to_document(issue: dict) -> dict:
    """Convert Jira issue to document dict format."""
    content_parts = [
        f"# {issue['summary']}",
        f"\n**Key**: {issue['key']}",
        f"**Type**: {issue['type']}",
        f"**Priority**: {issue['priority']}",
        f"**Status**: {issue['status']}",
        f"\n## Description\n{issue['description']}",
    ]

    if issue.get("root_cause"):
        content_parts.append(f"\n## Root Cause\n{issue['root_cause']}")

    if issue.get("comments"):
        content_parts.append("\n## Comments")
        for comment in issue["comments"]:
            author = comment.get("author", {}).get("displayName", "Unknown")
            body = comment.get("body", "")
            content_parts.append(f"\n**{author}**: {body}")

    full_text = "\n".join(content_parts)

    return {
        "document_id": issue["key"],
        "title": issue["summary"],
        "source_type": "jira",
        "version": issue["updated_at"],
        "language": "en",
        "authority_level": "contextual",
        "markdown": full_text,
        "provenance": {
            "source": "jira",
            "project": issue["project"],
            "fetched_at": issue["updated_at"],
        },
        "acl": {"policy": "public"},
        "structure": {"sections": [], "pages": []},
        "content_blocks": [{"text": full_text, "page": None}],
        "metadata": {
            "issue_fields": {
                "Type": issue["type"],
                "Priority": issue["priority"],
                "Status": issue["status"],
            }
        },
        "terminology": {"terms": []},
    }


def confluence_page_to_document(page: dict) -> dict:
    """Convert Confluence page to document dict format."""
    html_content = page["body"]["storage"]["value"]
    text_content = re.sub(r"<[^>]+>", " ", html_content)
    text_content = re.sub(r"\s+", " ", text_content).strip()
    full_text = f"# {page['title']}\n\n{text_content}"

    return {
        "document_id": page["id"],
        "title": page["title"],
        "source_type": "confluence",
        "version": page["version"]["when"],
        "language": "en",
        "authority_level": "contextual",
        "markdown": full_text,
        "provenance": {
            "source": "confluence",
            "space": page["space"],
            "fetched_at": page["version"]["when"],
        },
        "acl": {"policy": "public"},
        "structure": {"sections": [], "pages": []},
        "content_blocks": [{"text": full_text, "page": None}],
        "metadata": {"space": page["space"]},
        "terminology": {"terms": []},
    }


class TestNVMeRealData:
    """E2E tests with real NVMe demo data."""

    def test_s4_resume_timeout_analysis(self):
        """Test analysis of SSD-DEMO-A (S4 Resume Timeout)."""
        # Load fixtures
        jira_fixture = Path("fixtures/demo/jira/nvme_demo_sync.json")
        confluence_fixture = Path("fixtures/demo/confluence/nvme_demo_pages.json")

        with open(jira_fixture, encoding="utf-8") as f:
            jira_data = json.load(f)

        with open(confluence_fixture, encoding="utf-8") as f:
            confluence_data = json.load(f)

        # Find target issue and related page
        target_issue = next(
            (issue for issue in jira_data["issues"] if issue["key"] == "SSD-DEMO-A"),
            None,
        )
        assert target_issue is not None, "SSD-DEMO-A not found"

        related_page = next(
            (page for page in confluence_data["pages"] if page["id"] == "CONF-DEMO-1"),
            None,
        )
        assert related_page is not None, "CONF-DEMO-1 not found"

        # Convert to documents
        issue_doc = jira_issue_to_document(target_issue)
        confluence_doc = confluence_page_to_document(related_page)

        # Create temporary workspace
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_path = Path(tmpdir)

            # Create snapshot with documents
            snapshot_dir = workspace_path / "snapshot"
            snapshot_dir.mkdir(parents=True)

            documents_file = snapshot_dir / "documents.json"
            with open(documents_file, "w", encoding="utf-8") as f:
                json.dump([issue_doc, confluence_doc], f, indent=2)

            # Create API and analyze
            api = AnalysisAPI(workspace_root=workspace_path)

            result = api.deep_analyze_issue(
                issue_id="SSD-DEMO-A",
                workspace_dir=str(workspace_path),
                llm_backend="mock",
                prompt_mode="balanced",
            )

            # Validate result structure
            assert result["issue_id"] == "SSD-DEMO-A"
            assert "composite_report" in result
            assert "cross_source_citations" in result

            # Check saved files
            issue_dir = workspace_path / "knowledge" / "issues" / "SSD-DEMO-A"
            assert issue_dir.exists()

            analysis_file = issue_dir / "analysis.md"
            assert analysis_file.exists()

            analysis_content = analysis_file.read_text(encoding="utf-8")
            assert len(analysis_content) > 0

            # Check metadata
            metadata_file = issue_dir / "metadata.json"
            assert metadata_file.exists()

            with open(metadata_file, encoding="utf-8") as f:
                metadata = json.load(f)

            assert metadata["issue_id"] == "SSD-DEMO-A"
            assert "analyzed_at" in metadata

    def test_batch_analysis_and_daily_report(self):
        """Test batch analysis of multiple issues and daily report generation."""
        # Load fixtures
        jira_fixture = Path("fixtures/demo/jira/nvme_demo_sync.json")
        confluence_fixture = Path("fixtures/demo/confluence/nvme_demo_pages.json")

        with open(jira_fixture, encoding="utf-8") as f:
            jira_data = json.load(f)

        with open(confluence_fixture, encoding="utf-8") as f:
            confluence_data = json.load(f)

        # Convert all documents
        all_docs = []
        for issue in jira_data["issues"]:
            all_docs.append(jira_issue_to_document(issue))

        for page in confluence_data["pages"]:
            all_docs.append(confluence_page_to_document(page))

        # Create temporary workspace
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_path = Path(tmpdir)

            # Create snapshot
            snapshot_dir = workspace_path / "snapshot"
            snapshot_dir.mkdir(parents=True)

            documents_file = snapshot_dir / "documents.json"
            with open(documents_file, "w", encoding="utf-8") as f:
                json.dump(all_docs, f, indent=2)

            # Create API
            api = AnalysisAPI(workspace_root=workspace_path)

            # Analyze DEMO issues
            demo_issues = ["SSD-DEMO-A", "SSD-DEMO-B", "SSD-DEMO-C", "SSD-DEMO-D"]

            for issue_id in demo_issues:
                result = api.deep_analyze_issue(
                    issue_id=issue_id,
                    workspace_dir=str(workspace_path),
                    llm_backend="mock",
                    prompt_mode="balanced",
                )
                assert result["issue_id"] == issue_id
                assert "composite_report" in result

            # Generate daily report
            report = api.generate_daily_report(
                workspace_dir=str(workspace_path),
                mode="fast",
            )

            # Validate report
            assert report["mode"] == "fast"
            assert report["total_issues"] == 4
            assert len(report["sections"]) > 0

            # Check all issues appear in report
            report_text = json.dumps(report)
            for issue_id in demo_issues:
                assert issue_id in report_text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""Test Jira Sprint and Epic extraction."""

from pathlib import Path

from services.connectors.jira.connector import load_jira_sync


def test_sprint_extraction():
    """Test that sprint information is correctly extracted."""
    fixture_path = Path(__file__).parent.parent.parent / "fixtures" / "connectors" / "jira" / "issue_with_sprint_epic.json"
    result = load_jira_sync(fixture_path)

    assert result["sync_type"] == "full"
    assert len(result["documents"]) == 2

    # Check first issue (SSD-301) with full sprint info
    doc1 = result["documents"][0]
    assert doc1["document_id"] == "SSD-301"
    assert "sprints" in doc1
    assert len(doc1["sprints"]) == 1

    sprint = doc1["sprints"][0]
    assert sprint["name"] == "Sprint 15"
    assert sprint["state"] == "active"
    assert sprint["goal"] == "Complete search and analysis features"
    assert "start_date" in sprint
    assert "end_date" in sprint

    # Check sprint in markdown
    assert "## Sprint" in doc1["markdown"]
    assert "Sprint 15" in doc1["markdown"]
    assert "Complete search and analysis features" in doc1["markdown"]

    # Check sprint in content blocks
    sprint_blocks = [block for block in doc1["content_blocks"] if block.get("section") == "Sprint"]
    assert len(sprint_blocks) > 0
    assert "Sprint 15" in sprint_blocks[0]["text"]

    # Check metadata
    assert doc1["metadata"]["sprint_count"] == 1


def test_epic_extraction():
    """Test that epic information is correctly extracted."""
    fixture_path = Path(__file__).parent.parent.parent / "fixtures" / "connectors" / "jira" / "issue_with_sprint_epic.json"
    result = load_jira_sync(fixture_path)

    # Check first issue (SSD-301) with epic
    doc1 = result["documents"][0]
    assert doc1["document_id"] == "SSD-301"
    assert "epic" in doc1
    assert doc1["epic"] is not None

    epic = doc1["epic"]
    assert epic["key"] == "SSD-300"
    assert epic["summary"] == "Search and Retrieval System"
    assert epic["status"] == "In Progress"

    # Check epic in markdown
    assert "## Epic" in doc1["markdown"]
    assert "SSD-300" in doc1["markdown"]
    assert "Search and Retrieval System" in doc1["markdown"]

    # Check epic in content blocks
    epic_blocks = [block for block in doc1["content_blocks"] if block.get("section") == "Epic"]
    assert len(epic_blocks) > 0
    assert "SSD-300" in epic_blocks[0]["text"]

    # Check metadata
    assert doc1["metadata"]["has_epic"] is True


def test_comment_metadata_extraction():
    """Test that comment metadata is correctly extracted."""
    fixture_path = Path(__file__).parent.parent.parent / "fixtures" / "connectors" / "jira" / "issue_with_sprint_epic.json"
    result = load_jira_sync(fixture_path)

    doc1 = result["documents"][0]
    assert "comment_metadata" in doc1
    assert len(doc1["comment_metadata"]) == 2

    # Check first comment
    comment1 = doc1["comment_metadata"][0]
    assert comment1["id"] == "10100"
    assert comment1["author_name"] == "Bob Chen"
    assert comment1["author_email"] == "bob@example.com"
    assert comment1["author_id"] == "user123"
    assert comment1["created"] == "2026-04-20T14:30:00.000Z"
    assert comment1["updated"] == "2026-04-20T15:00:00.000Z"
    assert "BM25 implementation" in comment1["body"]

    # Check second comment
    comment2 = doc1["comment_metadata"][1]
    assert comment2["id"] == "10101"
    assert comment2["author_name"] == "Alice Wang"
    assert comment2["author_email"] == "alice@example.com"
    assert "unit tests" in comment2["body"]


def test_issue_without_sprint_epic():
    """Test that issues without sprint/epic are handled correctly."""
    fixture_path = Path(__file__).parent.parent.parent / "fixtures" / "connectors" / "jira" / "issue_with_links.json"
    result = load_jira_sync(fixture_path)

    doc1 = result["documents"][0]
    assert doc1["document_id"] == "SSD-201"
    assert "sprints" in doc1
    assert len(doc1["sprints"]) == 0
    assert doc1.get("epic") is None
    assert doc1["metadata"]["sprint_count"] == 0
    assert doc1["metadata"]["has_epic"] is False


def test_sprint_epic_in_search_content():
    """Test that sprint and epic info is included in searchable content."""
    fixture_path = Path(__file__).parent.parent.parent / "fixtures" / "connectors" / "jira" / "issue_with_sprint_epic.json"
    result = load_jira_sync(fixture_path)

    doc1 = result["documents"][0]

    # Sprint info should be in content blocks for search
    all_text = " ".join(block["text"] for block in doc1["content_blocks"])
    assert "Sprint 15" in all_text
    assert "Complete search and analysis features" in all_text

    # Epic info should be in content blocks for search
    assert "SSD-300" in all_text
    assert "Search and Retrieval System" in all_text

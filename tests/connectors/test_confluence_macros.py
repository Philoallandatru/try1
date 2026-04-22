"""Test Confluence macro extraction."""

from pathlib import Path

from services.connectors.confluence.connector import load_confluence_sync


def test_jira_macro_extraction():
    """Test that Jira issue macros are correctly extracted."""
    fixture_path = Path(__file__).parent.parent.parent / "fixtures" / "connectors" / "confluence" / "page_with_macros.json"
    result = load_confluence_sync(fixture_path)

    assert result["sync_type"] == "full"
    assert len(result["documents"]) == 2

    # Check first page with Jira macro
    doc1 = result["documents"][0]
    assert doc1["document_id"] == "98765"
    assert doc1["title"] == "API Documentation"

    # Check Jira macro in markdown
    assert "Jira Issue" in doc1["markdown"]
    assert "SSD-301" in doc1["markdown"]


def test_code_macro_extraction():
    """Test that code macros are correctly extracted."""
    fixture_path = Path(__file__).parent.parent.parent / "fixtures" / "connectors" / "confluence" / "page_with_macros.json"
    result = load_confluence_sync(fixture_path)

    doc1 = result["documents"][0]

    # Check code macro in markdown
    assert "```python" in doc1["markdown"]
    assert "def search_documents" in doc1["markdown"]
    assert "bm25_search" in doc1["markdown"]

    # Check code is in content blocks for search
    all_text = " ".join(block["text"] for block in doc1["content_blocks"])
    assert "search_documents" in all_text
    assert "bm25_search" in all_text


def test_status_macro_extraction():
    """Test that status macros are correctly extracted."""
    fixture_path = Path(__file__).parent.parent.parent / "fixtures" / "connectors" / "confluence" / "page_with_macros.json"
    result = load_confluence_sync(fixture_path)

    doc1 = result["documents"][0]

    # Check status macro in markdown
    assert "Status" in doc1["markdown"]
    assert "COMPLETE" in doc1["markdown"]
    assert "Green" in doc1["markdown"]


def test_info_panel_extraction():
    """Test that info panel macros are correctly extracted."""
    fixture_path = Path(__file__).parent.parent.parent / "fixtures" / "connectors" / "confluence" / "page_with_macros.json"
    result = load_confluence_sync(fixture_path)

    doc1 = result["documents"][0]

    # Check info panel in markdown
    assert "INFO" in doc1["markdown"]
    assert "beta" in doc1["markdown"]
    assert "development team" in doc1["markdown"]


def test_expand_macro_extraction():
    """Test that expand macros are correctly extracted."""
    fixture_path = Path(__file__).parent.parent.parent / "fixtures" / "connectors" / "confluence" / "page_with_macros.json"
    result = load_confluence_sync(fixture_path)

    doc1 = result["documents"][0]

    # Check expand macro in markdown
    assert "Click to see details" in doc1["markdown"]
    assert "implementation details" in doc1["markdown"]


def test_task_list_extraction():
    """Test that task lists are correctly extracted."""
    fixture_path = Path(__file__).parent.parent.parent / "fixtures" / "connectors" / "confluence" / "page_with_macros.json"
    result = load_confluence_sync(fixture_path)

    doc2 = result["documents"][1]
    assert doc2["document_id"] == "98766"
    assert doc2["title"] == "Meeting Notes"

    # Check task list in markdown
    assert "[ ] Review API documentation" in doc2["markdown"]
    assert "[x] Update test coverage" in doc2["markdown"]


def test_user_mention_extraction():
    """Test that user mentions are correctly extracted."""
    fixture_path = Path(__file__).parent.parent.parent / "fixtures" / "connectors" / "confluence" / "page_with_macros.json"
    result = load_confluence_sync(fixture_path)

    doc2 = result["documents"][1]

    # Check user mentions in markdown
    assert "@Bob Chen" in doc2["markdown"]
    assert "@Alice Wang" in doc2["markdown"]


def test_macro_content_searchable():
    """Test that macro content is included in searchable content blocks."""
    fixture_path = Path(__file__).parent.parent.parent / "fixtures" / "connectors" / "confluence" / "page_with_macros.json"
    result = load_confluence_sync(fixture_path)

    doc1 = result["documents"][0]

    # All macro content should be searchable
    all_text = " ".join(block["text"] for block in doc1["content_blocks"])

    # Jira macro content
    assert "SSD-301" in all_text

    # Code macro content
    assert "search_documents" in all_text

    # Status macro content
    assert "COMPLETE" in all_text

    # Info panel content
    assert "beta" in all_text

    # Expand macro content
    assert "implementation details" in all_text


def test_page_without_macros():
    """Test that pages without macros are handled correctly."""
    fixture_path = Path(__file__).parent.parent.parent / "fixtures" / "connectors" / "confluence" / "page_with_hierarchy.json"
    result = load_confluence_sync(fixture_path)

    # Should still work for pages without macros
    assert len(result["documents"]) > 0
    doc1 = result["documents"][0]
    assert "markdown" in doc1
    assert len(doc1["content_blocks"]) > 0

"""Test TOC (Table of Contents) filtering in PDF ingestion."""
from __future__ import annotations

import pytest

from services.ingest.adapters.pdf.adapter import _is_toc_page


def test_is_toc_page_with_table_of_contents():
    """Test detection of 'Table of Contents' page."""
    page_blocks = [
        "Table of Contents",
        "1. Introduction ............... 5",
        "2. Architecture .............. 12",
        "3. Implementation ............ 25",
    ]
    assert _is_toc_page(page_blocks) is True


def test_is_toc_page_with_table_of_figures():
    """Test detection of 'Table of Figures' page."""
    page_blocks = [
        "Table of Figures",
        "Figure 1: System Overview ........ 10",
        "Figure 2: Data Flow .............. 15",
        "Figure 3: Architecture ........... 20",
    ]
    assert _is_toc_page(page_blocks) is True


def test_is_toc_page_with_list_of_tables():
    """Test detection of 'List of Tables' page."""
    page_blocks = [
        "List of Tables",
        "Table 1: Configuration Options ... 8",
        "Table 2: Performance Metrics ..... 14",
    ]
    assert _is_toc_page(page_blocks) is True


def test_is_toc_page_with_high_page_ref_density():
    """Test detection based on high density of page references."""
    page_blocks = [
        "Chapter 1: Introduction .......... 5",
        "Section 1.1: Overview ............ 6",
        "Section 1.2: Goals ............... 8",
        "Chapter 2: Design ................ 12",
        "Section 2.1: Architecture ........ 13",
        "Section 2.2: Components .......... 18",
    ]
    # 6 out of 6 blocks have page references (100% > 30% threshold)
    assert _is_toc_page(page_blocks) is True


def test_is_not_toc_page_normal_content():
    """Test that normal content pages are not detected as TOC."""
    page_blocks = [
        "1. Introduction",
        "This chapter provides an overview of the system.",
        "The architecture is designed to be scalable and maintainable.",
        "We use a microservices approach with clear boundaries.",
    ]
    assert _is_toc_page(page_blocks) is False


def test_is_not_toc_page_with_few_page_refs():
    """Test that pages with few page references are not detected as TOC."""
    page_blocks = [
        "Section 2.1: Architecture",
        "The system consists of multiple components.",
        "See Figure 1 on page 10 for details.",
        "Each component has a specific responsibility.",
        "The data flow is shown in Figure 2.",
    ]
    # Only 1 out of 5 blocks has page reference (20% < 30% threshold)
    assert _is_toc_page(page_blocks) is False


def test_is_not_toc_page_empty():
    """Test that empty page blocks return False."""
    assert _is_toc_page([]) is False


def test_is_toc_page_case_insensitive():
    """Test that TOC detection is case-insensitive."""
    page_blocks = [
        "table of contents",
        "Chapter 1 ............... 5",
    ]
    assert _is_toc_page(page_blocks) is True

    page_blocks = [
        "TABLE OF FIGURES",
        "Figure 1 ............... 10",
    ]
    assert _is_toc_page(page_blocks) is True


def test_is_toc_page_contents_only():
    """Test detection of simple 'Contents' title."""
    page_blocks = [
        "Contents",
        "Introduction ............... 1",
        "Background ................. 5",
    ]
    assert _is_toc_page(page_blocks) is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

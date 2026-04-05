from __future__ import annotations


def _first_section_for_page(entry: dict) -> dict | None:
    page = entry.get("page")
    for section in entry.get("structure", {}).get("sections", []):
        if page is None or section.get("page") == page or section.get("page") is None:
            return section
    return None


def _first_table_for_page(entry: dict) -> dict | None:
    page = entry.get("page")
    for table in entry.get("structure", {}).get("tables", []):
        if page is None or table.get("page") == page or table.get("page") is None:
            return table
    return None


def _first_figure_for_page(entry: dict) -> dict | None:
    page = entry.get("page")
    for figure in entry.get("structure", {}).get("figures", []):
        if page is None or figure.get("page") == page or figure.get("page") is None:
            return figure
    return None


def assemble_citation(entry: dict) -> dict:
    section = _first_section_for_page(entry)
    table = _first_table_for_page(entry)
    figure = _first_figure_for_page(entry)
    evidence = [block.get("text", "") for block in entry.get("content_blocks", []) if block.get("text")]
    return {
        "document": entry["document_id"],
        "title": entry["title"],
        "version": entry["version"],
        "page": entry.get("page"),
        "section": section.get("heading") if section else None,
        "clause": section.get("clause") if section else None,
        "table_id": table.get("id") if table else None,
        "figure_id": figure.get("id") if figure else None,
        "source_uri": entry.get("provenance", {}).get("source_uri"),
        "evidence_span": evidence[:3],
    }


def build_source_inspection(entry: dict) -> dict:
    citation = assemble_citation(entry)
    return {
        "document_id": entry["document_id"],
        "title": entry["title"],
        "version": entry["version"],
        "authority_level": entry["authority_level"],
        "page": entry.get("page"),
        "language": entry.get("language"),
        "source_uri": entry.get("provenance", {}).get("source_uri"),
        "section": citation["section"],
        "clause": citation["clause"],
        "table_id": citation["table_id"],
        "figure_id": citation["figure_id"],
        "content_blocks": entry.get("content_blocks", []),
    }


from __future__ import annotations

from pathlib import Path
import re


TEXT_PATTERN = re.compile(rb"\((.*?)\)\s*Tj", re.DOTALL)
STREAM_PATTERN = re.compile(rb"stream\r?\n(.*?)\r?\nendstream", re.DOTALL)
SECTION_PATTERN = re.compile(r"^(?P<clause>\d+(?:\.\d+)*)\s+(?P<title>.+)$")
TABLE_PATTERN = re.compile(r"^Table\s+(?P<id>\d+)\s*:\s*(?P<title>.+)$", re.IGNORECASE)
FIGURE_PATTERN = re.compile(r"^Figure\s+(?P<id>\d+)\s*:\s*(?P<title>.+)$", re.IGNORECASE)
PAGE_PATTERN = re.compile(r"^Page\s+(?P<page>\d+)$", re.IGNORECASE)


def _decode_pdf_literal(raw: bytes) -> str:
    text = raw.decode("latin-1")
    text = text.replace(r"\(", "(").replace(r"\)", ")").replace(r"\n", "\n")
    return text.strip()


def extract_pdf_structure(path: str | Path) -> dict:
    source = Path(path)
    pdf_bytes = source.read_bytes()
    streams = STREAM_PATTERN.findall(pdf_bytes)
    extracted_lines: list[str] = []

    for stream in streams:
        for match in TEXT_PATTERN.findall(stream):
            line = _decode_pdf_literal(match)
            if line:
                extracted_lines.append(line)

    pages = []
    sections = []
    tables = []
    figures = []
    content_blocks = []
    current_page = None

    for idx, line in enumerate(extracted_lines, start=1):
        page_match = PAGE_PATTERN.match(line)
        if page_match:
            current_page = int(page_match.group("page"))
            pages.append({"page": current_page})
            continue

        section_match = SECTION_PATTERN.match(line)
        if section_match:
            sections.append(
                {
                    "id": f"section-{len(sections) + 1}",
                    "clause": section_match.group("clause"),
                    "heading": section_match.group("title"),
                    "page": current_page,
                }
            )

        table_match = TABLE_PATTERN.match(line)
        if table_match:
            tables.append(
                {
                    "id": f"table-{table_match.group('id')}",
                    "title": table_match.group("title"),
                    "page": current_page,
                }
            )

        figure_match = FIGURE_PATTERN.match(line)
        if figure_match:
            figures.append(
                {
                    "id": f"figure-{figure_match.group('id')}",
                    "title": figure_match.group("title"),
                    "page": current_page,
                }
            )

        content_blocks.append(
            {
                "id": f"block-{idx}",
                "page": current_page,
                "text": line,
            }
        )

    title = sections[0]["heading"] if sections else source.stem
    return {
        "document_id": source.stem,
        "source_type": "pdf",
        "authority_level": "canonical",
        "version": "fixture",
        "language": "en",
        "title": title,
        "provenance": {
            "source_uri": str(source).replace("\\", "/"),
            "ingested_at": "fixture",
        },
        "acl": {
            "policy": "team:ssd",
            "inherits_from": None,
        },
        "structure": {
            "pages": pages,
            "sections": sections,
            "tables": tables,
            "figures": figures,
            "worksheets": [],
            "slides": [],
        },
        "terminology": {
            "terms": [],
        },
        "content_blocks": content_blocks,
    }


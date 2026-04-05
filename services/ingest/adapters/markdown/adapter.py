from __future__ import annotations

from pathlib import Path


def parse_markdown(path: str | Path) -> dict:
    source = Path(path)
    text = source.read_text(encoding="utf-8")
    lines = text.splitlines()

    sections = []
    content_blocks = []
    current_heading = None
    block_index = 1

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#"):
            level = len(stripped) - len(stripped.lstrip("#"))
            heading = stripped[level:].strip()
            current_heading = heading
            sections.append(
                {
                    "id": f"sec-{len(sections) + 1}",
                    "level": level,
                    "heading": heading,
                }
            )
            continue
        if stripped:
            content_blocks.append(
                {
                    "id": f"block-{block_index}",
                    "section_heading": current_heading,
                    "text": stripped,
                }
            )
            block_index += 1

    title = sections[0]["heading"] if sections else source.stem
    return {
        "document_id": source.stem,
        "source_type": "md",
        "authority_level": "supporting",
        "version": "draft",
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
            "pages": [],
            "sections": sections,
            "tables": [],
            "figures": [],
            "worksheets": [],
            "slides": [],
        },
        "terminology": {
            "terms": [],
        },
        "content_blocks": content_blocks,
    }


from __future__ import annotations

from pathlib import Path
import re


MARKDOWN_HEADING_PATTERN = re.compile(r"^(?P<hashes>#{1,6})\s+(?P<title>.+)$")


def build_base_document(
    *,
    document_id: str,
    source_type: str,
    authority_level: str,
    version: str,
    language: str,
    title: str,
    source_uri: str,
    ingested_at: str,
    parser: str | None = None,
    acl_policy: str = "team:ssd",
    acl_inherits_from: str | None = None,
    terminology_terms: list[dict] | None = None,
    extra_provenance: dict | None = None,
) -> dict:
    provenance = {
        "source_uri": source_uri,
        "ingested_at": ingested_at,
    }
    if parser:
        provenance["parser"] = parser
    if extra_provenance:
        provenance.update(extra_provenance)

    return {
        "document_id": document_id,
        "source_type": source_type,
        "authority_level": authority_level,
        "version": version,
        "language": language,
        "title": title,
        "provenance": provenance,
        "acl": {
            "policy": acl_policy,
            "inherits_from": acl_inherits_from,
        },
        "structure": {
            "pages": [],
            "sections": [],
            "tables": [],
            "figures": [],
            "worksheets": [],
            "slides": [],
        },
        "terminology": {
            "terms": terminology_terms or [],
        },
        "content_blocks": [],
    }


def finalize_document(payload: dict) -> dict:
    sections = payload["structure"]["sections"]
    if sections:
        payload["title"] = sections[0]["heading"]
    elif payload["content_blocks"]:
        payload["title"] = payload["content_blocks"][0]["text"][:120]
    return payload


def register_page(payload: dict, page_number: int, seen_pages: set[int] | None = None) -> None:
    if seen_pages is not None and page_number in seen_pages:
        return
    payload["structure"]["pages"].append({"page": page_number})
    if seen_pages is not None:
        seen_pages.add(page_number)


def append_section(payload: dict, heading: str, **extra_fields: object) -> None:
    payload["structure"]["sections"].append(
        {
            "id": f"section-{len(payload['structure']['sections']) + 1}",
            "heading": heading,
            **extra_fields,
        }
    )


def append_caption_item(payload: dict, key: str, item_id: str, title: str, **extra_fields: object) -> None:
    payload["structure"][key].append(
        {
            "id": item_id,
            "title": title,
            **extra_fields,
        }
    )


def append_content_block(payload: dict, text: str, **extra_fields: object) -> None:
    payload["content_blocks"].append(
        {
            "id": f"block-{len(payload['content_blocks']) + 1}",
            "text": text,
            **extra_fields,
        }
    )


def normalize_markdown_text(
    markdown_text: str,
    *,
    document_id: str,
    source_type: str,
    authority_level: str,
    version: str,
    language: str,
    title: str,
    source_uri: str,
    ingested_at: str,
    parser: str = "markdown-normalizer",
    acl_policy: str = "team:ssd",
    acl_inherits_from: str | None = None,
    terminology_terms: list[dict] | None = None,
    extra_provenance: dict | None = None,
    block_extras: dict | None = None,
) -> dict:
    payload = build_base_document(
        document_id=document_id,
        source_type=source_type,
        authority_level=authority_level,
        version=version,
        language=language,
        title=title,
        source_uri=source_uri,
        ingested_at=ingested_at,
        parser=parser,
        acl_policy=acl_policy,
        acl_inherits_from=acl_inherits_from,
        terminology_terms=terminology_terms,
        extra_provenance=extra_provenance,
    )
    current_heading = None
    extras = block_extras or {}

    for raw_line in markdown_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        heading_match = MARKDOWN_HEADING_PATTERN.match(line)
        if heading_match:
            level = len(heading_match.group("hashes"))
            heading = heading_match.group("title").strip()
            current_heading = heading
            append_section(payload, heading=heading, level=level)
            continue

        block_payload = dict(extras)
        if current_heading:
            block_payload["section_heading"] = current_heading
        append_content_block(payload, line, **block_payload)

    if payload["structure"]["sections"]:
        payload["title"] = payload["structure"]["sections"][0]["heading"]
    return payload


def normalize_markdown_file(
    path: str | Path,
    *,
    source_type: str = "md",
    authority_level: str = "supporting",
    version: str = "draft",
    language: str = "en",
    ingested_at: str = "fixture",
    acl_policy: str = "team:ssd",
) -> dict:
    source = Path(path)
    return normalize_markdown_text(
        source.read_text(encoding="utf-8"),
        document_id=source.stem,
        source_type=source_type,
        authority_level=authority_level,
        version=version,
        language=language,
        title=source.stem,
        source_uri=str(source).replace("\\", "/"),
        ingested_at=ingested_at,
        acl_policy=acl_policy,
        parser="markdown-file-normalizer",
    )

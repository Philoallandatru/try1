from __future__ import annotations


def _block_text(block: dict) -> str:
    return str(block.get("text", "")).strip()


def _page_label(document: dict, page: int | None) -> str:
    if document.get("source_type") == "pptx" and page is not None:
        return f"Slide {page}"
    if page is not None:
        return f"Page {page}"
    return "Content"


def _ordered_pages(document: dict) -> list[int | None]:
    pages = [page.get("page") for page in document.get("structure", {}).get("pages", [])]
    if pages:
        return pages
    return [None]


def _blocks_for_page(document: dict, page: int | None) -> list[dict]:
    return [
        block
        for block in document.get("content_blocks", [])
        if block.get("page") == page or (page is None and block.get("page") in (None, "", 0))
    ]


def document_to_markdown(document: dict) -> str:
    if document.get("markdown"):
        return str(document["markdown"]).strip()

    title = document.get("title") or document.get("document_id") or "Untitled Document"
    lines = [f"# {title}", ""]
    source_uri = document.get("provenance", {}).get("source_uri")
    if source_uri:
        lines.extend([f"Source: {source_uri}", ""])

    for page in _ordered_pages(document):
        page_blocks = [_block_text(block) for block in _blocks_for_page(document, page)]
        page_blocks = [text for text in page_blocks if text]
        if not page_blocks:
            continue
        lines.extend([f"## {_page_label(document, page)}", ""])
        lines.extend(page_blocks)
        lines.append("")

    return "\n".join(lines).strip()


def ensure_document_markdown(document: dict) -> dict:
    document["markdown"] = document_to_markdown(document)
    return document


def documents_to_markdown(documents: list[dict]) -> str:
    return "\n\n---\n\n".join(document_to_markdown(document) for document in documents)

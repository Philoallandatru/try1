from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Iterable
import json
import re


TOKEN_PATTERN = re.compile(r"[\w\u4e00-\u9fff]+", re.UNICODE)
AUTHORITY_BOOST = {
    "canonical": 3.0,
    "supporting": 2.0,
    "contextual": 1.0,
}


def tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_PATTERN.findall(text)]


def _extract_terminology_terms(document: dict) -> list[str]:
    terms = []
    for entry in document.get("terminology", {}).get("terms", []):
        for value in entry.values():
            if isinstance(value, str) and value.strip():
                terms.append(value.strip())
    return terms


def _collect_page_numbers(document: dict) -> set[int | None]:
    pages = {page.get("page") for page in document.get("structure", {}).get("pages", [])}
    return pages or {None}


def build_page_index(documents: Iterable[dict]) -> list[dict]:
    entries = []
    for document in documents:
        page_numbers = _collect_page_numbers(document)
        terminology_terms = _extract_terminology_terms(document)
        for page in page_numbers:
            page_blocks = [
                block for block in document.get("content_blocks", [])
                if block.get("page") == page or (page is None and block.get("page") in (None, "", 0))
            ]
            if not page_blocks and page is not None:
                continue

            block_text = " ".join(block.get("text", "") for block in page_blocks)
            section_text = " ".join(section.get("heading", "") for section in document.get("structure", {}).get("sections", []) if section.get("page") == page or page is None)
            page_text = " ".join(filter(None, [document.get("title", ""), block_text, section_text, " ".join(terminology_terms)]))
            tokens = tokenize(page_text)
            entries.append(
                {
                    "document_id": document["document_id"],
                    "page": page,
                    "source_type": document["source_type"],
                    "authority_level": document["authority_level"],
                    "version": document["version"],
                    "language": document["language"],
                    "title": document["title"],
                    "provenance": document["provenance"],
                    "acl": document["acl"],
                    "structure": document["structure"],
                    "terminology": document.get("terminology", {}),
                    "content_blocks": page_blocks,
                    "text": page_text,
                    "token_counts": Counter(tokens),
                    "tokens": set(tokens),
                }
            )
    return entries


def load_documents(path: str | Path) -> list[dict]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return payload["documents"]

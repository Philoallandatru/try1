from __future__ import annotations

from pathlib import Path
from typing import Iterable
import json

from services.retrieval.citations.assembler import assemble_citation, build_source_inspection
from services.retrieval.indexing.page_index import build_page_index, load_page_index
from services.retrieval.search.hybrid_search import search_page_index


def load_document_snapshot(path: str | Path) -> list[dict]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return payload["documents"]


def build_retrieval_index(documents: Iterable[dict]) -> list[dict]:
    return build_page_index(documents)


def load_page_index_artifact(path: str | Path) -> list[dict]:
    return load_page_index(path)


def search_index(
    entries: Iterable[dict],
    query: str,
    allowed_policies: set[str],
    top_k: int = 10,
) -> list[dict]:
    return search_page_index(entries, query, allowed_policies, top_k=top_k)


def search_documents(
    documents: Iterable[dict],
    query: str,
    allowed_policies: set[str],
    top_k: int = 10,
) -> list[dict]:
    return search_index(build_retrieval_index(documents), query, allowed_policies, top_k=top_k)


def citation_for_index(
    entries: Iterable[dict],
    query: str,
    allowed_policies: set[str],
    top_k: int = 10,
) -> dict:
    results = search_index(entries, query, allowed_policies, top_k=top_k)
    if not results:
        return {"citation": None, "inspection": None}
    return {
        "citation": assemble_citation(results[0]),
        "inspection": build_source_inspection(results[0]),
    }


def citation_for_documents(
    documents: Iterable[dict],
    query: str,
    allowed_policies: set[str],
    top_k: int = 10,
) -> dict:
    return citation_for_index(build_retrieval_index(documents), query, allowed_policies, top_k=top_k)

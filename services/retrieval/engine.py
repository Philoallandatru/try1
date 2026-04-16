from __future__ import annotations

from collections import Counter
from typing import Iterable, Protocol

from services.retrieval.citations.assembler import assemble_citation, build_source_inspection
from services.retrieval.search.hybrid_search import search_page_index


class RetrievalEngine(Protocol):
    name: str

    def search(
        self,
        entries: Iterable[dict],
        query: str,
        allowed_policies: set[str],
        top_k: int = 10,
    ) -> list[dict]: ...

    def citation(
        self,
        entries: Iterable[dict],
        query: str,
        allowed_policies: set[str],
        top_k: int = 10,
    ) -> dict: ...

    def comparison_payload(
        self,
        entries: Iterable[dict],
        query: str,
        allowed_policies: set[str],
        top_k: int = 10,
    ) -> dict: ...


class PageIndexEngine:
    name = "pageindex"

    def search(
        self,
        entries: Iterable[dict],
        query: str,
        allowed_policies: set[str],
        top_k: int = 10,
    ) -> list[dict]:
        return search_page_index(entries, query, allowed_policies, top_k=top_k)

    def citation(
        self,
        entries: Iterable[dict],
        query: str,
        allowed_policies: set[str],
        top_k: int = 10,
    ) -> dict:
        results = self.search(entries, query, allowed_policies, top_k=top_k)
        return self.citation_from_results(results)

    def comparison_payload(
        self,
        entries: Iterable[dict],
        query: str,
        allowed_policies: set[str],
        top_k: int = 10,
    ) -> dict:
        results = self.search(entries, query, allowed_policies, top_k=top_k)
        return self.comparison_from_results(results, query)

    def citation_from_results(self, results: list[dict]) -> dict:
        if not results:
            return {"citation": None, "inspection": None}
        return {
            "citation": assemble_citation(results[0]),
            "inspection": build_source_inspection(results[0]),
        }

    def comparison_from_results(self, results: list[dict], query: str) -> dict:
        top_result = results[0] if results else None
        return {
            "engine": self.name,
            "query": query,
            "result_count": len(results),
            "top_result_document": top_result["document_id"] if top_result else None,
            "manual_review": {
                "hit_quality": None,
                "readability": None,
                "citation_fidelity": None,
            },
        }


PAGE_INDEX_ENGINE = PageIndexEngine()


def _json_safe(value: object) -> object:
    if isinstance(value, set):
        return sorted(value)
    if isinstance(value, Counter):
        return dict(value)
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    return value


def build_shared_retrieval_bundle(
    *,
    engine: RetrievalEngine,
    entries: Iterable[dict],
    query: str,
    allowed_policies: set[str],
    top_k: int = 10,
) -> dict:
    entry_list = list(entries)
    results = engine.search(entry_list, query, allowed_policies, top_k=top_k)
    if hasattr(engine, "citation_from_results"):
        citation_payload = engine.citation_from_results(results)
    else:
        citation_payload = engine.citation(entry_list, query, allowed_policies, top_k=top_k)
    if hasattr(engine, "comparison_from_results"):
        comparison = engine.comparison_from_results(results, query)
    else:
        comparison = engine.comparison_payload(entry_list, query, allowed_policies, top_k=top_k)
    citations = [assemble_citation(result) for result in results]
    source_breakdown: dict[str, dict] = {}
    for result in results:
        source_type = result.get("source_type", "unknown")
        bucket = source_breakdown.setdefault(
            source_type,
            {"result_count": 0, "document_ids": []},
        )
        bucket["result_count"] += 1
        if result["document_id"] not in bucket["document_ids"]:
            bucket["document_ids"].append(result["document_id"])
    return {
        "engine": engine.name,
        "query": query,
        "allowed_policies": sorted(allowed_policies),
        "top_k": top_k,
        "results": _json_safe(results),
        "citation": citation_payload["citation"],
        "inspection": citation_payload["inspection"],
        "comparison": comparison,
        "citations": citations,
        "source_breakdown": source_breakdown,
    }

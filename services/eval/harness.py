from __future__ import annotations

from pathlib import Path
import json

from services.eval.metrics import citation_fidelity, ndcg_at_k, recall_at_k
from services.retrieval.citations.assembler import assemble_citation
from services.retrieval.indexing.page_index import build_page_index, load_documents
from services.retrieval.search.hybrid_search import search_page_index


DEFAULT_THRESHOLDS = {
    "recall@10": 0.90,
    "ndcg@10": 0.80,
    "citation_fidelity": 0.95,
}


def _dedupe_ranked_documents(ranked_entries: list[dict]) -> list[str]:
    seen = set()
    deduped = []
    for entry in ranked_entries:
        document_id = entry["document_id"]
        if document_id in seen:
            continue
        seen.add(document_id)
        deduped.append(document_id)
    return deduped


def load_gold_set(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def evaluate_dataset(
    corpus_path: str | Path,
    dataset_path: str | Path,
    allowed_policies: set[str],
    top_k: int = 10,
) -> dict:
    documents = load_documents(corpus_path)
    index = build_page_index(documents)
    dataset = load_gold_set(dataset_path)
    query_results = []

    for item in dataset["queries"]:
        ranked_entries = search_page_index(index, item["query"], allowed_policies, top_k=top_k)
        ranked_doc_ids = _dedupe_ranked_documents(ranked_entries)
        citation = assemble_citation(ranked_entries[0]) if ranked_entries else {}
        relevant = {item["expected"]["document"]}
        query_results.append(
            {
                "id": item["id"],
                "query": item["query"],
                "recall": recall_at_k(relevant, ranked_doc_ids, top_k),
                "ndcg": ndcg_at_k(relevant, ranked_doc_ids, top_k),
                "citation_fidelity": citation_fidelity(item["expected"], citation),
                "top_result": ranked_doc_ids[0] if ranked_doc_ids else None,
                "citation": citation,
            }
        )

    aggregate = {
        "recall@10": sum(item["recall"] for item in query_results) / len(query_results),
        "ndcg@10": sum(item["ndcg"] for item in query_results) / len(query_results),
        "citation_fidelity": sum(item["citation_fidelity"] for item in query_results) / len(query_results),
    }
    return {
        "thresholds": dataset.get("thresholds", DEFAULT_THRESHOLDS),
        "aggregate": aggregate,
        "queries": query_results,
    }


def thresholds_pass(report: dict) -> bool:
    thresholds = report["thresholds"]
    aggregate = report["aggregate"]
    return (
        aggregate["recall@10"] >= thresholds["recall@10"]
        and aggregate["ndcg@10"] >= thresholds["ndcg@10"]
        and aggregate["citation_fidelity"] >= thresholds["citation_fidelity"]
    )

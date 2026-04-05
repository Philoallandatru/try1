from __future__ import annotations

from pathlib import Path
import json

from services.eval.harness import evaluate_dataset
from services.retrieval.citations.assembler import assemble_citation, build_source_inspection
from services.retrieval.indexing.page_index import build_page_index, load_documents
from services.retrieval.search.hybrid_search import search_page_index


DEFAULT_POLICIES = {"team:ssd", "public"}


def build_portal_state(
    corpus_path: str | Path = "fixtures/retrieval/pageindex_corpus.json",
    dataset_path: str | Path = "eval/gold_queries.yaml",
    query: str = "nvme flush",
    allowed_policies: set[str] | None = None,
) -> dict:
    policies = allowed_policies or DEFAULT_POLICIES
    documents = load_documents(corpus_path)
    index = build_page_index(documents)
    search_results = search_page_index(index, query, policies, top_k=5)
    eval_report = evaluate_dataset(corpus_path, dataset_path, policies)

    source_counts: dict[str, int] = {}
    for document in documents:
        source_counts[document["source_type"]] = source_counts.get(document["source_type"], 0) + 1

    ingestion_status = [
        {
            "source_type": source_type,
            "status": "healthy",
            "document_count": count,
        }
        for source_type, count in sorted(source_counts.items())
    ]

    corpus_inventory = [
        {
            "document_id": document["document_id"],
            "title": document["title"],
            "source_type": document["source_type"],
            "authority_level": document["authority_level"],
            "version": document["version"],
            "language": document["language"],
        }
        for document in documents
    ]

    search_workspace = [
        {
            "document_id": result["document_id"],
            "title": result["title"],
            "authority_level": result["authority_level"],
            "scores": result["scores"],
            "citation": assemble_citation(result),
            "inspection": build_source_inspection(result),
        }
        for result in search_results
    ]

    citation_inspection = search_workspace[0]["inspection"] if search_workspace else {}
    return {
        "ingestion_status": ingestion_status,
        "corpus_inventory": corpus_inventory,
        "search_query": query,
        "search_workspace": search_workspace,
        "citation_inspection": citation_inspection,
        "evaluation_health": eval_report["aggregate"],
    }


def write_portal_state(output_path: str | Path = "apps/portal/portal_state.json") -> Path:
    path = Path(output_path)
    path.write_text(
        json.dumps(build_portal_state(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return path


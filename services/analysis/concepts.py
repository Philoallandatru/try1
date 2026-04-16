from __future__ import annotations

import re

from services.analysis.llm_backends import LLMBackend


def _slugify(text: str) -> str:
    """Convert a string into a URL-safe slug."""
    slug = text.lower().strip()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-") or "unnamed"


def _extract_cluster_keywords(cluster: dict, documents: list[dict]) -> list[str]:
    """Extract common keywords from a cluster's issues."""
    keywords: list[str] = []
    issue_ids = set(cluster.get("issue_ids", []))
    for document in documents:
        if document["document_id"] not in issue_ids:
            continue
        title = document.get("title", "")
        if title:
            words = [w.strip() for w in title.split() if len(w.strip()) > 2]
            keywords.extend(words[:5])
    # Return most common keywords (deduplicated)
    seen: set[str] = set()
    unique: list[str] = []
    for kw in keywords:
        lower = kw.lower()
        if lower not in seen:
            seen.add(lower)
            unique.append(kw)
    return unique[:10]


def _find_shared_issues(concepts: list[dict]) -> None:
    """Update cross-references between concepts that share issues."""
    concept_issue_map: dict[str, set[str]] = {}
    for concept in concepts:
        concept_issue_map[concept["concept_id"]] = set(concept.get("related_issue_ids", []))

    for concept in concepts:
        related: list[str] = []
        my_issues = concept_issue_map.get(concept["concept_id"], set())
        for other in concepts:
            if other["concept_id"] == concept["concept_id"]:
                continue
            other_issues = concept_issue_map.get(other["concept_id"], set())
            if my_issues & other_issues:
                related.append(other["concept_id"])
        concept["related_concepts"] = related


def extract_concepts(
    clusters: list[dict],
    documents: list[dict],
) -> list[dict]:
    """Extract concept knowledge skeletons from clustering results.

    Each meaningful cluster generates one concept with deterministic fields.
    """
    concepts: list[dict] = []
    for cluster in clusters:
        if cluster.get("issue_count", 0) == 0:
            continue
        cluster_key = cluster.get("key", "unknown")
        concept_id = _slugify(cluster_key)
        keywords = _extract_cluster_keywords(cluster, documents)
        concepts.append(
            {
                "concept_id": concept_id,
                "title": cluster.get("title", cluster_key),
                "slug": concept_id,
                "source_cluster_id": cluster["cluster_id"],
                "source_strategy": cluster.get("strategy", "unknown"),
                "related_issue_ids": cluster.get("issue_ids", []),
                "related_concepts": [],
                "keywords": keywords,
                "description": f"Concept derived from cluster '{cluster_key}' with {cluster['issue_count']} issue(s).",
                "evidence_summary": f"Based on {cluster['issue_count']} Jira issue(s) from the '{cluster.get('strategy', 'unknown')}' clustering strategy.",
            }
        )

    _find_shared_issues(concepts)
    return concepts


def enrich_concepts(
    concepts: list[dict],
    llm_backend: LLMBackend,
) -> list[dict]:
    """Enrich concept descriptions using an LLM backend.

    This is an optional enhancement pass. The concepts are usable without it.
    """
    for concept in concepts:
        prompt = "\n".join(
            [
                "You are a knowledge management assistant. Given the following concept extracted from Jira issues,",
                "write a concise 2-3 sentence description that explains what this concept represents,",
                "its significance, and how the related issues connect to it.",
                "",
                f"Concept title: {concept['title']}",
                f"Keywords: {', '.join(concept['keywords'][:8])}",
                f"Issue count: {len(concept['related_issue_ids'])}",
                f"Cluster strategy: {concept['source_strategy']}",
                f"Current description: {concept['description']}",
                "",
                "Write the improved description (2-3 sentences only):",
            ]
        )
        concept["description"] = llm_backend.generate(prompt).strip()
        concept["enriched"] = True
    return concepts


def build_concept_registry(concepts: list[dict]) -> dict:
    """Build a concept registry (index) from a list of concepts."""
    return {
        "concept_count": len(concepts),
        "concepts": [
            {
                "concept_id": concept["concept_id"],
                "title": concept["title"],
                "slug": concept["slug"],
                "issue_count": len(concept.get("related_issue_ids", [])),
                "related_concept_count": len(concept.get("related_concepts", [])),
                "keywords": concept.get("keywords", [])[:5],
            }
            for concept in concepts
        ],
    }


def update_concept_cross_references(concepts: list[dict]) -> list[dict]:
    """Rebuild cross-references between concepts."""
    _find_shared_issues(concepts)
    return concepts

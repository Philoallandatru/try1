from __future__ import annotations

from typing import Iterable

from services.retrieval.indexing.page_index import AUTHORITY_BOOST, tokenize


def _is_acl_allowed(policy: str, allowed_policies: set[str]) -> bool:
    if policy == "deny":
        return False
    if policy == "public":
        return True
    if policy == "inherit":
        return False
    return policy in allowed_policies


def _query_expansions(query: str) -> set[str]:
    terms = set(tokenize(query))
    joined = query.lower()
    if "刷新" in query:
        terms.update({"flush", "刷新"})
    if "命令" in query:
        terms.update({"command", "命令"})
    if "延迟" in query:
        terms.update({"latency", "延迟"})
    if "ftl" in joined:
        terms.update({"flash", "translation", "layer", "ftl"})
    if "flash translation layer" in joined:
        terms.update({"ftl", "flash", "translation", "layer"})
    return terms


def search_page_index(entries: Iterable[dict], query: str, allowed_policies: set[str], top_k: int = 10) -> list[dict]:
    query_terms = _query_expansions(query)
    filtered_entries = [
        entry for entry in entries
        if _is_acl_allowed(entry["acl"]["policy"], allowed_policies)
    ]

    scored = []
    for entry in filtered_entries:
        lexical_score = sum(entry["token_counts"].get(term, 0) for term in query_terms)
        semantic_score = len(query_terms & entry["tokens"])
        if lexical_score == 0 and semantic_score == 0:
            continue
        authority_score = AUTHORITY_BOOST.get(entry["authority_level"], 0.0)
        total = (lexical_score * 2.0) + semantic_score + authority_score
        scored.append(
            {
                **entry,
                "scores": {
                    "lexical": lexical_score,
                    "semantic": semantic_score,
                    "authority": authority_score,
                    "total": total,
                }
            }
        )

    scored.sort(
        key=lambda item: (
            item["scores"]["total"],
            item["scores"]["authority"],
            item["document_id"],
        ),
        reverse=True,
    )
    return scored[:top_k]

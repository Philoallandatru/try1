from __future__ import annotations

import math


def recall_at_k(relevant: set[str], ranked: list[str], k: int) -> float:
    if not relevant:
        return 1.0
    hits = len(relevant.intersection(ranked[:k]))
    return hits / len(relevant)


def ndcg_at_k(relevant: set[str], ranked: list[str], k: int) -> float:
    truncated = ranked[:k]
    dcg = 0.0
    for idx, doc_id in enumerate(truncated, start=1):
        rel = 1.0 if doc_id in relevant else 0.0
        if rel:
            dcg += rel / math.log2(idx + 1)

    ideal_hits = min(len(relevant), k)
    if ideal_hits == 0:
        return 1.0
    idcg = sum(1.0 / math.log2(idx + 1) for idx in range(1, ideal_hits + 1))
    return dcg / idcg if idcg else 0.0


def citation_fidelity(expected: dict, actual: dict) -> float:
    required_fields = ["document", "version", "page", "clause"]
    expected_fields = [field for field in required_fields if expected.get(field) is not None]
    if not expected_fields:
        return 1.0
    matches = 0
    for field in expected_fields:
        if actual.get(field) == expected.get(field):
            matches += 1
    return matches / len(expected_fields)


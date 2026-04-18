from __future__ import annotations

from collections import Counter

from services.connectors.jira.issue_type_profiles import route_jira_issue_type


CLUSTERING_STRATEGIES = {
    "by_issue_family",
    "by_component",
    "by_label",
    "by_tag",
    "composite",
}


def _extract_metadata(document: dict) -> dict:
    """Extract clustering-relevant metadata from a Jira document."""
    issue_fields = document.get("metadata", {}).get("issue_fields", {})
    issue_type_raw = issue_fields.get("Issue Type") or document.get("metadata", {}).get("issue_type_raw")
    routing = route_jira_issue_type(issue_type_raw)
    components = issue_fields.get("Component/s") or []
    if isinstance(components, str):
        components = [c.strip() for c in components.split(",") if c.strip()]
    labels = issue_fields.get("Labels") or []
    if isinstance(labels, str):
        labels = [l.strip() for l in labels.split(",") if l.strip()]
    tags = issue_fields.get("Tag") or issue_fields.get("Tags") or []
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]
    return {
        "document_id": document["document_id"],
        "title": document.get("title", document["document_id"]),
        "issue_type_raw": routing["issue_type_raw"],
        "issue_family": routing["issue_family"],
        "issue_route": routing["issue_route"],
        "components": components,
        "labels": labels,
        "tags": tags,
        "priority": str(issue_fields.get("Priority") or "unknown"),
        "status": str(issue_fields.get("Status") or "unknown"),
    }


def _cluster_by_field(documents: list[dict], field: str) -> dict[str, list[dict]]:
    """Group documents by a single metadata field value."""
    groups: dict[str, list[dict]] = {}
    for document in documents:
        meta = _extract_metadata(document)
        values = meta.get(field)
        if isinstance(values, list):
            if not values:
                values = ["uncategorized"]
            for value in values:
                groups.setdefault(value, []).append(document)
        else:
            key = str(values or "uncategorized")
            groups.setdefault(key, []).append(document)
    return groups


def _cluster_composite(documents: list[dict]) -> dict[str, list[dict]]:
    """Cluster by composite key: issue_family + first component."""
    groups: dict[str, list[dict]] = {}
    for document in documents:
        meta = _extract_metadata(document)
        family = meta["issue_family"]
        component = meta["components"][0] if meta["components"] else "general"
        key = f"{family}/{component}"
        groups.setdefault(key, []).append(document)
    return groups


def _compute_cluster_stats(documents: list[dict]) -> dict:
    """Compute summary statistics for a cluster of documents."""
    priorities: list[str] = []
    statuses: list[str] = []
    for document in documents:
        issue_fields = document.get("metadata", {}).get("issue_fields", {})
        priorities.append(str(issue_fields.get("Priority") or "unknown"))
        statuses.append(str(issue_fields.get("Status") or "unknown"))
    return {
        "issue_count": len(documents),
        "priority_distribution": dict(Counter(priorities)),
        "status_distribution": dict(Counter(statuses)),
    }


def _make_cluster_id(strategy: str, key: str) -> str:
    """Generate a stable cluster ID from strategy and key."""
    slug = key.lower().replace("/", "-").replace(" ", "-").replace("_", "-")
    return f"{strategy}--{slug}"


def cluster_jira_issues(
    documents: list[dict],
    *,
    strategy: str = "composite",
) -> dict:
    """Cluster Jira documents by the given strategy.

    Returns a dict with 'strategy', 'clusters' list, and 'cluster_count'.
    Each cluster has: cluster_id, strategy, key, title, issue_ids, summary_stats.
    """
    if strategy not in CLUSTERING_STRATEGIES:
        raise ValueError(f"Unsupported clustering strategy: {strategy}. Must be one of {sorted(CLUSTERING_STRATEGIES)}")

    if strategy == "by_issue_family":
        groups = _cluster_by_field(documents, "issue_family")
    elif strategy == "by_component":
        groups = _cluster_by_field(documents, "components")
    elif strategy == "by_label":
        groups = _cluster_by_field(documents, "labels")
    elif strategy == "by_tag":
        groups = _cluster_by_field(documents, "tags")
    elif strategy == "composite":
        groups = _cluster_composite(documents)
    else:
        groups = _cluster_by_field(documents, "issue_family")

    clusters: list[dict] = []
    for key in sorted(groups):
        group_documents = groups[key]
        cluster_id = _make_cluster_id(strategy, key)
        clusters.append(
            {
                "cluster_id": cluster_id,
                "strategy": strategy,
                "key": key,
                "title": key.replace("/", " / ").replace("_", " ").title(),
                "issue_ids": [doc["document_id"] for doc in group_documents],
                "issue_count": len(group_documents),
                "summary_stats": _compute_cluster_stats(group_documents),
            }
        )

    return {
        "strategy": strategy,
        "cluster_count": len(clusters),
        "total_issues": len(documents),
        "clusters": clusters,
    }

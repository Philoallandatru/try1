"""Cross-reference analysis API for finding related issues.

Analyzes relationships between issues based on shared citations and content similarity.
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any


class CrossReferenceAPI:
    """Business logic for cross-reference analysis."""

    def __init__(self, workspace_root: Path):
        self.workspace_root = Path(workspace_root)
        self.knowledge_root = self.workspace_root / "knowledge"

    def find_related_issues(
        self,
        *,
        workspace_dir: str,
        issue_id: str,
        min_shared_citations: int = 2,
        limit: int = 10,
    ) -> dict[str, Any]:
        """Find issues related to the given issue.

        Args:
            workspace_dir: Path to workspace directory
            issue_id: Issue ID to find relations for
            min_shared_citations: Minimum number of shared citations
            limit: Maximum number of related issues to return

        Returns:
            Related issues with similarity scores
        """
        workspace_path = Path(workspace_dir)
        analyses_dir = workspace_path / "knowledge" / "analyses"

        if not analyses_dir.exists():
            return {
                "issue_id": issue_id,
                "related_issues": [],
                "total_found": 0,
            }

        # Load target issue
        target_file = analyses_dir / f"{issue_id}.json"
        if not target_file.exists():
            return {
                "issue_id": issue_id,
                "related_issues": [],
                "total_found": 0,
                "error": "Issue not found",
            }

        with open(target_file, encoding="utf-8") as f:
            target_analysis = json.load(f)

        target_citations = set(target_analysis.get("citations", []))

        # Find related issues
        related: list[dict[str, Any]] = []

        for analysis_file in analyses_dir.glob("*.json"):
            if analysis_file.stem == issue_id:
                continue

            try:
                with open(analysis_file, encoding="utf-8") as f:
                    analysis = json.load(f)

                other_issue_id = analysis.get("issue_id", "")
                other_citations = set(analysis.get("citations", []))

                # Calculate shared citations
                shared = target_citations & other_citations
                shared_count = len(shared)

                if shared_count >= min_shared_citations:
                    # Calculate similarity score (Jaccard similarity)
                    union = target_citations | other_citations
                    similarity = len(shared) / len(union) if union else 0

                    related.append({
                        "issue_id": other_issue_id,
                        "shared_citations": shared_count,
                        "similarity_score": round(similarity, 3),
                        "shared_citation_ids": sorted(list(shared)),
                        "summary": analysis.get("summary", ""),
                    })

            except (json.JSONDecodeError, KeyError):
                continue

        # Sort by similarity score (descending) and limit
        related.sort(key=lambda x: x["similarity_score"], reverse=True)
        limited_related = related[:limit]

        return {
            "issue_id": issue_id,
            "total_citations": len(target_citations),
            "related_issues": limited_related,
            "total_found": len(related),
        }

    def get_citation_network(
        self,
        *,
        workspace_dir: str,
        min_connections: int = 2,
    ) -> dict[str, Any]:
        """Get the citation network showing issue relationships.

        Args:
            workspace_dir: Path to workspace directory
            min_connections: Minimum shared citations to include edge

        Returns:
            Network graph data with nodes and edges
        """
        workspace_path = Path(workspace_dir)
        analyses_dir = workspace_path / "knowledge" / "analyses"

        if not analyses_dir.exists():
            return {
                "nodes": [],
                "edges": [],
                "total_issues": 0,
            }

        # Load all analyses
        issues: dict[str, set[str]] = {}

        for analysis_file in analyses_dir.glob("*.json"):
            try:
                with open(analysis_file, encoding="utf-8") as f:
                    analysis = json.load(f)

                issue_id = analysis.get("issue_id", "")
                citations = set(analysis.get("citations", []))
                issues[issue_id] = citations

            except (json.JSONDecodeError, KeyError):
                continue

        # Build nodes
        nodes = [
            {
                "id": issue_id,
                "citation_count": len(citations),
            }
            for issue_id, citations in issues.items()
        ]

        # Build edges (connections between issues)
        edges: list[dict[str, Any]] = []
        issue_ids = list(issues.keys())

        for i, issue_id_1 in enumerate(issue_ids):
            for issue_id_2 in issue_ids[i + 1:]:
                shared = issues[issue_id_1] & issues[issue_id_2]
                shared_count = len(shared)

                if shared_count >= min_connections:
                    # Calculate edge weight (similarity)
                    union = issues[issue_id_1] | issues[issue_id_2]
                    weight = len(shared) / len(union) if union else 0

                    edges.append({
                        "source": issue_id_1,
                        "target": issue_id_2,
                        "shared_citations": shared_count,
                        "weight": round(weight, 3),
                    })

        return {
            "nodes": nodes,
            "edges": edges,
            "total_issues": len(nodes),
            "total_connections": len(edges),
        }

    def get_most_cited_documents(
        self,
        *,
        workspace_dir: str,
        limit: int = 20,
    ) -> dict[str, Any]:
        """Get the most frequently cited documents across all analyses.

        Args:
            workspace_dir: Path to workspace directory
            limit: Maximum number of documents to return

        Returns:
            List of most cited documents with citation counts
        """
        workspace_path = Path(workspace_dir)
        analyses_dir = workspace_path / "knowledge" / "analyses"

        if not analyses_dir.exists():
            return {
                "documents": [],
                "total_documents": 0,
            }

        # Count citations
        citation_counts: dict[str, int] = defaultdict(int)
        citing_issues: dict[str, list[str]] = defaultdict(list)

        for analysis_file in analyses_dir.glob("*.json"):
            try:
                with open(analysis_file, encoding="utf-8") as f:
                    analysis = json.load(f)

                issue_id = analysis.get("issue_id", "")
                citations = analysis.get("citations", [])

                for citation in citations:
                    citation_counts[citation] += 1
                    citing_issues[citation].append(issue_id)

            except (json.JSONDecodeError, KeyError):
                continue

        # Sort by citation count
        sorted_docs = sorted(
            citation_counts.items(),
            key=lambda x: x[1],
            reverse=True,
        )[:limit]

        documents = [
            {
                "document_id": doc_id,
                "citation_count": count,
                "cited_by": citing_issues[doc_id],
            }
            for doc_id, count in sorted_docs
        ]

        return {
            "documents": documents,
            "total_documents": len(citation_counts),
        }

    def get_issue_clusters(
        self,
        *,
        workspace_dir: str,
        min_cluster_size: int = 2,
    ) -> dict[str, Any]:
        """Find clusters of related issues based on shared citations.

        Args:
            workspace_dir: Path to workspace directory
            min_cluster_size: Minimum number of issues in a cluster

        Returns:
            List of issue clusters
        """
        workspace_path = Path(workspace_dir)
        analyses_dir = workspace_path / "knowledge" / "analyses"

        if not analyses_dir.exists():
            return {
                "clusters": [],
                "total_clusters": 0,
            }

        # Load all analyses
        issues: dict[str, set[str]] = {}

        for analysis_file in analyses_dir.glob("*.json"):
            try:
                with open(analysis_file, encoding="utf-8") as f:
                    analysis = json.load(f)

                issue_id = analysis.get("issue_id", "")
                citations = set(analysis.get("citations", []))
                issues[issue_id] = citations

            except (json.JSONDecodeError, KeyError):
                continue

        # Simple clustering: group issues with high similarity
        clusters: list[set[str]] = []
        processed = set()

        for issue_id, citations in issues.items():
            if issue_id in processed:
                continue

            # Start a new cluster
            cluster = {issue_id}
            processed.add(issue_id)

            # Find similar issues
            for other_id, other_citations in issues.items():
                if other_id in processed:
                    continue

                # Calculate similarity
                shared = citations & other_citations
                union = citations | other_citations
                similarity = len(shared) / len(union) if union else 0

                # Add to cluster if similar enough (threshold: 0.3)
                if similarity >= 0.3:
                    cluster.add(other_id)
                    processed.add(other_id)

            # Only keep clusters meeting minimum size
            if len(cluster) >= min_cluster_size:
                clusters.append(cluster)

        # Format clusters
        formatted_clusters = [
            {
                "cluster_id": i,
                "issues": sorted(list(cluster)),
                "size": len(cluster),
            }
            for i, cluster in enumerate(clusters)
        ]

        return {
            "clusters": formatted_clusters,
            "total_clusters": len(formatted_clusters),
        }

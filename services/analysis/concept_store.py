from __future__ import annotations

from pathlib import Path
import json


def _write_json(path: Path, payload: dict | list) -> str:
    """Write a JSON file with proper encoding."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return str(path)


def save_concepts(knowledge_dir: str | Path, concepts: list[dict]) -> dict:
    """Save concepts to the knowledge directory.

    File structure:
        knowledge_dir/
            concepts.json          - Concept registry
            concepts/
                {concept-slug}.json - Individual concept details
    """
    root = Path(knowledge_dir)
    concepts_dir = root / "concepts"
    concepts_dir.mkdir(parents=True, exist_ok=True)

    registry = {
        "concept_count": len(concepts),
        "concepts": [
            {
                "concept_id": c["concept_id"],
                "title": c["title"],
                "slug": c["slug"],
            }
            for c in concepts
        ],
    }
    registry_path = _write_json(root / "concepts.json", registry)

    concept_paths: list[str] = []
    for concept in concepts:
        concept_path = _write_json(concepts_dir / f"{concept['slug']}.json", concept)
        concept_paths.append(concept_path)

    return {
        "registry_path": registry_path,
        "concept_paths": concept_paths,
        "concept_count": len(concepts),
    }


def load_concepts(knowledge_dir: str | Path) -> list[dict]:
    """Load all concepts from the knowledge directory."""
    root = Path(knowledge_dir)
    concepts_dir = root / "concepts"
    if not concepts_dir.exists():
        return []
    concepts: list[dict] = []
    for concept_path in sorted(concepts_dir.glob("*.json")):
        concept = json.loads(concept_path.read_text(encoding="utf-8"))
        concepts.append(concept)
    return concepts


def save_clusters(knowledge_dir: str | Path, cluster_payload: dict) -> str:
    """Save cluster results to the knowledge directory."""
    root = Path(knowledge_dir)
    return _write_json(root / "clusters.json", cluster_payload)


def load_clusters(knowledge_dir: str | Path) -> dict:
    """Load cluster results from the knowledge directory."""
    root = Path(knowledge_dir)
    clusters_path = root / "clusters.json"
    if not clusters_path.exists():
        return {"clusters": [], "cluster_count": 0}
    return json.loads(clusters_path.read_text(encoding="utf-8"))

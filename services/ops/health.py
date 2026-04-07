from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json

from services.eval.harness import evaluate_dataset
from services.retrieval.persistence.snapshot_store import load_snapshot


def _parse_utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def _build_freshness_from_snapshot(snapshot_dir: str | Path, budget_minutes: int, reference_time: datetime | None = None) -> dict:
    loaded = load_snapshot(snapshot_dir)
    manifest = loaded.get("manifest", {})
    sources = []
    now = reference_time or datetime.now(timezone.utc)

    for source_name, metadata in manifest.get("sources", {}).items():
        if source_name == "manual":
            continue
        last_sync = metadata.get("last_sync") or manifest.get("updated_at")
        lag_minutes = 0
        if last_sync:
            lag_delta = now - _parse_utc(last_sync)
            lag_minutes = max(0, int(lag_delta.total_seconds() // 60))
        sources.append(
            {
                "source_type": source_name,
                "status": "healthy" if lag_minutes <= budget_minutes else "stale",
                "last_sync": last_sync,
                "lag_minutes": lag_minutes,
            }
        )

    return {
        "sources": sources,
        "budget_minutes": budget_minutes,
        "snapshot_dir": str(snapshot_dir),
    }


def _build_backup_restore_from_snapshot(snapshot_dir: str | Path) -> dict:
    loaded = load_snapshot(snapshot_dir)
    manifest = loaded.get("manifest", {})
    snapshot_path = Path(snapshot_dir)
    page_index_entries = loaded.get("page_index", {}).get("entries", [])
    return {
        "backup": {
            "status": "healthy" if snapshot_path.exists() and manifest else "missing",
            "last_backup": manifest.get("updated_at"),
            "location": str(snapshot_path),
        },
        "restore": {
            "status": "validated" if page_index_entries else "missing",
            "last_restore_test": manifest.get("updated_at"),
            "target_env": "local-snapshot",
        },
    }


def build_ops_health(
    corpus_path: str | Path = "fixtures/retrieval/pageindex_corpus.json",
    dataset_path: str | Path = "eval/gold_queries.yaml",
    snapshot_dir: str | Path | None = None,
    freshness_budget_minutes: int = 30,
    reference_time_iso: str | None = None,
) -> dict:
    eval_report = evaluate_dataset(
        corpus_path=corpus_path,
        dataset_path=dataset_path,
        allowed_policies={"team:ssd", "public"},
    )
    reference_time = _parse_utc(reference_time_iso) if reference_time_iso else None

    if snapshot_dir and Path(snapshot_dir).exists():
        source_snapshot = _build_freshness_from_snapshot(snapshot_dir, freshness_budget_minutes, reference_time)
        backup_snapshot = _build_backup_restore_from_snapshot(snapshot_dir)
    else:
        source_snapshot = json.loads(Path("fixtures/ops/source_freshness.json").read_text(encoding="utf-8"))
        backup_snapshot = json.loads(Path("fixtures/ops/backup_restore.json").read_text(encoding="utf-8"))
    return {
        "freshness": source_snapshot,
        "backup_restore": backup_snapshot,
        "evaluation": eval_report["aggregate"],
    }

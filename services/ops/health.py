from __future__ import annotations

from pathlib import Path
import json

from services.eval.harness import evaluate_dataset


def build_ops_health(
    corpus_path: str | Path = "fixtures/retrieval/pageindex_corpus.json",
    dataset_path: str | Path = "eval/gold_queries.yaml",
) -> dict:
    eval_report = evaluate_dataset(
        corpus_path=corpus_path,
        dataset_path=dataset_path,
        allowed_policies={"team:ssd", "public"},
    )
    source_snapshot = json.loads(Path("fixtures/ops/source_freshness.json").read_text(encoding="utf-8"))
    backup_snapshot = json.loads(Path("fixtures/ops/backup_restore.json").read_text(encoding="utf-8"))
    return {
        "freshness": source_snapshot,
        "backup_restore": backup_snapshot,
        "evaluation": eval_report["aggregate"],
    }


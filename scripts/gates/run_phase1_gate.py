from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.portal.portal_state import build_portal_state
from services.eval.harness import evaluate_dataset, thresholds_pass
from services.ops.health import build_ops_health


def evaluate_phase1_gate(
    dataset_path: str | Path = "eval/gold_queries.yaml",
    corpus_path: str | Path = "fixtures/retrieval/pageindex_corpus.json",
    allowed_policies: set[str] | None = None,
) -> dict:
    policies = allowed_policies or {"team:ssd", "public"}
    eval_report = evaluate_dataset(corpus_path, dataset_path, policies)
    ops_report = build_ops_health(corpus_path, dataset_path)
    portal_state = build_portal_state(corpus_path, dataset_path, allowed_policies=policies)

    freshness_budget = ops_report["freshness"]["budget_minutes"]
    freshness_ok = all(
        source["status"] == "healthy" and source["lag_minutes"] <= freshness_budget
        for source in ops_report["freshness"]["sources"]
    )
    backup_ok = (
        ops_report["backup_restore"]["backup"]["status"] == "healthy"
        and ops_report["backup_restore"]["restore"]["status"] == "validated"
    )
    portal_ok = len(portal_state["search_workspace"]) > 0 and bool(portal_state["citation_inspection"])
    eval_ok = thresholds_pass(eval_report)

    passed = eval_ok and freshness_ok and backup_ok and portal_ok
    return {
        "passed": passed,
        "checks": {
            "eval": eval_ok,
            "freshness": freshness_ok,
            "backup_restore": backup_ok,
            "portal": portal_ok,
        },
        "eval": eval_report["aggregate"],
        "ops": ops_report,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="eval/gold_queries.yaml")
    parser.add_argument("--corpus", default="fixtures/retrieval/pageindex_corpus.json")
    parser.add_argument("--policies", nargs="*", default=["team:ssd", "public"])
    args = parser.parse_args()

    report = evaluate_phase1_gate(args.dataset, args.corpus, set(args.policies))
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())


from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.eval.harness import evaluate_dataset, thresholds_pass


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True)
    parser.add_argument(
        "--corpus",
        default="fixtures/retrieval/pageindex_corpus.json",
    )
    parser.add_argument(
        "--policies",
        nargs="*",
        default=["team:ssd", "public"],
    )
    args = parser.parse_args()

    report = evaluate_dataset(
        corpus_path=Path(args.corpus),
        dataset_path=Path(args.dataset),
        allowed_policies=set(args.policies),
        top_k=10,
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if thresholds_pass(report) else 1


if __name__ == "__main__":
    raise SystemExit(main())

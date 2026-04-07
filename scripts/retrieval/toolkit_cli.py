from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.retrieval.toolkit import build_retrieval_index, citation_for_documents, load_document_snapshot, search_documents


def _json_default(value: object) -> object:
    if isinstance(value, set):
        return sorted(value)
    if isinstance(value, Counter):
        return dict(value)
    raise TypeError(f"Object of type {value.__class__.__name__} is not JSON serializable")


def _print_json(payload: dict | list) -> int:
    print(json.dumps(payload, indent=2, ensure_ascii=False, default=_json_default))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Skill-ready grounded retrieval toolkit CLI.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    index_parser = subparsers.add_parser("index")
    index_parser.add_argument("--corpus", required=True)

    search_parser = subparsers.add_parser("search")
    search_parser.add_argument("query")
    search_parser.add_argument("--corpus", required=True)
    search_parser.add_argument("--policies", nargs="*", default=["team:ssd", "public"])

    citation_parser = subparsers.add_parser("citation")
    citation_parser.add_argument("query")
    citation_parser.add_argument("--corpus", required=True)
    citation_parser.add_argument("--policies", nargs="*", default=["team:ssd", "public"])

    args = parser.parse_args()
    documents = load_document_snapshot(args.corpus)

    if args.command == "index":
        return _print_json({"entries": build_retrieval_index(documents)})
    if args.command == "search":
        return _print_json(search_documents(documents, args.query, set(args.policies)))
    if args.command == "citation":
        return _print_json(citation_for_documents(documents, args.query, set(args.policies)))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

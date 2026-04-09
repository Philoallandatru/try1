from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.retrieval.toolkit import (
    build_retrieval_index,
    citation_for_documents,
    citation_for_index,
    load_document_snapshot,
    load_page_index_artifact,
    search_documents,
    search_index,
)
from services.retrieval.persistence.snapshot_store import snapshot_paths


def _json_default(value: object) -> object:
    if isinstance(value, set):
        return sorted(value)
    if isinstance(value, Counter):
        return dict(value)
    raise TypeError(f"Object of type {value.__class__.__name__} is not JSON serializable")


def _print_json(payload: dict | list) -> int:
    print(json.dumps(payload, indent=2, ensure_ascii=False, default=_json_default))
    return 0


def _write_json(path: str, payload: dict | list) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, default=_json_default),
        encoding="utf-8",
    )


def _validate_retrieval_source(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    selected = sum(bool(value) for value in (args.corpus, args.page_index, args.snapshot_dir))
    if selected != 1:
        parser.error("Provide exactly one of --corpus, --page-index, or --snapshot-dir")


def _load_snapshot_page_index(snapshot_dir: str | Path) -> list[dict]:
    return load_page_index_artifact(snapshot_paths(snapshot_dir)["page_index"])


def main() -> int:
    parser = argparse.ArgumentParser(description="Skill-ready grounded retrieval toolkit CLI.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    index_parser = subparsers.add_parser("index")
    index_parser.add_argument("--corpus", required=True)
    index_parser.add_argument("--output-page-index")

    search_parser = subparsers.add_parser("search")
    search_parser.add_argument("query")
    search_parser.add_argument("--corpus")
    search_parser.add_argument("--page-index")
    search_parser.add_argument("--snapshot-dir")
    search_parser.add_argument("--policies", nargs="*", default=["team:ssd", "public"])

    citation_parser = subparsers.add_parser("citation")
    citation_parser.add_argument("query")
    citation_parser.add_argument("--corpus")
    citation_parser.add_argument("--page-index")
    citation_parser.add_argument("--snapshot-dir")
    citation_parser.add_argument("--policies", nargs="*", default=["team:ssd", "public"])

    args = parser.parse_args()

    if args.command == "index":
        documents = load_document_snapshot(args.corpus)
        payload = {"entries": build_retrieval_index(documents)}
        if args.output_page_index:
            _write_json(args.output_page_index, payload)
        return _print_json(payload)
    if args.command == "search":
        _validate_retrieval_source(parser, args)
        if args.page_index:
            return _print_json(search_index(load_page_index_artifact(args.page_index), args.query, set(args.policies)))
        if args.snapshot_dir:
            return _print_json(search_index(_load_snapshot_page_index(args.snapshot_dir), args.query, set(args.policies)))
        return _print_json(search_documents(load_document_snapshot(args.corpus), args.query, set(args.policies)))
    if args.command == "citation":
        _validate_retrieval_source(parser, args)
        if args.page_index:
            return _print_json(citation_for_index(load_page_index_artifact(args.page_index), args.query, set(args.policies)))
        if args.snapshot_dir:
            return _print_json(citation_for_index(_load_snapshot_page_index(args.snapshot_dir), args.query, set(args.policies)))
        return _print_json(citation_for_documents(load_document_snapshot(args.corpus), args.query, set(args.policies)))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

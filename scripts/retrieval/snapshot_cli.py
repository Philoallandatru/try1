from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.connectors.confluence.connector import load_confluence_sync
from services.connectors.jira.connector import load_jira_sync
from services.retrieval.persistence.snapshot_store import create_snapshot, load_snapshot, refresh_snapshot
from services.retrieval.toolkit import load_document_snapshot


def _print_json(payload: dict | list) -> int:
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def _load_sync_payload(path: str | Path) -> dict:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if "documents" in payload:
        return payload
    if "issues" in payload:
        return load_jira_sync(path)
    if "pages" in payload:
        return load_confluence_sync(path)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Snapshot persistence and incremental refresh CLI.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create_parser = subparsers.add_parser("create")
    create_parser.add_argument("--snapshot-dir", required=True)
    create_parser.add_argument("--corpus", required=True)
    create_parser.add_argument("--source-name", default="manual")
    create_parser.add_argument("--cursor")
    create_parser.add_argument("--sync-type", default="full")

    show_parser = subparsers.add_parser("show")
    show_parser.add_argument("--snapshot-dir", required=True)

    refresh_parser = subparsers.add_parser("refresh")
    refresh_parser.add_argument("--snapshot-dir", required=True)
    refresh_parser.add_argument("--sync-payload", required=True)
    refresh_parser.add_argument("--source-name", required=True)

    args = parser.parse_args()

    if args.command == "create":
        return _print_json(
            create_snapshot(
                args.snapshot_dir,
                documents=load_document_snapshot(args.corpus),
                source_name=args.source_name,
                source_cursor=args.cursor,
                sync_type=args.sync_type,
            )
        )
    if args.command == "show":
        return _print_json(load_snapshot(args.snapshot_dir))
    if args.command == "refresh":
        return _print_json(
            refresh_snapshot(
                args.snapshot_dir,
                sync_payload=_load_sync_payload(args.sync_payload),
                source_name=args.source_name,
            )
        )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

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
from services.ingest.adapters.markdown.adapter import parse_markdown
from services.ingest.adapters.office.adapter import parse_docx, parse_pptx, parse_xlsx
from services.ingest.adapters.pdf.adapter import extract_pdf_structure


def _print_json(payload: dict | list) -> int:
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Skill-ready offline document normalizer CLI.")
    parser.add_argument(
        "kind",
        choices=["markdown", "docx", "xlsx", "pptx", "pdf", "jira-sync", "confluence-sync"],
    )
    parser.add_argument("path")
    args = parser.parse_args()

    if args.kind == "markdown":
        return _print_json(parse_markdown(args.path))
    if args.kind == "docx":
        return _print_json(parse_docx(args.path))
    if args.kind == "xlsx":
        return _print_json(parse_xlsx(args.path))
    if args.kind == "pptx":
        return _print_json(parse_pptx(args.path))
    if args.kind == "pdf":
        return _print_json(extract_pdf_structure(args.path))
    if args.kind == "jira-sync":
        return _print_json(load_jira_sync(args.path))
    if args.kind == "confluence-sync":
        return _print_json(load_confluence_sync(args.path))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

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
from services.ingest.markdown_export import documents_to_markdown, ensure_document_markdown
from services.retrieval.indexing.page_index import build_page_index


def _print_json(payload: dict | list) -> int:
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def _documents_from_payload(payload: dict) -> list[dict]:
    if "documents" in payload:
        return [ensure_document_markdown(document) for document in payload["documents"]]
    return [ensure_document_markdown(payload)]


def _write_outputs(payload: dict, *, output_md: str | None, output_page_index: str | None) -> dict:
    documents = _documents_from_payload(payload)
    if "documents" in payload:
        payload["documents"] = documents
    else:
        payload = documents[0]

    if output_md:
        output_path = Path(output_md)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(documents_to_markdown(documents), encoding="utf-8")
        payload["output_md"] = str(output_path)

    if output_page_index:
        output_path = Path(output_page_index)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(build_page_index(documents), indent=2, ensure_ascii=False, default=_json_default),
            encoding="utf-8",
        )
        payload["output_page_index"] = str(output_path)

    return payload


def _json_default(value: object) -> object:
    if isinstance(value, set):
        return sorted(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def main() -> int:
    parser = argparse.ArgumentParser(description="Skill-ready offline document normalizer CLI.")
    parser.add_argument(
        "kind",
        choices=["markdown", "docx", "xlsx", "pptx", "pdf", "jira-sync", "confluence-sync"],
    )
    parser.add_argument("path")
    parser.add_argument("--output-md")
    parser.add_argument("--output-page-index")
    args = parser.parse_args()

    if args.kind == "markdown":
        return _print_json(_write_outputs(parse_markdown(args.path), output_md=args.output_md, output_page_index=args.output_page_index))
    if args.kind == "docx":
        return _print_json(_write_outputs(parse_docx(args.path), output_md=args.output_md, output_page_index=args.output_page_index))
    if args.kind == "xlsx":
        return _print_json(_write_outputs(parse_xlsx(args.path), output_md=args.output_md, output_page_index=args.output_page_index))
    if args.kind == "pptx":
        return _print_json(_write_outputs(parse_pptx(args.path), output_md=args.output_md, output_page_index=args.output_page_index))
    if args.kind == "pdf":
        return _print_json(_write_outputs(extract_pdf_structure(args.path), output_md=args.output_md, output_page_index=args.output_page_index))
    if args.kind == "jira-sync":
        return _print_json(_write_outputs(load_jira_sync(args.path), output_md=args.output_md, output_page_index=args.output_page_index))
    if args.kind == "confluence-sync":
        return _print_json(_write_outputs(load_confluence_sync(args.path), output_md=args.output_md, output_page_index=args.output_page_index))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

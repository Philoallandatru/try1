from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.portal.portal_state import build_portal_state
from scripts.gates.check_adr_contract import main as adr_check_main
from scripts.gates.check_module_contracts import main as module_check_main
from scripts.gates.check_repo_shape import main as repo_check_main
from scripts.gates.run_phase1_gate import evaluate_phase1_gate
from services.connectors.confluence.connector import load_confluence_sync
from services.connectors.jira.connector import load_jira_sync
from services.eval.harness import evaluate_dataset
from services.ingest.adapters.markdown.adapter import parse_markdown
from services.ingest.adapters.office.adapter import parse_docx, parse_pptx, parse_xlsx
from services.ingest.adapters.pdf.adapter import extract_pdf_structure
from services.ops.health import build_ops_health
from services.retrieval.citations.assembler import assemble_citation, build_source_inspection
from services.retrieval.indexing.page_index import build_page_index, load_documents
from services.retrieval.search.hybrid_search import search_page_index


def _print_json(payload: dict | list) -> int:
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def _load_index(corpus: str | Path) -> list[dict]:
    return build_page_index(load_documents(corpus))


def main() -> int:
    parser = argparse.ArgumentParser(description="Unified CLI for SSD knowledge platform foundation utilities.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("adr-check")
    subparsers.add_parser("repo-check")
    subparsers.add_parser("module-check")

    eval_parser = subparsers.add_parser("eval")
    eval_parser.add_argument("--dataset", default="eval/gold_queries.yaml")
    eval_parser.add_argument("--corpus", default="fixtures/retrieval/pageindex_corpus.json")

    gate_parser = subparsers.add_parser("gate")
    gate_parser.add_argument("--dataset", default="eval/gold_queries.yaml")
    gate_parser.add_argument("--corpus", default="fixtures/retrieval/pageindex_corpus.json")

    portal_parser = subparsers.add_parser("portal-state")
    portal_parser.add_argument("--query", default="nvme flush")

    subparsers.add_parser("ops-health")

    ingest_parser = subparsers.add_parser("ingest")
    ingest_parser.add_argument("kind", choices=["markdown", "docx", "xlsx", "pptx", "pdf"])
    ingest_parser.add_argument("path")

    connector_parser = subparsers.add_parser("connector")
    connector_parser.add_argument("kind", choices=["jira", "confluence"])
    connector_parser.add_argument("path")

    search_parser = subparsers.add_parser("search")
    search_parser.add_argument("query")
    search_parser.add_argument("--corpus", default="fixtures/retrieval/pageindex_corpus.json")
    search_parser.add_argument("--policies", nargs="*", default=["team:ssd", "public"])

    citation_parser = subparsers.add_parser("citation")
    citation_parser.add_argument("query")
    citation_parser.add_argument("--corpus", default="fixtures/retrieval/pageindex_corpus.json")
    citation_parser.add_argument("--policies", nargs="*", default=["team:ssd", "public"])

    args = parser.parse_args()

    if args.command == "adr-check":
        return adr_check_main()
    if args.command == "repo-check":
        return repo_check_main()
    if args.command == "module-check":
        return module_check_main()
    if args.command == "eval":
        return _print_json(evaluate_dataset(args.corpus, args.dataset, {"team:ssd", "public"}))
    if args.command == "gate":
        return _print_json(evaluate_phase1_gate(args.dataset, args.corpus, {"team:ssd", "public"}))
    if args.command == "portal-state":
        return _print_json(build_portal_state(query=args.query))
    if args.command == "ops-health":
        return _print_json(build_ops_health())
    if args.command == "ingest":
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
    if args.command == "connector":
        if args.kind == "jira":
            return _print_json(load_jira_sync(args.path))
        if args.kind == "confluence":
            return _print_json(load_confluence_sync(args.path))
    if args.command == "search":
        results = search_page_index(_load_index(args.corpus), args.query, set(args.policies))
        return _print_json(results)
    if args.command == "citation":
        results = search_page_index(_load_index(args.corpus), args.query, set(args.policies))
        if not results:
            return _print_json({"citation": None, "inspection": None})
        return _print_json(
            {
                "citation": assemble_citation(results[0]),
                "inspection": build_source_inspection(results[0]),
            }
        )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())


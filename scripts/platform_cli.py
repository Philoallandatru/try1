from __future__ import annotations

import argparse
from collections import Counter
from contextlib import redirect_stderr, redirect_stdout
import io
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.portal.portal_state import build_portal_state
from scripts.gates.check_adr_contract import main as adr_check_main
from scripts.gates.check_module_contracts import main as module_check_main
from scripts.gates.check_repo_shape import main as repo_check_main
from services.eval.real_pdf_validation import validate_real_pdfs
from scripts.gates.run_phase1_gate import evaluate_phase1_gate
from services.analysis.jira_issue_analysis import (
    build_confluence_wiki_summary_payload,
    build_jira_batch_spec_report,
    build_jira_pm_daily_report,
    build_jira_spec_question_payload,
    build_jira_time_report,
    build_spec_section_explain_payload,
    render_confluence_static_wiki,
)
from services.analysis.llm_backends import build_llm_backend
from services.analysis.retrieval_consumption import build_retrieval_consumption_payload
from services.eval.harness import evaluate_dataset
from services.ingest.adapters.markdown.adapter import parse_markdown
from services.ingest.adapters.office.adapter import parse_docx, parse_pptx, parse_xlsx
from services.ingest.adapters.pdf.adapter import extract_pdf_structure
from services.ingest.markdown_export import documents_to_markdown, write_documents_markdown_tree
from services.ops.health import build_ops_health
from services.ops.orchestration import configured_sources, load_source_payload, run_multi_sync_health, run_sync_export, run_sync_health
from services.ops.profile import build_multi_sync_profile, load_json_file, validate_multi_sync_profile
from services.retrieval.persistence.snapshot_store import snapshot_paths
from services.retrieval.toolkit import (
    build_retrieval_index,
    citation_for_documents,
    citation_for_index,
    load_document_snapshot,
    load_page_index_artifact,
    search_documents,
    search_index,
)
from services.retrieval.indexing.page_index import build_page_index
from services.wiki_site.builder import build_export_package, build_wiki_site


def _print_json(payload: dict | list) -> int:
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def _write_json_output(path: str | Path, payload: dict | list) -> str:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return str(output_path)


def _write_text_output(path: str | Path, text: str) -> str:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(text, encoding="utf-8")
    return str(output_path)


def _json_default(value: object) -> object:
    if isinstance(value, set):
        return sorted(value)
    if isinstance(value, Counter):
        return dict(value)
    raise TypeError(f"Object of type {value.__class__.__name__} is not JSON serializable")


def _build_spec_corpus_from_pdf(
    *,
    spec_pdf: str | Path,
    output_dir: str | Path,
    preferred_parser: str = "auto",
    mineru_python_exe: str | None = None,
) -> dict:
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    previous_mineru_python = os.environ.get("MINERU_PYTHON_EXE")
    try:
        if mineru_python_exe:
            os.environ["MINERU_PYTHON_EXE"] = mineru_python_exe
        document = extract_pdf_structure(spec_pdf, preferred_parser=preferred_parser)
    finally:
        if mineru_python_exe:
            if previous_mineru_python is None:
                os.environ.pop("MINERU_PYTHON_EXE", None)
            else:
                os.environ["MINERU_PYTHON_EXE"] = previous_mineru_python

    spec_doc_path = output_root / "spec-doc.json"
    spec_corpus_path = output_root / "spec-corpus.json"
    spec_doc_path.write_text(json.dumps(document, indent=2, ensure_ascii=False, default=_json_default), encoding="utf-8")
    spec_corpus_path.write_text(
        json.dumps({"documents": [document]}, indent=2, ensure_ascii=False, default=_json_default),
        encoding="utf-8",
    )
    return {
        "document_id": document["document_id"],
        "preferred_parser": preferred_parser,
        "parser_used": document.get("provenance", {}).get("parser"),
        "spec_doc_json": str(spec_doc_path),
        "spec_corpus_json": str(spec_corpus_path),
        "section_count": len(document.get("structure", {}).get("sections", [])),
        "content_block_count": len(document.get("content_blocks", [])),
    }

def _validate_retrieval_source(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    if args.page_index and args.snapshot_dir:
        parser.error("Provide at most one of --page-index or --snapshot-dir")
    if (args.page_index or args.snapshot_dir) and args.corpus != "fixtures/retrieval/pageindex_corpus.json":
        parser.error("Provide one retrieval source override: --corpus, --page-index, or --snapshot-dir")


def _load_snapshot_page_index(snapshot_dir: str | Path) -> list[dict]:
    return load_page_index_artifact(snapshot_paths(snapshot_dir)["page_index"])


def _add_live_fetch_args(command_parser: argparse.ArgumentParser) -> None:
    command_parser.add_argument("--fetch-backend", choices=["native", "atlassian-api"], default="native")
    command_parser.add_argument("--issue-key")
    command_parser.add_argument("--issue-keys")
    command_parser.add_argument("--project-key")
    command_parser.add_argument("--project-keys")
    command_parser.add_argument("--issue-type")
    command_parser.add_argument("--status")
    command_parser.add_argument("--label")
    command_parser.add_argument("--updated-from")
    command_parser.add_argument("--updated-to")
    command_parser.add_argument("--page-id")
    command_parser.add_argument("--page-ids")
    command_parser.add_argument("--root-page-id")
    command_parser.add_argument("--include-descendants", action="store_true")
    command_parser.add_argument("--max-depth", type=int)
    command_parser.add_argument("--title")
    command_parser.add_argument("--ancestor-id")
    command_parser.add_argument("--modified-from")
    command_parser.add_argument("--modified-to")
    command_parser.add_argument("--no-include-comments", action="store_true")
    command_parser.add_argument("--no-include-attachments", action="store_true")
    command_parser.add_argument("--no-include-image-metadata", action="store_true")
    command_parser.add_argument("--download-images", action="store_true")
    command_parser.add_argument("--image-download-dir")


def _add_prefixed_jira_fetch_args(command_parser: argparse.ArgumentParser) -> None:
    command_parser.add_argument("--jira-fetch-backend", choices=["native", "atlassian-api"], default="native")
    command_parser.add_argument("--jira-issue-key")
    command_parser.add_argument("--jira-issue-keys")
    command_parser.add_argument("--jira-project-key")
    command_parser.add_argument("--jira-project-keys")
    command_parser.add_argument("--jira-issue-type")
    command_parser.add_argument("--jira-status")
    command_parser.add_argument("--jira-label")
    command_parser.add_argument("--jira-updated-from")
    command_parser.add_argument("--jira-updated-to")
    command_parser.add_argument("--jira-no-include-comments", action="store_true")
    command_parser.add_argument("--jira-no-include-attachments", action="store_true")
    command_parser.add_argument("--jira-no-include-image-metadata", action="store_true")
    command_parser.add_argument("--jira-download-images", action="store_true")
    command_parser.add_argument("--jira-image-download-dir")


def _add_prefixed_confluence_fetch_args(command_parser: argparse.ArgumentParser) -> None:
    command_parser.add_argument("--confluence-fetch-backend", choices=["native", "atlassian-api"], default="native")
    command_parser.add_argument("--confluence-page-id")
    command_parser.add_argument("--confluence-page-ids")
    command_parser.add_argument("--confluence-root-page-id")
    command_parser.add_argument("--confluence-include-descendants", action="store_true")
    command_parser.add_argument("--confluence-max-depth", type=int)
    command_parser.add_argument("--confluence-title")
    command_parser.add_argument("--confluence-label")
    command_parser.add_argument("--confluence-ancestor-id")
    command_parser.add_argument("--confluence-modified-from")
    command_parser.add_argument("--confluence-modified-to")
    command_parser.add_argument("--confluence-no-include-attachments", action="store_true")
    command_parser.add_argument("--confluence-no-include-image-metadata", action="store_true")
    command_parser.add_argument("--confluence-download-images", action="store_true")
    command_parser.add_argument("--confluence-image-download-dir")


def _validate_jira_filter_args(parser: argparse.ArgumentParser, args: argparse.Namespace, *, prefix: str = "") -> None:
    jql = getattr(args, f"{prefix}jql")
    fetch_backend = getattr(args, f"{prefix}fetch_backend", "native")
    helper_values = [
        getattr(args, f"{prefix}issue_key", None),
        getattr(args, f"{prefix}issue_keys", None),
        getattr(args, f"{prefix}project_key", None),
        getattr(args, f"{prefix}project_keys", None),
        getattr(args, f"{prefix}issue_type", None),
        getattr(args, f"{prefix}status", None),
        getattr(args, f"{prefix}label", None),
        getattr(args, f"{prefix}updated_from", None),
        getattr(args, f"{prefix}updated_to", None),
    ]
    backend_only_features = any(helper_values) or getattr(args, f"{prefix}no_include_comments", False) or getattr(args, f"{prefix}no_include_attachments", False) or getattr(args, f"{prefix}no_include_image_metadata", False) or getattr(args, f"{prefix}download_images", False)
    if fetch_backend != "atlassian-api" and backend_only_features:
        parser.error("Selective Jira live fetch flags require the atlassian-api backend")
    if jql != "order by updated asc" and any(helper_values):
        parser.error("Jira helper filters cannot be combined with raw JQL")
    if getattr(args, f"{prefix}download_images", False) and getattr(args, f"{prefix}no_include_attachments", False):
        parser.error("Image download requires attachments to be included")
    if getattr(args, f"{prefix}download_images", False) and getattr(args, f"{prefix}no_include_image_metadata", False):
        parser.error("Image download requires image metadata to be included")
    if getattr(args, f"{prefix}download_images", False) and not getattr(args, f"{prefix}image_download_dir", None):
        parser.error("Image download requires --image-download-dir")


def _validate_confluence_filter_args(parser: argparse.ArgumentParser, args: argparse.Namespace, *, prefix: str = "") -> None:
    cql = getattr(args, f"{prefix}cql")
    fetch_backend = getattr(args, f"{prefix}fetch_backend", "native")
    helper_values = [
        getattr(args, f"{prefix}page_id", None),
        getattr(args, f"{prefix}page_ids", None),
        getattr(args, f"{prefix}root_page_id", None),
        getattr(args, f"{prefix}title", None),
        getattr(args, f"{prefix}label", None),
        getattr(args, f"{prefix}ancestor_id", None),
        getattr(args, f"{prefix}modified_from", None),
        getattr(args, f"{prefix}modified_to", None),
    ]
    include_descendants = getattr(args, f"{prefix}include_descendants", False)
    max_depth = getattr(args, f"{prefix}max_depth", None)
    backend_only_features = any(helper_values) or include_descendants or max_depth is not None or getattr(args, f"{prefix}no_include_attachments", False) or getattr(args, f"{prefix}no_include_image_metadata", False) or getattr(args, f"{prefix}download_images", False)
    if fetch_backend != "atlassian-api" and backend_only_features:
        parser.error("Selective Confluence live fetch flags require the atlassian-api backend")
    if cql and any(helper_values):
        parser.error("Confluence helper filters cannot be combined with raw CQL")
    if include_descendants and not getattr(args, f"{prefix}root_page_id", None):
        parser.error("Confluence descendant traversal requires --root-page-id")
    if max_depth is not None and max_depth < 0:
        parser.error("--max-depth must be greater than or equal to 0")
    if max_depth is not None and not include_descendants:
        parser.error("--max-depth requires --include-descendants")
    if getattr(args, f"{prefix}download_images", False) and getattr(args, f"{prefix}no_include_attachments", False):
        parser.error("Image download requires attachments to be included")
    if getattr(args, f"{prefix}download_images", False) and getattr(args, f"{prefix}no_include_image_metadata", False):
        parser.error("Image download requires image metadata to be included")
    if getattr(args, f"{prefix}download_images", False) and not getattr(args, f"{prefix}image_download_dir", None):
        parser.error("Image download requires --image-download-dir")


def _validate_profile_source_config(parser: argparse.ArgumentParser, *, source_name: str, config: dict) -> None:
    if config.get("fetch_backend", "native") != "atlassian-api":
        if source_name == "jira" and any(
            [
                config.get("issue_key"),
                config.get("issue_keys"),
                config.get("project_key"),
                config.get("project_keys"),
                config.get("issue_type"),
                config.get("status"),
                config.get("label"),
                config.get("updated_from"),
                config.get("updated_to"),
                config.get("include_comments") is False,
                config.get("include_attachments") is False,
                config.get("include_image_metadata") is False,
                config.get("download_images"),
            ]
        ):
            parser.error("Selective Jira profile fetch flags require the atlassian-api backend")
        if source_name == "confluence" and any(
            [
                config.get("page_id"),
                config.get("page_ids"),
                config.get("root_page_id"),
                config.get("title"),
                config.get("label"),
                config.get("ancestor_id"),
                config.get("modified_from"),
                config.get("modified_to"),
                config.get("include_descendants"),
                config.get("max_depth") is not None,
                config.get("include_attachments") is False,
                config.get("include_image_metadata") is False,
                config.get("download_images"),
            ]
        ):
            parser.error("Selective Confluence profile fetch flags require the atlassian-api backend")
    if source_name == "jira" and config.get("jql") not in {None, "order by updated asc"} and any(
        [config.get("issue_key"), config.get("issue_keys"), config.get("project_key"), config.get("project_keys"), config.get("issue_type"), config.get("status"), config.get("label"), config.get("updated_from"), config.get("updated_to")]
    ):
        parser.error("Jira profile helper filters cannot be combined with raw JQL")
    if source_name == "confluence" and config.get("cql") and any(
        [config.get("page_id"), config.get("page_ids"), config.get("root_page_id"), config.get("title"), config.get("label"), config.get("ancestor_id"), config.get("modified_from"), config.get("modified_to")]
    ):
        parser.error("Confluence profile helper filters cannot be combined with raw CQL")
    if source_name == "confluence" and config.get("include_descendants") and not config.get("root_page_id"):
        parser.error("Confluence descendant traversal requires root_page_id")
    if source_name == "confluence" and config.get("max_depth") is not None:
        if not isinstance(config.get("max_depth"), int) or config.get("max_depth") < 0:
            parser.error("Confluence max_depth must be an integer greater than or equal to 0")
        if not config.get("include_descendants"):
            parser.error("Confluence max_depth requires include_descendants")
    if config.get("download_images") and not config.get("image_download_dir"):
        parser.error("Profile image download requires an image_download_dir")


def _validate_live_connector_args(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    if not args.live:
        return
    if not args.base_url:
        parser.error("--base-url is required when --live is set")
    if args.page_size <= 0:
        parser.error("--page-size must be greater than 0")
    if args.kind == "jira":
        _validate_jira_filter_args(parser, args)
    if args.kind == "confluence":
        _validate_confluence_filter_args(parser, args)


def _load_connector_payload(args: argparse.Namespace) -> dict:
    return load_source_payload(
        kind=args.kind,
        path=args.path,
        live=args.live,
        base_url=args.base_url,
        username=args.username,
        password=args.password,
        token=args.token,
        auth_mode=args.auth_mode,
        cursor=args.cursor,
        page_size=args.page_size,
        jql=args.jql,
        cql=args.cql,
        space_key=args.space_key,
        insecure=args.insecure,
        fetch_backend=args.fetch_backend,
        issue_key=args.issue_key,
        issue_keys=args.issue_keys,
        project_key=args.project_key,
        project_keys=args.project_keys,
        issue_type=args.issue_type,
        status=args.status,
        label=args.label,
        updated_from=args.updated_from,
        updated_to=args.updated_to,
        page_id=args.page_id,
        page_ids=args.page_ids,
        root_page_id=args.root_page_id,
        title=args.title,
        ancestor_id=args.ancestor_id,
        modified_from=args.modified_from,
        modified_to=args.modified_to,
        include_descendants=args.include_descendants,
        max_depth=args.max_depth,
        include_comments=not args.no_include_comments,
        include_attachments=not args.no_include_attachments,
        include_image_metadata=not args.no_include_image_metadata,
        download_images=args.download_images,
        image_download_dir=args.image_download_dir,
    )


def _add_jira_source_args(command_parser: argparse.ArgumentParser) -> None:
    command_parser.add_argument("--jira-path")
    command_parser.add_argument("--jira-live", action="store_true")
    command_parser.add_argument("--jira-base-url")
    command_parser.add_argument("--jira-username")
    command_parser.add_argument("--jira-password")
    command_parser.add_argument("--jira-token")
    command_parser.add_argument("--jira-auth-mode", default="auto")
    command_parser.add_argument("--jira-cursor")
    command_parser.add_argument("--jira-page-size", type=int, default=50)
    command_parser.add_argument("--jira-jql", default="order by updated asc")
    command_parser.add_argument("--jira-insecure", action="store_true")
    _add_prefixed_jira_fetch_args(command_parser)


def _add_confluence_source_args(command_parser: argparse.ArgumentParser) -> None:
    command_parser.add_argument("--confluence-path")
    command_parser.add_argument("--confluence-live", action="store_true")
    command_parser.add_argument("--confluence-base-url")
    command_parser.add_argument("--confluence-username")
    command_parser.add_argument("--confluence-password")
    command_parser.add_argument("--confluence-token")
    command_parser.add_argument("--confluence-auth-mode", default="auto")
    command_parser.add_argument("--confluence-cursor")
    command_parser.add_argument("--confluence-page-size", type=int, default=25)
    command_parser.add_argument("--confluence-cql")
    command_parser.add_argument("--confluence-space-key")
    command_parser.add_argument("--confluence-insecure", action="store_true")
    _add_prefixed_confluence_fetch_args(command_parser)


def _add_llm_backend_args(command_parser: argparse.ArgumentParser) -> None:
    command_parser.add_argument(
        "--llm-backend",
        choices=["none", "mock", "ollama", "openai-compatible"],
        default="none",
    )
    command_parser.add_argument("--llm-model")
    command_parser.add_argument("--llm-base-url")
    command_parser.add_argument("--llm-api-key")
    command_parser.add_argument("--llm-timeout-seconds", type=int, default=120)
    command_parser.add_argument("--llm-mock-response")
    command_parser.add_argument(
        "--llm-prompt-mode",
        choices=["strict", "balanced", "exploratory"],
        default="strict",
    )


def _build_llm_backend_from_args(parser: argparse.ArgumentParser, args: argparse.Namespace):
    try:
        return build_llm_backend(
            backend=args.llm_backend,
            model=args.llm_model,
            base_url=args.llm_base_url,
            api_key=args.llm_api_key,
            mock_response=args.llm_mock_response,
            timeout_seconds=args.llm_timeout_seconds,
        )
    except ValueError as error:
        parser.error(str(error))


def _load_jira_documents_from_args(parser: argparse.ArgumentParser, args: argparse.Namespace) -> list[dict]:
    _validate_prefixed_live_args(
        parser,
        args=args,
        live=args.jira_live,
        base_url=args.jira_base_url,
        page_size=args.jira_page_size,
        source_name="jira",
    )
    if not args.jira_live and not args.jira_path:
        parser.error("Jira source is required via --jira-path or --jira-live")
    _validate_jira_filter_args(parser, args, prefix="jira_")
    return load_source_payload(
        kind="jira",
        path=args.jira_path,
        live=args.jira_live,
        base_url=args.jira_base_url,
        username=args.jira_username,
        password=args.jira_password,
        token=args.jira_token,
        auth_mode=args.jira_auth_mode,
        cursor=args.jira_cursor,
        page_size=args.jira_page_size,
        jql=args.jira_jql,
        insecure=args.jira_insecure,
        fetch_backend=args.jira_fetch_backend,
        issue_key=args.jira_issue_key,
        issue_keys=args.jira_issue_keys,
        project_key=args.jira_project_key,
        project_keys=args.jira_project_keys,
        issue_type=args.jira_issue_type,
        status=args.jira_status,
        label=args.jira_label,
        updated_from=args.jira_updated_from,
        updated_to=args.jira_updated_to,
        include_comments=not args.jira_no_include_comments,
        include_attachments=not args.jira_no_include_attachments,
        include_image_metadata=not args.jira_no_include_image_metadata,
        download_images=args.jira_download_images,
        image_download_dir=args.jira_image_download_dir,
    )["documents"]


def _load_confluence_documents_from_args(parser: argparse.ArgumentParser, args: argparse.Namespace) -> list[dict]:
    _validate_prefixed_live_args(
        parser,
        args=args,
        live=args.confluence_live,
        base_url=args.confluence_base_url,
        page_size=args.confluence_page_size,
        source_name="confluence",
    )
    if not args.confluence_live and not args.confluence_path:
        parser.error("Confluence source is required via --confluence-path or --confluence-live")
    _validate_confluence_filter_args(parser, args, prefix="confluence_")
    return load_source_payload(
        kind="confluence",
        path=args.confluence_path,
        live=args.confluence_live,
        base_url=args.confluence_base_url,
        username=args.confluence_username,
        password=args.confluence_password,
        token=args.confluence_token,
        auth_mode=args.confluence_auth_mode,
        cursor=args.confluence_cursor,
        page_size=args.confluence_page_size,
        cql=args.confluence_cql,
        space_key=args.confluence_space_key,
        insecure=args.confluence_insecure,
        fetch_backend=args.confluence_fetch_backend,
        page_id=args.confluence_page_id,
        page_ids=args.confluence_page_ids,
        root_page_id=args.confluence_root_page_id,
        title=args.confluence_title,
        label=args.confluence_label,
        ancestor_id=args.confluence_ancestor_id,
        modified_from=args.confluence_modified_from,
        modified_to=args.confluence_modified_to,
        include_descendants=args.confluence_include_descendants,
        max_depth=args.confluence_max_depth,
        include_attachments=not args.confluence_no_include_attachments,
        include_image_metadata=not args.confluence_no_include_image_metadata,
        download_images=args.confluence_download_images,
        image_download_dir=args.confluence_image_download_dir,
    )["documents"]


def _load_retrieval_consumption_documents(parser: argparse.ArgumentParser, args: argparse.Namespace) -> list[dict]:
    if args.snapshot_dir:
        return load_document_snapshot(snapshot_paths(args.snapshot_dir)["documents"])
    if args.source_kind == "jira-live":
        _validate_jira_filter_args(parser, args)
        return load_source_payload(
            kind="jira",
            path=None,
            live=True,
            base_url=args.base_url,
            username=args.username,
            password=args.password,
            token=args.token,
            auth_mode=args.auth_mode,
            cursor=args.cursor,
            page_size=args.page_size,
            jql=args.jql,
            insecure=args.insecure,
            fetch_backend=args.fetch_backend,
            issue_key=args.issue_key,
            issue_keys=args.issue_keys,
            project_key=args.project_key,
            project_keys=args.project_keys,
            issue_type=args.issue_type,
            status=args.status,
            label=args.label,
            updated_from=args.updated_from,
            updated_to=args.updated_to,
            include_comments=not args.no_include_comments,
            include_attachments=not args.no_include_attachments,
            include_image_metadata=not args.no_include_image_metadata,
            download_images=args.download_images,
            image_download_dir=args.image_download_dir,
        )["documents"]
    if args.source_kind == "confluence-live":
        _validate_confluence_filter_args(parser, args)
        return load_source_payload(
            kind="confluence",
            path=None,
            live=True,
            base_url=args.base_url,
            username=args.username,
            password=args.password,
            token=args.token,
            auth_mode=args.auth_mode,
            cursor=args.cursor,
            page_size=args.page_size,
            cql=args.cql,
            space_key=args.space_key,
            insecure=args.insecure,
            fetch_backend=args.fetch_backend,
            page_id=args.page_id,
            page_ids=args.page_ids,
            root_page_id=args.root_page_id,
            title=args.title,
            label=args.label,
            ancestor_id=args.ancestor_id,
            modified_from=args.modified_from,
            modified_to=args.modified_to,
            include_descendants=args.include_descendants,
            max_depth=args.max_depth,
            include_attachments=not args.no_include_attachments,
            include_image_metadata=not args.no_include_image_metadata,
            download_images=args.download_images,
            image_download_dir=args.image_download_dir,
        )["documents"]
    if args.source_kind == "jira-sync":
        return load_source_payload(kind="jira", path=args.source_path, live=False)["documents"]
    if args.source_kind == "confluence-sync":
        return load_source_payload(kind="confluence", path=args.source_path, live=False)["documents"]
    if args.source_kind == "markdown":
        return [parse_markdown(args.source_path)]
    if args.source_kind == "docx":
        return [parse_docx(args.source_path)]
    if args.source_kind == "xlsx":
        return [parse_xlsx(args.source_path)]
    if args.source_kind == "pptx":
        return [parse_pptx(args.source_path)]
    if args.source_kind == "pdf":
        return [extract_pdf_structure(args.source_path)]
    parser.error(f"Unsupported source kind: {args.source_kind}")


def _load_retrieval_consumption_documents_quietly(parser: argparse.ArgumentParser, args: argparse.Namespace) -> list[dict]:
    sink = io.StringIO()
    with redirect_stdout(sink), redirect_stderr(sink):
        return _load_retrieval_consumption_documents(parser, args)


def _validate_retrieval_consumption_source(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    has_snapshot = bool(args.snapshot_dir)
    has_source = bool(args.source_kind or args.source_path)
    if has_snapshot and has_source:
        parser.error("Provide either --snapshot-dir or --source-kind/--source-path, not both")
    if not has_snapshot and not (args.source_kind and args.source_path):
        if args.source_kind not in {"jira-live", "confluence-live"}:
            parser.error("Provide --snapshot-dir or both --source-kind and --source-path")
    if args.source_kind in {"jira-live", "confluence-live"}:
        if not args.base_url:
            parser.error("--base-url is required for live retrieval-consume sources")
        if args.source_path:
            parser.error("--source-path is not used with live retrieval-consume sources")


def _validate_prefixed_live_args(
    parser: argparse.ArgumentParser,
    *,
    args: argparse.Namespace,
    live: bool,
    base_url: str | None,
    page_size: int,
    source_name: str,
) -> None:
    if not live:
        return
    if not base_url:
        parser.error(f"--{source_name}-base-url is required when --{source_name}-live is set")
    if page_size <= 0:
        parser.error(f"--{source_name}-page-size must be greater than 0")
    if source_name == "jira":
        _validate_jira_filter_args(parser, args, prefix="jira_")
    if source_name == "confluence":
        _validate_confluence_filter_args(parser, args, prefix="confluence_")


def main() -> int:
    parser = argparse.ArgumentParser(description="Unified CLI for SSD knowledge platform foundation utilities.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("adr-check")
    subparsers.add_parser("repo-check")
    subparsers.add_parser("module-check")

    eval_parser = subparsers.add_parser("eval")
    eval_parser.add_argument("--dataset", default="eval/gold_queries.yaml")
    eval_parser.add_argument("--corpus", default="fixtures/retrieval/pageindex_corpus.json")

    real_eval_parser = subparsers.add_parser("real-validate")
    real_eval_parser.add_argument("--spec-pdf", required=True)
    real_eval_parser.add_argument("--context-pdf", required=True)
    real_eval_parser.add_argument("--model", default="qwen2.5:0.5b")
    real_eval_parser.add_argument("--ollama-exe", default=str(Path.home() / "AppData/Local/Programs/Ollama/ollama.exe"))

    gate_parser = subparsers.add_parser("gate")
    gate_parser.add_argument("--dataset", default="eval/gold_queries.yaml")
    gate_parser.add_argument("--corpus", default="fixtures/retrieval/pageindex_corpus.json")

    portal_parser = subparsers.add_parser("portal-state")
    portal_parser.add_argument("--query", default="nvme flush")

    ops_health_parser = subparsers.add_parser("ops-health")
    ops_health_parser.add_argument("--snapshot-dir")
    ops_health_parser.add_argument("--freshness-budget-minutes", type=int, default=30)
    ops_health_parser.add_argument("--reference-time-iso")

    ingest_parser = subparsers.add_parser("ingest")
    ingest_parser.add_argument("kind", choices=["markdown", "docx", "xlsx", "pptx", "pdf"])
    ingest_parser.add_argument("path")

    connector_parser = subparsers.add_parser("connector")
    connector_parser.add_argument("kind", choices=["jira", "confluence"])
    connector_parser.add_argument("path", nargs="?")
    connector_parser.add_argument("--live", action="store_true")
    connector_parser.add_argument("--base-url")
    connector_parser.add_argument("--username")
    connector_parser.add_argument("--password")
    connector_parser.add_argument("--token")
    connector_parser.add_argument("--auth-mode", default="auto")
    connector_parser.add_argument("--cursor")
    connector_parser.add_argument("--page-size", type=int, default=50)
    connector_parser.add_argument("--jql", default="order by updated asc")
    connector_parser.add_argument("--cql")
    connector_parser.add_argument("--space-key")
    connector_parser.add_argument("--insecure", action="store_true")
    connector_parser.add_argument("--output-json")
    _add_live_fetch_args(connector_parser)

    sync_health_parser = subparsers.add_parser("sync-health")
    sync_health_parser.add_argument("kind", choices=["jira", "confluence"])
    sync_health_parser.add_argument("path", nargs="?")
    sync_health_parser.add_argument("--snapshot-dir", required=True)
    sync_health_parser.add_argument("--corpus", default="fixtures/retrieval/pageindex_corpus.json")
    sync_health_parser.add_argument("--live", action="store_true")
    sync_health_parser.add_argument("--base-url")
    sync_health_parser.add_argument("--username")
    sync_health_parser.add_argument("--password")
    sync_health_parser.add_argument("--token")
    sync_health_parser.add_argument("--auth-mode", default="auto")
    sync_health_parser.add_argument("--cursor")
    sync_health_parser.add_argument("--page-size", type=int, default=50)
    sync_health_parser.add_argument("--jql", default="order by updated asc")
    sync_health_parser.add_argument("--cql")
    sync_health_parser.add_argument("--space-key")
    sync_health_parser.add_argument("--insecure", action="store_true")
    sync_health_parser.add_argument("--freshness-budget-minutes", type=int, default=30)
    sync_health_parser.add_argument("--reference-time-iso")
    _add_live_fetch_args(sync_health_parser)

    multi_sync_health_parser = subparsers.add_parser("multi-sync-health")
    multi_sync_health_parser.add_argument("--snapshot-dir")
    multi_sync_health_parser.add_argument("--profile")
    multi_sync_health_parser.add_argument("--corpus", default="fixtures/retrieval/pageindex_corpus.json")
    multi_sync_health_parser.add_argument("--freshness-budget-minutes", type=int, default=30)
    multi_sync_health_parser.add_argument("--reference-time-iso")
    multi_sync_health_parser.add_argument("--jira-path")
    multi_sync_health_parser.add_argument("--jira-live", action="store_true")
    multi_sync_health_parser.add_argument("--jira-base-url")
    multi_sync_health_parser.add_argument("--jira-username")
    multi_sync_health_parser.add_argument("--jira-password")
    multi_sync_health_parser.add_argument("--jira-token")
    multi_sync_health_parser.add_argument("--jira-auth-mode", default="auto")
    multi_sync_health_parser.add_argument("--jira-cursor")
    multi_sync_health_parser.add_argument("--jira-page-size", type=int, default=50)
    multi_sync_health_parser.add_argument("--jira-jql", default="order by updated asc")
    multi_sync_health_parser.add_argument("--jira-insecure", action="store_true")
    _add_prefixed_jira_fetch_args(multi_sync_health_parser)
    multi_sync_health_parser.add_argument("--confluence-path")
    multi_sync_health_parser.add_argument("--confluence-live", action="store_true")
    multi_sync_health_parser.add_argument("--confluence-base-url")
    multi_sync_health_parser.add_argument("--confluence-username")
    multi_sync_health_parser.add_argument("--confluence-password")
    multi_sync_health_parser.add_argument("--confluence-token")
    multi_sync_health_parser.add_argument("--confluence-auth-mode", default="auto")
    multi_sync_health_parser.add_argument("--confluence-cursor")
    multi_sync_health_parser.add_argument("--confluence-page-size", type=int, default=25)
    multi_sync_health_parser.add_argument("--confluence-cql")
    multi_sync_health_parser.add_argument("--confluence-space-key")
    multi_sync_health_parser.add_argument("--confluence-insecure", action="store_true")
    _add_prefixed_confluence_fetch_args(multi_sync_health_parser)

    search_parser = subparsers.add_parser("search")
    search_parser.add_argument("query")
    search_parser.add_argument("--corpus", default="fixtures/retrieval/pageindex_corpus.json")
    search_parser.add_argument("--page-index")
    search_parser.add_argument("--snapshot-dir")
    search_parser.add_argument("--policies", nargs="*", default=["team:ssd", "public"])

    citation_parser = subparsers.add_parser("citation")
    citation_parser.add_argument("query")
    citation_parser.add_argument("--corpus", default="fixtures/retrieval/pageindex_corpus.json")
    citation_parser.add_argument("--page-index")
    citation_parser.add_argument("--snapshot-dir")
    citation_parser.add_argument("--policies", nargs="*", default=["team:ssd", "public"])

    jira_report_parser = subparsers.add_parser("jira-report")
    _add_jira_source_args(jira_report_parser)
    jira_report_parser.add_argument("--updated-from-iso")
    jira_report_parser.add_argument("--updated-to-iso")
    jira_report_parser.add_argument("--updated-on-date")
    jira_report_parser.add_argument("--updated-at-iso")
    jira_report_parser.add_argument("--report-profile", choices=["standard", "pm-daily"], default="standard")
    jira_report_parser.add_argument("--reference-date")
    jira_report_parser.add_argument("--status-filter", default="In Progress")
    jira_report_parser.add_argument("--stale-threshold-hours", type=int, default=24)
    jira_report_parser.add_argument("--prompt-template")
    jira_report_parser.add_argument("--output-md")
    jira_report_parser.add_argument("--output-answer-md")
    _add_llm_backend_args(jira_report_parser)

    jira_spec_qa_parser = subparsers.add_parser("jira-spec-qa")
    _add_jira_source_args(jira_spec_qa_parser)
    jira_spec_qa_parser.add_argument("--jira-issue-id")
    jira_spec_qa_parser.add_argument("--spec-corpus", default="fixtures/retrieval/pageindex_corpus.json")
    jira_spec_qa_parser.add_argument("--spec-document-id", required=True)
    jira_spec_qa_parser.add_argument("--question", required=True)
    jira_spec_qa_parser.add_argument("--prompt-template")
    jira_spec_qa_parser.add_argument("--output-answer-md")
    jira_spec_qa_parser.add_argument("--policies", nargs="*", default=["team:ssd", "public"])
    _add_llm_backend_args(jira_spec_qa_parser)

    jira_batch_spec_report_parser = subparsers.add_parser("jira-batch-spec-report")
    _add_jira_source_args(jira_batch_spec_report_parser)
    jira_batch_spec_report_parser.add_argument("--updated-from-iso")
    jira_batch_spec_report_parser.add_argument("--updated-to-iso")
    jira_batch_spec_report_parser.add_argument("--updated-on-date")
    jira_batch_spec_report_parser.add_argument("--updated-at-iso")
    jira_batch_spec_report_parser.add_argument("--spec-corpus", default="fixtures/retrieval/pageindex_corpus.json")
    jira_batch_spec_report_parser.add_argument("--spec-document-id", required=True)
    jira_batch_spec_report_parser.add_argument("--question-template", default="Analyze Jira {jira_issue_id} against the selected spec.")
    jira_batch_spec_report_parser.add_argument("--prompt-template")
    jira_batch_spec_report_parser.add_argument("--output-md")
    jira_batch_spec_report_parser.add_argument("--policies", nargs="*", default=["team:ssd", "public"])
    _add_llm_backend_args(jira_batch_spec_report_parser)

    spec_section_explain_parser = subparsers.add_parser("spec-section-explain")
    _add_jira_source_args(spec_section_explain_parser)
    spec_section_explain_parser.add_argument("--spec-corpus", default="fixtures/retrieval/pageindex_corpus.json")
    spec_section_explain_parser.add_argument("--spec-document-id", required=True)
    spec_section_explain_parser.add_argument("--clause")
    spec_section_explain_parser.add_argument("--section-heading")
    spec_section_explain_parser.add_argument("--question")
    spec_section_explain_parser.add_argument("--prompt-template")
    spec_section_explain_parser.add_argument("--output-answer-md")
    spec_section_explain_parser.add_argument("--policies", nargs="*", default=["team:ssd", "public"])
    spec_section_explain_parser.add_argument("--top-k", type=int, default=5)
    _add_llm_backend_args(spec_section_explain_parser)

    confluence_wiki_demo_parser = subparsers.add_parser("confluence-wiki-demo")
    _add_confluence_source_args(confluence_wiki_demo_parser)
    confluence_wiki_demo_parser.add_argument("--output-dir", required=True)
    confluence_wiki_demo_parser.add_argument("--prompt-template")
    _add_llm_backend_args(confluence_wiki_demo_parser)

    build_spec_corpus_parser = subparsers.add_parser("build-spec-corpus")
    build_spec_corpus_parser.add_argument("--spec-pdf", required=True)
    build_spec_corpus_parser.add_argument("--output-dir", required=True)
    build_spec_corpus_parser.add_argument("--preferred-parser", choices=["auto", "mineru", "pypdf"], default="auto")
    build_spec_corpus_parser.add_argument("--mineru-python-exe")

    demo_orchestrate_parser = subparsers.add_parser("demo-orchestrate")
    demo_orchestrate_parser.add_argument("--snapshot-dir", default=".tmp/demo/snapshot")
    demo_orchestrate_parser.add_argument("--output-dir", default=".tmp/demo")
    demo_orchestrate_parser.add_argument("--profile")
    demo_orchestrate_parser.add_argument("--corpus", default="fixtures/retrieval/pageindex_corpus.json")
    demo_orchestrate_parser.add_argument("--reference-time-iso")
    _add_jira_source_args(demo_orchestrate_parser)
    _add_confluence_source_args(demo_orchestrate_parser)
    demo_orchestrate_parser.add_argument("--spec-corpus", default="fixtures/retrieval/pageindex_corpus.json")
    demo_orchestrate_parser.add_argument("--spec-document-id", required=True)
    demo_orchestrate_parser.add_argument("--clause")
    demo_orchestrate_parser.add_argument("--section-heading")
    demo_orchestrate_parser.add_argument("--reference-date", required=True)
    demo_orchestrate_parser.add_argument("--policies", nargs="*", default=["team:ssd", "public"])
    _add_llm_backend_args(demo_orchestrate_parser)

    build_wiki_site_parser = subparsers.add_parser("build-wiki-site")
    build_wiki_site_parser.add_argument("--snapshot-dir", default=".tmp/wiki-demo/snapshot")
    build_wiki_site_parser.add_argument("--output-dir", default=".tmp/wiki-demo")
    build_wiki_site_parser.add_argument("--profile")
    build_wiki_site_parser.add_argument("--corpus", default="fixtures/retrieval/pageindex_corpus.json")
    build_wiki_site_parser.add_argument("--reference-time-iso")
    _add_jira_source_args(build_wiki_site_parser)
    _add_confluence_source_args(build_wiki_site_parser)
    build_wiki_site_parser.add_argument("--spec-corpus")
    build_wiki_site_parser.add_argument("--spec-document-id")
    build_wiki_site_parser.add_argument("--spec-pdf")
    build_wiki_site_parser.add_argument("--preferred-parser", choices=["auto", "mineru", "pypdf"], default="auto")
    build_wiki_site_parser.add_argument("--mineru-python-exe")
    build_wiki_site_parser.add_argument("--clause")
    build_wiki_site_parser.add_argument("--section-heading")
    build_wiki_site_parser.add_argument("--reference-date", required=True)
    build_wiki_site_parser.add_argument("--site-title", default="SSD Knowledge Wiki Demo")
    build_wiki_site_parser.add_argument("--policies", nargs="*", default=["team:ssd", "public"])
    _add_llm_backend_args(build_wiki_site_parser)

    retrieval_consume_parser = subparsers.add_parser("retrieval-consume")
    retrieval_consume_parser.add_argument("--snapshot-dir")
    retrieval_consume_parser.add_argument(
        "--source-kind",
        choices=["jira-sync", "confluence-sync", "jira-live", "confluence-live", "markdown", "docx", "xlsx", "pptx", "pdf"],
    )
    retrieval_consume_parser.add_argument("--source-path")
    retrieval_consume_parser.add_argument("--base-url")
    retrieval_consume_parser.add_argument("--username")
    retrieval_consume_parser.add_argument("--password")
    retrieval_consume_parser.add_argument("--token")
    retrieval_consume_parser.add_argument("--auth-mode", default="auto")
    retrieval_consume_parser.add_argument("--cursor")
    retrieval_consume_parser.add_argument("--page-size", type=int, default=50)
    retrieval_consume_parser.add_argument("--jql", default="order by updated asc")
    retrieval_consume_parser.add_argument("--cql")
    retrieval_consume_parser.add_argument("--space-key")
    retrieval_consume_parser.add_argument("--insecure", action="store_true")
    _add_live_fetch_args(retrieval_consume_parser)
    retrieval_consume_parser.add_argument("--question", required=True)
    retrieval_consume_parser.add_argument("--prompt-template")
    retrieval_consume_parser.add_argument("--output-answer-md")
    retrieval_consume_parser.add_argument("--output-json")
    retrieval_consume_parser.add_argument("--policies", nargs="*", default=["team:ssd", "public"])
    retrieval_consume_parser.add_argument("--top-k", type=int, default=5)
    _add_llm_backend_args(retrieval_consume_parser)

    sync_export_parser = subparsers.add_parser("sync-export")
    sync_export_parser.add_argument("--snapshot-dir")
    sync_export_parser.add_argument("--profile")
    sync_export_parser.add_argument("--corpus", default="fixtures/retrieval/pageindex_corpus.json")
    sync_export_parser.add_argument("--freshness-budget-minutes", type=int, default=30)
    sync_export_parser.add_argument("--reference-time-iso")
    sync_export_parser.add_argument("--export-scope", choices=["incoming", "snapshot"], default="incoming")
    sync_export_parser.add_argument("--output-md")
    sync_export_parser.add_argument("--output-md-dir")
    sync_export_parser.add_argument("--output-page-index")
    sync_export_parser.add_argument("--jira-path")
    sync_export_parser.add_argument("--jira-live", action="store_true")
    sync_export_parser.add_argument("--jira-base-url")
    sync_export_parser.add_argument("--jira-username")
    sync_export_parser.add_argument("--jira-password")
    sync_export_parser.add_argument("--jira-token")
    sync_export_parser.add_argument("--jira-auth-mode", default="auto")
    sync_export_parser.add_argument("--jira-cursor")
    sync_export_parser.add_argument("--jira-page-size", type=int, default=50)
    sync_export_parser.add_argument("--jira-jql", default="order by updated asc")
    sync_export_parser.add_argument("--jira-insecure", action="store_true")
    _add_prefixed_jira_fetch_args(sync_export_parser)
    sync_export_parser.add_argument("--confluence-path")
    sync_export_parser.add_argument("--confluence-live", action="store_true")
    sync_export_parser.add_argument("--confluence-base-url")
    sync_export_parser.add_argument("--confluence-username")
    sync_export_parser.add_argument("--confluence-password")
    sync_export_parser.add_argument("--confluence-token")
    sync_export_parser.add_argument("--confluence-auth-mode", default="auto")
    sync_export_parser.add_argument("--confluence-cursor")
    sync_export_parser.add_argument("--confluence-page-size", type=int, default=25)
    sync_export_parser.add_argument("--confluence-cql")
    sync_export_parser.add_argument("--confluence-space-key")
    sync_export_parser.add_argument("--confluence-insecure", action="store_true")
    _add_prefixed_confluence_fetch_args(sync_export_parser)

    args = parser.parse_args()

    if args.command == "adr-check":
        return adr_check_main()
    if args.command == "repo-check":
        return repo_check_main()
    if args.command == "module-check":
        return module_check_main()
    if args.command == "eval":
        return _print_json(evaluate_dataset(args.corpus, args.dataset, {"team:ssd", "public"}))
    if args.command == "real-validate":
        return _print_json(
            validate_real_pdfs(
                spec_pdf=args.spec_pdf,
                contextual_pdf=args.context_pdf,
                model=args.model,
                ollama_executable=args.ollama_exe,
            )
        )
    if args.command == "gate":
        return _print_json(evaluate_phase1_gate(args.dataset, args.corpus, {"team:ssd", "public"}))
    if args.command == "portal-state":
        return _print_json(build_portal_state(query=args.query))
    if args.command == "ops-health":
        return _print_json(
            build_ops_health(
                snapshot_dir=args.snapshot_dir,
                freshness_budget_minutes=args.freshness_budget_minutes,
                reference_time_iso=args.reference_time_iso,
            )
        )
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
        _validate_live_connector_args(parser, args)
        if not args.live and not args.path:
            parser.error("connector path is required unless --live is set")
        payload = _load_connector_payload(args)
        if args.output_json:
            payload["output_json"] = _write_json_output(args.output_json, payload)
        return _print_json(payload)
    if args.command == "sync-health":
        _validate_live_connector_args(parser, args)
        if not args.live and not args.path:
            parser.error("connector path is required unless --live is set")
        return _print_json(
            run_sync_health(
                snapshot_dir=args.snapshot_dir,
                corpus=args.corpus,
                kind=args.kind,
                path=args.path,
                live=args.live,
                base_url=args.base_url,
                username=args.username,
                password=args.password,
                token=args.token,
                auth_mode=args.auth_mode,
                cursor=args.cursor,
                page_size=args.page_size,
                jql=args.jql,
                cql=args.cql,
                space_key=args.space_key,
                insecure=args.insecure,
                freshness_budget_minutes=args.freshness_budget_minutes,
                reference_time_iso=args.reference_time_iso,
                fetch_backend=args.fetch_backend,
                issue_key=args.issue_key,
                issue_keys=args.issue_keys,
                project_key=args.project_key,
                project_keys=args.project_keys,
                issue_type=args.issue_type,
                status=args.status,
                label=args.label,
                updated_from=args.updated_from,
                updated_to=args.updated_to,
                page_id=args.page_id,
                page_ids=args.page_ids,
                title=args.title,
                ancestor_id=args.ancestor_id,
                modified_from=args.modified_from,
                modified_to=args.modified_to,
                include_comments=not args.no_include_comments,
                include_attachments=not args.no_include_attachments,
                include_image_metadata=not args.no_include_image_metadata,
                download_images=args.download_images,
                image_download_dir=args.image_download_dir,
            )
        )
    if args.command == "multi-sync-health":
        if args.profile:
            profile_errors = validate_multi_sync_profile(load_json_file(args.profile))
            if profile_errors:
                parser.error("; ".join(profile_errors))
        profile = build_multi_sync_profile(args)
        if not profile["snapshot_dir"]:
            parser.error("snapshot dir is required via --snapshot-dir or --profile")
        jira_config, confluence_config = profile["sources"]
        _validate_prefixed_live_args(
            parser,
            args=args,
            live=jira_config["live"],
            base_url=jira_config.get("base_url"),
            page_size=jira_config["page_size"],
            source_name="jira",
        )
        _validate_prefixed_live_args(
            parser,
            args=args,
            live=confluence_config["live"],
            base_url=confluence_config.get("base_url"),
            page_size=confluence_config["page_size"],
            source_name="confluence",
        )
        if not jira_config["live"] and not jira_config.get("path"):
            parser.error("Jira source is required via --jira-path, --jira-live, or --profile")
        if not confluence_config["live"] and not confluence_config.get("path"):
            parser.error("Confluence source is required via --confluence-path, --confluence-live, or --profile")
        result = run_multi_sync_health(profile)
        result["profile"] = args.profile
        return _print_json(result)
    if args.command == "search":
        _validate_retrieval_source(parser, args)
        if args.page_index:
            results = search_index(load_page_index_artifact(args.page_index), args.query, set(args.policies))
            return _print_json(results)
        if args.snapshot_dir:
            results = search_index(_load_snapshot_page_index(args.snapshot_dir), args.query, set(args.policies))
            return _print_json(results)
        results = search_documents(load_document_snapshot(args.corpus), args.query, set(args.policies))
        return _print_json(results)
    if args.command == "citation":
        _validate_retrieval_source(parser, args)
        if args.page_index:
            return _print_json(citation_for_index(load_page_index_artifact(args.page_index), args.query, set(args.policies)))
        if args.snapshot_dir:
            return _print_json(citation_for_index(_load_snapshot_page_index(args.snapshot_dir), args.query, set(args.policies)))
        return _print_json(citation_for_documents(load_document_snapshot(args.corpus), args.query, set(args.policies)))
    if args.command == "jira-report":
        jira_documents = _load_jira_documents_from_args(parser, args)
        llm_backend = _build_llm_backend_from_args(parser, args)
        if args.report_profile == "pm-daily":
            reference_date = args.reference_date or args.updated_on_date
            if not reference_date:
                parser.error("--report-profile pm-daily requires --reference-date or --updated-on-date")
            report = build_jira_pm_daily_report(
                jira_documents,
                reference_date=reference_date,
                status_filter=args.status_filter,
                stale_threshold_hours=args.stale_threshold_hours,
                prompt_template=args.prompt_template,
                prompt_mode=args.llm_prompt_mode,
                llm_backend=llm_backend,
            )
        else:
            report = build_jira_time_report(
                jira_documents,
                updated_from_iso=args.updated_from_iso,
                updated_to_iso=args.updated_to_iso,
                updated_on_date=args.updated_on_date,
                updated_at_iso=args.updated_at_iso,
                prompt_template=args.prompt_template,
                prompt_mode=args.llm_prompt_mode,
                llm_backend=llm_backend,
            )
        if args.output_md:
            output_path = Path(args.output_md)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(report["markdown"], encoding="utf-8")
            report["output_md"] = str(output_path)
        if args.output_answer_md:
            if "answer" not in report:
                parser.error("--output-answer-md requires --llm-backend to be set")
            output_path = Path(args.output_answer_md)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(report["answer"]["text"], encoding="utf-8")
            report["output_answer_md"] = str(output_path)
        return _print_json(report)
    if args.command == "jira-spec-qa":
        jira_documents = _load_jira_documents_from_args(parser, args)
        jira_document = next(
            (document for document in jira_documents if not args.jira_issue_id or document["document_id"] == args.jira_issue_id),
            None,
        )
        if jira_document is None:
            parser.error(f"Jira issue not found: {args.jira_issue_id}")
        spec_documents = [
            document
            for document in load_document_snapshot(args.spec_corpus)
            if document["document_id"] == args.spec_document_id
        ]
        if not spec_documents:
            parser.error(f"Spec document not found: {args.spec_document_id}")
        payload = build_jira_spec_question_payload(
            jira_document=jira_document,
            spec_documents=spec_documents,
            question=args.question,
            allowed_policies=set(args.policies),
            prompt_template=args.prompt_template,
            prompt_mode=args.llm_prompt_mode,
            llm_backend=_build_llm_backend_from_args(parser, args),
        )
        if args.output_answer_md:
            output_path = Path(args.output_answer_md)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(payload["answer"]["text"], encoding="utf-8")
            payload["output_answer_md"] = str(output_path)
        return _print_json(payload)
    if args.command == "jira-batch-spec-report":
        jira_documents = _load_jira_documents_from_args(parser, args)
        spec_documents = [
            document
            for document in load_document_snapshot(args.spec_corpus)
            if document["document_id"] == args.spec_document_id
        ]
        if not spec_documents:
            parser.error(f"Spec document not found: {args.spec_document_id}")
        payload = build_jira_batch_spec_report(
            jira_documents=jira_documents,
            spec_documents=spec_documents,
            question_template=args.question_template,
            allowed_policies=set(args.policies),
            updated_from_iso=args.updated_from_iso,
            updated_to_iso=args.updated_to_iso,
            updated_on_date=args.updated_on_date,
            updated_at_iso=args.updated_at_iso,
            prompt_template=args.prompt_template,
            prompt_mode=args.llm_prompt_mode,
            llm_backend=_build_llm_backend_from_args(parser, args),
        )
        if args.output_md:
            output_path = Path(args.output_md)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            sections = [payload["summary_markdown"]]
            sections.extend(report["answer"]["text"] for report in payload["issues"])
            output_path.write_text("\n\n---\n\n".join(section for section in sections if section), encoding="utf-8")
            payload["output_md"] = str(output_path)
        return _print_json(payload)
    if args.command == "spec-section-explain":
        jira_documents = _load_jira_documents_from_args(parser, args)
        spec_document = next(
            (
                document
                for document in load_document_snapshot(args.spec_corpus)
                if document["document_id"] == args.spec_document_id
            ),
            None,
        )
        if spec_document is None:
            parser.error(f"Spec document not found: {args.spec_document_id}")
        if not args.clause and not args.section_heading:
            parser.error("Provide --clause or --section-heading")
        payload = build_spec_section_explain_payload(
            spec_document=spec_document,
            jira_documents=jira_documents,
            allowed_policies=set(args.policies),
            clause=args.clause,
            section_heading=args.section_heading,
            question=args.question,
            top_k=args.top_k,
            prompt_template=args.prompt_template,
            prompt_mode=args.llm_prompt_mode,
            llm_backend=_build_llm_backend_from_args(parser, args),
        )
        if args.output_answer_md:
            output_path = Path(args.output_answer_md)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(payload["answer"]["text"], encoding="utf-8")
            payload["output_answer_md"] = str(output_path)
        return _print_json(payload)
    if args.command == "retrieval-consume":
        _validate_retrieval_consumption_source(parser, args)
        documents = _load_retrieval_consumption_documents_quietly(parser, args)
        payload = build_retrieval_consumption_payload(
            documents=documents,
            question=args.question,
            allowed_policies=set(args.policies),
            top_k=args.top_k,
            prompt_template=args.prompt_template,
            prompt_mode=args.llm_prompt_mode,
            llm_backend=_build_llm_backend_from_args(parser, args),
        )
        if args.output_answer_md:
            output_path = Path(args.output_answer_md)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(payload["answer"]["text"], encoding="utf-8")
            payload["output_answer_md"] = str(output_path)
        if args.output_json:
            payload["output_json"] = _write_json_output(args.output_json, payload)
        return _print_json(payload)
    if args.command == "sync-export":
        if args.profile:
            profile_errors = validate_multi_sync_profile(load_json_file(args.profile))
            if profile_errors:
                parser.error("; ".join(profile_errors))
        profile = build_multi_sync_profile(args)
        if not profile["snapshot_dir"]:
            parser.error("snapshot dir is required via --snapshot-dir or --profile")
        active_source_configs = configured_sources(profile)
        if not active_source_configs:
            parser.error("At least one source is required for sync-export")
        for config in active_source_configs:
            _validate_prefixed_live_args(
                parser,
                args=args,
                live=config["live"],
                base_url=config.get("base_url"),
                page_size=config["page_size"],
                source_name=config["source_name"],
            )
            _validate_profile_source_config(parser, source_name=config["source_name"], config=config)
        payload = run_sync_export(profile, export_scope=args.export_scope)
        payload["profile"] = args.profile
        if args.output_md:
            output_path = Path(args.output_md)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(documents_to_markdown(payload["documents"]), encoding="utf-8")
            payload["output_md"] = str(output_path)
        if args.output_md_dir:
            output_root = Path(args.output_md_dir)
            output_root.mkdir(parents=True, exist_ok=True)
            write_documents_markdown_tree(payload["documents"], output_root)
            payload["output_md_dir"] = str(output_root)
        if args.output_page_index:
            output_path = Path(args.output_page_index)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(
                json.dumps({"entries": build_page_index(payload["documents"])}, indent=2, ensure_ascii=False, default=_json_default),
                encoding="utf-8",
            )
            payload["output_page_index"] = str(output_path)
        return _print_json(payload)
    if args.command == "confluence-wiki-demo":
        documents = _load_confluence_documents_from_args(parser, args)
        llm_backend = _build_llm_backend_from_args(parser, args)
        page_payloads = [
            build_confluence_wiki_summary_payload(
                document=document,
                prompt_template=args.prompt_template,
                prompt_mode=args.llm_prompt_mode,
                llm_backend=llm_backend,
            )
            for document in documents
        ]
        site = render_confluence_static_wiki(page_payloads=page_payloads, output_dir=args.output_dir)
        return _print_json(
            {
                "output_dir": site["output_dir"],
                "index_html": site["index_html"],
                "page_count": len(page_payloads),
                "pages": page_payloads,
            }
        )
    if args.command == "build-spec-corpus":
        return _print_json(
            _build_spec_corpus_from_pdf(
                spec_pdf=args.spec_pdf,
                output_dir=args.output_dir,
                preferred_parser=args.preferred_parser,
                mineru_python_exe=args.mineru_python_exe,
            )
        )
    if args.command == "demo-orchestrate":
        if not args.clause and not args.section_heading:
            parser.error("Provide --clause or --section-heading")
        if args.profile:
            profile_errors = validate_multi_sync_profile(load_json_file(args.profile))
            if profile_errors:
                parser.error("; ".join(profile_errors))
        profile = build_multi_sync_profile(args)
        if not profile["snapshot_dir"]:
            parser.error("snapshot dir is required via --snapshot-dir or --profile")
        jira_config, confluence_config = profile["sources"]
        _validate_prefixed_live_args(
            parser,
            args=args,
            live=jira_config["live"],
            base_url=jira_config.get("base_url"),
            page_size=jira_config["page_size"],
            source_name="jira",
        )
        _validate_prefixed_live_args(
            parser,
            args=args,
            live=confluence_config["live"],
            base_url=confluence_config.get("base_url"),
            page_size=confluence_config["page_size"],
            source_name="confluence",
        )
        _validate_profile_source_config(parser, source_name="jira", config=jira_config)
        _validate_profile_source_config(parser, source_name="confluence", config=confluence_config)
        if not jira_config["live"] and not jira_config.get("path"):
            parser.error("Jira source is required via --jira-path, --jira-live, or --profile")
        if not confluence_config["live"] and not confluence_config.get("path"):
            parser.error("Confluence source is required via --confluence-path, --confluence-live, or --profile")

        sync_payload = run_sync_export(profile, export_scope="incoming")
        jira_documents = [document for document in sync_payload["documents"] if document["source_type"] == "jira"]
        confluence_documents = [document for document in sync_payload["documents"] if document["source_type"] == "confluence"]
        llm_backend = _build_llm_backend_from_args(parser, args)
        output_root = Path(args.output_dir)
        wiki_output_dir = output_root / "wiki"
        jira_daily_path = output_root / "jira-daily.md"
        spec_section_path = output_root / "spec-section.md"

        report = build_jira_pm_daily_report(
            jira_documents,
            reference_date=args.reference_date,
            prompt_mode=args.llm_prompt_mode,
            llm_backend=llm_backend,
        )
        spec_document = next(
            (
                document
                for document in load_document_snapshot(args.spec_corpus)
                if document["document_id"] == args.spec_document_id
            ),
            None,
        )
        if spec_document is None:
            parser.error(f"Spec document not found: {args.spec_document_id}")
        spec_payload = build_spec_section_explain_payload(
            spec_document=spec_document,
            jira_documents=jira_documents,
            allowed_policies=set(args.policies),
            clause=args.clause,
            section_heading=args.section_heading,
            prompt_mode=args.llm_prompt_mode,
            llm_backend=llm_backend,
        )
        page_payloads = [
            build_confluence_wiki_summary_payload(
                document=document,
                prompt_mode=args.llm_prompt_mode,
                llm_backend=llm_backend,
            )
            for document in confluence_documents
        ]
        site = render_confluence_static_wiki(page_payloads=page_payloads, output_dir=wiki_output_dir)
        report_text = report.get("answer", {}).get("text") or report["markdown"]
        spec_text = spec_payload["answer"]["text"]
        _write_text_output(jira_daily_path, report_text)
        _write_text_output(spec_section_path, spec_text)
        return _print_json(
            {
                "output_dir": str(output_root),
                "snapshot_dir": sync_payload["snapshot_dir"],
                "report_profile": report["report_profile"],
                "jira_daily_md": str(jira_daily_path),
                "spec_section_md": str(spec_section_path),
                "wiki_dir": site["output_dir"],
                "index_html": site["index_html"],
                "page_count": len(page_payloads),
                "updated_issue_ids": report["updated_issue_ids"],
                "stale_issue_ids": report["stale_issue_ids"],
                "section": spec_payload["section"],
            }
        )
    if args.command == "build-wiki-site":
        if args.profile:
            profile_errors = validate_multi_sync_profile(load_json_file(args.profile))
            if profile_errors:
                parser.error("; ".join(profile_errors))
        profile = build_multi_sync_profile(args)
        if not profile["snapshot_dir"]:
            parser.error("snapshot dir is required via --snapshot-dir or --profile")
        jira_config, confluence_config = profile["sources"]
        _validate_prefixed_live_args(
            parser,
            args=args,
            live=jira_config["live"],
            base_url=jira_config.get("base_url"),
            page_size=jira_config["page_size"],
            source_name="jira",
        )
        _validate_prefixed_live_args(
            parser,
            args=args,
            live=confluence_config["live"],
            base_url=confluence_config.get("base_url"),
            page_size=confluence_config["page_size"],
            source_name="confluence",
        )
        _validate_profile_source_config(parser, source_name="jira", config=jira_config)
        _validate_profile_source_config(parser, source_name="confluence", config=confluence_config)
        if not jira_config["live"] and not jira_config.get("path"):
            parser.error("Jira source is required via --jira-path, --jira-live, or --profile")
        if not confluence_config["live"] and not confluence_config.get("path"):
            parser.error("Confluence source is required via --confluence-path, --confluence-live, or --profile")

        output_root = Path(args.output_dir)
        export_root = output_root / "export"
        wiki_output_root = output_root / "wiki_site"
        llm_backend = _build_llm_backend_from_args(parser, args)

        spec_corpus_path = args.spec_corpus
        if args.spec_pdf:
            spec_build_root = output_root / "spec_build"
            spec_build_report = _build_spec_corpus_from_pdf(
                spec_pdf=args.spec_pdf,
                output_dir=spec_build_root,
                preferred_parser=args.preferred_parser,
                mineru_python_exe=args.mineru_python_exe,
            )
            spec_corpus_path = spec_build_report["spec_corpus_json"]
            if not args.spec_document_id:
                args.spec_document_id = spec_build_report["document_id"]

        if not spec_corpus_path:
            parser.error("Provide --spec-corpus or --spec-pdf")
        spec_documents = load_document_snapshot(spec_corpus_path)
        if not spec_documents:
            parser.error("Spec corpus is empty")
        spec_document = next(
            (
                document
                for document in spec_documents
                if not args.spec_document_id or document["document_id"] == args.spec_document_id
            ),
            None,
        )
        if spec_document is None:
            parser.error(f"Spec document not found: {args.spec_document_id}")

        if not args.clause and not args.section_heading:
            first_section = (spec_document.get("structure", {}).get("sections") or [None])[0]
            if not first_section:
                parser.error("Provide --clause or --section-heading, or ensure the spec has at least one section")
            if first_section.get("clause"):
                args.clause = str(first_section["clause"])
            else:
                args.section_heading = str(first_section.get("heading") or "")

        sync_payload = run_sync_export(profile, export_scope="incoming")
        jira_documents = [document for document in sync_payload["documents"] if document["source_type"] == "jira"]
        confluence_documents = [document for document in sync_payload["documents"] if document["source_type"] == "confluence"]
        combined_documents = [*sync_payload["documents"], *spec_documents]

        export_report = build_export_package(
            export_root=export_root,
            documents=combined_documents,
            export_mode="wiki-demo",
            source_snapshot=sync_payload["snapshot_dir"],
        )

        report = build_jira_pm_daily_report(
            jira_documents,
            reference_date=args.reference_date,
            prompt_mode=args.llm_prompt_mode,
            llm_backend=llm_backend,
        )
        spec_payload = build_spec_section_explain_payload(
            spec_document=spec_document,
            jira_documents=jira_documents,
            allowed_policies=set(args.policies),
            clause=args.clause,
            section_heading=args.section_heading,
            prompt_mode=args.llm_prompt_mode,
            llm_backend=llm_backend,
        )

        overview_body = "\n".join(
            [
                f"- Jira documents: {len(jira_documents)}",
                f"- Confluence documents: {len(confluence_documents)}",
                f"- Spec documents: {len(spec_documents)}",
                f"- Snapshot dir: `{sync_payload['snapshot_dir']}`",
                "",
                "## Jira Daily Report",
                "",
                report.get("answer", {}).get("text") or report["markdown"],
                "",
                "## Spec Section Explanation",
                "",
                spec_payload["answer"]["text"],
            ]
        ).strip()
        analysis_pages = [
            {
                "slug": "jira-daily.md",
                "title": "Jira Daily Report",
                "body": report.get("answer", {}).get("text") or report["markdown"],
                "derived_from": [document["document_id"] for document in jira_documents],
            },
            {
                "slug": "spec-section.md",
                "title": "Spec Section Explanation",
                "body": spec_payload["answer"]["text"],
                "derived_from": [spec_document["document_id"], *[document["document_id"] for document in jira_documents]],
            },
            {
                "slug": "demo-overview.md",
                "title": "Three-Source Demo Overview",
                "body": overview_body,
                "derived_from": [document["document_id"] for document in combined_documents],
            },
        ]
        site_report = build_wiki_site(
            export_root=export_root,
            output_root=wiki_output_root,
            site_title=args.site_title,
            analysis_pages=analysis_pages,
        )
        return _print_json(
            {
                "output_dir": str(output_root),
                "snapshot_dir": sync_payload["snapshot_dir"],
                "export": export_report,
                "wiki_site": site_report,
                "report_profile": report["report_profile"],
                "updated_issue_ids": report["updated_issue_ids"],
                "stale_issue_ids": report["stale_issue_ids"],
                "section": spec_payload["section"],
                "source_counts": {
                    "jira": len(jira_documents),
                    "confluence": len(confluence_documents),
                    "spec": len(spec_documents),
                },
            }
        )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.portal.portal_state import build_portal_state, write_portal_state
from services.analysis.llm_backends import build_llm_backend
from services.workspace import (
    add_workspace_profile,
    add_workspace_selector,
    add_workspace_source,
    build_workspace,
    build_workspace_site,
    compile_workspace_wiki,
    configure_workspace_source,
    control_workspace_run,
    deep_analyze_issue,
    export_workspace,
    fetch_workspace_source,
    fetch_workspace_spec,
    ingest_spec_asset,
    inbox_workspace,
    init_workspace,
    inspect_workspace_run,
    list_workspace_profiles,
    list_workspace_selectors,
    list_workspace_sources,
    lint_workspace,
    list_workspace_runs,
    load_workspace_run_artifact,
    publish_workspace_wiki,
    query_workspace,
    rebuild_workspace,
    refresh_workspace,
    refresh_workspace_source,
    reindex_workspace,
    route_workspace,
    run_workspace_analysis,
    set_workspace_source_credential,
    set_workspace_source_enabled,
    smoke_deep_analysis_workspace,
    show_workspace_profile,
    show_workspace_selector,
    show_workspace_source,
    status_workspace,
    submit_workspace_run_to_prefect,
    sync_workspace_run_prefect_state,
    test_workspace_source,
    update_workspace_source_defaults,
    update_workspace_profile,
    validate_workspace_profile,
    watch_workspace,
)


def _print_json(payload: dict | list) -> int:
    text = json.dumps(payload, indent=2, ensure_ascii=False)
    try:
        print(text)
    except UnicodeEncodeError:
        sys.stdout.buffer.write((text + "\n").encode("utf-8", errors="replace"))
    return 0


def _write_text_output(path: str | Path, text: str) -> str:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(text, encoding="utf-8")
    return str(output_path)


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


def _parse_profile_inputs(parser: argparse.ArgumentParser, values: list[str] | None) -> dict[str, dict] | None:
    if values is None:
        return None
    bindings: dict[str, dict] = {}
    for value in values:
        try:
            input_name, remainder = value.split("=", 1)
            source_name, selector_profile = remainder.split(":", 1)
        except ValueError:
            parser.error(f"Invalid --input value: {value}. Expected NAME=SOURCE:SELECTOR.")
        input_name = input_name.strip()
        source_name = source_name.strip()
        selector_profile = selector_profile.strip()
        if not input_name or not source_name or not selector_profile:
            parser.error(f"Invalid --input value: {value}. Expected NAME=SOURCE:SELECTOR.")
        bindings[input_name] = {
            "source": source_name,
            "selector_profile": selector_profile,
        }
    return bindings


def _parse_csv_list(value: str | None) -> list[str] | None:
    if value is None:
        return None
    items = [item.strip() for item in value.split(",")]
    return [item for item in items if item]


def main() -> int:
    parser = argparse.ArgumentParser(description="Workspace-first CLI for progressive Jira/Confluence ingestion.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init")
    init_parser.add_argument("workspace")

    fetch_parser = subparsers.add_parser("fetch")
    fetch_parser.add_argument("workspace")
    fetch_parser.add_argument("spec")

    source_parser = subparsers.add_parser("source")
    source_subparsers = source_parser.add_subparsers(dest="source_command", required=True)
    source_add = source_subparsers.add_parser("add")
    source_add.add_argument("workspace")
    source_add.add_argument("name")
    source_add.add_argument("--connector-type", required=True)
    source_add.add_argument("--base-url")
    source_add.add_argument("--path")
    source_add.add_argument("--credential-ref")
    source_add.add_argument("--policy", action="append")
    source_add.add_argument("--include-comments", action="store_true", default=True)
    source_add.add_argument("--include-attachments", action="store_true", default=True)
    source_list = source_subparsers.add_parser("list")
    source_list.add_argument("workspace")
    source_show = source_subparsers.add_parser("show")
    source_show.add_argument("workspace")
    source_show.add_argument("name")
    source_configure = source_subparsers.add_parser("configure")
    source_configure.add_argument("workspace")
    source_configure.add_argument("name")
    source_configure.add_argument("--base-url")
    source_configure.add_argument("--auth-mode")
    source_configure.add_argument("--path")
    source_credential = source_subparsers.add_parser("set-credential")
    source_credential.add_argument("workspace")
    source_credential.add_argument("name")
    source_credential.add_argument("--credential-ref")
    source_defaults = source_subparsers.add_parser("defaults")
    source_defaults.add_argument("workspace")
    source_defaults.add_argument("name")
    source_defaults.add_argument("--include-comments", action="store_true")
    source_defaults.add_argument("--no-include-comments", action="store_true")
    source_defaults.add_argument("--include-attachments", action="store_true")
    source_defaults.add_argument("--no-include-attachments", action="store_true")
    source_defaults.add_argument("--include-image-metadata", action="store_true")
    source_defaults.add_argument("--no-include-image-metadata", action="store_true")
    source_defaults.add_argument("--download-images", action="store_true")
    source_defaults.add_argument("--no-download-images", action="store_true")
    source_defaults.add_argument("--refresh-freq-minutes", type=int)
    source_defaults.add_argument("--prune-freq-hours", type=int)
    source_defaults.add_argument("--page-size", type=int)
    source_test = source_subparsers.add_parser("test")
    source_test.add_argument("workspace")
    source_test.add_argument("name")
    source_test.add_argument("--selector-profile")
    source_test.add_argument("--skip-credential-check", action="store_true")
    source_enable = source_subparsers.add_parser("enable")
    source_enable.add_argument("workspace")
    source_enable.add_argument("name")
    source_disable = source_subparsers.add_parser("disable")
    source_disable.add_argument("workspace")
    source_disable.add_argument("name")
    source_refresh = source_subparsers.add_parser("refresh")
    source_refresh.add_argument("workspace")
    source_refresh.add_argument("name")
    source_refresh.add_argument("--selector-profile", required=True)

    selector_parser = subparsers.add_parser("selector")
    selector_subparsers = selector_parser.add_subparsers(dest="selector_command", required=True)
    selector_add = selector_subparsers.add_parser("add")
    selector_add.add_argument("workspace")
    selector_add.add_argument("name")
    selector_add.add_argument("--source", required=True)
    selector_add.add_argument("--type", required=True)
    selector_add.add_argument("--issue-key")
    selector_add.add_argument("--project-key")
    selector_add.add_argument("--project-keys")
    selector_add.add_argument("--issue-type")
    selector_add.add_argument("--status")
    selector_add.add_argument("--label")
    selector_add.add_argument("--updated-from")
    selector_add.add_argument("--updated-to")
    selector_add.add_argument("--page-id")
    selector_add.add_argument("--root-page-id")
    selector_add.add_argument("--max-depth", type=int)
    selector_add.add_argument("--space-key")
    selector_add.add_argument("--modified-from")
    selector_add.add_argument("--modified-to")
    selector_add.add_argument("--ancestor-id")
    selector_add.add_argument("--title")
    selector_add.add_argument("--page-ids")
    selector_list = selector_subparsers.add_parser("list")
    selector_list.add_argument("workspace")
    selector_show = selector_subparsers.add_parser("show")
    selector_show.add_argument("workspace")
    selector_show.add_argument("name")

    profile_parser = subparsers.add_parser("profile")
    profile_subparsers = profile_parser.add_subparsers(dest="profile_command", required=True)
    profile_add = profile_subparsers.add_parser("add")
    profile_add.add_argument("workspace")
    profile_add.add_argument("name")
    profile_add.add_argument("--input", action="append")
    profile_add.add_argument("--spec-asset", action="append")
    profile_add.add_argument("--top-k", type=int, default=5)
    profile_add.add_argument("--policy", action="append")
    profile_add.add_argument(
        "--llm-backend",
        choices=["none", "mock", "ollama", "openai-compatible"],
        default="none",
    )
    profile_add.add_argument("--llm-model")
    profile_add.add_argument(
        "--llm-prompt-mode",
        choices=["strict", "balanced", "exploratory"],
        default="strict",
    )
    profile_list = profile_subparsers.add_parser("list")
    profile_list.add_argument("workspace")
    profile_show = profile_subparsers.add_parser("show")
    profile_show.add_argument("workspace")
    profile_show.add_argument("name")
    profile_update = profile_subparsers.add_parser("update")
    profile_update.add_argument("workspace")
    profile_update.add_argument("name")
    profile_update.add_argument("--input", action="append")
    profile_update.add_argument("--spec-asset", action="append")
    profile_update.add_argument("--top-k", type=int)
    profile_update.add_argument("--policy", action="append")
    profile_update.add_argument(
        "--llm-backend",
        choices=["none", "mock", "ollama", "openai-compatible"],
    )
    profile_update.add_argument("--llm-model")
    profile_update.add_argument(
        "--llm-prompt-mode",
        choices=["strict", "balanced", "exploratory"],
    )
    profile_validate = profile_subparsers.add_parser("validate")
    profile_validate.add_argument("workspace")
    profile_validate.add_argument("name")

    fetch_source_parser = subparsers.add_parser("fetch-source")
    fetch_source_parser.add_argument("workspace")
    fetch_source_parser.add_argument("--source", required=True)
    fetch_source_parser.add_argument("--selector-profile", required=True)

    refresh_parser = subparsers.add_parser("refresh")
    refresh_parser.add_argument("workspace")

    build_parser = subparsers.add_parser("build")
    build_parser.add_argument("workspace")

    rebuild_parser = subparsers.add_parser("rebuild")
    rebuild_parser.add_argument("workspace")
    rebuild_parser.add_argument("--from", dest="from_layer", default="raw")
    rebuild_parser.add_argument("--source")

    reindex_parser = subparsers.add_parser("reindex")
    reindex_parser.add_argument("workspace")
    reindex_parser.add_argument("--index-name", default="pageindex_v1")

    export_parser = subparsers.add_parser("export")
    export_parser.add_argument("workspace")

    spec_asset_parser = subparsers.add_parser("ingest-spec-asset")
    spec_asset_parser.add_argument("workspace")
    spec_asset_parser.add_argument("--spec-pdf", required=True)
    spec_asset_parser.add_argument("--asset-id")
    spec_asset_parser.add_argument("--display-name")
    spec_asset_parser.add_argument("--preferred-parser", choices=["auto", "mineru", "pypdf"], default="auto")
    spec_asset_parser.add_argument("--mineru-python-exe")

    query_parser = subparsers.add_parser("query")
    query_parser.add_argument("workspace")
    query_parser.add_argument("question")
    query_parser.add_argument("--top-k", type=int, default=5)
    query_parser.add_argument("--policies", nargs="*", default=["team:ssd", "public"])
    query_parser.add_argument("--prompt-template")
    query_parser.add_argument("--output-answer-md")
    _add_llm_backend_args(query_parser)

    status_parser = subparsers.add_parser("status")
    status_parser.add_argument("workspace")

    portal_state_parser = subparsers.add_parser("portal-state")
    portal_state_parser.add_argument("workspace")
    portal_state_parser.add_argument("--output", default="apps/portal/portal_state.json")
    portal_state_parser.add_argument("--query", default="nvme flush")
    portal_state_parser.add_argument("--corpus", default="fixtures/retrieval/pageindex_corpus.json")
    portal_state_parser.add_argument("--dataset", default="eval/gold_queries.yaml")
    portal_state_parser.add_argument("--policies", nargs="*", default=["team:ssd", "public"])

    runs_parser = subparsers.add_parser("runs")
    runs_parser.add_argument("workspace")

    run_detail_parser = subparsers.add_parser("run-detail")
    run_detail_parser.add_argument("workspace")
    run_detail_parser.add_argument("run")

    run_artifact_parser = subparsers.add_parser("run-artifact")
    run_artifact_parser.add_argument("workspace")
    run_artifact_parser.add_argument("run")
    run_artifact_parser.add_argument("artifact_type")

    inbox_parser = subparsers.add_parser("inbox")
    inbox_parser.add_argument("workspace")

    route_parser = subparsers.add_parser("route")
    route_parser.add_argument("workspace")
    route_parser.add_argument("--manifest", required=True)

    compile_wiki_parser = subparsers.add_parser("compile-wiki")
    compile_wiki_parser.add_argument("workspace")
    _add_llm_backend_args(compile_wiki_parser)

    build_site_parser = subparsers.add_parser("build-site")
    build_site_parser.add_argument("workspace")
    build_site_parser.add_argument("--renderer", choices=["vitepress"], default="vitepress")

    publish_wiki_parser = subparsers.add_parser("publish-wiki")
    publish_wiki_parser.add_argument("workspace")
    publish_wiki_parser.add_argument("--manifest", required=True)
    publish_wiki_parser.add_argument("--renderer", choices=["vitepress"], default="vitepress")
    publish_wiki_parser.add_argument("--verify-site-build", action="store_true")
    publish_wiki_parser.add_argument("--site-build-command", action="append")
    _add_llm_backend_args(publish_wiki_parser)

    lint_parser = subparsers.add_parser("lint")
    lint_parser.add_argument("workspace")

    watch_parser = subparsers.add_parser("watch")
    watch_parser.add_argument("workspace")
    watch_parser.add_argument("--interval-seconds", type=float, default=2.0)
    watch_parser.add_argument("--max-cycles", type=int)
    watch_parser.add_argument("--run-once", action="store_true")

    deep_analyze_parser = subparsers.add_parser("deep-analyze")
    deep_analyze_parser.add_argument("workspace")
    deep_analyze_parser.add_argument("issue_key")
    deep_analyze_parser.add_argument("--policies", nargs="*", default=["team:ssd", "public"])
    deep_analyze_parser.add_argument("--top-k", type=int, default=5)
    deep_analyze_parser.add_argument("--output-answer-md")
    _add_llm_backend_args(deep_analyze_parser)

    run_analysis_parser = subparsers.add_parser("run-analysis")
    run_analysis_parser.add_argument("workspace")
    run_analysis_parser.add_argument("--profile", required=True)
    run_analysis_parser.add_argument("--issue-key", required=True)
    run_analysis_parser.add_argument("--use-existing-snapshot", action="store_true")
    _add_llm_backend_args(run_analysis_parser)

    analyze_jira_parser = subparsers.add_parser("analyze-jira")
    analyze_jira_parser.add_argument("workspace")
    analyze_jira_parser.add_argument("--profile", required=True)
    analyze_jira_parser.add_argument("--issue-key", required=True)
    analyze_jira_parser.add_argument("--use-existing-snapshot", action="store_true")
    _add_llm_backend_args(analyze_jira_parser)

    rerun_analysis_parser = subparsers.add_parser("rerun-analysis")
    rerun_analysis_parser.add_argument("workspace")
    rerun_analysis_parser.add_argument("--profile", required=True)
    rerun_analysis_parser.add_argument("--issue-key", required=True)
    rerun_analysis_parser.add_argument("--use-existing-snapshot", action="store_true", default=True)
    _add_llm_backend_args(rerun_analysis_parser)

    control_run_parser = subparsers.add_parser("control-run")
    control_run_parser.add_argument("workspace")
    control_run_parser.add_argument("run")
    control_run_parser.add_argument("--action", choices=["stop", "resume", "rerun", "rerun-section"], required=True)
    control_run_parser.add_argument("--requested-by", default="workspace-operator")
    control_run_parser.add_argument("--step-name", help="Current step for stop, or section name for rerun-section.")
    control_run_parser.add_argument("--reason")
    control_run_parser.add_argument("--execute", action="store_true", help="Execute rerun-section immediately.")

    sync_adapter_parser = subparsers.add_parser("sync-prefect-state")
    sync_adapter_parser.add_argument("workspace")
    sync_adapter_parser.add_argument("run")
    sync_adapter_parser.add_argument("--prefect-state", required=True)
    sync_adapter_parser.add_argument("--flow-run-id")
    sync_adapter_parser.add_argument("--flow-name", default="jira_deep_analysis")
    sync_adapter_parser.add_argument("--deployment-name")
    sync_adapter_parser.add_argument("--requested-by", default="workspace-operator")
    sync_adapter_parser.add_argument("--error-message")

    submit_prefect_parser = subparsers.add_parser("submit-prefect-run")
    submit_prefect_parser.add_argument("workspace")
    submit_prefect_parser.add_argument("run")
    submit_prefect_parser.add_argument("--deployment-name", required=True)
    submit_prefect_parser.add_argument("--flow-name", default="jira_deep_analysis")
    submit_prefect_parser.add_argument("--requested-by", default="workspace-operator")
    submit_prefect_parser.add_argument("--parameters-json")
    submit_prefect_parser.add_argument("--timeout-seconds", type=float, default=0)
    submit_prefect_parser.add_argument("--flow-run-name")
    submit_prefect_parser.add_argument("--tag", action="append")
    submit_prefect_parser.add_argument("--idempotency-key")
    submit_prefect_parser.add_argument("--work-queue-name")
    submit_prefect_parser.add_argument("--job-variables-json")

    smoke_parser = subparsers.add_parser("smoke-deep-analysis")
    smoke_parser.add_argument("workspace")
    smoke_parser.add_argument("--profile")
    smoke_parser.add_argument("--jira-spec")
    smoke_parser.add_argument("--confluence-spec")
    smoke_parser.add_argument("--issue-key", required=True)
    smoke_parser.add_argument("--spec-pdf")
    smoke_parser.add_argument("--spec-asset-id")
    smoke_parser.add_argument("--spec-display-name")
    smoke_parser.add_argument("--preferred-parser", choices=["auto", "mineru", "pypdf"], default="auto")
    smoke_parser.add_argument("--mineru-python-exe")
    smoke_parser.add_argument("--top-k", type=int, default=5)
    smoke_parser.add_argument("--policies", nargs="*", default=["team:ssd", "public"])
    smoke_parser.add_argument("--portal-state-output")
    _add_llm_backend_args(smoke_parser)

    showcase_parser = subparsers.add_parser("showcase-workbench")
    showcase_parser.add_argument("workspace")
    showcase_parser.add_argument("--jira-spec", required=True)
    showcase_parser.add_argument("--confluence-spec", required=True)
    showcase_parser.add_argument("--issue-key", required=True)
    showcase_parser.add_argument("--spec-pdf")
    showcase_parser.add_argument("--spec-asset-id")
    showcase_parser.add_argument("--spec-display-name")
    showcase_parser.add_argument("--preferred-parser", choices=["auto", "mineru", "pypdf"], default="auto")
    showcase_parser.add_argument("--mineru-python-exe")
    showcase_parser.add_argument("--top-k", type=int, default=5)
    showcase_parser.add_argument("--policies", nargs="*", default=["team:ssd", "public"])
    showcase_parser.add_argument("--portal-state-output")
    _add_llm_backend_args(showcase_parser)

    args = parser.parse_args()

    if args.command == "init":
        return _print_json(init_workspace(args.workspace))
    if args.command == "fetch":
        return _print_json(fetch_workspace_spec(args.workspace, args.spec))
    if args.command == "source":
        try:
            if args.source_command == "add":
                return _print_json(
                    add_workspace_source(
                        args.workspace,
                        args.name,
                        connector_type=args.connector_type,
                        base_url=args.base_url,
                        path=args.path,
                        credential_ref=args.credential_ref,
                        policies=args.policy,
                        include_comments=args.include_comments,
                        include_attachments=args.include_attachments,
                    )
                )
            if args.source_command == "list":
                return _print_json(list_workspace_sources(args.workspace))
            if args.source_command == "show":
                return _print_json(show_workspace_source(args.workspace, args.name))
            if args.source_command == "configure":
                return _print_json(
                    configure_workspace_source(
                        args.workspace,
                        args.name,
                        base_url=args.base_url,
                        auth_mode=args.auth_mode,
                        path=args.path,
                    )
                )
            if args.source_command == "set-credential":
                return _print_json(
                    set_workspace_source_credential(
                        args.workspace,
                        args.name,
                        credential_ref=args.credential_ref,
                    )
                )
            if args.source_command == "defaults":
                include_comments = True if args.include_comments else False if args.no_include_comments else None
                include_attachments = True if args.include_attachments else False if args.no_include_attachments else None
                include_image_metadata = (
                    True if args.include_image_metadata else False if args.no_include_image_metadata else None
                )
                download_images = True if args.download_images else False if args.no_download_images else None
                return _print_json(
                    update_workspace_source_defaults(
                        args.workspace,
                        args.name,
                        include_comments=include_comments,
                        include_attachments=include_attachments,
                        include_image_metadata=include_image_metadata,
                        download_images=download_images,
                        refresh_freq_minutes=args.refresh_freq_minutes,
                        prune_freq_hours=args.prune_freq_hours,
                        page_size=args.page_size,
                    )
                )
            if args.source_command == "test":
                return _print_json(
                    test_workspace_source(
                        args.workspace,
                        args.name,
                        selector_profile=args.selector_profile,
                        skip_credential_check=args.skip_credential_check,
                    )
                )
            if args.source_command == "enable":
                return _print_json(set_workspace_source_enabled(args.workspace, args.name, enabled=True))
            if args.source_command == "disable":
                return _print_json(set_workspace_source_enabled(args.workspace, args.name, enabled=False))
            if args.source_command == "refresh":
                return _print_json(
                    refresh_workspace_source(
                        args.workspace,
                        args.name,
                        selector_profile=args.selector_profile,
                    )
                )
        except ValueError as error:
            parser.error(str(error))
    if args.command == "selector":
        try:
            if args.selector_command == "add":
                return _print_json(
                    add_workspace_selector(
                        args.workspace,
                        args.name,
                        source=args.source,
                        selector_type=args.type,
                        issue_key=args.issue_key,
                        project_key=args.project_key,
                        project_keys=_parse_csv_list(args.project_keys),
                        issue_type=args.issue_type,
                        status=args.status,
                        label=args.label,
                        updated_from=args.updated_from,
                        updated_to=args.updated_to,
                        page_id=args.page_id,
                        root_page_id=args.root_page_id,
                        max_depth=args.max_depth,
                        space_key=args.space_key,
                        modified_from=args.modified_from,
                        modified_to=args.modified_to,
                        ancestor_id=args.ancestor_id,
                        title=args.title,
                        page_ids=_parse_csv_list(args.page_ids),
                    )
                )
            if args.selector_command == "list":
                return _print_json(list_workspace_selectors(args.workspace))
            if args.selector_command == "show":
                return _print_json(show_workspace_selector(args.workspace, args.name))
        except ValueError as error:
            parser.error(str(error))
    if args.command == "profile":
        try:
            if args.profile_command == "add":
                return _print_json(
                    add_workspace_profile(
                        args.workspace,
                        args.name,
                        input_bindings=_parse_profile_inputs(parser, args.input),
                        spec_asset_ids=args.spec_asset,
                        top_k=args.top_k,
                        policies=args.policy,
                        llm_backend=args.llm_backend,
                        llm_model=args.llm_model,
                        llm_prompt_mode=args.llm_prompt_mode,
                    )
                )
            if args.profile_command == "list":
                return _print_json(list_workspace_profiles(args.workspace))
            if args.profile_command == "show":
                return _print_json(show_workspace_profile(args.workspace, args.name))
            if args.profile_command == "update":
                return _print_json(
                    update_workspace_profile(
                        args.workspace,
                        args.name,
                        input_bindings=_parse_profile_inputs(parser, args.input),
                        replace_inputs=args.input is not None,
                        spec_asset_ids=args.spec_asset,
                        top_k=args.top_k,
                        policies=args.policy,
                        llm_backend=args.llm_backend,
                        llm_model=args.llm_model,
                        llm_prompt_mode=args.llm_prompt_mode,
                    )
                )
            if args.profile_command == "validate":
                return _print_json(validate_workspace_profile(args.workspace, args.name))
        except ValueError as error:
            parser.error(str(error))
    if args.command == "fetch-source":
        try:
            return _print_json(
                fetch_workspace_source(
                    args.workspace,
                    source_name=args.source,
                    selector_profile=args.selector_profile,
                )
            )
        except ValueError as error:
            parser.error(str(error))
    if args.command == "refresh":
        try:
            return _print_json(refresh_workspace(args.workspace))
        except ValueError as error:
            parser.error(str(error))
    if args.command == "build":
        return _print_json(build_workspace(args.workspace))
    if args.command == "rebuild":
        try:
            return _print_json(
                rebuild_workspace(
                    args.workspace,
                    from_layer=args.from_layer,
                    source_name=args.source,
                )
            )
        except ValueError as error:
            parser.error(str(error))
    if args.command == "reindex":
        try:
            return _print_json(reindex_workspace(args.workspace, index_name=args.index_name))
        except ValueError as error:
            parser.error(str(error))
    if args.command == "export":
        return _print_json(export_workspace(args.workspace))
    if args.command == "ingest-spec-asset":
        return _print_json(
            ingest_spec_asset(
                args.workspace,
                spec_pdf=args.spec_pdf,
                asset_id=args.asset_id,
                display_name=args.display_name,
                preferred_parser=args.preferred_parser,
                mineru_python_exe=args.mineru_python_exe,
            )
        )
    if args.command == "query":
        payload = query_workspace(
            args.workspace,
            question=args.question,
            top_k=args.top_k,
            policies=args.policies,
            prompt_template=args.prompt_template,
            prompt_mode=args.llm_prompt_mode,
            llm_backend=_build_llm_backend_from_args(parser, args),
        )
        if args.output_answer_md:
            payload["output_answer_md"] = _write_text_output(args.output_answer_md, payload["answer"]["text"])
        return _print_json(payload)
    if args.command == "status":
        return _print_json(status_workspace(args.workspace))
    if args.command == "portal-state":
        policies = set(args.policies)
        output_path = write_portal_state(
            args.output,
            corpus_path=args.corpus,
            dataset_path=args.dataset,
            query=args.query,
            allowed_policies=policies,
            workspace_dir=args.workspace,
        )
        state = build_portal_state(
            corpus_path=args.corpus,
            dataset_path=args.dataset,
            query=args.query,
            allowed_policies=policies,
            workspace_dir=args.workspace,
        )
        return _print_json(
            {
                "portal_state_path": str(output_path),
                "task_count": len(state["task_workbench"]["tasks"]),
                "selected_task_id": state["task_workbench"]["selected_task_id"],
            }
        )
    if args.command == "runs":
        return _print_json(list_workspace_runs(args.workspace))
    if args.command == "run-detail":
        try:
            return _print_json(inspect_workspace_run(args.workspace, args.run))
        except ValueError as error:
            parser.error(str(error))
    if args.command == "run-artifact":
        try:
            return _print_json(load_workspace_run_artifact(args.workspace, args.run, args.artifact_type))
        except ValueError as error:
            parser.error(str(error))
    if args.command == "inbox":
        return _print_json(inbox_workspace(args.workspace))
    if args.command == "route":
        return _print_json(route_workspace(args.workspace, args.manifest))
    if args.command == "compile-wiki":
        return _print_json(
            compile_workspace_wiki(
                args.workspace,
                prompt_mode=args.llm_prompt_mode,
                llm_backend=_build_llm_backend_from_args(parser, args),
            )
        )
    if args.command == "build-site":
        return _print_json(
            build_workspace_site(
                args.workspace,
                renderer=args.renderer,
            )
        )
    if args.command == "publish-wiki":
        return _print_json(
            publish_workspace_wiki(
                args.workspace,
                manifest_path=args.manifest,
                renderer=args.renderer,
                prompt_mode=args.llm_prompt_mode,
                llm_backend=_build_llm_backend_from_args(parser, args),
                verify_site_build=args.verify_site_build,
                site_build_command=args.site_build_command,
            )
        )
    if args.command == "lint":
        return _print_json(lint_workspace(args.workspace))
    if args.command == "watch":
        return _print_json(
            watch_workspace(
                args.workspace,
                interval_seconds=args.interval_seconds,
                max_cycles=args.max_cycles,
                run_once=args.run_once,
            )
        )
    if args.command == "deep-analyze":
        try:
            payload = deep_analyze_issue(
                args.workspace,
                args.issue_key,
                policies=args.policies,
                top_k=args.top_k,
                prompt_mode=args.llm_prompt_mode,
                llm_backend=_build_llm_backend_from_args(parser, args),
            )
        except ValueError as error:
            parser.error(str(error))
        if args.output_answer_md:
            payload["output_answer_md"] = _write_text_output(args.output_answer_md, payload["answer"]["text"])
        return _print_json(payload)
    if args.command in {"run-analysis", "rerun-analysis", "analyze-jira"}:
        try:
            return _print_json(
                run_workspace_analysis(
                    args.workspace,
                    profile_name=args.profile,
                    issue_key=args.issue_key,
                    use_existing_snapshot=args.use_existing_snapshot,
                    llm_backend=_build_llm_backend_from_args(parser, args),
                )
            )
        except ValueError as error:
            parser.error(str(error))
    if args.command == "control-run":
        try:
            return _print_json(
                control_workspace_run(
                    args.workspace,
                    args.run,
                    action=args.action,
                    requested_by=args.requested_by,
                    step_name=args.step_name,
                    reason=args.reason,
                    execute=args.execute,
                )
            )
        except ValueError as error:
            parser.error(str(error))
    if args.command == "sync-prefect-state":
        try:
            return _print_json(
                sync_workspace_run_prefect_state(
                    args.workspace,
                    args.run,
                    prefect_state=args.prefect_state,
                    requested_by=args.requested_by,
                    flow_run_id=args.flow_run_id,
                    flow_name=args.flow_name,
                    deployment_name=args.deployment_name,
                    error={"message": args.error_message} if args.error_message else None,
                )
            )
        except ValueError as error:
            parser.error(str(error))
    if args.command == "submit-prefect-run":
        try:
            parameters = json.loads(args.parameters_json) if args.parameters_json else None
            job_variables = json.loads(args.job_variables_json) if args.job_variables_json else None
            return _print_json(
                submit_workspace_run_to_prefect(
                    args.workspace,
                    args.run,
                    deployment_name=args.deployment_name,
                    flow_name=args.flow_name,
                    requested_by=args.requested_by,
                    parameters=parameters,
                    timeout_seconds=args.timeout_seconds,
                    flow_run_name=args.flow_run_name,
                    tags=args.tag,
                    idempotency_key=args.idempotency_key,
                    work_queue_name=args.work_queue_name,
                    job_variables=job_variables,
                )
            )
        except (ValueError, RuntimeError) as error:
            parser.error(str(error))
    if args.command == "smoke-deep-analysis":
        if args.profile:
            try:
                payload = run_workspace_analysis(
                    args.workspace,
                    profile_name=args.profile,
                    issue_key=args.issue_key,
                    use_existing_snapshot=False,
                    llm_backend=_build_llm_backend_from_args(parser, args),
                )
            except ValueError as error:
                parser.error(str(error))
            portal_state_output = args.portal_state_output or str(Path(args.workspace) / "portal_state.json")
            write_portal_state(
                portal_state_output,
                query=args.issue_key,
                allowed_policies=set(payload["analysis"].get("allowed_policies", args.policies)),
                workspace_dir=args.workspace,
            )
            payload["portal_state_path"] = portal_state_output
            return _print_json(payload)
        if not args.jira_spec or not args.confluence_spec:
            parser.error("--jira-spec and --confluence-spec are required unless --profile is provided")
        try:
            payload = smoke_deep_analysis_workspace(
                args.workspace,
                jira_spec=args.jira_spec,
                confluence_spec=args.confluence_spec,
                issue_key=args.issue_key,
                spec_pdf=args.spec_pdf,
                spec_asset_id=args.spec_asset_id,
                spec_display_name=args.spec_display_name,
                preferred_parser=args.preferred_parser,
                mineru_python_exe=args.mineru_python_exe,
                policies=args.policies,
                top_k=args.top_k,
                prompt_mode=args.llm_prompt_mode,
                llm_backend=_build_llm_backend_from_args(parser, args),
            )
        except ValueError as error:
            parser.error(str(error))
        portal_state_output = args.portal_state_output or str(Path(args.workspace) / "portal_state.json")
        write_portal_state(
            portal_state_output,
            query=args.issue_key,
            allowed_policies=set(args.policies),
            workspace_dir=args.workspace,
        )
        payload["portal_state_path"] = portal_state_output
        return _print_json(payload)
    if args.command == "showcase-workbench":
        from services.workspace import showcase_workspace_runs

        try:
            payload = showcase_workspace_runs(
                args.workspace,
                jira_spec=args.jira_spec,
                confluence_spec=args.confluence_spec,
                issue_key=args.issue_key,
                spec_pdf=args.spec_pdf,
                spec_asset_id=args.spec_asset_id,
                spec_display_name=args.spec_display_name,
                preferred_parser=args.preferred_parser,
                mineru_python_exe=args.mineru_python_exe,
                policies=args.policies,
                top_k=args.top_k,
                prompt_mode=args.llm_prompt_mode,
                llm_backend=_build_llm_backend_from_args(parser, args),
                portal_state_output=args.portal_state_output,
            )
        except ValueError as error:
            parser.error(str(error))
        return _print_json(payload)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

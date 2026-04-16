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
    build_workspace,
    build_workspace_site,
    compile_workspace_wiki,
    control_workspace_run,
    deep_analyze_issue,
    export_workspace,
    fetch_workspace_spec,
    ingest_spec_asset,
    inbox_workspace,
    init_workspace,
    inspect_workspace_run,
    lint_workspace,
    list_workspace_runs,
    load_workspace_run_artifact,
    publish_workspace_wiki,
    query_workspace,
    route_workspace,
    smoke_deep_analysis_workspace,
    status_workspace,
    submit_workspace_run_to_prefect,
    sync_workspace_run_prefect_state,
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


def main() -> int:
    parser = argparse.ArgumentParser(description="Workspace-first CLI for progressive Jira/Confluence ingestion.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init")
    init_parser.add_argument("workspace")

    fetch_parser = subparsers.add_parser("fetch")
    fetch_parser.add_argument("workspace")
    fetch_parser.add_argument("spec")

    build_parser = subparsers.add_parser("build")
    build_parser.add_argument("workspace")

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
    smoke_parser.add_argument("--jira-spec", required=True)
    smoke_parser.add_argument("--confluence-spec", required=True)
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

    args = parser.parse_args()

    if args.command == "init":
        return _print_json(init_workspace(args.workspace))
    if args.command == "fetch":
        return _print_json(fetch_workspace_spec(args.workspace, args.spec))
    if args.command == "build":
        return _print_json(build_workspace(args.workspace))
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
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

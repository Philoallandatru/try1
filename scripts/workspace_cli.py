from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.analysis.llm_backends import build_llm_backend
from services.workspace import (
    build_workspace,
    build_workspace_site,
    compile_workspace_wiki,
    export_workspace,
    fetch_workspace_spec,
    inbox_workspace,
    init_workspace,
    lint_workspace,
    publish_workspace_wiki,
    query_workspace,
    route_workspace,
    status_workspace,
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

    args = parser.parse_args()

    if args.command == "init":
        return _print_json(init_workspace(args.workspace))
    if args.command == "fetch":
        return _print_json(fetch_workspace_spec(args.workspace, args.spec))
    if args.command == "build":
        return _print_json(build_workspace(args.workspace))
    if args.command == "export":
        return _print_json(export_workspace(args.workspace))
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
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

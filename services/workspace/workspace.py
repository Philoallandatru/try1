from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json
import shutil
import time

from services.analysis.llm_backends import LLMBackend
from services.analysis.retrieval_consumption import build_retrieval_consumption_payload
from services.ingest.markdown_export import documents_to_markdown, write_documents_markdown_tree
from services.ops.orchestration import load_source_payload
from services.retrieval.persistence.snapshot_store import load_snapshot, snapshot_paths, write_snapshot
from services.retrieval.toolkit import citation_for_index, load_page_index_artifact, search_index


WORKSPACE_CONFIG_FILE = "config.json"
WORKSPACE_VERSION = 1
DEFAULT_POLICIES = ["team:ssd", "public"]
SUPPORTED_KINDS = {"jira", "confluence"}
SUPPORTED_MODES = {"fixture", "live"}
JIRA_SCOPE_TYPES = {"issue", "project_slice", "project_full"}
CONFLUENCE_SCOPE_TYPES = {"page", "page_tree", "space_slice"}
SECRET_KEYS = {"token", "password", "api_key"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write_json(path: str | Path, payload: dict | list) -> str:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return str(output_path)


def _copy_file(source: str | Path, target: str | Path) -> str:
    source_path = Path(source)
    target_path = Path(target)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, target_path)
    return str(target_path)


def _redact(payload: object) -> object:
    if isinstance(payload, dict):
        sanitized = {}
        for key, value in payload.items():
            if key in SECRET_KEYS and value:
                sanitized[key] = "***"
            else:
                sanitized[key] = _redact(value)
        return sanitized
    if isinstance(payload, list):
        return [_redact(item) for item in payload]
    return payload


def workspace_paths(workspace_dir: str | Path) -> dict[str, Path]:
    root = Path(workspace_dir)
    return {
        "root": root,
        "config": root / WORKSPACE_CONFIG_FILE,
        "raw": root / "raw",
        "jira_specs": root / "raw" / "jira" / "specs",
        "jira_payloads": root / "raw" / "jira" / "payloads",
        "confluence_specs": root / "raw" / "confluence" / "specs",
        "confluence_payloads": root / "raw" / "confluence" / "payloads",
        "files": root / "raw" / "files",
        "snapshot_root": root / "snapshots" / "current",
        "export_root": root / "exports" / "latest",
        "runs": root / "runs",
        "wiki_summaries": root / "wiki" / "summaries",
        "wiki_reports": root / "wiki" / "reports",
    }


def _default_workspace_config() -> dict:
    return {
        "workspace_version": WORKSPACE_VERSION,
        "created_at": _utc_now(),
        "default_policies": DEFAULT_POLICIES,
        "paths": {
            "snapshot_dir": "snapshots/current",
            "export_dir": "exports/latest",
            "runs_dir": "runs",
        },
    }


def _starter_specs() -> dict[str, dict]:
    return {
        "raw/jira/specs/one-issue.json": {
            "kind": "jira",
            "mode": "fixture",
            "path": "fixtures/connectors/jira/full_sync.json",
            "scope": {"type": "issue", "issue_key": "SSD-777"},
            "fetch": {"fetch_backend": "atlassian-api", "include_comments": True},
        },
        "raw/jira/specs/project-slice.json": {
            "kind": "jira",
            "mode": "fixture",
            "path": "fixtures/connectors/jira/incremental_sync.json",
            "scope": {
                "type": "project_slice",
                "project_key": "SSD",
                "issue_type": "Bug",
                "updated_from": "2026-04-01T00:00:00Z",
                "updated_to": "2026-04-10T00:00:00Z",
            },
            "fetch": {"fetch_backend": "atlassian-api"},
        },
        "raw/jira/specs/full-project.json": {
            "kind": "jira",
            "mode": "fixture",
            "path": "fixtures/connectors/jira/full_sync.json",
            "scope": {"type": "project_full", "project_key": "SSD"},
            "fetch": {"fetch_backend": "atlassian-api"},
        },
        "raw/confluence/specs/one-page.json": {
            "kind": "confluence",
            "mode": "fixture",
            "path": "fixtures/connectors/confluence/page_sync.json",
            "scope": {"type": "page", "page_id": "123456"},
            "fetch": {"fetch_backend": "atlassian-api"},
        },
        "raw/confluence/specs/page-tree.json": {
            "kind": "confluence",
            "mode": "fixture",
            "path": "fixtures/connectors/confluence/page_sync.json",
            "scope": {"type": "page_tree", "root_page_id": "123456", "max_depth": None},
            "fetch": {"fetch_backend": "atlassian-api", "include_descendants": True},
        },
        "raw/confluence/specs/space-slice.json": {
            "kind": "confluence",
            "mode": "fixture",
            "path": "fixtures/connectors/confluence/page_sync.json",
            "scope": {"type": "space_slice", "space_key": "SSDENG", "label": "firmware"},
            "fetch": {"fetch_backend": "atlassian-api"},
        },
    }


def init_workspace(workspace_dir: str | Path) -> dict:
    paths = workspace_paths(workspace_dir)
    for key, path in paths.items():
        if key in {"root", "config"}:
            continue
        path.mkdir(parents=True, exist_ok=True)

    if not paths["config"].exists():
        _write_json(paths["config"], _default_workspace_config())

    written_specs = []
    for relative_path, payload in _starter_specs().items():
        target = paths["root"] / relative_path
        if not target.exists():
            _write_json(target, payload)
        written_specs.append(str(target))

    return {
        "workspace_dir": str(paths["root"]),
        "config_path": str(paths["config"]),
        "written_specs": written_specs,
    }


def _load_workspace_config(workspace_dir: str | Path) -> dict:
    paths = workspace_paths(workspace_dir)
    if not paths["config"].exists():
        raise ValueError(f"Workspace is not initialized: {paths['config']}")
    return _read_json(paths["config"])


def _resolve_spec_path(workspace_dir: str | Path, spec_ref: str | Path) -> Path:
    spec_path = Path(spec_ref)
    if spec_path.exists():
        return spec_path

    paths = workspace_paths(workspace_dir)
    candidates = [
        paths["jira_specs"] / spec_ref,
        paths["confluence_specs"] / spec_ref,
        paths["jira_specs"] / f"{spec_ref}.json",
        paths["confluence_specs"] / f"{spec_ref}.json",
    ]
    matches = [candidate for candidate in candidates if candidate.exists()]
    if not matches:
        raise ValueError(f"Unknown spec: {spec_ref}")
    if len(matches) > 1:
        raise ValueError(f"Ambiguous spec reference: {spec_ref}")
    return matches[0]


def _validate_source_spec(spec: dict) -> list[str]:
    errors: list[str] = []
    if not isinstance(spec, dict):
        return ["spec must be a JSON object"]

    kind = spec.get("kind")
    mode = spec.get("mode")
    scope = spec.get("scope", {})
    scope_type = scope.get("type")

    if kind not in SUPPORTED_KINDS:
        errors.append("spec.kind must be one of: jira, confluence")
    if mode not in SUPPORTED_MODES:
        errors.append("spec.mode must be one of: fixture, live")

    if mode == "fixture" and not spec.get("path"):
        errors.append("spec.path is required when mode=fixture")
    if mode == "live" and not spec.get("base_url"):
        errors.append("spec.base_url is required when mode=live")

    if kind == "jira":
        if scope_type not in JIRA_SCOPE_TYPES:
            errors.append("jira scope.type must be one of: issue, project_slice, project_full")
        if scope_type == "issue" and not scope.get("issue_key"):
            errors.append("jira issue scope requires scope.issue_key")
        if scope_type in {"project_slice", "project_full"} and not (scope.get("project_key") or scope.get("project_keys")):
            errors.append("jira project scope requires scope.project_key or scope.project_keys")

    if kind == "confluence":
        if scope_type not in CONFLUENCE_SCOPE_TYPES:
            errors.append("confluence scope.type must be one of: page, page_tree, space_slice")
        if scope_type == "page" and not scope.get("page_id"):
            errors.append("confluence page scope requires scope.page_id")
        if scope_type == "page_tree" and not scope.get("root_page_id"):
            errors.append("confluence page_tree scope requires scope.root_page_id")
        if scope_type == "space_slice" and not scope.get("space_key"):
            errors.append("confluence space_slice scope requires scope.space_key")

    return errors


def _load_source_spec(workspace_dir: str | Path, spec_ref: str | Path) -> tuple[Path, dict]:
    spec_path = _resolve_spec_path(workspace_dir, spec_ref)
    spec = _read_json(spec_path)
    errors = _validate_source_spec(spec)
    if errors:
        raise ValueError("; ".join(errors))
    return spec_path, spec


def _source_name(spec_path: Path, spec: dict) -> str:
    return str(spec.get("source_name") or spec_path.stem)


def _source_payload_kwargs(spec: dict) -> dict:
    kind = str(spec["kind"])
    mode = str(spec["mode"])
    scope = spec.get("scope", {})
    fetch = spec.get("fetch", {})

    kwargs = {
        "kind": kind,
        "path": spec.get("path"),
        "live": mode == "live",
        "base_url": spec.get("base_url"),
        "username": spec.get("username"),
        "password": spec.get("password"),
        "token": spec.get("token"),
        "auth_mode": spec.get("auth_mode", "auto"),
        "cursor": spec.get("cursor"),
        "page_size": int(fetch.get("page_size", spec.get("page_size", 50 if kind == "jira" else 25))),
        "jql": fetch.get("jql", spec.get("jql", "order by updated asc")),
        "cql": fetch.get("cql", spec.get("cql")),
        "space_key": scope.get("space_key") or spec.get("space_key"),
        "insecure": bool(fetch.get("insecure", spec.get("insecure", False))),
        "fetch_backend": fetch.get("fetch_backend", spec.get("fetch_backend", "native")),
        "include_comments": bool(fetch.get("include_comments", spec.get("include_comments", True))),
        "include_attachments": bool(fetch.get("include_attachments", spec.get("include_attachments", True))),
        "include_image_metadata": bool(fetch.get("include_image_metadata", spec.get("include_image_metadata", True))),
        "download_images": bool(fetch.get("download_images", spec.get("download_images", False))),
        "image_download_dir": fetch.get("image_download_dir") or spec.get("image_download_dir"),
    }

    scope_type = scope.get("type")
    if kind == "jira":
        if scope_type == "issue":
            kwargs["issue_key"] = scope.get("issue_key")
        else:
            kwargs["project_key"] = scope.get("project_key")
            kwargs["project_keys"] = scope.get("project_keys")
            kwargs["issue_type"] = scope.get("issue_type")
            kwargs["status"] = scope.get("status")
            kwargs["label"] = scope.get("label")
            kwargs["updated_from"] = scope.get("updated_from")
            kwargs["updated_to"] = scope.get("updated_to")

    if kind == "confluence":
        if scope_type == "page":
            kwargs["page_id"] = scope.get("page_id")
        elif scope_type == "page_tree":
            kwargs["root_page_id"] = scope.get("root_page_id")
            kwargs["include_descendants"] = True
            kwargs["max_depth"] = scope.get("max_depth")
        elif scope_type == "space_slice":
            kwargs["space_key"] = scope.get("space_key")
            kwargs["label"] = scope.get("label")
            kwargs["modified_from"] = scope.get("modified_from")
            kwargs["modified_to"] = scope.get("modified_to")
        kwargs["ancestor_id"] = scope.get("ancestor_id")
        kwargs["title"] = scope.get("title")
        kwargs["page_ids"] = scope.get("page_ids")

    return kwargs


def _payload_output_path(workspace_dir: str | Path, kind: str, source_name: str) -> Path:
    paths = workspace_paths(workspace_dir)
    if kind == "jira":
        return paths["jira_payloads"] / f"{source_name}.json"
    return paths["confluence_payloads"] / f"{source_name}.json"


def _run_dir(paths: dict[str, Path], *, source_name: str, command: str) -> Path:
    return paths["runs"] / f"{_utc_now().replace(':', '').replace('-', '')}-{source_name}-{command}"


def fetch_workspace_spec(workspace_dir: str | Path, spec_ref: str | Path) -> dict:
    _load_workspace_config(workspace_dir)
    paths = workspace_paths(workspace_dir)
    spec_path, spec = _load_source_spec(workspace_dir, spec_ref)
    source_name = _source_name(spec_path, spec)
    payload = load_source_payload(**_source_payload_kwargs(spec))
    payload_path = _payload_output_path(workspace_dir, str(spec["kind"]), source_name)
    _write_json(payload_path, payload)

    run_dir = _run_dir(paths, source_name=source_name, command="fetch")
    run_dir.mkdir(parents=True, exist_ok=True)
    _write_json(run_dir / "request.json", {"spec_path": str(spec_path), "spec": _redact(spec)})
    _write_json(
        run_dir / "result.json",
        {
            "payload_path": str(payload_path),
            "document_count": len(payload.get("documents", [])),
            "sync_type": payload.get("sync_type"),
            "cursor": payload.get("cursor"),
            "selector_summary": payload.get("selector_summary"),
        },
    )
    return {
        "workspace_dir": str(paths["root"]),
        "spec_path": str(spec_path),
        "payload_path": str(payload_path),
        "document_count": len(payload.get("documents", [])),
        "sync_type": payload.get("sync_type"),
        "cursor": payload.get("cursor"),
        "selector_summary": payload.get("selector_summary"),
        "run_dir": str(run_dir),
    }


def _payload_files(workspace_dir: str | Path) -> list[tuple[str, Path]]:
    paths = workspace_paths(workspace_dir)
    files: list[tuple[str, Path]] = []
    for kind, payload_dir in (("jira", paths["jira_payloads"]), ("confluence", paths["confluence_payloads"])):
        payload_paths = sorted(
            payload_dir.glob("*.json"),
            key=lambda path: (path.stat().st_mtime, str(path)),
        )
        files.extend((kind, path) for path in payload_paths)
    return files


def _spec_files(workspace_dir: str | Path) -> list[Path]:
    paths = workspace_paths(workspace_dir)
    return sorted(list(paths["jira_specs"].glob("*.json")) + list(paths["confluence_specs"].glob("*.json")))


def _file_state(paths: list[Path]) -> dict[str, int]:
    state: dict[str, int] = {}
    for path in paths:
        if path.exists():
            state[str(path)] = path.stat().st_mtime_ns
    return state


def _watch_summary(
    *,
    workspace_dir: str | Path,
    cycles: int,
    fetched_specs: list[str],
    build_report: dict | None,
) -> dict:
    return {
        "workspace_dir": str(Path(workspace_dir)),
        "cycles": cycles,
        "fetched_specs": fetched_specs,
        "fetched_spec_count": len(fetched_specs),
        "built": build_report is not None,
        "build": build_report,
    }


def build_workspace(workspace_dir: str | Path) -> dict:
    _load_workspace_config(workspace_dir)
    paths = workspace_paths(workspace_dir)
    payload_files = _payload_files(workspace_dir)
    if not payload_files:
        raise ValueError("No workspace payloads found. Run fetch first.")

    merged_documents: dict[str, dict] = {}
    sources: dict[str, dict] = {}
    for kind, payload_path in payload_files:
        payload = _read_json(payload_path)
        source_name = f"{kind}:{payload_path.stem}"
        documents = payload.get("documents", [])
        payload_synced_at = datetime.fromtimestamp(payload_path.stat().st_mtime, timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        for document in documents:
            merged_documents[document["document_id"]] = document
        sources[source_name] = {
            "cursor": payload.get("cursor"),
            "last_sync": payload_synced_at,
            "sync_type": payload.get("sync_type", "full"),
            "document_count": len(documents),
        }

    existing_manifest = load_snapshot(paths["snapshot_root"]).get("manifest", {})
    created_at = existing_manifest.get("created_at")
    snapshot_report = write_snapshot(
        paths["snapshot_root"],
        documents=[merged_documents[key] for key in sorted(merged_documents)],
        sources=sources,
        created_at=created_at,
    )

    run_dir = _run_dir(paths, source_name="workspace", command="build")
    run_dir.mkdir(parents=True, exist_ok=True)
    _write_json(
        run_dir / "result.json",
        {
            "snapshot_dir": str(paths["snapshot_root"]),
            "document_count": snapshot_report["manifest"]["document_count"],
            "page_index_count": snapshot_report["manifest"]["page_index_count"],
            "sources": sources,
        },
    )
    return {
        "workspace_dir": str(paths["root"]),
        "snapshot_dir": str(paths["snapshot_root"]),
        "document_count": snapshot_report["manifest"]["document_count"],
        "page_index_count": snapshot_report["manifest"]["page_index_count"],
        "sources": sources,
        "run_dir": str(run_dir),
    }


def export_workspace(workspace_dir: str | Path) -> dict:
    _load_workspace_config(workspace_dir)
    paths = workspace_paths(workspace_dir)
    snapshot = load_snapshot(paths["snapshot_root"])
    documents = snapshot.get("documents", {}).get("documents", [])
    page_index_path = snapshot_paths(paths["snapshot_root"])["page_index"]
    if not documents:
        raise ValueError("No snapshot documents found. Run build first.")

    export_root = paths["export_root"]
    export_root.mkdir(parents=True, exist_ok=True)
    bundle_markdown_path = export_root / "documents.md"
    page_index_export_path = export_root / "page_index.json"
    tree_root = export_root / "documents"
    manifest_path = export_root / "manifest.json"

    _write_text(bundle_markdown_path, documents_to_markdown(documents))
    tree_paths = write_documents_markdown_tree(documents, tree_root)
    _copy_file(page_index_path, page_index_export_path)
    manifest = {
        "exported_at": _utc_now(),
        "document_count": len(documents),
        "page_index_path": str(page_index_export_path),
        "bundle_markdown_path": str(bundle_markdown_path),
        "tree_root": str(tree_root),
        "tree_document_count": len(tree_paths),
    }
    _write_json(manifest_path, manifest)

    run_dir = _run_dir(paths, source_name="workspace", command="export")
    run_dir.mkdir(parents=True, exist_ok=True)
    _write_json(run_dir / "result.json", manifest)
    return {"workspace_dir": str(paths["root"]), "export_root": str(export_root), **manifest, "run_dir": str(run_dir)}


def _write_text(path: str | Path, text: str) -> str:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(text, encoding="utf-8")
    return str(output_path)


def query_workspace(
    workspace_dir: str | Path,
    *,
    question: str,
    top_k: int = 5,
    policies: list[str] | None = None,
    prompt_template: str | None = None,
    prompt_mode: str = "strict",
    llm_backend: LLMBackend | None = None,
) -> dict:
    _load_workspace_config(workspace_dir)
    paths = workspace_paths(workspace_dir)
    snapshot = load_snapshot(paths["snapshot_root"])
    documents = snapshot.get("documents", {}).get("documents", [])
    entries = load_page_index_artifact(snapshot_paths(paths["snapshot_root"])["page_index"])
    effective_policies = set(policies or DEFAULT_POLICIES)
    results = search_index(entries, question, effective_policies, top_k=top_k)
    citation = citation_for_index(entries, question, effective_policies, top_k=top_k)
    retrieval_payload = build_retrieval_consumption_payload(
        documents=documents,
        question=question,
        allowed_policies=effective_policies,
        top_k=top_k,
        prompt_template=prompt_template,
        prompt_mode=prompt_mode,
        llm_backend=llm_backend,
    )

    run_dir = _run_dir(paths, source_name="workspace", command="query")
    run_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "question": question,
        "top_k": top_k,
        "policies": sorted(effective_policies),
        "result_count": len(results),
        "results": results,
        "citation": citation,
        "ai_prompt": retrieval_payload["ai_prompt"],
        "answer": retrieval_payload["answer"],
    }
    _write_json(run_dir / "result.json", payload)
    return payload | {"run_dir": str(run_dir)}


def status_workspace(workspace_dir: str | Path) -> dict:
    config = _load_workspace_config(workspace_dir)
    paths = workspace_paths(workspace_dir)
    payload_files = _payload_files(workspace_dir)
    snapshot = load_snapshot(paths["snapshot_root"])
    export_manifest = _read_json(paths["export_root"] / "manifest.json") if (paths["export_root"] / "manifest.json").exists() else {}
    runs = sorted(path.name for path in paths["runs"].glob("*") if path.is_dir())

    return {
        "workspace_dir": str(paths["root"]),
        "workspace_version": config.get("workspace_version"),
        "spec_counts": {
            "jira": len(list(paths["jira_specs"].glob("*.json"))),
            "confluence": len(list(paths["confluence_specs"].glob("*.json"))),
        },
        "payload_counts": {
            "jira": len(list(paths["jira_payloads"].glob("*.json"))),
            "confluence": len(list(paths["confluence_payloads"].glob("*.json"))),
            "total": len(payload_files),
        },
        "snapshot": snapshot.get("manifest", {}),
        "export": export_manifest,
        "latest_run": runs[-1] if runs else None,
    }


def lint_workspace(workspace_dir: str | Path) -> dict:
    _load_workspace_config(workspace_dir)
    paths = workspace_paths(workspace_dir)
    errors: list[str] = []
    warnings: list[str] = []

    for spec_path in sorted(list(paths["jira_specs"].glob("*.json")) + list(paths["confluence_specs"].glob("*.json"))):
        try:
            spec = _read_json(spec_path)
        except json.JSONDecodeError:
            errors.append(f"Invalid JSON spec: {spec_path}")
            continue
        spec_errors = _validate_source_spec(spec)
        for error in spec_errors:
            errors.append(f"{spec_path.name}: {error}")

    payload_files = _payload_files(workspace_dir)
    snapshot_manifest_path = snapshot_paths(paths["snapshot_root"])["manifest"]
    export_manifest_path = paths["export_root"] / "manifest.json"

    if payload_files and not snapshot_manifest_path.exists():
        warnings.append("Payloads exist but snapshot has not been built")
    if snapshot_manifest_path.exists() and export_manifest_path.exists():
        if snapshot_manifest_path.stat().st_mtime > export_manifest_path.stat().st_mtime:
            warnings.append("Snapshot is newer than export output")

    for required_name, required_path in snapshot_paths(paths["snapshot_root"]).items():
        if snapshot_manifest_path.exists() and not required_path.exists():
            errors.append(f"Missing snapshot file: {required_name}")

    return {
        "workspace_dir": str(paths["root"]),
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
    }


def watch_workspace(
    workspace_dir: str | Path,
    *,
    interval_seconds: float = 2.0,
    max_cycles: int | None = None,
    run_once: bool = False,
) -> dict:
    _load_workspace_config(workspace_dir)
    spec_files = _spec_files(workspace_dir)
    payload_paths = [path for _, path in _payload_files(workspace_dir)]

    if run_once:
        fetched_specs = [fetch_workspace_spec(workspace_dir, spec_path)["spec_path"] for spec_path in spec_files]
        build_report = build_workspace(workspace_dir) if _payload_files(workspace_dir) else None
        return _watch_summary(
            workspace_dir=workspace_dir,
            cycles=1,
            fetched_specs=fetched_specs,
            build_report=build_report,
        )

    current_state = _file_state(spec_files + payload_paths)
    cycles = 0
    all_fetched_specs: list[str] = []
    last_build_report: dict | None = None

    while max_cycles is None or cycles < max_cycles:
        time.sleep(interval_seconds)
        cycles += 1

        spec_files = _spec_files(workspace_dir)
        payload_paths = [path for _, path in _payload_files(workspace_dir)]
        next_state = _file_state(spec_files + payload_paths)

        changed_specs = [
            spec_path
            for spec_path in spec_files
            if current_state.get(str(spec_path)) != next_state.get(str(spec_path))
        ]
        changed_payloads = [
            payload_path
            for payload_path in payload_paths
            if current_state.get(str(payload_path)) != next_state.get(str(payload_path))
        ]

        for spec_path in changed_specs:
            fetch_result = fetch_workspace_spec(workspace_dir, spec_path)
            all_fetched_specs.append(fetch_result["spec_path"])

        if changed_specs or changed_payloads:
            last_build_report = build_workspace(workspace_dir)

        current_state = next_state

    return _watch_summary(
        workspace_dir=workspace_dir,
        cycles=cycles,
        fetched_specs=all_fetched_specs,
        build_report=last_build_report,
    )

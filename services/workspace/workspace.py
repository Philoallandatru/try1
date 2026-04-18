from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import json
import subprocess
import shutil
import time
from uuid import uuid4

import yaml

from services.analysis.llm_backends import build_llm_backend
from services.analysis.llm_backends import LLMBackend
from services.analysis.deep_analysis import build_deep_analysis_from_documents
from services.analysis.demo_profiles import build_confluence_wiki_summary_prompt
from services.analysis.jira_issue_analysis import build_confluence_wiki_summary_payload
from services.analysis.jira_issue_analysis import summarize_jira_issue_markdown
from services.analysis.knowledge_compiler import build_knowledge_artifacts
from services.analysis.retrieval_consumption import build_retrieval_consumption_payload
from services.analysis.section_analysis import build_composite_report_markdown, build_section_outputs
from services.ingest.markdown_export import documents_to_markdown, write_documents_markdown_tree
from services.ops.orchestration import load_source_payload
from services.retrieval.persistence.snapshot_store import load_snapshot, snapshot_paths, write_snapshot
from services.retrieval.engine import PAGE_INDEX_ENGINE, build_shared_retrieval_bundle
from services.retrieval.toolkit import build_retrieval_index, citation_for_index, load_page_index_artifact, search_index
from services.workspace.task_manifest import (
    build_artifact_record,
    build_run_manifest,
    load_run_manifest,
    update_checkpoint,
    write_run_manifest,
)
from services.workspace.prefect_adapter import RealPrefectTaskAdapter, apply_prefect_state
from services.workspace.task_control import (
    append_control_event,
    build_control_event,
    build_rerun_manifest,
    request_section_rerun,
    request_resume,
    request_stop,
    write_controlled_manifest,
)
from services.workspace.source_registry import (
    build_fetch_request,
    fetch_cache_status,
    list_run_profiles,
    list_selector_profiles,
    list_sources,
    load_run_profile,
    load_selector_profile,
    load_source,
    validate_run_profile,
    write_credentials_example,
    write_run_profile,
    write_selector_profile,
    write_source,
)
from services.wiki_site import build_vitepress_site


WORKSPACE_CONFIG_FILE = "workspace.yaml"
LEGACY_WORKSPACE_CONFIG_FILE = "config.json"
WORKSPACE_VERSION = 1
DEFAULT_POLICIES = ["team:ssd", "public"]
SUPPORTED_KINDS = {"jira", "confluence"}
SUPPORTED_MODES = {"fixture", "live"}
JIRA_SCOPE_TYPES = {"issue", "project_slice", "project_full"}
CONFLUENCE_SCOPE_TYPES = {"page", "page_tree", "space_slice"}
SECRET_KEYS = {"token", "password", "api_key"}
SUPPORTED_TOPIC_ROUTE_SOURCE_TYPES = {"jira", "confluence"}
SUPPORTED_ROUTE_MODES = {
    "jira": {"analyze"},
    "confluence": {"summarize"},
}
SUPPORTED_PUBLISH_STATES = {
    "unprocessed",
    "summarized",
    "analyzed",
    "promoted",
    "rejected",
    "error",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def _json_default(value: object) -> object:
    if isinstance(value, set):
        return sorted(value)
    if isinstance(value, Counter):
        return dict(value)
    raise TypeError(f"Object of type {value.__class__.__name__} is not JSON serializable")


def _write_json(path: str | Path, payload: dict | list) -> str:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=_json_default), encoding="utf-8")
    return str(output_path)


def _copy_file(source: str | Path, target: str | Path) -> str:
    source_path = Path(source)
    target_path = Path(target)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, target_path)
    return str(target_path)


def _file_sha256(path: str | Path) -> str | None:
    target = Path(path)
    if not target.exists():
        return None
    return hashlib.sha256(target.read_bytes()).hexdigest()


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
        "legacy_config": root / LEGACY_WORKSPACE_CONFIG_FILE,
        "raw": root / "raw",
        "jira_specs": root / "raw" / "jira" / "specs",
        "jira_payloads": root / "raw" / "jira" / "payloads",
        "confluence_specs": root / "raw" / "confluence" / "specs",
        "confluence_payloads": root / "raw" / "confluence" / "payloads",
        "files": root / "raw" / "files",
        "sources": root / "sources",
        "selectors": root / "selectors",
        "profiles": root / "profiles",
        "local": root / ".local",
        "credentials_example": root / ".local" / "credentials.example.yaml",
        "build_root": root / "build",
        "normalize_root": root / "build" / "normalize",
        "index_root": root / "build" / "index",
        "spec_assets_root": root / "raw" / "files" / "spec_assets",
        "spec_assets_registry": root / "raw" / "files" / "spec_assets" / "registry.json",
        "snapshot_root": root / "snapshots" / "current",
        "export_root": root / "exports" / "latest",
        "runs": root / "runs",
        "wiki_root": root / "wiki",
        "wiki_topics": root / "wiki" / "topics.json",
        "wiki_routes": root / "wiki" / "routes.json",
        "wiki_compilation_manifest": root / "wiki" / "compilation-manifest.json",
        "wiki_compiled": root / "wiki" / "compiled",
        "wiki_vitepress_site": root / "wiki" / "vitepress_site",
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


def _write_yaml(path: str | Path, payload: dict) -> str:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(yaml.safe_dump(payload, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return str(output_path)


def _read_yaml(path: str | Path) -> dict:
    payload = yaml.safe_load(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"YAML file must contain a mapping: {path}")
    return payload


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


def _default_topic_registry() -> dict:
    return {
        "updated_at": _utc_now(),
        "topics": [],
    }


def _default_route_manifest() -> dict:
    return {
        "updated_at": _utc_now(),
        "confluence": [],
        "jira": [],
    }


def _default_compilation_manifest() -> dict:
    return {
        "updated_at": _utc_now(),
        "items": [],
    }


def init_workspace(workspace_dir: str | Path) -> dict:
    paths = workspace_paths(workspace_dir)
    for key, path in paths.items():
        if key in {
            "root",
            "config",
            "legacy_config",
            "wiki_topics",
            "wiki_routes",
            "wiki_compilation_manifest",
            "spec_assets_registry",
            "credentials_example",
        }:
            continue
        path.mkdir(parents=True, exist_ok=True)

    if not paths["config"].exists() and not paths["legacy_config"].exists():
        _write_yaml(paths["config"], _default_workspace_config())
    if not paths["wiki_topics"].exists():
        _write_json(paths["wiki_topics"], _default_topic_registry())
    if not paths["wiki_routes"].exists():
        _write_json(paths["wiki_routes"], _default_route_manifest())
    if not paths["wiki_compilation_manifest"].exists():
        _write_json(paths["wiki_compilation_manifest"], _default_compilation_manifest())
    if not paths["credentials_example"].exists():
        write_credentials_example(workspace_dir)

    written_specs = []
    for relative_path, payload in _starter_specs().items():
        target = paths["root"] / relative_path
        if not target.exists():
            _write_json(target, payload)
        written_specs.append(str(target))

    return {
        "workspace_dir": str(paths["root"]),
        "config_path": str(paths["config"]),
        "topic_registry_path": str(paths["wiki_topics"]),
        "route_manifest_path": str(paths["wiki_routes"]),
        "compilation_manifest_path": str(paths["wiki_compilation_manifest"]),
        "source_dir": str(paths["sources"]),
        "selector_dir": str(paths["selectors"]),
        "profile_dir": str(paths["profiles"]),
        "credentials_example_path": str(paths["credentials_example"]),
        "written_specs": written_specs,
    }


def _load_workspace_config(workspace_dir: str | Path) -> dict:
    paths = workspace_paths(workspace_dir)
    if paths["config"].exists():
        return _read_yaml(paths["config"])
    if paths["legacy_config"].exists():
        return _read_json(paths["legacy_config"])
    raise ValueError(f"Workspace is not initialized: {paths['config']}")


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
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    return paths["runs"] / f"{timestamp}-{uuid4().hex[:8]}-{source_name}-{command}"


def _resolve_run_dir(workspace_dir: str | Path, run_ref: str | Path) -> Path:
    run_path = Path(run_ref)
    if run_path.exists():
        return run_path
    candidate = workspace_paths(workspace_dir)["runs"] / run_path
    if candidate.exists():
        return candidate
    raise ValueError(f"Unknown run: {run_ref}")


def fetch_workspace_spec(workspace_dir: str | Path, spec_ref: str | Path) -> dict:
    _load_workspace_config(workspace_dir)
    spec_path, spec = _load_source_spec(workspace_dir, spec_ref)
    source_name = _source_name(spec_path, spec)
    selector_profile = f"{source_name}_selector"
    source_config = {
        "auth_mode": spec.get("auth_mode", "auto"),
    }
    for key in ("base_url", "path", "username", "password", "token", "jql", "cql", "space_key"):
        if spec.get(key) is not None:
            source_config[key] = spec[key]
    source_payload = {
        "version": 1,
        "name": source_name,
        "kind": spec["kind"],
        "mode": spec["mode"],
        "connector_type": f"{spec['kind']}.atlassian_api",
        "config": source_config,
        "defaults": dict(spec.get("fetch", {})),
        "policies": spec.get("policies", DEFAULT_POLICIES),
        "metadata": {"legacy_spec_path": str(spec_path)},
    }
    write_source(workspace_dir, source_payload)
    write_selector_profile(
        workspace_dir,
        {
            "version": 1,
            "name": selector_profile,
            "source": source_name,
            "selector": spec.get("scope", {}),
        },
    )
    result = fetch_workspace_source(workspace_dir, source_name=source_name, selector_profile=selector_profile)
    result["spec_path"] = str(spec_path)
    result["payload_path"] = result["latest_payload_path"]
    return {
        "workspace_dir": result["workspace_dir"],
        "spec_path": str(spec_path),
        "payload_path": result["latest_payload_path"],
        "latest_payload_path": result["latest_payload_path"],
        "history_payload_path": result["history_payload_path"],
        "fetch_manifest_path": result["fetch_manifest_path"],
        "document_count": result["document_count"],
        "run_dir": result["run_dir"],
    }


def add_workspace_source(
    workspace_dir: str | Path,
    name: str,
    *,
    connector_type: str,
    base_url: str | None = None,
    path: str | None = None,
    credential_ref: str | None = None,
    policies: list[str] | None = None,
    include_comments: bool = True,
    include_attachments: bool = True,
) -> dict:
    _load_workspace_config(workspace_dir)
    kind = "jira" if connector_type.startswith("jira.") else "pdf" if connector_type.startswith("pdf.") else "confluence"
    mode = "local" if kind == "pdf" else "live"
    config = {"auth_mode": "auto"}
    if base_url:
        config["base_url"] = base_url
    if path:
        config["path"] = path
    source = {
        "version": 1,
        "name": name,
        "kind": kind,
        "mode": mode,
        "connector_type": connector_type,
        "credential_ref": credential_ref,
        "config": config,
        "defaults": {
            "include_comments": include_comments,
            "include_attachments": include_attachments,
            "include_image_metadata": True,
            "download_images": False,
            **({"preferred_parser": "pypdf"} if kind == "pdf" else {}),
        },
        "policies": list(policies or DEFAULT_POLICIES),
        "metadata": {},
    }
    path = write_source(workspace_dir, source)
    return {
        "workspace_dir": str(workspace_paths(workspace_dir)["root"]),
        "path": path,
        "source": load_source(workspace_dir, name),
    }


def list_workspace_sources(workspace_dir: str | Path) -> dict:
    _load_workspace_config(workspace_dir)
    return {
        "workspace_dir": str(workspace_paths(workspace_dir)["root"]),
        "sources": list_sources(workspace_dir),
    }


def show_workspace_source(workspace_dir: str | Path, name: str) -> dict:
    _load_workspace_config(workspace_dir)
    return {
        "workspace_dir": str(workspace_paths(workspace_dir)["root"]),
        "source": load_source(workspace_dir, name),
    }


def configure_workspace_source(
    workspace_dir: str | Path,
    name: str,
    *,
    base_url: str | None = None,
    auth_mode: str | None = None,
    path: str | None = None,
) -> dict:
    _load_workspace_config(workspace_dir)
    source = load_source(workspace_dir, name)
    config = dict(source.get("config", {}))
    if base_url is not None:
        config["base_url"] = base_url
    if auth_mode is not None:
        config["auth_mode"] = auth_mode
    if path is not None:
        config["path"] = path
    source["config"] = config
    output_path = write_source(workspace_dir, source)
    return {"workspace_dir": str(workspace_paths(workspace_dir)["root"]), "path": output_path, "source": load_source(workspace_dir, name)}


def set_workspace_source_credential(
    workspace_dir: str | Path,
    name: str,
    *,
    credential_ref: str | None,
) -> dict:
    _load_workspace_config(workspace_dir)
    source = load_source(workspace_dir, name)
    if credential_ref:
        source["credential_ref"] = credential_ref
    else:
        source.pop("credential_ref", None)
    output_path = write_source(workspace_dir, source)
    return {"workspace_dir": str(workspace_paths(workspace_dir)["root"]), "path": output_path, "source": load_source(workspace_dir, name)}


def update_workspace_source_defaults(
    workspace_dir: str | Path,
    name: str,
    *,
    include_comments: bool | None = None,
    include_attachments: bool | None = None,
    include_image_metadata: bool | None = None,
    download_images: bool | None = None,
    refresh_freq_minutes: int | None = None,
    prune_freq_hours: int | None = None,
    page_size: int | None = None,
) -> dict:
    _load_workspace_config(workspace_dir)
    source = load_source(workspace_dir, name)
    defaults = dict(source.get("defaults", {}))
    updates = {
        "include_comments": include_comments,
        "include_attachments": include_attachments,
        "include_image_metadata": include_image_metadata,
        "download_images": download_images,
        "refresh_freq_minutes": refresh_freq_minutes,
        "prune_freq_hours": prune_freq_hours,
        "page_size": page_size,
    }
    for key, value in updates.items():
        if value is not None:
            defaults[key] = value
    source["defaults"] = defaults
    output_path = write_source(workspace_dir, source)
    return {"workspace_dir": str(workspace_paths(workspace_dir)["root"]), "path": output_path, "source": load_source(workspace_dir, name)}


def set_workspace_source_enabled(workspace_dir: str | Path, name: str, *, enabled: bool) -> dict:
    _load_workspace_config(workspace_dir)
    source = load_source(workspace_dir, name)
    source["enabled"] = enabled
    output_path = write_source(workspace_dir, source)
    return {"workspace_dir": str(workspace_paths(workspace_dir)["root"]), "path": output_path, "source": load_source(workspace_dir, name)}


def test_workspace_source(
    workspace_dir: str | Path,
    name: str,
    *,
    selector_profile: str | None = None,
    skip_credential_check: bool = False,
) -> dict:
    _load_workspace_config(workspace_dir)
    source = load_source(workspace_dir, name)
    selector_name = selector_profile
    if selector_name is None:
        matching_selectors = [selector for selector in list_selector_profiles(workspace_dir) if selector["source"] == name]
        selector_name = matching_selectors[0]["name"] if matching_selectors else None
    request = None
    if selector_name:
        request = build_fetch_request(
            workspace_dir,
            source_name=name,
            selector_profile=selector_name,
            resolve_credentials=not skip_credential_check,
        )
    return {
        "workspace_dir": str(workspace_paths(workspace_dir)["root"]),
        "source_name": name,
        "selector_profile": selector_name,
        "ok": True,
        "config_hash": request["manifest"]["config_hash"] if request else None,
        "selector_hash": request["manifest"]["selector_hash"] if request else None,
        "kind": source["kind"],
        "mode": source.get("mode", "live"),
    }


def add_workspace_selector(
    workspace_dir: str | Path,
    name: str,
    *,
    source: str,
    selector_type: str,
    issue_key: str | None = None,
    project_key: str | None = None,
    project_keys: list[str] | None = None,
    issue_type: str | None = None,
    status: str | None = None,
    label: str | None = None,
    updated_from: str | None = None,
    updated_to: str | None = None,
    page_id: str | None = None,
    root_page_id: str | None = None,
    max_depth: int | None = None,
    space_key: str | None = None,
    modified_from: str | None = None,
    modified_to: str | None = None,
    ancestor_id: str | None = None,
    title: str | None = None,
    page_ids: list[str] | None = None,
) -> dict:
    _load_workspace_config(workspace_dir)
    selector = {"type": selector_type}
    if issue_key:
        selector["issue_key"] = issue_key
    if project_key:
        selector["project_key"] = project_key
    if project_keys:
        selector["project_keys"] = list(project_keys)
    if issue_type:
        selector["issue_type"] = issue_type
    if status:
        selector["status"] = status
    if label:
        selector["label"] = label
    if updated_from:
        selector["updated_from"] = updated_from
    if updated_to:
        selector["updated_to"] = updated_to
    if page_id:
        selector["page_id"] = page_id
    if root_page_id:
        selector["root_page_id"] = root_page_id
    if max_depth is not None:
        selector["max_depth"] = max_depth
    if space_key:
        selector["space_key"] = space_key
    if modified_from:
        selector["modified_from"] = modified_from
    if modified_to:
        selector["modified_to"] = modified_to
    if ancestor_id:
        selector["ancestor_id"] = ancestor_id
    if title:
        selector["title"] = title
    if page_ids:
        selector["page_ids"] = list(page_ids)
    payload = {"version": 1, "name": name, "source": source, "selector": selector}
    path = write_selector_profile(workspace_dir, payload)
    return {
        "workspace_dir": str(workspace_paths(workspace_dir)["root"]),
        "path": path,
        "selector": load_selector_profile(workspace_dir, name),
    }


def list_workspace_selectors(workspace_dir: str | Path) -> dict:
    _load_workspace_config(workspace_dir)
    return {
        "workspace_dir": str(workspace_paths(workspace_dir)["root"]),
        "selectors": list_selector_profiles(workspace_dir),
    }


def show_workspace_selector(workspace_dir: str | Path, name: str) -> dict:
    _load_workspace_config(workspace_dir)
    return {
        "workspace_dir": str(workspace_paths(workspace_dir)["root"]),
        "selector": load_selector_profile(workspace_dir, name),
    }


def add_workspace_profile(
    workspace_dir: str | Path,
    name: str,
    *,
    input_bindings: dict[str, dict] | None = None,
    spec_asset_ids: list[str] | None = None,
    top_k: int = 5,
    policies: list[str] | None = None,
    llm_backend: str = "none",
    llm_model: str | None = None,
    llm_prompt_mode: str = "strict",
) -> dict:
    _load_workspace_config(workspace_dir)
    inputs = dict(input_bindings or {})
    if spec_asset_ids is not None:
        inputs["spec_assets"] = list(spec_asset_ids)
    payload = {
        "version": 1,
        "name": name,
        "inputs": inputs,
        "analysis": {
            "top_k": top_k,
            "policies": list(policies or DEFAULT_POLICIES),
            "llm_backend": llm_backend,
            "llm_prompt_mode": llm_prompt_mode,
        },
    }
    if llm_model:
        payload["analysis"]["llm_model"] = llm_model
    path = write_run_profile(workspace_dir, payload)
    return {
        "workspace_dir": str(workspace_paths(workspace_dir)["root"]),
        "path": path,
        "profile": load_run_profile(workspace_dir, name),
    }


def list_workspace_profiles(workspace_dir: str | Path) -> dict:
    _load_workspace_config(workspace_dir)
    return {
        "workspace_dir": str(workspace_paths(workspace_dir)["root"]),
        "profiles": list_run_profiles(workspace_dir),
    }


def show_workspace_profile(workspace_dir: str | Path, name: str) -> dict:
    _load_workspace_config(workspace_dir)
    return {
        "workspace_dir": str(workspace_paths(workspace_dir)["root"]),
        "profile": load_run_profile(workspace_dir, name),
    }


def update_workspace_profile(
    workspace_dir: str | Path,
    name: str,
    *,
    input_bindings: dict[str, dict] | None = None,
    replace_inputs: bool = False,
    spec_asset_ids: list[str] | None = None,
    top_k: int | None = None,
    policies: list[str] | None = None,
    llm_backend: str | None = None,
    llm_model: str | None = None,
    llm_prompt_mode: str | None = None,
) -> dict:
    _load_workspace_config(workspace_dir)
    profile = load_run_profile(workspace_dir, name)
    inputs = dict(profile.get("inputs", {}))
    if replace_inputs:
        existing_spec_assets = inputs.get("spec_assets")
        inputs = dict(input_bindings or {})
        if spec_asset_ids is None and existing_spec_assets is not None:
            inputs["spec_assets"] = list(existing_spec_assets)
    elif input_bindings is not None:
        inputs.update(input_bindings)
    if spec_asset_ids is not None:
        if spec_asset_ids:
            inputs["spec_assets"] = list(spec_asset_ids)
        else:
            inputs.pop("spec_assets", None)
    profile["inputs"] = inputs

    analysis = dict(profile.get("analysis", {}))
    if top_k is not None:
        analysis["top_k"] = top_k
    if policies is not None:
        analysis["policies"] = list(policies)
    if llm_backend is not None:
        analysis["llm_backend"] = llm_backend
    if llm_model is not None:
        analysis["llm_model"] = llm_model
    if llm_prompt_mode is not None:
        analysis["llm_prompt_mode"] = llm_prompt_mode
    profile["analysis"] = analysis

    path = write_run_profile(workspace_dir, profile)
    return {
        "workspace_dir": str(workspace_paths(workspace_dir)["root"]),
        "path": path,
        "profile": load_run_profile(workspace_dir, name),
    }


def validate_workspace_profile(workspace_dir: str | Path, name: str) -> dict:
    _load_workspace_config(workspace_dir)
    profile = load_run_profile(workspace_dir, name)
    return {
        "workspace_dir": str(workspace_paths(workspace_dir)["root"]),
        "ok": True,
        "profile": validate_run_profile(workspace_dir, profile),
    }


def _stable_payload_hash(payload: dict | list) -> str:
    data = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return f"sha256:{hashlib.sha256(data).hexdigest()}"


def _source_payload_cache_paths(workspace_dir: str | Path, kind: str, source_name: str) -> dict[str, Path]:
    payload_root = workspace_paths(workspace_dir)["raw"] / kind / "payloads" / source_name
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    return {
        "root": payload_root,
        "latest": payload_root / "latest.json",
        "manifest": payload_root / "fetch-manifest.json",
        "history": payload_root / "history" / f"{timestamp}.json",
    }


def fetch_workspace_source(workspace_dir: str | Path, *, source_name: str, selector_profile: str) -> dict:
    _load_workspace_config(workspace_dir)
    request = build_fetch_request(workspace_dir, source_name=source_name, selector_profile=selector_profile)
    source = request["source"]
    if source["kind"] == "pdf":
        from services.workspace.spec_assets import ingest_spec_asset

        asset = ingest_spec_asset(
            workspace_dir,
            spec_pdf=source.get("config", {}).get("path"),
            asset_id=source["name"],
            display_name=source.get("metadata", {}).get("description") or source["name"],
            preferred_parser=source.get("defaults", {}).get("preferred_parser", "auto"),
            mineru_python_exe=source.get("defaults", {}).get("mineru_python_exe"),
        )
        cache_paths = _source_payload_cache_paths(workspace_dir, source["kind"], source["name"])
        spec_corpus = _read_json(asset["corpus_json"])
        cached_payload = {
            "documents": spec_corpus.get("documents", []),
            "cursor": asset.get("version"),
            "sync_type": "local_file",
            "spec_asset": {
                "asset_id": asset["asset_id"],
                "version": asset["version"],
                "metadata_json": asset["metadata_json"],
                "corpus_json": asset["corpus_json"],
                "page_index_json": asset["page_index_json"],
            },
        }
        _write_json(cache_paths["latest"], cached_payload)
        _write_json(cache_paths["history"], cached_payload)
        manifest = {
            **request["manifest"],
            "fetched_at": _utc_now(),
            "payload_path": str(cache_paths["history"]),
            "latest_payload_path": str(cache_paths["latest"]),
            "payload_hash": _stable_payload_hash(cached_payload),
            "document_count": len(cached_payload["documents"]),
            "sync_type": "local_file",
            "cursor": asset.get("version"),
            "spec_asset": asset,
        }
        _write_json(cache_paths["manifest"], manifest)
        _normalize_payload_file(workspace_dir, source["kind"], cache_paths["latest"])
        paths = workspace_paths(workspace_dir)
        run_dir = _run_dir(paths, source_name=source["name"], command="fetch-source")
        run_dir.mkdir(parents=True, exist_ok=True)
        manifest = {
            **manifest,
            "normalize_manifest_path": str(paths["normalize_root"] / source["name"] / "manifest.json"),
        }
        _write_json(run_dir / "request.json", {"source": _redact(source), "selector_profile": request["selector_profile"]})
        _write_json(run_dir / "result.json", manifest)
        return {
            "workspace_dir": str(paths["root"]),
            "source_name": source["name"],
            "selector_profile": selector_profile,
            "latest_payload_path": str(cache_paths["latest"]),
            "history_payload_path": str(cache_paths["history"]),
            "fetch_manifest_path": str(cache_paths["manifest"]),
            "document_count": len(cached_payload["documents"]),
            "run_dir": str(run_dir),
            "spec_asset": asset,
        }
    payload = load_source_payload(**request["kwargs"])
    cache_paths = _source_payload_cache_paths(workspace_dir, source["kind"], source["name"])
    _write_json(cache_paths["latest"], payload)
    _write_json(cache_paths["history"], payload)
    manifest = {
        **request["manifest"],
        "fetched_at": _utc_now(),
        "payload_path": str(cache_paths["history"]),
        "latest_payload_path": str(cache_paths["latest"]),
        "payload_hash": _stable_payload_hash(payload),
        "document_count": len(payload.get("documents", [])),
        "sync_type": payload.get("sync_type"),
        "cursor": payload.get("cursor"),
    }
    _write_json(cache_paths["manifest"], manifest)
    _normalize_payload_file(workspace_dir, source["kind"], cache_paths["latest"])

    paths = workspace_paths(workspace_dir)
    run_dir = _run_dir(paths, source_name=source["name"], command="fetch-source")
    run_dir.mkdir(parents=True, exist_ok=True)
    _write_json(run_dir / "request.json", {"source": _redact(source), "selector_profile": request["selector_profile"]})
    _write_json(run_dir / "result.json", manifest)
    return {
        "workspace_dir": str(paths["root"]),
        "source_name": source["name"],
        "selector_profile": selector_profile,
        "latest_payload_path": str(cache_paths["latest"]),
        "history_payload_path": str(cache_paths["history"]),
        "fetch_manifest_path": str(cache_paths["manifest"]),
        "document_count": manifest["document_count"],
        "run_dir": str(run_dir),
    }


def refresh_workspace_source(workspace_dir: str | Path, source_name: str, *, selector_profile: str) -> dict:
    return fetch_workspace_source(workspace_dir, source_name=source_name, selector_profile=selector_profile)


def refresh_workspace(workspace_dir: str | Path) -> dict:
    _load_workspace_config(workspace_dir)
    paths = workspace_paths(workspace_dir)
    refreshed: list[dict] = []
    skipped: list[dict] = []
    for row in fetch_cache_status(workspace_dir):
        if row["status"] != "stale":
            skipped.append(row)
            continue
        source = load_source(workspace_dir, row["source_name"])
        manifest_path = paths["raw"] / source["kind"] / "payloads" / source["name"] / "fetch-manifest.json"
        if not manifest_path.exists():
            skipped.append(row | {"skip_reason": "no_prior_selector_profile"})
            continue
        manifest = _read_json(manifest_path)
        selector_profile = manifest.get("selector_profile")
        if not selector_profile:
            skipped.append(row | {"skip_reason": "missing_selector_profile"})
            continue
        refreshed.append(fetch_workspace_source(workspace_dir, source_name=source["name"], selector_profile=selector_profile))
    return {
        "workspace_dir": str(paths["root"]),
        "refreshed_count": len(refreshed),
        "skipped_count": len(skipped),
        "refreshed": refreshed,
        "skipped": skipped,
    }


def _normalize_payload_file(workspace_dir: str | Path, kind: str, payload_path: Path) -> str:
    paths = workspace_paths(workspace_dir)
    payload = _read_json(payload_path)
    documents = payload.get("documents", [])
    source_id = payload_path.parent.name if payload_path.name == "latest.json" else payload_path.stem
    normalize_dir = paths["normalize_root"] / source_id
    _write_json(
        normalize_dir / "manifest.json",
        {
            "source_name": source_id,
            "payload_hash": _stable_payload_hash(payload),
            "normalize_version": "workspace_payload_passthrough_v1",
            "created_at": _utc_now(),
            "documents_path": str(normalize_dir / "documents.json"),
            "document_count": len(documents),
            "source_type": kind,
        },
    )
    _write_json(normalize_dir / "documents.json", {"documents": documents})
    return source_id


def rebuild_workspace(workspace_dir: str | Path, *, from_layer: str = "raw", source_name: str | None = None) -> dict:
    if from_layer != "raw":
        raise ValueError("Only --from raw is supported")
    _load_workspace_config(workspace_dir)
    rebuilt_sources = []
    for kind, payload_path in _payload_files(workspace_dir):
        source_id = payload_path.parent.name if payload_path.name == "latest.json" else payload_path.stem
        if source_name and source_id != source_name:
            continue
        rebuilt_sources.append(_normalize_payload_file(workspace_dir, kind, payload_path))
    build_result = build_workspace(workspace_dir)
    return {
        "workspace_dir": str(workspace_paths(workspace_dir)["root"]),
        "from": from_layer,
        "rebuilt_sources": sorted(set(rebuilt_sources)),
        "build": build_result,
    }


def _load_normalized_documents(workspace_dir: str | Path) -> list[dict]:
    paths = workspace_paths(workspace_dir)
    documents_by_id: dict[str, dict] = {}
    for document_path in sorted(paths["normalize_root"].glob("*/documents.json")):
        for document in _read_json(document_path).get("documents", []):
            documents_by_id[document["document_id"]] = document
    from services.workspace.spec_assets import load_latest_spec_asset_documents

    asset_documents, _asset_sources = load_latest_spec_asset_documents(workspace_dir)
    for document in asset_documents:
        documents_by_id[document["document_id"]] = document
    return [documents_by_id[key] for key in sorted(documents_by_id)]


def reindex_workspace(workspace_dir: str | Path, *, index_name: str = "pageindex_v1") -> dict:
    if index_name != "pageindex_v1":
        raise ValueError("Only pageindex_v1 is supported")
    _load_workspace_config(workspace_dir)
    paths = workspace_paths(workspace_dir)
    documents = _load_normalized_documents(workspace_dir)
    if not documents:
        raise ValueError("No normalized documents found. Run build or rebuild first.")
    page_index = build_retrieval_index(documents)
    index_dir = paths["index_root"] / index_name
    page_index_path = index_dir / "page_index.json"
    _write_json(page_index_path, {"entries": page_index})
    manifest = {
        "index_name": index_name,
        "input_documents_hash": _stable_payload_hash({"documents": documents}),
        "index_version": "pageindex_v1_current",
        "created_at": _utc_now(),
        "page_index_path": str(page_index_path),
        "page_index_count": len(page_index),
    }
    _write_json(index_dir / "manifest.json", manifest)
    return {
        "workspace_dir": str(paths["root"]),
        "index_name": index_name,
        "page_index_path": str(page_index_path),
        "manifest_path": str(index_dir / "manifest.json"),
        "page_index_count": len(page_index),
    }


def _normalize_cache_status(workspace_dir: str | Path, fetch_rows: list[dict]) -> list[dict]:
    paths = workspace_paths(workspace_dir)
    fetch_by_source = {row["source_name"]: row for row in fetch_rows}
    rows: list[dict] = []
    for source in list_sources(workspace_dir):
        source_name = source["name"]
        fetch_row = fetch_by_source.get(source_name)
        if fetch_row and fetch_row["status"] != "fresh":
            rows.append({"source_name": source_name, "status": "stale", "reason": f"fetch_{fetch_row['reason']}"})
            continue
        fetch_manifest_path = paths["raw"] / source["kind"] / "payloads" / source_name / "fetch-manifest.json"
        normalize_manifest_path = paths["normalize_root"] / source_name / "manifest.json"
        if not fetch_manifest_path.exists():
            rows.append({"source_name": source_name, "status": "stale", "reason": "missing_fetch_manifest"})
            continue
        if not normalize_manifest_path.exists():
            rows.append({"source_name": source_name, "status": "stale", "reason": "missing_normalize_manifest"})
            continue
        fetch_manifest = _read_json(fetch_manifest_path)
        normalize_manifest = _read_json(normalize_manifest_path)
        if fetch_manifest.get("payload_hash") != normalize_manifest.get("payload_hash"):
            rows.append({"source_name": source_name, "status": "stale", "reason": "payload_changed"})
            continue
        if normalize_manifest.get("normalize_version") != "workspace_payload_passthrough_v1":
            rows.append({"source_name": source_name, "status": "stale", "reason": "normalize_version_changed"})
            continue
        rows.append({"source_name": source_name, "status": "fresh", "reason": "payload_hash_matches"})
    return rows


def _index_cache_status(workspace_dir: str | Path, normalize_rows: list[dict]) -> dict:
    paths = workspace_paths(workspace_dir)
    stale_normalize = [row for row in normalize_rows if row["status"] == "stale"]
    manifest_path = paths["index_root"] / "pageindex_v1" / "manifest.json"
    page_index_path = paths["index_root"] / "pageindex_v1" / "page_index.json"
    if stale_normalize:
        return {
            "index_name": "pageindex_v1",
            "status": "stale",
            "reason": "normalize_stale",
            "stale_sources": [row["source_name"] for row in stale_normalize],
        }
    if not manifest_path.exists():
        return {"index_name": "pageindex_v1", "status": "stale", "reason": "missing_index_manifest"}
    if not page_index_path.exists():
        return {"index_name": "pageindex_v1", "status": "stale", "reason": "missing_page_index"}
    documents = _load_normalized_documents(workspace_dir)
    expected_hash = _stable_payload_hash({"documents": documents})
    manifest = _read_json(manifest_path)
    if manifest.get("input_documents_hash") != expected_hash:
        return {"index_name": "pageindex_v1", "status": "stale", "reason": "documents_changed"}
    if manifest.get("index_version") != "pageindex_v1_current":
        return {"index_name": "pageindex_v1", "status": "stale", "reason": "index_version_changed"}
    return {"index_name": "pageindex_v1", "status": "fresh", "reason": "input_documents_hash_matches"}


def _analysis_cache_status(workspace_dir: str | Path, index_row: dict) -> dict:
    paths = workspace_paths(workspace_dir)
    rows: list[dict] = []
    if not paths["runs"].exists():
        return {"fresh": 0, "stale": 0, "runs": rows}
    current_snapshot_hashes = {
        name: _file_sha256(path)
        for name, path in snapshot_paths(paths["snapshot_root"]).items()
    }
    for run_dir in sorted(path for path in paths["runs"].glob("*") if path.is_dir()):
        manifest_path = run_dir / "analysis-manifest.json"
        if not manifest_path.exists():
            continue
        manifest = _read_json(manifest_path)
        if index_row["status"] != "fresh":
            rows.append({"run_id": run_dir.name, "status": "stale", "reason": "index_stale"})
            continue
        if manifest.get("snapshot_files") != current_snapshot_hashes:
            rows.append({"run_id": run_dir.name, "status": "stale", "reason": "snapshot_changed"})
            continue
        if manifest.get("analysis_version") != "deep_analysis_v1":
            rows.append({"run_id": run_dir.name, "status": "stale", "reason": "analysis_version_changed"})
            continue
        rows.append({"run_id": run_dir.name, "status": "fresh", "reason": "snapshot_hash_matches"})
    return {
        "fresh": len([row for row in rows if row["status"] == "fresh"]),
        "stale": len([row for row in rows if row["status"] == "stale"]),
        "runs": rows,
    }


def _payload_files(workspace_dir: str | Path) -> list[tuple[str, Path]]:
    paths = workspace_paths(workspace_dir)
    files: list[tuple[str, Path]] = []
    for kind, payload_dir in (
        ("jira", paths["jira_payloads"]),
        ("confluence", paths["confluence_payloads"]),
        ("pdf", paths["raw"] / "pdf" / "payloads"),
    ):
        payload_paths = sorted(
            payload_dir.glob("*.json"),
            key=lambda path: (path.stat().st_mtime, str(path)),
        )
        files.extend((kind, path) for path in payload_paths)
        source_payload_paths = sorted(
            payload_dir.glob("*/latest.json"),
            key=lambda path: (path.stat().st_mtime, str(path)),
        )
        files.extend((kind, path) for path in source_payload_paths)
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


def _snapshot_documents_by_id(workspace_dir: str | Path) -> dict[str, dict]:
    paths = workspace_paths(workspace_dir)
    snapshot = load_snapshot(paths["snapshot_root"])
    documents = snapshot.get("documents", {}).get("documents", [])
    if not documents:
        raise ValueError("No snapshot documents found. Run build first.")
    return {document["document_id"]: document for document in documents}


def _load_topic_registry(workspace_dir: str | Path) -> dict:
    paths = workspace_paths(workspace_dir)
    if not paths["wiki_topics"].exists():
        return _default_topic_registry()
    return _read_json(paths["wiki_topics"])


def _load_route_manifest(workspace_dir: str | Path) -> dict:
    paths = workspace_paths(workspace_dir)
    if not paths["wiki_routes"].exists():
        return _default_route_manifest()
    return _read_json(paths["wiki_routes"])


def _load_compilation_manifest(workspace_dir: str | Path) -> dict:
    paths = workspace_paths(workspace_dir)
    if not paths["wiki_compilation_manifest"].exists():
        return _default_compilation_manifest()
    return _read_json(paths["wiki_compilation_manifest"])


def _normalize_topic_registry(payload: dict) -> dict:
    topics = payload.get("topics", [])
    if not isinstance(topics, list):
        raise ValueError("topics must be a list")
    normalized_topics: list[dict] = []
    seen_slugs: set[str] = set()
    for raw_topic in topics:
        if not isinstance(raw_topic, dict):
            raise ValueError("topic entries must be objects")
        slug = str(raw_topic.get("slug") or "").strip()
        title = str(raw_topic.get("title") or "").strip()
        if not slug:
            raise ValueError("topic.slug is required")
        if not title:
            raise ValueError(f"topic.title is required for slug: {slug}")
        if slug in seen_slugs:
            raise ValueError(f"duplicate topic slug: {slug}")
        seen_slugs.add(slug)
        normalized_topics.append(
            {
                "slug": slug,
                "title": title,
                "description": str(raw_topic.get("description") or "").strip() or None,
            }
        )
    return {
        "updated_at": _utc_now(),
        "topics": normalized_topics,
    }


def _normalize_source_routes(
    *,
    source_type: str,
    entries: list[dict],
    topic_slugs: set[str],
    snapshot_documents: dict[str, dict],
) -> list[dict]:
    normalized_entries: list[dict] = []
    seen_document_ids: set[str] = set()
    allowed_modes = SUPPORTED_ROUTE_MODES[source_type]
    for raw_entry in entries:
        if not isinstance(raw_entry, dict):
            raise ValueError(f"{source_type} route entries must be objects")
        document_id = str(raw_entry.get("document_id") or "").strip()
        topic_slug = str(raw_entry.get("topic") or "").strip()
        mode = str(raw_entry.get("mode") or "").strip()
        if not document_id:
            raise ValueError(f"{source_type} route requires document_id")
        if document_id in seen_document_ids:
            raise ValueError(f"duplicate {source_type} route for document_id: {document_id}")
        seen_document_ids.add(document_id)
        if document_id not in snapshot_documents:
            raise ValueError(f"unknown routed document_id: {document_id}")
        document = snapshot_documents[document_id]
        if document["source_type"] != source_type:
            raise ValueError(f"document_id {document_id} is not a {source_type} document")
        if topic_slug not in topic_slugs:
            raise ValueError(f"unknown topic slug for {document_id}: {topic_slug}")
        if mode not in allowed_modes:
            allowed = ", ".join(sorted(allowed_modes))
            raise ValueError(f"{source_type} route mode must be one of: {allowed}")

        normalized_entry = {
            "document_id": document_id,
            "topic": topic_slug,
            "mode": mode,
        }
        if source_type == "jira":
            normalized_entry["promote"] = bool(raw_entry.get("promote", False))
        normalized_entries.append(normalized_entry)
    return normalized_entries


def _normalize_route_payload(
    *,
    payload: dict,
    snapshot_documents: dict[str, dict],
) -> tuple[dict, dict]:
    topic_registry = _normalize_topic_registry(payload)
    topic_slugs = {topic["slug"] for topic in topic_registry["topics"]}
    route_manifest = {
        "updated_at": _utc_now(),
        "confluence": _normalize_source_routes(
            source_type="confluence",
            entries=payload.get("confluence", []),
            topic_slugs=topic_slugs,
            snapshot_documents=snapshot_documents,
        ),
        "jira": _normalize_source_routes(
            source_type="jira",
            entries=payload.get("jira", []),
            topic_slugs=topic_slugs,
            snapshot_documents=snapshot_documents,
        ),
    }
    return topic_registry, route_manifest


def _build_compilation_manifest_from_routes(*, route_manifest: dict) -> dict:
    items: list[dict] = []
    for source_type in ("confluence", "jira"):
        for route_entry in route_manifest[source_type]:
            item = {
                "document_id": route_entry["document_id"],
                "source_type": source_type,
                "topic": route_entry["topic"],
                "mode": route_entry["mode"],
                "publish_state": "unprocessed",
                "last_error": None,
            }
            if source_type == "jira":
                item["promote"] = bool(route_entry.get("promote", False))
            items.append(item)
    items.sort(key=lambda item: (item["source_type"], item["document_id"]))
    return {
        "updated_at": _utc_now(),
        "items": items,
    }


def _topic_registry_by_slug(topic_registry: dict) -> dict[str, dict]:
    return {
        topic["slug"]: topic
        for topic in topic_registry.get("topics", [])
        if isinstance(topic, dict) and topic.get("slug")
    }


def _topic_context_markdown(
    *,
    topic: dict,
    route_manifest: dict,
    snapshot_documents: dict[str, dict],
    current_document_id: str,
) -> str:
    related_titles: list[str] = []
    for source_type in ("confluence", "jira"):
        for route_entry in route_manifest.get(source_type, []):
            if route_entry.get("topic") != topic["slug"]:
                continue
            document_id = route_entry.get("document_id")
            if not document_id or document_id == current_document_id:
                continue
            document = snapshot_documents.get(document_id)
            if document:
                related_titles.append(f"- {document.get('title', document_id)} ({document_id})")
    lines = [
        f"Topic: {topic['title']}",
        f"Description: {topic.get('description') or 'No topic description.'}",
        "",
        "Related routed items:",
        *(related_titles or ["- None"]),
    ]
    return "\n".join(lines).strip()


def _confluence_summary_markdown(
    *,
    document: dict,
    topic: dict,
    answer_text: str,
    derived_at: str,
) -> str:
    lines = [
        f"# {document.get('title', document['document_id'])}",
        "",
        '<nav class="breadcrumb-bar"><a href="../../index.md">Home</a><span>/</span><a href="../../topics/index.md">Topics</a><span>/</span><a href="../../topics/{slug}.md">Back to Topic Hub</a></nav>'.format(
            slug=topic["slug"]
        ),
        "",
        '<div class="page-hero">',
        '<p class="eyebrow">Confluence Summary</p>',
        f"<p class=\"hero-copy\">Prepared for the topic hub <strong>{topic['title']}</strong>. This is a derived summary; canonical source content remains authoritative.</p>",
        "</div>",
        "",
        '<div class="meta-strip">',
        '<span class="status-pill status-pill-summary">summary-ready</span>',
        '<span class="source-type-badge">confluence</span>',
        f'<span class="updated-timestamp">Derived `{derived_at}`</span>',
        f'<span class="updated-timestamp">Updated `{document.get("version") or "unknown"}`</span>',
        f'<span class="meta-chip">Document `{document["document_id"]}`</span>',
        f'<span class="meta-chip">Topic `{topic["slug"]}`</span>',
        f'<span class="meta-chip">Version `{document.get("version") or "unknown"}`</span>',
        "</div>",
        "",
        '<div class="page-layout">',
        '<div class="page-main">',
        "## Narrative Summary",
        "",
        answer_text.strip() or "No summary generated.",
        "</div>",
        '<aside class="page-aside">',
        '<section class="surface-card info-card">',
        "<h2>At a Glance</h2>",
        f"<ul><li><strong>Title:</strong> <code>{document.get('title', document['document_id'])}</code></li><li><strong>Topic Hub:</strong> <code>{topic['title']}</code></li><li><strong>Source Type:</strong> <code>confluence</code></li></ul>",
        "</section>",
        '<section class="surface-card info-card">',
        "<h2>Related Links</h2>",
        f'<ul><li><a href="../../topics/{topic["slug"]}.md">Back to Topic Hub</a></li><li><a href="./index.md">Browse All Confluence Summaries</a></li><li><a href="{document.get("provenance", {}).get("source_uri") or ""}">Trace Back To Source URI</a></li></ul>',
        "</section>",
        "</aside>",
        "</div>",
        "",
        "## Source Trace",
        "",
        '<div class="surface-card evidence-card">',
        f"<p><strong>Source URI:</strong> <code>{document.get('provenance', {}).get('source_uri') or ''}</code></p>",
        f"<p><strong>Canonical Topic Label:</strong> <code>{topic['title']}</code></p>",
        "<p><strong>Derived Artifact Type:</strong> <code>confluence-summary</code></p>",
        "</div>",
    ]
    return "\n".join(lines).strip()


def _jira_analysis_query(document: dict) -> str:
    issue_family = str(document.get("metadata", {}).get("issue_family") or "unknown")
    title = document.get("title", document["document_id"])
    if issue_family == "defect":
        return f"What failure signals, likely causes, and verification-relevant evidence exist for Jira issue {document['document_id']} {title}?"
    if issue_family == "requirement":
        return f"What requirement intent, decision signals, and open questions exist for Jira issue {document['document_id']} {title}?"
    if issue_family in {"requirement_change", "change_control"}:
        return f"What change impact, dependencies, and affected areas exist for Jira issue {document['document_id']} {title}?"
    if issue_family in {"delivery", "release"}:
        return f"What delivery status, blockers, and next-step evidence exist for Jira issue {document['document_id']} {title}?"
    return f"What grounded engineering evidence is available for Jira issue {document['document_id']} {title}?"


def _jira_analysis_task_instruction(document: dict) -> str:
    issue_family = str(document.get("metadata", {}).get("issue_family") or "unknown")
    issue_route = str(document.get("metadata", {}).get("issue_route") or "generic_jira_summary")
    return (
        "Analyze the routed Jira issue using only retrieved evidence from the current knowledge base. "
        f"Respect issue family `{issue_family}` and issue route `{issue_route}`. "
        "Do not treat this analysis as published topic knowledge yet."
    )


def _jira_analysis_markdown(
    *,
    document: dict,
    topic: dict,
    answer_text: str,
    derived_at: str,
    promote_requested: bool,
) -> str:
    metadata = document.get("metadata", {})
    lines = [
        f"# {document.get('title', document['document_id'])}",
        "",
        '<nav class="breadcrumb-bar"><a href="../../index.md">Home</a><span>/</span><a href="../../topics/index.md">Topics</a><span>/</span><a href="../../topics/{slug}.md">Back to Topic Hub</a></nav>'.format(
            slug=topic["slug"]
        ),
        "",
        '<div class="page-hero">',
        '<p class="eyebrow">Jira Analysis</p>',
        f"<p class=\"hero-copy\">Issue-centric analysis prepared for the topic hub <strong>{topic['title']}</strong>. This page is derived and does not replace the canonical Jira issue record.</p>",
        "</div>",
        "",
        '<div class="meta-strip">',
        '<span class="status-pill status-pill-analysis">analysis-ready</span>',
        '<span class="source-type-badge">jira</span>',
        f'<span class="updated-timestamp">Derived `{derived_at}`</span>',
        f'<span class="updated-timestamp">Updated `{document.get("version") or "unknown"}`</span>',
        f'<span class="meta-chip">Issue `{document["document_id"]}`</span>',
        f'<span class="meta-chip">Family `{metadata.get("issue_family") or "unknown"}`</span>',
        f'<span class="meta-chip">Route `{metadata.get("issue_route") or "generic_jira_summary"}`</span>',
        f'<span class="meta-chip">Version `{document.get("version") or "unknown"}`</span>',
        "</div>",
        "",
        '<div class="page-layout">',
        '<div class="page-main">',
        "## Analysis Narrative",
        "",
        answer_text.strip() or "No analysis generated.",
        "</div>",
        '<aside class="page-aside">',
        '<section class="surface-card info-card">',
        "<h2>At a Glance</h2>",
        f"<ul><li><strong>Topic Hub:</strong> <code>{topic['title']}</code></li><li><strong>Publishing Route:</strong> <code>{metadata.get('issue_route') or 'generic_jira_summary'}</code></li><li><strong>Issue Family:</strong> <code>{metadata.get('issue_family') or 'unknown'}</code></li></ul>",
        "</section>",
        '<section class="surface-card info-card">',
        "<h2>Publishing Status</h2>",
        f"<ul><li><strong>Promotion Requested:</strong> <code>{'yes' if promote_requested else 'no'}</code></li><li>This analysis can be promoted into a topic page when the route entry enables promotion.</li><li><strong>Topic Target:</strong> <code>{topic['slug']}</code></li></ul>",
        "</section>",
        '<section class="surface-card info-card">',
        "<h2>Related Links</h2>",
        f'<ul><li><a href="../../topics/{topic["slug"]}.md">Back to Topic Hub</a></li><li><a href="./index.md">Browse All Jira Analyses</a></li><li><a href="{document.get("provenance", {}).get("source_uri") or ""}">Trace Back To Source URI</a></li></ul>',
        "</section>",
        "</aside>",
        "</div>",
        "",
        "## Source Trace",
        "",
        '<div class="surface-card evidence-card">',
        f"<p><strong>Source URI:</strong> <code>{document.get('provenance', {}).get('source_uri') or ''}</code></p>",
        f"<p><strong>Canonical Issue Family:</strong> <code>{metadata.get('issue_family') or 'unknown'}</code></p>",
        f"<p><strong>Canonical Issue Route:</strong> <code>{metadata.get('issue_route') or 'generic_jira_summary'}</code></p>",
        "</div>",
    ]
    return "\n".join(lines).strip()


def _build_topic_page_markdown(
    *,
    topic: dict,
    confluence_artifacts: list[dict],
    jira_artifacts: list[dict],
    derived_at: str,
    has_unpromoted_jira: bool,
) -> str:
    open_questions = [
        "Review freshness and conflict indicators during the next compile cycle.",
    ]
    if has_unpromoted_jira:
        open_questions.insert(0, "A routed Jira analysis exists but is not promoted yet.")
    if not confluence_artifacts:
        open_questions.append("No Confluence summary is currently routed into this topic.")
    if not jira_artifacts:
        open_questions.append("No promoted Jira analysis is currently visible in this topic.")
    lines = [
        f"# {topic['title']}",
        "",
        '<nav class="breadcrumb-bar"><a href="../index.md">Home</a><span>/</span><a href="./index.md">Topics</a><span>/</span><span>{title}</span></nav>'.format(
            title=topic["title"]
        ),
        "",
        '<div class="page-hero">',
        '<p class="eyebrow">Topic Hub</p>',
        f"<p class=\"hero-copy\">{topic.get('description') or 'Curated cross-source knowledge for this topic.'}</p>",
        "</div>",
        "",
        '<div class="hero-metrics">',
        f'<div class="metric-card"><span class="metric-label">Confluence Inputs</span><strong>{len(confluence_artifacts)}</strong></div>',
        f'<div class="metric-card"><span class="metric-label">Promoted Jira Analyses</span><strong>{len(jira_artifacts)}</strong></div>',
        f'<div class="metric-card"><span class="metric-label">Topic Slug</span><strong>{topic["slug"]}</strong></div>',
        "</div>",
        "",
        '<div class="meta-strip">',
        '<span class="status-pill status-pill-topic">topic-live</span>',
        '<span class="source-type-badge">topic-hub</span>',
        f'<span class="updated-timestamp">Compiled `{derived_at}`</span>',
        f'<span class="meta-chip">Topic `{topic["slug"]}`</span>',
        "</div>",
        "",
        '<div class="page-layout">',
        '<div class="page-main">',
        "## Confluence Knowledge",
    ]
    if confluence_artifacts:
        for artifact in confluence_artifacts:
            lines.extend(
                [
                    '<article class="surface-card artifact-card">',
                    f"### {artifact['title']}",
                    '<div class="meta-strip">',
                    '<span class="source-type-badge">confluence</span>',
                    '<span class="status-pill status-pill-summary">summary-ready</span>',
                    "</div>",
                    f"<p><strong>Source Summary:</strong> <code>{artifact['output_path']}</code></p>",
                    f"<p>{artifact['text'].strip()}</p>",
                    "</article>",
                    "",
                ]
            )
    else:
        lines.extend(["No Confluence summary content routed into this topic yet.", ""])

    lines.append("## Jira Findings")
    if jira_artifacts:
        for artifact in jira_artifacts:
            lines.extend(
                [
                    '<article class="surface-card artifact-card">',
                    f"### {artifact['title']}",
                    '<div class="meta-strip">',
                    '<span class="source-type-badge">jira</span>',
                    '<span class="status-pill status-pill-analysis">analysis-ready</span>',
                    "</div>",
                    f"<p><strong>Jira Analysis:</strong> <code>{artifact['output_path']}</code></p>",
                    f"<p>{artifact['text'].strip()}</p>",
                    "</article>",
                    "",
                ]
            )
    else:
        lines.extend(["No promoted Jira analysis is published into this topic yet.", ""])
    lines.extend(
        [
            "</div>",
            '<aside class="page-aside">',
            '<section class="surface-card info-card">',
            "<h2>At a Glance</h2>",
            f"<ul><li><strong>Topic Title:</strong> <code>{topic['title']}</code></li><li><strong>Curated Confluence Inputs:</strong> <code>{len(confluence_artifacts)}</code></li><li><strong>Promoted Jira Analyses:</strong> <code>{len(jira_artifacts)}</code></li></ul>",
            "</section>",
            '<section class="surface-card info-card">',
            "<h2>Status Signals</h2>",
            f"<ul><li><strong>Last Compile:</strong> <code>{derived_at}</code></li><li><strong>Publication State:</strong> <code>{'active' if (confluence_artifacts or jira_artifacts) else 'empty'}</code></li><li><strong>Jira Promotion Coverage:</strong> <code>{len(jira_artifacts)}</code> promoted artifact(s)</li><li><strong>Routed But Unpromoted Jira Analyses:</strong> <code>{'yes' if has_unpromoted_jira else 'no'}</code></li></ul>",
            "</section>",
            '<section class="surface-card info-card">',
            "<h2>Related Links</h2>",
            "\n".join(f'<p><a href="../{"summaries/confluence" if artifact["source_type"] == "confluence" else "analyses/jira"}/{artifact["document_id"]}.md">{artifact["title"]}</a></p>' for artifact in [*confluence_artifacts, *jira_artifacts]) or "<p><a href=\"./index.md\">Browse All Topic Hubs</a></p>",
            '<p><a href="./index.md">Browse All Topic Hubs</a></p>',
            "</section>",
            "</aside>",
            "</div>",
            "",
            "## Evidence Trail",
            "",
            *(
                "\n".join(
                    [
                        '<div class="surface-card evidence-card">',
                        f"<p><span class=\"source-type-badge\">{artifact['source_type']}</span></p>",
                        f"<p><strong>Artifact:</strong> <code>{artifact['document_id']}</code></p>",
                        f"<p><strong>Path:</strong> <code>{artifact['output_path']}</code></p>",
                        f"<p><strong>Source Type:</strong> <code>{artifact['source_type']}</code></p>",
                        "</div>",
                    ]
                )
                for artifact in [*confluence_artifacts, *jira_artifacts]
            ),
            "",
            "## Open Questions",
            "",
            *(f"- {item}" for item in open_questions),
        ]
    )
    return "\n".join(lines).strip()


def _compilation_report(
    *,
    topics_by_slug: dict[str, dict],
    updated_items: list[dict],
    topic_paths: list[str],
    written_summaries: list[str],
    written_analyses: list[str],
) -> dict:
    built_topic_slugs = {Path(path).stem for path in topic_paths}
    empty_topics = sorted(slug for slug in topics_by_slug if slug not in built_topic_slugs)
    unpromoted_jira_document_ids = sorted(
        item["document_id"]
        for item in updated_items
        if item.get("source_type") == "jira" and not item.get("promote", False)
    )
    return {
        "generated_at": _utc_now(),
        "counts": {
            "topics_total": len(topics_by_slug),
            "topics_built": len(topic_paths),
            "summaries_built": len(written_summaries),
            "analyses_built": len(written_analyses),
            "routed_items": len(updated_items),
        },
        "empty_topics": empty_topics,
        "unpromoted_jira_document_ids": unpromoted_jira_document_ids,
    }


def _write_confluence_summary(
    *,
    workspace_dir: str | Path,
    document: dict,
    topic: dict,
    route_manifest: dict,
    snapshot_documents: dict[str, dict],
    prompt_mode: str,
    llm_backend: LLMBackend | None,
    derived_at: str,
) -> tuple[str, dict]:
    topic_context = _topic_context_markdown(
        topic=topic,
        route_manifest=route_manifest,
        snapshot_documents=snapshot_documents,
        current_document_id=document["document_id"],
    )
    if llm_backend:
        prompt = "\n\n".join(
            [
                build_confluence_wiki_summary_prompt(
                    title=document.get("title", document["document_id"]),
                    source_uri=document.get("provenance", {}).get("source_uri", ""),
                    page_markdown=document.get("markdown", "").strip(),
                    prompt_mode=prompt_mode,
                ),
                "## Existing Topic Context",
                topic_context,
            ]
        ).strip()
        answer = {
            "mode": "local-llm",
            "backend": llm_backend.name,
            "text": llm_backend.generate(prompt).strip(),
        }
        payload = {
            "document_id": document["document_id"],
            "title": document.get("title", document["document_id"]),
            "source_uri": document.get("provenance", {}).get("source_uri"),
            "version": document.get("version"),
            "space": document.get("metadata", {}).get("space") or document.get("provenance", {}).get("space") or "General",
            "derived_marker": "Derived page - canonical source remains Confluence.",
            "prompt": prompt,
            "answer": answer,
        }
    else:
        payload = build_confluence_wiki_summary_payload(
            document=document,
            prompt_mode=prompt_mode,
            llm_backend=None,
        )

    summary_markdown = _confluence_summary_markdown(
        document=document,
        topic=topic,
        answer_text=payload["answer"]["text"],
        derived_at=derived_at,
    )
    summary_path = workspace_paths(workspace_dir)["wiki_summaries"] / "confluence" / f"{document['document_id']}.md"
    _write_text(summary_path, summary_markdown)
    return str(summary_path), payload


def _write_jira_analysis(
    *,
    workspace_dir: str | Path,
    document: dict,
    topic: dict,
    prompt_mode: str,
    llm_backend: LLMBackend | None,
    derived_at: str,
    promote_requested: bool,
) -> tuple[str, dict]:
    summary_markdown = summarize_jira_issue_markdown(document)
    allowed_policies = set(DEFAULT_POLICIES)
    document_policy = str(document.get("acl", {}).get("policy") or "").strip()
    if document_policy:
        allowed_policies.add(document_policy)
    retrieval_payload = build_retrieval_consumption_payload(
        documents=_snapshot_documents_by_id(workspace_dir).values(),
        question=_jira_analysis_query(document),
        allowed_policies=allowed_policies,
        top_k=5,
        prompt_mode=prompt_mode,
        llm_backend=llm_backend,
        assistant_intro="You are an SSD issue-to-knowledge analysis assistant.",
        task_instruction=_jira_analysis_task_instruction(document),
        context_heading="Routed Jira Issue",
        context_markdown=summary_markdown,
    )
    analysis_markdown = _jira_analysis_markdown(
        document=document,
        topic=topic,
        answer_text=retrieval_payload["answer"]["text"],
        derived_at=derived_at,
        promote_requested=promote_requested,
    )
    analysis_path = workspace_paths(workspace_dir)["wiki_compiled"] / "analyses" / "jira" / f"{document['document_id']}.md"
    _write_text(analysis_path, analysis_markdown)
    return str(analysis_path), retrieval_payload


def route_workspace(workspace_dir: str | Path, manifest_path: str | Path) -> dict:
    _load_workspace_config(workspace_dir)
    paths = workspace_paths(workspace_dir)
    snapshot_documents = _snapshot_documents_by_id(workspace_dir)
    manifest_payload = _read_json(manifest_path)
    topic_registry, route_manifest = _normalize_route_payload(
        payload=manifest_payload,
        snapshot_documents=snapshot_documents,
    )
    compilation_manifest = _build_compilation_manifest_from_routes(route_manifest=route_manifest)

    _write_json(paths["wiki_topics"], topic_registry)
    _write_json(paths["wiki_routes"], route_manifest)
    _write_json(paths["wiki_compilation_manifest"], compilation_manifest)

    run_dir = _run_dir(paths, source_name="workspace", command="route")
    run_dir.mkdir(parents=True, exist_ok=True)
    _write_json(
        run_dir / "request.json",
        {
            "manifest_path": str(Path(manifest_path)),
            "manifest": manifest_payload,
        },
    )
    _write_json(
        run_dir / "result.json",
        {
            "topic_count": len(topic_registry["topics"]),
            "route_counts": {
                "confluence": len(route_manifest["confluence"]),
                "jira": len(route_manifest["jira"]),
            },
            "compilation_item_count": len(compilation_manifest["items"]),
        },
    )
    return {
        "workspace_dir": str(paths["root"]),
        "topic_registry_path": str(paths["wiki_topics"]),
        "route_manifest_path": str(paths["wiki_routes"]),
        "compilation_manifest_path": str(paths["wiki_compilation_manifest"]),
        "topic_count": len(topic_registry["topics"]),
        "route_counts": {
            "confluence": len(route_manifest["confluence"]),
            "jira": len(route_manifest["jira"]),
        },
        "compilation_item_count": len(compilation_manifest["items"]),
        "run_dir": str(run_dir),
    }


def inbox_workspace(workspace_dir: str | Path) -> dict:
    _load_workspace_config(workspace_dir)
    snapshot_documents = _snapshot_documents_by_id(workspace_dir)
    topic_registry = _load_topic_registry(workspace_dir)
    route_manifest = _load_route_manifest(workspace_dir)
    compilation_manifest = _load_compilation_manifest(workspace_dir)
    derived_at = _utc_now()

    routes_by_document_id: dict[str, dict] = {}
    for source_type in ("confluence", "jira"):
        for route_entry in route_manifest.get(source_type, []):
            routes_by_document_id[route_entry["document_id"]] = {
                "source_type": source_type,
                **route_entry,
            }

    compilation_by_document_id = {
        item["document_id"]: item for item in compilation_manifest.get("items", [])
    }

    items: list[dict] = []
    for document_id, document in sorted(snapshot_documents.items(), key=lambda item: (item[1]["source_type"], item[0])):
        if document["source_type"] not in SUPPORTED_TOPIC_ROUTE_SOURCE_TYPES:
            continue
        route_entry = routes_by_document_id.get(document_id)
        compilation_entry = compilation_by_document_id.get(document_id)
        metadata = document.get("metadata", {})
        item = {
            "document_id": document_id,
            "source_type": document["source_type"],
            "title": document.get("title", document_id),
            "version": document.get("version"),
            "routed": route_entry is not None,
            "topic": route_entry.get("topic") if route_entry else None,
            "mode": route_entry.get("mode") if route_entry else None,
            "promote": bool(route_entry.get("promote", False)) if route_entry else False,
            "publish_state": (
                compilation_entry.get("publish_state")
                if compilation_entry
                else "unrouted"
            ),
            "source_uri": document.get("provenance", {}).get("source_uri"),
        }
        if document["source_type"] == "jira":
            item["issue_family"] = metadata.get("issue_family")
            item["issue_route"] = metadata.get("issue_route")
            item["project"] = metadata.get("project")
        if document["source_type"] == "confluence":
            item["space"] = metadata.get("space")
        items.append(item)

    return {
        "workspace_dir": str(workspace_paths(workspace_dir)["root"]),
        "topic_count": len(topic_registry.get("topics", [])),
        "candidate_counts": {
            "jira": len([item for item in items if item["source_type"] == "jira"]),
            "confluence": len([item for item in items if item["source_type"] == "confluence"]),
            "total": len(items),
            "routed": len([item for item in items if item["routed"]]),
        },
        "items": items,
    }


def compile_workspace_wiki(
    workspace_dir: str | Path,
    *,
    prompt_mode: str = "strict",
    llm_backend: LLMBackend | None = None,
) -> dict:
    _load_workspace_config(workspace_dir)
    paths = workspace_paths(workspace_dir)
    snapshot_documents = _snapshot_documents_by_id(workspace_dir)
    topic_registry = _load_topic_registry(workspace_dir)
    topics_by_slug = _topic_registry_by_slug(topic_registry)
    route_manifest = _load_route_manifest(workspace_dir)
    compilation_manifest = _load_compilation_manifest(workspace_dir)
    derived_at = _utc_now()

    updated_items: list[dict] = []
    written_summaries: list[str] = []
    written_analyses: list[str] = []
    compiled_artifacts: dict[str, dict] = {}
    for item in compilation_manifest.get("items", []):
        updated_item = dict(item)
        if item.get("source_type") == "confluence" and item.get("mode") == "summarize":
            document = snapshot_documents[item["document_id"]]
            topic = topics_by_slug[item["topic"]]
            output_path, payload = _write_confluence_summary(
                workspace_dir=workspace_dir,
                document=document,
                topic=topic,
                route_manifest=route_manifest,
                snapshot_documents=snapshot_documents,
                prompt_mode=prompt_mode,
                llm_backend=llm_backend,
                derived_at=derived_at,
            )
            updated_item["publish_state"] = "summarized"
            updated_item["compiled_at"] = _utc_now()
            updated_item["output_path"] = output_path
            updated_item["last_error"] = None
            updated_item["summary_mode"] = payload["answer"]["mode"]
            written_summaries.append(output_path)
            compiled_artifacts[item["document_id"]] = {
                "document_id": item["document_id"],
                "source_type": "confluence",
                "topic": item["topic"],
                "title": document.get("title", document["document_id"]),
                "text": payload["answer"]["text"],
                "output_path": output_path,
            }
        elif item.get("source_type") == "jira" and item.get("mode") == "analyze":
            document = snapshot_documents[item["document_id"]]
            topic = topics_by_slug[item["topic"]]
            output_path, payload = _write_jira_analysis(
                workspace_dir=workspace_dir,
                document=document,
                topic=topic,
                prompt_mode=prompt_mode,
                llm_backend=llm_backend,
                derived_at=derived_at,
                promote_requested=bool(item.get("promote", False)),
            )
            updated_item["publish_state"] = "analyzed"
            updated_item["compiled_at"] = _utc_now()
            updated_item["output_path"] = output_path
            updated_item["last_error"] = None
            updated_item["analysis_mode"] = payload["answer"]["mode"]
            updated_item["topic_published"] = False
            written_analyses.append(output_path)
            compiled_artifacts[item["document_id"]] = {
                "document_id": item["document_id"],
                "source_type": "jira",
                "topic": item["topic"],
                "title": document.get("title", document["document_id"]),
                "text": payload["answer"]["text"],
                "output_path": output_path,
                "promote": bool(item.get("promote", False)),
            }
        updated_items.append(updated_item)

    topic_paths: list[str] = []
    for topic_slug, topic in sorted(topics_by_slug.items()):
        confluence_artifacts = [
            artifact
            for artifact in compiled_artifacts.values()
            if artifact["source_type"] == "confluence" and artifact["topic"] == topic_slug
        ]
        jira_artifacts = [
            artifact
            for artifact in compiled_artifacts.values()
            if artifact["source_type"] == "jira" and artifact["topic"] == topic_slug and artifact.get("promote")
        ]
        if not confluence_artifacts and not jira_artifacts:
            continue
        has_unpromoted_jira = any(
            artifact["source_type"] == "jira" and artifact["topic"] == topic_slug and not artifact.get("promote")
            for artifact in compiled_artifacts.values()
        )
        topic_markdown = _build_topic_page_markdown(
            topic=topic,
            confluence_artifacts=confluence_artifacts,
            jira_artifacts=jira_artifacts,
            derived_at=derived_at,
            has_unpromoted_jira=has_unpromoted_jira,
        )
        topic_path = paths["wiki_compiled"] / "topics" / f"{topic_slug}.md"
        _write_text(topic_path, topic_markdown)
        topic_paths.append(str(topic_path))
        published_document_ids = {artifact["document_id"] for artifact in confluence_artifacts}
        published_document_ids.update(artifact["document_id"] for artifact in jira_artifacts)
        for updated_item in updated_items:
            if updated_item["document_id"] not in published_document_ids:
                continue
            updated_item["topic_published"] = True
            if updated_item["source_type"] == "jira" and updated_item.get("promote"):
                updated_item["publish_state"] = "promoted"

    updated_manifest = {
        "updated_at": _utc_now(),
        "items": updated_items,
    }
    _write_json(paths["wiki_compilation_manifest"], updated_manifest)
    report = _compilation_report(
        topics_by_slug=topics_by_slug,
        updated_items=updated_items,
        topic_paths=topic_paths,
        written_summaries=written_summaries,
        written_analyses=written_analyses,
    )
    report_path = paths["wiki_reports"] / "compilation-report.json"
    _write_json(report_path, report)

    run_dir = _run_dir(paths, source_name="workspace", command="compile-wiki")
    run_dir.mkdir(parents=True, exist_ok=True)
    result = {
        "workspace_dir": str(paths["root"]),
        "summary_count": len(written_summaries),
        "analysis_count": len(written_analyses),
        "topic_page_count": len(topic_paths),
        "processed_counts": {
            "confluence": len(written_summaries),
            "jira": len(written_analyses),
        },
        "summary_paths": written_summaries,
        "analysis_paths": written_analyses,
        "topic_paths": topic_paths,
        "report_path": str(report_path),
        "compilation_manifest_path": str(paths["wiki_compilation_manifest"]),
        "run_dir": str(run_dir),
    }
    _write_json(run_dir / "result.json", result)
    return result


def build_workspace_site(
    workspace_dir: str | Path,
    *,
    renderer: str = "vitepress",
) -> dict:
    _load_workspace_config(workspace_dir)
    paths = workspace_paths(workspace_dir)
    if renderer != "vitepress":
        raise ValueError(f"Unsupported renderer: {renderer}")
    report = build_vitepress_site(
        compiled_root=paths["wiki_compiled"],
        output_root=paths["wiki_vitepress_site"],
        site_title="SSD Topic Wiki",
    )
    run_dir = _run_dir(paths, source_name="workspace", command="build-site")
    run_dir.mkdir(parents=True, exist_ok=True)
    result = {
        "workspace_dir": str(paths["root"]),
        **report,
        "run_dir": str(run_dir),
    }
    _write_json(run_dir / "result.json", result)
    return result


def verify_workspace_site_build(
    workspace_dir: str | Path,
    *,
    renderer: str = "vitepress",
    build_command: list[str] | None = None,
) -> dict:
    _load_workspace_config(workspace_dir)
    paths = workspace_paths(workspace_dir)
    if renderer != "vitepress":
        raise ValueError(f"Unsupported renderer: {renderer}")
    site_root = paths["wiki_vitepress_site"]
    vitepress_runtime_root = site_root / "docs" / ".vitepress"
    for transient_path in (
        vitepress_runtime_root / ".temp",
        vitepress_runtime_root / "dist",
    ):
        if transient_path.exists():
            shutil.rmtree(transient_path, ignore_errors=True)
    command = list(build_command or ["npm", "run", "docs:build"])
    resolved_executable = shutil.which(command[0])
    if not resolved_executable and command[0].lower() == "npm":
        resolved_executable = shutil.which("npm.cmd") or shutil.which("npm.exe")
    if not resolved_executable:
        report = {
            "renderer": renderer,
            "ok": False,
            "command": command,
            "exit_code": None,
            "stdout": "",
            "stderr": f"Executable not found: {command[0]}",
            "site_root": str(site_root),
            "dist_exists": (site_root / "docs" / ".vitepress" / "dist").exists(),
            "verified_at": _utc_now(),
        }
        report_path = paths["wiki_reports"] / "vitepress-build-report.json"
        _write_json(report_path, report)
        run_dir = _run_dir(paths, source_name="workspace", command="verify-site-build")
        run_dir.mkdir(parents=True, exist_ok=True)
        _write_json(run_dir / "result.json", report)
        return report | {"report_path": str(report_path), "run_dir": str(run_dir)}
    command[0] = resolved_executable
    completed = subprocess.run(
        command,
        cwd=site_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    report = {
        "renderer": renderer,
        "ok": completed.returncode == 0,
        "command": command,
        "exit_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "site_root": str(site_root),
        "dist_exists": (site_root / "docs" / ".vitepress" / "dist").exists(),
        "verified_at": _utc_now(),
    }
    report_path = paths["wiki_reports"] / "vitepress-build-report.json"
    _write_json(report_path, report)
    run_dir = _run_dir(paths, source_name="workspace", command="verify-site-build")
    run_dir.mkdir(parents=True, exist_ok=True)
    _write_json(run_dir / "result.json", report)
    return report | {"report_path": str(report_path), "run_dir": str(run_dir)}


def publish_workspace_wiki(
    workspace_dir: str | Path,
    *,
    manifest_path: str | Path,
    renderer: str = "vitepress",
    prompt_mode: str = "strict",
    llm_backend: LLMBackend | None = None,
    verify_site_build: bool = False,
    site_build_command: list[str] | None = None,
) -> dict:
    route_result = route_workspace(workspace_dir, manifest_path)
    compile_result = compile_workspace_wiki(
        workspace_dir,
        prompt_mode=prompt_mode,
        llm_backend=llm_backend,
    )
    build_result = build_workspace_site(
        workspace_dir,
        renderer=renderer,
    )
    site_verification = (
        verify_workspace_site_build(
            workspace_dir,
            renderer=renderer,
            build_command=site_build_command,
        )
        if verify_site_build
        else None
    )
    paths = workspace_paths(workspace_dir)
    run_dir = _run_dir(paths, source_name="workspace", command="publish-wiki")
    run_dir.mkdir(parents=True, exist_ok=True)
    result = {
        "workspace_dir": str(paths["root"]),
        "renderer": renderer,
        "route": route_result,
        "compile": compile_result,
        "build_site": build_result,
        "site_verification": site_verification,
        "report_path": compile_result["report_path"],
        "run_dir": str(run_dir),
    }
    _write_json(run_dir / "result.json", result)
    return result


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


def build_workspace(
    workspace_dir: str | Path,
    *,
    spec_asset_ids: list[str] | None = None,
    selected_sources: list[str] | None = None,
    snapshot_dir: str | Path | None = None,
    write_index_artifacts: bool = True,
) -> dict:
    _load_workspace_config(workspace_dir)
    paths = workspace_paths(workspace_dir)
    from services.workspace.spec_assets import load_latest_spec_asset_documents

    selected_source_names = set(selected_sources or [])
    for kind, payload_path in _payload_files(workspace_dir):
        source_id = payload_path.parent.name if payload_path.name == "latest.json" else payload_path.stem
        if selected_source_names and source_id not in selected_source_names:
            continue
        normalize_manifest = paths["normalize_root"] / source_id / "manifest.json"
        if not normalize_manifest.exists():
            _normalize_payload_file(workspace_dir, kind, payload_path)

    asset_documents, asset_sources = load_latest_spec_asset_documents(workspace_dir, asset_ids=spec_asset_ids)
    normalized_paths = sorted(paths["normalize_root"].glob("*/documents.json"))
    if selected_source_names:
        normalized_paths = [path for path in normalized_paths if path.parent.name in selected_source_names]
    if not normalized_paths and not asset_documents:
        raise ValueError("No normalized workspace documents or spec assets found. Run fetch-source, rebuild, or ingest-spec-asset first.")

    merged_documents: dict[str, dict] = {}
    sources: dict[str, dict] = {}
    for documents_path in normalized_paths:
        documents_payload = _read_json(documents_path)
        documents = documents_payload.get("documents", [])
        manifest_path = documents_path.parent / "manifest.json"
        manifest = _read_json(manifest_path) if manifest_path.exists() else {}
        source_id = str(manifest.get("source_name") or documents_path.parent.name)
        source_type = str(manifest.get("source_type") or "workspace")
        source_name = f"{source_type}:{source_id}"
        normalized_at = manifest.get("created_at") or datetime.fromtimestamp(
            documents_path.stat().st_mtime,
            timezone.utc,
        ).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        for document in documents:
            merged_documents[document["document_id"]] = document
        sources[source_name] = {
            "cursor": manifest.get("payload_hash"),
            "last_sync": normalized_at,
            "sync_type": "normalized",
            "document_count": len(documents),
        }
    for document in asset_documents:
        merged_documents[document["document_id"]] = document
    sources.update(asset_sources)

    target_snapshot_dir = Path(snapshot_dir) if snapshot_dir is not None else paths["snapshot_root"]
    existing_manifest = load_snapshot(target_snapshot_dir).get("manifest", {})
    created_at = existing_manifest.get("created_at")
    snapshot_report = write_snapshot(
        target_snapshot_dir,
        documents=[merged_documents[key] for key in sorted(merged_documents)],
        sources=sources,
        created_at=created_at,
    )
    documents_payload = {"documents": [merged_documents[key] for key in sorted(merged_documents)]}
    if write_index_artifacts:
        index_dir = paths["index_root"] / "pageindex_v1"
        index_page_path = index_dir / "page_index.json"
        _copy_file(target_snapshot_dir / "page_index.json", index_page_path)
        _write_json(
            index_dir / "manifest.json",
            {
                "index_name": "pageindex_v1",
                "input_documents_hash": _stable_payload_hash(documents_payload),
                "index_version": "pageindex_v1_current",
                "created_at": _utc_now(),
                "page_index_path": str(index_page_path),
                "page_index_count": snapshot_report["manifest"]["page_index_count"],
            },
        )

    run_dir = _run_dir(paths, source_name="workspace", command="build")
    run_dir.mkdir(parents=True, exist_ok=True)
    _write_json(
        run_dir / "result.json",
        {
            "snapshot_dir": str(target_snapshot_dir),
            "document_count": snapshot_report["manifest"]["document_count"],
            "page_index_count": snapshot_report["manifest"]["page_index_count"],
            "sources": sources,
        },
    )
    return {
        "workspace_dir": str(paths["root"]),
        "snapshot_dir": str(target_snapshot_dir),
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


def smoke_deep_analysis_workspace(
    workspace_dir: str | Path,
    *,
    jira_spec: str | Path,
    confluence_spec: str | Path,
    issue_key: str,
    spec_pdf: str | Path | None = None,
    spec_asset_id: str | None = None,
    spec_display_name: str | None = None,
    preferred_parser: str = "auto",
    mineru_python_exe: str | None = None,
    policies: list[str] | None = None,
    top_k: int = 5,
    prompt_mode: str = "strict",
    llm_backend: LLMBackend | None = None,
) -> dict:
    init_result = init_workspace(workspace_dir)
    jira_fetch = fetch_workspace_spec(workspace_dir, jira_spec)
    confluence_fetch = fetch_workspace_spec(workspace_dir, confluence_spec)
    spec_asset = None
    if spec_pdf:
        from services.workspace.spec_assets import ingest_spec_asset

        spec_asset = ingest_spec_asset(
            workspace_dir,
            spec_pdf=spec_pdf,
            asset_id=spec_asset_id,
            display_name=spec_display_name,
            preferred_parser=preferred_parser,
            mineru_python_exe=mineru_python_exe,
        )
    build_result = build_workspace(workspace_dir)
    deep_analysis = deep_analyze_issue(
        workspace_dir,
        issue_key,
        policies=policies,
        top_k=top_k,
        prompt_mode=prompt_mode,
        llm_backend=llm_backend,
    )
    return {
        "workspace_dir": str(workspace_paths(workspace_dir)["root"]),
        "init": init_result,
        "fetches": {
            "jira": jira_fetch,
            "confluence": confluence_fetch,
        },
        "spec_asset": spec_asset,
        "build": build_result,
        "deep_analysis": {
            "issue_id": deep_analysis["issue_id"],
            "analysis_profile": deep_analysis["analysis_profile"],
            "run_dir": deep_analysis["run_dir"],
            "run_manifest_path": deep_analysis["run_manifest_path"],
            "answer": deep_analysis["answer"],
        },
    }


def showcase_workspace_runs(
    workspace_dir: str | Path,
    *,
    jira_spec: str | Path,
    confluence_spec: str | Path,
    issue_key: str,
    spec_pdf: str | Path | None = None,
    spec_asset_id: str | None = None,
    spec_display_name: str | None = None,
    preferred_parser: str = "auto",
    mineru_python_exe: str | None = None,
    policies: list[str] | None = None,
    top_k: int = 5,
    prompt_mode: str = "strict",
    llm_backend: LLMBackend | None = None,
    portal_state_output: str | Path | None = None,
) -> dict:
    smoke = smoke_deep_analysis_workspace(
        workspace_dir,
        jira_spec=jira_spec,
        confluence_spec=confluence_spec,
        issue_key=issue_key,
        spec_pdf=spec_pdf,
        spec_asset_id=spec_asset_id,
        spec_display_name=spec_display_name,
        preferred_parser=preferred_parser,
        mineru_python_exe=mineru_python_exe,
        policies=policies,
        top_k=top_k,
        prompt_mode=prompt_mode,
        llm_backend=llm_backend,
    )
    completed_run = Path(smoke["deep_analysis"]["run_dir"]).name

    queued = control_workspace_run(
        workspace_dir,
        completed_run,
        action="rerun",
        requested_by="showcase",
        reason="showcase queued",
    )
    queued_run = Path(queued["run_dir"]).name

    running = control_workspace_run(
        workspace_dir,
        completed_run,
        action="rerun",
        requested_by="showcase",
        reason="showcase running",
    )
    running_run = Path(running["run_dir"]).name
    running_synced = sync_workspace_run_prefect_state(
        workspace_dir,
        running_run,
        prefect_state="Running",
        requested_by="showcase",
        flow_run_id=f"flow-{running_run}",
        deployment_name="jira-analysis",
    )

    stopped = control_workspace_run(
        workspace_dir,
        completed_run,
        action="rerun",
        requested_by="showcase",
        reason="showcase stopped",
    )
    stopped_run = Path(stopped["run_dir"]).name
    stopped_synced = sync_workspace_run_prefect_state(
        workspace_dir,
        stopped_run,
        prefect_state="Cancelled",
        requested_by="showcase",
        flow_run_id=f"flow-{stopped_run}",
        deployment_name="jira-analysis",
    )

    portal_state_path = None
    if portal_state_output:
        from apps.portal.portal_state import write_portal_state

        portal_state_path = write_portal_state(
            portal_state_output,
            query=issue_key,
            allowed_policies=set(policies or DEFAULT_POLICIES),
            workspace_dir=workspace_dir,
        )

    return {
        "workspace_dir": str(workspace_paths(workspace_dir)["root"]),
        "smoke": smoke,
        "runs": {
            "completed": completed_run,
            "queued": queued_run,
            "running": running_run,
            "stopped": stopped_run,
        },
        "prefect_runtime": {
            "running": running_synced,
            "stopped": stopped_synced,
        },
        "portal_state_path": str(portal_state_path) if portal_state_path else None,
    }


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
    retrieval_bundle = build_shared_retrieval_bundle(
        engine=PAGE_INDEX_ENGINE,
        entries=entries,
        query=question,
        allowed_policies=effective_policies,
        top_k=top_k,
    )
    retrieval_payload = build_retrieval_consumption_payload(
        documents=documents,
        question=question,
        allowed_policies=effective_policies,
        top_k=top_k,
        prompt_template=prompt_template,
        prompt_mode=prompt_mode,
        llm_backend=llm_backend,
        retrieval_bundle=retrieval_bundle,
    )

    run_dir = _run_dir(paths, source_name="workspace", command="query")
    run_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "question": question,
        "top_k": top_k,
        "policies": sorted(effective_policies),
        "result_count": len(retrieval_bundle["results"]),
        "results": retrieval_bundle["results"],
        "citation": {
            "citation": retrieval_bundle["citation"],
            "inspection": retrieval_bundle["inspection"],
        },
        "comparison": retrieval_bundle["comparison"],
        "ai_prompt": retrieval_payload["ai_prompt"],
        "answer": retrieval_payload["answer"],
    }
    _write_json(run_dir / "result.json", payload)
    return payload | {"run_dir": str(run_dir)}


def run_workspace_analysis(
    workspace_dir: str | Path,
    *,
    profile_name: str,
    issue_key: str,
    use_existing_snapshot: bool = False,
    llm_backend: LLMBackend | None = None,
) -> dict:
    _load_workspace_config(workspace_dir)
    profile = load_run_profile(workspace_dir, profile_name)
    analysis_config = profile.get("analysis", {})
    selected_sources: list[str] = []
    selected_selector_profiles: list[str] = []
    for input_name, input_config in profile.get("inputs", {}).items():
        if input_name == "spec_assets" or not isinstance(input_config, dict):
            continue
        source_name = input_config.get("source")
        selector_name = input_config.get("selector_profile")
        if source_name:
            selected_sources.append(source_name)
        if selector_name:
            selected_selector_profiles.append(selector_name)
    selected_sources = sorted(set(selected_sources))
    selected_selector_profiles = sorted(set(selected_selector_profiles))
    raw_spec_assets = profile.get("inputs", {}).get("spec_assets")
    selected_spec_assets = list(raw_spec_assets) if isinstance(raw_spec_assets, list) else []
    scope_hash = hashlib.sha256(
        json.dumps(
            {
                "profile": profile_name,
                "selected_sources": selected_sources,
                "selected_selector_profiles": selected_selector_profiles,
                "selected_spec_assets": selected_spec_assets,
            },
            ensure_ascii=False,
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()[:12]
    run_snapshot_dir = workspace_paths(workspace_dir)["runs"] / "_profile_snapshots" / profile_name / scope_hash
    orchestration: dict[str, object] = {"fetches": [], "skipped": []}
    if use_existing_snapshot:
        expected_snapshot = snapshot_paths(run_snapshot_dir)
        if not all(path.exists() for path in expected_snapshot.values()):
            raise ValueError(f"Scoped snapshot does not exist for profile {profile_name}: {run_snapshot_dir}")
    else:
        fetch_status_by_source = {row["source_name"]: row for row in fetch_cache_status(workspace_dir)}
        for input_name, input_config in profile.get("inputs", {}).items():
            if input_name == "spec_assets" or not isinstance(input_config, dict):
                continue
            source_name = input_config.get("source")
            selector_name = input_config.get("selector_profile")
            if not source_name or not selector_name:
                continue
            source_status = fetch_status_by_source.get(source_name, {"status": "stale", "reason": "not_fetched"})
            if source_status["status"] == "fresh":
                orchestration["skipped"].append({"source_name": source_name, "reason": "fresh"})
                continue
            orchestration["fetches"].append(
                fetch_workspace_source(workspace_dir, source_name=source_name, selector_profile=selector_name)
            )
        orchestration["build"] = build_workspace(
            workspace_dir,
            spec_asset_ids=selected_spec_assets,
            selected_sources=selected_sources,
            snapshot_dir=run_snapshot_dir,
            write_index_artifacts=False,
        )
    if llm_backend is None and analysis_config.get("llm_backend") not in (None, "none"):
        llm_backend = build_llm_backend(
            backend=analysis_config.get("llm_backend", "none"),
            model=analysis_config.get("llm_model"),
            base_url=analysis_config.get("llm_base_url"),
            api_key=analysis_config.get("llm_api_key"),
            mock_response=analysis_config.get("llm_mock_response"),
            timeout_seconds=int(analysis_config.get("llm_timeout_seconds", 120)),
        )
    payload = deep_analyze_issue(
        workspace_dir,
        issue_key,
        policies=analysis_config.get("policies", DEFAULT_POLICIES),
        top_k=int(analysis_config.get("top_k", 5)),
        prompt_mode=analysis_config.get("llm_prompt_mode", "strict"),
        llm_backend=llm_backend,
        snapshot_dir=run_snapshot_dir,
        input_metadata={
            "profile": profile_name,
            "selected_sources": selected_sources,
            "selected_selector_profiles": selected_selector_profiles,
            "selected_spec_assets": selected_spec_assets,
        },
    )
    manifest_path = Path(payload["run_dir"]) / "analysis-manifest.json"
    snapshot_hashes = {
        name: _file_sha256(path)
        for name, path in snapshot_paths(run_snapshot_dir).items()
    }
    analysis_manifest = {
        "profile": profile_name,
        "issue_key": issue_key,
        "snapshot_dir": str(run_snapshot_dir),
        "snapshot_files": snapshot_hashes,
        "snapshot_hash": _stable_payload_hash(snapshot_hashes),
        "selected_sources": selected_sources,
        "selected_selector_profiles": selected_selector_profiles,
        "selected_spec_assets": selected_spec_assets,
        "analysis_version": "deep_analysis_v1",
        "prompt_profile_version": analysis_config.get("llm_prompt_mode", "strict"),
        "created_at": _utc_now(),
    }
    _write_json(manifest_path, analysis_manifest)
    return {
        "workspace_dir": str(workspace_paths(workspace_dir)["root"]),
        "profile": profile_name,
        "snapshot_dir": str(run_snapshot_dir),
        "analysis_manifest_path": str(manifest_path),
        "orchestration": orchestration,
        "analysis": payload,
    }


def status_workspace(workspace_dir: str | Path) -> dict:
    config = _load_workspace_config(workspace_dir)
    paths = workspace_paths(workspace_dir)
    from services.workspace.spec_assets import load_spec_asset_registry

    payload_files = _payload_files(workspace_dir)
    snapshot = load_snapshot(paths["snapshot_root"])
    export_manifest = _read_json(paths["export_root"] / "manifest.json") if (paths["export_root"] / "manifest.json").exists() else {}
    runs = sorted(path.name for path in paths["runs"].glob("*") if path.is_dir())
    fetch_rows = fetch_cache_status(workspace_dir)
    normalize_rows = _normalize_cache_status(workspace_dir, fetch_rows)
    index_row = _index_cache_status(workspace_dir, normalize_rows)
    analysis_status = _analysis_cache_status(workspace_dir, index_row)

    return {
        "workspace_dir": str(paths["root"]),
        "workspace_version": config.get("workspace_version"),
        "registry_counts": {
            "sources": len(list_sources(workspace_dir)),
            "selectors": len(list_selector_profiles(workspace_dir)),
            "profiles": len(list_run_profiles(workspace_dir)),
        },
        "spec_counts": {
            "jira": len(list(paths["jira_specs"].glob("*.json"))),
            "confluence": len(list(paths["confluence_specs"].glob("*.json"))),
            "spec_assets": len(
                {
                    entry.get("asset_id")
                    for entry in load_spec_asset_registry(workspace_dir).get("assets", [])
                    if entry.get("asset_id")
                }
            ),
        },
        "payload_counts": {
            "jira": len(list(paths["jira_payloads"].glob("*.json"))),
            "confluence": len(list(paths["confluence_payloads"].glob("*.json"))),
            "pdf": len(list((paths["raw"] / "pdf" / "payloads").glob("*/latest.json"))),
            "total": len(payload_files),
        },
        "cache": {
            "fetch": {
                "fresh": len([row for row in fetch_rows if row["status"] == "fresh"]),
                "stale": len([row for row in fetch_rows if row["status"] == "stale"]),
                "disabled": len([row for row in fetch_rows if row["status"] == "disabled"]),
                "sources": fetch_rows,
            },
            "normalize": {
                "fresh": len([row for row in normalize_rows if row["status"] == "fresh"]),
                "stale": len([row for row in normalize_rows if row["status"] == "stale"]),
                "sources": normalize_rows,
            },
            "index": index_row,
            "analysis": analysis_status,
        },
        "snapshot": snapshot.get("manifest", {}),
        "export": export_manifest,
        "wiki": {
            "topic_count": len(_load_topic_registry(workspace_dir).get("topics", [])),
            "route_counts": {
                "confluence": len(_load_route_manifest(workspace_dir).get("confluence", [])),
                "jira": len(_load_route_manifest(workspace_dir).get("jira", [])),
            },
            "compilation_item_count": len(_load_compilation_manifest(workspace_dir).get("items", [])),
        },
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

    try:
        topic_registry = _load_topic_registry(workspace_dir)
        route_manifest = _load_route_manifest(workspace_dir)
        compilation_manifest = _load_compilation_manifest(workspace_dir)
    except json.JSONDecodeError:
        errors.append("Invalid JSON in workspace wiki control-plane artifacts")
        topic_registry = _default_topic_registry()
        route_manifest = _default_route_manifest()
        compilation_manifest = _default_compilation_manifest()

    topic_slugs = {topic.get("slug") for topic in topic_registry.get("topics", []) if isinstance(topic, dict)}
    for source_type in ("confluence", "jira"):
        for route_entry in route_manifest.get(source_type, []):
            if route_entry.get("topic") not in topic_slugs:
                errors.append(f"Unknown topic slug in {source_type} route: {route_entry.get('topic')}")
            if route_entry.get("mode") not in SUPPORTED_ROUTE_MODES[source_type]:
                errors.append(f"Invalid {source_type} route mode: {route_entry.get('mode')}")

    for item in compilation_manifest.get("items", []):
        if item.get("publish_state") not in SUPPORTED_PUBLISH_STATES:
            errors.append(f"Invalid compilation publish_state for {item.get('document_id')}: {item.get('publish_state')}")

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


def deep_analyze_issue(
    workspace_dir: str | Path,
    issue_key: str,
    *,
    policies: list[str] | None = None,
    top_k: int = 5,
    prompt_mode: str = "strict",
    llm_backend: LLMBackend | None = None,
    snapshot_dir: str | Path | None = None,
    input_metadata: dict | None = None,
) -> dict:
    """Deep-analyze a single Jira issue from the workspace snapshot."""
    _load_workspace_config(workspace_dir)
    paths = workspace_paths(workspace_dir)
    active_snapshot_dir = Path(snapshot_dir) if snapshot_dir is not None else paths["snapshot_root"]
    snapshot = load_snapshot(active_snapshot_dir)
    documents = snapshot.get("documents", {}).get("documents", [])
    snapshot_file_hashes = {
        name: _file_sha256(path)
        for name, path in snapshot_paths(active_snapshot_dir).items()
    }
    effective_policies = set(policies or DEFAULT_POLICIES)

    run_dir = _run_dir(paths, source_name="workspace", command="deep-analyze")
    run_dir.mkdir(parents=True, exist_ok=True)
    payload = build_deep_analysis_from_documents(
        documents=documents,
        issue_id=issue_key,
        allowed_policies=effective_policies,
        top_k=top_k,
        prompt_mode=prompt_mode,
        llm_backend=llm_backend,
    )

    result_path = run_dir / "result.json"
    shared_retrieval_bundle_path = run_dir / "shared_retrieval_bundle.json"
    section_outputs_dir = run_dir / "section_outputs"
    report_dir = run_dir / "report"
    report_markdown_path = report_dir / "report.md"
    knowledge_dir = run_dir / "knowledge"
    confluence_update_proposal_path = knowledge_dir / "confluence_update_proposal.json"
    concept_cards_path = knowledge_dir / "concept_cards.json"
    wiki_draft_path = knowledge_dir / "wiki_draft.md"
    _write_json(result_path, payload)
    _write_json(shared_retrieval_bundle_path, payload["shared_retrieval_bundle"])
    section_outputs_dir.mkdir(parents=True, exist_ok=True)
    for section_name, section_payload in payload["section_outputs"].items():
        _write_json(section_outputs_dir / f"{section_name}.json", section_payload)
    report_dir.mkdir(parents=True, exist_ok=True)
    _write_text(report_markdown_path, payload["composite_report"]["content"])
    knowledge_dir.mkdir(parents=True, exist_ok=True)
    _write_json(confluence_update_proposal_path, payload["knowledge_artifacts"]["confluence_update_proposal"])
    _write_json(concept_cards_path, payload["knowledge_artifacts"]["concept_cards"])
    _write_text(wiki_draft_path, payload["knowledge_artifacts"]["wiki_draft"]["content"])

    input_hash = hashlib.sha256(
        json.dumps(
            {
                "issue_key": issue_key,
                "policies": sorted(effective_policies),
                "top_k": top_k,
                "prompt_mode": prompt_mode,
                "snapshot_files": snapshot_file_hashes,
            },
            ensure_ascii=False,
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()
    manifest_path = run_dir / "run_manifest.json"
    artifacts = [
        build_artifact_record(
            artifact_type="deep_analysis_result",
            path=str(result_path),
            step_name="deep_analyze",
            step_version="v1",
            input_hash=input_hash,
            engine="pageindex",
            prompt_version=prompt_mode,
        ),
        build_artifact_record(
            artifact_type="shared_retrieval_bundle",
            path=str(shared_retrieval_bundle_path),
            step_name="shared_retrieval",
            step_version="v1",
            input_hash=input_hash,
            engine="pageindex",
            prompt_version=prompt_mode,
        ),
        *[
            build_artifact_record(
                artifact_type=f"section_output_{section_name}",
                path=str(section_outputs_dir / f"{section_name}.json"),
                step_name=f"section_runner_{section_name}",
                step_version=payload["section_outputs"][section_name]["runner_version"],
                input_hash=input_hash,
                depends_on=["shared_retrieval_bundle"],
                engine="pageindex",
                prompt_version=prompt_mode,
            )
            for section_name in sorted(payload["section_outputs"])
        ],
        build_artifact_record(
            artifact_type="composite_report",
            path=str(report_markdown_path),
            step_name="composite_report_builder",
            step_version="v1",
            input_hash=input_hash,
            depends_on=[f"section_output_{section_name}" for section_name in sorted(payload["section_outputs"])],
            engine="pageindex",
            prompt_version=prompt_mode,
        ),
        build_artifact_record(
            artifact_type="confluence_update_proposal",
            path=str(confluence_update_proposal_path),
            step_name="knowledge_compiler",
            step_version="v1",
            input_hash=input_hash,
            depends_on=["shared_retrieval_bundle", "composite_report"],
            engine="pageindex",
            prompt_version=prompt_mode,
        ),
        build_artifact_record(
            artifact_type="concept_cards",
            path=str(concept_cards_path),
            step_name="knowledge_compiler",
            step_version="v1",
            input_hash=input_hash,
            depends_on=["shared_retrieval_bundle", "composite_report"],
            engine="pageindex",
            prompt_version=prompt_mode,
        ),
        build_artifact_record(
            artifact_type="wiki_draft",
            path=str(wiki_draft_path),
            step_name="knowledge_compiler",
            step_version="v1",
            input_hash=input_hash,
            depends_on=["composite_report", "confluence_update_proposal", "concept_cards"],
            engine="pageindex",
            prompt_version=prompt_mode,
        ),
        build_artifact_record(
            artifact_type="run_manifest",
            path=str(manifest_path),
            step_name="deep_analyze_manifest",
            step_version="v1",
            input_hash=input_hash,
            depends_on=["deep_analysis_result", "wiki_draft"],
            engine="pageindex",
            prompt_version=prompt_mode,
        ),
    ]
    input_config = {
        "issue_key": issue_key,
        "policies": sorted(effective_policies),
        "top_k": top_k,
        "prompt_mode": prompt_mode,
        "snapshot_dir": str(active_snapshot_dir),
        "snapshot_files": snapshot_file_hashes,
    }
    if input_metadata:
        input_config.update(input_metadata)
    manifest = build_run_manifest(
        task_type="jira_deep_analysis",
        owner="workspace-operator",
        input_config=input_config,
        run_id=run_dir.name,
        status="completed",
        artifacts=artifacts,
    )
    manifest = update_checkpoint(
        manifest,
        "retrieval_ready",
        reached=True,
        artifact_types=["shared_retrieval_bundle"],
    )
    manifest = update_checkpoint(
        manifest,
        "analysis_ready",
        reached=True,
        artifact_types=[f"section_output_{section_name}" for section_name in sorted(payload["section_outputs"])],
    )
    manifest = update_checkpoint(
        manifest,
        "knowledge_ready",
        reached=True,
        artifact_types=["confluence_update_proposal", "concept_cards", "wiki_draft"],
    )
    write_run_manifest(manifest_path, manifest)
    return payload | {"run_dir": str(run_dir), "run_manifest_path": str(manifest_path)}


def control_workspace_run(
    workspace_dir: str | Path,
    run_ref: str | Path,
    *,
    action: str,
    requested_by: str = "workspace-operator",
    step_name: str | None = None,
    reason: str | None = None,
    execute: bool = False,
) -> dict:
    _load_workspace_config(workspace_dir)
    paths = workspace_paths(workspace_dir)
    run_dir = _resolve_run_dir(workspace_dir, run_ref)
    manifest = load_run_manifest(run_dir)

    if action == "stop":
        updated, event = request_stop(
            manifest,
            requested_by=requested_by,
            step_name=step_name or "manual",
            reason=reason,
        )
        return write_controlled_manifest(run_dir, updated, event)

    if action == "resume":
        updated, event = request_resume(
            manifest,
            requested_by=requested_by,
            reason=reason,
        )
        return write_controlled_manifest(run_dir, updated, event)

    if action == "rerun":
        rerun_manifest, event = build_rerun_manifest(
            manifest,
            requested_by=requested_by,
            reason=reason,
        )
        rerun_dir = paths["runs"] / rerun_manifest["run_id"]
        return write_controlled_manifest(rerun_dir, rerun_manifest, event) | {
            "source_run_dir": str(run_dir),
            "run_dir": str(rerun_dir),
        }

    if action == "rerun-section":
        if not step_name:
            raise ValueError("step_name is required when action=rerun-section")
        if execute:
            return execute_workspace_section_rerun(
                workspace_dir,
                run_dir,
                section_name=step_name,
                requested_by=requested_by,
                reason=reason,
            )
        updated, event = request_section_rerun(
            manifest,
            section_name=step_name,
            requested_by=requested_by,
            reason=reason,
        )
        return write_controlled_manifest(run_dir, updated, event)

    raise ValueError("action must be one of: stop, resume, rerun, rerun-section")


def sync_workspace_run_prefect_state(
    workspace_dir: str | Path,
    run_ref: str | Path,
    *,
    prefect_state: str,
    requested_by: str = "workspace-operator",
    flow_run_id: str | None = None,
    flow_name: str = "jira_deep_analysis",
    deployment_name: str | None = None,
    error: dict | None = None,
) -> dict:
    _load_workspace_config(workspace_dir)
    run_dir = _resolve_run_dir(workspace_dir, run_ref)
    manifest = load_run_manifest(run_dir)
    updated, event = apply_prefect_state(
        manifest,
        prefect_state=prefect_state,
        requested_by=requested_by,
        flow_run_id=flow_run_id,
        flow_name=flow_name,
        deployment_name=deployment_name,
        error=error,
    )
    return write_controlled_manifest(run_dir, updated, event)


def submit_workspace_run_to_prefect(
    workspace_dir: str | Path,
    run_ref: str | Path,
    *,
    deployment_name: str,
    flow_name: str = "jira_deep_analysis",
    requested_by: str = "workspace-operator",
    parameters: dict | None = None,
    timeout_seconds: float = 0,
    flow_run_name: str | None = None,
    tags: list[str] | None = None,
    idempotency_key: str | None = None,
    work_queue_name: str | None = None,
    job_variables: dict | None = None,
    adapter: RealPrefectTaskAdapter | None = None,
) -> dict:
    _load_workspace_config(workspace_dir)
    run_dir = _resolve_run_dir(workspace_dir, run_ref)
    manifest = load_run_manifest(run_dir)
    prefect_adapter = adapter or RealPrefectTaskAdapter(
        flow_name=flow_name,
        deployment_name=deployment_name,
    )
    updated, event = prefect_adapter.submit(
        manifest,
        requested_by=requested_by,
        parameters=parameters,
        timeout_seconds=timeout_seconds,
        flow_run_name=flow_run_name,
        tags=tags,
        idempotency_key=idempotency_key,
        work_queue_name=work_queue_name,
        job_variables=job_variables,
    )
    return write_controlled_manifest(run_dir, updated, event)


def _artifact_path_by_type(run_dir: Path, manifest: dict) -> dict[str, Path]:
    paths: dict[str, Path] = {}
    for artifact in manifest.get("artifacts", []):
        artifact_path = artifact.get("path")
        if artifact_path:
            path = Path(artifact_path)
            if path.is_absolute() or path.exists():
                paths[artifact["artifact_type"]] = path
            else:
                paths[artifact["artifact_type"]] = run_dir / path
    return paths


def _read_control_events(run_dir: Path) -> list[dict]:
    path = run_dir / "control-events.jsonl"
    if not path.exists():
        return []
    events: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            events.append(json.loads(line))
    return events


def _artifact_inventory(run_dir: Path, manifest: dict) -> list[dict]:
    artifact_paths = _artifact_path_by_type(run_dir, manifest)
    rows: list[dict] = []
    for artifact in manifest.get("artifacts", []):
        artifact_type = artifact["artifact_type"]
        path = artifact_paths.get(artifact_type)
        rows.append(
            {
                "artifact_type": artifact_type,
                "path": str(path) if path else artifact.get("path"),
                "exists": bool(path and path.exists()),
                "status": artifact.get("status"),
                "stale": bool(artifact.get("stale", False)),
                "step_name": artifact.get("step_name"),
                "step_version": artifact.get("step_version"),
                "depends_on": list(artifact.get("depends_on", [])),
            }
        )
    return rows


def _run_summary(run_dir: Path, manifest: dict) -> dict:
    checkpoints = manifest.get("checkpoints", {})
    reached_checkpoints = [
        name
        for name, checkpoint in checkpoints.items()
        if checkpoint.get("reached", False)
    ]
    artifacts = manifest.get("artifacts", [])
    input_config = manifest.get("input_config", {})
    return {
        "run_id": manifest["run_id"],
        "run_version": manifest["run_version"],
        "task_type": manifest["task_type"],
        "owner": manifest["owner"],
        "status": manifest["status"],
        "issue_key": input_config.get("issue_key") or input_config.get("jira_issue_key"),
        "updated_at": manifest.get("updated_at"),
        "run_dir": str(run_dir),
        "checkpoint_summary": {
            "reached": reached_checkpoints,
            "reached_count": len(reached_checkpoints),
            "total_count": len(checkpoints),
        },
        "artifact_count": len(artifacts),
        "stale_artifact_count": len([artifact for artifact in artifacts if artifact.get("stale", False)]),
    }


def list_workspace_runs(workspace_dir: str | Path) -> dict:
    _load_workspace_config(workspace_dir)
    paths = workspace_paths(workspace_dir)
    runs: list[dict] = []
    if paths["runs"].exists():
        for run_dir in sorted(paths["runs"].iterdir()):
            manifest_path = run_dir / "run_manifest.json"
            if run_dir.is_dir() and manifest_path.exists():
                runs.append(_run_summary(run_dir, load_run_manifest(run_dir)))
    runs.sort(key=lambda run: run.get("updated_at") or "", reverse=True)
    return {
        "workspace_dir": str(paths["root"]),
        "run_count": len(runs),
        "runs": runs,
    }


def inspect_workspace_run(workspace_dir: str | Path, run_ref: str | Path) -> dict:
    _load_workspace_config(workspace_dir)
    run_dir = _resolve_run_dir(workspace_dir, run_ref)
    manifest = load_run_manifest(run_dir)
    result_path = run_dir / "result.json"
    result = _read_json(result_path) if result_path.exists() else {}
    return {
        "run": _run_summary(run_dir, manifest),
        "manifest": manifest,
        "control_events": _read_control_events(run_dir),
        "artifact_inventory": _artifact_inventory(run_dir, manifest),
        "result_summary": {
            "exists": result_path.exists(),
            "issue_id": result.get("issue_id"),
            "title": result.get("title"),
            "analysis_profile": result.get("analysis_profile"),
            "section_names": sorted(result.get("section_outputs", {}).keys()),
            "knowledge_artifacts": sorted(result.get("knowledge_artifacts", {}).keys()),
        },
    }


def load_workspace_run_artifact(
    workspace_dir: str | Path,
    run_ref: str | Path,
    artifact_type: str,
) -> dict:
    _load_workspace_config(workspace_dir)
    run_dir = _resolve_run_dir(workspace_dir, run_ref)
    manifest = load_run_manifest(run_dir)
    artifact_paths = _artifact_path_by_type(run_dir, manifest)
    if artifact_type not in artifact_paths:
        raise ValueError(f"Unknown artifact type for run {manifest['run_id']}: {artifact_type}")
    path = artifact_paths[artifact_type]
    if not path.exists():
        raise ValueError(f"Artifact path does not exist for {artifact_type}: {path}")
    if path.suffix.lower() == ".json":
        return {
            "artifact_type": artifact_type,
            "path": str(path),
            "format": "json",
            "payload": _read_json(path),
        }
    return {
        "artifact_type": artifact_type,
        "path": str(path),
        "format": "text",
        "content": path.read_text(encoding="utf-8"),
    }


def _clear_rebuilt_artifact_staleness(manifest: dict, artifact_types: set[str]) -> dict:
    updated = json.loads(json.dumps(manifest))
    for artifact in updated.get("artifacts", []):
        if artifact.get("artifact_type") in artifact_types:
            artifact["stale"] = False
            artifact["status"] = "ready"
            artifact["created_at"] = _utc_now()
    updated["status"] = "completed"
    updated["updated_at"] = _utc_now()
    return updated


def execute_workspace_section_rerun(
    workspace_dir: str | Path,
    run_ref: str | Path,
    *,
    section_name: str,
    requested_by: str = "workspace-operator",
    reason: str | None = None,
) -> dict:
    _load_workspace_config(workspace_dir)
    run_dir = _resolve_run_dir(workspace_dir, run_ref)
    manifest = load_run_manifest(run_dir)
    invalidated_manifest, invalidation_event = request_section_rerun(
        manifest,
        section_name=section_name,
        requested_by=requested_by,
        reason=reason,
    )

    result_path = run_dir / "result.json"
    if not result_path.exists():
        raise ValueError(f"Cannot execute section rerun without result.json: {result_path}")
    payload = _read_json(result_path)
    section_retrieval_hooks = payload.get("section_retrieval_hooks", {})
    if section_name not in section_retrieval_hooks:
        raise ValueError(f"Unknown section in run payload: {section_name}")

    rebuilt_sections = build_section_outputs(
        issue_summary=payload["issue_summary"],
        shared_citations=payload["shared_retrieval_bundle"].get("citations", []),
        section_retrieval_hooks=section_retrieval_hooks,
        llm_backend=None,
    )
    section_outputs = dict(payload.get("section_outputs", {}))
    section_outputs[section_name] = rebuilt_sections[section_name]
    composite_content = build_composite_report_markdown(
        issue_id=payload["issue_id"],
        title=payload.get("title", payload["issue_id"]),
        section_outputs=section_outputs,
    )
    composite_report = {
        "format": "markdown",
        "content": composite_content,
    }
    knowledge_artifacts = build_knowledge_artifacts(
        jira_document={
            "document_id": payload["issue_id"],
            "title": payload.get("title", payload["issue_id"]),
        },
        shared_citations=payload["shared_retrieval_bundle"].get("citations", []),
        confluence_citations=payload.get("confluence_evidence", {}).get("citations", []),
        composite_report=composite_report,
    )

    artifact_paths = _artifact_path_by_type(run_dir, invalidated_manifest)
    target_section_path = artifact_paths.get(f"section_output_{section_name}") or (
        run_dir / "section_outputs" / f"{section_name}.json"
    )
    composite_report_path = artifact_paths.get("composite_report") or (run_dir / "report" / "report.md")
    confluence_update_proposal_path = artifact_paths.get("confluence_update_proposal") or (
        run_dir / "knowledge" / "confluence_update_proposal.json"
    )
    concept_cards_path = artifact_paths.get("concept_cards") or (run_dir / "knowledge" / "concept_cards.json")
    wiki_draft_path = artifact_paths.get("wiki_draft") or (run_dir / "knowledge" / "wiki_draft.md")

    _write_json(target_section_path, section_outputs[section_name])
    _write_text(composite_report_path, composite_report["content"])
    _write_json(confluence_update_proposal_path, knowledge_artifacts["confluence_update_proposal"])
    _write_json(concept_cards_path, knowledge_artifacts["concept_cards"])
    _write_text(wiki_draft_path, knowledge_artifacts["wiki_draft"]["content"])

    payload["section_outputs"] = section_outputs
    payload["composite_report"] = composite_report
    payload["knowledge_artifacts"] = knowledge_artifacts
    _write_json(result_path, payload)

    rebuilt_artifact_types = {
        "deep_analysis_result",
        f"section_output_{section_name}",
        "composite_report",
        "confluence_update_proposal",
        "concept_cards",
        "wiki_draft",
        "run_manifest",
    }
    completed_manifest = _clear_rebuilt_artifact_staleness(
        invalidated_manifest,
        rebuilt_artifact_types,
    )
    execution_event = build_control_event(
        manifest=completed_manifest,
        action="rerun_section",
        requested_by=requested_by,
        step_name=f"section_runner_{section_name}",
        reason=reason,
        result={
            **invalidation_event["result"],
            "executed": True,
            "rewritten_artifact_types": sorted(rebuilt_artifact_types - {"run_manifest"}),
        },
    )
    manifest_path = write_run_manifest(run_dir, completed_manifest)
    event_log_path = append_control_event(run_dir, execution_event)
    return {
        "run_id": completed_manifest["run_id"],
        "run_version": completed_manifest["run_version"],
        "status": completed_manifest["status"],
        "manifest_path": manifest_path,
        "control_event": execution_event,
        "control_event_log": event_log_path,
        "run_dir": str(run_dir),
    }

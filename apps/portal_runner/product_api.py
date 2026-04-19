from __future__ import annotations

from pathlib import Path
import json
import re

import yaml

from apps.portal.portal_state import build_portal_state
from services.analysis.llm_backends import build_llm_backend
from services.workspace import (
    add_workspace_selector,
    configure_workspace_source,
    fetch_workspace_source,
    init_workspace,
    inspect_workspace_run,
    list_workspace_selectors,
    list_workspace_profiles,
    list_workspace_runs,
    list_workspace_sources,
    load_workspace_run_artifact,
    run_workspace_analysis,
    status_workspace,
    show_workspace_selector,
    show_workspace_profile,
    test_workspace_source,
    update_workspace_profile,
    validate_workspace_profile,
    verify_workspace_run_with_llm,
)
from services.workspace.spec_assets import ingest_spec_asset, load_spec_asset_registry
from services.workspace.source_registry import (
    fetch_cache_status,
    load_source,
    write_run_profile,
    write_selector_profile,
    write_source,
)


SECRET_KEYS = {"token", "password", "api_key", "value"}


def create_workspace(root: str | Path, payload: dict) -> dict:
    name = _safe_name(str(payload.get("name") or "workspace"))
    workspace_dir = Path(root) / name
    result = init_workspace(workspace_dir)
    return {"name": name, **result}


def list_workspaces(root: str | Path, *, demo_workspace: dict | None = None) -> dict:
    workspace_root = Path(root)
    workspaces = []
    if demo_workspace:
        workspaces.append(demo_workspace)
    if workspace_root.exists():
        for config_path in sorted(workspace_root.glob("*/workspace.yaml")):
            if demo_workspace and str(config_path.parent) == str(demo_workspace.get("workspace_dir")):
                continue
            workspaces.append(
                {
                    "name": config_path.parent.name,
                    "workspace_dir": str(config_path.parent),
                    "mode": "real",
                    "setup_required": False,
                }
            )
    return {"workspaces": workspaces}


def workspace_status(workspace_dir: str | Path) -> dict:
    return status_workspace(workspace_dir)


def create_source(payload: dict) -> dict:
    workspace_dir = _required(payload, "workspace_dir")
    source_name = _safe_name(_required(payload, "name"))
    connector_type = _required(payload, "connector_type")
    kind = _kind_from_connector(connector_type)
    mode = payload.get("mode") or ("local" if kind == "pdf" else "live")
    config = {
        "auth_mode": payload.get("auth_mode") or "auto",
    }
    for key in ("base_url", "path", "username", "password", "token"):
        if payload.get(key):
            config[key] = payload[key]

    credential_ref = payload.get("credential_ref")
    if payload.get("token") and not credential_ref:
        credential_ref = f"{source_name}_token"
        _write_inline_credential(workspace_dir, credential_ref, str(payload["token"]))
        config.pop("token", None)

    source = {
        "version": 1,
        "name": source_name,
        "kind": kind,
        "mode": mode,
        "connector_type": connector_type,
        "credential_ref": credential_ref,
        "config": config,
        "defaults": _source_defaults(kind, payload.get("defaults", {})),
        "policies": list(payload.get("policies") or ["team:ssd", "public"]),
        "metadata": payload.get("metadata", {}),
        "enabled": bool(payload.get("enabled", True)),
    }
    write_source(workspace_dir, source)

    selector_payload = payload.get("selector")
    selector = None
    if isinstance(selector_payload, dict):
        selector_name = _safe_name(str(selector_payload.get("name") or f"{source_name}_selector"))
        selector = {
            "version": 1,
            "name": selector_name,
            "source": source_name,
            "selector": {
                key: value
                for key, value in selector_payload.items()
                if key != "name" and value not in (None, "")
            },
        }
        write_selector_profile(workspace_dir, selector)

    return _redact(
        {
            "workspace_dir": str(Path(workspace_dir)),
            "source": load_source(workspace_dir, source_name),
            "selector": selector,
        }
    )


def list_sources_response(workspace_dir: str | Path) -> dict:
    payload = list_workspace_sources(workspace_dir)
    selectors = list_workspace_selectors(workspace_dir)["selectors"]
    payload["selectors"] = selectors
    payload["sources"] = [
        _source_summary(workspace_dir, source, selectors)
        for source in payload["sources"]
    ]
    return _redact(payload)


def source_detail_response(workspace_dir: str | Path, source_name: str) -> dict:
    selectors = list_workspace_selectors(workspace_dir)["selectors"]
    source = _source_summary(workspace_dir, load_source(workspace_dir, source_name), selectors)
    return _redact({"workspace_dir": str(Path(workspace_dir)), "source": source})


def list_selectors_response(workspace_dir: str | Path) -> dict:
    return _redact(list_workspace_selectors(workspace_dir))


def selector_detail_response(workspace_dir: str | Path, selector_name: str) -> dict:
    return _redact(show_workspace_selector(workspace_dir, selector_name))


def create_selector(payload: dict) -> dict:
    selector = payload.get("selector") or {}
    if not isinstance(selector, dict):
        raise ValueError("selector must be an object")
    result = add_workspace_selector(
        _required(payload, "workspace_dir"),
        _safe_name(_required(payload, "name")),
        source=_required(payload, "source"),
        selector_type=_required(selector, "type"),
        issue_key=selector.get("issue_key"),
        project_key=selector.get("project_key"),
        project_keys=selector.get("project_keys"),
        issue_type=selector.get("issue_type"),
        status=selector.get("status"),
        label=selector.get("label"),
        updated_from=selector.get("updated_from"),
        updated_to=selector.get("updated_to"),
        page_id=selector.get("page_id"),
        root_page_id=selector.get("root_page_id"),
        max_depth=selector.get("max_depth"),
        space_key=selector.get("space_key"),
        modified_from=selector.get("modified_from"),
        modified_to=selector.get("modified_to"),
        ancestor_id=selector.get("ancestor_id"),
        title=selector.get("title"),
        page_ids=selector.get("page_ids"),
    )
    return _redact(result)


def update_source(source_name: str, payload: dict) -> dict:
    workspace_dir = _required(payload, "workspace_dir")
    result = configure_workspace_source(
        workspace_dir,
        source_name,
        base_url=payload.get("base_url"),
        auth_mode=payload.get("auth_mode"),
        path=payload.get("path"),
    )
    source = load_source(workspace_dir, source_name)
    if "enabled" in payload or "defaults" in payload:
        source["enabled"] = bool(payload.get("enabled", source.get("enabled", True)))
        defaults = dict(source.get("defaults", {}))
        defaults.update(payload.get("defaults") or {})
        source["defaults"] = _source_defaults(source["kind"], defaults)
        write_source(workspace_dir, source)
        result = {"workspace_dir": str(Path(workspace_dir)), "source": load_source(workspace_dir, source_name)}
    return _redact(result)


def test_source_response(source_name: str, payload: dict) -> dict:
    return _redact(
        test_workspace_source(
            _required(payload, "workspace_dir"),
            source_name,
            selector_profile=payload.get("selector_profile"),
        )
    )


def refresh_source_response(source_name: str, payload: dict) -> dict:
    return _redact(
        fetch_workspace_source(
            _required(payload, "workspace_dir"),
            source_name=source_name,
            selector_profile=_required(payload, "selector_profile"),
        )
    )


def create_profile(payload: dict) -> dict:
    workspace_dir = _required(payload, "workspace_dir")
    profile_name = _safe_name(_required(payload, "name"))
    inputs = dict(payload.get("inputs") or {})
    if payload.get("spec_asset_ids") is not None:
        inputs["spec_assets"] = list(payload.get("spec_asset_ids") or [])
    profile = {
        "version": 1,
        "name": profile_name,
        "inputs": inputs,
        "analysis": {
            "top_k": int(payload.get("analysis", {}).get("top_k", 5)),
            "policies": list(payload.get("analysis", {}).get("policies", ["team:ssd", "public"])),
            "llm_backend": payload.get("analysis", {}).get("llm_backend", "none"),
            "llm_prompt_mode": payload.get("analysis", {}).get("llm_prompt_mode", "strict"),
        },
    }
    for key in ("llm_model", "llm_base_url", "llm_api_key", "llm_timeout_seconds"):
        if payload.get("analysis", {}).get(key) is not None:
            profile["analysis"][key] = payload["analysis"][key]
    path = write_run_profile(workspace_dir, profile)
    return _redact({"workspace_dir": str(Path(workspace_dir)), "path": path, "profile": profile})


def list_profiles_response(workspace_dir: str | Path) -> dict:
    return _redact(list_workspace_profiles(workspace_dir))


def profile_detail_response(workspace_dir: str | Path, profile_name: str) -> dict:
    return _redact(show_workspace_profile(workspace_dir, profile_name))


def duplicate_profile(profile_name: str, payload: dict) -> dict:
    workspace_dir = _required(payload, "workspace_dir")
    duplicate_name = _safe_name(_required(payload, "name"))
    source_profile = show_workspace_profile(workspace_dir, profile_name)["profile"]
    copied = json.loads(json.dumps(source_profile))
    copied["name"] = duplicate_name
    path = write_run_profile(workspace_dir, copied)
    return _redact({"workspace_dir": str(Path(workspace_dir)), "path": path, "profile": copied})


def update_profile(profile_name: str, payload: dict) -> dict:
    analysis = payload.get("analysis") or {}
    result = update_workspace_profile(
        _required(payload, "workspace_dir"),
        profile_name,
        input_bindings=payload.get("inputs"),
        replace_inputs=payload.get("inputs") is not None,
        spec_asset_ids=payload.get("spec_asset_ids"),
        top_k=analysis.get("top_k"),
        policies=analysis.get("policies"),
        llm_backend=analysis.get("llm_backend"),
        llm_model=analysis.get("llm_model"),
        llm_prompt_mode=analysis.get("llm_prompt_mode"),
    )
    return _redact(result)


def set_default_profile(profile_name: str, payload: dict) -> dict:
    workspace_dir = Path(_required(payload, "workspace_dir"))
    config_path = workspace_dir / "workspace.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    config["default_profile"] = profile_name
    config_path.write_text(yaml.safe_dump(config, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return {"workspace_dir": str(workspace_dir), "default_profile": profile_name}


def validate_profile_response(profile_name: str, payload: dict) -> dict:
    return _redact(validate_workspace_profile(_required(payload, "workspace_dir"), profile_name))


def analyze_jira_response(payload: dict) -> dict:
    workspace_dir = _required(payload, "workspace_dir")
    profile = _required(payload, "profile")
    issue_key = _required(payload, "issue_key")
    analysis = run_workspace_analysis(
        workspace_dir,
        profile_name=profile,
        issue_key=issue_key,
    )
    state = build_portal_state(query=issue_key, workspace_dir=workspace_dir)
    return shape_analyze_response(analysis=analysis, portal_state=state)


def shape_analyze_response(*, analysis: dict, portal_state: dict) -> dict:
    result = analysis.get("analysis", analysis)
    run_dir = Path(result.get("run_dir") or "")
    run_id = run_dir.name if str(run_dir) else ""
    section_outputs = result.get("section_outputs", {})
    shared_bundle = result.get("shared_retrieval_bundle", {})
    citations = _collect_citations(shared_bundle, section_outputs)
    knowledge = result.get("knowledge_artifacts", {})
    summary = {
        "issue_id": result.get("issue_id"),
        "title": result.get("title"),
        "profile": analysis.get("profile") or result.get("analysis_profile"),
        "answer": result.get("answer", {}).get("text"),
    }
    artifacts = {
        "run_manifest": result.get("run_manifest_path"),
        "run_dir": result.get("run_dir"),
        "knowledge": sorted(knowledge.keys()) if isinstance(knowledge, dict) else [],
    }
    evidence_coverage = _evidence_coverage(shared_bundle, result)
    return {
        "run_id": run_id,
        "status": "completed",
        "issue_key": result.get("issue_id"),
        "profile": analysis.get("profile") or result.get("analysis_profile"),
        "summary": summary,
        "sections": section_outputs,
        "citations": citations,
        "evidence_coverage": evidence_coverage,
        "evidence_sources": sorted(shared_bundle.get("source_breakdown", {}).keys()),
        "missing_evidence": [],
        "artifacts": artifacts,
        "portal_state": portal_state,
        "analysis": analysis,
    }


def workspace_runs_response(workspace_dir: str | Path) -> dict:
    return list_workspace_runs(workspace_dir)


def workspace_run_detail_response(workspace_dir: str | Path, run_id: str) -> dict:
    return inspect_workspace_run(workspace_dir, run_id)


def workspace_artifact_response(workspace_dir: str | Path, run_id: str, artifact_type: str) -> dict:
    return load_workspace_run_artifact(workspace_dir, run_id, artifact_type)


def verify_run_llm_response(run_id: str, payload: dict) -> dict:
    backend = build_llm_backend(
        backend=payload.get("llm_backend", "openai-compatible"),
        model=payload.get("llm_model"),
        base_url=payload.get("llm_base_url"),
        api_key=payload.get("llm_api_key"),
        mock_response=payload.get("llm_mock_response"),
        timeout_seconds=int(payload.get("llm_timeout_seconds", 600)),
    )
    if backend is None:
        raise ValueError("llm_backend must be ollama, openai-compatible, or mock")
    return _redact(
        verify_workspace_run_with_llm(
            _required(payload, "workspace_dir"),
            run_id,
            llm_backend=backend,
        )
    )


def require_mineru_spec_asset(workspace_dir: str | Path, asset_id: str) -> dict:
    registry = load_spec_asset_registry(workspace_dir)
    matches = [entry for entry in registry.get("assets", []) if entry.get("asset_id") == asset_id]
    if not matches:
        raise ValueError(f"Spec asset is missing: {asset_id}. Parse the NVMe PDF once with MinerU before using this profile.")
    selected = sorted(matches, key=lambda entry: str(entry.get("version", "")))[-1]
    if selected.get("parser_used") != "mineru":
        raise ValueError(f"Spec asset {asset_id} must be parsed with MinerU; found {selected.get('parser_used') or 'unknown'}.")
    return {"workspace_dir": str(Path(workspace_dir)), "asset": selected, "ok": True}


def list_spec_assets_response(workspace_dir: str | Path) -> dict:
    registry = load_spec_asset_registry(workspace_dir)
    return {"workspace_dir": str(Path(workspace_dir)), "assets": registry.get("assets", [])}


def ingest_mineru_spec_asset(payload: dict) -> dict:
    result = ingest_spec_asset(
        _required(payload, "workspace_dir"),
        spec_pdf=_required(payload, "spec_pdf"),
        asset_id=payload.get("asset_id") or "nvme-spec-mineru",
        display_name=payload.get("display_name") or "NVMe Spec",
        preferred_parser="mineru",
        mineru_python_exe=payload.get("mineru_python_exe"),
    )
    if result.get("parser_used") != "mineru":
        raise ValueError(f"MinerU parsing is required; parser_used={result.get('parser_used') or 'unknown'}")
    return result


def _collect_citations(shared_bundle: dict, section_outputs: dict) -> list[dict]:
    seen = set()
    citations = []
    for citation in shared_bundle.get("citations", []):
        key = json.dumps(citation, sort_keys=True, ensure_ascii=False)
        if key not in seen:
            seen.add(key)
            citations.append(citation)
    for section in section_outputs.values():
        for citation in section.get("citations", []):
            key = json.dumps(citation, sort_keys=True, ensure_ascii=False)
            if key not in seen:
                seen.add(key)
                citations.append(citation)
    return citations


def _evidence_coverage(shared_bundle: dict, result: dict) -> dict:
    source_breakdown = shared_bundle.get("source_breakdown", {})
    confluence_count = int(source_breakdown.get("confluence", {}).get("result_count", 0) or 0)
    spec_count = sum(
        int(payload.get("result_count", 0) or 0)
        for source_type, payload in source_breakdown.items()
        if source_type not in {"jira", "confluence"}
    )
    jira_found = bool(result.get("issue_id"))
    missing = []
    if not confluence_count:
        missing.append("confluence")
    if not spec_count:
        missing.append("spec")
    return {
        "jira_found": jira_found,
        "confluence_count": confluence_count,
        "spec_count": spec_count,
        "missing": missing,
        "source_breakdown": source_breakdown,
    }


def _source_summary(workspace_dir: str | Path, source: dict, selectors: list[dict]) -> dict:
    status_by_source = {row["source_name"]: row for row in fetch_cache_status(workspace_dir)}
    status = status_by_source.get(source["name"], {"status": "stale", "reason": "missing_fetch_manifest"})
    manifest = _source_fetch_manifest(workspace_dir, source)
    selector = next((row for row in selectors if row.get("source") == source["name"]), None)
    return {
        **source,
        "status": status.get("status"),
        "status_reason": status.get("reason"),
        "last_refresh": manifest.get("fetched_at"),
        "document_count": int(manifest.get("document_count", 0) or 0),
        "selector": selector,
        "enabled": bool(source.get("enabled", True)),
    }


def _source_fetch_manifest(workspace_dir: str | Path, source: dict) -> dict:
    path = Path(workspace_dir) / "raw" / source["kind"] / "payloads" / source["name"] / "fetch-manifest.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write_inline_credential(workspace_dir: str | Path, name: str, value: str) -> None:
    path = Path(workspace_dir) / ".local" / "credentials.yaml"
    if path.exists():
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    else:
        payload = {"version": 1, "credentials": {}}
    payload.setdefault("version", 1)
    payload.setdefault("credentials", {})
    payload["credentials"][name] = {"type": "bearer_inline", "value": value}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False, allow_unicode=True), encoding="utf-8")


def _source_defaults(kind: str, defaults: dict) -> dict:
    result = {
        "include_comments": bool(defaults.get("include_comments", True)),
        "include_attachments": bool(defaults.get("include_attachments", True)),
        "include_image_metadata": bool(defaults.get("include_image_metadata", True)),
        "download_images": bool(defaults.get("download_images", False)),
        "fetch_backend": defaults.get("fetch_backend", "atlassian-api"),
    }
    if defaults.get("page_size") is not None:
        result["page_size"] = int(defaults["page_size"])
    if kind == "pdf":
        result["preferred_parser"] = defaults.get("preferred_parser", "mineru")
    return result


def _kind_from_connector(connector_type: str) -> str:
    if connector_type.startswith("jira."):
        return "jira"
    if connector_type.startswith("confluence."):
        return "confluence"
    if connector_type.startswith("pdf."):
        return "pdf"
    raise ValueError(f"Unsupported connector_type: {connector_type}")


def _safe_name(value: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "-", value.strip()).strip(".-")
    if not safe:
        raise ValueError("name is required")
    return safe


def _required(payload: dict, key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} is required")
    return value.strip()


def _redact(value: object) -> object:
    if isinstance(value, dict):
        return {
            key: "***" if key in SECRET_KEYS and item else _redact(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value

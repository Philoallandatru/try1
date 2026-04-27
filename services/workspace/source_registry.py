from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path

import yaml


SOURCE_KINDS = {"jira", "confluence", "pdf"}
SOURCE_MODES = {"fixture", "live", "local"}
CONNECTOR_TYPES = {
    "jira.atlassian_api": "jira",
    "confluence.atlassian_api": "confluence",
    "pdf.local_file": "pdf",
}
JIRA_SELECTORS = {"issue", "project_slice", "project_full"}
CONFLUENCE_SELECTORS = {"page", "page_tree", "space_slice"}
PDF_SELECTORS = {"file"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def registry_paths(workspace_dir: str | Path) -> dict[str, Path]:
    root = Path(workspace_dir)
    return {
        "root": root,
        "sources": root / "sources",
        "selectors": root / "selectors",
        "profiles": root / "profiles",
        "credentials": root / ".local" / "credentials.yaml",
        "credentials_example": root / ".local" / "credentials.example.yaml",
    }


def _read_yaml(path: str | Path) -> dict:
    payload = yaml.safe_load(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"YAML file must contain a mapping: {path}")
    return payload


def _write_yaml(path: str | Path, payload: dict) -> str:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(yaml.safe_dump(payload, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return str(target)


def _load_spec_asset_registry(workspace_dir: str | Path) -> dict:
    path = Path(workspace_dir) / "raw" / "files" / "spec_assets" / "registry.json"
    if not path.exists():
        return {"assets": []}
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"Spec asset registry must contain an object: {path}")
    return payload


def _known_spec_asset_ids(workspace_dir: str | Path) -> set[str]:
    return {
        str(entry.get("asset_id"))
        for entry in _load_spec_asset_registry(workspace_dir).get("assets", [])
        if isinstance(entry, dict) and entry.get("asset_id")
    }


def _json_hash(payload: dict) -> str:
    data = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"sha256:{hashlib.sha256(data).hexdigest()}"


def config_hash(source: dict) -> str:
    return _json_hash(
        {
            "version": source.get("version"),
            "mode": source.get("mode", "live"),
            "kind": source.get("kind"),
            "connector_type": source.get("connector_type"),
            "credential_ref": source.get("credential_ref"),
            "config": source.get("config", {}),
            "defaults": source.get("defaults", {}),
            "selector_defaults": source.get("selector_defaults", {}),
            "policies": source.get("policies", []),
        }
    )


def selector_hash(selector_profile: dict) -> str:
    return _json_hash(
        {
            "version": selector_profile.get("version"),
            "source": selector_profile.get("source"),
            "selector": selector_profile.get("selector", {}),
        }
    )


def _validate_name(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} is required")
    if any(char in value for char in "\\/:*?\"<>|"):
        raise ValueError(f"{field} contains an unsafe path character: {value}")
    return value


def _validate_selector(kind: str, selector: dict) -> None:
    selector_type = selector.get("type")
    if kind == "jira":
        if selector_type not in JIRA_SELECTORS:
            raise ValueError("jira selector.type must be one of: issue, project_slice, project_full")
        if selector_type == "issue" and not selector.get("issue_key"):
            raise ValueError("jira issue selector requires issue_key")
        if selector_type in {"project_slice", "project_full"} and not (
            selector.get("project_key") or selector.get("project_keys")
        ):
            raise ValueError("jira project selector requires project_key or project_keys")
    if kind == "confluence":
        if selector_type not in CONFLUENCE_SELECTORS:
            raise ValueError("confluence selector.type must be one of: page, page_tree, space_slice")
        if selector_type == "page" and not selector.get("page_id"):
            raise ValueError("confluence page selector requires page_id")
        if selector_type == "page_tree" and not selector.get("root_page_id"):
            raise ValueError("confluence page_tree selector requires root_page_id")
        if selector_type == "space_slice" and not selector.get("space_key"):
            raise ValueError("confluence space_slice selector requires space_key")
    if kind == "pdf":
        if selector_type not in PDF_SELECTORS:
            raise ValueError("pdf selector.type must be: file")


def validate_source(source: dict) -> dict:
    if source.get("version") != 1:
        raise ValueError("source.version must be 1")
    name = _validate_name(source.get("name"), "source.name")
    kind = source.get("kind")
    mode = source.get("mode", "live")
    connector_type = source.get("connector_type")
    if kind not in SOURCE_KINDS:
        raise ValueError("source.kind must be one of: jira, confluence, pdf")
    if mode not in SOURCE_MODES:
        raise ValueError("source.mode must be one of: fixture, live, local")
    if connector_type not in CONNECTOR_TYPES:
        raise ValueError("source.connector_type must be one of: jira.atlassian_api, confluence.atlassian_api, pdf.local_file")
    if CONNECTOR_TYPES[connector_type] != kind:
        raise ValueError("source.kind must match connector_type")

    config = source.get("config", {})
    if not isinstance(config, dict):
        raise ValueError("source.config must be an object")
    if mode == "live" and not config.get("base_url"):
        raise ValueError("source.config.base_url is required for live sources")
    if mode in {"fixture", "local"} and not config.get("path"):
        raise ValueError("source.config.path is required for fixture sources")

    selector_defaults = source.get("selector_defaults", {})
    if selector_defaults:
        _validate_selector(kind, selector_defaults)

    normalized = dict(source)
    normalized["name"] = name
    normalized["mode"] = mode
    normalized.setdefault("defaults", {})
    normalized.setdefault("policies", [])
    normalized.setdefault("metadata", {})
    normalized.setdefault("enabled", True)
    return normalized


def validate_selector_profile(workspace_dir: str | Path, selector_profile: dict) -> dict:
    if selector_profile.get("version") != 1:
        raise ValueError("selector.version must be 1")
    name = _validate_name(selector_profile.get("name"), "selector.name")
    source_name = _validate_name(selector_profile.get("source"), "selector.source")
    source = load_source(workspace_dir, source_name)
    selector = selector_profile.get("selector", {})
    if not isinstance(selector, dict):
        raise ValueError("selector.selector must be an object")
    _validate_selector(source["kind"], selector)
    normalized = dict(selector_profile)
    normalized["name"] = name
    normalized["source"] = source_name
    return normalized


def validate_run_profile(workspace_dir: str | Path, run_profile: dict) -> dict:
    if run_profile.get("version") != 1:
        raise ValueError("profile.version must be 1")
    name = _validate_name(run_profile.get("name"), "profile.name")
    inputs = run_profile.get("inputs", {})
    if not isinstance(inputs, dict) or not inputs:
        raise ValueError("profile.inputs must be a non-empty object")
    for input_name, input_config in inputs.items():
        if not isinstance(input_name, str):
            raise ValueError("profile.inputs entries must be named objects")
        if input_name == "spec_assets":
            if not isinstance(input_config, list) or any(not isinstance(asset_id, str) or not asset_id.strip() for asset_id in input_config):
                raise ValueError("profile.inputs.spec_assets must be a list of asset ids")
            known_asset_ids = _known_spec_asset_ids(workspace_dir)
            unknown_asset_ids = sorted(asset_id for asset_id in input_config if asset_id not in known_asset_ids)
            if unknown_asset_ids:
                raise ValueError(f"Unknown spec asset ids: {', '.join(unknown_asset_ids)}")
            continue
        if input_name == "document_assets":
            if not isinstance(input_config, list) or any(not isinstance(doc_id, str) or not doc_id.strip() for doc_id in input_config):
                raise ValueError("profile.inputs.document_assets must be a list of document ids")
            # Document assets are validated at runtime when building workspace
            continue
        if not isinstance(input_config, dict):
            raise ValueError("profile.inputs entries must be named objects")
        source_name = _validate_name(input_config.get("source"), f"profile.inputs.{input_name}.source")
        selector_name = _validate_name(
            input_config.get("selector_profile"),
            f"profile.inputs.{input_name}.selector_profile",
        )
        load_source(workspace_dir, source_name)
        selector_profile = load_selector_profile(workspace_dir, selector_name)
        if selector_profile["source"] != source_name:
            raise ValueError(f"profile input {input_name} selector does not belong to source {source_name}")
    analysis = run_profile.get("analysis", {})
    if not isinstance(analysis, dict):
        raise ValueError("profile.analysis must be an object")
    normalized = dict(run_profile)
    normalized["name"] = name
    normalized.setdefault("analysis", {})
    return normalized


def write_source(workspace_dir: str | Path, source: dict) -> str:
    normalized = validate_source(source)
    return _write_yaml(registry_paths(workspace_dir)["sources"] / f"{normalized['name']}.yaml", normalized)


def load_source(workspace_dir: str | Path, name: str) -> dict:
    source_name = _validate_name(name, "source.name")
    path = registry_paths(workspace_dir)["sources"] / f"{source_name}.yaml"
    if not path.exists():
        raise ValueError(f"Unknown source: {source_name}")
    return validate_source(_read_yaml(path))


def list_sources(workspace_dir: str | Path) -> list[dict]:
    source_dir = registry_paths(workspace_dir)["sources"]
    if not source_dir.exists():
        return []
    return [load_source(workspace_dir, path.stem) for path in sorted(source_dir.glob("*.yaml"))]


def write_selector_profile(workspace_dir: str | Path, selector_profile: dict) -> str:
    normalized = validate_selector_profile(workspace_dir, selector_profile)
    return _write_yaml(registry_paths(workspace_dir)["selectors"] / f"{normalized['name']}.yaml", normalized)


def load_selector_profile(workspace_dir: str | Path, name: str) -> dict:
    selector_name = _validate_name(name, "selector.name")
    path = registry_paths(workspace_dir)["selectors"] / f"{selector_name}.yaml"
    if not path.exists():
        raise ValueError(f"Unknown selector profile: {selector_name}")
    return validate_selector_profile(workspace_dir, _read_yaml(path))


def list_selector_profiles(workspace_dir: str | Path) -> list[dict]:
    selector_dir = registry_paths(workspace_dir)["selectors"]
    if not selector_dir.exists():
        return []
    return [load_selector_profile(workspace_dir, path.stem) for path in sorted(selector_dir.glob("*.yaml"))]


def write_run_profile(workspace_dir: str | Path, run_profile: dict) -> str:
    normalized = validate_run_profile(workspace_dir, run_profile)
    return _write_yaml(registry_paths(workspace_dir)["profiles"] / f"{normalized['name']}.yaml", normalized)


def load_run_profile(workspace_dir: str | Path, name: str) -> dict:
    profile_name = _validate_name(name, "profile.name")
    path = registry_paths(workspace_dir)["profiles"] / f"{profile_name}.yaml"
    if not path.exists():
        raise ValueError(f"Unknown run profile: {profile_name}")
    return validate_run_profile(workspace_dir, _read_yaml(path))


def list_run_profiles(workspace_dir: str | Path) -> list[dict]:
    profile_dir = registry_paths(workspace_dir)["profiles"]
    if not profile_dir.exists():
        return []
    return [load_run_profile(workspace_dir, path.stem) for path in sorted(profile_dir.glob("*.yaml"))]


def write_credentials_example(workspace_dir: str | Path) -> str:
    return _write_yaml(
        registry_paths(workspace_dir)["credentials_example"],
        {
            "version": 1,
            "credentials": {
                "jira_lab_token": {"type": "bearer_env", "env": "JIRA_TOKEN"},
                "conf_fw_token": {"type": "bearer_env", "env": "CONF_TOKEN"},
            },
        },
    )


def resolve_credential(workspace_dir: str | Path, credential_ref: str | None) -> dict:
    if not credential_ref:
        return {}
    path = registry_paths(workspace_dir)["credentials"]
    if not path.exists():
        raise ValueError(f"Credential file not found: {path}")
    payload = _read_yaml(path)
    credential = payload.get("credentials", {}).get(credential_ref)
    if not credential:
        raise ValueError(f"Unknown credential: {credential_ref}")
    if credential.get("type") == "bearer_inline":
        value = credential.get("value")
        if not value:
            raise ValueError(f"Inline bearer credential is empty: {credential_ref}")
        return {"auth_mode": "bearer", "token": str(value)}
    if credential.get("type") != "bearer_env":
        raise ValueError("Only bearer_env and bearer_inline credentials are supported in registry v1")
    env_name = credential.get("env")
    token = os.environ.get(env_name or "")
    if not token:
        raise ValueError(f"Environment variable is not set for credential {credential_ref}: {env_name}")
    return {"auth_mode": "bearer", "token": token}


def _fetch_flags(source: dict) -> dict:
    defaults = source.get("defaults", {})
    return {
        "fetch_backend": defaults.get("fetch_backend", "atlassian-api"),
        "include_comments": bool(defaults.get("include_comments", True)),
        "include_attachments": bool(defaults.get("include_attachments", True)),
        "include_image_metadata": bool(defaults.get("include_image_metadata", True)),
        "download_images": bool(defaults.get("download_images", False)),
        "page_size": int(defaults.get("page_size", 50 if source["kind"] == "jira" else 25)),
        "insecure": bool(defaults.get("insecure", False)),
    }


def build_fetch_request(
    workspace_dir: str | Path,
    *,
    source_name: str,
    selector_profile: str,
    resolve_credentials: bool = True,
) -> dict:
    source = load_source(workspace_dir, source_name)
    if not source.get("enabled", True):
        raise ValueError(f"Source is disabled: {source_name}")
    selector = load_selector_profile(workspace_dir, selector_profile)
    merged_selector = dict(source.get("selector_defaults", {}))
    merged_selector.update(selector.get("selector", {}))
    _validate_selector(source["kind"], merged_selector)

    mode = source.get("mode", "live")
    config = source.get("config", {})
    fetch_flags = _fetch_flags(source)
    kwargs = {
        "kind": source["kind"],
        "path": config.get("path") if mode == "fixture" else None,
        "live": mode == "live",
        "base_url": config.get("base_url"),
        "username": config.get("username"),
        "password": config.get("password"),
        "token": config.get("token"),
        "auth_mode": config.get("auth_mode", "auto"),
        "cursor": None,
        "page_size": fetch_flags["page_size"],
        "jql": config.get("jql", "order by updated asc"),
        "cql": config.get("cql"),
        "space_key": merged_selector.get("space_key") or config.get("space_key"),
        "insecure": fetch_flags["insecure"],
        "fetch_backend": fetch_flags["fetch_backend"],
        "include_comments": fetch_flags["include_comments"],
        "include_attachments": fetch_flags["include_attachments"],
        "include_image_metadata": fetch_flags["include_image_metadata"],
        "download_images": fetch_flags["download_images"],
        "image_download_dir": source.get("defaults", {}).get("image_download_dir"),
    }
    if resolve_credentials:
        kwargs.update(resolve_credential(workspace_dir, source.get("credential_ref")))

    selector_type = merged_selector.get("type")
    if source["kind"] == "jira":
        if selector_type == "jql_query":
            # 直接使用 JQL 查询
            kwargs["jql"] = merged_selector.get("jql", "order by updated asc")
        elif selector_type == "issue":
            kwargs["issue_key"] = merged_selector.get("issue_key")
        else:
            kwargs["project_key"] = merged_selector.get("project_key")
            kwargs["project_keys"] = merged_selector.get("project_keys")
            kwargs["issue_type"] = merged_selector.get("issue_type")
            kwargs["status"] = merged_selector.get("status")
            kwargs["label"] = merged_selector.get("label")
            kwargs["updated_from"] = merged_selector.get("updated_from")
            kwargs["updated_to"] = merged_selector.get("updated_to")

    if source["kind"] == "confluence":
        if selector_type == "cql_query":
            # 直接使用 CQL 查询
            if merged_selector.get("cql"):
                kwargs["cql"] = merged_selector.get("cql")
            if merged_selector.get("space_key"):
                kwargs["space_key"] = merged_selector.get("space_key")
        elif selector_type == "page":
            kwargs["page_id"] = merged_selector.get("page_id")
        elif selector_type == "page_tree":
            kwargs["root_page_id"] = merged_selector.get("root_page_id")
            kwargs["include_descendants"] = True
            kwargs["max_depth"] = merged_selector.get("max_depth")
        elif selector_type == "space_slice":
            kwargs["space_key"] = merged_selector.get("space_key")
            kwargs["label"] = merged_selector.get("label")
            kwargs["modified_from"] = merged_selector.get("modified_from")
            kwargs["modified_to"] = merged_selector.get("modified_to")
        kwargs["ancestor_id"] = merged_selector.get("ancestor_id")
        kwargs["title"] = merged_selector.get("title")
        kwargs["page_ids"] = merged_selector.get("page_ids")

    if source["kind"] == "pdf":
        kwargs["path"] = config.get("path")
        kwargs["live"] = False

    return {
        "source": source,
        "selector_profile": selector,
        "kwargs": kwargs,
        "manifest": {
            "source_name": source["name"],
            "selector_profile": selector["name"],
            "connector_type": source["connector_type"],
            "config_hash": config_hash(source),
            "selector_hash": selector_hash(selector),
            "requested_at": _utc_now(),
        },
    }


def fetch_cache_status(workspace_dir: str | Path) -> list[dict]:
    rows: list[dict] = []
    for source in list_sources(workspace_dir):
        source_name = source["name"]
        source_kind = source["kind"]
        if not source.get("enabled", True):
            rows.append({"source_name": source_name, "status": "disabled", "reason": "source_disabled"})
            continue
        manifest_path = Path(workspace_dir) / "raw" / source_kind / "payloads" / source_name / "fetch-manifest.json"
        if not manifest_path.exists():
            rows.append({"source_name": source_name, "status": "stale", "reason": "missing_fetch_manifest"})
            continue
        manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
        current_hash = config_hash(source)
        if manifest.get("config_hash") != current_hash:
            rows.append({"source_name": source_name, "status": "stale", "reason": "source_config_changed"})
            continue
        selector_name = manifest.get("selector_profile")
        if selector_name:
            try:
                selector = load_selector_profile(workspace_dir, selector_name)
            except ValueError:
                rows.append({"source_name": source_name, "status": "stale", "reason": "selector_missing"})
                continue
            if manifest.get("selector_hash") != selector_hash(selector):
                rows.append({"source_name": source_name, "status": "stale", "reason": "selector_changed"})
                continue
        fetched_at = manifest.get("fetched_at")
        refresh_freq = source.get("defaults", {}).get("refresh_freq_minutes")
        if fetched_at and refresh_freq is not None:
            try:
                fetched_time = datetime.fromisoformat(str(fetched_at).replace("Z", "+00:00"))
                age_seconds = (datetime.now(timezone.utc) - fetched_time).total_seconds()
                if age_seconds > int(refresh_freq) * 60:
                    rows.append({"source_name": source_name, "status": "stale", "reason": "refresh_expired"})
                    continue
            except ValueError:
                rows.append({"source_name": source_name, "status": "stale", "reason": "invalid_fetched_at"})
                continue
        if manifest.get("latest_payload_path") and not Path(manifest["latest_payload_path"]).exists():
            rows.append({"source_name": source_name, "status": "stale", "reason": "latest_payload_missing"})
        else:
            rows.append({"source_name": source_name, "status": "fresh", "reason": "config_hash_matches"})
    return rows

from __future__ import annotations

from pathlib import Path
import json
import shutil

from services.workspace import init_workspace
from services.workspace.source_registry import write_run_profile, write_selector_profile, write_source
from services.workspace.spec_assets import load_spec_asset_registry


DEMO_WORKSPACE_NAME = "demo"
DEMO_SPEC_ASSET_ID = "nvme-spec-mineru"


def ensure_demo_workspace(root: str | Path, spec_assets_workspace: str | Path) -> dict:
    workspace_dir = Path(root) / DEMO_WORKSPACE_NAME
    init_workspace(workspace_dir)
    _write_demo_sources(workspace_dir)
    spec_asset = _copy_mineru_spec_asset(
        spec_assets_workspace=spec_assets_workspace,
        target_workspace=workspace_dir,
    )
    setup_required = spec_asset is None
    if spec_asset:
        _write_demo_profile(workspace_dir)
    return {
        "name": DEMO_WORKSPACE_NAME,
        "workspace_dir": str(workspace_dir),
        "mode": "demo",
        "setup_required": setup_required,
        "missing_spec_asset": None if spec_asset else DEMO_SPEC_ASSET_ID,
        "spec_asset": spec_asset,
    }


def _write_demo_sources(workspace_dir: Path) -> None:
    write_source(
        workspace_dir,
        {
            "version": 1,
            "name": "demo_jira",
            "kind": "jira",
            "mode": "fixture",
            "connector_type": "jira.atlassian_api",
            "config": {"path": "fixtures/demo/jira/nvme_demo_sync.json", "auth_mode": "auto"},
            "defaults": {"fetch_backend": "atlassian-api", "include_comments": True, "include_attachments": True},
            "policies": ["team:ssd", "public"],
            "metadata": {"description": "Demo Jira issues for NVMe analysis"},
            "enabled": True,
        },
    )
    write_selector_profile(
        workspace_dir,
        {
            "version": 1,
            "name": "demo_jira_project",
            "source": "demo_jira",
            "selector": {"type": "project_slice", "project_key": "SSD"},
        },
    )
    write_source(
        workspace_dir,
        {
            "version": 1,
            "name": "demo_confluence",
            "kind": "confluence",
            "mode": "fixture",
            "connector_type": "confluence.atlassian_api",
            "config": {"path": "fixtures/demo/confluence/nvme_demo_pages.json", "auth_mode": "auto"},
            "defaults": {"fetch_backend": "atlassian-api", "include_attachments": True},
            "policies": ["team:ssd", "public"],
            "metadata": {"description": "Demo Confluence evidence pages for NVMe analysis"},
            "enabled": True,
        },
    )
    write_selector_profile(
        workspace_dir,
        {
            "version": 1,
            "name": "demo_confluence_space",
            "source": "demo_confluence",
            "selector": {"type": "space_slice", "space_key": "SSDENG"},
        },
    )


def _write_demo_profile(workspace_dir: Path) -> None:
    write_run_profile(
        workspace_dir,
        {
            "version": 1,
            "name": "demo_nvme_default",
            "inputs": {
                "jira": {"source": "demo_jira", "selector_profile": "demo_jira_project"},
                "evidence": {"source": "demo_confluence", "selector_profile": "demo_confluence_space"},
                "spec_assets": [DEMO_SPEC_ASSET_ID],
            },
            "analysis": {
                "top_k": 5,
                "policies": ["team:ssd", "public"],
                "llm_backend": "none",
                "llm_prompt_mode": "strict",
            },
        },
    )


def _copy_mineru_spec_asset(*, spec_assets_workspace: str | Path, target_workspace: Path) -> dict | None:
    existing = _latest_mineru_asset(target_workspace)
    if existing:
        return existing

    source_workspace = Path(spec_assets_workspace)
    if not (source_workspace / "workspace.yaml").exists():
        return None
    selected = _latest_mineru_asset(source_workspace)
    if not selected:
        return None
    source_root = Path(selected["asset_root"])
    target_root = target_workspace / "raw" / "files" / "spec_assets" / DEMO_SPEC_ASSET_ID / selected["version"]
    if target_root.exists():
        shutil.rmtree(target_root)
    target_root.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source_root, target_root)

    registry_path = target_workspace / "raw" / "files" / "spec_assets" / "registry.json"
    if registry_path.exists():
        target_registry = json.loads(registry_path.read_text(encoding="utf-8"))
    else:
        target_registry = {"assets": []}
    copied = {**selected, "asset_root": str(target_root)}
    target_registry["assets"] = [
        entry for entry in target_registry.get("assets", [])
        if not (entry.get("asset_id") == DEMO_SPEC_ASSET_ID and entry.get("version") == selected["version"])
    ]
    target_registry["assets"].append(copied)
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(json.dumps(target_registry, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return copied


def _latest_mineru_asset(workspace_dir: Path) -> dict | None:
    if not (workspace_dir / "workspace.yaml").exists():
        return None
    registry = load_spec_asset_registry(workspace_dir)
    matches = [
        entry for entry in registry.get("assets", [])
        if entry.get("asset_id") == DEMO_SPEC_ASSET_ID and entry.get("parser_used") == "mineru"
    ]
    if not matches:
        return None
    return sorted(matches, key=lambda entry: str(entry.get("version", "")))[-1]

# Workspace Source Registry Cache Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a persistent workspace source registry, selector profiles, profile-driven analysis entrypoints, and deterministic cache invalidation without changing the Phase 1 PageIndex, ACL, citation, or snapshot contracts.

**Architecture:** Keep `scripts/workspace_cli.py` as a thin argparse layer and put reusable behavior in `services/workspace/source_registry.py` plus small integration points in `services/workspace/workspace.py`. Store v1 registry files as YAML and promote `PyYAML` to a core dependency because the operator-facing registry is configuration, not runtime data. Preserve legacy `raw/*/specs/*.json` fetch behavior by translating old source specs into the new source + selector model at the service boundary.

**Tech Stack:** Python 3.12, `PyYAML`, stdlib `json`, `argparse`, `pathlib`, `hashlib`, existing `unittest` tests, existing `services.ops.orchestration.load_source_payload`, existing file-backed snapshot store.

---

## Design Evaluation

The design is directionally correct for the current repository. It solves the real operator problem: configuration should be durable, live payloads should be cached, and code changes should not force Jira or Confluence refetches.

The plan needs four boundaries before implementation:

1. Add `PyYAML` as a core dependency and use `.yaml` for source, selector, profile, and credential registry files.
2. Keep `snapshots/current/` limited to `manifest.json`, `documents.json`, and `page_index.json`. Put fetch and build-layer manifests under `raw/*/payloads/...` and `build/...` so the Phase 1 snapshot contract remains intact.
3. Credentials should be env-reference only in v1. Do not support inline bearer secrets in the first implementation because redaction and local-secret lifecycle are not yet a product requirement.
4. `run-analysis` should call existing `deep_analyze_issue` or `query_workspace` seams. It should not introduce a second analysis engine.

The smallest valuable slice is: registry YAML + selector YAML + fetch-source + profile-driven analysis + manifest hashes. Reindex/rebuild can follow once the registry is stable.

## Planned File Structure

Create:
- `services/workspace/source_registry.py` - registry paths, YAML load/write, validation, hashing, legacy spec translation, stale status helpers.
- `tests/workspace/test_source_registry.py` - focused service tests for source, selector, profile, hashes, and credential env resolution.
- `docs/superpowers/plans/2026-04-18-workspace-source-registry-cache.md` - this plan.

Modify:
- `pyproject.toml` - move `PyYAML>=6.0` into core dependencies and remove the duplicate optional-only requirement from `portal-runner`.
- `services/workspace/workspace.py` - add registry paths to `workspace_paths`, init new directories, add service functions for source/selector/profile/fetch-source/run-analysis/status integration.
- `services/workspace/__init__.py` - export new workspace service functions.
- `scripts/workspace_cli.py` - add `source`, `selector`, `fetch-source`, `run-analysis`, and `rerun-analysis` commands.
- `tests/ops/test_workspace_cli.py` - add CLI integration coverage for init, source add/show/list, selector add/show/list, fetch-source, and run-analysis.
- `docs/api-contracts.md` - document the new workspace source registry contracts.
- `docs/workspace-cli-guide.md` - document the operator workflow.
- `docs/cli-reference.md` - add command reference entries.

Do not modify:
- `services/retrieval/persistence/snapshot_store.py` in the first slice. Snapshot semantics stay stable.
- `services/retrieval/indexing/page_index.py` in the first slice. Index version metadata is recorded around existing output, not by changing PageIndex entry shape.
- Connector internals in the first slice. Fetch-source adapts into existing `load_source_payload`.

## Task 0: Promote PyYAML To Core Dependency

**Files:**
- Modify: `pyproject.toml`
- Test: `python -c "import yaml; print(yaml.__version__)"`

- [ ] **Step 1: Move `PyYAML` into core dependencies**

In `pyproject.toml`, update `[project].dependencies` to include:

```toml
dependencies = [
  "atlassian-python-api>=3.41.16",
  "pypdf>=4.0",
  "PyYAML>=6.0",
]
```

Keep `portal-runner` valid by removing `PyYAML>=6.0` from that optional dependency group after adding it to core dependencies.

- [ ] **Step 2: Verify the dependency imports**

Run:

```powershell
python -c "import yaml; print(yaml.__version__)"
```

Expected: prints an installed PyYAML version and exits 0.

## Task 1: Contract Tests For Registry Files

**Files:**
- Create: `tests/workspace/test_source_registry.py`
- Create later in Task 2: `services/workspace/source_registry.py`

- [ ] **Step 1: Write failing tests for source, selector, profile, and hashes**

Add this file:

```python
from __future__ import annotations

import json
import os
import unittest
from pathlib import Path

import yaml

from services.workspace.source_registry import (
    build_fetch_request,
    config_hash,
    list_sources,
    load_run_profile,
    load_selector_profile,
    load_source,
    resolve_credential,
    selector_hash,
    write_run_profile,
    write_selector_profile,
    write_source,
)
from tests.temp_utils import temporary_directory as TemporaryDirectory


class SourceRegistryTest(unittest.TestCase):
    def test_source_selector_and_profile_round_trip(self) -> None:
        with TemporaryDirectory() as workspace:
            source_path = write_source(
                workspace,
                {
                    "version": 1,
                    "name": "jira_lab",
                    "kind": "jira",
                    "connector_type": "jira.atlassian_api",
                    "credential_ref": "jira_lab_token",
                    "config": {"base_url": "https://jira.example.com", "auth_mode": "auto"},
                    "defaults": {"include_comments": True, "include_attachments": True},
                    "selector_defaults": {"type": "project_slice", "project_key": "SSD"},
                    "policies": ["team:ssd", "public"],
                    "metadata": {"description": "SSD team Jira server", "tags": ["jira", "ssd"]},
                },
            )
            selector_path = write_selector_profile(
                workspace,
                {
                    "version": 1,
                    "name": "jira_one_issue",
                    "source": "jira_lab",
                    "selector": {"type": "issue", "issue_key": "SSD-777"},
                },
            )
            profile_path = write_run_profile(
                workspace,
                {
                    "version": 1,
                    "name": "ssd_deep_analysis_default",
                    "inputs": {
                        "jira": {
                            "source": "jira_lab",
                            "selector_profile": "jira_one_issue",
                        }
                    },
                    "analysis": {
                        "top_k": 5,
                        "llm_backend": "none",
                        "llm_prompt_mode": "strict",
                        "policies": ["team:ssd", "public"],
                    },
                },
            )

            self.assertTrue(Path(source_path).exists())
            self.assertTrue(Path(selector_path).exists())
            self.assertTrue(Path(profile_path).exists())
            self.assertEqual(load_source(workspace, "jira_lab")["name"], "jira_lab")
            self.assertEqual(load_selector_profile(workspace, "jira_one_issue")["source"], "jira_lab")
            self.assertEqual(load_run_profile(workspace, "ssd_deep_analysis_default")["analysis"]["top_k"], 5)
            self.assertEqual([source["name"] for source in list_sources(workspace)], ["jira_lab"])

    def test_hashes_are_stable_and_ignore_description_metadata(self) -> None:
        source = {
            "version": 1,
            "name": "jira_lab",
            "kind": "jira",
            "connector_type": "jira.atlassian_api",
            "credential_ref": "jira_lab_token",
            "config": {"base_url": "https://jira.example.com", "auth_mode": "auto"},
            "defaults": {"include_comments": True},
            "metadata": {"description": "before"},
        }
        changed_description = dict(source)
        changed_description["metadata"] = {"description": "after"}
        changed_base_url = json.loads(json.dumps(source))
        changed_base_url["config"]["base_url"] = "https://jira2.example.com"

        self.assertEqual(config_hash(source), config_hash(changed_description))
        self.assertNotEqual(config_hash(source), config_hash(changed_base_url))
        self.assertEqual(
            selector_hash({"selector": {"type": "issue", "issue_key": "SSD-777"}}),
            selector_hash({"selector": {"issue_key": "SSD-777", "type": "issue"}}),
        )

    def test_env_credential_resolution_does_not_persist_secret_value(self) -> None:
        with TemporaryDirectory() as workspace:
            credential_path = Path(workspace) / ".local" / "credentials.yaml"
            credential_path.parent.mkdir(parents=True, exist_ok=True)
            credential_path.write_text(
                yaml.safe_dump(
                    {
                        "version": 1,
                        "credentials": {
                            "jira_lab_token": {"type": "bearer_env", "env": "JIRA_TOKEN"}
                        },
                    },
                    sort_keys=False,
                ),
                encoding="utf-8",
            )
            previous = os.environ.get("JIRA_TOKEN")
            os.environ["JIRA_TOKEN"] = "secret-token"
            try:
                credential = resolve_credential(workspace, "jira_lab_token")
            finally:
                if previous is None:
                    os.environ.pop("JIRA_TOKEN", None)
                else:
                    os.environ["JIRA_TOKEN"] = previous

            self.assertEqual(credential["auth_mode"], "bearer")
            self.assertEqual(credential["token"], "secret-token")
            stored = credential_path.read_text(encoding="utf-8")
            self.assertNotIn("secret-token", stored)

    def test_fetch_request_merges_source_defaults_and_selector(self) -> None:
        with TemporaryDirectory() as workspace:
            write_source(
                workspace,
                {
                    "version": 1,
                    "name": "jira_lab",
                    "kind": "jira",
                    "connector_type": "jira.atlassian_api",
                    "config": {"base_url": "https://jira.example.com", "auth_mode": "auto"},
                    "defaults": {"include_comments": True, "include_attachments": False},
                    "selector_defaults": {"type": "project_slice", "project_key": "SSD"},
                    "policies": ["team:ssd"],
                },
            )
            write_selector_profile(
                workspace,
                {
                    "version": 1,
                    "name": "jira_one_issue",
                    "source": "jira_lab",
                    "selector": {"type": "issue", "issue_key": "SSD-777"},
                },
            )

            request = build_fetch_request(workspace, source_name="jira_lab", selector_profile="jira_one_issue")

            self.assertEqual(request["kwargs"]["kind"], "jira")
            self.assertTrue(request["kwargs"]["live"])
            self.assertEqual(request["kwargs"]["base_url"], "https://jira.example.com")
            self.assertEqual(request["kwargs"]["issue_key"], "SSD-777")
            self.assertTrue(request["kwargs"]["include_comments"])
            self.assertFalse(request["kwargs"]["include_attachments"])
            self.assertEqual(request["manifest"]["source_name"], "jira_lab")
            self.assertEqual(request["manifest"]["selector_profile"], "jira_one_issue")
            self.assertTrue(request["manifest"]["config_hash"].startswith("sha256:"))
            self.assertTrue(request["manifest"]["selector_hash"].startswith("sha256:"))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the focused test and confirm it fails**

Run:

```powershell
python -m unittest tests.workspace.test_source_registry -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'services.workspace.source_registry'`.

## Task 2: Source Registry Service

**Files:**
- Create: `services/workspace/source_registry.py`
- Test: `tests/workspace/test_source_registry.py`

- [ ] **Step 1: Implement YAML registry paths, validation, and hashing**

Create `services/workspace/source_registry.py` with:

```python
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path

import yaml


SOURCE_KINDS = {"jira", "confluence"}
CONNECTOR_TYPES = {
    "jira.atlassian_api": "jira",
    "confluence.atlassian_api": "confluence",
}
JIRA_SELECTORS = {"issue", "project_slice", "project_full"}
CONFLUENCE_SELECTORS = {"page", "page_tree", "space_slice"}


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


def _json_hash(payload: dict) -> str:
    data = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"sha256:{hashlib.sha256(data).hexdigest()}"


def config_hash(source: dict) -> str:
    return _json_hash(
        {
            "version": source.get("version"),
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


def validate_source(source: dict) -> dict:
    if source.get("version") != 1:
        raise ValueError("source.version must be 1")
    name = _validate_name(source.get("name"), "source.name")
    kind = source.get("kind")
    connector_type = source.get("connector_type")
    if kind not in SOURCE_KINDS:
        raise ValueError("source.kind must be one of: jira, confluence")
    if connector_type not in CONNECTOR_TYPES:
        raise ValueError("source.connector_type must be one of: jira.atlassian_api, confluence.atlassian_api")
    if CONNECTOR_TYPES[connector_type] != kind:
        raise ValueError("source.kind must match connector_type")
    config = source.get("config", {})
    if not isinstance(config, dict):
        raise ValueError("source.config must be an object")
    if not config.get("base_url") and source.get("mode", "live") == "live":
        raise ValueError("source.config.base_url is required for live sources")
    selector_defaults = source.get("selector_defaults", {})
    if selector_defaults:
        _validate_selector(kind, selector_defaults)
    normalized = dict(source)
    normalized["name"] = name
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
        if not isinstance(input_name, str) or not isinstance(input_config, dict):
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
    if credential.get("type") != "bearer_env":
        raise ValueError("Only bearer_env credentials are supported in registry v1")
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


def build_fetch_request(workspace_dir: str | Path, *, source_name: str, selector_profile: str) -> dict:
    source = load_source(workspace_dir, source_name)
    selector = load_selector_profile(workspace_dir, selector_profile)
    merged_selector = dict(source.get("selector_defaults", {}))
    merged_selector.update(selector.get("selector", {}))
    _validate_selector(source["kind"], merged_selector)

    config = source.get("config", {})
    fetch_flags = _fetch_flags(source)
    kwargs = {
        "kind": source["kind"],
        "path": None,
        "live": True,
        "base_url": config.get("base_url"),
        "username": None,
        "password": None,
        "token": None,
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
    kwargs.update(resolve_credential(workspace_dir, source.get("credential_ref")))

    selector_type = merged_selector.get("type")
    if source["kind"] == "jira":
        if selector_type == "issue":
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
        if selector_type == "page":
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
```

- [ ] **Step 2: Run focused registry tests**

Run:

```powershell
python -m unittest tests.workspace.test_source_registry -v
```

Expected: PASS.

## Task 3: Initialize Registry Directories

**Files:**
- Modify: `services/workspace/workspace.py`
- Modify: `tests/ops/test_workspace_cli.py`
- Test: `tests/ops/test_workspace_cli.py`

- [ ] **Step 1: Add failing init assertions**

In `WorkspaceCliTest.test_workspace_cli_init_creates_layout`, add:

```python
self.assertTrue(Path(temp_dir, "sources").exists())
self.assertTrue(Path(temp_dir, "selectors").exists())
self.assertTrue(Path(temp_dir, "profiles").exists())
self.assertTrue(Path(temp_dir, ".local", "credentials.example.yaml").exists())
```

- [ ] **Step 2: Run the single test and confirm it fails**

Run:

```powershell
python -m unittest tests.ops.test_workspace_cli.WorkspaceCliTest.test_workspace_cli_init_creates_layout -v
```

Expected: FAIL because the new directories and example credential file do not exist.

- [ ] **Step 3: Modify workspace path setup**

In `services/workspace/workspace.py`, import the registry helpers:

```python
from services.workspace.source_registry import registry_paths, write_credentials_example
```

Extend `workspace_paths` with:

```python
"sources": root / "sources",
"selectors": root / "selectors",
"profiles": root / "profiles",
"local": root / ".local",
"credentials_example": root / ".local" / "credentials.example.yaml",
```

In `init_workspace`, keep the existing skip set, but let `sources`, `selectors`, `profiles`, and `.local` be created as directories. After the wiki manifest initialization, add:

```python
if not paths["credentials_example"].exists():
    write_credentials_example(workspace_dir)
```

Extend the returned payload with:

```python
"source_dir": str(paths["sources"]),
"selector_dir": str(paths["selectors"]),
"profile_dir": str(paths["profiles"]),
"credentials_example_path": str(paths["credentials_example"]),
```

- [ ] **Step 4: Run the init test**

Run:

```powershell
python -m unittest tests.ops.test_workspace_cli.WorkspaceCliTest.test_workspace_cli_init_creates_layout -v
```

Expected: PASS.

## Task 4: Source And Selector CLI

**Files:**
- Modify: `services/workspace/workspace.py`
- Modify: `services/workspace/__init__.py`
- Modify: `scripts/workspace_cli.py`
- Modify: `tests/ops/test_workspace_cli.py`
- Test: `tests/ops/test_workspace_cli.py`

- [ ] **Step 1: Add failing CLI coverage**

Add this test method to `WorkspaceCliTest`:

```python
def test_workspace_cli_source_and_selector_commands(self) -> None:
    with TemporaryDirectory() as temp_dir:
        self.assertEqual(self._run("scripts/workspace_cli.py", "init", temp_dir).returncode, 0)

        add_source = self._run(
            "scripts/workspace_cli.py",
            "source",
            "add",
            temp_dir,
            "jira_lab",
            "--connector-type",
            "jira.atlassian_api",
            "--base-url",
            "https://jira.example.com",
            "--credential-ref",
            "jira_lab_token",
            "--policy",
            "team:ssd",
            "--policy",
            "public",
            "--include-comments",
            "--include-attachments",
        )
        self.assertEqual(add_source.returncode, 0, add_source.stderr)
        add_payload = json.loads(add_source.stdout)
        self.assertEqual(add_payload["source"]["name"], "jira_lab")
        self.assertTrue(Path(add_payload["path"]).exists())

        source_list = self._run("scripts/workspace_cli.py", "source", "list", temp_dir)
        self.assertEqual(source_list.returncode, 0, source_list.stderr)
        self.assertEqual(json.loads(source_list.stdout)["sources"][0]["name"], "jira_lab")

        source_show = self._run("scripts/workspace_cli.py", "source", "show", temp_dir, "jira_lab")
        self.assertEqual(source_show.returncode, 0, source_show.stderr)
        self.assertEqual(json.loads(source_show.stdout)["source"]["connector_type"], "jira.atlassian_api")

        add_selector = self._run(
            "scripts/workspace_cli.py",
            "selector",
            "add",
            temp_dir,
            "jira_one_issue",
            "--source",
            "jira_lab",
            "--type",
            "issue",
            "--issue-key",
            "SSD-777",
        )
        self.assertEqual(add_selector.returncode, 0, add_selector.stderr)
        self.assertEqual(json.loads(add_selector.stdout)["selector"]["name"], "jira_one_issue")

        selector_list = self._run("scripts/workspace_cli.py", "selector", "list", temp_dir)
        self.assertEqual(selector_list.returncode, 0, selector_list.stderr)
        self.assertEqual(json.loads(selector_list.stdout)["selectors"][0]["name"], "jira_one_issue")
```

- [ ] **Step 2: Run the new test and confirm it fails**

Run:

```powershell
python -m unittest tests.ops.test_workspace_cli.WorkspaceCliTest.test_workspace_cli_source_and_selector_commands -v
```

Expected: FAIL because `source` and `selector` commands do not exist.

- [ ] **Step 3: Add workspace service functions**

In `services/workspace/workspace.py`, add imports:

```python
from services.workspace.source_registry import (
    list_selector_profiles,
    list_sources,
    load_selector_profile,
    load_source,
    write_selector_profile,
    write_source,
)
```

Add functions:

```python
def add_workspace_source(
    workspace_dir: str | Path,
    name: str,
    *,
    connector_type: str,
    base_url: str,
    credential_ref: str | None = None,
    policies: list[str] | None = None,
    include_comments: bool = True,
    include_attachments: bool = True,
) -> dict:
    _load_workspace_config(workspace_dir)
    kind = "jira" if connector_type.startswith("jira.") else "confluence"
    source = {
        "version": 1,
        "name": name,
        "kind": kind,
        "connector_type": connector_type,
        "credential_ref": credential_ref,
        "config": {"base_url": base_url, "auth_mode": "auto"},
        "defaults": {
            "include_comments": include_comments,
            "include_attachments": include_attachments,
            "include_image_metadata": True,
            "download_images": False,
        },
        "policies": list(policies or DEFAULT_POLICIES),
        "metadata": {},
    }
    path = write_source(workspace_dir, source)
    return {"workspace_dir": str(workspace_paths(workspace_dir)["root"]), "path": path, "source": load_source(workspace_dir, name)}


def list_workspace_sources(workspace_dir: str | Path) -> dict:
    _load_workspace_config(workspace_dir)
    return {"workspace_dir": str(workspace_paths(workspace_dir)["root"]), "sources": list_sources(workspace_dir)}


def show_workspace_source(workspace_dir: str | Path, name: str) -> dict:
    _load_workspace_config(workspace_dir)
    return {"workspace_dir": str(workspace_paths(workspace_dir)["root"]), "source": load_source(workspace_dir, name)}


def add_workspace_selector(
    workspace_dir: str | Path,
    name: str,
    *,
    source: str,
    selector_type: str,
    issue_key: str | None = None,
    project_key: str | None = None,
    page_id: str | None = None,
    root_page_id: str | None = None,
    max_depth: int | None = None,
) -> dict:
    _load_workspace_config(workspace_dir)
    selector = {"type": selector_type}
    if issue_key:
        selector["issue_key"] = issue_key
    if project_key:
        selector["project_key"] = project_key
    if page_id:
        selector["page_id"] = page_id
    if root_page_id:
        selector["root_page_id"] = root_page_id
    if max_depth is not None:
        selector["max_depth"] = max_depth
    payload = {"version": 1, "name": name, "source": source, "selector": selector}
    path = write_selector_profile(workspace_dir, payload)
    return {
        "workspace_dir": str(workspace_paths(workspace_dir)["root"]),
        "path": path,
        "selector": load_selector_profile(workspace_dir, name),
    }


def list_workspace_selectors(workspace_dir: str | Path) -> dict:
    _load_workspace_config(workspace_dir)
    return {"workspace_dir": str(workspace_paths(workspace_dir)["root"]), "selectors": list_selector_profiles(workspace_dir)}


def show_workspace_selector(workspace_dir: str | Path, name: str) -> dict:
    _load_workspace_config(workspace_dir)
    return {
        "workspace_dir": str(workspace_paths(workspace_dir)["root"]),
        "selector": load_selector_profile(workspace_dir, name),
    }
```

Export these functions from `services/workspace/__init__.py`.

- [ ] **Step 4: Add argparse subcommands**

In `scripts/workspace_cli.py`, import the new service functions and add nested subparsers:

```python
source_parser = subparsers.add_parser("source")
source_subparsers = source_parser.add_subparsers(dest="source_command", required=True)
source_add = source_subparsers.add_parser("add")
source_add.add_argument("workspace")
source_add.add_argument("name")
source_add.add_argument("--connector-type", required=True)
source_add.add_argument("--base-url", required=True)
source_add.add_argument("--credential-ref")
source_add.add_argument("--policy", action="append")
source_add.add_argument("--include-comments", action="store_true", default=True)
source_add.add_argument("--include-attachments", action="store_true", default=True)
source_list = source_subparsers.add_parser("list")
source_list.add_argument("workspace")
source_show = source_subparsers.add_parser("show")
source_show.add_argument("workspace")
source_show.add_argument("name")

selector_parser = subparsers.add_parser("selector")
selector_subparsers = selector_parser.add_subparsers(dest="selector_command", required=True)
selector_add = selector_subparsers.add_parser("add")
selector_add.add_argument("workspace")
selector_add.add_argument("name")
selector_add.add_argument("--source", required=True)
selector_add.add_argument("--type", required=True)
selector_add.add_argument("--issue-key")
selector_add.add_argument("--project-key")
selector_add.add_argument("--page-id")
selector_add.add_argument("--root-page-id")
selector_add.add_argument("--max-depth", type=int)
selector_list = selector_subparsers.add_parser("list")
selector_list.add_argument("workspace")
selector_show = selector_subparsers.add_parser("show")
selector_show.add_argument("workspace")
selector_show.add_argument("name")
```

Add dispatch branches:

```python
if args.command == "source":
    if args.source_command == "add":
        return _print_json(
            add_workspace_source(
                args.workspace,
                args.name,
                connector_type=args.connector_type,
                base_url=args.base_url,
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

if args.command == "selector":
    if args.selector_command == "add":
        return _print_json(
            add_workspace_selector(
                args.workspace,
                args.name,
                source=args.source,
                selector_type=args.type,
                issue_key=args.issue_key,
                project_key=args.project_key,
                page_id=args.page_id,
                root_page_id=args.root_page_id,
                max_depth=args.max_depth,
            )
        )
    if args.selector_command == "list":
        return _print_json(list_workspace_selectors(args.workspace))
    if args.selector_command == "show":
        return _print_json(show_workspace_selector(args.workspace, args.name))
```

- [ ] **Step 5: Run the CLI test**

Run:

```powershell
python -m unittest tests.ops.test_workspace_cli.WorkspaceCliTest.test_workspace_cli_source_and_selector_commands -v
```

Expected: PASS.

## Task 5: Fetch-Source With Latest And History Cache

**Files:**
- Modify: `services/workspace/source_registry.py`
- Modify: `services/workspace/workspace.py`
- Modify: `services/workspace/__init__.py`
- Modify: `scripts/workspace_cli.py`
- Modify: `tests/ops/test_workspace_cli.py`

- [ ] **Step 1: Add failing CLI test using fixture-backed source**

Add `import yaml` near the top of `tests/ops/test_workspace_cli.py`.

Add this test method:

```python
def test_workspace_cli_fetch_source_writes_latest_history_and_manifest(self) -> None:
    with TemporaryDirectory() as temp_dir:
        self.assertEqual(self._run("scripts/workspace_cli.py", "init", temp_dir).returncode, 0)
        source_file = Path(temp_dir, "sources", "jira_fixture.yaml")
        source_file.write_text(
            yaml.safe_dump(
                {
                    "version": 1,
                    "name": "jira_fixture",
                    "kind": "jira",
                    "connector_type": "jira.atlassian_api",
                    "mode": "fixture",
                    "config": {"path": "fixtures/connectors/jira/full_sync.json", "auth_mode": "auto"},
                    "defaults": {"include_comments": True, "include_attachments": True},
                    "policies": ["team:ssd", "public"],
                },
                sort_keys=False,
            ),
            encoding="utf-8",
        )
        selector_file = Path(temp_dir, "selectors", "jira_one_issue.yaml")
        selector_file.write_text(
            yaml.safe_dump(
                {
                    "version": 1,
                    "name": "jira_one_issue",
                    "source": "jira_fixture",
                    "selector": {"type": "issue", "issue_key": "SSD-101"},
                },
                sort_keys=False,
            ),
            encoding="utf-8",
        )

        result = self._run(
            "scripts/workspace_cli.py",
            "fetch-source",
            temp_dir,
            "--source",
            "jira_fixture",
            "--selector-profile",
            "jira_one_issue",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(Path(payload["latest_payload_path"]).exists())
        self.assertTrue(Path(payload["history_payload_path"]).exists())
        self.assertTrue(Path(payload["fetch_manifest_path"]).exists())
        manifest = json.loads(Path(payload["fetch_manifest_path"]).read_text(encoding="utf-8"))
        self.assertEqual(manifest["source_name"], "jira_fixture")
        self.assertEqual(manifest["selector_profile"], "jira_one_issue")
        self.assertEqual(manifest["document_count"], 1)
        self.assertTrue(manifest["payload_hash"].startswith("sha256:"))
```

- [ ] **Step 2: Run the new test and confirm it fails**

Run:

```powershell
python -m unittest tests.ops.test_workspace_cli.WorkspaceCliTest.test_workspace_cli_fetch_source_writes_latest_history_and_manifest -v
```

Expected: FAIL because `fetch-source` does not exist.

- [ ] **Step 3: Add fixture mode to fetch request builder**

In `services/workspace/source_registry.py`, update `validate_source` so `mode` may be `fixture` or `live`, and `fixture` requires `config.path`.

In `build_fetch_request`, set:

```python
mode = source.get("mode", "live")
kwargs["live"] = mode == "live"
kwargs["path"] = config.get("path") if mode == "fixture" else None
```

- [ ] **Step 4: Add payload cache paths and service function**

In `services/workspace/workspace.py`, add a helper:

```python
def _source_payload_cache_paths(workspace_dir: str | Path, kind: str, source_name: str) -> dict[str, Path]:
    payload_root = workspace_paths(workspace_dir)["raw"] / kind / "payloads" / source_name
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    return {
        "root": payload_root,
        "latest": payload_root / "latest.json",
        "manifest": payload_root / "fetch-manifest.json",
        "history": payload_root / "history" / f"{timestamp}.json",
    }
```

Add:

```python
def fetch_workspace_source(workspace_dir: str | Path, *, source_name: str, selector_profile: str) -> dict:
    _load_workspace_config(workspace_dir)
    request = build_fetch_request(workspace_dir, source_name=source_name, selector_profile=selector_profile)
    source = request["source"]
    payload = load_source_payload(**request["kwargs"])
    cache_paths = _source_payload_cache_paths(workspace_dir, source["kind"], source["name"])
    _write_json(cache_paths["latest"], payload)
    _write_json(cache_paths["history"], payload)
    payload_hash = f"sha256:{hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode('utf-8')).hexdigest()}"
    manifest = {
        **request["manifest"],
        "fetched_at": _utc_now(),
        "payload_path": str(cache_paths["history"]),
        "latest_payload_path": str(cache_paths["latest"]),
        "payload_hash": payload_hash,
        "document_count": len(payload.get("documents", [])),
        "sync_type": payload.get("sync_type"),
        "cursor": payload.get("cursor"),
    }
    _write_json(cache_paths["manifest"], manifest)

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
```

Update `_payload_files` to include only `latest.json` from nested source payload directories and keep legacy flat `*.json` payload files:

```python
for latest_path in sorted(payload_dir.glob("*/latest.json")):
    files.append((kind, latest_path))
```

- [ ] **Step 5: Add CLI command**

In `scripts/workspace_cli.py`:

```python
fetch_source_parser = subparsers.add_parser("fetch-source")
fetch_source_parser.add_argument("workspace")
fetch_source_parser.add_argument("--source", required=True)
fetch_source_parser.add_argument("--selector-profile", required=True)
```

Dispatch:

```python
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
```

Export `fetch_workspace_source` from `services/workspace/__init__.py`.

- [ ] **Step 6: Run fetch-source and legacy build tests**

Run:

```powershell
python -m unittest tests.ops.test_workspace_cli.WorkspaceCliTest.test_workspace_cli_fetch_source_writes_latest_history_and_manifest -v
python -m unittest tests.ops.test_workspace_cli.WorkspaceCliTest.test_workspace_cli_supports_fetch_build_export_query_and_lint -v
```

Expected: PASS.

## Task 6: Build Manifests Around Existing Snapshot Build

**Files:**
- Modify: `services/workspace/workspace.py`
- Modify: `tests/ops/test_workspace_cli.py`

- [ ] **Step 1: Add failing build manifest assertions**

Extend `test_workspace_cli_fetch_source_writes_latest_history_and_manifest` after `fetch-source`:

```python
build = self._run("scripts/workspace_cli.py", "build", temp_dir)
self.assertEqual(build.returncode, 0, build.stderr)
normalize_manifest = Path(temp_dir, "build", "normalize", "jira_fixture", "manifest.json")
index_manifest = Path(temp_dir, "build", "index", "pageindex_v1", "manifest.json")
self.assertTrue(normalize_manifest.exists())
self.assertTrue(index_manifest.exists())
normalize_payload = json.loads(normalize_manifest.read_text(encoding="utf-8"))
index_payload = json.loads(index_manifest.read_text(encoding="utf-8"))
self.assertEqual(normalize_payload["source_name"], "jira_fixture")
self.assertTrue(normalize_payload["payload_hash"].startswith("sha256:"))
self.assertEqual(index_payload["index_name"], "pageindex_v1")
self.assertTrue(index_payload["input_documents_hash"].startswith("sha256:"))
```

- [ ] **Step 2: Run the test and confirm it fails**

Run:

```powershell
python -m unittest tests.ops.test_workspace_cli.WorkspaceCliTest.test_workspace_cli_fetch_source_writes_latest_history_and_manifest -v
```

Expected: FAIL because build manifests do not exist.

- [ ] **Step 3: Write manifests during build without changing snapshot files**

In `workspace_paths`, add:

```python
"build_root": root / "build",
"normalize_root": root / "build" / "normalize",
"index_root": root / "build" / "index",
```

In `build_workspace`, inside the payload loop after reading `payload`, compute:

```python
payload_hash = f"sha256:{hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode('utf-8')).hexdigest()}"
normalize_source_name = payload_path.parent.name if payload_path.name == "latest.json" else payload_path.stem
normalize_dir = paths["normalize_root"] / normalize_source_name
_write_json(
    normalize_dir / "manifest.json",
    {
        "source_name": normalize_source_name,
        "payload_hash": payload_hash,
        "normalize_version": "workspace_payload_passthrough_v1",
        "created_at": _utc_now(),
        "documents_path": str(normalize_dir / "documents.json"),
        "document_count": len(documents),
    },
)
_write_json(normalize_dir / "documents.json", {"documents": documents})
```

After `write_snapshot`, compute an input hash from `merged_documents`:

```python
documents_payload = {"documents": [merged_documents[key] for key in sorted(merged_documents)]}
input_documents_hash = f"sha256:{hashlib.sha256(json.dumps(documents_payload, ensure_ascii=False, sort_keys=True).encode('utf-8')).hexdigest()}"
index_dir = paths["index_root"] / "pageindex_v1"
_write_json(
    index_dir / "manifest.json",
    {
        "index_name": "pageindex_v1",
        "input_documents_hash": input_documents_hash,
        "index_version": "pageindex_v1_current",
        "created_at": _utc_now(),
        "page_index_path": str(paths["snapshot_root"] / "page_index.json"),
        "page_index_count": snapshot_report["manifest"]["page_index_count"],
    },
)
```

- [ ] **Step 4: Run focused build test**

Run:

```powershell
python -m unittest tests.ops.test_workspace_cli.WorkspaceCliTest.test_workspace_cli_fetch_source_writes_latest_history_and_manifest -v
```

Expected: PASS.

## Task 7: Run Profiles And Profile-Driven Analysis

**Files:**
- Modify: `services/workspace/workspace.py`
- Modify: `services/workspace/__init__.py`
- Modify: `scripts/workspace_cli.py`
- Modify: `tests/ops/test_workspace_cli.py`

- [ ] **Step 1: Add failing run-analysis CLI test**

Add this test method:

```python
def test_workspace_cli_run_analysis_uses_profile_and_existing_snapshot(self) -> None:
    with TemporaryDirectory() as temp_dir:
        self._prepare_workspace_snapshot(temp_dir)
        Path(temp_dir, "sources").mkdir(exist_ok=True)
        Path(temp_dir, "selectors").mkdir(exist_ok=True)
        Path(temp_dir, "profiles").mkdir(exist_ok=True)
        Path(temp_dir, "sources", "jira_fixture.yaml").write_text(
            yaml.safe_dump(
                {
                    "version": 1,
                    "name": "jira_fixture",
                    "kind": "jira",
                    "connector_type": "jira.atlassian_api",
                    "mode": "fixture",
                    "config": {"path": "fixtures/connectors/jira/full_sync.json"},
                    "defaults": {},
                    "policies": ["team:ssd"],
                },
                sort_keys=False,
            ),
            encoding="utf-8",
        )
        Path(temp_dir, "selectors", "jira_one_issue.yaml").write_text(
            yaml.safe_dump(
                {
                    "version": 1,
                    "name": "jira_one_issue",
                    "source": "jira_fixture",
                    "selector": {"type": "issue", "issue_key": "SSD-102"},
                },
                sort_keys=False,
            ),
            encoding="utf-8",
        )
        Path(temp_dir, "profiles", "ssd_deep_analysis_default.yaml").write_text(
            yaml.safe_dump(
                {
                    "version": 1,
                    "name": "ssd_deep_analysis_default",
                    "inputs": {
                        "jira": {"source": "jira_fixture", "selector_profile": "jira_one_issue"}
                    },
                    "analysis": {"top_k": 3, "llm_backend": "none", "llm_prompt_mode": "strict", "policies": ["team:ssd"]},
                },
                sort_keys=False,
            ),
            encoding="utf-8",
        )

        result = self._run(
            "scripts/workspace_cli.py",
            "run-analysis",
            temp_dir,
            "--profile",
            "ssd_deep_analysis_default",
            "--issue-key",
            "SSD-102",
            "--use-existing-snapshot",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["profile"], "ssd_deep_analysis_default")
        self.assertEqual(payload["analysis"]["issue_id"], "SSD-102")
        self.assertTrue(Path(payload["analysis"]["run_dir"]).exists())
```

- [ ] **Step 2: Run the new test and confirm it fails**

Run:

```powershell
python -m unittest tests.ops.test_workspace_cli.WorkspaceCliTest.test_workspace_cli_run_analysis_uses_profile_and_existing_snapshot -v
```

Expected: FAIL because `run-analysis` does not exist.

- [ ] **Step 3: Add service function using existing deep analysis seam**

In `services/workspace/workspace.py`, import `load_run_profile` and add:

```python
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
    if not use_existing_snapshot:
        build_workspace(workspace_dir)
    payload = deep_analyze_issue(
        workspace_dir,
        issue_key,
        policies=analysis_config.get("policies", DEFAULT_POLICIES),
        top_k=int(analysis_config.get("top_k", 5)),
        prompt_mode=analysis_config.get("llm_prompt_mode", "strict"),
        llm_backend=llm_backend,
    )
    manifest_path = Path(payload["run_dir"]) / "analysis-manifest.json"
    snapshot_hashes = {
        name: _file_sha256(path)
        for name, path in snapshot_paths(workspace_paths(workspace_dir)["snapshot_root"]).items()
    }
    analysis_manifest = {
        "profile": profile_name,
        "issue_key": issue_key,
        "snapshot_files": snapshot_hashes,
        "analysis_version": "deep_analysis_v1",
        "prompt_profile_version": analysis_config.get("llm_prompt_mode", "strict"),
        "created_at": _utc_now(),
    }
    _write_json(manifest_path, analysis_manifest)
    return {
        "workspace_dir": str(workspace_paths(workspace_dir)["root"]),
        "profile": profile_name,
        "analysis_manifest_path": str(manifest_path),
        "analysis": payload,
    }
```

Export `run_workspace_analysis` from `services/workspace/__init__.py`.

- [ ] **Step 4: Add CLI parser**

In `scripts/workspace_cli.py`:

```python
run_analysis_parser = subparsers.add_parser("run-analysis")
run_analysis_parser.add_argument("workspace")
run_analysis_parser.add_argument("--profile", required=True)
run_analysis_parser.add_argument("--issue-key", required=True)
run_analysis_parser.add_argument("--use-existing-snapshot", action="store_true")
_add_llm_backend_args(run_analysis_parser)

rerun_analysis_parser = subparsers.add_parser("rerun-analysis")
rerun_analysis_parser.add_argument("workspace")
rerun_analysis_parser.add_argument("--profile", required=True)
rerun_analysis_parser.add_argument("--issue-key", required=True)
rerun_analysis_parser.add_argument("--use-existing-snapshot", action="store_true", default=True)
_add_llm_backend_args(rerun_analysis_parser)
```

Dispatch both commands:

```python
if args.command in {"run-analysis", "rerun-analysis"}:
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
```

- [ ] **Step 5: Run the run-analysis test**

Run:

```powershell
python -m unittest tests.ops.test_workspace_cli.WorkspaceCliTest.test_workspace_cli_run_analysis_uses_profile_and_existing_snapshot -v
```

Expected: PASS.

## Task 8: Stale Status Reporting

**Files:**
- Modify: `services/workspace/source_registry.py`
- Modify: `services/workspace/workspace.py`
- Modify: `tests/ops/test_workspace_cli.py`

- [ ] **Step 1: Add status assertions for registry and stale summaries**

Extend `test_workspace_cli_fetch_source_writes_latest_history_and_manifest` after build:

```python
status = self._run("scripts/workspace_cli.py", "status", temp_dir)
self.assertEqual(status.returncode, 0, status.stderr)
status_payload = json.loads(status.stdout)
self.assertEqual(status_payload["registry_counts"]["sources"], 1)
self.assertEqual(status_payload["registry_counts"]["selectors"], 1)
self.assertEqual(status_payload["cache"]["fetch"]["fresh"], 1)
self.assertEqual(status_payload["cache"]["fetch"]["stale"], 0)
```

- [ ] **Step 2: Implement status helper**

In `services/workspace/source_registry.py`, add:

```python
def fetch_cache_status(workspace_dir: str | Path) -> list[dict]:
    rows: list[dict] = []
    for source in list_sources(workspace_dir):
        source_name = source["name"]
        source_kind = source["kind"]
        manifest_path = Path(workspace_dir) / "raw" / source_kind / "payloads" / source_name / "fetch-manifest.json"
        if not manifest_path.exists():
            rows.append({"source_name": source_name, "status": "stale", "reason": "missing_fetch_manifest"})
            continue
        manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
        current_hash = config_hash(source)
        if manifest.get("config_hash") != current_hash:
            rows.append({"source_name": source_name, "status": "stale", "reason": "source_config_changed"})
        else:
            rows.append({"source_name": source_name, "status": "fresh", "reason": "config_hash_matches"})
    return rows
```

In `status_workspace`, include:

```python
from services.workspace.source_registry import fetch_cache_status, list_run_profiles, list_selector_profiles, list_sources

fetch_rows = fetch_cache_status(workspace_dir)
"registry_counts": {
    "sources": len(list_sources(workspace_dir)),
    "selectors": len(list_selector_profiles(workspace_dir)),
    "profiles": len(list_run_profiles(workspace_dir)),
},
"cache": {
    "fetch": {
        "fresh": len([row for row in fetch_rows if row["status"] == "fresh"]),
        "stale": len([row for row in fetch_rows if row["status"] == "stale"]),
        "sources": fetch_rows,
    }
},
```

- [ ] **Step 3: Run the focused status test**

Run:

```powershell
python -m unittest tests.ops.test_workspace_cli.WorkspaceCliTest.test_workspace_cli_fetch_source_writes_latest_history_and_manifest -v
```

Expected: PASS.

## Task 9: Documentation And Contracts

**Files:**
- Modify: `docs/api-contracts.md`
- Modify: `docs/workspace-cli-guide.md`
- Modify: `docs/cli-reference.md`

- [ ] **Step 1: Document source registry contracts**

Append a new `Workspace Source Registry Contract` section to `docs/api-contracts.md`:

```markdown
## 23. Workspace Source Registry Contract

Produced by:

- `services/workspace/source_registry.py`
- `scripts/workspace_cli.py source`
- `scripts/workspace_cli.py selector`
- `scripts/workspace_cli.py run-analysis`

Current registry files:

- `sources/<source-name>.yaml`
- `selectors/<selector-name>.yaml`
- `profiles/<profile-name>.yaml`
- `.local/credentials.yaml`

Key invariants:

- registry files are local workspace configuration and are not runtime payload cache files
- source names are stable identifiers used by payload cache and build manifests
- credentials use env references in v1; inline bearer secrets are not supported
- fetch cache invalidation is driven by source config hash and selector hash
- cached raw payloads live under `raw/<kind>/payloads/<source>/latest.json` and `history/*.json`
- `snapshots/current/` remains limited to `manifest.json`, `documents.json`, and `page_index.json`
```

- [ ] **Step 2: Document operator workflow**

Add examples to `docs/workspace-cli-guide.md`:

```markdown
## Source Registry Workflow

Create a named source:

```bash
python scripts/workspace_cli.py source add D:\ssd-workspaces\lab1 jira_lab --connector-type jira.atlassian_api --base-url https://jira.example.com --credential-ref jira_lab_token --policy team:ssd --policy public
```

Create a selector:

```bash
python scripts/workspace_cli.py selector add D:\ssd-workspaces\lab1 jira_one_issue --source jira_lab --type issue --issue-key SSD-777
```

Fetch and cache source payload:

```bash
python scripts/workspace_cli.py fetch-source D:\ssd-workspaces\lab1 --source jira_lab --selector-profile jira_one_issue
```

Build snapshot from cached payload:

```bash
python scripts/workspace_cli.py build D:\ssd-workspaces\lab1
```

Run analysis from the existing snapshot:

```bash
python scripts/workspace_cli.py run-analysis D:\ssd-workspaces\lab1 --profile ssd_deep_analysis_default --issue-key SSD-777 --use-existing-snapshot
```
```

- [ ] **Step 3: Add CLI reference entries**

In `docs/cli-reference.md`, add entries for:

```markdown
- `source add <workspace> <name> --connector-type ... --base-url ...`
- `source list <workspace>`
- `source show <workspace> <name>`
- `selector add <workspace> <name> --source ... --type ...`
- `selector list <workspace>`
- `selector show <workspace> <name>`
- `fetch-source <workspace> --source ... --selector-profile ...`
- `run-analysis <workspace> --profile ... --issue-key ... [--use-existing-snapshot]`
- `rerun-analysis <workspace> --profile ... --issue-key ... --use-existing-snapshot`
```

- [ ] **Step 4: Run documentation compile check**

Run:

```powershell
python -m compileall docs services scripts tests
```

Expected: PASS.

## Task 10: Final Validation

**Files:**
- No new edits unless validation fails.

- [ ] **Step 1: Run focused tests**

Run:

```powershell
python -m unittest tests.workspace.test_source_registry -v
python -m unittest tests.ops.test_workspace_cli.WorkspaceCliTest.test_workspace_cli_init_creates_layout -v
python -m unittest tests.ops.test_workspace_cli.WorkspaceCliTest.test_workspace_cli_source_and_selector_commands -v
python -m unittest tests.ops.test_workspace_cli.WorkspaceCliTest.test_workspace_cli_fetch_source_writes_latest_history_and_manifest -v
python -m unittest tests.ops.test_workspace_cli.WorkspaceCliTest.test_workspace_cli_run_analysis_uses_profile_and_existing_snapshot -v
```

Expected: PASS.

- [ ] **Step 2: Run broader workspace CLI test module**

Run:

```powershell
python -m unittest tests.ops.test_workspace_cli -v
```

Expected: PASS.

- [ ] **Step 3: Run repo contract checks affected by CLI and docs**

Run:

```powershell
python scripts/gates/check_adr_contract.py
python scripts/gates/check_repo_shape.py
python scripts/gates/check_module_contracts.py
python -m compileall docs scripts services tests
```

Expected: PASS.

## Explicit Non-Goals For This Plan

- Do not support inline bearer secrets in registry v1.
- Do not remove legacy `fetch <workspace> <spec>` behavior.
- Do not change canonical document, PageIndex entry, search result, citation, or source inspection payload shapes.
- Do not add database-backed storage.
- Do not add Jira or Confluence write-back.
- Do not implement full refresh frequency scheduling in this slice; report hash-based freshness first.

## Self-Review

Spec coverage:
- Named sources: Tasks 1, 2, and 4.
- Persistent local config: Tasks 2, 3, and 4.
- Local raw payload cache: Task 5.
- Layer manifests and hashes: Tasks 5, 6, and 7.
- Analysis rerun without refetch or reindex: Task 7.
- Phase 1 contract preservation: evaluation notes, file structure, and non-goals.

Placeholder scan:
- No task relies on unnamed files or unresolved function names.
- Deferred items are called out only as non-goals, not as implementation steps.

Type consistency:
- Registry function names introduced in Task 2 are the same names imported by tests and later workspace functions.
- CLI option names in tests match the argparse additions.
- `profile_name`, `selector_profile`, and `source_name` are used consistently in service functions.

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import json


TASK_CHECKPOINTS = (
    "retrieval_ready",
    "analysis_ready",
    "knowledge_ready",
)

RUN_STATUSES = {
    "queued",
    "running",
    "stopping",
    "stopped",
    "failed",
    "completed",
}

ARTIFACT_STATUSES = {
    "pending",
    "ready",
    "failed",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _manifest_path(path: str | Path) -> Path:
    target = Path(path)
    if target.suffix.lower() == ".json":
        return target
    return target / "run_manifest.json"


def _default_checkpoints() -> dict[str, dict]:
    return {
        name: {
            "reached": False,
            "updated_at": None,
            "artifact_types": [],
        }
        for name in TASK_CHECKPOINTS
    }


def _validate_checkpoint_name(name: str) -> None:
    if name not in TASK_CHECKPOINTS:
        expected = ", ".join(TASK_CHECKPOINTS)
        raise ValueError(f"Unsupported checkpoint: {name}. Expected one of: {expected}")


def build_artifact_record(
    *,
    artifact_type: str,
    path: str | None,
    step_name: str,
    step_version: str,
    input_hash: str,
    depends_on: list[str] | None = None,
    engine: str | None = None,
    prompt_version: str | None = None,
    status: str = "ready",
    created_at: str | None = None,
    stale: bool = False,
) -> dict:
    if status not in ARTIFACT_STATUSES:
        expected = ", ".join(sorted(ARTIFACT_STATUSES))
        raise ValueError(f"Unsupported artifact status: {status}. Expected one of: {expected}")
    return {
        "artifact_type": artifact_type,
        "path": path,
        "step_name": step_name,
        "step_version": step_version,
        "input_hash": input_hash,
        "depends_on": list(depends_on or []),
        "engine": engine,
        "prompt_version": prompt_version,
        "status": status,
        "created_at": created_at or _utc_now(),
        "stale": bool(stale),
    }


def refresh_artifact_staleness(artifacts: list[dict]) -> list[dict]:
    refreshed = [deepcopy(artifact) for artifact in artifacts]
    by_type = {artifact["artifact_type"]: artifact for artifact in refreshed}
    changed = True
    while changed:
        changed = False
        for artifact in refreshed:
            dependencies = artifact.get("depends_on", [])
            dependency_missing = any(dependency not in by_type for dependency in dependencies)
            dependency_stale = any(
                by_type[dependency].get("stale", False)
                for dependency in dependencies
                if dependency in by_type
            )
            new_stale = bool(artifact.get("stale")) or dependency_missing or dependency_stale
            if artifact.get("stale") != new_stale:
                artifact["stale"] = new_stale
                changed = True
    return refreshed


def build_run_manifest(
    *,
    task_type: str,
    owner: str,
    input_config: dict,
    run_id: str,
    run_version: int = 1,
    status: str = "queued",
    checkpoints: dict[str, dict] | None = None,
    artifacts: list[dict] | None = None,
    error: dict | None = None,
    created_at: str | None = None,
    updated_at: str | None = None,
) -> dict:
    if status not in RUN_STATUSES:
        expected = ", ".join(sorted(RUN_STATUSES))
        raise ValueError(f"Unsupported run status: {status}. Expected one of: {expected}")

    normalized_checkpoints = _default_checkpoints()
    if checkpoints:
        for name, state in checkpoints.items():
            _validate_checkpoint_name(name)
            normalized_checkpoints[name] = {
                "reached": bool(state.get("reached", False)),
                "updated_at": state.get("updated_at"),
                "artifact_types": list(state.get("artifact_types", [])),
            }

    current_time = created_at or _utc_now()
    return {
        "task_type": task_type,
        "owner": owner,
        "input_config": deepcopy(input_config),
        "run_id": run_id,
        "run_version": run_version,
        "status": status,
        "checkpoints": normalized_checkpoints,
        "artifacts": refresh_artifact_staleness(list(artifacts or [])),
        "created_at": current_time,
        "updated_at": updated_at or current_time,
        "error": deepcopy(error),
    }


def update_checkpoint(
    manifest: dict,
    checkpoint_name: str,
    *,
    reached: bool,
    artifact_types: list[str] | None = None,
    updated_at: str | None = None,
) -> dict:
    _validate_checkpoint_name(checkpoint_name)
    checkpoint_time = updated_at or _utc_now()
    updated_manifest = deepcopy(manifest)
    updated_manifest.setdefault("checkpoints", _default_checkpoints())
    updated_manifest["checkpoints"][checkpoint_name] = {
        "reached": bool(reached),
        "updated_at": checkpoint_time,
        "artifact_types": list(artifact_types or []),
    }
    updated_manifest["updated_at"] = checkpoint_time
    return updated_manifest


def write_run_manifest(path: str | Path, manifest: dict) -> str:
    manifest_path = _manifest_path(path)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return str(manifest_path)


def load_run_manifest(path: str | Path) -> dict:
    manifest_path = _manifest_path(path)
    return json.loads(manifest_path.read_text(encoding="utf-8"))

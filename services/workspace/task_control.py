from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import json
from uuid import uuid4

from services.workspace.task_manifest import _utc_now, build_run_manifest, refresh_artifact_staleness, write_run_manifest


ADAPTER_STATE_TO_RUN_STATUS = {
    "scheduled": "queued",
    "running": "running",
    "cancelling": "stopping",
    "cancelled": "stopped",
    "failed": "failed",
    "succeeded": "completed",
}

CONTROL_ACTIONS = {"stop", "resume", "rerun", "rerun_section", "sync_adapter_state"}
CHECKPOINT_STEPS = (
    ("retrieval", "retrieval_ready"),
    ("analysis", "analysis_ready"),
    ("knowledge", "knowledge_ready"),
)


def map_adapter_state(adapter_state: str) -> str:
    try:
        return ADAPTER_STATE_TO_RUN_STATUS[adapter_state]
    except KeyError as error:
        expected = ", ".join(sorted(ADAPTER_STATE_TO_RUN_STATUS))
        raise ValueError(f"Unsupported adapter state: {adapter_state}. Expected one of: {expected}") from error


def apply_adapter_state(manifest: dict, adapter_state: str, *, error: dict | None = None) -> dict:
    updated = deepcopy(manifest)
    updated["status"] = map_adapter_state(adapter_state)
    updated["updated_at"] = _utc_now()
    if error is not None:
        updated["error"] = deepcopy(error)
    return updated


def build_resume_plan(manifest: dict) -> dict:
    checkpoints = manifest.get("checkpoints", {})
    last_reached = None
    for step_name, checkpoint_name in CHECKPOINT_STEPS:
        if not checkpoints.get(checkpoint_name, {}).get("reached", False):
            return {
                "resume_from_step": step_name,
                "resume_from_checkpoint": last_reached,
                "completed": False,
            }
        last_reached = checkpoint_name
    return {
        "resume_from_step": None,
        "resume_from_checkpoint": last_reached,
        "completed": True,
    }


def build_control_event(
    *,
    manifest: dict,
    action: str,
    requested_by: str,
    step_name: str | None = None,
    reason: str | None = None,
    result: dict | None = None,
) -> dict:
    if action not in CONTROL_ACTIONS:
        expected = ", ".join(sorted(CONTROL_ACTIONS))
        raise ValueError(f"Unsupported control action: {action}. Expected one of: {expected}")
    return {
        "event_id": f"{manifest['run_id']}-{action}-{_utc_now()}",
        "run_id": manifest["run_id"],
        "run_version": manifest["run_version"],
        "task_type": manifest["task_type"],
        "action": action,
        "requested_by": requested_by,
        "step_name": step_name,
        "reason": reason,
        "result": deepcopy(result or {}),
        "created_at": _utc_now(),
    }


def request_stop(
    manifest: dict,
    *,
    requested_by: str,
    step_name: str,
    reason: str | None = None,
) -> tuple[dict, dict]:
    updated = deepcopy(manifest)
    updated["status"] = "stopping"
    updated["updated_at"] = _utc_now()
    event = build_control_event(
        manifest=updated,
        action="stop",
        requested_by=requested_by,
        step_name=step_name,
        reason=reason,
        result={"target_status": "stopping"},
    )
    return updated, event


def request_resume(
    manifest: dict,
    *,
    requested_by: str,
    reason: str | None = None,
) -> tuple[dict, dict]:
    plan = build_resume_plan(manifest)
    if plan["completed"]:
        raise ValueError(f"Run is already complete and cannot be resumed: {manifest['run_id']}")
    updated = deepcopy(manifest)
    updated["status"] = "queued"
    updated["updated_at"] = _utc_now()
    event = build_control_event(
        manifest=updated,
        action="resume",
        requested_by=requested_by,
        step_name=plan["resume_from_step"],
        reason=reason,
        result=plan,
    )
    return updated, event


def build_rerun_manifest(
    manifest: dict,
    *,
    requested_by: str,
    run_id: str | None = None,
    reason: str | None = None,
) -> tuple[dict, dict]:
    new_version = int(manifest.get("run_version", 1)) + 1
    new_run_id = run_id or f"{manifest['run_id']}-rerun-v{new_version}-{uuid4().hex[:8]}"
    input_config = deepcopy(manifest.get("input_config", {}))
    input_config["rerun_of"] = {
        "run_id": manifest["run_id"],
        "run_version": manifest.get("run_version", 1),
        "reason": reason,
    }
    rerun_manifest = build_run_manifest(
        task_type=manifest["task_type"],
        owner=manifest["owner"],
        input_config=input_config,
        run_id=new_run_id,
        run_version=new_version,
        status="queued",
    )
    event = build_control_event(
        manifest=rerun_manifest,
        action="rerun",
        requested_by=requested_by,
        reason=reason,
        result={"rerun_of": manifest["run_id"]},
    )
    return rerun_manifest, event


def request_section_rerun(
    manifest: dict,
    *,
    section_name: str,
    requested_by: str,
    reason: str | None = None,
) -> tuple[dict, dict]:
    target_artifact_type = f"section_output_{section_name}"
    updated = deepcopy(manifest)
    artifacts = updated.get("artifacts", [])
    target_found = False
    for artifact in artifacts:
        if artifact.get("artifact_type") == target_artifact_type:
            artifact["stale"] = True
            target_found = True
            break
    if not target_found:
        raise ValueError(f"Section artifact not found for rerun: {target_artifact_type}")

    updated["artifacts"] = refresh_artifact_staleness(artifacts)
    updated["status"] = "queued"
    updated["updated_at"] = _utc_now()
    stale_artifact_types = [
        artifact["artifact_type"]
        for artifact in updated["artifacts"]
        if artifact.get("stale", False)
    ]
    event = build_control_event(
        manifest=updated,
        action="rerun_section",
        requested_by=requested_by,
        step_name=f"section_runner_{section_name}",
        reason=reason,
        result={
            "section_name": section_name,
            "target_artifact_type": target_artifact_type,
            "stale_artifact_types": stale_artifact_types,
        },
    )
    return updated, event


def append_control_event(run_dir: str | Path, event: dict) -> str:
    path = Path(run_dir) / "control-events.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")
    return str(path)


def write_controlled_manifest(run_dir: str | Path, manifest: dict, event: dict) -> dict:
    manifest_path = write_run_manifest(run_dir, manifest)
    event_log_path = append_control_event(run_dir, event)
    return {
        "run_id": manifest["run_id"],
        "run_version": manifest["run_version"],
        "status": manifest["status"],
        "manifest_path": manifest_path,
        "control_event": event,
        "control_event_log": event_log_path,
    }

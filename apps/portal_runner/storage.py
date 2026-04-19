from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
import hashlib
import json
import re
import time
from threading import RLock

from apps.portal_runner.schemas import PipelineDefinition, PipelineInput


_SAFE_NAME_PATTERN = re.compile(r"[^A-Za-z0-9_.-]+")


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class PortalRunnerStorage:
    def __init__(self, *, runs_root: str | Path, uploads_root: str | Path) -> None:
        self.runs_root = Path(runs_root)
        self.uploads_root = Path(uploads_root)
        self._manifest_lock = RLock()
        self.runs_root.mkdir(parents=True, exist_ok=True)
        self.uploads_root.mkdir(parents=True, exist_ok=True)

    def create_run(
        self,
        *,
        definition: PipelineDefinition,
        pipeline_input: PipelineInput,
        client_ip: str | None,
    ) -> dict:
        run_id = f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{uuid4().hex[:8]}-{definition.pipeline_id}"
        run_dir = self.runs_root / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "artifacts").mkdir(parents=True, exist_ok=True)
        manifest = {
            "run_id": run_id,
            "pipeline_id": definition.pipeline_id,
            "label": definition.label,
            "status": "queued",
            "created_at": utc_now(),
            "started_at": None,
            "completed_at": None,
            "client_ip": client_ip,
            "request": pipeline_input.public_summary(),
            "steps": [
                {
                    "step_id": step_id,
                    "label": _label_from_step(step_id),
                    "status": "pending",
                    "started_at": None,
                    "completed_at": None,
                    "duration_seconds": None,
                    "latest_logs": [],
                    "artifact_names": [],
                    "error": None,
                }
                for step_id in definition.steps
            ],
            "artifacts": {},
            "upload": None,
            "cancel_requested": False,
        }
        self.write_manifest(run_id, manifest)
        self.append_event(run_id, {"event": "run-created", "status": "queued"})
        return manifest

    def read_manifest(self, run_id: str) -> dict:
        return _read_json(self.run_dir(run_id) / "manifest.json")

    def write_manifest(self, run_id: str, manifest: dict) -> None:
        with self._manifest_lock:
            path = self.run_dir(run_id) / "manifest.json"
            if path.exists() and not manifest.get("cancel_requested"):
                current = _read_json(path)
                if current.get("cancel_requested"):
                    manifest = {**manifest, "cancel_requested": True}
            _write_json(path, manifest)

    def append_event(self, run_id: str, payload: dict) -> None:
        event = {"created_at": utc_now(), **payload}
        path = self.run_dir(run_id) / "events.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False, default=_json_default) + "\n")

    def list_events(self, run_id: str) -> list[dict]:
        path = self.run_dir(run_id) / "events.jsonl"
        if not path.exists():
            return []
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

    def list_runs(self) -> list[dict]:
        runs = []
        for manifest_path in sorted(self.runs_root.glob("*/manifest.json"), reverse=True):
            manifest = _read_json(manifest_path)
            runs.append(
                {
                    "run_id": manifest["run_id"],
                    "pipeline_id": manifest["pipeline_id"],
                    "label": manifest["label"],
                    "status": manifest["status"],
                    "created_at": manifest["created_at"],
                    "started_at": manifest.get("started_at"),
                    "completed_at": manifest.get("completed_at"),
                    "request": manifest.get("request", {}),
                }
            )
        return runs

    def mark_run_status(self, run_id: str, status: str, *, error: str | None = None) -> None:
        manifest = self.read_manifest(run_id)
        if status == "running" and not manifest.get("started_at"):
            manifest["started_at"] = utc_now()
        if status in {"succeeded", "failed", "cancelled"}:
            manifest["completed_at"] = utc_now()
        manifest["status"] = status
        if error:
            manifest["error"] = error
        self.write_manifest(run_id, manifest)
        self.append_event(run_id, {"event": "run-status", "status": status, "error": error})

    def update_step(
        self,
        run_id: str,
        step_id: str,
        *,
        status: str,
        logs: list[str] | None = None,
        error: str | None = None,
        artifacts: dict[str, str] | None = None,
    ) -> None:
        manifest = self.read_manifest(run_id)
        now = utc_now()
        for step in manifest["steps"]:
            if step["step_id"] != step_id:
                continue
            if status == "running" and not step.get("started_at"):
                step["started_at"] = now
            if status in {"succeeded", "failed", "cancelled"}:
                step["completed_at"] = now
                if step.get("started_at"):
                    step["duration_seconds"] = _duration_seconds(step["started_at"], now)
            step["status"] = status
            if logs:
                step["latest_logs"] = [*step.get("latest_logs", []), *logs][-20:]
            if error:
                step["error"] = error
            if artifacts:
                artifact_names = set(step.get("artifact_names", []))
                artifact_names.update(artifacts)
                step["artifact_names"] = sorted(artifact_names)
                manifest.setdefault("artifacts", {}).update(artifacts)
            break
        self.write_manifest(run_id, manifest)
        self.append_event(run_id, {"event": "step-status", "step_id": step_id, "status": status, "error": error})

    def request_cancel(self, run_id: str) -> dict:
        manifest = self.read_manifest(run_id)
        manifest["cancel_requested"] = True
        self.write_manifest(run_id, manifest)
        self.append_event(run_id, {"event": "cancel-requested", "status": manifest["status"]})
        return manifest

    def is_cancel_requested(self, run_id: str) -> bool:
        return bool(self.read_manifest(run_id).get("cancel_requested"))

    def save_artifact(self, run_id: str, name: str, payload: dict | list | str | bytes, *, suffix: str = ".json") -> str:
        safe_name = _safe_segment(name)
        path = self.run_dir(run_id) / "artifacts" / f"{safe_name}{suffix}"
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(payload, bytes):
            path.write_bytes(payload)
        elif isinstance(payload, str):
            path.write_text(payload, encoding="utf-8")
        else:
            _write_json(path, payload)
        return str(path)

    def save_uploaded_pdf(self, run_id: str, *, filename: str, content: bytes, max_upload_mb: int) -> dict:
        if len(content) > max_upload_mb * 1024 * 1024:
            raise ValueError(f"Uploaded PDF exceeds {max_upload_mb} MB limit.")
        if not content.startswith(b"%PDF"):
            raise ValueError("Uploaded file is not a PDF.")
        safe_name = _safe_segment(Path(filename or "upload.pdf").name)
        if not safe_name.lower().endswith(".pdf"):
            safe_name = f"{safe_name}.pdf"
        target_dir = self.uploads_root / run_id
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / safe_name
        target.write_bytes(content)
        digest = hashlib.sha256(content).hexdigest()
        upload = {
            "original_filename": filename,
            "path": str(target),
            "size_bytes": len(content),
            "sha256": digest,
        }
        manifest = self.read_manifest(run_id)
        manifest["upload"] = upload
        self.write_manifest(run_id, manifest)
        return upload

    def run_dir(self, run_id: str) -> Path:
        return self.runs_root / run_id

    def artifact_path(self, run_id: str, artifact_name: str) -> Path:
        manifest = self.read_manifest(run_id)
        path = manifest.get("artifacts", {}).get(artifact_name)
        if not path:
            raise ValueError(f"Unknown artifact: {artifact_name}")
        resolved = Path(path).resolve()
        run_root = self.run_dir(run_id).resolve()
        if run_root not in resolved.parents and resolved != run_root:
            raise ValueError("Artifact is outside the run directory.")
        return resolved


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f"{path.name}.{uuid4().hex}.tmp")
    temp_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=_json_default) + "\n", encoding="utf-8")
    for attempt in range(5):
        try:
            temp_path.replace(path)
            return
        except PermissionError:
            if attempt == 4:
                raise
            time.sleep(0.02)


def _json_default(value: object) -> object:
    if isinstance(value, Path):
        return str(value)
    raise TypeError(f"Object of type {value.__class__.__name__} is not JSON serializable")


def _safe_segment(value: str) -> str:
    safe = _SAFE_NAME_PATTERN.sub("-", value).strip(".- ")
    return safe or "artifact"


def _label_from_step(step_id: str) -> str:
    return step_id.replace("_", " ").title()


def _duration_seconds(started_at: str, completed_at: str) -> float:
    start = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
    end = datetime.fromisoformat(completed_at.replace("Z", "+00:00"))
    return round((end - start).total_seconds(), 3)

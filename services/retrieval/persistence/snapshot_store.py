from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
import json

from services.retrieval.toolkit import build_retrieval_index


SNAPSHOT_FILES = {
    "manifest": "manifest.json",
    "documents": "documents.json",
    "page_index": "page_index.json",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read_json(path: Path, default: dict | list) -> dict | list:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _json_default(value: object) -> object:
    if isinstance(value, set):
        return sorted(value)
    if isinstance(value, Counter):
        return dict(value)
    raise TypeError(f"Object of type {value.__class__.__name__} is not JSON serializable")


def _write_json(path: Path, payload: dict | list) -> None:
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, default=_json_default),
        encoding="utf-8",
    )


def snapshot_paths(snapshot_dir: str | Path) -> dict[str, Path]:
    root = Path(snapshot_dir)
    return {key: root / filename for key, filename in SNAPSHOT_FILES.items()}


def create_snapshot(
    snapshot_dir: str | Path,
    *,
    documents: Iterable[dict],
    source_name: str = "manual",
    source_cursor: str | None = None,
    sync_type: str = "full",
) -> dict:
    paths = snapshot_paths(snapshot_dir)
    root = Path(snapshot_dir)
    root.mkdir(parents=True, exist_ok=True)

    document_list = list(documents)
    page_index = build_retrieval_index(document_list)
    manifest = {
        "created_at": _utc_now(),
        "updated_at": _utc_now(),
        "document_count": len(document_list),
        "page_index_count": len(page_index),
        "sources": {
            source_name: {
                "cursor": source_cursor,
                "last_sync": _utc_now(),
                "sync_type": sync_type,
                "document_count": len(document_list),
            }
        },
    }

    _write_json(paths["documents"], {"documents": document_list})
    _write_json(paths["page_index"], {"entries": page_index})
    _write_json(paths["manifest"], manifest)
    return {"snapshot_dir": str(root), "manifest": manifest}


def load_snapshot(snapshot_dir: str | Path) -> dict:
    paths = snapshot_paths(snapshot_dir)
    return {
        "manifest": _read_json(paths["manifest"], {}),
        "documents": _read_json(paths["documents"], {"documents": []}),
        "page_index": _read_json(paths["page_index"], {"entries": []}),
    }


def refresh_snapshot(
    snapshot_dir: str | Path,
    *,
    sync_payload: dict,
    source_name: str,
) -> dict:
    loaded = load_snapshot(snapshot_dir)
    existing_documents = loaded["documents"].get("documents", [])
    incoming_documents = sync_payload.get("documents", [])

    merged = {document["document_id"]: document for document in existing_documents}
    for document in incoming_documents:
        merged[document["document_id"]] = document

    merged_documents = list(merged.values())
    page_index = build_retrieval_index(merged_documents)

    manifest = loaded["manifest"] or {}
    if "created_at" not in manifest:
        manifest["created_at"] = _utc_now()
    manifest["updated_at"] = _utc_now()
    manifest["document_count"] = len(merged_documents)
    manifest["page_index_count"] = len(page_index)
    manifest.setdefault("sources", {})
    manifest["sources"][source_name] = {
        "cursor": sync_payload.get("cursor"),
        "last_sync": manifest["updated_at"],
        "sync_type": sync_payload.get("sync_type", "incremental"),
        "document_count": len(incoming_documents),
    }

    paths = snapshot_paths(snapshot_dir)
    Path(snapshot_dir).mkdir(parents=True, exist_ok=True)
    _write_json(paths["documents"], {"documents": merged_documents})
    _write_json(paths["page_index"], {"entries": page_index})
    _write_json(paths["manifest"], manifest)

    return {
        "snapshot_dir": str(Path(snapshot_dir)),
        "manifest": manifest,
        "updated_document_ids": [document["document_id"] for document in incoming_documents],
    }

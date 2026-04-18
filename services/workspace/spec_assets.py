from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from collections import Counter
import json
import os
import re

from services.ingest.adapters.pdf.adapter import extract_pdf_structure
from services.ingest.markdown_export import document_to_markdown
from services.retrieval.indexing.page_index import build_page_index, page_index_artifact
from services.workspace.workspace import _load_workspace_config, workspace_paths


_PATH_SAFE_PATTERN = re.compile(r'[<>:"/\\|?*]+')


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _safe_segment(value: str | None) -> str:
    text = str(value or "unknown").strip()
    text = _PATH_SAFE_PATTERN.sub("-", text)
    return text.strip(". ") or "unknown"


def _read_registry(path: Path) -> dict:
    if path.exists() and path.is_dir():
        if any(path.iterdir()):
            raise ValueError(f"Spec asset registry path must be a file, found non-empty directory: {path}")
        path.rmdir()
    if not path.exists():
        return {"assets": []}
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict | list) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, default=_json_default),
        encoding="utf-8",
    )
    return str(path)


def _json_default(value: object) -> object:
    if isinstance(value, set):
        return sorted(value)
    if isinstance(value, Counter):
        return dict(value)
    raise TypeError(f"Object of type {value.__class__.__name__} is not JSON serializable")


def _next_version(registry: dict, asset_id: str) -> str:
    versions = [
        entry.get("version", "v0")
        for entry in registry.get("assets", [])
        if entry.get("asset_id") == asset_id
    ]
    if not versions:
        return "v1"
    numeric_versions = []
    for version in versions:
        match = re.fullmatch(r"v(\d+)", version)
        if match:
            numeric_versions.append(int(match.group(1)))
    return f"v{(max(numeric_versions) if numeric_versions else len(versions)) + 1}"


def _version_sort_key(version: str | None) -> tuple[int, str]:
    text = str(version or "")
    match = re.fullmatch(r"v(\d+)", text)
    if match:
        return (int(match.group(1)), text)
    return (-1, text)


def ingest_spec_asset(
    workspace_dir: str | Path,
    *,
    spec_pdf: str | Path,
    asset_id: str | None = None,
    display_name: str | None = None,
    preferred_parser: str = "auto",
    mineru_python_exe: str | None = None,
) -> dict:
    _load_workspace_config(workspace_dir)
    paths = workspace_paths(workspace_dir)
    registry_path = paths["spec_assets_registry"]
    registry = _read_registry(registry_path)

    source_pdf = Path(spec_pdf)
    normalized_asset_id = _safe_segment(asset_id or source_pdf.stem)
    version = _next_version(registry, normalized_asset_id)

    previous_mineru_python = os.environ.get("MINERU_PYTHON_EXE")
    try:
        if mineru_python_exe:
            os.environ["MINERU_PYTHON_EXE"] = mineru_python_exe
        document = extract_pdf_structure(source_pdf, preferred_parser=preferred_parser)
    finally:
        if mineru_python_exe:
            if previous_mineru_python is None:
                os.environ.pop("MINERU_PYTHON_EXE", None)
            else:
                os.environ["MINERU_PYTHON_EXE"] = previous_mineru_python

    asset_root = paths["spec_assets_root"] / normalized_asset_id / version
    asset_root.mkdir(parents=True, exist_ok=True)
    document_markdown = document_to_markdown(document)
    entries = build_page_index([document])

    metadata = {
        "asset_id": normalized_asset_id,
        "display_name": display_name or document.get("title") or source_pdf.stem,
        "version": version,
        "document_id": document["document_id"],
        "source_pdf": str(source_pdf),
        "preferred_parser": preferred_parser,
        "parser_used": document.get("provenance", {}).get("parser"),
        "created_at": _utc_now(),
        "paths": {
            "document_json": str(asset_root / "spec-doc.json"),
            "corpus_json": str(asset_root / "spec-corpus.json"),
            "markdown": str(asset_root / "document.md"),
            "page_index": str(asset_root / "page_index.json"),
        },
    }

    _write_json(asset_root / "spec-doc.json", document)
    _write_json(asset_root / "spec-corpus.json", {"documents": [document]})
    _write_json(asset_root / "page_index.json", page_index_artifact(entries))
    (asset_root / "document.md").write_text(document_markdown, encoding="utf-8")
    _write_json(asset_root / "metadata.json", metadata)

    registry.setdefault("assets", [])
    registry["assets"] = [
        entry
        for entry in registry["assets"]
        if not (entry.get("asset_id") == normalized_asset_id and entry.get("version") == version)
    ]
    registry["assets"].append(
        {
            "asset_id": normalized_asset_id,
            "display_name": metadata["display_name"],
            "version": version,
            "document_id": document["document_id"],
            "created_at": metadata["created_at"],
            "source_pdf": str(source_pdf),
            "parser_used": metadata["parser_used"],
            "asset_root": str(asset_root),
        }
    )
    registry["assets"] = sorted(
        registry["assets"],
        key=lambda entry: (entry.get("asset_id", ""), _version_sort_key(entry.get("version"))),
    )
    _write_json(registry_path, registry)

    return {
        "asset_id": normalized_asset_id,
        "display_name": metadata["display_name"],
        "version": version,
        "document_id": document["document_id"],
        "preferred_parser": preferred_parser,
        "parser_used": metadata["parser_used"],
        "asset_root": str(asset_root),
        "metadata_json": str(asset_root / "metadata.json"),
        "document_json": str(asset_root / "spec-doc.json"),
        "corpus_json": str(asset_root / "spec-corpus.json"),
        "markdown": str(asset_root / "document.md"),
        "page_index_json": str(asset_root / "page_index.json"),
        "registry_json": str(registry_path),
    }


def load_spec_asset_registry(workspace_dir: str | Path) -> dict:
    _load_workspace_config(workspace_dir)
    paths = workspace_paths(workspace_dir)
    return _read_registry(paths["spec_assets_registry"])


def load_latest_spec_asset_documents(
    workspace_dir: str | Path,
    *,
    asset_ids: list[str] | set[str] | None = None,
) -> tuple[list[dict], dict[str, dict]]:
    registry = load_spec_asset_registry(workspace_dir)
    allowed_asset_ids = set(asset_ids or [])
    latest_by_asset: dict[str, dict] = {}
    for entry in registry.get("assets", []):
        asset_id = entry.get("asset_id")
        version = entry.get("version", "")
        if not asset_id:
            continue
        if allowed_asset_ids and asset_id not in allowed_asset_ids:
            continue
        previous = latest_by_asset.get(asset_id)
        if previous is None or _version_sort_key(version) > _version_sort_key(previous.get("version")):
            latest_by_asset[asset_id] = entry

    documents: list[dict] = []
    sources: dict[str, dict] = {}
    for asset_id, entry in sorted(latest_by_asset.items()):
        asset_root = Path(entry["asset_root"])
        corpus_path = asset_root / "spec-corpus.json"
        if not corpus_path.exists():
            continue
        payload = json.loads(corpus_path.read_text(encoding="utf-8"))
        asset_documents = payload.get("documents", [])
        documents.extend(asset_documents)
        sources[f"spec_asset:{asset_id}"] = {
            "cursor": entry.get("version"),
            "last_sync": entry.get("created_at"),
            "sync_type": "asset",
            "document_count": len(asset_documents),
        }
    return documents, sources

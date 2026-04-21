"""
Document asset management for user-uploaded documents.

Supports three document types:
- Spec: Technical specifications (high priority in retrieval)
- Policy: Policies and guidelines (medium priority)
- Other: General documents (normal priority)
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from collections import Counter
import json
import os
import re
import shutil

from services.ingest.adapters.pdf.adapter import extract_pdf_structure
from services.ingest.markdown_export import document_to_markdown
from services.retrieval.indexing.page_index import build_page_index, page_index_artifact
from services.workspace.workspace import _load_workspace_config, workspace_paths


_PATH_SAFE_PATTERN = re.compile(r'[<>:"/\\|?*]+')

# Document type priorities for retrieval
DOCUMENT_TYPES = {
    "spec": {"priority": 100, "label": "Specification"},
    "policy": {"priority": 50, "label": "Policy"},
    "other": {"priority": 10, "label": "Other"},
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _safe_segment(value: str | None) -> str:
    text = str(value or "unknown").strip()
    text = _PATH_SAFE_PATTERN.sub("-", text)
    return text.strip(". ") or "unknown"


def _read_registry(path: Path) -> dict:
    if path.exists() and path.is_dir():
        if any(path.iterdir()):
            raise ValueError(f"Document asset registry path must be a file, found non-empty directory: {path}")
        path.rmdir()
    if not path.exists():
        return {"documents": []}
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


def _next_version(registry: dict, doc_id: str) -> str:
    """Generate next version number for a document."""
    versions = [
        entry.get("version", "v0")
        for entry in registry.get("documents", [])
        if entry.get("doc_id") == doc_id
    ]
    if not versions:
        return "v1"
    numeric_versions = []
    for version in versions:
        match = re.fullmatch(r"v(\d+)", version)
        if match:
            numeric_versions.append(int(match.group(1)))
    return f"v{(max(numeric_versions) if numeric_versions else len(versions)) + 1}"


def upload_document_asset(
    workspace_dir: str | Path,
    *,
    file_path: str | Path,
    document_type: str = "other",
    display_name: str | None = None,
    preferred_parser: str = "auto",
    mineru_python_exe: str | None = None,
) -> dict:
    """
    Upload a document to the workspace.

    Args:
        workspace_dir: Workspace directory path
        file_path: Path to the PDF file to upload
        document_type: Type of document (spec, policy, other)
        display_name: Optional display name (defaults to filename)
        preferred_parser: PDF parser to use (auto, pypdf, mineru)
        mineru_python_exe: Path to Python executable for MinerU

    Returns:
        Metadata dict with upload information
    """
    if document_type not in DOCUMENT_TYPES:
        raise ValueError(f"Invalid document_type: {document_type}. Must be one of: {list(DOCUMENT_TYPES.keys())}")

    _load_workspace_config(workspace_dir)
    paths = workspace_paths(workspace_dir)

    # Create document-assets directory structure
    doc_assets_root = Path(workspace_dir) / "document-assets"
    registry_path = doc_assets_root / "registry.json"
    registry = _read_registry(registry_path)

    source_file = Path(file_path)
    if not source_file.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    # Generate document ID and version
    normalized_doc_id = _safe_segment(display_name or source_file.stem)
    version = _next_version(registry, normalized_doc_id)

    # Extract PDF structure
    previous_mineru_python = os.environ.get("MINERU_PYTHON_EXE")
    try:
        if mineru_python_exe:
            os.environ["MINERU_PYTHON_EXE"] = mineru_python_exe
        document = extract_pdf_structure(source_file, preferred_parser=preferred_parser)
    finally:
        if mineru_python_exe:
            if previous_mineru_python is None:
                os.environ.pop("MINERU_PYTHON_EXE", None)
            else:
                os.environ["MINERU_PYTHON_EXE"] = previous_mineru_python

    # Add document type metadata
    document["document_type"] = document_type
    document["document_type_priority"] = DOCUMENT_TYPES[document_type]["priority"]

    # Create asset directory
    asset_root = doc_assets_root / document_type / normalized_doc_id / version
    asset_root.mkdir(parents=True, exist_ok=True)

    # Copy original file
    dest_file = asset_root / source_file.name
    shutil.copy2(source_file, dest_file)

    # Generate outputs
    document_markdown = document_to_markdown(document)
    entries = build_page_index([document])

    metadata = {
        "doc_id": normalized_doc_id,
        "display_name": display_name or document.get("title") or source_file.stem,
        "document_type": document_type,
        "document_type_label": DOCUMENT_TYPES[document_type]["label"],
        "priority": DOCUMENT_TYPES[document_type]["priority"],
        "version": version,
        "document_id": document["document_id"],
        "source_file": str(source_file),
        "original_filename": source_file.name,
        "file_size": source_file.stat().st_size,
        "preferred_parser": preferred_parser,
        "parser_used": document.get("provenance", {}).get("parser"),
        "created_at": _utc_now(),
        "paths": {
            "document_json": str(asset_root / "document.json"),
            "corpus_json": str(asset_root / "corpus.json"),
            "markdown": str(asset_root / "document.md"),
            "page_index": str(asset_root / "page_index.json"),
            "original_file": str(dest_file),
        },
    }

    # Write outputs
    _write_json(asset_root / "document.json", document)
    _write_json(asset_root / "corpus.json", {"documents": [document]})
    _write_json(asset_root / "page_index.json", page_index_artifact(entries))
    (asset_root / "document.md").write_text(document_markdown, encoding="utf-8")
    _write_json(asset_root / "metadata.json", metadata)

    # Update registry
    registry.setdefault("documents", [])
    registry["documents"] = [
        entry
        for entry in registry["documents"]
        if not (entry.get("doc_id") == normalized_doc_id and entry.get("version") == version)
    ]
    registry["documents"].append(
        {
            "doc_id": normalized_doc_id,
            "display_name": metadata["display_name"],
            "document_type": document_type,
            "version": version,
            "document_id": document["document_id"],
            "created_at": metadata["created_at"],
            "file_size": metadata["file_size"],
            "original_filename": metadata["original_filename"],
        }
    )
    _write_json(registry_path, registry)

    return metadata


def list_document_assets(
    workspace_dir: str | Path,
    *,
    document_type: str | None = None,
) -> list[dict]:
    """
    List all uploaded documents.

    Args:
        workspace_dir: Workspace directory path
        document_type: Optional filter by document type

    Returns:
        List of document metadata dicts
    """
    doc_assets_root = Path(workspace_dir) / "document-assets"
    registry_path = doc_assets_root / "registry.json"

    if not registry_path.exists():
        return []

    registry = _read_registry(registry_path)
    documents = registry.get("documents", [])

    if document_type:
        documents = [doc for doc in documents if doc.get("document_type") == document_type]

    return sorted(documents, key=lambda d: d.get("created_at", ""), reverse=True)


def load_document_asset_documents(
    workspace_dir: str | Path,
    *,
    doc_ids: list[str] | None = None,
    document_type: str | None = None,
) -> tuple[list[dict], list[dict]]:
    """
    Load document structures from uploaded assets.

    Args:
        workspace_dir: Workspace directory path
        doc_ids: Optional list of document IDs to load
        document_type: Optional filter by document type

    Returns:
        Tuple of (documents, sources)
    """
    doc_assets_root = Path(workspace_dir) / "document-assets"
    registry_path = doc_assets_root / "registry.json"

    if not registry_path.exists():
        return [], []

    registry = _read_registry(registry_path)
    entries = registry.get("documents", [])

    # Filter by doc_ids if provided
    if doc_ids:
        entries = [e for e in entries if e.get("doc_id") in doc_ids]

    # Filter by document_type if provided
    if document_type:
        entries = [e for e in entries if e.get("document_type") == document_type]

    # Group by doc_id and get latest version
    latest_by_id: dict[str, dict] = {}
    for entry in entries:
        doc_id = entry.get("doc_id")
        if not doc_id:
            continue
        current = latest_by_id.get(doc_id)
        if not current or _version_sort_key(entry.get("version")) > _version_sort_key(current.get("version")):
            latest_by_id[doc_id] = entry

    documents: list[dict] = []
    sources: list[dict] = []

    for entry in latest_by_id.values():
        doc_id = entry["doc_id"]
        doc_type = entry.get("document_type", "other")
        version = entry["version"]

        asset_root = doc_assets_root / doc_type / doc_id / version
        corpus_path = asset_root / "corpus.json"

        if not corpus_path.exists():
            continue

        corpus = json.loads(corpus_path.read_text(encoding="utf-8"))
        asset_documents = corpus.get("documents", [])
        documents.extend(asset_documents)

        sources.append({
            "source_id": f"document-asset:{doc_id}",
            "source_type": "document-asset",
            "document_type": doc_type,
            "document_count": len(asset_documents),
            "version": version,
        })

    return documents, sources


def _version_sort_key(version: str | None) -> tuple[int, str]:
    """Sort key for version strings (v1, v2, etc.)."""
    text = str(version or "")
    match = re.fullmatch(r"v(\d+)", text)
    if match:
        return (int(match.group(1)), text)
    return (-1, text)


def delete_document_asset(
    workspace_dir: str | Path,
    *,
    doc_id: str,
    version: str | None = None,
) -> dict:
    """
    Delete a document asset.

    Args:
        workspace_dir: Workspace directory path
        doc_id: Document ID to delete
        version: Optional specific version (deletes all versions if not provided)

    Returns:
        Dict with deletion information
    """
    doc_assets_root = Path(workspace_dir) / "document-assets"
    registry_path = doc_assets_root / "registry.json"
    registry = _read_registry(registry_path)

    deleted_count = 0
    remaining_documents = []

    for entry in registry.get("documents", []):
        if entry.get("doc_id") == doc_id:
            if version is None or entry.get("version") == version:
                # Delete the asset directory
                doc_type = entry.get("document_type", "other")
                entry_version = entry.get("version")
                asset_root = doc_assets_root / doc_type / doc_id / entry_version
                if asset_root.exists():
                    shutil.rmtree(asset_root)
                deleted_count += 1
            else:
                remaining_documents.append(entry)
        else:
            remaining_documents.append(entry)

    registry["documents"] = remaining_documents
    _write_json(registry_path, registry)

    return {
        "doc_id": doc_id,
        "version": version,
        "deleted_count": deleted_count,
    }

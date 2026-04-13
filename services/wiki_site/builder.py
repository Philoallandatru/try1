from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import json
import os
import re

from services.ingest.markdown_export import document_to_markdown
from services.retrieval.indexing.page_index import build_page_index


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _write_json(path: str | Path, payload: dict | list) -> str:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=_json_default), encoding="utf-8")
    return str(output_path)


def _write_text(path: str | Path, text: str) -> str:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(text, encoding="utf-8")
    return str(output_path)


def _safe_slug(value: str | None) -> str:
    text = str(value or "unknown").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-") or "unknown"


def _content_hash(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()


def _json_default(value: object) -> object:
    if isinstance(value, set):
        return sorted(value)
    if isinstance(value, Counter):
        return dict(value)
    raise TypeError(f"Object of type {value.__class__.__name__} is not JSON serializable")


def _latest_versions_from_existing(export_root: Path) -> dict[str, str]:
    latest: dict[str, str] = {}
    documents_root = export_root / "documents"
    if not documents_root.exists():
        return latest
    for source_dir in documents_root.iterdir():
        if not source_dir.is_dir():
            continue
        for document_dir in source_dir.iterdir():
            if not document_dir.is_dir():
                continue
            versions = sorted(path.name for path in document_dir.iterdir() if path.is_dir())
            if versions:
                latest[document_dir.name] = versions[-1]
    return latest


def build_export_package(
    *,
    export_root: str | Path,
    documents: list[dict],
    export_mode: str,
    source_snapshot: str | None = None,
) -> dict:
    root = Path(export_root)
    root.mkdir(parents=True, exist_ok=True)
    exported_at = _utc_now()
    previous_versions = _latest_versions_from_existing(root)
    page_index = build_page_index(documents)
    page_index_counts = Counter(entry["document_id"] for entry in page_index)

    manifest_documents: list[dict] = []
    changes: list[dict] = []
    latest_versions: dict[str, str] = {}

    for document in sorted(documents, key=lambda item: (item["source_type"], item["document_id"], str(item.get("version") or ""))):
        source_type = document["source_type"]
        document_id = document["document_id"]
        version = str(document.get("version") or "unknown")
        document_dir = root / "documents" / _safe_slug(source_type) / _safe_slug(document_id) / _safe_slug(version)
        markdown_path = document_dir / "document.md"
        metadata_path = document_dir / "metadata.json"
        markdown = document_to_markdown(document)

        if markdown_path.exists():
            change_type = "unchanged"
        elif document_id in previous_versions:
            change_type = "updated"
        else:
            change_type = "new"

        _write_text(markdown_path, markdown)
        metadata_payload = {
            "document_id": document_id,
            "source_type": source_type,
            "version": version,
            "title": document.get("title", document_id),
            "authority_level": document.get("authority_level"),
            "language": document.get("language"),
            "provenance": document.get("provenance", {}),
            "acl": document.get("acl", {}),
            "structure": document.get("structure", {}),
            "terminology": document.get("terminology", {}),
            "exported_at": exported_at,
            "markdown_path": str(markdown_path.relative_to(root)).replace("\\", "/"),
            "page_index_entry_count": page_index_counts.get(document_id, 0),
            "latest_for_document": True,
            "previous_versions": [previous_versions[document_id]] if document_id in previous_versions and previous_versions[document_id] != version else [],
            "source_snapshot": source_snapshot,
            "content_hash": _content_hash(markdown),
            "metadata": document.get("metadata", {}),
        }
        _write_json(metadata_path, metadata_payload)

        relative_dir = str(document_dir.relative_to(root)).replace("\\", "/")
        latest_versions[document_id] = relative_dir
        manifest_documents.append(
            {
                "document_id": document_id,
                "source_type": source_type,
                "version": version,
                "path": relative_dir,
                "markdown_path": metadata_payload["markdown_path"],
                "metadata_path": str(metadata_path.relative_to(root)).replace("\\", "/"),
            }
        )
        changes.append(
            {
                "exported_at": exported_at,
                "change_type": change_type,
                "document_id": document_id,
                "version": version,
                "source_type": source_type,
                "paths": {
                    "document_dir": relative_dir,
                    "markdown_path": metadata_payload["markdown_path"],
                    "metadata_path": str(metadata_path.relative_to(root)).replace("\\", "/"),
                },
                "previous_version": previous_versions.get(document_id),
            }
        )

    page_index_path = root / "page_index.json"
    _write_json(page_index_path, {"entries": page_index})

    manifest = {
        "exported_at": exported_at,
        "export_mode": export_mode,
        "document_count": len(documents),
        "source_type_counts": dict(Counter(document["source_type"] for document in documents)),
        "latest_versions": latest_versions,
        "page_index_path": str(page_index_path.relative_to(root)).replace("\\", "/"),
        "documents": manifest_documents,
    }
    _write_json(root / "manifest.json", manifest)
    _write_json(root / "changes.json", changes)

    return {
        "export_root": str(root),
        "manifest_path": str(root / "manifest.json"),
        "changes_path": str(root / "changes.json"),
        "page_index_path": str(page_index_path),
        "document_count": len(documents),
        "source_type_counts": manifest["source_type_counts"],
    }


def _load_json(path: str | Path) -> dict | list:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _source_page_markdown(*, metadata: dict, markdown: str, relative_document_path: str) -> str:
    title = metadata.get("title") or metadata["document_id"]
    source_uri = metadata.get("provenance", {}).get("source_uri") or ""
    version = metadata.get("version") or "unknown"
    authority = metadata.get("authority_level") or "unknown"
    return "\n".join(
        [
            f"# {title}",
            "",
            "> Derived display page. Canonical document remains the source of truth.",
            "",
            f"- Document ID: `{metadata['document_id']}`",
            f"- Source Type: `{metadata['source_type']}`",
            f"- Version: `{version}`",
            f"- Authority: `{authority}`",
            f"- Source URI: `{source_uri}`",
            f"- Derived From: `{relative_document_path}`",
            "",
            "## Source Projection",
            "",
            markdown.strip(),
        ]
    ).strip()


def _project_key_for_document(metadata: dict) -> str:
    if metadata["source_type"] == "jira":
        return str(metadata.get("metadata", {}).get("project") or metadata.get("provenance", {}).get("project") or "jira")
    if metadata["source_type"] == "confluence":
        return str(metadata.get("metadata", {}).get("space") or metadata.get("provenance", {}).get("space") or "confluence")
    return "specifications"


def _project_page_title(project_key: str, source_types: set[str]) -> str:
    if source_types == {"jira"}:
        return f"Project {project_key}"
    if source_types == {"confluence"}:
        return f"Space {project_key}"
    if source_types == {"pdf"}:
        return "Specifications"
    return f"Group {project_key}"


def _build_project_page(*, project_key: str, items: list[dict]) -> str:
    title = _project_page_title(project_key, {item["metadata"]["source_type"] for item in items})
    lines = [
        f"# {title}",
        "",
        "> Derived landing page. Canonical documents remain the source of truth.",
        "",
    ]
    for item in items:
        metadata = item["metadata"]
        source_page = item["source_page"]
        source_link = _relative_link("projects", source_page)
        lines.extend(
            [
                f"## [{metadata['title']}]({source_link})",
                f"- Document ID: `{metadata['document_id']}`",
                f"- Source Type: `{metadata['source_type']}`",
                f"- Version: `{metadata['version']}`",
                f"- Authority: `{metadata.get('authority_level')}`",
                "",
            ]
        )
    return "\n".join(lines).strip()


def _build_topic_page(*, topic_name: str, items: list[dict]) -> str:
    lines = [
        f"# Topic: {topic_name}",
        "",
        "> Deterministic topic page grouped by source type.",
        "",
    ]
    for item in items:
        metadata = item["metadata"]
        lines.append(
            f"- [{metadata['title']}]({_relative_link('topics', item['source_page'])}) (`{metadata['document_id']}` v`{metadata['version']}`)"
        )
    return "\n".join(lines).strip()


def _analysis_page(title: str, body: str, *, derived_from: list[str]) -> str:
    lines = [
        f"# {title}",
        "",
        "> Derived analysis page.",
        "",
        f"- Derived From: {', '.join(f'`{item}`' for item in derived_from)}",
        "",
        body.strip(),
    ]
    return "\n".join(lines).strip()


def _relative_link(current_dir: str, target: str) -> str:
    current = Path(current_dir)
    target_path = Path(target)
    return str(Path(os.path.relpath(target_path, current))).replace("\\", "/")


def _mkdocs_config(
    site_name: str,
    *,
    source_items: list[dict],
    project_groups: dict[str, list[dict]],
    topic_groups: dict[str, list[dict]],
    analysis_pages: list[dict],
) -> str:
    def yaml_string(value: str) -> str:
        return json.dumps(value, ensure_ascii=False)

    lines = [
        f"site_name: {site_name}",
        "theme:",
        "  name: material",
        "nav:",
        "  - Home: index.md",
        "  - Sources:",
        "      - Overview: sources/index.md",
    ]
    for item in sorted(source_items, key=lambda entry: (entry["metadata"]["source_type"], entry["metadata"]["document_id"])):
        lines.append(f"      - {yaml_string(item['metadata']['title'])}: {item['source_page']}")

    lines.extend(
        [
            "  - Projects:",
            "      - Overview: projects/index.md",
        ]
    )
    for project_key in sorted(project_groups):
        lines.append(f"      - {yaml_string(project_key)}: projects/{project_key}.md")

    lines.extend(
        [
            "  - Topics:",
            "      - Overview: topics/index.md",
        ]
    )
    for topic_name in sorted(topic_groups):
        lines.append(f"      - {yaml_string(topic_name)}: topics/{topic_name}.md")

    lines.extend(
        [
            "  - Analysis:",
            "      - Overview: analysis/index.md",
        ]
    )
    for analysis_page in analysis_pages:
        lines.append(f"      - {yaml_string(analysis_page['title'])}: analysis/{analysis_page['slug']}")

    lines.append("  - Log: log.md")
    return "\n".join(lines)


def build_wiki_site(
    *,
    export_root: str | Path,
    output_root: str | Path,
    site_title: str,
    analysis_pages: list[dict],
) -> dict:
    export_root_path = Path(export_root)
    output_root_path = Path(output_root)
    docs_root = output_root_path / "docs"
    docs_root.mkdir(parents=True, exist_ok=True)

    manifest = _load_json(export_root_path / "manifest.json")
    manifest_documents = manifest.get("documents", [])
    source_items: list[dict] = []
    project_groups: dict[str, list[dict]] = defaultdict(list)
    topic_groups: dict[str, list[dict]] = defaultdict(list)

    for item in manifest_documents:
        markdown = (export_root_path / item["markdown_path"]).read_text(encoding="utf-8")
        metadata = _load_json(export_root_path / item["metadata_path"])
        source_page = Path("sources") / metadata["source_type"] / f"{metadata['document_id']}.md"
        _write_text(docs_root / source_page, _source_page_markdown(metadata=metadata, markdown=markdown, relative_document_path=item["markdown_path"]))
        source_item = {"metadata": metadata, "source_page": str(source_page).replace("\\", "/")}
        source_items.append(source_item)
        project_groups[_safe_slug(_project_key_for_document(metadata))].append(source_item)
        topic_groups[_safe_slug(metadata["source_type"])].append(source_item)

    sources_index_lines = ["# Sources", "", "> Latest source pages generated from exported document projections.", ""]
    for item in sorted(source_items, key=lambda entry: (entry["metadata"]["source_type"], entry["metadata"]["document_id"])):
        metadata = item["metadata"]
        sources_index_lines.append(
            f"- [{metadata['title']}]({_relative_link('sources', item['source_page'])}) (`{metadata['source_type']}`)"
        )
    _write_text(docs_root / "sources" / "index.md", "\n".join(sources_index_lines).strip())

    projects_index_lines = ["# Projects", "", "> Deterministic landing pages grouped from exported metadata.", ""]
    for project_key, items in sorted(project_groups.items()):
        project_page = Path("projects") / f"{project_key}.md"
        _write_text(docs_root / project_page, _build_project_page(project_key=project_key, items=items))
        projects_index_lines.append(f"- [{project_key}]({project_page.name})")
    _write_text(docs_root / "projects" / "index.md", "\n".join(projects_index_lines).strip())

    topics_index_lines = ["# Topics", "", "> Deterministic grouping pages by source type.", ""]
    for topic_name, items in sorted(topic_groups.items()):
        topic_page = Path("topics") / f"{topic_name}.md"
        _write_text(docs_root / topic_page, _build_topic_page(topic_name=topic_name, items=items))
        topics_index_lines.append(f"- [{topic_name}]({topic_page.name})")
    _write_text(docs_root / "topics" / "index.md", "\n".join(topics_index_lines).strip())

    analysis_index_lines = ["# Analysis", "", "> Derived cross-source analysis pages.", ""]
    for analysis_page in analysis_pages:
        page_path = Path("analysis") / analysis_page["slug"]
        _write_text(
            docs_root / page_path,
            _analysis_page(
                analysis_page["title"],
                analysis_page["body"],
                derived_from=analysis_page.get("derived_from", []),
            ),
        )
        analysis_index_lines.append(f"- [{analysis_page['title']}]({page_path.name})")
    _write_text(docs_root / "analysis" / "index.md", "\n".join(analysis_index_lines).strip())

    index_md = "\n".join(
        [
            f"# {site_title}",
            "",
            "> Static derived wiki site built from exported document-level artifacts.",
            "",
            "- [Sources](sources/index.md)",
            "- [Projects](projects/index.md)",
            "- [Topics](topics/index.md)",
            "- [Analysis](analysis/index.md)",
            "- [Log](log.md)",
        ]
    ).strip()
    _write_text(docs_root / "index.md", index_md)
    _write_text(
        docs_root / "log.md",
        "\n".join(
            [
                "# Log",
                "",
                f"- Generated at: `{_utc_now()}`",
                f"- Export root: `{export_root_path}`",
                f"- Document count: `{len(manifest_documents)}`",
                f"- Analysis page count: `{len(analysis_pages)}`",
            ]
        ).strip(),
    )

    mkdocs_path = output_root_path / "mkdocs.yml"
    _write_text(
        mkdocs_path,
        _mkdocs_config(
            site_title,
            source_items=source_items,
            project_groups=project_groups,
            topic_groups=topic_groups,
            analysis_pages=analysis_pages,
        ),
    )

    return {
        "output_root": str(output_root_path),
        "docs_root": str(docs_root),
        "mkdocs_yml": str(mkdocs_path),
        "source_page_count": len(source_items),
        "project_page_count": len(project_groups),
        "topic_page_count": len(topic_groups),
        "analysis_page_count": len(analysis_pages),
    }

from __future__ import annotations

from pathlib import Path

from services.connectors.confluence.connector import fetch_confluence_page_sync, load_confluence_sync
from services.connectors.jira.connector import fetch_jira_server_sync, load_jira_sync
from services.ops.health import build_ops_health
from services.retrieval.persistence.snapshot_store import create_snapshot, load_snapshot, refresh_snapshot, snapshot_paths
from services.retrieval.toolkit import load_document_snapshot


def load_source_payload(
    *,
    kind: str,
    path: str | None,
    live: bool,
    base_url: str | None = None,
    username: str | None = None,
    password: str | None = None,
    token: str | None = None,
    auth_mode: str = "auto",
    cursor: str | None = None,
    page_size: int = 50,
    jql: str = "order by updated asc",
    cql: str | None = None,
    space_key: str | None = None,
    insecure: bool = False,
    fetch_backend: str = "native",
    issue_key: str | None = None,
    issue_keys: str | None = None,
    project_key: str | None = None,
    project_keys: str | None = None,
    issue_type: str | None = None,
    status: str | None = None,
    label: str | None = None,
    updated_from: str | None = None,
    updated_to: str | None = None,
    page_id: str | None = None,
    page_ids: str | None = None,
    root_page_id: str | None = None,
    title: str | None = None,
    ancestor_id: str | None = None,
    modified_from: str | None = None,
    modified_to: str | None = None,
    include_descendants: bool = False,
    max_depth: int | None = None,
    include_comments: bool = True,
    include_attachments: bool = True,
    include_image_metadata: bool = True,
    download_images: bool = False,
    image_download_dir: str | None = None,
) -> dict:
    if kind == "jira" and not live:
        return load_jira_sync(path)
    if kind == "confluence" and not live:
        return load_confluence_sync(path)
    if kind == "jira":
        return fetch_jira_server_sync(
            base_url=base_url,
            username=username,
            password=password,
            token=token,
            auth_mode=auth_mode,
            jql=jql,
            cursor=cursor,
            page_size=page_size,
            verify_ssl=not insecure,
            fetch_backend=fetch_backend,
            issue_key=issue_key,
            issue_keys=issue_keys,
            project_key=project_key,
            project_keys=project_keys,
            issue_type=issue_type,
            status=status,
            label=label,
            updated_from=updated_from,
            updated_to=updated_to,
            include_comments=include_comments,
            include_attachments=include_attachments,
            include_image_metadata=include_image_metadata,
            download_images=download_images,
            image_download_dir=image_download_dir,
        )
    return fetch_confluence_page_sync(
        base_url=base_url,
        username=username,
        password=password,
        token=token,
        auth_mode=auth_mode,
        cql=cql,
        space_key=space_key,
        cursor=cursor,
        page_size=page_size,
        verify_ssl=not insecure,
        fetch_backend=fetch_backend,
        page_id=page_id,
        page_ids=page_ids,
        root_page_id=root_page_id,
        title=title,
        label=label,
        ancestor_id=ancestor_id,
        modified_from=modified_from,
        modified_to=modified_to,
        include_descendants=include_descendants,
        max_depth=max_depth,
        include_attachments=include_attachments,
        include_image_metadata=include_image_metadata,
        download_images=download_images,
        image_download_dir=image_download_dir,
    )


def ensure_snapshot(snapshot_dir: str | Path, corpus: str | Path, source_name: str = "manual") -> dict:
    manifest_path = snapshot_paths(snapshot_dir)["manifest"]
    if manifest_path.exists():
        return load_snapshot(snapshot_dir)
    create_snapshot(
        snapshot_dir,
        documents=load_document_snapshot(corpus),
        source_name=source_name,
        sync_type="full",
    )
    return load_snapshot(snapshot_dir)


def run_sync_health(
    *,
    snapshot_dir: str | Path,
    corpus: str | Path,
    kind: str,
    path: str | None,
    live: bool,
    base_url: str | None = None,
    username: str | None = None,
    password: str | None = None,
    token: str | None = None,
    auth_mode: str = "auto",
    cursor: str | None = None,
    page_size: int = 50,
    jql: str = "order by updated asc",
    cql: str | None = None,
    space_key: str | None = None,
    insecure: bool = False,
    freshness_budget_minutes: int = 30,
    reference_time_iso: str | None = None,
    fetch_backend: str = "native",
    issue_key: str | None = None,
    issue_keys: str | None = None,
    project_key: str | None = None,
    project_keys: str | None = None,
    issue_type: str | None = None,
    status: str | None = None,
    label: str | None = None,
    updated_from: str | None = None,
    updated_to: str | None = None,
    page_id: str | None = None,
    page_ids: str | None = None,
    root_page_id: str | None = None,
    title: str | None = None,
    ancestor_id: str | None = None,
    modified_from: str | None = None,
    modified_to: str | None = None,
    include_descendants: bool = False,
    max_depth: int | None = None,
    include_comments: bool = True,
    include_attachments: bool = True,
    include_image_metadata: bool = True,
    download_images: bool = False,
    image_download_dir: str | None = None,
) -> dict:
    ensure_snapshot(snapshot_dir, corpus)
    sync_payload = load_source_payload(
        kind=kind,
        path=path,
        live=live,
        base_url=base_url,
        username=username,
        password=password,
        token=token,
        auth_mode=auth_mode,
        cursor=cursor,
        page_size=page_size,
        jql=jql,
        cql=cql,
        space_key=space_key,
        insecure=insecure,
        fetch_backend=fetch_backend,
        issue_key=issue_key,
        issue_keys=issue_keys,
        project_key=project_key,
        project_keys=project_keys,
        issue_type=issue_type,
        status=status,
        label=label,
        updated_from=updated_from,
        updated_to=updated_to,
        page_id=page_id,
        page_ids=page_ids,
        root_page_id=root_page_id,
        title=title,
        ancestor_id=ancestor_id,
        modified_from=modified_from,
        modified_to=modified_to,
        include_descendants=include_descendants,
        max_depth=max_depth,
        include_comments=include_comments,
        include_attachments=include_attachments,
        include_image_metadata=include_image_metadata,
        download_images=download_images,
        image_download_dir=image_download_dir,
    )
    refresh_report = refresh_snapshot(
        snapshot_dir,
        sync_payload=sync_payload,
        source_name=kind,
    )
    health_report = build_ops_health(
        snapshot_dir=snapshot_dir,
        freshness_budget_minutes=freshness_budget_minutes,
        reference_time_iso=reference_time_iso,
    )
    return {
        "snapshot_dir": str(Path(snapshot_dir)),
        "sync": {
            "source_name": kind,
            "sync_type": sync_payload.get("sync_type"),
            "cursor": sync_payload.get("cursor"),
            "document_count": len(sync_payload.get("documents", [])),
        },
        "refresh": refresh_report,
        "ops_health": health_report,
    }


def run_multi_sync_health(profile: dict) -> dict:
    snapshot_dir = profile["snapshot_dir"]
    ensure_snapshot(snapshot_dir, profile["corpus"])
    refresh_reports = []
    for config in profile["sources"]:
        sync_payload = load_source_payload(
            kind=config["kind"],
            path=config["path"],
            live=config["live"],
            base_url=config.get("base_url"),
            username=config.get("username"),
            password=config.get("password"),
            token=config.get("token"),
            auth_mode=config.get("auth_mode", "auto"),
            cursor=config.get("cursor"),
            page_size=config.get("page_size", 50),
            jql=config.get("jql", "order by updated asc"),
            cql=config.get("cql"),
            space_key=config.get("space_key"),
            insecure=config.get("insecure", False),
            fetch_backend=config.get("fetch_backend", "native"),
            issue_key=config.get("issue_key"),
            issue_keys=config.get("issue_keys"),
            project_key=config.get("project_key"),
            project_keys=config.get("project_keys"),
            issue_type=config.get("issue_type"),
            status=config.get("status"),
            label=config.get("label"),
            updated_from=config.get("updated_from"),
            updated_to=config.get("updated_to"),
            page_id=config.get("page_id"),
            page_ids=config.get("page_ids"),
            root_page_id=config.get("root_page_id"),
            title=config.get("title"),
            ancestor_id=config.get("ancestor_id"),
            modified_from=config.get("modified_from"),
            modified_to=config.get("modified_to"),
            include_descendants=config.get("include_descendants", False),
            max_depth=config.get("max_depth"),
            include_comments=config.get("include_comments", True),
            include_attachments=config.get("include_attachments", True),
            include_image_metadata=config.get("include_image_metadata", True),
            download_images=config.get("download_images", False),
            image_download_dir=config.get("image_download_dir"),
        )
        refresh_reports.append(
            {
                "source_name": config["source_name"],
                "sync": {
                    "sync_type": sync_payload.get("sync_type"),
                    "cursor": sync_payload.get("cursor"),
                    "document_count": len(sync_payload.get("documents", [])),
                },
                "refresh": refresh_snapshot(
                    snapshot_dir,
                    sync_payload=sync_payload,
                    source_name=config["source_name"],
                ),
            }
        )
    health_report = build_ops_health(
        snapshot_dir=snapshot_dir,
        freshness_budget_minutes=profile["freshness_budget_minutes"],
        reference_time_iso=profile["reference_time_iso"],
    )
    return {
        "snapshot_dir": str(Path(snapshot_dir)),
        "sources": refresh_reports,
        "ops_health": health_report,
    }


def _resolve_source_cursor(manifest: dict, config: dict) -> str | None:
    if config.get("cursor"):
        return config["cursor"]
    if not config.get("live"):
        return None
    source_manifest = manifest.get("sources", {}).get(config["source_name"], {})
    return source_manifest.get("cursor")


def configured_sources(profile: dict) -> list[dict]:
    return [
        config
        for config in profile["sources"]
        if config.get("live") or config.get("path")
    ]


def run_sync_export(profile: dict, *, export_scope: str = "incoming") -> dict:
    snapshot_dir = profile["snapshot_dir"]
    ensure_snapshot(snapshot_dir, profile["corpus"])
    loaded_snapshot = load_snapshot(snapshot_dir)
    incoming_documents = []
    refresh_reports = []

    for config in configured_sources(profile):
        sync_payload = load_source_payload(
            kind=config["kind"],
            path=config["path"],
            live=config["live"],
            base_url=config.get("base_url"),
            username=config.get("username"),
            password=config.get("password"),
            token=config.get("token"),
            auth_mode=config.get("auth_mode", "auto"),
            cursor=_resolve_source_cursor(loaded_snapshot["manifest"], config),
            page_size=config.get("page_size", 50),
            jql=config.get("jql", "order by updated asc"),
            cql=config.get("cql"),
            space_key=config.get("space_key"),
            insecure=config.get("insecure", False),
            fetch_backend=config.get("fetch_backend", "native"),
            issue_key=config.get("issue_key"),
            issue_keys=config.get("issue_keys"),
            project_key=config.get("project_key"),
            project_keys=config.get("project_keys"),
            issue_type=config.get("issue_type"),
            status=config.get("status"),
            label=config.get("label"),
            updated_from=config.get("updated_from"),
            updated_to=config.get("updated_to"),
            page_id=config.get("page_id"),
            page_ids=config.get("page_ids"),
            root_page_id=config.get("root_page_id"),
            title=config.get("title"),
            ancestor_id=config.get("ancestor_id"),
            modified_from=config.get("modified_from"),
            modified_to=config.get("modified_to"),
            include_descendants=config.get("include_descendants", False),
            max_depth=config.get("max_depth"),
            include_comments=config.get("include_comments", True),
            include_attachments=config.get("include_attachments", True),
            include_image_metadata=config.get("include_image_metadata", True),
            download_images=config.get("download_images", False),
            image_download_dir=config.get("image_download_dir"),
        )
        incoming_documents.extend(sync_payload.get("documents", []))
        refresh_reports.append(
            {
                "source_name": config["source_name"],
                "sync": {
                    "sync_type": sync_payload.get("sync_type"),
                    "cursor": sync_payload.get("cursor"),
                    "document_count": len(sync_payload.get("documents", [])),
                },
                "refresh": refresh_snapshot(
                    snapshot_dir,
                    sync_payload=sync_payload,
                    source_name=config["source_name"],
                ),
            }
        )
        loaded_snapshot = load_snapshot(snapshot_dir)

    if export_scope == "snapshot":
        export_documents = loaded_snapshot["documents"].get("documents", [])
    else:
        export_documents = incoming_documents

    return {
        "snapshot_dir": str(Path(snapshot_dir)),
        "export_scope": export_scope,
        "sources": refresh_reports,
        "document_count": len(export_documents),
        "documents": export_documents,
    }

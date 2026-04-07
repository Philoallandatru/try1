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

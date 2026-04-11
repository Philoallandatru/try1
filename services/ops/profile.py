from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_json_file(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate_multi_sync_profile(profile: dict) -> list[str]:
    errors: list[str] = []
    if not isinstance(profile, dict):
        return ["profile must be a JSON object"]
    for required_source in ("jira", "confluence"):
        source_profile = profile.get(required_source)
        if not isinstance(source_profile, dict):
            errors.append(f"profile.{required_source} must be an object")
            continue
        live = source_profile.get("live", False)
        path = source_profile.get("path")
        base_url = source_profile.get("base_url")
        page_size = source_profile.get("page_size")
        auth_mode = source_profile.get("auth_mode")
        fetch_backend = source_profile.get("fetch_backend")
        if live and not base_url:
            errors.append(f"profile.{required_source}.base_url is required when live is true")
        if not live and not path:
            errors.append(f"profile.{required_source}.path is required when live is false or unset")
        if page_size is not None and (not isinstance(page_size, int) or page_size <= 0):
            errors.append(f"profile.{required_source}.page_size must be a positive integer")
        if auth_mode is not None and auth_mode not in {"auto", "basic", "bearer"}:
            errors.append(f"profile.{required_source}.auth_mode must be one of: auto, basic, bearer")
        if fetch_backend is not None and fetch_backend not in {"native", "atlassian-api"}:
            errors.append(f"profile.{required_source}.fetch_backend must be one of: native, atlassian-api")
        if source_profile.get("download_images") and not source_profile.get("image_download_dir"):
            errors.append(f"profile.{required_source}.image_download_dir is required when download_images is true")
    budget = profile.get("freshness_budget_minutes")
    if budget is not None and (not isinstance(budget, int) or budget <= 0):
        errors.append("profile.freshness_budget_minutes must be a positive integer")
    defaults = profile.get("defaults")
    if defaults is not None:
        if not isinstance(defaults, dict):
            errors.append("profile.defaults must be an object")
        else:
            default_budget = defaults.get("freshness_budget_minutes")
            if default_budget is not None and (not isinstance(default_budget, int) or default_budget <= 0):
                errors.append("profile.defaults.freshness_budget_minutes must be a positive integer")
    return errors


def merge_non_null(base: dict, overrides: dict) -> dict:
    merged = dict(base)
    for key, value in overrides.items():
        if value is not None:
            merged[key] = value
    return merged


def _arg(args: argparse.Namespace, name: str, default=None):
    return getattr(args, name, default)


def build_multi_sync_profile(args: argparse.Namespace) -> dict:
    profile = load_json_file(args.profile) if _arg(args, "profile") else {}
    jira_profile = profile.get("jira", {})
    confluence_profile = profile.get("confluence", {})
    defaults = profile.get("defaults", {})

    jira_page_size = _arg(args, "jira_page_size", 50)
    jira_auth_mode = _arg(args, "jira_auth_mode", "auto")
    jira_jql = _arg(args, "jira_jql", "order by updated asc")
    jira_fetch_backend = _arg(args, "jira_fetch_backend", "native")
    jira_config = merge_non_null(
        jira_profile,
        {
            "source_name": "jira",
            "kind": "jira",
            "path": _arg(args, "jira_path"),
            "live": _arg(args, "jira_live") if _arg(args, "jira_live") else None,
            "fetch_backend": jira_fetch_backend if jira_fetch_backend != "native" else jira_profile.get("fetch_backend"),
            "base_url": _arg(args, "jira_base_url"),
            "username": _arg(args, "jira_username"),
            "password": _arg(args, "jira_password"),
            "token": _arg(args, "jira_token"),
            "auth_mode": jira_auth_mode if jira_auth_mode != "auto" else jira_profile.get("auth_mode"),
            "cursor": _arg(args, "jira_cursor"),
            "page_size": jira_page_size if jira_page_size != 50 else jira_profile.get("page_size"),
            "jql": jira_jql if jira_jql != "order by updated asc" else jira_profile.get("jql"),
            "issue_key": _arg(args, "jira_issue_key"),
            "issue_keys": _arg(args, "jira_issue_keys"),
            "project_key": _arg(args, "jira_project_key"),
            "project_keys": _arg(args, "jira_project_keys"),
            "issue_type": _arg(args, "jira_issue_type"),
            "status": _arg(args, "jira_status"),
            "label": _arg(args, "jira_label"),
            "updated_from": _arg(args, "jira_updated_from"),
            "updated_to": _arg(args, "jira_updated_to"),
            "include_comments": False if _arg(args, "jira_no_include_comments", False) else jira_profile.get("include_comments"),
            "include_attachments": False if _arg(args, "jira_no_include_attachments", False) else jira_profile.get("include_attachments"),
            "include_image_metadata": False if _arg(args, "jira_no_include_image_metadata", False) else jira_profile.get("include_image_metadata"),
            "download_images": True if _arg(args, "jira_download_images", False) else jira_profile.get("download_images"),
            "image_download_dir": _arg(args, "jira_image_download_dir"),
            "insecure": True if _arg(args, "jira_insecure", False) else jira_profile.get("insecure"),
        },
    )
    jira_config.setdefault("source_name", "jira")
    jira_config.setdefault("kind", "jira")
    jira_config.setdefault("path", None)
    jira_config.setdefault("live", False)
    jira_config.setdefault("auth_mode", "auto")
    jira_config.setdefault("page_size", 50)
    jira_config.setdefault("fetch_backend", "native")
    jira_config.setdefault("jql", "order by updated asc")
    jira_config.setdefault("include_comments", True)
    jira_config.setdefault("include_attachments", True)
    jira_config.setdefault("include_image_metadata", True)
    jira_config.setdefault("download_images", False)
    jira_config.setdefault("insecure", False)

    confluence_page_size = _arg(args, "confluence_page_size", 25)
    confluence_auth_mode = _arg(args, "confluence_auth_mode", "auto")
    confluence_fetch_backend = _arg(args, "confluence_fetch_backend", "native")
    confluence_config = merge_non_null(
        confluence_profile,
        {
            "source_name": "confluence",
            "kind": "confluence",
            "path": _arg(args, "confluence_path"),
            "live": _arg(args, "confluence_live") if _arg(args, "confluence_live") else None,
            "fetch_backend": confluence_fetch_backend if confluence_fetch_backend != "native" else confluence_profile.get("fetch_backend"),
            "base_url": _arg(args, "confluence_base_url"),
            "username": _arg(args, "confluence_username"),
            "password": _arg(args, "confluence_password"),
            "token": _arg(args, "confluence_token"),
            "auth_mode": confluence_auth_mode if confluence_auth_mode != "auto" else confluence_profile.get("auth_mode"),
            "cursor": _arg(args, "confluence_cursor"),
            "page_size": confluence_page_size if confluence_page_size != 25 else confluence_profile.get("page_size"),
            "cql": _arg(args, "confluence_cql"),
            "space_key": _arg(args, "confluence_space_key"),
            "page_id": _arg(args, "confluence_page_id"),
            "page_ids": _arg(args, "confluence_page_ids"),
            "title": _arg(args, "confluence_title"),
            "label": _arg(args, "confluence_label"),
            "ancestor_id": _arg(args, "confluence_ancestor_id"),
            "modified_from": _arg(args, "confluence_modified_from"),
            "modified_to": _arg(args, "confluence_modified_to"),
            "include_attachments": False if _arg(args, "confluence_no_include_attachments", False) else confluence_profile.get("include_attachments"),
            "include_image_metadata": False if _arg(args, "confluence_no_include_image_metadata", False) else confluence_profile.get("include_image_metadata"),
            "download_images": True if _arg(args, "confluence_download_images", False) else confluence_profile.get("download_images"),
            "image_download_dir": _arg(args, "confluence_image_download_dir"),
            "insecure": True if _arg(args, "confluence_insecure", False) else confluence_profile.get("insecure"),
        },
    )
    confluence_config.setdefault("source_name", "confluence")
    confluence_config.setdefault("kind", "confluence")
    confluence_config.setdefault("path", None)
    confluence_config.setdefault("live", False)
    confluence_config.setdefault("auth_mode", "auto")
    confluence_config.setdefault("page_size", 25)
    confluence_config.setdefault("fetch_backend", "native")
    confluence_config.setdefault("include_attachments", True)
    confluence_config.setdefault("include_image_metadata", True)
    confluence_config.setdefault("download_images", False)
    confluence_config.setdefault("insecure", False)

    corpus = _arg(args, "corpus", "fixtures/retrieval/pageindex_corpus.json")
    freshness_budget_minutes = _arg(args, "freshness_budget_minutes", 30)
    return {
        "snapshot_dir": _arg(args, "snapshot_dir") or profile.get("snapshot_dir"),
        "corpus": (
            corpus
            if corpus != "fixtures/retrieval/pageindex_corpus.json"
            else profile.get("corpus", "fixtures/retrieval/pageindex_corpus.json")
        ),
        "freshness_budget_minutes": (
            freshness_budget_minutes
            if freshness_budget_minutes != 30
            else profile.get("freshness_budget_minutes", defaults.get("freshness_budget_minutes", 30))
        ),
        "reference_time_iso": _arg(args, "reference_time_iso") or profile.get("reference_time_iso") or defaults.get("reference_time_iso"),
        "sources": [jira_config, confluence_config],
    }

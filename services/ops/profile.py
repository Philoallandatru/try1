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
        if live and not base_url:
            errors.append(f"profile.{required_source}.base_url is required when live is true")
        if not live and not path:
            errors.append(f"profile.{required_source}.path is required when live is false or unset")
        if page_size is not None and (not isinstance(page_size, int) or page_size <= 0):
            errors.append(f"profile.{required_source}.page_size must be a positive integer")
        if auth_mode is not None and auth_mode not in {"auto", "basic", "bearer"}:
            errors.append(f"profile.{required_source}.auth_mode must be one of: auto, basic, bearer")
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


def build_multi_sync_profile(args: argparse.Namespace) -> dict:
    profile = load_json_file(args.profile) if args.profile else {}
    jira_profile = profile.get("jira", {})
    confluence_profile = profile.get("confluence", {})
    defaults = profile.get("defaults", {})

    jira_config = merge_non_null(
        jira_profile,
        {
            "source_name": "jira",
            "kind": "jira",
            "path": args.jira_path,
            "live": args.jira_live if args.jira_live else None,
            "base_url": args.jira_base_url,
            "username": args.jira_username,
            "password": args.jira_password,
            "token": args.jira_token,
            "auth_mode": args.jira_auth_mode if args.jira_auth_mode != "auto" else jira_profile.get("auth_mode"),
            "cursor": args.jira_cursor,
            "page_size": args.jira_page_size if args.jira_page_size != 50 else jira_profile.get("page_size"),
            "jql": args.jira_jql if args.jira_jql != "order by updated asc" else jira_profile.get("jql"),
            "insecure": True if args.jira_insecure else jira_profile.get("insecure"),
        },
    )
    jira_config.setdefault("source_name", "jira")
    jira_config.setdefault("kind", "jira")
    jira_config.setdefault("path", None)
    jira_config.setdefault("live", False)
    jira_config.setdefault("auth_mode", "auto")
    jira_config.setdefault("page_size", 50)
    jira_config.setdefault("jql", "order by updated asc")
    jira_config.setdefault("insecure", False)

    confluence_config = merge_non_null(
        confluence_profile,
        {
            "source_name": "confluence",
            "kind": "confluence",
            "path": args.confluence_path,
            "live": args.confluence_live if args.confluence_live else None,
            "base_url": args.confluence_base_url,
            "username": args.confluence_username,
            "password": args.confluence_password,
            "token": args.confluence_token,
            "auth_mode": args.confluence_auth_mode if args.confluence_auth_mode != "auto" else confluence_profile.get("auth_mode"),
            "cursor": args.confluence_cursor,
            "page_size": args.confluence_page_size if args.confluence_page_size != 25 else confluence_profile.get("page_size"),
            "cql": args.confluence_cql,
            "space_key": args.confluence_space_key,
            "insecure": True if args.confluence_insecure else confluence_profile.get("insecure"),
        },
    )
    confluence_config.setdefault("source_name", "confluence")
    confluence_config.setdefault("kind", "confluence")
    confluence_config.setdefault("path", None)
    confluence_config.setdefault("live", False)
    confluence_config.setdefault("auth_mode", "auto")
    confluence_config.setdefault("page_size", 25)
    confluence_config.setdefault("insecure", False)

    return {
        "snapshot_dir": args.snapshot_dir or profile.get("snapshot_dir"),
        "corpus": (
            args.corpus
            if args.corpus != "fixtures/retrieval/pageindex_corpus.json"
            else profile.get("corpus", "fixtures/retrieval/pageindex_corpus.json")
        ),
        "freshness_budget_minutes": (
            args.freshness_budget_minutes
            if args.freshness_budget_minutes != 30
            else profile.get("freshness_budget_minutes", defaults.get("freshness_budget_minutes", 30))
        ),
        "reference_time_iso": args.reference_time_iso or profile.get("reference_time_iso") or defaults.get("reference_time_iso"),
        "sources": [jira_config, confluence_config],
    }

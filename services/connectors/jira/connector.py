from __future__ import annotations

from base64 import b64encode
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import json
import re
import ssl

from services.connectors.jira.field_aliases import load_jira_field_aliases
from services.ingest.normalizer import normalize_markdown_text
from services.ingest.visual_assets import (
    append_visual_asset_to_document,
    build_visual_asset_markdown,
    image_asset_from_attachment,
    is_image_media_type,
)


def _build_auth_header(
    *,
    username: str | None = None,
    password: str | None = None,
    token: str | None = None,
    auth_mode: str = "auto",
) -> str | None:
    effective_mode = auth_mode
    if auth_mode == "auto":
        effective_mode = "basic" if username and (password or token) else "bearer"

    if effective_mode == "basic" and username and (password or token):
        secret = password or token or ""
        encoded = b64encode(f"{username}:{secret}".encode("utf-8")).decode("ascii")
        return f"Basic {encoded}"
    if effective_mode == "bearer" and token:
        return f"Bearer {token}"
    return None


def _request_json(url: str, *, headers: dict[str, str], verify_ssl: bool = True) -> dict:
    request = Request(url, headers=headers)
    ssl_context = None if verify_ssl else ssl._create_unverified_context()
    with urlopen(request, context=ssl_context) as response:
        return json.loads(response.read().decode("utf-8"))


def _markdown_escape(text: str) -> str:
    return re.sub(r"([*_`])", r"\\\1", text)


def _coerce_jira_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        if isinstance(value.get("content"), list):
            parts = [_coerce_jira_text(item) for item in value["content"]]
            return "\n".join(part for part in parts if part).strip()
        for key in ("text", "body", "value"):
            text = value.get(key)
            if isinstance(text, str) and text.strip():
                return text.strip()
    if isinstance(value, list):
        parts = [_coerce_jira_text(item) for item in value]
        return "\n".join(part for part in parts if part).strip()
    return str(value).strip()


def _coerce_issue_field_value(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        for key in ("name", "value", "displayName", "key"):
            text = value.get(key)
            if isinstance(text, str) and text.strip():
                return text.strip()
        return _coerce_jira_text(value)
    if isinstance(value, list):
        parts = [_coerce_issue_field_value(item) for item in value]
        return ", ".join(part for part in parts if part)
    return str(value).strip()


def _extract_issue_field(issue: dict, field_names: list[str], field_name_map: dict[str, str] | None = None) -> str:
    fields = issue.get("fields", {})
    normalized_names = {name.strip().lower() for name in field_names}
    for field_name in field_names:
        if field_name in fields:
            value = _coerce_issue_field_value(fields.get(field_name))
            if value:
                return value
        if field_name in issue:
            value = _coerce_issue_field_value(issue.get(field_name))
            if value:
                return value
    if field_name_map:
        for field_key, display_name in field_name_map.items():
            if display_name.strip().lower() not in normalized_names:
                continue
            if field_key in fields:
                value = _coerce_issue_field_value(fields.get(field_key))
                if value:
                    return value
    return ""


def _collect_issue_fields(
    issue: dict,
    field_name_map: dict[str, str] | None = None,
    field_aliases: dict[str, list[str]] | None = None,
) -> dict[str, str]:
    aliases = field_aliases or load_jira_field_aliases()
    collected = {}
    for label, alias_names in aliases.items():
        value = _extract_issue_field(issue, [label, *alias_names], field_name_map)
        if value:
            collected[label] = value
    return collected


def _comment_to_markdown(comment: object) -> str:
    if not isinstance(comment, dict):
        return _markdown_escape(_coerce_jira_text(comment))
    author = comment.get("author") or {}
    author_name = _coerce_issue_field_value(author) or "Unknown"
    created_at = _coerce_jira_text(comment.get("created"))
    body = _coerce_jira_text(comment.get("body"))
    prefix = author_name
    if created_at:
        prefix = f"{prefix} ({created_at})"
    if body:
        return f"**{_markdown_escape(prefix)}**: {_markdown_escape(body)}"
    return _markdown_escape(prefix)


def _attachment_to_markdown(attachment: dict, *, document_id: str | None = None, source_uri: str | None = None) -> str:
    name = attachment.get("filename") or attachment.get("name") or "attachment"
    mime_type = attachment.get("mimeType") or attachment.get("media_type") or "application/octet-stream"
    content = attachment.get("content") or attachment.get("downloadLink") or ""
    if document_id and source_uri and is_image_media_type(mime_type):
        asset = image_asset_from_attachment(
            attachment,
            source_type="jira",
            document_id=document_id,
            source_uri=source_uri,
            section="Attachments",
        )
        return build_visual_asset_markdown(asset)
    suffix = f" ({mime_type})"
    if content:
        return f"- [{name}]({content}){suffix}"
    return f"- {name}{suffix}"


def _issue_to_markdown(
    issue: dict,
    *,
    source_uri: str,
    field_name_map: dict[str, str] | None = None,
    field_aliases: dict[str, list[str]] | None = None,
) -> str:
    fields = issue.get("fields", {})
    summary = fields.get("summary") or issue.get("summary") or issue.get("key") or "Untitled Jira Issue"
    description = _coerce_jira_text(fields.get("description") or issue.get("description"))
    issue_fields = _collect_issue_fields(issue, field_name_map, field_aliases)
    root_cause = issue_fields.get("Root Cause", "")
    how_to_fix = issue_fields.get("How to fix", "")
    action = issue_fields.get("Action", "")
    comments_payload = fields.get("comment", {})
    comment_items = comments_payload.get("comments", issue.get("comments", []))
    comments = [_comment_to_markdown(comment) for comment in comment_items]
    comments = [comment for comment in comments if comment]
    attachments = fields.get("attachment", issue.get("attachments", []))

    lines = [f"# {issue.get('key', 'JIRA')} {summary}"]
    if issue_fields:
        lines.extend(["", "## Issue Fields"])
        lines.extend(f"- **{label}**: {_markdown_escape(value)}" for label, value in issue_fields.items())
    lines.extend(["", "## Description", description or "No description."])
    if root_cause and root_cause.lower() != "undefine":
        lines.extend(["", "## Root Cause", root_cause])
    if how_to_fix:
        lines.extend(["", "## How To Fix", how_to_fix])
    if action:
        lines.extend(["", "## Action", action])
    if comments:
        lines.extend(["", "## Comments"])
        lines.extend(f"- {comment}" for comment in comments)
    if attachments:
        lines.extend(["", "## Attachments"])
        lines.extend(
            _attachment_to_markdown(
                attachment,
                document_id=issue.get("key", "JIRA"),
                source_uri=source_uri,
            )
            for attachment in attachments
        )
    return "\n".join(lines)


def _issue_to_document(
    issue: dict,
    *,
    source_uri: str,
    incremental: bool,
    acl_policy: str,
    field_name_map: dict[str, str] | None = None,
    field_aliases: dict[str, list[str]] | None = None,
) -> dict:
    fields = issue.get("fields", {})
    project = fields.get("project", {})
    summary = fields.get("summary") or issue.get("summary") or issue.get("key") or "Untitled Jira Issue"
    updated_at = fields.get("updated") or issue.get("updated_at") or "fixture"
    comments_payload = fields.get("comment", {})
    comment_items = comments_payload.get("comments", issue.get("comments", []))
    attachments = fields.get("attachment", issue.get("attachments", []))
    issue_fields = _collect_issue_fields(issue, field_name_map, field_aliases)
    markdown = _issue_to_markdown(
        issue,
        source_uri=source_uri,
        field_name_map=field_name_map,
        field_aliases=field_aliases,
    )

    document = normalize_markdown_text(
        markdown,
        document_id=issue["key"],
        source_type="jira",
        authority_level="supporting",
        version=updated_at,
        language="en",
        title=summary,
        source_uri=source_uri,
        ingested_at=updated_at,
        parser="jira-markdown-normalizer",
        acl_policy=acl_policy,
        extra_provenance={"project": project.get("key") or issue.get("project")},
    )
    document["markdown"] = markdown
    document["comments"] = [_coerce_jira_text(comment.get("body") if isinstance(comment, dict) else comment) for comment in comment_items]
    document["attachments"] = attachments
    document["visual_assets"] = []
    document["metadata"] = {
        "project": project.get("key") or issue.get("project"),
        "incremental": incremental,
        "comment_count": len([comment for comment in document["comments"] if comment]),
        "attachment_count": len(attachments),
        "visual_asset_count": 0,
        "issue_fields": issue_fields,
    }
    for attachment in attachments:
        mime_type = attachment.get("mimeType") or attachment.get("media_type")
        if not is_image_media_type(mime_type):
            continue
        asset = image_asset_from_attachment(
            attachment,
            source_type="jira",
            document_id=issue["key"],
            source_uri=source_uri,
            section="Attachments",
        )
        append_visual_asset_to_document(document, asset)
    return document


def load_jira_sync(path: str | Path) -> dict:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    field_name_map = payload.get("names")
    field_aliases = load_jira_field_aliases()
    documents = [
        _issue_to_document(
            issue,
            source_uri=str(path).replace("\\", "/"),
            incremental=payload["sync_type"] == "incremental",
            acl_policy="team:ssd",
            field_name_map=field_name_map,
            field_aliases=field_aliases,
        )
        for issue in payload["issues"]
    ]
    return {
        "sync_type": payload["sync_type"],
        "cursor": payload["cursor"],
        "documents": documents,
    }


def fetch_jira_server_sync(
    *,
    base_url: str,
    username: str | None = None,
    password: str | None = None,
    token: str | None = None,
    auth_mode: str = "auto",
    jql: str = "order by updated asc",
    cursor: str | None = None,
    page_size: int = 50,
    verify_ssl: bool = True,
    acl_policy: str = "team:ssd",
) -> dict:
    normalized_base_url = base_url.rstrip("/")
    headers = {"Accept": "application/json"}
    auth_header = _build_auth_header(username=username, password=password, token=token, auth_mode=auth_mode)
    if auth_header:
        headers["Authorization"] = auth_header

    effective_jql = jql
    if cursor:
        effective_jql = f"({jql}) AND updated >= \"{cursor}\""

    documents = []
    start_at = 0
    total = None
    field_aliases = load_jira_field_aliases()
    while total is None or start_at < total:
        query = urlencode(
            {
                "jql": effective_jql,
                "startAt": start_at,
                "maxResults": page_size,
                "fields": "*all",
                "expand": "names",
            }
        )
        payload = _request_json(
            f"{normalized_base_url}/rest/api/2/search?{query}",
            headers=headers,
            verify_ssl=verify_ssl,
        )
        issues = payload.get("issues", [])
        field_name_map = payload.get("names", {})
        total = payload.get("total", len(issues))
        if not issues:
            break

        for issue in issues:
            documents.append(
                _issue_to_document(
                    issue,
                    source_uri=f"{normalized_base_url}/browse/{issue['key']}",
                    incremental=cursor is not None,
                    acl_policy=acl_policy,
                    field_name_map=field_name_map,
                    field_aliases=field_aliases,
                )
            )
        start_at += len(issues)

    next_cursor = cursor
    if documents:
        next_cursor = max(document["version"] for document in documents)

    return {
        "sync_type": "incremental" if cursor else "full",
        "cursor": next_cursor,
        "documents": documents,
    }

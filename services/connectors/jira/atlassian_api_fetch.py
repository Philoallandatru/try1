from __future__ import annotations

from base64 import b64encode
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import json
import ssl


def _import_jira_client():
    from atlassian import Jira

    return Jira


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


def _parse_csv_values(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _quote_jql_value(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _build_jql(
    *,
    issue_key: str | None = None,
    issue_keys: str | None = None,
    project_key: str | None = None,
    project_keys: str | None = None,
    issue_type: str | None = None,
    status: str | None = None,
    label: str | None = None,
    updated_from: str | None = None,
    updated_to: str | None = None,
    cursor: str | None = None,
    jql: str | None = None,
) -> str:
    helper_values = [
        issue_key,
        issue_keys,
        project_key,
        project_keys,
        issue_type,
        status,
        label,
        updated_from,
        updated_to,
    ]
    if jql and not (jql == "order by updated asc" and any(helper_values)):
        return jql

    clauses: list[str] = []

    exact_issue_keys = []
    if issue_key:
        exact_issue_keys.append(issue_key.strip())
    exact_issue_keys.extend(_parse_csv_values(issue_keys))
    if exact_issue_keys:
        if len(exact_issue_keys) == 1:
            clauses.append(f"issuekey = {_quote_jql_value(exact_issue_keys[0])}")
        else:
            joined = ", ".join(_quote_jql_value(item) for item in exact_issue_keys)
            clauses.append(f"issuekey in ({joined})")

    exact_project_keys = []
    if project_key:
        exact_project_keys.append(project_key.strip())
    exact_project_keys.extend(_parse_csv_values(project_keys))
    if exact_project_keys:
        if len(exact_project_keys) == 1:
            clauses.append(f"project = {_quote_jql_value(exact_project_keys[0])}")
        else:
            joined = ", ".join(_quote_jql_value(item) for item in exact_project_keys)
            clauses.append(f"project in ({joined})")

    if issue_type:
        clauses.append(f"issuetype = {_quote_jql_value(issue_type)}")
    if status:
        clauses.append(f"status = {_quote_jql_value(status)}")
    if label:
        clauses.append(f"labels = {_quote_jql_value(label)}")

    effective_updated_from = updated_from or cursor
    if effective_updated_from:
        clauses.append(f"updated >= {_quote_jql_value(effective_updated_from)}")
    if updated_to:
        clauses.append(f"updated <= {_quote_jql_value(updated_to)}")

    if not clauses:
        return "order by updated asc"
    return " AND ".join(clauses) + " order by updated asc"


def _build_client(
    *,
    base_url: str,
    username: str | None = None,
    password: str | None = None,
    token: str | None = None,
    auth_mode: str = "auto",
    verify_ssl: bool = True,
):
    Jira = _import_jira_client()
    client_kwargs: dict[str, object] = {"url": base_url.rstrip("/")}
    if auth_mode == "bearer" and token:
        client_kwargs["token"] = token
    elif username and (password or token):
        client_kwargs["username"] = username
        client_kwargs["password"] = password or token
    elif token:
        client_kwargs["token"] = token
    if not verify_ssl:
        client_kwargs["verify_ssl"] = False
    return Jira(**client_kwargs)


def _jira_get(client, path: str, params: dict[str, object] | None = None) -> dict:
    payload = client.get(path, params=params)
    if isinstance(payload, bytes):
        payload = payload.decode("utf-8")
    if isinstance(payload, str):
        payload = json.loads(payload)
    return payload


def _download_image_attachment(
    *,
    url: str,
    output_dir: str | None,
    filename: str,
    headers: dict[str, str],
    verify_ssl: bool,
) -> str | None:
    if not output_dir:
        return None
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / filename
    request = Request(url, headers=headers)
    ssl_context = None if verify_ssl else ssl._create_unverified_context()
    with urlopen(request, context=ssl_context) as response:
        target_path.write_bytes(response.read())
    return str(target_path)


def _normalize_issue_payload(
    issue: dict,
    *,
    include_comments: bool,
    include_attachments: bool,
    include_image_metadata: bool,
    download_images: bool,
    image_download_dir: str | None,
    auth_headers: dict[str, str],
    verify_ssl: bool,
) -> dict:
    normalized_issue = dict(issue)
    fields = dict(normalized_issue.get("fields", {}))

    if not include_comments:
        fields["comment"] = {"comments": []}

    attachments = list(fields.get("attachment", [])) if include_attachments else []
    normalized_attachments = []
    for attachment in attachments:
        normalized_attachment = dict(attachment)
        mime_type = normalized_attachment.get("mimeType") or normalized_attachment.get("mime_type")
        if not include_image_metadata and mime_type and str(mime_type).lower().startswith("image/"):
            normalized_attachment.pop("ocr_text", None)
            normalized_attachment.pop("vision_caption", None)
            normalized_attachment.pop("alt_text", None)
        if download_images and mime_type and str(mime_type).lower().startswith("image/"):
            content_url = normalized_attachment.get("content") or normalized_attachment.get("downloadLink")
            filename = normalized_attachment.get("filename") or normalized_attachment.get("name") or "image"
            if content_url:
                normalized_attachment["local_path"] = _download_image_attachment(
                    url=content_url,
                    output_dir=image_download_dir,
                    filename=filename,
                    headers=auth_headers,
                    verify_ssl=verify_ssl,
                )
        normalized_attachments.append(normalized_attachment)
    fields["attachment"] = normalized_attachments
    normalized_issue["fields"] = fields
    return normalized_issue


def fetch_jira_server_sync_atlassian_api(
    *,
    base_url: str,
    username: str | None = None,
    password: str | None = None,
    token: str | None = None,
    auth_mode: str = "auto",
    jql: str | None = None,
    cursor: str | None = None,
    page_size: int = 50,
    verify_ssl: bool = True,
    issue_key: str | None = None,
    issue_keys: str | None = None,
    project_key: str | None = None,
    project_keys: str | None = None,
    issue_type: str | None = None,
    status: str | None = None,
    label: str | None = None,
    updated_from: str | None = None,
    updated_to: str | None = None,
    include_comments: bool = True,
    include_attachments: bool = True,
    include_image_metadata: bool = True,
    download_images: bool = False,
    image_download_dir: str | None = None,
) -> dict:
    client = _build_client(
        base_url=base_url,
        username=username,
        password=password,
        token=token,
        auth_mode=auth_mode,
        verify_ssl=verify_ssl,
    )
    auth_header = _build_auth_header(username=username, password=password, token=token, auth_mode=auth_mode)
    auth_headers = {"Authorization": auth_header} if auth_header else {}

    effective_jql = _build_jql(
        issue_key=issue_key,
        issue_keys=issue_keys,
        project_key=project_key,
        project_keys=project_keys,
        issue_type=issue_type,
        status=status,
        label=label,
        updated_from=updated_from,
        updated_to=updated_to,
        cursor=cursor,
        jql=jql,
    )

    issues: list[dict] = []
    field_name_map: dict[str, str] = {}
    start_at = 0
    total: int | None = None

    while total is None or start_at < total:
        payload = _jira_get(
            client,
            "rest/api/2/search",
            params={
                "jql": effective_jql,
                "startAt": start_at,
                "maxResults": page_size,
                "fields": "*all",
                "expand": "names",
            },
        )
        batch = payload.get("issues", [])
        field_name_map.update(payload.get("names", {}))
        total = payload.get("total", len(batch))
        if not batch:
            break

        for issue in batch:
            issues.append(
                _normalize_issue_payload(
                    issue,
                    include_comments=include_comments,
                    include_attachments=include_attachments,
                    include_image_metadata=include_image_metadata,
                    download_images=download_images,
                    image_download_dir=image_download_dir,
                    auth_headers=auth_headers,
                    verify_ssl=verify_ssl,
                )
            )
        start_at += len(batch)

    return {
        "sync_type": "incremental" if cursor or updated_from or updated_to else "full",
        "cursor": cursor,
        "names": field_name_map,
        "issues": issues,
        "selector_summary": {
            "fetch_backend": "atlassian-api",
            "jql": effective_jql,
            "issue_key": issue_key,
            "issue_keys": _parse_csv_values(issue_keys),
            "project_key": project_key,
            "project_keys": _parse_csv_values(project_keys),
            "issue_type": issue_type,
            "status": status,
            "label": label,
            "updated_from": updated_from or cursor,
            "updated_to": updated_to,
            "include_comments": include_comments,
            "include_attachments": include_attachments,
            "include_image_metadata": include_image_metadata,
            "download_images": download_images,
        },
    }

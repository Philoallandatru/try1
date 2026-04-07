from __future__ import annotations

from base64 import b64encode
from html import unescape
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import json
import re
import ssl

from services.ingest.normalizer import normalize_markdown_text


TAG_PATTERN = re.compile(r"<[^>]+>")


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


def _strip_tags(text: str) -> str:
    return unescape(TAG_PATTERN.sub("", text)).strip()


def _storage_html_to_markdown(storage_value: str) -> str:
    markdown = storage_value
    markdown = re.sub(
        r"<h([1-6])[^>]*>(.*?)</h\1>",
        lambda match: f"\n{'#' * int(match.group(1))} {_strip_tags(match.group(2))}\n",
        markdown,
        flags=re.IGNORECASE | re.DOTALL,
    )
    markdown = re.sub(
        r"<li[^>]*>(.*?)</li>",
        lambda match: f"\n- {_strip_tags(match.group(1))}",
        markdown,
        flags=re.IGNORECASE | re.DOTALL,
    )
    markdown = re.sub(
        r"<p[^>]*>(.*?)</p>",
        lambda match: f"\n{_strip_tags(match.group(1))}\n",
        markdown,
        flags=re.IGNORECASE | re.DOTALL,
    )
    markdown = re.sub(r"<br\s*/?>", "\n", markdown, flags=re.IGNORECASE)
    markdown = _strip_tags(markdown)
    markdown = re.sub(r"\n{3,}", "\n\n", markdown)
    return markdown.strip()


def _attachment_to_markdown(attachment: dict) -> str:
    title = attachment.get("title") or attachment.get("name") or "attachment"
    media_type = attachment.get("metadata", {}).get("mediaType") or attachment.get("media_type") or "application/octet-stream"
    download = attachment.get("_links", {}).get("download")
    if download:
        return f"- [{title}]({download}) ({media_type})"
    return f"- {title} ({media_type})"


def _normalize_attachment_list(page: dict) -> list[dict]:
    attachments = page.get("attachments")
    if attachments is not None:
        return attachments
    results = page.get("children", {}).get("attachment", {}).get("results", [])
    normalized = []
    for item in results:
        normalized.append(
            {
                "name": item.get("title"),
                "media_type": item.get("metadata", {}).get("mediaType"),
                "_links": item.get("_links", {}),
                "metadata": item.get("metadata", {}),
            }
        )
    return normalized


def _page_to_markdown(page: dict) -> str:
    body = page.get("body", {}).get("storage", {}).get("value", "")
    content = _storage_html_to_markdown(body) or "No body."
    lines = [f"# {page.get('title', 'Untitled Confluence Page')}", "", content]
    attachments = page.get("attachments", [])
    if attachments:
        lines.extend(["", "## Attachments"])
        lines.extend(_attachment_to_markdown(attachment) for attachment in attachments)
    return "\n".join(lines)


def _page_to_document(page: dict, *, source_uri: str, incremental: bool, acl_policy: str) -> dict:
    attachments = _normalize_attachment_list(page)
    space_value = page.get("space", {})
    space_key = space_value.get("key") if isinstance(space_value, dict) else space_value
    version_payload = page.get("version", {})
    version_value = page.get("version") or "fixture"
    ingested_at = "fixture"
    if isinstance(version_payload, dict):
        version_value = str(version_payload.get("number") or version_value)
        ingested_at = version_payload.get("when") or ingested_at
    else:
        version_value = str(version_value)
    markdown = _page_to_markdown({**page, "attachments": attachments})

    document = normalize_markdown_text(
        markdown,
        document_id=page["id"],
        source_type="confluence",
        authority_level="supporting",
        version=version_value,
        language="en",
        title=page.get("title", page["id"]),
        source_uri=source_uri,
        ingested_at=ingested_at,
        parser="confluence-markdown-normalizer",
        acl_policy=acl_policy,
        extra_provenance={"space": space_key},
    )
    document["markdown"] = markdown
    document["attachments"] = attachments
    document["metadata"] = {
        "space": space_key,
        "incremental": incremental,
        "attachment_count": len(attachments),
    }
    return document


def load_confluence_sync(path: str | Path) -> dict:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    documents = [
        _page_to_document(
            page,
            source_uri=str(path).replace("\\", "/"),
            incremental=payload["sync_type"] == "incremental",
            acl_policy="team:ssd",
        )
        for page in payload["pages"]
    ]
    return {
        "sync_type": payload["sync_type"],
        "cursor": payload["cursor"],
        "documents": documents,
    }


def fetch_confluence_page_sync(
    *,
    base_url: str,
    username: str | None = None,
    password: str | None = None,
    token: str | None = None,
    auth_mode: str = "auto",
    cql: str | None = None,
    space_key: str | None = None,
    cursor: str | None = None,
    page_size: int = 25,
    verify_ssl: bool = True,
    acl_policy: str = "team:ssd",
) -> dict:
    normalized_base_url = base_url.rstrip("/")
    headers = {"Accept": "application/json"}
    auth_header = _build_auth_header(username=username, password=password, token=token, auth_mode=auth_mode)
    if auth_header:
        headers["Authorization"] = auth_header

    effective_cql = cql
    if not effective_cql and space_key:
        effective_cql = f'space="{space_key}"'
    if cursor:
        updated_clause = f'lastmodified >= "{cursor}"'
        effective_cql = f"({effective_cql}) AND {updated_clause}" if effective_cql else updated_clause

    documents = []
    start = 0
    size = None
    while size is None or size == page_size:
        params = {
            "type": "page",
            "start": start,
            "limit": page_size,
            "expand": "body.storage,version,space,children.attachment",
        }
        if effective_cql:
            params["cql"] = effective_cql

        payload = _request_json(
            f"{normalized_base_url}/rest/api/content?{urlencode(params)}",
            headers=headers,
            verify_ssl=verify_ssl,
        )
        pages = payload.get("results", [])
        size = len(pages)
        if not pages:
            break

        for page in pages:
            webui_path = page.get("_links", {}).get("webui")
            source_uri = f"{normalized_base_url}{webui_path}" if webui_path else f"{normalized_base_url}/pages/viewpage.action?pageId={page['id']}"
            documents.append(
                _page_to_document(
                    page,
                    source_uri=source_uri,
                    incremental=cursor is not None,
                    acl_policy=acl_policy,
                )
            )
        start += size

    next_cursor = cursor
    if documents:
        next_cursor = max(document["version"] for document in documents)

    return {
        "sync_type": "incremental" if cursor else "full",
        "cursor": next_cursor,
        "documents": documents,
    }

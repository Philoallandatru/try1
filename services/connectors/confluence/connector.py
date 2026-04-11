from __future__ import annotations

from base64 import b64encode
from html import unescape
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import json
import re
import ssl

from services.ingest.normalizer import append_content_block, append_section, build_base_document, finalize_document
from services.connectors.confluence.atlassian_api_fetch import fetch_confluence_page_sync_atlassian_api
from services.ingest.visual_assets import (
    append_visual_asset_to_document,
    build_visual_asset_markdown,
    image_asset_from_attachment,
    is_image_media_type,
)


TAG_PATTERN = re.compile(r"<[^>]+>")
CONFLUENCE_IMAGE_PATTERN = re.compile(r"<ac:image\b[^>]*>.*?</ac:image>", re.IGNORECASE | re.DOTALL)
CONFLUENCE_FILENAME_PATTERN = re.compile(r'ri:filename="(?P<filename>[^"]+)"', re.IGNORECASE)
CONFLUENCE_HEADING_PATTERN = re.compile(r"<h([1-6])[^>]*>(.*?)</h\1>", re.IGNORECASE | re.DOTALL)
CONFLUENCE_LIST_ITEM_PATTERN = re.compile(r"<li[^>]*>(.*?)</li>", re.IGNORECASE | re.DOTALL)
CONFLUENCE_PARAGRAPH_PATTERN = re.compile(r"<p[^>]*>(.*?)</p>", re.IGNORECASE | re.DOTALL)
CONFLUENCE_TABLE_PATTERN = re.compile(r"<table[^>]*>(.*?)</table>", re.IGNORECASE | re.DOTALL)
CONFLUENCE_TABLE_ROW_PATTERN = re.compile(r"<tr[^>]*>(.*?)</tr>", re.IGNORECASE | re.DOTALL)
CONFLUENCE_TABLE_CELL_PATTERN = re.compile(r"<t[dh][^>]*>(.*?)</t[dh]>", re.IGNORECASE | re.DOTALL)
CONFLUENCE_BLOCK_PATTERN = re.compile(
    r"(?P<heading><h(?P<heading_level>[1-6])[^>]*>(?P<heading_body>.*?)</h(?P=heading_level)>)|"
    r"(?P<paragraph><p[^>]*>(?P<paragraph_body>.*?)</p>)|"
    r"(?P<list_item><li[^>]*>(?P<list_item_body>.*?)</li>)|"
    r"(?P<table><table[^>]*>(?P<table_body>.*?)</table>)",
    re.IGNORECASE | re.DOTALL,
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


def _strip_tags(text: str) -> str:
    return unescape(TAG_PATTERN.sub("", text)).strip()


def _attachment_name(attachment: dict) -> str:
    return attachment.get("title") or attachment.get("name") or attachment.get("filename") or "attachment"


def _storage_html_to_markdown(
    storage_value: str,
    *,
    document_id: str | None = None,
    source_uri: str | None = None,
    attachments: list[dict] | None = None,
) -> str:
    markdown = storage_value
    attachment_map = {_attachment_name(attachment): attachment for attachment in attachments or []}

    def replace_image(match: re.Match[str]) -> str:
        if not document_id or not source_uri:
            return ""
        filename_match = CONFLUENCE_FILENAME_PATTERN.search(match.group(0))
        if not filename_match:
            return ""
        filename = filename_match.group("filename")
        attachment = attachment_map.get(filename, {"name": filename, "media_type": "image/unknown"})
        media_type = attachment.get("media_type") or attachment.get("metadata", {}).get("mediaType")
        if media_type and not is_image_media_type(media_type):
            return ""
        asset = image_asset_from_attachment(
            attachment,
            source_type="confluence",
            document_id=document_id,
            source_uri=source_uri,
            section="Inline Image",
        )
        return f"\n{build_visual_asset_markdown(asset)}\n"

    markdown = CONFLUENCE_IMAGE_PATTERN.sub(replace_image, markdown)
    markdown = CONFLUENCE_TABLE_PATTERN.sub(lambda match: "\n" + _table_html_to_markdown(match.group(1)) + "\n", markdown)
    markdown = CONFLUENCE_HEADING_PATTERN.sub(
        lambda match: f"\n{'#' * int(match.group(1))} {_strip_tags(match.group(2))}\n",
        markdown,
    )
    markdown = CONFLUENCE_LIST_ITEM_PATTERN.sub(
        lambda match: f"\n- {_strip_tags(match.group(1))}",
        markdown,
    )
    markdown = CONFLUENCE_PARAGRAPH_PATTERN.sub(
        lambda match: f"\n{_strip_tags(match.group(1))}\n",
        markdown,
    )
    markdown = re.sub(r"<br\s*/?>", "\n", markdown, flags=re.IGNORECASE)
    markdown = _strip_tags(markdown)
    markdown = re.sub(r"\n{3,}", "\n\n", markdown)
    return markdown.strip()


def _table_html_to_rows(table_html: str) -> list[list[str]]:
    rows = []
    for row_match in CONFLUENCE_TABLE_ROW_PATTERN.finditer(table_html):
        cells = [_strip_tags(cell_match.group(1)) for cell_match in CONFLUENCE_TABLE_CELL_PATTERN.finditer(row_match.group(1))]
        cells = [cell for cell in cells if cell]
        if cells:
            rows.append(cells)
    return rows


def _table_html_to_markdown(table_html: str) -> str:
    rows = _table_html_to_rows(table_html)
    if not rows:
        return ""
    header = rows[0]
    body = rows[1:]
    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join("---" for _ in header) + " |",
    ]
    for row in body:
        padded = row + [""] * (len(header) - len(row))
        lines.append("| " + " | ".join(padded[: len(header)]) + " |")
    return "\n".join(lines)


def _storage_html_to_blocks(
    storage_value: str,
    *,
    document_id: str | None = None,
    source_uri: str | None = None,
    attachments: list[dict] | None = None,
) -> tuple[list[dict], list[dict], list[dict]]:
    normalized_html = storage_value
    attachment_map = {_attachment_name(attachment): attachment for attachment in attachments or []}
    sections: list[dict] = []
    blocks: list[dict] = []
    tables: list[dict] = []
    current_heading: str | None = None

    def replace_image(match: re.Match[str]) -> str:
        if not document_id or not source_uri:
            return ""
        filename_match = CONFLUENCE_FILENAME_PATTERN.search(match.group(0))
        if not filename_match:
            return ""
        filename = filename_match.group("filename")
        attachment = attachment_map.get(filename, {"name": filename, "media_type": "image/unknown"})
        media_type = attachment.get("media_type") or attachment.get("metadata", {}).get("mediaType")
        if media_type and not is_image_media_type(media_type):
            return ""
        asset = image_asset_from_attachment(
            attachment,
            source_type="confluence",
            document_id=document_id,
            source_uri=source_uri,
            section="Inline Image",
        )
        return f"\n{build_visual_asset_markdown(asset)}\n"

    normalized_html = CONFLUENCE_IMAGE_PATTERN.sub(replace_image, normalized_html)
    table_index = 0
    for match in CONFLUENCE_BLOCK_PATTERN.finditer(normalized_html):
        if match.group("heading"):
            heading = _strip_tags(match.group("heading_body"))
            if not heading:
                continue
            current_heading = heading
            sections.append({"heading": heading, "level": int(match.group("heading_level"))})
            continue

        if match.group("paragraph"):
            block = _strip_tags(match.group("paragraph_body"))
            if block:
                blocks.append({"text": block, "section_heading": current_heading})
            continue

        if match.group("list_item"):
            block = _strip_tags(match.group("list_item_body"))
            if block:
                blocks.append({"text": block, "section_heading": current_heading})
            continue

        if match.group("table"):
            markdown_table = _table_html_to_markdown(match.group("table_body"))
            if not markdown_table:
                continue
            table_index += 1
            table = {
                "id": f"table-{table_index}",
                "title": f"HTML Table {table_index}",
                "section_heading": current_heading,
                "rows": _table_html_to_rows(match.group("table_body")),
                "markdown": markdown_table,
            }
            tables.append(table)
            blocks.append({"text": table["markdown"], "section_heading": current_heading, "block_type": "table"})

    return sections, blocks, tables


def _attachment_to_markdown(
    attachment: dict,
    *,
    document_id: str | None = None,
    source_uri: str | None = None,
    section: str | None = None,
) -> str:
    title = attachment.get("title") or attachment.get("name") or "attachment"
    media_type = attachment.get("metadata", {}).get("mediaType") or attachment.get("media_type") or "application/octet-stream"
    download = attachment.get("_links", {}).get("download")
    if document_id and source_uri and is_image_media_type(media_type):
        asset = image_asset_from_attachment(
            attachment,
            source_type="confluence",
            document_id=document_id,
            source_uri=source_uri,
            section=section or "Attachments",
        )
        return build_visual_asset_markdown(asset)
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


def _page_sync_cursor(page: dict, fallback: str = "fixture") -> str:
    version_payload = page.get("version", {})
    if isinstance(version_payload, dict):
        for key in ("when", "createdAt"):
            value = version_payload.get(key)
            if value:
                return str(value)
    for key in ("lastmodified", "lastModified", "updated", "updated_at"):
        value = page.get(key)
        if value:
            return str(value)
    return fallback


def _page_to_markdown(page: dict) -> str:
    body = page.get("body", {}).get("storage", {}).get("value", "")
    content = _storage_html_to_markdown(
        body,
        document_id=page.get("id"),
        source_uri=page.get("source_uri"),
        attachments=page.get("attachments", []),
    ) or "No body."
    lines = [f"# {page.get('title', 'Untitled Confluence Page')}", "", content]
    attachments = page.get("attachments", [])
    if attachments:
        non_inline_attachments = [
            attachment
            for attachment in attachments
            if _attachment_name(attachment) not in content
        ]
        if non_inline_attachments:
            lines.extend(["", "## Attachments"])
            lines.extend(
                _attachment_to_markdown(
                    attachment,
                    document_id=page.get("id"),
                    source_uri=page.get("source_uri"),
                    section="Attachments",
                )
                for attachment in non_inline_attachments
            )
    return "\n".join(lines)


def _page_to_document(page: dict, *, source_uri: str, incremental: bool, acl_policy: str) -> dict:
    attachments = _normalize_attachment_list(page)
    space_value = page.get("space", {})
    space_key = space_value.get("key") if isinstance(space_value, dict) else space_value
    version_payload = page.get("version", {})
    version_value = page.get("version") or "fixture"
    ingested_at = _page_sync_cursor(page)
    if isinstance(version_payload, dict):
        version_value = str(version_payload.get("number") or version_value)
    else:
        version_value = str(version_value)
    storage_value = page.get("body", {}).get("storage", {}).get("value", "")
    markdown = _page_to_markdown({**page, "attachments": attachments, "source_uri": source_uri})
    sections, blocks, tables = _storage_html_to_blocks(
        storage_value,
        document_id=page["id"],
        source_uri=source_uri,
        attachments=attachments,
    )

    document = build_base_document(
        document_id=page["id"],
        source_type="confluence",
        authority_level="supporting",
        version=version_value,
        language="en",
        title=page.get("title", page["id"]),
        source_uri=source_uri,
        ingested_at=ingested_at,
        parser="confluence-payload-normalizer",
        acl_policy=acl_policy,
        extra_provenance={"space": space_key},
    )
    for section in sections:
        append_section(document, section["heading"], level=section["level"])
    for block in blocks:
        append_content_block(document, block["text"], section_heading=block.get("section_heading"))
    for table in tables:
        document["structure"]["tables"].append(
            {
                "id": table["id"],
                "title": table["title"],
                "section_heading": table.get("section_heading"),
                "rows": table["rows"],
            }
        )
    if attachments:
        append_section(document, "Attachments")
    document["markdown"] = markdown
    document["attachments"] = attachments
    document["visual_assets"] = []
    document["metadata"] = {
        "space": space_key,
        "incremental": incremental,
        "attachment_count": len(attachments),
        "visual_asset_count": 0,
        "sync_cursor": ingested_at,
    }
    for attachment in attachments:
        media_type = attachment.get("media_type") or attachment.get("metadata", {}).get("mediaType")
        if not is_image_media_type(media_type):
            attachment_markdown = _attachment_to_markdown(attachment)
            if attachment_markdown:
                append_content_block(document, attachment_markdown, section_heading="Attachments")
            continue
        if _attachment_name(attachment) not in markdown:
            continue
        asset = image_asset_from_attachment(
            attachment,
            source_type="confluence",
            document_id=page["id"],
            source_uri=source_uri,
            section="Inline Image" if "### Image" in markdown else "Attachments",
        )
        append_visual_asset_to_document(document, asset)
    document = finalize_document(document)
    document["title"] = page.get("title", page["id"])
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
    fetch_backend: str = "native",
    page_id: str | None = None,
    page_ids: str | None = None,
    title: str | None = None,
    label: str | None = None,
    ancestor_id: str | None = None,
    modified_from: str | None = None,
    modified_to: str | None = None,
    include_attachments: bool = True,
    include_image_metadata: bool = True,
    download_images: bool = False,
    image_download_dir: str | None = None,
) -> dict:
    if fetch_backend == "atlassian-api":
        payload = fetch_confluence_page_sync_atlassian_api(
            base_url=base_url,
            username=username,
            password=password,
            token=token,
            auth_mode=auth_mode,
            cql=cql,
            space_key=space_key,
            cursor=cursor,
            page_size=page_size,
            verify_ssl=verify_ssl,
            page_id=page_id,
            page_ids=page_ids,
            title=title,
            label=label,
            ancestor_id=ancestor_id,
            modified_from=modified_from,
            modified_to=modified_to,
            include_attachments=include_attachments,
            include_image_metadata=include_image_metadata,
            download_images=download_images,
            image_download_dir=image_download_dir,
        )
        documents = [
            _page_to_document(
                page,
                source_uri=(
                    page.get("_links", {}).get("webui")
                    if str(page.get("_links", {}).get("webui", "")).startswith("http")
                    else f"{base_url.rstrip('/')}{page.get('_links', {}).get('webui', f'/pages/viewpage.action?pageId={page['id']}')}"
                ),
                incremental=bool(payload.get("cursor") or modified_from or modified_to),
                acl_policy=acl_policy,
            )
            for page in payload.get("pages", [])
        ]
        next_cursor = cursor
        if documents:
            next_cursor = max(document["metadata"]["sync_cursor"] for document in documents)
        return {
            "sync_type": payload.get("sync_type", "incremental" if cursor else "full"),
            "cursor": next_cursor,
            "documents": documents,
            "selector_summary": payload.get("selector_summary", {}),
        }

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
        next_cursor = max(document["metadata"]["sync_cursor"] for document in documents)

    return {
        "sync_type": "incremental" if cursor else "full",
        "cursor": next_cursor,
        "documents": documents,
    }

from __future__ import annotations

from base64 import b64encode
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import Request, urlopen
import json
import ssl


def _import_confluence_client():
    from atlassian import Confluence

    return Confluence


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


def _quote_cql_value(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _build_cql(
    *,
    page_id: str | None = None,
    page_ids: str | None = None,
    space_key: str | None = None,
    title: str | None = None,
    label: str | None = None,
    ancestor_id: str | None = None,
    modified_from: str | None = None,
    modified_to: str | None = None,
    cursor: str | None = None,
    cql: str | None = None,
) -> str | None:
    if cql:
        return cql

    clauses: list[str] = []
    exact_page_ids = []
    if page_id:
        exact_page_ids.append(page_id.strip())
    exact_page_ids.extend(_parse_csv_values(page_ids))
    if exact_page_ids:
        if len(exact_page_ids) == 1:
            clauses.append(f"id = {_quote_cql_value(exact_page_ids[0])}")
        else:
            joined = ", ".join(_quote_cql_value(item) for item in exact_page_ids)
            clauses.append(f"id in ({joined})")

    if space_key:
        clauses.append(f"space = {_quote_cql_value(space_key)}")
    if title:
        clauses.append(f"title = {_quote_cql_value(title)}")
    if label:
        clauses.append(f"label = {_quote_cql_value(label)}")
    if ancestor_id:
        clauses.append(f"ancestor = {_quote_cql_value(ancestor_id)}")

    effective_modified_from = modified_from or cursor
    if effective_modified_from:
        clauses.append(f'lastmodified >= {_quote_cql_value(effective_modified_from)}')
    if modified_to:
        clauses.append(f'lastmodified <= {_quote_cql_value(modified_to)}')

    if not clauses:
        return None
    return " AND ".join(clauses)


def _build_client(
    *,
    base_url: str,
    username: str | None = None,
    password: str | None = None,
    token: str | None = None,
    auth_mode: str = "auto",
    verify_ssl: bool = True,
):
    Confluence = _import_confluence_client()
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
    return Confluence(**client_kwargs)


def _confluence_get(client, path: str, params: dict[str, object] | None = None) -> dict:
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


def _normalize_attachment(
    attachment: dict,
    *,
    base_url: str,
    include_image_metadata: bool,
    download_images: bool,
    image_download_dir: str | None,
    auth_headers: dict[str, str],
    verify_ssl: bool,
) -> dict:
    normalized = {
        "name": attachment.get("title") or attachment.get("name"),
        "title": attachment.get("title") or attachment.get("name"),
        "media_type": attachment.get("metadata", {}).get("mediaType") or attachment.get("media_type"),
        "metadata": attachment.get("metadata", {}),
        "_links": dict(attachment.get("_links", {})),
    }
    download_path = normalized["_links"].get("download")
    if download_path:
        normalized["_links"]["download"] = urljoin(base_url.rstrip("/") + "/", download_path.lstrip("/"))
    media_type = normalized.get("media_type")
    if not include_image_metadata and media_type and str(media_type).lower().startswith("image/"):
        normalized.pop("ocr_text", None)
        normalized.pop("vision_caption", None)
        normalized.pop("alt_text", None)
    if download_images and media_type and str(media_type).lower().startswith("image/") and normalized["_links"].get("download"):
        normalized["local_path"] = _download_image_attachment(
            url=normalized["_links"]["download"],
            output_dir=image_download_dir,
            filename=normalized.get("name") or "image",
            headers=auth_headers,
            verify_ssl=verify_ssl,
        )
    return normalized


def _load_page_attachments(
    client,
    *,
    page_id: str,
    base_url: str,
    include_image_metadata: bool,
    download_images: bool,
    image_download_dir: str | None,
    auth_headers: dict[str, str],
    verify_ssl: bool,
) -> list[dict]:
    payload = _confluence_get(
        client,
        f"rest/api/content/{page_id}/child/attachment",
        params={"limit": 1000},
    )
    attachments = []
    for attachment in payload.get("results", []):
        attachments.append(
            _normalize_attachment(
                attachment,
                base_url=base_url,
                include_image_metadata=include_image_metadata,
                download_images=download_images,
                image_download_dir=image_download_dir,
                auth_headers=auth_headers,
                verify_ssl=verify_ssl,
            )
        )
    return attachments


def _normalize_page(
    page: dict,
    *,
    client,
    base_url: str,
    include_attachments: bool,
    include_image_metadata: bool,
    download_images: bool,
    image_download_dir: str | None,
    auth_headers: dict[str, str],
    verify_ssl: bool,
) -> dict:
    normalized_page = dict(page)
    if include_attachments:
        normalized_page["attachments"] = _load_page_attachments(
            client,
            page_id=str(page["id"]),
            base_url=base_url,
            include_image_metadata=include_image_metadata,
            download_images=download_images,
            image_download_dir=image_download_dir,
            auth_headers=auth_headers,
            verify_ssl=verify_ssl,
        )
    else:
        normalized_page["attachments"] = []
    return normalized_page


def _fetch_page_by_id(client, page_id: str) -> dict:
    return _confluence_get(
        client,
        f"rest/api/content/{page_id}",
        params={"expand": "body.storage,version,space"},
    )


def fetch_confluence_page_sync_atlassian_api(
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

    effective_cql = _build_cql(
        page_id=page_id,
        page_ids=page_ids,
        space_key=space_key,
        title=title,
        label=label,
        ancestor_id=ancestor_id,
        modified_from=modified_from,
        modified_to=modified_to,
        cursor=cursor,
        cql=cql,
    )

    pages: list[dict] = []
    exact_page_ids = []
    if page_id:
        exact_page_ids.append(page_id)
    exact_page_ids.extend(_parse_csv_values(page_ids))

    if exact_page_ids:
        raw_pages = [_fetch_page_by_id(client, current_page_id) for current_page_id in exact_page_ids]
    else:
        raw_pages = []
        start = 0
        size = None
        while size is None or size == page_size:
            params = {
                "type": "page",
                "start": start,
                "limit": page_size,
                "expand": "body.storage,version,space",
            }
            if effective_cql:
                payload = _confluence_get(client, "rest/api/content/search", params={"cql": effective_cql, "start": start, "limit": page_size, "expand": "body.storage,version,space"})
            else:
                payload = _confluence_get(client, "rest/api/content", params=params)
            batch = payload.get("results", [])
            size = len(batch)
            if not batch:
                break
            raw_pages.extend(batch)
            start += size

    for page in raw_pages:
        pages.append(
            _normalize_page(
                page,
                client=client,
                base_url=base_url,
                include_attachments=include_attachments,
                include_image_metadata=include_image_metadata,
                download_images=download_images,
                image_download_dir=image_download_dir,
                auth_headers=auth_headers,
                verify_ssl=verify_ssl,
            )
        )

    return {
        "sync_type": "incremental" if cursor or modified_from or modified_to else "full",
        "cursor": cursor,
        "pages": pages,
        "selector_summary": {
            "fetch_backend": "atlassian-api",
            "cql": effective_cql,
            "page_id": page_id,
            "page_ids": _parse_csv_values(page_ids),
            "space_key": space_key,
            "title": title,
            "label": label,
            "ancestor_id": ancestor_id,
            "modified_from": modified_from or cursor,
            "modified_to": modified_to,
            "include_attachments": include_attachments,
            "include_image_metadata": include_image_metadata,
            "download_images": download_images,
        },
    }

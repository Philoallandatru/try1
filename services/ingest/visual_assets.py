from __future__ import annotations

from pathlib import Path
import re


IMAGE_MEDIA_PREFIX = "image/"
SLUG_PATTERN = re.compile(r"[^a-zA-Z0-9]+")


def is_image_media_type(media_type: str | None) -> bool:
    return bool(media_type and media_type.lower().startswith(IMAGE_MEDIA_PREFIX))


def _slug(value: str) -> str:
    normalized = SLUG_PATTERN.sub("-", value).strip("-").lower()
    return normalized or "image"


def image_asset_from_attachment(
    attachment: dict,
    *,
    source_type: str,
    document_id: str,
    source_uri: str,
    section: str | None = None,
    page: int | None = None,
) -> dict:
    filename = attachment.get("filename") or attachment.get("name") or attachment.get("title") or "image"
    media_type = (
        attachment.get("mimeType")
        or attachment.get("media_type")
        or attachment.get("metadata", {}).get("mediaType")
        or "image/unknown"
    )
    image_uri = (
        attachment.get("content")
        or attachment.get("downloadLink")
        or attachment.get("_links", {}).get("download")
        or attachment.get("local_path")
        or ""
    )
    return {
        "asset_id": f"{_slug(source_type)}-{_slug(document_id)}-{_slug(filename)}",
        "source_type": source_type,
        "document_id": document_id,
        "source_uri": source_uri,
        "image_uri": image_uri,
        "local_path": attachment.get("local_path"),
        "media_type": media_type,
        "filename": filename,
        "page": page,
        "section": section,
        "alt_text": attachment.get("alt_text") or attachment.get("alt"),
        "ocr_text": attachment.get("ocr_text") or attachment.get("ocr"),
        "vision_caption": attachment.get("vision_caption") or attachment.get("caption"),
        "provenance": {
            "extractor": attachment.get("extractor") or f"{source_type}-image-reference",
            "ocr_engine": attachment.get("ocr_engine") or "provided-metadata",
            "vision_model": attachment.get("vision_model") or "provided-metadata",
        },
    }


def image_asset_from_pdf_block(
    page_block: dict,
    *,
    document_id: str,
    source_uri: str,
    page: int,
) -> dict:
    image_path = page_block.get("img_path") or page_block.get("image_path") or page_block.get("path") or ""
    filename = Path(str(image_path)).name if image_path else page_block.get("filename", "pdf-image")
    return {
        "asset_id": f"pdf-{_slug(document_id)}-page-{page}-{_slug(str(filename))}",
        "source_type": "pdf",
        "document_id": document_id,
        "source_uri": source_uri,
        "image_uri": str(image_path),
        "local_path": str(image_path) if image_path else None,
        "media_type": page_block.get("media_type") or "image/unknown",
        "filename": filename,
        "page": page,
        "section": page_block.get("section"),
        "alt_text": page_block.get("alt_text") or page_block.get("alt"),
        "ocr_text": page_block.get("ocr_text") or page_block.get("ocr"),
        "vision_caption": page_block.get("vision_caption") or page_block.get("caption"),
        "provenance": {
            "extractor": page_block.get("extractor") or "pdf-image-block",
            "ocr_engine": page_block.get("ocr_engine") or "provided-metadata",
            "vision_model": page_block.get("vision_model") or "provided-metadata",
        },
    }


def build_visual_asset_markdown(asset: dict) -> str:
    filename = asset.get("filename") or "image"
    image_uri = asset.get("image_uri") or asset.get("local_path") or ""
    source_parts = [asset.get("source_type", "source"), asset.get("document_id", "document")]
    if asset.get("page"):
        source_parts.append(f"page {asset['page']}")
    if asset.get("section"):
        source_parts.append(str(asset["section"]))

    lines = [f"### Image: {filename}", ""]
    if image_uri:
        lines.extend([f"![{filename}]({image_uri})", ""])
    lines.extend(
        [
            f"Image Source: {' '.join(source_parts)}",
            f"Media Type: {asset.get('media_type') or 'unknown'}",
        ]
    )
    if asset.get("alt_text"):
        lines.extend(["", "Alt Text:", f"> {asset['alt_text']}"])
    if asset.get("ocr_text"):
        lines.extend(["", "OCR Text:", f"> {asset['ocr_text']}"])
    if asset.get("vision_caption"):
        lines.extend(["", "Visual Summary:", f"> {asset['vision_caption']}"])
    return "\n".join(lines)


def append_visual_asset_to_document(document: dict, asset: dict, markdown: str | None = None) -> None:
    visual_markdown = markdown or build_visual_asset_markdown(asset)
    document.setdefault("visual_assets", []).append(asset)
    document.setdefault("metadata", {})["visual_asset_count"] = len(document["visual_assets"])
    document.setdefault("content_blocks", []).append(
        {
            "id": f"block-{len(document.get('content_blocks', [])) + 1}",
            "text": visual_markdown,
            "block_type": "image",
            "asset_id": asset["asset_id"],
            "page": asset.get("page"),
            "section_heading": asset.get("section"),
        }
    )
    document.setdefault("structure", {}).setdefault("figures", []).append(
        {
            "id": asset["asset_id"],
            "title": asset.get("filename") or asset["asset_id"],
            "page": asset.get("page"),
            "section": asset.get("section"),
        }
    )

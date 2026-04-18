from __future__ import annotations

from collections import Counter
from typing import Iterable


def _asset_state(asset: dict) -> tuple[str, list[str], list[str]]:
    indexed_fields: list[str] = []
    gaps: list[str] = []

    if asset.get("ocr_text"):
        indexed_fields.append("ocr_text")
    else:
        gaps.append("missing_ocr")

    if asset.get("vision_caption"):
        indexed_fields.append("vision_caption")
    else:
        gaps.append("missing_caption")

    if asset.get("alt_text"):
        indexed_fields.append("alt_text")

    state = "indexed" if indexed_fields else "degraded"
    return state, indexed_fields, gaps


def build_image_evidence_summary(documents: Iterable[dict]) -> dict:
    assets: list[dict] = []
    source_counts: Counter[str] = Counter()
    indexed_count = 0
    degraded_count = 0

    for document in documents:
        document_id = document.get("document_id", "unknown")
        source_type = document.get("source_type", "unknown")
        for asset in document.get("visual_assets", []):
            state, indexed_fields, gaps = _asset_state(asset)
            if state == "indexed":
                indexed_count += 1
            else:
                degraded_count += 1
            source_counts[source_type] += 1
            assets.append(
                {
                    "asset_id": asset.get("asset_id"),
                    "document_id": asset.get("document_id") or document_id,
                    "source_type": asset.get("source_type") or source_type,
                    "filename": asset.get("filename"),
                    "page": asset.get("page"),
                    "section": asset.get("section"),
                    "media_type": asset.get("media_type"),
                    "image_uri": asset.get("image_uri"),
                    "local_path": asset.get("local_path"),
                    "ocr_status": "provided" if asset.get("ocr_text") else "missing",
                    "caption_status": "provided" if asset.get("vision_caption") else "missing",
                    "enrichment_state": state,
                    "indexed_text_fields": indexed_fields,
                    "gaps": gaps,
                    "provenance": asset.get("provenance", {}),
                }
            )

    return {
        "asset_count": len(assets),
        "indexed_asset_count": indexed_count,
        "degraded_asset_count": degraded_count,
        "source_breakdown": dict(sorted(source_counts.items())),
        "assets": assets,
    }


def format_image_evidence_summary(summary: dict) -> str:
    if summary.get("asset_count", 0) == 0:
        return "No image evidence found."

    lines = [
        (
            f"{summary['asset_count']} image asset(s); "
            f"{summary['indexed_asset_count']} indexed; "
            f"{summary['degraded_asset_count']} degraded."
        )
    ]
    for asset in summary.get("assets", []):
        gaps = ", ".join(asset.get("gaps", [])) or "none"
        fields = ", ".join(asset.get("indexed_text_fields", [])) or "none"
        lines.append(
            "- "
            f"{asset.get('document_id')} / {asset.get('filename') or asset.get('asset_id')} "
            f"({asset.get('asset_id')}): "
            f"state={asset.get('enrichment_state')}; indexed_fields={fields}; gaps={gaps}"
        )
    return "\n".join(lines)

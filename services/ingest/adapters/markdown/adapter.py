from __future__ import annotations

from pathlib import Path

from services.ingest.normalizer import normalize_markdown_file


def parse_markdown(path: str | Path) -> dict:
    return normalize_markdown_file(path)

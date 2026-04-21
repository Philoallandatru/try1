from __future__ import annotations

import importlib
from pathlib import Path
import json
import os
import re
import shutil
import subprocess
import tempfile

from pypdf import PdfReader

from services.ingest.normalizer import (
    append_caption_item,
    append_content_block,
    append_section,
    build_base_document,
    finalize_document,
    register_page,
)
from services.ingest.visual_assets import (
    append_visual_asset_to_document,
    build_visual_asset_markdown,
    image_asset_from_pdf_block,
)


SECTION_PATTERN = re.compile(r"^(?P<clause>\d+(?:\.\d+)*)\s+(?P<title>.+)$")
TABLE_PATTERN = re.compile(r"^Table\s+(?P<id>[A-Za-z0-9_.-]+)\s*:\s*(?P<title>.+)$", re.IGNORECASE)
FIGURE_PATTERN = re.compile(r"^Figure\s+(?P<id>[A-Za-z0-9_.-]+)\s*:\s*(?P<title>.+)$", re.IGNORECASE)
PAGE_PATTERN = re.compile(r"^Page\s+(?P<page>\d+)$", re.IGNORECASE)
MARKDOWN_HEADING_PATTERN = re.compile(r"^(?P<hashes>#{1,6})\s+(?P<title>.+)$")
MARKDOWN_TABLE_ROW_PATTERN = re.compile(r"^\|.+\|$")

# Patterns to detect table of contents pages
TOC_TITLE_PATTERNS = [
    re.compile(r"^Table\s+of\s+(Contents|Figures|Tables)", re.IGNORECASE),
    re.compile(r"^List\s+of\s+(Figures|Tables)", re.IGNORECASE),
    re.compile(r"^Contents$", re.IGNORECASE),
]


def _is_toc_page(page_blocks: list[str]) -> bool:
    """
    Detect if a page is a table of contents page based on heuristics.

    Returns True if:
    - Page contains TOC title patterns
    - Page has high density of page number references (e.g., "....... 42")
    """
    if not page_blocks:
        return False

    # Check first few blocks for TOC title
    for block in page_blocks[:5]:
        text = block.strip()
        for pattern in TOC_TITLE_PATTERNS:
            if pattern.match(text):
                return True

    # Check for high density of page number patterns (dots followed by numbers)
    page_ref_pattern = re.compile(r"\.{2,}\s*\d+")
    page_ref_count = sum(1 for block in page_blocks if page_ref_pattern.search(block))

    # If more than 30% of blocks contain page references, likely a TOC
    if len(page_blocks) > 0 and page_ref_count / len(page_blocks) > 0.3:
        return True

    return False


def _index_structural_text(payload: dict, text: str, page_number: int) -> None:
    section_match = SECTION_PATTERN.match(text)
    if section_match:
        append_section(
            payload,
            heading=section_match.group("title"),
            clause=section_match.group("clause"),
            page=page_number,
        )

    table_match = TABLE_PATTERN.match(text)
    if table_match:
        append_caption_item(
            payload,
            key="tables",
            item_id=f"table-{table_match.group('id')}",
            title=table_match.group("title"),
            page=page_number,
        )

    figure_match = FIGURE_PATTERN.match(text)
    if figure_match:
        append_caption_item(
            payload,
            key="figures",
            item_id=f"figure-{figure_match.group('id')}",
            title=figure_match.group("title"),
            page=page_number,
        )


def _mineru_parse_kwargs(output_dir: Path, source: Path, pdf_bytes: bytes) -> dict:
    return {
        "output_dir": str(output_dir),
        "pdf_file_names": [source.stem],
        "pdf_bytes_list": [pdf_bytes],
        "p_lang_list": ["en"],
        "backend": "pipeline",
        "parse_method": "auto",
        "formula_enable": True,
        "table_enable": True,
        "f_draw_layout_bbox": False,
        "f_draw_span_bbox": False,
        "f_dump_md": True,
        "f_dump_middle_json": True,
        "f_dump_model_output": False,
        "f_dump_orig_pdf": False,
        "f_dump_content_list": False,
    }


def _fallback_to_pypdf(path: str | Path, exc: Exception) -> dict:
    payload = _extract_pdf_structure_pypdf(path)
    payload["provenance"]["parser"] = "pypdf-fallback"
    payload["provenance"]["parser_fallback_reason"] = str(exc)
    return payload


def _try_mineru_runner(label: str, runner, *args: object) -> tuple[dict | None, str | None]:
    try:
        return runner(*args), None
    except Exception as exc:
        return None, f"{label} failed: {exc}"


def _extract_pdf_structure_pypdf(path: str | Path) -> dict:
    source = Path(path)
    payload = build_base_document(
        document_id=source.stem,
        source_type="pdf",
        authority_level="canonical",
        version="fixture",
        language="en",
        title=source.stem,
        source_uri=str(source).replace("\\", "/"),
        ingested_at="fixture",
        parser="pypdf",
    )
    reader = PdfReader(str(source))
    logical_pages_seen: set[int] = set()

    for physical_page_number, page in enumerate(reader.pages, start=1):
        current_page = physical_page_number
        page_registered = False
        raw_text = page.extract_text() or ""
        lines = [line.strip() for line in raw_text.splitlines()]
        lines = [line for line in lines if line]

        for line in lines:
            page_match = PAGE_PATTERN.match(line)
            if page_match:
                current_page = int(page_match.group("page"))
                register_page(payload, current_page, logical_pages_seen)
                page_registered = True
                continue

            if not page_registered and current_page not in logical_pages_seen:
                register_page(payload, current_page, logical_pages_seen)
                page_registered = True

            _index_structural_text(payload, line, current_page)
            append_content_block(payload, line, page=current_page)

    return finalize_document(payload)


def _parse_mineru_markdown(source: Path, markdown_text: str, parser_name: str) -> dict:
    payload = build_base_document(
        document_id=source.stem,
        source_type="pdf",
        authority_level="canonical",
        version="fixture",
        language="en",
        title=source.stem,
        source_uri=str(source).replace("\\", "/"),
        ingested_at="fixture",
        parser=parser_name,
    )
    current_page = 1
    page_registered = False
    last_heading_clause = 0
    lines = [line.rstrip() for line in markdown_text.splitlines()]

    # Collect lines per page for TOC detection
    page_lines_buffer = []
    skip_current_page = False

    for idx, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if not line:
            continue

        # Check if this line indicates a new page (heuristic: page break patterns)
        # For now, we'll check TOC patterns on first few lines of each page
        if not page_registered:
            page_lines_buffer.append(line)

            # Check first 10 lines for TOC patterns
            if len(page_lines_buffer) <= 10:
                if _is_toc_page(page_lines_buffer):
                    skip_current_page = True

            if not skip_current_page:
                register_page(payload, current_page)
            page_registered = True

        if skip_current_page:
            # Skip content until we detect a new page (simplified: skip for now)
            continue

        heading_match = MARKDOWN_HEADING_PATTERN.match(line)
        if heading_match:
            title = heading_match.group("title").strip()
            explicit_clause = SECTION_PATTERN.match(title)
            if explicit_clause:
                clause = explicit_clause.group("clause")
                heading = explicit_clause.group("title")
            else:
                last_heading_clause += 1
                clause = str(last_heading_clause)
                heading = title
            append_section(
                payload,
                heading=heading,
                clause=clause,
                page=current_page,
            )

        table_match = TABLE_PATTERN.match(line)
        if table_match:
            append_caption_item(
                payload,
                key="tables",
                item_id=f"table-{table_match.group('id')}",
                title=table_match.group("title"),
                page=current_page,
            )
        elif MARKDOWN_TABLE_ROW_PATTERN.match(line):
            table_index = len(payload["structure"]["tables"]) + 1
            append_caption_item(
                payload,
                key="tables",
                item_id=f"table-{table_index}",
                title=f"Markdown Table {table_index}",
                page=current_page,
            )

        figure_match = FIGURE_PATTERN.match(line)
        if figure_match:
            append_caption_item(
                payload,
                key="figures",
                item_id=f"figure-{figure_match.group('id')}",
                title=figure_match.group("title"),
                page=current_page,
            )

        append_content_block(payload, line, page=current_page)

    return finalize_document(payload)


def _collect_mineru_span_text(block: dict) -> str:
    lines = block.get("lines", [])
    line_texts: list[str] = []
    for line in lines:
        spans = line.get("spans", [])
        span_texts = []
        for span in spans:
            content = span.get("content")
            if isinstance(content, str) and content.strip():
                span_texts.append(content.strip())
        if span_texts:
            line_texts.append(" ".join(span_texts))
    return "\n".join(line_texts).strip()


def _parse_mineru_middle_json(source: Path, middle_json: dict, parser_name: str) -> dict:
    payload = build_base_document(
        document_id=source.stem,
        source_type="pdf",
        authority_level="canonical",
        version="fixture",
        language="en",
        title=source.stem,
        source_uri=str(source).replace("\\", "/"),
        ingested_at="fixture",
        parser=parser_name,
    )
    pdf_info = middle_json.get("pdf_info", [])
    payload["visual_assets"] = []
    payload["metadata"] = {"visual_asset_count": 0}

    for fallback_page_number, page in enumerate(pdf_info, start=1):
        page_number = int(page.get("page_idx", fallback_page_number - 1)) + 1
        page_blocks = page.get("para_blocks", []) or page.get("preproc_blocks", [])

        # Collect all text blocks for TOC detection
        page_text_blocks = []
        for page_block in page_blocks:
            text = _collect_mineru_span_text(page_block)
            if text:
                normalized_lines = [line.strip() for line in text.splitlines() if line.strip()]
                normalized_text = " ".join(normalized_lines)
                if normalized_text:
                    page_text_blocks.append(normalized_text)

        # Skip table of contents pages
        if _is_toc_page(page_text_blocks):
            continue

        register_page(payload, page_number)

        for page_block in page_blocks:
            block_type = page_block.get("type", "")
            if block_type in {"image", "figure"}:
                asset = image_asset_from_pdf_block(
                    page_block,
                    document_id=source.stem,
                    source_uri=str(source).replace("\\", "/"),
                    page=page_number,
                )
                append_visual_asset_to_document(
                    payload,
                    asset,
                    build_visual_asset_markdown(asset),
                )
                continue

            text = _collect_mineru_span_text(page_block)
            if not text:
                continue

            block_level = page_block.get("level")
            normalized_lines = [line.strip() for line in text.splitlines() if line.strip()]
            normalized_text = " ".join(normalized_lines)
            if not normalized_text:
                continue

            if block_type == "title" and not SECTION_PATTERN.match(normalized_text):
                append_section(
                    payload,
                    heading=normalized_text,
                    clause=str(len(payload["structure"]["sections"]) + 1),
                    page=page_number,
                    level=block_level,
                )
            else:
                _index_structural_text(payload, normalized_text, page_number)

            append_content_block(
                payload,
                normalized_text,
                page=page_number,
                block_type=block_type,
            )

    return finalize_document(payload)


def _read_mineru_output(source: Path, output_dir: Path, parser_name: str = "mineru") -> dict:
    candidate_dirs = list(output_dir.rglob("txt")) + list(output_dir.rglob("auto"))
    for candidate_dir in candidate_dirs:
        middle_json_path = candidate_dir / f"{source.stem}_middle.json"
        if middle_json_path.exists():
            middle_json = json.loads(middle_json_path.read_text(encoding="utf-8"))
            if middle_json.get("pdf_info"):
                return _parse_mineru_middle_json(source, middle_json, parser_name)

        markdown_path = candidate_dir / f"{source.stem}.md"
        if markdown_path.exists():
            return _parse_mineru_markdown(
                source,
                markdown_path.read_text(encoding="utf-8"),
                parser_name,
            )

    raise RuntimeError("MinerU output did not contain an expected markdown or middle-json artifact.")


def _extract_pdf_structure_mineru_in_process(path: str | Path) -> dict:
    source = Path(path)
    try:
        mineru_common = importlib.import_module("mineru.cli.common")
    except Exception as exc:
        raise RuntimeError("MinerU Python package is not available in the active interpreter.") from exc

    do_parse = getattr(mineru_common, "do_parse", None)
    read_fn = getattr(mineru_common, "read_fn", None)
    if do_parse is None or read_fn is None:
        raise RuntimeError("MinerU Python package does not expose the expected parsing entrypoints.")

    with tempfile.TemporaryDirectory(prefix="mineru-parse-") as temp_dir:
        output_dir = Path(temp_dir)
        pdf_bytes = read_fn(source, "pdf")
        do_parse(**_mineru_parse_kwargs(output_dir, source, pdf_bytes))
        return _read_mineru_output(source, output_dir)


def _extract_pdf_structure_mineru_via_python(path: str | Path, python_executable: str | Path) -> dict:
    source = Path(path)
    python_path = Path(python_executable)
    if not python_path.exists():
        raise RuntimeError(f"Configured MINERU_PYTHON_EXE does not exist: {python_path}")

    script = """
from pathlib import Path
import sys
from mineru.cli.common import do_parse, read_fn

source = Path(sys.argv[1])
output_dir = Path(sys.argv[2])
pdf_bytes = read_fn(source, "pdf")
do_parse(**{
    "output_dir": str(output_dir),
    "pdf_file_names": [source.stem],
    "pdf_bytes_list": [pdf_bytes],
    "p_lang_list": ["en"],
    "backend": "pipeline",
    "parse_method": "auto",
    "formula_enable": True,
    "table_enable": True,
    "f_draw_layout_bbox": False,
    "f_draw_span_bbox": False,
    "f_dump_md": True,
    "f_dump_middle_json": True,
    "f_dump_model_output": False,
    "f_dump_orig_pdf": False,
    "f_dump_content_list": False,
})
"""

    with tempfile.TemporaryDirectory(prefix="mineru-parse-") as temp_dir:
        output_dir = Path(temp_dir)
        result = subprocess.run(
            [str(python_path), "-c", script, str(source), str(output_dir)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        if result.returncode != 0:
            stderr = (result.stderr or result.stdout).strip()
            raise RuntimeError(stderr or "MinerU direct Python parsing failed.")
        return _read_mineru_output(source, output_dir)


def _extract_pdf_structure_mineru_cli(path: str | Path) -> dict:
    source = Path(path)
    mineru_executable = shutil.which("mineru")
    if not mineru_executable:
        raise RuntimeError("MinerU CLI is not installed.")

    with tempfile.TemporaryDirectory(prefix="mineru-parse-") as temp_dir:
        output_dir = Path(temp_dir)
        command = [
            mineru_executable,
            "-p",
            str(source),
            "-o",
            str(output_dir),
            "-b",
            "pipeline",
            "-m",
            "txt",
            "-l",
            "en",
        ]
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        if result.returncode != 0:
            stderr = (result.stderr or result.stdout).strip()
            raise RuntimeError(stderr or "MinerU CLI parsing failed.")
        return _read_mineru_output(source, output_dir)


def _extract_pdf_structure_mineru(path: str | Path) -> dict:
    attempts: list[str] = []

    result, failure = _try_mineru_runner("in-process MinerU", _extract_pdf_structure_mineru_in_process, path)
    if result is not None:
        return result
    if failure:
        attempts.append(failure)

    external_python = os.getenv("MINERU_PYTHON_EXE")
    if external_python:
        result, failure = _try_mineru_runner(
            "external MinerU Python",
            _extract_pdf_structure_mineru_via_python,
            path,
            external_python,
        )
        if result is not None:
            return result
        if failure:
            attempts.append(failure)

    result, failure = _try_mineru_runner("MinerU CLI", _extract_pdf_structure_mineru_cli, path)
    if result is not None:
        return result
    if failure:
        attempts.append(failure)

    raise RuntimeError("; ".join(attempts))


def extract_pdf_structure(path: str | Path, preferred_parser: str = "auto") -> dict:
    if preferred_parser not in {"auto", "mineru", "pypdf"}:
        raise ValueError(f"Unsupported preferred_parser: {preferred_parser}")

    if preferred_parser in {"auto", "mineru"}:
        try:
            return _extract_pdf_structure_mineru(path)
        except Exception as exc:
            if preferred_parser == "mineru":
                raise
            return _fallback_to_pypdf(path, exc)

    return _extract_pdf_structure_pypdf(path)

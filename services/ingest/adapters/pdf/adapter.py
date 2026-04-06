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


SECTION_PATTERN = re.compile(r"^(?P<clause>\d+(?:\.\d+)*)\s+(?P<title>.+)$")
TABLE_PATTERN = re.compile(r"^Table\s+(?P<id>[A-Za-z0-9_.-]+)\s*:\s*(?P<title>.+)$", re.IGNORECASE)
FIGURE_PATTERN = re.compile(r"^Figure\s+(?P<id>[A-Za-z0-9_.-]+)\s*:\s*(?P<title>.+)$", re.IGNORECASE)
PAGE_PATTERN = re.compile(r"^Page\s+(?P<page>\d+)$", re.IGNORECASE)
MARKDOWN_HEADING_PATTERN = re.compile(r"^(?P<hashes>#{1,6})\s+(?P<title>.+)$")
MARKDOWN_TABLE_ROW_PATTERN = re.compile(r"^\|.+\|$")


def _base_payload(source: Path, parser_name: str) -> dict:
    return {
        "document_id": source.stem,
        "source_type": "pdf",
        "authority_level": "canonical",
        "version": "fixture",
        "language": "en",
        "title": source.stem,
        "provenance": {
            "source_uri": str(source).replace("\\", "/"),
            "ingested_at": "fixture",
            "parser": parser_name,
        },
        "acl": {
            "policy": "team:ssd",
            "inherits_from": None,
        },
        "structure": {
            "pages": [],
            "sections": [],
            "tables": [],
            "figures": [],
            "worksheets": [],
            "slides": [],
        },
        "terminology": {
            "terms": [],
        },
        "content_blocks": [],
    }


def _finalize_payload(payload: dict) -> dict:
    sections = payload["structure"]["sections"]
    if sections:
        payload["title"] = sections[0]["heading"]
    elif payload["content_blocks"]:
        payload["title"] = payload["content_blocks"][0]["text"][:120]
    return payload


def _register_page(payload: dict, page_number: int, seen_pages: set[int] | None = None) -> None:
    if seen_pages is not None and page_number in seen_pages:
        return
    payload["structure"]["pages"].append({"page": page_number})
    if seen_pages is not None:
        seen_pages.add(page_number)


def _append_section(payload: dict, clause: str, heading: str, page_number: int, **extra_fields: object) -> None:
    payload["structure"]["sections"].append(
        {
            "id": f"section-{len(payload['structure']['sections']) + 1}",
            "clause": clause,
            "heading": heading,
            "page": page_number,
            **extra_fields,
        }
    )


def _append_caption_item(payload: dict, key: str, item_id: str, title: str, page_number: int) -> None:
    payload["structure"][key].append(
        {
            "id": item_id,
            "title": title,
            "page": page_number,
        }
    )


def _append_content_block(
    payload: dict,
    block_index: int,
    page_number: int,
    text: str,
    **extra_fields: object,
) -> None:
    payload["content_blocks"].append(
        {
            "id": f"block-{block_index}",
            "page": page_number,
            "text": text,
            **extra_fields,
        }
    )


def _index_structural_text(payload: dict, text: str, page_number: int) -> None:
    section_match = SECTION_PATTERN.match(text)
    if section_match:
        _append_section(
            payload,
            clause=section_match.group("clause"),
            heading=section_match.group("title"),
            page_number=page_number,
        )

    table_match = TABLE_PATTERN.match(text)
    if table_match:
        _append_caption_item(
            payload,
            key="tables",
            item_id=f"table-{table_match.group('id')}",
            title=table_match.group("title"),
            page_number=page_number,
        )

    figure_match = FIGURE_PATTERN.match(text)
    if figure_match:
        _append_caption_item(
            payload,
            key="figures",
            item_id=f"figure-{figure_match.group('id')}",
            title=figure_match.group("title"),
            page_number=page_number,
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
    payload = _base_payload(source, "pypdf")
    reader = PdfReader(str(source))
    block_index = 0
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
                _register_page(payload, current_page, logical_pages_seen)
                page_registered = True
                continue

            if not page_registered and current_page not in logical_pages_seen:
                _register_page(payload, current_page, logical_pages_seen)
                page_registered = True

            block_index += 1
            _index_structural_text(payload, line, current_page)
            _append_content_block(payload, block_index, current_page, line)

    return _finalize_payload(payload)


def _parse_mineru_markdown(source: Path, markdown_text: str, parser_name: str) -> dict:
    payload = _base_payload(source, parser_name)
    current_page = 1
    page_registered = False
    last_heading_clause = 0
    lines = [line.rstrip() for line in markdown_text.splitlines()]

    for idx, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if not line:
            continue

        if not page_registered:
            _register_page(payload, current_page)
            page_registered = True

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
            _append_section(
                payload,
                clause=clause,
                heading=heading,
                page_number=current_page,
            )

        table_match = TABLE_PATTERN.match(line)
        if table_match:
            _append_caption_item(
                payload,
                key="tables",
                item_id=f"table-{table_match.group('id')}",
                title=table_match.group("title"),
                page_number=current_page,
            )
        elif MARKDOWN_TABLE_ROW_PATTERN.match(line):
            table_index = len(payload["structure"]["tables"]) + 1
            _append_caption_item(
                payload,
                key="tables",
                item_id=f"table-{table_index}",
                title=f"Markdown Table {table_index}",
                page_number=current_page,
            )

        figure_match = FIGURE_PATTERN.match(line)
        if figure_match:
            _append_caption_item(
                payload,
                key="figures",
                item_id=f"figure-{figure_match.group('id')}",
                title=figure_match.group("title"),
                page_number=current_page,
            )

        _append_content_block(payload, idx, current_page, line)

    return _finalize_payload(payload)


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
    payload = _base_payload(source, parser_name)
    block_index = 0
    pdf_info = middle_json.get("pdf_info", [])

    for fallback_page_number, page in enumerate(pdf_info, start=1):
        page_number = int(page.get("page_idx", fallback_page_number - 1)) + 1
        _register_page(payload, page_number)
        page_blocks = page.get("para_blocks", []) or page.get("preproc_blocks", [])
        for page_block in page_blocks:
            text = _collect_mineru_span_text(page_block)
            if not text:
                continue

            block_type = page_block.get("type", "")
            block_level = page_block.get("level")
            normalized_lines = [line.strip() for line in text.splitlines() if line.strip()]
            normalized_text = " ".join(normalized_lines)
            if not normalized_text:
                continue

            block_index += 1

            if block_type == "title" and not SECTION_PATTERN.match(normalized_text):
                _append_section(
                    payload,
                    clause=str(len(payload["structure"]["sections"]) + 1),
                    heading=normalized_text,
                    page_number=page_number,
                    level=block_level,
                )
            else:
                _index_structural_text(payload, normalized_text, page_number)

            _append_content_block(
                payload,
                block_index,
                page_number,
                normalized_text,
                block_type=block_type,
            )

    return _finalize_payload(payload)


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

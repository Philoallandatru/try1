from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree as ET
import zipfile


NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
}


def _base_payload(path: Path, source_type: str, title: str, language: str = "en") -> dict:
    return {
        "document_id": path.stem,
        "source_type": source_type,
        "authority_level": "supporting",
        "version": "fixture",
        "language": language,
        "title": title,
        "provenance": {
            "source_uri": str(path).replace("\\", "/"),
            "ingested_at": "fixture",
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


def parse_docx(path: str | Path) -> dict:
    source = Path(path)
    payload = _base_payload(source, "docx", source.stem)
    with zipfile.ZipFile(source) as archive:
        xml = archive.read("word/document.xml")
    root = ET.fromstring(xml)
    paragraphs = []
    for para in root.findall(".//w:p", NS):
        texts = [node.text for node in para.findall(".//w:t", NS) if node.text]
        merged = "".join(texts).strip()
        if merged:
            paragraphs.append(merged)

    payload["structure"]["sections"] = [{"id": "sec-1", "heading": paragraphs[0] if paragraphs else source.stem}]
    payload["content_blocks"] = [{"id": f"block-{idx}", "text": text} for idx, text in enumerate(paragraphs, start=1)]
    payload["title"] = paragraphs[0] if paragraphs else source.stem
    return payload


def parse_xlsx(path: str | Path) -> dict:
    source = Path(path)
    payload = _base_payload(source, "xlsx", source.stem)
    with zipfile.ZipFile(source) as archive:
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        shared_strings = []
        if "xl/sharedStrings.xml" in archive.namelist():
            shared_root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            for si in shared_root.findall(".//s:si", NS):
                text = "".join(node.text or "" for node in si.findall(".//s:t", NS)).strip()
                shared_strings.append(text)

        worksheets = []
        for sheet in workbook.findall(".//s:sheet", NS):
            name = sheet.attrib.get("name", "Sheet")
            worksheets.append({"name": name})

        payload["structure"]["worksheets"] = worksheets
        payload["structure"]["tables"] = [{"id": f"table-{idx}", "worksheet": sheet["name"]} for idx, sheet in enumerate(worksheets, start=1)]
        payload["content_blocks"] = [
            {"id": f"block-{idx}", "text": text}
            for idx, text in enumerate(shared_strings, start=1)
            if text
        ]
        if worksheets:
            payload["title"] = worksheets[0]["name"]
    return payload


def parse_pptx(path: str | Path) -> dict:
    source = Path(path)
    payload = _base_payload(source, "pptx", source.stem)
    with zipfile.ZipFile(source) as archive:
        slide_files = sorted(name for name in archive.namelist() if name.startswith("ppt/slides/slide") and name.endswith(".xml"))
        slides = []
        content_blocks = []
        for idx, slide_file in enumerate(slide_files, start=1):
            root = ET.fromstring(archive.read(slide_file))
            texts = [node.text for node in root.findall(".//a:t", NS) if node.text]
            slides.append({"id": f"slide-{idx}", "name": slide_file.rsplit("/", 1)[-1]})
            if texts:
                content_blocks.append({"id": f"block-{idx}", "text": " ".join(texts)})

    payload["structure"]["slides"] = slides
    payload["content_blocks"] = content_blocks
    if content_blocks:
        payload["title"] = content_blocks[0]["text"]
    return payload


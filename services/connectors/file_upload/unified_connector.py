"""
Unified File Upload connector implementing SourceConnector interface.

Supports:
- Connection testing (file existence check)
- Initial sync (parse file once)
- Incremental sync (re-parse if file modified)
- Conversion to canonical document format

Supported file types:
- PDF (MinerU primary, pypdf fallback)
- Office (DOCX, XLSX, PPTX via MinerU)
- Images (OCR via MinerU)
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from packages.source_models import (
    ConnectionTestResult,
    FetchResult,
    FileUploadSourceConfig,
    SourceConnector,
)


class FileUploadConnector(SourceConnector):
    """
    File Upload connector implementing unified SourceConnector interface.
    """

    def __init__(self, config: FileUploadSourceConfig, credential: dict[str, str]):
        """
        Initialize File Upload connector.

        Args:
            config: File upload source configuration
            credential: Credential dictionary (not used for file uploads)
        """
        self.config = config
        self.credential = credential

    async def test_connection(self) -> ConnectionTestResult:
        """
        Test file existence and readability.

        Returns:
            ConnectionTestResult with success status
        """
        try:
            file_path = Path(self.config.file_path)

            # Check if file exists
            if not file_path.exists():
                return ConnectionTestResult(
                    success=False,
                    message=f"File not found: {self.config.file_path}",
                    details={
                        "file_path": self.config.file_path,
                        "error": "File does not exist",
                    },
                )

            # Check if file is readable
            if not os.access(file_path, os.R_OK):
                return ConnectionTestResult(
                    success=False,
                    message=f"File not readable: {self.config.file_path}",
                    details={
                        "file_path": self.config.file_path,
                        "error": "Permission denied",
                    },
                )

            # Get file info
            file_stat = file_path.stat()
            file_size = file_stat.st_size
            modified_time = datetime.fromtimestamp(file_stat.st_mtime)

            return ConnectionTestResult(
                success=True,
                message=f"File accessible: {file_path.name}",
                details={
                    "file_path": self.config.file_path,
                    "file_type": self.config.file_type,
                    "file_size": file_size,
                    "modified_time": modified_time.isoformat(),
                },
            )

        except Exception as e:
            return ConnectionTestResult(
                success=False,
                message=f"Connection test failed: {str(e)}",
                details={
                    "file_path": self.config.file_path,
                    "error": str(e),
                },
            )

    async def fetch_initial(self, cursor: Optional[str] = None) -> FetchResult:
        """
        Initial sync - parse file once.

        Args:
            cursor: Not used for file uploads (files are parsed once)

        Returns:
            FetchResult with parsed file data
        """
        try:
            file_path = Path(self.config.file_path)

            # Check file exists
            if not file_path.exists():
                return FetchResult(
                    success=False,
                    items_fetched=0,
                    error_message=f"File not found: {self.config.file_path}",
                )

            # Get file modification time as cursor
            file_stat = file_path.stat()
            modified_time = datetime.fromtimestamp(file_stat.st_mtime)
            cursor_value = modified_time.isoformat()

            # Parse file based on type
            parsed_data = await self._parse_file(file_path)

            return FetchResult(
                success=True,
                items_fetched=1,  # One file = one item
                cursor=cursor_value,
                has_more=False,  # Files are parsed once
                raw_data=[parsed_data],
            )

        except Exception as e:
            return FetchResult(
                success=False,
                items_fetched=0,
                error_message=f"Initial fetch failed: {str(e)}",
            )

    async def fetch_incremental(self, since: datetime) -> FetchResult:
        """
        Incremental sync - re-parse if file modified since last sync.

        Args:
            since: Last sync time

        Returns:
            FetchResult with updated file data (if modified)
        """
        try:
            file_path = Path(self.config.file_path)

            # Check file exists
            if not file_path.exists():
                return FetchResult(
                    success=False,
                    items_fetched=0,
                    error_message=f"File not found: {self.config.file_path}",
                )

            # Check if file was modified since last sync
            file_stat = file_path.stat()
            modified_time = datetime.fromtimestamp(file_stat.st_mtime)

            if modified_time <= since:
                # File not modified, no need to re-parse
                return FetchResult(
                    success=True,
                    items_fetched=0,
                    has_more=False,
                    raw_data=[],
                )

            # File was modified, re-parse
            parsed_data = await self._parse_file(file_path)

            return FetchResult(
                success=True,
                items_fetched=1,
                has_more=False,
                raw_data=[parsed_data],
            )

        except Exception as e:
            return FetchResult(
                success=False,
                items_fetched=0,
                error_message=f"Incremental fetch failed: {str(e)}",
            )

    def to_canonical(self, raw_data: Any) -> dict[str, Any]:
        """
        Convert parsed file data to canonical document format.

        Args:
            raw_data: Parsed file data (already in canonical format)

        Returns:
            Canonical document as dictionary
        """
        if not isinstance(raw_data, dict):
            raise ValueError("raw_data must be a dictionary")

        # Parsed data is already in canonical format
        # Just validate it has required fields
        if "document_id" not in raw_data:
            raise ValueError("Parsed data must have 'document_id' field")

        if "source_type" not in raw_data:
            raise ValueError("Parsed data must have 'source_type' field")

        return raw_data

    async def _parse_file(self, file_path: Path) -> dict[str, Any]:
        """
        Parse file based on type.

        Args:
            file_path: Path to file

        Returns:
            Parsed data in canonical document format
        """
        file_type = self.config.file_type.lower()
        parser = self.config.parser.lower()

        # Import parsers dynamically to avoid circular dependencies
        if file_type == "pdf":
            return await self._parse_pdf(file_path, parser)
        elif file_type in ("docx", "xlsx", "pptx"):
            return await self._parse_office(file_path, parser)
        elif file_type in ("png", "jpg", "jpeg", "gif", "bmp"):
            return await self._parse_image(file_path, parser)
        else:
            raise ValueError(f"Unsupported file type: {file_type}")

    async def _parse_pdf(self, file_path: Path, parser: str) -> dict[str, Any]:
        """Parse PDF file."""
        from services.ingest.adapters.pdf.adapter import extract_pdf_structure

        try:
            # extract_pdf_structure handles MinerU with pypdf fallback automatically
            # parser: "auto" (default), "mineru", or "pypdf"
            preferred_parser = parser if parser in {"auto", "mineru", "pypdf"} else "auto"
            return extract_pdf_structure(str(file_path), preferred_parser=preferred_parser)
        except Exception as e:
            raise ValueError(f"PDF parsing failed: {str(e)}")

    async def _parse_office(self, file_path: Path, parser: str) -> dict[str, Any]:
        """Parse Office file (DOCX, XLSX, PPTX)."""
        from services.ingest.adapters.office.adapter import parse_docx, parse_pptx, parse_xlsx

        file_type = self.config.file_type.lower()

        if file_type == "docx":
            return parse_docx(file_path)

        elif file_type == "xlsx":
            return parse_xlsx(file_path)

        elif file_type == "pptx":
            return parse_pptx(file_path)

        else:
            raise ValueError(f"Unsupported office file type: {file_type}")

    async def _parse_image(self, file_path: Path, parser: str) -> dict[str, Any]:
        """Parse image file with OCR."""
        # For now, create a simple canonical document
        # TODO: Implement OCR via MinerU
        from services.ingest.normalizer import build_base_document, finalize_document

        document = build_base_document(
            document_id=file_path.stem,
            source_type="image",
            authority_level="supporting",
            version="1",
            language="en",
            title=file_path.name,
            source_uri=str(file_path),
            ingested_at=datetime.now().isoformat(),
            parser="image-placeholder",
            acl_policy="team:ssd",
        )

        document["metadata"] = {
            "file_type": self.config.file_type,
            "file_path": str(file_path),
            "ocr_pending": True,
        }

        return finalize_document(document)

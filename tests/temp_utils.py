from __future__ import annotations

from contextlib import contextmanager
import os
from pathlib import Path
import shutil
from uuid import uuid4


@contextmanager
def temporary_directory(prefix: str = "test"):
    temp_root = Path(os.environ.get("SSD_KNOWLEDGE_TEST_TMP", ".pytest_tmp"))
    temp_root.mkdir(parents=True, exist_ok=True)
    temp_dir = temp_root / f"{prefix}-{uuid4().hex}"
    temp_dir.mkdir()
    try:
        yield str(temp_dir)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

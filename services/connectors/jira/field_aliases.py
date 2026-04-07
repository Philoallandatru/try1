from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import json


DEFAULT_ALIAS_PATH = Path(__file__).resolve().parents[3] / "packages" / "schema" / "jira-field-aliases.json"


@lru_cache(maxsize=8)
def load_jira_field_aliases(path: str | Path | None = None) -> dict[str, list[str]]:
    alias_path = Path(path) if path else DEFAULT_ALIAS_PATH
    payload = json.loads(alias_path.read_text(encoding="utf-8"))
    return {
        str(label): [str(alias).strip() for alias in aliases if str(alias).strip()]
        for label, aliases in payload.items()
    }

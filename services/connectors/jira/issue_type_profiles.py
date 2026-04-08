from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import json


DEFAULT_PROFILE_PATH = Path(__file__).resolve().parents[3] / "packages" / "schema" / "jira-issue-type-profiles.json"


@lru_cache(maxsize=8)
def load_jira_issue_type_profiles(path: str | Path | None = None) -> dict:
    profile_path = Path(path) if path else DEFAULT_PROFILE_PATH
    payload = json.loads(profile_path.read_text(encoding="utf-8"))
    default = payload.get("default", {})
    profiles = payload.get("profiles", {})
    return {
        "default": {
            "issue_family": str(default.get("issue_family", "unknown")).strip() or "unknown",
            "issue_route": str(default.get("issue_route", "generic_jira_summary")).strip() or "generic_jira_summary",
        },
        "profiles": {
            str(issue_type).strip(): {
                "issue_family": str(profile.get("issue_family", "")).strip(),
                "issue_route": str(profile.get("issue_route", "")).strip(),
            }
            for issue_type, profile in profiles.items()
            if str(issue_type).strip()
        },
    }


def route_jira_issue_type(issue_type_raw: str | None, profiles: dict | None = None) -> dict[str, str]:
    issue_type = (issue_type_raw or "").strip()
    loaded_profiles = profiles or load_jira_issue_type_profiles()
    default = loaded_profiles["default"]
    profile = loaded_profiles["profiles"].get(issue_type, default)
    return {
        "issue_type_raw": issue_type or "unknown",
        "issue_family": profile.get("issue_family") or default["issue_family"],
        "issue_route": profile.get("issue_route") or default["issue_route"],
    }

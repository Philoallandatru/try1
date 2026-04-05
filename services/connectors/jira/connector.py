from __future__ import annotations

from pathlib import Path
import json


def load_jira_sync(path: str | Path) -> dict:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    documents = []
    for issue in payload["issues"]:
        documents.append(
            {
                "document_id": issue["key"],
                "source_type": "jira",
                "version": issue["updated_at"],
                "title": issue["summary"],
                "comments": issue["comments"],
                "metadata": {
                    "project": issue["project"],
                    "incremental": payload["sync_type"] == "incremental",
                },
            }
        )
    return {
        "sync_type": payload["sync_type"],
        "cursor": payload["cursor"],
        "documents": documents,
    }


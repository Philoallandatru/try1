from __future__ import annotations

from pathlib import Path
import json


def load_confluence_sync(path: str | Path) -> dict:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    documents = []
    for page in payload["pages"]:
        documents.append(
            {
                "document_id": page["id"],
                "source_type": "confluence",
                "version": page["version"],
                "title": page["title"],
                "attachments": page["attachments"],
                "metadata": {
                    "space": page["space"],
                    "incremental": payload["sync_type"] == "incremental",
                },
            }
        )
    return {
        "sync_type": payload["sync_type"],
        "cursor": payload["cursor"],
        "documents": documents,
    }


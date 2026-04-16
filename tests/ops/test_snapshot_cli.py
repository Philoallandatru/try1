from __future__ import annotations

import json
import subprocess
import sys
import unittest

from tests.temp_utils import temporary_directory as TemporaryDirectory


class SnapshotCliTest(unittest.TestCase):
    def _run(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, *args],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_snapshot_cli_create_and_show(self) -> None:
        with TemporaryDirectory() as temp_dir:
            create = self._run(
                "scripts/retrieval/snapshot_cli.py",
                "create",
                "--snapshot-dir",
                temp_dir,
                "--corpus",
                "fixtures/retrieval/pageindex_corpus.json",
            )
            self.assertEqual(create.returncode, 0, create.stderr)

            show = self._run(
                "scripts/retrieval/snapshot_cli.py",
                "show",
                "--snapshot-dir",
                temp_dir,
            )
            self.assertEqual(show.returncode, 0, show.stderr)
            payload = json.loads(show.stdout)
            self.assertIn("manifest", payload)
            self.assertIn("documents", payload)
            self.assertIn("page_index", payload)

    def test_snapshot_cli_refresh_updates_manifest(self) -> None:
        with TemporaryDirectory() as temp_dir:
            create = self._run(
                "scripts/retrieval/snapshot_cli.py",
                "create",
                "--snapshot-dir",
                temp_dir,
                "--corpus",
                "fixtures/retrieval/pageindex_corpus.json",
            )
            self.assertEqual(create.returncode, 0, create.stderr)

            refresh = self._run(
                "scripts/retrieval/snapshot_cli.py",
                "refresh",
                "--snapshot-dir",
                temp_dir,
                "--sync-payload",
                "fixtures/connectors/jira/incremental_sync.json",
                "--source-name",
                "jira",
            )
            self.assertEqual(refresh.returncode, 0, refresh.stderr)
            payload = json.loads(refresh.stdout)
            self.assertEqual(payload["manifest"]["sources"]["jira"]["cursor"], "jira-incr-002")
            self.assertIn("last_sync", payload["manifest"]["sources"]["jira"])
            self.assertEqual(payload["updated_document_ids"], ["SSD-102"])
            self.assertEqual(payload["manifest"]["sources"]["jira"]["document_count"], 1)


if __name__ == "__main__":
    unittest.main()

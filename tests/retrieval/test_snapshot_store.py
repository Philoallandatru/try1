from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

from services.connectors.jira.connector import load_jira_sync
from services.retrieval.persistence.snapshot_store import create_snapshot, load_snapshot, refresh_snapshot
from services.retrieval.toolkit import load_document_snapshot


class SnapshotStoreTest(unittest.TestCase):
    def test_create_snapshot_persists_manifest_documents_and_page_index(self) -> None:
        documents = load_document_snapshot(Path("fixtures/retrieval/pageindex_corpus.json"))
        with TemporaryDirectory() as temp_dir:
            result = create_snapshot(temp_dir, documents=documents, source_name="fixture-corpus")
            loaded = load_snapshot(temp_dir)

        self.assertIn("manifest", result)
        self.assertEqual(loaded["manifest"]["document_count"], len(documents))
        self.assertEqual(len(loaded["documents"]["documents"]), len(documents))
        self.assertGreater(len(loaded["page_index"]["entries"]), 0)

    def test_refresh_snapshot_replaces_documents_by_document_id(self) -> None:
        base_documents = load_document_snapshot(Path("fixtures/retrieval/pageindex_corpus.json"))
        incremental_payload = load_jira_sync(Path("fixtures/connectors/jira/incremental_sync.json"))

        with TemporaryDirectory() as temp_dir:
            create_snapshot(temp_dir, documents=base_documents, source_name="fixture-corpus")
            refresh_result = refresh_snapshot(temp_dir, sync_payload=incremental_payload, source_name="jira")
            loaded = load_snapshot(temp_dir)

        document_ids = {document["document_id"] for document in loaded["documents"]["documents"]}
        self.assertIn("SSD-102", document_ids)
        self.assertIn("jira", loaded["manifest"]["sources"])
        self.assertEqual(loaded["manifest"]["sources"]["jira"]["cursor"], "jira-incr-002")
        self.assertEqual(refresh_result["updated_document_ids"], ["SSD-102"])

    def test_snapshot_cli_payload_shape_is_json_serializable(self) -> None:
        documents = load_document_snapshot(Path("fixtures/retrieval/pageindex_corpus.json"))
        with TemporaryDirectory() as temp_dir:
            create_snapshot(temp_dir, documents=documents, source_name="fixture-corpus")
            loaded = load_snapshot(temp_dir)
            json.dumps(loaded, ensure_ascii=False)


if __name__ == "__main__":
    unittest.main()

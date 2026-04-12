from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from services.retrieval.toolkit import load_document_snapshot
from services.wiki_site.builder import build_export_package, build_wiki_site


class WikiSiteBuilderTest(unittest.TestCase):
    def test_build_export_package_writes_manifest_changes_and_documents(self) -> None:
        documents = load_document_snapshot("fixtures/retrieval/pageindex_corpus.json")
        with TemporaryDirectory() as temp_dir:
            report = build_export_package(
                export_root=temp_dir,
                documents=documents,
                export_mode="test",
                source_snapshot=".tmp/snapshot",
            )

            self.assertEqual(report["document_count"], len(documents))
            manifest = json.loads((Path(temp_dir) / "manifest.json").read_text(encoding="utf-8"))
            changes = json.loads((Path(temp_dir) / "changes.json").read_text(encoding="utf-8"))
            page_index = json.loads((Path(temp_dir) / "page_index.json").read_text(encoding="utf-8"))

            self.assertEqual(manifest["document_count"], len(documents))
            self.assertEqual(len(changes), len(documents))
            self.assertIn("entries", page_index)

            latest_doc = manifest["documents"][0]
            markdown_path = Path(temp_dir) / latest_doc["markdown_path"]
            metadata_path = Path(temp_dir) / latest_doc["metadata_path"]
            self.assertTrue(markdown_path.exists())
            self.assertTrue(metadata_path.exists())

    def test_build_wiki_site_writes_mkdocs_structure(self) -> None:
        documents = load_document_snapshot("fixtures/retrieval/pageindex_corpus.json")
        with TemporaryDirectory() as temp_dir:
            export_root = Path(temp_dir) / "export"
            wiki_root = Path(temp_dir) / "wiki_site"
            build_export_package(
                export_root=export_root,
                documents=documents,
                export_mode="test",
                source_snapshot=".tmp/snapshot",
            )
            report = build_wiki_site(
                export_root=export_root,
                output_root=wiki_root,
                site_title="Test Wiki",
                analysis_pages=[
                    {
                        "slug": "demo-overview.md",
                        "title": "Demo Overview",
                        "body": "Derived summary body",
                        "derived_from": ["nvme-spec-v1"],
                    }
                ],
            )

            self.assertTrue(Path(report["mkdocs_yml"]).exists())
            mkdocs_yml = Path(report["mkdocs_yml"]).read_text(encoding="utf-8")
            self.assertTrue((wiki_root / "docs" / "index.md").exists())
            self.assertTrue((wiki_root / "docs" / "sources" / "index.md").exists())
            self.assertTrue((wiki_root / "docs" / "projects" / "index.md").exists())
            self.assertTrue((wiki_root / "docs" / "topics" / "index.md").exists())
            self.assertTrue((wiki_root / "docs" / "analysis" / "index.md").exists())
            self.assertTrue((wiki_root / "docs" / "analysis" / "demo-overview.md").exists())
            self.assertIn("sources/pdf/nvme-spec-v1.md", mkdocs_yml)
            self.assertIn("analysis/demo-overview.md", mkdocs_yml)


if __name__ == "__main__":
    unittest.main()

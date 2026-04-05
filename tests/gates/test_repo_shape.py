from pathlib import Path
import unittest


REQUIRED_PATHS = [
    "apps/portal",
    "services/ingest",
    "services/connectors",
    "services/retrieval",
    "services/eval",
    "packages/schema",
    "packages/acl",
    "packages/terminology",
    "packages/shared-config",
    "ops",
    "docs/adr",
    "docs/runbooks",
    "docs/modules",
    "fixtures/corpus",
    "fixtures/schema",
    "fixtures/connectors",
    "fixtures/retrieval",
    "eval",
    "scripts/ingest",
    "scripts/eval",
    "scripts/gates",
    "tests/ingest",
    "tests/connectors",
    "tests/retrieval",
    "tests/security",
    "tests/portal",
    "tests/ops",
]


class RepoShapeTest(unittest.TestCase):
    def test_required_top_level_paths_exist(self) -> None:
        for rel_path in REQUIRED_PATHS:
            with self.subTest(path=rel_path):
                self.assertTrue(Path(rel_path).exists(), f"{rel_path} should exist")


if __name__ == "__main__":
    unittest.main()

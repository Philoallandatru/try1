from pathlib import Path
import unittest


ADR_REQUIREMENTS = {
    "docs/adr/0001-phase1-scope.md": ["## Status", "## In Scope", "## Out of Scope", "## Decision"],
    "docs/adr/0002-source-authority.md": ["## Status", "## Authority Levels", "## Ranking Rule", "## Decision"],
    "docs/adr/0003-phase1-success-metrics.md": ["## Status", "## Quality Thresholds", "## Gold Set Coverage", "## Decision"],
}


class AdrContractTest(unittest.TestCase):
    def test_required_adr_files_exist_with_headings(self) -> None:
        for rel_path, headings in ADR_REQUIREMENTS.items():
            with self.subTest(path=rel_path):
                path = Path(rel_path)
                self.assertTrue(path.exists(), f"{rel_path} should exist")
                text = path.read_text(encoding="utf-8")
                for heading in headings:
                    self.assertIn(heading, text)


if __name__ == "__main__":
    unittest.main()


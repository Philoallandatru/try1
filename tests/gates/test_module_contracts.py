from pathlib import Path
import unittest


REQUIRED_MODULES = [
    "docs/modules/product-design-optimization.md",
    "docs/modules/testcase-optimization.md",
    "docs/modules/wiki-summarization-intelligence.md",
    "docs/modules/pr-review-intelligence.md",
]

REQUIRED_HEADINGS = [
    "## Scope",
    "## Inputs",
    "## Outputs",
    "## Dependencies",
    "## KPIs",
]


class ModuleContractsTest(unittest.TestCase):
    def test_all_module_contracts_are_complete(self) -> None:
        for module_path in REQUIRED_MODULES:
            with self.subTest(path=module_path):
                path = Path(module_path)
                self.assertTrue(path.exists())
                text = path.read_text(encoding="utf-8")
                for heading in REQUIRED_HEADINGS:
                    self.assertIn(heading, text)


if __name__ == "__main__":
    unittest.main()


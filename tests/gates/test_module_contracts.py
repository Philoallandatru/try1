from pathlib import Path
import unittest


REQUIRED_MODULES = [
    "docs/modules/product-design-optimization.md",
    "docs/modules/testcase-optimization.md",
    "docs/modules/wiki-summarization-intelligence.md",
    "docs/modules/pr-review-intelligence.md",
    "docs/modules/live-source-normalization-and-indexing.md",
    "docs/modules/local-snapshot-persistence-and-refresh.md",
    "docs/modules/profile-driven-ops-orchestration.md",
    "docs/modules/jira-analysis-reporting.md",
]

REQUIRED_HEADINGS = [
    "## Scope",
    "## Inputs",
    "## Outputs",
    "## Dependencies",
    "## KPIs",
]

MODULE_REQUIRED_TOKENS = {
    "docs/modules/live-source-normalization-and-indexing.md": [
        "docs/jira-bug-field-mapping.md",
        "packages/schema/jira-field-aliases.json",
        "docs/confluence-page-mapping.md",
    ],
    "docs/modules/jira-analysis-reporting.md": [
        "services/analysis/jira_issue_analysis.py",
        "scripts/platform_cli.py jira-report",
        "scripts/platform_cli.py jira-spec-qa",
        "scripts/platform_cli.py jira-batch-spec-report",
        "tests.analysis.test_jira_issue_analysis",
    ],
}


class ModuleContractsTest(unittest.TestCase):
    def test_all_module_contracts_are_complete(self) -> None:
        for module_path in REQUIRED_MODULES:
            with self.subTest(path=module_path):
                path = Path(module_path)
                self.assertTrue(path.exists())
                text = path.read_text(encoding="utf-8")
                for heading in REQUIRED_HEADINGS:
                    self.assertIn(heading, text)
                for token in MODULE_REQUIRED_TOKENS.get(module_path, []):
                    self.assertIn(token, text)


if __name__ == "__main__":
    unittest.main()

from pathlib import Path
import sys


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
        "services/analysis/llm_backends.py",
        "scripts/platform_cli.py jira-report",
        "scripts/platform_cli.py jira-report --llm-backend",
        "scripts/platform_cli.py jira-spec-qa",
        "scripts/platform_cli.py jira-batch-spec-report",
        "--llm-backend none|ollama|openai-compatible",
        "--llm-prompt-mode",
        "tests.analysis.test_jira_issue_analysis",
    ],
}


def main() -> int:
    failures = []
    for module_path in REQUIRED_MODULES:
        path = Path(module_path)
        if not path.exists():
            failures.append(f"missing file: {module_path}")
            continue
        text = path.read_text(encoding="utf-8")
        for heading in REQUIRED_HEADINGS:
            if heading not in text:
                failures.append(f"{module_path}: missing heading {heading}")
        for token in MODULE_REQUIRED_TOKENS.get(module_path, []):
            if token not in text:
                failures.append(f"{module_path}: missing required token {token}")
    if failures:
        print("\n".join(failures))
        return 1
    print("Module contract check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from pathlib import Path
import sys


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
    if failures:
        print("\n".join(failures))
        return 1
    print("Module contract check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


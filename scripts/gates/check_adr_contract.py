from pathlib import Path
import sys


ADR_REQUIREMENTS = {
    "docs/adr/0001-phase1-scope.md": ["## Status", "## In Scope", "## Out of Scope", "## Decision"],
    "docs/adr/0002-source-authority.md": ["## Status", "## Authority Levels", "## Ranking Rule", "## Decision"],
    "docs/adr/0003-phase1-success-metrics.md": ["## Status", "## Quality Thresholds", "## Gold Set Coverage", "## Decision"],
}


def main() -> int:
    missing = []
    for rel_path, headings in ADR_REQUIREMENTS.items():
        path = Path(rel_path)
        if not path.exists():
            missing.append(f"missing file: {rel_path}")
            continue
        text = path.read_text(encoding="utf-8")
        for heading in headings:
            if heading not in text:
                missing.append(f"{rel_path}: missing heading {heading}")
    if missing:
        print("\n".join(missing))
        return 1
    print("ADR contract check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


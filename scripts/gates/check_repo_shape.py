from pathlib import Path
import sys


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


def main() -> int:
    missing = [path for path in REQUIRED_PATHS if not Path(path).exists()]
    if missing:
        print("\n".join(missing))
        return 1
    print("Repository shape check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

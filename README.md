# SSD Knowledge Platform

Internal SSD knowledge platform for trusted retrieval and grounded Q&A over specifications, design documents, requirements, Jira issues, and Confluence pages.

This repository currently contains a Phase 1 foundation implementation:

- Contract and ADR layer
- Canonical schema and ACL contracts
- Markdown, Office, and PDF ingestion adapters
- Jira and Confluence fixture-based connectors
- PageIndex-first hybrid retrieval
- Citation assembly and source inspection
- Retrieval evaluation harness and rollout gate
- Internal ops portal MVP
- Skill-ready reusable component boundaries

## Core Docs

- [agent.md](C:\Users\10259\Documents\code\codex\codex-try\agent.md)
- [spec.md](C:\Users\10259\Documents\code\codex\codex-try\spec.md)
- [todo.md](C:\Users\10259\Documents\code\codex\codex-try\todo.md)
- [docs/architecture-overview.md](C:\Users\10259\Documents\code\codex\codex-try\docs\architecture-overview.md)
- [docs/implementation-status.md](C:\Users\10259\Documents\code\codex\codex-try\docs\implementation-status.md)
- [docs/cli-reference.md](C:\Users\10259\Documents\code\codex\codex-try\docs\cli-reference.md)

## Repository Shape

```text
apps/
services/
packages/
scripts/
fixtures/
tests/
docs/
ops/
eval/
```

## Quick Start

Run the full test suite:

```bash
python -m unittest discover -s tests -t . -p "test_*.py" -v
```

Run retrieval evaluation:

```bash
python scripts/eval/run_recall_eval.py --dataset eval/gold_queries.yaml
```

Run the Phase 1 rollout gate:

```bash
python scripts/gates/run_phase1_gate.py
```

Use the unified CLI:

```bash
python scripts/platform_cli.py gate
python scripts/platform_cli.py eval
python scripts/platform_cli.py search "flush command"
python scripts/platform_cli.py citation "flush command"
```

Generate portal state for the static ops UI:

```bash
python -c "from apps.portal.portal_state import write_portal_state; print(write_portal_state())"
```

## Current Constraints

- Connectors and ingestion flows are fixture-driven, not yet live-integrated.
- The portal is a static internal UI backed by generated JSON state.
- Retrieval and evaluation currently run on the local fixture corpus.
- The implementation is structured to be extended into production integrations and reusable skills.


# SSD Knowledge Platform

Internal SSD knowledge platform for trusted retrieval and grounded Q&A over specifications, design documents, requirements, Jira issues, and Confluence pages.

This repository currently contains a Phase 1 foundation implementation for converting engineering sources into canonical documents, readable Markdown, PageIndex entries, and grounded retrieval/citation outputs.

- Contract and ADR layer
- Canonical schema and ACL contracts
- Markdown, Office, and PDF ingestion adapters
- Jira and Confluence fixture-backed and live connector paths
- Visual asset normalization for image references with provided OCR/caption metadata
- Markdown and PageIndex export from normalized documents
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
- [docs/environment-setup.md](C:\Users\10259\Documents\code\codex\codex-try\docs\environment-setup.md)
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

Create a local Python environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
python -m pip install pypdf
```

Convert supported sources to readable Markdown and PageIndex artifacts:

```powershell
python scripts/ingest/normalize_cli.py jira-sync fixtures/connectors/jira/full_sync.json --output-md .tmp/jira.md --output-page-index .tmp/jira-page-index.json
python scripts/ingest/normalize_cli.py confluence-sync fixtures/connectors/confluence/page_sync.json --output-md .tmp/confluence.md --output-page-index .tmp/confluence-page-index.json
python scripts/ingest/normalize_cli.py pptx fixtures/corpus/office/sample.pptx --output-md .tmp/pptx.md --output-page-index .tmp/pptx-page-index.json
python scripts/ingest/normalize_cli.py pdf fixtures/corpus/pdf/sample.pdf --output-md .tmp/pdf.md --output-page-index .tmp/pdf-page-index.json
```

Run the full test suite:

```powershell
python -m unittest discover
```

Run retrieval evaluation and the Phase 1 rollout gate:

```powershell
python scripts/eval/run_recall_eval.py --dataset eval/gold_queries.yaml
python scripts/gates/run_phase1_gate.py
```

Use the unified CLI:

```powershell
python scripts/platform_cli.py gate
python scripts/platform_cli.py eval
python scripts/platform_cli.py search "flush command"
python scripts/platform_cli.py citation "flush command"
```

Generate portal state for the static ops UI:

```powershell
python -c "from apps.portal.portal_state import write_portal_state; print(write_portal_state())"
```

## Environment

See [docs/environment-setup.md](C:\Users\10259\Documents\code\codex\codex-try\docs\environment-setup.md) for:

- Python and dependency setup
- optional MinerU PDF parser configuration
- optional Ollama/OpenAI-compatible local LLM configuration
- live Jira and Confluence credential examples
- Markdown and PageIndex export commands

## Current Constraints

- Live Jira and Confluence connector paths exist, but production rollout still needs real-environment smoke coverage.
- The portal is a static internal UI backed by generated JSON state.
- Retrieval and evaluation currently run on the local fixture corpus.
- Image references can be merged into Markdown when `alt_text`, `ocr_text`, or `vision_caption` metadata is present; automatic image download/OCR/vision captioning is still a production gap.
- The implementation is structured to be extended into production integrations and reusable skills.

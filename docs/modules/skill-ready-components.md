# Skill-Ready Components

## Purpose

This document identifies the Phase 1 capabilities that are already shaped to be extracted into reusable skills.

## Candidate Components

### Schema Contract Validator

- Entry point: `scripts/platform_cli.py adr-check` and `scripts/platform_cli.py repo-check`
- Core assets:
  - `scripts/gates/check_adr_contract.py`
  - `scripts/gates/check_repo_shape.py`
  - `scripts/gates/check_module_contracts.py`
- Skill value: reusable governance and contract validation for AI-assisted repositories

### Document Normalization Toolkit

- Entry point: `scripts/platform_cli.py ingest ...`
- Core assets:
  - Markdown adapter
  - OOXML office adapters
  - PDF structural extraction adapter
- Skill value: reusable offline normalization and structure-preserving extraction

### Retrieval and Citation Toolkit

- Entry point:
  - `scripts/platform_cli.py search ...`
  - `scripts/platform_cli.py citation ...`
- Core assets:
  - Page index builder
  - Hybrid search
  - Citation assembly
  - Source inspection payload
- Skill value: reusable grounded retrieval and citation formatting

### Evaluation and Rollout Toolkit

- Entry point:
  - `scripts/platform_cli.py eval`
  - `scripts/platform_cli.py gate`
  - `scripts/platform_cli.py ops-health`
- Core assets:
  - Eval harness
  - Metrics library
  - Rollout gate runner
  - Ops health builder
- Skill value: reusable release-gate and retrieval-quality validation

## Extraction Guidance

- Keep entrypoints stable and CLI-friendly.
- Keep project-specific thresholds or document lists in external config or datasets.
- Separate contracts from SSD-specific pilot policy where possible.


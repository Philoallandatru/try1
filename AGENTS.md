# Agent Instructions

## Scope And Source Of Truth
- This repo implements the Phase 1 foundation of the SSD knowledge platform: ingestion, normalization, PageIndex-first retrieval, citations, evaluation, ops health, and a static ops portal.
- Treat `spec.md` as the product contract, `docs/adr/*.md` as architecture decisions, `docs/api-contracts.md` as payload-shape reference, and `agent.md` plus `docs/developer-workflow.md` as the main agent workflow rules.
- Include `todo.md` when determining current task/stage intent; this repo uses it as an active planning and acceptance artifact.
- Treat `README.md` and `docs/implementation-status.md` as descriptive docs, not the final authority when they disagree with `spec.md` or ADRs.
- Ignore generated session artifacts under `.omx/state/sessions/**/AGENTS.md`; they are tool state, not repo policy.
- No repo-level Cursor rules were found in `.cursor/rules/` or `.cursorrules`.
- No Copilot rules were found in `.github/copilot-instructions.md`.

## Repository Shape
- Main runtime packages: `apps/*`, `services/*`.
- Contract and reference assets: `packages/*`, `docs/*`, `fixtures/*`, `eval/*`, `ops/*`, `skills/*`, `tests/*`.
- Unified CLI: `scripts/platform_cli.py`.
- Skill-ready CLIs: `scripts/ingest/normalize_cli.py`, `scripts/retrieval/toolkit_cli.py`, `scripts/retrieval/snapshot_cli.py`.
- Stable reusable seams are documented in `agent.md` and centered on normalization, retrieval, and snapshot persistence.

## Environment And Setup
- Python baseline is 3.12+.
- Preferred environment setup uses `uv`; plain `venv` + `pip` is also supported.
- Install runtime package in editable mode before running commands from a fresh environment.

```powershell
python -m pip install --upgrade uv
uv venv --python 3.12
.\.venv\Scripts\Activate.ps1
uv pip install -e .
uv pip install -e ".[dev]"
```

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
```

## Canonical Commands
- There is no JS package manager, `Makefile`, `justfile`, or separate task runner at the repo root.
- There is no dedicated lint tool configured in the repo today.
- `pytest` is optional and configured in `pyproject.toml`, but the canonical test path remains `unittest`.

### Core Validation
```powershell
python scripts/gates/check_adr_contract.py
python scripts/gates/check_repo_shape.py
python scripts/gates/check_module_contracts.py
python -m unittest discover -s tests -t . -p "test_*.py" -v
python -m compileall docs scripts services tests
python scripts/eval/run_recall_eval.py --dataset eval/gold_queries.yaml
python scripts/gates/run_phase1_gate.py
```

### Unified CLI
```powershell
python scripts/platform_cli.py eval
python scripts/platform_cli.py gate
python scripts/platform_cli.py search "flush command"
python scripts/platform_cli.py citation "flush command"
python scripts/platform_cli.py ops-health --snapshot-dir .tmp/snapshot
python scripts/platform_cli.py sync-health jira fixtures/connectors/jira/incremental_sync.json --snapshot-dir .tmp/snapshot
python scripts/platform_cli.py multi-sync-health --profile fixtures/ops/multi_sync_health_profile.json --snapshot-dir .tmp/snapshot
python scripts/platform_cli.py portal-state --query "nvme flush"
```

### Ingestion / Normalization
```powershell
python scripts/ingest/normalize_cli.py markdown fixtures/corpus/markdown/sample.md
python scripts/ingest/normalize_cli.py jira-sync fixtures/connectors/jira/full_sync.json --output-md .tmp/jira.md --output-page-index .tmp/jira-page-index.json
python scripts/ingest/normalize_cli.py confluence-sync fixtures/connectors/confluence/page_sync.json --output-md .tmp/confluence.md --output-page-index .tmp/confluence-page-index.json
python scripts/ingest/normalize_cli.py pptx fixtures/corpus/office/sample.pptx --output-md .tmp/pptx.md --output-page-index .tmp/pptx-page-index.json
python scripts/ingest/normalize_cli.py pdf fixtures/corpus/pdf/sample.pdf --output-md .tmp/pdf.md --output-page-index .tmp/pdf-page-index.json
```

### Retrieval Toolkit
```powershell
python scripts/retrieval/toolkit_cli.py index --corpus fixtures/retrieval/pageindex_corpus.json
python scripts/retrieval/toolkit_cli.py search "flush command" --corpus fixtures/retrieval/pageindex_corpus.json
python scripts/retrieval/toolkit_cli.py citation "flush command" --corpus fixtures/retrieval/pageindex_corpus.json
```

### Snapshot Persistence
```powershell
python scripts/retrieval/snapshot_cli.py create --snapshot-dir .tmp/snapshot --corpus fixtures/retrieval/pageindex_corpus.json
python scripts/retrieval/snapshot_cli.py show --snapshot-dir .tmp/snapshot
python scripts/retrieval/snapshot_cli.py refresh --snapshot-dir .tmp/snapshot --sync-payload fixtures/connectors/jira/incremental_sync.json --source-name jira
```

### Live Connector Examples
```powershell
python scripts/platform_cli.py connector jira --live --base-url https://jira.example.com --token $env:JIRA_TOKEN
python scripts/platform_cli.py connector confluence --live --base-url https://confluence.example.com --token $env:CONF_TOKEN
```

## Single-Test Commands
- Preferred single-test command style is `python -m unittest <module>`.
- Use the dotted module path, not a file path, when running a single unittest module.
- Confirmed examples that match real test modules:

```powershell
python -m unittest tests.analysis.test_jira_issue_analysis
python -m unittest tests.retrieval.test_snapshot_store
python -m unittest tests.ops.test_platform_cli
python -m unittest tests.ops.test_platform_cli_live_orchestration
python -m unittest tests.gates.test_phase1_gate
```

- If you need to run one test method:

```powershell
python -m unittest tests.analysis.test_jira_issue_analysis.JiraIssueAnalysisTest.test_jira_spec_question_payload_retrieves_jira_and_spec_evidence
```

## Code Style
- Follow existing Python style from `services/ingest/normalizer.py`, `services/retrieval/search/hybrid_search.py`, `services/analysis/llm_backends.py`, `services/ops/orchestration.py`, and `scripts/platform_cli.py`.
- Start Python files with `from __future__ import annotations`.
- Group imports as: standard library first, then absolute repo imports from `services`, `apps`, `scripts`, or `packages`.
- Prefer absolute imports over relative imports in runtime and CLI code.
- Use 4-space indentation and keep top-level definitions separated by two blank lines.
- Keep functions compact and explicit; avoid ornamental comments and unnecessary helper layers.

## Typing And Data Shapes
- Use Python 3.12 typing syntax: `list[dict]`, `set[str]`, `str | None`.
- Prefer narrow built-in generics over `typing.List` / `typing.Optional`.
- Use `Protocol` for lightweight interfaces when a module already follows that pattern.
- Use dataclasses only when the module already models a stable object that way.
- Most runtime contracts are dict-first; preserve existing payload keys instead of introducing new abstraction layers casually.
- If changing payload shape, update the contract docs and the relevant tests in the same slice.

## Naming
- Functions and variables: `snake_case`.
- Classes: `CapWords`.
- Constants: `UPPER_SNAKE_CASE`.
- Test modules: `test_*.py`.
- Test methods: `test_*`.
- Keep filenames domain-based and aligned with the current layout under `services/*`, `scripts/*`, and `tests/*`.

## Error Handling
- Validate CLI inputs early and fail with `argparse.ArgumentParser.error(...)` for user-facing argument mistakes.
- Raise narrow built-ins such as `ValueError`, `RuntimeError`, and `TypeError` with explicit messages.
- Do not add broad `except Exception` handlers unless a surrounding boundary truly requires it.
- Do not silently coerce invalid contract data; fail loudly at the edge.
- Preserve deterministic behavior by default; opt-in local-LLM behavior must stay explicit.

## Testing And Workflow Rules
- Start from the governing contract before editing code: `spec.md`, `docs/adr/*`, `docs/api-contracts.md`, `agent.md`, `todo.md`, and `docs/developer-workflow.md`.
- Write or update deterministic tests first when changing behavior.
- Keep fixture-backed tests deterministic; prefer mock/live validation only where the repo already does so.
- For meaningful changes, run the smallest validation set that proves the increment, then run broader gates if the contract changed.
- For substantial work, record execution evidence under `.sisyphus/evidence/` with commands run and observed results.
- Update `README.md`, `docs/architecture-overview.md`, `docs/implementation-status.md`, or `docs/cli-reference.md` when behavior changes.

## Architecture Hard Constraints
- Retrieval must remain PageIndex-first.
- ACL filtering must happen before ranking and before answer assembly.
- Ranking default remains `canonical > supporting > contextual`.
- Citation payloads must resolve to evidence-bearing content and include `document + version + page + section/clause` when available.
- Structure metadata such as page, clause, worksheet, slide, table, and figure must remain first-class.
- Snapshot persistence remains file-backed in this phase: `manifest.json`, `documents.json`, and `page_index.json` only.
- Refresh logic must merge by stable `document_id` and rebuild page index after create or refresh.

## Preferred Reuse Points
- Normalization seam: `services/ingest/normalizer.py`, `scripts/ingest/normalize_cli.py`.
- Retrieval seam: `services/retrieval/toolkit.py`, `scripts/retrieval/toolkit_cli.py`.
- Snapshot seam: `services/retrieval/persistence/snapshot_store.py`, `scripts/retrieval/snapshot_cli.py`.
- Prefer repo-local skills under `skills/offline-document-normalizer/` and `skills/grounded-retrieval-toolkit/` when the task matches those scopes.

## Jira Routing Constraints
- When touching Jira ingestion, sync/export, or analysis, preserve `issue_type_raw`, `issue_family`, and `issue_route` in Jira document metadata.
- Family mapping matters operationally: defects route to RCA, requirements route to PRD/MRD analysis, requirement changes and component changes route to impact analysis, delivery/release items must not be forced through bug RCA prompts.
- Keep Jira Markdown generation permissive; bug-only fields such as `Root Cause`, `How to fix`, and `Action` are optional and must not become required for PRD/MRD, release, or delivery issues.
- Planned routing details live in `docs/jira-issue-type-routing-plan.md`; align changes with that plan and existing tests.

## Avoid
- Do not treat this repo as a generic AI assistant app; it is a retrieval and grounded-QA substrate.
- Do not bypass ACL, citation, or evaluation gates for convenience.
- Do not weaken canonical document, citation, or retrieval contract shapes casually.
- Do not ingest `.omx/` session artifacts as source-controlled policy.
- Do not invent database-backed storage, hosted portal behavior, or request-scoped ACL identity handling inside Phase 1 slices unless the user explicitly changes scope.

# Jira Analysis Reporting Module Contract

## Scope

Provide a deterministic Jira analysis workflow that turns normalized Jira Server issues into reviewable reports and Jira-plus-spec question payloads.

This module covers:

- Jira issue markdown reporting
- Jira updated-time filtering with explicit ISO window inputs
- Jira updated-time filtering by calendar date or exact ISO timestamp
- optional custom prompt templates
- Jira-plus-selected-spec retrieval payloads
- batch Jira-plus-selected-spec report payloads for filtered issues
- extractive draft answers grounded in retrieved Jira and spec evidence
- optional local LLM answer generation for explicit `mock` and `openai-compatible` backends (use LM Studio for local validation)
- optional Markdown file export for reports and answers
- fixture-backed and live Jira Server CLI paths

This module does not cover:

- hosted UI report rendering
- cloud-only LLM API execution
- semantic date parsing such as "last week" or "today"
- production index backends beyond the existing PageIndex-first retrieval path

## Inputs

- normalized Jira documents from `services.connectors.jira.connector`
- selected spec documents from a document corpus
- explicit ISO updated-time filters: `updated_from_iso` and `updated_to_iso`
- calendar-date filters via `updated_on_date`
- exact timestamp filters via `updated_at_iso`
- user questions for Jira-plus-spec QA
- optional prompt templates
- optional local LLM backend settings: `llm_backend`, `llm_model`, `llm_base_url`, and `llm_timeout_seconds`
- optional prompt mode settings: `strict`, `balanced`, or `exploratory`
- allowed ACL policies for retrieval

## Outputs

- Jira Markdown report payloads from `services/analysis/jira_issue_analysis.py`
- optional report files via `scripts/platform_cli.py jira-report --output-md ...`
- optional local LLM report summaries via `scripts/platform_cli.py jira-report --llm-backend ... --output-answer-md ...`
- Jira-plus-spec QA payloads with:
  - retrieved citations
  - `ai_prompt`
  - extractive `answer` by default
  - local-LLM `answer` when an explicit backend is configured
  - optional answer files via `scripts/platform_cli.py jira-spec-qa --output-answer-md ...`
- batch Jira-plus-spec report payloads via `scripts/platform_cli.py jira-batch-spec-report`

## Dependencies

- Jira normalization contract in `docs/jira-bug-field-mapping.md`
- Jira field alias contract in `packages/schema/jira-field-aliases.json`
- retrieval and citation contracts in `services/retrieval/*`
- analysis implementation in `services/analysis/jira_issue_analysis.py`
- local LLM backend abstraction in `services/analysis/llm_backends.py`
- unified CLI entrypoint in `scripts/platform_cli.py`

## KPIs

- report generation preserves canonical Jira bug fields
- time-window filtering returns only matching issues
- date and exact timestamp filtering return only matching issues
- QA retrieval returns both Jira and selected spec evidence when available
- generated prompts include deterministic evidence
- Markdown exports preserve the generated report or answer text
- local LLM answers remain tied to the same retrieved citation payload
- strict prompt mode prevents unsupported compliance or alignment claims
- live Jira CLI paths can be mock-validated without network access

## Implementation Steps

1. Normalize Jira source content.
   Reuse `load_source_payload(kind="jira", ...)` so fixture and live paths share the same canonical document shape.

2. Build issue reports.
   Use `summarize_jira_issue_markdown` and `build_jira_time_report` to preserve Jira fields, comments, and rendered markdown.

3. Build Jira-plus-spec QA payloads.
   Use `build_jira_spec_question_payload` to retrieve over the selected Jira issue plus selected spec documents.

4. Build batch Jira-plus-spec reports.
   Use `build_jira_batch_spec_report` to run the same QA workflow for each issue selected by the time filter.

5. Keep the default answer backend deterministic.
   Emit an extractive draft answer unless the caller explicitly selects a local LLM backend.

6. Expose through the unified CLI.
   Keep `jira-report`, `jira-spec-qa`, and `jira-batch-spec-report` JSON-first, with optional Markdown export flags for report and answer artifacts.

7. Keep local LLM execution opt-in.
   Support `--llm-backend none|openai-compatible`, with `mock` reserved for deterministic tests. Use LM Studio for local validation.

8. Make prompt strictness explicit.
   Default to `strict`; allow `balanced` and `exploratory` only through `--llm-prompt-mode`.

## Boundary Rules

- Do not call an LLM unless the caller explicitly sets `--llm-backend`.
- Do not make a local LLM answer replace citations or `ai_prompt`.
- Do not let non-strict prompt modes become the default for report generation.
- Do not fabricate evidence outside retrieved citations.
- Do not bypass ACL filtering for spec retrieval.
- Do not accept ambiguous natural-language time filters in this step; use explicit ISO windows, calendar dates, or exact ISO timestamps.
- Do not make report file writing the only output; JSON payloads must remain available for automation.

## Validation

Validation for this module is split into three layers.

### 1. Service validation

- `python -m unittest tests.analysis.test_jira_issue_analysis`

### 2. CLI validation

- `python -m unittest tests.ops.test_platform_cli`
- `python -m unittest tests.ops.test_platform_cli_live_orchestration`

### 3. Retrieval validation

- `python -m unittest tests.retrieval.test_hybrid_search`
- `python -m unittest tests.connectors.test_jira_sync`

## Current Validation Entry Points

- `python -m unittest tests.analysis.test_jira_issue_analysis`
- `python -m unittest tests.ops.test_platform_cli`
- `python -m unittest tests.ops.test_platform_cli_live_orchestration`

## Exit Criteria

- Jira reports can be generated from fixture and live Jira sources.
- Jira reports can be filtered by explicit ISO updated-time windows.
- Jira reports can be filtered by calendar date or exact ISO timestamp.
- Jira reports can be written to Markdown files.
- Jira reports can generate opt-in local LLM summaries while preserving the raw Markdown report.
- Jira-plus-spec QA payloads cite both Jira and selected spec evidence when query terms match both.
- Jira-plus-spec QA can write the extractive answer to Markdown.
- Jira-plus-spec QA can write an explicit local LLM answer to Markdown while preserving citations.
- Jira-plus-spec QA supports strict, balanced, and exploratory prompt modes.
- Batch Jira-plus-spec reports run QA for each issue selected by the time filter.
- All default outputs remain deterministic without a model dependency.

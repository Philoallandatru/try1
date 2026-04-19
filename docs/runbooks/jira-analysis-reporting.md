# Jira Analysis Reporting Runbook

Use this runbook to generate Jira reports and Jira-plus-spec analysis artifacts from
the unified platform CLI.

## Purpose

This workflow supports the current Jira analysis stage:

- pull normalized Jira issues from fixture or live Jira Server sources
- filter issues by explicit updated-time criteria
- generate Markdown Jira reports
- build Jira-plus-selected-spec QA payloads
- generate deterministic extractive answers from retrieved Jira and spec evidence
- optionally call a local LLM backend for final answer text
- write reviewable Markdown artifacts for handoff

The default answer backend is deterministic and evidence-only. Local LLM execution
is opt-in through `--llm-backend`.

## Preconditions

- Jira source data is available through one of:
  - `--jira-path` for local fixture payloads
  - `--jira-live --jira-base-url ... --jira-token ...` for live Jira Server
- The selected spec is already available in a normalized corpus JSON file.
- The command is run from the repository root.

## Generate A Time-Window Jira Report

```powershell
python scripts/platform_cli.py jira-report `
  --jira-path fixtures/connectors/jira/incremental_sync.json `
  --updated-from-iso 2026-04-05T09:00:00Z `
  --updated-to-iso 2026-04-05T10:00:00Z `
  --output-md .tmp/jira-report.md
```

Expected result:

- JSON output includes `markdown`, `prompt`, `issue_ids`, and `time_filter`.
- The Markdown report is written to `.tmp/jira-report.md`.
- Only Jira issues updated inside the inclusive ISO window are included.

## Generate A Jira Report Summary With A Local Model

Use the LLM answer as a summary layer, not as a replacement for the raw Markdown
report:

```powershell
python scripts/platform_cli.py jira-report `
  --jira-path fixtures/connectors/jira/incremental_sync.json `
  --updated-from-iso 2026-04-05T09:00:00Z `
  --updated-to-iso 2026-04-05T10:00:00Z `
  --llm-backend openai-compatible `
  --llm-model qwen-9b `
  --llm-base-url http://127.0.0.1:1234/v1 `
  --llm-prompt-mode strict `
  --output-md .tmp/jira-report.md `
  --output-answer-md .tmp/jira-report-answer.md
```

Expected result:

- `markdown` and `.tmp/jira-report.md` preserve the raw Jira issue report.
- `answer.mode` is `local-llm`.
- `answer.backend` is `openai-compatible`.
- `.tmp/jira-report-answer.md` contains the LM Studio model summary.
- `.tmp/jira-report-answer.md` contains the local-model summary.
- The prompt requires `Executive summary`, `Issue table`, and `Follow-up actions`.

## Generate A Date Or Exact-Timestamp Report

```powershell
python scripts/platform_cli.py jira-report `
  --jira-path fixtures/connectors/jira/full_sync.json `
  --updated-on-date 2026-04-05 `
  --output-md .tmp/jira-report-date.md
```

```powershell
python scripts/platform_cli.py jira-report `
  --jira-path fixtures/connectors/jira/incremental_sync.json `
  --updated-at-iso 2026-04-05T09:30:00Z `
  --output-md .tmp/jira-report-at.md
```

Use `--updated-on-date` for a whole UTC calendar date and `--updated-at-iso` for
an exact update timestamp match.

## Generate Jira-Plus-Spec QA

```powershell
python scripts/platform_cli.py jira-spec-qa `
  --jira-path fixtures/connectors/jira/incremental_sync.json `
  --jira-issue-id SSD-102 `
  --spec-corpus fixtures/retrieval/pageindex_corpus.json `
  --spec-document-id nvme-spec-v1 `
  --question "Does this issue relate to NVMe flush command evidence?" `
  --output-answer-md .tmp/jira-spec-answer.md
```

Expected result:

- JSON output includes `ai_prompt`, `retrieval`, and `answer`.
- `answer.mode` is `extractive`.
- Citations should include the selected Jira issue and selected spec when the
  query terms match both sources.
- The Markdown answer is written to `.tmp/jira-spec-answer.md`.

## Generate Jira-Plus-Spec QA With A Local Model

Use LM Studio (recommended for local validation):

```powershell
python scripts/platform_cli.py jira-spec-qa `
  --jira-path fixtures/connectors/jira/incremental_sync.json `
  --jira-issue-id SSD-102 `
  --spec-corpus fixtures/retrieval/pageindex_corpus.json `
  --spec-document-id nvme-spec-v1 `
  --question "Does this issue relate to NVMe flush command evidence?" `
  --llm-backend openai-compatible `
  --llm-model qwen-9b `
  --llm-base-url http://127.0.0.1:1234/v1 `
  --llm-prompt-mode strict `
  --output-answer-md .tmp/jira-spec-answer-llm.md
```

Expected result:

- `answer.mode` is `local-llm`.
- `answer.backend` is `openai-compatible`.
- `retrieval.citations` and `ai_prompt` remain present for audit.
- The LLM answer must be reviewed against the citations before sharing.

Prompt mode options for Jira reports and Jira-plus-spec QA:

- `strict`: default; requires direct evidence and tells the model to say evidence
  is insufficient rather than infer protocol compliance from similar topics.
- `balanced`: allows cautious engineering inference, but requires the answer to
  separate direct evidence from inference and call out missing evidence.
- `exploratory`: allows hypotheses for follow-up triage, but requires hypotheses
  to be labeled and blocks final compliance claims.

## Generate A Batch Jira-Plus-Spec Report

```powershell
python scripts/platform_cli.py jira-batch-spec-report `
  --jira-path fixtures/connectors/jira/incremental_sync.json `
  --updated-from-iso 2026-04-05T09:00:00Z `
  --updated-to-iso 2026-04-05T10:00:00Z `
  --spec-corpus fixtures/retrieval/pageindex_corpus.json `
  --spec-document-id nvme-spec-v1 `
  --question-template "Analyze Jira {jira_issue_id} against the selected spec." `
  --output-md .tmp/jira-batch-spec-report.md
```

Expected result:

- The report first summarizes all Jira issues selected by the time filter.
- Each selected issue gets an individual Jira-plus-spec QA section.
- Each QA section contains deterministic evidence and answer text. By default the
  answer is extractive; with `--llm-backend`, the answer comes from the selected
  local model backend.

## Live Jira Source

Replace `--jira-path ...` with live Jira flags:

```powershell
python scripts/platform_cli.py jira-report `
  --jira-live `
  --jira-base-url https://jira.example.com `
  --jira-token $env:JIRA_TOKEN `
  --updated-on-date 2026-04-05 `
  --output-md .tmp/live-jira-report.md
```

Do not print tokens in logs or commit generated reports that contain private Jira
content.

## Custom Prompts

For a single Jira report:

```powershell
python scripts/platform_cli.py jira-report `
  --jira-path fixtures/connectors/jira/incremental_sync.json `
  --updated-on-date 2026-04-05 `
  --prompt-template "Summarize these Jira issues for firmware triage:{summaries}"
```

For batch Jira-plus-spec QA, customize the per-issue question:

```powershell
python scripts/platform_cli.py jira-batch-spec-report `
  --jira-path fixtures/connectors/jira/incremental_sync.json `
  --updated-on-date 2026-04-05 `
  --spec-corpus fixtures/retrieval/pageindex_corpus.json `
  --spec-document-id nvme-spec-v1 `
  --question-template "For {jira_issue_id}, identify spec evidence and risk."
```

## Validation

Run these checks before publishing changes to this workflow:

```powershell
python scripts/gates/check_module_contracts.py
python -m unittest tests.gates.test_module_contracts tests.analysis.test_jira_issue_analysis tests.ops.test_platform_cli
python -m compileall docs scripts services tests
```

## Troubleshooting

- If no Jira issues are returned, verify the issue `updated` timestamp and the
  selected time filter.
- If spec citations are missing, verify `--spec-document-id` and query terms.
- If live Jira fails, first reproduce with `--jira-path` to isolate connector
  behavior from network or credential issues.
- If a Markdown output file is missing, verify the `--output-md` or
  `--output-answer-md` path and parent directory permissions.
- If a local model overstates the conclusion, retry with
  `--llm-prompt-mode strict` and inspect `ai_prompt` plus `retrieval.citations`.

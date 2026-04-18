# Portal Runner

The portal runner turns the static ops portal into a local web workbench for real-source smoke tests.

## Install

```powershell
uv pip install --python .\.venv\Scripts\python.exe -e ".[portal-runner]"
```

Linux:

```bash
uv pip install --python .venv/bin/python -e ".[portal-runner]"
```

## Configure

Copy the example config to the local ignored config path:

```powershell
New-Item -ItemType Directory -Force -Path .local\portal-runner
Copy-Item config\portal-runner.example.yaml .local\portal-runner\config.yaml
```

Linux:

```bash
mkdir -p .local/portal-runner
cp config/portal-runner.example.yaml .local/portal-runner/config.yaml
```

Edit `.local/portal-runner/config.yaml` with the real Jira and Confluence settings.

Do not commit `.local/portal-runner/config.yaml`. The `.local/` directory is ignored by git.

## Run

Local-only:

```powershell
python -m apps.portal_runner.server --host 127.0.0.1 --port 8787
```

LAN access:

```powershell
python -m apps.portal_runner.server --host 0.0.0.0 --port 8787
```

Open:

```text
http://127.0.0.1:8787
```

For LAN access, open `http://<server-ip>:8787` from another machine.

## Concise CLI Smoke Test

After the server is up, you can submit one real-data run without using the browser:

```powershell
python scripts/run_portal_runner_smoke.py `
  --base-url http://127.0.0.1:8787 `
  --runner-token "<runner-token>" `
  --pipeline jira_pdf_qa_smoke `
  --jira-issue-key SSD-102 `
  --confluence-scope page `
  --confluence-page-id 123456 `
  --spec-asset-id nvme-spec-mineru
```

If you want to upload a PDF instead of reusing a spec asset:

```powershell
python scripts/run_portal_runner_smoke.py `
  --base-url http://127.0.0.1:8787 `
  --runner-token "<runner-token>" `
  --pipeline full_real_data_smoke `
  --jira-issue-key SSD-102 `
  --confluence-page-id 123456 `
  --pdf fixtures/corpus/pdf/sample.pdf `
  --preferred-parser pypdf `
  --publish-wiki
```

The script prints a short summary and exits non-zero if the run finishes as `failed` or `cancelled`.

## Security

- `server.runner_token` is required when binding beyond localhost.
- Browser clients send `Authorization: Bearer <runner_token>` to `/api/*`.
- Jira and Confluence tokens stay in local config and are never returned by the API.
- PDF inputs are uploaded into `.tmp/portal-runner/uploads/<run_id>/`.
- The runner only executes code-registered pipeline IDs; YAML does not define arbitrary commands.

## Built-In Pipelines

- `jira_live_smoke`
- `confluence_live_smoke`
- `pdf_ingest_smoke`
- `jira_pdf_qa_smoke`
- `full_real_data_smoke`
- `profile_prompt_debug`

The portal displays each run with step status, duration, the latest log lines, and artifact links.

## Prompt Debug Workflow

Use `profile_prompt_debug` when the goal is to ask an LLM a debugging prompt over Jira plus selected knowledge sources.

Recommended flow:

1. Choose `Profile prompt debug` in the portal.
2. Enter a natural-language prompt, for example `Debug this Jira issue using firmware knowledge and cite relevant evidence.`
3. Optionally enter a Jira issue key.
4. Optionally select a Confluence page, page tree, or space slice.
5. Optionally select a reusable spec asset or upload a PDF.
6. Submit the run.

The runner creates a registry-backed workspace for the run:

- `workspace.yaml`
- `sources/*.yaml`
- `selectors/*.yaml`
- `profiles/*.yaml`
- cached source payloads
- normalized documents
- PageIndex artifacts
- a prompt-query artifact

The LLM backend comes from `llm:` in the runner config, unless a mock response is supplied in the form.

## Jira QA Workflow

Use `jira_pdf_qa_smoke` when the goal is to test Jira QA over a small Confluence slice plus NVMe spec evidence.

Recommended flow:

1. Run `pdf_ingest_smoke` once with `preferred_parser: mineru` or `auto` and set a stable asset id such as `nvme-spec-mineru`.
2. On later runs, select that reusable spec asset instead of uploading the same PDF again.
3. Select a small Confluence scope:
   - `Single page`
   - `Page IDs`
   - `Page tree`
   - `Space slice`
4. Run `jira_pdf_qa_smoke` with the target Jira issue key.

This avoids reparsing the NVMe PDF with MinerU for every QA iteration.

## vLLM Configuration

The runner can call a vLLM server through its OpenAI-compatible API:

```yaml
llm:
  backend: "vllm"
  model: "Qwen/Qwen2.5-7B-Instruct"
  base_url: "http://localhost:8000/v1"
  api_key: null
  timeout_seconds: 120
```

When `llm.backend` is `vllm`, `llm.model` and `llm.base_url` are required.

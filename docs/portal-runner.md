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

The portal displays each run with step status, duration, the latest log lines, and artifact links.

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

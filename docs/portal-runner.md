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

## Product Portal

The runner now serves the React product portal from `apps/portal_web/dist` when that build output exists.
The legacy static ops portal remains available at:

```text
http://127.0.0.1:8787/admin/
```

Develop the React portal separately with Vite:

```powershell
cd apps\portal_web
npm install
npm run dev
```

Build it for runner hosting:

```powershell
cd apps\portal_web
npm run build
```

The product portal is organized around user-facing modules:

- `Analyze`: issue key, analysis profile, and run action.
- `Sources`: Jira and Confluence source setup, test, and refresh.
- `Profiles`: named analysis profile creation and validation.
- `Runs`: analysis history and result review.
- `Wiki`, `Reports`, and `Spec Lab`: extension surfaces for generated artifacts and spec evidence.

The root page must stay focused on Analyze Jira Issue. Raw runner forms, command previews, and technical inspection panels belong under `/admin/`.

## Demo Workspace

`GET /api/workspaces` bootstraps a `demo` workspace under the configured workspace root.
The demo workspace includes fixture-backed Jira and Confluence sources:

- `demo_jira`
- `demo_confluence`
- `demo_jira_project`
- `demo_confluence_space`

The fixture content lives under `fixtures/demo/`.

The demo profile is created only when `nvme-spec-mineru` is available as a MinerU-parsed reusable spec asset. If the asset is missing or was not parsed with MinerU, the workspace entry returns `setup_required: true` and `missing_spec_asset: "nvme-spec-mineru"`. The demo path does not fabricate spec evidence or fall back to `pypdf`.

## Product APIs

The product portal uses thin wrappers over the existing workspace services:

- `GET /api/workspaces`
- `POST /api/workspaces`
- `GET /api/workspace/status?workspace_dir=...`
- `GET /api/workspace/sources?workspace_dir=...`
- `POST /api/workspace/sources`
- `PATCH /api/workspace/sources/{name}`
- `POST /api/workspace/sources/{name}/test`
- `POST /api/workspace/sources/{name}/refresh`
- `GET /api/workspace/selectors?workspace_dir=...`
- `POST /api/workspace/selectors`
- `GET /api/workspace/selectors/{name}?workspace_dir=...`
- `GET /api/workspace/profiles?workspace_dir=...`
- `POST /api/workspace/profiles`
- `GET /api/workspace/profiles/{name}?workspace_dir=...`
- `PATCH /api/workspace/profiles/{name}`
- `POST /api/workspace/profiles/{name}/duplicate`
- `POST /api/workspace/profiles/{name}/validate`
- `POST /api/workspace/profiles/{name}/default`
- `GET /api/workspace/spec-assets?workspace_dir=...`
- `GET /api/workspace/spec-assets/{asset_id}/require-mineru?workspace_dir=...`
- `POST /api/workspace/spec-assets/ingest`
- `GET /api/workspace/runs?workspace_dir=...`
- `GET /api/workspace/runs/{run_id}?workspace_dir=...`
- `GET /api/workspace/runs/{run_id}/artifacts/{artifact_type}?workspace_dir=...`
- `POST /api/workspace/runs/{run_id}/verify-llm`

`POST /api/workspace/analyze-jira` still uses the existing workspace analysis path, but also returns a product-shaped response with summary, sections, citations, evidence sources, artifacts, and portal state.

Profiles can carry `inputs.spec_assets` via `spec_asset_ids`, plus `analysis.llm_backend`, `analysis.llm_model`, `analysis.llm_base_url`, `analysis.top_k`, and `analysis.llm_prompt_mode`. The product portal defaults the local acceptance path to LM Studio's OpenAI-compatible API at `http://127.0.0.1:1234/v1` with model `qwen-9b`; deterministic tests may still switch a copied profile to `none` to avoid requiring a local model.

### Local LLM Verification

Use `verify-run-llm` to validate a completed deep-analysis run with a local model without re-running the entire section pipeline through the LLM:

```powershell
python scripts/workspace_cli.py verify-run-llm .tmp\portal-runner\workspaces\demo <run-id> `
  --llm-backend openai-compatible `
  --llm-model qwen-9b `
  --llm-base-url http://127.0.0.1:1234/v1 `
  --llm-timeout-seconds 600
```

The command writes `llm_verification.json` into the run directory and registers it as an `llm_verification` artifact in `run_manifest.json`. This verification path is intentionally compact: it asks the local LLM to assess the completed deep-analysis result, citation inventory, section outputs, gaps, and next actions in one call.

The product portal exposes the same path from the `Runs` page with `Verify with LM Studio qwen-9b`. The `Analyze` page also shows a four-item setup checklist for Jira Source, Confluence Source, NVMe Spec Asset, and Analysis Profile.

The `Runs` page can also rerun a completed analysis using the same workspace, issue key, and profile recorded in the run manifest. The `Sources` page displays the source setup path as a lightweight stepper: Source Details -> Authentication -> Selector -> Test -> Fetch.

## Browser E2E

Run the full product portal browser smoke from an empty workspace:

```powershell
python scripts\run_portal_web_e2e.py
```

The script starts local fake Jira and Confluence HTTP services, starts the portal runner, drives the React UI with Playwright, creates a workspace, configures both sources through the source wizard, tests and fetches connector data, creates a profile, runs analysis, opens the run, and verifies the result through LM Studio `qwen-9b`. Use `--skip-llm-verify` when LM Studio is not running and you only need to validate the browser setup/analyze path.

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

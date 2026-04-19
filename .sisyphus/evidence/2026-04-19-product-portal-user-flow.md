# Product Portal User Flow Evidence

## Scope

Implemented the first product-facing slice for the SSD Knowledge Portal:

- Product API wrappers for workspace, sources, profiles, workspace runs, artifacts, and product-shaped Jira analysis responses.
- A zero-start API integration test that creates a workspace, configures Jira and Confluence live sources against a local HTTP fake server, refreshes both sources, creates a profile, validates it, and runs analysis.
- A new React/Vite/TypeScript portal under `apps/portal_web`.
- Root static hosting for the React build, with the legacy ops portal moved to `/admin/`.
- A storage race fix that preserves `cancel_requested` when background run writes race with cancel requests.

## Commands Run

```powershell
python -m unittest tests.portal.test_portal_runner.PortalRunnerTest.test_product_api_supports_zero_start_source_profile_and_analyze_workflow -v
```

Result: passed.

```powershell
python -m unittest tests.portal.test_portal_runner -v
```

Result: passed, 17 tests.

```powershell
python -m unittest tests.workspace.test_source_registry -v
```

Result: passed, 8 tests.

```powershell
cd apps\portal_web
npm install
npm run typecheck
npm run build
```

Result: dependencies installed, typecheck passed, production build passed.

```powershell
python scripts/gates/check_repo_shape.py
python scripts/gates/check_module_contracts.py
python -m compileall apps scripts services tests
```

Result: repo shape passed, module contract passed, compileall passed.

## Notes

- The fake Jira/Confluence test uses local HTTP endpoints and the live connector path, not direct fixture reads.
- Frontend build output and `node_modules` are ignored; source files and lockfile are the durable frontend artifacts.
- `GET /api/workspace/sources` now returns selectors beside sources so the UI can refresh exact named selectors instead of guessing selector names.
- Source rows now include user-facing status fields: `status`, `status_reason`, `last_refresh`, `document_count`, `enabled`, and the associated selector.
- `GET /api/workspace/sources/{name}` returns the same redacted source detail shape for edit/detail screens.
- The React Sources page now displays source status/document counts and provides Test/Refresh actions using exact selector names.
- The React Profiles page now lets users Validate and Set default without CLI.
- `GET /api/workspace/profiles/{name}` and `POST /api/workspace/profiles/{name}/duplicate` now support profile detail and duplication.
- The React Profiles page exposes Duplicate from the profile list.
- The React Profiles page defaults local model settings to LM Studio OpenAI-compatible API: `llm_backend=openai-compatible`, `llm_model=qwen-9b`, `llm_base_url=http://127.0.0.1:1234/v1`.
- `GET /api/workspace/spec-assets/{asset_id}/require-mineru` rejects non-MinerU NVMe spec assets; `POST /api/workspace/spec-assets/ingest` forces `preferred_parser="mineru"`.
- `GET /api/workspaces` now bootstraps a fixture-backed `demo` workspace with demo Jira/Confluence sources and selectors.
- Demo workspace does not create a demo analysis profile unless `nvme-spec-mineru` is available and parsed by MinerU; missing spec returns `setup_required` instead of fake evidence.
- Demo Jira and Confluence fixture payloads were added under `fixtures/demo/` and verified with existing connector loaders.
- When a MinerU `nvme-spec-mineru` asset already exists in the demo workspace, `GET /api/workspaces` now marks demo as ready and bootstraps `demo_nvme_default`.
- `scripts/workspace_cli.py analyze-jira .tmp\portal-runner\workspaces\demo --profile demo_nvme_default --issue-key SSD-DEMO-A` was run after the MinerU asset was present. The profile-scoped snapshot included `spec_asset:nvme-spec-mineru`, `document_count: 12`, and `page_index_count: 593`; the top retrieval result came from the NVMe PDF with `parser: mineru`.
- `python scripts\workspace_cli.py smoke-deep-analysis .tmp\portal-runner\workspaces\demo --profile demo_nvme_default --issue-key SSD-DEMO-A --llm-backend none --portal-state-output .tmp\portal-runner\workspaces\demo\portal_state_extract.json` generated a completed deep-analysis run at `.tmp\portal-runner\workspaces\demo\runs\20260419T085242412821Z-dd95f0d1-workspace-deep-analyze`.
- `python scripts\workspace_cli.py verify-run-llm .tmp\portal-runner\workspaces\demo 20260419T085242412821Z-dd95f0d1-workspace-deep-analyze --llm-backend ollama --llm-model qwen3.5:4b --llm-base-url http://127.0.0.1:11434 --llm-timeout-seconds 600` completed in 115.5 seconds and wrote `.tmp\portal-runner\workspaces\demo\runs\20260419T085242412821Z-dd95f0d1-workspace-deep-analyze\llm_verification.json`.
- The local LLM verification used `backend: ollama` and returned verdict `Analysis is inconclusive due to lack of empirical evidence`, with the concrete gap that the shared retrieval bundle had `confluence.result_count: 0` and `pdf.result_count: 5`.
- The React Analyze page now exposes a four-item setup checklist for Jira Source, Confluence Source, NVMe Spec Asset, and Analysis Profile, with direct navigation to the relevant setup page.
- The React Runs page now exposes `Verify with LM Studio qwen-9b`, which calls `POST /api/workspace/runs/{run_id}/verify-llm`, then displays the persisted `llm_verification` artifact.
- The React Runs page now supports `Rerun same issue/profile` by reading the selected run detail manifest and calling the existing analyze endpoint with the recorded `issue_key` and `profile`.
- The React Sources page now displays a lightweight stepper for `Source Details -> Authentication -> Selector -> Test -> Fetch`, driven by the current source form and source cache state.
- `POST /api/workspace/runs/{run_id}/verify-llm` was covered through the product API zero-start test with a deterministic mock backend; the frontend now targets LM Studio `qwen-9b` for future local verification.
- The same product API zero-start test now asserts that run-detail exposes `input_config.issue_key` and `input_config.profile`, and that rerunning through `/api/workspace/analyze-jira` creates a new run id.
- LM Studio at `http://127.0.0.1:1234/v1` was checked through `/v1/models`; it returned model `qwen-9b`. A real `verify-run-llm` call with `--llm-backend openai-compatible --llm-model qwen-9b --llm-base-url http://127.0.0.1:1234/v1` completed in 37.2 seconds and wrote a new `llm_verification` artifact with `backend: openai-compatible`.
- Playwright frontend closed-loop test passed against `http://127.0.0.1:8797`: it loaded the product portal, confirmed the four-item setup checklist, confirmed the Sources stepper, opened Runs, clicked `Rerun same issue/profile`, clicked `Verify with LM Studio qwen-9b`, and observed `openai-compatible / local-llm-verification` plus `Verdict` in the browser.
- Playwright screenshot: `.tmp/playwright-portal/frontend-closed-loop.png`.
- The React result and run detail views now include an Evidence Coverage panel. A Playwright browser test confirmed the Runs page shows `Evidence Coverage`, `Confluence: 0 hits`, `Spec: 5 hits`, `Missing evidence: confluence`, and the LM Studio verdict heading.
- Playwright evidence screenshot: `.tmp/playwright-portal/frontend-evidence-coverage.png`.
- The React Runs detail view now uses tabs for `Summary`, `RCA`, `Spec Impact`, `Decision Brief`, `Evidence`, `Verification`, and `Artifacts`. A Playwright browser test confirmed switching RCA, Spec Impact, Verification, and Artifacts tabs, including visibility of `deep_analysis_result` and `llm_verification` artifact rows.
- Playwright run-tabs screenshot: `.tmp/playwright-portal/frontend-run-tabs.png`.
- The React Sources page now uses a real wizard instead of a single always-visible form. The browser flow confirmed Source Details -> Authentication -> Selector -> Save source and selector -> Test step visibility.
- The wizard now advances from Test to Fetch after a successful connection test and exposes `Add another source` from the Fetch step, so users can configure Jira and Confluence back-to-back without leaving the page.
- Playwright sources-wizard screenshot: `.tmp/playwright-portal/frontend-sources-wizard.png`.
- `scripts/run_portal_web_e2e.py` now runs a full zero-start browser workflow with local fake Jira and Confluence HTTP servers. It creates a new workspace from the UI, seeds a minimal MinerU-marked `nvme-spec-mineru` test asset, creates Jira and Confluence sources through the wizard, tests and fetches both sources through connector HTTP paths, creates a profile, runs analysis, opens Runs, and verifies with LM Studio `qwen-9b`.
- `python scripts\run_portal_web_e2e.py` completed with `PORTAL_WEB_ZERO_START_E2E_OK`, including LM Studio `qwen-9b` verification.
- Zero-start E2E screenshot: `.tmp/portal-web-zero-start-e2e/zero-start-browser-e2e.png`.
- Manifest writes use atomic replace with a storage lock and short Windows retry to avoid cancel/runner poll races corrupting or overwriting run state.
- Local demo acceptance with `nvme-spec-mineru` has now run through LLM verification. The active frontend/browser path now uses LM Studio `qwen-9b` through `http://127.0.0.1:1234/v1`; real Jira/Confluence endpoint acceptance still needs credentials and live endpoint configuration.

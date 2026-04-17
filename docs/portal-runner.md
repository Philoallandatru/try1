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
- `full_real_data_smoke`

The portal displays each run with step status, duration, the latest log lines, and artifact links.

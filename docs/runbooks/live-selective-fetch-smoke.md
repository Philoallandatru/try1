# Live Selective Fetch Smoke Runbook

Use this runbook to validate the new selective Jira and Confluence live-fetch path
through the unified CLI.

## Purpose

This workflow is for the narrow question:

- can the live connector authenticate?
- can it fetch only the requested Jira issue or Confluence page?
- can it include or exclude comments/attachments/image metadata as expected?
- can it optionally download image binaries when explicitly enabled?

This runbook does not validate retrieval quality, local LLM behavior, or portal
rendering. It is only for connector smoke testing.

## Preconditions

- Run from the repository root.
- Use the experimental backend explicitly:
  - `--fetch-backend atlassian-api`
- Have valid credentials:
  - Jira Server or Jira Cloud token / password flow
  - Confluence token / password flow
- If testing image download, create or choose a writable local directory.

## Selector Rules

- Selective flags are only valid on `atlassian-api` backend.
- Jira helper filters cannot be mixed with raw `--jql`.
- Confluence helper filters cannot be mixed with raw `--cql`.
- `--download-images` requires `--image-download-dir`.

## Jira Smoke Commands

### 1. Exact issue fetch

```powershell
python scripts/platform_cli.py connector jira `
  --live `
  --base-url https://jira.example.com `
  --token $env:JIRA_TOKEN `
  --fetch-backend atlassian-api `
  --issue-key SSD-777
```

Expected result:

- exit code `0`
- JSON contains one document with `document_id == "SSD-777"` when the issue exists
- `selector_summary.fetch_backend == "atlassian-api"`
- `selector_summary.issue_key == "SSD-777"`

### 2. Narrow query fetch without comments

```powershell
python scripts/platform_cli.py connector jira `
  --live `
  --base-url https://jira.example.com `
  --token $env:JIRA_TOKEN `
  --fetch-backend atlassian-api `
  --project-key SSD `
  --issue-type Bug `
  --updated-from 2026-04-01T00:00:00Z `
  --updated-to 2026-04-10T00:00:00Z `
  --no-include-comments
```

Expected result:

- exit code `0`
- returned documents are bounded to the selected time window and filters
- documents still normalize into canonical output
- comments are empty or omitted from the effective builder input

### 3. Exact issue with image download

```powershell
python scripts/platform_cli.py connector jira `
  --live `
  --base-url https://jira.example.com `
  --token $env:JIRA_TOKEN `
  --fetch-backend atlassian-api `
  --issue-key SSD-777 `
  --download-images `
  --image-download-dir .tmp\jira-images
```

Expected result:

- exit code `0`
- image attachments keep URL metadata
- downloaded image files appear under `.tmp\jira-images`
- image assets still normalize into markdown evidence blocks

## Confluence Smoke Commands

### 1. Exact page fetch

```powershell
python scripts/platform_cli.py connector confluence `
  --live `
  --base-url https://confluence.example.com `
  --token $env:CONF_TOKEN `
  --fetch-backend atlassian-api `
  --page-id 123456
```

Expected result:

- exit code `0`
- JSON contains one document for page `123456` when the page exists
- `selector_summary.page_id == "123456"`

### 2. Narrow page query by space and label

```powershell
python scripts/platform_cli.py connector confluence `
  --live `
  --base-url https://confluence.example.com `
  --token $env:CONF_TOKEN `
  --fetch-backend atlassian-api `
  --space-key SSDENG `
  --label firmware `
  --modified-from 2026-04-01T00:00:00Z
```

Expected result:

- exit code `0`
- returned pages are bounded to the selected space/label/time filter
- attachments and inline image mapping still normalize cleanly

### 3. Exact page with image download

```powershell
python scripts/platform_cli.py connector confluence `
  --live `
  --base-url https://confluence.example.com `
  --token $env:CONF_TOKEN `
  --fetch-backend atlassian-api `
  --page-id 123456 `
  --download-images `
  --image-download-dir .tmp\confluence-images
```

Expected result:

- exit code `0`
- image files appear under `.tmp\confluence-images`
- canonical markdown still contains image evidence blocks

## Snapshot Smoke Commands

### 1. Dual-source selective profile

Use the included example profile:

- [selective_live_multi_sync_profile.json](C:\Users\10259\Documents\code\codex\codex-try\fixtures\ops\selective_live_multi_sync_profile.json)

```powershell
python scripts/platform_cli.py multi-sync-health `
  --profile fixtures\ops\selective_live_multi_sync_profile.json `
  --snapshot-dir .tmp\selective-live-snapshot
```

Expected result:

- snapshot refresh succeeds
- only the selected Jira issue and selected Confluence page are ingested
- `ops_health` still reports against the refreshed snapshot

## Troubleshooting

### 401 or 403

Check in this order:

1. `--base-url` points to the correct Jira/Confluence host
2. token is valid for that host
3. auth mode matches the environment
4. the selected issue/page is visible to the authenticated user

### The command returns too much data

Check in this order:

1. confirm `--fetch-backend atlassian-api` is present
2. confirm you used helper selectors instead of raw `--jql`/`--cql`
3. if using raw `--jql` or `--cql`, verify the query itself is narrow enough

### Attachments or images are missing

Check in this order:

1. verify `--no-include-attachments` is not set
2. verify the page or issue actually has attachment visibility for the current user
3. for Confluence inline images, verify the image is backed by an attachment that the page body references by filename

### `--download-images` succeeds but no files appear

This should now fail early unless `--image-download-dir` is provided. If you still
see no files:

1. verify the target directory is writable
2. verify the attachment is actually an image media type
3. verify the authenticated user can download the attachment binary

## Validation

After changing this path, run:

```powershell
python -m unittest tests.connectors.test_jira_atlassian_api_fetch tests.connectors.test_live_connectors tests.ops.test_profile_module tests.ops.test_platform_cli_live_orchestration
python -m compileall docs scripts services tests
```

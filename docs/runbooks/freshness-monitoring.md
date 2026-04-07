# Freshness Monitoring Runbook

## Purpose

Validate that incremental Jira and Confluence changes become visible within the agreed internal sync budget.

## Inputs

- Connector incremental sync fixtures or live sync metadata
- Local snapshot directory containing `manifest.json` and `page_index.json`
- Latest `ops-health` output from fixture mode or snapshot mode
- Sync budget threshold for the pilot

## Boundary

This runbook validates freshness against the Phase 1 local snapshot only.

It does not cover:

- database-backed index freshness
- scheduler orchestration
- request-scoped identity freshness views

## Procedure

1. Prefer the sequential `sync-health` path when the source payload still needs to be applied to the snapshot.
2. If the snapshot is already current, run `python scripts/platform_cli.py ops-health --snapshot-dir <snapshot-dir>`.
3. Capture the reported `last_sync`, `lag_minutes`, and `status` for each source.
4. Compare each lag against the configured freshness budget.
5. Mark the source unhealthy if the lag exceeds the budget.
6. Record the result under `.sisyphus/evidence/`.

## Reference Commands

```bash
python scripts/retrieval/snapshot_cli.py create --snapshot-dir .tmp/snapshot --corpus fixtures/retrieval/pageindex_corpus.json
python scripts/retrieval/snapshot_cli.py refresh --snapshot-dir .tmp/snapshot --sync-payload fixtures/connectors/jira/incremental_sync.json --source-name jira
python scripts/platform_cli.py ops-health --snapshot-dir .tmp/snapshot --reference-time-iso 2026-04-06T09:10:00Z
python scripts/platform_cli.py sync-health jira fixtures/connectors/jira/incremental_sync.json --snapshot-dir .tmp/snapshot --reference-time-iso 2026-04-06T09:10:00Z
python scripts/platform_cli.py multi-sync-health --snapshot-dir .tmp/snapshot --jira-path fixtures/connectors/jira/incremental_sync.json --confluence-path fixtures/connectors/confluence/incremental_sync.json --reference-time-iso 2026-04-06T09:10:00Z
python scripts/platform_cli.py multi-sync-health --profile fixtures/ops/multi_sync_health_profile.json --snapshot-dir .tmp/snapshot
```

## Validation

- `ops-health` returns `freshness.sources[*].status`.
- Jira source reports a healthy freshness status when its lag is within budget.
- Confluence source reports a healthy freshness status when its lag is within budget.
- The lag for each source is within the agreed budget.

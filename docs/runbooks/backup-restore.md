# Backup and Restore Runbook

## Purpose

Verify that the Phase 1 knowledge platform can produce a recoverable snapshot and validate restore readiness for the pilot.

## Inputs

- Latest local snapshot metadata
- Snapshot directory containing `manifest.json`, `documents.json`, and `page_index.json`
- Restore target environment identifier
- Reference corpus and retrieval evaluation baseline

## Boundary

This runbook covers Phase 1 file-backed snapshot recovery only.

It does not cover:

- object storage replication
- database restore
- hosted portal failover

## Procedure

1. Produce or locate the latest local snapshot using `snapshot_cli.py` or the sequential `sync-health` path.
2. Record the snapshot timestamp and storage location from `manifest.json`.
3. Restore the snapshot into the designated pilot restore environment by copying the snapshot directory intact.
4. Run `python scripts/platform_cli.py ops-health --snapshot-dir <snapshot-dir>` against the restored snapshot.
5. Re-run baseline retrieval checks or smoke validations against the restored environment.
6. Mark restore validation successful only if the restored snapshot behaves consistently with the baseline.

## Reference Commands

```bash
python scripts/retrieval/snapshot_cli.py create --snapshot-dir .tmp/snapshot --corpus fixtures/retrieval/pageindex_corpus.json
python scripts/retrieval/snapshot_cli.py show --snapshot-dir .tmp/snapshot
python scripts/platform_cli.py ops-health --snapshot-dir .tmp/snapshot
python scripts/platform_cli.py sync-health jira fixtures/connectors/jira/incremental_sync.json --snapshot-dir .tmp/snapshot --reference-time-iso 2026-04-06T09:10:00Z
python scripts/platform_cli.py multi-sync-health --snapshot-dir .tmp/snapshot --jira-path fixtures/connectors/jira/incremental_sync.json --confluence-path fixtures/connectors/confluence/incremental_sync.json --reference-time-iso 2026-04-06T09:10:00Z
python scripts/retrieval/toolkit_cli.py search "flush command" --corpus .tmp/snapshot/documents.json
```

## Validation

- A local snapshot directory exists and is locatable.
- `manifest.json`, `documents.json`, and `page_index.json` are all present.
- The restore environment is identified and reachable.
- `ops-health` reports backup `healthy` and restore `validated`.
- Restore validation is explicitly recorded.
- Evidence is stored under `.sisyphus/evidence/`.

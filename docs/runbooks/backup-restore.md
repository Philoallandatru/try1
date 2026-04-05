# Backup and Restore Runbook

## Purpose

Verify that the Phase 1 knowledge platform can produce a recoverable snapshot and validate restore readiness for the pilot.

## Inputs

- Latest backup snapshot metadata
- Restore target environment identifier
- Reference corpus and retrieval evaluation baseline

## Procedure

1. Produce or locate the latest platform backup archive.
2. Record the backup timestamp and storage location.
3. Restore the snapshot into the designated pilot restore environment.
4. Re-run baseline retrieval checks or smoke validations against the restored environment.
5. Mark restore validation successful only if the restored snapshot behaves consistently with the baseline.

## Validation

- A backup artifact exists and is locatable.
- The restore environment is identified and reachable.
- Restore validation is explicitly recorded.
- Evidence is stored under `.sisyphus/evidence/`.


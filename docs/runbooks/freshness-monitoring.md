# Freshness Monitoring Runbook

## Purpose

Validate that incremental Jira and Confluence changes become visible within the agreed internal sync budget.

## Inputs

- Connector incremental sync fixtures or live sync metadata
- Latest portal or ops health snapshot
- Sync budget threshold for the pilot

## Procedure

1. Capture the latest `last_sync` timestamp for Jira and Confluence sources.
2. Compute lag against the current execution timestamp or reference snapshot.
3. Compare each lag against the configured freshness budget.
4. Mark the source unhealthy if the lag exceeds the budget.
5. Record the result under `.sisyphus/evidence/`.

## Validation

- Jira source reports a healthy freshness status.
- Confluence source reports a healthy freshness status.
- The lag for each source is within the agreed budget.


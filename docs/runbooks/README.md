# Runbooks

Runbooks for pilot operations, recovery, rollout gates, and production support.

Current Phase 1 runbooks are based on local file-backed snapshots and unified CLI checks.

Available runbooks:

- [Backup and restore](backup-restore.md)
- [Freshness monitoring](freshness-monitoring.md)
- [Jira analysis reporting](jira-analysis-reporting.md)

They do not yet assume:

- database-backed persistence
- hosted control plane operations
- identity-aware recovery flows

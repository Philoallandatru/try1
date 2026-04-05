# Phase 1 Rollout Gate

## Purpose

Determine whether the SSD knowledge platform is ready for the Phase 1 internal pilot.

## Gate Inputs

- Retrieval evaluation report
- Freshness health report
- Backup and restore validation status
- Portal operator smoke status

## Gate Criteria

- Retrieval thresholds pass.
- Freshness checks remain within budget.
- Backup and restore checks are healthy and validated.
- Portal search and citation inspection are available.

## Execution

Run:

```bash
python scripts/gates/run_phase1_gate.py
```

## Success

The rollout gate passes only when all checks return healthy status.


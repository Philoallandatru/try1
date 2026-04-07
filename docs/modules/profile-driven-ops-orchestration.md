# Profile Driven Ops Orchestration Module Contract

## Scope

Provide a reusable profile format for `multi-sync-health` so multi-source operational refresh can be configured outside the command line without changing snapshot, retrieval, or health contracts.

This module covers:

- profile-backed configuration for Jira and Confluence source orchestration
- CLI override rules on top of profile values
- stable fixture examples for local deterministic operations
- validation of profile-driven multi-source refresh into a shared snapshot

This module does not cover:

- secret storage or secret encryption
- database-backed orchestration
- scheduler or workflow automation
- hosted control plane management

## Inputs

- JSON profile files for `multi-sync-health`
- optional CLI overrides for:
  - `snapshot_dir`
  - source fixture paths
  - live flags
  - source credentials and base URLs
  - freshness budget
  - reference time
- canonical connector outputs from Jira and Confluence

## Outputs

- profile-backed `multi-sync-health` execution
- merged source configuration with CLI-over-profile precedence
- shared snapshot refresh results across multiple sources
- aggregated `ops-health` output after sequential refresh
- reusable fixture profile example under `fixtures/ops/`

## Dependencies

- unified CLI in `scripts/platform_cli.py`
- local snapshot persistence contract
- Jira and Confluence connector contracts
- ops health contract
- runbook and CLI reference documentation

## KPIs

- profile execution success rate
- CLI override correctness rate
- multi-source refresh consistency rate
- documentation parity between profile schema and CLI behavior

## Implementation Steps

1. Keep the profile format minimal.
   Only include fields already supported by `multi-sync-health`.

2. Preserve CLI compatibility.
   Adding profile support must not break existing explicit-flag usage.

3. Define merge precedence clearly.
   CLI values override profile values.
   Profile values override built-in defaults.

4. Keep source configuration explicit.
   The profile must keep Jira and Confluence separated rather than introducing a generic plugin system.

5. Reuse existing connector and snapshot seams.
   The profile layer only selects configuration. It must not reshape connector payloads.

6. Add deterministic fixture coverage.
   Include at least one fixture profile for dual-source local validation.

7. Validate live-path compatibility with mocks.
   Confirm profile support does not regress live dual-source orchestration.

## Boundary Rules

- Do not invent a new secret-management layer in this step.
- Do not add a generic scheduler abstraction in this step.
- Do not let profile parsing change connector, snapshot, or ops-health contracts.
- Do not allow profile defaults to silently override explicit CLI values.

## Validation

### Structural validation

- `python -m compileall docs fixtures scripts tests`
- module contract gate must include this module

### Behavioral validation

- execute `multi-sync-health` with a fixture profile only
- execute `multi-sync-health` with a fixture profile plus CLI snapshot override
- confirm both sources refresh into the same snapshot

### Live compatibility validation

- keep live dual-source orchestration test passing under mocked connector fetches

## Current Validation Entry Points

- `python -m unittest tests.ops.test_platform_cli`
- `python -m unittest tests.ops.test_platform_cli_live_orchestration`
- `python scripts/gates/check_module_contracts.py`
- `python scripts/platform_cli.py multi-sync-health --profile fixtures/ops/multi_sync_health_profile.json --snapshot-dir .tmp/snapshot`

## Exit Criteria

- profile-backed `multi-sync-health` works with fixture sources
- CLI override precedence is validated
- live dual-source orchestration still passes with mocks
- profile schema and docs are consistent with actual CLI behavior

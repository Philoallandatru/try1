# Skill Extraction Plan

## Purpose

This document defines how to convert the current reusable Phase 1 components into standalone skills without mixing project-specific policy into general-purpose capabilities.

## Extraction Strategy

The current repository already has stable reusable seams:

- governance and contract validation
- document normalization
- retrieval and citation
- evaluation and rollout checks

These seams should become separate skills with small, stable entrypoints.

## Candidate Skill 1: Contract Guard

### Scope

Validate repository governance and implementation contracts.

### Inputs

- ADR files
- module contract files
- repo structure

### Entrypoints

- `scripts/gates/check_adr_contract.py`
- `scripts/gates/check_repo_shape.py`
- `scripts/gates/check_module_contracts.py`

### Extraction Notes

- remove SSD-specific file names only if a target project uses different naming
- keep required-heading checks configurable

## Candidate Skill 2: Offline Document Normalizer

### Scope

Normalize Markdown, Office, and PDF sources into a structure-preserving evidence format.

### Inputs

- local files
- file type indicator

### Entrypoints

- `scripts/platform_cli.py ingest markdown ...`
- `scripts/platform_cli.py ingest docx ...`
- `scripts/platform_cli.py ingest xlsx ...`
- `scripts/platform_cli.py ingest pptx ...`
- `scripts/platform_cli.py ingest pdf ...`

### Extraction Notes

- expose normalized JSON as the portable output
- keep schema-specific naming in config or docs, not hard-coded project assumptions

## Candidate Skill 3: Grounded Retrieval Toolkit

### Scope

Build page-level indexes, run hybrid search, and produce citations and source inspection payloads.

### Inputs

- normalized corpus snapshot
- search query
- allowed ACL policies

### Entrypoints

- `scripts/platform_cli.py search ...`
- `scripts/platform_cli.py citation ...`

### Extraction Notes

- keep authority weighting configurable
- keep ACL behavior strict and visible in the contract

## Candidate Skill 4: Retrieval Quality Gate

### Scope

Evaluate retrieval quality and gate release readiness.

### Inputs

- corpus snapshot
- gold-set dataset
- threshold config
- ops health snapshot

### Entrypoints

- `scripts/platform_cli.py eval`
- `scripts/platform_cli.py gate`
- `scripts/platform_cli.py ops-health`

### Extraction Notes

- keep metric and threshold configuration external
- separate generic eval logic from SSD-specific pilot defaults

## Packaging Guidance

- one skill per capability family
- each skill should point to a single human-friendly entrypoint
- prefer CLI-friendly JSON outputs
- keep contracts and examples close to the skill
- avoid bundling portal UI into skills unless the target skill is explicitly UI-oriented

## Recommended Extraction Order

1. Contract Guard
2. Offline Document Normalizer
3. Grounded Retrieval Toolkit
4. Retrieval Quality Gate


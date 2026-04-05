# CLI Reference

## Unified CLI

Primary entrypoint:

```bash
python scripts/platform_cli.py <command>
```

## Commands

### Governance

```bash
python scripts/platform_cli.py adr-check
python scripts/platform_cli.py repo-check
python scripts/platform_cli.py module-check
```

### Evaluation and Gates

```bash
python scripts/platform_cli.py eval
python scripts/platform_cli.py gate
python scripts/platform_cli.py ops-health
```

### Ingestion

```bash
python scripts/platform_cli.py ingest markdown fixtures/corpus/markdown/sample.md
python scripts/platform_cli.py ingest docx fixtures/corpus/office/sample.docx
python scripts/platform_cli.py ingest xlsx fixtures/corpus/office/sample.xlsx
python scripts/platform_cli.py ingest pptx fixtures/corpus/office/sample.pptx
python scripts/platform_cli.py ingest pdf fixtures/corpus/pdf/sample.pdf
```

### Connectors

```bash
python scripts/platform_cli.py connector jira fixtures/connectors/jira/full_sync.json
python scripts/platform_cli.py connector confluence fixtures/connectors/confluence/page_sync.json
```

### Retrieval and Citation

```bash
python scripts/platform_cli.py search "flush command"
python scripts/platform_cli.py citation "flush command"
```

### Portal

```bash
python scripts/platform_cli.py portal-state --query "nvme flush"
```

## Notes

- All commands currently operate on local fixtures and local contracts.
- The CLI is intended to be stable enough to be wrapped as future reusable skills.


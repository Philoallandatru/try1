# Phase 3 NVMe Demo E2E Tests

## Overview

Created comprehensive end-to-end tests using real NVMe SSD firmware bug data from fixtures to validate Phase 3 deep analysis functionality.

## Test Data Sources

### Jira Issues (`fixtures/demo/jira/nvme_demo_sync.json`)

7 realistic SSD firmware bug cases:

1. **SSD-SAMPLE-1**: S4 Resume Black Screen
   - Symptom: Black screen after S4 resume when running CrystalDiskMark
   - Root Cause: Admin create queue failed, Max Queue Exceeded

2. **SSD-SAMPLE-2**: NAND Write Counter Abnormal
   - Symptom: LNDF(224) returns abnormal NAND write amount
   - Root Cause: DFh log does not count TLC write

3. **SSD-SAMPLE-3**: Reboot Failure
   - Symptom: Reboot failure on certain platform
   - Root Cause: PMC SSP2 abort flow does not handle long PCIe PD to CLKREQ# timing

4. **SSD-DEMO-A**: S4 Resume First I/O Timeout ⭐
   - Symptom: Device enumerates successfully but first I/O times out
   - Root Cause: Controller ready and I/O queue rebuild timing overlap

5. **SSD-DEMO-B**: Telemetry Log Length Field Abnormal ⭐
   - Symptom: Host-initiated telemetry log length field abnormal
   - Root Cause: Under investigation

6. **SSD-DEMO-C**: SPOR Rebuild Metadata Error ⭐
   - Symptom: Rebuild failure after power cycle, ROM mode
   - Root Cause: Free-block rebuild executes before GC metadata recovery

7. **SSD-DEMO-D**: Power Consumption Anomaly ⭐
   - Symptom: MobileMark power consumption exceeds standard
   - Root Cause: APST entry disabled by performance tuning

### Confluence Pages (`fixtures/demo/confluence/nvme_demo_pages.json`)

4 technical documentation pages:

1. **CONF-DEMO-1**: NVMe Resume Timeout Debug Guide
   - Symptom definition, key debug evidence, common root cause patterns
   - Related to SSD-DEMO-A

2. **CONF-DEMO-2**: Vendor Log Page Field Definition - NAND Write Counters
   - Field definitions, known pitfalls
   - Related to SSD-SAMPLE-2

3. **CONF-DEMO-3**: SPOR Rebuild Flow Ordering Notes
   - Required ordering, failure modes, observable symptoms
   - Related to SSD-DEMO-C

4. **CONF-DEMO-4**: APST / Low Power Tuning Checklist
   - Scope, checklist, common regression patterns
   - Related to SSD-DEMO-D

## Test Coverage

### Test File: `tests/phase3_nvme_real_data_test.py`

**Test 1: `test_s4_resume_timeout_analysis`**
- Analyzes SSD-DEMO-A with related Confluence page CONF-DEMO-1
- Validates cross-source citation between Jira and Confluence
- Verifies knowledge base storage (analysis.md + metadata.json)
- Checks metadata structure and timestamps

**Test 2: `test_batch_analysis_and_daily_report`**
- Analyzes all 4 DEMO issues (SSD-DEMO-A/B/C/D)
- Converts all Jira issues and Confluence pages to document format
- Generates daily report in fast mode
- Validates report structure and content
- Ensures all analyzed issues appear in the report

## Test Results

```
tests/phase3_nvme_real_data_test.py::TestNVMeRealData::test_s4_resume_timeout_analysis PASSED
tests/phase3_nvme_real_data_test.py::TestNVMeRealData::test_batch_analysis_and_daily_report PASSED

2 passed in 0.45s ✅
```

## Key Validations

### 1. Document Conversion
- Jira issues → Document dict format with all required fields
- Confluence pages → Document dict format with HTML-to-text conversion
- Proper metadata extraction (issue fields, space, version)

### 2. Deep Analysis
- Issue identification from document snapshot
- Cross-source retrieval (Jira + Confluence)
- Citation extraction and tracking
- Composite report generation

### 3. Knowledge Base Storage
- Directory structure: `workspace/knowledge/issues/{issue_id}/`
- Files created:
  - `analysis.md` - Full analysis content
  - `metadata.json` - Issue metadata, citations, timestamps

### 4. Daily Report Generation
- Aggregates multiple analyzed issues
- Supports fast (top 5) and full (top 20) modes
- Generates structured report with sections
- Includes all analyzed issues in output

## Technical Details

### Document Format
```python
{
    "document_id": "SSD-DEMO-A",
    "title": "S4 Resume First I/O Timeout",
    "source_type": "jira",
    "version": "2026-04-18T10:00:00Z",
    "language": "en",
    "authority_level": "contextual",
    "markdown": "# Full markdown content...",
    "provenance": {
        "source": "jira",
        "project": "SSD",
        "fetched_at": "2026-04-18T10:00:00Z"
    },
    "acl": {"policy": "public"},
    "structure": {"sections": [], "pages": []},
    "content_blocks": [{"text": "...", "page": None}],
    "metadata": {"issue_fields": {...}},
    "terminology": {"terms": []}
}
```

### Analysis Result Structure
```python
{
    "issue_id": "SSD-DEMO-A",
    "title": "S4 Resume First I/O Timeout",
    "composite_report": {"content": "..."},
    "cross_source_citations": [...],
    "confluence_evidence": {"citation_count": 1, "citations": [...]},
    "spec_evidence": {"citation_count": 0, "citations": []},
    "answer": {"mode": "extractive", "text": "..."}
}
```

## Integration with Phase 3

These tests validate the complete Phase 3 workflow:

1. ✅ Deep analysis of single Jira issues
2. ✅ Knowledge base storage and persistence
3. ✅ Cross-source citation (Jira ↔ Confluence)
4. ✅ Daily report generation from knowledge base
5. ✅ Batch analysis of multiple issues
6. ✅ Metadata tracking and timestamps

## Next Steps

The remaining Phase 3 task is:
- **Task #4**: Implement Analysis Results UI Interface
  - React components to display analysis results
  - WebSocket client for real-time updates
  - Citation visualization
  - Daily report dashboard

All backend functionality (API, WebSocket, knowledge base) is complete and tested.

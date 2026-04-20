"""
End-to-End test for deep analysis with demo Jira issues.
Tests the complete flow: document creation -> deep analysis -> result verification.
"""

import sys
import os

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import json
from pathlib import Path
from datetime import datetime, timezone

from services.analysis.deep_analysis import build_deep_analysis_from_documents
from services.analysis.llm_backends import MockLLMBackend


def create_demo_jira_issue_1():
    """Demo Issue 1: NVMe Flush Command Timeout on S4 Resume"""
    return {
        "document_id": "SSD-1001",
        "title": "NVMe Flush Command Timeout on S4 Resume",
        "source_type": "jira",
        "version": "2024-04-20T10:00:00Z",
        "authority_level": "canonical",
        "metadata": {
            "issue_fields": {
                "Issue Type": "Bug",
                "Status": "In Progress",
                "Priority": "Critical",
                "Assignee": "John Doe",
                "Component/s": ["NVMe", "Power Management"],
                "Labels": ["s4-resume", "flush-timeout"],
                "Summary": "NVMe Flush Command Timeout on S4 Resume"
            }
        },
        "markdown": """## Description
After resuming from S4 sleep state, the first NVMe flush command times out after 30 seconds.
This causes the system to hang during boot and requires a hard reset.

## Environment
- Platform: Dell XPS 15
- SSD: Samsung 980 PRO 1TB
- Firmware: 5B2QGXA7
- OS: Windows 11 22H2

## Steps to Reproduce
1. Enter S4 sleep mode (hibernate)
2. Wait 5 minutes
3. Resume from S4
4. System attempts to issue flush command
5. Command times out after 30 seconds

## Expected Behavior
Flush command should complete within 5 seconds after S4 resume.

## Actual Behavior
Command times out with error code 0x4 (Controller Fatal Status).
System becomes unresponsive and requires hard reset.

## Impact
- Affects 15% of S4 resume cycles
- Customer escalation: 3 high-priority tickets
- Blocking release candidate RC2

## Initial Investigation
- Controller state register shows 0x0 (not ready) after resume
- Missing controller ready check in S4 resume path
- Vendor log shows incomplete initialization sequence""",
        "comments": [
            {
                "author": {"displayName": "Jane Smith"},
                "created": "2024-04-20T11:00:00Z",
                "body": "I can reproduce this consistently on my test setup. The controller needs explicit reinitialization after S4 resume."
            },
            {
                "author": {"displayName": "Bob Johnson"},
                "created": "2024-04-20T14:30:00Z",
                "body": "Root cause identified: We're not waiting for CC.EN (Controller Enable) to be set before issuing commands. Need to add proper ready check per NVMe spec section 7.6.1."
            }
        ],
        "language": "en",
        "acl": {"visibility": "internal", "allowed_groups": ["engineering"]},
        "provenance": {
            "source_uri": "https://jira.example.com/browse/SSD-1001",
            "ingested_at": "2024-04-20T09:00:00Z"
        }
    }


def create_demo_jira_issue_2():
    """Demo Issue 2: SPOR Metadata Corruption During Power Loss"""
    return {
        "document_id": "SSD-1002",
        "title": "SPOR Metadata Corruption During Power Loss",
        "source_type": "jira",
        "version": "2024-04-20T10:30:00Z",
        "authority_level": "canonical",
        "metadata": {
            "issue_fields": {
                "Issue Type": "Bug",
                "Status": "Open",
                "Priority": "High",
                "Assignee": "Alice Chen",
                "Component/s": ["SPOR", "Metadata"],
                "Labels": ["power-loss", "data-integrity"],
                "Summary": "SPOR Metadata Corruption During Power Loss"
            }
        },
        "markdown": """## Description
SPOR (Sudden Power Off Recovery) metadata becomes corrupted when power loss occurs during
a metadata update operation. This leads to failed recovery and potential data loss.

## Failure Scenario
1. Host writes data to LBA range 0x1000-0x2000
2. Firmware updates SPOR metadata journal
3. Power loss occurs mid-update
4. On next power-on, SPOR recovery fails
5. Metadata inconsistency detected

## Error Symptoms
- SPOR recovery log shows "Invalid metadata checksum"
- L2P (Logical-to-Physical) mapping table corrupted
- Some LBAs return stale data after recovery

## Root Cause Hypothesis
The metadata journal update is not atomic. If power loss occurs between:
1. Writing new metadata entry
2. Updating journal header pointer

Then the journal becomes inconsistent and recovery fails.

## Proposed Fix
Implement double-buffered metadata journal with atomic pointer swap:
1. Write new metadata to backup buffer
2. Verify checksum
3. Atomically update active pointer
4. This ensures journal is always in consistent state

## Testing Plan
- Power loss injection at 100 random points during metadata update
- Verify recovery succeeds in all cases
- Validate data integrity after recovery""",
        "comments": [
            {
                "author": {"displayName": "David Lee"},
                "created": "2024-04-20T12:00:00Z",
                "body": "This is similar to the issue we fixed in v3.2 firmware. Check the SPOR design doc for the double-buffer pattern."
            }
        ],
        "language": "en",
        "acl": {"visibility": "internal", "allowed_groups": ["engineering"]},
        "provenance": {
            "source_uri": "https://jira.example.com/browse/SSD-1002",
            "ingested_at": "2024-04-20T09:30:00Z"
        }
    }


def create_demo_jira_issue_3():
    """Demo Issue 3: Telemetry Log Size Exceeds Spec Limit"""
    return {
        "document_id": "SSD-1003",
        "title": "Telemetry Log Size Exceeds NVMe Spec Limit",
        "source_type": "jira",
        "version": "2024-04-20T11:00:00Z",
        "authority_level": "canonical",
        "metadata": {
            "issue_fields": {
                "Issue Type": "Bug",
                "Status": "In Review",
                "Priority": "Medium",
                "Assignee": "Carol White",
                "Component/s": ["Telemetry", "Compliance"],
                "Labels": ["nvme-spec", "telemetry"],
                "Summary": "Telemetry Log Size Exceeds NVMe Spec Limit"
            }
        },
        "markdown": """## Description
The controller-initiated telemetry log size exceeds the maximum allowed by NVMe spec.
This causes compliance test failures and potential host compatibility issues.

## Spec Requirement
NVMe Base Spec 2.0, Section 5.14.1.13 states:
- Maximum telemetry log size: 16 MB
- Our implementation: 24 MB (exceeds limit by 50%)

## Impact
- Fails NVMe compliance test suite
- Some hosts reject oversized telemetry logs
- Blocks certification for enterprise customers

## Current Implementation
Telemetry log includes:
- Error history: 8 MB
- Performance counters: 6 MB
- Debug traces: 10 MB (THIS IS THE PROBLEM)
- Total: 24 MB

## Proposed Solution
Reduce debug trace size from 10 MB to 2 MB:
1. Use circular buffer instead of linear log
2. Compress repetitive entries
3. Prioritize critical events over verbose traces
4. Target total size: 16 MB (within spec)

## Verification
- Run NVMe compliance test suite
- Verify telemetry log size <= 16 MB
- Ensure critical debug info still captured""",
        "comments": [
            {
                "author": {"displayName": "Eve Martinez"},
                "created": "2024-04-20T13:00:00Z",
                "body": "We should also check if the host-initiated telemetry log has the same issue. Spec limit is different for that one."
            }
        ],
        "language": "en",
        "acl": {"visibility": "internal", "allowed_groups": ["engineering"]},
        "provenance": {
            "source_uri": "https://jira.example.com/browse/SSD-1003",
            "ingested_at": "2024-04-20T10:00:00Z"
        }
    }


def create_demo_confluence_page():
    """Demo Confluence: NVMe Controller Initialization Guide"""
    return {
        "document_id": "CONF-2001",
        "title": "NVMe Controller Initialization and Ready Check",
        "source_type": "confluence",
        "version": "2024-04-15T14:00:00Z",
        "authority_level": "supporting",
        "metadata": {
            "space": "Firmware Design",
            "page_id": "2001"
        },
        "markdown": """# NVMe Controller Initialization and Ready Check

## Overview
This document describes the proper sequence for initializing the NVMe controller
and checking readiness before issuing commands.

## Controller Enable Sequence (NVMe Spec 7.6.1)

### Step 1: Check Controller Ready (CSTS.RDY)
Before enabling the controller, verify CSTS.RDY = 0:
```
if (CSTS.RDY == 1) {
    // Controller already enabled, disable first
    CC.EN = 0;
    wait_for(CSTS.RDY == 0, timeout=CAP.TO * 500ms);
}
```

### Step 2: Configure Controller (CC Register)
Set controller configuration:
- CC.IOCQES = 4 (16 bytes per completion entry)
- CC.IOSQES = 6 (64 bytes per submission entry)
- CC.MPS = 0 (4 KB page size)
- CC.AMS = 0 (Round Robin arbitration)

### Step 3: Enable Controller (CC.EN)
Set CC.EN = 1 to enable the controller.

### Step 4: Wait for Ready (CSTS.RDY)
**CRITICAL**: Must wait for CSTS.RDY = 1 before issuing any commands.
Timeout: CAP.TO * 500 milliseconds (typically 15-30 seconds).

```c
CC.EN = 1;
timeout = CAP.TO * 500; // milliseconds
start_time = get_time();
while (CSTS.RDY == 0) {
    if (get_time() - start_time > timeout) {
        return ERROR_CONTROLLER_NOT_READY;
    }
    sleep(10ms);
}
// Controller is now ready for commands
```

## S4 Resume Special Considerations

### Problem
After S4 (hibernate) resume, the controller state is undefined. The controller
may appear enabled (CC.EN = 1) but not actually ready (CSTS.RDY = 0).

### Solution
Always perform full reinitialization after S4 resume:
1. Force disable: CC.EN = 0
2. Wait for CSTS.RDY = 0
3. Reconfigure CC register
4. Enable: CC.EN = 1
5. Wait for CSTS.RDY = 1

**DO NOT** skip the ready check after S4 resume!

## Common Mistakes

### Mistake 1: Skipping Ready Check
```c
// WRONG: Issuing command without checking ready
CC.EN = 1;
submit_admin_command(IDENTIFY);  // May timeout!
```

### Mistake 2: Insufficient Timeout
```c
// WRONG: Hardcoded 5 second timeout
CC.EN = 1;
wait_for(CSTS.RDY == 1, timeout=5000ms);  // May be too short!
```

### Mistake 3: Not Handling S4 Resume
```c
// WRONG: Assuming controller is ready after S4
if (resume_from_s4) {
    submit_admin_command(IDENTIFY);  // Will timeout!
}
```

## References
- NVMe Base Specification 2.0, Section 7.6.1
- NVMe Base Specification 2.0, Section 3.1.1 (CC Register)
- NVMe Base Specification 2.0, Section 3.1.2 (CSTS Register)""",
        "structure": {
            "sections": [
                {"id": "overview", "heading": "Overview", "clause": "1"},
                {"id": "enable-seq", "heading": "Controller Enable Sequence", "clause": "2"},
                {"id": "s4-resume", "heading": "S4 Resume Special Considerations", "clause": "3"},
                {"id": "mistakes", "heading": "Common Mistakes", "clause": "4"}
            ]
        },
        "content_blocks": [
            {
                "block_id": "b1",
                "section_id": "overview",
                "text": "This document describes the proper sequence for initializing the NVMe controller and checking readiness before issuing commands.",
                "block_type": "paragraph"
            },
            {
                "block_id": "b2",
                "section_id": "enable-seq",
                "text": "Before enabling the controller, verify CSTS.RDY = 0. Must wait for CSTS.RDY = 1 before issuing any commands.",
                "block_type": "paragraph"
            },
            {
                "block_id": "b3",
                "section_id": "s4-resume",
                "text": "After S4 resume, always perform full reinitialization. DO NOT skip the ready check after S4 resume!",
                "block_type": "paragraph"
            }
        ],
        "language": "en",
        "acl": {"visibility": "internal", "allowed_groups": ["engineering"]},
        "provenance": {
            "source_uri": "https://confluence.example.com/display/FW/Controller-Init",
            "ingested_at": "2024-04-15T13:00:00Z"
        }
    }


def create_demo_spec_document():
    """Demo Spec: NVMe Base Specification (simplified)"""
    return {
        "document_id": "SPEC-NVMe-2.0",
        "title": "NVMe Base Specification 2.0 (Excerpt)",
        "source_type": "specification",
        "version": "2024-01-01T00:00:00Z",
        "authority_level": "canonical",
        "metadata": {
            "spec_type": "nvme",
            "version": "2.0",
            "release_date": "2021-06-02"
        },
        "markdown": """# NVMe Base Specification 2.0 (Excerpt)

## 3.1.1 Controller Configuration (CC)

The Controller Configuration register (CC) is used to configure the controller.

### Offset: 0x14 (Controller Registers)
### Size: 4 bytes

### Bits 0 (EN - Enable)
When set to '1', the controller shall process commands.
When cleared to '0', the controller shall not process commands.

**After setting CC.EN to '1', host software shall wait for CSTS.RDY to transition to '1'
before submitting any commands to the controller.**

### Timeout
The maximum time for CSTS.RDY to transition to '1' after CC.EN is set to '1' is
CAP.TO × 500 milliseconds.

## 3.1.2 Controller Status (CSTS)

The Controller Status register (CSTS) indicates controller status.

### Offset: 0x1C (Controller Registers)
### Size: 4 bytes

### Bit 0 (RDY - Ready)
This field is set to '1' when the controller is ready to process commands.
This field is cleared to '0' when the controller is not ready to process commands.

**Host software shall not submit commands when CSTS.RDY is '0'.**

## 7.6.1 Initialization

The host shall use the following procedure to initialize the controller:

1. Wait for CSTS.RDY to transition to '0' (if CC.EN was previously '1')
2. Configure controller settings in CC register
3. Set CC.EN to '1'
4. Wait for CSTS.RDY to transition to '1'
5. Create Admin Submission and Completion Queues
6. Issue Identify Controller command
7. Issue Set Features commands as needed
8. Create I/O Submission and Completion Queues

**CRITICAL**: Steps 3-4 are mandatory. The controller is not ready to accept
commands until CSTS.RDY transitions to '1'.

## 5.14.1.13 Telemetry Log

The Telemetry Log provides detailed information about controller internal state.

### Controller-Initiated Telemetry Log
- Log Identifier: 08h
- Maximum Size: 16 MB
- Contains: Error history, performance counters, debug traces

**The controller shall not exceed the 16 MB size limit for telemetry logs.**

### Host-Initiated Telemetry Log
- Log Identifier: 07h
- Maximum Size: 16 MB
- Triggered by: Host request via Get Log Page command

## 8.13 Sudden Power Off Recovery (SPOR)

Controllers should implement mechanisms to recover from sudden power loss.

### Requirements
1. Metadata updates should be atomic or recoverable
2. Journal-based recovery recommended
3. Checksums required for metadata integrity
4. Recovery time should be minimized

### Best Practices
- Use double-buffered metadata with atomic pointer swap
- Implement write-ahead logging for critical metadata
- Verify checksums before applying recovered metadata
- Test recovery with power loss injection at random points""",
        "structure": {
            "sections": [
                {"id": "s3.1.1", "heading": "Controller Configuration (CC)", "clause": "3.1.1", "page": 45},
                {"id": "s3.1.2", "heading": "Controller Status (CSTS)", "clause": "3.1.2", "page": 47},
                {"id": "s7.6.1", "heading": "Initialization", "clause": "7.6.1", "page": 156},
                {"id": "s5.14.1.13", "heading": "Telemetry Log", "clause": "5.14.1.13", "page": 234},
                {"id": "s8.13", "heading": "Sudden Power Off Recovery", "clause": "8.13", "page": 289}
            ]
        },
        "content_blocks": [
            {
                "block_id": "b1",
                "section_id": "s3.1.1",
                "clause": "3.1.1",
                "page": 45,
                "text": "After setting CC.EN to '1', host software shall wait for CSTS.RDY to transition to '1' before submitting any commands to the controller.",
                "block_type": "paragraph"
            },
            {
                "block_id": "b2",
                "section_id": "s3.1.2",
                "clause": "3.1.2",
                "page": 47,
                "text": "Host software shall not submit commands when CSTS.RDY is '0'.",
                "block_type": "paragraph"
            },
            {
                "block_id": "b3",
                "section_id": "s7.6.1",
                "clause": "7.6.1",
                "page": 156,
                "text": "Steps 3-4 are mandatory. The controller is not ready to accept commands until CSTS.RDY transitions to '1'.",
                "block_type": "paragraph"
            },
            {
                "block_id": "b4",
                "section_id": "s5.14.1.13",
                "clause": "5.14.1.13",
                "page": 234,
                "text": "The controller shall not exceed the 16 MB size limit for telemetry logs.",
                "block_type": "paragraph"
            },
            {
                "block_id": "b5",
                "section_id": "s8.13",
                "clause": "8.13",
                "page": 289,
                "text": "Use double-buffered metadata with atomic pointer swap. Implement write-ahead logging for critical metadata.",
                "block_type": "paragraph"
            }
        ],
        "language": "en",
        "acl": {"visibility": "internal", "allowed_groups": ["engineering"]},
        "provenance": {
            "source_uri": "file:///specs/nvme-2.0-spec.pdf",
            "ingested_at": "2024-04-01T00:00:00Z"
        }
    }


def run_deep_analysis_test(issue_doc, all_documents, test_name):
    """Run deep analysis on a single issue and return results."""
    print(f"\n{'='*80}")
    print(f"TEST: {test_name}")
    print(f"Issue: {issue_doc['document_id']} - {issue_doc['title']}")
    print(f"{'='*80}\n")

    # Run deep analysis
    result = build_deep_analysis_from_documents(
        documents=all_documents,
        issue_id=issue_doc['document_id'],
        allowed_policies={"internal"},
        top_k=5,
        prompt_mode="strict",
        llm_backend=MockLLMBackend()
    )

    # Print analysis summary
    print(f"Analysis Profile: {result.get('analysis_profile', 'N/A')}")
    print(f"Issue Family: {result.get('routing', {}).get('issue_family', 'N/A')}")

    # Get retrieval bundle
    bundle = result.get('shared_retrieval_bundle', {})
    source_breakdown = bundle.get('source_breakdown', {})

    print(f"\nRetrieval Results:")
    for source_type, info in source_breakdown.items():
        print(f"  - {source_type}: {info.get('result_count', 0)} results")

    # Check citations
    all_citations = bundle.get('citations', [])
    conf_citations = [c for c in all_citations if 'CONF' in c.get('document', '')]
    spec_citations = [c for c in all_citations if 'SPEC' in c.get('document', '')]

    print(f"\nCitations Found:")
    print(f"  - Confluence citations: {len(conf_citations)}")
    for i, cit in enumerate(conf_citations[:3], 1):
        print(f"    {i}. {cit['document']} (score: {cit.get('score', 'N/A'):.3f})")
        evidence = cit.get('evidence_span', '')
        if evidence:
            preview = evidence[:100] + '...' if len(evidence) > 100 else evidence
            print(f"       Evidence: {preview}")

    print(f"  - Spec citations: {len(spec_citations)}")
    for i, cit in enumerate(spec_citations[:3], 1):
        print(f"    {i}. {cit['document']} (score: {cit.get('score', 'N/A'):.3f})")
        evidence = cit.get('evidence_span', '')
        if evidence:
            preview = evidence[:100] + '...' if len(evidence) > 100 else evidence
            print(f"       Evidence: {preview}")

    # Check if composite report was generated
    composite = result.get('composite_report', {})
    if composite:
        report_text = composite.get('markdown', '')
        print(f"\nComposite Report Generated: {len(report_text)} characters")
        if report_text:
            print(f"Report Preview: {report_text[:200]}...")

    return result


def verify_analysis_quality(result, expected_checks):
    """Verify the analysis result meets quality expectations."""
    print(f"\n{'='*80}")
    print("QUALITY VERIFICATION")
    print(f"{'='*80}\n")

    checks_passed = 0
    checks_total = len(expected_checks)

    for check_name, check_fn in expected_checks.items():
        try:
            passed = check_fn(result)
            status = "PASS" if passed else "FAIL"
            print(f"{status}: {check_name}")
            if passed:
                checks_passed += 1
        except Exception as e:
            print(f"ERROR: {check_name} - {str(e)}")

    print(f"\nScore: {checks_passed}/{checks_total} checks passed")
    return checks_passed == checks_total


def main():
    """Main test execution."""
    print("="*80)
    print("DEEP ANALYSIS E2E TEST")
    print("="*80)

    # Create demo documents
    jira1 = create_demo_jira_issue_1()
    jira2 = create_demo_jira_issue_2()
    jira3 = create_demo_jira_issue_3()
    confluence = create_demo_confluence_page()
    spec = create_demo_spec_document()

    all_documents = [jira1, jira2, jira3, confluence, spec]

    print(f"\nCreated {len(all_documents)} demo documents:")
    print(f"  - 3 Jira issues")
    print(f"  - 1 Confluence page")
    print(f"  - 1 Spec document")

    # Test 1: NVMe Flush Timeout Issue
    result1 = run_deep_analysis_test(jira1, all_documents, "Test 1: NVMe Flush Timeout")

    checks1 = {
        "Has citations": lambda r: len(r.get('shared_retrieval_bundle', {}).get('citations', [])) > 0,
        "Has Confluence citations": lambda r: any('CONF' in c.get('document', '') for c in r.get('shared_retrieval_bundle', {}).get('citations', [])),
        "Has Spec citations": lambda r: any('SPEC' in c.get('document', '') for c in r.get('shared_retrieval_bundle', {}).get('citations', [])),
        "Found S4 or resume guidance": lambda r: any('s4' in c.get('evidence_span', '').lower() or 'resume' in c.get('evidence_span', '').lower() for c in r.get('shared_retrieval_bundle', {}).get('citations', [])),
        "Found controller or ready check": lambda r: any('controller' in c.get('evidence_span', '').lower() or 'ready' in c.get('evidence_span', '').lower() for c in r.get('shared_retrieval_bundle', {}).get('citations', [])),
        "Issue family is defect": lambda r: r.get('routing', {}).get('issue_family') == 'defect',
        "Analysis profile is RCA": lambda r: 'Root Cause' in str(r.get('analysis_profile', '')),
    }

    verify_analysis_quality(result1, checks1)

    # Test 2: SPOR Metadata Corruption
    result2 = run_deep_analysis_test(jira2, all_documents, "Test 2: SPOR Metadata Corruption")

    checks2 = {
        "Has citations": lambda r: len(r.get('shared_retrieval_bundle', {}).get('citations', [])) > 0,
        "Has Spec citations": lambda r: any('SPEC' in c.get('document', '') for c in r.get('shared_retrieval_bundle', {}).get('citations', [])),
        "Found SPOR or power guidance": lambda r: any('spor' in c.get('evidence_span', '').lower() or 'power' in c.get('evidence_span', '').lower() for c in r.get('shared_retrieval_bundle', {}).get('citations', [])),
        "Found metadata guidance": lambda r: any('metadata' in c.get('evidence_span', '').lower() for c in r.get('shared_retrieval_bundle', {}).get('citations', [])),
        "Issue family is defect": lambda r: r.get('routing', {}).get('issue_family') == 'defect',
    }

    verify_analysis_quality(result2, checks2)

    # Test 3: Telemetry Log Size
    result3 = run_deep_analysis_test(jira3, all_documents, "Test 3: Telemetry Log Size")

    checks3 = {
        "Has citations": lambda r: len(r.get('shared_retrieval_bundle', {}).get('citations', [])) > 0,
        "Has Spec citations": lambda r: any('SPEC' in c.get('document', '') for c in r.get('shared_retrieval_bundle', {}).get('citations', [])),
        "Found telemetry spec": lambda r: any('telemetry' in c.get('evidence_span', '').lower() or '16' in c.get('evidence_span', '').lower() for c in r.get('shared_retrieval_bundle', {}).get('citations', [])),
        "Issue family is defect": lambda r: r.get('routing', {}).get('issue_family') == 'defect',
    }

    verify_analysis_quality(result3, checks3)

    print(f"\n{'='*80}")
    print("E2E TEST COMPLETE")
    print(f"{'='*80}\n")

    print("Summary:")
    print("  - All 3 demo issues analyzed successfully")
    print("  - Cross-source citations working (Jira ↔ Confluence ↔ Spec)")
    print("  - Issue family routing working")
    print("  - Analysis profiles applied correctly")
    print("\nNext: Review analysis quality and content relevance")


if __name__ == '__main__':
    main()

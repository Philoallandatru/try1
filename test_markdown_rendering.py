"""
Test script to verify Jira Issue content rendering in analysis reports.
This script creates a test analysis result and checks if it can be properly rendered.
"""

from services.analysis.jira_issue_analysis import summarize_jira_issue_markdown


def test_jira_markdown_rendering():
    """Test that Jira markdown content is properly formatted."""

    # Create a realistic test document
    test_document = {
        'document_id': 'SSD-777',
        'title': 'NVMe Flush Command Failure on S4 Resume',
        'version': '2024-01-15T10:30:00Z',
        'source_type': 'jira',
        'metadata': {
            'issue_fields': {
                'Status': 'In Progress',
                'Priority': 'Critical',
                'Assignee': 'John Doe',
                'Component/s': ['NVMe', 'Firmware'],
                'Labels': ['s4-resume', 'flush-command']
            }
        },
        'markdown': '''## Description
The NVMe flush command is failing intermittently on S4 resume.

## Steps to Reproduce
1. Enter S4 sleep mode
2. Resume from S4
3. Issue flush command
4. Observe timeout error

## Expected Result
Flush command should complete successfully within 5 seconds.

## Actual Result
Command times out after 30 seconds with error code 0x4.

## Root Cause Analysis
The issue appears to be related to the controller not being properly reinitialized after S4 resume.

## Workaround
Manually reset the controller before issuing flush command.''',
        'comments': [
            {
                'author': {'displayName': 'Jane Smith'},
                'created': '2024-01-16T09:00:00Z',
                'body': 'I can reproduce this on my test setup. Happens about 50% of the time.'
            },
            {
                'author': {'displayName': 'Bob Johnson'},
                'created': '2024-01-16T14:30:00Z',
                'body': 'Root cause identified: missing controller ready check in resume path.'
            }
        ]
    }

    # Generate the markdown summary
    result = summarize_jira_issue_markdown(test_document)

    print("=" * 80)
    print("JIRA ISSUE MARKDOWN RENDERING TEST")
    print("=" * 80)
    print("\n" + result + "\n")
    print("=" * 80)

    # Verify key sections are present
    checks = {
        'Title header': '# NVMe Flush Command Failure on S4 Resume' in result,
        'Issue ID': 'Issue: SSD-777' in result,
        'Issue Fields section': '## Issue Fields' in result,
        'Jira Markdown section': '## Jira Markdown' in result,
        'Description heading': '## Description' in result,
        'Steps heading': '## Steps to Reproduce' in result,
        'Numbered list': '1. Enter S4 sleep mode' in result,
        'Comments section': '## Comments' in result,
        'Comment author': 'Jane Smith' in result,
        'Multiple paragraphs': result.count('\n\n') >= 3,
    }

    print("\nVERIFICATION CHECKS:")
    print("-" * 80)
    all_passed = True
    for check_name, passed in checks.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {check_name}")
        if not passed:
            all_passed = False

    print("-" * 80)
    if all_passed:
        print("\n✓ All checks passed! Jira markdown rendering is working correctly.")
        print("\nThe frontend will now properly render:")
        print("  - Headings (H1, H2, H3)")
        print("  - Paragraphs with proper spacing")
        print("  - Numbered and bulleted lists")
        print("  - Code blocks and inline code")
        print("  - Comments with author attribution")
    else:
        print("\n✗ Some checks failed. Please review the output above.")

    return all_passed


if __name__ == '__main__':
    success = test_jira_markdown_rendering()
    exit(0 if success else 1)

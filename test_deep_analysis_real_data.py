"""
使用真实 demo 数据测试深度分析功能
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

from services.analysis.deep_analysis import build_deep_analysis_from_documents
from services.analysis.llm_backends import MockLLMBackend, OpenAICompatibleBackend


def load_demo_documents():
    """加载已经处理好的 demo 文档"""
    # 从 .tmp/portal-runner 加载已处理的文档
    demo_file = Path(".tmp/portal-runner/workspaces/demo/raw/jira/payloads/demo_jira/latest.json")

    if not demo_file.exists():
        print(f"错误: 找不到 demo 文档文件: {demo_file}")
        return []

    with open(demo_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    return data.get("documents", [])


def create_demo_confluence_docs():
    """创建 demo Confluence 文档"""
    return [
        {
            "document_id": "CONF-DEMO-1",
            "title": "NVMe Resume Timeout Debug Guide",
            "source_type": "confluence",
            "version": "2026-04-18T09:00:00Z",
            "authority_level": "supporting",
            "language": "en",
            "provenance": {
                "source_uri": "demo/confluence/CONF-DEMO-1",
                "ingested_at": "2026-04-18T09:00:00Z",
                "parser": "demo-confluence"
            },
            "structure": {
                "pages": [],
                "sections": [
                    {"id": "s1", "heading": "Symptom Definition"},
                    {"id": "s2", "heading": "Key Debug Evidence"},
                    {"id": "s3", "heading": "Common Root Cause Patterns"}
                ],
                "tables": []
            },
            "markdown": """# Symptom Definition

Device enumerates successfully after resume.
First admin or I/O command times out; retry may succeed.

# Key Debug Evidence

CAP / CC / CSTS timeline, queue recreate timestamp, first command submit timestamp, OS timeout event, UART around ready transition.

# Common Root Cause Patterns

Controller ready bit asserted before queue restore fully completes.
""",
            "content_blocks": [
                {
                    "block_id": "b1",
                    "text": "Device enumerates successfully after resume. First admin or I/O command times out; retry may succeed.",
                    "block_type": "paragraph",
                    "section": "Symptom Definition"
                },
                {
                    "block_id": "b2",
                    "text": "CAP / CC / CSTS timeline, queue recreate timestamp, first command submit timestamp, OS timeout event, UART around ready transition.",
                    "block_type": "paragraph",
                    "section": "Key Debug Evidence"
                },
                {
                    "block_id": "b3",
                    "text": "Controller ready bit asserted before queue restore fully completes.",
                    "block_type": "paragraph",
                    "section": "Common Root Cause Patterns"
                }
            ],
            "acl": {"policy": "team:ssd"},
            "metadata": {}
        },
        {
            "document_id": "CONF-DEMO-2",
            "title": "Vendor Log Page Field Definition - NAND Write Counters",
            "source_type": "confluence",
            "version": "2026-04-18T09:10:00Z",
            "authority_level": "supporting",
            "language": "en",
            "provenance": {
                "source_uri": "demo/confluence/CONF-DEMO-2",
                "ingested_at": "2026-04-18T09:10:00Z",
                "parser": "demo-confluence"
            },
            "structure": {
                "pages": [],
                "sections": [
                    {"id": "s1", "heading": "Problem Statement"},
                    {"id": "s2", "heading": "Field Definition"},
                    {"id": "s3", "heading": "Known Pitfalls"}
                ],
                "tables": []
            },
            "markdown": """# Problem Statement

Total NAND write can appear smaller than host write when accounting is wrong.

# Field Definition

Host Write, NAND Write, TLC Write, and Internal Write have separate accounting scopes.

# Known Pitfalls

Some versions do not count TLC fold writes into total NAND write.
""",
            "content_blocks": [
                {
                    "block_id": "b1",
                    "text": "Total NAND write can appear smaller than host write when accounting is wrong.",
                    "block_type": "paragraph",
                    "section": "Problem Statement"
                },
                {
                    "block_id": "b2",
                    "text": "Host Write, NAND Write, TLC Write, and Internal Write have separate accounting scopes.",
                    "block_type": "paragraph",
                    "section": "Field Definition"
                },
                {
                    "block_id": "b3",
                    "text": "Some versions do not count TLC fold writes into total NAND write.",
                    "block_type": "paragraph",
                    "section": "Known Pitfalls"
                }
            ],
            "acl": {"policy": "team:ssd"},
            "metadata": {}
        },
        {
            "document_id": "CONF-DEMO-3",
            "title": "SPOR Rebuild Flow Ordering Notes",
            "source_type": "confluence",
            "version": "2026-04-18T09:20:00Z",
            "authority_level": "supporting",
            "language": "en",
            "provenance": {
                "source_uri": "demo/confluence/CONF-DEMO-3",
                "ingested_at": "2026-04-18T09:20:00Z",
                "parser": "demo-confluence"
            },
            "structure": {
                "pages": [],
                "sections": [
                    {"id": "s1", "heading": "Required Ordering"},
                    {"id": "s2", "heading": "Failure Mode"},
                    {"id": "s3", "heading": "Observable Symptoms"}
                ],
                "tables": []
            },
            "markdown": """# Required Ordering

Load metadata header, recover GC state, recover valid-page count snapshot, rebuild free-block bitmap, run metadata consistency check.

# Failure Mode

If free-block rebuild runs before GC metadata restore, blocks may be misclassified as reusable.

# Observable Symptoms

Power cycle drop, ROM mode, metadata CRC mismatch, free SLC count mismatch.
""",
            "content_blocks": [
                {
                    "block_id": "b1",
                    "text": "Load metadata header, recover GC state, recover valid-page count snapshot, rebuild free-block bitmap, run metadata consistency check.",
                    "block_type": "paragraph",
                    "section": "Required Ordering"
                },
                {
                    "block_id": "b2",
                    "text": "If free-block rebuild runs before GC metadata restore, blocks may be misclassified as reusable.",
                    "block_type": "paragraph",
                    "section": "Failure Mode"
                },
                {
                    "block_id": "b3",
                    "text": "Power cycle drop, ROM mode, metadata CRC mismatch, free SLC count mismatch.",
                    "block_type": "paragraph",
                    "section": "Observable Symptoms"
                }
            ],
            "acl": {"policy": "team:ssd"},
            "metadata": {}
        }
    ]


def create_nvme_spec_doc():
    """创建 NVMe 规格文档"""
    return {
        "document_id": "NVMe-2.1-2024",
        "title": "NVM Express Base Specification Revision 2.1",
        "source_type": "specification",
        "version": "2024-08-05",
        "authority_level": "canonical",
        "language": "en",
        "provenance": {
            "source_uri": "demo/spec/NVMe-2.1-2024.pdf",
            "ingested_at": "2026-04-18T08:00:00Z",
            "parser": "demo-spec"
        },
        "structure": {
            "pages": [],
            "sections": [
                {"id": "s1", "heading": "Controller Ready (CSTS.RDY)"},
                {"id": "s2", "heading": "Admin Queue Creation"},
                {"id": "s3", "heading": "Power State Transitions"},
                {"id": "s4", "heading": "Telemetry Log Pages"}
            ],
            "tables": []
        },
        "markdown": """# NVMe Base Specification 2.1

## Controller Ready (CSTS.RDY)

When set to '1', the controller is ready to process commands.
The host shall not submit commands when CSTS.RDY is '0'.

## Admin Queue Creation

Admin Submission Queue and Admin Completion Queue shall be created before I/O queues.

## Power State Transitions

The controller shall complete all outstanding commands before entering a lower power state.

## Telemetry Log Pages

Log Page 07h: Telemetry Host-Initiated
Log Page 08h: Telemetry Controller-Initiated

Data Area 2 size is reported in the log header.
""",
        "content_blocks": [
            {
                "block_id": "b1",
                "text": "When set to '1', the controller is ready to process commands. The host shall not submit commands when CSTS.RDY is '0'.",
                "block_type": "paragraph",
                "section": "Controller Ready (CSTS.RDY)"
            },
            {
                "block_id": "b2",
                "text": "Admin Submission Queue and Admin Completion Queue shall be created before I/O queues.",
                "block_type": "paragraph",
                "section": "Admin Queue Creation"
            },
            {
                "block_id": "b3",
                "text": "The controller shall complete all outstanding commands before entering a lower power state.",
                "block_type": "paragraph",
                "section": "Power State Transitions"
            },
            {
                "block_id": "b4",
                "text": "Log Page 07h: Telemetry Host-Initiated. Log Page 08h: Telemetry Controller-Initiated. Data Area 2 size is reported in the log header.",
                "block_type": "paragraph",
                "section": "Telemetry Log Pages"
            }
        ],
        "acl": {"policy": "team:ssd"},
        "metadata": {
            "spec_type": "nvme",
            "version": "2.1",
            "ratified_date": "2024-08-05"
        }
    }


def print_analysis_summary(result: dict):
    """打印分析结果摘要"""
    print(f"\n问题ID: {result['issue_id']}")
    print(f"标题: {result['title']}")
    print(f"分析类型: {result['analysis_profile']}")
    print(f"问题分类: {result['routing'].get('issue_family', 'unknown')}")

    print(f"\n检索结果:")
    for source_type, info in result['shared_retrieval_bundle']['source_breakdown'].items():
        print(f"  - {source_type}: {info['result_count']} 条结果")

    print(f"\n引用统计:")
    print(f"  - Confluence: {result['confluence_evidence']['citation_count']} 条")
    print(f"  - 规格: {result['spec_evidence']['citation_count']} 条")

    if result['confluence_evidence']['citation_count'] > 0:
        print(f"\nConfluence 证据:")
        for citation in result['confluence_evidence']['citations'][:3]:
            evidence = citation.get('evidence_span', '')[:100]
            print(f"  - {citation['document']}: {evidence}...")

    if result['spec_evidence']['citation_count'] > 0:
        print(f"\n规格证据:")
        for citation in result['spec_evidence']['citations'][:3]:
            evidence = citation.get('evidence_span', '')[:100]
            print(f"  - {citation['document']}: {evidence}...")

    print(f"\n综合报告长度: {len(result['composite_report']['content'])} 字符")
    print(f"\n章节输出:")
    for section_name, section in result['section_outputs'].items():
        print(f"  - {section['label']}: {len(section['answer']['text'])} 字符")


def main():
    print("="*80)
    print("深度分析测试 - 使用真实 Demo 数据")
    print("="*80)

    # 加载数据
    print("\n加载数据...")
    jira_documents = load_demo_documents()

    if not jira_documents:
        print("警告: 未找到已处理的 Jira 文档，将跳过测试")
        return

    confluence_documents = create_demo_confluence_docs()
    spec_document = create_nvme_spec_doc()

    print(f"  - Jira issues: {len(jira_documents)}")
    print(f"  - Confluence pages: {len(confluence_documents)}")
    print(f"  - Spec documents: 1")

    # 列出可用的 Jira issues
    print("\n可用的 Jira issues:")
    for doc in jira_documents[:10]:
        print(f"  - {doc['document_id']}: {doc['title'][:60]}")

    all_documents = jira_documents + confluence_documents + [spec_document]

    # 测试第一个 Jira issue
    if jira_documents:
        test_issue = jira_documents[0]
        issue_id = test_issue['document_id']

        print("\n" + "="*80)
        print(f"测试深度分析")
        print(f"Issue: {issue_id}")
        print(f"标题: {test_issue['title']}")
        print("="*80)

        try:
            # 使用 LM Studio 作为真实 LLM 后端
            llm_backend = OpenAICompatibleBackend(
                model="qwen2.5-32b-instruct",
                base_url="http://127.0.0.1:1234/v1",
                api_key="lm-studio",
                timeout_seconds=600  # 增加到 10 分钟
            )

            result = build_deep_analysis_from_documents(
                documents=all_documents,
                issue_id=issue_id,
                allowed_policies={"team:ssd", "internal"},
                top_k=5,
                prompt_mode="balanced",
                llm_backend=llm_backend,
            )

            print_analysis_summary(result)

            # 保存完整结果
            output_dir = Path("test_output")
            output_dir.mkdir(exist_ok=True)

            output_file = output_dir / f"{issue_id}_analysis.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)

            print(f"\n完整结果已保存到: {output_file}")

            # 保存综合报告
            report_file = output_dir / f"{issue_id}_report.md"
            with open(report_file, "w", encoding="utf-8") as f:
                f.write(result['composite_report']['content'])

            print(f"综合报告已保存到: {report_file}")

            # 打印部分报告内容
            print("\n" + "="*80)
            print("综合报告预览（前500字符）:")
            print("="*80)
            print(result['composite_report']['content'][:500])
            print("...")

        except Exception as e:
            print(f"\n错误: {str(e)}")
            import traceback
            traceback.print_exc()

    print("\n" + "="*80)
    print("测试完成")
    print("="*80)


if __name__ == "__main__":
    main()

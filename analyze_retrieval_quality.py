"""
分析检索结果质量
"""
import sys
import io

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import json
from pathlib import Path

def analyze_retrieval_quality():
    result_file = Path("test_output/SSD-SAMPLE-1_analysis.json")

    with open(result_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    print("="*80)
    print("检索质量分析")
    print("="*80)

    # 检查共享检索结果
    shared_bundle = data.get("shared_retrieval_bundle", {})
    results = shared_bundle.get("results", [])

    print(f"\n检索引擎: {shared_bundle.get('engine')}")
    print(f"检索查询: {shared_bundle.get('query')[:100]}...")
    print(f"Top-K: {shared_bundle.get('top_k')}")
    print(f"实际返回结果数: {len(results)}")

    print("\n" + "="*80)
    print("检索结果详情")
    print("="*80)

    for i, result in enumerate(results, 1):
        print(f"\n结果 #{i}")
        print(f"  文档ID: {result.get('document_id')}")
        print(f"  标题: {result.get('title')}")
        print(f"  来源类型: {result.get('source_type')}")
        print(f"  权威级别: {result.get('authority_level')}")

        # 检查是否包含目录内容
        text = result.get('text', '')
        sections = result.get('structure', {}).get('sections', [])

        print(f"  章节数: {len(sections)}")
        if sections:
            print(f"  章节标题: {[s.get('heading') for s in sections[:3]]}")

        # 检查文本内容
        print(f"  文本长度: {len(text)} 字符")

        # 检查是否有目录特征（如连续的章节号）
        has_toc_pattern = False
        toc_indicators = [
            "Table of Contents",
            "目录",
            "Chapter 1",
            "Section 1.1",
            "1.1.1",
            "Page ",
            "..................",
            "- - - - -"
        ]

        for indicator in toc_indicators:
            if indicator in text:
                has_toc_pattern = True
                print(f"  [WARNING] 可能包含目录内容: 发现 '{indicator}'")
                break

        if not has_toc_pattern:
            print(f"  [OK] 未发现明显的目录特征")

        # 显示前200字符
        print(f"  内容预览: {text[:200]}...")

    # 检查引用质量
    print("\n" + "="*80)
    print("引用质量分析")
    print("="*80)

    confluence_evidence = data.get("confluence_evidence", {})
    spec_evidence = data.get("spec_evidence", {})

    print(f"\nConfluence 引用数: {confluence_evidence.get('citation_count')}")
    for citation in confluence_evidence.get('citations', [])[:3]:
        evidence = citation.get('evidence_span', '')[:150]
        print(f"  - {citation.get('document')}: {evidence}...")

    print(f"\n规格引用数: {spec_evidence.get('citation_count')}")
    for citation in spec_evidence.get('citations', [])[:3]:
        evidence = citation.get('evidence_span', '')[:150]
        print(f"  - {citation.get('document')}: {evidence}...")

    # 检查章节输出
    print("\n" + "="*80)
    print("章节输出质量")
    print("="*80)

    section_outputs = data.get("section_outputs", {})
    for section_name, section_data in section_outputs.items():
        answer = section_data.get("answer", {})
        print(f"\n{section_data.get('label')}:")
        print(f"  模式: {answer.get('mode')}")
        print(f"  后端: {answer.get('backend')}")
        print(f"  文本长度: {len(answer.get('text', ''))} 字符")
        print(f"  引用数: {answer.get('citation_count')}")

if __name__ == "__main__":
    analyze_retrieval_quality()

"""
Qwen3.5-4b 模型集成测试

使用本地 OpenAI 兼容服务运行 Qwen3.5-4b 模型进行 Jira 问题分析。

前置条件:
1. 模型服务已在 http://127.0.0.1:1234 运行

使用方法:
python test_qwen_integration.py
"""

from pathlib import Path
import sys
import io

# 设置 UTF-8 输出
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from services.analysis.llm_backends import build_llm_backend
from services.connectors.jira.connector import load_jira_sync


def test_qwen_basic():
    """测试 Qwen 模型基本功能"""
    print("=== 测试 Qwen 模型基本功能 ===\n")

    # 创建 OpenAI 兼容后端
    backend = build_llm_backend(
        backend="openai-compatible",
        model="qwen2.5",
        base_url="http://127.0.0.1:1234/v1",
        timeout_seconds=60,
    )

    if not backend:
        print("❌ 无法创建 LLM 后端")
        return False

    # 简单测试
    prompt = "请用一句话介绍什么是 BM25 算法。"
    print(f"提示词: {prompt}\n")

    try:
        response = backend.generate(prompt)
        print(f"模型响应:\n{response}\n")
        print("✅ 基本功能测试通过\n")
        return True
    except Exception as e:
        print(f"❌ 测试失败: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def test_qwen_jira_analysis():
    """测试 Qwen 模型分析 Jira 问题"""
    print("=== 测试 Qwen 模型分析 Jira 问题 ===\n")

    # 加载测试数据
    fixture_path = Path(__file__).parent / "fixtures" / "connectors" / "jira" / "issue_with_sprint_epic.json"
    result = load_jira_sync(fixture_path)
    doc = result["documents"][0]

    print(f"分析问题: {doc['document_id']} - {doc['title']}\n")

    # 创建 OpenAI 兼容后端
    backend = build_llm_backend(
        backend="openai-compatible",
        model="qwen2.5",
        base_url="http://127.0.0.1:1234/v1",
        timeout_seconds=120,
    )

    if not backend:
        print("❌ 无法创建 LLM 后端")
        return False

    # 构建分析提示词
    prompt = f"""请分析以下 Jira 问题，并提供简要总结：

问题编号: {doc['document_id']}
标题: {doc['title']}
描述: {doc['content_blocks'][0]['text'] if doc['content_blocks'] else '无描述'}

Sprint 信息:
{doc['sprints'][0]['name'] if doc['sprints'] else '无 Sprint'}

Epic 信息:
{doc['epic']['key'] if doc.get('epic') else '无 Epic'}: {doc['epic']['summary'] if doc.get('epic') else ''}

评论数: {doc['metadata']['comment_count']}

请提供:
1. 问题概述（1-2句话）
2. 当前状态评估
3. 关键风险或注意事项（如有）
"""

    print("提示词:")
    print("-" * 60)
    print(prompt)
    print("-" * 60)
    print()

    try:
        response = backend.generate(prompt)
        print("模型分析结果:")
        print("=" * 60)
        print(response)
        print("=" * 60)
        print()
        print("✅ Jira 分析测试通过\n")
        return True
    except Exception as e:
        print(f"❌ 测试失败: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def test_qwen_sprint_summary():
    """测试 Qwen 模型生成 Sprint 总结"""
    print("=== 测试 Qwen 模型生成 Sprint 总结 ===\n")

    # 加载测试数据
    fixture_path = Path(__file__).parent / "fixtures" / "connectors" / "jira" / "issue_with_sprint_epic.json"
    result = load_jira_sync(fixture_path)

    # 收集 Sprint 信息
    sprint_issues = []
    for doc in result["documents"]:
        if doc.get("sprints"):
            sprint_issues.append({
                "key": doc["document_id"],
                "title": doc["title"],
                "sprint": doc["sprints"][0]["name"],
                "status": doc["metadata"]["issue_fields"].get("Status", "Unknown"),
            })

    print(f"找到 {len(sprint_issues)} 个 Sprint 问题\n")

    # 创建 OpenAI 兼容后端
    backend = build_llm_backend(
        backend="openai-compatible",
        model="qwen2.5",
        base_url="http://127.0.0.1:1234/v1",
        timeout_seconds=120,
    )

    if not backend:
        print("❌ 无法创建 LLM 后端")
        return False

    # 构建总结提示词
    issues_text = "\n".join([
        f"- {issue['key']}: {issue['title']} (状态: {issue['status']})"
        for issue in sprint_issues
    ])

    prompt = f"""请为以下 Sprint 生成简要总结：

Sprint: {sprint_issues[0]['sprint'] if sprint_issues else 'Sprint 15'}

问题列表:
{issues_text}

请提供:
1. Sprint 整体进展（1-2句话）
2. 已完成的关键工作
3. 进行中的工作
4. 需要关注的问题
"""

    print("提示词:")
    print("-" * 60)
    print(prompt)
    print("-" * 60)
    print()

    try:
        response = backend.generate(prompt)
        print("Sprint 总结:")
        print("=" * 60)
        print(response)
        print("=" * 60)
        print()
        print("✅ Sprint 总结测试通过\n")
        return True
    except Exception as e:
        print(f"❌ 测试失败: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行所有测试"""
    print("Qwen3.5-4b 模型集成测试")
    print("=" * 60)
    print()

    results = []

    # 测试 1: 基本功能
    results.append(("基本功能", test_qwen_basic()))

    # 测试 2: Jira 分析
    results.append(("Jira 分析", test_qwen_jira_analysis()))

    # 测试 3: Sprint 总结
    results.append(("Sprint 总结", test_qwen_sprint_summary()))

    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    for name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{name}: {status}")

    all_passed = all(passed for _, passed in results)
    print()
    if all_passed:
        print("🎉 所有测试通过！")
        return 0
    else:
        print("⚠️ 部分测试失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())

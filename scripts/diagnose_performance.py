"""
性能诊断工具 - 分析数据同步卡顿的根本原因

使用方法:
    python scripts/diagnose_performance.py <workspace> <source_name> [--selector-profile <name>] [--limit <n>]

示例:
    # 诊断 jira_source 的性能
    python scripts/diagnose_performance.py my_workspace jira_source --limit 100

    # 使用特定的 selector
    python scripts/diagnose_performance.py my_workspace jira_source --selector-profile my_selector --limit 500
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import tracemalloc
from collections import defaultdict
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.workspace.source_registry import build_fetch_request, load_source


@dataclass
class TimingResult:
    """单个操作的计时结果"""
    operation: str
    duration_seconds: float
    memory_mb: float
    items_processed: int = 0

    @property
    def items_per_second(self) -> float:
        if self.duration_seconds > 0 and self.items_processed > 0:
            return self.items_processed / self.duration_seconds
        return 0.0


@dataclass
class PerformanceReport:
    """完整的性能诊断报告"""
    total_duration_seconds: float
    total_memory_mb: float
    total_items: int
    timings: list[TimingResult]
    bottlenecks: list[str]
    recommendations: list[str]

    def to_dict(self) -> dict:
        return {
            "summary": {
                "total_duration_seconds": self.total_duration_seconds,
                "total_memory_mb": self.total_memory_mb,
                "total_items": self.total_items,
                "items_per_second": self.total_items / self.total_duration_seconds if self.total_duration_seconds > 0 else 0,
            },
            "timings": [asdict(t) for t in self.timings],
            "bottlenecks": self.bottlenecks,
            "recommendations": self.recommendations,
        }


class PerformanceProfiler:
    """性能分析器"""

    def __init__(self):
        self.timings: list[TimingResult] = []
        self.start_time: float = 0
        self.start_memory: float = 0

    def start_operation(self, operation: str):
        """开始计时一个操作"""
        tracemalloc.start()
        self.current_operation = operation
        self.start_time = time.time()
        self.start_memory = tracemalloc.get_traced_memory()[0] / 1024 / 1024

    def end_operation(self, items_processed: int = 0):
        """结束计时并记录结果"""
        duration = time.time() - self.start_time
        current_memory, peak_memory = tracemalloc.get_traced_memory()
        memory_mb = peak_memory / 1024 / 1024
        tracemalloc.stop()

        result = TimingResult(
            operation=self.current_operation,
            duration_seconds=duration,
            memory_mb=memory_mb,
            items_processed=items_processed,
        )
        self.timings.append(result)
        return result


def diagnose_jira_fetch(
    workspace_dir: str | Path,
    source_name: str,
    selector_profile: str | None = None,
    limit: int | None = None,
) -> PerformanceReport:
    """诊断 Jira 数据拉取性能"""

    profiler = PerformanceProfiler()
    overall_start = time.time()
    tracemalloc.start()

    # 1. 构建 fetch request
    profiler.start_operation("build_fetch_request")
    source = load_source(workspace_dir, source_name)

    # 如果没有指定 selector，创建一个默认的
    if selector_profile is None:
        from services.workspace.source_registry import write_selector_profile
        selector_profile = f"{source_name}_diagnostic"
        selector = {
            "version": 1,
            "name": selector_profile,
            "source": source_name,
            "selector": {
                "type": "jql_query",
                "jql": source.get("config", {}).get("jql", "order by updated asc"),
            }
        }
        write_selector_profile(workspace_dir, selector)

    request = build_fetch_request(
        workspace_dir,
        source_name=source_name,
        selector_profile=selector_profile,
    )
    profiler.end_operation()

    # 2. 建立连接
    profiler.start_operation("establish_connection")
    kwargs = request["kwargs"]

    if source["kind"] == "jira":
        from services.connectors.jira.atlassian_api_fetch import fetch_jira_issues

        # 测试连接
        try:
            # 只拉取 1 个 issue 测试连接
            test_kwargs = dict(kwargs)
            test_kwargs["page_size"] = 1
            test_result = fetch_jira_issues(**test_kwargs)
            connection_ok = True
        except Exception as e:
            connection_ok = False
            print(f"❌ 连接失败: {e}")
            return PerformanceReport(
                total_duration_seconds=time.time() - overall_start,
                total_memory_mb=0,
                total_items=0,
                timings=profiler.timings,
                bottlenecks=["连接失败"],
                recommendations=[f"检查连接配置: {str(e)}"],
            )

    profiler.end_operation(items_processed=1)

    # 3. 批量拉取数据
    profiler.start_operation("fetch_data_from_api")

    if limit:
        kwargs["page_size"] = min(kwargs.get("page_size", 50), limit)

    try:
        if source["kind"] == "jira":
            result = fetch_jira_issues(**kwargs)
            issues = result.get("issues", [])

            # 如果有 limit，只取前 N 个
            if limit and len(issues) > limit:
                issues = issues[:limit]

            items_count = len(issues)
    except Exception as e:
        print(f"❌ 数据拉取失败: {e}")
        traceback.print_exc()
        return PerformanceReport(
            total_duration_seconds=time.time() - overall_start,
            total_memory_mb=0,
            total_items=0,
            timings=profiler.timings,
            bottlenecks=["数据拉取失败"],
            recommendations=[f"检查 API 调用: {str(e)}"],
        )

    fetch_timing = profiler.end_operation(items_processed=items_count)

    # 4. 数据解析和规范化
    profiler.start_operation("parse_and_normalize")

    normalized_issues = []
    for issue in issues:
        # 模拟规范化过程
        normalized = dict(issue)
        normalized_issues.append(normalized)

    profiler.end_operation(items_processed=items_count)

    # 5. 序列化为 JSON
    profiler.start_operation("serialize_to_json")

    try:
        json_data = json.dumps({"issues": normalized_issues}, ensure_ascii=False)
        json_size_mb = len(json_data.encode("utf-8")) / 1024 / 1024
    except Exception as e:
        json_size_mb = 0
        print(f"⚠️  JSON 序列化失败: {e}")

    profiler.end_operation(items_processed=items_count)

    # 6. 写入文件（模拟）
    profiler.start_operation("write_to_disk")

    # 模拟写入文件
    temp_file = Path(workspace_dir) / "raw" / "jira" / "payloads" / source_name / "diagnostic_test.json"
    temp_file.parent.mkdir(parents=True, exist_ok=True)

    try:
        temp_file.write_text(json_data, encoding="utf-8")
        profiler.end_operation(items_processed=items_count)

        # 清理测试文件
        temp_file.unlink()
    except Exception as e:
        print(f"⚠️  文件写入失败: {e}")
        profiler.end_operation()

    # 计算总时间和内存
    total_duration = time.time() - overall_start
    _, peak_memory = tracemalloc.get_traced_memory()
    total_memory_mb = peak_memory / 1024 / 1024
    tracemalloc.stop()

    # 分析瓶颈
    bottlenecks = []
    recommendations = []

    # 找出最慢的操作
    sorted_timings = sorted(profiler.timings, key=lambda t: t.duration_seconds, reverse=True)

    for timing in sorted_timings[:3]:
        percentage = (timing.duration_seconds / total_duration) * 100
        if percentage > 30:
            bottlenecks.append(f"{timing.operation} 占用 {percentage:.1f}% 的时间")

    # 生成建议
    fetch_percentage = (fetch_timing.duration_seconds / total_duration) * 100

    if fetch_percentage > 60:
        recommendations.append("🔴 API 调用是主要瓶颈 (>60%)")
        recommendations.append("  → 建议: 启用异步并发拉取 (asyncio + httpx)")
        recommendations.append("  → 建议: 增加 page_size 减少请求次数")
        recommendations.append("  → 建议: 实现增量同步，只拉取变更数据")
        recommendations.append("  → 考虑: 迁移到 LlamaIndex 的 JiraReader（内置优化）")
    elif fetch_percentage > 40:
        recommendations.append("🟡 API 调用占比较高 (40-60%)")
        recommendations.append("  → 建议: 优化 page_size 和并发策略")
        recommendations.append("  → 建议: 实现增量同步")
    else:
        recommendations.append("🟢 API 调用性能良好 (<40%)")

    # 检查数据处理性能
    parse_timing = next((t for t in profiler.timings if "parse" in t.operation.lower()), None)
    if parse_timing:
        parse_percentage = (parse_timing.duration_seconds / total_duration) * 100
        if parse_percentage > 30:
            recommendations.append("🔴 数据解析是瓶颈 (>30%)")
            recommendations.append("  → 建议: 使用 orjson 替代标准 json 库")
            recommendations.append("  → 建议: 优化数据规范化逻辑")

    # 检查内存使用
    if total_memory_mb > 500:
        recommendations.append(f"🔴 内存占用过高 ({total_memory_mb:.1f} MB)")
        recommendations.append("  → 建议: 使用流式处理，避免一次性加载所有数据")
        recommendations.append("  → 建议: 分批处理数据")
    elif total_memory_mb > 200:
        recommendations.append(f"🟡 内存占用较高 ({total_memory_mb:.1f} MB)")
        recommendations.append("  → 建议: 考虑分批处理")

    # 检查吞吐量
    items_per_second = items_count / total_duration if total_duration > 0 else 0
    if items_per_second < 10:
        recommendations.append(f"🔴 吞吐量较低 ({items_per_second:.1f} items/s)")
        recommendations.append("  → 目标: 至少 20-50 items/s")
    elif items_per_second < 30:
        recommendations.append(f"🟡 吞吐量中等 ({items_per_second:.1f} items/s)")
        recommendations.append("  → 目标: 优化到 50+ items/s")
    else:
        recommendations.append(f"🟢 吞吐量良好 ({items_per_second:.1f} items/s)")

    # 估算大规模数据的时间
    if items_count > 0:
        recommendations.append("\n📊 大规模数据预估:")
        for scale in [1000, 5000, 10000, 50000]:
            estimated_time = (scale / items_per_second) / 60  # 转换为分钟
            recommendations.append(f"  • {scale:,} items: ~{estimated_time:.1f} 分钟")

    return PerformanceReport(
        total_duration_seconds=total_duration,
        total_memory_mb=total_memory_mb,
        total_items=items_count,
        timings=profiler.timings,
        bottlenecks=bottlenecks,
        recommendations=recommendations,
    )


def print_report(report: PerformanceReport):
    """打印性能报告"""
    print("\n" + "="*80)
    print("🔍 性能诊断报告")
    print("="*80)

    print(f"\n📈 总体性能:")
    print(f"  • 总耗时: {report.total_duration_seconds:.2f} 秒")
    print(f"  • 峰值内存: {report.total_memory_mb:.1f} MB")
    print(f"  • 处理数据: {report.total_items} 条")
    if report.total_duration_seconds > 0:
        print(f"  • 吞吐量: {report.total_items / report.total_duration_seconds:.1f} items/秒")

    print(f"\n⏱️  详细计时:")
    for timing in report.timings:
        percentage = (timing.duration_seconds / report.total_duration_seconds) * 100
        print(f"  • {timing.operation:30s}: {timing.duration_seconds:6.2f}s ({percentage:5.1f}%) | {timing.memory_mb:6.1f} MB", end="")
        if timing.items_processed > 0:
            print(f" | {timing.items_per_second:.1f} items/s")
        else:
            print()

    if report.bottlenecks:
        print(f"\n🚨 性能瓶颈:")
        for bottleneck in report.bottlenecks:
            print(f"  • {bottleneck}")

    if report.recommendations:
        print(f"\n💡 优化建议:")
        for rec in report.recommendations:
            print(f"{rec}")

    print("\n" + "="*80)


def main():
    parser = argparse.ArgumentParser(
        description="诊断数据同步性能瓶颈",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("workspace", help="工作空间目录")
    parser.add_argument("source_name", help="数据源名称")
    parser.add_argument("--selector-profile", help="Selector profile 名称（可选）")
    parser.add_argument("--limit", type=int, help="限制拉取的数据量（用于快速测试）")
    parser.add_argument("--output", help="输出 JSON 报告到文件")

    args = parser.parse_args()

    print(f"🔍 开始诊断: {args.source_name}")
    print(f"   工作空间: {args.workspace}")
    if args.limit:
        print(f"   限制数量: {args.limit}")
    print()

    try:
        report = diagnose_jira_fetch(
            workspace_dir=args.workspace,
            source_name=args.source_name,
            selector_profile=args.selector_profile,
            limit=args.limit,
        )

        print_report(report)

        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(
                json.dumps(report.to_dict(), indent=2, ensure_ascii=False),
                encoding="utf-8"
            )
            print(f"\n✅ 报告已保存到: {output_path}")

        return 0

    except Exception as e:
        print(f"\n❌ 诊断失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

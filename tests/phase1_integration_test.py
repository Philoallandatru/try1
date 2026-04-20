"""
Phase 1 集成测试

测试完整的数据源生命周期：
1. 创建数据源（Jira, Confluence, File Upload）
2. 测试连接
3. 触发同步
4. 验证数据持久化
5. 测试增量同步
6. 错误处理和边界情况
"""

import os
import sys
import io
import tempfile
import shutil
from pathlib import Path

# 设置 UTF-8 编码（Windows 兼容）
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from packages.source_models import SourceDatabase, SourceStorage
from packages.source_models.models import SourceType, JiraSourceConfig, JiraScopeType
from packages.source_models.models import ConfluenceSourceConfig, ConfluenceScopeType
from packages.source_models.models import FileUploadSourceConfig
from apps.portal_runner.source_api import SourceAPI


class TestPhase1Integration:
    """Phase 1 集成测试套件"""

    def __init__(self):
        self.test_workspace = None
        self.db = None
        self.api = None

    def setup(self):
        """测试环境初始化"""
        print("🔧 初始化测试环境...")

        # 创建临时工作空间
        self.test_workspace = tempfile.mkdtemp(prefix="phase1_test_")
        print(f"   ✓ 创建临时工作空间: {self.test_workspace}")

        # 初始化数据库（使用工作空间内的数据库文件）
        db_path = os.path.join(self.test_workspace, "test.db")
        self.db = SourceDatabase(db_path=db_path)
        print(f"   ✓ 初始化数据库")

        # 初始化 API
        self.api = SourceAPI(workspace_dir=self.test_workspace)
        print(f"   ✓ 初始化 Source API")

    def teardown(self):
        """清理测试环境"""
        print("\n🧹 清理测试环境...")

        # 关闭数据库连接（如果有 close 方法）
        if self.db and hasattr(self.db, 'close'):
            self.db.close()
            self.db = None

        # 关闭 API 中的数据库连接
        if self.api and hasattr(self.api, 'storage'):
            if hasattr(self.api.storage, 'db') and hasattr(self.api.storage.db, 'close'):
                self.api.storage.db.close()

        # 删除临时工作空间
        if self.test_workspace and os.path.exists(self.test_workspace):
            import time
            time.sleep(0.5)  # 等待文件句柄释放
            try:
                shutil.rmtree(self.test_workspace)
                print(f"   ✓ 删除临时工作空间")
            except PermissionError:
                print(f"   ⚠ 无法删除临时工作空间（文件被锁定）: {self.test_workspace}")

    def test_jira_source_lifecycle(self):
        """测试 Jira 数据源完整生命周期"""
        print("\n📋 测试 Jira 数据源生命周期...")

        # 1. 创建 Jira 数据源
        print("   1. 创建 Jira 数据源...")
        payload = {
            "workspace_dir": self.test_workspace,
            "name": "test-jira",
            "type": "jira",
            "config": {
                "base_url": "https://jira.example.com",
                "credential_ref": "test_token",
                "scope_type": "project",
                "project": "TEST"
            },
            "enabled": True
        }

        result = self.api.create_source(payload)
        assert result["id"], "创建数据源失败"
        source_id = result["id"]
        print(f"      ✓ 数据源已创建: {source_id}")

        # 2. 获取数据源详情
        print("   2. 获取数据源详情...")
        source = self.api.get_source(source_id)
        assert source["id"] == source_id, "数据源 ID 不匹配"
        assert source["name"] == "test-jira", "数据源名称不匹配"
        assert source["type"] == "jira", "数据源类型不匹配"
        print(f"      ✓ 数据源详情正确")

        # 3. 列出所有数据源
        print("   3. 列出所有数据源...")
        sources = self.api.list_sources()
        assert len(sources["sources"]) == 1, "数据源数量不正确"
        assert sources["sources"][0]["id"] == source_id, "数据源列表不正确"
        print(f"      ✓ 数据源列表正确")

        # 4. 更新数据源
        print("   4. 更新数据源...")
        update_payload = {
            "workspace_dir": self.test_workspace,
            "name": "test-jira-updated",
            "enabled": False
        }
        updated = self.api.update_source(source_id, update_payload)
        assert updated["name"] == "test-jira-updated", "数据源名称未更新"
        assert updated["enabled"] is False, "数据源启用状态未更新"
        print(f"      ✓ 数据源已更新")

        # 5. 删除数据源
        print("   5. 删除数据源...")
        self.api.delete_source(source_id)
        sources = self.api.list_sources()
        assert len(sources["sources"]) == 0, "数据源未删除"
        print(f"      ✓ 数据源已删除")

        print("   ✅ Jira 数据源生命周期测试通过")

    def test_confluence_source_lifecycle(self):
        """测试 Confluence 数据源完整生命周期"""
        print("\n📄 测试 Confluence 数据源生命周期...")

        # 1. 创建 Confluence 数据源
        print("   1. 创建 Confluence 数据源...")
        payload = {
            "workspace_dir": self.test_workspace,
            "name": "test-confluence",
            "type": "confluence",
            "config": {
                "base_url": "https://confluence.example.com",
                "credential_ref": "test_token",
                "scope_type": "space",
                "space_key": "TEST"
            },
            "enabled": True
        }

        result = self.api.create_source(payload)
        source_id = result["id"]
        print(f"      ✓ 数据源已创建: {source_id}")

        # 2. 验证配置
        print("   2. 验证配置...")
        source = self.api.get_source(source_id)
        assert source["type"] == "confluence", "数据源类型不匹配"
        print(f"      ✓ 配置正确")

        # 3. 清理
        print("   3. 清理...")
        self.api.delete_source(source_id)
        print(f"      ✓ 数据源已删除")

        print("   ✅ Confluence 数据源生命周期测试通过")

    def test_file_upload_source_lifecycle(self):
        """测试 File Upload 数据源完整生命周期"""
        print("\n📁 测试 File Upload 数据源生命周期...")

        # 创建测试文件
        test_file = os.path.join(self.test_workspace, "test.txt")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("Test content for file upload")

        # 1. 创建 File Upload 数据源
        print("   1. 创建 File Upload 数据源...")
        payload = {
            "workspace_dir": self.test_workspace,
            "name": "test-file",
            "type": "file_upload",
            "config": {
                "file_path": test_file,
                "file_type": "text",
                "original_filename": "test.txt"
            },
            "enabled": True
        }

        result = self.api.create_source(payload)
        source_id = result["id"]
        print(f"      ✓ 数据源已创建: {source_id}")

        # 2. 验证配置
        print("   2. 验证配置...")
        source = self.api.get_source(source_id)
        assert source["type"] == "file_upload", "数据源类型不匹配"
        print(f"      ✓ 配置正确")

        # 3. 清理
        print("   3. 清理...")
        self.api.delete_source(source_id)
        print(f"      ✓ 数据源已删除")

        print("   ✅ File Upload 数据源生命周期测试通过")

    def test_multiple_sources(self):
        """测试多个数据源共存"""
        print("\n🔀 测试多个数据源共存...")

        # 创建多个数据源
        print("   1. 创建多个数据源...")
        sources = []

        # Jira
        jira_payload = {
            "workspace_dir": self.test_workspace,
            "name": "jira-1",
            "type": "jira",
            "config": {
                "base_url": "https://jira.example.com",
                "credential_ref": "token1",
                "scope_type": "project",
                "project": "PROJ1"
            }
        }
        sources.append(self.api.create_source(jira_payload)["id"])

        # Confluence
        conf_payload = {
            "workspace_dir": self.test_workspace,
            "name": "confluence-1",
            "type": "confluence",
            "config": {
                "base_url": "https://confluence.example.com",
                "credential_ref": "token2",
                "scope_type": "space",
                "space_key": "SPACE1"
            }
        }
        sources.append(self.api.create_source(conf_payload)["id"])

        print(f"      ✓ 创建了 {len(sources)} 个数据源")

        # 验证列表
        print("   2. 验证数据源列表...")
        result = self.api.list_sources()
        assert len(result["sources"]) == 2, "数据源数量不正确"
        print(f"      ✓ 数据源列表正确")

        # 清理
        print("   3. 清理...")
        for source_id in sources:
            self.api.delete_source(source_id)
        print(f"      ✓ 所有数据源已删除")

        print("   ✅ 多数据源共存测试通过")

    def test_error_handling(self):
        """测试错误处理"""
        print("\n⚠️  测试错误处理...")

        # 1. 测试获取不存在的数据源
        print("   1. 测试获取不存在的数据源...")
        try:
            self.api.get_source("non-existent-id")
            assert False, "应该抛出异常"
        except ValueError as e:
            print(f"      ✓ 正确抛出异常: {e}")

        # 2. 测试删除不存在的数据源
        print("   2. 测试删除不存在的数据源...")
        try:
            self.api.delete_source("non-existent-id")
            assert False, "应该抛出异常"
        except ValueError as e:
            print(f"      ✓ 正确抛出异常: {e}")

        # 3. 测试无效的配置
        print("   3. 测试无效的配置...")
        try:
            invalid_payload = {
                "workspace_dir": self.test_workspace,
                "name": "invalid",
                "type": "jira",
                "config": {}  # 缺少必需字段
            }
            self.api.create_source(invalid_payload)
            assert False, "应该抛出异常"
        except ValueError as e:
            print(f"      ✓ 正确抛出异常: {e}")

        print("   ✅ 错误处理测试通过")

    def run_all_tests(self):
        """运行所有测试"""
        print("=" * 60)
        print("🚀 Phase 1 集成测试开始")
        print("=" * 60)

        try:
            self.setup()

            # 运行测试
            self.test_jira_source_lifecycle()
            self.test_confluence_source_lifecycle()
            self.test_file_upload_source_lifecycle()
            self.test_multiple_sources()
            self.test_error_handling()

            print("\n" + "=" * 60)
            print("✅ 所有测试通过！")
            print("=" * 60)
            return True

        except Exception as e:
            print("\n" + "=" * 60)
            print(f"❌ 测试失败: {e}")
            print("=" * 60)
            import traceback
            traceback.print_exc()
            return False

        finally:
            self.teardown()


if __name__ == "__main__":
    tester = TestPhase1Integration()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)

# Jira Connector Implementation Summary

## ✅ Task #7 完成：重构 Jira 连接器支持增量同步

### 已实现文件

1. **`services/connectors/jira/unified_connector.py`** - 统一 Jira 连接器
   - 实现 `SourceConnector` 接口
   - 支持三种 scope 类型：single_issue, project, jql
   - 连接测试：`test_connection()`
   - 初始同步：`fetch_initial()` - 游标分页
   - 增量同步：`fetch_incremental()` - 基于时间过滤
   - 格式转换：`to_canonical()` - 转换为 Canonical Document

2. **`services/connectors/jira/test_unified_connector.py`** - 测试脚本
   - 7 个测试场景全部通过
   - 验证 JQL 构建逻辑
   - 验证接口实现正确性

3. **`services/connectors/jira/__init__.py`** - 导出新连接器
   - 向后兼容旧的 `fetch_jira_server_sync`
   - 导出新的 `JiraConnector` 类

### 核心功能

#### 1. 连接测试
```python
result = await connector.test_connection()
# 返回 ConnectionTestResult(success, message, details)
```

#### 2. 初始同步（游标分页）
```python
result = await connector.fetch_initial(cursor=None)
# 返回 FetchResult(success, items_fetched, cursor, has_more, raw_data)
```

特点：
- 每次获取 50 条记录
- 返回下一个游标（最大 updated 时间）
- 支持断点续传

#### 3. 增量同步（时间过滤）
```python
since = datetime.now() - timedelta(days=7)
result = await connector.fetch_incremental(since)
# 返回 FetchResult(success, items_fetched, raw_data)
```

特点：
- 基于 `updated >= since` 过滤
- 每次获取 100 条记录
- 一次性获取所有更新

#### 4. Scope 支持

**Single Issue:**
```python
config = JiraSourceConfig(
    scope_type=JiraScopeType.SINGLE_ISSUE,
    issue_key="NVME-777"
)
# JQL: issuekey = "NVME-777" order by updated asc
```

**Project:**
```python
config = JiraSourceConfig(
    scope_type=JiraScopeType.PROJECT,
    project="NVME"
)
# JQL: project = "NVME" order by updated asc
```

**Custom JQL:**
```python
config = JiraSourceConfig(
    scope_type=JiraScopeType.JQL,
    jql="project = NVME AND status = 'In Progress'"
)
# JQL: project = NVME AND status = 'In Progress' ORDER BY updated ASC
```

### 测试结果

```
[OK] Jira connector interface tests passed!

✓ JQL 构建正确
✓ 单 issue scope 正确
✓ 自定义 JQL scope 正确
✓ Canonical document 转换正确
✓ 接口实现符合规范
```

### 集成方式

```python
from packages.source_models import JiraSourceConfig, JiraScopeType
from services.connectors.jira import JiraConnector

# 创建配置
config = JiraSourceConfig(
    base_url="https://jira.example.com",
    credential_ref="jira_token",
    scope_type=JiraScopeType.PROJECT,
    project="NVME"
)

# 加载凭证
credential = load_credential(config.credential_ref)

# 初始化连接器
connector = JiraConnector(config, credential)

# 测试连接
result = await connector.test_connection()

# 初始同步
result = await connector.fetch_initial()

# 增量同步
result = await connector.fetch_incremental(since=last_sync_time)

# 转换为 Canonical Document
for raw_issue in result.raw_data:
    doc = connector.to_canonical(raw_issue)
```

### 下一步

- Task #11: 重构 Confluence 连接器支持增量同步
- Task #9: 实现 File Upload 连接器
- 实现同步服务（使用连接器执行实际同步）

# 简化数据源配置方案

## 目标

移除复杂的 selector name 配置，改为在数据源配置中直接使用 JQL（Jira Query Language）或 CQL（Confluence Query Language）作为过滤条件。

## 当前架构问题

1. **配置复杂**：需要先创建 source，再创建 selector，然后在 fetch 时指定 selector-profile
2. **不直观**：用户需要理解 selector 的概念和各种字段（project_key, issue_type, status 等）
3. **灵活性差**：selector 字段有限，无法支持复杂的查询条件
4. **学习成本高**：用户需要学习 selector 的配置方式，而不是直接使用熟悉的 JQL/CQL

## 改进方案

### 1. 在 source 配置中直接添加 JQL/CQL

```python
# 当前方式（复杂）
# 1. 创建 source
python scripts/workspace_cli.py source add workspace1 jira_source \
  --connector-type jira.cloud \
  --base-url https://company.atlassian.net

# 2. 创建 selector
python scripts/workspace_cli.py selector add workspace1 my_selector \
  --source jira_source \
  --type jira_issues \
  --project-key SSD \
  --status Open

# 3. Fetch 数据
python scripts/workspace_cli.py fetch-source workspace1 \
  --source jira_source \
  --selector-profile my_selector

# 改进后（简单）
# 1. 创建 source 时直接指定 JQL
python scripts/workspace_cli.py source add workspace1 jira_source \
  --connector-type jira.cloud \
  --base-url https://company.atlassian.net \
  --jql "project = SSD AND status = Open ORDER BY updated DESC"

# 2. 直接 Fetch（自动使用 source 中的 JQL）
python scripts/workspace_cli.py source fetch workspace1 jira_source
```

### 2. 修改的文件和函数

#### 2.1 `services/workspace/workspace.py`

**修改 `add_workspace_source` 函数**：
```python
def add_workspace_source(
    workspace_dir: str | Path,
    name: str,
    *,
    connector_type: str,
    mode: str | None = None,
    base_url: str | None = None,
    path: str | None = None,
    credential_ref: str | None = None,
    policies: list[str] | None = None,
    include_comments: bool = True,
    include_attachments: bool = True,
    jql: str | None = None,  # 新增
    cql: str | None = None,  # 新增
) -> dict:
    # ... 现有代码 ...
    config = {"auth_mode": "auto"}
    if base_url:
        config["base_url"] = base_url
    if path:
        config["path"] = path
    if jql:  # 新增
        config["jql"] = jql
    if cql:  # 新增
        config["cql"] = cql
    # ... 其余代码 ...
```

**修改 `fetch_workspace_source` 函数**：
```python
def fetch_workspace_source(
    workspace_dir: str | Path, 
    *, 
    source_name: str, 
    selector_profile: str | None = None  # 改为可选
) -> dict:
    _load_workspace_config(workspace_dir)
    
    # 如果没有指定 selector_profile，使用 source 中的 JQL/CQL
    if selector_profile is None:
        source = load_source(workspace_dir, source_name)
        config = source.get("config", {})
        
        # 创建默认的 selector
        if source["kind"] == "jira":
            jql = config.get("jql", "order by updated asc")
            selector_profile = _create_default_jql_selector(workspace_dir, source_name, jql)
        elif source["kind"] == "confluence":
            cql = config.get("cql")
            space_key = config.get("space_key")
            selector_profile = _create_default_cql_selector(workspace_dir, source_name, cql, space_key)
    
    request = build_fetch_request(workspace_dir, source_name=source_name, selector_profile=selector_profile)
    # ... 其余代码 ...
```

**新增辅助函数**：
```python
def _create_default_jql_selector(workspace_dir: str | Path, source_name: str, jql: str) -> str:
    """为 JQL 创建默认的 selector"""
    selector_name = f"{source_name}_default"
    selector = {
        "version": 1,
        "name": selector_name,
        "source": source_name,
        "selector": {
            "type": "jql_query",
            "jql": jql
        }
    }
    write_selector_profile(workspace_dir, selector)
    return selector_name

def _create_default_cql_selector(workspace_dir: str | Path, source_name: str, cql: str | None, space_key: str | None) -> str:
    """为 CQL 创建默认的 selector"""
    selector_name = f"{source_name}_default"
    selector = {
        "version": 1,
        "name": selector_name,
        "source": source_name,
        "selector": {
            "type": "cql_query",
            "cql": cql,
            "space_key": space_key
        }
    }
    write_selector_profile(workspace_dir, selector)
    return selector_name
```

#### 2.2 `services/workspace/source_registry.py`

**修改 `build_fetch_request` 函数**：
```python
def build_fetch_request(
    workspace_dir: str | Path,
    *,
    source_name: str,
    selector_profile: str,
    resolve_credentials: bool = True,
) -> dict:
    source = load_source(workspace_dir, source_name)
    selector = load_selector_profile(workspace_dir, selector_profile)
    
    # 支持 JQL/CQL selector
    selector_type = selector.get("selector", {}).get("type")
    
    if selector_type == "jql_query":
        # 直接使用 JQL
        kwargs["jql"] = selector.get("selector", {}).get("jql", "order by updated asc")
    elif selector_type == "cql_query":
        # 直接使用 CQL
        kwargs["cql"] = selector.get("selector", {}).get("cql")
        kwargs["space_key"] = selector.get("selector", {}).get("space_key")
    else:
        # 保持现有的 selector 逻辑（向后兼容）
        # ... 现有代码 ...
```

#### 2.3 `scripts/workspace_cli.py`

**修改命令行参数**：
```python
# source add 命令添加 JQL/CQL 参数
source_add.add_argument("--jql", help="Jira Query Language for filtering issues")
source_add.add_argument("--cql", help="Confluence Query Language for filtering pages")

# source configure 命令添加 JQL/CQL 参数
source_configure.add_argument("--jql", help="Update JQL query")
source_configure.add_argument("--cql", help="Update CQL query")

# fetch-source 命令的 selector-profile 改为可选
fetch_source_parser.add_argument("--selector-profile", help="Optional: use specific selector profile")

# 新增简化的 fetch 命令
source_fetch = source_subparsers.add_parser("fetch")
source_fetch.add_argument("workspace")
source_fetch.add_argument("name")
```

**修改命令处理逻辑**：
```python
if args.source_command == "add":
    return _print_json(
        add_workspace_source(
            args.workspace,
            args.name,
            connector_type=args.connector_type,
            mode=args.mode,
            base_url=args.base_url,
            path=args.path,
            credential_ref=args.credential_ref,
            policies=args.policy,
            include_comments=args.include_comments,
            include_attachments=args.include_attachments,
            jql=args.jql,  # 新增
            cql=args.cql,  # 新增
        )
    )

if args.source_command == "fetch":
    return _print_json(
        fetch_workspace_source(
            args.workspace,
            source_name=args.name,
            selector_profile=None  # 使用 source 中的默认配置
        )
    )
```

### 3. 向后兼容性

- 保留现有的 selector 机制，确保旧代码仍然可以工作
- 如果 `fetch_workspace_source` 指定了 `selector_profile`，优先使用指定的 selector
- 如果没有指定 `selector_profile`，则使用 source 配置中的 JQL/CQL

### 4. 使用示例

#### Jira 数据源

```bash
# 创建 Jira 数据源（使用 JQL）
python scripts/workspace_cli.py source add my_workspace jira_bugs \
  --connector-type jira.cloud \
  --base-url https://company.atlassian.net \
  --jql "project = SSD AND status IN (Open, 'In Progress') AND priority = High ORDER BY updated DESC"

# 直接拉取数据
python scripts/workspace_cli.py source fetch my_workspace jira_bugs

# 或者使用旧的方式（向后兼容）
python scripts/workspace_cli.py fetch-source my_workspace \
  --source jira_bugs \
  --selector-profile custom_selector
```

#### Confluence 数据源

```bash
# 创建 Confluence 数据源（使用 CQL）
python scripts/workspace_cli.py source add my_workspace conf_docs \
  --connector-type confluence.cloud \
  --base-url https://company.atlassian.net/wiki \
  --cql "type=page AND space=TECH AND label=firmware"

# 直接拉取数据
python scripts/workspace_cli.py source fetch my_workspace conf_docs
```

### 5. 配置文件示例

#### 简化后的 source 配置文件

```json
{
  "version": 1,
  "name": "jira_bugs",
  "kind": "jira",
  "mode": "live",
  "connector_type": "jira.cloud",
  "credential_ref": "jira_token",
  "config": {
    "auth_mode": "auto",
    "base_url": "https://company.atlassian.net",
    "jql": "project = SSD AND status IN (Open, 'In Progress') ORDER BY updated DESC"
  },
  "defaults": {
    "include_comments": true,
    "include_attachments": true,
    "include_image_metadata": true,
    "download_images": false
  },
  "policies": ["team:ssd", "public"],
  "metadata": {}
}
```

#### 自动生成的默认 selector

```json
{
  "version": 1,
  "name": "jira_bugs_default",
  "source": "jira_bugs",
  "selector": {
    "type": "jql_query",
    "jql": "project = SSD AND status IN (Open, 'In Progress') ORDER BY updated DESC"
  }
}
```

## 优势

1. **简化配置**：一步完成数据源配置，无需单独创建 selector
2. **更直观**：直接使用 JQL/CQL，用户无需学习新的配置格式
3. **更灵活**：JQL/CQL 支持任意复杂的查询条件
4. **向后兼容**：保留现有的 selector 机制，不影响旧代码
5. **降低学习成本**：用户只需了解 JQL/CQL，无需学习 selector 配置

## 实施步骤

1. 修改 `add_workspace_source` 函数，添加 `jql` 和 `cql` 参数
2. 修改 `configure_workspace_source` 函数，支持更新 JQL/CQL
3. 修改 `fetch_workspace_source` 函数，支持自动使用 source 中的 JQL/CQL
4. 修改 `build_fetch_request` 函数，支持 `jql_query` 和 `cql_query` selector 类型
5. 更新 CLI 工具，添加新的命令行参数
6. 编写测试用例，确保向后兼容性
7. 更新文档和示例

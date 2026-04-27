# Mock Data 样例数据

这个文件夹包含了 Mock Server 使用的样例 Jira 和 Confluence 数据。

## 📁 文件结构

```
mock-data/
├── jira-issues.json          # Jira 问题列表
├── jira-user.json            # Jira 用户信息
├── jira-projects.json        # Jira 项目列表
├── confluence-pages.json     # Confluence 页面列表
├── confluence-user.json      # Confluence 用户信息
├── confluence-spaces.json    # Confluence 空间列表
└── README.md                 # 本文档
```

## 🔧 Jira 数据

### jira-user.json
用户认证信息，对应 API: `GET /rest/api/3/myself`

### jira-issues.json
包含 2 个测试问题:
- **TEST-1**: 高优先级，进行中
- **TEST-2**: 中优先级，待办

对应 API: `GET /rest/api/3/search`

### jira-projects.json
包含 1 个测试项目:
- **TEST**: Test Project

对应 API: `GET /rest/api/3/project`

## 📄 Confluence 数据

### confluence-user.json
用户认证信息，对应 API: `GET /rest/api/user/current`

### confluence-pages.json
包含 2 个测试页面:
- **Mock Confluence Page 1**: 测试页面 1
- **Mock Confluence Page 2**: 测试页面 2

对应 API: `GET /rest/api/content`

### confluence-spaces.json
包含 1 个测试空间:
- **TEST**: Test Space

对应 API: `GET /rest/api/space`

## 🚀 使用方法

这些 JSON 文件可以用于:

1. **测试数据参考**: 了解 Jira/Confluence API 的响应格式
2. **Mock Server 开发**: 修改 `mock-server.ts` 时参考数据结构
3. **E2E 测试验证**: 验证测试用例的预期数据
4. **API 文档**: 作为 API 响应示例

## 📝 数据说明

### Jira Issue 字段
- `id`: 问题 ID
- `key`: 问题键值 (如 TEST-1)
- `fields.summary`: 问题标题
- `fields.description`: 问题描述
- `fields.status.name`: 状态 (To Do, In Progress, Done)
- `fields.priority.name`: 优先级 (High, Medium, Low)
- `fields.created`: 创建时间
- `fields.updated`: 更新时间

### Confluence Page 字段
- `id`: 页面 ID
- `type`: 类型 (page, blogpost)
- `status`: 状态 (current, archived)
- `title`: 页面标题
- `space.key`: 空间键值
- `space.name`: 空间名称
- `body.storage.value`: 页面内容 (HTML)
- `version.when`: 版本时间
- `version.number`: 版本号

## 🔄 修改数据

如需修改测试数据:

1. 编辑对应的 JSON 文件
2. 更新 `mock-server.ts` 中的响应数据
3. 重启 Mock Server: `npm run mock-server`
4. 重新运行测试验证

## 📚 相关文档

- [Mock Server 使用指南](../README-MOCK-SERVER.md)
- [E2E 测试文档](../README-E2E-TESTS.md)

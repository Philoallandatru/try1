# 工作空间权限控制系统

本文档说明工作空间权限控制系统的设计和使用方法。

## 概述

权限控制系统提供了细粒度的访问控制，支持多用户协作场景。系统定义了四个权限级别和多个具体权限。

## 权限级别

### 1. Owner（所有者）
- **描述**：完全控制工作空间
- **权限**：所有权限，包括删除工作空间
- **适用场景**：工作空间创建者

### 2. Admin（管理员）
- **描述**：管理工作空间和成员
- **权限**：除删除工作空间外的所有权限
- **适用场景**：团队管理员

### 3. Write（读写）
- **描述**：可以创建和修改内容
- **权限**：
  - 查看数据源和文档
  - 上传和更新文档
  - 运行分析
  - 同步数据源
- **限制**：不能删除或管理资源
- **适用场景**：普通协作者

### 4. Read（只读）
- **描述**：只能查看内容
- **权限**：
  - 查看数据源
  - 查看文档
  - 查看分析结果
  - 查看 Profile
- **限制**：不能修改任何内容
- **适用场景**：访客、审计人员

## 具体权限

### 工作空间管理
- `workspace.delete` - 删除工作空间
- `workspace.settings` - 修改工作空间设置
- `workspace.members` - 管理成员权限

### 数据源管理
- `source.create` - 创建数据源
- `source.update` - 更新数据源配置
- `source.delete` - 删除数据源
- `source.sync` - 同步数据源
- `source.view` - 查看数据源

### 文档管理
- `document.upload` - 上传文档
- `document.update` - 更新文档
- `document.delete` - 删除文档
- `document.view` - 查看文档

### 分析功能
- `analysis.run` - 运行分析
- `analysis.view` - 查看分析结果

### Profile 管理
- `profile.create` - 创建 Profile
- `profile.update` - 更新 Profile
- `profile.delete` - 删除 Profile
- `profile.view` - 查看 Profile

## 后端使用

### 基本用法

```python
from apps.portal_runner.permissions import (
    WorkspacePermissions,
    PermissionLevel,
    Permission,
    check_permission,
    get_default_permissions,
)

# 获取用户权限
permissions = get_default_permissions(workspace_dir, user_id="user123")

# 检查权限
if permissions.has_permission(Permission.SOURCE_CREATE):
    # 允许创建数据源
    pass

# 或使用便捷方法
if permissions.can_manage_sources():
    # 允许管理数据源
    pass

# 使用检查函数（会抛出异常）
try:
    check_permission(permissions, Permission.WORKSPACE_DELETE)
    # 执行删除操作
except PermissionError as e:
    # 权限不足
    return {"error": str(e)}
```

### API 集成示例

```python
from fastapi import HTTPException

@app.delete("/api/workspaces/{workspace_dir}")
async def delete_workspace(workspace_dir: str, user_id: str):
    # 获取用户权限
    permissions = get_default_permissions(workspace_dir, user_id)
    
    # 检查权限
    if not permissions.can_delete_workspace():
        raise HTTPException(
            status_code=403,
            detail="Permission denied: workspace.delete required"
        )
    
    # 执行删除
    # ...
```

## 前端使用

### 1. 使用 Permission Context

```typescript
import { usePermissions, Permission } from './PermissionContext';

function MyComponent() {
  const { hasPermission, canManageSources } = usePermissions();
  
  // 检查具体权限
  if (hasPermission(Permission.SOURCE_CREATE)) {
    // 显示创建按钮
  }
  
  // 使用便捷方法
  if (canManageSources()) {
    // 显示管理界面
  }
}
```

### 2. 使用 ProtectedButton 组件

```typescript
import { ProtectedButton, Permission } from './PermissionContext';

function SourceManager() {
  return (
    <div>
      <ProtectedButton
        permission={Permission.SOURCE_CREATE}
        onClick={handleCreate}
      >
        Create Source
      </ProtectedButton>
      
      <ProtectedButton
        permission={Permission.SOURCE_DELETE}
        onClick={handleDelete}
        fallback={<span>Delete (No permission)</span>}
      >
        Delete Source
      </ProtectedButton>
    </div>
  );
}
```

### 3. 使用 ProtectedContent 组件

```typescript
import { ProtectedContent, Permission } from './PermissionContext';

function AdminPanel() {
  return (
    <ProtectedContent
      permission={Permission.WORKSPACE_SETTINGS}
      fallback={<PermissionDenied message="Admin access required" />}
    >
      <div>
        {/* 管理界面 */}
      </div>
    </ProtectedContent>
  );
}
```

### 4. 显示权限级别

```typescript
import { PermissionBadge, PermissionLevel } from './PermissionContext';

function UserInfo({ level }: { level: PermissionLevel }) {
  return (
    <div>
      <span>Your role: </span>
      <PermissionBadge level={level} />
    </div>
  );
}
```

## 权限矩阵

| 权限 | Owner | Admin | Write | Read |
|------|-------|-------|-------|------|
| workspace.delete | ✅ | ❌ | ❌ | ❌ |
| workspace.settings | ✅ | ✅ | ❌ | ❌ |
| workspace.members | ✅ | ✅ | ❌ | ❌ |
| source.create | ✅ | ✅ | ❌ | ❌ |
| source.update | ✅ | ✅ | ❌ | ❌ |
| source.delete | ✅ | ✅ | ❌ | ❌ |
| source.sync | ✅ | ✅ | ✅ | ❌ |
| source.view | ✅ | ✅ | ✅ | ✅ |
| document.upload | ✅ | ✅ | ✅ | ❌ |
| document.update | ✅ | ✅ | ✅ | ❌ |
| document.delete | ✅ | ✅ | ❌ | ❌ |
| document.view | ✅ | ✅ | ✅ | ✅ |
| analysis.run | ✅ | ✅ | ✅ | ❌ |
| analysis.view | ✅ | ✅ | ✅ | ✅ |
| profile.create | ✅ | ✅ | ❌ | ❌ |
| profile.update | ✅ | ✅ | ❌ | ❌ |
| profile.delete | ✅ | ✅ | ❌ | ❌ |
| profile.view | ✅ | ✅ | ✅ | ✅ |

## 当前实现状态

### 已实现
- ✅ 权限级别定义（Owner, Admin, Write, Read）
- ✅ 具体权限枚举
- ✅ 权限矩阵
- ✅ 后端权限检查逻辑
- ✅ 前端 Permission Context
- ✅ 前端权限保护组件（ProtectedButton, ProtectedContent）
- ✅ 权限级别徽章组件
- ✅ 权限样式

### 待实现（未来扩展）
- ⏳ 多用户认证系统
- ⏳ 用户管理界面
- ⏳ 权限分配界面
- ⏳ 权限审计日志
- ⏳ 角色模板
- ⏳ 自定义权限组合

## 默认行为

当前系统处于**单用户模式**，所有用户默认拥有 **Owner** 权限。这意味着：

- 所有操作都被允许
- 不需要额外的权限检查
- UI 不会显示权限限制

当系统升级到多用户模式时，只需：
1. 实现用户认证
2. 在后端 API 中获取真实的用户权限
3. 前端通过 API 获取并设置权限

权限系统的基础设施已经就绪，可以无缝切换到多用户模式。

## 扩展权限系统

### 添加新权限

1. 在后端 `permissions.py` 中添加新权限：

```python
class Permission(str, Enum):
    # 现有权限...
    EXPORT_DATA = "export.data"
```

2. 更新权限矩阵：

```python
PERMISSION_MATRIX: Dict[PermissionLevel, List[Permission]] = {
    PermissionLevel.OWNER: [
        # 现有权限...
        Permission.EXPORT_DATA,
    ],
    # 其他级别...
}
```

3. 在前端 `PermissionContext.tsx` 中同步更新。

### 添加新权限级别

如果需要更细粒度的权限控制，可以添加新的权限级别：

```python
class PermissionLevel(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    CONTRIBUTOR = "contributor"  # 新增
    WRITE = "write"
    READ = "read"
```

然后在权限矩阵中定义该级别的权限。

## 最佳实践

1. **最小权限原则**：只授予用户完成任务所需的最小权限
2. **定期审计**：定期检查用户权限，移除不再需要的权限
3. **权限分离**：敏感操作（如删除）应该需要更高权限
4. **清晰的错误消息**：权限不足时提供清晰的错误提示
5. **前后端一致**：确保前后端权限检查逻辑一致

## 安全考虑

1. **前端权限检查仅用于 UI**：不要依赖前端权限检查来保护数据
2. **后端必须验证**：所有 API 端点都必须在后端验证权限
3. **避免权限提升**：确保用户不能通过 API 提升自己的权限
4. **审计日志**：记录所有权限相关的操作

## 故障排查

### 问题：权限检查总是失败

**解决方案**：
1. 检查 PermissionProvider 是否正确包装了应用
2. 确认权限级别正确设置
3. 查看浏览器控制台是否有错误

### 问题：按钮显示但点击无效

**解决方案**：
1. 检查后端 API 是否也进行了权限检查
2. 确认前后端权限逻辑一致

### 问题：权限徽章不显示

**解决方案**：
1. 确认 `permissions.css` 已导入
2. 检查 CSS 变量是否定义

## 相关文档

- [工作空间管理](WORKSPACE_MANAGER.md)
- [API 文档](API.md)
- [启动指南](../STARTUP_GUIDE.md)

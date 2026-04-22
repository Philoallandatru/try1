"""
Workspace Permission System

定义工作空间权限级别和权限检查逻辑。
"""

from enum import Enum
from typing import Optional, Dict, List
from dataclasses import dataclass


class PermissionLevel(str, Enum):
    """权限级别"""
    OWNER = "owner"          # 所有者：完全控制
    ADMIN = "admin"          # 管理员：管理权限，不能删除工作空间
    WRITE = "write"          # 读写：可以修改内容
    READ = "read"            # 只读：只能查看


class Permission(str, Enum):
    """具体权限"""
    # 工作空间管理
    WORKSPACE_DELETE = "workspace.delete"
    WORKSPACE_SETTINGS = "workspace.settings"
    WORKSPACE_MEMBERS = "workspace.members"

    # 数据源管理
    SOURCE_CREATE = "source.create"
    SOURCE_UPDATE = "source.update"
    SOURCE_DELETE = "source.delete"
    SOURCE_SYNC = "source.sync"
    SOURCE_VIEW = "source.view"

    # 文档管理
    DOCUMENT_UPLOAD = "document.upload"
    DOCUMENT_UPDATE = "document.update"
    DOCUMENT_DELETE = "document.delete"
    DOCUMENT_VIEW = "document.view"

    # 分析功能
    ANALYSIS_RUN = "analysis.run"
    ANALYSIS_VIEW = "analysis.view"
    ANALYSIS_SHARE = "analysis.share"

    # Profile 管理
    PROFILE_CREATE = "profile.create"
    PROFILE_UPDATE = "profile.update"
    PROFILE_DELETE = "profile.delete"
    PROFILE_VIEW = "profile.view"


# 权限级别到具体权限的映射
PERMISSION_MATRIX: Dict[PermissionLevel, List[Permission]] = {
    PermissionLevel.OWNER: [
        # 所有者拥有所有权限
        Permission.WORKSPACE_DELETE,
        Permission.WORKSPACE_SETTINGS,
        Permission.WORKSPACE_MEMBERS,
        Permission.SOURCE_CREATE,
        Permission.SOURCE_UPDATE,
        Permission.SOURCE_DELETE,
        Permission.SOURCE_SYNC,
        Permission.SOURCE_VIEW,
        Permission.DOCUMENT_UPLOAD,
        Permission.DOCUMENT_UPDATE,
        Permission.DOCUMENT_DELETE,
        Permission.DOCUMENT_VIEW,
        Permission.ANALYSIS_RUN,
        Permission.ANALYSIS_VIEW,
        Permission.ANALYSIS_SHARE,
        Permission.PROFILE_CREATE,
        Permission.PROFILE_UPDATE,
        Permission.PROFILE_DELETE,
        Permission.PROFILE_VIEW,
    ],
    PermissionLevel.ADMIN: [
        # 管理员：除了删除工作空间外的所有权限
        Permission.WORKSPACE_SETTINGS,
        Permission.WORKSPACE_MEMBERS,
        Permission.SOURCE_CREATE,
        Permission.SOURCE_UPDATE,
        Permission.SOURCE_DELETE,
        Permission.SOURCE_SYNC,
        Permission.SOURCE_VIEW,
        Permission.DOCUMENT_UPLOAD,
        Permission.DOCUMENT_UPDATE,
        Permission.DOCUMENT_DELETE,
        Permission.DOCUMENT_VIEW,
        Permission.ANALYSIS_RUN,
        Permission.ANALYSIS_VIEW,
        Permission.ANALYSIS_SHARE,
        Permission.PROFILE_CREATE,
        Permission.PROFILE_UPDATE,
        Permission.PROFILE_DELETE,
        Permission.PROFILE_VIEW,
    ],
    PermissionLevel.WRITE: [
        # 读写：可以创建和修改内容，但不能删除或管理
        Permission.SOURCE_VIEW,
        Permission.SOURCE_SYNC,
        Permission.DOCUMENT_UPLOAD,
        Permission.DOCUMENT_UPDATE,
        Permission.DOCUMENT_VIEW,
        Permission.ANALYSIS_RUN,
        Permission.ANALYSIS_VIEW,
        Permission.PROFILE_VIEW,
    ],
    PermissionLevel.READ: [
        # 只读：只能查看
        Permission.SOURCE_VIEW,
        Permission.DOCUMENT_VIEW,
        Permission.ANALYSIS_VIEW,
        Permission.PROFILE_VIEW,
    ],
}


@dataclass
class WorkspacePermissions:
    """工作空间权限配置"""
    workspace_dir: str
    user_id: str
    permission_level: PermissionLevel

    def has_permission(self, permission: Permission) -> bool:
        """检查是否拥有特定权限"""
        allowed_permissions = PERMISSION_MATRIX.get(self.permission_level, [])
        return permission in allowed_permissions

    def can_delete_workspace(self) -> bool:
        """是否可以删除工作空间"""
        return self.has_permission(Permission.WORKSPACE_DELETE)

    def can_manage_sources(self) -> bool:
        """是否可以管理数据源"""
        return self.has_permission(Permission.SOURCE_CREATE)

    def can_upload_documents(self) -> bool:
        """是否可以上传文档"""
        return self.has_permission(Permission.DOCUMENT_UPLOAD)

    def can_run_analysis(self) -> bool:
        """是否可以运行分析"""
        return self.has_permission(Permission.ANALYSIS_RUN)

    def can_manage_profiles(self) -> bool:
        """是否可以管理 Profile"""
        return self.has_permission(Permission.PROFILE_CREATE)

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "workspace_dir": self.workspace_dir,
            "user_id": self.user_id,
            "permission_level": self.permission_level.value,
            "permissions": {
                "can_delete_workspace": self.can_delete_workspace(),
                "can_manage_sources": self.can_manage_sources(),
                "can_upload_documents": self.can_upload_documents(),
                "can_run_analysis": self.can_run_analysis(),
                "can_manage_profiles": self.can_manage_profiles(),
            }
        }


class PermissionError(Exception):
    """权限错误"""
    pass


def check_permission(
    workspace_permissions: WorkspacePermissions,
    required_permission: Permission
) -> None:
    """
    检查权限，如果没有权限则抛出异常

    Args:
        workspace_permissions: 工作空间权限
        required_permission: 需要的权限

    Raises:
        PermissionError: 如果没有权限
    """
    if not workspace_permissions.has_permission(required_permission):
        raise PermissionError(
            f"Permission denied: {required_permission.value} required, "
            f"but user has {workspace_permissions.permission_level.value} level"
        )


def get_default_permissions(workspace_dir: str, user_id: str = "default") -> WorkspacePermissions:
    """
    获取默认权限（所有者权限）

    在当前单用户模式下，所有用户都是所有者
    """
    return WorkspacePermissions(
        workspace_dir=workspace_dir,
        user_id=user_id,
        permission_level=PermissionLevel.OWNER
    )


def get_permission_level_description(level: PermissionLevel) -> str:
    """获取权限级别的描述"""
    descriptions = {
        PermissionLevel.OWNER: "所有者 - 完全控制工作空间，包括删除",
        PermissionLevel.ADMIN: "管理员 - 管理工作空间和成员，但不能删除工作空间",
        PermissionLevel.WRITE: "读写 - 可以创建和修改内容，但不能删除或管理",
        PermissionLevel.READ: "只读 - 只能查看内容，不能修改",
    }
    return descriptions.get(level, "未知权限级别")

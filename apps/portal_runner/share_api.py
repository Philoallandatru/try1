"""
Analysis Sharing API

提供分析结果分享功能，支持生成分享链接、权限控制和过期管理。
"""

from __future__ import annotations

import json
import secrets
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field


class SharePermission(str):
    """分享权限级别"""
    VIEW = "view"
    COMMENT = "comment"
    EDIT = "edit"


class ShareSettings(BaseModel):
    """分享设置"""
    share_id: str = Field(description="分享ID")
    analysis_id: str = Field(description="分析ID")
    workspace_dir: str = Field(description="工作空间目录")
    created_by: str = Field(description="创建者")
    created_at: str = Field(description="创建时间")
    expires_at: Optional[str] = Field(None, description="过期时间")
    permissions: str = Field(default="view", description="权限级别")
    require_auth: bool = Field(default=True, description="是否需要认证")
    allowed_users: Optional[List[str]] = Field(None, description="允许的用户列表")
    access_count: int = Field(default=0, description="访问次数")
    last_accessed: Optional[str] = Field(None, description="最后访问时间")


class ShareStorage:
    """分享数据存储"""

    def __init__(self, storage_dir: str | Path):
        self.storage_dir = Path(storage_dir)
        self.shares_file = self.storage_dir / "shares.json"
        self._ensure_storage()

    def _ensure_storage(self):
        """确保存储目录和文件存在"""
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        if not self.shares_file.exists():
            self.shares_file.write_text("{}")

    def _load_shares(self) -> Dict[str, Dict[str, Any]]:
        """加载所有分享"""
        try:
            return json.loads(self.shares_file.read_text())
        except Exception:
            return {}

    def _save_shares(self, shares: Dict[str, Dict[str, Any]]):
        """保存所有分享"""
        self.shares_file.write_text(json.dumps(shares, indent=2))

    def create_share(self, settings: ShareSettings) -> ShareSettings:
        """创建分享"""
        shares = self._load_shares()
        shares[settings.share_id] = settings.model_dump()
        self._save_shares(shares)
        return settings

    def get_share(self, share_id: str) -> Optional[ShareSettings]:
        """获取分享"""
        shares = self._load_shares()
        share_data = shares.get(share_id)
        if share_data:
            return ShareSettings(**share_data)
        return None

    def update_share(self, share_id: str, updates: Dict[str, Any]) -> Optional[ShareSettings]:
        """更新分享"""
        shares = self._load_shares()
        if share_id not in shares:
            return None

        shares[share_id].update(updates)
        self._save_shares(shares)
        return ShareSettings(**shares[share_id])

    def delete_share(self, share_id: str) -> bool:
        """删除分享"""
        shares = self._load_shares()
        if share_id in shares:
            del shares[share_id]
            self._save_shares(shares)
            return True
        return False

    def list_shares(
        self,
        workspace_dir: Optional[str] = None,
        created_by: Optional[str] = None,
    ) -> List[ShareSettings]:
        """列出分享"""
        shares = self._load_shares()
        results = []

        for share_data in shares.values():
            if workspace_dir and share_data.get("workspace_dir") != workspace_dir:
                continue
            if created_by and share_data.get("created_by") != created_by:
                continue
            results.append(ShareSettings(**share_data))

        return results

    def increment_access_count(self, share_id: str):
        """增加访问计数"""
        now = datetime.utcnow().isoformat()
        self.update_share(
            share_id,
            {
                "access_count": (self.get_share(share_id).access_count if self.get_share(share_id) else 0) + 1,
                "last_accessed": now,
            }
        )

    def cleanup_expired(self) -> int:
        """清理过期的分享"""
        shares = self._load_shares()
        now = datetime.utcnow()
        expired_ids = []

        for share_id, share_data in shares.items():
            expires_at = share_data.get("expires_at")
            if expires_at:
                try:
                    expiry_time = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                    if expiry_time < now:
                        expired_ids.append(share_id)
                except Exception:
                    pass

        for share_id in expired_ids:
            del shares[share_id]

        if expired_ids:
            self._save_shares(shares)

        return len(expired_ids)


def generate_share_id() -> str:
    """生成唯一的分享ID"""
    return secrets.token_urlsafe(16)


def create_share_response(
    workspace_dir: str,
    analysis_id: str,
    user_id: str,
    permissions: str = "view",
    expires_in: Optional[str] = None,
    require_auth: bool = True,
    allowed_users: Optional[List[str]] = None,
    storage: Optional[ShareStorage] = None,
) -> dict:
    """
    创建分享链接

    Args:
        workspace_dir: 工作空间目录
        analysis_id: 分析ID
        user_id: 创建者ID
        permissions: 权限级别 (view, comment, edit)
        expires_in: 过期时间 (例如: "7d", "24h", "1h")
        require_auth: 是否需要认证
        allowed_users: 允许的用户列表
        storage: 分享存储实例

    Returns:
        包含分享信息的字典
    """
    if storage is None:
        storage = ShareStorage(".local/shares")

    share_id = generate_share_id()
    now = datetime.utcnow()
    created_at = now.isoformat()

    # 计算过期时间
    expires_at = None
    if expires_in:
        expires_at = calculate_expiry(now, expires_in).isoformat()

    settings = ShareSettings(
        share_id=share_id,
        analysis_id=analysis_id,
        workspace_dir=workspace_dir,
        created_by=user_id,
        created_at=created_at,
        expires_at=expires_at,
        permissions=permissions,
        require_auth=require_auth,
        allowed_users=allowed_users,
    )

    storage.create_share(settings)

    return {
        "share_id": share_id,
        "share_url": f"/shared/{share_id}",
        "created_at": created_at,
        "expires_at": expires_at,
        "permissions": permissions,
        "require_auth": require_auth,
    }


def get_shared_analysis_response(
    share_id: str,
    user_id: Optional[str] = None,
    storage: Optional[ShareStorage] = None,
) -> dict:
    """
    获取分享的分析结果

    Args:
        share_id: 分享ID
        user_id: 访问用户ID
        storage: 分享存储实例

    Returns:
        包含分析结果的字典

    Raises:
        ValueError: 如果分享不存在、已过期或无权限访问
    """
    if storage is None:
        storage = ShareStorage(".local/shares")

    share = storage.get_share(share_id)
    if not share:
        raise ValueError("Share not found")

    # 检查是否过期
    if share.expires_at:
        expiry_time = datetime.fromisoformat(share.expires_at.replace("Z", "+00:00"))
        if expiry_time < datetime.utcnow():
            raise ValueError("Share has expired")

    # 检查认证要求
    if share.require_auth and not user_id:
        raise ValueError("Authentication required")

    # 检查用户权限
    if share.allowed_users and user_id not in share.allowed_users:
        raise ValueError("Access denied")

    # 增加访问计数
    storage.increment_access_count(share_id)

    return {
        "share_id": share_id,
        "analysis_id": share.analysis_id,
        "workspace_dir": share.workspace_dir,
        "permissions": share.permissions,
        "created_at": share.created_at,
        "expires_at": share.expires_at,
        "access_count": share.access_count + 1,
    }


def list_shares_response(
    workspace_dir: Optional[str] = None,
    user_id: Optional[str] = None,
    storage: Optional[ShareStorage] = None,
) -> dict:
    """
    列出分享

    Args:
        workspace_dir: 工作空间目录（可选）
        user_id: 用户ID（可选）
        storage: 分享存储实例

    Returns:
        包含分享列表的字典
    """
    if storage is None:
        storage = ShareStorage(".local/shares")

    shares = storage.list_shares(workspace_dir=workspace_dir, created_by=user_id)

    return {
        "shares": [
            {
                "share_id": share.share_id,
                "analysis_id": share.analysis_id,
                "workspace_dir": share.workspace_dir,
                "created_at": share.created_at,
                "expires_at": share.expires_at,
                "permissions": share.permissions,
                "require_auth": share.require_auth,
                "access_count": share.access_count,
                "last_accessed": share.last_accessed,
            }
            for share in shares
        ]
    }


def delete_share_response(
    share_id: str,
    user_id: str,
    storage: Optional[ShareStorage] = None,
) -> dict:
    """
    删除分享

    Args:
        share_id: 分享ID
        user_id: 用户ID
        storage: 分享存储实例

    Returns:
        删除结果

    Raises:
        ValueError: 如果分享不存在或无权限删除
    """
    if storage is None:
        storage = ShareStorage(".local/shares")

    share = storage.get_share(share_id)
    if not share:
        raise ValueError("Share not found")

    if share.created_by != user_id:
        raise ValueError("Permission denied")

    storage.delete_share(share_id)

    return {"status": "deleted", "share_id": share_id}


def calculate_expiry(base_time: datetime, expires_in: str) -> datetime:
    """
    计算过期时间

    Args:
        base_time: 基准时间
        expires_in: 过期时间字符串 (例如: "7d", "24h", "1h")

    Returns:
        过期时间
    """
    if expires_in.endswith("h"):
        hours = int(expires_in[:-1])
        return base_time + timedelta(hours=hours)
    elif expires_in.endswith("d"):
        days = int(expires_in[:-1])
        return base_time + timedelta(days=days)
    else:
        raise ValueError(f"Invalid expiry format: {expires_in}")

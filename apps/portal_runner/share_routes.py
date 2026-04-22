"""
Share Routes

提供分享功能的 API 路由。
"""

from fastapi import APIRouter, HTTPException, Header
from typing import Optional, List
from pydantic import BaseModel

from apps.portal_runner.share_api import (
    ShareStorage,
    create_share_response,
    get_shared_analysis_response,
    list_shares_response,
    delete_share_response,
)


class CreateShareRequest(BaseModel):
    """创建分享请求"""
    workspace_dir: str
    analysis_id: str
    permissions: str = "view"
    expires_in: Optional[str] = None
    require_auth: bool = True
    allowed_users: Optional[List[str]] = None


class ShareResponse(BaseModel):
    """分享响应"""
    share_id: str
    share_url: str
    created_at: str
    expires_at: Optional[str]
    permissions: str
    require_auth: bool


class SharedAnalysisResponse(BaseModel):
    """分享的分析响应"""
    share_id: str
    analysis_id: str
    workspace_dir: str
    permissions: str
    created_at: str
    expires_at: Optional[str]
    access_count: int


class ShareListItem(BaseModel):
    """分享列表项"""
    share_id: str
    analysis_id: str
    workspace_dir: str
    created_at: str
    expires_at: Optional[str]
    permissions: str
    require_auth: bool
    access_count: int
    last_accessed: Optional[str]


class ShareListResponse(BaseModel):
    """分享列表响应"""
    shares: List[ShareListItem]


class DeleteShareResponse(BaseModel):
    """删除分享响应"""
    status: str
    share_id: str


def create_share_router(storage_dir: str = ".local/shares") -> APIRouter:
    """创建分享路由"""
    router = APIRouter(prefix="/api/shares", tags=["shares"])
    share_storage = ShareStorage(storage_dir)

    @router.post("", response_model=ShareResponse)
    async def create_share(
        request: CreateShareRequest,
        x_user_id: Optional[str] = Header(None),
    ):
        """
        创建分享链接

        - **workspace_dir**: 工作空间目录
        - **analysis_id**: 分析ID
        - **permissions**: 权限级别 (view, comment, edit)
        - **expires_in**: 过期时间 (例如: "7d", "24h", "1h")
        - **require_auth**: 是否需要认证
        - **allowed_users**: 允许的用户列表
        """
        user_id = x_user_id or "anonymous"

        try:
            result = create_share_response(
                workspace_dir=request.workspace_dir,
                analysis_id=request.analysis_id,
                user_id=user_id,
                permissions=request.permissions,
                expires_in=request.expires_in,
                require_auth=request.require_auth,
                allowed_users=request.allowed_users,
                storage=share_storage,
            )
            return ShareResponse(**result)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.get("/{share_id}", response_model=SharedAnalysisResponse)
    async def get_shared_analysis(
        share_id: str,
        x_user_id: Optional[str] = Header(None),
    ):
        """
        获取分享的分析结果

        - **share_id**: 分享ID
        """
        user_id = x_user_id

        try:
            result = get_shared_analysis_response(
                share_id=share_id,
                user_id=user_id,
                storage=share_storage,
            )
            return SharedAnalysisResponse(**result)
        except ValueError as e:
            if "not found" in str(e).lower():
                raise HTTPException(status_code=404, detail=str(e))
            elif "expired" in str(e).lower():
                raise HTTPException(status_code=410, detail=str(e))
            elif "denied" in str(e).lower() or "required" in str(e).lower():
                raise HTTPException(status_code=403, detail=str(e))
            else:
                raise HTTPException(status_code=400, detail=str(e))

    @router.get("", response_model=ShareListResponse)
    async def list_shares(
        workspace_dir: Optional[str] = None,
        x_user_id: Optional[str] = Header(None),
    ):
        """
        列出分享

        - **workspace_dir**: 工作空间目录（可选，筛选特定工作空间的分享）
        """
        user_id = x_user_id

        try:
            result = list_shares_response(
                workspace_dir=workspace_dir,
                user_id=user_id,
                storage=share_storage,
            )
            return ShareListResponse(**result)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.delete("/{share_id}", response_model=DeleteShareResponse)
    async def delete_share(
        share_id: str,
        x_user_id: Optional[str] = Header(None),
    ):
        """
        删除分享

        - **share_id**: 分享ID
        """
        user_id = x_user_id or "anonymous"

        try:
            result = delete_share_response(
                share_id=share_id,
                user_id=user_id,
                storage=share_storage,
            )
            return DeleteShareResponse(**result)
        except ValueError as e:
            if "not found" in str(e).lower():
                raise HTTPException(status_code=404, detail=str(e))
            elif "denied" in str(e).lower():
                raise HTTPException(status_code=403, detail=str(e))
            else:
                raise HTTPException(status_code=400, detail=str(e))

    return router

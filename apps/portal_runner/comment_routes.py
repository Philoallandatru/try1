"""
评论和标注路由
"""

from fastapi import APIRouter, HTTPException, Header
from typing import Optional, List, Dict, Any
from pydantic import BaseModel

from .comment_api import CommentManager, Comment, Annotation


router = APIRouter(prefix="/api/comments", tags=["comments"])
comment_manager = CommentManager()


class CreateCommentRequest(BaseModel):
    """创建评论请求"""
    analysis_id: str
    workspace_dir: str
    content: str
    parent_id: Optional[str] = None
    annotation: Optional[Dict[str, Any]] = None


class UpdateCommentRequest(BaseModel):
    """更新评论请求"""
    content: Optional[str] = None
    resolved: Optional[bool] = None


@router.post("", response_model=Comment)
async def create_comment(
    request: CreateCommentRequest,
    x_user_id: str = Header(..., alias="X-User-Id"),
    x_user_name: str = Header(default="Anonymous", alias="X-User-Name")
):
    """
    创建评论

    Args:
        request: 创建评论请求
        x_user_id: 用户 ID（从请求头获取）
        x_user_name: 用户名（从请求头获取）

    Returns:
        创建的评论对象
    """
    try:
        comment = comment_manager.create_comment(
            analysis_id=request.analysis_id,
            workspace_dir=request.workspace_dir,
            user_id=x_user_id,
            user_name=x_user_name,
            content=request.content,
            parent_id=request.parent_id,
            annotation=request.annotation
        )
        return comment
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=List[Comment])
async def get_comments(
    workspace_dir: str,
    analysis_id: str,
    include_resolved: bool = True
):
    """
    获取评论列表

    Args:
        workspace_dir: 工作空间目录
        analysis_id: 分析 ID
        include_resolved: 是否包含已解决的评论

    Returns:
        评论列表
    """
    try:
        comments = comment_manager.get_comments(
            workspace_dir=workspace_dir,
            analysis_id=analysis_id,
            include_resolved=include_resolved
        )
        return comments
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{comment_id}", response_model=Comment)
async def get_comment(
    comment_id: str,
    workspace_dir: str,
    analysis_id: str
):
    """
    获取单个评论

    Args:
        comment_id: 评论 ID
        workspace_dir: 工作空间目录
        analysis_id: 分析 ID

    Returns:
        评论对象
    """
    comment = comment_manager.get_comment(
        workspace_dir=workspace_dir,
        analysis_id=analysis_id,
        comment_id=comment_id
    )

    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    return comment


@router.put("/{comment_id}", response_model=Comment)
async def update_comment(
    comment_id: str,
    request: UpdateCommentRequest,
    workspace_dir: str,
    analysis_id: str,
    x_user_id: str = Header(..., alias="X-User-Id")
):
    """
    更新评论

    Args:
        comment_id: 评论 ID
        request: 更新评论请求
        workspace_dir: 工作空间目录
        analysis_id: 分析 ID
        x_user_id: 用户 ID（从请求头获取）

    Returns:
        更新后的评论对象
    """
    # 检查评论是否存在
    existing_comment = comment_manager.get_comment(
        workspace_dir=workspace_dir,
        analysis_id=analysis_id,
        comment_id=comment_id
    )

    if not existing_comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    # 检查权限（只有评论作者可以编辑内容）
    if request.content is not None and existing_comment.user_id != x_user_id:
        raise HTTPException(status_code=403, detail="You can only edit your own comments")

    # 更新评论
    updated_comment = comment_manager.update_comment(
        workspace_dir=workspace_dir,
        analysis_id=analysis_id,
        comment_id=comment_id,
        content=request.content,
        resolved=request.resolved
    )

    if not updated_comment:
        raise HTTPException(status_code=500, detail="Failed to update comment")

    return updated_comment


@router.delete("/{comment_id}")
async def delete_comment(
    comment_id: str,
    workspace_dir: str,
    analysis_id: str,
    x_user_id: str = Header(..., alias="X-User-Id")
):
    """
    删除评论

    Args:
        comment_id: 评论 ID
        workspace_dir: 工作空间目录
        analysis_id: 分析 ID
        x_user_id: 用户 ID（从请求头获取）

    Returns:
        删除结果
    """
    # 检查评论是否存在
    existing_comment = comment_manager.get_comment(
        workspace_dir=workspace_dir,
        analysis_id=analysis_id,
        comment_id=comment_id
    )

    if not existing_comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    # 检查权限（只有评论作者可以删除）
    if existing_comment.user_id != x_user_id:
        raise HTTPException(status_code=403, detail="You can only delete your own comments")

    # 删除评论
    success = comment_manager.delete_comment(
        workspace_dir=workspace_dir,
        analysis_id=analysis_id,
        comment_id=comment_id
    )

    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete comment")

    return {"status": "deleted", "comment_id": comment_id}


@router.get("/{comment_id}/thread", response_model=List[Comment])
async def get_comment_thread(
    comment_id: str,
    workspace_dir: str,
    analysis_id: str
):
    """
    获取评论线程（包括所有回复）

    Args:
        comment_id: 根评论 ID
        workspace_dir: 工作空间目录
        analysis_id: 分析 ID

    Returns:
        评论线程列表
    """
    thread = comment_manager.get_comment_thread(
        workspace_dir=workspace_dir,
        analysis_id=analysis_id,
        comment_id=comment_id
    )

    if not thread:
        raise HTTPException(status_code=404, detail="Comment not found")

    return thread


@router.get("/annotations/list")
async def get_annotations(
    workspace_dir: str,
    analysis_id: str
):
    """
    获取所有标注

    Args:
        workspace_dir: 工作空间目录
        analysis_id: 分析 ID

    Returns:
        标注列表
    """
    try:
        annotations = comment_manager.get_annotations(
            workspace_dir=workspace_dir,
            analysis_id=analysis_id
        )
        return {"annotations": annotations}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

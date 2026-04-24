"""Chat API routes."""

from fastapi import APIRouter, HTTPException, Request


def create_chat_router(workspace_root: str) -> APIRouter:
    """Create the chat router."""
    from apps.portal_runner.chat_api import (
        load_chat_sessions,
        create_chat_session,
        load_chat_session,
        chat_with_source,
    )
    from apps.portal_runner.model_config_api import load_model_config

    router = APIRouter(prefix="/api/chat", tags=["chat"])

    @router.get("/sessions")
    async def get_chat_sessions() -> dict:
        """Get all chat sessions."""
        try:
            sessions = load_chat_sessions(workspace_root)
            return {"success": True, "sessions": sessions}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/sessions")
    async def new_chat_session(request: Request) -> dict:
        """Create a new chat session."""
        try:
            payload = await request.json()
            source_name = payload.get("source_name")
            if not source_name:
                raise ValueError("source_name is required")

            session = create_chat_session(workspace_root, source_name)
            return {"success": True, "session": session}
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/sessions/{session_id}")
    async def get_chat_session(session_id: str) -> dict:
        """Get a specific chat session."""
        try:
            session = load_chat_session(workspace_root, session_id)
            return {"success": True, "session": session}
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/sessions/{session_id}/messages")
    async def send_message(session_id: str, request: Request) -> dict:
        """Send a message in a chat session."""
        try:
            payload = await request.json()
            message = payload.get("message")
            if not message:
                raise ValueError("message is required")

            # Load model config
            model_config = load_model_config(workspace_root)

            # Chat with source
            result = chat_with_source(workspace_root, session_id, message, model_config)
            return {"success": True, **result}
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return router

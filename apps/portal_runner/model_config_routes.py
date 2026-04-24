"""Model Configuration API routes."""

from fastapi import APIRouter, HTTPException, Request


def create_model_config_router(workspace_root: str) -> APIRouter:
    """Create the model configuration router."""
    from apps.portal_runner.model_config_api import (
        load_model_config,
        save_model_config,
        test_model_connection,
    )

    router = APIRouter(prefix="/api/model-config", tags=["model-config"])

    @router.get("")
    async def get_model_config() -> dict:
        """Get the current model configuration."""
        try:
            config = load_model_config(workspace_root)
            return {"success": True, "config": config}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("")
    async def update_model_config(request: Request) -> dict:
        """Update the model configuration."""
        try:
            payload = await request.json()
            result = save_model_config(workspace_root, payload)
            return result
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/test")
    async def test_connection() -> dict:
        """Test the connection to the configured model."""
        try:
            result = test_model_connection(workspace_root)
            return result
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return router

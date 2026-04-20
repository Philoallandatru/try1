from argparse import ArgumentParser
from pathlib import Path
from apps.portal_runner.auth import PortalRunnerAuthError, verify_bearer_token
from apps.portal_runner.config import DEFAULT_CONFIG_PATH, PortalRunnerConfigError, load_config, validate_bind_security
from apps.portal_runner.demo_workspace import ensure_demo_workspace
from apps.portal_runner.pipeline_registry import list_pipeline_definitions
from apps.portal_runner.product_api import (
    analyze_jira_response,
    create_profile,
    create_selector,
    create_source,
    create_workspace,
    duplicate_profile,
    list_profiles_response,
    list_sources_response,
    list_workspaces,
    refresh_source_response,
    ingest_mineru_spec_asset,
    list_selectors_response,
    list_spec_assets_response,
    require_mineru_spec_asset,
    set_default_profile,
    profile_detail_response,
    selector_detail_response,
    source_detail_response,
    test_source_response,
    update_profile,
    update_source,
    validate_profile_response,
    verify_run_llm_response,
    workspace_artifact_response,
    workspace_run_detail_response,
    workspace_runs_response,
    workspace_status,
)
from apps.portal_runner.runner import PortalPipelineRunner
from apps.portal_runner.schemas import PipelineInput
from apps.portal_runner.source_routes import create_source_router
from apps.portal_runner.retrieval_routes import create_retrieval_router
from apps.portal_runner.storage import PortalRunnerStorage
from services.workspace import init_workspace
from services.workspace.spec_assets import load_spec_asset_registry


def create_app(config_path: str | Path = DEFAULT_CONFIG_PATH, *, host: str = "127.0.0.1"):
    try:
        from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Request, UploadFile
        from fastapi.responses import FileResponse
        from fastapi.staticfiles import StaticFiles
    except ImportError as exc:
        raise RuntimeError("FastAPI runner dependencies are required. Install with .[portal-runner].") from exc

    config = load_config(config_path)
    validate_bind_security(config, host)
    storage = PortalRunnerStorage(
        runs_root=config.workspace.runs_root,
        uploads_root=config.workspace.uploads_root,
    )
    runner = PortalPipelineRunner(config=config, storage=storage)

    app = FastAPI(title="SSD Knowledge Portal Runner")

    def require_auth(authorization: str | None = Header(default=None)) -> None:
        try:
            verify_bearer_token(authorization, config.server.runner_token)
        except PortalRunnerAuthError as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc

    @app.get("/api/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.get("/api/config/status")
    def config_status(_: None = Depends(require_auth)) -> dict:
        return {"config": config.public_status()}

    @app.post("/api/auth/check")
    def auth_check(_: None = Depends(require_auth)) -> dict:
        return {"authenticated": True}

    @app.get("/api/pipelines")
    def pipelines(_: None = Depends(require_auth)) -> dict:
        enabled = {
            pipeline_id: pipeline.enabled
            for pipeline_id, pipeline in config.pipelines.items()
        }
        return {"pipelines": list_pipeline_definitions(enabled)}

    @app.get("/api/spec-assets")
    def spec_assets(_: None = Depends(require_auth)) -> dict:
        init_workspace(config.workspace.spec_assets_workspace)
        registry = load_spec_asset_registry(config.workspace.spec_assets_workspace)
        return {"workspace": str(config.workspace.spec_assets_workspace), "assets": registry.get("assets", [])}

    @app.get("/api/workspaces")
    def workspaces(_: None = Depends(require_auth)) -> dict:
        demo = ensure_demo_workspace(config.workspace.root, config.workspace.spec_assets_workspace)
        return list_workspaces(config.workspace.root, demo_workspace=demo)

    @app.post("/api/workspaces")
    async def workspace_create(request: Request, _: None = Depends(require_auth)) -> dict:
        try:
            return create_workspace(config.workspace.root, await request.json())
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/api/workspace/status")
    def workspace_status_endpoint(workspace_dir: str, _: None = Depends(require_auth)) -> dict:
        try:
            return workspace_status(workspace_dir)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/api/workspace/sources")
    def workspace_sources(workspace_dir: str, _: None = Depends(require_auth)) -> dict:
        try:
            return list_sources_response(workspace_dir)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/workspace/sources")
    async def workspace_source_create(request: Request, _: None = Depends(require_auth)) -> dict:
        try:
            return create_source(await request.json())
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/api/workspace/sources/{source_name}")
    def workspace_source_detail(source_name: str, workspace_dir: str, _: None = Depends(require_auth)) -> dict:
        try:
            return source_detail_response(workspace_dir, source_name)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/api/workspace/selectors")
    def workspace_selectors(workspace_dir: str, _: None = Depends(require_auth)) -> dict:
        try:
            return list_selectors_response(workspace_dir)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/workspace/selectors")
    async def workspace_selector_create(request: Request, _: None = Depends(require_auth)) -> dict:
        try:
            return create_selector(await request.json())
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/api/workspace/selectors/{selector_name}")
    def workspace_selector_detail(selector_name: str, workspace_dir: str, _: None = Depends(require_auth)) -> dict:
        try:
            return selector_detail_response(workspace_dir, selector_name)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.patch("/api/workspace/sources/{source_name}")
    async def workspace_source_update(source_name: str, request: Request, _: None = Depends(require_auth)) -> dict:
        try:
            return update_source(source_name, await request.json())
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/workspace/sources/{source_name}/test")
    async def workspace_source_test(source_name: str, request: Request, _: None = Depends(require_auth)) -> dict:
        try:
            return test_source_response(source_name, await request.json())
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/workspace/sources/{source_name}/refresh")
    async def workspace_source_refresh(source_name: str, request: Request, _: None = Depends(require_auth)) -> dict:
        try:
            return refresh_source_response(source_name, await request.json())
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/api/workspace/profiles")
    def workspace_profiles(workspace_dir: str, _: None = Depends(require_auth)) -> dict:
        try:
            return list_profiles_response(workspace_dir)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/workspace/profiles")
    async def workspace_profile_create(request: Request, _: None = Depends(require_auth)) -> dict:
        try:
            return create_profile(await request.json())
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/api/workspace/profiles/{profile_name}")
    def workspace_profile_detail(profile_name: str, workspace_dir: str, _: None = Depends(require_auth)) -> dict:
        try:
            return profile_detail_response(workspace_dir, profile_name)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.patch("/api/workspace/profiles/{profile_name}")
    async def workspace_profile_update(profile_name: str, request: Request, _: None = Depends(require_auth)) -> dict:
        try:
            return update_profile(profile_name, await request.json())
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/workspace/profiles/{profile_name}/duplicate")
    async def workspace_profile_duplicate(profile_name: str, request: Request, _: None = Depends(require_auth)) -> dict:
        try:
            return duplicate_profile(profile_name, await request.json())
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/workspace/profiles/{profile_name}/validate")
    async def workspace_profile_validate(profile_name: str, request: Request, _: None = Depends(require_auth)) -> dict:
        try:
            return validate_profile_response(profile_name, await request.json())
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/workspace/profiles/{profile_name}/default")
    async def workspace_profile_default(profile_name: str, request: Request, _: None = Depends(require_auth)) -> dict:
        try:
            return set_default_profile(profile_name, await request.json())
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/api/workspace/runs")
    def workspace_runs(workspace_dir: str, _: None = Depends(require_auth)) -> dict:
        try:
            return workspace_runs_response(workspace_dir)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/api/workspace/runs/{run_id}")
    def workspace_run_detail(run_id: str, workspace_dir: str, _: None = Depends(require_auth)) -> dict:
        try:
            return workspace_run_detail_response(workspace_dir, run_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/api/workspace/runs/{run_id}/artifacts/{artifact_type}")
    def workspace_run_artifact(run_id: str, artifact_type: str, workspace_dir: str, _: None = Depends(require_auth)) -> dict:
        try:
            return workspace_artifact_response(workspace_dir, run_id, artifact_type)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.post("/api/workspace/runs/{run_id}/verify-llm")
    async def workspace_run_verify_llm(run_id: str, request: Request, _: None = Depends(require_auth)) -> dict:
        try:
            return verify_run_llm_response(run_id, await request.json())
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/api/workspace/spec-assets/{asset_id}/require-mineru")
    def workspace_spec_asset_require_mineru(asset_id: str, workspace_dir: str, _: None = Depends(require_auth)) -> dict:
        try:
            return require_mineru_spec_asset(workspace_dir, asset_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/api/workspace/spec-assets")
    def workspace_spec_assets(workspace_dir: str, _: None = Depends(require_auth)) -> dict:
        try:
            return list_spec_assets_response(workspace_dir)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/workspace/spec-assets/ingest")
    async def workspace_spec_asset_ingest(request: Request, _: None = Depends(require_auth)) -> dict:
        try:
            return ingest_mineru_spec_asset(await request.json())
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/workspace/analyze-jira")
    async def workspace_analyze_jira(
        request: Request,
        _: None = Depends(require_auth),
    ) -> dict:
        payload = await request.json()
        try:
            return analyze_jira_response(payload)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/runs")
    async def create_run(
        request: Request,
        _: None = Depends(require_auth),
        pipeline_id: str = Form(...),
        jira_issue_key: str | None = Form(None),
        confluence_page_id: str | None = Form(None),
        confluence_page_ids: str | None = Form(None),
        confluence_scope: str | None = Form(None),
        confluence_root_page_id: str | None = Form(None),
        confluence_space_key: str | None = Form(None),
        confluence_label: str | None = Form(None),
        confluence_modified_from: str | None = Form(None),
        confluence_modified_to: str | None = Form(None),
        confluence_max_depth: int | None = Form(None),
        spec_asset_id: str | None = Form(None),
        preferred_parser: str | None = Form(None),
        publish_wiki: bool | None = Form(None),
        topic_slug: str | None = Form(None),
        topic_title: str | None = Form(None),
        mock_response: str | None = Form(None),
        profile: str | None = Form(None),
        prompt: str | None = Form(None),
        pdf: UploadFile | None = File(None),
    ) -> dict:
        upload = None
        if pdf is not None:
            content = await pdf.read()
            upload = {
                "filename": pdf.filename or "upload.pdf",
                "content": content,
            }
        pipeline_input = PipelineInput(
            pipeline_id=pipeline_id,
            jira_issue_key=_blank_to_none(jira_issue_key),
            confluence_page_id=_blank_to_none(confluence_page_id),
            confluence_page_ids=_blank_to_none(confluence_page_ids),
            confluence_scope=_blank_to_none(confluence_scope),
            confluence_root_page_id=_blank_to_none(confluence_root_page_id),
            confluence_space_key=_blank_to_none(confluence_space_key),
            confluence_label=_blank_to_none(confluence_label),
            confluence_modified_from=_blank_to_none(confluence_modified_from),
            confluence_modified_to=_blank_to_none(confluence_modified_to),
            confluence_max_depth=confluence_max_depth,
            spec_asset_id=_blank_to_none(spec_asset_id),
            preferred_parser=_blank_to_none(preferred_parser),
            publish_wiki=publish_wiki,
            topic_slug=_blank_to_none(topic_slug),
            topic_title=_blank_to_none(topic_title),
            mock_response=_blank_to_none(mock_response),
            profile=_blank_to_none(profile),
            prompt=_blank_to_none(prompt),
        )
        try:
            manifest = runner.create_run(
                pipeline_input=pipeline_input,
                client_ip=request.client.host if request.client else None,
                upload=upload,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return manifest

    @app.get("/api/runs")
    def runs(_: None = Depends(require_auth)) -> dict:
        return {"runs": storage.list_runs()}

    @app.get("/api/runs/{run_id}")
    def run_detail(run_id: str, _: None = Depends(require_auth)) -> dict:
        try:
            return storage.read_manifest(run_id)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Unknown run") from exc

    @app.get("/api/runs/{run_id}/events")
    def run_events(run_id: str, _: None = Depends(require_auth)) -> dict:
        try:
            return {"events": storage.list_events(run_id)}
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Unknown run") from exc

    @app.get("/api/runs/{run_id}/artifacts/{artifact_name}")
    def run_artifact(run_id: str, artifact_name: str, _: None = Depends(require_auth)):
        try:
            return FileResponse(storage.artifact_path(run_id, artifact_name))
        except (FileNotFoundError, ValueError) as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.post("/api/runs/{run_id}/cancel")
    def cancel_run(run_id: str, _: None = Depends(require_auth)) -> dict:
        try:
            return storage.request_cancel(run_id)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Unknown run") from exc

    apps_root = Path(__file__).resolve().parents[1]
    legacy_portal_root = apps_root / "portal"
    portal_web_dist = apps_root / "portal_web" / "dist"
    app.mount("/admin", StaticFiles(directory=legacy_portal_root, html=True), name="portal-admin")
    app.mount(
        "/",
        StaticFiles(directory=portal_web_dist if portal_web_dist.exists() else legacy_portal_root, html=True),
        name="portal",
    )

    # Include unified Source API v2 routes
    source_router = create_source_router(str(config.workspace.root))
    app.include_router(source_router)

    # Include Retrieval API routes
    retrieval_router = create_retrieval_router(str(config.workspace.root))
    app.include_router(retrieval_router)

    return app


def main() -> int:
    parser = ArgumentParser(description="Run the SSD portal with local pipeline execution APIs.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH))
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    args = parser.parse_args()

    try:
        app = create_app(args.config, host=args.host)
    except PortalRunnerConfigError as exc:
        parser.error(str(exc))

    import uvicorn

    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        reload=False,
    )
    return 0


def _blank_to_none(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


if __name__ == "__main__":
    raise SystemExit(main())

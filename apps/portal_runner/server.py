from argparse import ArgumentParser
from pathlib import Path
from apps.portal_runner.auth import PortalRunnerAuthError, verify_bearer_token
from apps.portal_runner.config import DEFAULT_CONFIG_PATH, PortalRunnerConfigError, load_config, validate_bind_security
from apps.portal_runner.pipeline_registry import list_pipeline_definitions
from apps.portal_runner.runner import PortalPipelineRunner
from apps.portal_runner.schemas import PipelineInput
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

    portal_root = Path(__file__).resolve().parents[1] / "portal"
    app.mount("/", StaticFiles(directory=portal_root, html=True), name="portal")
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

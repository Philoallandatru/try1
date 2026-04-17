from __future__ import annotations

from pathlib import Path
from threading import Lock, Thread
import json
import re

from apps.portal.portal_state import write_portal_state
from apps.portal_runner.config import PortalRunnerConfig
from apps.portal_runner.pipeline_registry import get_pipeline_definition
from apps.portal_runner.schemas import PipelineInput
from apps.portal_runner.storage import PortalRunnerStorage
from services.analysis.llm_backends import MockLLMBackend
from services.ops.orchestration import load_source_payload
from services.workspace import build_workspace, deep_analyze_issue, init_workspace, publish_workspace_wiki
from services.workspace.spec_assets import ingest_spec_asset


class PipelineExecutionError(RuntimeError):
    pass


class PortalPipelineRunner:
    def __init__(self, *, config: PortalRunnerConfig, storage: PortalRunnerStorage) -> None:
        self.config = config
        self.storage = storage
        self._threads: dict[str, Thread] = {}
        self._lock = Lock()

    def create_run(
        self,
        *,
        pipeline_input: PipelineInput,
        client_ip: str | None,
        upload: dict | None = None,
    ) -> dict:
        definition = get_pipeline_definition(pipeline_input.pipeline_id)
        pipeline_config = self.config.pipeline_config(definition.pipeline_id)
        if not pipeline_config.enabled:
            raise ValueError(f"Pipeline is disabled: {definition.pipeline_id}")
        self._validate_required_inputs(definition.required_inputs, pipeline_input, upload)
        manifest = self.storage.create_run(
            definition=definition,
            pipeline_input=pipeline_input,
            client_ip=client_ip,
        )
        if upload:
            saved_upload = self.storage.save_uploaded_pdf(
                manifest["run_id"],
                filename=upload["filename"],
                content=upload["content"],
                max_upload_mb=self.config.server.max_upload_mb,
            )
            self.storage.update_step(
                manifest["run_id"],
                "store_uploaded_pdf",
                status="succeeded",
                logs=[
                    f"Stored {saved_upload['original_filename']}",
                    f"SHA256 {saved_upload['sha256']}",
                ],
            )
        thread = Thread(target=self._execute_run, args=(manifest["run_id"], pipeline_input), daemon=True)
        with self._lock:
            self._threads[manifest["run_id"]] = thread
        thread.start()
        return self.storage.read_manifest(manifest["run_id"])

    def _execute_run(self, run_id: str, pipeline_input: PipelineInput) -> None:
        definition = get_pipeline_definition(pipeline_input.pipeline_id)
        context: dict = {"workspace_dir": self._workspace_dir(run_id)}
        try:
            self.storage.mark_run_status(run_id, "running")
            self._run_step(run_id, "validate_config", lambda: self._validate_config(definition.pipeline_id))

            if definition.pipeline_id == "jira_live_smoke":
                self._run_step(run_id, "jira_live_fetch", lambda: self._jira_live_fetch(run_id, pipeline_input, context))
            elif definition.pipeline_id == "confluence_live_smoke":
                self._run_step(
                    run_id,
                    "confluence_live_fetch",
                    lambda: self._confluence_live_fetch(run_id, pipeline_input, context),
                )
            elif definition.pipeline_id == "pdf_ingest_smoke":
                self._run_step(run_id, "workspace_init", lambda: self._workspace_init(run_id, context))
                self._run_step(run_id, "pdf_spec_asset_ingest", lambda: self._pdf_spec_asset_ingest(run_id, pipeline_input, context))
            elif definition.pipeline_id == "full_real_data_smoke":
                self._run_step(run_id, "jira_live_fetch", lambda: self._jira_live_fetch(run_id, pipeline_input, context))
                self._run_step(
                    run_id,
                    "confluence_live_fetch",
                    lambda: self._confluence_live_fetch(run_id, pipeline_input, context),
                )
                self._run_step(run_id, "workspace_init", lambda: self._workspace_init(run_id, context))
                self._run_step(run_id, "pdf_spec_asset_ingest", lambda: self._pdf_spec_asset_ingest(run_id, pipeline_input, context))
                self._run_step(run_id, "workspace_build", lambda: self._workspace_build(run_id, context))
                self._run_step(run_id, "deep_analysis", lambda: self._deep_analysis(run_id, pipeline_input, context))
                self._run_step(run_id, "portal_state", lambda: self._portal_state(run_id, context, pipeline_input))
                self._run_step(run_id, "optional_publish_wiki", lambda: self._optional_publish_wiki(run_id, pipeline_input, context))
            else:
                raise PipelineExecutionError(f"No executor registered for {definition.pipeline_id}")

            self.storage.mark_run_status(run_id, "succeeded")
        except Exception as exc:
            self.storage.mark_run_status(run_id, "failed", error=str(exc))
        finally:
            with self._lock:
                self._threads.pop(run_id, None)

    def _run_step(self, run_id: str, step_id: str, action) -> dict | None:
        if self.storage.is_cancel_requested(run_id):
            self.storage.update_step(run_id, step_id, status="cancelled", logs=["Cancel requested before step."])
            self.storage.mark_run_status(run_id, "cancelled")
            raise PipelineExecutionError("Pipeline cancelled.")
        self.storage.update_step(run_id, step_id, status="running", logs=[f"Starting {step_id}"])
        try:
            result = action()
        except Exception as exc:
            self.storage.update_step(run_id, step_id, status="failed", error=str(exc), logs=[str(exc)])
            raise
        self.storage.update_step(run_id, step_id, status="succeeded", logs=_logs_from_result(result))
        return result

    def _validate_config(self, pipeline_id: str) -> dict:
        pipeline_config = self.config.pipeline_config(pipeline_id)
        if not pipeline_config.enabled:
            raise ValueError(f"Pipeline is disabled: {pipeline_id}")
        if pipeline_id in {"jira_live_smoke", "full_real_data_smoke"} and not self.config.jira.configured:
            raise ValueError("Jira is not configured in portal runner config.")
        if pipeline_id in {"confluence_live_smoke", "full_real_data_smoke"} and not self.config.confluence.configured:
            raise ValueError("Confluence is not configured in portal runner config.")
        return {"pipeline_id": pipeline_id, "configured": True}

    def _jira_live_fetch(self, run_id: str, pipeline_input: PipelineInput, context: dict) -> dict:
        if not pipeline_input.jira_issue_key:
            raise ValueError("jira_issue_key is required.")
        payload = load_source_payload(
            kind="jira",
            path=None,
            live=True,
            base_url=self.config.jira.base_url,
            username=self.config.jira.username,
            password=self.config.jira.password,
            token=self.config.jira.token,
            auth_mode=self.config.jira.auth_mode,
            fetch_backend="atlassian-api",
            issue_key=pipeline_input.jira_issue_key,
        )
        artifact = self.storage.save_artifact(run_id, "jira-live", payload)
        self._write_workspace_payload(context["workspace_dir"], "jira", "jira-live", payload)
        self.storage.update_step(run_id, "jira_live_fetch", status="running", artifacts={"jira-live": artifact})
        return {"document_count": len(payload.get("documents", [])), "artifact": artifact}

    def _confluence_live_fetch(self, run_id: str, pipeline_input: PipelineInput, context: dict) -> dict:
        if not pipeline_input.confluence_page_id:
            raise ValueError("confluence_page_id is required.")
        payload = load_source_payload(
            kind="confluence",
            path=None,
            live=True,
            base_url=self.config.confluence.base_url,
            username=self.config.confluence.username,
            password=self.config.confluence.password,
            token=self.config.confluence.token,
            auth_mode=self.config.confluence.auth_mode,
            fetch_backend="atlassian-api",
            page_id=pipeline_input.confluence_page_id,
        )
        artifact = self.storage.save_artifact(run_id, "confluence-live", payload)
        self._write_workspace_payload(context["workspace_dir"], "confluence", "confluence-live", payload)
        self.storage.update_step(run_id, "confluence_live_fetch", status="running", artifacts={"confluence-live": artifact})
        return {"document_count": len(payload.get("documents", [])), "artifact": artifact}

    def _workspace_init(self, run_id: str, context: dict) -> dict:
        result = init_workspace(context["workspace_dir"])
        artifact = self.storage.save_artifact(run_id, "workspace-init", result)
        self.storage.update_step(run_id, "workspace_init", status="running", artifacts={"workspace-init": artifact})
        return result

    def _pdf_spec_asset_ingest(self, run_id: str, pipeline_input: PipelineInput, context: dict) -> dict:
        upload = self.storage.read_manifest(run_id).get("upload")
        if not upload:
            raise ValueError("PDF upload is required.")
        preferred_parser = pipeline_input.preferred_parser or self.config.pipeline_config(pipeline_input.pipeline_id).preferred_parser
        result = ingest_spec_asset(
            context["workspace_dir"],
            spec_pdf=upload["path"],
            asset_id=_asset_id_from_run(run_id),
            display_name=pipeline_input.topic_title or "Portal Runner Spec",
            preferred_parser=preferred_parser,
        )
        artifact = self.storage.save_artifact(run_id, "pdf-spec-asset", result)
        self.storage.update_step(run_id, "pdf_spec_asset_ingest", status="running", artifacts={"pdf-spec-asset": artifact})
        return result

    def _workspace_build(self, run_id: str, context: dict) -> dict:
        result = build_workspace(context["workspace_dir"])
        artifact = self.storage.save_artifact(run_id, "workspace-build", result)
        self.storage.update_step(run_id, "workspace_build", status="running", artifacts={"workspace-build": artifact})
        return result

    def _deep_analysis(self, run_id: str, pipeline_input: PipelineInput, context: dict) -> dict:
        if not pipeline_input.jira_issue_key:
            raise ValueError("jira_issue_key is required.")
        backend = MockLLMBackend(response_text=pipeline_input.mock_response or "Portal runner smoke analysis")
        result = deep_analyze_issue(
            context["workspace_dir"],
            pipeline_input.jira_issue_key,
            llm_backend=backend,
        )
        artifact = self.storage.save_artifact(run_id, "deep-analysis", _compact_result(result))
        self.storage.update_step(run_id, "deep_analysis", status="running", artifacts={"deep-analysis": artifact})
        return {
            "issue_id": result.get("issue_id"),
            "run_dir": result.get("run_dir"),
            "answer_mode": result.get("answer", {}).get("mode"),
        }

    def _portal_state(self, run_id: str, context: dict, pipeline_input: PipelineInput) -> dict:
        output_path = Path(context["workspace_dir"]) / "portal_state.json"
        path = write_portal_state(
            output_path,
            query=pipeline_input.jira_issue_key or "portal runner",
            workspace_dir=context["workspace_dir"],
        )
        artifact = self.storage.save_artifact(run_id, "portal-state-path", {"portal_state_path": str(path)})
        self.storage.update_step(run_id, "portal_state", status="running", artifacts={"portal-state": artifact})
        return {"portal_state_path": str(path)}

    def _optional_publish_wiki(self, run_id: str, pipeline_input: PipelineInput, context: dict) -> dict:
        publish_wiki = pipeline_input.publish_wiki
        if publish_wiki is None:
            publish_wiki = self.config.pipeline_config(pipeline_input.pipeline_id).publish_wiki
        if not publish_wiki:
            return {"skipped": True}

        snapshot = json.loads((Path(context["workspace_dir"]) / "snapshots/current/documents.json").read_text(encoding="utf-8"))
        documents = snapshot.get("documents", [])
        jira_doc = next((doc for doc in documents if doc.get("source_type") == "jira"), None)
        confluence_doc = next((doc for doc in documents if doc.get("source_type") == "confluence"), None)
        if not jira_doc or not confluence_doc:
            raise ValueError("Jira and Confluence documents are required before publishing wiki.")

        topic_slug = _safe_slug(pipeline_input.topic_slug or "real-source-smoke")
        topic_title = pipeline_input.topic_title or "Real Source Smoke"
        route_manifest = {
            "topics": [
                {
                    "slug": topic_slug,
                    "title": topic_title,
                    "description": "Portal runner generated smoke topic.",
                }
            ],
            "confluence": [
                {
                    "document_id": confluence_doc["document_id"],
                    "topic": topic_slug,
                    "mode": "summarize",
                }
            ],
            "jira": [
                {
                    "document_id": jira_doc["document_id"],
                    "topic": topic_slug,
                    "mode": "analyze",
                    "promote": True,
                }
            ],
        }
        route_path = Path(context["workspace_dir"]) / "route-manifest.json"
        route_path.write_text(json.dumps(route_manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        backend = MockLLMBackend(response_text=pipeline_input.mock_response or "Portal runner wiki content")
        result = publish_workspace_wiki(
            context["workspace_dir"],
            manifest_path=route_path,
            renderer="vitepress",
            llm_backend=backend,
        )
        artifact = self.storage.save_artifact(run_id, "wiki-publish", result)
        self.storage.update_step(run_id, "optional_publish_wiki", status="running", artifacts={"wiki-publish": artifact})
        return {"report_path": result.get("report_path"), "run_dir": result.get("run_dir")}

    def _workspace_dir(self, run_id: str) -> Path:
        return self.config.workspace.root / run_id

    def _write_workspace_payload(self, workspace_dir: str | Path, kind: str, source_name: str, payload: dict) -> None:
        root = Path(workspace_dir)
        payload_dir = root / "raw" / kind / "payloads"
        payload_dir.mkdir(parents=True, exist_ok=True)
        (payload_dir / f"{source_name}.json").write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    def _validate_required_inputs(self, required_inputs: list[str], pipeline_input: PipelineInput, upload: dict | None) -> None:
        if "jira_issue_key" in required_inputs and not pipeline_input.jira_issue_key:
            raise ValueError("jira_issue_key is required.")
        if "confluence_page_id" in required_inputs and not pipeline_input.confluence_page_id:
            raise ValueError("confluence_page_id is required.")
        if "pdf" in required_inputs and not upload:
            raise ValueError("PDF upload is required.")


def _logs_from_result(result: dict | None) -> list[str]:
    if not result:
        return ["Step completed."]
    return [f"{key}: {value}" for key, value in result.items() if isinstance(value, (str, int, float, bool))]


def _compact_result(result: dict) -> dict:
    return {
        "issue_id": result.get("issue_id"),
        "analysis_profile": result.get("analysis_profile"),
        "answer": result.get("answer"),
        "run_dir": result.get("run_dir"),
        "run_manifest_path": result.get("run_manifest_path"),
    }


def _asset_id_from_run(run_id: str) -> str:
    return _safe_slug(f"spec-{run_id[:17]}")


def _safe_slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_-]+", "-", value).strip("-").lower()
    return slug or "portal-runner"

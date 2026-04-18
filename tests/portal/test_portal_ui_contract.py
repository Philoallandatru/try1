from pathlib import Path
import unittest


class PortalUiContractTest(unittest.TestCase):
    def test_index_html_contains_required_operator_sections(self) -> None:
        text = Path("apps/portal/index.html").read_text(encoding="utf-8")
        for marker in [
            "New Task",
            "Issue Key",
            "Analysis Profile",
            "new-task-run",
            "new-task-command-preview",
            "Task Workbench",
            "Pipeline Runner",
            "data-runner-field",
            "runner-spec-asset",
            "runner-confluence-scope",
            "runner-profile",
            "runner-prompt",
            "runner-events",
            "Task Details",
            "Ingestion Status",
            "Corpus Inventory",
            "Search Workspace",
            "Citation Inspection",
            "Evaluation Health",
        ]:
            with self.subTest(marker=marker):
                self.assertIn(marker, text)

    def test_app_js_supports_citation_drilldown(self) -> None:
        text = Path("apps/portal/app.js").read_text(encoding="utf-8")
        self.assertIn("portal_state.json", text)
        self.assertIn("citation-inspection", text)
        self.assertIn("search-card", text)

    def test_app_js_supports_task_workbench_rendering(self) -> None:
        text = Path("apps/portal/app.js").read_text(encoding="utf-8")
        for marker in [
            "renderTaskWorkbench",
            "new-task-issue-key",
            "new-task-profile",
            "renderNewTaskCommandPreview",
            "currentPortalState",
            "renderPortal",
            "/api/workspace/analyze-jira",
            "task-list",
            "task-detail-tabs",
            "report-tabs",
            "knowledge-panels",
            "control-events",
            "artifact-inventory",
            "command-recipes",
            "task-control",
            "row.preview",
            "taskDetailsById",
            "selectedTaskId",
            "renderSelectedTask",
            "renderEventList",
            "renderArtifactInventory",
            "renderCommandRecipes",
        ]:
            with self.subTest(marker=marker):
                self.assertIn(marker, text)

    def test_app_js_supports_pipeline_runner_rendering(self) -> None:
        text = Path("apps/portal/app.js").read_text(encoding="utf-8")
        for marker in [
            "portalRunnerToken",
            "runnerFetch",
            "renderPipelineOptions",
            "renderRunnerRuns",
            "renderRunnerDetail",
            "renderRunnerEvents",
            "updateRunnerFormForPipeline",
            "renderSpecAssetOptions",
            "saveRunnerForm",
            "restoreRunnerForm",
            "profile_prompt_debug",
            "runner-profile",
            "runner-prompt",
            "/api/pipelines",
            "/api/spec-assets",
            "/api/runs",
            "/events",
            "/cancel",
        ]:
            with self.subTest(marker=marker):
                self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()

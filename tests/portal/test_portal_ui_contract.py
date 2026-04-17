from pathlib import Path
import unittest


class PortalUiContractTest(unittest.TestCase):
    def test_index_html_contains_required_operator_sections(self) -> None:
        text = Path("apps/portal/index.html").read_text(encoding="utf-8")
        for marker in [
            "New Task",
            "Task Workbench",
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
            "task-list",
            "task-detail-tabs",
            "report-tabs",
            "knowledge-panels",
            "task-control",
            "row.preview",
            "taskDetailsById",
            "selectedTaskId",
            "renderSelectedTask",
        ]:
            with self.subTest(marker=marker):
                self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()

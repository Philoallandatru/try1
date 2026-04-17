from pathlib import Path
import unittest

from apps.portal.portal_state import build_portal_state, write_portal_state
from services.connectors.confluence.connector import load_confluence_sync
from services.connectors.jira.connector import load_jira_sync
from services.retrieval.indexing.page_index import load_documents
from services.retrieval.persistence.snapshot_store import write_snapshot
from services.workspace.workspace import deep_analyze_issue, init_workspace, workspace_paths
from tests.temp_utils import temporary_directory as TemporaryDirectory


class PortalStateTest(unittest.TestCase):
    def test_portal_state_contains_operator_views(self) -> None:
        state = build_portal_state()
        self.assertIn("ingestion_status", state)
        self.assertIn("corpus_inventory", state)
        self.assertIn("search_workspace", state)
        self.assertIn("citation_inspection", state)
        self.assertIn("evaluation_health", state)
        self.assertIn("task_workbench", state)
        self.assertTrue(len(state["search_workspace"]) >= 1)

    def test_portal_state_contains_task_workbench_views(self) -> None:
        state = build_portal_state()
        workbench = state["task_workbench"]

        self.assertIn("new_task_entry", workbench)
        self.assertIn("filters", workbench)
        self.assertIn("tasks", workbench)
        self.assertIn("detail_tabs", workbench)
        self.assertIn("report_tabs", workbench)
        self.assertIn("knowledge_panels", workbench)
        self.assertIn("control_events", workbench)
        self.assertIn("artifact_inventory", workbench)
        self.assertIn("retrieval_comparison", workbench)
        self.assertIn("controls", workbench)
        self.assertIn("task_details_by_id", workbench)
        self.assertGreaterEqual(len(workbench["tasks"]), 1)
        selected = next(task for task in workbench["tasks"] if task["selected"])
        self.assertEqual(selected["task_type"], "jira_deep_analysis")
        self.assertEqual(workbench["controls"], ["stop", "resume", "rerun"])
        self.assertEqual(
            [tab["id"] for tab in workbench["report_tabs"]],
            ["rca", "spec_impact", "decision_brief", "general_summary"],
        )

    def test_portal_state_can_be_written_for_static_ui(self) -> None:
        path = write_portal_state("apps/portal/portal_state.json")
        self.assertTrue(Path(path).exists())
        self.assertGreater(Path(path).stat().st_size, 0)

    def test_portal_state_can_use_workspace_run_artifacts_for_workbench(self) -> None:
        with TemporaryDirectory() as temp_dir:
            init_workspace(temp_dir)
            snapshot_dir = workspace_paths(temp_dir)["snapshot_root"]
            jira_documents = load_jira_sync(Path("fixtures/connectors/jira/incremental_sync.json"))["documents"]
            confluence_documents = load_confluence_sync(Path("fixtures/connectors/confluence/page_sync.json"))["documents"]
            spec_documents = load_documents(Path("fixtures/retrieval/pageindex_corpus.json"))
            write_snapshot(
                snapshot_dir,
                documents=[*jira_documents, *confluence_documents, *spec_documents],
                sources={
                    "jira": {"cursor": "jira-test", "last_sync": "2026-04-15T00:00:00Z", "sync_type": "incremental", "document_count": len(jira_documents)},
                    "confluence": {"cursor": "conf-test", "last_sync": "2026-04-15T00:00:00Z", "sync_type": "full", "document_count": len(confluence_documents)},
                    "spec": {"cursor": "spec-test", "last_sync": "2026-04-15T00:00:00Z", "sync_type": "manual", "document_count": len(spec_documents)},
                },
            )
            run_payload = deep_analyze_issue(temp_dir, "SSD-102", policies=["team:ssd"])

            state = build_portal_state(workspace_dir=temp_dir)
            workbench = state["task_workbench"]
            selected = next(task for task in workbench["tasks"] if task["selected"])

            self.assertEqual(selected["task_id"], Path(run_payload["run_dir"]).name)
            self.assertEqual(selected["issue_key"], "SSD-102")
            self.assertIn("rerun-section", workbench["controls"])
            self.assertEqual(workbench["report_tabs"][0]["status"], "ready")
            self.assertEqual(workbench["knowledge_panels"][0]["status"], "ready")
            self.assertIn("Action:", workbench["knowledge_panels"][0]["preview"])
            self.assertIn("section_outputs/rca.json", workbench["detail_tabs"][3]["content"])
            self.assertIn("checkpoints", workbench["detail_tabs"][0]["content"].lower())
            self.assertIn(selected["task_id"], workbench["task_details_by_id"])
            self.assertIsInstance(workbench["artifact_inventory"], list)
            self.assertTrue(any(row["artifact_type"] == "confluence_update_proposal" for row in workbench["artifact_inventory"]))


if __name__ == "__main__":
    unittest.main()

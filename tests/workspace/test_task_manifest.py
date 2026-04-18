from __future__ import annotations

from pathlib import Path
import unittest

from tests.temp_utils import temporary_directory as TemporaryDirectory
from services.workspace.task_manifest import (
    build_artifact_record,
    build_run_manifest,
    load_run_manifest,
    refresh_artifact_staleness,
    update_checkpoint,
    write_run_manifest,
)


class TaskManifestTest(unittest.TestCase):
    def test_build_run_manifest_initializes_required_fields(self) -> None:
        manifest = build_run_manifest(
            task_type="jira_deep_analysis",
            owner="alice",
            input_config={"jira_issue_key": "SSD-777"},
            run_id="run-001",
        )

        self.assertEqual(manifest["task_type"], "jira_deep_analysis")
        self.assertEqual(manifest["owner"], "alice")
        self.assertEqual(manifest["run_id"], "run-001")
        self.assertEqual(manifest["status"], "queued")
        self.assertEqual(
            sorted(manifest["checkpoints"].keys()),
            ["analysis_ready", "knowledge_ready", "retrieval_ready"],
        )
        self.assertEqual(manifest["artifacts"], [])

    def test_update_checkpoint_records_artifact_types(self) -> None:
        manifest = build_run_manifest(
            task_type="jira_deep_analysis",
            owner="alice",
            input_config={"jira_issue_key": "SSD-777"},
            run_id="run-001",
        )

        updated = update_checkpoint(
            manifest,
            "retrieval_ready",
            reached=True,
            artifact_types=["shared_retrieval_bundle"],
            updated_at="2026-04-15T00:00:00Z",
        )

        self.assertTrue(updated["checkpoints"]["retrieval_ready"]["reached"])
        self.assertEqual(
            updated["checkpoints"]["retrieval_ready"]["artifact_types"],
            ["shared_retrieval_bundle"],
        )
        self.assertEqual(updated["checkpoints"]["retrieval_ready"]["updated_at"], "2026-04-15T00:00:00Z")

    def test_refresh_artifact_staleness_propagates_dependency_stale(self) -> None:
        artifacts = [
            build_artifact_record(
                artifact_type="shared_retrieval_bundle",
                path="runs/run-001/shared_retrieval_bundle.json",
                step_name="shared_retrieval",
                step_version="v1",
                input_hash="abc",
                stale=True,
            ),
            build_artifact_record(
                artifact_type="section_output_rca",
                path="runs/run-001/section_outputs/rca.json",
                step_name="section_analysis",
                step_version="v1",
                input_hash="def",
                depends_on=["shared_retrieval_bundle"],
            ),
        ]

        refreshed = refresh_artifact_staleness(artifacts)
        by_type = {artifact["artifact_type"]: artifact for artifact in refreshed}
        self.assertTrue(by_type["shared_retrieval_bundle"]["stale"])
        self.assertTrue(by_type["section_output_rca"]["stale"])

    def test_write_and_load_run_manifest_roundtrip(self) -> None:
        manifest = build_run_manifest(
            task_type="jira_deep_analysis",
            owner="alice",
            input_config={"jira_issue_key": "SSD-777"},
            run_id="run-001",
            artifacts=[
                build_artifact_record(
                    artifact_type="run_manifest",
                    path="runs/run-001/run_manifest.json",
                    step_name="task_submission",
                    step_version="v1",
                    input_hash="manifest-hash",
                )
            ],
        )

        with TemporaryDirectory() as temp_dir:
            run_dir = Path(temp_dir) / "run-001"
            written_path = write_run_manifest(run_dir, manifest)
            loaded = load_run_manifest(run_dir)

        self.assertEqual(written_path, str(run_dir / "run_manifest.json"))
        self.assertEqual(loaded["task_type"], manifest["task_type"])
        self.assertEqual(loaded["artifacts"][0]["artifact_type"], "run_manifest")

    def test_failed_run_preserves_partial_artifacts_and_error(self) -> None:
        partial_artifact = build_artifact_record(
            artifact_type="shared_retrieval_bundle",
            path="runs/run-002/shared_retrieval_bundle.json",
            step_name="shared_retrieval",
            step_version="v1",
            input_hash="partial-hash",
        )
        manifest = build_run_manifest(
            task_type="jira_deep_analysis",
            owner="alice",
            input_config={"jira_issue_key": "SSD-777"},
            run_id="run-002",
            status="failed",
            artifacts=[partial_artifact],
            error={"message": "analysis step failed"},
        )

        self.assertEqual(manifest["status"], "failed")
        self.assertEqual(manifest["artifacts"][0]["artifact_type"], "shared_retrieval_bundle")
        self.assertEqual(manifest["error"]["message"], "analysis step failed")

    def test_update_checkpoint_rejects_unknown_names(self) -> None:
        manifest = build_run_manifest(
            task_type="jira_deep_analysis",
            owner="alice",
            input_config={"jira_issue_key": "SSD-777"},
            run_id="run-001",
        )

        with self.assertRaises(ValueError):
            update_checkpoint(manifest, "unknown_checkpoint", reached=True)


if __name__ == "__main__":
    unittest.main()

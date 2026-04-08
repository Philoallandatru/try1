from pathlib import Path
import json
import unittest


EXPECTED_ROUTES = {
    "FW Bug": ("defect", "fw_bug_rca"),
    "HW Bug": ("defect", "hw_bug_rca"),
    "Test Bug": ("defect", "test_bug_rca"),
    "Misc Bug": ("defect", "misc_bug_rca"),
    "DAS/PRD": ("requirement", "prd_review"),
    "MRD": ("requirement", "mrd_review"),
    "Requirement Change": ("requirement_change", "requirement_change_impact"),
    "Component Change": ("change_control", "component_change_impact"),
    "Epic": ("delivery", "delivery_summary"),
    "Story": ("delivery", "story_summary"),
    "Task": ("delivery", "task_summary"),
    "Release": ("release", "release_summary"),
}


class JiraIssueTypeProfilesSchemaTest(unittest.TestCase):
    def test_jira_issue_type_profiles_contract_contains_expected_routes(self) -> None:
        payload = json.loads(Path("packages/schema/jira-issue-type-profiles.json").read_text(encoding="utf-8"))
        self.assertEqual(payload["default"]["issue_family"], "unknown")
        self.assertEqual(payload["default"]["issue_route"], "generic_jira_summary")

        profiles = payload["profiles"]
        for issue_type, (issue_family, issue_route) in EXPECTED_ROUTES.items():
            with self.subTest(issue_type=issue_type):
                self.assertEqual(profiles[issue_type]["issue_family"], issue_family)
                self.assertEqual(profiles[issue_type]["issue_route"], issue_route)


if __name__ == "__main__":
    unittest.main()

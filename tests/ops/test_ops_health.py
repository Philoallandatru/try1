from pathlib import Path
import unittest

from services.ops.health import build_ops_health


class OpsHealthTest(unittest.TestCase):
    def test_freshness_reporting_is_within_budget(self) -> None:
        report = build_ops_health()
        budget = report["freshness"]["budget_minutes"]
        for source in report["freshness"]["sources"]:
            with self.subTest(source=source["source_type"]):
                self.assertEqual(source["status"], "healthy")
                self.assertLessEqual(source["lag_minutes"], budget)

    def test_backup_restore_validation_is_present(self) -> None:
        report = build_ops_health()
        self.assertEqual(report["backup_restore"]["backup"]["status"], "healthy")
        self.assertEqual(report["backup_restore"]["restore"]["status"], "validated")
        self.assertIn("phase1-snapshot", report["backup_restore"]["backup"]["location"])


if __name__ == "__main__":
    unittest.main()


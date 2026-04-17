from pathlib import Path
import unittest


class RealDataSmokeScriptTest(unittest.TestCase):
    def test_real_data_smoke_script_supports_showcase_workbench_mode(self) -> None:
        text = Path("scripts/run_real_data_smoke.ps1").read_text(encoding="utf-8")
        self.assertIn("UseShowcaseWorkbench", text)
        self.assertIn("showcase-workbench", text)
        self.assertIn("--portal-state-output", text)


if __name__ == "__main__":
    unittest.main()

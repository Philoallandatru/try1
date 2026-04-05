from pathlib import Path
import unittest

from apps.portal.portal_state import build_portal_state, write_portal_state


class PortalStateTest(unittest.TestCase):
    def test_portal_state_contains_operator_views(self) -> None:
        state = build_portal_state()
        self.assertIn("ingestion_status", state)
        self.assertIn("corpus_inventory", state)
        self.assertIn("search_workspace", state)
        self.assertIn("citation_inspection", state)
        self.assertIn("evaluation_health", state)
        self.assertTrue(len(state["search_workspace"]) >= 1)

    def test_portal_state_can_be_written_for_static_ui(self) -> None:
        path = write_portal_state("apps/portal/portal_state.json")
        self.assertTrue(Path(path).exists())
        self.assertGreater(Path(path).stat().st_size, 0)


if __name__ == "__main__":
    unittest.main()


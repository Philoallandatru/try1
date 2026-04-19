from __future__ import annotations

from argparse import ArgumentParser
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
import subprocess
import sys
from threading import Thread
from time import sleep
from urllib import request
from urllib.parse import parse_qs, urlparse
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[1]


class FakeSourceHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/rest/api/2/search":
            self._send_json(_fake_jira_payload())
            return
        if parsed.path == "/rest/api/content":
            self._send_json(_fake_confluence_payload(parse_qs(parsed.query)))
            return
        self.send_error(404)

    def log_message(self, *_: object) -> None:
        return

    def _send_json(self, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class FakeSourceServer:
    def __enter__(self):
        self.server = HTTPServer(("127.0.0.1", 0), FakeSourceHandler)
        self.thread = Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        host, port = self.server.server_address
        self.base_url = f"http://{host}:{port}"
        return self

    def __exit__(self, *_: object) -> None:
        self.server.shutdown()
        self.thread.join(timeout=2)
        self.server.server_close()


def _fake_jira_payload() -> dict:
    return {
        "total": 1,
        "startAt": 0,
        "maxResults": 50,
        "names": {},
        "issues": [
            {
                "key": "SSD-E2E-1",
                "fields": {
                    "project": {"key": "SSD"},
                    "summary": "[SV][SSD1100][Power][S4 Resume] Device enumerates but first I/O times out",
                    "issuetype": {"name": "FW Bug"},
                    "labels": ["S4", "Resume", "Timeout", "NVMe"],
                    "priority": {"name": "High"},
                    "components": [{"name": "FW"}],
                    "versions": [{"name": "SSD1100"}],
                    "resolution": None,
                    "status": {"name": "In Progress"},
                    "fixVersions": [],
                    "Severity": "Major",
                    "Report department": "SV",
                    "Root Cause": "Controller ready and I/O queue recreate timing overlap after resume",
                    "description": "Windows resume sends first I/O before queue context restore completes.",
                    "updated": "2026-04-18T12:00:00.000+0000",
                    "comment": {
                        "comments": [
                            {
                                "author": {"displayName": "FW"},
                                "created": "2026-04-18T12:05:00.000+0000",
                                "body": "Controller ready is set early while queue context restore is still in background.",
                            }
                        ]
                    },
                },
            }
        ],
    }


def _fake_confluence_payload(_query: dict) -> dict:
    return {
        "results": [
            {
                "id": "CONF-E2E-1",
                "space": {"key": "SSDENG"},
                "title": "NVMe Resume Timeout Debug Guide",
                "version": {"number": 1, "when": "2026-04-18T09:00:00Z"},
                "body": {
                    "storage": {
                        "value": (
                            "<h1>Symptom Definition</h1>"
                            "<p>Device enumerates successfully after resume.</p>"
                            "<p>First admin or I/O command times out; retry may succeed.</p>"
                            "<h1>Common Root Cause Patterns</h1>"
                            "<p>Controller ready bit asserted before queue restore fully completes.</p>"
                        )
                    }
                },
                "_links": {"webui": "/display/SSDENG/CONF-E2E-1"},
            }
        ],
        "size": 1,
        "start": 0,
        "limit": 25,
    }


def seed_spec_asset(workspace_dir: Path) -> None:
    asset_root = workspace_dir / "raw" / "files" / "spec_assets" / "nvme-spec-mineru" / "v1"
    asset_root.mkdir(parents=True, exist_ok=True)
    document = {
        "document_id": "nvme-e2e-spec",
        "source_type": "pdf",
        "authority_level": "canonical",
        "version": "v1",
        "language": "en",
        "title": "NVMe E2E Spec Asset",
        "provenance": {"source_uri": "e2e://nvme.pdf", "ingested_at": "2026-04-19T00:00:00Z", "parser": "mineru"},
        "acl": {"policy": "team:ssd", "inherits_from": None},
        "structure": {
            "pages": [{"page": 1}],
            "sections": [{"id": "section-1", "heading": "Controller Ready", "level": 1, "page": 1}],
            "tables": [],
            "figures": [],
            "worksheets": [],
            "slides": [],
        },
        "terminology": {"terms": []},
        "content_blocks": [
            {
                "id": "block-1",
                "text": "Controller ready shall reflect initialization completion before command processing is reliable.",
                "page": 1,
                "section_heading": "Controller Ready",
            },
            {
                "id": "block-2",
                "text": "Power management resume flows must restore queue context before host I/O commands are serviced.",
                "page": 1,
                "section_heading": "Controller Ready",
            },
        ],
        "markdown": "# NVMe E2E Spec Asset\n\nController ready shall reflect initialization completion before command processing is reliable.\n\nPower management resume flows must restore queue context before host I/O commands are serviced.",
        "metadata": {"parser_used": "mineru"},
    }
    (asset_root / "spec-corpus.json").write_text(json.dumps({"documents": [document]}, indent=2), encoding="utf-8")
    (asset_root / "spec-doc.json").write_text(json.dumps(document, indent=2), encoding="utf-8")
    (asset_root / "metadata.json").write_text(json.dumps({"parser_used": "mineru", "display_name": "NVMe E2E Spec"}, indent=2), encoding="utf-8")
    (asset_root / "document.md").write_text(document["markdown"], encoding="utf-8")
    (asset_root / "page_index.json").write_text(json.dumps({"entries": []}, indent=2), encoding="utf-8")
    registry = {
        "assets": [
            {
                "asset_id": "nvme-spec-mineru",
                "display_name": "NVMe E2E Spec",
                "version": "v1",
                "document_id": "nvme-e2e-spec",
                "created_at": "2026-04-19T00:00:00Z",
                "source_pdf": "e2e://nvme.pdf",
                "parser_used": "mineru",
                "asset_root": str(asset_root),
            }
        ]
    }
    (workspace_dir / "raw" / "files" / "spec_assets" / "registry.json").write_text(json.dumps(registry, indent=2), encoding="utf-8")


def wait_health(port: int) -> None:
    for _ in range(40):
        try:
            with request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=2) as response:
                if json.loads(response.read().decode("utf-8")).get("status") == "ok":
                    return
        except Exception:
            sleep(1)
    raise RuntimeError("portal runner did not become ready")


def create_source(page, expect, base_url: str, kind: str, name: str, selector_name: str, selector_value: str) -> None:
    page.get_by_role("button", name="Sources").click()
    if page.get_by_role("button", name="Add another source").is_visible():
        page.get_by_role("button", name="Add another source").click()
    expect(page.get_by_text("Source Details")).to_be_visible(timeout=30000)
    page.get_by_label("Source type").select_option(kind)
    page.get_by_label("Source name").fill(name)
    page.get_by_label("Base URL").fill(base_url)
    page.get_by_role("button", name="Next: Authentication").click()
    page.get_by_placeholder("Stored locally and redacted").fill("pw-token")
    page.get_by_role("button", name="Next: Selector").click()
    page.get_by_label("Selector name").fill(selector_name)
    if kind == "jira":
        page.get_by_label("Issue key").fill(selector_value)
    else:
        page.get_by_label("Space key").fill(selector_value)
    with page.expect_response(lambda r: "/api/workspace/sources" in r.url and r.request.method == "POST" and r.status == 200, timeout=60000):
        page.get_by_role("button", name="Save source and selector").click()
    with page.expect_response(lambda r: "/test" in r.url and r.status == 200, timeout=60000):
        page.get_by_role("button", name="Test Connection").click()
    with page.expect_response(lambda r: "/refresh" in r.url and r.status == 200, timeout=120000):
        page.get_by_role("button", name="Fetch Data").click()


def main() -> int:
    parser = ArgumentParser(description="Run browser E2E for the product portal from an empty workspace.")
    parser.add_argument("--port", type=int, default=8797)
    parser.add_argument("--runner-token", default="runner-secret")
    parser.add_argument("--skip-llm-verify", action="store_true")
    args = parser.parse_args()

    try:
        from playwright.sync_api import expect, sync_playwright
    except ImportError as exc:
        raise SystemExit("Playwright Python package is required") from exc

    e2e_root = ROOT / ".tmp" / "portal-web-zero-start-e2e"
    e2e_root.mkdir(parents=True, exist_ok=True)
    workspace_root = e2e_root / "workspaces"
    config_path = e2e_root / "config.yaml"
    config_path.write_text(
        "\n".join(
            [
                "server:",
                f"  runner_token: {args.runner_token}",
                "workspace:",
                f"  root: {workspace_root.as_posix()}",
                f"  uploads_root: {(e2e_root / 'uploads').as_posix()}",
                f"  runs_root: {(e2e_root / 'runs').as_posix()}",
                f"  spec_assets_workspace: {(e2e_root / 'spec-assets-workspace').as_posix()}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    with FakeSourceServer() as fake_sources:
        process = subprocess.Popen(
            [sys.executable, "-m", "apps.portal_runner.server", "--config", str(config_path), "--host", "127.0.0.1", "--port", str(args.port)],
            cwd=ROOT,
        )
        try:
            wait_health(args.port)
            workspace_name = f"pw-zero-{uuid4().hex[:8]}"
            workspace_dir = workspace_root / workspace_name
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page(viewport={"width": 1440, "height": 1100})
                page.add_init_script(f"localStorage.setItem('ssdPortalToken', '{args.runner_token}')")
                page.goto(f"http://127.0.0.1:{args.port}", wait_until="networkidle", timeout=60000)

                page.get_by_label("New").fill(workspace_name)
                with page.expect_response(lambda r: "/api/workspaces" in r.url and r.request.method == "POST" and r.status == 200, timeout=60000):
                    page.get_by_role("button", name="Create", exact=True).click()
                for _ in range(40):
                    if (workspace_dir / "workspace.yaml").exists():
                        break
                    sleep(0.5)
                seed_spec_asset(workspace_dir)

                create_source(page, expect, fake_sources.base_url, "jira", "pw_jira", "pw_jira_selector", "SSD-E2E-1")
                create_source(page, expect, fake_sources.base_url, "confluence", "pw_confluence", "pw_confluence_selector", "SSDENG")

                page.get_by_role("button", name="Profiles").click()
                expect(page.get_by_text("Analysis Settings")).to_be_visible(timeout=30000)
                page.get_by_label("Profile name").fill("pw_profile")
                page.get_by_label("Jira source").select_option("pw_jira")
                page.get_by_label("Jira selector").select_option("pw_jira_selector")
                page.get_by_label("Evidence source").select_option("pw_confluence")
                page.get_by_label("Evidence selector").select_option("pw_confluence_selector")
                page.get_by_label("Spec asset").select_option("nvme-spec-mineru")
                page.get_by_label("LLM backend").select_option("none")
                with page.expect_response(lambda r: "/api/workspace/profiles" in r.url and r.request.method == "POST" and r.status == 200, timeout=60000):
                    page.get_by_role("button", name="Create Profile").click()
                expect(page.get_by_text("pw_profile")).to_be_visible(timeout=30000)

                page.get_by_role("button", name="Analyze").click()
                expect(page.get_by_text("4 / 4 ready")).to_be_visible(timeout=30000)
                page.get_by_label("Issue Key").fill("SSD-E2E-1")
                page.get_by_label("Profile").select_option("pw_profile")
                with page.expect_response(lambda r: "/api/workspace/analyze-jira" in r.url and r.status == 200, timeout=180000):
                    page.get_by_role("button", name="Run", exact=True).click()
                expect(page.get_by_text("Evidence Coverage", exact=True)).to_be_visible(timeout=30000)

                page.get_by_role("button", name="Runs").click()
                expect(page.get_by_role("tab", name="Summary")).to_be_visible(timeout=30000)
                if not args.skip_llm_verify:
                    with page.expect_response(lambda r: "/verify-llm" in r.url and r.status == 200, timeout=240000):
                        page.get_by_role("button", name="Verify with LM Studio qwen-9b").click()
                    page.get_by_role("tab", name="Verification").click()
                    expect(page.get_by_text("openai-compatible / local-llm-verification")).to_be_visible(timeout=30000)
                page.screenshot(path=str(e2e_root / "zero-start-browser-e2e.png"), full_page=True)
                browser.close()
            print("PORTAL_WEB_ZERO_START_E2E_OK")
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

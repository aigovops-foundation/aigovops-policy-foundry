"""Offline browser regressions for selection, credential and raw-editor boundaries.

Build web first. Requires tests/requirements-browser.txt and a prepared Chromium.
Run: python web/tests/dashboard-browser.py --output <persistent-evidence-directory>
"""
import argparse
import functools
import http.server
import json
import pathlib
import threading
from urllib.parse import urlsplit

from playwright.sync_api import expect, sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[2]


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    demo = json.loads((ROOT / "web/public/demo/bundle.json").read_text())
    run = json.loads((ROOT / "web/public/demo/run.json").read_text())
    bad = json.loads(json.dumps(demo))
    packet = json.loads(bad["files"]["underwriting_packet.json"])
    packet["metrics"]["gate_coverage_bp"] = 1
    bad["files"]["underwriting_packet.json"] = json.dumps(packet)
    handler = functools.partial(QuietHandler, directory=str(ROOT / "web/dist"))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    blocked, posts, creates, held, errors = [], [], [], [], []
    state = {"hold": False, "error": False, "bad_run": False}
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            context = browser.new_context(service_workers="block", accept_downloads=True)

            def route(req):
                request = req.request
                url = urlsplit(request.url)
                if request.url.startswith(base + "/") or url.hostname in {"foundry-a.invalid", "foundry-b.invalid", "remote.invalid"}:
                    if url.path == "/api/meta":
                        req.fulfill(json={"name": "AiGovOps Policy Foundry"})
                    elif url.path == "/api/verify":
                        posts.append(json.loads(request.post_data))
                        if state["hold"]:
                            held.append(req)
                        elif state["error"]:
                            req.fulfill(status=503, json={"detail": "synthetic error"})
                        else:
                            req.fulfill(json={"ok": posts[-1] == demo})
                    elif url.path == "/api/runs":
                        creates.append({"url": request.url, "authorization": request.headers.get("authorization")})
                        req.fulfill(status=201, json={**run, "id": f"synthetic-{len(creates)}"})
                    elif url.path.endswith("/bundle.json") and "/api/" in url.path:
                        req.fulfill(json={"files": None} if state["bad_run"] else demo)
                    elif request.url.startswith(base + "/"):
                        req.continue_()
                    else:
                        raise AssertionError(f"Unexpected fake API route: {url.path}")
                else:
                    blocked.append(request.url)
                    req.abort()

            context.route("**/*", route)
            page = context.new_page()
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(base + "/#/verify")
            expect(page.get_by_text("All checks passed", exact=True)).to_be_visible()
            file = page.locator('input[type="file"]')
            file.set_input_files({"name": "tampered.json", "mimeType": "application/json", "buffer": json.dumps(bad).encode()})
            expect(page.get_by_text("Verification failed", exact=True)).to_be_visible()
            expect(page.get_by_text("Verified", exact=True)).to_have_count(0)
            page.get_by_role("button", name="Also verify on server").click()
            expect(page.get_by_text("Server verifier: FAILED", exact=False)).to_be_visible()
            assert posts[-1] == bad
            with page.expect_download() as download:
                page.get_by_role("button", name="Download bundle.json", exact=True).click()
            assert json.loads(pathlib.Path(download.value.path()).read_text()) == bad
            assert download.value.suggested_filename == "tampered.json"
            for width, height in [(1440, 900), (390, 844)]:
                for scheme in ["light", "dark"]:
                    page.set_viewport_size({"width": width, "height": height})
                    page.emulate_media(color_scheme=scheme)
                    if page.locator("html").get_attribute("data-theme") != scheme:
                        page.get_by_role("button", name=f"Switch to {scheme} mode").click()
                    page.screenshot(path=str(args.output / f"verify-{width}-{scheme}.png"), full_page=True, animations="disabled")
            state["error"] = True
            page.get_by_role("button", name="Also verify on server").click()
            expect(page.get_by_text("Server error 503", exact=False)).to_be_visible()
            state["error"] = False
            state["hold"] = True
            page.get_by_role("button", name="Also verify on server").click()
            page.get_by_role("button", name="Back to current bundle").click()
            assert held
            held.pop().fulfill(json={"ok": False})
            expect(page.get_by_text("All checks passed", exact=True)).to_be_visible()
            expect(page.get_by_text("Server verifier:", exact=False)).to_have_count(0)
            state["hold"] = False
            file.set_input_files({"name": "invalid.json", "mimeType": "application/json", "buffer": b"not JSON"})
            expect(page.get_by_text("Not a bundle.json file", exact=True)).to_be_visible()
            expect(page.get_by_role("button", name="Download bundle.json", exact=True)).to_be_disabled()
            expect(page.get_by_role("button", name="Also verify on server")).to_be_disabled()
            page.get_by_role("button", name="Back to current bundle").click()
            depth = 200000
            deep = ('{"files":' + "[" * depth + "]" * depth + "}").encode()
            file.set_input_files({"name": "deep.json", "mimeType": "application/json", "buffer": deep})
            expect(page.get_by_text("Verification failed", exact=True)).to_be_visible()
            expect(page.get_by_role("button", name="Download bundle.json", exact=True)).to_be_disabled()
            page.get_by_role("button", name="Back to current bundle").click()

            def visit(path):
                page.evaluate("path => location.hash = path", path)
                expect(page.locator("h1")).to_have_text(path.strip("/").capitalize() or "Overview")

            def connect(url):
                visit("/settings")
                page.get_by_label("API base URL").fill(url)
                page.get_by_role("button", name="Connect", exact=True).click()
                expect(page.get_by_text("Connected.", exact=False)).to_be_visible()

            connect("https://foundry-a.invalid")
            token = page.get_by_label("Access token", exact=False)
            token.fill("synthetic-token-A")
            visit("/")
            page.get_by_role("button", name="Run pipeline", exact=True).click()
            expect(page.get_by_role("button", name="Run pipeline", exact=True)).to_be_enabled()
            assert creates[-1]["authorization"] == "Bearer synthetic-token-A"
            connect("https://foundry-b.invalid")
            expect(token).to_have_value("")
            visit("/")
            page.get_by_role("button", name="Run pipeline", exact=True).click()
            expect(page.get_by_role("button", name="Run pipeline", exact=True)).to_be_enabled()
            assert creates[-1]["authorization"] is None
            state["bad_run"] = True
            page.get_by_role("button", name="Run pipeline", exact=True).click()
            expect(page.get_by_text("Run failed: Invalid bundle structure; previous bundle retained", exact=False)).to_be_visible()
            state["bad_run"] = False
            visit("/verify")
            zip_link = page.get_by_role("link", name="Bundle .zip (with Python verifier)")
            expect(zip_link).to_have_attribute("href", "https://foundry-b.invalid/api/runs/synthetic-2/bundle.zip")
            connect("http://remote.invalid")
            token.fill("synthetic-denied")
            expect(token).to_have_value("")
            page.get_by_label("Allow sending a token unencrypted", exact=False).check()
            token.fill("synthetic-explicit-consent")
            expect(token).to_have_value("synthetic-explicit-consent")
            for width, height in [(1440, 900), (390, 844)]:
                for scheme in ["light", "dark"]:
                    page.set_viewport_size({"width": width, "height": height})
                    page.emulate_media(color_scheme=scheme)
                    if page.locator("html").get_attribute("data-theme") != scheme:
                        page.get_by_role("button", name=f"Switch to {scheme} mode").click()
                    page.screenshot(path=str(args.output / f"settings-{width}-{scheme}.png"), full_page=True, animations="disabled")
            page.get_by_role("button", name="Use offline demo", exact=True).click()
            expect(token).to_have_value("")
            visit("/gate")
            page.locator("summary").filter(has_text="Edit raw request").click()
            page.locator("textarea").fill(json.dumps({"agent": "manager", "action": "devin.session.create", "delegation": {"child_scope": {}}}))
            expect(page.get_by_role("alert")).to_contain_text("Invalid request structure")
            assert not errors, errors
            assert not blocked, blocked
            browser.close()
        print("Browser boundaries: selected upload/server/download, stale response, invalid JSON, API token switch/offline/HTTP consent, malformed run and raw editor passed")
        print("8 screenshots captured: desktop/mobile, light/dark, Verify and Settings")
        print("0 unexpected external requests; 0 page errors")
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()

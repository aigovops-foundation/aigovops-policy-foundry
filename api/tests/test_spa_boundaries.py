"""Load a separate app instance so static configuration cannot affect other API tests."""
import importlib.util
import shutil
import sys

from fastapi.testclient import TestClient
from app import main


def test_spa_cannot_serve_prefix_sibling_or_symlink(tmp_path, monkeypatch):
    web = tmp_path / "web"
    web.mkdir()
    (web / "assets").mkdir()
    (web / "index.html").write_text("SYNTHETIC_INDEX")
    (web / "allowed.txt").write_text("SYNTHETIC_ALLOWED")
    sibling = tmp_path / "web-private"
    sibling.mkdir()
    (sibling / "marker.txt").write_text("SYNTHETIC_REVIEW_MARKER")
    (web / "linked.txt").symlink_to(sibling / "marker.txt")
    monkeypatch.setenv("FOUNDRY_WEB_DIST", str(web))
    spec = importlib.util.spec_from_file_location("spa_boundary_app", main.__file__)
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, module)
    spec.loader.exec_module(module)
    try:
        with TestClient(module.app) as client:
            assert client.get("/allowed.txt").text == "SYNTHETIC_ALLOWED"
            assert client.get("/dashboard/deep-link").text == "SYNTHETIC_INDEX"
            assert client.get("/").text == "SYNTHETIC_INDEX"
            for path in ("/%2e%2e/web-private/marker.txt", "/linked.txt"):
                response = client.get(path)
                assert response.status_code == 200
                assert response.text == "SYNTHETIC_INDEX"
    finally:
        shutil.rmtree(module.WORK)

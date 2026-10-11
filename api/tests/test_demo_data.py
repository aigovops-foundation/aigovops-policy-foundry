"""The committed dashboard demo bundle must verify with the Python verifier (cross-language check)."""
import json, pathlib, tempfile
from foundry.verify_bundle import verify

DEMO = pathlib.Path(__file__).resolve().parents[2] / "web/public/demo/bundle.json"


def test_committed_demo_bundle_verifies():
    b = json.loads(DEMO.read_text())
    with tempfile.TemporaryDirectory() as t:
        for rel, content in b["files"].items():
            p = pathlib.Path(t) / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content)
        res = verify(pathlib.Path(t))
    assert res["ok"], res

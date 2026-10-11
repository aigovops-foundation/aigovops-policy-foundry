#!/usr/bin/env python3
"""Regenerate the offline demo data the dashboard, desktop and mobile apps ship with.

Writes web/public/demo/{bundle.json, run.json, agents.json}. Keys are freshly generated on each
run, so the committed demo bundle changes every time; both the Python and TypeScript test suites
verify whatever is committed.
"""
import json, pathlib, sys, tempfile
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "api"))
from foundry import gate, pipeline  # noqa: E402

out = ROOT / "web/public/demo"
out.mkdir(parents=True, exist_ok=True)
with tempfile.TemporaryDirectory() as t:
    d = pathlib.Path(t) / "bundle"
    s = pipeline.run(d)
    s.pop("log")
    (out / "bundle.json").write_text(json.dumps(pipeline.bundle_json(d)))
    (out / "run.json").write_text(json.dumps(s, indent=1))
(out / "agents.json").write_text(json.dumps(gate.manifest(), indent=1))
print("demo data written:", s["receipts"], "receipts, verdict", s["verdict"], "engines", s["gate_engine"], s["verifier_engine"])

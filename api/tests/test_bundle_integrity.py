"""Packet integrity and runtime JSON shape checks across CLI and HTTP verification."""
import copy
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from foundry.verify_bundle import validate_packet_display

DEMO = json.loads((Path(__file__).resolve().parents[2] / "web/public/demo/bundle.json").read_text())


def verify(files):
    response = TestClient(app, raise_server_exceptions=False).post("/api/verify", json={**DEMO, "files": files})
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.parametrize("change", ["mutate", "remove", "swap", "no-commitment", "duplicate-commitment"])
def test_packet_integrity(change):
    files = copy.deepcopy(DEMO["files"])
    if change == "remove":
        del files["underwriting_packet.json"]
    elif change in ("mutate", "swap"):
        packet = json.loads(files["underwriting_packet.json"])
        packet["metrics"]["gate_coverage_bp"] = 1
        if change == "swap":
            packet["tenant"] = "another-demo-tenant"
        files["underwriting_packet.json"] = json.dumps(packet)
    else:
        receipts = [json.loads(s) for s in files["receipts.ndjson"].splitlines()]
        packet = next(r for r in receipts if r["type"] == "underwriting_packet")
        if change == "no-commitment":
            packet["type"] = "review"
        else:
            receipts.append(packet)
        files["receipts.ndjson"] = "\n".join(map(json.dumps, receipts))
    result = verify(files)
    assert not result["ok"]
    assert not next(c for c in result["checks"] if c["name"] == "underwriting-packet")["ok"]


@pytest.mark.parametrize("file", ["manifest.json", "statement.dsse.json", "checkpoint.json", "inclusion_bundle_signed.json", "underwriting_packet.json"])
@pytest.mark.parametrize("value", [None, [], {}, 7, "bad"])
def test_wrong_json_shapes_are_structured_failures(file, value):
    files = copy.deepcopy(DEMO["files"])
    files[file] = json.dumps(value)
    assert not verify(files)["ok"]


@pytest.mark.parametrize("field,value", [("body", []), ("body", None), ("sig", {}), ("key_id", []), ("counter", None),
                                        ("ts_ns", "not-nanoseconds"), ("body", {"request_id": {}}), ("body", {"approvers": None})])
def test_malformed_receipt_fields(field, value):
    files = copy.deepcopy(DEMO["files"])
    rows = files["receipts.ndjson"].splitlines()
    row = json.loads(rows[0]); row[field] = value; rows[0] = json.dumps(row)
    files["receipts.ndjson"] = "\n".join(rows)
    assert not verify(files)["ok"]


@pytest.mark.parametrize("signatures", [None, {}, [None], [{"keyid": [], "sig": {}}]])
def test_malformed_signature_fields(signatures):
    files = copy.deepcopy(DEMO["files"])
    env = json.loads(files["statement.dsse.json"]); env["signatures"] = signatures
    files["statement.dsse.json"] = json.dumps(env)
    assert not verify(files)["ok"]


def test_empty_receipt_log():
    assert not verify({**DEMO["files"], "receipts.ndjson": ""})["ok"]


@pytest.mark.parametrize("patch", [{"risk_tier": {}}, {"pillars": {"unexpected": {}}},
                                   {"pillars": {"unexpected": "bad"}}, {"pillars": {"unexpected": 10001}}])
def test_packet_display_values_are_validated_before_rendering(patch):
    packet = json.loads(DEMO["files"]["underwriting_packet.json"])
    with pytest.raises(ValueError):
        validate_packet_display({**packet, **patch})


def test_deep_manifest_returns_structure_failure_not_500():
    assert not verify({**DEMO["files"], "manifest.json": "[" * 2000 + "0" + "]" * 2000})["ok"]

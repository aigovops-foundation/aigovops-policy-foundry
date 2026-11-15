"""Untrusted bundle manifests must not become arbitrary filesystem reads."""
import hashlib
import json
import os
from pathlib import Path

import pytest

from foundry import verify_bundle as vb

DEMO = Path(__file__).resolve().parents[2] / "web/public/demo/bundle.json"


@pytest.fixture
def bundle(tmp_path):
    root = tmp_path / "bundle"
    for rel, content in json.loads(DEMO.read_text())["files"].items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
    return root


def manifest(root, value):
    (root / "manifest.json").write_text(json.dumps(value))


def assert_structure_failure(root, message=None):
    result = vb.verify(root)
    assert not result["ok"]
    assert result["checks"][0]["name"] == "structure"
    if message:
        assert message in result["checks"][0]["detail"]


@pytest.mark.parametrize("value", [None, [], "bad", 42, {}, {"a": None}, {"a": "0" * 63}, {"a": 12}])
def test_invalid_manifest_structure(bundle, value):
    manifest(bundle, value)
    assert_structure_failure(bundle)


@pytest.mark.parametrize("rel", ["../marker", "nested/../../marker", "/etc/passwd", "", ".", "a/./b",
                                      "a//b", "a/", "C:/marker", r"C:\marker", r"\\host\marker", "a\0b"])
def test_all_manifest_entries_validated_before_artifact_or_key_access(bundle, rel, monkeypatch):
    contents = json.loads((bundle / "manifest.json").read_text())
    contents[rel] = "0" * 64
    manifest(bundle, contents)
    paths = []
    original = vb._BundleReader.path

    def track(self, path, *args, **kwargs):
        paths.append(path)
        return original(self, path, *args, **kwargs)

    monkeypatch.setattr(vb._BundleReader, "path", track)
    assert_structure_failure(bundle, "unsafe bundle path")
    assert paths == ["manifest.json"]


def test_absolute_marker_digest_probe_rejected_before_read(bundle, tmp_path, monkeypatch):
    marker = tmp_path / "outside"
    marker.write_bytes(b"synthetic-review-marker")
    manifest(bundle, {str(marker): hashlib.sha256(marker.read_bytes()).hexdigest()})
    original = vb._BundleReader.bytes
    reads = []

    def track(self, rel):
        reads.append(rel)
        return original(self, rel)

    monkeypatch.setattr(vb._BundleReader, "bytes", track)
    assert_structure_failure(bundle, "unsafe bundle path")
    assert reads == ["manifest.json"]


@pytest.mark.parametrize("rel", ["artifacts/policy/ai_code_change.rego", "artifacts/policy",
                                     "keys", "keys/arbiter.ed25519.pub.hex", "manifest.json", "receipts.ndjson"])
def test_symlink_components_rejected(bundle, tmp_path, rel):
    source = bundle / rel
    outside = tmp_path / "linked-target"
    source.rename(outside)
    source.symlink_to(outside, target_is_directory=outside.is_dir())
    assert_structure_failure(bundle, "symlink")


def test_in_bundle_symlink_also_rejected(bundle):
    target = bundle / "artifacts/policy/ai_code_change.rego"
    real = target.with_suffix(".real")
    target.rename(real)
    target.symlink_to(real.name)
    assert_structure_failure(bundle, "symlink")


@pytest.mark.parametrize("kind", ["directory", "fifo"])
def test_nonregular_artifacts_rejected_without_opening(bundle, kind):
    target = bundle / "artifacts/policy/ai_code_change.rego"
    target.unlink()
    if kind == "directory":
        target.mkdir()
    else:
        os.mkfifo(target)
    assert_structure_failure(bundle, "regular files")


def test_manifest_entry_limit(bundle, monkeypatch):
    monkeypatch.setattr(vb, "MAX_MANIFEST_ENTRIES", 1)
    assert_structure_failure(bundle, "bounded object")


def test_cumulative_bytes_include_metadata_and_enforce_exact_boundary(bundle, monkeypatch):
    artifacts = json.loads((bundle / "manifest.json").read_text())
    checked = ["manifest.json", "statement.dsse.json", "receipts.ndjson", "checkpoint.json", "underwriting_packet.json",
               "inclusion_bundle_signed.json", *["artifacts/" + rel for rel in artifacts],
               *["keys/" + p.name for p in (bundle / "keys").glob("*.pub.hex")]]
    size = sum((bundle / rel).stat().st_size for rel in checked)
    monkeypatch.setattr(vb, "MAX_BUNDLE_BYTES", size)
    assert vb.verify(bundle)["ok"]
    monkeypatch.setattr(vb, "MAX_BUNDLE_BYTES", size - 1)
    assert_structure_failure(bundle, "total byte limit")


def test_oversized_manifest_rejected(bundle, monkeypatch):
    monkeypatch.setattr(vb, "MAX_BUNDLE_BYTES", 1)
    assert_structure_failure(bundle, "total byte limit")


def test_binary_artifact_digest_is_not_text_normalized(bundle):
    data = b"\xff\x00\r\n"
    rel = "policy/ai_code_change.rego"
    (bundle / "artifacts" / rel).write_bytes(data)
    contents = json.loads((bundle / "manifest.json").read_text())
    contents[rel] = hashlib.sha256(data).hexdigest()
    manifest(bundle, contents)
    result = vb.verify(bundle)
    assert next(c for c in result["checks"] if c["name"] == "manifest")["ok"]
    assert not result["ok"]  # The existing signed statement still binds the original bytes.

"""Release/native workflow contracts; no hosted workflows or services are called."""
import importlib.util
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("approval", ROOT / "scripts/check_release_approval.py")
approval = importlib.util.module_from_spec(spec)
spec.loader.exec_module(approval)


def workflow(name):
    return yaml.load((ROOT / f".github/workflows/{name}.yml").read_text(), Loader=yaml.BaseLoader)


def test_release_verifies_the_tagged_revision_before_protected_publication():
    release = workflow("release")
    assert release["jobs"]["verify"]["uses"] == "./.github/workflows/ci.yml"
    assert "workflow_call" in workflow("ci")["on"]
    image = release["jobs"]["image"]
    assert image["needs"] == "verify" and image["environment"] == "release"
    steps = image["steps"]
    checkout = steps[0]
    assert checkout["with"]["ref"] == "${{ github.sha }}"
    assert "check_release_approval.py" in steps[1]["run"]
    assert "environments/release" in steps[1]["run"]
    assert not any("secrets." in str(job) for job in [release["jobs"]["verify"]])
    ci = workflow("ci")
    assert {"policy", "api", "web", "terraform", "container"} <= ci["jobs"].keys()


def test_native_shared_web_changes_are_checked_without_signing_secrets():
    native = workflow("native")
    assert "web/**" in native["on"]["pull_request"]["paths"]
    assert "apps/native/**" in native["on"]["pull_request"]["paths"]
    assert "secrets." not in (ROOT / ".github/workflows/native.yml").read_text()


@pytest.mark.parametrize("value", [None, [], {}, {"name": "release"},
    {"name": "release", "protection_rules": None},
    {"name": "release", "protection_rules": [{"type": "required_reviewers", "prevent_self_review": True, "reviewers": []}]},
    {"name": "release", "protection_rules": [{"type": "required_reviewers", "reviewers": [{}]}]}])
def test_missing_approval_configuration_fails_closed(value):
    assert not approval.protected_environment(value)


def test_independent_required_reviewers():
    assert approval.protected_environment({"name": "release", "protection_rules": [
        {"type": "required_reviewers", "prevent_self_review": True, "reviewers": [{"type": "Team", "reviewer": {"name": "review-circle"}}]}]})

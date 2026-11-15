"""Fail closed unless publication is gated by independent environment reviewers."""
import json
import sys


def protected_environment(value):
    if not isinstance(value, dict) or value.get("name") != "release":
        return False
    rules = value.get("protection_rules", [])
    if not isinstance(rules, list):
        return False
    return any(isinstance(r, dict) and r.get("type") == "required_reviewers"
               and r.get("prevent_self_review") is True
               and isinstance(r.get("reviewers"), list) and bool(r["reviewers"])
               for r in rules)


if __name__ == "__main__":
    with open(sys.argv[1]) as f:
        value = json.load(f)
    if not protected_environment(value):
        sys.exit("Release environment needs required reviewers and prevent-self-review before publication")
    print("Release environment requires independent human approval")

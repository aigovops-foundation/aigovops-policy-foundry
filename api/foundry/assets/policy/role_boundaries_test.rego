package foundry.gate_test

import rego.v1

import data.foundry.gate

# --- writer ------------------------------------------------------------------

test_writer_can_push_feature_branch if {
	gate.decision.result == "allow" with input as {"agent": "policy_writer", "action": "git.push", "target": "policy-src/branches/foundry/req-1042"}
}

test_writer_cannot_push_main if {
	d := gate.decision with input as {"agent": "policy_writer", "action": "git.push", "target": "policy-src/main"}
	d.result == "deny"
	"forbidden:git.push:policy-src/main" in d.reasons
}

test_writer_cannot_touch_tests_repo if {
	d := gate.decision with input as {"agent": "policy_writer", "action": "git.push", "target": "policy-tests/branches/foundry/req-1042"}
	d.result == "deny"
}

test_writer_merge_is_escalated_not_executed if {
	d := gate.decision with input as {"agent": "policy_writer", "action": "git.merge", "target": "policy-src/main"}
	d.result == "escalate"
}

test_writer_blocked_from_ot_zone if {
	d := gate.decision with input as {"agent": "policy_writer", "action": "network.connect", "target": "ot/level2/historian"}
	d.result == "deny"
	"ot-zone-conduit" in d.reasons
}

# --- verifier ----------------------------------------------------------------

test_verifier_can_push_tests if {
	gate.decision.result == "allow" with input as {"agent": "test_verifier", "action": "git.push", "target": "policy-tests/branches/foundry/req-1042"}
}

test_verifier_cannot_edit_policy_source if {
	d := gate.decision with input as {"agent": "test_verifier", "action": "git.push", "target": "policy-src/branches/foundry/req-1042"}
	d.result == "deny"
	"forbidden:git.push:policy-src/**" in d.reasons
}

# --- auditor -----------------------------------------------------------------

test_auditor_can_request_changes if {
	gate.decision.result == "allow" with input as {"agent": "compliance_auditor", "action": "pr.review.request_changes"}
}

test_auditor_cannot_approve_pr if {
	d := gate.decision with input as {"agent": "compliance_auditor", "action": "pr.review.approve"}
	d.result == "deny"
}

test_auditor_cannot_sign if {
	d := gate.decision with input as {"agent": "compliance_auditor", "action": "artifact.sign"}
	d.result == "escalate"
}

# --- manager / delegation ----------------------------------------------------

test_manager_cannot_push if {
	d := gate.decision with input as {"agent": "manager", "action": "git.push", "target": "policy-src/branches/foundry/x"}
	d.result == "deny"
}

test_delegation_narrowing_allowed if {
	gate.decision.result == "allow" with input as {
		"agent": "manager", "action": "devin.session.create",
		"delegation": {
			"to": "policy_writer",
			"parent_scope": ["git.read:policy-src", "git.push:policy-src/branches/foundry/*", "pr.open:policy-src", "opa.test.local"],
			"child_scope": ["git.read:policy-src", "git.push:policy-src/branches/foundry/*"],
		},
	}
}

test_delegation_widening_denied if {
	d := gate.decision with input as {
		"agent": "manager", "action": "devin.session.create",
		"delegation": {
			"to": "policy_writer",
			"parent_scope": ["git.read:policy-src"],
			"child_scope": ["git.read:policy-src", "git.push:policy-src/branches/foundry/*"],
		},
	}
	d.result == "deny"
	"scope-widening:git.push:policy-src/branches/foundry/*" in d.reasons
}

test_delegation_beyond_role_denied if {
	d := gate.decision with input as {
		"agent": "manager", "action": "devin.session.create",
		"delegation": {"to": "test_verifier", "parent_scope": ["git.push:policy-src/branches/foundry/*"], "child_scope": ["git.push:policy-src/branches/foundry/*"]},
	}
	d.result == "deny"
}

# --- relay / limits ----------------------------------------------------------

test_relay_bypass_denied if {
	# writer tries to push "on behalf of" the auditor, who is forbidden git.push
	d := gate.decision with input as {"agent": "policy_writer", "on_behalf_of": "compliance_auditor", "action": "git.push", "target": "policy-src/branches/foundry/x"}
	d.result == "deny"
	"relay-bypass" in d.reasons
}

test_recursion_limit if {
	d := gate.decision with input as {"agent": "policy_writer", "action": "opa.test.local", "depth": 4}
	"recursion-depth-exceeded" in d.reasons
}

test_unknown_agent_denied if {
	d := gate.decision with input as {"agent": "rogue", "action": "git.read"}
	d.result == "deny"
}

# --- human approvals (HITL-4.3) ----------------------------------------------

owner := {"subject": "u-alvarez", "groups": ["grp-ai-policy-owners"]}

board := {"subject": "u-chen", "groups": ["grp-ai-governance-board"]}

test_two_distinct_authorized_approvers_ok if {
	gate.approval_ok with input as {"requester": "u-patel", "signer": "u-okafor", "approvals": [owner, board]}
}

test_requester_cannot_self_approve if {
	errs := gate.approval_errors with input as {"requester": "u-alvarez", "signer": "u-okafor", "approvals": [owner, board]}
	"requester-counted-as-approver" in errs
}

test_single_approver_rejected if {
	errs := gate.approval_errors with input as {"requester": "u-patel", "signer": "u-okafor", "approvals": [owner]}
	"fewer-than-two-approvers" in errs
}

test_agent_cannot_approve if {
	errs := gate.approval_errors with input as {"requester": "u-patel", "signer": "u-okafor", "approvals": [owner, {"subject": "compliance_auditor", "groups": []}]}
	"agent-cannot-approve" in errs
}

test_signer_cannot_approve if {
	errs := gate.approval_errors with input as {"requester": "u-patel", "signer": "u-chen", "approvals": [owner, board]}
	"signer-also-approver" in errs
}

# --- regressions found by the parity corpus (fail-open on missing fields) ----

test_delegation_without_parent_scope_denied if {
	d := gate.decision with input as {
		"agent": "manager", "action": "devin.session.create",
		"delegation": {"to": "policy_writer", "child_scope": ["git.read:policy-src"]},
	}
	d.result == "deny"
	"delegation-missing-parent-scope" in d.reasons
	"scope-widening:git.read:policy-src" in d.reasons
}

test_non_delegating_agent_cannot_delegate if {
	d := gate.decision with input as {
		"agent": "policy_writer", "action": "devin.session.create",
		"delegation": {"to": "test_verifier", "parent_scope": [], "child_scope": []},
	}
	"delegation-target-not-allowed" in d.reasons
}

test_delegation_to_unknown_agent_denied_for_every_capability if {
	d := gate.decision with input as {
		"agent": "manager", "action": "devin.session.create",
		"delegation": {"to": "nobody", "parent_scope": ["git.read:policy-src"], "child_scope": ["git.read:policy-src"]},
	}
	"delegation-target-not-allowed" in d.reasons
	"exceeds-role-capability:git.read:policy-src" in d.reasons
}

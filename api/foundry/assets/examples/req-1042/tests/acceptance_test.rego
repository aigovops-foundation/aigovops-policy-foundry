# EXAMPLE OUTPUT of the Test Verifier agent, phase A: acceptance vectors written from
# REQ-1042's text only, committed (and receipted) BEFORE the writer's policy was visible.
package acme.ai_code_change_test

import rego.v1

import data.acme.ai_code_change as p

good := {
	"ai_assisted": true, "author": "devin-session-7f", "target_zone": "it-l4",
	"reviewers": [{"id": "u-chen", "kind": "human", "roles": []}],
	"requirement_ids": ["REQ-1042"], "tests_passed": true, "sbom_digest": "sha256:ab",
	"safety_relevant": false,
}

test_compliant_change_allowed if p.allow with input as {"change": good}

test_ot_target_without_moc_denied if {
	not p.allow with input as {"change": object.union(good, {"target_zone": "ot-l2"})}
}

test_ot_target_with_moc_allowed if {
	p.allow with input as {"change": object.union(good, {"target_zone": "ot-l2", "moc_ticket": "MOC-881"})}
}

test_self_review_does_not_count if {
	not p.allow with input as {"change": object.union(good, {"reviewers": [{"id": "devin-session-7f", "kind": "human", "roles": []}]})}
}

test_agent_reviewer_does_not_count if {
	not p.allow with input as {"change": object.union(good, {"reviewers": [{"id": "auditor", "kind": "agent", "roles": []}]})}
}

test_safety_relevant_needs_fs_and_two_humans if {
	v := p.violations with input as {"change": object.union(good, {"safety_relevant": true})}
	"REQ-1042.3:functional-safety-review" in v
	"REQ-1042.3:two-human-reviewers" in v
}

test_safety_relevant_satisfied if {
	p.allow with input as {"change": object.union(good, {
		"safety_relevant": true,
		"reviewers": [{"id": "u-chen", "kind": "human", "roles": []}, {"id": "u-ito", "kind": "human", "roles": ["functional-safety"]}],
	})}
}

test_missing_trace_denied if {
	not p.allow with input as {"change": object.union(good, {"requirement_ids": []})}
}

test_missing_sbom_denied if {
	not p.allow with input as {"change": object.remove(good, ["sbom_digest"])}
}

test_failed_tests_denied if {
	not p.allow with input as {"change": object.union(good, {"tests_passed": false})}
}

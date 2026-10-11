# EXAMPLE OUTPUT of the Policy Writer agent for request REQ-1042 (illustrative fixture).
# Requirement REQ-1042: "AI-assisted changes to plant software must be traceable, human-reviewed,
# tested, and may never be deployed directly into an OT zone; safety-relevant changes need a
# functional-safety reviewer."
package acme.ai_code_change

import rego.v1

ot_zones := {"ot-l0", "ot-l1", "ot-l2", "ot-l3"} # IEC 62443 zones below the IT/OT DMZ

default allow := false

allow if count(violations) == 0

# REQ-1042.1 -- AI-assisted changes cannot target an OT zone directly; route through MOC
violations contains "REQ-1042.1:ot-target-requires-moc" if {
	input.change.ai_assisted
	input.change.target_zone in ot_zones
	not input.change.moc_ticket
}

# REQ-1042.2 -- at least one human reviewer who is not the author
violations contains "REQ-1042.2:independent-human-review" if {
	input.change.ai_assisted
	independent := {r | some r in input.change.reviewers; r.kind == "human"; r.id != input.change.author}
	count(independent) < 1
}

# REQ-1042.3 -- safety-relevant changes need a functional-safety reviewer and two humans
violations contains "REQ-1042.3:functional-safety-review" if {
	input.change.safety_relevant
	not has_fs_reviewer
}

violations contains "REQ-1042.3:two-human-reviewers" if {
	input.change.safety_relevant
	humans := {r.id | some r in input.change.reviewers; r.kind == "human"; r.id != input.change.author}
	count(humans) < 2
}

has_fs_reviewer if {
	some r in input.change.reviewers
	r.kind == "human"
	"functional-safety" in r.roles
}

# REQ-1042.4 -- every change traces to at least one approved requirement
violations contains "REQ-1042.4:requirement-trace" if count(object.get(input.change, "requirement_ids", [])) == 0

# REQ-1042.5 -- tests passed and SBOM attached
violations contains "REQ-1042.5:tests" if not input.change.tests_passed

violations contains "REQ-1042.5:sbom" if not input.change.sbom_digest

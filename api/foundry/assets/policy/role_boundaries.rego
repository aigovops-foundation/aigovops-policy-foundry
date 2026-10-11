# Governed Policy Foundry -- runtime gate for agent actions (Beacon policy decision point)
#
# Evaluated by the Beacon gate before every governed action crosses a customer conduit
# (OVERT TOOL-1.1/1.2). Every decision -- allow, deny, escalate -- produces a receipt.
# data.agents / data.humans / data.runtime_limits come from config/agents.yaml.
package foundry.gate

import rego.v1

default decision := {"result": "deny", "reasons": ["default-deny"]}

requested := concat(":", [input.action, input.target]) if input.target
requested := input.action if not input.target

agent := data.agents[input.agent]

# ---------------------------------------------------------------- matching helpers

cap_matches(cap) if cap == input.action

cap_matches(cap) if {
	contains(cap, ":")
	glob.match(cap, ["/"], requested)
}

forbidden_hit contains f if {
	some f in agent.forbidden
	not contains(f, ":")
	f == input.action
}

forbidden_hit contains f if {
	some f in agent.forbidden
	contains(f, ":")
	glob.match(f, ["/"], requested)
}

capability_ok if {
	some cap in agent.capabilities
	cap_matches(cap)
}

# Actions that always need a human in the loop (OVERT TOOL-4.1)
human_only_actions := {"policy.approve", "artifact.sign", "git.merge", "underwriting.release"}

# ---------------------------------------------------------------- deny reasons

deny contains "unknown-agent" if not data.agents[input.agent]

deny contains sprintf("forbidden:%s", [f]) if some f in forbidden_hit

deny contains "no-matching-capability" if {
	data.agents[input.agent]
	not capability_ok
}

deny contains "human-only-action" if input.action in human_only_actions

deny contains "ot-zone-conduit" if startswith(object.get(input, "target", ""), "ot/")

# Relay / confused-deputy detection (OVERT MULTI-1.3): an agent acting on behalf of
# another agent may not perform anything the originating agent is itself forbidden to do.
deny contains "relay-bypass" if {
	origin := data.agents[input.on_behalf_of]
	some f in origin.forbidden
	not contains(f, ":")
	f == input.action
}

deny contains "relay-bypass" if {
	origin := data.agents[input.on_behalf_of]
	some f in origin.forbidden
	contains(f, ":")
	glob.match(f, ["/"], requested)
}

# Delegation must narrow or preserve scope, never widen (OVERT IDENT-1.3).
# Missing fields resolve to [] via object.get so an omitted parent_scope, an agent with no
# may_delegate_to, or an unknown target agent all fail CLOSED. (A reference to an undefined
# value inside `not x in ref` makes the rule silently not fire -- found by the parity corpus.)
delegation_parent_scope := object.get(input.delegation, "parent_scope", [])

delegator_targets := object.get(data.agents, [input.agent, "may_delegate_to"], [])

delegate_caps := object.get(data.agents, [input.delegation.to, "capabilities"], [])

deny contains "delegation-target-not-allowed" if {
	input.delegation
	not input.delegation.to in delegator_targets
}

deny contains "delegation-missing-parent-scope" if {
	input.delegation
	not input.delegation.parent_scope
}

deny contains sprintf("scope-widening:%s", [c]) if {
	input.delegation
	some c in input.delegation.child_scope
	not c in delegation_parent_scope
}

deny contains sprintf("exceeds-role-capability:%s", [c]) if {
	input.delegation
	some c in input.delegation.child_scope
	not c in delegate_caps
}

# Runtime limits (OVERT TOOL-3.4)
deny contains "recursion-depth-exceeded" if {
	object.get(input, "depth", 0) > data.runtime_limits.max_recursion_depth
}

deny contains "repeat-limit-exceeded" if {
	object.get(input, "identical_call_count", 0) > data.runtime_limits.identical_call_repeat_limit
}

# ---------------------------------------------------------------- decision

decision := {"result": "allow", "reasons": []} if count(deny) == 0

decision := {"result": "deny", "reasons": sort([r | some r in deny])} if {
	count(deny) > 0
	not escalate_only
}

# A human-only action requested by an agent is escalated to the approval queue
# instead of silently denied, so the request is visible and attested (TOOL-4.2).
escalate_only if {
	input.action in human_only_actions
	every r in deny {
		benign_for_escalation(r)
	}
}

benign_for_escalation(r) if r in {"human-only-action", "no-matching-capability"}

benign_for_escalation(r) if r == sprintf("forbidden:%s", [input.action])

decision := {"result": "escalate", "reasons": sort([r | some r in deny])} if {
	count(deny) > 0
	escalate_only
}

# ================================================================ human approvals
# Evaluated separately at the approval step (package foundry.approval would also work;
# kept here so one bundle carries the whole gate).

approval_errors contains "fewer-than-two-approvers" if count({a.subject | some a in input.approvals}) < 2

approval_errors contains "requester-is-sole-approver" if {
	others := {a.subject | some a in input.approvals; a.subject != input.requester}
	count(others) < 1
}

approval_errors contains "requester-counted-as-approver" if {
	some a in input.approvals
	a.subject == input.requester
}

approval_errors contains sprintf("approver-not-authorized:%s", [a.subject]) if {
	some a in input.approvals
	not approver_authorized(a)
}

approval_errors contains "agent-cannot-approve" if {
	some a in input.approvals
	data.agents[a.subject]
}

approval_errors contains "signer-also-approver" if {
	some a in input.approvals
	a.subject == input.signer
}

approver_authorized(a) if {
	some role, h in data.humans
	h.idp_group in a.groups
	"policy.approve" in h.may
}

approval_ok if count(approval_errors) == 0

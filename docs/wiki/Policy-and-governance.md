# Policy and governance

For requesters, policy owners, Governance Board approvers, signing officers, OT security leads and functional safety engineers.

> **Start here:** Read the plain-language REQ-1042 policy and its Rego implementation side by side.

- [REQ-1042 plain-language example](../../api/foundry/assets/examples/req-1042/docs/ai_code_change.md)
- [REQ-1042 Rego policy](../../api/foundry/assets/examples/req-1042/policy/ai_code_change.rego)
- [Requirement context and decisions: BLUEPRINT §§2.4, 15.1–15.2](../../docs/BLUEPRINT.md)

## Who can do what

The current manifest defines four agent roles. The dashboard's
[Agents view](../../web/src/pages/Agents.tsx) is at `#/agents` after you start
the local app; the [role manifest](../../api/foundry/assets/config/agents.yaml)
is the source of truth.

| Role | Can | Cannot |
|---|---|---|
| Manager | Plan, delegate narrowed scopes, run sessions and request human approval | Write policy, approve, sign or push |
| Policy Writer | Draft policy and tests on its permitted branches, open a PR | Edit tests, merge, approve, sign or reach an OT zone |
| Test Verifier | Write tests before seeing the draft, run tests and mutation checks | Push policy, merge, approve or sign |
| Compliance Auditor | Map controls, file findings and request changes | Approve, merge, push or sign |

## Approval and change journey

1. A requester submits a requirement. The requester cannot be the sole approver and
   does not count among the two policy approvers.
2. Two distinct authorized humans approve. A separate signing officer signs the
   approved bytes. Agents cannot approve or sign.
3. The work lands through a pull request, maintainer review and CI. Releases also
   need Review Circle sign-off; see [release guidance](../../RELEASING.md).

## Write a useful requirement

Use the [REQ-1042 example](../../api/foundry/assets/examples/req-1042/docs/ai_code_change.md)
as a model. State rules that can be checked, not a desired outcome alone.

```text
Requirement: What must or must not happen?
Scope: Which systems, changes and people are covered?
Owner: Who is accountable for the policy?
Risk tier: What risk tier applies, and why?
Exceptions: Who may request one, how is it time-limited, and how is it recorded?
Review date: When must this requirement be reviewed?
```

## Decisions still waiting on people

BLUEPRINT decisions D1–D7 are open. ADRs 0002–0006 are marked **Proposed**.
They cover the Devin deployment model, receipt profile, independent witness,
auditor model family, AIUC-1 control snapshot licensing, thresholds and predicate
ownership. Do not treat a proposal as a decision; see
[the decision table](../../docs/BLUEPRINT.md#152-decisions-needed).

[Back to Home](README.md)

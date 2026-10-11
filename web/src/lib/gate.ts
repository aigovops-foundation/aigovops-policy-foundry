// TypeScript port of api/foundry/assets/policy/role_boundaries.rego (Rego is authoritative).
// Held to OPA's output by the shared parity corpus: web/tests/gate.test.ts.
export type Manifest = {
  agents: Record<string, { capabilities?: string[]; forbidden?: string[]; may_delegate_to?: string[]; [k: string]: unknown }>;
  humans: Record<string, { idp_group: string; may: string[] }>;
  runtime_limits: { max_recursion_depth: number; identical_call_repeat_limit: number; [k: string]: number };
  [k: string]: unknown;
};
export type GateInput = {
  agent: string; action: string; target?: string; on_behalf_of?: string;
  delegation?: { to?: string; parent_scope?: string[] | false; child_scope?: string[] };
  depth?: number; identical_call_count?: number;
};
export type Decision = { result: "allow" | "deny" | "escalate"; reasons: string[] };

export const HUMAN_ONLY = new Set(["policy.approve", "artifact.sign", "git.merge", "underwriting.release"]);

const reCache = new Map<string, RegExp>();
export function globMatch(pattern: string, value: string): boolean {
  let re = reCache.get(pattern);
  if (!re) {
    let out = "";
    for (let i = 0; i < pattern.length; ) {
      if (pattern.startsWith("**", i)) { out += ".*"; i += 2; }
      else if (pattern[i] === "*") { out += "[^/]*"; i++; }
      else if (pattern[i] === "?") { out += "[^/]"; i++; }
      else { out += pattern[i].replace(/[.*+?^${}()|[\]\\]/g, "\\$&"); i++; }
    }
    re = new RegExp("^" + out + "$", "s");
    reCache.set(pattern, re);
  }
  return re.test(value);
}

const requested = (i: GateInput) => (i.target ? `${i.action}:${i.target}` : i.action);

function forbiddenHits(agent: { forbidden?: string[] }, i: GateInput): string[] {
  const req = requested(i);
  return (agent.forbidden ?? []).filter((f) => (f.includes(":") ? globMatch(f, req) : f === i.action));
}

const has = <T,>(o: Record<string, T>, k: string | undefined): k is string =>
  k !== undefined && Object.prototype.hasOwnProperty.call(o, k);

export function decide(i: GateInput, m: Manifest): Decision {
  const deny = new Set<string>();
  const agent = has(m.agents, i.agent) ? m.agents[i.agent] : undefined;
  const req = requested(i);
  if (!agent) deny.add("unknown-agent");
  else {
    forbiddenHits(agent, i).forEach((f) => deny.add(`forbidden:${f}`));
    const ok = (agent.capabilities ?? []).some((c) => c === i.action || (c.includes(":") && globMatch(c, req)));
    if (!ok) deny.add("no-matching-capability");
  }
  if (HUMAN_ONLY.has(i.action)) deny.add("human-only-action");
  if (typeof i.target === "string" && i.target.startsWith("ot/")) deny.add("ot-zone-conduit");
  if (has(m.agents, i.on_behalf_of) && forbiddenHits(m.agents[i.on_behalf_of], i).length) deny.add("relay-bypass");

  const d = i.delegation;
  if (d) {
    const may = agent?.may_delegate_to;
    if (!(may && d.to !== undefined && may.includes(d.to))) deny.add("delegation-target-not-allowed");
    if (d.parent_scope === undefined || d.parent_scope === false) deny.add("delegation-missing-parent-scope");
    const parent = Array.isArray(d.parent_scope) ? d.parent_scope : [];
    const toCaps = (has(m.agents, d.to) ? m.agents[d.to].capabilities : undefined) ?? [];
    for (const c of d.child_scope ?? []) {
      if (!parent.includes(c)) deny.add(`scope-widening:${c}`);
      if (!toCaps.includes(c)) deny.add(`exceeds-role-capability:${c}`);
    }
  }
  if ((i.depth ?? 0) > m.runtime_limits.max_recursion_depth) deny.add("recursion-depth-exceeded");
  if ((i.identical_call_count ?? 0) > m.runtime_limits.identical_call_repeat_limit) deny.add("repeat-limit-exceeded");

  const reasons = [...deny].sort();
  if (!reasons.length) return { result: "allow", reasons: [] };
  const benign = new Set(["human-only-action", "no-matching-capability", `forbidden:${i.action}`]);
  if (HUMAN_ONLY.has(i.action) && reasons.every((r) => benign.has(r))) return { result: "escalate", reasons };
  return { result: "deny", reasons };
}

export type ApprovalInput = { requester: string; signer: string; approvals: { subject: string; groups: string[] }[] };

export function approvalErrors(i: ApprovalInput, m: Manifest): string[] {
  const errs = new Set<string>();
  const subjects = new Set(i.approvals.map((a) => a.subject));
  if (subjects.size < 2) errs.add("fewer-than-two-approvers");
  if ([...subjects].filter((s) => s !== i.requester).length < 1) errs.add("requester-is-sole-approver");
  if (subjects.has(i.requester)) errs.add("requester-counted-as-approver");
  for (const a of i.approvals) {
    const authorized = Object.values(m.humans).some((h) => a.groups.includes(h.idp_group) && h.may.includes("policy.approve"));
    if (!authorized) errs.add(`approver-not-authorized:${a.subject}`);
    if (has(m.agents, a.subject)) errs.add("agent-cannot-approve");
    if (a.subject === i.signer) errs.add("signer-also-approver");
  }
  return [...errs].sort();
}

// Plain-language explanations for the UI
export const REASON_TEXT: Record<string, string> = {
  "unknown-agent": "This identity is not a registered agent.",
  "no-matching-capability": "The role has no capability that covers this action.",
  "human-only-action": "Only a person can do this. Sent to the approval queue.",
  "ot-zone-conduit": "Plant-floor (OT) systems are never reachable from the Foundry.",
  "relay-bypass": "An agent tried to act for another agent that is not allowed to do this.",
  "delegation-target-not-allowed": "This agent may not delegate to that role.",
  "delegation-missing-parent-scope": "Delegation must state the parent scope it narrows.",
  "recursion-depth-exceeded": "Too many nested calls. The session is stopped.",
  "repeat-limit-exceeded": "The same call repeated too often. The session is stopped.",
};
export function explain(r: string): string {
  if (REASON_TEXT[r]) return REASON_TEXT[r];
  if (r.startsWith("forbidden:")) return `Explicitly forbidden for this role (${r.slice(10)}).`;
  if (r.startsWith("scope-widening:")) return `Delegation would widen scope: ${r.slice(15)}.`;
  if (r.startsWith("exceeds-role-capability:")) return `Beyond the receiving role's capabilities: ${r.slice(24)}.`;
  return r;
}

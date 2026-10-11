import { useMemo, useState } from "react";
import { useStore } from "../lib/store";
import { approvalErrors, decide, explain, type GateInput } from "../lib/gate";

const PRESETS: { label: string; input: GateInput }[] = [
  { label: "Normal branch push", input: { agent: "policy_writer", action: "git.push", target: "policy-src/branches/foundry/REQ-1042-iter1" } },
  { label: "Injected: merge to main", input: { agent: "policy_writer", action: "git.merge", target: "policy-src/main" } },
  { label: "Injected: edit the tests", input: { agent: "policy_writer", action: "git.push", target: "policy-tests/branches/foundry/REQ-1042-vectors" } },
  { label: "Reach the plant floor", input: { agent: "policy_writer", action: "network.connect", target: "ot/l2/historian-plant3" } },
  { label: "Auditor tries to approve", input: { agent: "compliance_auditor", action: "pr.review.approve" } },
  { label: "Relay through another agent", input: { agent: "policy_writer", on_behalf_of: "compliance_auditor", action: "git.push", target: "policy-src/branches/foundry/x" } },
  { label: "Widen a delegation", input: { agent: "manager", action: "devin.session.create", delegation: { to: "policy_writer", parent_scope: ["git.read:policy-src"], child_scope: ["git.read:policy-src", "git.push:policy-src/main"] } } },
];
const ACTIONS = ["git.read", "git.push", "git.merge", "pr.open", "pr.review.approve", "pr.review.request_changes", "opa.test.local",
  "devin.session.create", "finding.file", "network.connect", "secret.read", "policy.approve", "artifact.sign", "underwriting.release"];
const LABEL = { allow: "Allow", deny: "Deny", escalate: "Escalate to a human" } as const;

const PEOPLE = [
  { subject: "u-patel", name: "Patel · requester", groups: ["grp-engineering"] },
  { subject: "u-alvarez", name: "Alvarez · policy owner", groups: ["grp-ai-policy-owners"] },
  { subject: "u-chen", name: "Chen · governance board", groups: ["grp-ai-governance-board"] },
  { subject: "u-okafor", name: "Okafor · signing officer", groups: ["grp-evidence-signers"] },
  { subject: "compliance_auditor", name: "Compliance Auditor (agent)", groups: [] },
];

export default function Gate() {
  const { manifest, mode, apiBase } = useStore();
  const [input, setInput] = useState<GateInput>(PRESETS[1].input);
  const [raw, setRaw] = useState<string | null>(null);
  const [server, setServer] = useState<{ result: string; engine: string } | null>(null);
  const [requester, setRequester] = useState("u-patel");
  const [signer, setSigner] = useState("u-okafor");
  const [approvers, setApprovers] = useState<string[]>(["u-alvarez", "u-chen"]);

  const parsed: GateInput | null = useMemo(() => {
    if (raw === null) return input;
    try { const v = JSON.parse(raw); return v && typeof v.agent === "string" && typeof v.action === "string" ? v : null; } catch { return null; }
  }, [raw, input]);
  if (!manifest) return null;
  const d = parsed ? decide(parsed, manifest) : null;
  const agents = Object.keys(manifest.agents);

  const set = (patch: Partial<GateInput>) => { setRaw(null); setServer(null); setInput((p) => ({ ...p, ...patch })); };
  const checkServer = async () => {
    if (!parsed) return;
    const r = await fetch(`${apiBase}/api/gate/evaluate`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(parsed) });
    const j = await r.json();
    setServer(r.ok ? { result: j.decision.result, engine: j.engine } : { result: "error", engine: String(r.status) });
  };
  const apErr = approvalErrors({ requester, signer, approvals: PEOPLE.filter((p) => approvers.includes(p.subject)) }, manifest);

  return (
    <div className="page">
      <section className="card">
        <h2>Try an action</h2>
        <p className="sub">Pick a scenario or build your own. The decision is computed on this device by the same rules the server enforces.</p>
        <div className="row chips" style={{ marginBottom: "var(--space-4)" }}>
          {PRESETS.map((p) => (
            <button key={p.label} className="btn" aria-pressed={JSON.stringify(p.input) === JSON.stringify(input) && raw === null}
              onClick={() => { setRaw(null); setServer(null); setInput(p.input); }}>{p.label}</button>
          ))}
        </div>
        <div className="grid g3">
          <label className="field">Agent
            <select className="input" value={input.agent} onChange={(e) => set({ agent: e.target.value })}>
              {agents.map((a) => <option key={a}>{a}</option>)}<option value="rogue">rogue (unregistered)</option>
            </select>
          </label>
          <label className="field">Action
            <select className="input" value={input.action} onChange={(e) => set({ action: e.target.value })}>
              {ACTIONS.map((a) => <option key={a}>{a}</option>)}
            </select>
          </label>
          <label className="field">Target
            <input className="input mono" value={input.target ?? ""} placeholder="e.g. policy-src/main"
              onChange={(e) => set({ target: e.target.value || undefined })} />
          </label>
        </div>
        <details style={{ marginTop: "var(--space-4)" }}>
          <summary className="small muted" style={{ cursor: "pointer" }}>Edit raw request (delegation, on_behalf_of, depth)</summary>
          <textarea className="input" aria-label="Raw gate request JSON" style={{ marginTop: "var(--space-2)" }}
            value={raw ?? JSON.stringify(input, null, 2)} onChange={(e) => { setRaw(e.target.value); setServer(null); }} />
          {parsed === null && <p className="xs" style={{ color: "var(--deny)" }}>Needs valid JSON with agent and action.</p>}
        </details>
      </section>

      {d && (
        <section className={`verdict ${d.result}`} aria-live="polite">
          <div className="stack" style={{ gap: "var(--space-1)" }}>
            <span className="big">{LABEL[d.result]}</span>
            {d.reasons.length === 0
              ? <span className="small">Inside this role's scope. A permit receipt is written.</span>
              : <ul className="small" style={{ margin: 0, paddingLeft: "1.1rem" }}>{d.reasons.map((r) => <li key={r}>{explain(r)} <span className="mono xs muted">{r}</span></li>)}</ul>}
          </div>
          {mode === "live" && (
            <div className="stack" style={{ justifyItems: "end" }}>
              <button className="btn" onClick={checkServer}>Check on server</button>
              {server && <span className="xs mono">{server.result === d.result ? "Server agrees" : "Server says"}: {server.result} ({server.engine})</span>}
            </div>
          )}
        </section>
      )}

      <section className="card">
        <h2>Separation of duties</h2>
        <p className="sub">Publishing needs two authorized people. The requester can't count, the signer can't approve, and agents never approve.</p>
        <div className="grid g3">
          <label className="field">Requester
            <select className="input" value={requester} onChange={(e) => setRequester(e.target.value)}>{PEOPLE.map((p) => <option key={p.subject} value={p.subject}>{p.name}</option>)}</select>
          </label>
          <label className="field">Signer
            <select className="input" value={signer} onChange={(e) => setSigner(e.target.value)}>{PEOPLE.map((p) => <option key={p.subject} value={p.subject}>{p.name}</option>)}</select>
          </label>
          <fieldset className="field" style={{ border: 0, padding: 0, margin: 0 }}>
            <legend style={{ fontWeight: 550, fontSize: "var(--text-sm)", marginBottom: "var(--space-1)" }}>Approvers</legend>
            {PEOPLE.map((p) => (
              <label key={p.subject} className="row small" style={{ fontWeight: 400 }}>
                <input type="checkbox" checked={approvers.includes(p.subject)}
                  onChange={(e) => setApprovers((a) => e.target.checked ? [...a, p.subject] : a.filter((x) => x !== p.subject))} />
                {p.name}
              </label>
            ))}
          </fieldset>
        </div>
        <div className={`verdict ${apErr.length ? "deny" : "allow"}`} style={{ marginTop: "var(--space-4)" }} aria-live="polite">
          <div className="stack" style={{ gap: "var(--space-1)" }}>
            <span className="big" style={{ fontSize: "var(--text-lg)" }}>{apErr.length ? "Cannot publish" : "Approval valid"}</span>
            {apErr.length > 0 && <ul className="small" style={{ margin: 0, paddingLeft: "1.1rem" }}>{apErr.map((e) => <li key={e} className="mono xs">{e}</li>)}</ul>}
          </div>
        </div>
      </section>
    </div>
  );
}

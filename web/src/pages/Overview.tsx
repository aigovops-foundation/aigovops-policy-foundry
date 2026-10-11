import { useRef } from "react";
import { Link } from "wouter";
import { useLocation } from "wouter";
import { Check, X, Play, ShieldAlert, ArrowRight, Loader2, ChevronRight, ExternalLink } from "lucide-react";
import { useStore, type GateEvent } from "../lib/store";
import type { Receipt } from "../lib/evidence";
import { explain } from "../lib/gate";
import { openExternal } from "../lib/links";
import { isRole, ROLES, TOUR } from "../lib/roles";

const STEPS: { label: string; find: (r: Receipt) => boolean; detail: (r: Receipt) => string }[] = [
  { label: "Request", find: (r) => r.type === "session_open", detail: () => "Signed requirement" },
  { label: "Tests first", find: (r) => r.type === "test_commitment", detail: () => "Committed before draft" },
  { label: "Draft", find: (r) => r.type === "permit" && r.body.agent === "policy_writer" && r.body.action === "git.push", detail: () => "Writer branch pushed" },
  { label: "Verified", find: (r) => r.type === "review" && r.body.reviewer === "test_verifier", detail: (r) => `${r.body.passed}/${Number(r.body.passed) + Number(r.body.failed)} tests · ${r.body.mutation_killed}/${r.body.mutation_total} mutants` },
  { label: "Audited", find: (r) => r.type === "review" && r.body.reviewer === "compliance_auditor", detail: (r) => `${r.body.blockers} blockers` },
  { label: "Approved", find: (r) => r.type === "policy_approval", detail: (r) => `${(r.body.approvers as unknown[]).length} people, not the requester` },
  { label: "Signed", find: (r) => r.type === "bundle_signed", detail: (r) => `${(r.body.signers as unknown[]).length} signatures` },
];

export default function Overview() {
  const { result, run, mode, newRun, busy, error, visited } = useStore();
  const [loc] = useLocation();
  const startRef = useRef<HTMLElement | null>(null);
  const roleId = loc.startsWith("/start/") ? loc.slice("/start/".length).split("/")[0] : undefined;
  const selectedRole = isRole(roleId) ? ROLES.find((role) => role.id === roleId) : undefined;
  const steps = selectedRole?.steps ?? TOUR;
  if (!result || !run) return <div className="page"><div className="card skeleton" style={{ height: 220 }} /></div>;

  const status = new Map(result.receiptStatus.map((s) => [s.counter, s.sigOk && s.chainOk && s.counterOk]));
  const gates = run.events.filter((e): e is GateEvent => e.kind === "gate");
  const blocked = gates.filter((g) => g.result !== "allow");
  const verifiedCount = result.receiptStatus.filter((s) => s.sigOk && s.chainOk && s.counterOk).length;
  const sigCheck = result.checks.find((c) => c.name === "statement");
  const [killed, total] = run.mutation.split("/");
  const focusStart = () => {
    const section = startRef.current;
    if (!section) return;
    const reducedMotion = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false;
    section.scrollIntoView({ behavior: reducedMotion ? "auto" : "smooth", block: "start" });
    section.focus({ preventScroll: true });
  };

  return (
    <div className="page">
      <section className="card" id="start" tabIndex={-1} aria-labelledby="start-h" ref={startRef}>
        <div className="row" style={{ justifyContent: "space-between", alignItems: "flex-start" }}>
          <div>
            <h2 id="start-h">Start here</h2>
            <p className="sub">Pick the one that sounds like you. Three steps, about two minutes.</p>
          </div>
          {selectedRole && <Link className="small" href="/">Clear</Link>}
        </div>
        <div className="role-chips" aria-label="Choose your role">
          {ROLES.map((role) => (
            <Link
              key={role.id}
              className="chip"
              href={`/start/${role.id}`}
              aria-current={selectedRole?.id === role.id ? "true" : undefined}
            >
              {role.label}
            </Link>
          ))}
        </div>
        {selectedRole && <p className="muted small role-who">{selectedRole.who}</p>}
        <h3 className="tour-heading">{selectedRole ? `${selectedRole.label} path` : "Quick tour"}</h3>
        <ol className="checklist">
          {steps.map((step, index) => {
            const done = !step.external && visited.has(step.to);
            const contents = (
              <>
                <span className={`checklist-number${done ? " is-done" : ""}`}>
                  {done ? <><Check size={16} aria-hidden /><span className="sr-only">done</span></> : index + 1}
                </span>
                <span className="checklist-copy">
                  <span className="checklist-label">{step.label}</span>
                  <span className="checklist-hint">{step.hint}</span>
                </span>
                {step.external
                  ? <><ExternalLink size={16} aria-hidden /><span className="sr-only">(opens GitHub)</span></>
                  : <ChevronRight size={18} aria-hidden />}
              </>
            );
            return (
              <li key={`${step.to}-${step.label}`}>
                {step.external
                  ? <a className="checklist-link" href={step.to} target="_blank" rel="noreferrer" onClick={openExternal}>{contents}</a>
                  : <Link className="checklist-link" href={step.to}>{contents}</Link>}
              </li>
            );
          })}
        </ol>
      </section>

      <section className="card">
        <div className="row" style={{ justifyContent: "space-between", alignItems: "flex-start", gap: "var(--space-4)" }}>
          <div className="stack" style={{ gap: "var(--space-2)", maxWidth: 640 }}>
            <span className="pill accent mono" style={{ justifySelf: "start" }}>{run.request_id}</span>
            <p className="hero-title">AI-assisted changes to plant software</p>
            <p className="muted small" style={{ margin: 0 }}>
              One requirement became a tested, audited, human-approved policy with signed evidence.
              Four agents did the work. None could finish it alone.
            </p>
          </div>
          <div className="row">
            {mode === "live" ? (
              <button className="btn primary" onClick={newRun} disabled={busy}>
                {busy ? <Loader2 size={16} className="spin" /> : <Play size={16} />} {busy ? "Running…" : "Run pipeline"}
              </button>
            ) : (
              <button className="btn primary" onClick={focusStart}>Take the 2-minute tour</button>
            )}
            <Link href="/verify" className="btn">Verify bundle <ArrowRight size={16} /></Link>
          </div>
        </div>
        {error && <p className="notice" role="alert" style={{ marginTop: "var(--space-4)" }}>{error}</p>}
        <div className="journey" style={{ marginTop: "var(--space-6)" }} aria-label="Policy journey">
          {STEPS.map((s) => {
            const r = result.receipts.find(s.find);
            const ok = r ? status.get(r.counter) : undefined;
            return (
              <div className="step" key={s.label}>
                <div className={`dot ${r === undefined ? "pending" : ok ? "" : "broken"}`} aria-hidden>
                  {r === undefined ? null : ok ? <Check size={16} /> : <X size={16} />}
                </div>
                <b>{s.label}</b>
                <span>{r ? `${s.detail(r)} · #${r.counter}` : "Pending"}</span>
              </div>
            );
          })}
        </div>
      </section>

      <section className="grid g5" aria-label="Key figures">
        <div className="card kpi"><span className="label">Receipts verified</span><span className="value">{verifiedCount}/{result.receipts.length}</span><span className="hint">On this device</span></div>
        <div className="card kpi"><span className="label">Acceptance tests</span><span className="value">{run.tests.passed}/{run.tests.passed + run.tests.failed}</span><span className="hint">Written before the draft</span></div>
        <div className="card kpi"><span className="label">Mutants killed</span><span className="value">{killed}/{total}</span><span className="hint">Every rule is tested</span></div>
        <div className="card kpi"><span className="label">Signatures</span><span className="value">{sigCheck?.ok ? "2/2" : "0/2"}</span><span className="hint">Officer + gate</span></div>
        <div className="card kpi"><span className="label">Gate stops</span><span className="value">{blocked.length}</span><span className="hint">Denied or sent to a human</span></div>
      </section>

      <section className="card">
        <div className="row" style={{ justifyContent: "space-between" }}>
          <div><h2>What the gate stopped</h2><p className="sub">Every attempt was blocked at the boundary and receipted.</p></div>
          <Link href="/gate" className="btn">Try to break it</Link>
        </div>
        <div className="list">
          {blocked.map((g) => (
            <div className="li" key={g.receipt}>
              <ShieldAlert size={18} aria-hidden style={{ color: g.result === "deny" ? "var(--deny)" : "var(--esc)", flex: "none" }} />
              <div className="grow">
                <div className="title">{g.note ?? `${g.agent} → ${g.action}`}</div>
                <div className="meta mono">{g.agent} · {g.action}{g.target ? ` · ${g.target}` : ""}</div>
                <div className="meta">{explain(g.result === "escalate" ? "human-only-action" : g.reasons.find((r) => !r.startsWith("no-matching")) ?? g.reasons[0])}</div>
              </div>
              <span className={`pill ${g.result}`}>{g.result === "deny" ? "Denied" : "To a human"}</span>
              <span className="xs muted mono num">#{g.receipt}</span>
            </div>
          ))}
        </div>
      </section>

      <p className="xs muted" style={{ margin: 0 }}>
        Gate engine: {run.gate_engine} · Verifier: {run.verifier_engine} · Evidence is operator-signed demo data, below OVERT AAL-4.
        Not a conformance claim or certification.
      </p>
    </div>
  );
}

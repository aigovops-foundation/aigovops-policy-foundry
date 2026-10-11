import { AlertTriangle, Lock } from "lucide-react";
import { useStore } from "../lib/store";

const PILLARS: Record<string, string> = {
  data_privacy: "Data & privacy", security: "Security", safety: "Safety",
  reliability: "Reliability", accountability: "Accountability", society: "Society",
};
const pct = (bp: number) => `${(bp / 100).toFixed(bp % 100 ? 2 : 0)}%`;

export default function Underwriting() {
  const { bundle } = useStore();
  if (!bundle) return null;
  const p = JSON.parse(bundle.files["underwriting_packet.json"]);
  const m = p.metrics;
  return (
    <div className="page">
      <section className="card">
        <div className="row" style={{ justifyContent: "space-between" }}>
          <div>
            <h2>Underwriting evidence packet</h2>
            <p className="sub" style={{ marginBottom: 0 }}>{p.tenant} · {p.period.start} to {p.period.end} · risk tier <b>{p.risk_tier}</b></p>
          </div>
          <span className="pill warn"><Lock size={14} aria-hidden /> Not released · risk officer only</span>
        </div>
      </section>
      <section className="grid g5">
        <div className="card kpi"><span className="label">Gate coverage</span><span className="value">{pct(m.gate_coverage_bp)}</span><span className="hint">Of boundary-crossing actions</span></div>
        <div className="card kpi"><span className="label">Denial rate</span><span className="value">{pct(m.denial_rate_bp)}</span><span className="hint">Of gate decisions</span></div>
        <div className="card kpi"><span className="label">Human overrides</span><span className="value">{pct(m.hitl_override_rate_bp)}</span><span className="hint">Of reviewed outputs</span></div>
        <div className="card kpi"><span className="label">Attestation gaps</span><span className="value">{m.attestation_gap_count}</span><span className="hint">This period</span></div>
        <div className="card kpi"><span className="label">Incidents</span><span className="value">{p.incidents.length}</span><span className="hint">Reported</span></div>
      </section>
      <div className="grid g2" style={{ alignItems: "start" }}>
        <section className="card">
          <h2>Control coverage by AIUC-1 pillar</h2>
          <p className="sub">Self-assessed coverage, not a certification result.</p>
          <div className="stack">
            {Object.entries(p.pillars as Record<string, number>).map(([k, v]) => (
              <div key={k} className="stack" style={{ gap: "var(--space-1)" }}>
                <div className="row small" style={{ justifyContent: "space-between" }}><span>{PILLARS[k] ?? k}</span><span className="num mono">{pct(v)}</span></div>
                <div className="bar" role="img" aria-label={`${PILLARS[k]} ${pct(v)}`}><i style={{ width: pct(v) }} /></div>
              </div>
            ))}
          </div>
        </section>
        <section className="card">
          <h2>Stated limitations</h2>
          <p className="sub">Every packet must list these. Underwriters see them first.</p>
          <div className="list">
            {p.limitations.map((l: string) => (
              <div className="li" key={l}><AlertTriangle size={16} color="var(--esc)" aria-hidden style={{ flex: "none" }} /><span className="small">{l}</span></div>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}

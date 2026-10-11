import { useStore } from "../lib/store";

const ROLE: Record<string, { title: string; blurb: string }> = {
  manager: { title: "Manager", blurb: "Plans, delegates narrowed scopes, runs the loop. Never writes, approves or signs." },
  policy_writer: { title: "Policy Writer", blurb: "Drafts the policy on a side branch in a Devin session. Can't touch tests or merge." },
  test_verifier: { title: "Test Verifier", blurb: "Writes tests before seeing the draft, then runs tests and mutation checks." },
  compliance_auditor: { title: "Compliance Auditor", blurb: "Maps controls and finds conflicts on a different model. Can block, never approve." },
};

export default function Agents() {
  const { manifest } = useStore();
  if (!manifest) return null;
  const sod = (manifest as any).separation_of_duties as { rule: string }[];
  return (
    <div className="page">
      <div className="grid g2">
        {Object.entries(manifest.agents).map(([id, a]) => (
          <section className="card stack" key={id}>
            <div className="row" style={{ justifyContent: "space-between" }}>
              <h2 style={{ margin: 0 }}>{ROLE[id]?.title ?? id}</h2>
              <span className="pill neutral mono">{String((a as any).runtime)}</span>
            </div>
            <p className="small muted" style={{ margin: 0 }}>{ROLE[id]?.blurb}</p>
            <div>
              <div className="xs muted" style={{ fontWeight: 600, marginBottom: 4 }}>CAN</div>
              <div className="row">{(a.capabilities ?? []).map((c) => <span key={c} className="pill ok mono">{c}</span>)}</div>
            </div>
            <div>
              <div className="xs muted" style={{ fontWeight: 600, marginBottom: 4 }}>NEVER</div>
              <div className="row">{(a.forbidden ?? []).map((c) => <span key={c} className="pill bad mono">{c}</span>)}</div>
            </div>
          </section>
        ))}
      </div>
      <div className="grid g2" style={{ alignItems: "start" }}>
        <section className="card">
          <h2>People with authority</h2>
          <p className="sub">Agents never hold these rights.</p>
          <div className="list">
            {Object.entries(manifest.humans).map(([k, h]) => (
              <div className="li" key={k}>
                <div className="grow"><div className="title">{k.replace(/_/g, " ")}</div><div className="meta mono">{h.idp_group}</div></div>
                {h.may.map((m) => <span key={m} className="pill accent mono">{m}</span>)}
              </div>
            ))}
          </div>
        </section>
        <section className="card">
          <h2>Separation of duties</h2>
          <p className="sub">Enforced by the gate on every approval.</p>
          <div className="list">{sod.map((s) => <div className="li small" key={s.rule}>{s.rule.replace(/_/g, " ")}</div>)}</div>
        </section>
      </div>
    </div>
  );
}

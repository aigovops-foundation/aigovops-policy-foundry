import { useState } from "react";
import { Check, X, RotateCcw, Hammer } from "lucide-react";
import { useStore } from "../lib/store";
import { parseReceipts, type Receipt } from "../lib/evidence";

function summary(r: Receipt): string {
  const b = r.body as Record<string, any>;
  switch (r.type) {
    case "permit": case "denial": case "escalation": return `${b.agent} · ${b.action}${b.target ? ` · ${b.target}` : ""}`;
    case "delegation": return `${b.from} → ${b.to} (${(b.child_scope ?? []).length} capabilities)`;
    case "review": return `${b.reviewer}: ${b.decision}`;
    case "policy_approval": return `${b.approvers.length} approvers · new policy ${String(b.new_policy_sha256).slice(0, 12)}…`;
    case "bundle_signed": return `envelope ${String(b.envelope_sha256).slice(0, 12)}…`;
    case "test_commitment": return `vectors ${String(b.vectors_tree_sha256).slice(0, 12)}…`;
    case "underwriting_packet": return `released: ${b.released}`;
    default: return b.request_id ?? "";
  }
}
const TONE: Record<string, string> = { permit: "allow", denial: "deny", escalation: "escalate" };

export default function Evidence() {
  const { bundle, result, tamperWith, restore, tampered } = useStore();
  const [sel, setSel] = useState(0);
  if (!bundle || !result) return null;
  const receipts = result.receipts;
  const r = receipts[sel];
  const st = result.receiptStatus[sel];
  const cp = JSON.parse(bundle.files["checkpoint.json"]);

  const tamper = () => {
    const rs = parseReceipts(bundle.files["receipts.ndjson"]);
    const t = rs[sel];
    const b = t.body as Record<string, any>;
    if ("agent" in b) b.agent = "attacker"; else if ("decision" in b) b.decision = "approved"; else b.tampered = true;
    tamperWith({ ...bundle, files: { ...bundle.files, "receipts.ndjson": rs.map((x) => JSON.stringify(x)).join("\n") + "\n" } });
  };

  return (
    <div className="page">
      <section className="card">
        <div className="row" style={{ justifyContent: "space-between" }}>
          <div>
            <h2>Receipt log</h2>
            <p className="sub" style={{ marginBottom: 0 }}>Each receipt is signed, points to the one before it, and sits in a witnessed Merkle tree.</p>
          </div>
          <div className="stack xs muted mono" style={{ gap: 0, textAlign: "right" }}>
            <span>root {cp.root.slice(0, 20)}…</span><span>size {cp.size} · witness {cp.witness_keyid}</span>
          </div>
        </div>
        {tampered && (
          <div className="notice row" role="status" style={{ marginTop: "var(--space-4)", justifyContent: "space-between" }}>
            <span>You edited a receipt. Its signature fails, and the next receipt's chain link breaks.</span>
            <button className="btn" onClick={restore}><RotateCcw size={16} /> Restore</button>
          </div>
        )}
      </section>
      <div className="grid g2" style={{ alignItems: "start" }}>
        <section className="card" style={{ padding: "var(--space-2) 0" }}>
          <div className="list" role="group" aria-label="Receipts">
            {receipts.map((x, i) => {
              const s = result.receiptStatus[i];
              const ok = s.sigOk && s.chainOk && s.counterOk;
              return (
                <button key={i} className="li" aria-pressed={i === sel} onClick={() => setSel(i)} style={{ paddingInline: "var(--space-4)" }}>
                  <span className="mono xs muted num" style={{ width: 28 }}>#{x.counter}</span>
                  <div className="grow">
                    <div className={`title ${TONE[x.type] ? "t-" + TONE[x.type] : ""}`}>{x.type.replace("_", " ")}</div>
                    <div className="meta mono">{summary(x)}</div>
                  </div>
                  {ok ? <Check size={16} color="var(--allow)" aria-label="verified" /> : <X size={16} color="var(--deny)" aria-label="failed" />}
                </button>
              );
            })}
          </div>
        </section>
        {r && (
          <section className="card stack" style={{ position: "sticky", top: 0 }}>
            <div className="row" style={{ justifyContent: "space-between" }}>
              <h2>Receipt #{r.counter}</h2>
              <button className="btn" onClick={tamper}><Hammer size={16} /> Tamper with it</button>
            </div>
            <div className="row">
              <span className={`pill ${st.sigOk ? "ok" : "bad"}`}>Signature {st.sigOk ? "valid" : "invalid"}</span>
              <span className={`pill ${st.chainOk ? "ok" : "bad"}`}>Chain {st.chainOk ? "linked" : "broken"}</span>
              <span className={`pill ${st.counterOk ? "ok" : "bad"}`}>Counter {st.counterOk ? "in order" : "gap"}</span>
            </div>
            <p className="xs muted" style={{ margin: 0 }}>
              {new Date(Number(BigInt(r.ts_ns) / 1000000n)).toLocaleString()} · key {r.key_id}
            </p>
            <pre className="json" tabIndex={0} aria-label={`Receipt #${r.counter} JSON`}>{JSON.stringify(r, null, 2)}</pre>
          </section>
        )}
      </div>
    </div>
  );
}

import { useEffect, useRef, useState } from "react";
import { Check, X, Upload, Download } from "lucide-react";
import { useStore } from "../lib/store";
import { sha256Hex, verifyBundle, type Bundle, type VerifyResult } from "../lib/evidence";

const NAMES: Record<string, string> = {
  manifest: "Files match their digests", statement: "Two signatures on the statement", receipts: "Receipt chain intact",
  "underwriting-packet": "Packet matches its signed receipt",
  "non-egress": "No raw content in receipts", checkpoint: "Witnessed log checkpoint", inclusion: "Signing receipt is in the log", structure: "Bundle structure",
};

export default function Verify() {
  const { bundle, mode, apiBase, runId } = useStore();
  const [own, setOwn] = useState<{ name: string; bundle: Bundle | null; res: VerifyResult } | null>(null);
  const [over, setOver] = useState(false);
  const [server, setServer] = useState<{ key: string; text: string } | null>(null);
  const generation = useRef(0);
  const reading = useRef(0);
  const input = useRef<HTMLInputElement>(null);
  const current = bundle ? verifyBundle(bundle) : null;
  const shown = own?.res ?? current;
  const active = own ? own.bundle : bundle;
  const label = own?.name ?? "Current bundle";
  const bytes = active ? JSON.stringify(active) : "";
  const digest = bytes ? sha256Hex(new TextEncoder().encode(bytes)) : "";
  const selectionKey = `${apiBase}:${digest}`;
  useEffect(() => { generation.current++; setServer(null); }, [active, apiBase]);

  const readFile = async (f: File) => {
    const selected = ++reading.current;
    generation.current++; setServer(null);
    setOwn({ name: f.name, bundle: null, res: { ok: false, receipts: [], receiptStatus: [], checks: [{ name: "structure", ok: false, detail: "Reading selected file" }] } });
    try {
      const b = JSON.parse(await f.text()) as Bundle;
      if (selected === reading.current) setOwn({ name: f.name, bundle: b, res: verifyBundle(b) });
    } catch (e) {
      if (selected === reading.current) setOwn({ name: f.name, bundle: null, res: { ok: false, receipts: [], receiptStatus: [], checks: [{ name: "structure", ok: false, detail: "Not a bundle.json file" }] } });
    }
  };
  const download = () => {
    if (!active) return;
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([bytes], { type: "application/json" }));
    a.download = own?.name ?? "foundry-bundle.json"; a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  };
  const serverCheck = async () => {
    if (!active) return;
    const request = ++generation.current;
    setServer(null);
    try {
      const r = await fetch(`${apiBase}/api/verify`, { method: "POST", redirect: "error", headers: { "Content-Type": "application/json" }, body: bytes });
      const j = await r.json();
      if (request === generation.current) setServer({ key: selectionKey, text: `${label} (${digest.slice(0, 12)}): ${r.ok ? (j.ok ? "Server verifier: OK" : "Server verifier: FAILED") : `Server error ${r.status}`}` });
    } catch {
      if (request === generation.current) setServer({ key: selectionKey, text: `${label} (${digest.slice(0, 12)}): Server verification unavailable` });
    }
  };

  return (
    <div className="page">
      <section className="card">
        <h2>Verify a bundle</h2>
        <p className="sub">Runs entirely on this device. Nothing is uploaded. The same checks ship as a Python script inside every bundle.</p>
        <div className={`drop ${over ? "over" : ""}`}
          onDragOver={(e) => { e.preventDefault(); setOver(true); }} onDragLeave={() => setOver(false)}
          onDrop={(e) => { e.preventDefault(); setOver(false); const f = e.dataTransfer.files[0]; if (f) readFile(f); }}>
          <Upload size={20} aria-hidden /><br />
          Drop a <span className="mono">bundle.json</span> here, or{" "}
          <button className="btn" style={{ marginTop: "var(--space-2)" }} onClick={() => input.current?.click()}>choose a file</button>
          <input ref={input} type="file" accept="application/json,.json" hidden onChange={(e) => e.target.files?.[0] && readFile(e.target.files[0])} />
        </div>
        <div className="row" style={{ marginTop: "var(--space-4)" }}>
          {own && <button className="btn" onClick={() => { reading.current++; generation.current++; setServer(null); setOwn(null); }}>Back to current bundle</button>}
          <button className="btn" disabled={!active} onClick={download}><Download size={16} /> Download bundle.json</button>
          {mode === "live" && runId && !own && <a className="btn" href={`${apiBase}/api/runs/${runId}/bundle.zip`}><Download size={16} /> Bundle .zip (with Python verifier)</a>}
          {mode === "live" && <button className="btn" disabled={!active} onClick={serverCheck}>Also verify on server</button>}
          {server?.key === selectionKey && <span className="small mono" role="status">{server.text}</span>}
        </div>
      </section>

      {shown && (
        <section className="card">
          <div className="row" style={{ justifyContent: "space-between", marginBottom: "var(--space-3)" }}>
            <h2>{own ? own.name : "Current bundle"}</h2>
            <span className={`pill ${shown.ok ? "ok" : "bad"}`}>{shown.ok ? "All checks passed" : "Verification failed"}</span>
          </div>
          <div className="list">
            {shown.checks.map((c) => (
              <div className="li" key={c.name}>
                {c.ok ? <Check size={18} color="var(--allow)" aria-hidden /> : <X size={18} color="var(--deny)" aria-hidden />}
                <div className="grow"><div className="title">{NAMES[c.name] ?? c.name}</div><div className="meta">{c.detail}</div></div>
                <span className="sr-only">{c.ok ? "passed" : "failed"}</span>
              </div>
            ))}
          </div>
          <p className="xs muted" style={{ marginBottom: 0 }}>
            Passing proves who signed which bytes and that the log was not edited. It does not prove the policy is correct, complete, or legally compliant.
          </p>
        </section>
      )}
    </div>
  );
}

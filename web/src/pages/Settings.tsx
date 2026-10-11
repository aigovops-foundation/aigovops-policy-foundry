import { useState } from "react";
import { useStore } from "../lib/store";
import { openExternal, REPO } from "../lib/links";

export default function Settings() {
  const { mode, apiBase, setApiBase, error, theme, toggleTheme, token, setToken } = useStore();
  const [url, setUrl] = useState(apiBase);
  const [msg, setMsg] = useState<string | null>(null);
  return (
    <div className="page">
      <section className="card stack">
        <div><h2>API connection</h2><p className="sub" style={{ marginBottom: 0 }}>Leave empty for the offline demo. Point at a Policy Foundry API to run the live pipeline.</p></div>
        <form className="row" onSubmit={async (e) => { e.preventDefault(); const ok = await setApiBase(url); setMsg(ok ? (url ? "Connected." : "Using offline demo.") : null); }}>
          <input className="input mono" style={{ flex: "1 1 280px" }} value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://foundry.example.com" aria-label="API base URL" />
          <button className="btn primary" type="submit">Connect</button>
          {mode === "live" && <button className="btn" type="button" onClick={async () => { setUrl(""); await setApiBase(""); setMsg("Using offline demo."); }}>Use offline demo</button>}
        </form>
        <p className="small" role="status" style={{ margin: 0 }}>
          Mode: <b>{mode === "live" ? `Live API ${apiBase || "(same origin)"}` : "Offline demo"}</b>
          {msg && <> · {msg}</>}{error && <span style={{ color: "var(--deny)" }}> · {error}</span>}
        </p>
        <label className="field" style={{ maxWidth: 520 }}>Access token (if the API requires one)
          <input className="input mono" type="password" autoComplete="off" value={token} onChange={(e) => setToken(e.target.value)} placeholder="Kept in memory only" />
        </label>
      </section>
      <section className="card row" style={{ justifyContent: "space-between" }}>
        <div><h2>Appearance</h2><p className="sub" style={{ margin: 0 }}>Follows your system until you change it.</p></div>
        <button className="btn" onClick={toggleTheme}>Use {theme === "dark" ? "light" : "dark"} mode</button>
      </section>
      <section className="card stack small">
        <h2>About</h2>
        <p style={{ margin: 0 }}>AiGovOps Policy Foundry v0.1.0 · Apache-2.0 code, CC BY 4.0 docs · an AiGovOps Foundation incubation project.</p>
        <p className="muted" style={{ margin: 0 }}>
          Demo evidence is operator-signed and below OVERT AAL-4. This is not an OVERT conformance claim, an AIUC-1 certification,
          or legal advice. Devin is a trademark of Cognition AI, Inc.; this project is not affiliated with or endorsed by Cognition.
        </p>
        <div className="row">
          <a className="btn" href={REPO} target="_blank" rel="noreferrer" onClick={openExternal}>Source code</a>
          <a className="btn" href={`${REPO}/blob/main/docs/BLUEPRINT.md`} target="_blank" rel="noreferrer" onClick={openExternal}>Blueprint</a>
          <a className="btn" href={`${REPO}/blob/main/DEVIN.md`} target="_blank" rel="noreferrer" onClick={openExternal}>Build with Devin</a>
        </div>
      </section>
    </div>
  );
}

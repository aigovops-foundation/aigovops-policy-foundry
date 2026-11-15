import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { authorizationHeaders, changeDestination, normalizeDestination, type Connection } from "./connection";
import { verifyBundle, type Bundle, type VerifyResult } from "./evidence";
import type { Manifest } from "./gate";

export type GateEvent = { kind: "gate"; agent: string; action: string; target: string | null; result: "allow" | "deny" | "escalate"; reasons: string[]; receipt: number; note?: string | null };
export type RunSummary = {
  request_id: string; receipts: number; root: string; verdict: string; coverage_bp: number; mutation: string;
  tests: { passed: number; failed: number; errors: number }; gate_engine: string; verifier_engine: string;
  events: (GateEvent | { kind: string; [k: string]: unknown })[];
};
export type Mode = "demo" | "live";

type Store = {
  mode: Mode; apiBase: string; setApiBase: (u: string) => Promise<boolean>;
  token: string; setToken: (t: string) => void;
  allowInsecure: boolean; setAllowInsecure: (allow: boolean) => void;
  manifest: Manifest | null; run: RunSummary | null; bundle: Bundle | null; result: VerifyResult | null;
  runId: string | null; busy: boolean; error: string | null;
  visited: Set<string>; recordVisit: (location: string) => void;
  loadBundle: (b: Bundle, run?: RunSummary | null) => void;
  tamperWith: (b: Bundle) => void; restore: () => void; tampered: boolean;
  newRun: () => Promise<void>;
  theme: "light" | "dark"; toggleTheme: () => void;
};

const Ctx = createContext<Store | null>(null);
export const useStore = () => {
  const s = useContext(Ctx);
  if (!s) throw new Error("store missing");
  return s;
};

const ENV_API = (import.meta.env.VITE_API_BASE as string | undefined)?.replace(/\/$/, "") ?? "";

async function getJSON<T>(url: string, init?: RequestInit): Promise<T> {
  const r = await fetch(url, { ...init, redirect: "error", headers: { "Content-Type": "application/json", ...(init?.headers || {}) } });
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
  return r.json() as Promise<T>;
}

async function probe(base: string): Promise<boolean> {
  try {
    const ctl = new AbortController();
    const t = setTimeout(() => ctl.abort(), 2500);
    const r = await fetch(`${base}/api/meta`, { signal: ctl.signal });
    clearTimeout(t);
    if (!r.ok) return false;
    const j = await r.json();
    return j?.name === "AiGovOps Policy Foundry";
  } catch { return false; }
}

export function StoreProvider({ children }: { children: ReactNode }) {
  const [mode, setMode] = useState<Mode>("demo");
  const [connection, setConnection] = useState<Connection>({ base: "", token: "", allowInsecure: false });
  const { base: apiBase, token, allowInsecure } = connection;
  const attempt = useRef(0);
  const setToken = useCallback((t: string) => {
    try { authorizationHeaders({ ...connection, token: t }); setConnection({ ...connection, token: t }); setError(null); }
    catch (e) { setError(String(e instanceof Error ? e.message : e)); }
  }, [connection]);
  const setAllowInsecure = useCallback((allow: boolean) => setConnection(c => ({ ...c, token: "", allowInsecure: allow })), []);
  const [manifest, setManifest] = useState<Manifest | null>(null);
  const [run, setRun] = useState<RunSummary | null>(null);
  const [bundle, setBundle] = useState<Bundle | null>(null);
  const [pristine, setPristine] = useState<Bundle | null>(null);
  const [result, setResult] = useState<VerifyResult | null>(null);
  const [runId, setRunId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [visited, setVisited] = useState<Set<string>>(() => new Set());
  const [theme, setTheme] = useState<"light" | "dark">(() =>
    typeof window !== "undefined" && window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light");

  useEffect(() => { document.documentElement.dataset.theme = theme; }, [theme]);
  const recordVisit = useCallback((location: string) => {
    setVisited((current) => {
      if (current.has(location)) return current;
      const next = new Set(current);
      next.add(location);
      return next;
    });
  }, []);

  const loadBundle = useCallback((b: Bundle, r?: RunSummary | null) => {
    const checked = verifyBundle(b);
    if (checked.checks.some(c => c.name === "structure" && !c.ok)) throw new Error("Invalid bundle structure; previous bundle retained");
    setBundle(b);
    setPristine(null);
    setResult(checked);
    if (r !== undefined) setRun(r);
  }, []);
  // Tamper demo: keep the untouched bundle so the user can restore it from any screen.
  const tamperWith = useCallback((b: Bundle) => {
    setPristine((p) => p ?? bundle);
    setBundle(b);
    setResult(verifyBundle(b));
  }, [bundle]);
  const restore = useCallback(() => {
    if (!pristine) return;
    setBundle(pristine); setResult(verifyBundle(pristine)); setPristine(null);
  }, [pristine]);

  useEffect(() => {
    (async () => {
      const generation = attempt.current;
      const [m, r, b] = await Promise.all([
        getJSON<Manifest>("./demo/agents.json"), getJSON<RunSummary>("./demo/run.json"), getJSON<Bundle>("./demo/bundle.json"),
      ]);
      setManifest(m);
      loadBundle(b, r);
      for (const cand of [ENV_API, ""]) {
        if (generation !== attempt.current) break;
        if (cand === "" && ENV_API) continue;
        if (await probe(cand) && generation === attempt.current) { setConnection(c => changeDestination(c, cand)); setMode("live"); break; }
      }
    })().catch((e) => setError(String(e)));
  }, [loadBundle]);

  const setApiBase = useCallback(async (u: string) => {
    let base: string;
    try { base = normalizeDestination(u); }
    catch (e) { setError(String(e instanceof Error ? e.message : e)); return false; }
    const generation = ++attempt.current;
    if (!base) { setConnection(c => changeDestination(c, "")); setRunId(null); setMode("demo"); setError(null); return true; }
    const ok = await probe(base);
    if (generation !== attempt.current) return false;
    if (ok) { setConnection(c => changeDestination(c, base)); setRunId(null); setMode("live"); setError(null); } else setError(`No Policy Foundry API at ${base}`);
    return ok;
  }, []);

  const newRun = useCallback(async () => {
    if (mode !== "live") return;
    setBusy(true); setError(null);
    try {
      const auth = authorizationHeaders(connection);
      const created = await getJSON<RunSummary & { id: string }>(`${apiBase}/api/runs`, { method: "POST", headers: auth });
      const b = await getJSON<Bundle>(`${apiBase}/api/runs/${created.id}/bundle.json`);
      const full = created.mutation ? created : await getJSON<RunSummary>(`${apiBase}/api/runs/${created.id}`);
      setRunId(created.id);
      loadBundle(b, full);
    } catch (e) {
      const m = e instanceof Error ? e.message : String(e);
      setError(m.startsWith("401") ? "This API needs an access token. Add it in Settings." : `Run failed: ${m}`);
    }
    finally { setBusy(false); }
  }, [mode, apiBase, connection, loadBundle]);

  const value = useMemo<Store>(() => ({
    mode, apiBase, setApiBase, token, setToken, allowInsecure, setAllowInsecure, manifest, run, bundle, result, runId, busy, error, visited, recordVisit, loadBundle, newRun,
    tamperWith, restore, tampered: pristine !== null,
    theme, toggleTheme: () => setTheme((t) => (t === "dark" ? "light" : "dark")),
  }), [mode, apiBase, setApiBase, token, setToken, allowInsecure, setAllowInsecure, manifest, run, bundle, result, runId, busy, error, visited, recordVisit, loadBundle, newRun, tamperWith, restore, pristine, theme]);

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

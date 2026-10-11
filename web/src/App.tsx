import { useEffect } from "react";
import { Link, Route, Router, Switch, useLocation } from "wouter";
import { useHashLocation } from "wouter/use-hash-location";
import { Activity, BadgeCheck, FileText, Gauge, Menu, Moon, Settings as Cog, ShieldHalf, Sun, Users, Receipt, FileCheck2 } from "lucide-react";
import { useStore } from "./lib/store";
import Overview from "./pages/Overview";
import Policy from "./pages/Policy";
import Gate from "./pages/Gate";
import Evidence from "./pages/Evidence";
import Verify from "./pages/Verify";
import Underwriting from "./pages/Underwriting";
import Agents from "./pages/Agents";
import Settings from "./pages/Settings";
import More from "./pages/More";

export function Logo({ size = 28 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" fill="none" aria-label="Policy Foundry" role="img">
      <path d="M7 3.5h13a2 2 0 0 1 2 2V15M7 3.5a2 2 0 0 0-2 2v21l3-2 3 2 3-2 2.2 1.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M9.5 9.5h8M9.5 14h5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      <circle cx="23" cy="23" r="6.5" fill="var(--accent)" />
      <path d="m20.2 23.1 2 2 3.8-4" stroke="var(--on-accent)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

const NAV = [
  { to: "/", label: "Overview", icon: Gauge },
  { to: "/policy", label: "Policy", icon: FileText },
  { to: "/gate", label: "Gate", icon: ShieldHalf },
  { to: "/evidence", label: "Evidence", icon: Receipt },
  { to: "/verify", label: "Verify", icon: FileCheck2 },
  { to: "/underwriting", label: "Underwriting", icon: Activity },
  { to: "/agents", label: "Agents", icon: Users },
  { to: "/settings", label: "Settings", icon: Cog },
];
const TABS = [NAV[0], NAV[2], NAV[3], NAV[4], { to: "/more", label: "More", icon: Menu }];
const TITLES: Record<string, string> = Object.fromEntries([...NAV, TABS[4]].map((n) => [n.to, n.label]));
TITLES["/start"] = "Overview";

function NavLink({ to, label, Icon, compact }: { to: string; label: string; Icon: typeof Gauge; compact?: boolean }) {
  const [loc] = useLocation();
  const active = to === "/"
    ? loc === "/" || loc.startsWith("/start/")
    : loc.startsWith(to) || (to === "/more" && ["/policy", "/underwriting", "/agents", "/settings"].some((p) => loc.startsWith(p)));
  return (
    <Link href={to} aria-current={active ? "page" : undefined}>
      <Icon size={compact ? 20 : 18} aria-hidden /> <span>{label}</span>
    </Link>
  );
}

function Shell() {
  const { mode, theme, toggleTheme, result, tampered, restore, recordVisit } = useStore();
  const [loc] = useLocation();
  useEffect(() => { recordVisit(loc); }, [loc, recordVisit]);
  const title = TITLES[loc] ?? TITLES["/" + loc.split("/")[1]] ?? "Policy Foundry";
  return (
    <div className="shell">
      <aside className="sidebar">
        <Link href="/" className="brand"><Logo /><div><b>Policy Foundry</b><span>AiGovOps Foundation</span></div></Link>
        <nav className="nav stack" style={{ gap: "var(--space-1)" }} aria-label="Main">
          {NAV.map((n) => <NavLink key={n.to} to={n.to} label={n.label} Icon={n.icon} />)}
        </nav>
        <div className="sidebar-foot">
          Apache-2.0 · v0.1.0<br />Demo evidence. Not a certification.
        </div>
      </aside>
      <div className="main">
        <header className="topbar">
          <h1>{title}</h1>
          <span className="spacer" />
          {result && (
            <span className={`pill ${result.ok ? "ok" : "bad"}`} title="Bundle verification on this device">
              <BadgeCheck size={14} aria-hidden /> {result.ok ? "Verified" : "Not verified"}
            </span>
          )}
          <span className={`pill ${mode === "live" ? "accent" : "neutral"}`}>{mode === "live" ? "Live API" : "Offline demo"}</span>
          <button className="btn ghost icon-btn" onClick={toggleTheme} aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}>
            {theme === "dark" ? <Sun size={18} /> : <Moon size={18} />}
          </button>
        </header>
        {tampered && !loc.startsWith("/evidence") && (
          <div className="notice row" role="status" style={{ borderRadius: 0, borderInline: 0, justifyContent: "space-between" }}>
            <span>Demo: a receipt was tampered with, so verification fails.</span>
            <button className="btn" onClick={restore}>Restore original</button>
          </div>
        )}
        <main className="content" id="main" tabIndex={0}>
          <Switch>
            <Route path="/" component={Overview} />
            <Route path="/start/:role" component={Overview} />
            <Route path="/policy" component={Policy} />
            <Route path="/gate" component={Gate} />
            <Route path="/evidence" component={Evidence} />
            <Route path="/verify" component={Verify} />
            <Route path="/underwriting" component={Underwriting} />
            <Route path="/agents" component={Agents} />
            <Route path="/settings" component={Settings} />
            <Route path="/more" component={More} />
            <Route><div className="page"><div className="card"><h2>Not found</h2><Link href="/">Back to overview</Link></div></div></Route>
          </Switch>
        </main>
      </div>
      <nav className="tabbar" aria-label="Main">
        {TABS.map((n) => <NavLink key={n.to} to={n.to} label={n.label} Icon={n.icon} compact />)}
      </nav>
    </div>
  );
}

export default function App() {
  return <Router hook={useHashLocation}><Shell /></Router>;
}

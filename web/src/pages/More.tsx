import { Link } from "wouter";
import { Activity, Users, Settings as Cog, ChevronRight } from "lucide-react";

const ITEMS = [
  { to: "/underwriting", label: "Underwriting", hint: "Evidence packet for insurers", Icon: Activity },
  { to: "/agents", label: "Agents", hint: "Roles, rights and limits", Icon: Users },
  { to: "/settings", label: "Settings", hint: "API connection, appearance, about", Icon: Cog },
];

export default function More() {
  return (
    <div className="page">
      <section className="card" style={{ padding: "var(--space-2) var(--space-4)" }}>
        <div className="list">
          {ITEMS.map(({ to, label, hint, Icon }) => (
            <Link key={to} href={to} className="li" style={{ textDecoration: "none", color: "inherit" }}>
              <Icon size={20} aria-hidden />
              <div className="grow"><div className="title">{label}</div><div className="meta">{hint}</div></div>
              <ChevronRight size={18} aria-hidden className="muted" />
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}

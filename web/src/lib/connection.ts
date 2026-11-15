export type Connection = { base: string; token: string; allowInsecure: boolean };

export function normalizeDestination(value: string): string {
  if (!value.trim()) return "";
  const u = new URL(value.trim());
  if (!["https:", "http:"].includes(u.protocol) || u.username || u.password || u.search || u.hash) throw new Error("Use an HTTP(S) API URL without credentials, query or fragment");
  return u.href.replace(/\/+$/, "");
}

export function changeDestination(current: Connection, value: string): Connection {
  const base = normalizeDestination(value);
  return base && base === current.base ? current : { base, token: "", allowInsecure: false };
}

export function insecureDestination(base: string): boolean {
  const u = new URL(base || (typeof window !== "undefined" ? window.location.origin : "http://localhost"));
  return u.protocol === "http:" && !["localhost", "127.0.0.1", "[::1]"].includes(u.hostname);
}

export function authorizationHeaders(c: Connection): Record<string, string> {
  if (c.token && insecureDestination(c.base) && !c.allowInsecure) throw new Error("Explicitly allow unencrypted remote token transmission before entering a token");
  return c.token ? { Authorization: `Bearer ${c.token}` } : {};
}

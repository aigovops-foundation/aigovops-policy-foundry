import { describe, expect, it, vi } from "vitest";
import { readFileSync } from "node:fs";
import { validatePacketDisplay, verifyBundle, type Bundle } from "../src/lib/evidence";
import { decide, isGateInput } from "../src/lib/gate";
import { authorizationHeaders, changeDestination, normalizeDestination } from "../src/lib/connection";

const demo: Bundle = JSON.parse(readFileSync(new URL("../public/demo/bundle.json", import.meta.url), "utf8"));

describe("runtime evidence boundaries", () => {
  it.each([{ risk_tier: {} }, { pillars: { unexpected: {} } }, { pillars: { unexpected: "bad" } }, { pillars: { unexpected: 10001 } }])("validates packet display fields %j", patch => {
    const packet = JSON.parse(demo.files["underwriting_packet.json"]);
    expect(() => validatePacketDisplay({ ...packet, ...patch })).toThrow();
  });
  it.each([null, [], {}, 7, "bad"])("rejects outer shape %j without throwing", value => {
    expect(verifyBundle(value as Bundle).ok).toBe(false);
  });
  for (const file of ["manifest.json", "statement.dsse.json", "checkpoint.json", "inclusion_bundle_signed.json", "underwriting_packet.json"]) {
    it.each([null, [], {}, 7, "bad"])(`rejects ${file} shape %j`, value => {
      expect(verifyBundle({ ...demo, files: { ...demo.files, [file]: JSON.stringify(value) } }).ok).toBe(false);
    });
  }
  it.each(["mutate", "remove", "swap", "no-commitment", "duplicate-commitment"])("rejects packet %s", change => {
    const b: Bundle = structuredClone(demo);
    if (change === "remove") delete b.files["underwriting_packet.json"];
    else if (change === "mutate" || change === "swap") {
      const p = JSON.parse(b.files["underwriting_packet.json"]);
      p.metrics.gate_coverage_bp = 1;
      if (change === "swap") p.tenant = "another-demo-tenant";
      b.files["underwriting_packet.json"] = JSON.stringify(p);
    } else {
      const rows = b.files["receipts.ndjson"].trim().split("\n").map(s => JSON.parse(s));
      const p = rows.find(r => r.type === "underwriting_packet");
      if (change === "no-commitment") p.type = "review"; else rows.push(p);
      b.files["receipts.ndjson"] = rows.map(r => JSON.stringify(r)).join("\n");
    }
    const r = verifyBundle(b);
    expect(r.ok).toBe(false);
    expect(r.checks.find(c => c.name === "underwriting-packet")?.ok).toBe(false);
  });
  it.each([null, {}, [], [{ keyid: [], sig: {} }]])("rejects malformed signature fields %j", signatures => {
    const env = JSON.parse(demo.files["statement.dsse.json"]); env.signatures = signatures;
    expect(verifyBundle({ ...demo, files: { ...demo.files, "statement.dsse.json": JSON.stringify(env) } }).ok).toBe(false);
  });
  it("rejects an empty receipt log", () => expect(verifyBundle({ ...demo, files: { ...demo.files, "receipts.ndjson": "" } }).ok).toBe(false));
  it.each(["ts_ns", "approvers", "request_id"])("rejects malformed receipt display field %s", field => {
    const b = structuredClone(demo);
    const rows = b.files["receipts.ndjson"].trim().split("\n").map(s => JSON.parse(s));
    if (field === "ts_ns") rows[0].ts_ns = "not-nanoseconds";
    else rows[0].body[field] = null;
    b.files["receipts.ndjson"] = rows.map(r => JSON.stringify(r)).join("\n");
    expect(verifyBundle(b).checks.find(c => c.name === "structure")?.ok).toBe(false);
  });
});

describe("raw gate editor schema", () => {
  it.each([null, [], {}, { agent: "manager", action: "devin.session.create", delegation: { child_scope: {} } },
    ...[null, [], "bad", 7].map(delegation => ({ agent: "manager", action: "devin.session.create", delegation }))])("rejects %j locally", input => expect(isGateInput(input)).toBe(false));
  it("accepts an empty delegation for a recoverable deny", () => expect(isGateInput({ agent: "manager", action: "devin.session.create", delegation: {} })).toBe(true));
  it("accepts normal actions", () => expect(isGateInput({ agent: "policy_writer", action: "opa.test.local" })).toBe(true));
  it("does not introduce an allow for a nonempty delegation missing its target", () => {
    const m = JSON.parse(readFileSync(new URL("../public/demo/agents.json", import.meta.url), "utf8"));
    const i = { agent: "manager", action: "devin.session.create", delegation: { parent_scope: [] } };
    expect(isGateInput(i)).toBe(false);
    expect(decide(i, m).result).toBe("deny");
  });
});

describe("destination-scoped credentials", () => {
  it("never forwards A's token to B or the offline reset", async () => {
    const fakeFetch = vi.fn(async (_url: string, _init: RequestInit) => ({ ok: true }));
    const a = { base: "https://a.example", token: "synthetic-token-A", allowInsecure: false };
    await fakeFetch(a.base, { headers: authorizationHeaders(a) });
    const b = changeDestination(a, "https://b.example/");
    await fakeFetch(b.base, { headers: authorizationHeaders(b) });
    expect(fakeFetch.mock.calls[0][1].headers).toEqual({ Authorization: "Bearer synthetic-token-A" });
    expect(fakeFetch.mock.calls[1][1].headers).toEqual({});
    expect(changeDestination(a, "").token).toBe("");
    expect(changeDestination(a, "https://a.example/other").token).toBe("");
    expect(changeDestination(a, "https://A.EXAMPLE:443/").token).toBe(a.token);
  });
  it("requires explicit remote HTTP consent and resets it on a destination change", () => {
    const c = { base: "http://remote.example", token: "synthetic", allowInsecure: false };
    expect(() => authorizationHeaders(c)).toThrow("Explicitly");
    expect(authorizationHeaders({ ...c, allowInsecure: true })).toHaveProperty("Authorization");
    expect(changeDestination({ ...c, allowInsecure: true }, "http://other.example").allowInsecure).toBe(false);
    expect(authorizationHeaders({ ...c, base: "http://127.0.0.1:8000" })).toHaveProperty("Authorization");
  });
  it.each(["ftp://example.com", "https://user:pass@example.com", "https://example.com/?query", "https://example.com/#fragment"])("rejects unsafe destination %s", u => expect(() => normalizeDestination(u)).toThrow());
});

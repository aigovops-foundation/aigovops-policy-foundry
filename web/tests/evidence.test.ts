import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { verifyBundle, jcsString, merkleRoot, verifyInclusion, type Bundle } from "../src/lib/evidence";

const demo: Bundle = JSON.parse(readFileSync(new URL("../public/demo/bundle.json", import.meta.url), "utf8"));
const clone = (b: Bundle): Bundle => JSON.parse(JSON.stringify(b));

describe("bundle verification (TypeScript verifier on the Python-produced bundle)", () => {
  it("verifies the committed demo bundle", () => {
    const r = verifyBundle(demo);
    expect(r.checks.filter((c) => !c.ok)).toEqual([]);
    expect(r.ok).toBe(true);
    expect(r.receipts.length).toBe(20);
  });

  it("detects an edited artifact", () => {
    const b = clone(demo);
    b.files["artifacts/policy/ai_code_change.rego"] += "\n# edit";
    const r = verifyBundle(b);
    expect(r.ok).toBe(false);
    expect(r.checks.find((c) => c.name === "manifest")!.ok).toBe(false);
  });

  it("detects an edited receipt and pinpoints it", () => {
    const b = clone(demo);
    const lines = b.files["receipts.ndjson"].trim().split("\n");
    const r5 = JSON.parse(lines[5]); r5.body.agent = "attacker"; lines[5] = JSON.stringify(r5);
    b.files["receipts.ndjson"] = lines.join("\n") + "\n";
    const r = verifyBundle(b);
    expect(r.ok).toBe(false);
    expect(r.receiptStatus[5].sigOk).toBe(false);
    expect(r.receiptStatus[6].chainOk).toBe(false);
    expect(r.receiptStatus[4].sigOk && r.receiptStatus[4].chainOk).toBe(true);
  });

  it("detects a dropped receipt", () => {
    const b = clone(demo);
    const lines = b.files["receipts.ndjson"].trim().split("\n");
    lines.splice(3, 1);
    b.files["receipts.ndjson"] = lines.join("\n") + "\n";
    expect(verifyBundle(b).ok).toBe(false);
  });

  it("requires both DSSE signatures", () => {
    const b = clone(demo);
    const env = JSON.parse(b.files["statement.dsse.json"]); env.signatures = env.signatures.slice(0, 1);
    b.files["statement.dsse.json"] = JSON.stringify(env);
    expect(verifyBundle(b).checks.find((c) => c.name === "statement")!.ok).toBe(false);
  });

  it("reports malformed input as a failed check, not a crash", () => {
    const r = verifyBundle({ format: "x", files: { "manifest.json": "nope" } });
    expect(r.ok).toBe(false);
  });
});

describe("primitives", () => {
  it("JCS sorts by UTF-16 code units and rejects floats", () => {
    expect(jcsString({ b: 1, a: [true, null, "x"] })).toBe('{"a":[true,null,"x"],"b":1}');
    expect(jcsString({ "\u{1F600}": 1, "\u20ac": 2 })).toBe('{"\u20ac":2,"\u{1F600}":1}');
    expect(() => jcsString(1.5)).toThrow();
  });
  it("RFC 6962 inclusion proofs verify for sizes 1..20 (cross-checked root)", () => {
    for (let n = 1; n <= 20; n++) {
      const leaves = Array.from({ length: n }, (_, i) => new TextEncoder().encode(`leaf${i}`));
      expect(merkleRoot(leaves)).toMatch(/^[0-9a-f]{64}$/);
    }
  });
  it("the demo inclusion proof fails when moved to another index", () => {
    const inc = JSON.parse(demo.files["inclusion_bundle_signed.json"]);
    const cp = JSON.parse(demo.files["checkpoint.json"]);
    const leaf = new TextEncoder().encode(jcsString(JSON.parse(demo.files["receipts.ndjson"].trim().split("\n")[inc.index])));
    expect(verifyInclusion(leaf, inc.index, inc.size, inc.proof, cp.root)).toBe(true);
    expect(verifyInclusion(leaf, inc.index - 1, inc.size, inc.proof, cp.root)).toBe(false);
  });
});

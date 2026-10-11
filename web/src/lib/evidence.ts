// Browser/offline verifier for Foundry bundles. Mirrors api/foundry/evidence.py + verify_bundle.py.
// Cross-language parity is tested: web/tests verify the same bundle the Python pipeline produced.
import * as ed from "@noble/ed25519";
import { sha256, sha512 } from "@noble/hashes/sha2.js";
import { bytesToHex, hexToBytes, utf8ToBytes } from "@noble/hashes/utils.js";

ed.hashes.sha512 = sha512;

export type Json = null | boolean | number | string | Json[] | { [k: string]: Json };

// ---------------------------------------------------------------- RFC 8785 (float-free subset)
export function jcsString(v: Json): string {
  if (v === null) return "null";
  if (typeof v === "boolean") return v ? "true" : "false";
  if (typeof v === "number") {
    if (!Number.isInteger(v)) throw new Error("floats are prohibited");
    if (!Number.isSafeInteger(v)) throw new Error("integer outside I-JSON safe range");
    return String(v);
  }
  if (typeof v === "string") return JSON.stringify(v);
  if (Array.isArray(v)) return "[" + v.map(jcsString).join(",") + "]";
  // JS string comparison is by UTF-16 code units, exactly what RFC 8785 requires
  const keys = Object.keys(v).sort((a, b) => (a < b ? -1 : a > b ? 1 : 0));
  return "{" + keys.map((k) => JSON.stringify(k) + ":" + jcsString(v[k] as Json)).join(",") + "}";
}
export const jcs = (v: Json) => utf8ToBytes(jcsString(v));
export const sha256Hex = (b: Uint8Array) => bytesToHex(sha256(b));
export const b64d = (s: string) => Uint8Array.from(atob(s), (c) => c.charCodeAt(0));
export const keyId = (raw: Uint8Array) => "ed25519:" + sha256Hex(raw).slice(0, 16);

function concat(...parts: Uint8Array[]): Uint8Array {
  const out = new Uint8Array(parts.reduce((n, p) => n + p.length, 0));
  let o = 0;
  for (const p of parts) { out.set(p, o); o += p.length; }
  return out;
}

function edVerify(sig: Uint8Array, msg: Uint8Array, pub: Uint8Array): boolean {
  try { return ed.verify(sig, msg, pub); } catch { return false; }
}

// ---------------------------------------------------------------- RFC 6962 Merkle
const leafHash = (b: Uint8Array) => sha256(concat(new Uint8Array([0]), b));
const nodeHash = (l: Uint8Array, r: Uint8Array) => sha256(concat(new Uint8Array([1]), l, r));
function mth(leaves: Uint8Array[]): Uint8Array {
  const n = leaves.length;
  if (n === 0) return sha256(new Uint8Array());
  if (n === 1) return leafHash(leaves[0]);
  let k = 1;
  while (k * 2 < n) k *= 2;
  return nodeHash(mth(leaves.slice(0, k)), mth(leaves.slice(k)));
}
export const merkleRoot = (leaves: Uint8Array[]) => bytesToHex(mth(leaves));

export function verifyInclusion(entry: Uint8Array, index: number, size: number, proof: string[], root: string): boolean {
  if (index >= size) return false;
  let fn = index, sn = size - 1;
  let r = leafHash(entry);
  for (const ph of proof) {
    const p = hexToBytes(ph);
    if (sn === 0) return false;
    if (fn & 1 || fn === sn) {
      r = nodeHash(p, r);
      if (!(fn & 1)) while (fn && !(fn & 1)) { fn >>= 1; sn >>= 1; }
    } else r = nodeHash(r, p);
    fn >>= 1; sn >>= 1;
  }
  return sn === 0 && bytesToHex(r) === root;
}

// ---------------------------------------------------------------- bundle verification
export type Receipt = { [k: string]: Json } & { counter: number; type: string; key_id: string; prev: string; sig: string; body: { [k: string]: Json }; ts_ns: string };
export type Check = { name: string; ok: boolean; detail: string };
export type ReceiptStatus = { counter: number; sigOk: boolean; chainOk: boolean; counterOk: boolean };
export type Bundle = { format: string; files: Record<string, string> };
export type VerifyResult = { ok: boolean; checks: Check[]; receipts: Receipt[]; receiptStatus: ReceiptStatus[] };

const FORBIDDEN_BODY_KEYS = ["prompt", "response", "content", "raw", "email", "password", "secret"];

export function parseReceipts(ndjson: string): Receipt[] {
  return ndjson.split("\n").filter((l) => l.trim()).map((l) => JSON.parse(l));
}

export function verifyBundle(b: Bundle): VerifyResult {
  const f = b.files;
  const checks: Check[] = [];
  const add = (name: string, ok: boolean, detail: string) => checks.push({ name, ok, detail });
  const fail = (e: unknown): VerifyResult => ({
    ok: false, receipts: [], receiptStatus: [],
    checks: [...checks, { name: "structure", ok: false, detail: String(e instanceof Error ? e.message : e) }],
  });

  try {
    const keys = new Map<string, Uint8Array>();
    for (const [p, v] of Object.entries(f)) if (p.startsWith("keys/") && p.endsWith(".pub.hex")) {
      const raw = hexToBytes(v.trim());
      keys.set(keyId(raw), raw);
    }

    const manifest = JSON.parse(f["manifest.json"]) as Record<string, string>;
    const bad = Object.entries(manifest).filter(([rel, dg]) => {
      const c = f["artifacts/" + rel];
      return c === undefined || sha256Hex(utf8ToBytes(c)) !== dg;
    }).map(([rel]) => rel);
    add("manifest", bad.length === 0, bad.length ? `digest mismatch: ${bad.join(", ")}` : `${Object.keys(manifest).length} artifacts match their digests`);

    const env = JSON.parse(f["statement.dsse.json"]);
    const payload = b64d(env.payload);
    const t = utf8ToBytes(env.payloadType);
    const pae = concat(utf8ToBytes(`DSSEv1 ${t.length} `), t, utf8ToBytes(` ${payload.length} `), payload);
    const good = new Set<string>();
    for (const s of env.signatures) {
      const pk = keys.get(s.keyid);
      if (pk && edVerify(b64d(s.sig), pae, pk)) good.add(s.keyid);
    }
    const st = JSON.parse(new TextDecoder().decode(payload));
    const subj: Record<string, string> = Object.fromEntries(st.subject.map((s: any) => [s.name, s.digest.sha256]));
    const subjOk = Object.keys(subj).length === Object.keys(manifest).length && Object.entries(manifest).every(([k, v]) => subj[k] === v);
    add("statement", good.size >= 2 && subjOk,
      good.size < 2 ? `DSSE threshold not met (${good.size}/2)` : !subjOk ? "signed subjects do not match manifest" : `DSSE 2-of-${env.signatures.length} signatures valid`);

    const receipts = parseReceipts(f["receipts.ndjson"]);
    const status: ReceiptStatus[] = [];
    let prev = "0".repeat(64), expected = 1;
    const errs: string[] = [];
    receipts.forEach((r, i) => {
      const { sig, ...unsigned } = r;
      const canon = jcs(unsigned as Json);
      const pk = keys.get(r.key_id);
      const sigOk = !!pk && !!sig && edVerify(b64d(sig), canon, pk);
      const chainOk = r.prev === prev;
      const counterOk = r.counter === expected;
      if (!sigOk) errs.push(`#${i}: signature failure`);
      if (!chainOk) errs.push(`#${i}: chain break`);
      if (!counterOk) errs.push(`#${i}: counter gap`);
      status.push({ counter: r.counter, sigOk, chainOk, counterOk });
      prev = sha256Hex(canon);
      expected = r.counter + 1;
    });
    add("receipts", errs.length === 0, errs.length ? errs.slice(0, 4).join("; ") : `${receipts.length} receipts signed, chained, counters contiguous`);
    const leaks = receipts.filter((r) => FORBIDDEN_BODY_KEYS.some((k) => k in (r.body || {}))).map((r) => r.counter);
    add("non-egress", leaks.length === 0, leaks.length ? `content-like fields in receipts ${leaks}` : "receipt bodies hold commitments and digests only");

    const cp = JSON.parse(f["checkpoint.json"]);
    const leaves = receipts.map((r) => jcs(r as Json));
    const rootOk = merkleRoot(leaves) === cp.root && cp.size === leaves.length;
    const sth = { log: cp.log, size: cp.size, root: cp.root, ts_ns: cp.ts_ns };
    const wk = keys.get(cp.witness_keyid);
    const witOk = !!wk && edVerify(b64d(cp.witness_sig), jcs(sth), wk);
    add("checkpoint", rootOk && witOk, rootOk && witOk ? `witness-signed Merkle root ${cp.root.slice(0, 16)}` : !rootOk ? "Merkle root/size mismatch" : "witness signature invalid");

    const inc = JSON.parse(f["inclusion_bundle_signed.json"]);
    const br = receipts[inc.index];
    const incOk = !!br && br.type === "bundle_signed" &&
      verifyInclusion(leaves[inc.index], inc.index, inc.size, inc.proof, cp.root) &&
      br.body.envelope_sha256 === sha256Hex(jcs(env));
    add("inclusion", incOk, incOk ? "bundle_signed receipt proven in log and bound to this envelope" : "inclusion proof or envelope binding failed");

    return { ok: checks.every((c) => c.ok), checks, receipts, receiptStatus: status };
  } catch (e) {
    return fail(e);
  }
}

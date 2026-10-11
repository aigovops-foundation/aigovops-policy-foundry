import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { decide, approvalErrors, type Manifest } from "../src/lib/gate";

const P = (p: string) => JSON.parse(readFileSync(new URL(`../../api/foundry/assets/parity/${p}`, import.meta.url), "utf8"));
const corpus = P("corpus.json");
const expected = P("expected.json");
const manifest: Manifest = JSON.parse(readFileSync(new URL("../public/demo/agents.json", import.meta.url), "utf8"));

describe("gate parity with OPA golden output", () => {
  it(`all ${corpus.decisions.length} decision cases match`, () => {
    const mismatches = corpus.decisions
      .map((c: any, i: number) => ({ c, got: decide(c, manifest), want: expected.decisions[i] }))
      .filter((x: any) => JSON.stringify(x.got) !== JSON.stringify({ result: x.want.result, reasons: x.want.reasons }));
    expect(mismatches.slice(0, 3)).toEqual([]);
  });
  it(`all ${corpus.approvals.length} approval cases match`, () => {
    corpus.approvals.forEach((c: any, i: number) => expect(approvalErrors(c, manifest)).toEqual(expected.approvals[i]));
  });
});

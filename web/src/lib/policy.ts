import type { Receipt } from "./evidence";

export const POLICY_FILES = {
  doc: "artifacts/docs/ai_code_change.md",
  rego: "artifacts/policy/ai_code_change.rego",
  tests: "artifacts/tests/acceptance_test.rego",
} as const;

export type Block = { kind: "h1" | "h2" | "p"; text: string } | { kind: "ol"; items: string[] };

export function parseMarkdown(md: string): Block[] {
  const blocks: Block[] = [];
  let paragraph: string[] = [];
  let items: string[] = [];

  const flushParagraph = () => {
    if (paragraph.length) blocks.push({ kind: "p", text: paragraph.join(" ") });
    paragraph = [];
  };
  const flushList = () => {
    if (items.length) blocks.push({ kind: "ol", items });
    items = [];
  };

  for (const line of md.split(/\r?\n/)) {
    if (!line.trim()) {
      flushParagraph();
      flushList();
      continue;
    }
    if (line.startsWith("# ")) {
      flushParagraph();
      flushList();
      blocks.push({ kind: "h1", text: line.slice(2).trim() });
      continue;
    }
    if (line.startsWith("## ")) {
      flushParagraph();
      flushList();
      blocks.push({ kind: "h2", text: line.slice(3).trim() });
      continue;
    }
    if (/^\s*\d+\.\s+/.test(line)) {
      flushParagraph();
      items.push(line.replace(/^\s*\d+\.\s+/, "").trim());
      continue;
    }
    if (items.length && /^\s+/.test(line)) {
      items[items.length - 1] += ` ${line.trim()}`;
      continue;
    }
    flushList();
    paragraph.push(line.trim());
  }

  flushParagraph();
  flushList();
  return blocks;
}

export function regoRequirements(rego: string): { id: string; text: string }[] {
  return Array.from(rego.matchAll(/^# (REQ-[\d.]+) -- (.*)$/gm), ([, id, text]) => ({ id, text }));
}

export function regoTests(rego: string): string[] {
  return Array.from(rego.matchAll(/^(test_\w+)/gm), ([, name]) => name);
}

export function policyTitle(h1: string): string {
  return h1
    .replace(/ -- EXAMPLE$/, "")
    .replace(/^Policy:\s*/, "")
    .replace(/\s*\(REQ-[^)]+\)$/, "");
}

export type Decisions = {
  requester: string | null;
  approvers: string[];
  requesterApproved: boolean;
  approvalCounter: number | null;
  signingOfficer: string | null;
  signers: string[];
  signedCounter: number | null;
  testsCommittedCounter: number | null;
  draftCounter: number | null;
};

export function decisions(receipts: Receipt[]): Decisions {
  const approval = receipts.find((r) => r.type === "policy_approval");
  const signature = receipts.find((r) => r.type === "bundle_signed");
  const commitment = receipts.find((r) => r.type === "test_commitment");
  const draft = receipts.find((r) =>
    r.type === "permit" && r.body.agent === "policy_writer" && r.body.action === "git.push");
  const requester = typeof approval?.body.requester === "string" ? approval.body.requester : null;
  const approvers = Array.isArray(approval?.body.approvers)
    ? approval.body.approvers.filter((value): value is string => typeof value === "string")
    : [];
  const signingOfficer = typeof signature?.body.signing_officer === "string" ? signature.body.signing_officer : null;
  const signers = Array.isArray(signature?.body.signers)
    ? signature.body.signers.filter((value): value is string => typeof value === "string")
    : [];

  return {
    requester,
    approvers,
    requesterApproved: requester !== null && approvers.includes(requester),
    approvalCounter: approval?.counter ?? null,
    signingOfficer,
    signers,
    signedCounter: signature?.counter ?? null,
    testsCommittedCounter: commitment?.counter ?? null,
    draftCounter: draft?.counter ?? null,
  };
}

export const shortId = (id: string) => id.slice(id.lastIndexOf(":") + 1).slice(0, 8);

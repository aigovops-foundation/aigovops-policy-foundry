import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { parseReceipts, type Bundle } from "../src/lib/evidence";
import { decisions, parseMarkdown, POLICY_FILES, regoRequirements, regoTests, shortId } from "../src/lib/policy";
import { isRole, ROLES } from "../src/lib/roles";

const bundle = JSON.parse(readFileSync(new URL("../public/demo/bundle.json", import.meta.url), "utf8")) as Bundle;
const run = JSON.parse(readFileSync(new URL("../public/demo/run.json", import.meta.url), "utf8"));
const doc = bundle.files[POLICY_FILES.doc];
const rego = bundle.files[POLICY_FILES.rego];
const tests = bundle.files[POLICY_FILES.tests];

describe("policy source helpers", () => {
  it("parses the policy markdown and joins ordered-list continuation lines", () => {
    const blocks = parseMarkdown(doc);
    expect(blocks[0]).toMatchObject({ kind: "h1", text: expect.stringMatching(/^Policy: AI-assisted changes/) });
    const list = blocks.find((block) => block.kind === "ol");
    expect(list?.kind).toBe("ol");
    if (list?.kind === "ol") {
      expect(list.items).toHaveLength(5);
      expect(list.items[0]).toContain("Management of Change (MOC) process");
    }
    expect(blocks.some((block) => block.kind === "h2" && block.text === "Requirements")).toBe(true);
  });

  it("extracts the five requirement identifiers", () => {
    expect(regoRequirements(rego).map((requirement) => requirement.id)).toEqual([
      "REQ-1042.1",
      "REQ-1042.2",
      "REQ-1042.3",
      "REQ-1042.4",
      "REQ-1042.5",
    ]);
  });

  it("extracts the tests in source order and matches the run summary", () => {
    const names = regoTests(tests);
    expect(names).toHaveLength(10);
    expect(names).toHaveLength(run.tests.passed + run.tests.failed);
    expect(names).toContain("test_ot_target_without_moc_denied");
  });
});

describe("policy decision evidence", () => {
  const receipts = parseReceipts(bundle.files["receipts.ndjson"]);

  it("reads the expected approval, test and signing receipts", () => {
    const result = decisions(receipts);
    expect(result.approvers).toHaveLength(2);
    expect(result.requesterApproved).toBe(false);
    expect(result.approvalCounter).toBe(17);
    expect(result.signedCounter).toBe(18);
    expect(result.signers).toHaveLength(2);
    expect(result.testsCommittedCounter).toBe(5);
    expect(result.draftCounter).toBe(8);
  });

  it("detects when the requester is included among approvers", () => {
    const result = decisions(receipts);
    const injected = receipts.map((receipt) => receipt.type === "policy_approval"
      ? {
        ...receipt,
        body: {
          ...receipt.body,
          approvers: [...(receipt.body.approvers as string[]), result.requester as string],
        },
      }
      : receipt);
    expect(decisions(injected).requesterApproved).toBe(true);
  });

  it("returns empty decisions when there are no receipts", () => {
    expect(decisions([])).toEqual({
      requester: null,
      approvers: [],
      requesterApproved: false,
      approvalCounter: null,
      signingOfficer: null,
      signers: [],
      signedCounter: null,
      testsCommittedCounter: null,
      draftCounter: null,
    });
  });

  it("shortens both keyed commitment and public-key identifiers", () => {
    expect(shortId("hmac-sha256:9c4584e8f365…")).toBe("9c4584e8");
    expect(shortId("ed25519:ff7941ae6b04d8de")).toBe("ff7941ae");
  });
});

describe("role tours", () => {
  it("defines five three-step roles with registered internal routes", () => {
    const routes = ["/policy", "/gate", "/evidence", "/verify", "/underwriting", "/agents"];
    expect(ROLES).toHaveLength(5);
    for (const role of ROLES) {
      expect(role.steps).toHaveLength(3);
      for (const step of role.steps.filter((item) => !item.external)) {
        expect(routes).toContain(step.to);
      }
    }
    expect(isRole("auditor")).toBe(true);
    expect(isRole("xyz")).toBe(false);
  });
});

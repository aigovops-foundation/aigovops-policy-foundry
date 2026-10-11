import { useRef, useState, type KeyboardEvent } from "react";
import { Link } from "wouter";
import { useStore } from "../lib/store";
import { openExternal, POLICY_REQUEST_URL } from "../lib/links";
import { decisions, parseMarkdown, POLICY_FILES, policyTitle, regoRequirements, regoTests, shortId, testOrder } from "../lib/policy";
import type { ReceiptStatus } from "../lib/evidence";

type SourceTab = "rego" | "tests";

function StatusPill({ ok, label }: { ok: boolean; label?: string }) {
  return <span className={`pill ${ok ? "ok" : "bad"}`}>{label ?? (ok ? "Verified" : "Broken")}</span>;
}

function receiptChecksOk(counters: (number | null)[], status: ReceiptStatus[]): boolean {
  return counters.length > 0 && counters.every((counter) => {
    if (counter === null) return false;
    const receipt = status.find((s) => s.counter === counter);
    return !!receipt && receipt.sigOk && receipt.chainOk && receipt.counterOk;
  });
}

function receiptLabels(counters: (number | null)[]): string {
  const present = counters.filter((counter): counter is number => counter !== null);
  return present.length ? present.map((counter) => `#${counter}`).join(" · ") : "—";
}

export default function Policy() {
  const { bundle, result, run } = useStore();
  const [source, setSource] = useState<SourceTab>("rego");
  const tabRefs = useRef<Record<SourceTab, HTMLButtonElement | null>>({ rego: null, tests: null });

  if (!bundle || !result) return <div className="page"><div className="card skeleton" style={{ height: 220 }} /></div>;

  const doc = bundle.files[POLICY_FILES.doc];
  const rego = bundle.files[POLICY_FILES.rego];
  const testsFile = bundle.files[POLICY_FILES.tests];
  if (doc === undefined || rego === undefined || testsFile === undefined) {
    return <div className="page"><section className="card">This bundle has no policy files.</section></div>;
  }

  const blocks = parseMarkdown(doc);
  const titleBlock = blocks.find((block): block is { kind: "h1"; text: string } => block.kind === "h1");
  const owner = blocks.find((block): block is { kind: "p"; text: string } => block.kind === "p" && block.text.startsWith("Owner:"));
  const title = policyTitle(titleBlock?.text ?? "Policy");
  const languageBlocks = blocks.filter((block) => block.kind !== "h1" && block !== owner);
  const requirements = regoRequirements(rego);
  const tests = regoTests(testsFile);
  const decision = decisions(result.receipts);
  const manifestOk = result.checks.find((check) => check.name === "manifest")?.ok ?? false;
  const approvalNote = `${decision.approvers.length} approvers: ${decision.approvers.map(shortId).join(", ")}${!decision.requesterApproved ? " · neither is the requester" : ""}`;
  const testsOrder = testOrder(decision);
  const testsNote = testsOrder === "before"
    ? `Committed before the draft was written (receipt #${decision.testsCommittedCounter} before #${decision.draftCounter})`
    : testsOrder === "after"
    ? `Tests were committed after the draft (receipt #${decision.testsCommittedCounter} after #${decision.draftCounter})`
    : "No receipt shows when the tests were committed relative to the draft";

  const handleTabKeyDown = (event: KeyboardEvent<HTMLButtonElement>, current: SourceTab) => {
    if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
    event.preventDefault();
    const next = current === "rego" ? "tests" : "rego";
    setSource(next);
    tabRefs.current[next]?.focus();
  };

  return (
    <div className="page">
      <section className="card">
        <div className="policy-header">
          <div className="stack" style={{ gap: "var(--space-2)", minWidth: 0 }}>
            {run && <span className="pill accent mono" style={{ justifySelf: "start" }}>{run.request_id}</span>}
            <div className="row">
              <p className="hero-title">{title}</p>
              <span className="pill neutral">Example policy</span>
            </div>
            {owner && <p className="muted small" style={{ margin: 0 }}>{owner.text}</p>}
          </div>
          <div className="policy-actions">
            <a className="btn primary" href={POLICY_REQUEST_URL} target="_blank" rel="noreferrer" onClick={openExternal}>
              Request a policy
            </a>
            <StatusPill ok={manifestOk} label={manifestOk ? "Matches the signed bundle" : "Doesn't match the signed bundle"} />
          </div>
        </div>
      </section>

      <section className="card">
        <h2>What it requires</h2>
        <div className="grid g2 policy-grid">
          <div className="stack">
            <h3 className="policy-column-title">In plain language</h3>
            <div className="md">
              {languageBlocks.map((block, index) => {
                if (block.kind === "h2") return <h3 key={index}>{block.text}</h3>;
                if (block.kind === "p") return <p key={index}>{block.text}</p>;
                if (block.kind === "ol") return <ol key={index}>{block.items.map((item, itemIndex) => <li key={itemIndex}>{item}</li>)}</ol>;
                return null;
              })}
            </div>
          </div>
          <div className="stack">
            <h3 className="policy-column-title">How each rule is enforced</h3>
            <div className="list">
              {requirements.map((requirement) => (
                <div className="li policy-requirement" key={requirement.id}>
                  <span className="mono xs">{requirement.id}</span>
                  <span>{requirement.text.charAt(0).toUpperCase() + requirement.text.slice(1)}</span>
                </div>
              ))}
            </div>
            <p className="muted xs" style={{ margin: 0 }}>Enforced by the rule file below. If any rule is broken, the change is denied.</p>
          </div>
        </div>
      </section>

      <section className="card">
        <h2>Who decided</h2>
        <div className="list">
          <div className="li">
            <div className="grow">
              <div className="title">Tests written first</div>
              <div className="meta">{testsNote}</div>
            </div>
            <span className="xs muted mono num">{receiptLabels([decision.testsCommittedCounter])}</span>
            {testsOrder === "before"
              ? <StatusPill ok={receiptChecksOk([decision.testsCommittedCounter], result.receiptStatus)} />
              : testsOrder === "after"
              ? <StatusPill ok={false} label="Not test-first" />
              : <span className="pill warn">Unproven</span>}
          </div>
          <div className="li">
            <div className="grow">
              <div className="title">Approved by {decision.approvers.length} {decision.approvers.length === 1 ? "person" : "people"}</div>
              <div className="meta">{approvalNote}</div>
            </div>
            <span className="xs muted mono num">{receiptLabels([decision.approvalCounter])}</span>
            <StatusPill
              ok={!decision.requesterApproved && receiptChecksOk([decision.approvalCounter], result.receiptStatus)}
              label={decision.requesterApproved ? "Requester approved" : undefined}
            />
          </div>
          <div className="li">
            <div className="grow">
              <div className="title">Signed by the signing officer</div>
              <div className="meta">Officer {decision.signingOfficer ? shortId(decision.signingOfficer) : "—"} · {decision.signers.length} signatures</div>
            </div>
            <span className="xs muted mono num">{receiptLabels([decision.signedCounter])}</span>
            <StatusPill ok={receiptChecksOk([decision.signedCounter], result.receiptStatus)} />
          </div>
          <div className="li">
            <div className="grow">
              <div className="title">Agents cannot approve or sign</div>
              <div className="meta">Only people can approve or sign; the gate enforces this. <Link href="/agents">See each agent&apos;s limits</Link></div>
            </div>
          </div>
        </div>
        <p className="muted xs" style={{ margin: "var(--space-3) 0 0" }}>
          People appear as pseudonymous IDs. The operator keeps the mapping; names are never in the bundle.
        </p>
      </section>

      <section className="card stack policy-source">
        <h2>Source</h2>
        <div className="seg" role="tablist" aria-label="Policy source">
          <button
            ref={(element) => { tabRefs.current.rego = element; }}
            id="policy-tab-rego"
            type="button"
            role="tab"
            aria-selected={source === "rego"}
            aria-controls="policy-source-panel"
            onClick={() => setSource("rego")}
            onKeyDown={(event) => handleTabKeyDown(event, "rego")}
          >
            Rule (Rego)
          </button>
          <button
            ref={(element) => { tabRefs.current.tests = element; }}
            id="policy-tab-tests"
            type="button"
            role="tab"
            aria-selected={source === "tests"}
            aria-controls="policy-source-panel"
            onClick={() => setSource("tests")}
            onKeyDown={(event) => handleTabKeyDown(event, "tests")}
          >
            Tests ({tests.length})
          </button>
        </div>
        <div id="policy-source-panel" className="policy-source-panel" role="tabpanel" aria-labelledby={`policy-tab-${source}`} tabIndex={0}>
          {source === "tests" && run && (
            <p className="muted xs" style={{ margin: "0 0 var(--space-2)" }}>
              {run.tests.passed}/{run.tests.passed + run.tests.failed} pass · written from the requirement before the draft
            </p>
          )}
          <pre className="json" tabIndex={0} aria-label={source === "rego" ? "Rule source" : "Tests source"}>{source === "rego" ? rego : testsFile}</pre>
        </div>
      </section>
    </div>
  );
}

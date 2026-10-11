# End users

For plant engineers and staff whose AI-assisted changes are governed, and anyone curious about the process.

> **Start here:** A human decides what the requirement means. The gate limits what an agent can do.

## What happens to my change

1. Someone writes a requirement for a change to plant-supporting software.
2. Agents may draft a policy, write tests and look for conflicts within their
   separate scopes.
3. The gate checks boundary-crossing actions and records demo evidence.
4. Two authorized people approve the policy. A separate signing officer signs it.
5. A pull request and maintainer review are part of how a repository change lands.

An agent cannot approve or sign its own work. This project does not connect to an
OT zone.

## Allow, Deny or Escalate

- **Allow:** the action matches the agent's permitted scope.
- **Deny:** the action conflicts with a rule or exceeds the agent's scope.
- **Escalate to a human:** the action needs a human decision, such as approval or signing.

These are gate decisions about observed actions. They do not tell you whether a
policy is correct or complete.

## Explore the dashboard

Open the [browser demo](https://aigovops-foundation.github.io/aigovops-policy-foundry/)
to explore bundled demo evidence without installing anything; no data leaves your
device. To run the local Docker demo, follow the
[Home instructions](README.md#a-time-ladder) or
[`scripts/demo.sh`](../../scripts/demo.sh).

Overview shows the request-to-signing journey, verified-receipt count, acceptance
tests and gate stops. In three clicks, open Evidence, select a receipt and click
**Tamper with it**; its signature and the next receipt's chain link fail. Click
**Restore** to return to the original demo data. Verify can check a bundle
without uploading it.

Desktop and mobile Tauri builds exist, but CI artifacts are unsigned today.
Store distribution needs Foundation-owned signing credentials and Review Circle
sign-off; see [native app details](../../apps/native/README.md).

The accessibility pass with a real screen reader has not been done yet. See
[DEVIN.md §5](../../DEVIN.md).

## Questions

Ask your organization's policy owner or open an issue in the repository's Issues
tab. Do not include secrets, plant topology, OT asset lists or export-controlled
data in a public issue.

[Back to Home](README.md)

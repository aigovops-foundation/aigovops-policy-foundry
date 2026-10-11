# 90-second demo walkthrough

A script for showing the Policy Foundry to anyone, live, in about 90 seconds.
It uses the [browser demo](https://aigovops-foundation.github.io/aigovops-policy-foundry/),
which runs offline with bundled demo evidence; nothing you click leaves your device.

| Time | Click | Say |
|---|---|---|
| 0:00 | Open the [browser demo](https://aigovops-foundation.github.io/aigovops-policy-foundry/). | "Four AI agents drafted, tested and audited a policy. People approved and signed it. Every step left a signed receipt." Point at **Offline demo** and **Verified**. |
| 0:15 | **Start here** → pick the role closest to your audience (for example **Auditor or insurer**). | "Each role gets a three-step path. You can share it as a link, like `#/start/auditor`." |
| 0:25 | **Policy**. | "This is REQ-1042 in plain language, next to the rule that enforces it and the tests written before the draft." Point at **What it requires** and **Who decided**. |
| 0:40 | **Gate** → **Reach the plant floor**, then **Auditor tries to approve**. | "The agents can't reach plant systems, and they can't approve or sign. Only people can, and the gate enforces it." |
| 0:55 | **Evidence** → pick receipt #5 → **Tamper with it**. | "Change a field in one receipt and verification fails." Show **Not verified**. On **Policy**, "Tests written first" now says **Broken**. |
| 1:10 | **Evidence** → **Restore**. | "Put it back and everything verifies again. An auditor can run the same check offline with `foundry-verify`." |
| 1:20 | **Underwriting**. | "Insurers and auditors get a self-assessment with its limitations stated. It's evidence to review, not a certification." |
| 1:30 | Done. | "Your path starts at the [persona wiki](README.md)." |

## Tips

- On a phone, Policy and Underwriting are under **More**.
- Reloading the page resets the demo, including any tampering.
- Don't say the demo proves a policy is correct, complete, safe or certified. It shows how the evidence is produced and checked.

[Back to Home](README.md)

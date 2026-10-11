import { POLICY_REQUEST_URL, wiki } from "./links";

export type RoleId = "policy" | "lowcode" | "procode" | "auditor" | "enduser";
export type Step = { label: string; hint: string; to: string; external?: boolean };

export const TOUR: Step[] = [
  { label: "Read the policy", hint: "Plain language beside the rule that enforces it", to: "/policy" },
  { label: "Try to break the gate", hint: "Ask an agent to do something it shouldn't", to: "/gate" },
  { label: "Tamper with the evidence", hint: "Change one receipt and watch verification fail", to: "/evidence" },
];

export const ROLES: { id: RoleId; label: string; who: string; steps: Step[] }[] = [
  { id: "policy", label: "Policy", who: "You write, own, approve or sign policy", steps: [
    { label: "Read REQ-1042", hint: "Plain language beside its rule and tests", to: "/policy" },
    { label: "See who may approve and sign", hint: "Agents can't; two people and a signing officer must", to: "/agents" },
    { label: "Request a policy", hint: "Structured form on GitHub", to: POLICY_REQUEST_URL, external: true },
  ] },
  { id: "lowcode", label: "Low-code", who: "You configure with forms, YAML or JSON", steps: [
    { label: "Try an action on the gate", hint: "Pick a scenario or edit the JSON", to: "/gate" },
    { label: "See what each agent may do", hint: "Allowed and forbidden actions", to: "/agents" },
    { label: "Read the low-code guide", hint: "Edit config safely and see what CI checks", to: wiki("Low-code-builders"), external: true },
  ] },
  { id: "procode", label: "Pro-code", who: "You build on the API or change the code", steps: [
    { label: "Read the rule and its tests", hint: "Rego, written by agents, tests first", to: "/policy" },
    { label: "Run the gate", hint: "Same rules as the server, computed here", to: "/gate" },
    { label: "Read the developer guide", hint: "Setup, API routes, tests, extension points", to: wiki("Pro-code-developers"), external: true },
  ] },
  { id: "auditor", label: "Auditor or insurer", who: "You check evidence or assess risk", steps: [
    { label: "Verify the bundle", hint: "Runs on this device; nothing is uploaded", to: "/verify" },
    { label: "Tamper with a receipt", hint: "See exactly which check catches it", to: "/evidence" },
    { label: "Read the underwriting packet", hint: "Limitations are listed first", to: "/underwriting" },
  ] },
  { id: "enduser", label: "Affected by a change", who: "You use or run the plant software", steps: [
    { label: "See what the policy requires", hint: "Five rules in plain language", to: "/policy" },
    { label: "See what the gate stopped", hint: "Denied, or sent to a person", to: "/gate" },
    { label: "Tamper with the evidence", hint: "Proof that edits are caught", to: "/evidence" },
  ] },
];

export const isRole = (s: string | undefined): s is RoleId => ROLES.some((r) => r.id === s);

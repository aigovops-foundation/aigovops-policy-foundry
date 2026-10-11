import type { MouseEvent } from "react";

export const REPO = "https://github.com/aigovops-foundation/aigovops-policy-foundry";

export function openExternal(e: MouseEvent<HTMLAnchorElement>) {
  const t = (window as any).__TAURI__;
  if (t?.opener?.openUrl) { e.preventDefault(); t.opener.openUrl(e.currentTarget.href); }
}

export const POLICY_REQUEST_URL = `${REPO}/issues/new?template=policy_request.yml`;
export const wiki = (page: string) => `${REPO}/blob/main/docs/wiki/${page}.md`;

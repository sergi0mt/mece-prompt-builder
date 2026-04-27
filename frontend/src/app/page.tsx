/**
 * Root route — redirects to the V2 redesign landing.
 *
 * The original V1 landing has been archived to `_v1-page-archived.tsx.bak`.
 * V1 project workspaces are still reachable directly at `/projects/[id]`
 * for back-compat with bookmarks, but the default entrypoint for new
 * users is now the V2 design system at `/v2`.
 */
import { redirect } from "next/navigation";

export default function RootRedirect() {
  redirect("/v2");
}

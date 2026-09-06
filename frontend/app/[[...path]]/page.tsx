// [Input] Any existing Dream browser URL handled by the App Router.
// [Output] The client-only compatibility shell, preserving refresh and history semantics.
// [Pos] Next catch-all page; API and public Route Handlers take precedence.
// [Sync] 2026-09-05: route existing SPA paths through the canonical root Next shell.

import ClientShell from '../client-shell';

export default function CompatibilityPage() {
  return <ClientShell />;
}

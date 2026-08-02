// [Input] Dream business content supplied by the app composition root.
// [Output] Render the canonical Dream route as a full-height Chat/Agent workspace.
// [Pos] Canonical /story-workspace/dream page.
import type { ReactNode } from 'react';

export function StoryWorkspaceDreamPage({ children }: { children: ReactNode }) {
  return (
    <div style={{ width: '100%', height: '100%', minWidth: 0, minHeight: 0, overflow: 'hidden' }}>
      {children}
    </div>
  );
}

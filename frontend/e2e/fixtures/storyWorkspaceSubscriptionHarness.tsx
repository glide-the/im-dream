// [Input] Real subscription view from the non-framework Story Workspace UI tree.
// [Output] Browser-only Playwright harness without App-wide data fixtures.
// [Pos] Provider-free subscription component harness.
// [Sync] 2026-09-05: resolve the relocated subscription view from app/_dream/views.
import { createRoot } from 'react-dom/client';
import { StoryWorkspaceSubscriptionPage } from '../../app/_dream/views/story-workspace/StoryWorkspaceSubscriptionPage';

const root = document.getElementById('root');
if (!root) throw new Error('Subscription harness root is unavailable.');
createRoot(root).render(<StoryWorkspaceSubscriptionPage />);

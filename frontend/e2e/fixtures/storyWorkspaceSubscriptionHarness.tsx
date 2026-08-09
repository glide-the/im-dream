// Browser-only Playwright harness for rendering the real subscription component without App-wide data fixtures.
import { createRoot } from 'react-dom/client';
import { StoryWorkspaceSubscriptionPage } from '../../src/pages/story-workspace/StoryWorkspaceSubscriptionPage';

const root = document.getElementById('root');
if (!root) throw new Error('Subscription harness root is unavailable.');
createRoot(root).render(<StoryWorkspaceSubscriptionPage />);

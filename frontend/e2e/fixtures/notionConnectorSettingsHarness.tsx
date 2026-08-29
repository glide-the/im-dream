// [Input] Production Notion Settings components and provider-free intercepted connector DTOs.
// [Output] Minimal browser harness for Settings summary, redesigned detail/child navigation, and disconnect interaction.
// [Pos] Notion connector technical browser fixture in frontend/e2e/fixtures.
// [Sync] 2026-08-29: host the seven-section Notion detail and focused child views beside the restored disabled discovery placeholders.

import { useState } from 'react';
import { createRoot } from 'react-dom/client';
import ConnectorNotionDetailPage from '../../src/components/dashboard/ConnectorNotionDetailPage';
import ConnectorSettingsSection from '../../src/components/dashboard/ConnectorSettingsSection';

export function Harness() {
  const [detailOpen, setDetailOpen] = useState(false);
  return (
    <main style={{ maxWidth: 920, margin: '0 auto', padding: 24 }}>
      {detailOpen ? (
        <ConnectorNotionDetailPage onBack={() => setDetailOpen(false)} />
      ) : (
        <ConnectorSettingsSection onOpenNotionDetail={() => setDetailOpen(true)} />
      )}
    </main>
  );
}

const harnessWindow = window as typeof window & {
  __notionConnectorHarnessRoot?: ReturnType<typeof createRoot>;
};
const root = harnessWindow.__notionConnectorHarnessRoot
  ?? createRoot(document.getElementById('root')!);
harnessWindow.__notionConnectorHarnessRoot = root;
root.render(<Harness />);

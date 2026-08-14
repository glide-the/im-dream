import { createRoot } from 'react-dom/client';
import ModelConfigSection from '../../src/components/dashboard/ModelConfigSection';

createRoot(document.getElementById('root')!).render(
  <main style={{ maxWidth: 760, margin: '0 auto', padding: 24 }}>
    <h1>AI 模型配置</h1>
    <ModelConfigSection />
  </main>,
);

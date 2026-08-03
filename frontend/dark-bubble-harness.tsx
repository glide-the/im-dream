// 暗色模式用户气泡复现 harness — 跑完即删。
import { createRoot } from 'react-dom/client';
import UserMessagePart from './src/components/chat/UserMessagePart';
import './src/styles/tokens.css';
import './src/styles/markdown.css';

const container = document.getElementById('root');
if (container) {
  container.style.cssText = 'padding:40px;background:var(--color-bg-app);min-height:300px;';
  createRoot(container).render(
    <UserMessagePart text={'你好，这是一条用户消息测试。\n\n第二行内容。'} />,
  );
}

// [Input] One trusted saved official tool part injected by the Node-side Playwright harness.
// [Output] The production ToolMessagePart tree plus an auditable user-message boundary callback.
// [Pos] Provider-free Browser mount only; production components and policy APIs remain unmodified.
// [Sync] 2026-09-06: expose a deterministic same-mount Thread switch for Browser session lifecycle acceptance.
// [Sync] 2026-09-06: expose a parent rerender with a fresh Chat callback identity to prove the mounted App keeps in-progress input.

/* eslint-disable react-refresh/only-export-components -- provider-free browser entry renders at module load */

import { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';

import '../../../app/_dream/i18n';
import { ToolMessagePart } from '../../../app/_dream/components/chat/ToolMessagePart';
import type { ChatUserMessage } from '../../../app/_dream/components/chat/chatUserMessageIngress';


type BrowserHarnessState = {
  messages: ChatUserMessage[];
  sendMessageCalls: number;
  switchThread: (threadId: string) => void;
};

type BrowserHarnessConfig = {
  threadId: string;
  part: Record<string, unknown>;
};

declare global {
  interface Window {
    __MCP_APPS_E2E_CONFIG__: BrowserHarnessConfig;
    mcpAppsE2e: BrowserHarnessState;
  }
}


const harnessState: BrowserHarnessState = {
  messages: [],
  sendMessageCalls: 0,
  switchThread: () => undefined,
};
window.mcpAppsE2e = harnessState;


function OfficialToolMessageHarness() {
  const config = window.__MCP_APPS_E2E_CONFIG__;
  const [messageCount, setMessageCount] = useState(0);
  const [threadId, setThreadId] = useState(config.threadId);
  const [parentRevision, setParentRevision] = useState(0);
  const sendUserMessage = async (message: ChatUserMessage) => {
    harnessState.messages.push(structuredClone(message));
    harnessState.sendMessageCalls += 1;
    setMessageCount(harnessState.sendMessageCalls);
  };
  useEffect(() => {
    harnessState.switchThread = setThreadId;
    return () => {
      harnessState.switchThread = () => undefined;
    };
  }, []);

  return (
    <main style={{ width: 'min(760px, calc(100vw - 48px))', margin: '24px auto', fontFamily: 'system-ui' }}>
      <h1>Official MCP App production-path harness</h1>
      <p data-testid="existing-chat-ingress-count">{messageCount}</p>
      <button
        type="button"
        data-testid="mcp-app-parent-rerender"
        onClick={() => setParentRevision((value) => value + 1)}
      >
        Parent rerender {parentRevision}
      </button>
      <ToolMessagePart
        part={structuredClone(config.part) as never}
        threadId={threadId}
        sendUserMessage={sendUserMessage}
      />
    </main>
  );
}


createRoot(document.getElementById('root')!).render(<OfficialToolMessageHarness />);

// [Input] Successful latest-page history reads and the current in-memory browser session.
// [Output] Current/previous Thread reading previews; runtime state and write authorization remain uncached.
// [Pos] Bounded Chat navigation memory shared by Web and Native callers, with no persistent storage.
import type {UIMessage} from 'ai';
import {getBrowserCsrfToken} from '../../lib/browserSession';
import type {ClaudeThreadHistorySnapshot} from './threadSessionHydration';

export function createThreadHistoryPreview() {
  let scope = getBrowserCsrfToken();
  let current: {id:string;history:ClaudeThreadHistorySnapshot}|undefined;
  let previous: typeof current;
  function clear() { current=undefined;previous=undefined; }
  function synchronize() {
    const next=getBrowserCsrfToken();
    if(next!==scope || next===null) { clear();scope=next; }
    return next;
  }
  return {
    read(id:string) {
      if(!synchronize())return undefined;
      return current?.id===id?current.history:previous?.id===id?previous.history:undefined;
    },
    remember(id:string,history:ClaudeThreadHistorySnapshot,requestScope:string|null) {
      if(!synchronize() || scope!==requestScope)return;
      if(history.thread && history.thread.id!==id)return;
      if(current?.id!==id)previous=current;
      const {thread,messages,dispatchStatusByMessageId,nextCursor,hasMore,latestMessageId,unchanged}=history;
      current={id,history:{thread,messages,dispatchStatusByMessageId,nextCursor,hasMore,latestMessageId,unchanged}};
    },
    forget(id:string) {
      if(current?.id===id)current=undefined;
      if(previous?.id===id)previous=undefined;
    },
    clear,
  };
}

/** Reading previews expose saved prose only. Tool hosts, approvals and runtime
 * controls mount after the fresh history/status reconciliation completes. */
export function threadHistoryPreviewMessages(history:ClaudeThreadHistorySnapshot|undefined):UIMessage[] {
  return (history?.messages??[]).map(message=>({id:message.id,role:message.role,parts:message.parts.filter(part=>part.type==='text')}))
    .filter(message=>message.parts.length>0);
}

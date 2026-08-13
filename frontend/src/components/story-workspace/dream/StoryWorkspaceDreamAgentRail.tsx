// [Input] Dream business provenance and the actor-scoped canonical thread binding.
// [Output] Compact business annotation and a direct full-Chat thread handoff;
//          live lifecycle stays inside ChatPanel.
// [Pos] Dream right rail, never an Agent runtime status owner.
// [Sync] 2026-08-13: add a bound-thread navigation action to canonical Chat.

import { StoryWorkspaceDreamDeckMetadata } from './StoryWorkspaceDreamDeckMetadata';

export interface StoryWorkspaceDreamAgentRailProps {
  readonly deckName: string;
  readonly runId: string;
  readonly stageLine: string;
  readonly runtimeSnapshotId: string | null;
  readonly runtimeLockId: string | null;
  readonly threadId: string | null;
  readonly onOpenChatThread: (threadId: string) => void;
}

export function StoryWorkspaceDreamAgentRail({
  deckName,
  runId,
  stageLine,
  runtimeSnapshotId,
  runtimeLockId,
  threadId,
  onOpenChatThread,
}: StoryWorkspaceDreamAgentRailProps) {
  return (
    <section className="story-workspace-dream-agent-rail" aria-label="Dream Agent 会话">
      <div className="story-workspace-dream-agent-rail__summary">
        <StoryWorkspaceDreamDeckMetadata
          deckName={deckName}
          runId={runId}
          runtimeLockId={runtimeLockId}
          runtimeSnapshotId={runtimeSnapshotId}
          stageLine={stageLine}
        />
        <span className="story-workspace-dream-agent-rail__status">
          <span aria-hidden="true" className="story-workspace-dream-agent-rail__mark" />
          <span>{threadId ? '与 Chat 共用同一 Agent 会话' : '正在读取 Agent 会话绑定'}</span>
        </span>
        <span className="story-workspace-dream-agent-rail__meta">{stageLine}</span>
        <button
          aria-label={threadId ? '在 Chat 中打开当前 thread' : '正在等待 Chat thread'}
          className="story-workspace-dream-agent-rail__chat-link"
          disabled={threadId === null}
          onClick={() => {
            if (threadId !== null) onOpenChatThread(threadId);
          }}
          title={threadId ? '在 Chat 中打开' : undefined}
          type="button"
        >
          {threadId ? 'Chat ↗' : 'Chat …'}
        </button>
      </div>
    </section>
  );
}

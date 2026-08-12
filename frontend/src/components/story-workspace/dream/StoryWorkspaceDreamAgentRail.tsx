// [Input] Dream business provenance and the actor-scoped canonical thread binding.
// [Output] Compact business annotation; live lifecycle stays inside ChatPanel.
// [Pos] Dream right rail, never an Agent runtime status owner.

import { StoryWorkspaceDreamDeckMetadata } from './StoryWorkspaceDreamDeckMetadata';

export interface StoryWorkspaceDreamAgentRailProps {
  readonly deckName: string;
  readonly runId: string;
  readonly stageLine: string;
  readonly runtimeSnapshotId: string | null;
  readonly runtimeLockId: string | null;
  readonly threadId: string | null;
}

export function StoryWorkspaceDreamAgentRail({
  deckName,
  runId,
  stageLine,
  runtimeSnapshotId,
  runtimeLockId,
  threadId,
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
      </div>
    </section>
  );
}

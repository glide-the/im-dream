// [Input] Dream-only safe message view model and run context.
// [Output] A compact, accessible Agent-section status annotation.
// [Pos] Dream right rail (design_008 §5/§7); no generic Chat UI is mounted.

import type { StoryWorkspaceDreamAgentViewModel } from '../../../hooks/story-workspace';
import { StoryWorkspaceDreamDeckMetadata } from './StoryWorkspaceDreamDeckMetadata';

export interface StoryWorkspaceDreamAgentRailProps {
  readonly agent: StoryWorkspaceDreamAgentViewModel;
  readonly deckName: string;
  readonly runId: string;
  readonly stageLine: string;
  readonly runtimeSnapshotId: string | null;
  readonly runtimeLockId: string | null;
}

function storyWorkspaceDreamAgentStatus(agent: StoryWorkspaceDreamAgentViewModel): string {
  if (agent.pendingToolConfirmation) return '等待你确认一项操作';
  if (agent.isReconnecting) return '正在恢复实时消息…';
  if (agent.terminalOutcome === 'failed') return 'Dream Agent 本轮执行失败';
  if (agent.terminalOutcome === 'cancelled') return 'Dream Agent 本轮已取消';
  if (agent.snapshot?.lifecycle === 'streaming') return 'Dream Agent 正在输出';
  if (agent.snapshot?.sendBlockReason === 'waiting_confirmation') return '等待你修改并确认';
  if (agent.snapshot?.sendBlockReason === 'continuing') return 'Dream Agent 正在继续';
  if (agent.snapshot?.canSend) return 'Dream Agent 已完成本轮输出';
  return 'Dream Agent 正在准备内容';
}

export function StoryWorkspaceDreamAgentRail({
  agent, deckName, runId, stageLine, runtimeSnapshotId, runtimeLockId,
}: StoryWorkspaceDreamAgentRailProps) {
  return (
    <section className="story-workspace-dream-agent-rail" aria-label="Dream Agent 状态">
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
          <span>{storyWorkspaceDreamAgentStatus(agent)}</span>
        </span>
        <span className="story-workspace-dream-agent-rail__meta">{stageLine}</span>
      </div>
    </section>
  );
}

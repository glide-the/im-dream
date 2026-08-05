// [Input] Dream-only safe message view model and run context.
// [Output] A compact, accessible Agent-section status annotation.
// [Pos] Dream right rail (design_008 §5/§7); no generic Chat UI is mounted.

import type { StoryWorkspaceDreamAgentViewModel } from '../../../hooks/story-workspace';

export interface StoryWorkspaceDreamAgentRailProps {
  readonly agent: StoryWorkspaceDreamAgentViewModel;
  readonly deckName: string;
  readonly runId: string;
  readonly stageLine: string;
  readonly runtimeSnapshotId: string | null;
  readonly runtimeLockId: string | null;
}

function storyWorkspaceDreamAgentStatus(agent: StoryWorkspaceDreamAgentViewModel): string {
  if (agent.isReconnecting) return '正在恢复实时消息…';
  if (agent.snapshot?.lifecycle === 'streaming') return 'Dream Agent 正在输出';
  if (agent.snapshot?.sendBlockReason === 'waiting_confirmation') return '等待你修改并确认';
  if (agent.snapshot?.sendBlockReason === 'continuing') return 'Dream Agent 正在继续';
  if (agent.snapshot?.canSend) return 'Dream Agent 已完成本轮输出';
  return 'Dream Agent 正在准备内容';
}

export function StoryWorkspaceDreamAgentRail({
  agent, deckName, runId, stageLine, runtimeSnapshotId, runtimeLockId,
}: StoryWorkspaceDreamAgentRailProps) {
  const assistant = agent.snapshot?.messages.filter((message) => message.role === 'assistant').slice(-3) ?? [];
  const preview = agent.streamText || assistant.at(-1)?.text;
  return (
    <section className="story-workspace-dream-agent-rail" aria-label="Dream Agent 状态">
      <div className="story-workspace-dream-agent-rail__summary">
        <span className="story-workspace-dream-agent-rail__context">
          <span>Dream Agent · {deckName}</span>
        </span>
        <span className="story-workspace-dream-agent-rail__status">
          <span aria-hidden="true" className="story-workspace-dream-agent-rail__mark" />
          <span>{storyWorkspaceDreamAgentStatus(agent)}</span>
        </span>
        <span className="story-workspace-dream-agent-rail__preview">
          {preview || (agent.isLoading ? '正在读取 Dream Agent 消息…' : 'Dream Agent 的回复会显示在这里。')}
        </span>
        <span className="story-workspace-dream-agent-rail__meta">{stageLine}</span>
      </div>
      <details className="story-workspace-dream-agent-rail__details">
        <summary>技术详情</summary>
        <dl>
          <div><dt>完整 Run ID</dt><dd>{runId}</dd></div>
          <div><dt>runtime snapshot</dt><dd>{runtimeSnapshotId ?? '—'}</dd></div>
          <div><dt>runtime lock</dt><dd>{runtimeLockId ?? '—'}</dd></div>
        </dl>
      </details>
    </section>
  );
}

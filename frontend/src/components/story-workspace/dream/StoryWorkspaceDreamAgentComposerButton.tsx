/* eslint-disable react-refresh/only-export-components -- exports a deterministic composer state seam. */
// [Input] Dream Agent lifecycle and composer send availability.
// [Output] One shared send control with the Chat stop glyph as a non-actionable running marker.
// [Pos] Dream Agent Panel/Dialog composer action seam.

import type { StoryWorkspaceDreamAgentMessageSnapshot } from '../../../hooks/story-workspace';
import { IconStop } from '../../chat/Icons';

export interface StoryWorkspaceDreamAgentComposerStateInput {
  readonly isSending: boolean;
  readonly snapshot: Pick<
    StoryWorkspaceDreamAgentMessageSnapshot,
    'lifecycle' | 'sendBlockReason'
  > | null;
}

const STORY_WORKSPACE_DREAM_AGENT_RUNNING_BLOCK_REASONS = new Set([
  'generating',
  'confirming',
  'continuing',
  'busy',
]);

export function storyWorkspaceDreamAgentComposerState(
  agent: StoryWorkspaceDreamAgentComposerStateInput,
): 'idle' | 'running' {
  if (agent.isSending || agent.snapshot?.lifecycle === 'streaming') return 'running';
  return agent.snapshot?.sendBlockReason
    && STORY_WORKSPACE_DREAM_AGENT_RUNNING_BLOCK_REASONS.has(agent.snapshot.sendBlockReason)
    ? 'running'
    : 'idle';
}

export function StoryWorkspaceDreamAgentComposerButton({
  agent,
  canSend,
}: {
  readonly agent: StoryWorkspaceDreamAgentComposerStateInput;
  readonly canSend: boolean;
}) {
  const state = storyWorkspaceDreamAgentComposerState(agent);
  if (state === 'running') {
    return (
      <button
        aria-label="Dream Agent 正在运行"
        className="story-workspace-dream-agent-composer-button"
        data-state="running"
        disabled
        title="Dream Agent 正在运行"
        type="button"
      >
        <IconStop />
      </button>
    );
  }
  return (
    <button
      className="story-workspace-dream-agent-composer-button"
      data-state="idle"
      disabled={!canSend}
      type="submit"
    >发送</button>
  );
}

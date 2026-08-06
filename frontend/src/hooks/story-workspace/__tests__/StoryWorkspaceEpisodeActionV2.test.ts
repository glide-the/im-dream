// [Input] Server-owned OptionV2 projection and a selected opaque action ID.
// [Output] Strict parsing, action-specific confirmation inputs, and path-free POST body.
// [Pos] Multi-Episode action/confirmation Node seam (U7).

import { expect, test } from '@playwright/test';
import {
  storyWorkspaceParseEpisodeActionProjectionV2,
  storyWorkspaceEpisodeOptionCanonicalInputs,
  type StoryWorkspaceEpisodeArtifactSurface,
} from '../contracts';
import { storyWorkspaceContinueEpisodeAction } from '../useStoryWorkspaceEpisodeArtifacts';

const RUN_ID = `run_${'1'.repeat(32)}`;
const EP01_ID = '1'.repeat(32);
const REVISION = `sha256:${'a'.repeat(64)}`;
const ACTION_ID = `episode_action_${'b'.repeat(64)}`;
const PREVIEW_ID = `episode_action_${'c'.repeat(64)}`;

function option(
  actionId: string,
  availability: 'executable' | 'preview',
  recommended: boolean,
) {
  return {
    actionId,
    action: availability === 'executable' ? 'regenerate_storyboard' : 'generate_prompts',
    inputRevision: REVISION,
    targetEpisode: {
      opaqueEpisodeId: EP01_ID,
      candidateId: null,
      displayLabel: 'EP01',
      relation: 'current',
    },
    label: availability === 'executable'
      ? '基于最新剧本更新 EP01 详细分镜'
      : '生成 EP01 Prompt 包',
    description: '只使用当前服务端 revisions。',
    displayCommand: availability === 'executable'
      ? '/drama-storyboard (EP01)'
      : '/drama-prompt (EP01)',
    availability,
    isRecommended: recommended,
    canDispatch: availability === 'executable',
    disabledReason: availability === 'executable' ? null : '完成当前步骤后可用',
    canonicalInputs: [{
      sourceType: 'episode_artifact',
      artifact: 'script',
      owner: 'episode_artifact_manifest',
      label: 'EP01 剧本',
      availability: 'available',
      publicRevision: REVISION,
      revisionKind: 'content',
      requirement: 'required',
    }],
    consequences: ['Prompt 包', '完整产物审阅', '校验提交'],
    dispatchState: 'idle',
  };
}

function projectionPayload() {
  return {
    recommendedActionId: ACTION_ID,
    actionOptions: [
      option(ACTION_ID, 'executable', true),
      option(PREVIEW_ID, 'preview', false),
    ],
  };
}

function surface(): StoryWorkspaceEpisodeArtifactSurface {
  return {
    runId: RUN_ID,
    opaqueEpisodeId: EP01_ID,
    manifestRevision: REVISION,
    etag: REVISION,
    bindingAvailability: 'bound',
    bindingRecovery: { autoRepairAttempted: false, canDispatch: false, publicReason: null },
    artifacts: [],
    documents: [],
    narrative: null,
    auxiliary: null,
    workflow: null,
    actionProjection: storyWorkspaceParseEpisodeActionProjectionV2(projectionPayload()),
  };
}

test('strictly parses target-aware OptionV2 and action-specific confirmation inputs', () => {
  const projection = storyWorkspaceParseEpisodeActionProjectionV2(projectionPayload());
  const selected = projection.actionOptions[0];

  expect(selected.targetEpisode.displayLabel).toBe('EP01');
  expect(selected.inputRevision).toBe(REVISION);
  expect(storyWorkspaceEpisodeOptionCanonicalInputs(selected)).toEqual([{
    label: 'EP01 剧本',
    availability: 'available',
    revision: REVISION,
  }]);
});

test('posts only opaque action identity and rejects preview action before fetch', async () => {
  const calls: Array<Record<string, unknown>> = [];
  const fetchImpl = async (_input: RequestInfo | URL, init?: RequestInit) => {
    calls.push(JSON.parse(String(init?.body)) as Record<string, unknown>);
    return new Response(JSON.stringify({
      runId: RUN_ID,
      episodeId: EP01_ID,
      capability: 'regenerate_storyboard',
      messageId: 'dream-agent-message',
      accepted: true,
      replayed: false,
    }), { status: 202, headers: { 'Content-Type': 'application/json' } });
  };

  await storyWorkspaceContinueEpisodeAction(RUN_ID, surface(), {
    actionId: ACTION_ID,
    idempotencyKey: 'action-key',
    userGuidance: '保留克制氛围',
    fetchImpl,
  });

  expect(calls).toEqual([{
    actionId: ACTION_ID,
    idempotencyKey: 'action-key',
    userGuidance: '保留克制氛围',
  }]);
  expect(calls[0]).not.toHaveProperty('episodeId');
  expect(calls[0]).not.toHaveProperty('action');
  expect(calls[0]).not.toHaveProperty('displayCommand');

  await expect(storyWorkspaceContinueEpisodeAction(RUN_ID, surface(), {
    actionId: PREVIEW_ID,
    idempotencyKey: 'preview-key',
    fetchImpl,
  })).rejects.toThrow();
  expect(calls).toHaveLength(1);
});

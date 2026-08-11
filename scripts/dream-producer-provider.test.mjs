import assert from 'node:assert/strict';
import test from 'node:test';

import {
  buildFullReview,
  currentInstruction,
  instructionKind,
  PRODUCER_FILES,
  runIdFromText,
} from './dream-producer-provider.mjs';

import { createHash } from 'node:crypto';

test('selects the Dream user instruction when SDK appends a system message', () => {
  const runId = `run_${'1'.repeat(32)}`;
  const instruction = currentInstruction([
    {
      role: 'user',
      content: [
        { type: 'text', text: `<story_workspace_dream_context>${runId}</story_workspace_dream_context>` },
        { type: 'text', text: '你正在执行 Dream 工作空间生成流程。' },
      ],
    },
    {
      role: 'system',
      content: [{ type: 'text', text: 'Available agent types for the Agent tool' }],
    },
  ]);

  assert.equal(instructionKind(instruction), 'initial');
  assert.equal(runIdFromText(instruction), runId);
});

test('full-chain review pins the storyboard actually produced by initial Dream', () => {
  const revision = (content) => `sha256:${createHash('sha256').update(content).digest('hex')}`;
  const review = buildFullReview(PRODUCER_FILES.storyboardInitial);

  assert.match(review, new RegExp(`storyboard\\.yaml: ${revision(PRODUCER_FILES.storyboardInitial)}`));
  assert.doesNotMatch(review, new RegExp(`storyboard\\.yaml: ${revision(PRODUCER_FILES.storyboardFinal)}`));
});

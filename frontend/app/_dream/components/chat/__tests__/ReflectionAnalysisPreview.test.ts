// [Input] Representative Reflections prompts and ordinary large user messages.
// [Output] Contract tests for exact, post-anchor workflow classification.
// [Pos] Pure preview-recognition regression test; no browser or transport required.
// [Sync] 2026-10-14: cover three defaults, false positives, custom workflows and repeated anchors.

import { expect, test } from '@playwright/test';
import { parseReflectionAnalysisPreview } from '../reflectionAnalysisPreview';

const anchor = 'Complete this Reflections analysis in this turn.';

test.describe('parseReflectionAnalysisPreview', () => {
  test('recognizes each default workflow from the first H1 after the final anchor', () => {
    expect(parseReflectionAnalysisPreview(`${anchor}\n# Reflections — Recurring Themes (Echoes) Workflow\nbody`)).toBe('echoes');
    expect(parseReflectionAnalysisPreview(`${anchor}\r\n# Reflections — Character Traits Workflow\r\nbody`)).toBe('traits');
    expect(parseReflectionAnalysisPreview(`${anchor}\nintro\n# Reflections — Behavioral Patterns Workflow\nbody`)).toBe('patterns');
  });

  test('ignores matching text in diary or Notion context before the server anchor', () => {
    const text = [
      '# Reflections — Character Traits Workflow',
      'quoted from a source page',
      anchor,
      '# Custom Reflection Workflow',
    ].join('\n');
    expect(parseReflectionAnalysisPreview(text)).toBeNull();
  });

  test('uses the final anchor and does not classify custom or ordinary messages', () => {
    const repeated = [
      anchor,
      '# Reflections — Recurring Themes (Echoes) Workflow',
      anchor,
      '# Custom Reflection Workflow',
    ].join('\n');
    expect(parseReflectionAnalysisPreview(repeated)).toBeNull();
    expect(parseReflectionAnalysisPreview('# Reflections — Behavioral Patterns Workflow')).toBeNull();
    expect(parseReflectionAnalysisPreview(`${anchor}\n## Reflections — Behavioral Patterns Workflow`)).toBeNull();
    expect(parseReflectionAnalysisPreview(`${anchor}\n# Reflections - Behavioral Patterns Workflow`)).toBeNull();
    expect(parseReflectionAnalysisPreview(`${anchor}\nNo workflow heading follows.`)).toBeNull();
    expect(parseReflectionAnalysisPreview(`${anchor}\ntext\n# Reflections — Behavioral Patterns Workflow\n# later`)).toBe('patterns');
  });
});

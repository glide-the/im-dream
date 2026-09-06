// [Input] Representative Hook-published asset Markdown with nested YAML frontmatter.
// [Output] Regression proof that metadata and prose are separate presentation surfaces.
// [Pos] Story Workspace Execution asset-document view-model contract.

import { expect, test } from '@playwright/test';
import { storyWorkspaceBuildAssetDocumentViewModel } from '../assetDocumentViewModel';

test('separates nested asset metadata from Markdown body without losing fields', () => {
  const document = storyWorkspaceBuildAssetDocumentViewModel(`---
char_id: ext-01
char_name: 老板娘
appears_in: ["ep-01"]
appearance:
  height: "158cm"
  build: "微胖"
  default_outfit: "围裙 + 棉衣"
---

# 老板娘

阿青的舅妈。`);

  expect(document.body).toBe('# 老板娘\n\n阿青的舅妈。');
  expect(document.metadataFallback).toBeNull();
  expect(document.metadata).toEqual([
    { key: 'char_id', label: 'char_id', value: 'ext-01' },
    { key: 'char_name', label: 'char_name', value: '老板娘' },
    { key: 'appears_in', label: 'appears_in', value: 'ep-01' },
    { key: 'appearance.height', label: 'appearance / height', value: '158cm' },
    { key: 'appearance.build', label: 'appearance / build', value: '微胖' },
    {
      key: 'appearance.default_outfit',
      label: 'appearance / default_outfit',
      value: '围裙 + 棉衣',
    },
  ]);
});

test('keeps ordinary Markdown and an unclosed separator untouched', () => {
  const markdown = '---\n这是一条普通分隔线，没有闭合 frontmatter。';
  expect(storyWorkspaceBuildAssetDocumentViewModel(markdown)).toEqual({
    body: markdown,
    metadata: [],
    metadataFallback: null,
  });
});

test('falls back to compact source metadata when YAML cannot be parsed', () => {
  const document = storyWorkspaceBuildAssetDocumentViewModel('---\nbroken: [\n---\n# 正文');
  expect(document.body).toBe('# 正文');
  expect(document.metadata).toEqual([]);
  expect(document.metadataFallback).toBe('broken: [');
});

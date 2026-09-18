// [Input] Story Workspace layout stylesheet.
// [Output] Static responsive boundary for desktop sidebar widths and mobile bottom navigation.
// [Pos] Story Workspace layout CSS-only narrow-screen Node seam (U4 Red/Green).
// [Sync] 2026-09-18: replace compact mobile rail assertions with bottom navigation and More-sheet coverage.

import { expect, test } from '@playwright/test';
// @ts-expect-error Playwright Node seam reads source; browser app omits Node types.
import { readFileSync } from 'node:fs';

const CSS = readFileSync(new URL('../StoryWorkspaceLayout.css', import.meta.url), 'utf8');

function narrowLayoutCss(): string {
  const marker = '@media (max-width: 767px)';
  const start = CSS.indexOf(marker);
  expect(start).toBeGreaterThanOrEqual(0);
  return CSS.slice(start);
}

test('desktop and explicit collapsed sidebar widths remain canonical', () => {
  expect(CSS).toMatch(/\.story-workspace-layout__sidebar\s*{[^}]*flex:\s*0 0 240px;[^}]*width:\s*240px;[^}]*min-width:\s*240px;/s);
  expect(CSS).toMatch(/\[data-sidebar-state='collapsed'\] \.story-workspace-layout__sidebar\s*{[^}]*flex:\s*0 0 72px;[^}]*width:\s*72px;[^}]*min-width:\s*72px;/s);
  expect(CSS).toMatch(/\.story-workspace-layout__main\s*{[^}]*min-width:\s*0;[^}]*overflow-x:\s*hidden;[^}]*overflow-y:\s*auto;/s);
});

test('narrow workspace uses a fixed safe-area bottom navigation without a JS viewport owner', () => {
  const narrow = narrowLayoutCss();
  expect(narrow).toMatch(/\.story-workspace-layout__sidebar\s*{[^}]*position:\s*fixed;[^}]*inset:\s*auto 0 0;[^}]*width:\s*100%;/s);
  expect(narrow).toMatch(/\.story-workspace-layout \.story-workspace-sidebar__nav\s*{[^}]*grid-template-columns:\s*repeat\(4, minmax\(0, 1fr\)\);/s);
  expect(narrow).toContain('env(safe-area-inset-bottom, 0px)');
  expect(CSS).not.toContain('window.innerWidth');
  expect(CSS).not.toContain('matchMedia');
});

test('mobile navigation keeps primary labels and exposes secondary controls in the More sheet', () => {
  const narrow = narrowLayoutCss();
  for (const selector of [
    '.story-workspace-sidebar__brand-text',
    '.story-workspace-sidebar__theme-label',
    '.story-workspace-sidebar__settings-label',
    '.story-workspace-sidebar__user-details',
  ]) {
    expect(narrow).toContain(selector);
  }
  expect(narrow).toContain('clip-path: inset(50%)');
  expect(narrow).toMatch(/data-mobile-more-open='true'[\s\S]*\.story-workspace-sidebar__footer\s*{[^}]*display:\s*flex;/);
  expect(narrow).toMatch(/\.story-workspace-sidebar__legacy-nav\s*{[^}]*position:\s*fixed;[^}]*grid-template-columns:\s*repeat\(3, minmax\(0, 1fr\)\);/s);
  expect(narrow).toMatch(/\.story-workspace-sidebar__label,[\s\S]*\.story-workspace-sidebar--collapsed \.story-workspace-sidebar__label\s*{[^}]*display:\s*block;/);
});

test('narrow main consumes full width and reserves the bottom navigation height', () => {
  const narrow = narrowLayoutCss();
  expect(narrow).toMatch(/\.story-workspace-layout__main\s*{[^}]*width:\s*100%;[^}]*max-width:\s*100%;[^}]*min-width:\s*0;[^}]*overflow-x:\s*hidden;[^}]*padding-bottom:\s*calc\(4\.25rem \+ env\(safe-area-inset-bottom, 0px\)\);/s);
  expect(narrow).toMatch(/\.story-workspace-writing-split\s*{[^}]*left:\s*0;[^}]*bottom:\s*calc\(4\.25rem \+ env\(safe-area-inset-bottom, 0px\)\);/s);
});

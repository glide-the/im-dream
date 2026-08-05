// [Input] Story Workspace layout stylesheet.
// [Output] Static responsive boundary for a persistent compact navigation rail.
// [Pos] Story Workspace layout CSS-only narrow-screen Node seam (U4 Red/Green).

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
});

test('narrow workspace keeps a 72px navigation rail without a JS viewport owner', () => {
  const narrow = narrowLayoutCss();
  expect(narrow).toMatch(/\.story-workspace-layout__sidebar\s*{[^}]*flex:\s*0 0 72px;[^}]*width:\s*72px;[^}]*min-width:\s*72px;/s);
  expect(narrow).toMatch(/\.story-workspace-layout \.story-workspace-sidebar\s*{[^}]*width:\s*72px;[^}]*min-width:\s*72px;/s);
  expect(narrow).not.toContain('display: none; /* sidebar */');
  expect(CSS).not.toContain('window.innerWidth');
  expect(CSS).not.toContain('matchMedia');
});

test('compact rail hides copy and menus while preserving icon controls', () => {
  const narrow = narrowLayoutCss();
  for (const selector of [
    '.story-workspace-sidebar__brand-text',
    '.story-workspace-sidebar__label',
    '.story-workspace-sidebar__theme-label',
    '.story-workspace-sidebar__settings-label',
    '.story-workspace-sidebar__user-details',
  ]) {
    expect(narrow).toContain(selector);
  }
  expect(narrow).toContain('clip-path: inset(50%)');
  expect(narrow).toMatch(/\.story-workspace-sidebar__user-menu,[\s\S]*\.story-workspace-sidebar__user-scrim\s*{[^}]*display:\s*none;/);
  expect(narrow).toMatch(/\.story-workspace-sidebar__nav-button,[\s\S]*\.story-workspace-sidebar__settings-button\s*{[^}]*justify-content:\s*center;[^}]*padding:\s*10px 0;/);
  expect(narrow).toMatch(/\.story-workspace-sidebar__user-trigger\s*{[^}]*justify-content:\s*center;/);
  expect(narrow).not.toMatch(/\.story-workspace-sidebar__icon\s*{[^}]*display:\s*none/);
  expect(narrow).not.toMatch(/\.story-workspace-sidebar__toggle\s*{[^}]*display:\s*none/);
});

test('narrow main consumes the remaining width without horizontal overflow', () => {
  const narrow = narrowLayoutCss();
  expect(narrow).toMatch(/\.story-workspace-layout__main\s*{[^}]*width:\s*calc\(100% - 72px\);[^}]*max-width:\s*calc\(100% - 72px\);[^}]*min-width:\s*0;[^}]*overflow-x:\s*hidden;/s);
});

// [Input] Task 3 Dream frontend modules and their public runtime exports.
// [Output] DEC-004 namespace guard for functions, components, and constants.
// [Pos] Story Workspace public-symbol naming contract test seam (Task 3 F8).

import { expect, test } from '@playwright/test';
import * as storyWorkspaceDreamState from '../dreamState';
import * as storyWorkspaceSurfaceLink from '../surfaceLink';
import * as storyWorkspaceDreamFiles from '../../../hooks/story-workspace/useStoryWorkspaceDreamFiles';
import * as storyWorkspaceDreamConfirmation from '../../../hooks/story-workspace/useStoryWorkspaceDreamConfirmation';
import * as storyWorkspaceDreamViewModel from '../../../pages/story-workspace/dreamViewModel';
import * as storyWorkspaceExecutionViewModel from '../../../pages/story-workspace/executionViewModel';

const STORY_WORKSPACE_TASK3_MODULES = {
  storyWorkspaceDreamState,
  storyWorkspaceSurfaceLink,
  storyWorkspaceDreamFiles,
  storyWorkspaceDreamConfirmation,
  storyWorkspaceDreamViewModel,
  storyWorkspaceExecutionViewModel,
};

test('Task 3 public runtime exports retain the Story Workspace namespace', () => {
  for (const [moduleName, exports] of Object.entries(STORY_WORKSPACE_TASK3_MODULES)) {
    for (const [exportName, value] of Object.entries(exports)) {
      if (typeof value === 'function') {
        // React custom hooks retain the framework-required `use` prefix while
        // still carrying the full StoryWorkspace namespace.
        expect(exportName, `${moduleName}.${exportName}`).toMatch(
          /^(?:storyWorkspace|StoryWorkspace|useStoryWorkspace)/,
        );
        continue;
      }
      expect(exportName, `${moduleName}.${exportName}`).toMatch(/^STORY_WORKSPACE/);
    }
  }
});

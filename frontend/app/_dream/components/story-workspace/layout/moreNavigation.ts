// [Input] Existing Writing, Timeline, Reflections, theme and Settings entry points.
// [Output] The same ordered, single-level More navigation for narrow Web and native.
// [Pos] Presentation metadata; route, theme, authentication and business state stay with their owners.
// [Sync] 2026-10-29: record the user-specified five-item narrow navigation.
import {STORY_WORKSPACE_PATHS} from '../../../router/storyWorkspacePath';
export const MORE_NAVIGATION_ITEMS=[
  {id:'writing',labelKey:'nav.writing',path:STORY_WORKSPACE_PATHS.writing},
  {id:'timeline',labelKey:'nav.timeline',path:STORY_WORKSPACE_PATHS.timeline},
  {id:'analysis',labelKey:'nav.analysis',path:STORY_WORKSPACE_PATHS.analysis},
  {id:'theme',labelKey:'nav.theme'},
  {id:'settings',labelKey:'nav.settings',path:STORY_WORKSPACE_PATHS.settings},
] as const;
export type MoreNavigationDestination=Exclude<(typeof MORE_NAVIGATION_ITEMS)[number]['id'],'theme'>;

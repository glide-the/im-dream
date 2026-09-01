// [Input] Story Workspace layout components owned by this folder.
// [Output] Public layout exports for router and app-shell consumers.
// [Pos] Story Workspace layout module boundary.
// [Sync] 2026-08-31: export the resizable Writing canvas and Thread Chat split pane.

export {
  StoryWorkspaceLayout,
  type StoryWorkspaceLayoutProps,
} from './StoryWorkspaceLayout';
export {
  StoryWorkspaceReviewPanel,
  type StoryWorkspaceReviewPanelProps,
} from './StoryWorkspaceReviewPanel';
export {
  StoryWorkspaceReviewDetail,
  type StoryWorkspaceReviewDetailProps,
  type StoryWorkspaceReviewSelection,
} from './StoryWorkspaceReviewDetail';
export {
  StoryWorkspaceToolbar,
  type StoryWorkspaceSortOption,
  type StoryWorkspaceToolbarProps,
} from './StoryWorkspaceToolbar';
export {
  StoryWorkspaceBatchReviewToolbar,
  type StoryWorkspaceBatchReviewToolbarProps,
} from './StoryWorkspaceBatchReviewToolbar';
export {
  WritingWorkspaceSplitPane,
  type WritingWorkspaceSplitPaneProps,
} from './WritingWorkspaceSplitPane';

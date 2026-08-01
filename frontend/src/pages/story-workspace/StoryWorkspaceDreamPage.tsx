// [Input] Reusable Story Workspace dashboard/page shell.
// [Output] Render the canonical Dream route skeleton without Dashboard business content.
// [Pos] Canonical /story-workspace/dream page.
import { StoryWorkspaceDashboardPage } from './StoryWorkspaceDashboardPage';

export function StoryWorkspaceDreamPage() {
  return (
    <StoryWorkspaceDashboardPage
      description="这里是 Story Workspace 的 canonical 入口。工作流上下文、审阅 Gate 与业务内容将在各自任务中接入。"
      eyebrow="Story Workspace · Dream"
      title="Dream"
    />
  );
}

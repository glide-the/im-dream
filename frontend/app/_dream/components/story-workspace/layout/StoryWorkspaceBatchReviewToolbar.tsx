import '../table/StoryWorkspaceTable.css';

export interface StoryWorkspaceBatchReviewToolbarProps {
  selectedCount: number;
  onCancel: () => void;
  onConfirm: () => void;
  onReject: () => void;
}

export function StoryWorkspaceBatchReviewToolbar({
  selectedCount,
  onCancel,
  onConfirm,
  onReject,
}: StoryWorkspaceBatchReviewToolbarProps) {
  return (
    <div aria-label="批量审阅操作" className="story-workspace-batch-toolbar">
      <span className="story-workspace-batch-toolbar__count">已选择 {selectedCount} 项待审阅内容</span>
      <button onClick={onConfirm} type="button">批量确认</button>
      <button onClick={onReject} type="button">批量驳回</button>
      <button onClick={onCancel} type="button">取消</button>
    </div>
  );
}

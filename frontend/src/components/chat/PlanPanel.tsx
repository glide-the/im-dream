// [Input] useThreadPlan store（planMode / exists / content / truncated / updatedAt）与
//         hydrateThreadPlan 全量拉取。
// [Output] ChatView 顶部右侧浮动控制栏内的「计划」按钮 + 锚定弹层：默认不渲染，仅当
//          planMode 为 planning/exited 或 exists===true 时出现；点击切换弹层，弹层内展示
//          Markdown 计划内容、planMode 徽标、updatedAt 相对时间、截断时的「加载完整」入口；
//          点击外部 / Esc 收起，threadId 切换时收起并重置未读指示。
// [Pos] claude-plan button+popover component in frontend/src/components/chat
// [Sync] 2026-07-20: 初版 — 依据 docs/design/claude-agent/claude-plan.md §5.6 实现；
//                    复用 CollapsibleSection 与 AssistMessagePart 的 ReactMarkdown 渲染链。
// [Sync] 2026-07-20: 交互方案变更 — 取消常驻面板，改为浮动控制栏内的「计划」按钮 +
//                    锚定弹层（PlanButton + PlanPopoverContent）；按钮仅在有计划时渲染，
//                    弹层直接受控渲染（不再嵌套 CollapsibleSection 折叠头）。
// [Sync] 2026-07-20: Markdown 渲染切换到共享 ChatMarkdown，计划内容中的 ```mermaid 块
//                    与会话消息一样渲染为 SVG 图表。

import { useEffect, useRef, useState } from 'react';
import { IconChecklist } from './Icons';
import ChatMarkdown from './ChatMarkdown';
import { hydrateThreadPlan, useThreadPlan, type ThreadPlanMode, type ThreadPlanState } from '../../hooks/useThreadPlan';

interface PlanButtonProps {
  threadId: string;
}

const PLAN_MODE_BADGE: Record<Exclude<ThreadPlanMode, 'none'>, { label: string; color: string }> = {
  planning: { label: '规划中', color: '#f9a875' },
  exited: { label: '已退出规划', color: '#52c77e' },
};

/** Relative timestamp label consistent with ChatView 的历史时间分组风格（zh-CN）。 */
function formatRelativeTime(value: string): string {
  const date = new Date(value.includes('T') ? value : value.replace(' ', 'T'));
  if (Number.isNaN(date.getTime())) return '';
  const diffMs = Date.now() - date.getTime();
  if (diffMs < 0) return '刚刚';
  const minutes = Math.floor(diffMs / 60000);
  if (minutes < 1) return '刚刚';
  if (minutes < 60) return `${minutes} 分钟前`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} 小时前`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days} 天前`;
  return new Intl.DateTimeFormat('zh-CN', { month: 'numeric', day: 'numeric' }).format(date);
}

function PlanModeBadge({ planMode }: { planMode: ThreadPlanMode }) {
  if (planMode === 'none') return null;
  const badge = PLAN_MODE_BADGE[planMode];
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '0.3rem',
        height: '1.4rem',
        padding: '0 0.5rem',
        borderRadius: '0.5rem',
        border: `1px solid ${badge.color}55`,
        background: `${badge.color}18`,
        color: badge.color,
        fontSize: '0.72rem',
        fontWeight: 600,
        whiteSpace: 'nowrap',
      }}
    >
      <IconChecklist style={{ width: '0.75rem', height: '0.75rem' }} />
      {badge.label}
    </span>
  );
}

/** 弹层正文：沿用原常驻 PlanPanel 的全部内容能力；exists:false 时不渲染内容区。 */
function PlanPopoverContent({ threadId, plan }: { threadId: string; plan: ThreadPlanState }) {
  const [isLoadingFull, setIsLoadingFull] = useState(false);

  if (!plan.exists) {
    // 已进入/退出规划态但尚未捕获计划文件（plan-mode-changed 先于 plan-updated）。
    return (
      <div style={{ fontSize: '0.82rem', color: 'var(--color-text-muted)' }}>
        {plan.planMode === 'planning' ? '规划已触发，等待计划内容…' : '未找到计划内容。'}
      </div>
    );
  }

  const handleLoadFull = () => {
    if (isLoadingFull) return;
    setIsLoadingFull(true);
    void hydrateThreadPlan(threadId).finally(() => setIsLoadingFull(false));
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
      {plan.fileName ? (
        <div style={{ fontSize: '0.72rem', color: 'var(--color-text-muted)', fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace' }}>
          {plan.fileName}
        </div>
      ) : null}
      <div style={{ maxHeight: '16rem', overflowY: 'auto', color: 'var(--color-text-primary)', fontSize: '0.9rem', lineHeight: 1.7 }}>
        <div className="prose prose-chat">
          <ChatMarkdown text={plan.content ?? ''} />
        </div>
      </div>
      {plan.truncated ? (
        <button
          type="button"
          onClick={handleLoadFull}
          disabled={isLoadingFull}
          style={{
            alignSelf: 'flex-start',
            border: '1px solid var(--color-border-paper)',
            borderRadius: '0.55rem',
            background: 'var(--color-bg-surface)',
            color: 'var(--color-action-link)',
            cursor: isLoadingFull ? 'not-allowed' : 'pointer',
            fontSize: '0.78rem',
            padding: '0.3rem 0.65rem',
            opacity: isLoadingFull ? 0.6 : 1,
          }}
        >
          {isLoadingFull ? '加载中…' : '内容已截断，点击加载完整'}
        </button>
      ) : null}
    </div>
  );
}

export default function PlanButton({ threadId }: PlanButtonProps) {
  const plan = useThreadPlan(threadId);
  const [open, setOpen] = useState(false);
  const [seenUpdatedAt, setSeenUpdatedAt] = useState<string | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);

  // 面板打开状态（与未读指示）随 threadId 切换而重置。
  useEffect(() => {
    setOpen(false);
    setSeenUpdatedAt(null);
  }, [threadId]);

  // 点击弹层外部或按 Esc 收起。
  useEffect(() => {
    if (!open) return;
    const handlePointerDown = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handlePointerDown);
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('mousedown', handlePointerDown);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [open]);

  // 可见性规则：仅当计划被触发（planning/exited）或计划文件存在时渲染按钮。
  const visible = plan.exists || plan.planMode !== 'none';
  if (!visible) {
    return null;
  }

  const hasUnseenUpdate = !open && !!plan.updatedAt && plan.updatedAt !== seenUpdatedAt;

  const handleToggle = () => {
    setOpen((value) => {
      const next = !value;
      if (next) {
        // 打开即视为已读当前版本。
        setSeenUpdatedAt(plan.updatedAt);
      }
      return next;
    });
  };

  const updatedLabel = plan.updatedAt ? formatRelativeTime(plan.updatedAt) : '';

  return (
    <div ref={containerRef} style={{ position: 'relative' }}>
      <button
        type="button"
        onClick={handleToggle}
        style={{
          height: '2rem',
          border: '1px solid transparent',
          borderRadius: '0.55rem',
          background: open ? 'var(--color-bg-surface)' : 'transparent',
          color: open ? 'var(--color-text-primary)' : 'var(--color-text-secondary)',
          cursor: 'pointer',
          display: 'inline-flex',
          alignItems: 'center',
          gap: '0.35rem',
          padding: '0 0.55rem',
          fontSize: '0.82rem',
          transition: 'background 0.14s ease, color 0.14s ease',
          position: 'relative',
        }}
        title="计划"
        aria-expanded={open}
        onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--color-bg-surface)'; e.currentTarget.style.color = 'var(--color-text-primary)'; }}
        onMouseLeave={(e) => { if (!open) { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--color-text-secondary)'; } }}
      >
        <IconChecklist style={{ width: '0.95rem', height: '0.95rem' }} />
        <span>计划</span>
        {hasUnseenUpdate ? (
          <span
            aria-hidden="true"
            style={{
              position: 'absolute',
              top: '0.28rem',
              right: '0.28rem',
              width: '0.4rem',
              height: '0.4rem',
              borderRadius: '50%',
              background: '#f9a875',
            }}
          />
        ) : null}
      </button>

      {open ? (
        <div
          style={{
            position: 'absolute',
            top: '2.4rem',
            right: 0,
            zIndex: 20,
            width: 'min(26rem, calc(100vw - 1.5rem))',
            padding: '0.75rem 0.85rem',
            border: '1px solid var(--color-border-paper)',
            borderRadius: '0.85rem',
            background: 'var(--color-bg-surface-solid)',
            boxShadow: '0 8px 24px var(--color-shadow-medium)',
            display: 'flex',
            flexDirection: 'column',
            gap: '0.6rem',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.75rem' }}>
            <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--color-text-primary)' }}>计划</span>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <PlanModeBadge planMode={plan.planMode} />
              {updatedLabel ? (
                <span style={{ fontSize: '0.72rem', color: 'var(--color-text-muted)', whiteSpace: 'nowrap' }}>
                  {updatedLabel}
                </span>
              ) : null}
            </div>
          </div>
          <PlanPopoverContent threadId={threadId} plan={plan} />
        </div>
      ) : null}
    </div>
  );
}

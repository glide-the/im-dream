// [Input] useThreadPlan store（planMode / exists / content / truncated / updatedAt）、
//         useThreadTodos store（source / exists / todos / truncated / updatedAt）与
//         hydrateThreadPlan / hydrateThreadTodos 全量拉取。
//         scheduledTaskApi 的当前 Thread 定时任务投影与 ChatView settled-turn refresh key。
// [Output] ChatView 顶部右侧的任务活动按钮与 Todo-style 卡片组：定时任务、独立任务会话、子智能体、
//          计划和待办各占一张卡片，点击外部 / Esc 收起，threadId 切换时收起并重置未读指示。
// [Pos] Current-Thread activity button+popover component in frontend/app/_dream/components/chat.
// [Sync] 2026-10-07: include scheduled-only activity, cancellable Thread reads, retries and settled-turn refresh.
// [Sync] 2026-09-28: keep PluginReceiptBadge Environment info unchanged and host task sessions/subagents here.
// [Sync] 2026-07-20: 初版 — 依据 docs/design/claude-agent/claude-plan.md §5.6 实现；
//                    复用 CollapsibleSection 与 AssistMessagePart 的 ReactMarkdown 渲染链。
// [Sync] 2026-07-20: 交互方案变更 — 取消常驻面板，改为浮动控制栏内的「计划」按钮 +
//                    锚定弹层（PlanButton + PlanPopoverContent）；按钮仅在有计划时渲染，
//                    弹层直接受控渲染（不再嵌套 CollapsibleSection 折叠头）。
// [Sync] 2026-07-20: Markdown 渲染切换到共享 ChatMarkdown，计划内容中的 ```mermaid 块
//                    与会话消息一样渲染为 SVG 图表。
// [Sync] 2026-07-20: claude-todo §5.6 — 按钮升级为「计划与待办」双区弹层：图标切换为
//                    IconPlanTasks，title 改为「计划与待办」，可见性扩展为
//                    plan.exists || planMode!=='none' || todos.exists；弹层在计划区下方
//                    新增「待办」分区（序号徽标 + 三态徽章 + content/active_form + owner +
//                    ⛔ blocked_by），未读红点与 plan 共用（任一区更新即点亮）。
// [Sync] 2026-07-20: 按钮形态修订 — 去除常驻文字「计划」，仅显示 IconList 列表图标；
//                    「计划与待办」文字改为悬浮 tooltip（hover 且弹层未打开时显示），
//                    aria-label 保留可访问性语义。
// [Sync] 2026-07-20: 弹层样式修订（参照进度卡片样式图）— 单卡片+分隔线改为「计划」「待办」
//                    双卡片堆叠（POPOVER_CARD_STYLE 共享样式，标题加粗 0.95rem）；待办区
//                    去除 #id 与文字徽章，改为圆点状态图标（completed 实心+白勾+删除线、
//                    in_progress 描边+中心点、pending 空心圆），默认展示前 3 条，
//                    超出经「展开 N 个 / 收起」折叠控制（TODO_VISIBLE_COUNT=3）。
// [Sync] 2026-07-20: i18n — plan/todo popover copy, plan-mode badges, and the relative-time
//                    helper resolve through the chat.planPanel namespace (en + zh);
//                    formatRelativeTime now takes t() and formats via getDateLocale.
// [Sync] 2026-07-26: harden 待办区 render against payload-shape drift (2026-07-26
//                    React warning investigation): TodoListItem tolerates
//                    missing content/active_form/blocked_by fields and the list
//                    key falls back to the index when todo.id is absent.
// [Sync] 2026-08-22: bind plan Markdown workspace:// references to the panel Thread.

import { useCallback, useEffect, useId, useRef, useState, type CSSProperties } from 'react';
import { useTranslation } from 'react-i18next';
import type { TFunction } from 'i18next';
import { IconChevronDown, IconChevronUp, IconList, IconPlanTasks } from './Icons';
import ChatMarkdown from './ChatMarkdown';
import { hydrateThreadPlan, useThreadPlan, type ThreadPlanMode, type ThreadPlanState } from '../../hooks/useThreadPlan';
import { useThreadTodos, type ThreadTodoItem, type ThreadTodoState, type ThreadTodoStatus } from '../../hooks/useThreadTodos';
import { getDateLocale } from '../../i18n';
import TaskActivityContent from './TaskActivityContent';
import { fetchTaskSessionLinks } from './taskSessionLinks';
import { hydrateThreadSubagents, useThreadSubagents } from '../../hooks/useThreadSubagents';
import { getThreadScheduledTasks, type ScheduledTaskThreadSnapshot } from '../../api/scheduledTaskApi';
import type { ScheduledTaskMarkerSnapshot } from './scheduledTaskMarkerModel';

interface PlanButtonProps {
  threadId: string;
  subagentSidebarOpen: boolean;
  onToggleSubagents: () => void;
  onNavigateThread: (threadId: string) => void;
  onOpenScheduledTask?: (task: ScheduledTaskMarkerSnapshot) => void;
  scheduledRefreshKey?: number;
}

const PLAN_MODE_BADGE: Record<Exclude<ThreadPlanMode, 'none'>, { labelKey: string; color: string }> = {
  planning: { labelKey: 'chat.planPanel.planning', color: '#f9a875' },
  exited: { labelKey: 'chat.planPanel.exited', color: '#52c77e' },
};

const ACTIVITY_REFRESH_INTERVAL_MS = 8000;

/** 弹层双卡片（计划 / 待办）共享的卡片样式：圆角纸面 + 细边 + 柔和投影。 */
const POPOVER_CARD_STYLE: CSSProperties = {
  border: '1px solid var(--color-border-paper)',
  borderRadius: '1rem',
  background: 'var(--color-bg-surface-solid)',
  boxShadow: '0 8px 24px var(--color-shadow-medium)',
  padding: '0.85rem 1rem',
  display: 'flex',
  flexDirection: 'column',
  gap: '0.6rem',
};

/** Relative timestamp label consistent with ChatView 的历史时间分组风格（i18n-aware）。 */
function formatRelativeTime(value: string, t: TFunction, language?: string): string {
  const date = new Date(value.includes('T') ? value : value.replace(' ', 'T'));
  if (Number.isNaN(date.getTime())) return '';
  const diffMs = Date.now() - date.getTime();
  if (diffMs < 0) return t('chat.planPanel.justNow');
  const minutes = Math.floor(diffMs / 60000);
  if (minutes < 1) return t('chat.planPanel.justNow');
  if (minutes < 60) return t('chat.planPanel.minutesAgo', { count: minutes });
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return t('chat.planPanel.hoursAgo', { count: hours });
  const days = Math.floor(hours / 24);
  if (days < 7) return t('chat.planPanel.daysAgo', { count: days });
  return new Intl.DateTimeFormat(getDateLocale(language), { month: 'numeric', day: 'numeric' }).format(date);
}

function PlanModeBadge({ planMode }: { planMode: ThreadPlanMode }) {
  const { t } = useTranslation();
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
      <IconPlanTasks style={{ width: '0.75rem', height: '0.75rem' }} />
      {t(badge.labelKey)}
    </span>
  );
}

/** 弹层正文：沿用原常驻 PlanPanel 的全部内容能力；exists:false 时不渲染内容区。 */
function PlanPopoverContent({ threadId, plan }: { threadId: string; plan: ThreadPlanState }) {
  const { t } = useTranslation();
  const [isLoadingFull, setIsLoadingFull] = useState(false);

  if (!plan.exists) {
    // 已进入/退出规划态但尚未捕获计划文件（plan-mode-changed 先于 plan-updated）。
    return (
      <div style={{ fontSize: '0.82rem', color: 'var(--color-text-muted)' }}>
        {plan.planMode === 'planning' ? t('chat.planPanel.waitingContent') : t('chat.planPanel.noContent')}
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
          <ChatMarkdown text={plan.content ?? ''} workspaceSessionId={threadId} />
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
          {isLoadingFull ? t('chat.planPanel.loading') : t('chat.planPanel.loadFull')}
        </button>
      ) : null}
    </div>
  );
}

// ---------------------------------------------------------------------------
// 待办区（claude-todo §5.6）：参照「进度卡片」样式 —— 圆点状态图标 + 完成删除线，
// 默认展示前 3 条，其余经「展开 N 个」折叠控制显隐。
// ---------------------------------------------------------------------------

/** 三态圆点图标：completed=实心深色+白勾，in_progress=描边+中心点，pending=空心圆。 */
function TodoStatusIcon({ status }: { status: ThreadTodoStatus }) {
  if (status === 'completed') {
    return (
      <svg viewBox="0 0 24 24" style={{ width: '1.05rem', height: '1.05rem', flexShrink: 0 }} aria-hidden="true">
        <circle cx="12" cy="12" r="9" fill="var(--color-text-primary)" />
        <polyline points="8.5 12.5 11 15 15.5 9.5" fill="none" stroke="var(--color-bg-surface-solid)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    );
  }
  if (status === 'in_progress') {
    return (
      <svg viewBox="0 0 24 24" style={{ width: '1.05rem', height: '1.05rem', flexShrink: 0 }} aria-hidden="true">
        <circle cx="12" cy="12" r="8.5" fill="none" stroke="#6ea8fe" strokeWidth="2" />
        <circle cx="12" cy="12" r="3.5" fill="#6ea8fe" />
      </svg>
    );
  }
  return (
    <svg viewBox="0 0 24 24" style={{ width: '1.05rem', height: '1.05rem', flexShrink: 0 }} aria-hidden="true">
      <circle cx="12" cy="12" r="8.5" fill="none" stroke="var(--color-text-muted)" strokeWidth="2" />
    </svg>
  );
}

function TodoListItem({ todo }: { todo: ThreadTodoItem }) {
  // Defensive against payload-shape drift (raw SSE/REST items): the v1/v2
  // backend always sends these fields, but a malformed item must never
  // crash the popover render (2026-07-26 React warning investigation).
  const blockedBy = Array.isArray(todo.blocked_by) ? todo.blocked_by : [];
  const content = typeof todo.content === 'string' ? todo.content : '';
  const activeForm = typeof todo.active_form === 'string' ? todo.active_form : null;
  // in_progress 时优先展示 active_form（进行态描述），其余状态展示 content。
  const text = todo.status === 'in_progress' && activeForm ? activeForm : content;
  return (
    <li
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '0.6rem',
        fontSize: '0.85rem',
        lineHeight: 1.55,
        color: 'var(--color-text-primary)',
      }}
    >
      <TodoStatusIcon status={todo.status} />
      <span style={{ flex: 1, minWidth: 0, overflowWrap: 'anywhere' }}>
        <span style={todo.status === 'completed' ? { textDecoration: 'line-through', color: 'var(--color-text-muted)' } : undefined}>
          {text}
        </span>
        {todo.owner ? (
          <span style={{ marginLeft: '0.4rem', fontSize: '0.72rem', color: 'var(--color-text-muted)' }}>
            @{todo.owner}
          </span>
        ) : null}
        {blockedBy.length > 0 ? (
          <span style={{ marginLeft: '0.4rem', fontSize: '0.72rem', color: 'var(--color-text-muted)', whiteSpace: 'nowrap' }}>
            ⛔ {blockedBy.map((blocker) => `#${blocker}`).join(' ')}
          </span>
        ) : null}
      </span>
    </li>
  );
}

/** 默认可见条数；超出部分折叠为「展开 N 个」。 */
const TODO_VISIBLE_COUNT = 3;

/** 弹层「待办」分区：exists:false 时显示「暂无待办」占位。 */
function TodoPopoverContent({ todos }: { todos: ThreadTodoState }) {
  const { t } = useTranslation();
  const [expanded, setExpanded] = useState(false);

  if (!todos.exists) {
    return (
      <div style={{ fontSize: '0.82rem', color: 'var(--color-text-muted)' }}>
        {t('chat.planPanel.noTodos')}
      </div>
    );
  }

  const hiddenCount = todos.todos.length - TODO_VISIBLE_COUNT;
  const visibleTodos = expanded ? todos.todos : todos.todos.slice(0, TODO_VISIBLE_COUNT);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
      <ul
        style={{
          listStyle: 'none',
          margin: 0,
          padding: 0,
          display: 'flex',
          flexDirection: 'column',
          gap: '0.55rem',
          maxHeight: expanded ? '12rem' : undefined,
          overflowY: expanded ? 'auto' : undefined,
        }}
      >
        {visibleTodos.map((todo, index) => (
          // Fallback key guards the React unique-key warning if an item ever
          // arrives without an id (payload-shape drift).
          <TodoListItem key={todo.id ?? `todo-${index}`} todo={todo} />
        ))}
      </ul>
      {hiddenCount > 0 ? (
        <button
          type="button"
          onClick={() => setExpanded((value) => !value)}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '0.4rem',
            alignSelf: 'flex-start',
            border: 'none',
            background: 'transparent',
            padding: 0,
            cursor: 'pointer',
            color: 'var(--color-text-muted)',
            fontSize: '0.8rem',
          }}
        >
          {expanded ? (
            <><IconChevronUp style={{ width: '0.85rem', height: '0.85rem' }} /> {t('chat.planPanel.collapse')}</>
          ) : (
            <><IconChevronDown style={{ width: '0.85rem', height: '0.85rem' }} /> {t('chat.planPanel.expandMore', { count: hiddenCount })}</>
          )}
        </button>
      ) : null}
    </div>
  );
}

export default function PlanButton({ threadId, subagentSidebarOpen, onToggleSubagents, onNavigateThread,
  onOpenScheduledTask, scheduledRefreshKey = 0 }: PlanButtonProps) {
  const { t, i18n } = useTranslation();
  const panelId = useId();
  const plan = useThreadPlan(threadId);
  const todos = useThreadTodos(threadId);
  const subagents = useThreadSubagents(threadId);
  const [hasTaskSessions, setHasTaskSessions] = useState(false);
  const [scheduledActivity, setScheduledActivity] = useState<{
    threadId: string; snapshot: ScheduledTaskThreadSnapshot | null; loading: boolean; failed: boolean;
  }>({ threadId, snapshot: null, loading: true, failed: false });
  const scheduledRequestRef = useRef<{ generation: number; controller: AbortController | null }>({ generation: 0, controller: null });
  const refreshScheduledActivity = useCallback(async () => {
    scheduledRequestRef.current.controller?.abort();
    const controller = new AbortController();
    const generation = ++scheduledRequestRef.current.generation;
    scheduledRequestRef.current.controller = controller;
    setScheduledActivity((current) => ({ threadId,
      snapshot: current.threadId === threadId ? current.snapshot : null, loading: true, failed: false }));
    try {
      const snapshot = await getThreadScheduledTasks(threadId, { signal: controller.signal });
      if (generation === scheduledRequestRef.current.generation && !controller.signal.aborted) {
        setScheduledActivity({ threadId, snapshot, loading: false, failed: false });
      }
    } catch {
      if (generation === scheduledRequestRef.current.generation && !controller.signal.aborted) {
        setScheduledActivity((current) => ({ ...current, loading: false, failed: true }));
      }
    }
  }, [threadId]);
  const scheduledSnapshot = scheduledActivity.threadId === threadId ? scheduledActivity.snapshot : null;
  const scheduledFailed = scheduledActivity.threadId === threadId && scheduledActivity.failed;
  const scheduledLoading = scheduledActivity.threadId !== threadId || scheduledActivity.loading;
  const [open, setOpen] = useState(false);
  // 按钮 hover 态：驱动「计划与待办」悬浮 tooltip（弹层打开时不显示）。
  const [hovered, setHovered] = useState(false);
  // 计划区与待办区各自的已读水位；任一区有更新即点亮未读红点（claude-todo §5.6）。
  const [seenUpdatedAt, setSeenUpdatedAt] = useState<{ plan: string | null; todos: string | null }>({ plan: null, todos: null });
  const containerRef = useRef<HTMLDivElement | null>(null);

  // 面板打开状态（与未读指示）随 threadId 切换而重置。
  useEffect(() => {
    setOpen(false);
    setSeenUpdatedAt({ plan: null, todos: null });
  }, [threadId]);

  useEffect(() => {
    const scheduledRequest = scheduledRequestRef.current;
    void refreshScheduledActivity();
    const refreshVisible = () => { if (document.visibilityState === 'visible') void refreshScheduledActivity(); };
    const timer = window.setInterval(refreshVisible, ACTIVITY_REFRESH_INTERVAL_MS);
    document.addEventListener('visibilitychange', refreshVisible);
    return () => {
      window.clearInterval(timer);
      document.removeEventListener('visibilitychange', refreshVisible);
      scheduledRequest.controller?.abort();
      scheduledRequest.generation += 1;
    };
  }, [refreshScheduledActivity, scheduledRefreshKey]);

  useEffect(() => {
    let cancelled = false;
    setHasTaskSessions(false);
    const refreshActivity = async () => {
      const [links] = await Promise.allSettled([
        fetchTaskSessionLinks(threadId),
        hydrateThreadSubagents(threadId),
      ]);
      if (cancelled) return;
      if (links.status === 'fulfilled') setHasTaskSessions(links.value.created.length > 0);
    };
    void refreshActivity();
    const timer = window.setInterval(() => {
      if (document.visibilityState === 'visible') void refreshActivity();
    }, ACTIVITY_REFRESH_INTERVAL_MS);
    const handleVisibility = () => {
      if (document.visibilityState === 'visible') void refreshActivity();
    };
    document.addEventListener('visibilitychange', handleVisibility);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
      document.removeEventListener('visibilitychange', handleVisibility);
    };
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

  const hasPlan = plan.exists || plan.planMode !== 'none';
  const hasTodos = todos.exists;
  const hasScheduledTasks = Boolean(scheduledSnapshot?.source || scheduledSnapshot?.created.length);
  const visible = hasTaskSessions || subagents.exists || hasPlan || hasTodos || hasScheduledTasks || scheduledFailed;
  if (!visible) return null;

  const hasUnseenUpdate =
    !open &&
    ((!!plan.updatedAt && plan.updatedAt !== seenUpdatedAt.plan) ||
      (!!todos.updatedAt && todos.updatedAt !== seenUpdatedAt.todos));

  const handleToggle = () => {
    if (!open) {
      setSeenUpdatedAt({ plan: plan.updatedAt, todos: todos.updatedAt });
      void refreshScheduledActivity();
    }
    setOpen(!open);
  };

  const updatedLabel = plan.updatedAt ? formatRelativeTime(plan.updatedAt, t, i18n.language) : '';

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
          padding: '0 0.45rem',
          fontSize: '0.82rem',
          transition: 'background 0.14s ease, color 0.14s ease',
          position: 'relative',
        }}
        aria-label={t('chat.taskActivity.activityTitle')}
        title={t('chat.taskActivity.activityTitle')}
        aria-controls={panelId}
        aria-expanded={open}
        onMouseEnter={(e) => { setHovered(true); e.currentTarget.style.background = 'var(--color-bg-surface)'; e.currentTarget.style.color = 'var(--color-text-primary)'; }}
        onMouseLeave={(e) => { setHovered(false); if (!open) { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--color-text-secondary)'; } }}
      >
        <IconList style={{ width: '0.95rem', height: '0.95rem' }} />
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

      {hovered && !open ? (
        <div
          role="tooltip"
          style={{
            position: 'absolute',
            top: '2.3rem',
            right: 0,
            zIndex: 30,
            padding: '0.25rem 0.55rem',
            borderRadius: '0.45rem',
            border: '1px solid var(--color-border-paper)',
            background: 'var(--color-bg-surface-solid)',
            boxShadow: '0 4px 12px var(--color-shadow-medium)',
            fontSize: '0.72rem',
            color: 'var(--color-text-primary)',
            whiteSpace: 'nowrap',
            pointerEvents: 'none',
          }}
        >
          {t('chat.taskActivity.activityTitle')}
        </div>
      ) : null}

      <div
          id={panelId}
          role="dialog"
          aria-label={t('chat.taskActivity.activityTitle')}
          hidden={!open}
          style={{
            position: 'absolute',
            top: '2.4rem',
            right: 0,
            zIndex: 20,
            width: 'min(26rem, calc(100vw - 1.5rem))',
            maxHeight: 'min(42rem, calc(100vh - 5rem))',
            overflowY: 'auto',
            overscrollBehavior: 'contain',
            padding: '0.25rem',
            display: open ? 'flex' : 'none',
            flexDirection: 'column',
            gap: '0.75rem',
          }}
        >
          <TaskActivityContent
            key={threadId}
            active={open}
            threadId={threadId}
            subagentSidebarOpen={subagentSidebarOpen}
            onRequestClose={() => setOpen(false)}
            onToggleSubagents={onToggleSubagents}
            onNavigateThread={onNavigateThread}
            scheduledTasks={scheduledSnapshot}
            scheduledLoading={scheduledLoading}
            scheduledFailed={scheduledFailed}
            onRefreshScheduledTasks={() => void refreshScheduledActivity()}
            onOpenScheduledTask={onOpenScheduledTask}
          />
          {hasPlan ? <div className="task-activity__plan-card" style={POPOVER_CARD_STYLE}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.75rem' }}>
              <span style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--color-text-primary)' }}>{t('chat.planPanel.planTitle')}</span>
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
          </div> : null}
          {hasTodos ? <div className="task-activity__todo-card" style={POPOVER_CARD_STYLE}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.75rem' }}>
              <span style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--color-text-primary)' }}>{t('chat.planPanel.todosTitle')}</span>
              {todos.updatedAt ? (
                <span style={{ fontSize: '0.72rem', color: 'var(--color-text-muted)', whiteSpace: 'nowrap' }}>
                  {formatRelativeTime(todos.updatedAt, t, i18n.language)}
                </span>
              ) : null}
            </div>
            <TodoPopoverContent todos={todos} />
          </div> : null}
        </div>
    </div>
  );
}

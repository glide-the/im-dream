// [Input] Strict same-origin Product BFF data through useStoryWorkspaceSubscription.
// [Output] Responsive monthly Token subscription, allowance, entitlement, model, usage, and command UI.
// [Pos] Canonical Story Workspace subscription route; contains no local plan or quota truth.

import { useEffect, useMemo, useRef, useState, type KeyboardEvent } from 'react';
import type {
  CommandPreviewEnvelope,
  ProductAction,
  ProductApiError,
  ProductPlan,
} from '../../api/productApi';
import { useStoryWorkspaceSubscription } from '../../hooks/story-workspace/useStoryWorkspaceSubscription';
import './StoryWorkspaceSubscriptionPage.css';

const ACTION_LABELS: Record<ProductAction, string> = {
  create: '开通月度订阅',
  renew: '续订下一个月度周期',
  upgrade: '下周期升级',
  downgrade: '下周期降级',
  pause: '暂停订阅',
  resume: '恢复订阅',
  cancel: '在周期末取消',
  revoke_cancel: '撤销周期末取消',
};

const STATUS_LABELS: Record<string, string> = {
  trial: '试用中',
  active: '使用中',
  paused: '已暂停',
  cancel_at_period_end: '将于周期末取消',
  cancelled: '已取消',
  expired: '已过期',
  legacyUnavailable: '历史状态需处理',
};

const TARGET_ACTIONS = new Set<ProductAction>(['create', 'upgrade', 'downgrade']);

function formatInteger(value: number): string {
  return new Intl.NumberFormat('zh-CN', { maximumFractionDigits: 0 }).format(value);
}

function formatTimestamp(value: string | null | undefined): string {
  if (!value) return '未设置';
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    timeZoneName: 'short',
  }).format(new Date(value));
}

function formatStorage(value: number | null): string {
  if (value === null) return '未设置';
  if (value < 1_024) return `${formatInteger(value)} B`;
  const units = ['KB', 'MB', 'GB', 'TB'];
  let next = value / 1_024;
  let index = 0;
  while (next >= 1_024 && index < units.length - 1) {
    next /= 1_024;
    index += 1;
  }
  return `${new Intl.NumberFormat('zh-CN', { maximumFractionDigits: 1 }).format(next)} ${units[index]}`;
}

function joinValues(values: readonly string[]): string {
  return values.length > 0 ? values.join(' · ') : '未设置';
}

function actionLabel(action: ProductAction): string {
  return ACTION_LABELS[action];
}

interface ProductErrorPresentation {
  title: string;
  description: string;
  recovery: string;
}

function productErrorPresentation(error: ProductApiError): ProductErrorPresentation {
  const tokenDetails = error.status === 402 && error.details
    ? `可用 ${formatInteger(error.details.availableTokens ?? 0)} Token，需要 ${formatInteger(error.details.requiredTokens ?? 0)} Token；本周期结束于 ${formatTimestamp(error.details.periodEnd)}。`
    : null;
  switch (error.status) {
    case 401:
      return { title: '登录状态已失效', description: '保护的订阅数据未显示。', recovery: '重新验证登录后返回此页。' };
    case 402:
      return { title: '本周期 Token 不足', description: tokenDetails ?? '当前月度 Token 已不足以完成请求。', recovery: '等待个人周期重置，或查看下周期可用套餐。' };
    case 403:
      return { title: '当前条件不允许此操作', description: '订阅状态、模型或权限条件尚未满足。', recovery: '刷新当前订阅与可用操作。' };
    case 404:
      return { title: '请求的对象不可用', description: '套餐、订阅或模型可能已更新，或当前用户不可见。', recovery: '返回真实列表并重新读取。' };
    case 409:
      return { title: '订阅状态已发生变化', description: '服务器版本、预览或操作状态与当前页面不同。', recovery: '保留输入，刷新后重新预览。' };
    case 429:
      return { title: '请求暂时受限', description: error.retryAfterSeconds === null ? '当前请求窗口已达到限制。' : `请在 ${error.retryAfterSeconds} 秒后重试。`, recovery: '等待窗口恢复后手动重试。' };
    case 502:
      return { title: '模型上游暂时失败', description: '本次推理未被误报为成功，Token 终态由服务端确认。', recovery: '保留请求编号，按可重试状态手动重试。' };
    case 503:
    default:
      return { title: '订阅服务暂时不可用', description: '数据依赖、维护状态或安全合同当前无法满足。', recovery: '稍后重试；页面不会展示本地替代数据。' };
  }
}

function ErrorPanel({ error, onRetry, compact = false }: {
  error: ProductApiError;
  onRetry: () => void;
  compact?: boolean;
}) {
  const view = productErrorPresentation(error);
  return (
    <section className={`story-workspace-subscription__error${compact ? ' is-compact' : ''}`} role="alert">
      <div>
        <p className="story-workspace-subscription__kicker">{error.code}</p>
        <h2>{view.title}</h2>
        <p>{view.description}</p>
        <p>{view.recovery}</p>
        {error.requestId ? <small>请求编号：<code>{error.requestId}</code></small> : null}
      </div>
      <div className="story-workspace-subscription__error-actions">
        <button className="story-workspace-subscription__button" onClick={onRetry} type="button">重新读取</button>
        {error.status === 401 ? <a href="/">重新验证登录</a> : null}
      </div>
    </section>
  );
}

function LoadingPage() {
  return (
    <div aria-busy="true" aria-label="正在读取月度 Token 订阅" className="story-workspace-subscription__loading">
      <div className="story-workspace-subscription__skeleton is-title" />
      <div className="story-workspace-subscription__summary-grid">
        <div className="story-workspace-subscription__skeleton is-panel" />
        <div className="story-workspace-subscription__skeleton is-panel" />
      </div>
      <div className="story-workspace-subscription__skeleton is-wide" />
      <span className="story-workspace-subscription__sr-only">正在读取真实订阅与 Token 数据。</span>
    </div>
  );
}

function DefinitionItem({ label, value }: { label: string; value: string }) {
  return <div><dt>{label}</dt><dd>{value}</dd></div>;
}

function TokenAllowance({ allowance }: {
  allowance: NonNullable<ReturnType<typeof useStoryWorkspaceSubscription>['data']>['context']['data']['allowance'];
}) {
  if (!allowance) {
    return <div className="story-workspace-subscription__empty is-small">当前没有月度 Token 发放记录。</div>;
  }
  const consumedPercent = allowance.granted === 0 ? 0 : (allowance.consumed / allowance.granted) * 100;
  const reservedPercent = allowance.granted === 0 ? 0 : (allowance.reserved / allowance.granted) * 100;
  return (
    <div className="story-workspace-subscription__allowance">
      <div className="story-workspace-subscription__allowance-heading">
        <div><span>剩余 Token</span><strong>{formatInteger(allowance.remaining)}</strong></div>
        <small>重置于 {formatTimestamp(allowance.resetsAt)}</small>
      </div>
      <div
        aria-label={`本周期发放 ${formatInteger(allowance.granted)} Token，已消耗 ${formatInteger(allowance.consumed)}，已预留 ${formatInteger(allowance.reserved)}，剩余 ${formatInteger(allowance.remaining)}`}
        aria-valuemax={allowance.granted}
        aria-valuemin={0}
        aria-valuenow={allowance.consumed}
        className="story-workspace-subscription__token-bar"
        role="progressbar"
      >
        <span className="is-consumed" style={{ width: `${Math.min(100, consumedPercent)}%` }} />
        <span className="is-reserved" style={{ width: `${Math.min(100 - consumedPercent, reservedPercent)}%` }} />
      </div>
      <dl className="story-workspace-subscription__metrics is-four">
        <DefinitionItem label="本周期发放" value={`${formatInteger(allowance.granted)} Token`} />
        <DefinitionItem label="已消耗" value={`${formatInteger(allowance.consumed)} Token`} />
        <DefinitionItem label="执行中预留" value={`${formatInteger(allowance.reserved)} Token`} />
        <DefinitionItem label="仍可使用" value={`${formatInteger(allowance.remaining)} Token`} />
      </dl>
      <p className="story-workspace-subscription__hint">预留 Token 属于正在执行或等待终态的请求，完成后会消费实际用量并释放余量。</p>
    </div>
  );
}

function PageControls({ page, pageSize, total, onPage }: {
  page: number;
  pageSize: number;
  total: number;
  onPage: (page: number) => void;
}) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  return (
    <nav aria-label="分页" className="story-workspace-subscription__pagination">
      <span>第 {page} / {totalPages} 页，共 {formatInteger(total)} 项</span>
      <div>
        <button disabled={page <= 1} onClick={() => onPage(page - 1)} type="button">上一页</button>
        <button disabled={page >= totalPages} onClick={() => onPage(page + 1)} type="button">下一页</button>
      </div>
    </nav>
  );
}

function PlanRow({ plan, selected, onSelect }: {
  plan: ProductPlan;
  selected: boolean;
  onSelect: () => void;
}) {
  const modelAliases = [...new Set(plan.entitlements.flatMap((item) => item.modelAliases))];
  const gatewayScopes = [...new Set(plan.entitlements.flatMap((item) => item.gatewayScopes))];
  const rpmLimits = [...new Set(plan.entitlements.flatMap((item) => item.rpmLimit === null ? [] : [formatInteger(item.rpmLimit)]))];
  const dailyTokenLimits = [...new Set(plan.entitlements.flatMap((item) => item.dailyTokenLimit === null ? [] : [`${formatInteger(item.dailyTokenLimit)} Token`]))];
  const storageLimits = [...new Set(plan.entitlements.flatMap((item) => item.storageBytes === null ? [] : [formatStorage(item.storageBytes)]))];
  const name = `${plan.planName}，版本 ${plan.version}，每月 ${formatInteger(plan.monthlyAllowanceTokens)} Token`;
  return (
    <label className={`story-workspace-subscription__plan${selected ? ' is-selected' : ''}${!plan.eligibility.eligible ? ' is-ineligible' : ''}`}>
      <input
        aria-describedby={`plan-${plan.planVersionId}-description`}
        checked={selected}
        disabled={!plan.eligibility.eligible}
        name="monthly-token-plan"
        onChange={onSelect}
        type="radio"
        value={plan.planVersionId}
      />
      <span className="story-workspace-subscription__plan-main">
        <span><strong>{plan.planName}</strong><small>v{plan.version} · 月度</small></span>
        <b>{formatInteger(plan.monthlyAllowanceTokens)} Token / 月</b>
      </span>
      <span id={`plan-${plan.planVersionId}-description`} className="story-workspace-subscription__plan-detail">
        {plan.description ? <span>{plan.description}</span> : null}
        <span>模型：{joinValues(modelAliases)}</span>
        <span>范围：{joinValues(gatewayScopes)}</span>
        <span>RPM：{joinValues(rpmLimits)}</span>
        <span>每日 Token：{joinValues(dailyTokenLimits)}</span>
        <span>存储：{joinValues(storageLimits)}</span>
        <span>预计应用：{formatTimestamp(plan.eligibility.appliesAt)}</span>
        <span>{plan.eligibility.eligible ? '当前可选择' : `当前不可选择：${plan.eligibility.reasonCode ?? '条件未满足'}`}</span>
      </span>
      <span className="story-workspace-subscription__sr-only">{name}</span>
    </label>
  );
}

function CommandDialog({ preview, isExecuting, error, restoreFocus, onClose, onExecute, onRetry }: {
  preview: CommandPreviewEnvelope;
  isExecuting: boolean;
  error: ProductApiError | null;
  restoreFocus: HTMLElement | null;
  onClose: () => void;
  onExecute: (reason: string) => void;
  onRetry: () => void;
}) {
  const dialogRef = useRef<HTMLDivElement>(null);
  const titleRef = useRef<HTMLHeadingElement>(null);
  const previousFocusRef = useRef<HTMLElement | null>(null);
  const [reason, setReason] = useState('用户确认按服务端预览应用月度 Token 订阅变更');
  const [confirmed, setConfirmed] = useState(false);

  useEffect(() => {
    previousFocusRef.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    titleRef.current?.focus();
    return () => {
      const target = restoreFocus?.isConnected ? restoreFocus : previousFocusRef.current;
      window.requestAnimationFrame(() => {
        if (target?.isConnected) target.focus();
      });
    };
  }, [restoreFocus]);

  const handleKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key === 'Escape' && !isExecuting) {
      event.preventDefault();
      onClose();
      return;
    }
    if (event.key !== 'Tab') return;
    const focusable = Array.from(dialogRef.current?.querySelectorAll<HTMLElement>(
      'button:not([disabled]), textarea:not([disabled]), input:not([disabled]), a[href]',
    ) ?? []);
    if (focusable.length === 0) return;
    const first = focusable[0]!;
    const last = focusable[focusable.length - 1]!;
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  };

  const action = actionLabel(preview.data.action);
  return (
    <div className="story-workspace-subscription__dialog-backdrop">
      <div
        aria-labelledby="subscription-command-title"
        aria-modal="true"
        className="story-workspace-subscription__dialog"
        onKeyDown={handleKeyDown}
        ref={dialogRef}
        role="dialog"
      >
        <header>
          <div>
            <p className="story-workspace-subscription__kicker">操作影响预览</p>
            <h2 id="subscription-command-title" ref={titleRef} tabIndex={-1}>{action}</h2>
          </div>
          <button aria-label="关闭操作预览" disabled={isExecuting} onClick={onClose} type="button">关闭</button>
        </header>
        <div className="story-workspace-subscription__dialog-body">
          <section aria-labelledby="command-timing-title" className="story-workspace-subscription__impact">
            <h3 id="command-timing-title">应用时点</h3>
            <strong>{preview.data.appliesAt ? formatTimestamp(preview.data.appliesAt) : '操作成功时'}</strong>
            <p>{preview.data.allowanceImpact.currentPeriodChanges ? '本周期 Token 将按服务端回执变化。' : '本周期 Token 不变。'}</p>
          </section>
          <dl className="story-workspace-subscription__metrics is-two">
            <DefinitionItem label="当前版本" value={preview.data.current ? `${preview.data.current.planName} v${preview.data.current.version}` : '无'} />
            <DefinitionItem label="目标版本" value={preview.data.target ? `${preview.data.target.planName} v${preview.data.target.version}` : '保持当前版本'} />
            <DefinitionItem label="当前周期 Token" value={preview.data.allowanceImpact.currentPeriodTokens === null ? '无' : `${formatInteger(preview.data.allowanceImpact.currentPeriodTokens)} Token`} />
            <DefinitionItem label="下周期 Token" value={preview.data.allowanceImpact.nextPeriodTokens === null ? '无' : `${formatInteger(preview.data.allowanceImpact.nextPeriodTokens)} Token`} />
          </dl>
          <section className="story-workspace-subscription__impact">
            <h3>模型权益变化</h3>
            <p>当前：{joinValues(preview.data.entitlementImpact.currentModelAliases)}</p>
            <p>目标：{joinValues(preview.data.entitlementImpact.targetModelAliases)}</p>
            <p>执行后 Gateway：{preview.data.gatewayImpact.callableAfterExecute ? '可按订阅状态调用' : '不可调用'}</p>
          </section>
          {preview.data.warnings.length > 0 ? (
            <section className="story-workspace-subscription__warnings" aria-labelledby="command-warning-title">
              <h3 id="command-warning-title">请注意</h3>
              <ul>{preview.data.warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul>
            </section>
          ) : null}
          {!preview.data.allowed ? <p className="story-workspace-subscription__blocked" role="status">当前不可执行：{preview.data.reasonCode ?? '条件未满足'}</p> : null}
          {error ? <ErrorPanel compact error={error} onRetry={onRetry} /> : null}
          <div className="story-workspace-subscription__field">
            <label htmlFor="subscription-command-reason">操作原因</label>
            <p id="subscription-command-reason-description">用于安全审计，不得填写密钥或用户内容。</p>
            <textarea
              aria-describedby="subscription-command-reason-description"
              disabled={isExecuting}
              id="subscription-command-reason"
              maxLength={500}
              onChange={(event) => setReason(event.target.value)}
              rows={3}
              value={reason}
            />
          </div>
          <label className="story-workspace-subscription__confirm">
            <input checked={confirmed} disabled={isExecuting || !preview.data.allowed} onChange={(event) => setConfirmed(event.target.checked)} type="checkbox" />
            <span>我已核对应用时点、个人月度周期、Token 与模型权益影响。</span>
          </label>
          <small className="story-workspace-subscription__receipt">预览有效至 {formatTimestamp(preview.data.expiresAt)} · 请求编号 {preview.meta.requestId}</small>
        </div>
        <footer>
          <button className="story-workspace-subscription__button is-secondary" disabled={isExecuting} onClick={onClose} type="button">返回检查</button>
          <button
            className="story-workspace-subscription__button is-primary"
            disabled={!confirmed || reason.trim().length < 3 || !preview.data.allowed || isExecuting}
            onClick={() => onExecute(reason)}
            type="button"
          >
            {isExecuting ? '正在提交…' : `确认${action}`}
          </button>
        </footer>
      </div>
    </div>
  );
}

export function StoryWorkspaceSubscriptionPage() {
  const subscription = useStoryWorkspaceSubscription();
  const titleRef = useRef<HTMLHeadingElement>(null);
  const hasFocusedTitleRef = useRef(false);
  const commandTriggerRef = useRef<HTMLButtonElement | null>(null);
  const [selectedPlanVersionId, setSelectedPlanVersionId] = useState<string | null>(null);
  const { data, commandState } = subscription;
  const selectedPlan = useMemo(
    () => data?.plans.data.find((plan) => plan.planVersionId === selectedPlanVersionId) ?? null,
    [data?.plans.data, selectedPlanVersionId],
  );

  useEffect(() => {
    if (selectedPlanVersionId && !data?.plans.data.some((plan) => plan.planVersionId === selectedPlanVersionId)) {
      setSelectedPlanVersionId(null);
    }
  }, [data?.plans.data, selectedPlanVersionId]);

  useEffect(() => {
    if (subscription.isLoading || hasFocusedTitleRef.current || !titleRef.current) return;
    titleRef.current.focus();
    hasFocusedTitleRef.current = true;
  }, [data, subscription.error, subscription.isLoading]);

  if (subscription.isLoading && data === null) {
    return (
      <section aria-labelledby="story-workspace-subscription-title" className="story-workspace-subscription">
        <header className="story-workspace-subscription__page-header">
          <div>
            <p className="story-workspace-subscription__kicker">Dream · Monthly Token</p>
            <h1 id="story-workspace-subscription-title" ref={titleRef} tabIndex={-1}>月度 Token 订阅</h1>
            <p>正在读取个人月度周期、Token、权益与用量。</p>
          </div>
        </header>
        <LoadingPage />
      </section>
    );
  }

  if (data === null && subscription.error) {
    return (
      <section aria-labelledby="story-workspace-subscription-title" className="story-workspace-subscription">
        <header className="story-workspace-subscription__page-header">
          <p className="story-workspace-subscription__kicker">Dream · Monthly Token</p>
          <h1 id="story-workspace-subscription-title" ref={titleRef} tabIndex={-1}>月度 Token 订阅</h1>
          <p>查看个人月度周期、Token 与模型权益。</p>
        </header>
        <ErrorPanel error={subscription.error} onRetry={subscription.refetch} />
      </section>
    );
  }

  if (data === null) return null;

  const context = data.context.data;
  const current = context.subscription;
  const allowance = context.allowance;
  const usage = data.usage.data;
  const lifecycleActions = current?.allowedActions.filter((action) => !TARGET_ACTIONS.has(action)) ?? [];
  const targetActions = selectedPlan?.availableActions.filter((action) => TARGET_ACTIONS.has(action)) ?? [];

  return (
    <section aria-labelledby="story-workspace-subscription-title" className="story-workspace-subscription">
      <a className="story-workspace-subscription__skip-link" href="#subscription-current">跳到当前订阅</a>
      <div aria-atomic="true" aria-live="polite" className="story-workspace-subscription__sr-only">{subscription.announcement}</div>
      <header className="story-workspace-subscription__page-header">
        <div>
          <p className="story-workspace-subscription__kicker">Dream · Monthly Token</p>
          <h1 id="story-workspace-subscription-title" ref={titleRef} tabIndex={-1}>月度 Token 订阅</h1>
          <p>每位用户按自己的开通时间滚动计算月度周期；这里展示服务器确认的 Token、权益与用量。</p>
        </div>
        <div className="story-workspace-subscription__data-health">
          <span>{subscription.isRefreshing ? '正在刷新' : '数据已同步'}</span>
          <time dateTime={context.asOf}>{formatTimestamp(context.asOf)}</time>
          <button disabled={subscription.isRefreshing} onClick={subscription.refetch} type="button">刷新</button>
        </div>
      </header>

      {subscription.error ? <ErrorPanel compact error={subscription.error} onRetry={subscription.refetch} /> : null}
      {commandState.result ? (
        <section className="story-workspace-subscription__receipt-banner" role="status">
          <div>
            <strong>{commandState.result.data.outcome === 'scheduled' ? '变更已安排' : '操作已应用'}</strong>
            <span>命令 {commandState.result.data.commandId} · 订阅版本 {commandState.result.data.subscription.version}</span>
            {commandState.result.data.idempotentReplay ? <small>这是同一操作的安全重放结果。</small> : null}
          </div>
          <button onClick={subscription.clearCommandResult} type="button">关闭回执</button>
        </section>
      ) : null}

      <div className="story-workspace-subscription__summary-grid" id="subscription-current">
        <section aria-labelledby="current-subscription-title" className="story-workspace-subscription__panel is-current">
          <header className="story-workspace-subscription__panel-header">
            <div><p className="story-workspace-subscription__kicker">Current subscription</p><h2 id="current-subscription-title">当前订阅与个人周期</h2></div>
            <span className={`story-workspace-subscription__status is-${current?.status ?? 'empty'}`}>{current ? STATUS_LABELS[current.status] ?? current.status : '尚未开通'}</span>
          </header>
          {current && context.planVersion ? (
            <>
              <div className="story-workspace-subscription__current-plan">
                <strong>{context.planVersion.planName}</strong>
                <span>v{context.planVersion.version} · 每月 {formatInteger(context.planVersion.monthlyAllowanceTokens)} Token</span>
              </div>
              <dl className="story-workspace-subscription__metrics is-two">
                <DefinitionItem label="周期开始" value={formatTimestamp(current.currentPeriodStart)} />
                <DefinitionItem label="周期结束" value={formatTimestamp(current.currentPeriodEnd)} />
                <DefinitionItem label="个人锚点" value={formatTimestamp(current.cycleAnchorAt)} />
                <DefinitionItem label="周期序号" value={`第 ${formatInteger(current.currentPeriodNumber + 1)} 期`} />
                <DefinitionItem label="自动续订" value={current.renewalEnabled ? '已启用' : '未启用'} />
                <DefinitionItem label="期末取消" value={current.cancelAtPeriodEnd ? '已安排' : '未安排'} />
              </dl>
              {current.pendingChange ? (
                <p className="story-workspace-subscription__pending">已安排 {current.pendingChange.planName} v{current.pendingChange.version}，将在 {formatTimestamp(current.pendingChange.appliesAt)} 应用。</p>
              ) : null}
              {current.status === 'legacyUnavailable' ? <p className="story-workspace-subscription__blocked">此历史状态只读，需由管理员安全处理；新命令已禁用。</p> : null}
            </>
          ) : (
            <div className="story-workspace-subscription__empty is-small"><strong>当前没有订阅</strong><span>从下方真实可用的月度套餐开始预览。</span></div>
          )}
        </section>

        <section aria-labelledby="allowance-title" className="story-workspace-subscription__panel is-allowance">
          <header className="story-workspace-subscription__panel-header"><div><p className="story-workspace-subscription__kicker">Token conservation</p><h2 id="allowance-title">本周期 Token 守恒</h2></div></header>
          <TokenAllowance allowance={allowance} />
        </section>
      </div>

      <section aria-labelledby="entitlement-title" className="story-workspace-subscription__section">
        <header className="story-workspace-subscription__section-header"><div><p className="story-workspace-subscription__kicker">Entitlements</p><h2 id="entitlement-title">当前权益</h2></div><p>模型、Gateway 范围、RPM、每日 Token 与存储限制均由当前版本快照提供。</p></header>
        {context.entitlements.length > 0 ? (
          <div className="story-workspace-subscription__entitlements">
            {context.entitlements.map((entitlement) => (
              <article key={`${entitlement.gatewayScope}-${entitlement.modelAliases.join('-')}`}>
                <strong>{entitlement.gatewayScope}</strong>
                <dl>
                  <DefinitionItem label="模型 alias" value={joinValues(entitlement.modelAliases)} />
                  <DefinitionItem label="RPM" value={entitlement.rpmLimit === null ? '未设置' : formatInteger(entitlement.rpmLimit)} />
                  <DefinitionItem label="每日 Token" value={entitlement.dailyTokenLimit === null ? '未设置' : `${formatInteger(entitlement.dailyTokenLimit)} Token`} />
                  <DefinitionItem label="存储" value={formatStorage(entitlement.storageBytes)} />
                </dl>
              </article>
            ))}
          </div>
        ) : <div className="story-workspace-subscription__empty">当前订阅没有可展示的权益。</div>}
      </section>

      <section aria-labelledby="model-catalog-title" className="story-workspace-subscription__section">
        <header className="story-workspace-subscription__section-header"><div><p className="story-workspace-subscription__kicker">Model catalog</p><h2 id="model-catalog-title">当前可用模型</h2></div><time dateTime={data.models.data.asOf}>目录时间 {formatTimestamp(data.models.data.asOf)}</time></header>
        {data.models.data.items.length > 0 ? (
          <div className="story-workspace-subscription__models">
            {data.models.data.items.map((model) => (
              <article key={model.modelAlias}>
                <header><div><strong>{model.displayName}</strong><code>{model.modelAlias}</code></div><span>可用</span></header>
                {model.description ? <p>{model.description}</p> : null}
                <dl className="story-workspace-subscription__metrics is-two">
                  <DefinitionItem label="能力" value={joinValues(model.capabilities)} />
                  <DefinitionItem label="使用场景" value={joinValues(model.contexts)} />
                  <DefinitionItem label="Gateway 范围" value={joinValues(model.eligibility.gatewayScopes)} />
                  <DefinitionItem label="RPM" value={model.eligibility.rpmLimit === null ? '未设置' : formatInteger(model.eligibility.rpmLimit)} />
                  <DefinitionItem label="每日 Token" value={model.eligibility.dailyTokenLimit === null ? '未设置' : `${formatInteger(model.eligibility.dailyTokenLimit)} Token`} />
                  <DefinitionItem label="存储" value={formatStorage(model.eligibility.storageBytes)} />
                  <DefinitionItem label="剩余 Token" value={`${formatInteger(model.eligibility.monthlyTokenRemaining)} Token`} />
                  <DefinitionItem label="Token 重置" value={formatTimestamp(model.eligibility.monthlyTokenResetAt)} />
                  <DefinitionItem label="上下文窗口" value={model.limits.contextWindow === null ? '未设置' : `${formatInteger(model.limits.contextWindow)} Token`} />
                  <DefinitionItem label="最大输出" value={model.limits.maxOutputTokens === null ? '未设置' : `${formatInteger(model.limits.maxOutputTokens)} Token`} />
                </dl>
              </article>
            ))}
          </div>
        ) : <div className="story-workspace-subscription__empty">当前没有可用模型；页面不会选择本地默认型号。</div>}
      </section>

      <section aria-labelledby="usage-title" className="story-workspace-subscription__section">
        <header className="story-workspace-subscription__section-header"><div><p className="story-workspace-subscription__kicker">Current period usage</p><h2 id="usage-title">本周期 Usage</h2></div><p>{usage.period ? `${formatTimestamp(usage.period.start)} — ${formatTimestamp(usage.period.end)}` : '当前没有可用周期'}</p></header>
        <div className="story-workspace-subscription__usage-summary">
          <dl className="story-workspace-subscription__metrics is-six">
            <DefinitionItem label="请求" value={`${formatInteger(usage.summary.requestCount)} 次`} />
            <DefinitionItem label="输入" value={`${formatInteger(usage.summary.inputTokens)} Token`} />
            <DefinitionItem label="输出" value={`${formatInteger(usage.summary.outputTokens)} Token`} />
            <DefinitionItem label="Cache read" value={`${formatInteger(usage.summary.cacheReadTokens)} Token`} />
            <DefinitionItem label="Cache write" value={`${formatInteger(usage.summary.cacheWriteTokens)} Token`} />
            <DefinitionItem label="合计" value={`${formatInteger(usage.summary.totalTokens)} Token`} />
          </dl>
          <p>{usage.summary.unknownUsageCount > 0 ? `${formatInteger(usage.summary.unknownUsageCount)} 个请求的 Token 终态待确认。` : '所有请求 Token 终态均已确认。'}</p>
          <p>耗尽预测：{usage.projection.projectedExhaustionAt ? formatTimestamp(usage.projection.projectedExhaustionAt) : `样本不足（观察窗 ${formatInteger(usage.projection.sampleWindowDays)} 天）`}</p>
          <p>Usage 快照时间：{formatTimestamp(usage.projection.asOf)}{usage.allowance ? ` · 快照剩余 ${formatInteger(usage.allowance.remaining)} Token` : ''}</p>
        </div>
        {usage.items.length > 0 ? (
          <>
            <div aria-label="本周期 Token Usage 明细，可横向滚动" className="story-workspace-subscription__table-scroll" tabIndex={0}>
              <table>
                <caption>本周期 Gateway 请求与 Token 终态</caption>
                <thead><tr><th scope="col">时间</th><th scope="col">模型</th><th scope="col">范围</th><th scope="col">结果</th><th scope="col">输入 / 输出</th><th scope="col">总 Token</th><th scope="col">结算状态</th><th scope="col">请求编号</th></tr></thead>
                <tbody>{usage.items.map((item) => (
                  <tr key={item.gatewayRequestId}>
                    <td>{formatTimestamp(item.occurredAt)}</td><td><code>{item.modelAlias}</code></td><td>{item.gatewayScope}</td><td>{item.outcome}</td><td>{formatInteger(item.inputTokens)} / {formatInteger(item.outputTokens)}</td><td>{item.settlementState === 'usageUnknown' ? '待确认' : formatInteger(item.totalTokens)}</td><td>{item.settlementState}</td><td><code>{item.gatewayRequestId}</code></td>
                  </tr>
                ))}</tbody>
              </table>
            </div>
            <div className="story-workspace-subscription__usage-cards">
              {usage.items.map((item) => (
                <article key={item.gatewayRequestId}>
                  <header><strong>{item.modelAlias}</strong><span>{item.outcome}</span></header>
                  <time dateTime={item.occurredAt}>{formatTimestamp(item.occurredAt)}</time>
                  <dl><DefinitionItem label="总 Token" value={item.settlementState === 'usageUnknown' ? '待确认' : formatInteger(item.totalTokens)} /><DefinitionItem label="范围" value={item.gatewayScope} /><DefinitionItem label="终态" value={item.settlementState} /><DefinitionItem label="请求编号" value={item.gatewayRequestId} /></dl>
                </article>
              ))}
            </div>
            <PageControls onPage={subscription.setUsagePage} page={data.usage.meta.page} pageSize={data.usage.meta.pageSize} total={data.usage.meta.total} />
          </>
        ) : <div className="story-workspace-subscription__empty">当前个人周期还没有 Usage；返回创作后，已确认的请求会出现在这里。</div>}
      </section>

      <section aria-labelledby="plans-title" className="story-workspace-subscription__section" id="subscription-plans">
        <header className="story-workspace-subscription__section-header"><div><p className="story-workspace-subscription__kicker">Published monthly versions</p><h2 id="plans-title">可用月度套餐与操作</h2></div><p>选择 Admin 已发布的真实版本。升级与降级均在你的下一个周期边界应用。</p></header>
        {data.plans.data.length > 0 ? (
          <fieldset className="story-workspace-subscription__plan-list">
            <legend>选择一个月度 Token 套餐版本</legend>
            {data.plans.data.map((plan) => <PlanRow key={plan.planVersionId} onSelect={() => setSelectedPlanVersionId(plan.planVersionId)} plan={plan} selected={selectedPlanVersionId === plan.planVersionId} />)}
          </fieldset>
        ) : <div className="story-workspace-subscription__empty"><strong>暂无已发布的月度套餐</strong><span>请稍后刷新；页面不会显示过期或本地套餐。</span><small>请求编号：{data.plans.meta.requestId}</small></div>}
        {data.plans.data.length > 0 ? <PageControls onPage={subscription.setPlanPage} page={data.plans.meta.page} pageSize={data.plans.meta.pageSize} total={data.plans.meta.total} /> : null}

        <div className="story-workspace-subscription__actions">
          <section aria-labelledby="plan-actions-title">
            <h3 id="plan-actions-title">套餐操作</h3>
            <p>{selectedPlan ? `已选择 ${selectedPlan.planName} v${selectedPlan.version}` : '先选择一个真实套餐版本。'}</p>
            <div>{targetActions.map((action) => <button
              className="story-workspace-subscription__button is-primary"
              disabled={!selectedPlan?.eligibility.eligible || commandState.isPreviewing}
              key={action}
              onClick={(event) => {
                commandTriggerRef.current = event.currentTarget;
                void subscription.previewCommand(action, selectedPlan!.planVersionId);
              }}
              type="button"
            >{commandState.isPreviewing ? '正在预览…' : actionLabel(action)}</button>)}</div>
          </section>
          <section aria-labelledby="lifecycle-actions-title">
            <h3 id="lifecycle-actions-title">当前订阅操作</h3>
            <p>仅显示服务器对当前状态允许的操作。</p>
            <div>{lifecycleActions.length > 0 ? lifecycleActions.map((action) => <button
              className="story-workspace-subscription__button"
              disabled={commandState.isPreviewing}
              key={action}
              onClick={(event) => {
                commandTriggerRef.current = event.currentTarget;
                void subscription.previewCommand(action);
              }}
              type="button"
            >{actionLabel(action)}</button>) : <span>当前没有可执行的生命周期操作。</span>}</div>
          </section>
        </div>
        {commandState.error && commandState.preview === null ? <ErrorPanel compact error={commandState.error} onRetry={subscription.refetch} /> : null}
      </section>

      {commandState.preview ? (
        <CommandDialog
          error={commandState.error}
          isExecuting={commandState.isExecuting}
          onClose={subscription.closeCommand}
          onExecute={(reason) => void subscription.executeCommand(reason)}
          onRetry={subscription.refetch}
          preview={commandState.preview}
          restoreFocus={commandTriggerRef.current}
        />
      ) : null}
    </section>
  );
}

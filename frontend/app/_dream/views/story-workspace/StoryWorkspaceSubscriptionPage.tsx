// [Sync] 2026-10-29: share existing presentation copy with the read-only native page; Web layout remains.
// [Input] Authenticated subscription context and product plans from the Dream Product BFF.
// [Output] A quiet, accessible subscription overview with one focused panel at a time.
// [Pos] Canonical Story Workspace subscription route; it never invents plan or allowance data.

import { useEffect, useMemo, useRef, useState, type KeyboardEvent } from 'react';
import type { ProductApiError, ProductPlan } from '../../api/productApi';
import { useStoryWorkspaceSubscription } from '../../hooks/story-workspace/useStoryWorkspaceSubscription';
import {STATUS_LABELS,TABS,formatInteger,formatDate,productErrorPresentation,type SubscriptionTab} from './subscriptionPresentation';
import './StoryWorkspaceSubscriptionPage.css';

function ErrorPanel({ error, onRetry, compact = false }: {
  error: ProductApiError;
  onRetry: () => void;
  compact?: boolean;
}) {
  const view = productErrorPresentation(error);
  return (
    <section className={`story-workspace-subscription__error${compact ? ' is-compact' : ''}`} role="alert">
      <div>
        <h2>{view.title}</h2>
        <p>{view.description} {view.recovery}</p>
      </div>
      <button className="story-workspace-subscription__button" onClick={onRetry} type="button">重新读取</button>
    </section>
  );
}

function LoadingPage() {
  return (
    <div aria-label="正在读取订阅" className="story-workspace-subscription__loading" role="status">
      <span />
      <span />
      <span />
    </div>
  );
}

function PlanState({ current, plan }: { current: boolean; plan: ProductPlan }) {
  if (current) return <span className="story-workspace-subscription__plan-state is-current">当前套餐</span>;
  if (!plan.available || !plan.eligibility.eligible) {
    return <span className="story-workspace-subscription__plan-state">暂不可开通</span>;
  }
  return <span className="story-workspace-subscription__plan-state is-available">可以开通</span>;
}

function PlanCard({ current, plan }: { current: boolean; plan: ProductPlan }) {
  return (
    <article className={`story-workspace-subscription__plan${current ? ' is-current' : ''}`}>
      <div className="story-workspace-subscription__plan-topline">
        <p>{plan.eyebrow}</p>
        <PlanState current={current} plan={plan} />
      </div>
      <h3>{plan.planName}</h3>
      <p className="story-workspace-subscription__plan-note">{plan.note}</p>
      <ul>
        {plan.details.map((detail) => <li key={detail}>{detail}</li>)}
      </ul>
      {plan.monthlyAllowanceTokens !== null ? (
        <p className="story-workspace-subscription__plan-allowance">
          每月 {formatInteger(plan.monthlyAllowanceTokens)} Token
        </p>
      ) : null}
    </article>
  );
}

function EmptyPanel({ title, children }: { title: string; children: string }) {
  return (
    <div className="story-workspace-subscription__empty">
      <strong>{title}</strong>
      <span>{children}</span>
    </div>
  );
}

export function StoryWorkspaceSubscriptionPage() {
  const subscription = useStoryWorkspaceSubscription();
  const [activeTab, setActiveTab] = useState<SubscriptionTab>('info');
  const titleRef = useRef<HTMLHeadingElement>(null);
  const tabRefs = useRef<Array<HTMLButtonElement | null>>([]);
  const hasFocusedTitleRef = useRef(false);
  const data = subscription.data;
  const currentPlan = useMemo(() => {
    const planCode = data?.context.data.planVersion?.planCode;
    if (!planCode) return null;
    return data.plans.data.find((plan) => plan.planCode === planCode) ?? null;
  }, [data]);

  useEffect(() => {
    if (subscription.isLoading || hasFocusedTitleRef.current) return;
    hasFocusedTitleRef.current = true;
    titleRef.current?.focus({ preventScroll: true });
  }, [subscription.isLoading]);

  const activateTab = (tab: SubscriptionTab, focus = false) => {
    setActiveTab(tab);
    if (!focus) return;
    const index = TABS.findIndex((item) => item.id === tab);
    requestAnimationFrame(() => tabRefs.current[index]?.focus());
  };

  const handleTabKeyDown = (event: KeyboardEvent<HTMLButtonElement>, index: number) => {
    let nextIndex: number | null = null;
    if (event.key === 'ArrowRight') nextIndex = (index + 1) % TABS.length;
    if (event.key === 'ArrowLeft') nextIndex = (index - 1 + TABS.length) % TABS.length;
    if (event.key === 'Home') nextIndex = 0;
    if (event.key === 'End') nextIndex = TABS.length - 1;
    if (nextIndex === null) return;
    event.preventDefault();
    activateTab(TABS[nextIndex].id, true);
  };

  if (subscription.isLoading && data === null) {
    return (
      <section aria-labelledby="story-workspace-subscription-title" className="story-workspace-subscription">
        <header className="story-workspace-subscription__overview">
          <p className="story-workspace-subscription__eyebrow">Dream · Subscription</p>
          <h1 id="story-workspace-subscription-title" ref={titleRef} tabIndex={-1}>订阅</h1>
          <p>正在读取你的套餐与额度。</p>
        </header>
        <LoadingPage />
      </section>
    );
  }

  if (data === null && subscription.error) {
    return (
      <section aria-labelledby="story-workspace-subscription-title" className="story-workspace-subscription">
        <header className="story-workspace-subscription__overview">
          <p className="story-workspace-subscription__eyebrow">Dream · Subscription</p>
          <h1 id="story-workspace-subscription-title" ref={titleRef} tabIndex={-1}>订阅</h1>
          <p>查看你的套餐与本周期额度。</p>
        </header>
        <ErrorPanel error={subscription.error} onRetry={subscription.refetch} />
      </section>
    );
  }

  if (data === null) return null;

  const context = data.context.data;
  const current = context.subscription;
  const allowance = context.allowance;
  const planName = context.planVersion?.planName ?? currentPlan?.planName ?? '订阅';
  const planNote = currentPlan?.note ?? '为持续创作保留一处安静的工作空间。';
  const resetDate = allowance?.resetsAt ?? current?.currentPeriodEnd;
  const statusLabel = current ? STATUS_LABELS[current.status] ?? '当前套餐' : '尚未开通';
  const consumedPercent = allowance && allowance.granted > 0
    ? Math.min(100, Math.max(0, (allowance.consumed / allowance.granted) * 100))
    : 0;

  return (
    <section aria-labelledby="story-workspace-subscription-title" className="story-workspace-subscription">
      <div aria-atomic="true" aria-live="polite" className="story-workspace-subscription__sr-only">
        {subscription.announcement}
      </div>

      <header className="story-workspace-subscription__overview">
        <div className="story-workspace-subscription__overview-copy">
          <p className="story-workspace-subscription__eyebrow">Dream · Subscription</p>
          <h1 id="story-workspace-subscription-title" ref={titleRef} tabIndex={-1}>{planName}</h1>
          <p>{planNote}</p>
          <time dateTime={resetDate}>额度将在 {formatDate(resetDate)} 更新</time>
        </div>
        <div className="story-workspace-subscription__overview-actions">
          <button
            className="story-workspace-subscription__button is-quiet"
            disabled={subscription.isRefreshing}
            onClick={subscription.refetch}
            type="button"
          >
            {subscription.isRefreshing ? '正在更新…' : '重新读取'}
          </button>
          <button
            className="story-workspace-subscription__button is-primary"
            onClick={() => activateTab('plans', true)}
            type="button"
          >查看可选套餐</button>
        </div>
      </header>

      {subscription.error ? <ErrorPanel compact error={subscription.error} onRetry={subscription.refetch} /> : null}

      <div aria-label="订阅内容" className="story-workspace-subscription__tabs" role="tablist">
        {TABS.map((tab, index) => (
          <button
            aria-controls={`subscription-panel-${tab.id}`}
            aria-selected={activeTab === tab.id}
            id={`subscription-tab-${tab.id}`}
            key={tab.id}
            onClick={() => activateTab(tab.id)}
            onKeyDown={(event) => handleTabKeyDown(event, index)}
            ref={(node) => { tabRefs.current[index] = node; }}
            role="tab"
            tabIndex={activeTab === tab.id ? 0 : -1}
            type="button"
          >{tab.label}</button>
        ))}
      </div>

      {activeTab === 'info' ? (
        <section
          aria-labelledby="subscription-tab-info"
          className="story-workspace-subscription__panel"
          id="subscription-panel-info"
          role="tabpanel"
          tabIndex={0}
        >
          {current && context.planVersion ? (
            <>
              <div className="story-workspace-subscription__panel-heading">
                <div>
                  <p className="story-workspace-subscription__eyebrow">当前套餐</p>
                  <h2>{context.planVersion.planName}</h2>
                </div>
                <span className="story-workspace-subscription__status">{statusLabel}</span>
              </div>
              <p className="story-workspace-subscription__panel-note">{planNote}</p>
              {currentPlan?.details.length ? (
                <ul className="story-workspace-subscription__benefits">
                  {currentPlan.details.map((detail) => <li key={detail}>{detail}</li>)}
                </ul>
              ) : null}
              <p className="story-workspace-subscription__panel-footer">
                <span>按月更新</span>
                <time dateTime={resetDate}>下次更新 {formatDate(resetDate)}</time>
              </p>
            </>
          ) : (
            <EmptyPanel title="当前没有有效订阅">查看可选套餐，选择适合你的创作空间。</EmptyPanel>
          )}
        </section>
      ) : null}

      {activeTab === 'allowance' ? (
        <section
          aria-labelledby="subscription-tab-allowance"
          className="story-workspace-subscription__panel"
          id="subscription-panel-allowance"
          role="tabpanel"
          tabIndex={0}
        >
          {allowance ? (
            <>
              <div className="story-workspace-subscription__allowance-heading">
                <div>
                  <p className="story-workspace-subscription__eyebrow">本周期可用</p>
                  <h2>{formatInteger(allowance.remaining)} <small>Token</small></h2>
                </div>
                <p>已使用 {formatInteger(allowance.consumed)} / {formatInteger(allowance.granted)}</p>
              </div>
              <div
                aria-label={`已使用 ${Math.round(consumedPercent)}%`}
                aria-valuemax={allowance.granted}
                aria-valuemin={0}
                aria-valuenow={allowance.consumed}
                className="story-workspace-subscription__progress"
                role="progressbar"
              >
                <span style={{ width: `${consumedPercent}%` }} />
              </div>
              <p className="story-workspace-subscription__allowance-footer">
                <span>{Math.round(consumedPercent)}% 已使用</span>
                <time dateTime={allowance.resetsAt}>{formatDate(allowance.resetsAt)} 后更新</time>
              </p>
            </>
          ) : (
            <EmptyPanel title="额度暂不可用">当前没有可展示的月度 Token 额度。</EmptyPanel>
          )}
        </section>
      ) : null}

      {activeTab === 'plans' ? (
        <section
          aria-labelledby="subscription-tab-plans"
          className="story-workspace-subscription__panel is-plans"
          id="subscription-panel-plans"
          role="tabpanel"
          tabIndex={0}
        >
          <div className="story-workspace-subscription__plans-heading" id="subscription-plans">
            <div>
              <p className="story-workspace-subscription__eyebrow">A place for stories to keep growing</p>
              <h2>为正在形成的故事留出空间</h2>
            </div>
            <p>未完成商业配置的套餐会保留展示，但不会伪造价格或开通结果。</p>
          </div>
          {data.plans.data.length > 0 ? (
            <div className="story-workspace-subscription__plans-grid">
              {data.plans.data.map((plan) => (
                <PlanCard
                  current={context.planVersion?.planCode === plan.planCode}
                  key={plan.planCode}
                  plan={plan}
                />
              ))}
            </div>
          ) : (
            <EmptyPanel title="暂时没有可选套餐">稍后重新读取；页面不会显示本地套餐。</EmptyPanel>
          )}
        </section>
      ) : null}
    </section>
  );
}

// [Input] Static Dream plan copy only.
// [Output] Accessible three-tier subscription information surface without billing transport.
// [Pos] Story Workspace subscription route (R2).

import './StoryWorkspaceSubscriptionPage.css';

const STORY_WORKSPACE_DREAM_PLANS = [
  {
    name: 'Free',
    eyebrow: 'A quiet beginning',
    note: '从一段创作目标开始',
    details: ['查看已有 Deck', '发起有限次数的 Dream', '保留最近的工作台入口'],
  },
  {
    name: 'Dream',
    eyebrow: 'For active stories',
    note: '给持续创作留出空间',
    details: ['更充足的 Dream 创作额度', '更长的 Dream Agent 对话历史', '优先体验新的创作工作台能力'],
  },
  {
    name: 'is Dreaming',
    eyebrow: 'For ongoing worlds',
    note: '为长期作品准备的工作台',
    details: ['面向多部作品的持续创作支持', '更完整的 Deck 与工作台协作空间', '适合正在形成中的故事世界'],
  },
] as const;

export function StoryWorkspaceSubscriptionPage() {
  return (
    <section aria-labelledby="story-workspace-subscription-title" className="story-workspace-subscription">
      <header className="story-workspace-subscription__header">
        <div className="story-workspace-subscription__intro">
          <p>Dream plans · choose your pace</p>
          <h1 id="story-workspace-subscription-title">选择适合现在创作节奏的方式</h1>
          <span>从一次灵感到一个持续生长的故事世界，选择与你当前创作节奏相符的空间。</span>
        </div>
        <aside aria-label="订阅状态" className="story-workspace-subscription__status">
          <span>当前状态</span>
          <strong>订阅功能即将开放</strong>
          <small>现在无需付款，方案信息仅用于了解各档位的创作侧重点。</small>
        </aside>
      </header>
      <div aria-label="Dream 订阅档位" className="story-workspace-subscription__plans">
        {STORY_WORKSPACE_DREAM_PLANS.map((plan, index) => (
          <article className={`story-workspace-subscription__plan${plan.name === 'Dream' ? ' is-featured' : ''}`} key={plan.name}>
            <header className="story-workspace-subscription__plan-header">
              <span className="story-workspace-subscription__plan-number">0{index + 1}</span>
              <p>{plan.eyebrow}</p>
            </header>
            <h2>{plan.name}</h2>
            <strong>{plan.note}</strong>
            <ul>
              {plan.details.map((detail) => (
                <li key={detail}>
                  <span aria-hidden="true">✓</span>
                  {detail}
                </li>
              ))}
            </ul>
            <footer>
              <span>正式开通后可在此管理</span>
              {plan.name === 'Dream' ? <b>推荐给持续创作</b> : null}
            </footer>
          </article>
        ))}
      </div>
      <p className="story-workspace-subscription__note">定价与开通方式将在可用时通过正式账户流程说明。</p>
    </section>
  );
}

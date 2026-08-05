// [Input] Static Dream plan copy only.
// [Output] Accessible three-tier subscription information surface without billing transport.
// [Pos] Story Workspace subscription route (R2).

import './StoryWorkspaceSubscriptionPage.css';

const STORY_WORKSPACE_DREAM_PLANS = [
  {
    name: 'Free',
    note: '从一段创作目标开始',
    details: ['查看已有 Deck', '发起有限次数的 Dream', '保留最近的工作台入口'],
  },
  {
    name: 'Dream',
    note: '给持续创作留出空间',
    details: ['更充足的 Dream 创作额度', '更长的 Dream Agent 对话历史', '优先体验新的创作工作台能力'],
  },
  {
    name: 'is Dreaming',
    note: '为长期作品准备的工作台',
    details: ['面向多部作品的持续创作支持', '更完整的 Deck 与工作台协作空间', '适合正在形成中的故事世界'],
  },
] as const;

export function StoryWorkspaceSubscriptionPage() {
  return (
    <section aria-labelledby="story-workspace-subscription-title" className="story-workspace-subscription">
      <header className="story-workspace-subscription__header">
        <p>Dream workspace · plans</p>
        <h1 id="story-workspace-subscription-title">选择适合现在创作节奏的方式</h1>
        <span>订阅能力仍在准备中。这里说明各档位的创作侧重点，不会在此页发起扣费或改变你的权限。</span>
      </header>
      <div aria-label="Dream 订阅档位" className="story-workspace-subscription__plans">
        {STORY_WORKSPACE_DREAM_PLANS.map((plan) => (
          <article className="story-workspace-subscription__plan" key={plan.name}>
            <p>{plan.name === 'is Dreaming' ? 'For ongoing worlds' : 'Dream plan'}</p>
            <h2>{plan.name}</h2>
            <strong>{plan.note}</strong>
            <ul>
              {plan.details.map((detail) => <li key={detail}>{detail}</li>)}
            </ul>
            <span>定价与开通方式将在可用时通过正式账户流程说明。</span>
          </article>
        ))}
      </div>
    </section>
  );
}

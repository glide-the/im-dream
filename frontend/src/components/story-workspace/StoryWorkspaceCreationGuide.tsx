// [Input] Static drama workflow rules and the Story Workspace guide illustration.
// [Output] A read-only, three-stage creation guide inside the draft focus layer.
// [Pos] Story Workspace Execution Outline guide surface.
// [Sync] 2026-08-31: introduce shared-asset, per-Episode, and future-stage guidance
//                    with Mimo identity in the Xiaohei-style 2D triptych.
// [Sync] 2026-08-31: let the shared guide name the actual source surface in its back action.

export const STORY_WORKSPACE_CREATION_GUIDE_FOCUS_KEY = 'creation-guide';

interface StoryWorkspaceCreationGuideProps {
  readonly backLabel?: string;
  readonly onBack: () => void;
}

interface CreationGuideCommand {
  readonly command: string;
  readonly description: string;
}

interface CreationGuideStage {
  readonly id: string;
  readonly label: string;
  readonly status: string;
  readonly title: string;
  readonly description: string;
  readonly commands: readonly CreationGuideCommand[];
  readonly illustrationAlt: string;
  readonly tone: 'shared' | 'repeat' | 'future';
}

const CREATION_GUIDE_STAGES: readonly CreationGuideStage[] = [
  {
    id: 'shared-assets',
    label: '阶段一',
    status: '跨集复用',
    title: '建立项目与共享资产',
    description: '角色卡和场景卡首次定稿后，由后续所有 Episode 直接复用。',
    illustrationAlt: 'Mimo 把角色卡和场景卡存入共享档案，并分发给多个 Episode 跨集复用',
    tone: 'shared',
    commands: [
      { command: '/drama-init', description: '初始化项目（选题、画幅、集数）' },
      { command: '/drama-plan', description: '分集规划（节奏、伏笔、角色节奏）' },
      { command: '/drama-asset', description: '创建角色卡 + 场景卡（定稿）' },
    ],
  },
  {
    id: 'episode-loop',
    label: '阶段二',
    status: '每个 EP 重复',
    title: '逐集创作与审查',
    description: '每一集都从剧本开始，依次完成分镜、Prompt 包和五维度审查。',
    illustrationAlt: 'Mimo 转动制作循环装置，让每一集依次经过剧本、分镜、Prompt 和审查',
    tone: 'repeat',
    commands: [
      { command: '/drama-script (EP01)', description: '创作第一集剧本' },
      { command: '/drama-storyboard (EP01)', description: '设计分镜表' },
      { command: '/drama-prompt (EP01)', description: '生成 Prompt 包' },
      { command: '/script-reviewer', description: '审查：剧本通过五维度审查' },
    ],
  },
  {
    id: 'future-production',
    label: '阶段三',
    status: '尚未实现',
    title: '渲染、后期与宣发',
    description: '以下环节用于说明完整制作方向，当前工作台尚未开放对应功能。',
    illustrationAlt: 'Mimo 停在尚未开放的边界外，边界内是渲染、配音、后期和宣发工具',
    tone: 'future',
    commands: [
      { command: '/drama-render + /drama-voice', description: '渲染 + 配音' },
      { command: '/drama-edit', description: '后期整合' },
      { command: '/drama-promote', description: '宣发物料' },
    ],
  },
] as const;

export function StoryWorkspaceCreationGuide({
  backLabel = '返回故事线',
  onBack,
}: StoryWorkspaceCreationGuideProps) {
  return (
    <main
      className="story-workspace-collaboration__focus-layer"
      data-execution-depth="focus"
    >
      <article
        aria-labelledby="story-workspace-creation-guide-title"
        className="story-workspace-collaboration__focus story-workspace-creation-guide"
      >
        <header className="story-workspace-collaboration__focus-nav">
          <button onClick={onBack} type="button">← {backLabel}</button>
        </header>

        <div className="story-workspace-creation-guide__intro">
          <h2 id="story-workspace-creation-guide-title">短剧创作流程</h2>
        </div>

        <ol aria-label="短剧创作三阶段" className="story-workspace-creation-guide__stages">
          {CREATION_GUIDE_STAGES.map((stage) => (
            <li
              className={`story-workspace-creation-guide__stage story-workspace-creation-guide__stage--${stage.tone}`}
              key={stage.id}
            >
              <section aria-labelledby={`story-workspace-creation-guide-${stage.id}`}>
                <div className="story-workspace-creation-guide__stage-copy">
                  <header>
                    <span>{stage.label}</span>
                    <small>{stage.status}</small>
                  </header>
                  <h3 id={`story-workspace-creation-guide-${stage.id}`}>{stage.title}</h3>
                  <p>{stage.description}</p>
                  <ul aria-label={`${stage.label}命令`}>
                    {stage.commands.map((item) => (
                      <li key={item.command}>
                        <code>{item.command}</code>
                        <span>{item.description}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                <figure>
                  <img
                    alt={stage.illustrationAlt}
                    className={`story-workspace-creation-guide__illustration--${stage.tone}`}
                    src="/assets/story-workspace-guide-illustrations/01-mimo-xiaohei-workflow-triptych.png"
                  />
                </figure>
              </section>
            </li>
          ))}
        </ol>
      </article>
    </main>
  );
}

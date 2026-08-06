/* eslint-disable react-refresh/only-export-components -- The reader exports a pure keyboard seam for deterministic accessibility tests. */
// [Input] Actor-scoped Episode documents, manifest facts, storyboard projection and controlled selection.
// [Output] Safe Markdown reading tabs plus an allowlisted storyboard property inspector.
// [Pos] Story Workspace storyboard focus layer; canonical files remain read-only truth owners.

import type { KeyboardEvent } from 'react';
import ReactMarkdown, { type Components } from 'react-markdown';
import remarkGfm from 'remark-gfm';

import type {
  StoryWorkspaceEpisodeArtifactDocument,
  StoryWorkspaceEpisodeArtifactManifestEntry,
  StoryWorkspaceEpisodeStoryboardShot,
} from '../../../hooks/story-workspace/contracts';

export type StoryWorkspaceEpisodeReadableArtifact =
  | 'episode-outline.md'
  | 'script.md'
  | 'storyboard.yaml'
  | 'review-report.md';

export interface StoryWorkspaceEpisodeArtifactReaderProps {
  readonly activeArtifact: StoryWorkspaceEpisodeReadableArtifact;
  readonly artifacts: readonly StoryWorkspaceEpisodeArtifactManifestEntry[];
  readonly documents: readonly StoryWorkspaceEpisodeArtifactDocument[];
  readonly shots: readonly StoryWorkspaceEpisodeStoryboardShot[];
  readonly selectedShotId: string | null;
  readonly onArtifactSelection: (artifact: StoryWorkspaceEpisodeReadableArtifact) => void;
  readonly onShotSelection: (shotId: string) => void;
}

const ARTIFACT_TABS: readonly {
  readonly key: StoryWorkspaceEpisodeReadableArtifact;
  readonly label: string;
}[] = [
  { key: 'episode-outline.md', label: '分集大纲' },
  { key: 'script.md', label: '剧本' },
  { key: 'storyboard.yaml', label: '分镜' },
  { key: 'review-report.md', label: '审阅' },
];

const AVAILABILITY_LABELS = {
  available: '已生成',
  not_generated: '尚未生成',
  invalid: '来源无效',
  unavailable: '当前不可用',
} as const;

export function storyWorkspaceEpisodeArtifactTabTarget(
  activeArtifact: StoryWorkspaceEpisodeReadableArtifact,
  key: string,
): StoryWorkspaceEpisodeReadableArtifact | null {
  const index = ARTIFACT_TABS.findIndex((tab) => tab.key === activeArtifact);
  if (index < 0) return null;
  if (key === 'Home') return ARTIFACT_TABS[0].key;
  if (key === 'End') return ARTIFACT_TABS[ARTIFACT_TABS.length - 1].key;
  if (key !== 'ArrowLeft' && key !== 'ArrowRight') return null;
  const offset = key === 'ArrowRight' ? 1 : -1;
  return ARTIFACT_TABS[(index + offset + ARTIFACT_TABS.length) % ARTIFACT_TABS.length].key;
}

const MARKDOWN_COMPONENTS: Components = {
  a({ children, href }) {
    if (href === undefined) return <span>{children}</span>;
    return <a href={href} rel="noreferrer" target="_blank">{children}</a>;
  },
  img({ alt }) {
    return <span role="img" aria-label={alt ?? '文档图片'}>[图片：{alt ?? '未命名'}]</span>;
  },
};

function artifactFact(
  artifacts: readonly StoryWorkspaceEpisodeArtifactManifestEntry[],
  key: StoryWorkspaceEpisodeReadableArtifact,
): StoryWorkspaceEpisodeArtifactManifestEntry | null {
  return artifacts.find((artifact) => artifact.relativeKey === key) ?? null;
}

function availabilityText(
  artifacts: readonly StoryWorkspaceEpisodeArtifactManifestEntry[],
  key: StoryWorkspaceEpisodeReadableArtifact,
): string {
  const fact = artifactFact(artifacts, key);
  return fact === null ? '尚未生成' : AVAILABILITY_LABELS[fact.availability];
}

function MarkdownDocument({
  artifact,
  artifacts,
  documents,
}: {
  readonly artifact: Exclude<StoryWorkspaceEpisodeReadableArtifact, 'storyboard.yaml'>;
  readonly artifacts: readonly StoryWorkspaceEpisodeArtifactManifestEntry[];
  readonly documents: readonly StoryWorkspaceEpisodeArtifactDocument[];
}) {
  const document = documents.find((item) => item.relativeKey === artifact) ?? null;
  const fact = artifactFact(artifacts, artifact);
  if (document === null) {
    return (
      <section aria-label="文件内容" role="status">
        <p>{availabilityText(artifacts, artifact)}，当前没有可阅读正文。</p>
      </section>
    );
  }
  return (
    <article aria-label={`${ARTIFACT_TABS.find((item) => item.key === artifact)?.label}文件内容`}>
      {fact?.availability === 'available' ? null : (
        <p role="status">当前显示最近一次有效正文；最新来源状态为{availabilityText(artifacts, artifact)}。</p>
      )}
      <div className="story-workspace-episode-artifact-reader__markdown">
        <ReactMarkdown
          components={MARKDOWN_COMPONENTS}
          remarkPlugins={[remarkGfm]}
          skipHtml
        >
          {document.markdown}
        </ReactMarkdown>
      </div>
      <footer aria-label="文件来源信息">
        来源：{artifact} · Revision：{document.sourceRevision}
      </footer>
    </article>
  );
}

function pending(value: string | number | null): string | number {
  return value === null || value === '' ? '尚未生成' : value;
}

function StoryboardInspector({
  artifacts,
  shots,
  selectedShotId,
  onShotSelection,
}: {
  readonly artifacts: readonly StoryWorkspaceEpisodeArtifactManifestEntry[];
  readonly shots: readonly StoryWorkspaceEpisodeStoryboardShot[];
  readonly selectedShotId: string | null;
  readonly onShotSelection: (shotId: string) => void;
}) {
  const fact = artifactFact(artifacts, 'storyboard.yaml');
  if (fact?.availability !== 'available') {
    return <section role="status">{availabilityText(artifacts, 'storyboard.yaml')}，尚无分镜属性。</section>;
  }
  const selected = shots.find((shot) => shot.id === selectedShotId) ?? shots[0] ?? null;
  if (selected === null) return <section role="status">分镜文件已生成，但尚未投影出有效镜头。</section>;
  const definition = (label: string, value: string | number | null) => (
    <div key={label}>
      <dt>{label}</dt>
      <dd>{pending(value)}</dd>
    </div>
  );
  return (
    <div className="story-workspace-episode-artifact-reader__storyboard">
      <nav aria-label="分镜镜头导航">
        <ol>
          {shots.map((shot) => (
            <li key={shot.id}>
              <button
                aria-current={shot.id === selected.id ? 'true' : undefined}
                onClick={() => onShotSelection(shot.id)}
                type="button"
              >
                {shot.shotId}
              </button>
            </li>
          ))}
        </ol>
      </nav>
      <article aria-label="分镜 YAML 属性">
        <p>详细分镜</p>
        <h3>{selected.shotId}</h3>
        <section>
          <h4>镜头意图</h4>
          <p>{pending(selected.visual)}</p>
        </section>
        <section>
          <h4>镜头参数</h4>
          <dl>
            {definition('景别', selected.shotType)}
            {definition('角度', selected.camera.angle)}
            {definition('高度', selected.camera.height)}
            {definition('运动', selected.camera.movement)}
            {definition('镜头', selected.camera.lens)}
            {definition(
              '时长',
              selected.timing.durationSec === null
                ? null
                : `${selected.timing.durationSec} 秒`,
            )}
            {definition('入场转场', selected.timing.transitionIn)}
            {definition('出场转场', selected.timing.transitionOut)}
          </dl>
        </section>
        <section>
          <h4>角色</h4>
          {selected.characters.length === 0 ? <p>尚未生成</p> : (
            <ul>
              {selected.characters.map((character) => (
                <li key={character.ref}>
                  <strong>{character.displayName ?? character.ref}</strong>
                  {' · '}{pending(character.action)}{' · '}{pending(character.emotion)}
                </li>
              ))}
            </ul>
          )}
        </section>
        <section>
          <h4>对白</h4>
          {selected.dialogue.length === 0 ? <p>尚未生成</p> : (
            <ol>
              {selected.dialogue.map((line) => (
                <li key={`${line.speaker}:${line.type}:${line.line}`}>
                  <strong>{line.speaker}</strong>：{line.line} · {line.type}
                </li>
              ))}
            </ol>
          )}
        </section>
        <footer aria-label="分镜来源与关联">
          <p>
            来源：storyboard.yaml · Revision：{selected.sourceRevision ?? '尚未生成'}
          </p>
          <p>
            script_scene_ref → {pending(selected.declaredScriptSceneRef)} ·{' '}
            narrative_beat_ref → {pending(selected.declaredNarrativeBeatRef)}
          </p>
        </footer>
      </article>
    </div>
  );
}

export function StoryWorkspaceEpisodeArtifactReader({
  activeArtifact,
  artifacts,
  documents,
  shots,
  selectedShotId,
  onArtifactSelection,
  onShotSelection,
}: StoryWorkspaceEpisodeArtifactReaderProps) {
  const handleTabKey = (
    event: KeyboardEvent<HTMLButtonElement>,
    artifact: StoryWorkspaceEpisodeReadableArtifact,
  ) => {
    const target = storyWorkspaceEpisodeArtifactTabTarget(artifact, event.key);
    if (target === null) return;
    event.preventDefault();
    onArtifactSelection(target);
    event.currentTarget.parentElement
      ?.querySelector<HTMLButtonElement>(`#story-workspace-episode-artifact-tab-${target.replaceAll('.', '-')}`)
      ?.focus();
  };
  return (
    <section
      aria-label="第一集文件阅读器"
      className="story-workspace-episode-artifact-reader"
    >
      <header>
        <div>
          <p>EP01 · Canonical artifacts</p>
          <h3>第一集产物查阅</h3>
        </div>
        <nav aria-label="第一集文件导航" role="tablist">
          {ARTIFACT_TABS.map((tab) => (
            <button
              aria-controls="story-workspace-episode-artifact-content"
              aria-selected={activeArtifact === tab.key}
              id={`story-workspace-episode-artifact-tab-${tab.key.replaceAll('.', '-')}`}
              key={tab.key}
              onClick={() => onArtifactSelection(tab.key)}
              onKeyDown={(event) => handleTabKey(event, tab.key)}
              role="tab"
              tabIndex={activeArtifact === tab.key ? 0 : -1}
              type="button"
            >
              <span>{tab.label}</span>
              <small>{availabilityText(artifacts, tab.key)}</small>
            </button>
          ))}
        </nav>
      </header>
      <div
        aria-labelledby={`story-workspace-episode-artifact-tab-${activeArtifact.replaceAll('.', '-')}`}
        id="story-workspace-episode-artifact-content"
        role="tabpanel"
      >
        {activeArtifact === 'storyboard.yaml' ? (
          <StoryboardInspector
            artifacts={artifacts}
            onShotSelection={onShotSelection}
            selectedShotId={selectedShotId}
            shots={shots}
          />
        ) : (
          <MarkdownDocument
            artifact={activeArtifact}
            artifacts={artifacts}
            documents={documents}
          />
        )}
      </div>
    </section>
  );
}

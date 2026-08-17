// [Input] Optional page-heading copy supplied by Story Workspace route pages.
// [Output] Render a reusable, business-content-free Story Workspace page skeleton.
// [Pos] Reusable Story Workspace dashboard/page shell; it owns no canonical route.
export interface StoryWorkspaceDashboardPageProps {
  description?: string;
  eyebrow?: string;
  title?: string;
}

export function StoryWorkspaceDashboardPage({
  description = 'Agent 产出的工作区内容将在后续任务中呈现在这里。',
  eyebrow = 'Story Workspace',
  title = '工作台首页',
}: StoryWorkspaceDashboardPageProps) {
  return (
    <section
      aria-labelledby="story-workspace-page-title"
      style={{
        minHeight: '100%',
        padding: '56px clamp(32px, 5vw, 72px)',
        boxSizing: 'border-box',
      }}
    >
      <div style={{ maxWidth: 760 }}>
        <p style={{
          margin: '0 0 10px',
          color: 'var(--color-text-muted)',
          fontSize: 12,
          fontWeight: 600,
          letterSpacing: '0.12em',
          textTransform: 'uppercase',
        }}>
          {eyebrow}
        </p>
        <h1
          id="story-workspace-page-title"
          style={{
            margin: 0,
            color: 'var(--color-text-primary)',
            fontFamily: "'Excalifont', 'Xiaolai', Georgia, serif",
            fontSize: 28,
            fontWeight: 600,
            lineHeight: 1.35,
          }}
        >
          {title}
        </h1>
        <p style={{
          maxWidth: 620,
          margin: '18px 0 0',
          color: 'var(--color-text-secondary)',
          fontSize: 14,
          lineHeight: 1.8,
        }}>
          {description}
        </p>
      </div>
    </section>
  );
}

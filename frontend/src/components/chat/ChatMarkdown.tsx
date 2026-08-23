// [Input] Markdown text, optional owning Chat Thread ID, WorkspaceContext, and shared Markdown/file reference components.
// [Output] GFM Markdown rendered through the shared chain, with Mermaid and exact workspace:// references safely routed.
// [Pos] chat-markdown component node in frontend/src/components/chat
// [Sync] 2026-07-20: created per docs/design/claude-agent/chat-markdown-mermaid.md — consolidates the
//                    three local ReactMarkdown+remarkGfm call sites; `pre` override unwraps Mermaid
//                    blocks so no block-level element is nested inside <pre>.
// [Sync] 2026-08-22: preserve only exact workspace:// candidates through the secure URL
//                    transform and resolve them with current Thread/Workspace context.
import { Children, isValidElement, memo, useMemo, type ReactNode } from 'react';
import ReactMarkdown, { defaultUrlTransform, type Components } from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useWorkspaceSession } from '../../contexts/WorkspaceContext';
import MermaidBlock from './MermaidBlock';
import { WorkspaceFileLink, WorkspaceImage } from './WorkspaceFileReference';
import { isWorkspaceUri } from './workspaceUri';

const REMARK_PLUGINS = [remarkGfm];

function extractText(node: ReactNode): string {
  if (typeof node === 'string') {
    return node;
  }
  if (Array.isArray(node)) {
    return node.map(extractText).join('');
  }
  return '';
}

const BASE_COMPONENTS: Components = {
  code({ className, children }) {
    if (className === 'language-mermaid') {
      return <MermaidBlock chart={extractText(children)} />;
    }
    return <code className={className}>{children}</code>;
  },
  pre({ children }) {
    // Mermaid code blocks render a block-level MermaidBlock; unwrapping the <pre>
    // keeps the DOM valid (<pre> only accepts phrasing content). The child here is
    // the (not yet invoked) custom `code` component element, so detect Mermaid via
    // its props.className rather than its rendered type.
    const child = Children.toArray(children)[0];
    if (isValidElement<{ className?: string }>(child) && child.props.className === 'language-mermaid') {
      return <>{children}</>;
    }
    return <pre>{children}</pre>;
  },
};

interface ChatMarkdownProps {
  text: string;
  workspaceSessionId?: string;
}

function workspaceUrlTransform(value: string): string {
  return isWorkspaceUri(value) ? value : defaultUrlTransform(value);
}

export default memo(function ChatMarkdown({ text, workspaceSessionId }: ChatMarkdownProps) {
  const { activeSessionId, workspaceConfigLoaded, workspaceEnabled } = useWorkspaceSession();
  const threadId = workspaceSessionId ?? activeSessionId ?? undefined;
  const workspaceAvailability = workspaceConfigLoaded
    ? (workspaceEnabled ? 'enabled' : 'disabled')
    : 'loading';
  const components = useMemo<Components>(() => ({
    ...BASE_COMPONENTS,
    a({ href, children, node, ...props }) {
      void node;
      if (isWorkspaceUri(href)) {
        return (
          <WorkspaceFileLink uri={href} threadId={threadId} workspaceAvailability={workspaceAvailability}>
            {children}
          </WorkspaceFileLink>
        );
      }
      return <a href={href} {...props}>{children}</a>;
    },
    img({ src, alt, node, ...props }) {
      void node;
      if (isWorkspaceUri(src)) {
        return <WorkspaceImage uri={src} alt={alt} threadId={threadId} workspaceAvailability={workspaceAvailability} />;
      }
      return <img src={src} alt={alt} {...props} />;
    },
  }), [threadId, workspaceAvailability]);

  return (
    <ReactMarkdown remarkPlugins={REMARK_PLUGINS} components={components} urlTransform={workspaceUrlTransform}>
      {text}
    </ReactMarkdown>
  );
});

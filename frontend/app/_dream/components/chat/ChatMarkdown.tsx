// [Sync] 2026-10-10: bind image operation/model ownership and preserve real call identity through original authorization, files and history.
// [Input] Markdown text, owning Chat Thread ID, optional authenticated report path, WorkspaceContext and shared Markdown/file components.
// [Output] Shared GFM/math/Mermaid rendering with safe workspace:// references and document-only relative resolution; code stays literal.
// [Sync] 2026-11-08: add explicit math tokens and source-preserving selection copying to the original renderer.
// [Pos] chat-markdown component node in frontend/app/_dream/components/chat
// [Sync] 2026-07-20: created per docs/design/claude-agent/chat-markdown-mermaid.md — consolidates the
//                    three local ReactMarkdown+remarkGfm call sites; `pre` override unwraps Mermaid
//                    blocks so no block-level element is nested inside <pre>.
// [Sync] 2026-08-22: preserve only exact workspace:// candidates through the secure URL
//                    transform and resolve them with current Thread/Workspace context.
// [Sync] 2026-09-06: narrow React Markdown image sources before applying the Workspace URI boundary.
// [Sync] 2026-09-13: reuse the same renderer for authenticated reports, resolving their relative references without changing ordinary Chat URLs or code.
import { Children, isValidElement, memo, useMemo, type ReactNode } from 'react';
import ReactMarkdown, { defaultUrlTransform, type Components } from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useWorkspaceSession } from '../../contexts/WorkspaceContext';
import MermaidBlock from './MermaidBlock';
import { WorkspaceFileLink, WorkspaceImage } from './WorkspaceFileReference';
import { isWorkspaceUri, resolveWorkspaceDocumentReference } from './workspaceUri';
import remarkChatMath from './remarkChatMath';
import ChatMath from './ChatMath';
import {mathSource} from './chatMathRender';
import {projectMathSelection} from './chatMathSelection';

const REMARK_PLUGINS = [remarkGfm, remarkChatMath];

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
  span({node, children, ...props}) {
    const source = node && mathSource(node);
    return source !== undefined
      ? <ChatMath source={source} display={node?.properties.dataMathDisplay === 'true'} closed={node?.properties.dataMathClosed === 'true'}/>
      : <span {...props}>{children}</span>;
  },
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
  publicView?: boolean;
  text: string;
  workspaceSessionId?: string;
  workspaceDocumentPath?: string;
  onAddImageMaterial?: (file: File) => void;
}

function workspaceUrlTransform(value: string): string {
  return isWorkspaceUri(value) ? value : defaultUrlTransform(value);
}

// [Sync] 2026-11-12: public snapshots reuse Markdown/math/Mermaid with inert file/image references.
export default memo(function ChatMarkdown({ text, workspaceSessionId, workspaceDocumentPath, onAddImageMaterial, publicView = false }: ChatMarkdownProps) {
  const { activeSessionId, workspaceConfigLoaded, workspaceEnabled } = useWorkspaceSession();
  const threadId = workspaceSessionId ?? activeSessionId ?? undefined;
  const workspaceAvailability = workspaceConfigLoaded
    ? (workspaceEnabled ? 'enabled' : 'disabled')
    : 'loading';
  const components = useMemo<Components>(() => ({
    ...BASE_COMPONENTS,
    a({ href, children, node, ...props }) {
      void node;
      if (publicView) return href && /^https?:\/\//i.test(href) ? <a href={href} target="_blank" rel="noopener noreferrer">{children}</a> : <span>{children}</span>;
      if (isWorkspaceUri(href)) {
        return (
          <WorkspaceFileLink uri={href} threadId={threadId} workspaceAvailability={workspaceAvailability} allowDocumentPreview={!workspaceDocumentPath}>
            {children}
          </WorkspaceFileLink>
        );
      }
      return <a href={href} {...props}>{children}</a>;
    },
    img({ src, alt, node, ...props }) {
      void node;
      if (publicView) return <span>{alt ?? ''}</span>;
      if (typeof src === 'string' && isWorkspaceUri(src)) {
        return <WorkspaceImage uri={src} alt={alt} threadId={threadId} workspaceAvailability={workspaceAvailability} onAddImageMaterial={onAddImageMaterial} />;
      }
      return <img src={src} alt={alt} {...props} />;
    },
  }), [threadId, workspaceAvailability, workspaceDocumentPath, onAddImageMaterial, publicView]);

  return (
    <div className="chat-markdown" style={publicView ? {maxWidth: '100%', overflowX: 'auto'} : undefined} onCopy={event => {
      if (event.defaultPrevented) return;
      const projection = projectMathSelection(event.currentTarget);
      if (!projection) return;
      event.clipboardData.setData('text/plain', projection.text);
      event.clipboardData.setData('text/html', projection.html);
      event.preventDefault();
    }}>
      <ReactMarkdown remarkPlugins={REMARK_PLUGINS} components={components} urlTransform={(value) => workspaceUrlTransform(resolveWorkspaceDocumentReference(value, workspaceDocumentPath))}>
        {text}
      </ReactMarkdown>
    </div>
  );
});

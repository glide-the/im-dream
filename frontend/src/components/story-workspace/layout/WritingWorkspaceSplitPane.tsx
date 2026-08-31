// [Input] Writing canvas content, an optional canonical Thread Chat surface, viewport mode, and close callback.
// [Output] Render the Story Workspace writing canvas with an accessible resizable right-side Chat panel.
// [Pos] Writing-specific split-pane composition inside the Story Workspace layout region.
// [Sync] 2026-08-31: replace inline writing chat expansion with the related Thread's resizable Chat surface.
import { useLayoutEffect, useRef, type CSSProperties, type ReactNode } from 'react';
import { useResizableRightPanel } from '../../../hooks/useResizableRightPanel';
import './StoryWorkspaceLayout.css';

const DEFAULT_CHAT_PANEL_WIDTH_PX = 560;
const MIN_CHAT_PANEL_WIDTH_PX = 360;
const MAX_CHAT_PANEL_WIDTH_PX = 840;
const MIN_WRITING_CANVAS_WIDTH_PX = 420;
const CHAT_PANEL_WIDTH_STORAGE_KEY = 'ink-dream:story-workspace:writing-chat-width';

export interface WritingWorkspaceSplitPaneProps {
  children: ReactNode;
  chat: ReactNode;
  chatOpen: boolean;
  isMobile: boolean;
  onCloseChat: () => void;
}

export function WritingWorkspaceSplitPane({
  children,
  chat,
  chatOpen,
  isMobile,
  onCloseChat,
}: WritingWorkspaceSplitPaneProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const resize = useResizableRightPanel({
    defaultWidth: DEFAULT_CHAT_PANEL_WIDTH_PX,
    minWidth: MIN_CHAT_PANEL_WIDTH_PX,
    maxWidth: MAX_CHAT_PANEL_WIDTH_PX,
    minSiblingWidth: MIN_WRITING_CANVAS_WIDTH_PX,
    storageKey: CHAT_PANEL_WIDTH_STORAGE_KEY,
    getAvailableWidth: () => containerRef.current?.clientWidth ?? window.innerWidth,
  });
  const finishResize = resize.finishResize;
  const reclampWidth = resize.reclampWidth;

  useLayoutEffect(() => {
    reclampWidth();
  }, [reclampWidth]);

  useLayoutEffect(() => {
    if (!chatOpen) finishResize();
  }, [chatOpen, finishResize]);

  const panelWidth = isMobile ? '100%' : `${resize.width}px`;
  const exposedPanelWidth = chatOpen && !isMobile ? `${resize.width}px` : '0px';

  return (
    <div
      className="story-workspace-writing-split"
      data-chat-panel-state={chatOpen ? 'open' : 'closed'}
      ref={containerRef}
      style={{ '--story-workspace-writing-chat-width': exposedPanelWidth } as CSSProperties}
    >
      <section className="story-workspace-writing-split__canvas">
        {children}
      </section>

      {chatOpen ? (
        <aside
          aria-label="Writing Thread Chat"
          className="story-workspace-writing-split__chat"
          style={{ width: panelWidth, minWidth: panelWidth }}
        >
          {!isMobile ? (
            <div
              aria-label="调整 Writing Chat 宽度；可使用方向键，双击恢复默认宽度"
              aria-orientation="vertical"
              aria-valuemax={Math.round(resize.bounds.max)}
              aria-valuemin={Math.round(resize.bounds.min)}
              aria-valuenow={Math.round(resize.width)}
              aria-valuetext={`${Math.round(resize.width)} px`}
              className={`story-workspace-writing-split__resize${resize.isResizing || resize.resizeRailActive ? ' story-workspace-writing-split__resize--active' : ''}`}
              onBlur={() => resize.setResizeRailActive(false)}
              onDoubleClick={resize.resetWidth}
              onFocus={() => resize.setResizeRailActive(true)}
              onKeyDown={resize.handleResizeKeyDown}
              onLostPointerCapture={resize.finishResize}
              onMouseEnter={() => resize.setResizeRailActive(true)}
              onMouseLeave={() => resize.setResizeRailActive(false)}
              onPointerCancel={resize.handleResizePointerEnd}
              onPointerDown={resize.handleResizePointerDown}
              onPointerMove={resize.handleResizePointerMove}
              onPointerUp={resize.handleResizePointerEnd}
              role="separator"
              tabIndex={0}
              title="拖动调整 Chat 宽度；双击恢复默认宽度"
            >
              <span aria-hidden="true" />
            </div>
          ) : null}

          <header className="story-workspace-writing-split__chat-header">
            <div>
              <strong>Thread Chat</strong>
              <span>与当前写作片段关联的对话</span>
            </div>
            <button aria-label="关闭 Writing Thread Chat" onClick={onCloseChat} type="button">
              ×
            </button>
          </header>
          <div className="story-workspace-writing-split__chat-content">
            {chat}
          </div>
        </aside>
      ) : null}
    </div>
  );
}

// [Input] Writing layout, last prose editor, mood chooser state and scroll tracking.
// [Output] Plain writing surface. Empty-space clicks continue the last text cell.
// [Pos] Shared Writing canvas for the desktop and narrow layouts.
import type {ReactNode, RefObject} from 'react';

interface NotebookLinesProps {
  mobile: boolean;
  inert: boolean;
  scrollRef: RefObject<HTMLDivElement | null>;
  onScrollTop: (top: number) => void;
  onBlankPaper: (clientY: number) => void;
  children: ReactNode;
}

export default function NotebookLines({mobile, inert, scrollRef, onScrollTop, onBlankPaper, children}: NotebookLinesProps) {
  return <div className="notebook-lines" ref={scrollRef} inert={inert || undefined}
    onScroll={event => onScrollTop(event.currentTarget.scrollTop)}
    onClick={event => {
      if (event.target !== event.currentTarget || window.getSelection()?.isCollapsed === false) return;
      onBlankPaper(event.clientY);
    }}
    style={{flex: 1, minHeight: 0, position: 'relative', overflow: 'auto', padding: '20px',
      paddingLeft: mobile ? '20px' : '80px', paddingBottom: mobile ? '20px' : '80px',
      backgroundColor: 'var(--color-bg-paper)'}}>
    {children}
  </div>;
}

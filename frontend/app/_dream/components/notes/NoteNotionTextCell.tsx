// [Input] Live TextCell, its original editor, and the normal text/IME update callbacks.
// [Output] In-place article references, editable continuation rows and scoped reading.
// [Pos] Logical lines are derived from the same plain text that the session saves.
import {Fragment, useEffect, useImperativeHandle, useMemo, useReducer, useRef, useState, type ReactNode, type Ref} from 'react';
import {flushSync} from 'react-dom';
import {useTranslation} from 'react-i18next';
import NotionMark from '../NotionMark';
import NoteNotionArticleReader from './NoteNotionArticleReader';
import {findNotionArticleLinks, type NotionArticleLink} from './notionArticleLinks';
import {articleLines} from './notionArticleLines';
import './NoteNotionTextCell.css';

export interface NoteWritingHandle {
  continueAtEnd: (clientY: number) => void;
}

interface Props {
  content: string;
  documentActive: boolean;
  children: ReactNode;
  ref?: Ref<NoteWritingHandle>;
  onTextChange: (text: string) => void;
  onCompositionStart: () => void;
  onCompositionCommit: (text: string) => void;
}

// The suffix stays outside the editor even when a multiline paste grows the active passage.
type Passage = {first: number; following: number};

export default function NoteNotionTextCell({content, documentActive, children, ref, onTextChange, onCompositionStart, onCompositionCommit}: Props) {
  const {t} = useTranslation();
  const root = useRef<HTMLDivElement>(null);
  const rowInput = useRef<HTMLTextAreaElement>(null);
  const lastSelection = useRef<{start: number; end: number; row: boolean} | null>(null);
  const [sourceEditing, setSourceEditing] = useState(false);
  const [passage, setPassage] = useState<Passage | null>(null);
  const typing = useRef<number | null>(null);
  const [,refreshLinks] = useReducer((revision: number) => revision + 1, 0);
  const typingAt = typing.current;
  const [reading, setReading] = useState<NotionArticleLink | null>(null);
  const links = useMemo(() => findNotionArticleLinks(content), [content]);
  const lines = useMemo(() => articleLines(content, links), [content, links]);
  const last = passage ? lines.length - 1 - passage.following : -1;
  const editingRow = passage && passage.first <= last ? lines[passage.first] : undefined;
  const end = editingRow ? lines[last].end : 0;
  const draft = editingRow ? content.slice(editingRow.start, end) : '';
  const compact = !sourceEditing && (links.length > 0 || !!editingRow);
  const active = documentActive && reading && links.find(link => link.start === reading.start && link.href === reading.href);

  useEffect(() => { if (reading && !active) setReading(null); }, [reading, active]);

  function sourceEditor() { return root.current?.querySelector<HTMLTextAreaElement>('.note-article-source textarea'); }

  function focusSource(start: number, finish = start) {
    flushSync(() => {setPassage(null); setSourceEditing(true);});
    const textarea = sourceEditor();
    textarea?.focus({preventScroll: true});
    textarea?.setSelectionRange(start, finish);
  }

  // Mount the real, empty textarea during the click so touch keyboards can open in the same gesture.
  function focusRow(first: number, following: number, offset: number, next?: string) {
    flushSync(() => {
      if (next !== undefined && next !== content) onTextChange(next);
      setSourceEditing(false);
      typing.current = null;
      setPassage({first, following});
    });
    rowInput.current?.focus();
    rowInput.current?.setSelectionRange(offset, offset);
  }

  function continueAfter(index: number) {
    const anchor = lines[index];
    const target = anchor.text === '' ? index : index + 1;
    if (lines[target]?.text === '') {
      focusRow(target, lines.length - target - 1, 0);
    } else {
      focusRow(target, lines.length - target, 0, content.slice(0, anchor.end) + '\n' + content.slice(anchor.end));
    }
  }

  useImperativeHandle(ref, () => ({continueAtEnd(y) {
    if (!root.current || y < root.current.getBoundingClientRect().top) return;
    if (links.length || editingRow) continueAfter(lines.length - 1);
    else focusSource(content.length);
  }}));

  function article(link: NotionArticleLink) {
    return <span className="note-article" data-notion-page={link.pageId}>
      <button type="button" className="note-article-read" aria-haspopup="dialog"
        aria-label={t('noteArticle.read', {name: link.label})} title={link.href} onClick={() => setReading(link)}>
        <NotionMark className="note-article-mark"/><span className="note-article-label">{link.label}</span>
      </button>
      <a href={link.href} target="_blank" rel="noopener noreferrer" referrerPolicy="no-referrer"
        className="note-article-open" title={t('noteArticle.original')} aria-label={t('noteArticle.original')}>↗</a>
    </span>;
  }

  function lineView(index: number) {
    const line = lines[index];
    const prose = (start: number, finish: number) => start === finish ? null :
      <span className="note-article-prose" data-start={start}>{content.slice(start, finish)}</span>;
    return <div className="note-article-row" key={index} data-line={index} onClick={event => {
      if (!(event.target instanceof Element) || event.target.closest('button, a')) return;
      const caret = window.getSelection();
      if (caret && !caret.isCollapsed) return;
      const span = event.target.closest<HTMLElement>('.note-article-prose');
      if (!span && line.links.length) {continueAfter(index); return;}
      const offset = span ? Number(span.dataset.start) - line.start +
        (caret?.focusNode?.parentElement === span ? caret.focusOffset : (span.textContent?.length ?? 0)) : line.text.length;
      if (line.links.length) focusSource(line.start + offset);
      else focusRow(index, lines.length - 1 - index, offset);
    }}>
      {line.links.map((link, i) => <Fragment key={link.start}>
        {prose(i ? line.links[i - 1].end : line.start, link.start)}{article(link)}
      </Fragment>)}
      {prose(line.links.at(-1)?.end ?? line.start, line.end)}
    </div>;
  }

  const actionLinks = links.filter(link =>
    (!compact || (editingRow && link.start >= editingRow.start && link.end <= end)) &&
    (typingAt === null || typingAt <= link.start || typingAt > link.end));

  return <div ref={root} className="note-article-cell" data-compact={compact || undefined}
    onFocusCapture={event => {if (event.target instanceof HTMLTextAreaElement && event.target === sourceEditor()) {setPassage(null); setSourceEditing(true);}}}
    onBlurCapture={event => {
      if (event.target instanceof HTMLTextAreaElement) {
        lastSelection.current = {start: event.target.selectionStart, end: event.target.selectionEnd, row: event.target === rowInput.current};
        typing.current = null;
      }
      if (!event.currentTarget.contains(event.relatedTarget)) {
        setSourceEditing(false);
        if (event.relatedTarget && !reading) setPassage(null);
      }
    }}
    onInputCapture={event => {
      if (!(event.target instanceof HTMLTextAreaElement)) return;
      const input = event.nativeEvent as InputEvent;
      const start = event.target === rowInput.current ? editingRow?.start ?? 0 : 0;
      typing.current = input.isComposing || input.inputType === 'insertText' ? start + event.target.selectionStart : null;
    }}
    onSelectCapture={event => {
      if (!(event.target instanceof HTMLTextAreaElement)) return;
      const start = event.target === rowInput.current ? editingRow?.start ?? 0 : 0;
      if (typing.current !== null && typing.current !== start + event.target.selectionStart) {typing.current = null; refreshLinks();}
    }}
    onCompositionEnd={() => {typing.current = null;}}>
    <div className="note-article-source">{children}</div>
    {compact && <div className="note-article-projection">
      {lines.map((line, index) => {
        if (!editingRow || !passage || index < passage.first || index > last) return lineView(index);
        if (index !== passage.first) return null;
        const assemble = (value: string) => content.slice(0, line.start) + value + content.slice(end);
        return <div className="note-article-row note-article-row--editing" key={index} data-line={index}>
          <div className="note-article-input-wrap">
            <span aria-hidden="true">{draft + '\u200b'}</span>
            <textarea ref={rowInput} className="note-article-row-input" rows={1} value={draft}
              aria-label={t('noteArticle.line', {number: index + 1})}
              onChange={event => onTextChange(assemble(event.currentTarget.value))}
              onCompositionStart={onCompositionStart} onCompositionEnd={event => onCompositionCommit(assemble(event.currentTarget.value))}
              onKeyDown={event => {
                if (event.nativeEvent.isComposing) return;
                const input = event.currentTarget;
                const start = input.selectionStart, finish = input.selectionEnd;
                if (event.key === 'Enter' && !event.shiftKey) {
                  event.preventDefault();
                  const next = assemble(draft.slice(0, start) + '\n' + draft.slice(finish));
                  const first = index + draft.slice(0, start).split('\n').length;
                  focusRow(first, next.split('\n').length - first - 1, 0, next);
                } else if ((event.key === 'Backspace' && start === 0 && finish === 0 && line.start > 0) ||
                    ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'a') || event.key === '@') {
                  // Cross-row editing and Writing shortcuts use the full editor and its original handlers.
                  focusSource(line.start + start, line.start + finish);
                  if (event.key === '@') sourceEditor()?.dispatchEvent(new KeyboardEvent('keydown', {key:'@', bubbles:true}));
                } else if ((event.key === 'ArrowUp' && start === 0 && index > 0) ||
                    (event.key === 'ArrowDown' && finish === draft.length && last + 1 < lines.length)) {
                  event.preventDefault();
                  const target = event.key === 'ArrowUp' ? index - 1 : last + 1;
                  focusRow(target, lines.length - target - 1, Math.min(start, lines[target].text.length));
                }
              }}/>
          </div>
          {actionLinks.length > 0 && <div>{actionLinks.map(link => <Fragment key={link.start}>{article(link)}</Fragment>)}</div>}
        </div>;
      })}
    </div>}
    {!compact && actionLinks.length > 0 && <div className="note-article-projection">
      {lines.map((line, index) => {
        const visible = line.links.filter(link => typingAt === null || typingAt <= link.start || typingAt > link.end);
        if (!visible.length) return null;
        return <div className="note-article-row" data-line={index} key={index} onClick={event => {
          if (event.target instanceof Element && !event.target.closest('button, a')) continueAfter(index);
        }}>{visible.map(link => <Fragment key={link.start}>{article(link)}</Fragment>)}</div>;
      })}
    </div>}
    {compact && !editingRow && <button type="button" className="note-article-edit" onClick={() => continueAfter(lines.length - 1)}>{t('noteArticle.continueWriting')}</button>}
    {active && <NoteNotionArticleReader key={active.href} link={active} onClose={() => {
      setReading(null);
      const selection = lastSelection.current;
      requestAnimationFrame(() => {
        if (selection?.row && rowInput.current) {
          rowInput.current.focus();
          rowInput.current.setSelectionRange(selection.start, selection.end);
        } else {focusSource(selection?.start ?? active.end, selection?.end ?? active.end);}
      });
    }}/>}
  </div>;
}

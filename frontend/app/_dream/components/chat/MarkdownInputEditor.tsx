// [Sync] 2026-11-08: parse supported Markdown into native paste/undo transactions; retain unsupported source and explicit plain/HTML/file/code paste.
// [Sync] 2026-10-29: skip effects for a destroyed Tiptap instance during placeholder-driven recreation and initial native prefill.
// [Input] User-authored rich text, Markdown value, and composer keyboard/focus callbacks.
// [Output] Accessible Tiptap composer that round-trips user input to Markdown and exposes optional autocomplete semantics.
// [Pos] markdown-input-editor component node in frontend/app/_dream/components/chat
// [Sync] 2026-08-06: replace the plain chat textarea with a Markdown-aware editor so user-authored
//                    paragraphs, lists, inline code, and placeholder paths survive the user bubble round trip.
// [Sync] 2026-08-13: expose listbox ARIA attributes for installed-Skill slash suggestions.
// [Sync] 2026-09-11: create the Tiptap editor only after client mount
//                    (immediatelyRender: false) so Next.js SSR never renders or
//                    hydrates the composer before the browser runtime exists.
// [Sync] 2026-09-27: suppress repeated Tiptap DOM-observer updates before they can re-enter controlled composer state.
import { useEffect, useRef, type FocusEventHandler, type KeyboardEventHandler } from 'react';
import Placeholder from '@tiptap/extension-placeholder';
import { Markdown } from '@tiptap/markdown';
import { closeHistory } from '@tiptap/pm/history';
import { Slice } from '@tiptap/pm/model';
import { EditorContent, useEditor } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import './MarkdownInputEditor.css';

interface MarkdownInputEditorProps {
  id: string;
  value: string;
  placeholder: string;
  ariaLabel: string;
  ariaDescribedBy?: string;
  ariaControls?: string;
  ariaActiveDescendant?: string;
  ariaAutocomplete?: 'list';
  disabled?: boolean;
  onChange: (markdown: string) => void;
  onKeyDown?: KeyboardEventHandler<HTMLDivElement>;
  onFocus?: FocusEventHandler<HTMLDivElement>;
  onBlur?: FocusEventHandler<HTMLDivElement>;
}

export default function MarkdownInputEditor({
  id,
  value,
  placeholder,
  ariaLabel,
  ariaDescribedBy,
  ariaControls,
  ariaActiveDescendant,
  ariaAutocomplete,
  disabled = false,
  onChange,
  onKeyDown,
  onFocus,
  onBlur,
}: MarkdownInputEditorProps) {
  const valueRef = useRef(value);
  const onChangeRef = useRef(onChange);
  const pasteAsPlainTextRef = useRef(false);
  valueRef.current = value;
  onChangeRef.current = onChange;

  const editor = useEditor({
    immediatelyRender: false,
    extensions: [
      StarterKit,
      Placeholder.configure({ placeholder }),
      Markdown,
    ],
    content: value,
    contentType: 'markdown',
    editable: !disabled,
    editorProps: {
      attributes: {
        id,
        role: 'textbox',
        'aria-label': ariaLabel,
        'aria-multiline': 'true',
        class: 'markdown-input-editor__content',
      },
    },
    onUpdate: ({ editor: currentEditor }) => {
      const markdown = currentEditor.getMarkdown();
      if (markdown === valueRef.current) {
        return;
      }
      valueRef.current = markdown;
      onChangeRef.current(markdown);
    },
  }, [placeholder]);

  useEffect(() => {
    valueRef.current = value;
    if (!editor || editor.isDestroyed || editor.getMarkdown() === value) {
      return;
    }
    editor.commands.setContent(value, {
      contentType: 'markdown',
      emitUpdate: false,
    });
  }, [editor, value]);

  useEffect(() => {
    if (editor && !editor.isDestroyed) editor.setEditable(!disabled);
  }, [disabled, editor]);

  useEffect(() => {
    if (!editor || editor.isDestroyed) {
      return;
    }
    editor.setOptions({
      editorProps: {
        transformPastedText: (text, plainText) => {
          pasteAsPlainTextRef.current = plainText;
          return text;
        },
        handlePaste: (view, event) => {
          const clipboard = event.clipboardData;
          if (
            event.defaultPrevented
            || !editor.isEditable
            || pasteAsPlainTextRef.current
            || !clipboard
            || clipboard.files.length > 0
            || clipboard.getData('text/html')
            || editor.isActive('codeBlock')
            || editor.isActive('code')
          ) {
            return false;
          }
          const text = clipboard.getData('text/plain');
          if (!text || !editor.markdown) return false;
          const transaction = closeHistory(view.state.tr);
          try {
            let unsupportedContent = false;
            editor.markdown.instance.walkTokens(editor.markdown.instance.lexer(text), (token) => {
              if (
                (token.type === 'table' && !editor.schema.nodes.table)
                || (token.type === 'image' && !editor.schema.nodes.image)
                || (token.type === 'list_item' && token.task && !editor.schema.nodes.taskItem)
              ) {
                unsupportedContent = true;
              }
            });
            if (unsupportedContent) return false;
            const document = editor.schema.nodeFromJSON(editor.markdown.parse(text));
            document.check();
            transaction.replaceSelection(Slice.maxOpen(document.content))
              .scrollIntoView()
              .setMeta('paste', true)
              .setMeta('uiEvent', 'paste');
          } catch {
            // Let Tiptap retain the clipboard text when Markdown parsing fails.
            return false;
          }
          view.dispatch(transaction);
          return true;
        },
        attributes: {
          id,
          role: 'textbox',
          'aria-label': ariaLabel,
          ...(ariaControls ? { 'aria-controls': ariaControls } : {}),
          ...(ariaActiveDescendant ? { 'aria-activedescendant': ariaActiveDescendant } : {}),
          ...(ariaAutocomplete ? { 'aria-autocomplete': ariaAutocomplete } : {}),
          ...(ariaDescribedBy ? { 'aria-describedby': ariaDescribedBy } : {}),
          'aria-disabled': String(disabled),
          'aria-multiline': 'true',
          class: 'markdown-input-editor__content',
        },
      },
    });
  }, [
    ariaActiveDescendant,
    ariaAutocomplete,
    ariaControls,
    ariaDescribedBy,
    ariaLabel,
    disabled,
    editor,
    id,
  ]);

  return (
    <div
      className="markdown-input-editor"
      data-testid="markdown-input-editor"
      onKeyDownCapture={onKeyDown}
      onFocus={onFocus}
      onBlur={onBlur}
    >
      <EditorContent editor={editor} />
    </div>
  );
}

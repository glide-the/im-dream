// [Input] User-authored rich text, Markdown value, and composer keyboard/focus callbacks.
// [Output] Accessible Tiptap composer that round-trips user input to Markdown for chat transport and rendering.
// [Pos] markdown-input-editor component node in frontend/src/components/chat
// [Sync] 2026-08-06: replace the plain chat textarea with a Markdown-aware editor so user-authored
//                    paragraphs, lists, inline code, and placeholder paths survive the user bubble round trip.
import { useEffect, type FocusEventHandler, type KeyboardEventHandler } from 'react';
import Placeholder from '@tiptap/extension-placeholder';
import { Markdown } from '@tiptap/markdown';
import { EditorContent, useEditor } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import './MarkdownInputEditor.css';

interface MarkdownInputEditorProps {
  id: string;
  value: string;
  placeholder: string;
  ariaLabel: string;
  ariaDescribedBy?: string;
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
  disabled = false,
  onChange,
  onKeyDown,
  onFocus,
  onBlur,
}: MarkdownInputEditorProps) {
  const editor = useEditor({
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
      onChange(currentEditor.getMarkdown());
    },
  }, [placeholder]);

  useEffect(() => {
    if (!editor || editor.getMarkdown() === value) {
      return;
    }
    editor.commands.setContent(value, {
      contentType: 'markdown',
      emitUpdate: false,
    });
  }, [editor, value]);

  useEffect(() => {
    editor?.setEditable(!disabled);
  }, [disabled, editor]);

  useEffect(() => {
    if (!editor) {
      return;
    }
    editor.setOptions({
      editorProps: {
        attributes: {
          id,
          role: 'textbox',
          'aria-label': ariaLabel,
          ...(ariaDescribedBy ? { 'aria-describedby': ariaDescribedBy } : {}),
          'aria-disabled': String(disabled),
          'aria-multiline': 'true',
          class: 'markdown-input-editor__content',
        },
      },
    });
  }, [ariaDescribedBy, ariaLabel, disabled, editor, id]);

  return (
    <div
      className="markdown-input-editor"
      data-testid="markdown-input-editor"
      onKeyDown={onKeyDown}
      onFocus={onFocus}
      onBlur={onBlur}
    >
      <EditorContent editor={editor} />
    </div>
  );
}

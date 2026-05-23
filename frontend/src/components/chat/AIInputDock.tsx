import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ChangeEvent,
  type ClipboardEvent,
  type DragEvent,
  type KeyboardEvent,
} from 'react';
import { IconArrowUp, IconFile, IconLoader, IconStop, IconX } from './Icons';
import { shouldSendMessageOnKeyDown } from './interaction-utils';

export interface UploadedFile {
  id: string;
  name: string;
  mimeType: string;
  size: number;
  previewUrl?: string;
  url?: string;
  storageKey?: string;
  dataUrl?: string;
  progress?: number;
  isUploading?: boolean;
  abortController?: AbortController;
  file?: File;
  workspacePath?: string;
  savedAt?: string;
  hash?: string;
  uploadSource?: 'click' | 'paste' | 'drag';
}

export interface Attachment {
  name: string;
  type: string;
  size: number;
  url?: string;
  storageKey?: string;
  workspacePath?: string;
  savedAt?: string;
  hash?: string;
  uploadSource?: 'click' | 'paste' | 'drag';
}

export function toAttachment(file: UploadedFile): Attachment {
  return {
    name: file.name,
    type: file.mimeType,
    size: file.size,
    url: file.url,
    storageKey: file.storageKey,
    workspacePath: file.workspacePath,
    savedAt: file.savedAt,
    hash: file.hash,
    uploadSource: file.uploadSource,
  };
}

export interface ContextCustomer {
  id: string;
  name?: string;
  company?: string;
}

export type ToolChoice = 'auto' | 'none' | 'manual';
export type AIInputDockMode = 'simple' | 'full';

interface AIInputDockProps {
  contextCustomerId?: string;
  contextCustomers?: ContextCustomer[];
  onSendMessage: (
    message: string,
    files?: UploadedFile[],
    customerIds?: string[],
    toolChoice?: ToolChoice,
  ) => void;
  placeholder?: string;
  disabled?: boolean;
  loading?: boolean;
  defaultToolChoice?: ToolChoice;
  openFileDialogSignal?: number;
  onStop?: () => void;
  mode?: AIInputDockMode;
  workspaceSessionId?: string;
}

let fileDialogOpenLocked = false;

export function shouldHandleOpenFileDialogSignal(signal: number | undefined, lastHandledSignal: number): signal is number {
  return typeof signal === 'number' && signal > 0 && signal !== lastHandledSignal;
}

export function runWithFileDialogTaskLock(callback: () => void): boolean {
  if (fileDialogOpenLocked) return false;
  fileDialogOpenLocked = true;
  callback();
  queueMicrotask(() => {
    fileDialogOpenLocked = false;
  });
  return true;
}

function generateFileId(): string {
  return `file_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function revokeObjectPreviewUrl(url?: string): void {
  if (url?.startsWith('blob:')) {
    URL.revokeObjectURL(url);
  }
}

const QUERY_INPUT_MAX_HEIGHT = 320;
const QUERY_INPUT_MIN_HEIGHT = 72;

export function shouldShowUploadHint(query: string, isInputFocused: boolean): boolean {
  return query.length === 0 && !isInputFocused;
}

function shouldSendWithKeyboard(mode: AIInputDockMode, event: KeyboardEvent<HTMLInputElement | HTMLTextAreaElement>): boolean {
  if (event.nativeEvent.isComposing) return false;
  if (mode === 'full') {
    return shouldSendMessageOnKeyDown({
      key: event.key,
      metaKey: event.metaKey || event.ctrlKey,
      shiftKey: event.shiftKey,
      isComposing: event.nativeEvent.isComposing,
    });
  }
  return event.key === 'Enter' && !event.shiftKey;
}

export default function AIInputDock({
  contextCustomerId,
  contextCustomers = [],
  onSendMessage,
  placeholder = 'Ask Ink & Memory…',
  disabled = false,
  loading = false,
  defaultToolChoice = 'auto',
  openFileDialogSignal,
  onStop,
  mode = 'simple',
  workspaceSessionId,
}: AIInputDockProps) {
  const [query, setQuery] = useState('');
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
  const [isDragOver, setIsDragOver] = useState(false);
  const [isInputFocused, setIsInputFocused] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const queryInputRef = useRef<HTMLTextAreaElement>(null);
  const lastHandledOpenFileDialogSignalRef = useRef(0);

  const openAttachmentDialog = useCallback(() => {
    runWithFileDialogTaskLock(() => {
      fileInputRef.current?.click();
    });
  }, []);

  useEffect(() => {
    if (!shouldHandleOpenFileDialogSignal(openFileDialogSignal, lastHandledOpenFileDialogSignalRef.current)) return;
    lastHandledOpenFileDialogSignalRef.current = openFileDialogSignal;
    openAttachmentDialog();
  }, [openAttachmentDialog, openFileDialogSignal]);

  useEffect(() => () => {
    uploadedFiles.forEach((file) => revokeObjectPreviewUrl(file.previewUrl));
  }, [uploadedFiles]);

  const handleFiles = useCallback((files: FileList | null, uploadSource: 'click' | 'paste' | 'drag') => {
    if (!files?.length) return;
    const maxFileSize = 50 * 1024 * 1024;
    const nextFiles: UploadedFile[] = [];

    Array.from(files).forEach((file) => {
      if (file.size > maxFileSize) {
        setUploadError(`${file.name}: file too large (max 50MB)`);
        return;
      }

      const previewUrl = file.type.startsWith('image/') ? URL.createObjectURL(file) : undefined;
      nextFiles.push({
        id: generateFileId(),
        name: file.name,
        mimeType: file.type || 'application/octet-stream',
        size: file.size,
        previewUrl,
        url: previewUrl,
        file,
        isUploading: false,
        progress: 100,
        uploadSource,
        workspacePath: workspaceSessionId ? `workspace/${file.name}` : undefined,
      });
    });

    if (!nextFiles.length) return;
    setUploadError(null);
    setUploadedFiles((current) => [...current, ...nextFiles]);
  }, [workspaceSessionId]);

  const deleteFile = useCallback((fileId: string) => {
    setUploadedFiles((current) => {
      const target = current.find((file) => file.id === fileId);
      revokeObjectPreviewUrl(target?.previewUrl);
      return current.filter((file) => file.id !== fileId);
    });
  }, []);

  const handleFileInputChange = useCallback((event: ChangeEvent<HTMLInputElement>) => {
    handleFiles(event.target.files, 'click');
    event.target.value = '';
  }, [handleFiles]);

  const handleDragOver = useCallback((event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback((event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setIsDragOver(false);
    handleFiles(event.dataTransfer.files, 'drag');
  }, [handleFiles]);

  const handlePaste = useCallback((event: ClipboardEvent<HTMLDivElement>) => {
    const clipboardFiles = event.clipboardData?.files;
    if (!clipboardFiles?.length) return;
    event.preventDefault();
    handleFiles(clipboardFiles, 'paste');
  }, [handleFiles]);

  const updateQueryInputHeight = useCallback(() => {
    const input = queryInputRef.current;
    if (!input) return;
    input.style.height = 'auto';
    const nextHeight = Math.min(Math.max(input.scrollHeight, QUERY_INPUT_MIN_HEIGHT), QUERY_INPUT_MAX_HEIGHT);
    input.style.height = `${nextHeight}px`;
    input.style.overflowY = input.scrollHeight > QUERY_INPUT_MAX_HEIGHT ? 'auto' : 'hidden';
  }, []);

  useEffect(() => {
    updateQueryInputHeight();
  }, [query, updateQueryInputHeight]);

  const handleSend = useCallback(() => {
    if (loading) return;
    const trimmedQuery = query.trim();
    if (!trimmedQuery && uploadedFiles.length === 0) return;

    const customerIds = contextCustomers.map((customer) => customer.id);
    if (contextCustomerId && !customerIds.includes(contextCustomerId)) customerIds.push(contextCustomerId);

    onSendMessage(trimmedQuery, uploadedFiles.length ? uploadedFiles : undefined, customerIds, defaultToolChoice);
    setQuery('');
    uploadedFiles.forEach((file) => revokeObjectPreviewUrl(file.previewUrl));
    setUploadedFiles([]);
  }, [contextCustomerId, contextCustomers, defaultToolChoice, loading, onSendMessage, query, uploadedFiles]);

  const showUploadHint = shouldShowUploadHint(query, isInputFocused);
  const canSend = useMemo(() => !loading && !disabled && (query.trim().length > 0 || uploadedFiles.length > 0), [disabled, loading, query, uploadedFiles.length]);

  return (
    <div
      data-mode={mode}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      onPaste={handlePaste}
      style={{
        width: '100%',
        minWidth: 0,
        padding: '1rem',
        borderRadius: '12px 12px 0 0',
        border: `1px solid ${isDragOver ? 'var(--color-border-focus)' : 'var(--color-border-paper)'}`,
        background: isDragOver ? 'rgba(74, 144, 226, 0.08)' : 'var(--color-bg-paper)',
        boxShadow: '0 -10px 30px var(--color-shadow-soft)',
        transition: 'all 0.2s ease',
        boxSizing: 'border-box',
      }}
    >
      <input
        ref={fileInputRef}
        type="file"
        multiple
        accept=".pdf,.txt,.md,.csv,.json,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.zip,.rar,.7z,.tar,.gz,.mp3,.wav,.m4a,.ogg,.mp4,.webm,.mov,image/*"
        onChange={handleFileInputChange}
        disabled={disabled}
        style={{ display: 'none' }}
      />

      {uploadError ? <div style={{ marginBottom: '0.75rem', borderRadius: '10px', padding: '0.65rem 0.8rem', background: 'rgba(244,67,54,0.12)', color: 'var(--color-state-error)', fontSize: '0.85rem' }}>{uploadError}</div> : null}

      {uploadedFiles.length > 0 ? (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.6rem', marginBottom: '0.85rem' }}>
          {uploadedFiles.map((file) => {
            const isImage = file.mimeType.startsWith('image/');
            const extension = file.name.split('.').pop()?.toUpperCase() || 'FILE';
            return (
              <div key={file.id} style={{ position: 'relative', overflow: 'hidden', borderRadius: '12px', border: '1px solid var(--color-border-paper)', background: 'var(--color-bg-surface-solid)' }}>
                {isImage && file.previewUrl ? (
                  <img src={file.previewUrl} alt={file.name} style={{ display: 'block', width: '80px', height: '80px', objectFit: 'cover' }} />
                ) : (
                  <div style={{ width: '120px', height: '80px', padding: '0.5rem', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', textAlign: 'center', background: 'var(--color-bg-surface)' }}>
                    <IconFile style={{ width: '1.5rem', height: '1.5rem', color: 'var(--color-text-muted)', marginBottom: '0.2rem' }} />
                    <span style={{ width: '100%', fontSize: '0.65rem', fontWeight: 600, color: 'var(--color-text-secondary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{file.name}</span>
                    <span style={{ fontSize: '0.6rem', color: 'var(--color-text-muted)' }}>{extension} · {formatFileSize(file.size)}</span>
                  </div>
                )}
                <button type="button" onClick={() => deleteFile(file.id)} aria-label={`Remove ${file.name}`} style={{ position: 'absolute', top: '0.35rem', right: '0.35rem', width: '1.6rem', height: '1.6rem', border: 'none', borderRadius: '999px', background: 'rgba(255,255,255,0.85)', color: 'var(--color-state-danger)', cursor: 'pointer', display: 'grid', placeItems: 'center' }}>
                  <IconX style={{ width: '0.9rem', height: '0.9rem' }} />
                </button>
              </div>
            );
          })}
        </div>
      ) : null}

      {(showUploadHint || mode === 'full') ? (
        <div style={{ marginBottom: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.75rem', fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>
          {showUploadHint ? <span id="chat-upload-hint">Paste, drag, or attach files</span> : null}
          {mode === 'full' ? <span style={{ marginLeft: 'auto' }}>⌘/Ctrl + Enter sends</span> : null}
        </div>
      ) : null}

      <textarea
        id="chat-input"
        ref={queryInputRef}
        aria-label="Chat input"
        aria-describedby={showUploadHint ? 'chat-upload-hint' : undefined}
        placeholder={placeholder}
        value={query}
        rows={1}
        onChange={(event) => setQuery(event.target.value)}
        onFocus={() => setIsInputFocused(true)}
        onBlur={() => setIsInputFocused(false)}
        disabled={disabled}
        onKeyDown={(event) => {
          if (!shouldSendWithKeyboard(mode, event)) return;
          event.preventDefault();
          handleSend();
        }}
        style={{ width: '100%', minHeight: '72px', border: 'none', outline: 'none', resize: 'none', background: 'transparent', color: 'var(--color-text-primary)', fontSize: '1rem', lineHeight: 1.6, fontFamily: "'Excalifont', 'Xiaolai', Georgia, serif", boxSizing: 'border-box' }}
      />

      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.75rem', marginTop: '0.75rem' }}>
        <button type="button" aria-label="Add attachment" onClick={openAttachmentDialog} disabled={disabled} style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem', border: '1px solid var(--color-border-paper)', borderRadius: '999px', padding: '0.55rem 0.85rem', background: 'var(--color-bg-surface-solid)', color: 'var(--color-text-secondary)', cursor: disabled ? 'not-allowed' : 'pointer' }}>
          <IconFile style={{ width: '1rem', height: '1rem' }} />
          Add
        </button>

        {loading && onStop ? (
          <button type="button" onClick={onStop} title="Stop generating" aria-label="Stop generating" style={{ display: 'grid', placeItems: 'center', width: '2.4rem', height: '2.4rem', border: 'none', borderRadius: '999px', background: 'var(--color-state-danger)', color: '#fff', cursor: 'pointer' }}>
            <IconStop style={{ width: '1rem', height: '1rem' }} />
          </button>
        ) : (
          <button type="button" onClick={handleSend} disabled={!canSend} title="Send" aria-label="Send message" style={{ display: 'grid', placeItems: 'center', width: '2.5rem', height: '2.5rem', border: 'none', borderRadius: '999px', background: canSend ? 'var(--color-action-link)' : 'var(--color-disabled-bg)', color: '#fff', cursor: canSend ? 'pointer' : 'not-allowed', transition: 'transform 0.2s ease' }}>
            {loading ? <IconLoader style={{ width: '1rem', height: '1rem' }} /> : <IconArrowUp style={{ width: '1rem', height: '1rem' }} />}
          </button>
        )}
      </div>
    </div>
  );
}

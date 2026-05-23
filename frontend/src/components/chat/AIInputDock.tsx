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
import { useFileUpload } from '../../hooks/useFileUpload';
import { toFileProxyUrl } from '../../lib/toFileProxyUrl';
import { IconArrowUp, IconFile, IconLoader, IconStop, IconX } from './Icons';
import { shouldSendMessageOnKeyDown } from './interaction-utils';

const API_BASE = '/ink-and-memory';

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
    url: file.storageKey ? toFileProxyUrl(file.storageKey) : file.url,
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
const QUERY_INPUT_MAX_HEIGHT = 320;
const QUERY_INPUT_MIN_HEIGHT = 72;
const MAX_UPLOAD_FILE_SIZE_BYTES = 50 * 1024 * 1024;

export function shouldHandleOpenFileDialogSignal(
  signal: number | undefined,
  lastHandledSignal: number,
): signal is number {
  return typeof signal === 'number' && signal > 0 && signal !== lastHandledSignal;
}

export function runWithFileDialogTaskLock(callback: () => void): boolean {
  if (fileDialogOpenLocked) {
    return false;
  }
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

function revokeObjectPreviewUrl(url?: string) {
  if (url?.startsWith('blob:')) {
    URL.revokeObjectURL(url);
  }
}

export function shouldShowUploadHint(query: string, isInputFocused: boolean): boolean {
  return query.length === 0 && !isInputFocused;
}

function shouldSendWithKeyboard(
  mode: AIInputDockMode,
  event: KeyboardEvent<HTMLInputElement | HTMLTextAreaElement>,
): boolean {
  if (event.nativeEvent.isComposing) {
    return false;
  }
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
  const { upload, error: uploadHookError } = useFileUpload();

  const openAttachmentDialog = useCallback(() => {
    runWithFileDialogTaskLock(() => {
      fileInputRef.current?.click();
    });
  }, []);

  useEffect(() => {
    if (
      !shouldHandleOpenFileDialogSignal(
        openFileDialogSignal,
        lastHandledOpenFileDialogSignalRef.current,
      )
    ) {
      return;
    }
    lastHandledOpenFileDialogSignalRef.current = openFileDialogSignal;
    openAttachmentDialog();
  }, [openAttachmentDialog, openFileDialogSignal]);

  useEffect(
    () => () => {
      uploadedFiles.forEach((file) => revokeObjectPreviewUrl(file.previewUrl));
    },
    [uploadedFiles],
  );

  const syncFileToWorkspace = useCallback(
    async (file: File) => {
      if (!workspaceSessionId) {
        return undefined;
      }

      const formData = new FormData();
      formData.set('sessionId', workspaceSessionId);
      formData.set('path', 'files');
      formData.append('file', file);

      const response = await fetch(`${API_BASE}/api/workspace/files`, {
        method: 'POST',
        body: formData,
      });

      const responseBody = (await response.json().catch(() => ({}))) as {
        error?: string;
        code?: string;
        uploaded?: string[];
        files?: Array<{ workspacePath: string; savedAt: string; hash?: string }>;
      };

      if (!response.ok) {
        const message = responseBody.error || '工作空间文件同步失败';
        throw new Error(responseBody.code ? `${message} (${responseBody.code})` : message);
      }

      const metadata = responseBody.files?.[0];
      if (metadata?.workspacePath) {
        return metadata;
      }

      const fallbackPath = responseBody.uploaded?.[0];
      if (!fallbackPath) {
        return undefined;
      }

      return { workspacePath: fallbackPath, savedAt: new Date().toISOString() };
    },
    [workspaceSessionId],
  );

  const uploadFileToStorage = useCallback(
    async (fileId: string, file: File) => {
      try {
        const workspaceMetadata = await syncFileToWorkspace(file);
        const result = await upload(file, {
          filename: file.name,
          contentType: file.type || 'application/octet-stream',
          onProgress: (progress) => {
            setUploadedFiles((prev) =>
              prev.map((entry) => (entry.id === fileId ? { ...entry, progress } : entry)),
            );
          },
        });

        if (!result) {
          setUploadedFiles((prev) => prev.filter((entry) => entry.id !== fileId));
          return;
        }

        setUploadedFiles((prev) =>
          prev.map((entry) =>
            entry.id === fileId
              ? {
                  ...entry,
                  url: result.url,
                  storageKey: result.key,
                  progress: 100,
                  isUploading: false,
                  workspacePath: workspaceMetadata?.workspacePath,
                  savedAt: workspaceMetadata?.savedAt,
                  hash: workspaceMetadata?.hash,
                }
              : entry,
          ),
        );
      } catch (error) {
        setUploadedFiles((prev) => {
          const current = prev.find((entry) => entry.id === fileId);
          revokeObjectPreviewUrl(current?.previewUrl);
          return prev.filter((entry) => entry.id !== fileId);
        });
        setUploadError(error instanceof Error ? error.message : '上传失败');
      }
    },
    [syncFileToWorkspace, upload],
  );

  const handleFiles = useCallback(
    (files: FileList | null, uploadSource: 'click' | 'paste' | 'drag') => {
      if (!files?.length) {
        return;
      }

      const nextFiles: UploadedFile[] = [];
      const filesToUpload: Array<{ id: string; file: File }> = [];

      Array.from(files).forEach((file) => {
        if (file.size > MAX_UPLOAD_FILE_SIZE_BYTES) {
          setUploadError(`${file.name}: 文件过大 (最大 ${formatFileSize(MAX_UPLOAD_FILE_SIZE_BYTES)})`);
          return;
        }

        const id = generateFileId();
        const previewUrl = file.type.startsWith('image/') ? URL.createObjectURL(file) : undefined;
        nextFiles.push({
          id,
          name: file.name,
          mimeType: file.type || 'application/octet-stream',
          size: file.size,
          previewUrl,
          progress: 0,
          isUploading: true,
          file,
          uploadSource,
        });
        filesToUpload.push({ id, file });
      });

      if (!nextFiles.length) {
        return;
      }

      setUploadError(null);
      setUploadedFiles((prev) => [...prev, ...nextFiles]);
      filesToUpload.forEach(({ id, file }) => {
        void uploadFileToStorage(id, file);
      });
    },
    [uploadFileToStorage],
  );

  const deleteFile = useCallback((fileId: string) => {
    setUploadedFiles((prev) => {
      const target = prev.find((entry) => entry.id === fileId);
      revokeObjectPreviewUrl(target?.previewUrl);
      return prev.filter((entry) => entry.id !== fileId);
    });
  }, []);

  const handleFileInputChange = useCallback(
    (event: ChangeEvent<HTMLInputElement>) => {
      handleFiles(event.target.files, 'click');
      event.target.value = '';
    },
    [handleFiles],
  );

  const handleDragOver = useCallback((event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback(
    (event: DragEvent<HTMLDivElement>) => {
      event.preventDefault();
      setIsDragOver(false);
      handleFiles(event.dataTransfer.files, 'drag');
    },
    [handleFiles],
  );

  const handlePaste = useCallback(
    (event: ClipboardEvent<HTMLDivElement>) => {
      const clipboardFiles = event.clipboardData?.files;
      if (!clipboardFiles?.length) {
        return;
      }
      event.preventDefault();
      handleFiles(clipboardFiles, 'paste');
    },
    [handleFiles],
  );

  const updateQueryInputHeight = useCallback(() => {
    const input = queryInputRef.current;
    if (!input) {
      return;
    }
    input.style.height = 'auto';
    const nextHeight = Math.min(
      Math.max(input.scrollHeight, QUERY_INPUT_MIN_HEIGHT),
      QUERY_INPUT_MAX_HEIGHT,
    );
    input.style.height = `${nextHeight}px`;
    input.style.overflowY = input.scrollHeight > QUERY_INPUT_MAX_HEIGHT ? 'auto' : 'hidden';
  }, []);

  useEffect(() => {
    updateQueryInputHeight();
  }, [query, updateQueryInputHeight]);

  const handleSend = useCallback(() => {
    if (loading) {
      return;
    }
    if (uploadedFiles.some((file) => file.isUploading)) {
      setUploadError('请等待文件上传完成');
      return;
    }

    const trimmedQuery = query.trim();
    if (!trimmedQuery && uploadedFiles.length === 0) {
      return;
    }

    const customerIds = contextCustomers.map((customer) => customer.id);
    if (contextCustomerId && !customerIds.includes(contextCustomerId)) {
      customerIds.push(contextCustomerId);
    }

    onSendMessage(
      trimmedQuery,
      uploadedFiles.length > 0 ? uploadedFiles : undefined,
      customerIds,
      defaultToolChoice,
    );
    setQuery('');
    uploadedFiles.forEach((file) => revokeObjectPreviewUrl(file.previewUrl));
    setUploadedFiles([]);
  }, [
    contextCustomerId,
    contextCustomers,
    defaultToolChoice,
    loading,
    onSendMessage,
    query,
    uploadedFiles,
  ]);

  const hasUploadingFiles = uploadedFiles.some((file) => file.isUploading);
  const showUploadHint = shouldShowUploadHint(query, isInputFocused);
  const canSend = useMemo(
    () => !loading && !disabled && !hasUploadingFiles && (query.trim().length > 0 || uploadedFiles.length > 0),
    [disabled, hasUploadingFiles, loading, query, uploadedFiles.length],
  );

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
        borderRadius: '1.25rem',
        border: `1px solid ${isDragOver ? 'var(--color-action-link)' : 'var(--color-border-paper)'}`,
        background: isDragOver ? 'rgba(74,144,226,0.08)' : 'var(--color-bg-paper)',
        boxShadow: '0 4px 12px rgba(0,0,0,0.12)',
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

      {(uploadError || uploadHookError) ? (
        <div
          style={{
            marginBottom: '0.75rem',
            borderRadius: '0.75rem',
            padding: '0.65rem 0.8rem',
            background: 'rgba(217,83,79,0.1)',
            color: '#d9534f',
            fontSize: '0.85rem',
          }}
        >
          {uploadError || uploadHookError}
        </div>
      ) : null}

      {uploadedFiles.length > 0 ? (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', marginBottom: '0.75rem' }}>
          {uploadedFiles.map((file) => {
            const isImage = file.mimeType.startsWith('image/');
            const previewUrl = file.storageKey ? toFileProxyUrl(file.storageKey) : file.previewUrl;
            const displayExt = file.name.split('.').pop()?.toUpperCase() || 'FILE';
            return (
              <div
                key={file.id}
                style={{
                  position: 'relative',
                  overflow: 'hidden',
                  borderRadius: '0.75rem',
                  border: '1px solid var(--color-border-paper)',
                  background: 'var(--color-bg-paper)',
                }}
              >
                {isImage && previewUrl ? (
                  <img src={previewUrl} alt={file.name} style={{ display: 'block', width: '5rem', height: '5rem', objectFit: 'cover' }} />
                ) : (
                  <div style={{ width: '7rem', height: '5rem', padding: '0.5rem', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', textAlign: 'center', background: 'var(--color-bg-paper)' }}>
                    <IconFile style={{ width: '1.4rem', height: '1.4rem', color: 'var(--color-text-muted)', marginBottom: '0.2rem' }} />
                    <span style={{ width: '100%', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', fontSize: '0.68rem', color: 'var(--color-text-secondary)' }}>{file.name}</span>
                    <span style={{ fontSize: '0.6rem', color: 'var(--color-text-muted)' }}>{displayExt} · {formatFileSize(file.size)}</span>
                  </div>
                )}
                {file.isUploading ? (
                  <div style={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', background: 'rgba(255,254,249,0.88)' }}>
                    <IconLoader style={{ width: '1rem', height: '1rem', color: 'var(--color-action-link)', marginBottom: '0.25rem' }} className="spin" />
                    <div style={{ width: '3rem', height: '0.25rem', borderRadius: '999px', overflow: 'hidden', background: 'var(--color-border-paper)' }}>
                      <div style={{ width: `${file.progress || 0}%`, height: '100%', background: 'var(--color-action-link)' }} />
                    </div>
                    <span style={{ marginTop: '0.2rem', fontSize: '0.6rem', color: 'var(--color-text-secondary)' }}>{Math.round(file.progress || 0)}%</span>
                  </div>
                ) : null}
                <button
                  type="button"
                  onClick={() => deleteFile(file.id)}
                  disabled={file.isUploading}
                  aria-label={`删除文件 ${file.name}`}
                  style={{
                    position: 'absolute',
                    top: '0.35rem',
                    right: '0.35rem',
                    width: '1.5rem',
                    height: '1.5rem',
                    border: 'none',
                    borderRadius: '999px',
                    background: 'rgba(255,255,255,0.92)',
                    color: '#d9534f',
                    cursor: file.isUploading ? 'not-allowed' : 'pointer',
                    display: 'grid',
                    placeItems: 'center',
                  }}
                >
                  <IconX style={{ width: '0.85rem', height: '0.85rem' }} />
                </button>
              </div>
            );
          })}
        </div>
      ) : null}

      {(showUploadHint || mode === 'full') ? (
        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', marginBottom: '0.5rem', fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>
          {showUploadHint ? <span id="chat-upload-hint">上传方式：粘贴 · 拖拽 · 点击选择</span> : null}
          {mode === 'full' ? <span style={{ marginLeft: 'auto' }}>⌘/Ctrl + Enter 发送</span> : null}
        </div>
      ) : null}

      <textarea
        id="chat-input"
        ref={queryInputRef}
        aria-label="聊天输入"
        aria-describedby={showUploadHint ? 'chat-upload-hint' : undefined}
        placeholder={placeholder}
        value={query}
        rows={1}
        onChange={(event) => setQuery(event.target.value)}
        onFocus={() => setIsInputFocused(true)}
        onBlur={() => setIsInputFocused(false)}
        disabled={disabled}
        onKeyDown={(event) => {
          if (!shouldSendWithKeyboard(mode, event)) {
            return;
          }
          event.preventDefault();
          handleSend();
        }}
        style={{
          width: '100%',
          minHeight: '4.5rem',
          resize: 'none',
          border: 'none',
          outline: 'none',
          background: 'transparent',
          color: 'var(--color-text-primary)',
          fontSize: '1rem',
          lineHeight: 1.6,
          fontFamily: "'Excalifont', 'Xiaolai', Georgia, serif",
          boxSizing: 'border-box',
        }}
      />

      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.75rem', marginTop: '0.75rem' }}>
        <button
          type="button"
          aria-label="添加附件"
          onClick={openAttachmentDialog}
          disabled={disabled}
          style={{
            border: '1px solid var(--color-border-paper)',
            borderRadius: '999px',
            padding: '0.55rem 0.9rem',
            background: 'var(--color-bg-paper)',
            color: 'var(--color-text-secondary)',
            cursor: disabled ? 'not-allowed' : 'pointer',
          }}
        >
          + Add
        </button>

        {loading && onStop ? (
          <button
            type="button"
            onClick={onStop}
            title="停止生成"
            aria-label="停止生成"
            style={{
              display: 'grid',
              placeItems: 'center',
              width: '2.25rem',
              height: '2.25rem',
              borderRadius: '999px',
              border: 'none',
              background: '#d9534f',
              color: 'var(--color-text-on-action)',
              cursor: 'pointer',
            }}
          >
            <IconStop style={{ width: '0.9rem', height: '0.9rem' }} />
          </button>
        ) : (
          <button
            type="button"
            onClick={handleSend}
            disabled={!canSend}
            title={hasUploadingFiles ? '等待上传完成...' : '发送'}
            aria-label="发送消息"
            style={{
              display: 'grid',
              placeItems: 'center',
              width: '2.25rem',
              height: '2.25rem',
              borderRadius: '999px',
              border: 'none',
              background: canSend ? 'var(--color-action-link)' : 'var(--color-disabled-bg)',
              color: 'var(--color-text-on-action)',
              cursor: canSend ? 'pointer' : 'not-allowed',
            }}
          >
            {hasUploadingFiles ? (
              <IconLoader style={{ width: '0.95rem', height: '0.95rem' }} className="spin" />
            ) : (
              <IconArrowUp style={{ width: '0.95rem', height: '0.95rem' }} />
            )}
          </button>
        )}
      </div>
    </div>
  );
}

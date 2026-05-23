import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { IconChevronDown, IconChevronRight, IconDownload, IconFile, IconFolder, IconPlus, IconTrash } from '../chat/Icons';

export interface FileInfo {
  name: string;
  path: string;
  isDirectory: boolean;
  size: number;
  modifiedAt: string;
  downloadUrl?: string;
  file?: File;
}

interface FileTreeNode extends FileInfo {
  children?: FileTreeNode[];
}

interface FileSidebarProps {
  sessionId: string;
  open: boolean;
  onClose: () => void;
  files?: FileInfo[];
  onFilesChange?: (files: FileInfo[]) => void;
  onUploadFiles?: (files: File[]) => void;
  title?: string;
}

function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB'];
  const unitIndex = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  return `${(bytes / 1024 ** unitIndex).toFixed(unitIndex === 0 ? 0 : 1)} ${units[unitIndex]}`;
}

function buildTree(files: FileInfo[]): FileTreeNode[] {
  const root: FileTreeNode[] = [];
  const folderMap = new Map<string, FileTreeNode>();

  const ensureFolder = (folderPath: string) => {
    const normalizedPath = folderPath.replace(/^\/+|\/+$/g, '');
    if (!normalizedPath) return null;
    const existing = folderMap.get(normalizedPath);
    if (existing) return existing;
    const parts = normalizedPath.split('/');
    const name = parts[parts.length - 1];
    const parentPath = parts.slice(0, -1).join('/');
    const node: FileTreeNode = { name, path: normalizedPath, isDirectory: true, size: 0, modifiedAt: new Date().toISOString(), children: [] };
    folderMap.set(normalizedPath, node);
    if (parentPath) {
      const parent = ensureFolder(parentPath);
      parent?.children?.push(node);
    } else {
      root.push(node);
    }
    return node;
  };

  files.forEach((file) => {
    const normalizedPath = file.path.replace(/^\/+|\/+$/g, '');
    if (file.isDirectory) {
      ensureFolder(normalizedPath);
      return;
    }
    const parts = normalizedPath.split('/');
    const parentPath = parts.slice(0, -1).join('/');
    const node: FileTreeNode = { ...file, path: normalizedPath };
    if (parentPath) {
      const parent = ensureFolder(parentPath);
      parent?.children?.push(node);
    } else {
      root.push(node);
    }
  });

  const sortNodes = (nodes: FileTreeNode[]) => {
    nodes.sort((a, b) => Number(b.isDirectory) - Number(a.isDirectory) || a.name.localeCompare(b.name));
    nodes.forEach((node) => node.children && sortNodes(node.children));
  };
  sortNodes(root);
  return root;
}

export default function FileSidebar({ sessionId, open, onClose, files = [], onFilesChange, onUploadFiles, title = 'Files' }: FileSidebarProps) {
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [notice, setNotice] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const folderInputRef = useRef<HTMLInputElement>(null);
  const tree = useMemo(() => buildTree(files), [files]);

  useEffect(() => {
    const folderInput = folderInputRef.current;
    if (!folderInput) return;
    folderInput.setAttribute('webkitdirectory', '');
    folderInput.setAttribute('directory', '');
  }, []);

  const addFiles = useCallback((selectedFiles: FileList | null) => {
    if (!selectedFiles?.length) return;
    const additions = Array.from(selectedFiles).map((file) => ({
      name: file.name,
      path: file.webkitRelativePath || file.name,
      isDirectory: false,
      size: file.size,
      modifiedAt: new Date(file.lastModified).toISOString(),
      downloadUrl: URL.createObjectURL(file),
      file,
    }));
    onUploadFiles?.(Array.from(selectedFiles));
    onFilesChange?.([...files, ...additions]);
    setNotice(`${additions.length} file${additions.length === 1 ? '' : 's'} added to ${sessionId}`);
  }, [files, onFilesChange, onUploadFiles, sessionId]);

  const removeFile = useCallback((filePath: string) => {
    onFilesChange?.(files.filter((file) => file.path !== filePath));
  }, [files, onFilesChange]);

  const toggleFolder = useCallback((path: string) => {
    setExpanded((current) => {
      const next = new Set(current);
      if (next.has(path)) next.delete(path);
      else next.add(path);
      return next;
    });
  }, []);

  return (
    <aside style={{ width: open ? '20rem' : 0, minWidth: open ? '20rem' : 0, overflow: 'hidden', borderLeft: open ? '1px solid var(--color-border-paper)' : 'none', background: 'var(--color-bg-app)', transition: 'width 0.25s ease, min-width 0.25s ease', display: 'flex', flexDirection: 'column' }}>
      {open ? (
        <>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '1rem', borderBottom: '1px solid var(--color-border-paper)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--color-text-primary)' }}>
              <IconFolder style={{ width: '1.1rem', height: '1.1rem', color: 'var(--color-action-link)' }} />
              <span style={{ fontWeight: 600 }}>{title}</span>
            </div>
            <button type="button" onClick={onClose} style={{ border: 'none', background: 'transparent', color: 'var(--color-text-muted)', cursor: 'pointer' }}>Close</button>
          </div>

          <div style={{ display: 'flex', gap: '0.5rem', padding: '1rem' }}>
            <button type="button" onClick={() => fileInputRef.current?.click()} style={{ flex: 1, borderRadius: '999px', border: '1px solid var(--color-border-paper)', background: 'var(--color-bg-paper)', padding: '0.65rem 0.8rem', color: 'var(--color-text-secondary)', cursor: 'pointer' }}><IconPlus style={{ width: '0.9rem', height: '0.9rem', marginRight: '0.3rem', verticalAlign: 'middle' }} />Files</button>
            <button type="button" onClick={() => folderInputRef.current?.click()} style={{ flex: 1, borderRadius: '999px', border: '1px solid var(--color-border-paper)', background: 'var(--color-bg-paper)', padding: '0.65rem 0.8rem', color: 'var(--color-text-secondary)', cursor: 'pointer' }}><IconFolder style={{ width: '0.9rem', height: '0.9rem', marginRight: '0.3rem', verticalAlign: 'middle' }} />Folder</button>
          </div>

          <input ref={fileInputRef} type="file" multiple style={{ display: 'none' }} onChange={(event) => { addFiles(event.target.files); event.target.value = ''; }} />
          <input ref={folderInputRef} type="file" multiple style={{ display: 'none' }} onChange={(event) => { addFiles(event.target.files); event.target.value = ''; }} />

          {notice ? <div style={{ margin: '0 1rem 1rem', padding: '0.7rem 0.85rem', borderRadius: '10px', background: 'var(--color-bg-paper)', color: 'var(--color-text-secondary)', fontSize: '0.8rem' }}>{notice}</div> : null}

          <div style={{ flex: 1, overflow: 'auto', padding: '0 0.75rem 1rem' }}>
            {tree.length === 0 ? <div style={{ padding: '1rem', borderRadius: '12px', background: 'var(--color-bg-paper)', color: 'var(--color-text-muted)', fontSize: '0.84rem' }}>No files yet.</div> : tree.map((node) => <FileTreeItem key={node.path} node={node} expanded={expanded} onToggle={toggleFolder} onDelete={removeFile} />)}
          </div>
        </>
      ) : null}
    </aside>
  );
}

function FileTreeItem({ node, expanded, onToggle, onDelete }: { node: FileTreeNode; expanded: Set<string>; onToggle: (path: string) => void; onDelete: (path: string) => void }) {
  const isOpen = expanded.has(node.path);
  const isFolder = node.isDirectory;

  return (
    <div style={{ marginBottom: '0.35rem' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem', padding: '0.55rem 0.6rem', borderRadius: '10px', background: 'var(--color-bg-paper)' }}>
        {isFolder ? <button type="button" onClick={() => onToggle(node.path)} style={{ border: 'none', background: 'transparent', color: 'var(--color-text-muted)', cursor: 'pointer' }}>{isOpen ? <IconChevronDown style={{ width: '0.9rem', height: '0.9rem' }} /> : <IconChevronRight style={{ width: '0.9rem', height: '0.9rem' }} />}</button> : <span style={{ width: '0.9rem' }} />}
        {isFolder ? <IconFolder style={{ width: '1rem', height: '1rem', color: 'var(--color-action-link)' }} /> : <IconFile style={{ width: '1rem', height: '1rem', color: 'var(--color-text-muted)' }} />}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: '0.83rem', color: 'var(--color-text-primary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{node.name}</div>
          {!isFolder ? <div style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)' }}>{formatFileSize(node.size)}</div> : null}
        </div>
        {!isFolder ? (
          <>
            {node.downloadUrl ? <a href={node.downloadUrl} download={node.name} style={{ color: 'var(--color-text-muted)', display: 'inline-flex' }}><IconDownload style={{ width: '0.95rem', height: '0.95rem' }} /></a> : null}
            <button type="button" onClick={() => onDelete(node.path)} style={{ border: 'none', background: 'transparent', color: 'var(--color-state-danger)', cursor: 'pointer' }}><IconTrash style={{ width: '0.95rem', height: '0.95rem' }} /></button>
          </>
        ) : null}
      </div>
      {isFolder && isOpen && node.children?.length ? <div style={{ marginLeft: '1.2rem', marginTop: '0.35rem' }}>{node.children.map((child) => <FileTreeItem key={child.path} node={child} expanded={expanded} onToggle={onToggle} onDelete={onDelete} />)}</div> : null}
    </div>
  );
}

// [Input] Original Workspace file/tree DTOs, authenticated same-origin endpoints and optional platform HTTP.
// [Output] Shared original tree projection, formatting, list/read and DELETE request behavior.
// [Pos] Workspace file API/model owner; Web keeps its existing markup and native injects the local transport.
// [Sync] 2026-10-28: extract original sidebar helpers and repair the missing DELETE method/CSRF without changing paths or permissions.
import {API_BASE} from '../lib/apiBase';
import {browserRequestHeaders} from '../lib/browserSession';

export interface FileInfo {
  name: string;
  path: string;
  isDirectory: boolean;
  size: number;
  modifiedAt: string;
  children?: FileInfo[];
}

export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB'];
  const unitIndex = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  return `${(bytes / 1024 ** unitIndex).toFixed(unitIndex === 0 ? 0 : 1)} ${units[unitIndex]}`;
}

export function normalizePath(value: string) {
  return value.replace(/\\/g, '/').replace(/^\/+|\/+$/g, '');
}

export function buildTree(files: FileInfo[]): FileInfo[] {
  const root: FileInfo[] = [];
  const directoryMap = new Map<string, FileInfo>();

  const ensureDirectory = (directoryPath: string) => {
    const normalized = normalizePath(directoryPath);
    if (!normalized) return null;
    const existing = directoryMap.get(normalized);
    if (existing) return existing;
    const parts = normalized.split('/');
    const name = parts[parts.length - 1];
    const parentPath = parts.slice(0, -1).join('/');
    const node: FileInfo = { name, path: normalized, isDirectory: true, size: 0, modifiedAt: new Date().toISOString(), children: [] };
    directoryMap.set(normalized, node);
    if (parentPath) {
      ensureDirectory(parentPath)?.children?.push(node);
    } else {
      root.push(node);
    }
    return node;
  };

  files.forEach((file) => {
    const normalizedPath = normalizePath(file.path);
    if (file.isDirectory) {
      ensureDirectory(normalizedPath);
      return;
    }
    const parentPath = normalizedPath.split('/').slice(0, -1).join('/');
    const node: FileInfo = { ...file, path: normalizedPath };
    if (parentPath) {
      ensureDirectory(parentPath)?.children?.push(node);
    } else {
      root.push(node);
    }
  });

  const sortNodes = (nodes: FileInfo[]) => {
    nodes.sort((a, b) => Number(b.isDirectory) - Number(a.isDirectory) || a.name.localeCompare(b.name));
    nodes.forEach((node) => node.children && sortNodes(node.children));
  };
  sortNodes(root);
  return root;
}

export function flattenVisible(nodes: FileInfo[], currentPath: string): FileInfo[] {
  if (!currentPath) {
    return nodes;
  }
  const walk = (entries: FileInfo[]): FileInfo[] => {
    for (const entry of entries) {
      if (entry.path === currentPath && entry.isDirectory) {
        return entry.children ?? [];
      }
      if (entry.children?.length) {
        const nested = walk(entry.children);
        if (nested.length || entry.path === currentPath) {
          return nested;
        }
      }
    }
    return [];
  };
  return walk(nodes);
}

export function buildWorkspaceDownloadUrl(sessionId: string, filePath: string): string {
  const params = new URLSearchParams({ sessionId, path: filePath });
  return `${API_BASE}/api/workspace/files/download?${params.toString()}`;
}


export async function readWorkspaceFileTree(sessionId:string,options:{transport?:typeof fetch;signal?:AbortSignal}={}):Promise<FileInfo[]> {
  const response=await (options.transport??fetch)(`${API_BASE}/api/workspace/files?${new URLSearchParams({sessionId,recursive:'1'})}`,{headers:browserRequestHeaders(),signal:options.signal});
  if(!response.ok){const payload=await response.json().catch(()=>({})) as {error?:string};throw new Error(payload.error||`目录刷新失败 (${response.status})`);}
  const payload=await response.json() as {tree?:FileInfo[];files?:FileInfo[]};
  const files=payload.tree?.length?payload.tree:buildTree(payload.files??[]);
  return files.map(entry=>({...entry,path:normalizePath(entry.path),children:entry.children}));
}
export async function deleteWorkspaceFile(sessionId:string,path:string,transport:typeof fetch=fetch):Promise<void> {
  const response=await transport(`${API_BASE}/api/workspace/files`,{method:'DELETE',headers:{...browserRequestHeaders(),'Content-Type':'application/json'},body:JSON.stringify({sessionId,path})});
  if(!response.ok){const payload=await response.json().catch(()=>({})) as {error?:string};throw new Error(payload.error||`删除失败 (${response.status})`);}
}

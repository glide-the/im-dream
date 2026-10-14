# [Input] Server-owned root, Admin-verified artifact identities and canonical UTF-8 documents.
# [Output] Atomic, hash-verified private Markdown publications and safe loss recovery.
# [Pos] Memory file boundary; never extends a native Agent workspace or read allowlist.
# [Sync] 2026-10-15: reject symlinks and publish durable L2/L3 files.
from __future__ import annotations
import os
from pathlib import Path
import stat
import tempfile
from uuid import UUID
from .documents import digest,validate_document

def memory_root() -> Path:
    raw=os.environ.get('MEMORY_ARTIFACT_ROOT')
    root=Path(raw) if raw else Path(__file__).resolve().parents[2]/'data'/'memory-artifacts'
    if not root.is_absolute(): raise ValueError('MEMORY_ROOT_INVALID')
    return root

def _directory(path:Path):
    parts=[path,*path.parents]
    for parent in reversed(parts):
        if parent.exists() or parent.is_symlink():
            if parent.is_symlink() or not parent.is_dir(): raise ValueError('MEMORY_PATH_INVALID')
        else: parent.mkdir(mode=0o700)

def artifact_path(artifact,theme=False) -> Path:
    if str(UUID(artifact.artifact_id))!=artifact.artifact_id or type(artifact.revision) is not int or artifact.revision<1: raise ValueError('MEMORY_PATH_INVALID')
    directory=memory_root()/artifact.artifact_id/str(artifact.revision)
    _directory(directory)
    return directory/('memory_theme.md' if theme else 'memory_distillation.md')

def publish(artifact,theme=False) -> Path:
    validate_document(artifact,theme=theme)
    document=artifact.theme_document if theme else artifact.document
    expected=artifact.theme_sha256 if theme else artifact.document_sha256
    target=artifact_path(artifact,theme)
    if target.is_symlink(): raise ValueError('MEMORY_PATH_INVALID')
    fd,name=tempfile.mkstemp(prefix='.publish-',dir=target.parent)
    try:
        os.fchmod(fd,0o600)
        with os.fdopen(fd,'wb') as f:
            f.write(document.encode('utf-8'));f.flush();os.fsync(f.fileno())
        os.replace(name,target)
        dfd=os.open(target.parent,os.O_RDONLY | os.O_DIRECTORY)
        try: os.fsync(dfd)
        finally: os.close(dfd)
    finally:
        if os.path.exists(name): os.unlink(name)
    _read(target,expected,len(document.encode('utf-8')))
    return target

def _read(path:Path,expected:str,length:int) -> str:
    fd=os.open(path,os.O_RDONLY | os.O_NOFOLLOW)
    try:
        info=os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_size!=length: raise ValueError('MEMORY_FILE_INVALID')
        with os.fdopen(fd,'rb',closefd=False) as f: raw=f.read(length+1)
        text=raw.decode('utf-8')
        if digest(text)!=expected: raise ValueError('MEMORY_FILE_INVALID')
        return text
    finally: os.close(fd)

def read(artifact,theme=False) -> str:
    validate_document(artifact,theme=theme)
    target=artifact_path(artifact,theme)
    document=artifact.theme_document if theme else artifact.document
    expected=artifact.theme_sha256 if theme else artifact.document_sha256
    try: return _read(target,expected,len(document.encode('utf-8')))
    except FileNotFoundError:
        publish(artifact,theme)
        return _read(target,expected,len(document.encode('utf-8')))

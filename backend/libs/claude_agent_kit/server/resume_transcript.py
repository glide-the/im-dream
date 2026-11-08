# [Input] Owner-authorized canonical Chat history and server-owned Runtime cwd/config home.
# [Output] Validated same-session JSONL, atomic checkpoints and a no-follow execution lock.
# [Pos] Local Runtime storage adapter; no database, model, historical tool execution or file sync.
# [Sync] 2026-11-04: initialize missing cross-platform transcripts without changing session identity.
# [Sync] 2026-11-08: retain Runtime parallel results and meta injections; reconcile saved stopped text without replay.
from __future__ import annotations

import errno
import fcntl
import hashlib
import json
import os
import stat
import sys
import unicodedata
from datetime import datetime, timedelta, timezone
from functools import wraps
from pathlib import Path
from uuid import UUID, NAMESPACE_URL, uuid5

from .session_files import ClaudeResumeStorageError, _runtime_project_name

FORMAT = "ink-admin-history/1"


def _fail(code="CLAUDE_RESUME_HISTORY_UNSUPPORTED"):
    raise ClaudeResumeStorageError(code)


def _storage_boundary(method):
    @wraps(method)
    def call(*args, **kwargs):
        try:
            return method(*args, **kwargs)
        except PermissionError:
            _fail("CLAUDE_RESUME_PERMISSION_DENIED")
        except BlockingIOError:
            _fail("CHAT_CONTINUATION_BUSY")
        except OSError as exc:
            _fail("CLAUDE_RESUME_SYMLINK_DENIED" if exc.errno == errno.ELOOP else "CLAUDE_RESUME_STORAGE_UNAVAILABLE")
    return call


def history_records(messages: list[dict], *, thread_id: str, session_id: str, cwd: str) -> list[dict]:
    """Convert explicit text and complete text tool results; reject missing semantics."""
    try:
        UUID(session_id)
    except (ValueError, TypeError):
        _fail("CLAUDE_RESUME_INVALID_SESSION_ID")
    records: list[dict] = []
    seen: set[str] = set()
    tools: set[str] = set()
    pending_user = False
    last_time = datetime(1970, 1, 1, tzinfo=timezone.utc)

    def append(role, content, identity, timestamp, *, tool=False):
        nonlocal last_time
        try:
            instant = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            if instant.tzinfo is None:
                _fail()
        except (AttributeError, TypeError, ValueError):
            _fail()
        last_time = max(instant, last_time + timedelta(milliseconds=1))
        uid = str(uuid5(NAMESPACE_URL, f"{FORMAT}/{thread_id}/{session_id}/{identity}/{len(records)}/{role}"))
        message = {"role": role, "content": content}
        if role == "assistant":
            message.update(id=str(uuid5(NAMESPACE_URL, uid + "/message")), type="message", model="<synthetic>", stop_reason="tool_use" if tool else "end_turn", stop_sequence=None, usage={"input_tokens": 0, "output_tokens": 0}, container=None, context_management=None)
        records.append({"parentUuid": records[-1]["uuid"] if records else None, "isSidechain": False, "type": role, "uuid": uid, "sessionId": session_id, "timestamp": last_time.isoformat(timespec="milliseconds"), "cwd": cwd, "version": "0.1.12", "message": message})

    for item in messages:
        identity = item.get("id")
        if not isinstance(identity, str) or not identity or identity in seen or item.get("metadata_decode_error"):
            _fail()
        seen.add(identity)
        metadata = item.get("metadata") or {}
        if metadata.get("is_partial") or metadata.get("kind"):
            _fail()
        role = item.get("role")
        parts = item.get("parts")
        if not isinstance(parts, list) or not parts:
            _fail()
        if role == "user":
            if pending_user or any(not isinstance(p, dict) or p.get("type") != "text" or not isinstance(p.get("text"), str) for p in parts):
                _fail()
            append(role, [{"type": "text", "text": p["text"]} for p in parts], identity, item.get("created_at"))
            pending_user = True
        elif role == "assistant":
            if not pending_user or metadata.get("turnStatus") != "completed":
                _fail()
            if sum(isinstance(p, dict) and p.get("type") == "tool-invocation" for p in parts) > 1:
                _fail()
            text: list[dict] = []
            for part in parts:
                if not isinstance(part, dict):
                    _fail()
                kind = part.get("type")
                if kind == "text" and isinstance(part.get("text"), str):
                    text.append({"type": "text", "text": part["text"]})
                elif kind == "reasoning":
                    # UI reasoning lacks the signature; no synthetic thinking blocks.
                    continue
                elif kind == "tool-invocation":
                    call = part.get("toolCallId")
                    output = part.get("output")
                    if not isinstance(call, str) or not call or call in tools or part.get("providerExecuted") or part.get("state") not in {"output-available", "output-error"} or not isinstance(part.get("toolName"), str) or not isinstance(part.get("input"), dict) or not isinstance(output, str):
                        _fail()
                    tools.add(call)
                    text.append({"type": "tool_use", "id": call, "name": part["toolName"], "input": part["input"]})
                    append("assistant", text, identity, item.get("created_at"), tool=True)
                    text = []
                    append("user", [{"type": "tool_result", "tool_use_id": call, "content": output, "is_error": part["state"] == "output-error"}], identity, item.get("created_at"))
                else:
                    _fail()
            if not text or not any(p["text"].strip() for p in text):
                _fail()
            append("assistant", text, identity, item.get("created_at"))
            pending_user = False
        else:
            _fail()
    if pending_user or not records:
        _fail()
    return records


def validate_transcript(raw: bytes, session_id: str, *, allow_unsettled: bool = False) -> list[dict]:
    """Validate every JSON line and the actual non-sidechain conversation chain."""
    try:
        entries = [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]
        records = [e for e in entries if isinstance(e, dict) and e.get("type") in {"user", "assistant", "system", "attachment"} and not e.get("isSidechain")]
        if any(not isinstance(e, dict) for e in entries) or not records:
            _fail("CLAUDE_RESUME_INVALID_RECORD")
        by_id = {}
        for record in records:
            uid = record.get("uuid")
            if not isinstance(uid, str) or not uid or uid in by_id or record.get("sessionId") != session_id:
                _fail("CLAUDE_RESUME_RECORD_ID_MISMATCH")
            if record.get("type") in {"user", "assistant"} and not isinstance(record.get("message"), dict):
                _fail("CLAUDE_RESUME_INVALID_RECORD")
            by_id[uid] = record
        leaf = max(records, key=lambda r: datetime.fromisoformat(r["timestamp"].replace("Z", "+00:00")))
        chain, seen = [], set()
        while leaf:
            if leaf["uuid"] in seen:
                _fail("CLAUDE_RESUME_INVALID_RECORD")
            seen.add(leaf["uuid"])
            chain.append(leaf)
            parent = leaf.get("parentUuid")
            if parent and parent not in by_id:
                _fail("CLAUDE_RESUME_INVALID_RECORD")
            leaf = by_id.get(parent)
        chain.reverse()
        # Runtime 0.1.12 buildConversationChain recovers parallel assistant
        # siblings by message.id and their tool results outside the parent path.
        assistants = [r for r in chain if r["type"] == "assistant"]
        anchors = {r["message"].get("id"): r for r in assistants if r["message"].get("id")}
        inserts = {}
        for message_id, anchor in anchors.items():
            siblings = [r for r in records if r["type"] == "assistant" and r["message"].get("id") == message_id]
            sibling_ids = {r["uuid"] for r in siblings}
            orphaned = [r for r in siblings if r["uuid"] not in seen]
            results = [r for r in records if r["type"] == "user" and r.get("parentUuid") in sibling_ids
                       and r["uuid"] not in seen and isinstance(r["message"].get("content"), list)
                       and any(b.get("type") == "tool_result" for b in r["message"]["content"] if isinstance(b, dict))]
            recovered = sorted(orphaned, key=lambda r: r["timestamp"]) + sorted(results, key=lambda r: r["timestamp"])
            if recovered:
                inserts[anchor["uuid"]] = recovered
                seen.update(r["uuid"] for r in recovered)
        chain = [item for record in chain for item in [record, *inserts.get(record["uuid"], [])]]
        conversation = [e for e in chain if e["type"] in {"user", "assistant"}]
        if not conversation or not allow_unsettled and conversation[-1]["type"] != "assistant":
            _fail("CLAUDE_RESUME_TRANSCRIPT_UNSETTLED")
        outstanding = set()
        for entry in conversation:
            content = entry["message"].get("content")
            if not isinstance(content, (str, list)):
                _fail("CLAUDE_RESUME_INVALID_RECORD")
            for block in content if isinstance(content, list) else []:
                if not isinstance(block, dict):
                    _fail("CLAUDE_RESUME_INVALID_RECORD")
                if block.get("type") == "tool_use":
                    if block.get("id") in outstanding:
                        _fail("CLAUDE_RESUME_INVALID_RECORD")
                    outstanding.add(block.get("id"))
                if block.get("type") == "tool_result":
                    if block.get("tool_use_id") not in outstanding:
                        _fail("CLAUDE_RESUME_INVALID_RECORD")
                    outstanding.remove(block.get("tool_use_id"))
        if outstanding and not allow_unsettled:
            _fail("CLAUDE_RESUME_TRANSCRIPT_UNSETTLED")
        return conversation
    except ClaudeResumeStorageError:
        raise
    except (ValueError, KeyError, TypeError, UnicodeError):
        _fail("CLAUDE_RESUME_INVALID_RECORD")


def _projection(records):
    """Compare complete visible turns while retaining native Runtime envelopes."""
    from .agent_runner import _normalize_tool_result_output
    turns = []
    for record in records:
        if record["type"] == "user" and record.get("isMeta") is True:
            continue
        role, content = record["type"], record["message"]["content"]
        blocks = [{"type": "text", "text": content}] if isinstance(content, str) else content
        text = "".join(b.get("text", "") for b in blocks if b.get("type") == "text")
        if role == "user" and text in {"[Request interrupted by user]", "[Request interrupted by user for tool use]"}:
            continue
        calls = [(b.get("id"), b.get("name"), b.get("input")) for b in blocks if b.get("type") == "tool_use"]
        results = [(b.get("tool_use_id"), _normalize_tool_result_output(b.get("content")), bool(b.get("is_error"))) for b in blocks if b.get("type") == "tool_result"]
        if role == "user" and not results:
            turns.append([text, "", [], []])
        elif turns:
            turns[-1][1] += text
            turns[-1][2].extend(calls)
            turns[-1][3].extend(results)
    return turns


def _covers_history(native, messages):
    expected = []
    for item in messages:
        if item.get("metadata_decode_error") or not isinstance(item.get("parts"), list):
            return False
        text = "".join(p.get("text", "") for p in item["parts"] if isinstance(p, dict) and p.get("type") == "text")
        if item.get("role") == "user":
            expected.append([text, "", [], []])
        elif item.get("role") == "assistant" and expected:
            expected[-1][1] += text
            for part in item["parts"]:
                if isinstance(part, dict) and part.get("type") == "tool-invocation":
                    expected[-1][2].append((part.get("toolCallId"), part.get("toolName"), part.get("input")))
                    if part.get("state") in {"output-available", "output-error"}:
                        expected[-1][3].append((part.get("toolCallId"), part.get("output"), part.get("state") == "output-error"))
        else:
            return False
    actual = _projection(native)
    def tools_equal(left, right):
        # Parallel result completion order differs from the UI call order.
        return (len({v[0] for v in left}) == len(left) == len(right) == len({v[0] for v in right})
                and {v[0]: v[1:] for v in left} == {v[0]: v[1:] for v in right})

    stopped = bool(messages and messages[-1].get("role") == "assistant"
                   and (messages[-1].get("metadata") or {}).get("is_partial") is True
                   and (messages[-1].get("metadata") or {}).get("turnStatus") in {"cancelled", "error"})
    return len(actual) == len(expected) and all(
        a[0].endswith(b[0]) and (a[1] == b[1] or stopped and index == len(expected) - 1 and a[1].startswith(b[1]))
        and tools_equal(a[2], b[2]) and tools_equal(a[3], b[3])
        for index, (a, b) in enumerate(zip(actual, expected)))


def _stopped_text_record(native, messages, *, thread_id, session_id, cwd):
    """Recover only saved text from the final confirmed stopped assistant."""
    if len(messages) < 2 or messages[-2].get("role") != "user" or messages[-1].get("role") != "assistant":
        return None
    assistant = messages[-1]
    metadata = assistant.get("metadata") or {}
    if metadata.get("turnStatus") not in {"cancelled", "error"} or metadata.get("is_partial") is not True:
        return None
    parts = assistant.get("parts")
    if not isinstance(parts, list) or any(not isinstance(p, dict) or p.get("type") not in {"text", "reasoning"} for p in parts):
        return None
    actual = _projection(native)
    text = "".join(p.get("text", "") for p in parts if p.get("type") == "text")
    if not actual or not text.startswith(actual[-1][1]) or len(text) <= len(actual[-1][1]):
        return None
    restored = {**assistant, "parts": [{"type": "text", "text": text[len(actual[-1][1]):]}],
                "metadata": {"turnStatus": "completed"}}
    record = history_records([messages[-2], restored], thread_id=thread_id, session_id=session_id, cwd=cwd)[-1]
    record["uuid"] = str(uuid5(NAMESPACE_URL, f"{FORMAT}/{thread_id}/{session_id}/stopped/{assistant['id']}"))
    record["parentUuid"] = native[-1]["uuid"]
    record["timestamp"] = max(datetime.fromisoformat(record["timestamp"]),
                              datetime.fromisoformat(native[-1]["timestamp"].replace("Z", "+00:00")) + timedelta(milliseconds=1)).isoformat(timespec="milliseconds")
    return record


def _directory(path: Path) -> int:
    if not path.is_absolute() or str(path) != os.path.normpath(str(path)):
        _fail("CLAUDE_RESUME_INVALID_CONFIG_HOME")
    if sys.platform == "ios":
        root = Path.home().resolve(strict=True)
        if not path.is_relative_to(root):
            _fail("CLAUDE_RESUME_INVALID_CONFIG_HOME")
        fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        components = path.relative_to(root).parts
    else:
        fd = os.open(path.anchor, os.O_RDONLY | os.O_DIRECTORY)
        components = path.parts[1:]
    try:
        for component in components:
            try:
                if stat.S_ISLNK(os.stat(component, dir_fd=fd, follow_symlinks=False).st_mode):
                    _fail("CLAUDE_RESUME_SYMLINK_DENIED")
                child = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            except FileNotFoundError:
                try:
                    os.mkdir(component, mode=0o700, dir_fd=fd)
                except FileExistsError:
                    pass
                child = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = child
        return fd
    except BaseException:
        os.close(fd)
        raise


class ResumeTranscriptLease:
    """One thread-local file lock, held until SDK cleanup and history settlement."""
    @_storage_boundary
    def __init__(self, *, thread_id: str, session_id: str | None, cwd: str, config_home: str, lock_root: str):
        if session_id is not None:
            try:
                if str(UUID(session_id)) != session_id:
                    raise ValueError
            except (TypeError, ValueError, AttributeError):
                _fail("CLAUDE_RESUME_INVALID_SESSION_ID")
        self.thread_id, self.session_id = thread_id, session_id
        self.cwd = unicodedata.normalize("NFC", str(Path(cwd).resolve(strict=True)))
        self.config_home = config_home
        self.lock_dir = _directory(Path(lock_root) / ".claude-tmp")
        try:
            self.lock = os.open(".claude-resume.lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600, dir_fd=self.lock_dir)
            if not stat.S_ISREG(os.fstat(self.lock).st_mode):
                _fail("CLAUDE_RESUME_INVALID_RECORD")
            fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BaseException:
            self.close()
            raise
        self.project = None

    def _open(self):
        if self.project is None:
            self.project = _directory(Path(self.config_home) / "projects" / _runtime_project_name(self.cwd))
        return self.project

    def _read(self, name):
        try:
            if stat.S_ISLNK(os.stat(name, dir_fd=self._open(), follow_symlinks=False).st_mode):
                _fail("CLAUDE_RESUME_SYMLINK_DENIED")
            fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=self._open())
        except FileNotFoundError:
            return None
        with os.fdopen(fd, "rb") as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                _fail("CLAUDE_RESUME_INVALID_RECORD")
            return stream.read()

    def _write(self, name, raw):
        temp = ".ink-resume-" + str(uuid5(NAMESPACE_URL, name + hashlib.sha256(raw).hexdigest()))
        try:
            fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=self._open())
        except FileExistsError:
            unfinished = self._read(temp)
            if unfinished != raw:
                if unfinished is None or not raw.startswith(unfinished):
                    _fail("CLAUDE_RESUME_INVALID_RECORD")
                os.unlink(temp, dir_fd=self.project)
                return self._write(name, raw)
            os.replace(temp, name, src_dir_fd=self.project, dst_dir_fd=self.project)
            os.fsync(self.project)
            return
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp, name, src_dir_fd=self.project, dst_dir_fd=self.project)
            os.fsync(self.project)
        finally:
            try:
                os.unlink(temp, dir_fd=self.project)
            except FileNotFoundError:
                pass

    @_storage_boundary
    def prepare(self, messages, history_digest):
        if self.session_id is None:
            if messages:
                _fail()
            return
        target = f"{self.session_id}.jsonl"
        raw = self._read(target)
        expected = None
        marker = self._read(target + ".ink-continuation.json")
        try:
            checkpoint = json.loads(marker) if marker else None
            if checkpoint is not None and (not isinstance(checkpoint, dict) or checkpoint.get("format") != FORMAT):
                _fail("CLAUDE_RESUME_INVALID_RECORD")
        except (ValueError, UnicodeError):
            _fail("CLAUDE_RESUME_INVALID_RECORD")
        if raw is not None:
            native = validate_transcript(raw, self.session_id, allow_unsettled=True)
            digest = hashlib.sha256(raw).hexdigest()
            if checkpoint and checkpoint.get("session_id") == self.session_id and checkpoint.get("file_digest") == digest:
                if checkpoint.get("history_digest") == history_digest:
                    return
            else:
                if _covers_history(native, messages):
                    self.checkpoint(history_digest)
                    return
                stopped = _stopped_text_record(native, messages, thread_id=self.thread_id, session_id=self.session_id, cwd=self.cwd)
                if stopped is not None:
                    candidate = raw + (b"" if raw.endswith(b"\n") else b"\n") + json.dumps(stopped, ensure_ascii=False, separators=(",", ":")).encode() + b"\n"
                    restored = validate_transcript(candidate, self.session_id, allow_unsettled=True)
                    if _covers_history(restored, messages):
                        archive = target + ".archive-" + digest
                        saved = self._read(archive)
                        if saved is not None and saved != raw:
                            _fail("CLAUDE_RESUME_INVALID_RECORD")
                        if saved is None:
                            self._write(archive, raw)
                        self._write(target, candidate)
                        self.checkpoint(history_digest)
                        return
                _fail("CLAUDE_RESUME_HISTORY_DIVERGED")
        expected = expected or history_records(messages, thread_id=self.thread_id, session_id=self.session_id, cwd=self.cwd)
        if raw is not None:
            archive = target + ".archive-" + hashlib.sha256(raw).hexdigest()
            saved = self._read(archive)
            if saved is None:
                self._write(archive, raw)
            elif saved != raw:
                _fail("CLAUDE_RESUME_INVALID_RECORD")
        candidate = ("\n".join(json.dumps(v, ensure_ascii=False, separators=(",", ":")) for v in expected) + "\n").encode()
        validate_transcript(candidate, self.session_id)
        self._write(target, candidate)
        self.checkpoint(history_digest)

    @_storage_boundary
    def checkpoint(self, history_digest, *, session_id=None):
        if self.session_id is not None and session_id is not None and self.session_id != session_id:
            _fail("CLAUDE_RESUME_RECORD_ID_MISMATCH")
        if session_id is not None:
            try:
                if str(UUID(session_id)) != session_id:
                    raise ValueError
            except (TypeError, ValueError, AttributeError):
                _fail("CLAUDE_RESUME_INVALID_SESSION_ID")
        self.session_id = session_id or self.session_id
        if self.session_id is None:
            return
        raw = self._read(f"{self.session_id}.jsonl")
        if raw is None:
            _fail("CLAUDE_RESUME_TRANSCRIPT_UNAVAILABLE")
        records = validate_transcript(raw, self.session_id, allow_unsettled=True)
        self._write(f"{self.session_id}.jsonl.ink-continuation.json", json.dumps({"format": FORMAT, "session_id": self.session_id, "history_digest": history_digest, "file_digest": hashlib.sha256(raw).hexdigest(), "leaf_uuid": records[-1]["uuid"]}).encode())

    def close(self):
        for key in ("project", "lock", "lock_dir"):
            fd = getattr(self, key, None)
            if fd is not None:
                os.close(fd)
                setattr(self, key, None)

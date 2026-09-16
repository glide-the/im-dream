<!-- [Input] Dream commits 1ccb80d4/9f00f777, repository test command and Luna read-only consumer validation. -->
<!-- [Output] Sanitized Reflections request-consumer compile, static, pytest and owned-environment cleanup evidence. -->
<!-- [Pos] Technical evidence for Dream request ingress; background Reflections task and real business acceptance remain separate. -->
<!-- [Sync] 2026-09-15: record 35-test DTO consumer and original-receipt recovery gate. -->

# Dream Reflections consumer deterministic gate

## Worktree and instructions

The applicable repository contracts were read from `Agent.md`, `AGENTS.md`, the root/backend folder contracts, and the rules index entry points. `git status --short` was inspected in `/Users/dmeck/.codex/worktrees/ef6e/ink-dream-memory`; extensive unrelated concurrent edits were present and preserved. No project file was edited, staged, committed, formatted, or reverted by this gate.

## Named deterministic tests

```text
cwd: /Users/dmeck/.codex/worktrees/ef6e/ink-dream-memory
command: backend/.venv/bin/python -m pytest -q backend/tests/test_admin_reflections_config.py backend/tests/test_reflections_config_router.py backend/tests/test_reflections_agent.py
exit: 127
stdout/stderr: zsh:1: no such file or directory: backend/.venv/bin/python
```

Runner discovery (read-only, no installation):

```text
cwd: /Users/dmeck/.codex/worktrees/ef6e/ink-dream-memory
command: python3 -m pytest --version
exit: 1
stdout/stderr: /opt/homebrew/opt/python@3.14/bin/python3.14: No module named pytest
```

The requested pytest suite did not execute; therefore no test count or skip count exists. This is a Python environment/pytest harness blocker, not a product assertion result. No alternate runner or dependency installation was used.

## Python compilation

```text
cwd: /Users/dmeck/.codex/worktrees/ef6e/ink-dream-memory
command: python3 -B -c 'from pathlib import Path; files=["backend/reflections_agent.py","backend/reflections_config.py","backend/routers/reflections.py","backend/services/admin_data/reflections_config_data.py","backend/tests/test_admin_reflections_config.py","backend/tests/test_reflections_config_router.py","backend/tests/test_reflections_agent.py"]; [compile(Path(f).read_text(), f, "exec") for f in files]; print("PYTHON COMPILE PASS", len(files), "files")'
exit: 0
stdout: PYTHON COMPILE PASS 7 files
```

Compilation was in memory with `-B`; no bytecode or project cache was written.

## Static consumer/router assertions

```text
cwd: /Users/dmeck/.codex/worktrees/ef6e/ink-dream-memory
command: python3 /private/tmp/ink-workflow-read-validation/verify-dream-reflections-static.py
exit: 0
stdout: {"result": "PASS", "ast_files": 5, "single_write_post_assertion": true, "same_operation_receipt_assertion": true, "unknown_outcome_states": ["absent", "timeout", "invalid"], "legacy_helpers_router": "not called", "consumer_direct_db_runtime_fs": "absent"}
```

The checker parsed the affected Python files and verified: save/delete have one write POST path; original receipt lookup reuses the same operation and request ID; absent/timeout/invalid receipt states remain `outcome_unknown`; public routes use the Admin consumer; legacy save/delete helpers are not called by the route/agent paths; and the Admin consumer contains no direct PostgreSQL, shared filesystem, or streaming-runtime dependency.

## Diff check

```text
cwd: /Users/dmeck/.codex/worktrees/ef6e/ink-dream-memory
command: git diff --check
exit: 0
stdout: (empty)
stderr: (empty)
```

## Scope and cleanup

No PostgreSQL, shared filesystem, Runtime, SSE, provider, model, public contract, migration, fixture, credential, network, or service operation ran. Only the named Python source/test files were compiled or statically inspected. Temporary checker scripts were written under `/private/tmp/ink-workflow-read-validation`; no project or production files were changed. Cleanup was limited to checker/test shell processes; no user service or shared resource was stopped or removed.

## uv pytest supplement

Initial sandbox attempt:

```text
cwd: /Users/dmeck/.codex/worktrees/ef6e/ink-dream-memory
command: PYTHONPATH=backend uv run --native-tls --project backend --frozen --with pytest==9.1.1 --with pytest-asyncio python -m pytest -q backend/tests/test_admin_reflections_config.py backend/tests/test_reflections_config_router.py backend/tests/test_reflections_agent.py
exit: 2
stdout/stderr: error: failed to open file `/Users/dmeck/.cache/uv/sdists-v9/.git`: Operation not permitted (os error 1)
```

The same exact command was then run with narrowly scoped permission to read the existing uv cache:

```text
exit: 0
Using CPython 3.12.9
Creating virtual environment at: backend/.venv
Installed 68 packages in 165ms
...................................                                      [100%]
35 passed in 2.94s
```

All 35 tests passed; no skips were reported. The frozen run created the local `backend/.venv` runtime and used cached ephemeral dependencies; no lockfile sync or database/service action occurred. The environment creation is runner setup, not an application source change. The earlier pytest-unavailable result and the cache-permission harness failure remain preserved.

## Authorized cleanup supplement

```text
cwd: /Users/dmeck/.codex/worktrees/ef6e/ink-dream-memory
command: rm -rf /Users/dmeck/.codex/worktrees/ef6e/ink-dream-memory/backend/.venv
exit: 0
command: test ! -e /Users/dmeck/.codex/worktrees/ef6e/ink-dream-memory/backend/.venv
exit: 0
command: git status --short
exit: 0
```

The exact uv-created `backend/.venv` path is absent after cleanup. The final status contains only the pre-existing concurrent docs/`.pnpm-store` changes and no `backend/.venv` entry. No other cache, file, or user environment was removed.

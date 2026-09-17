# Dream Memory Workspace Database Scan Correction

## Optimized Prompt

Verify whether the Dream memory workspace helper opens PostgreSQL in production.
Distinguish executable code from examples and comments. If the only match is a
retired route example, replace it with a caller-provided Admin DTO projection and
state the no-lookup boundary in the file header. Preserve the exact prompt-file
allowlist, procedural defaults, path containment, filesystem writes, and context
rendering. Do not add an API, database client, fallback, environment switch, or new
runtime behavior. Validate with the existing memory workspace tests, Python compile,
and a production source scan.

Optional enhancer: keep any future Voice memory DTO parsing at the Admin consumer
boundary so this file remains a pure filesystem module.

## Evidence and Decision

- The source match was inside the usage example for the removed
  `/api/workspace/memory-init` endpoint.
- Executable functions accept `memory_config` from callers and never import
  `database`, SQL, ORM, a connection pool, or an Admin HTTP client.
- The current production context builder only reads the already-created memory
  directory through `get_memory_context_block`.

## Change and Preserved Behavior

- The example now passes `admin_voice_snapshot.memory_workspace_config`.
- The file header records that data lookup belongs to the caller's typed Admin
  boundary.
- Prompt-file selection, legacy key parsing, safe workspace containment,
  procedural JSON initialization, and file permissions remain unchanged.

## Acceptance

1. `memory_workspace.py` contains no Dream database lookup example or executable
   database access.
2. The focused memory workspace suite passes.
3. Python compile and production database-reference scans pass.

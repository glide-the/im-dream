<!-- [Input] Repository governance, README contract, package-manager boundaries, and the Dream SDK/Runtime compatibility model. -->
<!-- [Output] Mandatory maintenance rules for humans and coding agents working in this repository. -->
<!-- [Pos] Root operational rulebook; product-level Agent interaction behavior remains in docs/Agent.md. -->
<!-- [Sync] 2026-08-28: define README parity, atomic Runtime versions, and authenticated model-capability ownership. -->

# Repository Agent Rules

This file contains mandatory repository-maintenance rules. Read it together with `AGENTS.md`, `CLAUDE.md`, affected `.folder.md` files, and the rules index under `docs/rules/` before changing code or documentation.

`docs/Agent.md` has a different purpose: it documents product-level Agent entry points and interaction behavior. Do not move repository governance into that product document.

## 1. README contract

`README.md` is the canonical English repository entry guide. `README.zh.md` is its faithful Chinese mirror.

Every change that affects setup, runtime behavior, supported versions, commands, architecture, or operational boundaries must update both files in the same change. The two files must keep the same section structure, version facts, commands, warnings, and links; translation wording may differ but meaning may not.

The README must answer all of the following without requiring prior project knowledge:

1. What Ink & Memory is and what users can do with it.
2. Which repository/service owns Dream, Admin/Gateway/PostgreSQL, the Python SDK, and the native Runtime.
3. Which branch, Python, Node, SDK, Runtime, and CLI-compatibility versions are supported.
4. How to install Admin, Python dependencies, the exact native Runtime, and frontend dependencies.
5. How to configure and start Admin, Dream backend, and Dream frontend.
6. How to run provider-free checks, automated tests, and registry acceptance.
7. Which security, schema, credential, process-ownership, platform, rollback, and fail-closed notices apply.
8. How to diagnose common failures, including SDK/Runtime mismatches and `uv sync` removing undeclared packages.

The README is an operator guide, not a historical progress diary. Do not retain stale PR status tables, obsolete branches, superseded SQLite instructions, old language/runtime requirements, or claims that no longer match the checked-in source.

## 2. SDK and Runtime version management

The Claude Python SDK and native Claude Runtime are separate release artifacts but one Dream compatibility contract:

- `uv`/PyPI manages `ink-claude-dream-agent-sdk`.
- npm manages `@glide-the/ink-claude-code-dream` and its platform package.
- `uv sync` must never be described or treated as installing/upgrading the npm Runtime.
- Dream must reject an unqualified or mismatched Runtime instead of silently using an ambient CLI.

Any SDK or Runtime version change must be atomic across the following affected surfaces:

1. `backend/pyproject.toml`, `backend/uv.lock`, and exported requirements for the Python SDK.
2. `backend/libs/claude_agent_kit/server/sdk_env.py` compatibility constants and resolver behavior.
3. `backend/Dockerfile` exact SDK/Runtime/official-rollback versions.
4. Focused contract tests and registry acceptance fixtures.
5. `README.md` and `README.zh.md` exact installation, PATH verification, and troubleshooting commands.
6. Affected architecture/deploy documents, file headers, and `.folder.md` entries.
7. Public registry evidence and provider-free fresh-install verification.

Do not merge a version-only source change that leaves local operators with an older executable and no explicit upgrade/verification path. If a unified sync command exists, it must install both ecosystems, validate the manifest/capabilities/checksums, and fail closed. Until such a command exists, the README must show the separate exact npm installation and Dream resolver verification explicitly.

Runtime errors must identify the failed field whenever safe: expected and actual Runtime version, resolved executable path, manifest path, protocol mismatch, and missing capabilities. Do not emit credentials, request bodies, transcripts, or complete sensitive environment values.

## 3. Dependency synchronization

`uv sync` makes the Python environment match declared project dependencies and may remove undeclared tools. Test-only dependencies must be either:

- declared in an explicitly reviewed development dependency group, or
- invoked with a documented ephemeral command such as `uv run --with ...`.

Do not rely on ad-hoc packages surviving a later sync. Do not add a Python package whose install hook downloads or mutates the npm Runtime; cross-ecosystem installation belongs in an explicit repository-owned orchestration command.

## 4. Runtime installation and PATH

The normal Dream Runtime path is the manifest-qualified `ink-claude-code-dream` executable resolved from `PATH`.

- Verify `command -v`, the resolved symlink target, CLI compatibility output, release manifest version, capability evidence, and executable checksum.
- Treat a running service's inherited `PATH` as immutable until that owned process is restarted.
- Do not change or restart user-owned services as an incidental setup step.
- Do not use `CLAUDE_CODE_CLI_PATH` to hide a stale normal installation. It is reserved for an explicit reviewed absolute-path rollback.
- Do not silently select the SDK-bundled CLI, ambient `claude`, or a different package version.

## 5. Schema, secrets, and test boundaries

- Admin Drizzle is the only owner of the shared PostgreSQL schema.
- Dream must not add runtime DDL, Alembic, automatic shared-table creation, or a SQLite runtime fallback.
- Never commit database credentials, Provider keys, Gateway service keys, OAuth secrets, package-registry tokens, transcripts, or user Workspace contents.
- Provider-free tests must not be reported as real-business validation.
- Real-business validation must use the normal Dream/Admin/Gateway/PostgreSQL path and leave its normal Admin-visible evidence unless the user explicitly requests cleanup.
- Tests may stop or delete only processes and temporary resources created by that test run.

## 6. Required completion checks

Before completing a relevant change:

1. Verify `README.md` and `README.zh.md` structural and factual parity.
2. Verify every new Markdown link and documented path exists.
3. Run focused tests for changed contracts and `git diff --check`.
4. For SDK/Runtime changes, run manifest resolver tests and provider-free registry acceptance.
5. Update affected file headers and `.folder.md` inventories.
6. Report exact commands, exit codes, skipped tests, live-service state, Git branch/commit/PR state, and any remaining manual operator action.

## 7. Claude Runtime model-capability ownership

Runtime request tuning must preserve explicit ownership. Global effort comes from the resource-policy last-known-good snapshot. Auto-compact, max context, and model max output come from the final authenticated Admin model-catalog selection. Missing values are omitted; browser input, user env, Deck, Plugin, workspace settings, and ambient parent env must not override these server-owned values.

`ai_models.max_output_tokens` is the existing model capability and must reach the CLI through the vendor-scoped `INK_CLAUDE_CODE_MODEL_MAX_OUTPUT_TOKENS` projection. Do not infer third-party capability by matching model IDs, and do not rewrite `max_tokens` in Gateway. The official `CLAUDE_CODE_MAX_OUTPUT_TOKENS` remains a standalone CLI override, but Dream must scrub ambient/user copies before launching its managed Runtime.

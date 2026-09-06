<!-- [Input] AutoDL direct-host scripts, the current Next.js/pnpm frontend tree, and deployment safety contracts. -->
<!-- [Output] Explicit blocked status, historical topology evidence, and requirements for a future AutoDL migration. -->
<!-- [Pos] AutoDL deployment status record; not a runnable current operator guide while the source contract is mismatched. -->
<!-- [Sync] 2026-09-06: mark the Vite/npm direct-host path incompatible with the canonical Next.js workspace at 54f3bbe5. -->

# AutoDL direct-host deployment status

## Current status: blocked

Do not use `deploy/autodl-ssh/deploy.sh` to publish revision `54f3bbe5` or a
later revision derived from the same frontend migration. The script has not been
migrated to the current Web source and dependency contract.

The failure is deterministic before a valid release can be built:

- `deploy.sh` requires `frontend/package-lock.json` and
  `frontend/vite.config.ts`, which no longer exist;
- it executes `npm ci` and a Vite build instead of installing
  `frontend/pnpm-lock.yaml` and building the root Next.js project;
- it accepts a release only when `frontend/dist/index.html` exists;
- `runtime/start-dream.sh` starts `vite preview` from
  `frontend/node_modules/vite/bin/vite.js`;
- its crawler, host-policy, health, and rollback checks are written for the old
  static application.

The current application contract is documented in the
[root operator guide](../../README.md) and the
[deployment entry matrix](../README.md). The current Web source is
`frontend/app/_dream/**`; the only frontend lock is
`frontend/pnpm-lock.yaml`.

## Historical topology

Before the Next.js migration, this directory published a direct-host stack with
Vite Preview on `127.0.0.1:6006`, FastAPI on `127.0.0.1:8765`, and Admin on
`127.0.0.1:6008`. It used `screen` for process survival and did not use Docker or
Nginx for Dream. Those facts explain the existing script names and checks; they
do not make the path compatible with the current source.

The historical launcher also installed a qualified Linux Runtime, kept Dream
workspaces and plugin artifacts on the AutoDL data root, and fixed
`INK_AGENT_SANDBOX_ENABLED=false` because the outer container did not permit the
required namespace operations. That security fact must not be erased or
silently changed by a future frontend migration: approved Bash commands ran as
the Dream root service account without bubblewrap filesystem or network
isolation.

## Invariants for a future migration

A separate production-code task must satisfy all of the following before this
directory can again be called a current deployment path:

1. Install the frozen pnpm workspace from `frontend/pnpm-lock.yaml` and build
   the root Next.js project from `frontend/`.
2. Start one owned Next.js server on the configured frontend port and FastAPI on
   its private backend port; do not recreate a second App Router or copy
   `frontend/app/_dream` into another source tree.
3. Replace every `dist/index.html`, Vite host, Vite preview, and Vite environment
   check with a Next.js-owned build, health, and graceful-shutdown contract.
4. Validate `/robots.txt`, `/sitemap.xml`, and `/llms.txt` by media type and body,
   and reject an HTML fallback. The corresponding Route Handlers currently live
   under `frontend/app/` and proxy backend-owned content.
5. Preserve the Admin-owned PostgreSQL schema boundary. The launcher must not
   migrate, restore, create, or delete the database.
6. Preserve the existing persistent workspace, Notion credential, Artifact,
   local-file, plugin Runtime, and service-home ownership and symbolic-link
   rejection rules.
7. Preserve explicit process ownership. Start, stop, and rollback may affect
   only the named Dream processes and release links created by this deployment.
8. Revalidate the qualified Claude Runtime, built-in Skill catalog, default Deck
   Plugin, frontend build, public routes, rollback behavior, and real public
   mapping before declaring the platform usable.

## Historical files retained for migration work

| File | Current meaning |
|---|---|
| `deploy.sh` | Historical Vite/npm release implementation and the concrete migration target |
| `prepare-env.sh` | Historical Vite host projection plus still-relevant secret and persistent-root projection logic |
| `runtime/start-dream.sh` | Historical Vite and FastAPI supervisor; not valid for the current frontend |
| `runtime/start-ink-memory.sh` | Historical already-published stack restarter that depends on the invalid frontend release shape |
| `runtime/init-dream-data.sh` | Persistent-directory safety logic that must be reviewed and preserved during migration |
| `test-topology.sh` | Historical topology test that still asserts removed Vite files and therefore cannot qualify the current source |

## Validation boundary

This documentation update did not connect to AutoDL, stop any service, create a
release, run a model, or establish production readiness. Until the production
scripts and their tests are migrated, the only truthful AutoDL result for the
current source is blocked by code incompatibility.

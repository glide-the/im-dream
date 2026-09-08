<!-- [Input] AutoDL direct-host scripts, current Next.js/pnpm source, and deployment safety contracts. -->
<!-- [Output] Current release, runtime, safety, verification, and rollback procedure. -->
<!-- [Pos] AutoDL Dream operator guide for the canonical Next.js/FastAPI topology. -->
<!-- [Sync] 2026-09-06: migrate AutoDL to Next.js standalone, frozen pnpm, and the Node MCP Apps runtime. -->

# AutoDL direct-host deployment

## Current topology

The script builds the sole frontend workspace from `frontend/` with pnpm's frozen
lock and Next.js standalone output. The application remains in
`frontend/app/_dream/**`; `frontend/packages/mcp-apps-runtime/**` is bundled as
the server-only Node MCP Apps runtime.

Dream uses Next.js on `127.0.0.1:6006` and FastAPI on
`127.0.0.1:8765`; Admin remains on `127.0.0.1:6008`. Next rewrites the
same-origin API/auth routes to FastAPI. The standalone launcher uses `screen`
and does not install Docker or Nginx.

`prepare-env.sh` combines the backend runtime configuration, Admin-owned
PostgreSQL identity, and a private MCP Apps env file. MCP Apps iframe content
must use a separate HTTPS origin routed to the same port 6006 Next service;
the parent origin remains the primary Dream HTTPS origin.

## Release

Create gitignored `platform.env` from `platform.env.example`, then project the
runtime env and deploy:

```bash
AUTODL_ADMIN_ENV_FILE=../ink-admin-memory/deploy/autodl-ssh/.env \
  ./deploy/autodl-ssh/prepare-env.sh
./deploy/autodl-ssh/test-topology.sh
./deploy/autodl-ssh/deploy.sh check
./deploy/autodl-ssh/deploy.sh deploy
```

`deploy` installs Node 22.18.0 and pnpm 10.28.1, installs the qualified Claude
Runtime and Notion CLI, builds a versioned Python/Next release, starts only the
owned Dream screen session, and qualifies the release only after private and
public health gates pass.

## Safety and acceptance

- Dream consumes the Admin-owned PostgreSQL schema and never runs migration,
  runtime DDL, restore, or database deletion.
- Workspace, Notion credential, Artifact, local-file, plugin Runtime, and
  service-home roots remain persistent and reject symbolic-link substitution.
- AutoDL fixes `INK_AGENT_SANDBOX_ENABLED=false` because the outer container
  rejects the required namespace operations. Approved Bash therefore runs as
  the Dream root service account without bubblewrap filesystem/network
  isolation; the launcher fails if this deployment-owned value changes.
- Start, stop, and rollback affect only the named Dream process, screen session,
  and versioned release links.
- Acceptance checks the standalone server, Node MCP Apps route manifest,
  FastAPI and same-origin health, crawler media/body (including `/llms.txt`),
  built-in Skills, default Deck Plugin, Admin dependency, and public mapping.

## Files

| File | Current meaning |
|---|---|
| `deploy.sh` | Versioned pnpm/Next/FastAPI release, verification, qualification, and rollback |
| `prepare-env.sh` | Backend, Admin DB, public-origin, sandbox, and MCP Apps runtime projection |
| `runtime/start-dream.sh` | Next.js and FastAPI supervisor |
| `runtime/start-ink-memory.sh` | Admin-first idempotent restarter for already-published releases |
| `runtime/init-dream-data.sh` | Persistent-directory ownership and symlink safety |
| `test-topology.sh` | Provider-free current topology and env projection test |

Use `status`, `logs`, and `verify` for diagnosis. `rollback` switches only the
Dream release links and never reverses Admin migrations or user data.

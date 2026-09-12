<!-- [Input] Checked-in deployment scripts, current Next.js frontend image, Admin-owned PostgreSQL contract, and platform configuration. -->
<!-- [Output] Current deployment entry matrix, commands, unsupported paths, and validation boundaries. -->
<!-- [Pos] Operator index for deploy/; detailed configuration remains in platform directories and root README files. -->
<!-- [Sync] 2026-09-06: align deployment status with Next.js, pnpm, and known script drift at revision 54f3bbe5. -->
<!-- [Sync] 2026-09-12: add the explicit-origin NATAPP edge-relay entry and recovery boundary. -->

# Deployment entry points

## Current architecture

The default Web artifact is the standalone Next.js server built from the single
pnpm workspace in `frontend/`. The default container runs that server on port
`80`; FastAPI remains a separate backend service. Admin owns Gateway,
PostgreSQL, and the shared schema.

Deployment script presence is not production acceptance. The table below states
what the checked-in scripts actually do at revision `54f3bbe5` and identifies
known gaps that prevent an entry from being treated as current.

## Entry matrix

| Platform | Entry | Current status |
|---|---|---|
| Local direct processes | [`local/deploy.sh`](local/deploy.sh) | Uses `pnpm run build` and `pnpm run dev`; an immutable Vite image may be selected only as an explicit rollback. It does not project the Browser Voice WebSocket base, and stop/clean does not strongly revalidate PID/container ownership. |
| Local Docker Compose | [`docker/deploy.sh`](docker/deploy.sh) | Builds `frontend/Dockerfile`, which installs the frozen pnpm workspace and runs standalone Next.js. The helper still checks the historical Nginx template although the default image does not consume it. |
| Remote SSH, including the Alibaba Cloud profile | [`remote-ssh/deploy.sh`](remote-ssh/deploy.sh) | Builds the same Next.js image through Compose. Its Compose file still passes `VITE_PUBLIC_SITE_URL`; the current Dockerfile ignores that argument, so it is configuration drift rather than active metadata injection. |
| NATAPP edge relay on an existing SSH host | [`remote-ssh/switch-edge-relay.sh`](remote-ssh/switch-edge-relay.sh) | Does not build or stop services. It atomically backs up and relays the existing Dream/Admin domains to two explicit origins, tests nginx, reloads it, and supports checksum-verified rollback. |
| Google Cloud Run | [`google-cloud/deploy.sh`](google-cloud/deploy.sh) | **Blocked for production.** It builds the same Next.js image but still passes the ignored Vite build argument; adjacent SQLite synchronization conflicts with the Admin-owned PostgreSQL-only schema contract. |
| AutoDL direct host | [`autodl-ssh/deploy.sh`](autodl-ssh/deploy.sh) | Builds the frozen pnpm workspace as standalone Next.js, verifies the Node MCP Apps routes, and supervises Next/FastAPI on 6006/8765 without database DDL. |

The Docker, Remote SSH, and Google Cloud rows describe checked-in build
mechanics. This documentation update did not deploy them, call a real model, or
establish public production availability.

## Local commands

Validate inputs without starting services:

```bash
./deploy/local/deploy.sh check
./deploy/local/deploy.sh --dry-run build
```

Build, start, and verify the current local path:

```bash
./deploy/local/deploy.sh build
./deploy/local/deploy.sh start
./deploy/local/deploy.sh verify
```

The local script records process identifiers, but `stop`/`clean` trusts those
PID files and the configured rollback-container name without validating process
start time, command, cwd, image, or a run-owned label. Confirm identity manually
before stopping; stale identifiers can target user-owned resources. The launcher
also omits the Browser Voice WebSocket base; use the explicit manual command in
the root README for a Voice-capable local run.

## Docker and Remote SSH checks

Render the local Compose configuration:

```bash
./deploy/docker/deploy.sh check
./deploy/docker/deploy.sh config
```

Inspect the Remote SSH plan without changing a server:

```bash
./deploy/remote-ssh/deploy.sh --dry-run plan
```

For an edge-only NATAPP switch, do not use the Compose release path or infer a
tunnel port. Follow the explicit-origin [edge-relay runbook](../docs/deploy/natapp-edge-relay.md).

Remote deployment requires explicit target configuration, a protected backend
environment file, and the Mihomo configuration described by
[`clash/README.md`](clash/README.md). A dry run is a script check, not a remote
release or business acceptance result.

## Database and secret boundaries

- Admin Drizzle is the only owner of the shared PostgreSQL schema.
- Dream deployment scripts must not create tables, run Alembic, introduce a
  SQLite runtime fallback, or claim an unpublished schema capability.
- The Google Cloud SQLite backup and upload commands are retained historical
  code and must not be used for the current shared database.
- Database credentials, provider keys, Gateway service keys, OAuth secrets,
  package-registry tokens, and user workspace contents must remain outside Git.
- Docker Compose deployment requires a private `deploy/clash/config.yaml`; the
  repository excludes that file.

## Known code gaps

The following gaps require production-code changes and validation in a separate
task; this documentation change does not repair them:

1. Remove or replace the ignored `VITE_PUBLIC_SITE_URL` arguments in root,
   Remote SSH, and Google Cloud build orchestration with a real Next.js-owned
   metadata contract when one is designed.
2. Retire the Google Cloud SQLite synchronization path under the Admin-owned
   PostgreSQL schema contract.
3. Remove the default Docker helper's obsolete Nginx-template prerequisite after
   rollback ownership is explicitly separated.
4. Project an explicit local Browser Voice WebSocket base, or render the runtime
   config, and add a launcher-owned Voice connection check.
5. Bind local PID/container cleanup to verifiable run ownership such as process
   start time/command/cwd plus a container label; reject stale identifiers.

## Further documentation

- [Root English operator guide](../README.md)
- [Root Chinese operator guide](../README.zh.md)
- [Deployment architecture and status](../docs/deploy/README.md)
- [AutoDL direct-host guide](autodl-ssh/README.md)

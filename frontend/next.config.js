// [Input] Configuration-file location, server-owned deployment environment and public asset/API behavior.
// [Output] Stable frontend-root Next config with optional standalone output and Python fallbacks.
// [Pos] Sole Next project configuration owned by the frontend workspace root.
// [Sync] 2026-09-05: move the nested Next config to the canonical root without enabling production Apps.
// [Sync] 2026-09-05: leave runtime-injected crawler resources to root Route Handlers instead of build-time rewrites.
// [Sync] 2026-09-06: enforce the canonical root TypeScript gate during every production build.
// [Sync] 2026-09-06: reserve MCP Apps and streaming Claude Agent API routes for
//                    explicit Next handlers while proxying other APIs to Python.
// [Sync] 2026-09-14: bind Turbopack and tracing to this config's directory, not ancestor lockfiles.
// [Sync] 2026-09-14: runtime API/auth Route Handlers own credentials; disable legacy unauthenticated rewrites.

import { dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const projectRoot = dirname(fileURLToPath(import.meta.url));
const standaloneOutput = process.env.INK_NEXT_OUTPUT === 'standalone';

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: standaloneOutput ? 'standalone' : undefined,
  reactStrictMode: true,
  poweredByHeader: false,
  turbopack: { root: projectRoot },
  async headers() {
    return [
      {
        source: '/runtime-config.js',
        headers: [
          { key: 'Cache-Control', value: 'no-store, no-cache, must-revalidate' },
          { key: 'Pragma', value: 'no-cache' },
          { key: 'Expires', value: '0' },
        ],
      },
    ];
  },
  async rewrites() {
    return [];
  },
};

export default nextConfig;

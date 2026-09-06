// [Input] Server-owned deployment environment and the existing public asset/API behavior.
// [Output] Root Next compatibility shell config with optional standalone output and Python fallbacks.
// [Pos] Sole Next project configuration owned by the frontend workspace root.
// [Sync] 2026-09-05: move the nested Next config to the canonical root without enabling production Apps.
// [Sync] 2026-09-05: leave runtime-injected crawler resources to root Route Handlers instead of build-time rewrites.
// [Sync] 2026-09-06: enforce the canonical root TypeScript gate during every production build.
// [Sync] 2026-09-06: reserve MCP Apps API routes for Next while proxying other APIs to Python.

const backendUrl = process.env.INK_BACKEND_INTERNAL_URL?.replace(/\/+$/, '');
const standaloneOutput = process.env.INK_NEXT_OUTPUT === 'standalone';

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: standaloneOutput ? 'standalone' : undefined,
  reactStrictMode: true,
  poweredByHeader: false,
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
    if (!backendUrl) return [];
    return {
      beforeFiles: [],
      afterFiles: [
        {
          source: '/api/:path((?!mcp-apps(?:/|$)).*)',
          destination: `${backendUrl}/api/:path`,
        },
        { source: '/auth/:path*', destination: `${backendUrl}/auth/:path*` },
        { source: '/oauth/google/:path*', destination: `${backendUrl}/oauth/google/:path*` },
        { source: '/oauth/device/code', destination: `${backendUrl}/oauth/device/code` },
        { source: '/oauth/token', destination: `${backendUrl}/oauth/token` },
      ],
      fallback: [],
    };
  },
};

export default nextConfig;

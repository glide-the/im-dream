// [Input] Same-origin public REST/SSE/file requests with Browser or native OAuth credentials.
// [Output] Thin delegation to the sole BFF API authentication and streaming transport.
// [Pos] Generic Next API Route Handler; explicit health/MCP Apps routes retain their owners.
// [Sync] 2026-09-14: replace unauthenticated generic rewrites with runtime request validation.
import { proxyApiRequest } from '../_auth/api-proxy';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';
export const GET = proxyApiRequest;
export const HEAD = proxyApiRequest;
export const POST = proxyApiRequest;
export const PUT = proxyApiRequest;
export const PATCH = proxyApiRequest;
export const DELETE = proxyApiRequest;
export const OPTIONS = proxyApiRequest;

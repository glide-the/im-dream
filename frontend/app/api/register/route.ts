// [Input] Legacy authentication path; sensitive request data is never read.
// [Output] Explicit 410 configured Admin standard-endpoint response.
// [Pos] Thin Next retired issuer path; shared public authority owner supplies the response.
// [Sync] 2026-09-14: preserve original public path without local signing or credential forwarding.
// [Sync] 2026-11-19: observe the legacy 410 without reading submitted credentials.
import { retiredAuthentication } from '../../api/_auth/retired-auth.ts';
import { tracedOptions, withApiTrace } from '../_trace.ts';
export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';
const route = '/api/register';
export const POST = withApiTrace(route, () => retiredAuthentication());
export const OPTIONS = tracedOptions(route, ['POST']);

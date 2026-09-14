// [Input] Legacy authentication path; sensitive request data is never read.
// [Output] Explicit 410 configured Admin standard-endpoint response.
// [Pos] Thin Next retired issuer path; shared public authority owner supplies the response.
// [Sync] 2026-09-14: preserve original public path without local signing or credential forwarding.
import { retiredAuthentication } from '../../../api/_auth/retired-auth.ts';
export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';
export const POST = () => retiredAuthentication();

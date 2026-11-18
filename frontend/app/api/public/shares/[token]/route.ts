// [Input] Anonymous opaque share token; visitor headers remain outside the upstream request.
// [Output] No-store public snapshot, uniform unavailable response or temporary failure.
// [Pos] Explicit public exception to the authenticated generic BFF, using the same server reader as the page.
// [Sync] 2026-11-19: trace the public route template without serializing its token.
import {readPublicShare, publicShareHeaders} from '../../../../share/readPublicShare';
import {tracedOptions, withApiTrace} from '../../../_trace';
export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';
const route = '/api/public/shares/{token}';
export const GET = withApiTrace(route, async (request, {params}: {params: Promise<{token: string}>}) => {
  const {token} = await params, result = await readPublicShare(token, request.signal);
  return result.status === 200 ? Response.json(result.snapshot, {headers: publicShareHeaders})
    : Response.json({error: result.status === 404 ? 'SHARE_UNAVAILABLE' : 'SHARE_TEMPORARILY_UNAVAILABLE'}, {status: result.status, headers: publicShareHeaders});
});
export const OPTIONS = tracedOptions(route, ['GET']);

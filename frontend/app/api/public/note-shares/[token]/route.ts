// [Input] Legacy unowned file-share token.
// [Output] Uniform anonymous 404 without credentials, storage reads or content output.
// [Pos] Explicit legacy closure alongside the canonical public share route.
// [Sync] 2026-11-19: trace the uniform legacy 404 with a literal route template.
import {publicShareHeaders} from '../../../../share/readPublicShare';
import {tracedOptions, withApiTrace} from '../../../_trace';
export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';
const route = '/api/public/note-shares/{token}';
export const GET = withApiTrace(route, () =>
  Response.json({error: 'SHARE_UNAVAILABLE'}, {status: 404, headers: publicShareHeaders}));
export const OPTIONS = tracedOptions(route, ['GET']);

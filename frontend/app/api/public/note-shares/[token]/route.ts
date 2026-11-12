// [Input] Legacy unowned file-share token.
// [Output] Uniform anonymous 404 without credentials, storage reads or content output.
// [Pos] Explicit legacy closure alongside the canonical public share route.
import {publicShareHeaders} from '../../../../share/readPublicShare';
export const dynamic = 'force-dynamic';
export function GET() {return Response.json({error: 'SHARE_UNAVAILABLE'}, {status: 404, headers: publicShareHeaders});}

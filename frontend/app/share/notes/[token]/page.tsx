// [Input] Legacy note share URL; old unowned file tokens remain closed.
// [Output] Canonical route for valid new database tokens or the ordinary not-found page.
// [Pos] Compatibility navigation only; it performs no file reads.
import {notFound, redirect} from 'next/navigation';
export default async function LegacyNoteSharePage({params}: {params: Promise<{token: string}>}) {
  const {token} = await params;
  if (!/^[A-Za-z0-9_-]{43}$/.test(token)) notFound();
  redirect('/share/' + token);
}

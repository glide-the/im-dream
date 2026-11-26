/* eslint-disable react-refresh/only-export-components -- Next route metadata and render policy. */
// [Input] Opaque database share token and server-owned Python origin.
// [Output] Dynamic anonymous snapshot page after per-request revocation checks.
// [Pos] Public route independent of authentication and ordinary application navigation.
import type {Metadata} from 'next';
import {notFound} from 'next/navigation';
import {readPublicShare} from '../readPublicShare';
import PublicShareContent from '../../_dream/components/sharing/PublicShareContent';
export const dynamic = 'force-dynamic';
export const metadata: Metadata = {title: 'Kastention · Shared content', robots: {index: false, follow: false}, referrer: 'no-referrer'};
function unavailable() {return <main role="alert" style={{padding: 24}}>分享内容暂时无法读取，请稍后重试。<br/>Shared content is temporarily unavailable. Please try again later.</main>;}
export default async function SharedContentPage({params}: {params: Promise<{token: string}>}) {
  const {token} = await params;
  const result = await readPublicShare(token);
  if (result.status === 404) notFound();
  if (result.status !== 200) return unavailable();
  return <main style={{minHeight: '100dvh', background: 'var(--color-bg-app)'}}><PublicShareContent snapshot={result.snapshot}/></main>;
}

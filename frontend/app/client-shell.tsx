'use client';

// [Input] Shared application entry with explicit .web platform resolution.
// [Output] Client-only RNW/Web mount under the Next Server Component shell.
// [Pos] Sole App Router client boundary for the unified frontend source.
// [Sync] 2026-11-19: install the same-origin Web Bearer transport before loading any business module.
// [Sync] 2026-10-24: mount the same provider composition used by the native mobile resource target.

import dynamic from 'next/dynamic';
import { installBrowserBearerFetch } from './_dream/lib/browserSession.web';

installBrowserBearerFetch();

const SharedApp = dynamic(() => import('../src/App'), { ssr: false });

export default function ClientShell() {
  return <SharedApp />;
}

'use client';

// [Input] Shared application entry with explicit .web platform resolution.
// [Output] Client-only RNW/Web mount under the Next Server Component shell.
// [Pos] Sole App Router client boundary for the unified frontend source.
// [Sync] 2026-10-24: mount the same provider composition used by the native mobile resource target.

import dynamic from 'next/dynamic';

const SharedApp = dynamic(() => import('../src/App'), { ssr: false });

export default function ClientShell() {
  return <SharedApp />;
}

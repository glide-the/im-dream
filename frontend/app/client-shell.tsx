'use client';

// [Input] Canonical browser-only Dream React root, auth context, i18n, and theme helpers from app/_dream.
// [Output] Client-only Dream mount under the Next Server Component shell.
// [Pos] Sole App Router boundary allowed to load browser-owned Dream modules.
// [Sync] 2026-09-06: resolve the canonical Dream source owner under the private app/_dream tree.

import dynamic from 'next/dynamic';
import { useEffect } from 'react';

import '@/_dream/i18n';
import { AuthProvider } from '@/_dream/contexts/AuthContext';
import { initTheme } from '@/_dream/utils/theme';

const DreamApp = dynamic(() => import('@/_dream/App'), { ssr: false });

export default function ClientShell() {
  useEffect(() => {
    initTheme();
    window.__INK_FRONTEND_VERSION__ = 'next-phase1';
  }, []);

  return (
    <AuthProvider>
      <DreamApp />
    </AuthProvider>
  );
}

declare global {
  interface Window {
    __INK_FRONTEND_VERSION__?: string;
  }
}

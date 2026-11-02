'use client';

// [Input] Canonical Dream application, auth provider, i18n, theme helpers, and a host version label.
// [Output] One shared provider composition for the Next browser shell and native mobile resource target.
// [Pos] Sole React business-root composition beneath host-specific bootstrap code.
// [Sync] 2026-10-24: share provider initialization across Web and local WebView resources.
// [Sync] 2026-10-27: scope RN-owned navigation spacing to the mobile host.

import { useEffect } from 'react';

import App from './App';
import { AuthProvider } from './contexts/AuthContext';
import './i18n';
import { initTheme } from './utils/theme';
import {isReactNativeHost} from './platform/mobileHost';
import './platform/mobileHost.css';

export default function DreamRoot({ frontendVersion }: { frontendVersion: string }) {
  useEffect(() => {
    initTheme();
    window.__INK_FRONTEND_VERSION__ = frontendVersion;
    if (isReactNativeHost()) document.documentElement.dataset.mobileHost = 'react-native';
  }, [frontendVersion]);

  return <AuthProvider><App /></AuthProvider>;
}

declare global {
  interface Window {
    __INK_FRONTEND_VERSION__?: string;
  }
}

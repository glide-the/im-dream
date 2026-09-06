/* eslint-disable react-refresh/only-export-components -- App Router layouts intentionally export metadata alongside the component. */
// [Input] Server-owned public-site metadata, runtime config, and the canonical app/_dream global stylesheet.
// [Output] Stable root document, SEO metadata, and pre-hydration runtime config for the Dream shell.
// [Pos] Next Server Component root; no browser globals are accessed here.
// [Sync] 2026-09-06: resolve global presentation from the private canonical app/_dream source tree.

import type { Metadata } from 'next';
import Script from 'next/script';
import type { ReactNode } from 'react';

import '@/_dream/index.css';

const PRODUCT_TITLE = 'Ink & Memory | AI Journaling Studio for Reflective Writing';
const PRODUCT_DESCRIPTION = 'Ink & Memory is a bilingual AI journaling studio for reflective writing, inner voice feedback, visual memory timelines, and personal pattern discovery.';

function publicSiteUrl(): URL | undefined {
  const configured = process.env.INK_PUBLIC_SITE_URL?.trim();
  if (!configured) return undefined;
  try {
    return new URL(configured);
  } catch {
    return undefined;
  }
}

export function generateMetadata(): Metadata {
  const metadataBase = publicSiteUrl();
  return {
    metadataBase,
    title: PRODUCT_TITLE,
    description: PRODUCT_DESCRIPTION,
    keywords: ['AI journaling', 'reflective writing', 'bilingual journal', 'personal knowledge', 'memory timeline'],
    applicationName: 'Ink & Memory',
    icons: { icon: '/placeholder-memory.png' },
    alternates: metadataBase ? { canonical: '/' } : undefined,
    openGraph: {
      type: 'website',
      siteName: 'Ink & Memory',
      title: 'Ink & Memory | AI Journaling Studio',
      description: PRODUCT_DESCRIPTION,
      url: metadataBase ? '/' : undefined,
      images: metadataBase ? [{ url: '/login-banner.jpg', alt: 'Ink & Memory reflective journaling interface' }] : undefined,
      locale: 'en_US',
      alternateLocale: ['zh_CN'],
    },
    twitter: {
      card: 'summary_large_image',
      title: 'Ink & Memory | AI Journaling Studio',
      description: PRODUCT_DESCRIPTION,
      images: metadataBase ? ['/login-banner.jpg'] : undefined,
    },
    robots: { index: true, follow: true },
  };
}

function structuredData() {
  const url = publicSiteUrl()?.toString();
  return {
    '@context': 'https://schema.org',
    '@graph': [
      {
        '@type': 'Organization',
        name: 'Ink & Memory',
        ...(url ? { url, logo: new URL('/login-banner.jpg', url).toString() } : {}),
        description: 'Open-source AI journaling and reflective writing application.',
      },
      {
        '@type': 'WebApplication',
        name: 'Ink & Memory',
        ...(url ? { url } : {}),
        applicationCategory: 'LifestyleApplication',
        operatingSystem: 'Any modern web browser',
        description: PRODUCT_DESCRIPTION,
        inLanguage: ['en', 'zh-CN'],
      },
    ],
  };
}

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        <Script src="/runtime-config.js?runtime=1" strategy="beforeInteractive" />
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(structuredData()).replace(/</g, '\\u003c') }}
        />
        {children}
      </body>
    </html>
  );
}

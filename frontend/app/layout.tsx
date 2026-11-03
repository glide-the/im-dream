/* eslint-disable react-refresh/only-export-components -- App Router layouts intentionally export metadata alongside the component. */
// [Sync] 2026-11-02: adopt display-only Kastention naming; existing behavior and technical identities remain.
// [Input] Server-owned public-site metadata, runtime config, and the canonical app/_dream global stylesheet.
// [Output] Stable root document, SEO metadata, and pre-hydration runtime config for the Dream shell.
// [Pos] Next Server Component root; no browser globals are accessed here.
// [Sync] 2026-09-06: resolve global presentation from the private canonical app/_dream source tree.
// [Sync] 2026-09-06: load the user-installed Grab inspector only in the local development document.

import { BRAND_NAME, BRAND_BANNER_PATH } from './_dream/constants/brand';
import type { Metadata } from 'next';
import Script from 'next/script';
import type { ReactNode } from 'react';

import '@/_dream/index.css';

const PRODUCT_TITLE = `${BRAND_NAME} | AI Journaling Studio for Reflective Writing`;
const PRODUCT_DESCRIPTION = `${BRAND_NAME} is a bilingual AI journaling studio for reflective writing, inner voice feedback, visual memory timelines, and personal pattern discovery.`;

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
    applicationName: BRAND_NAME,
    icons: { icon: '/placeholder-memory.png' },
    alternates: metadataBase ? { canonical: '/' } : undefined,
    openGraph: {
      type: 'website',
      siteName: BRAND_NAME,
      title: `${BRAND_NAME} | AI Journaling Studio`,
      description: PRODUCT_DESCRIPTION,
      url: metadataBase ? '/' : undefined,
      images: metadataBase ? [{ url: BRAND_BANNER_PATH, alt: `${BRAND_NAME} reflective journaling interface` }] : undefined,
      locale: 'en_US',
      alternateLocale: ['zh_CN'],
    },
    twitter: {
      card: 'summary_large_image',
      title: `${BRAND_NAME} | AI Journaling Studio`,
      description: PRODUCT_DESCRIPTION,
      images: metadataBase ? [BRAND_BANNER_PATH] : undefined,
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
        name: BRAND_NAME,
        ...(url ? { url, logo: new URL(BRAND_BANNER_PATH, url).toString() } : {}),
        description: 'Open-source AI journaling and reflective writing application.',
      },
      {
        '@type': 'WebApplication',
        name: BRAND_NAME,
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
      <head>
        {process.env.NODE_ENV === "development" && (
          <Script
            src="//unpkg.com/react-grab/dist/index.global.js"
            crossOrigin="anonymous"
            strategy="beforeInteractive"
          />
        )}
      </head>
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

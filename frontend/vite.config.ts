// [Input] Vite mode env, React plugin, and public site URL build configuration.
// [Output] Build the SPA under /ink-and-memory/ with SEO HTML placeholders resolved.
// [Pos] frontend build configuration
// [Sync] 2026-06-14: add Codex SEO public URL replacement for canonical, OG, and JSON-LD metadata.
import { defineConfig, loadEnv, type Plugin } from 'vite'
import react from '@vitejs/plugin-react'

const BASE_PATH = '/ink-and-memory/'
const DEFAULT_PUBLIC_SITE_URL = 'http://localhost:5173/ink-and-memory/'

function withTrailingSlash(value: string): string {
  return value.endsWith('/') ? value : `${value}/`
}

function joinSeoUrl(baseUrl: string, path: string): string {
  const cleanPath = path.replace(/^\/+/, '')
  return `${withTrailingSlash(baseUrl)}${cleanPath}`
}

function escapeHtmlAttribute(value: string): string {
  return value
    .replace(/&/g, '&amp;')
    .replace(/"/g, '&quot;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
}

function seoHtmlReplacementPlugin(publicSiteUrl: string): Plugin {
  const siteUrl = withTrailingSlash(publicSiteUrl.trim() || DEFAULT_PUBLIC_SITE_URL)
  const imageUrl = joinSeoUrl(siteUrl, 'login-banner.jpg')
  const replacements: Record<string, string> = {
    '%SEO_PUBLIC_SITE_URL%': escapeHtmlAttribute(siteUrl),
    '%SEO_PUBLIC_IMAGE_URL%': escapeHtmlAttribute(imageUrl),
    '%SEO_PUBLIC_SITE_URL_JSON%': JSON.stringify(siteUrl),
    '%SEO_PUBLIC_IMAGE_URL_JSON%': JSON.stringify(imageUrl),
  }

  return {
    name: 'ink-seo-html-replacements',
    transformIndexHtml(html) {
      let transformed = html
      for (const [token, replacement] of Object.entries(replacements)) {
        transformed = transformed.replaceAll(token, replacement)
      }
      return transformed
    },
  }
}

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, '.', '')
  const publicSiteUrl = env.VITE_PUBLIC_SITE_URL || DEFAULT_PUBLIC_SITE_URL

  return {
    plugins: [react(), seoHtmlReplacementPlugin(publicSiteUrl)],
    base: BASE_PATH,
    server: {
      proxy: {
        '/ink-and-memory/api': {
          target: 'http://localhost:8765',
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/ink-and-memory/, '')
        },
        '/ink-and-memory/polycli': {
          target: 'http://localhost:8765',
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/ink-and-memory/, '')
        }
      }
    }
  }
})

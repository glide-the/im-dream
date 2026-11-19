// [Input] Same-origin protected file URLs or ordinary public/data/blob media URLs.
// [Output] Bearer-fetched object URLs for images and explicit file downloads, released after use.
// [Pos] Web media adapter for browser elements that cannot attach Authorization headers.
import { useEffect, useState, type ComponentProps } from 'react';
import { isProtectedBrowserUrl } from '../../lib/browserSession.web';

export function AuthenticatedImage({ src, alt, ...props }: ComponentProps<'img'>) {
  const protectedUrl = typeof src === 'string' && isProtectedBrowserUrl(src);
  const [resource, setResource] = useState<{ source: string; url: string } | null>(null);
  useEffect(() => {
    if (!protectedUrl || typeof src !== 'string') return;
    const controller = new AbortController(); let objectUrl: string | undefined;
    const clear = () => { controller.abort(); if (objectUrl) URL.revokeObjectURL(objectUrl); setResource(null); };
    window.addEventListener('ink:auth-state', clear);
    void fetch(src, { signal: controller.signal, cache: 'no-store' }).then(async response => {
      if (!response.ok) return;
      const blob = await response.blob();
      if (controller.signal.aborted) return;
      objectUrl = URL.createObjectURL(blob); setResource({ source: src, url: objectUrl });
    }).catch(() => { /* The existing alt text remains available when media cannot load. */ });
    return () => { controller.abort(); window.removeEventListener('ink:auth-state', clear); if (objectUrl) URL.revokeObjectURL(objectUrl); };
  }, [src, protectedUrl]);
  return <img {...props} alt={alt} src={protectedUrl ? (resource?.source === src ? resource.url : undefined) : src} />;
}

export function AuthenticatedLink({ href, download, children, onClick, ...props }: ComponentProps<'a'>) {
  const [failed, setFailed] = useState(false);
  return <><a {...props} href={href} download={download} onClick={async event => {
    onClick?.(event);
    if (event.defaultPrevented || !href || !isProtectedBrowserUrl(href)) return;
    event.preventDefault(); setFailed(false);
    try {
      const response = await fetch(href, { cache: 'no-store' });
      if (!response.ok) throw new Error('DOWNLOAD_UNAVAILABLE');
      const url = URL.createObjectURL(await response.blob());
      const anchor = document.createElement('a'); anchor.href = url;
      anchor.download = typeof download === 'string' ? download : decodeURIComponent(new URL(href, window.location.origin).pathname.split('/').pop() || 'download');
      document.body.append(anchor); anchor.click(); anchor.remove();
      setTimeout(() => URL.revokeObjectURL(url), 0);
    } catch { setFailed(true); }
  }}>{children}</a>{failed ? <span role="alert">Download failed. Please try again.</span> : null}</>;
}

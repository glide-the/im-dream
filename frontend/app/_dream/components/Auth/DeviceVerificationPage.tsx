// [Input] Existing device verification page URL and optional device user_code.
// [Output] Redirect to the sole Admin review/approve/deny UI through the configured BFF entry.
// [Pos] Legacy Browser device entry; no local device state, decision API or OAuth credentials.
// [Sync] 2026-09-14: route device authorization to Admin without a second authority.
import { useEffect } from 'react';

export default function DeviceVerificationPage() {
  const query = typeof window === 'undefined' ? '' : new URLSearchParams({ user_code: new URLSearchParams(window.location.search).get('user_code') ?? '' }).toString();
  const destination = '/auth/device?' + query;
  useEffect(() => { window.location.replace(destination); }, [destination]);
  return <a href={destination}>Continue to device authorization</a>;
}

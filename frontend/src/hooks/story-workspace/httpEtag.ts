// [Input] One server-owned business revision and an HTTP ETag response header.
// [Output] Exact strong request tag formatting and strong/weak response matching.
// [Pos] Shared Story Workspace HTTP cache-validator policy.
// [Sync] 2026-09-02: accept only an exact optional W/ wrapper around one revision.

export function storyWorkspaceQuotedEtag(etag: string): string {
  return `"${etag}"`;
}

export function storyWorkspaceResponseMatchesEtag(
  responseEtag: string | null,
  etag: string,
): boolean {
  const quotedEtag = storyWorkspaceQuotedEtag(etag);
  return responseEtag === quotedEtag || responseEtag === `W/${quotedEtag}`;
}

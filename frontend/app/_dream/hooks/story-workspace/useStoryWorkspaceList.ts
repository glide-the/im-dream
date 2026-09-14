// [Sync] 2026-09-14: same-origin Cookie session with in-memory CSRF; no Browser OAuth Bearer/storage.
import { getBrowserCsrfToken, browserRequestHeaders } from '../../lib/browserSession';
import { useCallback, useEffect, useMemo, useState } from 'react';

import { apiUrl } from '../../lib/apiBase';
import type {
  StoryWorkspaceListQuery,
  StoryWorkspaceListResponse,
  StoryWorkspaceListState,
} from './contracts';

const EMPTY_PAGINATION = {
  page: 1,
  per_page: 20,
  total: 0,
  total_pages: 0,
};

function buildQueryString(query: StoryWorkspaceListQuery): string {
  const params = new URLSearchParams();
  const search = query.q?.trim();

  if (search) params.set('q', search);
  if (query.reviewStatus?.length) params.set('review_status', query.reviewStatus.join(','));
  if (query.sort) params.set('sort', query.sort);
  if (query.order) params.set('order', query.order);
  params.set('page', String(query.page ?? 1));
  params.set('per_page', String(query.perPage ?? 20));

  return params.toString();
}

export function useStoryWorkspaceList<T>(
  endpoint: string,
  query: StoryWorkspaceListQuery,
  appendParams?: (params: URLSearchParams) => void,
): StoryWorkspaceListState<T> {
  const baseQueryString = buildQueryString(query);
  const queryString = useMemo(() => {
    const params = new URLSearchParams(baseQueryString);
    appendParams?.(params);
    return params.toString();
  }, [appendParams, baseQueryString]);
  const [data, setData] = useState<T[]>([]);
  const [pagination, setPagination] = useState(EMPTY_PAGINATION);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [requestVersion, setRequestVersion] = useState(0);

  const refetch = useCallback(() => {
    setRequestVersion((version) => version + 1);
  }, []);

  useEffect(() => {
    const controller = new AbortController();

    async function load() {
      setIsLoading(true);
      setError(null);

      try {
        const headers = new Headers({ Accept: 'application/json' });
        const csrfToken = getBrowserCsrfToken();
        for (const [name, value] of Object.entries(browserRequestHeaders({}, csrfToken))) headers.set(name, value);

        const response = await fetch(apiUrl(`${endpoint}?${queryString}`), {
          credentials: 'include',
          headers,
          signal: controller.signal,
        });
        if (!response.ok) {
          throw new Error(`列表加载失败（${response.status}）`);
        }

        const payload = await response.json() as StoryWorkspaceListResponse<T>;
        setData(Array.isArray(payload.data) ? payload.data : []);
        setPagination(payload.pagination ?? EMPTY_PAGINATION);
      } catch (cause) {
        if (controller.signal.aborted) return;
        setData([]);
        setPagination(EMPTY_PAGINATION);
        setError(cause instanceof Error ? cause : new Error('列表加载失败'));
      } finally {
        if (!controller.signal.aborted) setIsLoading(false);
      }
    }

    void load();
    return () => controller.abort();
  }, [endpoint, queryString, requestVersion]);

  return { data, pagination, isLoading, error, refetch };
}

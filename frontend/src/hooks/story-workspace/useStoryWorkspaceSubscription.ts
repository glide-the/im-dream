// [Input] Strict Product API client and the current subscription page pagination/commands.
// [Output] One authoritative Token-only page state with preview/execute/refetch orchestration.
// [Pos] Story Workspace subscription application hook; it never derives server facts locally.

import { useCallback, useEffect, useRef, useState } from 'react';
import {
  ProductApiError,
  fetchProductModelCatalog,
  fetchProductPlans,
  fetchProductSubscriptionContext,
  fetchProductUsage,
  submitProductSubscriptionCommand,
  type CommandPreviewEnvelope,
  type CommandResultEnvelope,
  type ExecuteProductCommand,
  type ModelCatalogEnvelope,
  type PlansEnvelope,
  type PreviewProductCommand,
  type ProductAction,
  type ProductCommandRequestOptions,
  type ProductRequestOptions,
  type SubscriptionContextEnvelope,
  type UsageEnvelope,
} from '../../api/productApi';

const DEFAULT_PLAN_PAGE_SIZE = 20;
const DEFAULT_USAGE_PAGE_SIZE = 25;

export interface StoryWorkspaceSubscriptionData {
  context: SubscriptionContextEnvelope;
  plans: PlansEnvelope;
  usage: UsageEnvelope;
  models: ModelCatalogEnvelope;
}

export interface StoryWorkspaceSubscriptionApi {
  context: (options?: ProductRequestOptions) => Promise<SubscriptionContextEnvelope>;
  plans: (input: { page: number; pageSize: number }, options?: ProductRequestOptions) => Promise<PlansEnvelope>;
  usage: (input: { page: number; pageSize: number }, options?: ProductRequestOptions) => Promise<UsageEnvelope>;
  models: (options?: ProductRequestOptions) => Promise<ModelCatalogEnvelope>;
  command: typeof submitProductSubscriptionCommand;
}

const DEFAULT_API: StoryWorkspaceSubscriptionApi = {
  context: fetchProductSubscriptionContext,
  plans: fetchProductPlans,
  usage: fetchProductUsage,
  models: fetchProductModelCatalog,
  command: submitProductSubscriptionCommand,
};

export interface StoryWorkspaceSubscriptionCommandState {
  preview: CommandPreviewEnvelope | null;
  result: CommandResultEnvelope | null;
  targetPlanVersionId: string | null;
  isPreviewing: boolean;
  isExecuting: boolean;
  error: ProductApiError | null;
}

export interface UseStoryWorkspaceSubscriptionOptions {
  api?: StoryWorkspaceSubscriptionApi;
  planPageSize?: number;
  usagePageSize?: number;
}

function normalizeError(cause: unknown): ProductApiError {
  if (cause instanceof ProductApiError) return cause;
  return new ProductApiError({
    code: 'PRODUCT_DEPENDENCY_UNAVAILABLE',
    status: 503,
    message: '订阅服务暂时不可用。',
  });
}

function isAbortError(cause: unknown): boolean {
  return cause instanceof DOMException && cause.name === 'AbortError';
}

export function buildProductCommandPreview(
  action: ProductAction,
  targetPlanVersionId: string | null,
  currentVersion: number | null,
): PreviewProductCommand {
  return {
    action,
    phase: 'preview',
    targetPlanVersionId,
    expectedVersion: action === 'create' ? null : currentVersion,
  };
}

export function buildProductCommandExecute(
  preview: CommandPreviewEnvelope,
  targetPlanVersionId: string | null,
  reason: string,
): ExecuteProductCommand {
  return {
    action: preview.data.action,
    phase: 'execute',
    targetPlanVersionId,
    expectedVersion: preview.data.expectedVersion,
    previewId: preview.data.previewId,
    digest: preview.data.digest,
    expiresAt: preview.data.expiresAt,
    reason,
  };
}

export function newProductCommandIdempotencyKey(
  randomUuid: () => string = () => crypto.randomUUID(),
): string {
  return `dream-subscription-${randomUuid()}`;
}

export function useStoryWorkspaceSubscription(
  options: UseStoryWorkspaceSubscriptionOptions = {},
) {
  const api = options.api ?? DEFAULT_API;
  const planPageSize = options.planPageSize ?? DEFAULT_PLAN_PAGE_SIZE;
  const usagePageSize = options.usagePageSize ?? DEFAULT_USAGE_PAGE_SIZE;
  const [planPage, setPlanPageState] = useState(1);
  const [usagePage, setUsagePageState] = useState(1);
  const [refreshVersion, setRefreshVersion] = useState(0);
  const [data, setData] = useState<StoryWorkspaceSubscriptionData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<ProductApiError | null>(null);
  const [announcement, setAnnouncement] = useState('正在读取月度 Token 订阅。');
  const [commandState, setCommandState] = useState<StoryWorkspaceSubscriptionCommandState>({
    preview: null,
    result: null,
    targetPlanVersionId: null,
    isPreviewing: false,
    isExecuting: false,
    error: null,
  });
  const idempotencyKeyRef = useRef<string | null>(null);
  const hasLoadedRef = useRef(false);

  useEffect(() => {
    const controller = new AbortController();
    setError(null);
    if (!hasLoadedRef.current) setIsLoading(true);
    else setIsRefreshing(true);

    void Promise.all([
      api.context({ signal: controller.signal }),
      api.plans({ page: planPage, pageSize: planPageSize }, { signal: controller.signal }),
      api.usage({ page: usagePage, pageSize: usagePageSize }, { signal: controller.signal }),
      api.models({ signal: controller.signal }),
    ]).then(([context, plans, usage, models]) => {
      if (controller.signal.aborted) return;
      hasLoadedRef.current = true;
      setData({ context, plans, usage, models });
      setAnnouncement(`月度 Token 订阅已更新，数据时间 ${context.data.asOf}。`);
    }).catch((cause: unknown) => {
      if (controller.signal.aborted || isAbortError(cause)) return;
      const nextError = normalizeError(cause);
      setError(nextError);
      setAnnouncement(`订阅数据读取失败：${nextError.code}。`);
    }).finally(() => {
      if (controller.signal.aborted) return;
      setIsLoading(false);
      setIsRefreshing(false);
    });

    return () => controller.abort();
  }, [api, planPage, planPageSize, refreshVersion, usagePage, usagePageSize]);

  const refetch = useCallback(() => {
    setRefreshVersion((version) => version + 1);
  }, []);

  const setPlanPage = useCallback((page: number) => {
    setPlanPageState(Math.max(1, Math.trunc(page)));
  }, []);

  const setUsagePage = useCallback((page: number) => {
    setUsagePageState(Math.max(1, Math.trunc(page)));
  }, []);

  const previewCommand = useCallback(async (
    action: ProductAction,
    targetPlanVersionId: string | null = null,
  ) => {
    const currentVersion = data?.context.data.subscription?.version ?? null;
    const command = buildProductCommandPreview(action, targetPlanVersionId, currentVersion);
    if (action !== 'create' && currentVersion === null) {
      setCommandState((current) => ({
        ...current,
        error: new ProductApiError({
          code: 'SUBSCRIPTION_NOT_FOUND',
          status: 404,
          message: '当前没有可执行此操作的订阅。',
        }),
      }));
      return;
    }

    setCommandState({
      preview: null,
      result: null,
      targetPlanVersionId,
      isPreviewing: true,
      isExecuting: false,
      error: null,
    });
    try {
      const preview = await api.command(command);
      idempotencyKeyRef.current = newProductCommandIdempotencyKey();
      setCommandState({
        preview,
        result: null,
        targetPlanVersionId,
        isPreviewing: false,
        isExecuting: false,
        error: null,
      });
      setAnnouncement(`${action} 影响预览已就绪。`);
    } catch (cause) {
      const nextError = normalizeError(cause);
      setCommandState({
        preview: null,
        result: null,
        targetPlanVersionId,
        isPreviewing: false,
        isExecuting: false,
        error: nextError,
      });
      setAnnouncement(`操作预览失败：${nextError.code}。`);
    }
  }, [api, data]);

  const executeCommand = useCallback(async (reason: string) => {
    const preview = commandState.preview;
    if (preview === null) return;
    const idempotencyKey = idempotencyKeyRef.current ?? newProductCommandIdempotencyKey();
    idempotencyKeyRef.current = idempotencyKey;
    const command = buildProductCommandExecute(
      preview,
      commandState.targetPlanVersionId,
      reason,
    );
    const requestOptions: ProductCommandRequestOptions & { idempotencyKey: string } = {
      idempotencyKey,
    };
    setCommandState((current) => ({ ...current, isExecuting: true, error: null }));
    try {
      const result = await api.command(command, requestOptions);
      idempotencyKeyRef.current = null;
      setCommandState({
        preview: null,
        result,
        targetPlanVersionId: null,
        isPreviewing: false,
        isExecuting: false,
        error: null,
      });
      setAnnouncement(`订阅操作已${result.data.outcome === 'scheduled' ? '安排' : '应用'}。`);
      setRefreshVersion((version) => version + 1);
    } catch (cause) {
      const nextError = normalizeError(cause);
      setCommandState((current) => ({ ...current, isExecuting: false, error: nextError }));
      setAnnouncement(`订阅操作未确认：${nextError.code}。`);
      if (nextError.status === 409) setRefreshVersion((version) => version + 1);
    }
  }, [api, commandState.preview, commandState.targetPlanVersionId]);

  const closeCommand = useCallback(() => {
    idempotencyKeyRef.current = null;
    setCommandState((current) => ({
      ...current,
      preview: null,
      targetPlanVersionId: null,
      isPreviewing: false,
      isExecuting: false,
      error: null,
    }));
  }, []);

  const clearCommandResult = useCallback(() => {
    setCommandState((current) => ({ ...current, result: null }));
  }, []);

  return {
    data,
    isLoading,
    isRefreshing,
    error,
    announcement,
    planPage,
    usagePage,
    commandState,
    refetch,
    setPlanPage,
    setUsagePage,
    previewCommand,
    executeCommand,
    closeCommand,
    clearCommandResult,
  };
}

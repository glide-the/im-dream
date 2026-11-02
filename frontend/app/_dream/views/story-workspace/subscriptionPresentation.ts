// [Input] Existing Product API errors/statuses and display values.
// [Output] Original subscription tabs, labels, date/Token formatting and recovery copy.
// [Pos] Shared presentation only; pricing, allowance and eligibility remain server-owned.
import type {ProductApiError} from '../../api/productApi';
export const STATUS_LABELS: Record<string, string> = {
  trial: '试用中',
  active: '当前套餐',
  past_due: '需要处理',
  paused: '已暂停',
  cancel_at_period_end: '周期末结束',
  cancelled: '已取消',
  expired: '已过期',
  legacyUnavailable: '暂不可用',
};

export const TABS = [
  { id: 'info', label: '订阅信息' },
  { id: 'allowance', label: '我的额度' },
  { id: 'plans', label: '可选套餐' },
] as const;

export type SubscriptionTab = typeof TABS[number]['id'];

export function formatInteger(value: number): string {
  return new Intl.NumberFormat('zh-CN', { maximumFractionDigits: 0 }).format(value);
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return '日期暂不可用';
  const date = new Date(value);
  if (!Number.isFinite(date.getTime())) return '日期暂不可用';
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(date);
}

interface ProductErrorPresentation {
  title: string;
  description: string;
  recovery: string;
}

export function productErrorPresentation(error: ProductApiError): ProductErrorPresentation {
  switch (error.status) {
    case 401:
      return { title: '登录状态已失效', description: '暂时无法读取你的订阅。', recovery: '重新登录后再试。' };
    case 402:
      return { title: '本周期额度已用完', description: '当前 Token 不足。', recovery: '等待额度重置，或查看其他套餐。' };
    case 403:
      return { title: '暂时无法执行此操作', description: '当前订阅状态或权限不满足操作条件。', recovery: '刷新页面后查看可用选项。' };
    case 409:
      return { title: '订阅状态已更新', description: '页面中的状态已经不是最新。', recovery: '刷新后重新确认。' };
    case 429:
      return { title: '请求有些频繁', description: '订阅服务正在限制请求频率。', recovery: '稍后再试。' };
    case 502:
    case 503:
    default:
      return { title: '订阅服务暂时不可用', description: '现在无法安全读取真实订阅数据。', recovery: '稍后重试；页面不会显示替代数据。' };
  }
}


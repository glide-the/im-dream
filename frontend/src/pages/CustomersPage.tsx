import { useEffect, useMemo, useState } from 'react';
import Modal from '../components/chat/Modal';
import Toast from '../components/chat/Toast';
import { IconEdit, IconPlus, IconSearch, IconTrash } from '../components/chat/Icons';
import { useDebounce } from '../hooks/useDebounce';

type Customer = {
  id: string;
  name?: string;
  company?: string;
  title?: string;
  phones?: string[];
  emails?: string[];
  wechat?: string;
  tags?: string[];
  updated_at: string;
};

type CustomerResponse = {
  data?: Customer[];
  meta?: {
    page: number;
    pageSize: number;
    total: number;
    totalPages: number;
    tagOptions: string[];
    totalCustomers: number;
  };
};

const sortOptions = [
  { value: 'updated_at', label: '最近更新' },
  { value: 'created_at', label: '最近创建' },
  { value: 'name', label: '姓名 A-Z' },
];

const emptyForm = {
  name: '',
  company: '',
  title: '',
  phones: '',
  emails: '',
  wechat: '',
  tags: '',
  profile_markdown: '',
};

function formatRelativeTime(value: string) {
  const timestamp = Date.parse(value);
  if (Number.isNaN(timestamp)) return '未知';
  const diffMs = timestamp - Date.now();
  const diffDays = Math.round(diffMs / (1000 * 60 * 60 * 24));
  return new Intl.RelativeTimeFormat('zh-CN', { numeric: 'auto' }).format(diffDays, 'day');
}

function formatContactStatus(hasContact: boolean) {
  return hasContact ? '已配置联系方式' : '缺少联系方式';
}

export default function CustomersPage() {
  const [search, setSearch] = useState('');
  const [sort, setSort] = useState('updated_at');
  const [order, setOrder] = useState<'asc' | 'desc'>('desc');
  const [tag, setTag] = useState('all');
  const [hasContact, setHasContact] = useState(false);
  const [page, setPage] = useState(1);
  const [toast, setToast] = useState<string | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState({ ...emptyForm });
  const [data, setData] = useState<CustomerResponse>({});
  const [isLoading, setIsLoading] = useState(false);

  const debouncedSearch = useDebounce(search, 300);

  useEffect(() => {
    let active = true;
    setIsLoading(true);
    const params = new URLSearchParams({
      page: String(page),
      pageSize: '6',
      search: debouncedSearch,
      sort,
      order,
      tag,
      hasContact: hasContact ? '1' : '0',
    });
    void (async () => {
      try {
        const response = await fetch(`/api/customers?${params.toString()}`);
        if (!response.ok) {
          throw new Error(`加载客户失败 (${response.status})`);
        }
        const payload = (await response.json()) as CustomerResponse;
        if (active) {
          setData(payload);
        }
      } catch (error) {
        if (active) {
          setData({});
          setToast(error instanceof Error ? error.message : '加载客户失败');
        }
      } finally {
        if (active) {
          setIsLoading(false);
        }
      }
    })();
    return () => {
      active = false;
    };
  }, [debouncedSearch, hasContact, order, page, sort, tag]);

  const customers = data.data ?? [];
  const meta = data.meta ?? { page: 1, pageSize: 6, total: 0, totalPages: 1, tagOptions: [], totalCustomers: 0 };
  const hasResults = customers.length > 0;

  const payload = useMemo(() => ({
    name: form.name,
    company: form.company,
    title: form.title,
    phones: form.phones ? form.phones.split(/[,，]/).map((value) => value.trim()).filter(Boolean) : [],
    emails: form.emails ? form.emails.split(/[,，]/).map((value) => value.trim()).filter(Boolean) : [],
    wechat: form.wechat,
    tags: form.tags ? form.tags.split(/[,，]/).map((value) => value.trim()).filter(Boolean) : [],
    profile_markdown: form.profile_markdown,
    source: 'manual' as const,
  }), [form]);

  async function handleCreate() {
    if (!form.name && !form.company) {
      setToast('至少填写姓名或公司');
      return;
    }
    try {
      const response = await fetch('/api/customers', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!response.ok) {
        const body = (await response.json().catch(() => ({}))) as { error?: string };
        throw new Error(body.error || `新增失败 (${response.status})`);
      }
      setToast('客户已新增');
      setForm({ ...emptyForm });
      setModalOpen(false);
      setPage(1);
    } catch (error) {
      setToast(error instanceof Error ? error.message : '新增失败');
    }
  }

  async function handleDelete(id: string) {
    try {
      const response = await fetch(`/api/customers/${id}`, { method: 'DELETE' });
      if (!response.ok) {
        const body = (await response.json().catch(() => ({}))) as { error?: string };
        throw new Error(body.error || `删除失败 (${response.status})`);
      }
      setToast('客户已删除');
      setData((current) => ({ ...current, data: (current.data ?? []).filter((customer) => customer.id !== id) }));
    } catch (error) {
      setToast(error instanceof Error ? error.message : '删除失败');
    }
  }

  return (
    <div style={{ position: 'relative', overflow: 'hidden', borderRadius: '32px', background: 'var(--color-bg-app)', padding: '1.5rem', boxShadow: '0 1px 4px rgba(0,0,0,0.06)' }}>
      <div style={{ position: 'relative' }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: '0.75rem' }}>
          <div>
            <h1 style={{ margin: 0, fontSize: '1.5rem', color: 'var(--color-text-primary)' }}>客户</h1>
            <p style={{ margin: '0.2rem 0 0', fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>共 {meta.totalCustomers} 位客户</p>
          </div>
          <button type="button" onClick={() => setModalOpen(true)} style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem', border: 'none', borderRadius: '999px', background: 'var(--color-action-link)', padding: '0.65rem 1rem', color: '#fff', fontWeight: 600, cursor: 'pointer' }}>
            <IconPlus style={{ width: '1rem', height: '1rem' }} />新增客户
          </button>
        </div>

        <div style={{ marginTop: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem', borderRadius: '999px', border: '1px solid var(--color-border-paper)', background: 'var(--color-bg-paper)', padding: '0.75rem 1rem', color: 'var(--color-text-muted)' }}>
          <IconSearch style={{ width: '1rem', height: '1rem' }} />
          <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="搜索姓名 / 公司 / 联系方式" style={{ flex: 1, border: 'none', outline: 'none', background: 'transparent', color: 'var(--color-text-primary)' }} />
        </div>

        <div style={{ marginTop: '0.75rem', display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
          <select value={sort} onChange={(event) => setSort(event.target.value)} style={{ borderRadius: '999px', border: '1px solid var(--color-border-paper)', background: 'var(--color-bg-paper)', padding: '0.45rem 0.75rem', color: 'var(--color-text-secondary)' }}>
            {sortOptions.map((option) => <option key={option.value} value={option.value}>排序：{option.label}</option>)}
          </select>
          <button type="button" onClick={() => setHasContact((value) => !value)} style={{ borderRadius: '999px', border: '1px solid var(--color-border-paper)', background: hasContact ? 'rgba(74,144,226,0.12)' : 'var(--color-bg-paper)', padding: '0.45rem 0.75rem', color: hasContact ? 'var(--color-action-link)' : 'var(--color-text-secondary)', cursor: 'pointer' }}>过滤：有联系方式</button>
          <select value={tag} onChange={(event) => setTag(event.target.value)} style={{ borderRadius: '999px', border: '1px solid var(--color-border-paper)', background: 'var(--color-bg-paper)', padding: '0.45rem 0.75rem', color: 'var(--color-text-secondary)' }}>
            <option value="all">全部标签</option>
            {meta.tagOptions.map((option) => <option key={option} value={option}>{option}</option>)}
          </select>
          <button type="button" onClick={() => setOrder((value) => value === 'asc' ? 'desc' : 'asc')} style={{ borderRadius: '999px', border: '1px solid var(--color-border-paper)', background: 'var(--color-bg-paper)', padding: '0.45rem 0.75rem', color: 'var(--color-text-secondary)', cursor: 'pointer' }}>{order === 'asc' ? '升序' : '降序'}</button>
        </div>

        <div style={{ marginTop: '1.5rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {isLoading ? [1, 2, 3].map((item) => <div key={item} style={{ height: '5rem', borderRadius: '18px', background: 'var(--color-bg-paper)' }} />) : null}
          {!isLoading && hasResults ? customers.map((customer) => {
            const hasContactInfo = Boolean((customer.phones && customer.phones.length > 0) || (customer.emails && customer.emails.length > 0) || customer.wechat);
            return (
              <div key={customer.id} style={{ borderRadius: '18px', border: '1px solid var(--color-border-paper)', background: 'var(--color-bg-paper)', padding: '1rem', boxShadow: '0 1px 4px rgba(0,0,0,0.06)' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.75rem' }}>
                  <div>
                    <p style={{ margin: 0, fontSize: '1rem', fontWeight: 600, color: 'var(--color-text-primary)' }}>{customer.name || '未命名客户'}</p>
                    <p style={{ margin: '0.25rem 0 0', fontSize: '0.875rem', color: 'var(--color-text-secondary)' }}>{customer.company || '-'} · {customer.title || '-'}</p>
                  </div>
                  <span style={{ borderRadius: '999px', background: 'rgba(74,144,226,0.12)', padding: '0.2rem 0.55rem', fontSize: '0.7rem', fontWeight: 600, color: 'var(--color-action-link)' }}>{(customer.tags ?? ['普通'])[0]}</span>
                </div>
                <div style={{ marginTop: '0.75rem', display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: '0.5rem', fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>
                  <span>最近更新：{formatRelativeTime(customer.updated_at)}</span>
                  <span style={{ borderRadius: '999px', background: 'var(--color-bg-surface)', padding: '0.2rem 0.55rem', color: 'var(--color-text-secondary)' }}>{formatContactStatus(hasContactInfo)}</span>
                </div>
                <div style={{ marginTop: '0.75rem', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <a href={`/customers/${customer.id}`} style={{ color: 'var(--color-action-link)', fontSize: '0.8rem', fontWeight: 600, textDecoration: 'none' }}>查看详情</a>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <a href={`/customers/${customer.id}`} style={{ display: 'grid', placeItems: 'center', width: '2rem', height: '2rem', borderRadius: '999px', border: '1px solid var(--color-border-paper)', background: 'var(--color-bg-surface)', color: 'var(--color-text-secondary)' }}><IconEdit style={{ width: '0.95rem', height: '0.95rem' }} /></a>
                    <button type="button" onClick={() => void handleDelete(customer.id)} style={{ display: 'grid', placeItems: 'center', width: '2rem', height: '2rem', borderRadius: '999px', border: '1px solid var(--color-border-paper)', background: 'var(--color-bg-surface)', color: '#d9534f', cursor: 'pointer' }}><IconTrash style={{ width: '0.95rem', height: '0.95rem' }} /></button>
                  </div>
                </div>
              </div>
            );
          }) : null}
          {!isLoading && !hasResults ? <div style={{ padding: '1.5rem', borderRadius: '18px', background: 'var(--color-bg-paper)', color: 'var(--color-text-muted)' }}>暂无客户。</div> : null}
        </div>

        {meta.totalPages > 1 ? (
          <div style={{ marginTop: '1rem', display: 'flex', justifyContent: 'flex-end', gap: '0.5rem' }}>
            <button type="button" onClick={() => setPage((value) => Math.max(1, value - 1))} disabled={page <= 1} style={{ borderRadius: '999px', border: '1px solid var(--color-border-paper)', background: 'var(--color-bg-paper)', padding: '0.5rem 0.8rem', cursor: page <= 1 ? 'not-allowed' : 'pointer' }}>上一页</button>
            <button type="button" onClick={() => setPage((value) => Math.min(meta.totalPages, value + 1))} disabled={page >= meta.totalPages} style={{ borderRadius: '999px', border: '1px solid var(--color-border-paper)', background: 'var(--color-bg-paper)', padding: '0.5rem 0.8rem', cursor: page >= meta.totalPages ? 'not-allowed' : 'pointer' }}>下一页</button>
          </div>
        ) : null}
      </div>

      <Modal open={modalOpen} title="新增客户" onClose={() => setModalOpen(false)}>
        <div style={{ display: 'grid', gap: '0.75rem' }}>
          {Object.entries({ 姓名: 'name', 公司: 'company', 职位: 'title', 电话: 'phones', 邮箱: 'emails', 微信: 'wechat', 标签: 'tags' } as const).map(([label, key]) => (
            <label key={key} style={{ display: 'grid', gap: '0.35rem', fontSize: '0.85rem', color: 'var(--color-text-primary)' }}>
              <span>{label}</span>
              <input value={form[key]} onChange={(event) => setForm((current) => ({ ...current, [key]: event.target.value }))} style={{ padding: '0.7rem 0.8rem', borderRadius: '10px', border: '1px solid var(--color-border-paper)', background: 'var(--color-bg-paper)', color: 'var(--color-text-primary)' }} />
            </label>
          ))}
          <label style={{ display: 'grid', gap: '0.35rem', fontSize: '0.85rem', color: 'var(--color-text-primary)' }}>
            <span>简介</span>
            <textarea value={form.profile_markdown} onChange={(event) => setForm((current) => ({ ...current, profile_markdown: event.target.value }))} rows={4} style={{ padding: '0.7rem 0.8rem', borderRadius: '10px', border: '1px solid var(--color-border-paper)', background: 'var(--color-bg-paper)', color: 'var(--color-text-primary)' }} />
          </label>
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem' }}>
            <button type="button" onClick={() => setModalOpen(false)} style={{ borderRadius: '999px', border: '1px solid var(--color-border-paper)', background: 'var(--color-bg-paper)', padding: '0.6rem 0.9rem', cursor: 'pointer' }}>取消</button>
            <button type="button" onClick={() => void handleCreate()} style={{ border: 'none', borderRadius: '999px', background: 'var(--color-action-link)', padding: '0.6rem 0.9rem', color: '#fff', fontWeight: 600, cursor: 'pointer' }}>保存</button>
          </div>
        </div>
      </Modal>

      {toast ? <Toast message={toast} onClose={() => setToast(null)} /> : null}
    </div>
  );
}

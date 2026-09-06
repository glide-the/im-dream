import type { ChangeEvent } from 'react';

export function formatStoryWorkspaceDate(value: string | null | undefined): string {
  if (!value) return '—';
  const date = new Date(value.includes('T') ? value : value.replace(' ', 'T') + 'Z');
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat('zh-CN', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date);
}

export function togglePendingSelection(
  selectedIds: string[],
  id: string,
  checked: boolean,
): string[] {
  if (checked) return selectedIds.includes(id) ? selectedIds : [...selectedIds, id];
  return selectedIds.filter((selectedId) => selectedId !== id);
}

export function pendingSelectionHandler(
  pendingIds: string[],
  selectedIds: string[],
  onSelectionChange: (ids: string[]) => void,
) {
  return (event: ChangeEvent<HTMLInputElement>) => {
    if (event.target.checked) {
      onSelectionChange(Array.from(new Set([...selectedIds, ...pendingIds])));
      return;
    }
    onSelectionChange(selectedIds.filter((id) => !pendingIds.includes(id)));
  };
}

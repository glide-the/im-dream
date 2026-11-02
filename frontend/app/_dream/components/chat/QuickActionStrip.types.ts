// [Input] Existing ChatView quick-action labels, prompts and icon identities.
// [Output] Shared Web/native callback contract without DOM dependencies.
// [Pos] Original QuickActionStrip public props; platform views retain the same actions.
export type QuickActionStripIcon = 'image' | 'edit' | 'search';
export interface QuickActionStripItem {
  id: string;
  label: string;
  prompt: string;
  icon: QuickActionStripIcon;
  description?: string;
}
export interface QuickActionStripProps {
  items: QuickActionStripItem[];
  onSelect: (item: QuickActionStripItem) => void;
  className?: string;
}

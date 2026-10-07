// [Input] Caller-owned class name and existing Notion lettermark styling.
// [Output] Shared decorative Notion lettermark for Settings and Calendar.
// [Pos] Shared provider glyph in frontend/app/_dream/components.
// [Sync] 2026-10-05: extract the existing Settings mark without duplicating its drawing.
export default function NotionMark({ className = 'notion-detail__mark' }: { className?: string }) {
  return <span aria-hidden="true" className={className}><span>N</span></span>;
}

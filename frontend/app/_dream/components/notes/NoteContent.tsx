// [Input] Text-only note snapshot, display brand and an optional fixed export width.
// [Output] Read-only prose shared by public reading and PNG capture, with escaped text.
// [Pos] Server-compatible note presentation; no authentication, editor or model imports.
import type {NoteSnapshot} from './noteShare';
import {BRAND_NAME} from '../../constants/brand';
export default function NoteContent({note, exporting = false}: {note: NoteSnapshot; exporting?: boolean}) {
  return <article aria-label={note.title} style={{boxSizing: 'border-box', width: exporting ? 720 : '100%', maxWidth: 720, margin: '0 auto', padding: exporting ? '48px' : 'clamp(20px, 5vw, 48px)', background: 'var(--color-bg-paper, #F6EFE5)', color: 'var(--color-text-primary, #302b27)', fontFamily: "'Excalifont', 'Xiaolai', Georgia, serif", fontSize: 18, lineHeight: 1.8, overflowWrap: 'anywhere'}}>
    <header style={{marginBottom: 28, borderBottom: '1px dashed var(--color-border-paper, #d7cbbb)', paddingBottom: 18}}>
      <div style={{fontSize: 14, opacity: 0.7}}>{BRAND_NAME}</div>
      <h1 style={{fontSize: 26, lineHeight: 1.4, margin: '8px 0', whiteSpace: 'pre-wrap'}}>{note.title}</h1>
      {note.created_at ? <time dateTime={note.created_at} style={{fontSize: 14, opacity: 0.7}}>{note.created_at.slice(0, 10)}</time> : null}
    </header>
    {note.paragraphs.map((text, index) => <p key={index} style={{whiteSpace: 'pre-wrap', margin: '0 0 18px', minHeight: text ? undefined : '1.8em'}}>{text}</p>)}
    <footer style={{marginTop: 28, fontSize: 12, opacity: 0.65}}>{BRAND_NAME}</footer>
  </article>;
}

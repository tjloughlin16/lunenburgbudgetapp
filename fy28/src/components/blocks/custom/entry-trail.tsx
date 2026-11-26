/** THE 29 JUNE ENTRY, DATED (FY2026 school surplus).
 *
 *  One row an event, from the reclassification form to the Finance Committee in October: when,
 *  who, what the record shows, the record's own words where it has them, and a link to each
 *  record. A quotation is drawn as a quotation, so the school office's words and the Town
 *  Manager's are never mistaken for ours. Every string is formatted and every quotation checked
 *  against our transcription by scripts/build_fy2026_school_surplus.py; this prints the text. */
import type { CustomProps } from './index'

type Link = { label: string; href: string }
type Row = { when: string; who: string; what: string; quote?: string; links: Link[] }
type Data = { rows: Row[] }

export default function EntryTrail({ data, alt }: CustomProps) {
  const d = data as Data
  return (
    <ol aria-label={alt} className="max-w-3xl border-l-2 ml-1.5" style={{ borderColor: 'var(--grid)' }}>
      {d.rows.map((r, i) => (
        <li key={i} className="relative pl-5 pb-4 last:pb-0">
          <span className="absolute -left-[7px] top-1.5 h-3 w-3 rounded-full"
            style={{ background: 'var(--bg)', border: '2px solid var(--text-secondary)' }} aria-hidden="true" />
          <p className="text-[13px]">
            <span className="font-semibold" style={{ color: 'var(--text-primary)' }}>{r.when}</span>
            <span style={{ color: 'var(--text-muted)' }}> · {r.who}</span>
          </p>
          <p className="text-[14px] leading-relaxed mt-0.5" style={{ color: 'var(--text-primary)' }}>{r.what}</p>
          {r.quote ? (
            <blockquote className="text-[14px] leading-relaxed mt-1 pl-3 border-l-2 italic"
              style={{ borderColor: 'var(--thread-1)', color: 'var(--text-secondary)' }}>“{r.quote}”</blockquote>
          ) : null}
          {r.links.length ? (
            <p className="mt-1 text-[12.5px] flex flex-wrap gap-x-3 gap-y-1">
              {r.links.map((l, j) => (
                <a key={j} href={l.href} className="underline" style={{ color: 'var(--text-secondary)' }}>{l.label}</a>
              ))}
            </p>
          ) : null}
        </li>
      ))}
    </ol>
  )
}

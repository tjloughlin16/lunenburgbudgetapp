/** WHERE A DECISION WOULD BE ON THE RECORD, meeting by meeting (Year-end tuition payment).
 *
 *  TJ, 26 October 2026: "put the meeting recordings and minutes if available for the meetings
 *  that WOULD be where we expect the warrants to show up for the early prepay." One row a
 *  meeting: what the agenda put before the board, what the record shows, and a link to each
 *  record that exists. A record that was never posted is said to be missing, in words, so an
 *  absent link cannot be mistaken for one we forgot. Everything is formatted by
 *  build_journal_surplus_topics.py; this prints the given text. */
import type { CustomProps } from './index'

type Link = { label: string; href: string; caption?: boolean }
type Row = { when: string; board: string; expected: string; shows: string; links: Link[]; missing: string[] }
type Data = { rows: Row[] }

export default function MeetingTrail({ data, alt }: CustomProps) {
  const d = data as Data
  return (
    <ol aria-label={alt} className="max-w-3xl space-y-2.5">
      {d.rows.map((r, i) => (
        <li key={i} className="border rounded-md p-3 grid gap-2 sm:grid-cols-[120px_1fr]"
          style={{ borderColor: 'var(--grid)' }}>
          <div className="text-[13px]">
            <p className="font-semibold" style={{ color: 'var(--text-primary)' }}>{r.when}</p>
            <p style={{ color: 'var(--text-secondary)' }}>{r.board}</p>
          </div>
          <div className="min-w-0 text-[14px] leading-relaxed">
            <p style={{ color: 'var(--text-secondary)' }}>
              <span className="text-[11.5px] uppercase tracking-wide" style={{ color: 'var(--text-muted)' }}>On the agenda </span>
              {r.expected}</p>
            <p className="mt-1" style={{ color: 'var(--text-primary)' }}>{r.shows}</p>
            <p className="mt-1.5 text-[13px] flex flex-wrap gap-x-3 gap-y-1">
              {r.links.map((l, j) => (
                <a key={j} href={l.href} className="underline" style={{ color: 'var(--text-secondary)' }}>
                  {l.label}</a>
              ))}
              {r.missing.map((m, j) => (
                <span key={'m' + j} style={{ color: 'var(--status-warning)' }}>{m}</span>
              ))}
            </p>
          </div>
        </li>
      ))}
    </ol>
  )
}

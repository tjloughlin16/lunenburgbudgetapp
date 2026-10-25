/** WHAT WAS SAID, BESIDE THAT YEAR'S LEDGER (the SERF hub).
 *
 *  TJ, 25 October 2026: "the school committee will disagree with this ... can you find quotes
 *  that say the surprises from special education crush the budget and put them on this page."
 *  Each quotation sits beside what the town's ledger shows for the fiscal year it was said in,
 *  so a reader sees both at once. Neither is marked right: a line can run over while the three
 *  together come in under, and the meeting is usually describing the line. Everything is
 *  formatted by build_serf_topics.py; this prints the given text. */
import type { CustomProps } from './index'

type Line = { label: string; value: string; tone?: 'bad' | 'good' | null }
type Item = {
  quote: string; who: string; when: string; board: string; href: string; label: string
  caption?: boolean; fy: string; ledger: Line[]; open?: string
}
type Data = { items: Item[]; ledger_head: string }

const TONE = { bad: 'var(--status-bad)', good: 'var(--status-good)' }

export default function SerfSaidLedger({ data, alt }: CustomProps) {
  const d = data as Data
  return (
    <div aria-label={alt} className="max-w-3xl space-y-3">
      {d.items.map((q, i) => (
        <figure key={i} className="grid gap-3 sm:grid-cols-[1fr_260px] border rounded-md p-3"
          style={{ borderColor: 'var(--grid)' }}>
          <div className="min-w-0">
            <blockquote className="text-[15px] leading-relaxed pl-3 border-l-2"
              style={{ color: 'var(--text-primary)', borderColor: q.caption ? 'var(--axis)' : 'var(--grid)' }}>
              “{q.quote}”</blockquote>
            <figcaption className="text-[13px] mt-1.5" style={{ color: 'var(--text-secondary)' }}>
              — {q.who}, {q.board}, <span className="font-semibold">{q.when}</span>
              <br />
              <a href={q.href} className="underline text-[12.5px]" style={{ color: 'var(--text-secondary)' }}>{q.label}</a>
              {q.caption ? <span className="text-[12.5px]" style={{ color: 'var(--text-muted)' }}> — machine captions, a finding aid</span> : null}
            </figcaption>
          </div>
          <div className="text-[13px] sm:border-l sm:pl-3 pt-2 sm:pt-0 border-t sm:border-t-0"
            style={{ borderColor: 'var(--grid)' }}>
            <p className="text-[11.5px] uppercase tracking-wide" style={{ color: 'var(--text-muted)' }}>
              {d.ledger_head} {q.fy}</p>
            {q.open ? (
              <p className="mt-1" style={{ color: 'var(--text-secondary)' }}>{q.open}</p>
            ) : (
              <ul className="mt-1 space-y-0.5">
                {q.ledger.map((l, j) => (
                  <li key={j} className="flex justify-between gap-3 items-baseline">
                    <span className="min-w-0" style={{ color: 'var(--text-secondary)' }}>{l.label}</span>
                    <span className="tabular-nums shrink-0" style={{ color: l.tone ? TONE[l.tone] : 'var(--text-primary)' }}>{l.value}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </figure>
      ))}
    </div>
  )
}

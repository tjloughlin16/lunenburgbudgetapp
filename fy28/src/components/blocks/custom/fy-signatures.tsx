/** BEGINNING AND END (fy-breakdown): the picked year as residents heard it, at both ends.
 *  TJ, 29 October 2026: "the surplus for the year. So it gets announced ... right at the top of
 *  the page as sort of like executive summary call out ... but there's also a beginning".
 *
 *  The start: the gap, the cuts and the override ANNOUNCED. The end: the surplus ANNOUNCED, each
 *  figure the speaker's and cited as theirs, beside the page's own Left -- never added to it, never
 *  reconciled to it (rule 7). Where nothing was found, the block says what was searched (rule 13c).
 *  Every string is formatted by scripts/build_fy_breakdown.py (signatures_data). */
import { useMemo } from 'react'
import type { CustomProps } from './index'
import { useFyYear } from './fy-year'

type Cite = { href: string; label: string; ref?: string; captions?: boolean }
type Start = { id: string; label: string; v: string; sub: string; none?: boolean; quote?: string; then?: string[]; cite?: Cite }
type Said = { v: string | null; who: string; on: string; quote: string; note?: string | null; later?: boolean; captions?: boolean; cite: Cite }
type Year = { fy: string; start: Start[]; said: Said[]; searched: { start: string[]; end: string[] }; ours: string }
type Data = { years: Year[]; text: Record<string, string> }

const muted = { color: 'var(--text-muted)' }, secondary = { color: 'var(--text-secondary)' }
const line = { borderColor: 'var(--grid)' }

function Source({ c, t }: { c: Cite; t: Data['text'] }) {
  return (
    <p className="text-[12px] leading-snug mt-1" style={muted}>
      <a href={c.href} className="underline underline-offset-2" target={c.href.startsWith('http') ? '_blank' : undefined}
        rel="noreferrer">{c.label}</a>{c.ref ? `, ${c.ref}` : ''}
      {c.captions ? <span className="ml-1 uppercase tracking-wide text-[10.5px]">· {t.captions}</span> : null}
    </p>)
}

function More({ summary, children }: { summary: string; children: React.ReactNode }) {
  return (
    <details className="mt-1.5 text-[13px] leading-snug" style={secondary}>
      <summary className="cursor-pointer select-none text-[12px]" style={muted}>{summary}</summary>
      <div className="mt-1 space-y-1">{children}</div>
    </details>)
}

export default function FySignatures({ data, alt }: CustomProps) {
  const d = data as Data
  const t = d.text
  const fys = useMemo(() => d.years.map(v => v.fy), [d])
  const [fy] = useFyYear(fys)
  const y = d.years[Math.max(0, fys.indexOf(fy))]
  const announced = y.said.filter(s => s.v)
  const remarks = y.said.filter(s => !s.v)
  const head = 'text-[11px] uppercase tracking-wide font-semibold mb-2'
  return (
    <div aria-label={alt} aria-live="polite" className="max-w-3xl grid gap-3 sm:grid-cols-2">
      {/* THE START: three facts, each a figure and one line */}
      <section className="border rounded-md p-3 min-w-0" style={line}>
        <h3 className={head} style={muted}>{t.start} · {y.fy}</h3>
        <dl className="space-y-3">
          {y.start.map(s => (
            <div key={s.id}>
              <dt className="text-[12.5px]" style={secondary}>{s.label}</dt>
              <dd>
                <p className="text-[19px] font-bold tabular-nums leading-tight" style={s.none ? muted : undefined}>{s.v}</p>
                <p className="text-[13px] leading-snug" style={secondary}>{s.sub}</p>
                {s.cite ? <Source c={s.cite} t={t} /> : null}
                {s.quote || s.then?.length ? (
                  <More summary={t.source}>
                    {s.quote ? <p>“{s.quote}”</p> : null}
                    {s.then?.map((x, i) => <p key={i}>{x}</p>)}
                  </More>) : null}
              </dd>
            </div>))}
        </dl>
        {y.searched.start.length ? <More summary={t.searched}>{y.searched.start.map((x, i) => <p key={i}>{x}</p>)}</More> : null}
      </section>

      {/* THE END: what was announced, then ours, apart */}
      <section className="border rounded-md p-3 min-w-0" style={line}>
        <h3 className={head} style={muted}>{t.end} · {y.fy}</h3>
        <p className="text-[12.5px]" style={secondary}>{t.said}</p>
        {announced.length ? announced.map((s, i) => (
          <div key={i} className={i ? 'mt-2.5' : ''}>
            <p className="text-[19px] font-bold tabular-nums leading-tight">{s.v}
              {s.later ? <span className="ml-1.5 text-[11px] font-normal uppercase tracking-wide" style={muted}>{t.later}</span> : null}</p>
            <p className="text-[13px] leading-snug" style={secondary}>{s.who}, {s.on}</p>
            <Source c={s.cite} t={t} />
            <More summary={t.source}>
              <p>“{s.quote}”</p>
              {s.note ? <p>{s.note}</p> : null}
            </More>
          </div>)) : <p className="text-[15px] font-semibold" style={muted}>{t.none_said}</p>}
        {remarks.map((s, i) => (
          <div key={i} className="mt-2 text-[13px] leading-snug" style={secondary}>
            <p>“{s.quote}” — {s.who}, {s.on}</p>
            {s.note ? <p style={muted}>{s.note}</p> : null}
            <Source c={s.cite} t={t} />
          </div>))}
        {y.searched.end.length ? <More summary={t.searched}>{y.searched.end.map((x, i) => <p key={i}>{x}</p>)}</More> : null}
        <div className="mt-3 pt-2.5 border-t" style={line}>
          <p className="text-[12.5px]" style={secondary}>{t.ours}</p>
          <p className="text-[19px] font-bold tabular-nums leading-tight">{y.ours}</p>
          <p className="text-[12px] leading-snug" style={muted}>{t.ours_sub}</p>
          <p className="text-[12px] leading-snug mt-1" style={muted}>{t.apart}</p>
        </div>
      </section>
    </div>)
}

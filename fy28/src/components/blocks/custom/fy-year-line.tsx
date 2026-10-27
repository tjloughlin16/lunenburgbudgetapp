/** ACROSS THE YEAR LINE (fy-breakdown). TJ, 27 October 2026: "watching the money cross
 *  boundaries is really what we're trying to represent here. This is a money relationship page
 *  more than anything."
 *
 *  The page's year as a band between two lines, 1 July and 30 June. On the left what came in
 *  across the first -- last year's orders and the budget carried with them, and bills paid ahead;
 *  on the right what went out across the second -- orders still owed, next year's bills paid
 *  early, what was left, and entries posted after the year ended. Dollar crossings share one
 *  scale, so the sizes compare. Every figure is formatted by scripts/build_fy_breakdown.py
 *  (year_line_data), which ties each crossing to the year on its other side. */
import { useMemo } from 'react'
import { useFyYear } from './fy-year'
import type { CustomProps } from './index'

type Part = { id: string; label: string; v: string; n: number }
type Cross = { id: string; label: string; v: string | null; n: number; parts: Part[]; means: string
  items: { what: string; v: string }[]; items_h: string }
type Year = { fy: string; prev: string; next: string; span: string; inn: Cross[]; out: Cross[] }
type Data = { years: Year[]; text: Record<string, string> }

const muted = { color: 'var(--text-muted)' }, secondary = { color: 'var(--text-secondary)' }
const hatch = (c: string) => `repeating-linear-gradient(135deg, ${c} 0 3px, transparent 3px 6px)`
const FILL: Record<string, string> = {
  carried: 'var(--thread-2)', paid: 'var(--thread-2)', never: hatch('var(--thread-2)'),
  ahead: 'var(--thread-4)', owed: 'var(--thread-2)', early: 'var(--thread-4)', left: 'var(--thread-1)',
}

function Card({ c, max, side }: { c: Cross; max: number; side: 'in' | 'out' }) {
  const segs = c.parts.length ? c.parts : [{ id: c.id, label: c.label, v: c.v ?? '', n: c.n }]
  return (
    <div className="rounded-md px-3 py-2" style={{ border: '1px solid var(--grid)' }}>
      <div className="flex items-baseline justify-between gap-3">
        <p className="text-[13px] font-semibold leading-tight">{c.label}</p>
        <p className="text-[14px] font-semibold tabular-nums whitespace-nowrap" style={c.v ? undefined : muted}>{c.v ?? '—'}</p>
      </div>
      {c.n > 0.5 ? (
        <div className={`flex h-2.5 mt-1.5 ${side === 'in' ? 'justify-end' : ''}`}>
          {segs.filter(p => p.n > 0.5).map(p => (
            <div key={p.id} title={`${p.label}: ${p.v}`}
              style={{ width: `max(2px, ${(p.n / max) * 100}%)`, background: FILL[p.id] ?? 'var(--text-muted)' }} />))}
        </div>) : null}
      {c.parts.length ? (
        <p className="text-[12px] mt-1" style={secondary}>
          {c.parts.map(p => <span key={p.id} className="inline-flex items-center gap-1 mr-3">
            <span className="inline-block w-2 h-2" style={{ background: FILL[p.id] }} />{p.label} <span className="tabular-nums">{p.v}</span></span>)}
        </p>) : null}
      <p className="text-[12px] leading-snug mt-1" style={muted}>{c.means}</p>
      {c.items.length ? (
        <details className="mt-1 text-[12.5px]">
          <summary className="cursor-pointer" style={secondary}>{c.items_h || c.label} ({c.items.length})</summary>
          <ul className="mt-1 space-y-0.5">
            {c.items.map((it, i) => (
              <li key={i} className="flex gap-3"><span className="tabular-nums w-20 shrink-0 text-right">{it.v}</span>
                <span className="min-w-0">{it.what}</span></li>))}
          </ul>
        </details>) : null}
    </div>)
}

export default function FyYearLine({ data, alt }: CustomProps) {
  const d = data as Data
  const t = d.text
  const fys = useMemo(() => d.years.map(v => v.fy), [d])
  const [fy] = useFyYear(fys)
  const y = d.years[Math.max(0, fys.indexOf(fy))]
  // one scale for every dollar crossing in the year, in and out, so the sizes compare
  const max = Math.max(1, ...[...y.inn, ...y.out].map(c => c.n))
  return (
    <figure aria-label={alt}>
      <div className="grid gap-3 md:grid-cols-[1fr_auto_1fr] md:items-stretch">
        <div className="space-y-2">
          <p className="text-[12px] font-semibold uppercase tracking-wide" style={muted}>{t.from_} {y.prev} → {t.h_in}</p>
          {y.inn.map(c => <Card key={c.id} c={c} max={max} side="in" />)}
        </div>
        {/* the year itself, between its two lines */}
        <div className="flex md:flex-col items-center justify-center gap-2 px-3 py-2 md:py-0 rounded-md"
          style={{ borderLeft: '2px solid var(--text-secondary)', borderRight: '2px solid var(--text-secondary)', background: 'var(--surface-2, transparent)' }}>
          <span className="text-[18px] font-semibold">{y.fy}</span>
          <span className="text-[11.5px] text-center md:max-w-[7rem]" style={muted}>{y.span}</span>
        </div>
        <div className="space-y-2">
          <p className="text-[12px] font-semibold uppercase tracking-wide" style={muted}>{t.h_out} → {t.to} {y.next}</p>
          {y.out.map(c => <Card key={c.id} c={c} max={max} side="out" />)}
        </div>
      </div>
    </figure>)
}

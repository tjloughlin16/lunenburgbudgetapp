/** EVERY LINE, EVERY YEAR (budget-against-actual, the signature). One column per fiscal year;
 *  each dot is one school line, placed by what it SPENT against what it was VOTED (a ratio, on a
 *  log scale so half and double sit equally far from the vote), its area by the size of its vote.
 *  A bar across each column is every dot added together. The total sits on the vote while the
 *  dots spread far above and below it: the whole finding of the August report, as one picture.
 *
 *  Years from the district's budget documents and years from the accounting system are shaded
 *  apart and never joined. FY2021's documents print the budget in the actual column, so that year
 *  comes from the Finance Committee workbook (src 'workbook'), labelled as such, with the reason.
 *  Every percentage carries its direction in words -- over budget, under budget -- because a bare
 *  +300% does not say which way it is read (TJ, 30 October 2026).
 *  The flags, line by line and year by year, are the grid below it (bva-grid). Every string and
 *  figure is the payload's (scripts/build_budget_against_actual.py, across()). */
import { useMemo, useState } from 'react'
import type { CustomProps } from './index'

type Dot = { name: string; b: number; a: number; s: 0 | 1 | 2; bt: string; at: string; pt: string }
type Src = 'books' | 'ledger' | 'workbook'
type Year = { fy: string; src: Src; lines: Dot[]; total: string; tr: number | null }
type Data = { years: Year[]; ticks: { r: number; t: string; sub: string }[]; lo: number; hi: number; text: Record<string, string> }

const muted = { color: 'var(--text-muted)' }
const COLOUR = ['var(--thread-2)', 'var(--thread-1)', 'var(--text-muted)']   // everything else, salaries, not in the workbook
const W = 960, H = 396, TOP = 34, BOT = 36, LEFT = 112, RIGHT = 8

/** A deterministic spread inside a column: lines sorted by ratio, x by a low-discrepancy step. */
const spread = (i: number) => ((i * 0.6180339887) % 1)

export default function BvaAcross({ data, alt }: CustomProps) {
  const d = data as Data
  const t = d.text
  const [hover, setHover] = useState<{ y: Year; l: Dot } | null>(null)
  const col = (W - LEFT - RIGHT) / d.years.length
  const ly = (r: number) => {
    const c = Math.min(Math.max(r, d.lo), d.hi)
    const f = (Math.log2(c) - Math.log2(d.lo)) / (Math.log2(d.hi) - Math.log2(d.lo))
    return TOP + (1 - f) * (H - TOP - BOT)
  }
  const maxB = useMemo(() => Math.max(1, ...d.years.flatMap(y => y.lines.map(l => l.b))), [d])
  const rad = (b: number) => 1.6 + 7 * Math.sqrt(b / maxB)
  /** Contiguous runs of one record: each is labelled once, and every run but the journal's shaded. */
  const runs = d.years.reduce<{ src: Src; a: number; b: number }[]>((rs, y, i) => {
    const r = rs[rs.length - 1]
    if (r && r.src === y.src) r.b = i
    else rs.push({ src: y.src, a: i, b: i })
    return rs
  }, [])
  const shadeOf: Record<Src, number> = { books: 0.55, workbook: 0.9, ledger: 0 }
  return (
    <figure aria-label={alt}>
      <div className="flex flex-wrap gap-x-4 gap-y-1 text-[12.5px] mb-2">
        {[t.sal, t.oth, t.unk].map((k, i) => (
          <span key={k} className="inline-flex items-center gap-1.5">
            <span className="inline-block w-2.5 h-2.5 rounded-full" style={{ background: COLOUR[i === 0 ? 1 : i === 1 ? 0 : 2], opacity: 0.75 }} />{k}</span>))}
        <span className="inline-flex items-center gap-1.5">
          <span className="inline-block w-4 h-[3px]" style={{ background: 'var(--text-primary)' }} />{t.total}</span>
      </div>
      <div className="overflow-x-auto">
        <svg viewBox={`0 0 ${W} ${H}`} className="w-full min-w-[640px] h-auto select-none" role="img" aria-label={alt}>
          {runs.map((r, i) => (
            <g key={r.a}>
              {shadeOf[r.src] ? <rect x={LEFT + r.a * col} y={TOP - 30} width={(r.b - r.a + 1) * col} height={H - TOP + 30 - BOT}
                fill="var(--surface-3)" opacity={shadeOf[r.src]} /> : null}
              {/* a record's name once, over its first run: FY2022 resumes the documents unlabelled */}
              {runs.findIndex(x => x.src === r.src) === i ? (
                <text x={LEFT + r.a * col + 6} y={TOP - 18} fontSize={12} fontWeight={600} fill="var(--text-secondary)">
                  {r.src === 'workbook' ? `${t.workbook}*` : t[r.src]}</text>) : null}
            </g>))}
          {d.ticks.map(k => (
            <g key={k.r}>
              <line x1={LEFT} x2={W - RIGHT} y1={ly(k.r)} y2={ly(k.r)} stroke="var(--grid)" strokeWidth={k.r === 1 ? 1.5 : 1}
                strokeDasharray={k.r === 1 ? undefined : '3 4'} />
              <text x={LEFT - 6} y={ly(k.r) + (k.sub ? -1 : 4)} fontSize={11} textAnchor="end" fill="var(--text-muted)">{k.t}</text>
              {k.sub ? <text x={LEFT - 6} y={ly(k.r) + 11} fontSize={10} textAnchor="end" fill="var(--text-muted)">{k.sub}</text> : null}
            </g>))}
          {d.years.map((y, i) => {
            const x0 = LEFT + i * col
            return (
              <g key={y.fy}>
                <text x={x0 + col / 2} y={TOP - 4} fontSize={12} textAnchor="middle" fontWeight={600} fill="var(--text-primary)">{y.fy}</text>
                {y.lines.map((l, j) => {
                  const r = l.a / l.b
                  const cx = x0 + 10 + spread(j) * (col - 20)
                  const on = hover?.l === l
                  return (
                    <circle key={j} cx={cx} cy={ly(r)} r={on ? rad(l.b) + 2 : rad(l.b)} fill={COLOUR[l.s === 1 ? 1 : l.s === 0 ? 0 : 2]}
                      fillOpacity={on ? 0.95 : 0.45} stroke={on ? 'var(--text-primary)' : 'none'} strokeWidth={1}
                      onMouseEnter={() => setHover({ y, l })} onClick={() => setHover({ y, l })} style={{ cursor: 'pointer' }}>
                      <title>{`${l.name} · ${y.fy} · ${l.bt} → ${l.at} · ${l.pt}`}</title>
                    </circle>)
                })}
                {y.tr ? <line x1={x0 + 4} x2={x0 + col - 4} y1={ly(y.tr)} y2={ly(y.tr)} stroke="var(--text-primary)" strokeWidth={3} /> : null}
                {y.total ? (() => {
                  // "0.71% over budget": the figure on one line, its direction under it
                  const k = y.total.indexOf(' ')
                  return (
                    <text x={x0 + col / 2} y={H - 20} fontSize={11.5} textAnchor="middle" fontWeight={600} fill="var(--text-primary)">
                      {y.total.slice(0, k)}
                      <tspan x={x0 + col / 2} dy={13} fontSize={10} fontWeight={400} fill="var(--text-muted)">{y.total.slice(k + 1)}</tspan>
                    </text>)
                })() : null}
              </g>)
          })}
        </svg>
      </div>
      <p className="text-[12.5px] mt-2 min-h-[1.5em]" aria-live="polite">
        {hover ? <><span className="font-semibold">{hover.l.name}</span> · {hover.y.fy} · {hover.l.bt} → {hover.l.at} · <span className="font-semibold">{hover.l.pt}</span></>
          : <span style={muted}>{t.hover}</span>}</p>
      <p className="text-[12px] mt-1" style={muted}>{t.books}: {t.books_note}. {t.ledger}: {t.ledger_note}. {t.clipped}.</p>
      <p className="text-[12px] mt-1" style={muted}>* {t.workbook}: {t.workbook_note}.</p>
    </figure>)
}

/** EVERY LINE, EVERY YEAR (budget-against-actual, the signature). One column per fiscal year;
 *  each dot is one school line, placed by what it SPENT against what it was VOTED (a ratio, on a
 *  log scale so half and double sit equally far from the vote), its area by the size of its vote.
 *  A bar across each column is every dot added together. The total sits on the vote while the
 *  dots spread far above and below it: the whole finding of the August report, as one picture.
 *
 *  Years from the district's budget documents and years from the accounting system are shaded
 *  apart and never joined; a year neither can compare (FY2021) is drawn empty, with its reason.
 *  The flags, line by line and year by year, are the grid below it (bva-grid). Every string and
 *  figure is the payload's (scripts/build_budget_against_actual.py, across()). */
import { useMemo, useState } from 'react'
import type { CustomProps } from './index'

type Dot = { name: string; b: number; a: number; s: 0 | 1 | 2; bt: string; at: string; pt: string }
type Year = { fy: string; src: 'books' | 'ledger' | 'none'; lines: Dot[]; total: string; tr: number | null }
type Data = { years: Year[]; ticks: { r: number; t: string }[]; lo: number; hi: number; text: Record<string, string> }

const muted = { color: 'var(--text-muted)' }
const COLOUR = ['var(--thread-2)', 'var(--thread-1)', 'var(--text-muted)']   // everything else, salaries, not in the workbook
const W = 960, H = 380, TOP = 34, BOT = 20, LEFT = 112, RIGHT = 8

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
  const first = (src: Year['src']) => d.years.findIndex(y => y.src === src)
  const last = (src: Year['src']) => d.years.length - 1 - [...d.years].reverse().findIndex(y => y.src === src)
  const band = (src: 'books' | 'ledger') => {
    const a = first(src), b = last(src)
    return a < 0 ? null : { x: LEFT + a * col, w: (b - a + 1) * col }
  }
  const books = band('books'), ledger = band('ledger')
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
          {books ? <rect x={books.x} y={TOP - 30} width={books.w} height={H - TOP + 30 - BOT} fill="var(--surface-3)" opacity={0.55} /> : null}
          {books ? <text x={books.x + 6} y={TOP - 18} fontSize={12} fontWeight={600} fill="var(--text-secondary)">{t.books}</text> : null}
          {ledger ? <text x={ledger.x + 6} y={TOP - 18} fontSize={12} fontWeight={600} fill="var(--text-secondary)">{t.ledger}</text> : null}
          {d.ticks.map(k => (
            <g key={k.r}>
              <line x1={LEFT} x2={W - RIGHT} y1={ly(k.r)} y2={ly(k.r)} stroke="var(--grid)" strokeWidth={k.r === 1 ? 1.5 : 1}
                strokeDasharray={k.r === 1 ? undefined : '3 4'} />
              <text x={LEFT - 6} y={ly(k.r) + 4} fontSize={11} textAnchor="end" fill="var(--text-muted)">{k.t}</text>
            </g>))}
          {d.years.map((y, i) => {
            const x0 = LEFT + i * col
            return (
              <g key={y.fy}>
                <text x={x0 + col / 2} y={TOP - 4} fontSize={12} textAnchor="middle" fontWeight={600} fill="var(--text-primary)">{y.fy}</text>
                {y.src === 'none' ? (
                  <>
                    <rect x={x0 + 6} y={TOP + 4} width={col - 12} height={H - TOP - BOT - 8} fill="url(#bva-hatch)" opacity={0.5} />
                    <text x={x0 + col / 2} y={ly(1) - 8} fontSize={11} textAnchor="middle" fill="var(--text-secondary)">{t.none}</text>
                  </>) : null}
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
                {y.total ? <text x={x0 + col / 2} y={H - 4} fontSize={11.5} textAnchor="middle" fontWeight={600} fill="var(--text-primary)">{y.total}</text> : null}
              </g>)
          })}
          <defs>
            <pattern id="bva-hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
              <line x1="0" y1="0" x2="0" y2="6" stroke="var(--text-muted)" strokeWidth="1.2" />
            </pattern>
          </defs>
        </svg>
      </div>
      <p className="text-[12.5px] mt-2 min-h-[1.5em]" aria-live="polite">
        {hover ? <><span className="font-semibold">{hover.l.name}</span> · {hover.y.fy} · {hover.l.bt} → {hover.l.at} · <span className="font-semibold">{hover.l.pt}</span></>
          : <span style={muted}>{t.hover}</span>}</p>
      <p className="text-[12px] mt-1" style={muted}>{t.books}: {t.books_note}. {t.ledger}: {t.ledger_note}. {t.none}: {t.none_note}. {t.clipped}.</p>
    </figure>)
}

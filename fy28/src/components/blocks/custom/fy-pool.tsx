/** ONE POOL, NOT PAIRS (fy2026-breakdown): where a year's leftovers went, drawn as the books
 *  record it.
 *
 *  Inside one appropriation a dollar left on one line pays for another, and the books record
 *  no pairing between a line's leftover and another line's overrun. So nothing here is drawn
 *  from one line to another: every category whose lines ended under flows into ONE pool, the
 *  pool flows out to every category whose lines ran over, and what remains is what was left.
 *  The only line-to-line pairings the books do record are transfers, which are on the timeline.
 *
 *  Three columns, one scale: under (left), the pool (middle), over and left (right). A year
 *  picked from the chips; hover or tap a category for its amount and how many lines.
 *  Every figure is formatted by scripts/build_fy_breakdown.py. */
import { useState } from 'react'
import type { CustomProps } from './index'

type Side = { cat: string; value: number; text: string; lines: string }
type Year = { fy: string; under: number; over: number; left: number; t_under: string; t_over: string; t_left: string
  into: Side[]; out: Side[]; transfers: string; n_transfers: string }
type Data = { years: Year[]; text: { under: string; over: string; pool: string; left: string; lines: string; transfers: string; read: string } }

const W = 720, H = 460, NODE = 14, GAP = 3, LX = 0, PX = 345, RX = W - NODE
const IN = 'var(--status-good, var(--thread-5))', OUT = 'var(--status-bad, var(--thread-1))', POOL = 'var(--text-secondary)'

function Chip({ on, onClick, children }: { on: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button type="button" onClick={onClick} aria-pressed={on}
      className="px-2.5 py-1 rounded-full text-[12.5px] border leading-tight"
      style={{ borderColor: on ? 'var(--text-secondary)' : 'var(--grid)', color: on ? 'var(--text-primary)' : 'var(--text-muted)',
        background: on ? 'var(--surface-2)' : 'transparent', fontWeight: on ? 600 : 400 }}>{children}</button>)
}

const band = (x1: number, a0: number, a1: number, x2: number, b0: number, b1: number) => {
  const xm = (x1 + x2) / 2
  return `M${x1},${a0} C${xm},${a0} ${xm},${b0} ${x2},${b0} L${x2},${b1} C${xm},${b1} ${xm},${a1} ${x1},${a1} Z`
}

export default function FyPool({ data, alt }: CustomProps) {
  const d = data as Data
  const [yi, setYi] = useState(d.years.length - 1)
  const [hot, setHot] = useState<string | null>(null)
  const y = d.years[yi]
  // One scale for every year, so a bigger pool looks bigger.
  const maxPool = Math.max(...d.years.map(v => v.under))
  const nodes = Math.max(y.into.length, y.out.length + 1)
  const k = (H - 40 - nodes * GAP) / maxPool

  let at = 20
  const left = y.into.map(s => { const h = Math.max(1, s.value * k); const r = { s, y0: at, y1: at + h }; at += h + GAP; return r })
  const poolH = y.under * k
  const p0 = 20
  let pin = p0
  const inBands = left.map(n => { const h = n.y1 - n.y0; const b = band(LX + NODE, n.y0, n.y1, PX, pin, pin + h); pin += h; return { n, b } })
  at = 20
  let pout = p0
  const right = [...y.out.map(s => ({ s, kind: 'out' as const })), { s: { cat: d.text.left, value: y.left, text: y.t_left, lines: '' }, kind: 'left' as const }]
    .filter(r => r.s.value > 0)
    .map(r => { const h = Math.max(1, r.s.value * k); const node = { ...r, y0: at, y1: at + h }; at += h + GAP; return node })
  const outBands = right.map(n => { const h = n.s.value * k; const b = band(PX + NODE, pout, pout + h, RX, n.y0, n.y0 + h); pout += h; return { n, b } })

  const tip = hot ? [...left.map(n => ({ ...n, side: d.text.under })), ...right.map(n => ({ ...n, side: n.kind === 'left' ? '' : d.text.over }))].find(n => `${n.side}|${n.s.cat}` === hot) : null

  return (
    <figure aria-label={alt} className="max-w-3xl">
      <div className="flex flex-wrap gap-1.5">
        {d.years.map((v, i) => <Chip key={v.fy} on={i === yi} onClick={() => { setYi(i); setHot(null) }}>{v.fy}</Chip>)}
      </div>
      <div className="grid grid-cols-3 mt-3 text-[13px] font-semibold">
        <span>{d.text.under} <span className="tabular-nums font-normal" style={{ color: 'var(--text-secondary)' }}>{y.t_under}</span></span>
        <span className="text-center">{d.text.pool}</span>
        <span className="text-right">{d.text.over} <span className="tabular-nums font-normal" style={{ color: 'var(--text-secondary)' }}>{y.t_over}</span></span>
      </div>
      <div className="relative">
        <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto block mt-1" role="img" aria-label={alt} onMouseLeave={() => setHot(null)}>
          {inBands.map(({ n, b }) => <path key={n.s.cat} d={b} fill={IN} opacity={!hot || hot === `${d.text.under}|${n.s.cat}` ? 0.28 : 0.08} />)}
          {outBands.map(({ n, b }) => <path key={n.s.cat} d={b} fill={n.kind === 'left' ? POOL : OUT} opacity={!hot || hot === `${n.kind === 'left' ? '' : d.text.over}|${n.s.cat}` ? 0.28 : 0.08} />)}
          <rect x={PX} y={p0} width={NODE} height={poolH} fill={POOL} />
          {left.map(n => (
            <g key={n.s.cat} style={{ cursor: 'pointer' }} onMouseEnter={() => setHot(`${d.text.under}|${n.s.cat}`)}
              onClick={() => setHot(h => (h === `${d.text.under}|${n.s.cat}` ? null : `${d.text.under}|${n.s.cat}`))}>
              <rect x={LX} y={n.y0} width={NODE} height={n.y1 - n.y0} fill={IN} />
              {n.y1 - n.y0 > 11 ? <text x={LX + NODE + 5} y={(n.y0 + n.y1) / 2 + 4} fontSize={12} fill="var(--text-secondary)">{n.s.cat}</text> : null}
            </g>))}
          {right.map(n => {
            const key = `${n.kind === 'left' ? '' : d.text.over}|${n.s.cat}`
            return (
              <g key={n.s.cat} style={{ cursor: 'pointer' }} onMouseEnter={() => setHot(key)} onClick={() => setHot(h => (h === key ? null : key))}>
                <rect x={RX} y={n.y0} width={NODE} height={n.y1 - n.y0} fill={n.kind === 'left' ? POOL : OUT} />
                {n.y1 - n.y0 > 11 || n.kind === 'left' ? <text x={RX - 5} y={(n.y0 + n.y1) / 2 + 4} fontSize={12} textAnchor="end"
                  fontWeight={n.kind === 'left' ? 700 : 400} fill={n.kind === 'left' ? 'var(--text-primary)' : 'var(--text-secondary)'}>
                  {n.kind === 'left' ? `${n.s.cat} ${n.s.text}` : n.s.cat}</text> : null}
              </g>)
          })}
        </svg>
        {tip ? (
          <div role="status" className="mt-2 sm:absolute sm:left-1/2 sm:-translate-x-1/2 sm:bottom-2 sm:w-[300px] px-2.5 py-2 rounded text-[12.5px] leading-snug shadow"
            style={{ background: 'var(--surface-1)', border: '1px solid var(--grid)' }}>
            <p className="font-semibold">{tip.s.cat}</p>
            <p className="flex justify-between gap-3 mt-1 tabular-nums"><span style={{ color: 'var(--text-secondary)' }}>{tip.side || d.text.left}{tip.s.lines ? ` · ${tip.s.lines}` : ''}</span><span className="font-semibold">{tip.s.text}</span></p>
          </div>) : null}
      </div>
      <p className="text-[13px] mt-2" style={{ color: 'var(--text-secondary)' }}>{d.text.transfers} <span className="tabular-nums font-semibold">{y.transfers}</span>, {y.n_transfers}.</p>
      <figcaption className="text-[12.5px] mt-1 leading-snug" style={{ color: 'var(--text-muted)' }}>{d.text.read}</figcaption>
    </figure>
  )
}

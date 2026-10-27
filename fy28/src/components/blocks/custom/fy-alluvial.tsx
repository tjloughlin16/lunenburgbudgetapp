/** WHO PAID FOR WHAT, YEAR BY YEAR (fy2026-breakdown): an alluvial diagram.
 *
 *  TJ, 26 October 2026: "there has to be a way to visualize fungibility then. this has to be a
 *  solved problem?" Across funds it is: four fiscal years side by side, each a stack of what
 *  the school budget's lines cost from every fund, in seven blocks, each block split by who
 *  paid. A band carries each (block, payer) from one year to the next, so a cost that held
 *  while its payer changed reads as a band keeping its height and changing colour.
 *
 *  At the scale of the whole budget a grant's share of a block is a hairline, so a reader can
 *  pick ONE block and see it alone at full height (chips above, or `?block=<id>` in the address).
 *  Hovering or tapping a segment prints its year, block, payer and amount. The grey block is
 *  other funds' spending no match rule places on a line, and is never coloured as a payer of
 *  a line.
 *
 *  Every figure is formatted by scripts/build_fy_breakdown.py; this draws marks from the
 *  numbers and prints the given text. */
import { useMemo, useState } from 'react'
import type { CustomProps } from './index'

type Seg = { payer: string; value: number; text: string }
type Block = { group: string; total: number; text: string; segs: Seg[] }
type Year = { fy: string; total: number; text: string; blocks: Block[] }
type Data = {
  years: Year[]
  groups: { id: string; label: string }[]
  payers: { id: string; label: string }[]
  negatives: { fy: string; group: string; payer: string; text: string }[]
  text: { all: string; one: string; total: string; pick: string; negatives: string }
  note: string
}

const COLOR: Record<string, string> = {
  gf: 'var(--thread-1)', idea: 'var(--thread-2)', grants: 'var(--thread-3)',
  cb: 'var(--thread-4)', fees: 'var(--thread-5)', other: 'var(--text-secondary)',
}
const UNMATCHED = 'unmatched'
const GREY = 'var(--text-muted)'
const fill = (g: string, p: string) => (g === UNMATCHED ? GREY : COLOR[p] ?? GREY)

const W = 720, H = 380, TOP = 4, BOTTOM = 4, BAR = 26, GAP = 5

type Placed = { g: string; p: string; y0: number; y1: number; seg: Seg; block: Block }

function Chip({ on, onClick, children }: { on: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button type="button" onClick={onClick} aria-pressed={on}
      className="px-2.5 py-1 rounded-full text-[12.5px] border leading-tight"
      style={{ borderColor: on ? 'var(--text-secondary)' : 'var(--grid)', color: on ? 'var(--text-primary)' : 'var(--text-muted)',
        background: on ? 'var(--surface-2)' : 'transparent', fontWeight: on ? 600 : 400 }}>
      {children}
    </button>
  )
}

export default function FyAlluvial({ data, alt }: CustomProps) {
  const d = data as Data
  // `?block=<id>` opens on one block, so a picked view can be linked to.
  const [focus, setFocus] = useState<string | null>(() => {
    const b = typeof window === 'undefined' ? null : new URLSearchParams(window.location.search).get('block')
    return b && d.groups.some(g => g.id === b) ? b : null
  })
  const [hover, setHover] = useState<{ i: number; k: string } | null>(null)
  const [held, setHeld] = useState<{ i: number; k: string } | null>(null)
  const tip = hover ?? held
  const groupLabel = (g: string) => d.groups.find(x => x.id === g)?.label ?? g
  const payerLabel = (p: string) => d.payers.find(x => x.id === p)?.label ?? p

  const n = d.years.length
  const xs = d.years.map((_, i) => (i * (W - BAR)) / (n - 1))

  // Every column stacked on one scale: the largest column (or the largest picked block) fills
  // the height, so lengths compare across years.
  const cols = useMemo(() => {
    const shown = (y: Year) => y.blocks.filter(b => focus === null || b.group === focus)
    const gaps = (y: Year) => Math.max(0, shown(y).filter(b => b.segs.length).length - 1) * GAP
    const max = Math.max(1, ...d.years.map(y => shown(y).reduce((a, b) => a + b.total, 0)))
    const k = (H - TOP - BOTTOM - Math.max(...d.years.map(gaps))) / max
    return d.years.map(y => {
      let at = TOP
      const placed: Placed[] = []
      const heads: { g: string; y0: number; y1: number; block: Block }[] = []
      for (const b of shown(y)) {
        if (!b.segs.length) continue
        const start = at
        for (const s of b.segs) {
          const h = s.value * k
          placed.push({ g: b.group, p: s.payer, y0: at, y1: at + h, seg: s, block: b })
          at += h
        }
        heads.push({ g: b.group, y0: start, y1: at, block: b })
        at += GAP
      }
      return { placed, heads }
    })
  }, [d.years, focus])

  // A band per (block, payer) between adjacent years. One that is missing on a side starts or
  // ends at zero height where it would have been, so a payer that appears visibly grows in.
  const bands = useMemo(() => {
    const out: { key: string; g: string; p: string; d: string }[] = []
    for (let i = 0; i < n - 1; i++) {
      const a = cols[i], b = cols[i + 1]
      const keys = new Set([...a.placed, ...b.placed].map(s => `${s.g}|${s.p}`))
      for (const key of keys) {
        const [g, p] = key.split('|')
        const end = (c: typeof a) => {
          const s = c.placed.find(x => x.g === g && x.p === p)
          if (s) return [s.y0, s.y1]
          const h = c.heads.find(x => x.g === g)
          const y = h ? h.y1 : (c.heads.length ? c.heads[c.heads.length - 1].y1 : TOP)
          return [y, y]
        }
        const [a0, a1] = end(a), [b0, b1] = end(b)
        if (a1 - a0 < 0.01 && b1 - b0 < 0.01) continue
        const x1 = xs[i] + BAR, x2 = xs[i + 1], xm = (x1 + x2) / 2
        out.push({ key: `${i}|${key}`, g, p,
          d: `M${x1},${a0} C${xm},${a0} ${xm},${b0} ${x2},${b0} L${x2},${b1} C${xm},${b1} ${xm},${a1} ${x1},${a1} Z` })
      }
    }
    return out
  }, [cols, n, xs])

  const tipSeg = tip ? cols[tip.i].placed.find(s => `${s.g}|${s.p}` === tip.k) : undefined
  const lit = (g: string, p: string) => !tip || tip.k === `${g}|${p}`
  const payersUsed = d.payers.filter(p => d.years.some(y => y.blocks.some(b => b.group !== UNMATCHED && b.segs.some(s => s.payer === p.id))))

  return (
    <figure aria-label={alt} className="max-w-3xl">
      <div className="flex flex-wrap gap-1.5" role="group" aria-label={d.text.pick}>
        <Chip on={focus === null} onClick={() => { setFocus(null); setHeld(null) }}>{d.text.all}</Chip>
        {d.groups.map(g => (
          <Chip key={g.id} on={focus === g.id} onClick={() => { setFocus(f => (f === g.id ? null : g.id)); setHeld(null) }}>
            {g.label}</Chip>))}
      </div>
      <div className="relative mt-3">
        <div className="relative h-5 text-[13px] font-semibold">
          {d.years.map((y, i) => (
            <span key={y.fy} className="absolute whitespace-nowrap tabular-nums" style={{ left: i === 0 ? '0%' : i === n - 1 ? '100%' : `${(100 * (xs[i] + BAR / 2)) / W}%`,
              transform: i === 0 ? 'translateX(0)' : i === n - 1 ? 'translateX(-100%)' : 'translateX(-50%)' }}>{y.fy}</span>))}
        </div>
        <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto block" role="img" aria-label={alt}
          onMouseLeave={() => setHover(null)}>
          {bands.map(b => (
            <path key={b.key} d={b.d} fill={fill(b.g, b.p)}
              opacity={lit(b.g, b.p) ? (b.g === UNMATCHED ? 0.18 : 0.3) : 0.06} />))}
          {cols.map((c, i) => (
            <g key={d.years[i].fy}>
              {c.placed.map(s => {
                const k = `${s.g}|${s.p}`
                return (
                  <rect key={k} x={xs[i]} y={s.y0} width={BAR} height={Math.max(0.6, s.y1 - s.y0)}
                    fill={fill(s.g, s.p)} opacity={lit(s.g, s.p) ? (s.g === UNMATCHED ? 0.55 : 1) : 0.25}
                    style={{ cursor: 'pointer' }}
                    onMouseEnter={() => setHover({ i, k })}
                    onClick={() => setHeld(h => (h && h.i === i && h.k === k ? null : { i, k }))}>
                    <title>{`${d.years[i].fy} · ${groupLabel(s.g)} · ${payerLabel(s.p)}: ${s.seg.text}`}</title>
                  </rect>)
              })}
            </g>))}
          {focus === null ? <g className="hidden sm:inline">{cols[0].heads.map(h => (h.y1 - h.y0 > 16 ? (
            <text key={h.g} x={xs[0] + BAR + 6} y={(h.y0 + h.y1) / 2 + 4} fontSize={12}
              fill="var(--text-secondary)" style={{ pointerEvents: 'none' }}>{groupLabel(h.g)}</text>) : null))}</g> : null}
        </svg>
        <div className="relative h-5 mt-1 text-[12px]" style={{ color: 'var(--text-secondary)' }}>
          {d.years.map((y, i) => (
            <span key={y.fy} className="absolute whitespace-nowrap tabular-nums" style={{ left: i === 0 ? '0%' : i === n - 1 ? '100%' : `${(100 * (xs[i] + BAR / 2)) / W}%`,
              transform: i === 0 ? 'translateX(0)' : i === n - 1 ? 'translateX(-100%)' : 'translateX(-50%)' }}>{focus === null ? y.text : (y.blocks.find(b => b.group === focus)?.text ?? '')}</span>))}
        </div>
        {tipSeg && tip ? (
          <div role="status" className="mt-2 sm:absolute sm:right-0 sm:top-0 sm:w-[300px] px-2.5 py-2 rounded text-[12.5px] leading-snug shadow"
            style={{ background: 'var(--surface-1)', border: '1px solid var(--grid)', color: 'var(--text-primary)' }}>
            <p className="font-semibold">{d.years[tip.i].fy} · {groupLabel(tipSeg.g)}</p>
            <p className="flex justify-between gap-3 mt-1">
              <span className="inline-flex items-center gap-1.5">
                <span className="inline-block w-2.5 h-2.5 rounded-sm" style={{ background: fill(tipSeg.g, tipSeg.p) }} />
                {payerLabel(tipSeg.p)}</span>
              <span className="tabular-nums font-semibold">{tipSeg.seg.text}</span></p>
            <p className="flex justify-between gap-3 mt-1 pt-1 border-t tabular-nums" style={{ borderColor: 'var(--grid)', color: 'var(--text-secondary)' }}>
              <span>{d.text.total}</span><span>{tipSeg.block.text}</span></p>
          </div>) : null}
      </div>
      <ul className="flex flex-wrap gap-x-4 gap-y-1.5 mt-3 text-[13px]" style={{ color: 'var(--text-secondary)' }}>
        {payersUsed.map(p => (
          <li key={p.id} className="inline-flex items-center gap-1.5">
            <span className="inline-block w-3.5 h-3 rounded-sm shrink-0" style={{ background: COLOR[p.id] }} />{p.label}</li>))}
        <li className="inline-flex items-center gap-1.5">
          <span className="inline-block w-3.5 h-3 rounded-sm shrink-0" style={{ background: GREY, opacity: 0.55 }} />
          {groupLabel(UNMATCHED)}</li>
      </ul>
      {d.negatives.length ? (
        <p className="text-[12.5px] mt-2" style={{ color: 'var(--text-muted)' }}>{d.text.negatives}{' '}
          {d.negatives.map(x => `${x.fy}, ${groupLabel(x.group)}, ${payerLabel(x.payer)} ${x.text}`).join('; ')}</p>) : null}
      <figcaption className="text-[12.5px] mt-2 leading-snug" style={{ color: 'var(--text-muted)' }}>{d.note}</figcaption>
    </figure>
  )
}

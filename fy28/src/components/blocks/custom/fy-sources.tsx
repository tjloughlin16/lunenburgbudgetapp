/** WHERE EACH SOURCE'S MONEY WENT (fy-breakdown). TJ, 29 October 2026: "a viz that shows every
 *  non general fund source of funding, and show what it paid for in that year (the lines, funds,
 *  etc) as proportions ... a horizontal thing ... it would be ideal if we could also show the
 *  revenue and amount unspent on the same chart."
 *
 *  One bar per source, the page's year: what it spent, split by the school lines it paid toward
 *  (the same few lines keep the same colour on every bar and every year), every other line, the
 *  same kind of work with no single line, and -- hatched, as everywhere on this page -- spending on
 *  no school line. A mark at what it received: where the bar stops short of it, the rest is drawn
 *  outlined, received and not spent; where the bar runs past it, the source spent more than it
 *  took in. Dollars put every bar on one scale; Shares make each bar the same length so how each
 *  source split its money compares. Every figure is formatted by scripts/build_fy_breakdown.py
 *  (sources_data). */
import { useMemo, useState } from 'react'
import { useFyYear } from './fy-year'
import type { CustomProps } from './index'
import { Chip, hatch, Row } from './fy-shared'
import { itemHrefs, useItemIndex, withYear } from './fy-items'

type Seg = { id: string; v: number; t: string }
type Bar = { id: string; label: string; segs: Seg[]; received: number; spent: number
  t: { received: string; spent: string; gap: string }; top: { account: string; name: string; t: string }[] }
type Data = { years: { fy: string; bars: Bar[] }[]; lines: { id: string; name: string }[]; text: Record<string, string> }

const LINE_COLOURS = ['var(--thread-1)', 'var(--thread-2)', 'var(--thread-5)', 'var(--thread-3)', 'var(--thread-4)', 'var(--thread-6, var(--text-secondary))']
const muted = { color: 'var(--text-muted)' }, secondary = { color: 'var(--text-secondary)' }
const link = { color: 'var(--link, var(--thread-2))' }

export default function FySources({ data, alt }: CustomProps) {
  const d = data as Data
  const t = d.text
  const fys = useMemo(() => d.years.map(v => v.fy), [d])
  const [fy] = useFyYear(fys)
  const y = d.years[Math.max(0, fys.indexOf(fy))]
  const [shares, setShares] = useState(false)
  const href = itemHrefs(useItemIndex())
  const fill = (id: string): React.CSSProperties => {
    const i = d.lines.findIndex(l => l.id === id)
    if (i >= 0) return { background: LINE_COLOURS[i % LINE_COLOURS.length], opacity: 0.85 }
    if (id === 'rest') return { background: 'var(--text-muted)', opacity: 0.45 }
    if (id === 'kind') return { background: 'var(--text-muted)', opacity: 0.2 }
    return { background: hatch('var(--text-secondary)') }
  }
  const name = (id: string) => d.lines.find(l => l.id === id)?.name ?? (id === 'rest' ? t.rest : id === 'kind' ? t.kind : t.none)
  const max = Math.max(1, ...y.bars.map(b => Math.max(b.received, b.spent)))
  const legend: { id: string; label: string; href?: string }[] = [
    ...d.lines.map(l => ({ id: l.id, label: l.name, href: href.line(l.id) })),
    { id: 'rest', label: t.rest }, { id: 'kind', label: t.kind }, { id: 'none', label: t.none }]

  return (
    <figure aria-label={alt}>
      <div className="flex flex-wrap items-center gap-1.5 mb-2">
        <Chip on={!shares} onClick={() => setShares(false)}>{t.dollars}</Chip>
        <Chip on={shares} onClick={() => setShares(true)}>{t.shares}</Chip>
      </div>
      <div className="flex flex-wrap gap-x-3 gap-y-1 text-[12px] mb-3" style={secondary}>
        {legend.map(l => (
          <span key={l.id} className="inline-flex items-center gap-1">
            <span className="inline-block w-2.5 h-2.5 rounded-[2px]" style={fill(l.id)} />
            {l.href ? <a href={withYear(l.href, y.fy)} className="underline" style={link}>{l.label}</a> : l.label}</span>))}
        <span className="inline-flex items-center gap-1">
          <span className="inline-block w-2.5 h-2.5 rounded-[2px]" style={{ border: '1.5px dashed var(--text-secondary)' }} />{t.unspent}</span>
        <span className="inline-flex items-center gap-1">
          <span className="inline-block w-[2px] h-3" style={{ background: 'var(--text-primary)' }} />{t.received}</span>
      </div>
      <div className="space-y-3">
        {y.bars.map(b => {
          const scale = shares ? Math.max(b.received, b.spent, 1) : max
          const pc = (v: number) => (v / scale) * 100
          let at = 0
          return (
            <Row key={b.id} label={b.label} sub={`${t.received} ${b.t.received} · ${t.spent} ${b.t.spent} · ${t.gap} ${b.t.gap}`}>
              <div className="w-full sm:flex-1 min-w-0">
                <div className="relative h-7">
                  {b.segs.filter(s => s.v > 0.5).map(s => {
                    const el = <div key={s.id} title={`${name(s.id)}: ${s.t}`} className="absolute top-0.5 bottom-0.5"
                      style={{ left: `${pc(at)}%`, width: `max(2px, ${pc(s.v)}%)`, borderRight: '1px solid var(--surface-1, #fff)', ...fill(s.id) }} />
                    at += s.v
                    return el
                  })}
                  {/* received and not spent: outlined, never filled -- it is not spending */}
                  {b.received > b.spent + 0.5 ? <div title={`${t.unspent}: ${b.t.gap}`} className="absolute top-0.5 bottom-0.5"
                    style={{ left: `${pc(b.spent)}%`, width: `${pc(b.received - b.spent)}%`, border: '1.5px dashed var(--text-secondary)' }} /> : null}
                  {b.received > 0.5 ? <div title={`${t.received}: ${b.t.received}`} className="absolute -top-0.5 -bottom-0.5 w-[2px]"
                    style={{ left: `calc(${pc(b.received)}% - 1px)`, background: 'var(--text-primary)' }} /> : null}
                </div>
                {b.top.length ? (
                  <p className="text-[11.5px] mt-0.5" style={muted}>{t.top}: {b.top.map((x, i) => {
                    const h = href.line(x.account)
                    return <span key={x.account}>{i ? ' · ' : ''}{h ? <a href={withYear(h, y.fy)} className="underline" style={link}>{x.name}</a> : x.name} <span className="tabular-nums">{x.t}</span></span>
                  })}</p>) : null}
              </div>
            </Row>)
        })}
      </div>
      <p className="text-[11.5px] mt-3 max-w-3xl" style={muted}>{t.note}</p>
    </figure>)
}

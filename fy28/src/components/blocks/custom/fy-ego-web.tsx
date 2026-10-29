/** ONE ITEM'S OWN WEB (TJ, 28 October 2026: "a chart for each that shows similar to the canvas
 *  chart at the bottom of the breakout page, but on a per-fund/school line basis: visually show
 *  what funds it, and what it funds, a sort of isolated look").
 *
 *  The item in the centre -- a school line, or a fund (each award, where a programme has several
 *  in the year) -- what came IN on the left and what went OUT on the right. Every arrow is an
 *  arrow of the year's web (scripts/fy_web.py, the model's placements), kept by fy_items.py
 *  because it touches the item; nothing is added. One block per arrow, so a fund that both paid
 *  toward a line and was re-charged its bills shows twice, once per way. A block with its own
 *  page links to it. Drawn with the big web's colours, arrowheads and curve (fy-web-parts).
 *
 *  CHART OR TABLE, never both (TJ, 29 October 2026: "put it as a toggle: chart vs table view"). The
 *  In / Out lists under the chart repeated it block for block; the table now holds the same arrows
 *  in the same order, and since the SVG is role="img" it is the chart's only text version. */
import { useState, type ReactNode } from 'react'
import { Chip } from './fy-shared'
import { WEB_COLOUR, WebMarkers, curve, cut, edgeWidth, nodeFill, type WebEdge, type WebKind, type WebNode } from './fy-web-parts'

export type Ego = { centre: string[]; nodes: WebNode[]; edges: WebEdge[] }
type Kinds = { id: WebKind; label: string; means: string }[]

const muted = { color: 'var(--text-muted)' }, secondary = { color: 'var(--text-secondary)' }
const SW = 250, CW = 230, GAP = 120, RH = 36, RG = 6, TOP = 26
const link = { color: 'var(--link, var(--thread-2))' }
const VIEW_KEY = 'fy-ego-view'
type View = 'chart' | 'table'
const readView = (): View => {
  try { return window.localStorage.getItem(VIEW_KEY) === 'table' ? 'table' : 'chart' } catch { return 'chart' }
}

type Side = { e: WebEdge; n: WebNode; y: number; c: string }
const KIND_ORDER = Object.keys(WEB_COLOUR) as WebKind[]

/** 'IDEA (special education), FY2025 · 2813' -> ['IDEA (special education)', 'FY2025 · 2813'] */
const centreName = (label: string): [string, string] => {
  const [name, num] = label.split(' · ')
  const i = name.lastIndexOf(', ')
  return i < 0 ? [name, num ?? ''] : [name.slice(0, i), `${name.slice(i + 2)}${num ? ` · ${num}` : ''}`]
}

export function EgoWeb({ ego, kinds, text, fy }: { ego: Ego; kinds: Kinds; text: Record<string, string>; fy: string }) {
  const [view, setViewState] = useState<View>(readView)
  const setView = (v: View) => {
    setViewState(v)
    try { window.localStorage.setItem(VIEW_KEY, v) } catch { /* private window: the choice lasts this page */ }
  }
  const nodes = new Map(ego.nodes.map(n => [n.id, n]))
  const centre = new Set(ego.centre)
  const kindLabel = Object.fromEntries(kinds.map(k => [k.id, k.label]))
  // A FIXED ORDER, never by size (TJ, 28 October 2026): the same ins and outs sit in the same rows
  // every year, so flipping between years shows the amounts moving, not the blocks. Kind of arrow
  // first, in the legend's order, then the other end's name.
  const order = (other: (e: WebEdge) => string) => (a: WebEdge, b: WebEdge) =>
    KIND_ORDER.indexOf(a.k) - KIND_ORDER.indexOf(b.k)
    || (nodes.get(other(a))?.label ?? '').localeCompare(nodes.get(other(b))?.label ?? '')
    || other(a).localeCompare(other(b))
  const ins = ego.edges.filter(e => centre.has(e.b) && !centre.has(e.a)).sort(order(e => e.a))
  const outs = ego.edges.filter(e => centre.has(e.a) && !centre.has(e.b)).sort(order(e => e.b))
  // between two of the centre's own blocks (one programme's awards): an arc on the centre's left
  const inner = ego.edges.filter(e => centre.has(e.a) && centre.has(e.b)).sort(order(e => e.a))
  const rows = Math.max(ins.length, outs.length, ego.centre.length, 1)
  const H = TOP + rows * (RH + RG) + 8
  // the centre blocks share the height of the taller side, so arrows fan in rather than pile up
  const ch = Math.max(RH, (H - TOP - 8 - (ego.centre.length - 1) * RG) / ego.centre.length)
  const cy = new Map(ego.centre.map((id, i) => [id, TOP + i * (ch + RG)]))
  const side = (es: WebEdge[], other: (e: WebEdge) => string, c: (e: WebEdge) => string): Side[] =>
    es.map((e, i) => ({ e, n: nodes.get(other(e))!, y: TOP + i * (RH + RG), c: c(e) }))
  const left = side(ins, e => e.a, e => e.b), right = side(outs, e => e.b, e => e.a)
  const max = Math.max(1, ...ego.edges.map(e => Math.abs(e.v)))
  const W = SW + GAP + CW + GAP + SW, cx = SW + GAP
  const used = [...new Set(ego.edges.map(e => e.k))]
  const mid = (id: string) => (cy.get(id) ?? TOP) + ch / 2

  const block = (s: Side, x: number) => {
    const body = (
      <g transform={`translate(${x},${s.y})`}>
        <rect width={SW} height={RH} rx={4} fill={s.n.kind === 'fund' ? 'var(--surface-1, var(--bg))' : nodeFill(s.n)}
          stroke={s.n.kind === 'fund' ? nodeFill(s.n) : 'var(--grid)'} />
        {s.n.kind === 'fund' ? <rect width={6} height={RH} rx={2} fill={nodeFill(s.n)} /> : null}
        <text x={s.n.kind === 'fund' ? 12 : 8} y={15} fontSize={12} fill={s.n.href ? 'var(--link, var(--thread-2))' : 'var(--text-primary)'}
          textDecoration={s.n.href ? 'underline' : undefined}>{cut(s.n.label, 36)}</text>
        <text x={s.n.kind === 'fund' ? 12 : 8} y={30} fontSize={10.5} fill="var(--text-muted)">{cut(kindLabel[s.e.k] ?? s.e.k, 30)}</text>
        <text x={SW - 8} y={30} fontSize={11.5} fontWeight={600} textAnchor="end" fill="var(--text-primary)">{s.e.t}</text>
        <title>{`${s.n.label}${s.n.sub ? ` · ${s.n.sub}` : ''}\n${kindLabel[s.e.k] ?? s.e.k}: ${s.e.t}${s.e.d ? `\n${s.e.d} · ${s.e.m ?? ''}` : ''}`}</title>
      </g>)
    return s.n.href ? <a key={`${s.e.a}${s.e.b}${s.e.k}${s.y}`} href={`${s.n.href}?fy=${encodeURIComponent(fy)}`}>{body}</a>
      : <g key={`${s.e.a}${s.e.b}${s.e.k}${s.y}`}>{body}</g>
  }
  const href = (n: WebNode) => `${n.href}?fy=${encodeURIComponent(fy)}`
  const name = (n?: WebNode) => !n ? null : n.href ? <a href={href(n)} className="underline" style={link}>{n.label}</a> : n.label
  const kindCell = (e: WebEdge) => (
    <span className="inline-flex items-start gap-1.5"><span className="inline-block w-2 h-2 rounded-sm mt-1.5 shrink-0" style={{ background: WEB_COLOUR[e.k] }} />
      <span>{kindLabel[e.k] ?? e.k}{e.d ? <span className="block text-[11.5px]" style={muted}>{e.d}</span> : null}</span></span>)
  const group = (title: string, rows: { key: string; other: ReactNode; e: WebEdge }[]) => (
    <tbody key={title}>
      <tr><th colSpan={3} scope="colgroup" className="text-left font-semibold pt-3 pb-1">{title}</th></tr>
      {rows.length ? rows.map(r => (
        <tr key={r.key} className="border-t" style={{ borderColor: 'var(--grid)' }}>
          <td className="py-1.5 pr-3 align-top">{r.other}</td>
          <td className="py-1.5 pr-3 align-top">{kindCell(r.e)}</td>
          <td className="py-1.5 align-top text-right tabular-nums font-semibold whitespace-nowrap">{r.e.t}</td></tr>))
        : <tr><td colSpan={3} className="py-1.5" style={muted}>{text.web_none_row}</td></tr>}
    </tbody>)
  const table = (
    <div className="overflow-x-auto">
      <table className="w-full text-[13px]">
        <caption className="sr-only">{text.web_h}</caption>
        <thead><tr style={secondary} className="text-[12px]">
          <th scope="col" className="text-left font-normal pr-3">{text.web_th_other}</th>
          <th scope="col" className="text-left font-normal pr-3">{text.web_th_kind}</th>
          <th scope="col" className="text-right font-normal">{text.web_th_amount}</th></tr></thead>
        {group(text.web_from, left.map((s, i) => ({ key: `l${i}`, other: name(s.n), e: s.e })))}
        {group(text.web_to, right.map((s, i) => ({ key: `r${i}`, other: name(s.n), e: s.e })))}
        {inner.length ? group(text.web_inner, inner.map((e, i) => ({ key: `i${i}`, e,
          other: <>{nodes.get(e.a)?.label} <span style={muted}>{text.web_took}</span> {nodes.get(e.b)?.label}</> }))) : null}
      </table>
    </div>)

  return (
    <figure>
      <div className="flex gap-1.5 mb-2" role="group" aria-label={text.web_view}>
        <Chip on={view === 'chart'} onClick={() => setView('chart')}>{text.web_view_chart}</Chip>
        <Chip on={view === 'table'} onClick={() => setView('table')}>{text.web_view_table}</Chip>
      </div>
      {view === 'table' ? table : <>
      <div className="flex flex-wrap gap-x-3 gap-y-1 text-[12px] mb-1.5" style={secondary}>
        {used.map(k => (
          <span key={k} className="inline-flex items-center gap-1" title={kinds.find(x => x.id === k)?.means}>
            <span className="inline-block w-3 h-[3px] rounded" style={{ background: k === 'transfer'
              ? `repeating-linear-gradient(90deg, ${WEB_COLOUR[k]} 0 3px, transparent 3px 5px)` : WEB_COLOUR[k] }} />{kindLabel[k] ?? k}</span>))}
      </div>
      <div className="overflow-x-auto">
        <svg viewBox={`0 0 ${W} ${H}`} className="block w-full h-auto min-w-[720px]" role="img" aria-label={text.web_h}>
          <WebMarkers prefix="fye" />
          <text x={0} y={14} fontSize={12} fontWeight={600} fill="var(--text-secondary)">{text.web_from}</text>
          <text x={W - SW} y={14} fontSize={12} fontWeight={600} fill="var(--text-secondary)">{text.web_to}</text>
          <g fill="none">
            {left.map((s, i) => (
              <path key={`l${i}`} d={curve(SW, s.y + RH / 2, cx - 6, mid(s.c), GAP / 2)} stroke={WEB_COLOUR[s.e.k]} strokeOpacity={0.6}
                strokeWidth={edgeWidth(s.e.v, max)} strokeDasharray={s.e.k === 'transfer' ? '5 4' : undefined} markerEnd={`url(#fye-${s.e.k})`} />))}
            {right.map((s, i) => (
              <path key={`r${i}`} d={curve(cx + CW, mid(s.c), W - SW - 6, s.y + RH / 2, GAP / 2)} stroke={WEB_COLOUR[s.e.k]} strokeOpacity={0.6}
                strokeWidth={edgeWidth(s.e.v, max)} strokeDasharray={s.e.k === 'transfer' ? '5 4' : undefined} markerEnd={`url(#fye-${s.e.k})`} />))}
            {inner.map((e, i) => {
              const y1 = mid(e.a) + 6, y2 = mid(e.b) - 6, b = 34 + 14 * i
              return <path key={`i${i}`} d={`M${cx},${y1} C${cx - b},${y1} ${cx - b},${y2} ${cx - 6},${y2}`} stroke={WEB_COLOUR[e.k]}
                strokeOpacity={0.8} strokeWidth={edgeWidth(e.v, max)} markerEnd={`url(#fye-${e.k})`}><title>{`${kindLabel[e.k] ?? e.k}: ${e.t}`}</title></path>
            })}
          </g>
          {ego.centre.map(id => {
            const n = nodes.get(id)!
            const y = cy.get(id)!
            return (
              <g key={id} transform={`translate(${cx},${y})`}>
                <rect width={CW} height={ch} rx={5} fill="var(--surface-2)" stroke="var(--text-primary)" strokeWidth={1.5} />
                {n.kind === 'fund' ? <rect width={7} height={ch} rx={2} fill={nodeFill(n)} /> : null}
                {/* a programme's award names its year after the comma: that part is what tells two blocks apart */}
                <text x={12} y={Math.min(ch / 2 + 4, 22)} fontSize={12.5} fontWeight={600} fill="var(--text-primary)">{cut(centreName(n.label)[0], 32)}</text>
                {centreName(n.label)[1] ? <text x={12} y={Math.min(ch / 2 + 4, 22) + 16} fontSize={11.5} fill="var(--text-secondary)">{centreName(n.label)[1]}</text> : null}
                <title>{`${n.label}${n.sub ? ` · ${n.sub}` : ''}`}</title>
              </g>)
          })}
          {left.map(s => block(s, 0))}
          {right.map(s => block(s, W - SW))}
        </svg>
      </div>
      </>}
    </figure>)
}

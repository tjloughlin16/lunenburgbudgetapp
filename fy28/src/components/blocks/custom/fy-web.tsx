/** THE WEB OF A YEAR (fy-breakdown). TJ, 28 October 2026: "every school line is a block. every
 *  fund / source of money is a block. then draw directional lines between them for the year that
 *  show the relationships of how they connect (re-charges, pays, etc). I want to see the web of
 *  how the accounts are paying for things across the school department."
 *
 *  A canvas: funds down the left, school lines down the right by category, and an arrow for each
 *  way money connected them in the page's year -- paid from the start, re-charged later, moved
 *  back, same kind of work, on no line -- with budget transfers between lines as dashed arcs.
 *  Drag to move, the buttons (or ctrl + scroll) to zoom; a block focuses its own arrows and lists
 *  them. The school budget's own spending on every line is one arrow per line and buries the
 *  rest, so it is off until asked for. Every arrow is a placement fy_breakdown already made;
 *  /data/fy-breakdown/web-<year>.json, written by scripts/fy_web.py. */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useFyYear } from './fy-year'
import { Chip } from './fy-shared'
import { WEB_COLOUR as COLOUR, WebMarkers, curve, cut, edgeWidth, nodeFill, type WebEdge as Edge, type WebFile as File, type WebKind as Kind, type WebNode as Node } from './fy-web-parts'
import { itemHrefs, useItemIndex, withYear } from './fy-items'
import type { CustomProps } from './index'

type Data = { years: string[]; kinds: { id: Kind; label: string; means: string }[]; text: Record<string, string> }

const muted = { color: 'var(--text-muted)' }, secondary = { color: 'var(--text-secondary)' }
const FUND_ORDER = ['gf', 'idea', 'grants', 'cb', 'fees', 'other']
const FW = 270, LW = 300, GAPX = 520, RH = 24, RG = 4, HEAD = 26
const FILES = new Map<string, Promise<File>>()
const load = (fy: string) => {
  if (!FILES.has(fy)) FILES.set(fy, fetch(`/data/fy-breakdown/web-${fy.replace(/\D/g, '')}.json`)
    .then(r => { if (!r.ok) throw new Error(String(r.status)); return r.json() }))
  return FILES.get(fy)!
}
type Box = { x: number; y: number; w: number; n: Node }
type Rank = 'size' | 'sources' | 'share'
/** HOW MUCH OF A LINE OTHER FUNDS CARRIED, and how many (TJ, 28 October 2026: "draw attention to
 *  lines that have a lot of connections or BIG connections to them, so i can trace them"). From
 *  every arrow the year holds, shown or not: the school budget's own spending on the line, and
 *  what funds paid toward it or took off it by re-charge. Thresholds OURS, to draw the eye. */
type Stat = { sources: number; other: number; school: number; share: number }
const MANY = 3, BIG = 0.25
function lineStats(f: File) {
  const st = new Map<string, Stat>()
  const get = (id: string) => { if (!st.has(id)) st.set(id, { sources: 0, other: 0, school: 0, share: 0 }); return st.get(id)! }
  const funds = new Map<string, Set<string>>()
  for (const e of f.edges) {
    if (e.k === 'school') { get(e.b).school += e.v; continue }
    if (e.k === 'paid' || e.k === 'later' || e.k === 'kind') { get(e.b).other += e.v; if (!funds.has(e.b)) funds.set(e.b, new Set()); funds.get(e.b)!.add(e.a) }
    if (e.k === 'back') { if (!funds.has(e.a)) funds.set(e.a, new Set()); funds.get(e.a)!.add(e.b) }
  }
  for (const [id, s] of st) { s.sources = funds.get(id)?.size ?? 0; s.share = s.other + s.school > 0 ? s.other / (s.other + s.school) : 0 }
  for (const [id, fs] of funds) if (!st.has(id)) st.set(id, { sources: fs.size, other: 0, school: 0, share: 0 })
  return st
}

/** WHERE EVERY BLOCK SITS. Funds in a column, the school budget first and the rest by kind, then
 *  size; lines in a column by category, largest connected category first; the places money lands
 *  on no line under the lines. Deterministic, so a block is where it was last time. */
function layout(f: File, kinds: Set<Kind>, everyLine: boolean, rank: Rank, stats: Map<string, Stat>, found: Set<string>) {
  const vis = f.edges.filter(e => kinds.has(e.k))
  const size = new Map<string, number>()
  for (const e of vis) { size.set(e.a, (size.get(e.a) ?? 0) + e.v); size.set(e.b, (size.get(e.b) ?? 0) + e.v) }
  const touched = new Set(vis.flatMap(e => [e.a, e.b]))
  const funds = f.nodes.filter(n => n.kind === 'fund' && (touched.has(n.id) || n.id === 'f:school'))
    .sort((a, b) => (a.id === 'f:school' ? -1 : b.id === 'f:school' ? 1 : 0)
      || FUND_ORDER.indexOf(a.group ?? '') - FUND_ORDER.indexOf(b.group ?? '') || (size.get(b.id) ?? 0) - (size.get(a.id) ?? 0))
  // a line the reader searched for is shown even with no arrow but the school budget's own
  const lines = f.nodes.filter(n => n.kind === 'line' && (everyLine || touched.has(n.id) || found.has(n.id)))
  const cats = new Map<string, Node[]>()
  for (const n of lines) { const c = n.cat ?? ''; if (!cats.has(c)) cats.set(c, []); cats.get(c)!.push(n) }
  const catSize = (ns: Node[]) => ns.reduce((a, n) => a + (size.get(n.id) ?? 0), 0)
  const order = [...cats.entries()].sort((a, b) => catSize(b[1]) - catSize(a[1]) || a[0].localeCompare(b[0]))
  const boxes = new Map<string, Box>(), heads: { y: number; label: string }[] = []
  let y = HEAD
  for (const n of funds) { boxes.set(n.id, { x: 0, y, w: FW, n }); y += RH + RG }
  const fundsH = y
  y = 0
  for (const [c, ns] of order) {
    heads.push({ y, label: c }); y += HEAD
    const key = (n: Node) => rank === 'sources' ? (stats.get(n.id)?.sources ?? 0) * 1e12 + (size.get(n.id) ?? 0)
      : rank === 'share' ? (stats.get(n.id)?.share ?? 0) * 1e12 + (size.get(n.id) ?? 0) : (size.get(n.id) ?? 0)
    ns.sort((a, b) => key(b) - key(a) || a.label.localeCompare(b.label))
    for (const n of ns) { boxes.set(n.id, { x: FW + GAPX, y, w: LW, n }); y += RH + RG }
    y += 10
  }
  const sinks = f.nodes.filter(n => n.kind === 'sink' && touched.has(n.id))
  if (sinks.length) { heads.push({ y, label: '' }); y += HEAD }
  for (const n of sinks) { boxes.set(n.id, { x: FW + GAPX, y, w: LW, n }); y += RH + RG }
  return { boxes, heads, edges: vis.filter(e => boxes.has(e.a) && boxes.has(e.b)), h: Math.max(fundsH, y) + 20, size }
}

export default function FyWeb({ data, alt }: CustomProps) {
  const d = data as Data
  const t = d.text
  const [fy] = useFyYear(d.years)
  const [file, setFile] = useState<File | null>(null)
  const [err, setErr] = useState(false)
  const [kinds, setKinds] = useState<Set<Kind>>(() => new Set(d.kinds.map(k => k.id).filter(k => k !== 'school')))
  // EVERY LINE BY DEFAULT (TJ, 28 October 2026: "i want to show them even if they are funded only
  // by the general fund. thats good info"); the chip narrows to the lines other funds touched
  const [everyLine, setEveryLine] = useState(true)
  const [hover, setHover] = useState<string | null>(null)
  const [pin, setPin] = useState<string | null>(null)
  useEffect(() => {
    let live = true
    setFile(null); setErr(false); setPin(null)
    load(fy).then(f => { if (live) setFile(f) }, () => { if (live) setErr(true) })
    return () => { live = false }
  }, [fy])
  const [rank, setRank] = useState<Rank>('size')
  const stats = useMemo(() => (file ? lineStats(file) : new Map<string, Stat>()), [file])
  // FIND A BLOCK (TJ, 28 October 2026: "why dont i see the athletic director line ... or
  // superintendent"): lines the general fund paid alone have no arrow but its own, which is off
  // by default, so they were not drawn. A search shows them, focuses the first, and moves to it
  const [q, setQ] = useState('')
  const found = useMemo(() => {
    const ql = q.trim().toLowerCase()
    return new Set(ql.length < 2 || !file ? [] : file.nodes.filter(n => n.label.toLowerCase().includes(ql)).map(n => n.id))
  }, [q, file])
  const L = useMemo(() => (file ? layout(file, kinds, everyLine, rank, stats, found) : null), [file, kinds, everyLine, rank, stats, found])
  const W = FW + GAPX + LW + 180

  // ---- the view: a viewBox moved by dragging and scaled by the buttons or ctrl + scroll
  const svg = useRef<SVGSVGElement>(null)
  const [vb, setVb] = useState({ x: -170, y: -10, w: W + 180, h: 900 })
  // FIT IS THE WHOLE WEB. The canvas takes the web's own shape (TJ, 28 October 2026: it was cut
  // off by a fixed height), so every block shows at once; zoom in to read, drag to move
  const fit = useCallback(() => { if (L) setVb({ x: -170, y: -10, w: W + 180, h: L.h + 20 }) }, [L, W])
  useEffect(() => { fit() }, [fit])
  const zoom = (k: number, cx?: number, cy?: number) => setVb(v => {
    const w = Math.min(Math.max(v.w * k, 200), W * 3), h = v.h * (w / v.w)
    const px = cx ?? v.x + v.w / 2, py = cy ?? v.y + v.h / 2
    return { x: px - (px - v.x) * (w / v.w), y: py - (py - v.y) * (w / v.w), w, h }
  })
  const drag = useRef<{ x: number; y: number; vx: number; vy: number; moved: boolean } | null>(null)
  const toView = (e: { clientX: number; clientY: number }) => {
    const r = svg.current!.getBoundingClientRect()
    return { x: vb.x + ((e.clientX - r.left) / r.width) * vb.w, y: vb.y + ((e.clientY - r.top) / r.height) * vb.h }
  }
  useEffect(() => {
    const el = svg.current
    if (!el) return
    const wheel = (e: WheelEvent) => {
      if (!e.ctrlKey && !e.metaKey) return   // a plain scroll scrolls the page
      e.preventDefault()
      const p = toView(e)
      zoom(e.deltaY > 0 ? 1.12 : 1 / 1.12, p.x, p.y)
    }
    el.addEventListener('wheel', wheel, { passive: false })
    return () => el.removeEventListener('wheel', wheel)
  })

  const go = () => {
    if (!L) return
    const first = [...found].map(id => L.boxes.get(id)).filter(Boolean).sort((a, b) => a!.y - b!.y)[0]
    if (!first) return
    setPin(first.n.id)
    setVb(v => ({ ...v, x: first.x + first.w / 2 - v.w / 2, y: first.y - v.h / 3 }))
  }
  useEffect(() => { if (found.size) go() }, [found])  // eslint-disable-line react-hooks/exhaustive-deps
  const active = pin ?? hover
  const near = useMemo(() => {
    if (!L || !active) return null
    const s = new Set([active])
    for (const e of L.edges) { if (e.a === active) s.add(e.b); if (e.b === active) s.add(e.a) }
    return s
  }, [L, active])
  const maxV = useMemo(() => Math.max(1, ...(L?.edges.filter(e => e.k !== 'school').map(e => e.v) ?? [1])), [L])
  const maxS = useMemo(() => Math.max(1, ...(L?.edges.filter(e => e.k === 'school').map(e => e.v) ?? [1])), [L])
  const width = (e: Edge) => (e.k === 'school' ? edgeWidth(e.v, maxS, true) : edgeWidth(e.v, maxV))

  const path = (e: Edge) => {
    const A = L!.boxes.get(e.a)!, B = L!.boxes.get(e.b)!
    const ay = A.y + RH / 2, by = B.y + RH / 2
    if (e.k === 'transfer') {
      // line to line, both in the right column: an arc out to the right
      const x = A.x + A.w, bulge = 40 + Math.min(120, Math.abs(by - ay) / 6)
      return `M${x},${ay} C${x + bulge},${ay} ${x + bulge},${by} ${x + 6},${by}`
    }
    if (e.k === 'fund') {
      // fund to fund, both in the left column: an arc out to the left
      const x = A.x, bulge = 40 + Math.min(120, Math.abs(by - ay) / 6)
      return `M${x},${ay} C${x - bulge},${ay} ${x - bulge},${by} ${x - 6},${by}`
    }
    if (e.k === 'back') {
      // from the line back to the fund
      return curve(A.x, ay, B.x + B.w + 6, by, -GAPX / 2)
    }
    return curve(A.x + A.w, ay, B.x - 6, by, GAPX / 2)
  }
  const toggle = (k: Kind) => setKinds(s => { const n = new Set(s); if (n.has(k)) n.delete(k); else n.add(k); return n })
  const label = (id: string) => file?.nodes.find(n => n.id === id)
  // every arrow the block has this year, drawn or not: a line the general fund paid alone still says so
  const list = active && file ? file.edges.filter(e => e.a === active || e.b === active).sort((x, y) => y.v - x.v) : []
  const only = !!active && list.length > 0 && list.every(e => e.k === 'school')
  const kindLabel = Object.fromEntries(d.kinds.map(k => [k.id, k.label]))
  // every line and fund has its own page (fy_items.py); the panel links to it
  const ix = useItemIndex()
  const hrefs = useMemo(() => itemHrefs(ix), [ix])
  const page = active ? hrefs.node(active) : undefined

  return (
    <figure aria-label={alt}>
      <div className="flex flex-wrap gap-1.5 items-center">
        {d.kinds.map(k => (
          <Chip key={k.id} on={kinds.has(k.id)} onClick={() => toggle(k.id)}>
            <span className="inline-block w-3 h-[3px] align-middle mr-1.5 rounded" style={{ background: COLOUR[k.id],
              ...(k.id === 'transfer' ? { background: `repeating-linear-gradient(90deg, ${COLOUR[k.id]} 0 3px, transparent 3px 5px)` } : {}) }} />
            <span title={k.means}>{k.label}</span></Chip>))}
        <Chip on={!everyLine} onClick={() => setEveryLine(v => !v)}>{t.only_touched}</Chip>
        <input value={q} onChange={e => setQ(e.target.value)} placeholder={t.find} aria-label={t.find}
          onKeyDown={e => { if (e.key === 'Enter') go() }}
          className="w-full sm:w-64 px-2 py-1 rounded border text-[13px]"
          style={{ borderColor: 'var(--grid)', background: 'var(--surface-1)', color: 'var(--text-primary)' }} />
        {q.trim().length >= 2 ? <span className="text-[12.5px]" style={muted}>{found.size} {t.found}</span> : null}
      </div>
      <div className="flex flex-wrap gap-1.5 items-center mt-2 text-[12.5px]">
        <span style={muted}>{t.rank}</span>
        <Chip on={rank === 'size'} onClick={() => setRank('size')}>{t.rank_size}</Chip>
        <Chip on={rank === 'sources'} onClick={() => setRank('sources')}>{t.rank_sources}</Chip>
        <Chip on={rank === 'share'} onClick={() => setRank('share')}>{t.rank_share}</Chip>
        <span className="ml-2 inline-flex items-center gap-1" style={muted}>
          <svg width="18" height="18" aria-hidden><circle cx="9" cy="9" r="8" fill="var(--thread-3)" /><text x="9" y="13" fontSize="10" textAnchor="middle" fill="#fff" fontWeight="700">3</text></svg>
          {t.key_many}</span>
        <span className="ml-2 inline-flex items-center gap-1" style={muted}>
          <span className="inline-block w-6 h-[5px] rounded-sm" style={{ background: 'var(--thread-2)' }} />{t.key_big}</span>
      </div>
      <div className="flex gap-2 items-center mt-2 text-[12.5px]" style={muted}>
        <button type="button" className="px-2 py-0.5 rounded border" style={{ borderColor: 'var(--grid)' }} onClick={() => zoom(1 / 1.3)} aria-label={t.zoom_in}>+</button>
        <button type="button" className="px-2 py-0.5 rounded border" style={{ borderColor: 'var(--grid)' }} onClick={() => zoom(1.3)} aria-label={t.zoom_out}>−</button>
        <button type="button" className="px-2 py-0.5 rounded border" style={{ borderColor: 'var(--grid)' }} onClick={fit}>{t.fit}</button>
        <span>{t.how}</span>
      </div>
      {err ? <p className="text-[13px] mt-3" style={muted}>{t.failed}</p> : !L ? <p className="text-[13px] mt-3" style={muted}>{t.loading}</p> : (
        <div className="mt-2 flex flex-col lg:flex-row gap-3 relative left-1/2 -translate-x-1/2 w-[calc(100vw-32px)] sm:w-[calc(100vw-96px)] lg:w-[calc(100vw-160px)] max-w-[1600px]">
          <svg ref={svg} preserveAspectRatio="xMinYMin meet" viewBox={`${vb.x} ${vb.y} ${vb.w} ${vb.h}`} className="w-full lg:flex-1 rounded border select-none touch-none"
            style={{ aspectRatio: `${W + 20} / ${(L?.h ?? 800) + 20}`, height: 'auto', borderColor: 'var(--grid)', background: 'var(--surface-1, var(--bg))', cursor: drag.current?.moved ? 'grabbing' : 'grab' }}
            onPointerDown={e => { (e.target as Element).setPointerCapture?.(e.pointerId); drag.current = { x: e.clientX, y: e.clientY, vx: vb.x, vy: vb.y, moved: false } }}
            onPointerMove={e => {
              const g = drag.current
              if (!g) return
              const r = svg.current!.getBoundingClientRect()
              const dx = ((e.clientX - g.x) / r.width) * vb.w, dy = ((e.clientY - g.y) / r.height) * vb.h
              if (Math.abs(e.clientX - g.x) + Math.abs(e.clientY - g.y) > 3) g.moved = true
              if (g.moved) setVb(v => ({ ...v, x: g.vx - dx, y: g.vy - dy }))
            }}
            onPointerUp={e => {
              const g = drag.current
              drag.current = null
              if (g && !g.moved && (e.target as Element).tagName === 'svg') setPin(null)
            }}>
            <WebMarkers prefix="fyw" />
            <text x={0} y={14} fontSize={12} fontWeight={600} fill="var(--text-secondary)">{t.col_funds}</text>
            {L.heads.map((h, i) => (
              <text key={i} x={FW + GAPX} y={h.y + 16} fontSize={12} fontWeight={600} fill="var(--text-secondary)">{h.label || t.col_sinks}</text>))}
            <g fill="none">
              {L.edges.map((e, i) => {
                const on = !near || e.a === active || e.b === active
                return (
                  <path key={i} d={path(e)} stroke={COLOUR[e.k]} strokeWidth={width(e)} strokeOpacity={on ? (near ? 0.85 : e.k === 'school' ? 0.35 : 0.5) : 0.05}
                    strokeDasharray={e.k === 'transfer' ? '5 4' : undefined} markerEnd={on ? `url(#fyw-${e.k})` : undefined}
                    onPointerEnter={() => setHover(null)}>
                    <title>{`${label(e.a)?.label} → ${label(e.b)?.label}\n${kindLabel[e.k]}: ${e.t}${e.d ? `\n${e.d} · ${e.m ?? ''}` : ''}`}</title>
                  </path>)
              })}
            </g>
            {[...L.boxes.values()].map(b => {
              const on = !near || near.has(b.n.id), me = active === b.n.id
              const fund = b.n.kind === 'fund'
              return (
                <g key={b.n.id} transform={`translate(${b.x},${b.y})`} opacity={on ? 1 : 0.25} className="cursor-pointer"
                  onPointerEnter={() => setHover(b.n.id)} onPointerLeave={() => setHover(h => (h === b.n.id ? null : h))}
                  onPointerUp={e => { if (!drag.current?.moved) { e.stopPropagation(); setPin(p => (p === b.n.id ? null : b.n.id)) } }}>
                  {(() => {
                    const st = b.n.kind === 'line' ? stats.get(b.n.id) : undefined
                    const many = !!st && st.sources >= MANY, big = !!st && st.share >= BIG
                    return (<>
                      <rect width={b.w} height={RH} rx={4} fill={fund ? 'var(--surface-1, var(--bg))' : nodeFill(b.n)}
                        stroke={me ? 'var(--text-primary)' : fund ? nodeFill(b.n) : many || big ? 'var(--text-secondary)' : 'var(--grid)'}
                        strokeWidth={me ? 2 : many || big ? 1.5 : 1} />
                      {st && st.share > 0.005 ? (
                        <rect x={1} y={RH - (big ? 5 : 3)} width={Math.max(2, (b.w - 2) * Math.min(1, st.share))} height={big ? 4 : 2} rx={1}
                          fill="var(--thread-2)" opacity={big ? 1 : 0.55} />) : null}
                      {b.n.kind === 'line' && !b.n.id.startsWith('k:') && (!st || st.sources === 0) ? (
                        <text x={b.w - 8} y={16} fontSize={10.5} textAnchor="end" fill="var(--text-muted)">{t.gf_only}</text>) : null}
                      {st && st.sources > 0 ? (<>
                        {st.share > 0.005 ? <text x={b.w - 28} y={16} fontSize={11} textAnchor="end" fontWeight={big ? 700 : 400}
                          fill={big ? 'var(--thread-2)' : 'var(--text-muted)'}>{Math.round(st.share * 100)}%</text> : null}
                        <circle cx={b.w - 13} cy={RH / 2} r={8.5} fill={many ? 'var(--thread-3)' : 'var(--surface-1, var(--bg))'}
                          stroke={many ? 'var(--thread-3)' : 'var(--text-muted)'} strokeWidth={1} />
                        <text x={b.w - 13} y={RH / 2 + 3.5} fontSize={10} textAnchor="middle" fontWeight={700}
                          fill={many ? '#fff' : 'var(--text-secondary)'}>{st.sources}</text>
                      </>) : null}
                    </>)
                  })()}
                  {fund ? <rect width={6} height={RH} rx={2} fill={nodeFill(b.n)} /> : null}
                  <text x={fund ? 12 : 8} y={16} fontSize={12} fill="var(--text-primary)">{cut(b.n.label, fund ? 38 : stats.get(b.n.id)?.sources ? 33 : 30)}</text>
                  <title>{`${b.n.label}${b.n.sub ? ` · ${b.n.sub}` : ''}`}</title>
                </g>)
            })}
          </svg>
          <aside className="lg:w-[22rem] shrink-0 text-[13px] lg:sticky lg:top-20 lg:self-start">
            {active ? (
              <div className="rounded border p-3" style={{ borderColor: 'var(--grid)' }}>
                <p className="text-[12px] uppercase tracking-wide" style={muted}>{label(active)?.kind === 'fund' ? t.a_fund : label(active)?.kind === 'sink' ? t.a_sink : t.a_line}</p>
                <p className="font-semibold leading-snug">{label(active)?.label}</p>
                {label(active)?.sub ? <p className="text-[11.5px]" style={muted}>{label(active)?.sub}</p> : null}
                {page && ix ? <a href={withYear(page, fy)} className="inline-block mt-1 text-[12.5px] underline" style={{ color: 'var(--link, var(--thread-2))' }}>{ix.text.web_open} →</a> : null}
                {label(active)?.kind === 'line' && stats.get(active) ? (
                  <p className="text-[12.5px] mt-1" style={secondary}>{stats.get(active)!.sources} {t.st_sources} · {Math.round(stats.get(active)!.share * 100)}% {t.st_share}</p>) : null}
                {only ? <p className="text-[12.5px] mt-1 font-semibold">{t.only_gf}</p> : null}
                <ul className="mt-2 space-y-1.5 max-h-[60vh] overflow-y-auto">
                  {list.map((e, i) => {
                    const other = e.a === active ? e.b : e.a, out = e.a === active
                    return (
                      <li key={i}>
                        <button type="button" className="w-full text-left flex justify-between gap-2" onClick={() => setPin(other)}>
                          <span><span className="inline-block w-2 h-2 rounded-sm mr-1.5" style={{ background: COLOUR[e.k] }} />
                            <span style={muted}>{out ? '→' : '←'}</span> <span className="underline decoration-dotted underline-offset-2">{label(other)?.label}</span>
                            <span className="block text-[11.5px] pl-3.5" style={muted}>{kindLabel[e.k]}{e.d ? ` · ${e.d}` : ''}</span></span>
                          <span className="tabular-nums font-semibold whitespace-nowrap">{e.t}</span>
                        </button>
                      </li>)
                  })}
                </ul>
                {pin ? <button type="button" className="mt-2 text-[12.5px] underline" style={secondary} onClick={() => setPin(null)}>{t.clear}</button> : null}
              </div>
            ) : <p style={muted}>{t.pick}</p>}
          </aside>
        </div>)}
    </figure>)
}

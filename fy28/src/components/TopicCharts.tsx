/** THE INLINE CHART: every topic's signature, drawn from a spec its generator wrote in a few
 *  lines of Python (scripts/topic.py: series, ranking, parts, image). One component for all
 *  of them, so a chart costs a category agent no React and every chart reads as one system.
 *
 *  TJ, 13 October 2026: "Every topic page should have some defining chart OR image if the
 *  data doesnt represent well by a chart." CLAUDE.md 7f: a chart is a COMPONENT rendered
 *  from the payload, never an image of one -- and the image kind here is for a document or
 *  a diagram, not for a picture of numbers.
 *
 *  Nothing here computes or words a figure (rule 2): values arrive as numbers and are only
 *  FORMATTED, by the unit the generator declared.
 *
 *  WHAT KIND A NUMBER IS (rule 3) is drawn, never colour alone: an estimate is dashed and
 *  carries the amber edge the fact tiles use, and says "our estimate"; a figure somebody
 *  assembled by hand (13a) is lighter and says "not from the books".
 *
 *  COLOUR. Tracks take --thread-1..5 IN ORDER -- the one categorical set validated in both
 *  modes for lightness, chroma and colour-blind separation (index.css says why the order is
 *  part of the validation). A ranking's highlighted row takes --thread-1 and the rest
 *  --axis, so the row the page is about is the only coloured thing.
 *
 *  A PHONE. Rankings and parts are drawn in HTML, labels above bars and values printed, so
 *  they reflow to any width and need no hover; the series chart is recharts in a
 *  ResponsiveContainer. Nothing here sets a width wider than its column. */
import {
  Bar, CartesianGrid, ComposedChart, Line, ReferenceLine, ResponsiveContainer, Tooltip, XAxis,
  YAxis,
} from 'recharts'
import { usdShort } from '../model/engine'
import { abs } from '../lib/abs'

type Unit = { text: string }
type Basis = 'published' | 'stated' | 'estimate'
export type SeriesChart = {
  type: 'series'; title: string; unit: string; kind: 'line' | 'bar'; stacked: boolean
  x: string[]
  series: { name: string; values: (number | null)[]; texts: (string | null)[]; basis: Basis; mark: 'line' | 'bar'
    /** Palette place, when it must match another chart of the same things. */
    colour?: number
    /** Small multiples only: first value to last, written by the generator. */
    change?: string }[]
  note: Unit | null
  reference?: { value: number; label: string; text: string } | null
  from_zero?: boolean
  /** Small multiples: one panel per track, all on one scale from zero (scripts/topic.py). */
  multiples?: boolean
}
export type RankingChart = {
  type: 'ranking'; title: string; unit: string; basis: Basis; stack: string[] | null
  rows: { label: string; value?: number | null; values?: (number | null)[]; texts: (string | null)[]; total: string | null }[]
  highlight: string[]; note: Unit | null
}
export type PartsChart = {
  type: 'parts'; title: string; unit: string; basis: Basis
  parts: { label: string; value: number; text: string; share: string }[]; total: string; note: Unit | null
}
export type ImageChart = { type: 'image'; src: string; alt: string; caption: Unit }
export type InlineChart = SeriesChart | RankingChart | PartsChart | ImageChart

export const isInline = (c: unknown): c is InlineChart =>
  !!c && typeof c === 'object' && 'type' in (c as Record<string, unknown>)

const COLOURS = [1, 2, 3, 4, 5].map(i => `var(--thread-${i})`)
const BASIS_TAG: Record<Basis, string | null> = {
  published: null, stated: 'not from the books', estimate: 'our estimate',
}

/** EVERY VALUE A READER SEES IS A STRING THE GENERATOR WROTE (topic.fmt, the same
 *  formatters as the prose), so a bar and the sentence beside it cannot round one figure two
 *  ways. Only an axis TICK is formatted here, because a tick is a scale, not a figure. */
const shown = (t: string | null | undefined) => t ?? 'not published'
function tick(unit: string, v: number): string {
  // Below $10k a tick keeps one decimal, or $1,500 and $2,000 both read "$2k".
  // Below $1,000 it is whole dollars: a fee axis read "$0.3k, $0.3k, $0.2k".
  if (unit === '$') return Math.abs(v) >= 1e4 || v === 0 ? usdShort(v)
    : Math.abs(v) < 1e3 ? `${v < 0 ? '-' : ''}$${Math.round(Math.abs(v)).toLocaleString('en-US')}`
    : `${v < 0 ? '-' : ''}$${(Math.abs(v) / 1e3).toFixed(Math.abs(v) % 1e3 ? 1 : 0)}k`
  if (unit === '%') return `${v}%`
  return v.toLocaleString('en-US', { maximumFractionDigits: 1 })
}

const unitWord = (u: string) =>
  u === '$' ? 'dollars' : u === '%' ? 'percent' : u === 'count' ? 'a count' : u

function Frame({ title, basis, note, label, children }: {
  title: string; basis?: Basis; note: Unit | null; label: string; children: React.ReactNode
}) {
  const tag = basis ? BASIS_TAG[basis] : null
  return (
    <figure className="card p-4 mt-5 max-w-3xl min-w-0" aria-label={label}>
      <figcaption className="flex flex-wrap items-baseline gap-x-3 gap-y-0.5 mb-3">
        <span className="text-[14.5px] font-semibold" style={{ color: 'var(--text-primary)' }}>{title}</span>
        {tag ? <span className="text-[10px] font-semibold uppercase tracking-widest"
          style={{ color: 'var(--text-muted)' }}>{tag}</span> : null}
      </figcaption>
      {children}
      {note ? <p className="text-[12.5px] leading-snug mt-3" style={{ color: 'var(--text-muted)' }}>
        {note.text}</p> : null}
    </figure>
  )
}

/** A legend chip that draws the mark as the chart does: dashed for an estimate. The estimate
 *  colour goes on the TAG, not as the left rule the stat tiles use: on a card that rule is an
 *  edge, on a 12px inline chip it read as a stray orange bar (TJ, 19 October 2026). */
function Key({ colour, name, basis, mark, tag = true }: {
  colour: string; name: string; basis: Basis; mark: 'line' | 'bar'; tag?: boolean
}) {
  const est = basis === 'estimate'
  return (
    <span className="inline-flex items-center gap-1.5 text-[12px]"
      style={{ color: 'var(--text-secondary)' }}>
      {mark === 'line'
        ? <svg width="18" height="8" aria-hidden><line x1="1" y1="4" x2="17" y2="4" stroke={colour}
            strokeWidth="2.5" strokeDasharray={est ? '4 3' : undefined} /></svg>
        : <span className="inline-block w-2.5 h-2.5 rounded-[2px]" style={{
            background: est ? 'transparent' : colour, opacity: basis === 'stated' ? 0.6 : 1,
            border: est ? `1.5px dashed ${colour}` : undefined }} />}
      {name}
      {tag && BASIS_TAG[basis] ? <span className="text-[10px] uppercase tracking-wider"
        style={{ color: est ? 'var(--status-warning)' : 'var(--text-muted)' }}>{BASIS_TAG[basis]}</span> : null}
    </span>
  )
}

/* ------------------------------------------------------------------- series */

type TipProps = { active?: boolean; label?: string; c: SeriesChart; row?: Record<string, number | null>
  /** A small-multiples panel passes one track; this is its colour's place in the set. */
  offset?: number }

function SeriesTip({ active, label, c, payload, offset = 0 }: TipProps & { payload?: { payload: Record<string, number | null> }[] }) {
  if (!active || !payload?.length) return null
  const row = payload[0].payload
  const at = c.x.indexOf(String(label))
  return (
    <div className="rounded-lg px-3 py-2 text-[12px] shadow-lg"
      style={{ background: 'var(--surface-1)', border: '1px solid var(--grid)' }}>
      <p className="font-semibold mb-1" style={{ color: 'var(--text-secondary)' }}>{label}</p>
      {c.series.map((s, i) => row[`s${i}`] === undefined ? null : (
        <p key={s.name} className="flex items-center justify-between gap-5 tnum">
          <span className="inline-flex items-center gap-1.5" style={{ color: 'var(--text-secondary)' }}>
            <span className="inline-block w-2.5 h-2.5 rounded-[2px]" style={{ background: COLOURS[(i + offset) % COLOURS.length] }} />
            {s.name}{BASIS_TAG[s.basis] ? ` (${BASIS_TAG[s.basis]})` : ''}</span>
          <span className="font-semibold" style={{ color: row[`s${i}`] == null ? 'var(--text-muted)' : undefined }}>
            {shown(s.texts[at])}</span>
        </p>
      ))}
    </div>
  )
}

function seriesLabel(c: SeriesChart) {
  const span = `${c.x[0]} to ${c.x[c.x.length - 1]}`
  const each = c.series.map(s => {
    const pts = s.texts.map((t, i) => [c.x[i], t] as const).filter(([, t]) => t != null)
    const first = pts[0], last = pts[pts.length - 1]
    return `${s.name}${BASIS_TAG[s.basis] ? `, ${BASIS_TAG[s.basis]}` : ''}: ${first[1]} in ${first[0]}`
      + (pts.length > 1 ? `, ${last[1]} in ${last[0]}` : '')
  })
  return `${c.title}. Chart in ${unitWord(c.unit)}, ${span}. ${each.join('; ')}.`
}

/** SMALL MULTIPLES. One panel per track, every panel on ONE scale from zero -- so each
 *  track's own change reads as its own slope, and a big track still looks big beside a small
 *  one. A stack cannot do the first: only its bottom band sits on a flat baseline. Each
 *  panel prints its first and last value, so the change is readable without hovering. */
function Multiples({ c }: { c: SeriesChart }) {
  const max = Math.max(0, ...c.series.flatMap(s => s.values).filter((v): v is number => v != null))
  // The shared scale tops out on a round number with a round midpoint ($12M, not $11.27M).
  const mag = max > 0 ? Math.pow(10, Math.floor(Math.log10(max)) - 1) : 1
  const top = ([2, 4, 6, 8, 10, 12, 15, 20, 30, 40, 60, 80, 100].find(m => m * mag >= max) ?? 100) * mag
  const common = c.series.every(s => s.basis === c.series[0].basis) ? c.series[0].basis : undefined
  return (
    <Frame title={c.title} basis={common} note={c.note} label={seriesLabel(c)}>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-5 gap-y-4">
        {c.series.map((s, i) => {
          const pts = s.texts.map((t, k) => [c.x[k], t] as const).filter(([, t]) => t != null)
          const first = pts[0], last = pts[pts.length - 1]
          const est = s.basis === 'estimate'
          const rows = c.x.map((x, k) => ({ x, s0: s.values[k] }))
          const col = COLOURS[(s.colour ?? i) % COLOURS.length]
          return (
            <div key={s.name} className="min-w-0">
              <p className="text-[12.5px] font-semibold leading-snug flex items-center gap-1.5"
                style={{ color: 'var(--text-primary)' }}>
                <span className="inline-block w-2.5 h-2.5 rounded-[2px] shrink-0" style={{ background: col }} />
                {s.name}</p>
              {s.change ? <p className="text-[17px] font-bold tnum leading-tight mt-1" style={{ color: col }}>
                {s.change} <span className="text-[12px] font-medium" style={{ color: 'var(--text-secondary)' }}>
                  added since {c.x[0]}</span></p> : null}
              <p className="text-[11.5px] tnum mt-0.5" style={{ color: 'var(--text-secondary)' }}>
                {first[1]} in {first[0]} &rarr; {last[1]} in {last[0]}</p>
              <div style={{ height: 110 }} aria-hidden>
                <ResponsiveContainer width="100%" height="100%">
                  <ComposedChart data={rows} margin={{ top: 6, right: 26, bottom: 0, left: 0 }}>
                    <CartesianGrid stroke="var(--grid)" vertical={false} />
                    <XAxis dataKey="x" ticks={[c.x[0], c.x[c.x.length - 1]]} interval={0}
                      tick={{ fill: 'var(--text-muted)', fontSize: 10 }} stroke="var(--axis)" tickLine={false} />
                    <YAxis width={c.unit === '$' ? 50 : 40} domain={[0, top]} ticks={[0, top / 2, top]}
                      tick={{ fill: 'var(--text-muted)', fontSize: 10 }} stroke="var(--axis)"
                      tickLine={false} axisLine={false} tickFormatter={(v: number) => tick(c.unit, v)} />
                    <Tooltip content={<SeriesTip c={{ ...c, series: [s] }} offset={s.colour ?? i} />}
                      cursor={{ fill: 'var(--surface-3)', opacity: 0.5 }} />
                    {s.mark === 'bar' ? (
                      <Bar dataKey="s0" fill={col} isAnimationActive={false}
                        fillOpacity={est ? 0.15 : s.basis === 'stated' ? 0.6 : 1} radius={[2, 2, 0, 0]} />
                    ) : (
                      <Line dataKey="s0" stroke={col} strokeWidth={2}
                        strokeDasharray={est ? '6 4' : undefined} dot={false} connectNulls={false}
                        isAnimationActive={false} type="linear" />
                    )}
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
            </div>
          )
        })}
      </div>
      <SrTable head={['', ...c.series.map(s => s.name)]}
        rows={c.x.map((x, i) => [x, ...c.series.map(s => shown(s.texts[i]))])} />
    </Frame>
  )
}

function Series({ c }: { c: SeriesChart }) {
  if (c.multiples) return <Multiples c={c} />
  const rows = c.x.map((x, i) => Object.fromEntries([['x', x],
    ...c.series.map((s, j) => [`s${j}`, s.values[i]] as const)]))
  const negative = c.series.some(s => s.values.some(v => v != null && v < 0))
  // An axis that need not start at zero still starts on a round number, and takes in the
  // reference line, so "the minimum" is never off the bottom of its own chart.
  const domain = (() => {
    if (c.from_zero !== false) return undefined
    const all = c.series.flatMap(s => s.values).filter((v): v is number => v != null)
      .concat(c.reference ? [c.reference.value] : [])
    const lo = Math.min(...all), hi = Math.max(...all)
    const step = Math.pow(10, Math.floor(Math.log10(Math.max(hi - lo, 1)))) / 2
    const a = Math.floor((lo - step / 2) / step) * step, z = Math.ceil((hi + step / 2) / step) * step
    const every = (z - a) / step > 6 ? step * 2 : step
    const ticks: number[] = []
    for (let t = Math.ceil(a / every) * every; t <= z; t += every) ticks.push(t)
    return { range: [a, z] as [number, number], ticks }
  })()
  // One kind across every track is said once, beside the title, not on every key.
  const common = c.series.every(s => s.basis === c.series[0].basis) ? c.series[0].basis : undefined
  return (
    <Frame title={c.title} basis={common} note={c.note} label={seriesLabel(c)}>
      {c.series.length > 1 ? (
        <div className="flex flex-wrap gap-x-4 gap-y-1 mb-2">
          {c.series.map((s, i) => <Key key={s.name} colour={COLOURS[i]} name={s.name} basis={s.basis}
            mark={s.mark} tag={!common} />)}
        </div>
      ) : null}
      <div style={{ height: 260 }} aria-hidden>
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={rows} margin={{ top: 6, right: 22, bottom: 0, left: 0 }} barGap={2}>
            <CartesianGrid stroke="var(--grid)" vertical={false} />
            <XAxis dataKey="x" interval={c.x.length <= 12 ? 0 : 'preserveStartEnd'} minTickGap={c.x.length <= 12 ? 2 : 14}
              tick={{ fill: 'var(--text-muted)', fontSize: 11 }} stroke="var(--axis)" tickLine={false} />
            <YAxis width={c.unit === '$' ? 54 : 44}
              domain={domain?.range} ticks={domain?.ticks} tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
              stroke="var(--axis)" tickLine={false} axisLine={false}
              tickFormatter={(v: number) => tick(c.unit, v)} />
            {negative ? <ReferenceLine y={0} stroke="var(--axis)" /> : null}
            {c.reference ? (
              <ReferenceLine y={c.reference.value} stroke="var(--text-muted)" strokeDasharray="2 3"
                label={{ value: `${c.reference.label}, ${c.reference.text}`, position: 'insideBottomRight',
                  fill: 'var(--text-muted)', fontSize: 11 }} />
            ) : null}
            <Tooltip content={<SeriesTip c={c} />} cursor={{ fill: 'var(--surface-3)', opacity: 0.5 }} />
            {c.series.map((s, i) => {
              const est = s.basis === 'estimate'
              return s.mark === 'bar' ? (
                <Bar key={s.name} dataKey={`s${i}`} name={s.name} fill={COLOURS[i]} isAnimationActive={false}
                  stackId={c.stacked ? 'stack' : undefined}
                  fillOpacity={est ? 0.15 : s.basis === 'stated' ? 0.6 : 1}
                  stroke={est ? COLOURS[i] : undefined} strokeDasharray={est ? '4 3' : undefined}
                  radius={c.stacked ? undefined : [3, 3, 0, 0]}
                  /* A ZERO IS NOT A GAP. A bar of zero would draw nothing, exactly as a year
                     nobody printed does; a two-pixel stub tells them apart. Stacks skip it,
                     because a stacked track is empty by design where another stands. */
                  minPointSize={c.stacked ? undefined : 2} />
              ) : (
                <Line key={s.name} dataKey={`s${i}`} name={s.name} stroke={COLOURS[i]} strokeWidth={2.25}
                  strokeDasharray={est ? '6 4' : undefined} dot={c.x.length <= 12 ? { r: 2.5 } : false}
                  connectNulls={false} isAnimationActive={false} type="linear" />
              )
            })}
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      <SrTable head={['', ...c.series.map(s => s.name)]}
        rows={c.x.map((x, i) => [x, ...c.series.map(s => shown(s.texts[i]))])} />
    </Frame>
  )
}

/** The numbers for a screen reader, which cannot hover a chart. */
function SrTable({ head, rows }: { head: string[]; rows: string[][] }) {
  return (
    // The wrapper is sr-only, not the table: a table ignores width:1px and grows to its
    // content, which made a 400px page scroll sideways.
    <div className="sr-only"><table>
      <thead><tr>{head.map((h, i) => <th key={i}>{h}</th>)}</tr></thead>
      <tbody>{rows.map((r, i) => <tr key={i}>{r.map((v, j) => <td key={j}>{v}</td>)}</tr>)}</tbody>
    </table></div>
  )
}

/* ------------------------------------------------------------------- ranking */

function Ranking({ c }: { c: RankingChart }) {
  const vals = (r: RankingChart['rows'][number]) => (c.stack ? r.values ?? [] : [r.value ?? null])
  const total = (r: RankingChart['rows'][number]) => vals(r).reduce<number>((a, v) => a + (v ?? 0), 0)
  const max = Math.max(...c.rows.map(r => Math.abs(total(r))), 1)
  const est = c.basis === 'estimate'
  const diverging = !c.stack && c.rows.some(r => (r.value ?? 0) < 0)
  const lo = Math.max(0, ...c.rows.map(r => -(r.value ?? 0)))
  const hi = Math.max(0, ...c.rows.map(r => r.value ?? 0))
  const span = Math.max(lo + hi, 1)
  const zero = (100 * lo) / span
  const label = `${c.title}. Ranked, in ${unitWord(c.unit)}. `
    + c.rows.map(r => `${r.label}${c.highlight.includes(r.label) ? ' (highlighted)' : ''}: ${shown(r.total)}`).join('; ') + '.'
  return (
    <Frame title={c.title} basis={c.basis} note={c.note} label={label}>
      {c.stack ? (
        <div className="flex flex-wrap gap-x-4 gap-y-1 mb-3">
          {c.stack.map((s, i) => <Key key={s} colour={COLOURS[i]} name={s} basis={c.basis} mark="bar" />)}
        </div>
      ) : null}
      <ol className="space-y-2" aria-hidden>
        {c.rows.map(r => {
          const hl = c.highlight.includes(r.label)
          const none = vals(r).every(v => v == null)
          return (
            <li key={r.label} title={c.stack ? c.stack.map((s, i) => `${s}: ${shown(r.texts[i])}`).join(' · ') : undefined}>
              <div className="flex items-baseline justify-between gap-3 text-[13px] leading-tight">
                <span className="min-w-0 break-words" style={{ color: hl ? 'var(--text-primary)' : 'var(--text-secondary)',
                  fontWeight: hl ? 600 : 400 }}>{r.label}</span>
                <span className="tnum shrink-0" style={{ color: none ? 'var(--text-muted)' : 'var(--text-primary)',
                  fontWeight: hl ? 600 : 500 }}>{shown(r.total)}</span>
              </div>
              {diverging ? (() => {
                /* A FALL IS A BAR TOO. Without this a negative row drew an empty track and
                   read as "not published"; the zero line sits where the largest fall ends. */
                const v = r.value ?? null
                const w = v == null ? 0 : (100 * Math.abs(v)) / span
                return (
                  <div className="mt-1 h-2.5 rounded-[2px] relative overflow-hidden" style={{ background: 'var(--surface-3)' }}>
                    <span className="absolute top-0 bottom-0" style={{ left: `${zero}%`, width: 1, background: 'var(--axis)' }} />
                    {v == null || v === 0 ? null : (
                      <span className="absolute top-0 bottom-0" style={{
                        left: v < 0 ? `${zero - w}%` : `${zero}%`, width: `${w}%`,
                        background: est ? 'transparent' : hl || !c.highlight.length ? COLOURS[v < 0 ? 1 : 0] : 'var(--axis)',
                        opacity: c.basis === 'stated' ? 0.65 : 1,
                        border: est ? `1.5px dashed ${COLOURS[v < 0 ? 1 : 0]}` : undefined,
                      }} />
                    )}
                  </div>
                )
              })() : (
              <div className="mt-1 h-2.5 rounded-[2px] flex overflow-hidden" style={{ background: 'var(--surface-3)' }}>
                {vals(r).map((v, i) => v == null || v <= 0 ? null : (
                  <span key={i} style={{
                    width: `${(100 * v) / max}%`,
                    background: est ? 'transparent' : c.stack ? COLOURS[i] : hl || !c.highlight.length ? COLOURS[0] : 'var(--axis)',
                    opacity: c.basis === 'stated' ? 0.65 : c.stack && c.highlight.length && !hl ? 0.45 : 1,
                    border: est ? `1.5px dashed ${COLOURS[c.stack ? i : 0]}` : undefined,
                  }} />
                ))}
              </div>
              )}
            </li>
          )
        })}
      </ol>
      <SrTable head={['', ...(c.stack ?? ['Value'])]}
        rows={c.rows.map(r => [r.label, ...r.texts.map(shown)])} />
    </Frame>
  )
}

/* ------------------------------------------------------------------- parts */

function Parts({ c }: { c: PartsChart }) {
  const sum = c.parts.reduce((a, p) => a + p.value, 0)
  const est = c.basis === 'estimate'
  const label = `${c.title}. One whole of ${c.total}, in parts: `
    + c.parts.map(p => `${p.label}, ${p.text} (${p.share})`).join('; ') + '.'
  return (
    <Frame title={c.title} basis={c.basis} note={c.note} label={label}>
      <div className="h-7 rounded-[3px] flex overflow-hidden gap-[2px]" aria-hidden>
        {c.parts.map((p, i) => (
          <span key={p.label} title={`${p.label}: ${p.text} (${p.share})`}
            style={{ width: `${(100 * p.value) / sum}%`, background: est ? `color-mix(in srgb, ${COLOURS[i]} 22%, transparent)` : COLOURS[i],
              opacity: c.basis === 'stated' ? 0.65 : 1, border: est ? `1.5px dashed ${COLOURS[i]}` : undefined }} />
        ))}
      </div>
      <ul className="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-1.5" aria-hidden>
        {c.parts.map((p, i) => (
          <li key={p.label} className="flex items-baseline justify-between gap-3 text-[13px]">
            <span className="inline-flex items-baseline gap-1.5 min-w-0" style={{ color: 'var(--text-secondary)' }}>
              <span className="inline-block w-2.5 h-2.5 rounded-[2px] shrink-0 translate-y-[1px]"
                style={{ background: COLOURS[i] }} />
              <span className="break-words">{p.label}</span></span>
            <span className="tnum shrink-0"><span className="font-semibold">{p.text}</span>
              <span style={{ color: 'var(--text-muted)' }}> · {p.share}</span></span>
          </li>
        ))}
      </ul>
    </Frame>
  )
}

/* ------------------------------------------------------------------- image */

function Picture({ c }: { c: ImageChart }) {
  return (
    <figure className="card p-3 mt-5 max-w-3xl min-w-0">
      <a href={abs(c.src)} className="block">
        <img src={abs(c.src)} alt={c.alt} loading="lazy" className="block w-full h-auto rounded"
          style={{ border: '1px solid var(--grid)' }} />
      </a>
      <figcaption className="text-[12.5px] leading-snug mt-2" style={{ color: 'var(--text-muted)' }}>
        {c.caption.text}</figcaption>
    </figure>
  )
}

export function InlineTopicChart({ c }: { c: InlineChart }) {
  switch (c.type) {
    case 'series': return <Series c={c} />
    case 'ranking': return <Ranking c={c} />
    case 'parts': return <Parts c={c} />
    case 'image': return <Picture c={c} />
    default: return null
  }
}

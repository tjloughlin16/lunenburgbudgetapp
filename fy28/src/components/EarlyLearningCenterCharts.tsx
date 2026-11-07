import {
  Bar, BarChart, CartesianGrid, ComposedChart, Legend, Line, ReferenceLine,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import type { ChartProps } from './analysisCharts'

/* The charts for /analysis/early-learning-center, drawn from /data/early-learning-center.json,
 * which scripts/build_early_learning_center.py writes in the same pass as the markdown. Rule
 * 7f: the SVGs beside the markdown stay for /docs and the PDF; the web page draws these.
 *
 * Nothing here computes a figure (rule 2): every amount arrives in the payload. The one
 * thing done here is the gap: a year our reading of the annual reports does not hold is
 * shown as a gap, never interpolated, so the balance line breaks rather than inventing a
 * path through FY2011-FY2013. */

const N = (v: unknown) => (Array.isArray(v) ? Number(v[0]) : Number(v))
const box = {
  background: 'var(--surface-1)', border: '1px solid var(--grid)',
  borderRadius: 8, fontSize: 12.5, color: 'var(--text-primary)',
  boxShadow: '0 2px 10px rgba(0,0,0,.12)', opacity: 1,
}
const usd = (v: number) => (v < 0 ? '-$' : '$') + Math.abs(Math.round(v)).toLocaleString()
const usdk = (v: number) =>
  Math.abs(v) >= 1e6 ? `${v < 0 ? '-' : ''}$${(Math.abs(v) / 1e6).toFixed(1)}M`
    : Math.abs(v) >= 1e3 ? `${v < 0 ? '-' : ''}$${Math.round(Math.abs(v) / 1e3)}k`
      : `${v < 0 ? '-' : ''}$${Math.round(Math.abs(v))}`
const tick = { fontSize: 10.5, fill: 'var(--text-muted)' }

const TAG_COLOR: Record<string, string> = {
  place: '#2b6cb0', run: '#7c3aed', handbook: '#0f766e', rates: '#b45309',
  distinct: '#be185d', money: '#15803d',
}
const C_IN = '#2b6cb0'
const C_OUT = '#dc2626'
const C_BAL = 'var(--text-primary)'
const C_ELC = '#be185d'
const C_REST = '#94a3b8'

type Event = { date: string; body: string; what: string; tag: string; url: string }
type Tag = { tag: string; label: string }
type FundYr = { fy: number; opening: number; received: number; spent: number; closing: number;
  source: string }
type FeeYr = { fy: number; elc: number; rest: number; all: number }
type Payload = { timeline: Event[]; timeline_tags: Tag[]; fund_series: FundYr[];
  fees_by_year: FeeYr[] }

/** THE SIGNATURE: every dated document that names the ELC, one dot each, coloured by what
 *  it records. Each entry links to the town's copy of the document. */
export function EarlyLearningCenterTimeline({ data }: ChartProps) {
  const p = data as Payload
  const used = new Set(p.timeline.map(e => e.tag))
  return (
    <div style={{ width: '100%' }}>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px 16px', fontSize: 12,
        color: 'var(--text-muted)', marginBottom: 12 }}>
        {p.timeline_tags.filter(t => used.has(t.tag)).map(t => (
          <span key={t.tag} style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
            <span style={{ width: 10, height: 10, borderRadius: 5, background: TAG_COLOR[t.tag] }} />
            {t.label}
          </span>
        ))}
      </div>
      <ol style={{ listStyle: 'none', margin: 0, padding: 0, position: 'relative' }}>
        <span aria-hidden style={{ position: 'absolute', left: 97, top: 6, bottom: 6, width: 2,
          background: 'var(--grid)' }} />
        {p.timeline.map((e, i) => (
          <li key={i} style={{ display: 'grid', gridTemplateColumns: '84px 28px 1fr',
            alignItems: 'start', padding: '5px 0' }}>
            <span style={{ fontSize: 12, color: 'var(--text-muted)', textAlign: 'right',
              fontVariantNumeric: 'tabular-nums', paddingTop: 1 }}>{e.date}</span>
            <span style={{ display: 'flex', justifyContent: 'center', paddingTop: 3 }}>
              <span title={p.timeline_tags.find(t => t.tag === e.tag)?.label}
                style={{ width: 12, height: 12, borderRadius: 6, background: TAG_COLOR[e.tag],
                  position: 'relative', zIndex: 1, boxShadow: '0 0 0 3px var(--surface-1)' }} />
            </span>
            <span style={{ fontSize: 13.5, lineHeight: 1.4 }}>
              <a href={e.url} target="_blank" rel="noreferrer"
                style={{ fontWeight: 650, color: 'var(--text-primary)' }}>{e.body}</a>
              <span style={{ display: 'block', color: 'var(--text-muted)' }}>{e.what}</span>
            </span>
          </li>
        ))}
      </ol>
    </div>
  )
}

/** The fund that pays for the ELC and Extended Day together: in, out, and the balance. */
export function EarlyLearningCenterFund({ data }: ChartProps) {
  const series = (data as Payload).fund_series
  const rows: Record<string, number | string | null>[] = []
  series.forEach((y, i) => {
    const prev = series[i - 1]
    // A gap in our reading shows as empty years, never as a line drawn across them.
    if (prev) for (let g = prev.fy + 1; g < y.fy; g++) {
      rows.push({ fy: `FY${g}`, received: null, spent: null, closing: null, gap: 1 })
    }
    rows.push({ fy: `FY${y.fy}`, received: y.received, spent: y.spent, closing: y.closing,
      opening: y.opening, source: y.source })
  })
  return (
    <div style={{ width: '100%', height: 340 }}>
      <ResponsiveContainer>
        <ComposedChart data={rows} margin={{ top: 8, right: 8, left: 4, bottom: 4 }}>
          <CartesianGrid stroke="var(--grid)" vertical={false} />
          <XAxis dataKey="fy" tick={tick} interval="preserveStartEnd" />
          <YAxis tickFormatter={usdk} width={56} tick={tick} />
          <ReferenceLine y={0} stroke="var(--text-muted)" />
          <Tooltip contentStyle={box}
            formatter={(v, name) => (v == null ? [null, null] : [usd(N(v)), String(name)]) as [string, string]}
            labelFormatter={(l, p) => {
              const r = p?.[0]?.payload as { gap?: number; opening?: number; source?: string } | undefined
              if (r?.gap) return `${l} · not in our reading of the annual reports`
              return r?.source ? `${l} · opened at ${usd(N(r.opening))} · ${r.source}` : String(l)
            }} />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <Bar dataKey="received" name="fees and receipts" fill={C_IN} isAnimationActive={false} />
          <Bar dataKey="spent" name="spent" fill={C_OUT} isAnimationActive={false} />
          <Line dataKey="closing" name="closing balance" stroke={C_BAL} strokeWidth={2}
            dot={{ r: 3 }} connectNulls={false} isAnimationActive={false} />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}

/** Fees into the fund: deposits somebody typed ELC beside, and the rest. A floor for the
 *  ELC, not its share: the label is optional. */
export function EarlyLearningCenterFees({ data }: ChartProps) {
  const rows = (data as Payload).fees_by_year.map(y => ({ ...y, fy: `FY${y.fy}` }))
  return (
    <div style={{ width: '100%', height: 300 }}>
      <ResponsiveContainer>
        <BarChart data={rows} margin={{ top: 8, right: 8, left: 4, bottom: 4 }}>
          <CartesianGrid stroke="var(--grid)" vertical={false} />
          <XAxis dataKey="fy" tick={tick} />
          <YAxis tickFormatter={usdk} width={56} tick={tick} />
          <Tooltip contentStyle={box} formatter={(v, name) => [usd(N(v)), String(name)]}
            labelFormatter={(l, p) => {
              const r = p?.[0]?.payload as FeeYr | undefined
              return r ? `${l} · ${usd(r.all)} in fees` : String(l)
            }} />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <Bar dataKey="elc" name="typed ELC" stackId="f" fill={C_ELC} isAnimationActive={false} />
          <Bar dataKey="rest" name="the rest of the fund’s fees" stackId="f" fill={C_REST}
            isAnimationActive={false} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

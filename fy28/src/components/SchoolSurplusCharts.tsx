import {
  Bar, BarChart, CartesianGrid, Cell, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import type { ChartProps } from './analysisCharts'

/* The signature chart of the school surplus reports -- /analysis/fy25-school-surplus and
 * /analysis/fy26-school-surplus -- drawn from each report's own payload (`waterfall`),
 * written by scripts/build_school_surplus.py. Rule 7f: the SVG beside the markdown stays
 * for /docs and the PDF; the web page draws this.
 *
 * TWO PANELS, because one scale cannot carry both findings. The left is the whole flow on
 * the full appropriation scale, where almost everything was spent. The right is the
 * unspent figure beside what it is compared with -- the district's own figure for FY25,
 * the period-12 floor and ceiling for FY26 -- on an axis ZOOMED to those values, and it
 * says so, because a zoomed axis that does not say so exaggerates.
 *
 * Nothing here computes a figure (rule 2). The comparison bars come from `compare` when
 * the payload carries it; the FY25 payload predates that field and carries
 * `district_figure`, which is drawn as the same two-bar comparison. */

const N = (v: unknown) => (Array.isArray(v) ? Number(v[0]) : Number(v))
const box = {
  background: 'var(--surface-1)', border: '1px solid var(--grid)',
  borderRadius: 8, fontSize: 12.5, color: 'var(--text-primary)',
  boxShadow: '0 2px 10px rgba(0,0,0,.12)', opacity: 1,
}
const usd = (v: number) => (v < 0 ? '-$' : '$') + Math.abs(Math.round(v)).toLocaleString()
const usdk = (v: number) =>
  Math.abs(v) >= 1e6 ? `$${(v / 1e6).toFixed(1)}M`
    : Math.abs(v) >= 1e3 ? `$${Math.round(v / 1e3)}k` : `$${Math.round(v)}`

type Waterfall = {
  voted: number; moved_out: number; revised: number; spent: number; unspent: number
  district_figure?: number
  compare?: { label: string; value: number }[]
  gap_label?: string; gap?: number
}

const tick = { fontSize: 11, fill: 'var(--text-muted)' }
const COLORS = ['var(--series-1, #3987e5)', 'var(--series-2, #86b6ef)', '#b9b8ae', '#e34948']

export function SchoolSurplusWaterfall({ data }: ChartProps) {
  const w = (data as { waterfall: Waterfall }).waterfall
  const flow = [
    { stage: 'Voted', value: w.voted, fill: '#184f95' },
    { stage: 'Revised', value: w.revised, fill: '#184f95' },
    { stage: 'Spent', value: w.spent, fill: '#184f95' },
    { stage: 'Unspent', value: w.unspent, fill: '#3987e5' },
  ]
  const compare = w.compare
    ?? (w.district_figure != null
      ? [{ label: 'Our ledger', value: w.unspent },
        { label: 'The district’s figure', value: w.district_figure }]
      : [])
  const vals = compare.map(c => c.value)
  const lo = Math.min(...vals) * 0.9
  const hi = Math.max(...vals) * 1.08
  const moved = w.moved_out
  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 16 }}>
      <div style={{ flex: '1 1 300px', minWidth: 0 }}>
        <div style={{ fontSize: 12.5, color: 'var(--text-muted)', marginBottom: 4 }}>
          The whole flow, on one scale · {usd(Math.abs(moved))} moved {moved < 0 ? 'out' : 'in'} mid-year
        </div>
        <div style={{ width: '100%', height: 260 }}>
          <ResponsiveContainer>
            <BarChart data={flow} margin={{ top: 18, right: 8, left: 4, bottom: 4 }}>
              <CartesianGrid stroke="var(--grid)" vertical={false} />
              <XAxis dataKey="stage" tick={tick} />
              <YAxis tickFormatter={usdk} width={54} tick={tick} />
              <Tooltip contentStyle={box} formatter={(v) => usd(N(v))} />
              <Bar dataKey="value" name="dollars" isAnimationActive={false}
                radius={[3, 3, 0, 0]}>
                {flow.map(r => <Cell key={r.stage} fill={r.fill} />)}
                <LabelList dataKey="value" position="top"
                  formatter={(v: unknown) => usdk(N(v))}
                  style={{ fontSize: 11, fill: 'var(--text-primary)' }} />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
      {compare.length > 0 && (
        <div style={{ flex: '1 1 260px', minWidth: 0 }}>
          <div style={{ fontSize: 12.5, color: 'var(--text-muted)', marginBottom: 4 }}>
            Zoomed to {usdk(lo)}–{usdk(hi)}
            {w.gap != null && w.gap_label ? ` · ${usd(w.gap)} ${w.gap_label}` : ''}
          </div>
          <div style={{ width: '100%', height: 260 }}>
            <ResponsiveContainer>
              <BarChart data={compare} margin={{ top: 18, right: 8, left: 4, bottom: 4 }}>
                <CartesianGrid stroke="var(--grid)" vertical={false} />
                <XAxis dataKey="label" tick={tick} interval={0} />
                <YAxis domain={[lo, hi]} allowDataOverflow tickFormatter={usdk} width={54}
                  tick={tick} />
                <Tooltip contentStyle={box} formatter={(v) => usd(N(v))} />
                <Bar dataKey="value" name="dollars" isAnimationActive={false}
                  radius={[3, 3, 0, 0]}>
                  {compare.map((c, i) => <Cell key={c.label} fill={COLORS[i % COLORS.length]} />)}
                  <LabelList dataKey="value" position="top"
                    formatter={(v: unknown) => usd(N(v))}
                    style={{ fontSize: 11, fill: 'var(--text-primary)' }} />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </div>
  )
}

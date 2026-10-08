import {
  Bar, BarChart, CartesianGrid, Cell, LabelList, ReferenceLine, ResponsiveContainer, Tooltip,
  XAxis, YAxis,
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

/* WHERE THE MONEY WAS LEFT, and HOW EACH BUDGET WAS USED -- the two charts of the
 * "Why there was money left over" section, drawn from the payload's `causes` block
 * (scripts/build_school_surplus.py, `why()`). Same rule as above: every figure comes from
 * the payload, nothing is computed here but a bar's position.
 *
 * The first is the section's signature: one bar per plain-English category, net, largest
 * first, coloured by the thrift test (discretionary vs circumstantial) so the answer to
 * "was it thrift?" is visible in the same picture. Over-budget categories run left of
 * zero in grey.
 *
 * The second splits each category's revised budget into spent / still committed / left,
 * as shares of that budget, so a $12M salary line and a $0.1M service line can be read on
 * one axis. A category spent past the axis cap says so in its label. */

type Cat = {
  key: string; label: string; kind: 'discretionary' | 'circumstantial'
  unspent: number; revised: number; expended: number; encumbered: number
  pct_of_revised: number | null
}
type Bvs = {
  key: string; label: string; revised: number; spent_pct: number; committed_pct: number
  left_pct: number; over_pct: number; spent_shown: number
}
type Causes = { categories: Cat[]; budget_vs_spent: Bvs[]; bvs_cap: number }

const KIND_FILL = { discretionary: '#eb6834', circumstantial: '#3987e5' }
const OVER_FILL = '#b9b8ae'

function Legend({ items }: { items: [string, string][] }) {
  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px 16px', fontSize: 12,
      color: 'var(--text-muted)', marginTop: 6 }}>
      {items.map(([fill, text]) => (
        <span key={text} style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
          <span style={{ width: 10, height: 10, background: fill, borderRadius: 2 }} />{text}
        </span>
      ))}
    </div>
  )
}

export function SchoolSurplusCauses({ data }: ChartProps) {
  const rows = (data as { causes: Causes }).causes.categories
  return (
    <div>
      <div style={{ width: '100%', height: rows.length * 30 + 40 }}>
        <ResponsiveContainer>
          <BarChart data={rows} layout="vertical"
            margin={{ top: 4, right: 64, left: 4, bottom: 4 }}>
            <CartesianGrid stroke="var(--grid)" horizontal={false} />
            <XAxis type="number" tickFormatter={usdk} tick={tick} />
            <YAxis type="category" dataKey="label" width={150} interval={0}
              tick={{ fontSize: 11, fill: 'var(--text-primary)' }} />
            <Tooltip contentStyle={box}
              formatter={(v, _n, item) => {
                const c = (item as { payload?: Cat }).payload
                return [`${usd(N(v))} left over` + (c && c.pct_of_revised != null
                  ? ` — ${c.pct_of_revised}% of a ${usd(c.revised)} budget` : ''), '']
              }} />
            <ReferenceLine x={0} stroke="var(--text-muted)" />
            <Bar dataKey="unspent" isAnimationActive={false} radius={[0, 3, 3, 0]}>
              {rows.map(r => (
                <Cell key={r.key} fill={r.unspent < 0 ? OVER_FILL : KIND_FILL[r.kind]} />
              ))}
              <LabelList dataKey="unspent" position="right"
                formatter={(v: unknown) => usdk(N(v))}
                style={{ fontSize: 11, fill: 'var(--text-primary)' }} />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <Legend items={[[KIND_FILL.discretionary, 'Discretionary (supplies, upkeep, equipment)'],
        [KIND_FILL.circumstantial, 'Circumstantial (staff, tuition, prices)'],
        [OVER_FILL, 'Over budget']]} />
    </div>
  )
}

export function SchoolSurplusBudgetVsSpent({ data }: ChartProps) {
  const c = (data as { causes: Causes }).causes
  const rows = c.budget_vs_spent
  const pct = (v: number) => `${Math.round(v)}%`
  return (
    <div>
      <div style={{ width: '100%', height: rows.length * 30 + 40 }}>
        <ResponsiveContainer>
          <BarChart data={rows} layout="vertical" barCategoryGap={6}
            margin={{ top: 4, right: 56, left: 4, bottom: 4 }}>
            <CartesianGrid stroke="var(--grid)" horizontal={false} />
            <XAxis type="number" domain={[0, c.bvs_cap]} allowDataOverflow
              tickFormatter={pct} tick={tick} />
            <YAxis type="category" dataKey="label" width={150} interval={0}
              tick={{ fontSize: 11, fill: 'var(--text-primary)' }} />
            <Tooltip contentStyle={box}
              formatter={(v, name, item) => {
                const r = (item as { payload?: Bvs }).payload
                if (name === 'Spent' && r) return [`${r.spent_pct}% of ${usd(r.revised)}`, name]
                return [`${N(v)}%`, name]
              }} />
            <ReferenceLine x={100} stroke="#b3261e" strokeDasharray="3 2" />
            <Bar dataKey="spent_shown" name="Spent" stackId="a" fill="#184f95"
              isAnimationActive={false} />
            <Bar dataKey="committed_pct" name="Still committed" stackId="a" fill="#86b6ef"
              isAnimationActive={false} />
            <Bar dataKey="left_pct" name="Left over" stackId="a" fill="#3987e5"
              isAnimationActive={false}>
              <LabelList dataKey="key" position="right" content={(p) => {
                const { x, y, width, height, index } = p as {
                  x: number; y: number; width: number; height: number; index: number }
                const r = rows[index]
                if (!r) return null
                const txt = r.over_pct ? `${Math.round(r.spent_pct)}% spent`
                  : r.left_pct >= 1 ? `${Math.round(r.left_pct)}% left` : ''
                return txt ? (
                  <text x={Number(x) + Number(width) + 4} y={Number(y) + Number(height) / 2 + 4}
                    fontSize={11} fontWeight={700}
                    fill={r.over_pct ? '#b3261e' : 'var(--text-primary)'}>{txt}</text>
                ) : null
              }} />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <Legend items={[['#184f95', 'Spent'], ['#86b6ef', 'Still committed (open orders)'],
        ['#3987e5', 'Left over'], ['#b3261e', 'The budget (100%)']]} />
    </div>
  )
}

import {
  Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart, ReferenceLine,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import type { ChartProps } from './analysisCharts'

/* The charts for /analysis/department-budgets, from /data/department-budgets.json.
 * Rule 7f. Nothing here computes a figure: the index values, the pulls and the names all
 * arrive from the payload scripts/build_department_budgets.py writes, the same payload the
 * stat row and the conclusion cards read.
 *
 * The colours are the validated categorical set TownBudgetsCharts uses (see the note
 * there for the validator run), assigned per GROUP rather than per rank so a group is the
 * same colour in both charts. The levy line is neutral and dashed because it is a
 * benchmark, not a part of the budget. */

const N = (v: unknown) => (Array.isArray(v) ? Number(v[0]) : Number(v))

const COLOUR: Record<string, string> = {
  schools: '#2b6cb0', town: '#dc2626', benefits: '#ea8c00', retirement: '#7c3aed',
  debt: '#2f8f4e', assessments: '#0d9488', reserves: '#92400e', levy: 'var(--text-muted)',
}

type Group = { key: string; name: string; pull: number; rate: number; share_first: number }
type Payload = {
  index_series: Record<string, number | null>[]
  index_keys: { key: string; name: string }[]
  groups: Group[]
}

const box = {
  background: 'var(--surface-1)', border: '1px solid var(--grid)',
  borderRadius: 8, fontSize: 12.5, color: 'var(--text-primary)',
  boxShadow: '0 2px 10px rgba(0,0,0,.12)', opacity: 1,
}
const signed = (v: number) => `${v >= 0 ? '+' : '−'}${Math.abs(v).toFixed(2)}`

/** Each group's starting budget, and the levy limit less overrides, indexed to 100. */
export function DepartmentBudgetsIndex({ data }: ChartProps) {
  const d = data as Payload
  const rows = d.index_series.map(p => ({ ...p, label: `FY${p.fy}` }))
  return (
    <div style={{ width: '100%', height: 340 }}>
      <ResponsiveContainer>
        <LineChart data={rows} margin={{ top: 8, right: 16, left: 0, bottom: 4 }}>
          <CartesianGrid stroke="var(--grid)" vertical={false} />
          <XAxis dataKey="label" tick={{ fontSize: 11, fill: 'var(--text-muted)' }}
            interval="preserveStartEnd" minTickGap={24} />
          <YAxis width={40} tick={{ fontSize: 11, fill: 'var(--text-muted)' }}
            domain={['dataMin - 10', 'dataMax + 10']} allowDecimals={false} />
          <ReferenceLine y={100} stroke="var(--text-muted)" strokeOpacity={0.4} />
          <Tooltip contentStyle={box}
            formatter={(v, name) => [`${N(v).toFixed(0)} (FY${d.index_series[0].fy} = 100)`,
              String(name)]} />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          {d.index_keys.map(k => (
            <Line key={k.key} dataKey={k.key} name={k.name} dot={false}
              isAnimationActive={false} strokeWidth={2.2} stroke={COLOUR[k.key]}
              strokeDasharray={k.key === 'levy' ? '5 4' : undefined} connectNulls />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

/** Pull on the levy, points a year, one bar per group, ranked. */
export function DepartmentBudgetsPull({ data }: ChartProps) {
  const rows = [...(data as Payload).groups].sort((a, b) => b.pull - a.pull)
  return (
    <div style={{ width: '100%', height: Math.max(220, rows.length * 32 + 40) }}>
      <ResponsiveContainer>
        <BarChart data={rows} layout="vertical"
          margin={{ top: 4, right: 24, left: 8, bottom: 4 }}>
          <CartesianGrid stroke="var(--grid)" horizontal={false} />
          <XAxis type="number" tickFormatter={v => signed(N(v))}
            tick={{ fontSize: 11, fill: 'var(--text-muted)' }} />
          <YAxis type="category" dataKey="name" width={150}
            tick={{ fontSize: 11, fill: 'var(--text-primary)' }} />
          <Tooltip contentStyle={box}
            formatter={(v, _n, item) => {
              const g = (item as { payload?: Group }).payload
              return [`${signed(N(v))} points a year` + (g
                ? ` — ${(g.share_first * 100).toFixed(1)}% of the budget, growing ${(g.rate * 100).toFixed(1)}% a year`
                : ''), '']
            }} />
          <ReferenceLine x={0} stroke="var(--text-muted)" />
          <Bar dataKey="pull" isAnimationActive={false} radius={[0, 3, 3, 0]}>
            {rows.map(r => <Cell key={r.key} fill={COLOUR[r.key]} />)}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

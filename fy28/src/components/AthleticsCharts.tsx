import { useMemo, useState } from 'react'
import {
  BarChart, Bar, Cell, XAxis, YAxis, CartesianGrid, Tooltip, ReferenceLine,
  ResponsiveContainer, ComposedChart, Line, LabelList,
} from 'recharts'
import { usd, usdShort } from '../model/engine'

/** The charts for /athletics-money. Every series arrives from /data/athletics.json,
 *  written by scripts/build_athletics_charts.py — nothing here computes a headline figure
 *  and nothing here has one typed into it (rule 2).
 *
 *  COLOUR CARRIES TWO DIFFERENT JOBS ON THIS PAGE AND THEY ARE KEPT APART.
 *
 *  1. THE TWO SIDES OF THE MONEY — what the town appropriates and what the fee-funded
 *     revolving fund spends — use --series-cost and --series-revenue. That is the site's
 *     validated identity pair, already doing the same categorical duty on
 *     /budget-vs-actual, and every chart that uses it carries a legend and a table.
 *  2. WHAT THE SPORTS COST, BY CATEGORY — coaches, transportation, officials, and the
 *     residual — use --ath-*, defined and validated in index.css against both surfaces.
 *
 *  A hue never crosses between the two. "Blue" means the town's appropriation everywhere
 *  on this page and never a category; the categories are never drawn in blue or orange.
 *
 *  EVERY CHART HAS A TABLE TWIN. That is the accessibility floor and the house style: a
 *  figure a reader cannot copy out of the page is a figure they cannot check.
 *
 *  A BLANK IS A FINDING HERE, NOT A ZERO. For four years nobody published the fund side
 *  at all. A bar of height zero would say the fund paid nothing, which is false, so an
 *  unpublished year is drawn as an explicit hatched gap and labelled. */

export const TOWN = 'var(--series-cost)'
export const FUND = 'var(--series-revenue)'
export const NEUTRAL = 'var(--text-muted)'
export const CAT_COLOUR: Record<string, string> = {
  Coaches: 'var(--ath-coaches)',
  Transportation: 'var(--ath-transport)',
  Officials: 'var(--ath-officials)',
  'Everything else': NEUTRAL,
}

export const fy = (n: number) => `FY${String(n).slice(2)}`
export const share = (x: number) => `${(x * 100).toFixed(x >= 0.1 ? 0 : 1)}%`

export function Card({ children }: { children: React.ReactNode }) {
  return <div className="card p-4">{children}</div>
}

export function Chip({ color, children, hollow }: {
  color: string; children: React.ReactNode; hollow?: boolean
}) {
  return (
    <span className="inline-flex items-center gap-1.5 text-[11.5px]"
      style={{ color: 'var(--text-secondary)' }}>
      <span className="inline-block w-2.5 h-2.5 rounded-[2px]"
        style={hollow
          ? { border: `1.5px dashed ${color}` }
          : { background: color }} />
      {children}
    </span>
  )
}

function Tip({ title, rows, foot }: {
  title: string
  rows: { label: string; value: string; colour?: string }[]
  foot?: React.ReactNode
}) {
  return (
    <div className="rounded-[10px] px-3 py-2 text-xs"
      style={{ background: 'var(--surface-1)', border: '1px solid var(--grid)' }}>
      <p className="font-semibold mb-1.5" style={{ color: 'var(--text-secondary)' }}>{title}</p>
      {rows.map(r => (
        <p key={r.label} className="flex justify-between gap-4">
          <span style={{ color: r.colour ?? 'var(--text-secondary)' }}>{r.label}</span>
          <span className="tnum font-semibold">{r.value}</span>
        </p>
      ))}
      {foot ? (
        <p className="mt-1 pt-1 border-t text-[11px]"
          style={{ borderColor: 'var(--grid)', color: 'var(--text-muted)' }}>{foot}</p>
      ) : null}
    </div>
  )
}

/* --------------------------------------------------------------- both sides */

export type SideRow = {
  fy: number; general: number; general_basis: string
  revolving: number | null; revolving_state: string
  revenue: number | null; all_in: number | null; fund_share: number | null
}

/** Both sides of the money, every year either one is visible.
 *
 *  A stacked bar, because the two ARE two parts of one programme in the years both were
 *  published — and the years they were not are the whole point, so those carry a dashed
 *  outline at the height of the appropriation alone and are called out in the legend.
 *  Fund REVENUE is not on this chart at any height: it is a third quantity, and the one
 *  published figure of "$335,856 through the revolving fund" was revenue plus spending. */
export function BothSides({ rows }: { rows: SideRow[] }) {
  return (
    <Card>
      <div className="flex flex-wrap gap-x-5 gap-y-1 mb-2">
        <Chip color={TOWN}>what the town appropriated</Chip>
        <Chip color={FUND}>what the fee-funded fund spent</Chip>
        <Chip color={NEUTRAL} hollow>fund side never published</Chip>
      </div>
      <div style={{ width: '100%', height: 280 }}>
        <ResponsiveContainer>
          <BarChart data={rows} margin={{ top: 8, right: 12, bottom: 4, left: 4 }}>
            <CartesianGrid stroke="var(--grid)" vertical={false} />
            <XAxis dataKey="fy" tickFormatter={v => fy(v as number)}
              tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
              stroke="var(--axis)" tickLine={false} interval={0} />
            <YAxis width={54} tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
              stroke="var(--axis)" tickLine={false} axisLine={false}
              tickFormatter={v => usdShort(v as number)} />
            <Tooltip cursor={{ fill: 'var(--surface-3)', opacity: 0.5 }}
              content={({ active, payload }) => {
                if (!active || !payload?.length) return null
                const d = payload[0].payload as SideRow
                return (
                  <Tip title={`${fy(d.fy)} · ${d.general_basis}`}
                    rows={[
                      { label: 'Town appropriation', value: usd(d.general), colour: TOWN },
                      {
                        label: 'Fee-funded fund',
                        value: d.revolving === null ? 'not published' : usd(d.revolving),
                        colour: FUND,
                      },
                      ...(d.all_in
                        ? [{ label: 'Whole programme', value: usd(d.all_in) }]
                        : []),
                    ]}
                    foot={d.revolving_state === 'published'
                      ? `The fund carried ${share(d.fund_share ?? 0)} of it`
                      : d.revolving_state === 'partial'
                        ? 'Two lines only — the fund certainly paid for more'
                        : 'No document published the fund side this year'} />
                )
              }} />
            <Bar dataKey="general" stackId="a" fill={TOWN} isAnimationActive={false}
              maxBarSize={44} />
            <Bar dataKey="revolving" stackId="a" isAnimationActive={false}
              maxBarSize={44} radius={[4, 4, 0, 0]}>
              {rows.map(r => (
                <Cell key={r.fy} fill={FUND}
                  fillOpacity={r.revolving_state === 'partial' ? 0.55 : 1} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <table className="stack w-full text-xs mt-4 tnum">
        <caption className="sr-only">
          Athletics, both sides of the money, by fiscal year
        </caption>
        <thead>
          <tr className="text-left" style={{ color: 'var(--text-muted)' }}>
            <th className="font-semibold py-1.5">Year</th>
            <th className="font-semibold py-1.5 text-right">Town appropriation</th>
            <th className="font-semibold py-1.5 text-right">Fee-funded fund</th>
            <th className="font-semibold py-1.5 text-right">Whole programme</th>
            <th className="font-semibold py-1.5 text-right">Fund&rsquo;s share</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(r => (
            <tr key={r.fy} className="border-t" style={{ borderColor: 'var(--grid)' }}>
              <td className="rowhead py-1.5 font-semibold">{fy(r.fy)}</td>
              <td data-label="Town" className="py-1.5 text-right">{usd(r.general)}</td>
              <td data-label="Fund" className="py-1.5 text-right"
                style={{ color: r.revolving === null ? 'var(--text-muted)' : undefined }}>
                {r.revolving === null
                  ? 'not published'
                  : usd(r.revolving) + (r.revolving_state === 'partial' ? ' (partial)' : '')}
              </td>
              <td data-label="Whole programme" className="py-1.5 text-right">
                {r.all_in ? usd(r.all_in) : <span style={{ color: 'var(--text-muted)' }}>
                  &ge; {usd(r.general + (r.revolving ?? 0))}</span>}
              </td>
              <td data-label="Fund share" className="py-1.5 text-right font-semibold">
                {r.fund_share === null ? '—' : share(r.fund_share)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </Card>
  )
}

/* ------------------------------------------------------- the transport swap */

export type TransportRow = {
  fy: number; general: number | null; fund: number | null; state: string
  cost: number | null; fund_share: number | null
}

/** One line, two funds, thirteen years. The chart the page exists for.
 *
 *  In FY24 and FY25 the two bars sum EXACTLY to the district workbook's own
 *  transportation total, which the generator asserts before it will write — so this is
 *  one cost split two ways rather than two numbers stacked for effect. */
export function TransportSwap({ rows }: { rows: TransportRow[] }) {
  return (
    <Card>
      <div className="flex flex-wrap gap-x-5 gap-y-1 mb-2">
        <Chip color={TOWN}>paid from the town&rsquo;s budget</Chip>
        <Chip color={FUND}>paid by the fee-funded fund</Chip>
        <Chip color={NEUTRAL} hollow>fund side never published</Chip>
      </div>
      <div style={{ width: '100%', height: 250 }}>
        <ResponsiveContainer>
          <BarChart data={rows} margin={{ top: 8, right: 12, bottom: 4, left: 4 }}>
            <CartesianGrid stroke="var(--grid)" vertical={false} />
            <XAxis dataKey="fy" tickFormatter={v => fy(v as number)} interval={0}
              tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
              stroke="var(--axis)" tickLine={false} />
            <YAxis width={54} tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
              stroke="var(--axis)" tickLine={false} axisLine={false}
              tickFormatter={v => usdShort(v as number)} />
            <Tooltip cursor={{ fill: 'var(--surface-3)', opacity: 0.5 }}
              content={({ active, payload }) => {
                if (!active || !payload?.length) return null
                const d = payload[0].payload as TransportRow
                return (
                  <Tip title={`${fy(d.fy)} · athletic transportation`}
                    rows={[
                      { label: 'Town budget line', value: d.general === null ? '—' : usd(d.general), colour: TOWN },
                      { label: 'Fee-funded fund', value: d.fund === null ? 'not published' : usd(d.fund), colour: FUND },
                      ...(d.cost ? [{ label: 'Whole cost of the buses', value: usd(d.cost) }] : []),
                    ]}
                    foot={d.fund_share !== null
                      ? `${share(d.fund_share)} of it fell outside the town's budget`
                      : undefined} />
                )
              }} />
            <Bar dataKey="general" stackId="t" fill={TOWN} isAnimationActive={false} maxBarSize={44} />
            <Bar dataKey="fund" stackId="t" fill={FUND} isAnimationActive={false}
              maxBarSize={44} radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <table className="stack w-full text-xs mt-4 tnum">
        <caption className="sr-only">Athletic transportation, by fund, by fiscal year</caption>
        <thead>
          <tr className="text-left" style={{ color: 'var(--text-muted)' }}>
            <th className="font-semibold py-1.5">Year</th>
            <th className="font-semibold py-1.5 text-right">Town budget line</th>
            <th className="font-semibold py-1.5 text-right">Fee-funded fund</th>
            <th className="font-semibold py-1.5 text-right">Outside the budget</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(r => (
            <tr key={r.fy} className="border-t" style={{ borderColor: 'var(--grid)' }}>
              <td className="rowhead py-1.5 font-semibold">{fy(r.fy)}</td>
              <td data-label="Town" className="py-1.5 text-right">
                {r.general === null ? '—' : usd(r.general)}</td>
              <td data-label="Fund" className="py-1.5 text-right"
                style={{ color: r.fund === null ? 'var(--text-muted)' : undefined }}>
                {r.fund === null ? 'not published' : usd(r.fund)}</td>
              <td data-label="Outside the budget" className="py-1.5 text-right font-semibold">
                {r.fund_share === null ? '—' : share(r.fund_share)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </Card>
  )
}

/* --------------------------------------------------------- coaching over time */

export type CoachRow = {
  fy: number; general: number | null; fund: number | null; lines: string[]
}

export function Coaching({ rows, workbook }: {
  rows: CoachRow[]; workbook: { fy: number; amount: number }[]
}) {
  const wb = new Map(workbook.map(r => [r.fy, r.amount]))
  const data = rows.map(r => ({ ...r, workbook: wb.get(r.fy) ?? null }))
  return (
    <Card>
      <div className="flex flex-wrap gap-x-5 gap-y-1 mb-2">
        <Chip color={TOWN}>coaching lines in the town&rsquo;s budget</Chip>
        <Chip color={FUND}>coaching paid by the fund</Chip>
        <Chip color={CAT_COLOUR.Coaches}>what the district&rsquo;s workbook says coaching cost</Chip>
      </div>
      <div style={{ width: '100%', height: 250 }}>
        <ResponsiveContainer>
          <ComposedChart data={data} margin={{ top: 8, right: 12, bottom: 4, left: 4 }}>
            <CartesianGrid stroke="var(--grid)" vertical={false} />
            <XAxis dataKey="fy" tickFormatter={v => fy(v as number)} interval={0}
              tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
              stroke="var(--axis)" tickLine={false} />
            <YAxis width={54} tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
              stroke="var(--axis)" tickLine={false} axisLine={false}
              tickFormatter={v => usdShort(v as number)} />
            <Tooltip cursor={{ fill: 'var(--surface-3)', opacity: 0.5 }}
              content={({ active, payload }) => {
                if (!active || !payload?.length) return null
                const d = payload[0].payload as CoachRow & { workbook: number | null }
                return (
                  <Tip title={`${fy(d.fy)} · coaching`}
                    rows={[
                      { label: 'Town budget lines', value: d.general === null ? '—' : usd(d.general), colour: TOWN },
                      { label: 'Fee-funded fund', value: d.fund === null ? 'not published' : usd(d.fund), colour: FUND },
                      { label: 'Workbook cost', value: d.workbook === null ? 'not published' : usd(d.workbook), colour: CAT_COLOUR.Coaches },
                    ]}
                    foot={d.lines.length ? d.lines.join(' + ') : undefined} />
                )
              }} />
            <Bar dataKey="general" stackId="c" fill={TOWN} isAnimationActive={false} maxBarSize={40} />
            <Bar dataKey="fund" stackId="c" fill={FUND} isAnimationActive={false}
              maxBarSize={40} radius={[4, 4, 0, 0]} />
            <Line type="monotone" dataKey="workbook" stroke={CAT_COLOUR.Coaches}
              strokeWidth={2} dot={{ r: 4, fill: CAT_COLOUR.Coaches, strokeWidth: 0 }}
              connectNulls isAnimationActive={false} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      <table className="stack w-full text-xs mt-4 tnum">
        <caption className="sr-only">Coaching, by source of money, by fiscal year</caption>
        <thead>
          <tr className="text-left" style={{ color: 'var(--text-muted)' }}>
            <th className="font-semibold py-1.5">Year</th>
            <th className="font-semibold py-1.5 text-right">Town budget</th>
            <th className="font-semibold py-1.5 text-right">Fund</th>
            <th className="font-semibold py-1.5 text-right">Workbook cost</th>
          </tr>
        </thead>
        <tbody>
          {data.map(r => (
            <tr key={r.fy} className="border-t" style={{ borderColor: 'var(--grid)' }}>
              <td className="rowhead py-1.5 font-semibold">{fy(r.fy)}</td>
              <td data-label="Town budget" className="py-1.5 text-right">
                {r.general === null ? '—' : usd(r.general)}</td>
              <td data-label="Fund" className="py-1.5 text-right"
                style={{ color: r.fund === null ? 'var(--text-muted)' : undefined }}>
                {r.fund === null ? '—' : usd(r.fund)}</td>
              <td data-label="Workbook cost" className="py-1.5 text-right"
                style={{ color: r.workbook === null ? 'var(--text-muted)' : undefined }}>
                {r.workbook === null ? '—' : usd(r.workbook)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </Card>
  )
}

/* ----------------------------------------------------- cost by category */

export type CatRow = { fy: number; total: number } & Record<string, number>

export function CostByCategory({ rows, order }: { rows: CatRow[]; order: string[] }) {
  return (
    <Card>
      <div className="flex flex-wrap gap-x-5 gap-y-1 mb-2">
        {order.map(k => <Chip key={k} color={CAT_COLOUR[k] ?? NEUTRAL}>{k}</Chip>)}
      </div>
      <div style={{ width: '100%', height: 240 }}>
        <ResponsiveContainer>
          <BarChart data={rows} layout="vertical"
            margin={{ top: 8, right: 16, bottom: 4, left: 4 }}>
            <CartesianGrid stroke="var(--grid)" horizontal={false} />
            <XAxis type="number" tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
              stroke="var(--axis)" tickLine={false}
              tickFormatter={v => usdShort(v as number)} />
            <YAxis type="category" dataKey="fy" width={46}
              tickFormatter={v => fy(v as number)}
              tick={{ fill: 'var(--text-muted)', fontSize: 12 }}
              stroke="var(--axis)" tickLine={false} axisLine={false} />
            <Tooltip cursor={{ fill: 'var(--surface-3)', opacity: 0.5 }}
              content={({ active, payload }) => {
                if (!active || !payload?.length) return null
                const d = payload[0].payload as CatRow
                return (
                  <Tip title={`${fy(d.fy)} · what the sports cost`}
                    rows={order.map(k => ({
                      label: k, value: usd(d[k] ?? 0), colour: CAT_COLOUR[k] ?? NEUTRAL,
                    }))}
                    foot={`Totals ${usd(d.total)} — the workbook's own figure`} />
                )
              }} />
            {order.map((k, i) => (
              <Bar key={k} dataKey={k} stackId="s" fill={CAT_COLOUR[k] ?? NEUTRAL}
                isAnimationActive={false} maxBarSize={54}
                radius={i === order.length - 1 ? [0, 4, 4, 0] : undefined} />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </div>
      <table className="stack w-full text-xs mt-4 tnum">
        <caption className="sr-only">
          What the sports cost, by category, from the district&rsquo;s own workbook
        </caption>
        <thead>
          <tr className="text-left" style={{ color: 'var(--text-muted)' }}>
            <th className="font-semibold py-1.5">Year</th>
            {order.map(k => (
              <th key={k} className="font-semibold py-1.5 text-right">{k}</th>
            ))}
            <th className="font-semibold py-1.5 text-right">Total</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(r => (
            <tr key={r.fy} className="border-t" style={{ borderColor: 'var(--grid)' }}>
              <td className="rowhead py-1.5 font-semibold">{fy(r.fy)}</td>
              {order.map(k => (
                <td key={k} data-label={k} className="py-1.5 text-right">{usd(r[k] ?? 0)}</td>
              ))}
              <td data-label="Total" className="py-1.5 text-right font-semibold">{usd(r.total)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </Card>
  )
}

/* ------------------------------------------------- what a sport costs a head */

export type SportRow = {
  season: string; level: string; sport: string; fy: number
  athletes: number; cost: number | null; per_athlete: number | null
}

/** Cost per participation, by sport. OURS: the workbook prints a cost and prints a
 *  headcount and never divides one by the other.
 *
 *  A participation is not a student. One child playing three seasons is three of these,
 *  and the page says so beside the chart rather than under it. */
export function CostPerSport({ rows, feeLine, years }: {
  rows: SportRow[]; feeLine: number; years: number[]
}) {
  const [year, setYear] = useState(years[years.length - 1])
  const data = useMemo(() => rows
    .filter(r => r.fy === year && r.per_athlete !== null && r.athletes > 0)
    .sort((a, b) => (b.per_athlete ?? 0) - (a.per_athlete ?? 0))
    .map(r => ({ ...r, label: `${r.sport}${r.level === 'MS' ? ' (MS)' : ''}` })),
  [rows, year])
  return (
    <Card>
      <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
        <div className="flex flex-wrap gap-x-5 gap-y-1">
          <Chip color={CAT_COLOUR.Coaches}>cost per participation</Chip>
          <Chip color={NEUTRAL} hollow>what one family paid that year</Chip>
        </div>
        <div className="flex gap-1.5">
          {years.map(y => (
            <button key={y} type="button" onClick={() => setYear(y)}
              className="rounded-full px-3 text-[12px] font-semibold"
              style={{
                minHeight: 44, minWidth: 44,
                background: y === year ? 'var(--surface-3)' : 'transparent',
                border: `1px solid ${y === year ? 'var(--axis)' : 'var(--grid)'}`,
                color: y === year ? 'var(--text-primary)' : 'var(--text-secondary)',
              }}>{fy(y)}</button>
          ))}
        </div>
      </div>
      <div style={{ width: '100%', height: Math.max(240, data.length * 22 + 40) }}>
        <ResponsiveContainer>
          <BarChart data={data} layout="vertical"
            margin={{ top: 4, right: 46, bottom: 4, left: 4 }}>
            <CartesianGrid stroke="var(--grid)" horizontal={false} />
            <XAxis type="number" tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
              stroke="var(--axis)" tickLine={false}
              tickFormatter={v => usdShort(v as number)} />
            <YAxis type="category" dataKey="label" width={132}
              tick={{ fill: 'var(--text-secondary)', fontSize: 11 }}
              stroke="var(--axis)" tickLine={false} axisLine={false} />
            <Tooltip cursor={{ fill: 'var(--surface-3)', opacity: 0.5 }}
              content={({ active, payload }) => {
                if (!active || !payload?.length) return null
                const d = payload[0].payload as SportRow
                return (
                  <Tip title={`${d.sport} · ${d.season} ${fy(d.fy)}`}
                    rows={[
                      { label: 'Cost, whole season', value: usd(d.cost ?? 0) },
                      { label: 'Participations', value: String(d.athletes) },
                      { label: 'Per participation', value: usd(d.per_athlete ?? 0) },
                    ]}
                    foot="The workbook's cost divided by the workbook's headcount. The division is ours." />
                )
              }} />
            <ReferenceLine x={feeLine} stroke="var(--axis)" strokeDasharray="4 3" />
            <Bar dataKey="per_athlete" fill={CAT_COLOUR.Coaches} isAnimationActive={false}
              radius={[0, 4, 4, 0]} maxBarSize={16}>
              <LabelList dataKey="per_athlete" position="right"
                formatter={v => usdShort(Number(v))}
                style={{ fill: 'var(--text-muted)', fontSize: 10 }} />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <p className="text-[11.5px] mt-2" style={{ color: 'var(--text-muted)' }}>
        The dashed rule is the high-school fee a first child paid that year &mdash;{' '}
        {usd(feeLine)}.
      </p>
      <table className="stack w-full text-xs mt-4 tnum">
        <caption className="sr-only">Cost per participation, by sport</caption>
        <thead>
          <tr className="text-left" style={{ color: 'var(--text-muted)' }}>
            <th className="font-semibold py-1.5">Sport</th>
            <th className="font-semibold py-1.5 text-right">Season</th>
            <th className="font-semibold py-1.5 text-right">Participations</th>
            <th className="font-semibold py-1.5 text-right">Cost</th>
            <th className="font-semibold py-1.5 text-right">Per participation</th>
          </tr>
        </thead>
        <tbody>
          {data.map(r => (
            <tr key={r.label + r.season} className="border-t" style={{ borderColor: 'var(--grid)' }}>
              <td className="rowhead py-1.5 font-semibold">{r.label}</td>
              <td data-label="Season" className="py-1.5 text-right">{r.season}</td>
              <td data-label="Participations" className="py-1.5 text-right">{r.athletes}</td>
              <td data-label="Cost" className="py-1.5 text-right">{usd(r.cost ?? 0)}</td>
              <td data-label="Per participation" className="py-1.5 text-right font-semibold">
                {usd(r.per_athlete ?? 0)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </Card>
  )
}

/* ------------------------------------------------------------ participation */

export type PartRow = { fy: number; season: string; level: string; athletes: number }

const SEASONS = ['Fall', 'Winter', 'Spring']

/** Participations by season, three years.
 *
 *  THREE YEARS IS PLOTTED HERE ON PURPOSE and the span is on the chart. The boards in this
 *  town will not project two years out, so a three-year series is more forward visibility
 *  than they currently use. It is not a long trend and the caption does not call it one. */
export function Participation({ rows, totals }: {
  rows: PartRow[]; totals: { fy: number; total: number; hs: number; ms: number }[]
}) {
  const [level, setLevel] = useState<'both' | 'HS' | 'MS'>('both')
  const data = totals.map(t => {
    const o: Record<string, number> = { fy: t.fy }
    for (const s of SEASONS) {
      o[s] = rows.filter(r => r.fy === t.fy && r.season === s
        && (level === 'both' || r.level === level))
        .reduce((a, r) => a + r.athletes, 0)
    }
    return o
  })
  const shade: Record<string, string> = {
    Fall: 'var(--ath-coaches)', Winter: 'var(--ath-transport)', Spring: 'var(--ath-officials)',
  }
  const first = totals[0], last = totals[totals.length - 1]
  const chg = (last.total - first.total) / first.total
  return (
    <Card>
      <div className="flex flex-wrap items-center justify-between gap-3 mb-2">
        <div className="flex flex-wrap gap-x-5 gap-y-1">
          {SEASONS.map(s => <Chip key={s} color={shade[s]}>{s}</Chip>)}
        </div>
        <div className="flex gap-1.5">
          {(['both', 'HS', 'MS'] as const).map(l => (
            <button key={l} type="button" onClick={() => setLevel(l)}
              className="rounded-full px-3 text-[12px] font-semibold"
              style={{
                minHeight: 44, minWidth: 44,
                background: l === level ? 'var(--surface-3)' : 'transparent',
                border: `1px solid ${l === level ? 'var(--axis)' : 'var(--grid)'}`,
                color: l === level ? 'var(--text-primary)' : 'var(--text-secondary)',
              }}>{l === 'both' ? 'All' : l}</button>
          ))}
        </div>
      </div>
      <div style={{ width: '100%', height: 230 }}>
        <ResponsiveContainer>
          <BarChart data={data} margin={{ top: 8, right: 12, bottom: 4, left: 4 }}>
            <CartesianGrid stroke="var(--grid)" vertical={false} />
            <XAxis dataKey="fy" tickFormatter={v => fy(v as number)} interval={0}
              tick={{ fill: 'var(--text-muted)', fontSize: 12 }}
              stroke="var(--axis)" tickLine={false} />
            <YAxis width={44} tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
              stroke="var(--axis)" tickLine={false} axisLine={false} />
            <Tooltip cursor={{ fill: 'var(--surface-3)', opacity: 0.5 }}
              content={({ active, payload }) => {
                if (!active || !payload?.length) return null
                const d = payload[0].payload as Record<string, number>
                return (
                  <Tip title={`${fy(d.fy)} · participations`}
                    rows={SEASONS.map(s => ({ label: s, value: String(d[s]), colour: shade[s] }))}
                    foot={`${SEASONS.reduce((a, s) => a + d[s], 0)} across the year. One child in three seasons is three of these.`} />
                )
              }} />
            {SEASONS.map((s, i) => (
              <Bar key={s} dataKey={s} stackId="p" fill={shade[s]} isAnimationActive={false}
                maxBarSize={64} radius={i === SEASONS.length - 1 ? [4, 4, 0, 0] : undefined} />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </div>
      <p className="text-[11.5px] mt-2" style={{ color: 'var(--text-muted)' }}>
        {fy(first.fy)}&ndash;{fy(last.fy)} &mdash; three years, which is the whole of what
        the district&rsquo;s workbook covers. {first.total} participations to {last.total}:{' '}
        {chg >= 0 ? '+' : '−'}{Math.abs(chg * 100).toFixed(1)}%.
      </p>
      <table className="stack w-full text-xs mt-4 tnum">
        <caption className="sr-only">Participations by year, level and season</caption>
        <thead>
          <tr className="text-left" style={{ color: 'var(--text-muted)' }}>
            <th className="font-semibold py-1.5">Year</th>
            {SEASONS.map(s => (
              <th key={s} className="font-semibold py-1.5 text-right">{s}</th>
            ))}
            <th className="font-semibold py-1.5 text-right">High school</th>
            <th className="font-semibold py-1.5 text-right">Middle school</th>
            <th className="font-semibold py-1.5 text-right">All</th>
          </tr>
        </thead>
        <tbody>
          {totals.map((t, i) => (
            <tr key={t.fy} className="border-t" style={{ borderColor: 'var(--grid)' }}>
              <td className="rowhead py-1.5 font-semibold">{fy(t.fy)}</td>
              {SEASONS.map(s => (
                <td key={s} data-label={s} className="py-1.5 text-right">{data[i][s]}</td>
              ))}
              <td data-label="High school" className="py-1.5 text-right">{t.hs}</td>
              <td data-label="Middle school" className="py-1.5 text-right">{t.ms}</td>
              <td data-label="All" className="py-1.5 text-right font-semibold">{t.total}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </Card>
  )
}

/* ---------------------------------------------------------------- who pays */

export type MixRow = { fy: number; total: number; unclassified: number } & Record<string, number>

export function WhoPays({ rows, columns }: { rows: MixRow[]; columns: string[] }) {
  const order = [...columns, 'unclassified']
  const colour: Record<string, string> = {
    'Full Pay': 'var(--ath-coaches)',
    '2nd Sibling': 'var(--ath-transport)',
    '3rd sibling': 'var(--ath-officials)',
    'Full Waiver': 'var(--series-cost)',
    unclassified: NEUTRAL,
  }
  const label: Record<string, string> = {
    'Full Pay': 'paid the full fee',
    '2nd Sibling': 'second-child rate',
    '3rd sibling': 'third-child rate',
    'Full Waiver': 'fee waived entirely',
    unclassified: 'in none of the four columns',
  }
  return (
    <Card>
      <div className="flex flex-wrap gap-x-5 gap-y-1 mb-2">
        {order.map(k => <Chip key={k} color={colour[k]}>{label[k]}</Chip>)}
      </div>
      <div style={{ width: '100%', height: 190 }}>
        <ResponsiveContainer>
          <BarChart data={rows} layout="vertical" margin={{ top: 4, right: 16, bottom: 4, left: 4 }}>
            <CartesianGrid stroke="var(--grid)" horizontal={false} />
            <XAxis type="number" tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
              stroke="var(--axis)" tickLine={false} />
            <YAxis type="category" dataKey="fy" width={46}
              tickFormatter={v => fy(v as number)}
              tick={{ fill: 'var(--text-muted)', fontSize: 12 }}
              stroke="var(--axis)" tickLine={false} axisLine={false} />
            <Tooltip cursor={{ fill: 'var(--surface-3)', opacity: 0.5 }}
              content={({ active, payload }) => {
                if (!active || !payload?.length) return null
                const d = payload[0].payload as MixRow
                return (
                  <Tip title={`${fy(d.fy)} · how the fee was paid`}
                    rows={order.map(k => ({
                      label: label[k], value: String(d[k] ?? 0), colour: colour[k],
                    }))}
                    foot={`${d.total} participations. The counts are ours, summed from the workbook's rows — its own printed totals for these columns are dollars.`} />
                )
              }} />
            {order.map((k, i) => (
              <Bar key={k} dataKey={k} stackId="w" fill={colour[k]} isAnimationActive={false}
                maxBarSize={48} radius={i === order.length - 1 ? [0, 4, 4, 0] : undefined} />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </div>
      <table className="stack w-full text-xs mt-4 tnum">
        <caption className="sr-only">How each participation&rsquo;s fee was paid</caption>
        <thead>
          <tr className="text-left" style={{ color: 'var(--text-muted)' }}>
            <th className="font-semibold py-1.5">Year</th>
            {order.map(k => (
              <th key={k} className="font-semibold py-1.5 text-right">{label[k]}</th>
            ))}
            <th className="font-semibold py-1.5 text-right">All</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(r => (
            <tr key={r.fy} className="border-t" style={{ borderColor: 'var(--grid)' }}>
              <td className="rowhead py-1.5 font-semibold">{fy(r.fy)}</td>
              {order.map(k => (
                <td key={k} data-label={label[k]} className="py-1.5 text-right">{r[k] ?? 0}</td>
              ))}
              <td data-label="All" className="py-1.5 text-right font-semibold">{r.total}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </Card>
  )
}

/* ------------------------------------------------------------ the cashbook */

export type FlowRow = {
  fy: number; opening: number; receipts: number; payments: number; net: number
  closing: number; journals: number; without_journals: number; postings: number
}

/** The fund's cash, three years, and what four journal entries do to it.
 *
 *  The counterfactual bar is drawn HOLLOW rather than filled: it is arithmetic on the
 *  town's own rows and not a balance the town ever reported, and a solid bar beside a
 *  solid bar would read as two measurements. */
export function FundCash({ rows }: { rows: FlowRow[] }) {
  return (
    <Card>
      <div className="flex flex-wrap gap-x-5 gap-y-1 mb-2">
        <Chip color={TOWN}>closing cash, as the ledger chains</Chip>
        <Chip color={FUND} hollow>where it would close without the &ldquo;per memo&rdquo; entries</Chip>
      </div>
      <div style={{ width: '100%', height: 230 }}>
        <ResponsiveContainer>
          <BarChart data={rows} margin={{ top: 8, right: 12, bottom: 4, left: 4 }}>
            <CartesianGrid stroke="var(--grid)" vertical={false} />
            <XAxis dataKey="fy" tickFormatter={v => fy(v as number)} interval={0}
              tick={{ fill: 'var(--text-muted)', fontSize: 12 }}
              stroke="var(--axis)" tickLine={false} />
            <YAxis width={58} tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
              stroke="var(--axis)" tickLine={false} axisLine={false}
              tickFormatter={v => usdShort(v as number)} />
            <Tooltip cursor={{ fill: 'var(--surface-3)', opacity: 0.5 }}
              content={({ active, payload }) => {
                if (!active || !payload?.length) return null
                const d = payload[0].payload as FlowRow
                return (
                  <Tip title={`${fy(d.fy)} · fund 1301, ${d.postings} postings`}
                    rows={[
                      { label: 'Opened at', value: usd(d.opening) },
                      { label: 'Money in', value: usd(d.receipts) },
                      { label: 'Money out', value: usd(d.payments) },
                      { label: 'Closed at', value: usd(d.closing), colour: TOWN },
                      { label: 'Of which “per memo”', value: usd(d.journals), colour: FUND },
                    ]}
                    foot={d.journals
                      ? `Without them the year closes at ${usd(d.without_journals)}`
                      : 'No journal entries of that shape this year'} />
                )
              }} />
            <ReferenceLine y={0} stroke="var(--axis)" />
            <Bar dataKey="closing" fill={TOWN} isAnimationActive={false} maxBarSize={54}
              radius={[4, 4, 0, 0]} />
            <Bar dataKey="without_journals" isAnimationActive={false} maxBarSize={54}
              fill="transparent" stroke={FUND} strokeWidth={1.5} strokeDasharray="4 3" />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <table className="stack w-full text-xs mt-4 tnum">
        <caption className="sr-only">The athletics revolving fund&rsquo;s cash, by year</caption>
        <thead>
          <tr className="text-left" style={{ color: 'var(--text-muted)' }}>
            <th className="font-semibold py-1.5">Year</th>
            <th className="font-semibold py-1.5 text-right">Opened</th>
            <th className="font-semibold py-1.5 text-right">In</th>
            <th className="font-semibold py-1.5 text-right">Out</th>
            <th className="font-semibold py-1.5 text-right">Closed</th>
            <th className="font-semibold py-1.5 text-right">Without the memos</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(r => (
            <tr key={r.fy} className="border-t" style={{ borderColor: 'var(--grid)' }}>
              <td className="rowhead py-1.5 font-semibold">{fy(r.fy)}</td>
              <td data-label="Opened" className="py-1.5 text-right">{usd(r.opening)}</td>
              <td data-label="In" className="py-1.5 text-right">{usd(r.receipts)}</td>
              <td data-label="Out" className="py-1.5 text-right">{usd(r.payments)}</td>
              <td data-label="Closed" className="py-1.5 text-right font-semibold">{usd(r.closing)}</td>
              <td data-label="Without the memos" className="py-1.5 text-right"
                style={{ color: r.without_journals < 0 ? 'var(--status-bad)' : 'var(--text-secondary)' }}>
                {usd(r.without_journals)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </Card>
  )
}

/* ------------------------------------------------------------ the fee ladder */

export type FeeRow = {
  fy: number; school_year: string; level: string; amount: number
  set_on: string; source: string
}

export function FeeLadder({ rows }: { rows: FeeRow[] }) {
  const years = [...new Set(rows.map(r => r.fy))].sort()
  const data = years.map(y => ({
    fy: y,
    school_year: rows.find(r => r.fy === y)?.school_year ?? '',
    HS: rows.find(r => r.fy === y && r.level === 'HS')?.amount ?? null,
    MS: rows.find(r => r.fy === y && r.level === 'MS')?.amount ?? null,
  }))
  return (
    <Card>
      <div className="flex flex-wrap gap-x-5 gap-y-1 mb-2">
        <Chip color={CAT_COLOUR.Coaches}>high school, first child</Chip>
        <Chip color={CAT_COLOUR.Transportation}>middle school, first child</Chip>
      </div>
      <div style={{ width: '100%', height: 210 }}>
        <ResponsiveContainer>
          <BarChart data={data} margin={{ top: 16, right: 12, bottom: 4, left: 4 }}>
            <CartesianGrid stroke="var(--grid)" vertical={false} />
            <XAxis dataKey="fy" tickFormatter={v => fy(v as number)} interval={0}
              tick={{ fill: 'var(--text-muted)', fontSize: 12 }}
              stroke="var(--axis)" tickLine={false} />
            <YAxis width={48} tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
              stroke="var(--axis)" tickLine={false} axisLine={false}
              tickFormatter={v => usd(v as number)} />
            <Tooltip cursor={{ fill: 'var(--surface-3)', opacity: 0.5 }}
              content={({ active, payload }) => {
                if (!active || !payload?.length) return null
                const d = payload[0].payload as { fy: number; school_year: string; HS: number | null; MS: number | null }
                const src = rows.filter(r => r.fy === d.fy)
                return (
                  <Tip title={`${d.school_year} season`}
                    rows={[
                      { label: 'High school', value: d.HS === null ? 'not published' : usd(d.HS), colour: CAT_COLOUR.Coaches },
                      { label: 'Middle school', value: d.MS === null ? 'not published' : usd(d.MS), colour: CAT_COLOUR.Transportation },
                    ]}
                    foot={src[0]?.source} />
                )
              }} />
            <Bar dataKey="HS" fill={CAT_COLOUR.Coaches} isAnimationActive={false}
              maxBarSize={36} radius={[4, 4, 0, 0]}>
              <LabelList dataKey="HS" position="top"
                formatter={v => (v ? usd(Number(v)) : '')}
                style={{ fill: 'var(--text-muted)', fontSize: 10 }} />
            </Bar>
            <Bar dataKey="MS" fill={CAT_COLOUR.Transportation} isAnimationActive={false}
              maxBarSize={36} radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <table className="stack w-full text-xs mt-4 tnum">
        <caption className="sr-only">The athletic fee, by level and season</caption>
        <thead>
          <tr className="text-left" style={{ color: 'var(--text-muted)' }}>
            <th className="font-semibold py-1.5">Season</th>
            <th className="font-semibold py-1.5 text-right">High school</th>
            <th className="font-semibold py-1.5 text-right">Middle school</th>
            <th className="font-semibold py-1.5 text-right">Set on</th>
          </tr>
        </thead>
        <tbody>
          {data.map(d => {
            const set = rows.find(r => r.fy === d.fy && r.set_on)?.set_on
            return (
              <tr key={d.fy} className="border-t" style={{ borderColor: 'var(--grid)' }}>
                <td className="rowhead py-1.5 font-semibold">{d.school_year}</td>
                <td data-label="High school" className="py-1.5 text-right">
                  {d.HS === null ? '—' : usd(d.HS)}</td>
                <td data-label="Middle school" className="py-1.5 text-right">
                  {d.MS === null ? '—' : usd(d.MS)}</td>
                <td data-label="Set on" className="py-1.5 text-right"
                  style={{ color: 'var(--text-muted)' }}>{set || 'not recorded'}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </Card>
  )
}

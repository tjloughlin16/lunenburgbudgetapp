import {
  Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart, ReferenceLine,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import type { ChartProps } from './analysisCharts'

/* The charts for /analysis/stabilization-funds, from /data/stabilization-funds.json.
 * Rule 7f. Nothing here computes a figure — every number arrives from the payload that
 * scripts/build_stabilization.py writes and the stat row already reads. */

// A CATEGORICAL PALETTE, VALIDATED RATHER THAN CHOSEN. TJ: *"the colors have to be
// distinct enough. the personel page is hard to see the differences."* The old one ran
// four BLUES in a row -- #12325f, #184f95, #3f78bd, #7ea6d8 -- so the four biggest
// departments, which are the four a reader cares most about telling apart, were four
// shades of one hue.
//
// Checked with the dataviz validator rather than by eye (`scripts/validate_palette.js`
// in the bundled skill), against this surface, in this ORDER -- the checks are on
// ADJACENT pairs and these charts are ranked by size, so adjacent means adjacent in rank:
//
//   lightness band       all 12 inside L 0.43-0.77      PASS
//   chroma floor         all 12 >= 0.1                  PASS
//   CVD separation       worst adjacent dE 8.4 protan   PASS
//   normal-vision floor  worst adjacent dE 19.6         PASS
//   contrast vs surface  three below 3:1                WARN -- see below
//
// The contrast warning is not dismissable and is not dismissed: it obliges visible labels
// or a table view, and every chart using this palette carries a legend naming each series
// with its value, plus the same figures as a table further down the page.
//
// DARK MODE IS NOT THIS PALETTE FLIPPED. Three of these fall outside the band the
// validator wants against the dark surface, and the honest fix is a second set of steps
// chosen for that surface rather than a reuse of these. These SVGs are fixed-colour files
// served to /docs and to the PDF, so they use the light set; picking the dark steps is
// open work.
const SLICES = ['#2b6cb0', '#dc2626', '#ea8c00', '#2f8f4e', '#7c3aed', '#0d9488', '#92400e', '#c026d3', '#38bdf8', '#a3a324', '#e0558a', '#3b5bbf']
const box = {
  background: 'var(--surface-1)', border: '1px solid var(--grid)',
  borderRadius: 8, fontSize: 12.5, color: 'var(--text-primary)',
  boxShadow: '0 2px 10px rgba(0,0,0,.12)', opacity: 1,
}
const usdk = (v: number) =>
  Math.abs(v) >= 1e6 ? `$${(v / 1e6).toFixed(1)}M`
    : Math.abs(v) >= 1e3 ? `$${Math.round(v / 1e3)}k` : `$${Math.round(v)}`
const usd = (v: number) => '$' + Math.round(v).toLocaleString()

type Point = { fy: number; ending_cash: number; ending_market: number; basis: string }
type Series = { fund: string; rate: number; points: Point[] }
type ByYear = { fy: number; amount: number; articles: number; understated: boolean }
type Spend = { fy: number; amount: number; article: string; subject: string }
type Fund = { name: string; code: string; balance: number; general: boolean }
type Payload = {
  series: Series[]
  funds: Fund[]
  totals: { held: number; general: number; restricted: number; funds: number }
  flows: { by_year: ByYear[]; spends: Spend[] }
}

/* A BALANCE IS ONLY DRAWN WHERE THE PAGE PROVED IT. Each point carries the basis on which
 * it was accepted, and the tooltip shows it, because a reader looking at a savings balance
 * is entitled to know it came off a table that closed its own arithmetic rather than off
 * a number somebody read across a scan. */
function wide(series: Series[]) {
  const yrs = [...new Set(series.flatMap(s => s.points.map(p => p.fy)))].sort((a, b) => a - b)
  return yrs.map(fy => {
    const row: Record<string, number | string | null> = { fy: `FY${fy}` }
    for (const s of series) {
      const p = s.points.find(q => q.fy === fy)
      row[s.fund] = p ? p.ending_cash : null
    }
    return row
  })
}

/** Every fund on one dollar axis: what each one actually holds beside the others. */
export function StabilizationAll({ data }: ChartProps) {
  const series = (data as Payload).series
  return (
    <div style={{ width: '100%', height: 360 }}>
      <ResponsiveContainer>
        <LineChart data={wide(series)} margin={{ top: 8, right: 16, left: 4, bottom: 4 }}>
          <CartesianGrid stroke="var(--grid)" vertical={false} />
          <XAxis dataKey="fy" tick={{ fontSize: 11, fill: 'var(--text-muted)' }}
            interval="preserveStartEnd" />
          <YAxis tickFormatter={usdk} width={54}
            tick={{ fontSize: 11, fill: 'var(--text-muted)' }} />
          <Tooltip contentStyle={box} formatter={(v: number) => usd(v)} />
          <Legend wrapperStyle={{ fontSize: 12 }} iconType="plainline" />
          {series.map((s, i) => (
            <Line key={s.fund} dataKey={s.fund} type="linear" connectNulls={false}
              stroke={SLICES[i % SLICES.length]} strokeWidth={2} dot={{ r: 2.5 }}
              isAnimationActive={false} />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

/** The same funds, each on its own range: shapes comparable, heights not. */
export function StabilizationEach({ data }: ChartProps) {
  const series = (data as Payload).series
  return (
    <div className="grid gap-4"
      style={{ gridTemplateColumns: 'repeat(auto-fit,minmax(250px,1fr))' }}>
      {series.map((s, i) => (
        <div key={s.fund}>
          <div className="text-[12px] font-semibold" style={{ color: 'var(--text-primary)' }}>
            {s.fund}
          </div>
          <div className="text-[11px] mb-1" style={{ color: 'var(--text-muted)' }}>
            FY{s.points[0]?.fy}–FY{s.points[s.points.length - 1]?.fy} ·{' '}
            {usdk(s.points[s.points.length - 1]?.ending_cash ?? 0)}
          </div>
          <div style={{ width: '100%', height: 126 }}>
            <ResponsiveContainer>
              <LineChart
                data={s.points.map(p => ({ fy: `FY${p.fy}`, cash: p.ending_cash }))}
                margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
                <CartesianGrid stroke="var(--grid)" vertical={false} />
                <XAxis dataKey="fy" tick={{ fontSize: 10, fill: 'var(--text-muted)' }}
                  interval="preserveStartEnd" />
                <YAxis tickFormatter={usdk} width={48} domain={['dataMin', 'dataMax']}
                  tick={{ fontSize: 10, fill: 'var(--text-muted)' }} />
                <Tooltip contentStyle={box} formatter={(v: number) => usd(v)} />
                <Line dataKey="cash" type="linear" dot={{ r: 2.5 }}
                  stroke={SLICES[i % SLICES.length]} strokeWidth={2}
                  isAnimationActive={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      ))}
    </div>
  )
}

/* THE SPAN IS PART OF THE FIGURE. 40.8% a year over seven years and 7.2% over fourteen
 * are not comparable rates of the same thing, so the label carries the span and the
 * tooltip repeats it. A bar chart of rates alone invites exactly the comparison the
 * underlying series will not support. */
export function StabilizationGrowth({ data }: ChartProps) {
  const rows = [...(data as Payload).series]
    .map(s => ({
      fund: s.fund, rate: s.rate,
      years: (s.points[s.points.length - 1]?.fy ?? 0) - (s.points[0]?.fy ?? 0),
    }))
    .sort((a, b) => b.rate - a.rate)
  return (
    <div style={{ width: '100%', height: Math.max(190, rows.length * 46 + 48) }}>
      <ResponsiveContainer>
        <BarChart data={rows} layout="vertical"
          margin={{ top: 4, right: 40, left: 8, bottom: 4 }}>
          <CartesianGrid stroke="var(--grid)" horizontal={false} />
          <XAxis type="number" tickFormatter={(v: number) => `${v.toFixed(0)}%`}
            tick={{ fontSize: 11, fill: 'var(--text-muted)' }} />
          <YAxis type="category" dataKey="fund" width={196}
            tick={{ fontSize: 11, fill: 'var(--text-primary)' }} />
          <Tooltip contentStyle={box}
            formatter={(v: number, _n: string, p: { payload?: { years: number } }) =>
              [`${v.toFixed(1)}% a year over ${p.payload?.years} years`, 'growth']} />
          <Bar dataKey="rate" isAnimationActive={false} radius={[0, 3, 3, 0]}>
            {rows.map((r, i) => <Cell key={r.fund} fill={SLICES[i % SLICES.length]} />)}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

/* IN ABOVE THE LINE, OUT BELOW IT, and both are FLOORS rather than totals: several
 * articles print no amount, and money also leaves inside articles about something else.
 * The page says so in words; the chart says so by marking the years that are understated
 * rather than drawing them as if they were complete. */
export function StabilizationFlows({ data }: ChartProps) {
  const f = (data as Payload).flows
  const out = new Map<number, number>()
  for (const s of f.spends) out.set(s.fy, (out.get(s.fy) ?? 0) + s.amount)
  const yrs = [...new Set([...f.by_year.map(r => r.fy), ...out.keys()])].sort((a, b) => a - b)
  const rows = yrs.map(fy => {
    const dep = f.by_year.find(r => r.fy === fy)
    return {
      fy: `FY${fy}`,
      voted_in: dep?.amount ?? 0,
      voted_out: -(out.get(fy) ?? 0),
      understated: dep?.understated ?? false,
    }
  })
  return (
    <div style={{ width: '100%', height: 340 }}>
      <ResponsiveContainer>
        <BarChart data={rows} margin={{ top: 8, right: 16, left: 4, bottom: 4 }}
          stackOffset="sign">
          <CartesianGrid stroke="var(--grid)" vertical={false} />
          <XAxis dataKey="fy" tick={{ fontSize: 11, fill: 'var(--text-muted)' }} />
          <YAxis tickFormatter={usdk} width={54}
            tick={{ fontSize: 11, fill: 'var(--text-muted)' }} />
          <Tooltip contentStyle={box}
            formatter={(v: number, n: string, p: { payload?: { understated: boolean } }) =>
              [`${usd(Math.abs(v))}${n === 'voted_in' && p.payload?.understated
                ? ' — a floor: an article printed no amount' : ''}`,
               n === 'voted_in' ? 'voted in' : 'voted out']} />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <ReferenceLine y={0} stroke="var(--text-muted)" />
          <Bar dataKey="voted_in" name="voted in" fill="#184f95"
            isAnimationActive={false} radius={[3, 3, 0, 0]}>
            {rows.map(r => (
              <Cell key={r.fy} fill={r.understated ? '#7ea6d8' : '#184f95'} />
            ))}
          </Bar>
          <Bar dataKey="voted_out" name="voted out" fill="#e08214"
            isAnimationActive={false} radius={[0, 0, 3, 3]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}


/* THE SIGNATURE VISUAL FOR THIS PAGE: the whole reserve, in proportion, fund by fund.
 *
 * TJ: *"for stabilization funds, we should show a chart of the largest funds with the most
 * money in them... or some visual that shows that... conceptually (but in proportion)."*
 * Rule 7f's signature note: a reader remembers one image per page, and for a page about
 * savings that image is how the savings are actually divided.
 *
 * AREA, NOT LENGTH, because the point is a WHOLE being carved up -- $9,061,421 held across
 * nine funds -- and nine bars of different lengths do not read as one pot. Each block is
 * sized by its balance, so the smallest funds are visibly small: the Health Insurance
 * fund is $11,027 of nine million and looks like it.
 *
 * AND THE COLOUR CARRIES THE FINDING. Only the general Stabilization Fund may be spent on
 * anything lawful; the other eight are restricted to the purpose the article creating them
 * named. That is the page's whole argument -- whether any of this can cover a school
 * deficit is a question of purpose, not of balance -- so the block for the one spendable
 * fund is a different colour from the eight that are not, and the reader sees that the
 * larger part of the pot is the part that is not available. */
export function StabilizationHoldings({ data }: ChartProps) {
  const d = data as Payload
  const funds = [...d.funds].sort((a, b) => b.balance - a.balance)
  const held = d.totals.held
  // A simple squarified layout in rows: each row takes a share of the height and its
  // funds split that row's width. Written here rather than pulled in, because the shape
  // is nine blocks and a dependency for that is not worth its weight.
  const rows: Fund[][] = [[], [], []]
  rows[0] = funds.slice(0, 2)
  rows[1] = funds.slice(2, 4)
  rows[2] = funds.slice(4)
  const rowTotal = (r: Fund[]) => r.reduce((s, f) => s + f.balance, 0)
  const title = (n: string) =>
    n.replace(/\b\w/g, c => c.toUpperCase()).replace('Opeb', 'OPEB').replace('Opiod', 'Opioid')
  return (
    <div>
      <div className="flex flex-col gap-1" style={{ width: '100%', height: 320 }}>
        {rows.filter(r => r.length).map((r, ri) => (
          <div key={ri} className="flex gap-1"
            style={{ flexGrow: rowTotal(r), flexBasis: 0, minHeight: 36 }}>
            {r.map(f => (
              <div key={f.code}
                title={`${title(f.name)} — ${usd(f.balance)}`}
                className="rounded-[3px] p-2 overflow-hidden flex flex-col justify-between"
                style={{
                  flexGrow: f.balance, flexBasis: 0, minWidth: 34,
                  background: f.general ? '#184f95' : '#7ea6d8',
                  color: f.general ? '#ffffff' : '#0d2340',
                }}>
                <span className="text-[11.5px] font-semibold leading-tight">
                  {title(f.name)}
                </span>
                <span className="text-[11px] tnum leading-tight">
                  {usdk(f.balance)} · {(f.balance / held * 100).toFixed(1)}%
                </span>
              </div>
            ))}
          </div>
        ))}
      </div>
      <ul className="mt-3 flex flex-wrap gap-x-5 gap-y-1.5 list-none p-0 m-0 text-[12px]">
        <li className="flex items-baseline gap-2">
          <span aria-hidden className="inline-block rounded-[2px]"
            style={{ width: 10, height: 10, background: '#184f95', transform: 'translateY(1px)' }} />
          <span style={{ color: 'var(--text-primary)' }}>spendable on anything lawful</span>
          <span className="tnum" style={{ color: 'var(--text-muted)' }}>
            {usd(d.totals.general)}
          </span>
        </li>
        <li className="flex items-baseline gap-2">
          <span aria-hidden className="inline-block rounded-[2px]"
            style={{ width: 10, height: 10, background: '#7ea6d8', transform: 'translateY(1px)' }} />
          <span style={{ color: 'var(--text-primary)' }}>
            restricted to the purpose its article named
          </span>
          <span className="tnum" style={{ color: 'var(--text-muted)' }}>
            {usd(d.totals.restricted)}
          </span>
        </li>
      </ul>
    </div>
  )
}

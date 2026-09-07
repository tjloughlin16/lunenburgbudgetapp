import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, ReferenceLine,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import { usd, usdShort } from '../model/engine'

/** The charts for /money-outside-the-budget. Every series arrives from
 *  /data/special-revenue.json, written by scripts/build_special_revenue.py — nothing here
 *  computes a figure and nothing here has one typed into it (rule 2).
 *
 *  TWO COLOUR JOBS, KEPT APART. Where a chart shows money in against money out, or a net
 *  that has a sign, colour is DIVERGING and uses the site's own poles: warm
 *  (--series-revenue) for money coming in, cool (--series-cost) for money going out. That
 *  is the same meaning those two hues carry on /budget-vs-actual, so nobody has to relearn
 *  them. Where a chart shows WHICH FUNDS, colour is CATEGORICAL and uses the four
 *  --fund-* tokens, which exist precisely so that identity never borrows a hue that means
 *  a direction. Both sets were run through the data-viz validator against both surfaces
 *  rather than eyeballed; the reasoning is in index.css beside the tokens.
 *
 *  EVERY CHART HAS A TABLE TWIN. House style, and here it is also the relief the palette
 *  validator requires for the amber: a band whose fill is under 3:1 against the surface
 *  must be readable some other way, and a table of the same numbers is that.
 *
 *  A STOCK AND A FLOW ARE NEVER ON ONE AXIS. Receipts and disbursements are a year's
 *  flow; the balance carried forward is what is sitting there on 30 June. They are both
 *  dollars and they are not the same measurement, so they get separate charts rather than
 *  a second y-axis. */

export const IN = 'var(--series-revenue)'
export const OUT = 'var(--series-cost)'
export const fy = (n: number) => `FY${String(n).slice(2)}`

export const BAND_COLOUR: Record<string, string> = {
  enterprise: 'var(--fund-enterprise)',
  pandemic: 'var(--fund-pandemic)',
  school: 'var(--fund-school)',
  other: 'var(--fund-other)',
}

function Card({ children }: { children: React.ReactNode }) {
  return <div className="card p-4">{children}</div>
}

export function Chip({ color, children }: { color: string; children: React.ReactNode }) {
  return (
    <span className="inline-flex items-center gap-1.5 text-[11.5px]"
      style={{ color: 'var(--text-secondary)' }}>
      <span className="inline-block w-2.5 h-2.5 rounded-[2px]" style={{ background: color }} />
      {children}
    </span>
  )
}

function TipShell({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-lg px-3 py-2 text-[12px] shadow-lg"
      style={{ background: 'var(--surface-1)', border: '1px solid var(--grid)' }}>
      <p className="font-semibold mb-1.5" style={{ color: 'var(--text-secondary)' }}>{title}</p>
      {children}
    </div>
  )
}

function TipRow({ colour, label, value }: { colour?: string; label: string; value: string }) {
  return (
    <p className="flex items-center justify-between gap-6 tnum">
      <span className="inline-flex items-center gap-1.5" style={{ color: 'var(--text-secondary)' }}>
        {colour
          ? <span className="inline-block w-2.5 h-2.5 rounded-[2px]" style={{ background: colour }} />
          : null}
        {label}
      </span>
      <span className="font-semibold">{value}</span>
    </p>
  )
}

/* ------------------------------------------------------------ money in, money out */

export type YearRow = {
  fy: number; funds: number
  forward: number; receipts: number; disbursements: number; carried: number; net: number
}

function FlowTip({ active, payload }: { active?: boolean; payload?: { payload: YearRow }[] }) {
  if (!active || !payload?.length) return null
  const d = payload[0].payload
  return (
    <TipShell title={`${fy(d.fy)} — ${d.funds} funds`}>
      <TipRow colour={IN} label="Received" value={usd(d.receipts)} />
      <TipRow colour={OUT} label="Spent" value={usd(d.disbursements)} />
      <div className="mt-1 pt-1 border-t" style={{ borderColor: 'var(--grid)' }}>
        <TipRow label={d.net >= 0 ? 'Added to balances' : 'Drawn from balances'}
          value={usd(Math.abs(d.net))} />
      </div>
    </TipShell>
  )
}

export function Flow({ rows }: { rows: YearRow[] }) {
  return (
    <Card>
      <div className="flex flex-wrap gap-x-4 gap-y-1 mb-2">
        <Chip color={IN}>Receipts</Chip>
        <Chip color={OUT}>Disbursements</Chip>
      </div>
      <div style={{ height: 260 }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={rows} margin={{ top: 4, right: 4, bottom: 0, left: 0 }} barGap={2}>
            <CartesianGrid stroke="var(--grid)" vertical={false} />
            <XAxis dataKey="fy" tickFormatter={fy} interval="preserveStartEnd"
              tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
              stroke="var(--axis)" tickLine={false} />
            <YAxis width={52} tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
              stroke="var(--axis)" tickLine={false} axisLine={false}
              tickFormatter={usdShort} />
            <Tooltip content={<FlowTip />} cursor={{ fill: 'var(--surface-3)', opacity: 0.5 }} />
            <Bar dataKey="receipts" fill={IN} radius={[4, 4, 0, 0]} />
            <Bar dataKey="disbursements" fill={OUT} radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <details className="mt-3">
        <summary className="text-[12px] cursor-pointer select-none min-h-[44px] flex items-center"
          style={{ color: 'var(--text-muted)' }}>The same numbers, as a table</summary>
        <div className="overflow-x-auto">
          <table className="w-full text-[12px] tnum mt-1">
            <thead>
              <tr className="text-left" style={{ color: 'var(--text-muted)' }}>
                <th className="py-1 pr-3 font-medium">Year</th>
                <th className="py-1 pr-3 font-medium text-right">Funds</th>
                <th className="py-1 pr-3 font-medium text-right">Received</th>
                <th className="py-1 pr-3 font-medium text-right">Spent</th>
                <th className="py-1 font-medium text-right">Net</th>
              </tr>
            </thead>
            <tbody>
              {rows.map(r => (
                <tr key={r.fy} className="border-t" style={{ borderColor: 'var(--grid)' }}>
                  <td className="py-1 pr-3">{fy(r.fy)}</td>
                  <td className="py-1 pr-3 text-right">{r.funds}</td>
                  <td className="py-1 pr-3 text-right">{usd(r.receipts)}</td>
                  <td className="py-1 pr-3 text-right">{usd(r.disbursements)}</td>
                  <td className="py-1 text-right font-semibold"
                    style={{ color: r.net >= 0 ? IN : OUT }}>{usd(r.net)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </Card>
  )
}

/* --------------------------------------------------------------- what is being held */

export type BandRow = Record<string, number> & { fy: number; total: number }
export type BandDef = { id: string; label: string; funds: string[] | null }

function HeldTip({ active, payload, bands }: {
  active?: boolean; payload?: { payload: BandRow }[]; bands: BandDef[]
}) {
  if (!active || !payload?.length) return null
  const d = payload[0].payload
  return (
    <TipShell title={`${fy(d.fy)} — held on 30 June`}>
      {[...bands].reverse().map(b => (
        <TipRow key={b.id} colour={BAND_COLOUR[b.id]} label={b.label} value={usd(d[b.id])} />
      ))}
      <div className="mt-1 pt-1 border-t" style={{ borderColor: 'var(--grid)' }}>
        <TipRow label="Total" value={usd(d.total)} />
      </div>
    </TipShell>
  )
}

export function Held({ rows, bands }: { rows: BandRow[]; bands: BandDef[] }) {
  return (
    <Card>
      <div className="flex flex-wrap gap-x-4 gap-y-1 mb-2">
        {bands.map(b => <Chip key={b.id} color={BAND_COLOUR[b.id]}>{b.label}</Chip>)}
      </div>
      <div style={{ height: 280 }}>
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={rows} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
            <CartesianGrid stroke="var(--grid)" vertical={false} />
            <XAxis dataKey="fy" tickFormatter={fy} interval="preserveStartEnd"
              tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
              stroke="var(--axis)" tickLine={false} />
            <YAxis width={52} tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
              stroke="var(--axis)" tickLine={false} axisLine={false}
              tickFormatter={usdShort} />
            <Tooltip content={<HeldTip bands={bands} />}
              cursor={{ stroke: 'var(--axis)', strokeWidth: 1 }} />
            {bands.map(b => (
              <Area key={b.id} type="monotone" dataKey={b.id} stackId="held"
                stroke="var(--surface-1)" strokeWidth={2}
                fill={BAND_COLOUR[b.id]} fillOpacity={0.92} />
            ))}
          </AreaChart>
        </ResponsiveContainer>
      </div>
      <details className="mt-3">
        <summary className="text-[12px] cursor-pointer select-none min-h-[44px] flex items-center"
          style={{ color: 'var(--text-muted)' }}>The same numbers, as a table</summary>
        <div className="overflow-x-auto">
          <table className="w-full text-[12px] tnum mt-1">
            <thead>
              <tr className="text-left" style={{ color: 'var(--text-muted)' }}>
                <th className="py-1 pr-3 font-medium">Year</th>
                {bands.map(b => (
                  <th key={b.id} className="py-1 pr-3 font-medium text-right whitespace-nowrap">
                    {b.label}
                  </th>
                ))}
                <th className="py-1 font-medium text-right">Total held</th>
              </tr>
            </thead>
            <tbody>
              {rows.map(r => (
                <tr key={r.fy} className="border-t" style={{ borderColor: 'var(--grid)' }}>
                  <td className="py-1 pr-3">{fy(r.fy)}</td>
                  {bands.map(b => (
                    <td key={b.id} className="py-1 pr-3 text-right">{usd(r[b.id])}</td>
                  ))}
                  <td className="py-1 text-right font-semibold">{usd(r.total)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </Card>
  )
}

/* ----------------------------------------------------------------- a signed net, by year */

function NetTip({ active, payload, what }: {
  active?: boolean; payload?: { payload: YearRow }[]; what: string
}) {
  if (!active || !payload?.length) return null
  const d = payload[0].payload
  return (
    <TipShell title={`${fy(d.fy)} — ${what}`}>
      <TipRow colour={IN} label="Received" value={usd(d.receipts)} />
      <TipRow colour={OUT} label="Spent" value={usd(d.disbursements)} />
      <div className="mt-1 pt-1 border-t" style={{ borderColor: 'var(--grid)' }}>
        <TipRow label={d.net >= 0 ? 'Balances rose by' : 'Balances fell by'}
          value={usd(Math.abs(d.net))} />
        <TipRow label="Held at year end" value={usd(d.carried)} />
      </div>
    </TipShell>
  )
}

export function Net({ rows, what }: { rows: YearRow[]; what: string }) {
  return (
    <Card>
      <div className="flex flex-wrap gap-x-4 gap-y-1 mb-2">
        <Chip color={IN}>Took in more than it spent</Chip>
        <Chip color={OUT}>Spent more than it took in</Chip>
      </div>
      <div style={{ height: 230 }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={rows} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
            <CartesianGrid stroke="var(--grid)" vertical={false} />
            <XAxis dataKey="fy" tickFormatter={fy} interval="preserveStartEnd"
              tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
              stroke="var(--axis)" tickLine={false} />
            <YAxis width={52} tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
              stroke="var(--axis)" tickLine={false} axisLine={false}
              tickFormatter={usdShort} />
            <Tooltip content={<NetTip what={what} />}
              cursor={{ fill: 'var(--surface-3)', opacity: 0.5 }} />
            <ReferenceLine y={0} stroke="var(--axis)" />
            <Bar dataKey="net" radius={[4, 4, 0, 0]}>
              {rows.map(r => <Cell key={r.fy} fill={r.net >= 0 ? IN : OUT} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <details className="mt-3">
        <summary className="text-[12px] cursor-pointer select-none min-h-[44px] flex items-center"
          style={{ color: 'var(--text-muted)' }}>The same numbers, as a table</summary>
        <div className="overflow-x-auto">
          <table className="w-full text-[12px] tnum mt-1">
            <thead>
              <tr className="text-left" style={{ color: 'var(--text-muted)' }}>
                <th className="py-1 pr-3 font-medium">Year</th>
                <th className="py-1 pr-3 font-medium text-right">Received</th>
                <th className="py-1 pr-3 font-medium text-right">Spent</th>
                <th className="py-1 pr-3 font-medium text-right">Net</th>
                <th className="py-1 font-medium text-right">Held at year end</th>
              </tr>
            </thead>
            <tbody>
              {rows.map(r => (
                <tr key={r.fy} className="border-t" style={{ borderColor: 'var(--grid)' }}>
                  <td className="py-1 pr-3">{fy(r.fy)}</td>
                  <td className="py-1 pr-3 text-right">{usd(r.receipts)}</td>
                  <td className="py-1 pr-3 text-right">{usd(r.disbursements)}</td>
                  <td className="py-1 pr-3 text-right font-semibold"
                    style={{ color: r.net >= 0 ? IN : OUT }}>{usd(r.net)}</td>
                  <td className="py-1 text-right">{usd(r.carried)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </Card>
  )
}

/* ----------------------------------------------------------------------- the movers */

export type MoverRow = {
  fund: string; group: string; band: string
  first: number; last: number; change: number
}

/** Change in the balance a fund carried, drawn as a bar from a shared zero.
 *
 *  Built by hand rather than in Recharts: the label a reader needs is the FUND NAME, it
 *  is long, and a horizontal bar chart with a 20rem category axis is unreadable on a
 *  phone. This lays the name above its own bar and the two figures below it, which
 *  reflows to one column without a scroll container.
 *
 *  Colour is the diverging pair, by SIGN, not by rank — re-sorting the list never
 *  repaints a fund the reader has already learned. */
export function Movers({ rows, firstFy, lastFy }: {
  rows: MoverRow[]; firstFy: number; lastFy: number
}) {
  const span = Math.max(...rows.map(r => Math.abs(r.change)), 1)
  return (
    <Card>
      <p className="text-[11.5px] mb-3" style={{ color: 'var(--text-muted)' }}>
        Change in the balance carried forward, {fy(firstFy)} to {fy(lastFy)}
      </p>
      <ul>
        {rows.map(r => {
          const w = `${(Math.abs(r.change) / span) * 50}%`
          const up = r.change >= 0
          return (
            <li key={r.fund} className="border-t pt-2.5 pb-3" style={{ borderColor: 'var(--grid)' }}>
              <div className="flex items-baseline justify-between gap-3">
                <p className="text-[13px] font-semibold leading-tight">{r.fund}</p>
                <p className="text-[12.5px] tnum font-bold shrink-0"
                  style={{ color: up ? IN : OUT }}>
                  {up ? '+' : '−'}{usd(Math.abs(r.change)).replace('-', '')}
                </p>
              </div>
              <div className="relative h-2.5 mt-2 rounded-full"
                style={{ background: 'var(--grid)' }}>
                <div className="absolute inset-y-0 w-px" style={{ left: '50%', background: 'var(--axis)' }} />
                <div className="absolute inset-y-0 rounded-full"
                  style={{
                    width: w, background: up ? IN : OUT,
                    left: up ? '50%' : undefined, right: up ? undefined : '50%',
                    boxShadow: '0 0 0 2px var(--surface-1)',
                  }} />
              </div>
              <p className="text-[11.5px] tnum mt-1.5" style={{ color: 'var(--text-secondary)' }}>
                {usd(r.first)} <span style={{ color: 'var(--text-muted)' }}>&rarr;</span> {usd(r.last)}
                <span style={{ color: 'var(--text-muted)' }}> &middot; {r.group.toLowerCase()}</span>
              </p>
            </li>
          )
        })}
      </ul>
    </Card>
  )
}

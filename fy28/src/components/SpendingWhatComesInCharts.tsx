import {
  Bar, BarChart, CartesianGrid, ComposedChart, Legend, Line, ReferenceLine, ResponsiveContainer,
  Tooltip, XAxis, YAxis, Cell,
} from 'recharts'
import type { ChartProps } from './analysisCharts'

/* The charts for /analysis/spending-what-comes-in, drawn from /data/spending-what-comes-in.json,
 * which scripts/build_spending_what_comes_in.py writes in the same pass as the markdown. Rule
 * 7f: the SVGs beside the markdown stay for /docs and the PDF; the web page draws these.
 *
 * Nothing here computes a figure (rule 2). Every in, out and net arrives in the payload. */

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
const IN = '#2f8f4e'
const OUT = '#dc2626'

type Yr = { fy: number; in: number; out: number; net: number }
type Kind = { key: string; label: string; short: string; years: Yr[]; in: number; out: number; net: number }
type Fund = { fund: string; kind: string; name: string; years: Yr[]; net: number; active: boolean;
  years_out_above_in: number }
type AthYr = { fy: number; gf_spent: number; fund_spent: number; fees_in: number; fund_share_pct: number }
type Payload = { kinds: Kind[]; funds: Fund[]; athletics: { years: AthYr[] } }

/** THE SIGNATURE: one panel per kind of fund, money in beside money out for each of the four
 *  closed years, every panel on ONE dollar scale so the size of each kind reads as well as
 *  its direction. */
export function SpendingWhatComesInKinds({ data }: ChartProps) {
  const { kinds } = data as Payload
  const hi = Math.max(...kinds.flatMap(k => k.years.flatMap(y => [y.in, y.out]))) * 1.05
  return (
    <div>
      <div className="grid gap-x-5 gap-y-6"
        style={{ gridTemplateColumns: 'repeat(auto-fit,minmax(240px,1fr))' }}>
        {kinds.map(k => {
          const rows = k.years.map(y => ({ ...y, fy: `FY${String(y.fy).slice(2)}` }))
          return (
            <div key={k.key} style={{ minWidth: 0 }}>
              <div className="text-[12.5px] font-semibold" style={{ color: 'var(--text-primary)' }}>
                {k.short}
              </div>
              <div className="text-[11px]" style={{ color: k.net < 0 ? OUT : IN }}>
                four years: {usdk(k.net)} {k.net < 0 ? 'more out than in' : 'more in than out'}
              </div>
              <div style={{ width: '100%', height: 140 }}>
                <ResponsiveContainer>
                  <BarChart data={rows} margin={{ top: 6, right: 4, left: 0, bottom: 0 }}>
                    <CartesianGrid stroke="var(--grid)" vertical={false} />
                    <XAxis dataKey="fy" tick={tick} />
                    <YAxis domain={[0, hi]} tickFormatter={usdk} width={46} tick={tick} />
                    <Tooltip contentStyle={box}
                      formatter={(v, name) => [usd(N(v)), String(name)]}
                      labelFormatter={(l, p) => {
                        const r = p?.[0]?.payload as Yr | undefined
                        return r ? `${l} · net ${usd(r.net)}` : String(l)
                      }} />
                    <Bar dataKey="in" name="came in" fill={IN} isAnimationActive={false} />
                    <Bar dataKey="out" name="went out" fill={OUT} isAnimationActive={false} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          )
        })}
      </div>
      <div className="mt-2 flex gap-4 text-[11.5px]" style={{ color: 'var(--text-muted)' }}>
        <span><span style={{ display: 'inline-block', width: 10, height: 10, background: IN, marginRight: 4 }} />came in</span>
        <span><span style={{ display: 'inline-block', width: 10, height: 10, background: OUT, marginRight: 4 }} />went out</span>
      </div>
    </div>
  )
}

/** Each of the fourteen funds that moved money, in minus out per year: green above the line
 *  where more came in, red below where more went out. One shared scale. */
export function SpendingWhatComesInFunds({ data }: ChartProps) {
  const funds = (data as Payload).funds.filter(f => f.active && f.kind !== 'grants')
  const m = Math.max(...funds.flatMap(f => f.years.map(y => Math.abs(y.net)))) * 1.05
  return (
    <div className="grid gap-x-5 gap-y-5"
      style={{ gridTemplateColumns: 'repeat(auto-fit,minmax(200px,1fr))' }}>
      {funds.map(f => {
        const rows = f.years.map(y => ({ ...y, fy: `FY${String(y.fy).slice(2)}` }))
        return (
          <div key={f.fund} style={{ minWidth: 0 }}>
            <div className="text-[12px] font-semibold" style={{ color: 'var(--text-primary)' }}>
              {f.name} <span style={{ color: 'var(--text-muted)', fontWeight: 400 }}>({f.fund})</span>
            </div>
            <div className="text-[10.5px]" style={{ color: 'var(--text-muted)' }}>
              four years {usd(f.net)} · out above in {f.years_out_above_in} of {f.years.length} years
            </div>
            <div style={{ width: '100%', height: 110 }}>
              <ResponsiveContainer>
                <BarChart data={rows} margin={{ top: 4, right: 4, left: 0, bottom: 0 }}>
                  <XAxis dataKey="fy" tick={tick} />
                  <YAxis domain={[-m, m]} tickFormatter={usdk} width={44} tick={tick} />
                  <ReferenceLine y={0} stroke="var(--text-muted)" />
                  <Tooltip contentStyle={box}
                    formatter={(v) => [usd(N(v)), 'in minus out']}
                    labelFormatter={(l, p) => {
                      const r = p?.[0]?.payload as Yr | undefined
                      return r ? `${l} · in ${usd(r.in)} · out ${usd(r.out)}` : String(l)
                    }} />
                  <Bar dataKey="net" isAnimationActive={false}>
                    {rows.map(r => <Cell key={r.fy} fill={r.net < 0 ? OUT : IN} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        )
      })}
    </div>
  )
}

/** Athletics spending as the books record it: the general fund under function 3510 and the
 *  fee fund 1301, stacked, with the fees the fund received as a line. */
export function SpendingWhatComesInAthletics({ data }: ChartProps) {
  const rows = (data as Payload).athletics.years.map(y => ({ ...y, fy: `FY${y.fy}` }))
  return (
    <div style={{ width: '100%', height: 320 }}>
      <ResponsiveContainer>
        <ComposedChart data={rows} margin={{ top: 8, right: 8, left: 4, bottom: 4 }}>
          <CartesianGrid stroke="var(--grid)" vertical={false} />
          <XAxis dataKey="fy" tick={tick} />
          <YAxis tickFormatter={usdk} width={52} tick={tick} />
          <Tooltip contentStyle={box} formatter={(v, name) => [usd(N(v)), String(name)]}
            labelFormatter={(l, p) => {
              const r = p?.[0]?.payload as AthYr | undefined
              return r ? `${l} · fee fund paid ${r.fund_share_pct}% of the two` : String(l)
            }} />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <Bar dataKey="gf_spent" name="General fund, function 3510" stackId="a" fill="#2b6cb0"
            isAnimationActive={false} />
          <Bar dataKey="fund_spent" name="Athletics fee fund 1301 spent" stackId="a" fill={IN}
            isAnimationActive={false} />
          <Line dataKey="fees_in" name="Fees received into 1301" stroke="var(--text-primary)"
            strokeWidth={2.5} dot={{ r: 3 }} isAnimationActive={false} />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}

import { Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis, Legend } from 'recharts'
import type { Tab } from '../routes'
import { Conclusions, Grain, H2, MoreReports, NotEstablished, Provenance, ReportShell, Stat, useReport } from '../components/report'
import type { Conclusion, Source } from '../components/report'

const TAB: Tab = 'circuitbreaker'
const DATA = '/data/circuit-breaker.json'

/** THE CIRCUIT BREAKER, FY2006 to FY2026. Page 8 of the build order. The mechanism is
 *  stated at the top because the name explains nothing: a threshold deducted per child,
 *  then a share of the rest, pro-rated to whatever the Legislature appropriated.
 *
 *  Rule 7b: conclusions, then the series, then the neighbours and the raw table. */

type Year = {
  fy: number; children: number; eligible: number; threshold: number; claim: number; paid: number
  transport: number; extra: number; per_child: number | null; threshold_per_child: number | null
  paid_share_of_claim: number | null; paid_share_of_eligible: number | null; check: string
}
type Payload = {
  about: string; grain: string; mechanism: string; first_fy: number; last_fy: number
  series: Year[]
  peers: { district: string; children: number; per_child: number; paid_share: number | null }[]
  state: { fy: number; children: number; eligible: number; paid: number }
  sources: Source[]; not_established: string[]; conclusions: Conclusion[]
}

const AXIS = { fontSize: 11, fill: 'var(--text-muted)' }
const n0 = (n: number) => n.toLocaleString('en-US')
const usd = (n: number) => '$' + Math.round(n).toLocaleString('en-US')
const usdk = (n: number) => '$' + Math.round(n / 1000) + 'k'
const pct1 = (x: number) => `${(x * 100).toFixed(1)}%`

function Box({ children }: { children: React.ReactNode }) {
  return <div className="card p-2.5 text-[12px]" style={{ minWidth: 190 }}>{children}</div>
}

export function CircuitBreaker() {
  const { d, err } = useReport<Payload>('circuit-breaker.json')
  const last = d ? d.series[d.series.length - 1] : null
  return (
    <ReportShell tab={TAB}
      title={d && last ? `${n0(last.children)} children, ${usd(last.paid)} back from the state` : 'The circuit breaker'}
      standfirst={d && last ? <>The state reimburses part of what the costliest special education placements cost — after deducting {usd(last.threshold_per_child ?? 0)} per child, and only at the share it appropriated that year. Twenty-one years of what Lunenburg claimed and what came back.</> : undefined}
      err={err} loading={!d && !err} dataUrl={DATA}>
      {d && <Report d={d} />}
    </ReportShell>
  )
}

function Report({ d }: { d: Payload }) {
  const last = d.series[d.series.length - 1]
  const money = d.series.map(y => ({ fy: `FY${y.fy}`, eligible: y.eligible, threshold: y.threshold, paid: y.paid, claim: y.claim }))
  const kids = d.series.map(y => ({ fy: `FY${y.fy}`, children: y.children, per_child: y.per_child ?? 0 }))
  const share = d.series.map(y => ({ fy: `FY${y.fy}`, share: y.paid_share_of_claim ?? 0 }))
  return (
    <>
      <section data-section="conclusions">
        <div className="flex flex-wrap gap-x-10 gap-y-5 mt-8">
          <Stat value={usd(last.paid)} tone="var(--series-cost)">reimbursed in FY{last.fy}, on {usd(last.eligible)} of eligible costs</Stat>
          <Stat value={n0(last.children)}>children claimed &mdash; {n0(Math.max(...d.series.map(y => y.children)))} at the most</Stat>
          <Stat value={pct1(last.paid_share_of_claim ?? 0)}>of the claim paid this year; the statute allows up to 75%</Stat>
        </div>
        <div className="card p-4 mt-6 max-w-3xl">
          <p className="text-[10.5px] font-bold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>How it works</p>
          <p className="text-sm mt-1" style={{ color: 'var(--text-secondary)' }}>{d.mechanism}</p>
        </div>
        <Grain>{d.grain}</Grain>
        <Conclusions rows={d.conclusions} />
      </section>

      <section data-section="categorical">
        <H2>The money, year by year</H2>
        <p className="text-sm max-w-3xl" style={{ color: 'var(--text-secondary)' }}>
          Eligible costs, the threshold deducted, and what the state paid. The gap between the top line and the bottom is the district&rsquo;s own share.
        </p>
        <div style={{ width: '100%', height: 320 }} className="mt-4 avoid-break">
          <ResponsiveContainer>
            <LineChart data={money} margin={{ top: 8, right: 8, left: 0, bottom: 4 }}>
              <CartesianGrid stroke="var(--grid)" vertical={false} />
              <XAxis dataKey="fy" tick={AXIS} stroke="var(--axis)" interval={2} />
              <YAxis tick={AXIS} stroke="var(--axis)" tickFormatter={(v: number) => usdk(v)} />
              <Tooltip content={({ active, payload, label }) => {
                if (!active || !payload?.length) return null
                const r = payload[0].payload as typeof money[number]
                return <Box><p className="font-bold">{label}</p><p>eligible {usd(r.eligible)}</p><p>threshold {usd(r.threshold)} · claim {usd(r.claim)}</p><p className="font-semibold">paid {usd(r.paid)}</p></Box>
              }} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Line type="monotone" dataKey="eligible" name="eligible costs" stroke="var(--text-primary)" strokeWidth={2} dot={false} isAnimationActive={false} />
              <Line type="monotone" dataKey="threshold" name="threshold deducted" stroke="var(--series-revenue)" strokeDasharray="4 3" dot={false} isAnimationActive={false} />
              <Line type="monotone" dataKey="paid" name="paid by the state" stroke="var(--series-cost)" strokeWidth={2} dot={false} isAnimationActive={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <H2>Children claimed, and the cost of each</H2>
        <div className="grid gap-6 lg:grid-cols-2">
          <div style={{ width: '100%', height: 260 }} className="avoid-break">
            <ResponsiveContainer>
              <BarChart data={kids} margin={{ top: 8, right: 8, left: 0, bottom: 4 }}>
                <CartesianGrid stroke="var(--grid)" vertical={false} />
                <XAxis dataKey="fy" tick={AXIS} stroke="var(--axis)" interval={3} />
                <YAxis tick={AXIS} stroke="var(--axis)" />
                <Tooltip cursor={{ fill: 'var(--surface-3)' }} content={({ active, payload, label }) => active && payload?.length ? <Box><p className="font-bold">{label}</p><p>{n0((payload[0].payload as { children: number }).children)} children claimed</p></Box> : null} />
                <Bar dataKey="children" name="children claimed" fill="var(--series-cost)" radius={[2, 2, 0, 0]} isAnimationActive={false} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div style={{ width: '100%', height: 260 }} className="avoid-break">
            <ResponsiveContainer>
              <LineChart data={kids} margin={{ top: 8, right: 8, left: 0, bottom: 4 }}>
                <CartesianGrid stroke="var(--grid)" vertical={false} />
                <XAxis dataKey="fy" tick={AXIS} stroke="var(--axis)" interval={3} />
                <YAxis tick={AXIS} stroke="var(--axis)" tickFormatter={(v: number) => usdk(v)} />
                <Tooltip content={({ active, payload, label }) => active && payload?.length ? <Box><p className="font-bold">{label}</p><p>{usd((payload[0].payload as { per_child: number }).per_child)} eligible cost per child claimed</p></Box> : null} />
                <Line type="monotone" dataKey="per_child" name="eligible cost per child" stroke="var(--series-revenue)" strokeWidth={2} dot={false} isAnimationActive={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        <H2>The share the state paid</H2>
        <div style={{ width: '100%', height: 220 }} className="mt-3 avoid-break">
          <ResponsiveContainer>
            <BarChart data={share} margin={{ top: 8, right: 8, left: 0, bottom: 4 }}>
              <CartesianGrid stroke="var(--grid)" vertical={false} />
              <XAxis dataKey="fy" tick={AXIS} stroke="var(--axis)" interval={3} />
              <YAxis tick={AXIS} stroke="var(--axis)" domain={[0, 0.8]} tickFormatter={(v: number) => `${Math.round(v * 100)}%`} />
              <Tooltip cursor={{ fill: 'var(--surface-3)' }} content={({ active, payload, label }) => active && payload?.length ? <Box><p className="font-bold">{label}</p><p>{pct1((payload[0].payload as { share: number }).share)} of the claim paid</p></Box> : null} />
              <Bar dataKey="share" name="share of claim paid" fill="var(--series-cost)" radius={[2, 2, 0, 0]} isAnimationActive={false} />
            </BarChart>
          </ResponsiveContainer>
        </div>
        <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>The statute allows up to 75%; the years below 70% are years the Legislature’s appropriation fell short and every district was pro-rated.</p>

        <H2>The neighbours, FY{d.state.fy}</H2>
        <table className="w-full text-sm max-w-2xl">
          <thead><tr className="text-[10px] font-bold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>
            <th className="text-left py-1.5">district</th><th className="text-right py-1.5">children</th><th className="text-right py-1.5">per child</th><th className="text-right py-1.5">share paid</th></tr></thead>
          <tbody>{[...d.peers].sort((a, b) => b.per_child - a.per_child).map(p => (
            <tr key={p.district} style={{ borderTop: '1px solid var(--grid)', fontWeight: p.district === 'Lunenburg' ? 600 : 400 }}>
              <td className="py-1.5">{p.district}</td><td className="text-right tnum">{n0(p.children)}</td><td className="text-right tnum">{usd(p.per_child)}</td><td className="text-right tnum">{p.paid_share != null ? pct1(p.paid_share) : '—'}</td></tr>))}</tbody>
        </table>
        <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>Statewide: {n0(d.state.children)} children claimed, {usd(d.state.eligible)} eligible, {usd(d.state.paid)} paid.</p>
      </section>

      <section data-section="raw">
        <H2>Every year</H2>
        <div className="overflow-x-auto">
          <table className="text-xs" style={{ minWidth: 720 }}>
            <thead><tr className="text-[10px] font-bold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>
              <th className="text-left py-1 pr-3">fy</th><th className="text-right px-1.5">children</th><th className="text-right px-1.5">eligible</th><th className="text-right px-1.5">threshold</th><th className="text-right px-1.5">claim</th><th className="text-right px-1.5">paid</th><th className="text-right px-1.5">transport</th><th className="text-right px-1.5">share</th></tr></thead>
            <tbody>{d.series.map(y => (
              <tr key={y.fy} style={{ borderTop: '1px solid var(--grid)' }}>
                <td className="py-1 pr-3 tnum">FY{y.fy}</td><td className="text-right tnum px-1.5">{y.children}</td><td className="text-right tnum px-1.5">{usd(y.eligible)}</td><td className="text-right tnum px-1.5">{usd(y.threshold)}</td><td className="text-right tnum px-1.5">{usd(y.claim)}</td><td className="text-right tnum px-1.5">{usd(y.paid)}</td><td className="text-right tnum px-1.5">{y.transport ? usd(y.transport) : ''}</td><td className="text-right tnum px-1.5">{y.paid_share_of_claim != null ? pct1(y.paid_share_of_claim) : ''}</td></tr>))}</tbody>
          </table>
        </div>
        <NotEstablished rows={d.not_established} closes="The district’s own out-of-district placement list by setting and cost, which it holds and does not publish." />
        <Provenance sources={d.sources} />
        <MoreReports here={TAB} />
      </section>
    </>
  )
}

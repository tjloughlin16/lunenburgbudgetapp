import { Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis, Legend } from 'recharts'
import type { Tab } from '../routes'
import { Conclusions, Grain, H2, MoreReports, NotEstablished, Provenance, ReportShell, Stat, useReport } from '../components/report'
import type { Conclusion, Source } from '../components/report'

const TAB: Tab = 'ap'
const DATA = '/data/ap.json'

/** ADVANCED PLACEMENT, SY2007 to SY2025. Page 9 of the build order. Three counts that are
 *  not the same thing -- children, sittings, tests at a score -- kept apart on every
 *  chart, and a participation ratio labelled the approximation it is. */

type Year = { sy: number; takers: number; sittings: number; per_taker: number | null; g1112: number | null; share_1112: number | null; pass_share: number | null; scores: number[] | null }
type Family = { family: string; then: number | null; now: number | null; takers_now: number; pass_share: number | null; basis_now: string; basis_then: string }
type Payload = {
  about: string; grain: string; first_sy: number; last_sy: number; compare_sy: number
  years: Year[]; families: Family[]
  sources: Source[]; not_established: string[]; conclusions: Conclusion[]
}

const AXIS = { fontSize: 11, fill: 'var(--text-muted)' }
const n0 = (n: number) => n.toLocaleString('en-US')
const pct0 = (x: number) => `${Math.round(x * 100)}%`
const pct1 = (x: number) => `${(x * 100).toFixed(1)}%`

function Box({ children }: { children: React.ReactNode }) {
  return <div className="card p-2.5 text-[12px]" style={{ minWidth: 180 }}>{children}</div>
}

export function AdvancedPlacement() {
  const { d, err } = useReport<Payload>('ap.json')
  const last = d ? d.years[d.years.length - 1] : null
  return (
    <ReportShell tab={TAB}
      title={d && last ? `${n0(last.takers)} students sat an AP exam; ${pct1(last.pass_share ?? 0)} of the tests scored 3 or better` : 'Advanced Placement'}
      standfirst={d && last ? <>About {pct0(last.share_1112 ?? 0)} of Lunenburg High&rsquo;s juniors and seniors sat at least one AP exam in SY{last.sy}, the tests scored 3 or better at the highest rate in nineteen years — and three in four sittings were English or history.</> : undefined}
      err={err} loading={!d && !err} dataUrl={DATA}>
      {d && <Report d={d} />}
    </ReportShell>
  )
}

function Report({ d }: { d: Payload }) {
  const last = d.years[d.years.length - 1]
  const series = d.years.map(y => ({ sy: `SY${y.sy}`, takers: y.takers, sittings: y.sittings, share: y.share_1112, pass: y.pass_share }))
  const scores = last.scores ? [1, 2, 3, 4, 5].map((s, i) => ({ score: String(s), tests: last.scores![i] })) : []
  return (
    <>
      <section data-section="conclusions">
        <div className="flex flex-wrap gap-x-10 gap-y-5 mt-8">
          <Stat value={n0(last.takers)} tone="var(--series-cost)">students sat at least one AP exam in SY{last.sy}; {n0(last.sittings)} sittings</Stat>
          <Stat value={pct1(last.pass_share ?? 0)}>of tests scored 3 or better</Stat>
          <Stat value={pct0(last.share_1112 ?? 0)}>of the 11th and 12th grades, approximately</Stat>
        </div>
        <Grain>{d.grain}</Grain>
        <Conclusions rows={d.conclusions} />
      </section>

      <section data-section="categorical">
        <H2>Who sits, year by year</H2>
        <div style={{ width: '100%', height: 300 }} className="mt-4 avoid-break">
          <ResponsiveContainer>
            <LineChart data={series} margin={{ top: 8, right: 8, left: 0, bottom: 4 }}>
              <CartesianGrid stroke="var(--grid)" vertical={false} />
              <XAxis dataKey="sy" tick={AXIS} stroke="var(--axis)" interval={2} />
              <YAxis tick={AXIS} stroke="var(--axis)" />
              <Tooltip content={({ active, payload, label }) => active && payload?.length ? (() => { const r = payload[0].payload as typeof series[number]; return <Box><p className="font-bold">{label}</p><p>{n0(r.takers)} students · {n0(r.sittings)} sittings</p>{r.share != null && <p style={{ color: 'var(--text-muted)' }}>about {pct0(r.share)} of grades 11–12</p>}</Box> })() : null} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Line type="monotone" dataKey="takers" name="students who sat an exam" stroke="var(--series-cost)" strokeWidth={2} dot={false} isAnimationActive={false} />
              <Line type="monotone" dataKey="sittings" name="sittings" stroke="var(--text-muted)" strokeDasharray="4 3" dot={false} isAnimationActive={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <H2>How the tests scored</H2>
        <div className="grid gap-6 lg:grid-cols-2">
          <div style={{ width: '100%', height: 260 }} className="avoid-break">
            <ResponsiveContainer>
              <LineChart data={series} margin={{ top: 8, right: 8, left: 0, bottom: 4 }}>
                <CartesianGrid stroke="var(--grid)" vertical={false} />
                <XAxis dataKey="sy" tick={AXIS} stroke="var(--axis)" interval={2} />
                <YAxis tick={AXIS} stroke="var(--axis)" domain={[0.5, 1]} tickFormatter={(v: number) => pct0(v)} />
                <Tooltip content={({ active, payload, label }) => active && payload?.length ? <Box><p className="font-bold">{label}</p><p>{pct1((payload[0].payload as { pass: number }).pass)} of tests scored 3–5</p></Box> : null} />
                <Line type="monotone" dataKey="pass" name="share of tests at 3 or better" stroke="var(--status-good)" strokeWidth={2} dot={false} isAnimationActive={false} connectNulls />
              </LineChart>
            </ResponsiveContainer>
          </div>
          <div style={{ width: '100%', height: 260 }} className="avoid-break">
            <ResponsiveContainer>
              <BarChart data={scores} margin={{ top: 8, right: 8, left: 0, bottom: 4 }}>
                <CartesianGrid stroke="var(--grid)" vertical={false} />
                <XAxis dataKey="score" tick={AXIS} stroke="var(--axis)" label={{ value: `score, SY${last.sy}`, position: 'insideBottom', offset: -2, fontSize: 11, fill: 'var(--text-muted)' }} />
                <YAxis tick={AXIS} stroke="var(--axis)" />
                <Tooltip cursor={{ fill: 'var(--surface-3)' }} content={({ active, payload, label }) => active && payload?.length ? <Box><p className="font-bold">score {label}</p><p>{n0((payload[0].payload as { tests: number }).tests)} tests</p></Box> : null} />
                <Bar dataKey="tests" fill="var(--series-cost)" radius={[2, 2, 0, 0]} isAnimationActive={false} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
        <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>Tests, not students. A student who sat three exams is three bars’ worth.</p>

        <H2>In what subjects</H2>
        <table className="w-full text-sm max-w-3xl">
          <thead><tr className="text-[10px] font-bold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>
            <th className="text-left py-1.5">subject family</th><th className="text-right py-1.5">SY{d.compare_sy}</th><th className="text-right py-1.5">SY{d.last_sy}</th><th className="text-right py-1.5">students</th><th className="text-right py-1.5">3 or better</th></tr></thead>
          <tbody>{d.families.map(f => (
            <tr key={f.family} style={{ borderTop: '1px solid var(--grid)' }}>
              <td className="py-1.5">{f.family}</td>
              <td className="text-right tnum">{f.then == null ? <span style={{ color: 'var(--text-muted)' }}>suppressed</span> : n0(f.then)}{f.basis_then.startsWith('performance') && f.then != null ? <span title={f.basis_then} style={{ color: 'var(--text-muted)' }}>*</span> : ''}</td>
              <td className="text-right tnum">{f.now == null ? <span style={{ color: 'var(--text-muted)' }}>suppressed</span> : n0(f.now)}{f.basis_now.startsWith('performance') && f.now != null ? <span title={f.basis_now} style={{ color: 'var(--text-muted)' }}>*</span> : ''}</td>
              <td className="text-right tnum">{n0(f.takers_now)}</td>
              <td className="text-right tnum">{f.pass_share != null ? pct1(f.pass_share) : <span style={{ color: 'var(--text-muted)' }}>—</span>}</td></tr>))}</tbody>
        </table>
        <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>Sittings by subject family, DESE’s own rollups. * DESE suppresses small groups in the participation file; the count is taken from the performance file, which reports the same tests. A dash is suppressed in both.</p>
      </section>

      <section data-section="raw">
        <H2>Every year</H2>
        <div className="overflow-x-auto">
          <table className="text-xs" style={{ minWidth: 560 }}>
            <thead><tr className="text-[10px] font-bold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>
              <th className="text-left py-1 pr-3">year</th><th className="text-right px-1.5">students</th><th className="text-right px-1.5">sittings</th><th className="text-right px-1.5">grades 11–12</th><th className="text-right px-1.5">share</th><th className="text-right px-1.5">3 or better</th></tr></thead>
            <tbody>{d.years.map(y => (
              <tr key={y.sy} style={{ borderTop: '1px solid var(--grid)' }}>
                <td className="py-1 pr-3 tnum">SY{y.sy}</td><td className="text-right tnum px-1.5">{n0(y.takers)}</td><td className="text-right tnum px-1.5">{n0(y.sittings)}</td><td className="text-right tnum px-1.5">{y.g1112 != null ? n0(y.g1112) : ''}</td><td className="text-right tnum px-1.5">{y.share_1112 != null ? pct0(y.share_1112) : ''}</td><td className="text-right tnum px-1.5">{y.pass_share != null ? pct1(y.pass_share) : ''}</td></tr>))}</tbody>
          </table>
        </div>
        <NotEstablished rows={d.not_established} closes="The high school’s program of studies for each year, which lists the AP courses offered; the district publishes it and the archive does not yet hold it." />
        <Provenance sources={d.sources} />
        <MoreReports here={TAB} />
      </section>
    </>
  )
}

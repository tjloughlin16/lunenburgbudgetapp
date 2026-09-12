import {
  Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis, Legend,
} from 'recharts'
import type { Tab } from '../routes'
import {
  Conclusions, Grain, H2, MoreReports, NotEstablished, Provenance, ReportShell, Stat, useReport,
} from '../components/report'
import type { Conclusion, Source } from '../components/report'

const TAB: Tab = 'enrollment'
const DATA = '/data/enrollment.json'

/** WHO IS IN THE SCHOOLS. Page 7 of the build order: the denominator every other page
 *  divides by, shown on its own. DESE's headcount, FY1994 to FY2026.
 *
 *  Rule 7b: conclusions, then the series by grade band and student group, then the
 *  schools and the neighbours, then what the file does not carry.
 *
 *  THE ONE DRAWING RULE: low-income is three series with two definition changes, and
 *  they are drawn as three lines that do not touch. A reader who saw one line would
 *  read a policy change as a change in the town. */

type Year = {
  fy: number; total: number; check: string; k5: number; g68: number; g912: number; sp: number
  swd: number | null; swd_pct: number | null; el: number | null
  low_income: number | null; low_income_pct: number | null; econ_dis: number | null; high_needs: number | null
}
type Payload = {
  about: string; grain: string; first_fy: number; last_fy: number; base_fy: number
  peak: { fy: number; total: number }; trough: { fy: number; total: number }
  plateau: { since: number; low: number; high: number }
  district: Year[]
  bands: { band: string; first: number; last: number; pct: number }[]
  schools: { fy: number; school: string; total: number }[]
  peers: { district: string; first: number; last: number; change: number; pct: number }[]
  low_income: { old: { fy: number; n: number; pct: number }[]; econ: { fy: number; n: number }[]; new: { fy: number; n: number; pct: number }[]; note: string }
  sources: Source[]; not_established: string[]; conclusions: Conclusion[]
}

const AXIS = { fontSize: 11, fill: 'var(--text-muted)' }
const n0 = (n: number) => n.toLocaleString('en-US')
const pct1 = (x: number) => `${(x * 100).toFixed(1)}%`

function Box({ children }: { children: React.ReactNode }) {
  return <div className="card p-2.5 text-[12px]" style={{ minWidth: 170 }}>{children}</div>
}

export function Enrollment() {
  const { d, err } = useReport<Payload>('enrollment.json')
  return (
    <ReportShell tab={TAB}
      title={d ? `${n0(d.district[d.district.length - 1].total)} children, and the fall that stopped in FY${d.trough.fy}` : 'Who is in the schools'}
      standfirst={d ? <>Lunenburg&rsquo;s enrolment fell {pct1((d.peak.total - d.trough.total) / d.peak.total)} from FY{d.peak.fy} to FY{d.trough.fy} and has held between {n0(d.plateau.low)} and {n0(d.plateau.high)} since. The decline was a high-school decline; the number of children with disabilities never moved.</> : undefined}
      err={err} loading={!d && !err} dataUrl={DATA}>
      {d && <Report d={d} />}
    </ReportShell>
  )
}

function Report({ d }: { d: Payload }) {
  const last = d.district[d.district.length - 1]
  const base = d.district.find(y => y.fy === d.base_fy)!
  const series = d.district.map(y => ({ fy: `FY${y.fy}`, total: y.total, k5: y.k5, g68: y.g68, g912: y.g912 }))
  const groups = d.district.filter(y => y.fy >= d.base_fy).map(y => ({
    fy: `FY${y.fy}`, swd: y.swd, el: y.el,
    li_old: y.fy <= 2014 ? y.low_income : null, econ: y.econ_dis, li_new: y.fy >= 2022 ? y.low_income : null,
  }))
  const schoolYears = Array.from(new Set(d.schools.map(s => s.fy))).sort()
  const schoolNames = Array.from(new Set(d.schools.map(s => s.school)))
  return (
    <>
      <section data-section="conclusions">
        <div className="flex flex-wrap gap-x-10 gap-y-5 mt-8">
          <Stat value={n0(last.total)}>children enrolled in FY{last.fy}, against {n0(d.peak.total)} at the FY{d.peak.fy} peak</Stat>
          <Stat value={pct1(Math.abs(d.bands[2].pct))} tone="var(--series-cost)">fewer in grades 9&ndash;12 than in FY{d.base_fy}; pre-K to grade 5 is down {pct1(Math.abs(d.bands[0].pct))}</Stat>
          <Stat value={n0(last.swd ?? 0)}>students with disabilities &mdash; {n0(base.swd ?? 0)} in FY{d.base_fy}</Stat>
        </div>
        <Grain>{d.grain}</Grain>
        <Conclusions rows={d.conclusions} />
      </section>

      <section data-section="categorical">
        <H2>The count, by grade band</H2>
        <p className="text-sm max-w-3xl" style={{ color: 'var(--text-secondary)' }}>
          Every district year DESE publishes, FY{d.first_fy} to FY{d.last_fy}. The three bands sum to the total (a handful of students past grade 12 make up the rest).
        </p>
        <div style={{ width: '100%', height: 320 }} className="mt-4 avoid-break">
          <ResponsiveContainer>
            <LineChart data={series} margin={{ top: 8, right: 8, left: 0, bottom: 4 }}>
              <CartesianGrid stroke="var(--grid)" vertical={false} />
              <XAxis dataKey="fy" tick={AXIS} stroke="var(--axis)" interval={3} />
              <YAxis tick={AXIS} stroke="var(--axis)" tickFormatter={(v: number) => n0(v)} />
              <Tooltip content={({ active, payload, label }) => {
                if (!active || !payload?.length) return null
                const r = payload[0].payload as typeof series[number]
                return <Box><p className="font-bold">{label}</p><p>{n0(r.total)} children</p>
                  <p style={{ color: 'var(--text-muted)' }}>pre-K–5 {n0(r.k5)} · 6–8 {n0(r.g68)} · 9–12 {n0(r.g912)}</p></Box>
              }} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Line type="monotone" dataKey="total" name="all" stroke="var(--text-primary)" strokeWidth={2} dot={false} isAnimationActive={false} />
              <Line type="monotone" dataKey="k5" name="pre-K to 5" stroke="var(--series-cost)" dot={false} isAnimationActive={false} />
              <Line type="monotone" dataKey="g68" name="grades 6–8" stroke="var(--status-warning)" dot={false} isAnimationActive={false} />
              <Line type="monotone" dataKey="g912" name="grades 9–12" stroke="var(--series-revenue)" dot={false} isAnimationActive={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
        <table className="w-full text-sm mt-3 max-w-2xl">
          <thead><tr className="text-[10px] font-bold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>
            <th className="text-left py-1.5">band</th><th className="text-right py-1.5">FY{d.base_fy}</th><th className="text-right py-1.5">FY{d.last_fy}</th><th className="text-right py-1.5">change</th></tr></thead>
          <tbody>{d.bands.map(b => (
            <tr key={b.band} style={{ borderTop: '1px solid var(--grid)' }}>
              <td className="py-1.5">{b.band}</td><td className="text-right tnum">{n0(b.first)}</td><td className="text-right tnum">{n0(b.last)}</td>
              <td className="text-right tnum" style={{ color: b.pct < 0 ? 'var(--series-revenue)' : 'var(--text-primary)' }}>{b.pct > 0 ? '+' : ''}{pct1(b.pct)}</td></tr>))}</tbody>
        </table>

        <H2>Who the children are</H2>
        <p className="text-sm max-w-3xl" style={{ color: 'var(--text-secondary)' }}>
          Students with disabilities and English learners are one series each. <strong>Low-income is three</strong>, because DESE changed its definition twice — the lines deliberately do not join.
        </p>
        <div style={{ width: '100%', height: 320 }} className="mt-4 avoid-break">
          <ResponsiveContainer>
            <LineChart data={groups} margin={{ top: 8, right: 8, left: 0, bottom: 4 }}>
              <CartesianGrid stroke="var(--grid)" vertical={false} />
              <XAxis dataKey="fy" tick={AXIS} stroke="var(--axis)" interval={2} />
              <YAxis tick={AXIS} stroke="var(--axis)" tickFormatter={(v: number) => n0(v)} />
              <Tooltip content={({ active, payload, label }) => {
                if (!active || !payload?.length) return null
                const r = payload[0].payload as typeof groups[number]
                return <Box><p className="font-bold">{label}</p>
                  <p>{r.swd ?? '—'} with disabilities · {r.el ?? '—'} English learners</p>
                  <p style={{ color: 'var(--text-muted)' }}>{r.li_old != null ? `${r.li_old} low-income (lunch)` : r.econ != null ? `${r.econ} economically disadvantaged` : r.li_new != null ? `${r.li_new} low-income (new definition)` : ''}</p></Box>
              }} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Line type="monotone" dataKey="swd" name="students with disabilities" stroke="var(--series-cost)" strokeWidth={2} dot={false} isAnimationActive={false} connectNulls />
              <Line type="monotone" dataKey="el" name="English learners" stroke="var(--status-good)" dot={false} isAnimationActive={false} connectNulls />
              <Line type="monotone" dataKey="li_old" name="low-income (to FY2014)" stroke="var(--series-revenue)" dot={false} isAnimationActive={false} />
              <Line type="monotone" dataKey="econ" name="economically disadvantaged (FY2015–21)" stroke="var(--series-revenue)" strokeDasharray="4 3" dot={false} isAnimationActive={false} />
              <Line type="monotone" dataKey="li_new" name="low-income (from FY2022)" stroke="var(--series-revenue)" strokeWidth={2} dot={false} isAnimationActive={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
        <p className="text-xs mt-2 max-w-3xl" style={{ color: 'var(--text-muted)' }}>{d.low_income.note}</p>

        <H2>The neighbours</H2>
        <div style={{ width: '100%', height: 220 }} className="mt-3 avoid-break">
          <ResponsiveContainer>
            <BarChart data={d.peers.map(p => ({ district: p.district, fall: Math.abs(p.pct) }))} layout="vertical" margin={{ top: 4, right: 24, left: 8, bottom: 4 }}>
              <CartesianGrid stroke="var(--grid)" horizontal={false} />
              <XAxis type="number" tick={AXIS} stroke="var(--axis)" tickFormatter={(v: number) => `${Math.round(v * 100)}%`} />
              <YAxis type="category" dataKey="district" tick={AXIS} stroke="var(--axis)" width={150} />
              <Tooltip cursor={{ fill: 'var(--surface-3)' }} content={({ active, payload }) => {
                if (!active || !payload?.length) return null
                const p = d.peers.find(x => x.district === (payload[0].payload as { district: string }).district)!
                return <Box><p className="font-bold">{p.district}</p><p>{n0(p.first)} → {n0(p.last)} ({pct1(p.pct)})</p></Box>
              }} />
              <Bar dataKey="fall" radius={[0, 2, 2, 0]} isAnimationActive={false} fill="var(--series-cost)" />
            </BarChart>
          </ResponsiveContainer>
        </div>
        <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>Fall in enrolment, FY{d.base_fy} to FY{d.last_fy}. Ayer Shirley regionalised in FY2012 and has no FY{d.base_fy} row.</p>
      </section>

      <section data-section="raw">
        <H2>Each school, year by year</H2>
        <div className="overflow-x-auto">
          <table className="text-xs" style={{ minWidth: 640 }}>
            <thead><tr className="text-[10px] font-bold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>
              <th className="text-left py-1 pr-3">school</th>{schoolYears.filter((_, i) => i % 3 === 0 || i === schoolYears.length - 1).map(y => <th key={y} className="text-right py-1 px-1.5">FY{y}</th>)}</tr></thead>
            <tbody>{schoolNames.map(s => (
              <tr key={s} style={{ borderTop: '1px solid var(--grid)' }}>
                <td className="py-1 pr-3">{s}</td>
                {schoolYears.filter((_, i) => i % 3 === 0 || i === schoolYears.length - 1).map(y => {
                  const r = d.schools.find(x => x.school === s && x.fy === y)
                  return <td key={y} className="text-right tnum px-1.5">{r ? n0(r.total) : ''}</td>
                })}
              </tr>))}</tbody>
          </table>
        </div>
        <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>Every third year shown; schools appear and disappear as the district reorganised them. A blank is a school that did not exist under that name.</p>
        <NotEstablished rows={d.not_established} closes="DESE’s enrollment file carries no reason a count moved; the district’s own October 1 report and its birth-cohort projections would." />
        <Provenance sources={d.sources} />
        <MoreReports here={TAB} />
      </section>
    </>
  )
}

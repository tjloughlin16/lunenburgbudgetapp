import { FullVersion } from '../components/FullVersion'
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { Tab } from '../routes'
import { Conclusions, Grain, H2, MoreReports, NotEstablished, Provenance, ReportShell, Stat, useReport, splitConclusions } from '../components/report'
import type { Conclusion, Source } from '../components/report'

const TAB: Tab = 'homestudents'
const DATA = '/data/homes-and-students.json'

/** HOMES AND STUDENTS. TJ, 16 September 2026: "we can probably relate residential
 *  development to school enrollment right?! Im curious how we are building residential
 *  but the enrollment isnt increasing." Two counts this archive already held, set beside
 *  each other by scripts/build_homes_and_students.py: single-family parcels as DLS
 *  reports them, and DESE's headcount. Rule 7 governs the page: the lines crossing is a
 *  measurement; why they cross is not, and the card says so. */

type Row = { fy: number; homes: number; students: number; students_per_100_homes: number }
type Payload = {
  about: string; grain: string; first_fy: number; last_fy: number
  series: Row[]
  window5: { first_fy: number; last_fy: number; homes: number; students: number }
  sources: Source[]; not_established: string[]; conclusions: Conclusion[]
}

const AXIS = { fontSize: 11, fill: 'var(--text-muted)' }
const n0 = (n: number) => n.toLocaleString('en-US')
const signed = (n: number) => (n >= 0 ? '+' : '−') + n0(Math.abs(n))

function Box({ children }: { children: React.ReactNode }) {
  return <div className="card p-2.5 text-[12px]" style={{ minWidth: 170 }}>{children}</div>
}

export function HomesAndStudents() {
  const { d, err } = useReport<Payload>('homes-and-students.json')
  const first = d?.series[0], last = d?.series[d.series.length - 1]
  return (
    <ReportShell tab={TAB}
      title={d && first && last ? `${n0(last.homes - first.homes)} more homes, ${n0(Math.max(...d.series.map(r => r.students)) - last.students)} fewer students` : 'Homes and students'}
      standfirst={d && first && last ? <>Lunenburg has added single-family homes in every year the state records, FY{first.fy} to FY{last.fy}, and the schools have fewer children than they had. Two counts from two state files, and the one thing they cannot say between them is why.</> : undefined}
      err={err} loading={!d && !err} dataUrl={DATA}>
      {d && first && last && <Report d={d} first={first} last={last} />}
    </ReportShell>
  )
}

function Report({ d, first, last }: { d: Payload; first: Row; last: Row }) {
  const peak = d.series.reduce((a, b) => (b.students > a.students ? b : a))
  const series = d.series.map(r => ({ fy: `FY${r.fy}`, homes: r.homes, students: r.students, ratio: r.students_per_100_homes }))
  const [shortRows, moreRows] = splitConclusions(d.conclusions, undefined)
  return (
    <>
      <section data-section="conclusions" data-short="">
        <div className="flex flex-wrap gap-x-10 gap-y-5 mt-8">
          <Stat value={n0(last.homes)}>single-family homes in FY{last.fy}, from {n0(first.homes)} in FY{first.fy}</Stat>
          <Stat value={n0(last.students)} tone="var(--series-cost)">students in FY{last.fy}, from a peak of {n0(peak.students)} in FY{peak.fy}</Stat>
          <Stat value={last.students_per_100_homes.toFixed(1)}>students for every hundred homes &mdash; {first.students_per_100_homes.toFixed(1)} in FY{first.fy}</Stat>
          <Stat value={signed(d.window5.homes)} tone="var(--series-revenue)">homes in the last five years; students {signed(d.window5.students)}</Stat>
        </div>
        <Grain>{d.grain}</Grain>
        <Conclusions rows={shortRows} />
      </section>
      <FullVersion>
      {moreRows.length > 0 && (
        <>
          <H2 id="more-findings">The other findings</H2>
          <Conclusions rows={moreRows} noAsk short={false} />
        </>
      )}

      <section data-section="categorical">
        <H2 id="the-two-lines">The two lines, FY{d.first_fy} to FY{d.last_fy}</H2>
        <p className="text-sm max-w-3xl" style={{ color: 'var(--text-secondary)' }}>
          Homes on the left axis, students on the right; the two are counts of different things and share no scale. A gap in the students line is a year DESE&rsquo;s file does not carry.
        </p>
        <div style={{ width: '100%', height: 340 }} className="mt-4 avoid-break">
          <ResponsiveContainer>
            <LineChart data={series} margin={{ top: 8, right: 8, left: 0, bottom: 4 }}>
              <CartesianGrid stroke="var(--grid)" vertical={false} />
              <XAxis dataKey="fy" tick={AXIS} stroke="var(--axis)" interval={3} />
              <YAxis yAxisId="homes" tick={AXIS} stroke="var(--axis)" tickFormatter={(v: number) => n0(v)} domain={['dataMin - 100', 'dataMax + 100']} />
              <YAxis yAxisId="students" orientation="right" tick={AXIS} stroke="var(--axis)" tickFormatter={(v: number) => n0(v)} domain={['dataMin - 100', 'dataMax + 100']} />
              <Tooltip content={({ active, payload, label }) => {
                if (!active || !payload?.length) return null
                const r = payload[0].payload as typeof series[number]
                return <Box><p className="font-bold">{label}</p><p>{n0(r.homes)} single-family homes</p><p>{n0(r.students)} students</p>
                  <p style={{ color: 'var(--text-muted)' }}>{r.ratio.toFixed(1)} students per 100 homes</p></Box>
              }} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Line yAxisId="homes" type="monotone" dataKey="homes" name="single-family homes" stroke="var(--text-primary)" strokeWidth={2} dot={false} isAnimationActive={false} />
              <Line yAxisId="students" type="monotone" dataKey="students" name="students" stroke="var(--series-cost)" strokeWidth={2} dot={false} isAnimationActive={false} connectNulls />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <H2 id="students-per-home">Students for every hundred homes</H2>
        <p className="text-sm max-w-3xl" style={{ color: 'var(--text-secondary)' }}>
          One series divided by the other. A ratio of two counts, not a survey of who lives where.
        </p>
        <div style={{ width: '100%', height: 220 }} className="mt-4 avoid-break">
          <ResponsiveContainer>
            <LineChart data={series} margin={{ top: 8, right: 8, left: 0, bottom: 4 }}>
              <CartesianGrid stroke="var(--grid)" vertical={false} />
              <XAxis dataKey="fy" tick={AXIS} stroke="var(--axis)" interval={3} />
              <YAxis tick={AXIS} stroke="var(--axis)" domain={[0, 'dataMax + 5']} />
              <Tooltip content={({ active, payload, label }) => {
                if (!active || !payload?.length) return null
                const r = payload[0].payload as typeof series[number]
                return <Box><p className="font-bold">{label}</p><p>{r.ratio.toFixed(1)} students per 100 homes</p></Box>
              }} />
              <Line type="monotone" dataKey="ratio" name="students per 100 homes" stroke="var(--series-revenue)" strokeWidth={2} dot={false} isAnimationActive={false} connectNulls />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </section>

      <section data-section="raw">
        <H2 id="the-table">Every year, as the two files print it</H2>
        <div className="overflow-x-auto">
          <table className="text-sm" style={{ minWidth: 480 }}>
            <thead><tr className="text-[10px] font-bold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>
              <th className="text-left py-1.5 pr-4">fiscal year</th><th className="text-right py-1.5 px-2">single-family homes</th><th className="text-right py-1.5 px-2">change</th><th className="text-right py-1.5 px-2">students</th><th className="text-right py-1.5 px-2">change</th><th className="text-right py-1.5 pl-2">per 100 homes</th></tr></thead>
            <tbody>{d.series.map((r, i) => {
              const p = d.series[i - 1]
              return (
                <tr key={r.fy} style={{ borderTop: '1px solid var(--grid)' }} className={r.fy === peak.fy ? 'font-bold' : undefined}>
                  <td className="py-1 pr-4 tnum">FY{r.fy}</td>
                  <td className="text-right tnum px-2">{n0(r.homes)}</td><td className="text-right tnum px-2" style={{ color: 'var(--text-muted)' }}>{p ? signed(r.homes - p.homes) : ''}</td>
                  <td className="text-right tnum px-2">{n0(r.students)}</td><td className="text-right tnum px-2" style={{ color: 'var(--text-muted)' }}>{p ? signed(r.students - p.students) : ''}</td>
                  <td className="text-right tnum pl-2">{r.students_per_100_homes.toFixed(1)}</td>
                </tr>)
            })}</tbody>
          </table>
        </div>
        <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>The peak enrolment year in bold. A change is against the previous year the record holds, which is not always the previous calendar year early in the series.</p>
        <NotEstablished rows={d.not_established} closes="School-age children per household by year — the Census carries it only as a five-year sample, and the district’s own October 1 report by residence would be the like-for-like." />
        <Provenance sources={d.sources} />
      </section>
      </FullVersion>
      <MoreReports here={TAB} />
    </>
  )
}

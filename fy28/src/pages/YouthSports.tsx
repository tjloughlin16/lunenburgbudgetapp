import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { FullVersion } from '../components/FullVersion'
import type { Tab } from '../routes'
import { Conclusions, Grain, H2, MoreReports, NotEstablished, Provenance, ReportShell, Stat, useReport, splitConclusions } from '../components/report'
import type { Conclusion, Source } from '../components/report'
import { usd, usdShort } from '../model/engine'

const TAB: Tab = 'youthsports'
const DATA = '/data/youth-sports.json'

/** YOUTH SPORTS AND THE TOWN. TJ, 17 September 2026: "Youth Sports report ;) Please
 *  build, starting with this" -- after a records request produced Lunenburg Youth
 *  Soccer's field-rental receipts and the archive turned out to hold the fund they land
 *  in, the turf fund the 2016 deal feeds, and fifteen years of the fund's own history in
 *  the annual reports.
 *
 *  THREE KINDS OF EVIDENCE, AND THE PAGE SAYS WHICH IS WHICH: the town's MUNIS fund
 *  report (evidence), the district's typed answer to a records request (stated), and
 *  the annual reports' schedules (transcribed, unreconciled -- drawn, not concluded
 *  from). What the boards said is cited to the recording at its second. Built by
 *  scripts/build_youth_sports.py. */
type Fund = { fund: number; name: string; opening: number; revenue: number; salaries: number; expenditure: number; available: number }
type Receipt = { fy: string; date: string; amount: number; payer: string; munis: string }
type Year = { fy: number; forward: number | null; receipts: number | null; disbursed: number | null; carried: number | null; status: string; page: number | null }
type Said = { board: string; date: string; video: string; t: number; what: string }
type Payload = {
  about: string; grain: string; as_of: string; leagues: string[]
  funds: Fund[]; receipts: Receipt[]; receipts_total: number; receipts_by_fy: Record<string, number>
  series: Year[]; series_peak: { fy: number; receipts: number }; series_latest: Year
  said: Said[]; sources: Source[]; not_established: string[]; conclusions: Conclusion[]
}
const AXIS = { fontSize: 11, fill: 'var(--text-muted)' }
const hms = (t: number) => `${Math.floor(t / 3600)}:${String(Math.floor((t % 3600) / 60)).padStart(2, '0')}:${String(t % 60).padStart(2, '0')}`
const nice = (iso: string) => new Date(iso + 'T12:00:00').toLocaleDateString('en-US', { day: 'numeric', month: 'long', year: 'numeric' })

export function YouthSports() {
  const { d, err } = useReport<Payload>('youth-sports.json')
  return (
    <ReportShell tab={TAB}
      title="Youth sports and the fields: the funds, and who uses them"
      standfirst={d ? <>Four funds take rent and fees for the town&rsquo;s fields and buildings and hold {usdShort(d.funds.reduce((s2, f) => s2 + f.available, 0))} between them, outside anything Town Meeting votes. This page is what goes in and out of them, which leagues use the fields, and what the boards have said since 2014. What any league pays is published nowhere; one league&rsquo;s receipts came by records request and are shown as the sample they are.</> : undefined}
      err={err} loading={!d && !err} dataUrl={DATA}>
      {d && <Report d={d} />}
    </ReportShell>
  )
}

function Report({ d }: { d: Payload }) {
  const f1306 = d.funds.find(f => f.fund === 1306)!
  const f1545 = d.funds.find(f => f.fund === 1545)!
  const [shortRows, moreRows] = splitConclusions(d.conclusions, undefined)
  const series = d.series.map(y => ({ fy: `FY${String(y.fy).slice(2)}`, receipts: y.receipts ?? 0, disbursed: y.disbursed ?? 0 }))
  return (
    <>
      <section data-section="conclusions" data-short="">
        <div className="flex flex-wrap gap-x-10 gap-y-5 mt-8">
          <Stat value={usdShort(d.funds.reduce((s2, f) => s2 + f.available, 0))} tone="var(--series-revenue)">held across the four field and facility funds at 31 March 2026, spendable without a vote</Stat>
          <Stat value={usdShort(f1306.revenue)}>of field and building rent into the schools&rsquo; fund in FY2026 through March; {usdShort(f1306.available)} available</Stat>
          <Stat value={usdShort(f1545.revenue)}>a year into the Artificial Turf fund &mdash; the 2016 deal&rsquo;s figure</Stat>
          <Stat value={`${d.leagues.length} leagues`} tone="var(--text-secondary)">use the fields; the payments of {d.receipts.length ? 'one' : 'none'} of them are in the archive, by records request</Stat>
        </div>
        <Grain>{d.grain}</Grain>
        <Conclusions rows={shortRows} />
      </section>

      <FullVersion what="the receipts, the funds, the years, and what was said">
        {moreRows.length > 0 && (
          <>
            <H2 id="more-findings">The other findings</H2>
            <Conclusions rows={moreRows} noAsk short={false} />
          </>
        )}

        <section data-section="categorical">
          <H2 id="receipts">One league&rsquo;s payments, as the district listed them</H2>
          <p className="text-sm max-w-3xl" style={{ color: 'var(--text-secondary)' }}>
            <strong>The only user group whose payments the archive holds</strong> &mdash; because it is the one we asked for first, not because it is unusual. A workbook the district&rsquo;s business office typed in answer to a records request, September 2026. Grouped by fiscal year as the district groups them &mdash; the 8 July 2024 receipt sits under FY24 although the date is in FY25. One row carries a pasted record from the accounting system.
          </p>
          <div className="overflow-x-auto mt-4">
            <table className="text-sm" style={{ minWidth: 560 }}>
              <thead><tr className="text-[10px] font-bold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>
                <th className="text-left py-2 pr-4">listed under</th><th className="text-left py-2 pr-4">date</th><th className="text-right py-2 pr-4">amount</th><th className="text-left py-2 pr-4">payer, as printed</th><th className="text-left py-2">accounting-system note</th></tr></thead>
              <tbody>{d.receipts.map((r, i) => (
                <tr key={i} style={{ borderTop: '1px solid var(--grid)' }}>
                  <td className="py-1.5 pr-4 tnum">{r.fy}</td><td className="py-1.5 pr-4 tnum whitespace-nowrap">{nice(r.date)}</td><td className="py-1.5 pr-4 text-right tnum">{usd(r.amount)}</td><td className="py-1.5 pr-4">{r.payer}</td><td className="py-1.5 text-[12px]" style={{ color: 'var(--text-muted)' }}>{r.munis || '—'}</td>
                </tr>))}
                <tr style={{ borderTop: '2px solid var(--grid)' }} className="font-bold"><td className="py-2 pr-4" colSpan={2}>All seven</td><td className="py-2 pr-4 text-right tnum">{usd(d.receipts_total)}</td><td colSpan={2} /></tr>
              </tbody>
            </table>
          </div>

          <H2 id="funds">The funds, from the town&rsquo;s books</H2>
          <p className="text-sm max-w-3xl" style={{ color: 'var(--text-secondary)' }}>
            The town&rsquo;s FY26 special-revenue report as of {nice(d.as_of)} &mdash; a printout from the accounting system, so these are evidence in the sense this site uses the word. Credits print negative on the report and are shown here as amounts; the four columns are the ones the report&rsquo;s own arithmetic identifies (opening + revenue &minus; spent = available, to the cent, for every fund), because the export&rsquo;s header row has fewer labels than its rows have columns. The opening balance is the FY2025 close.
          </p>
          <div className="overflow-x-auto mt-4">
            <table className="text-sm" style={{ minWidth: 560 }}>
              <thead><tr className="text-[10px] font-bold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>
                <th className="text-left py-2 pr-4">fund</th><th className="text-right py-2 pr-4">opening, 1 July 2025</th><th className="text-right py-2 pr-4">revenue to March</th><th className="text-right py-2 pr-4">spent</th><th className="text-right py-2">available</th></tr></thead>
              <tbody>{d.funds.map(f => (
                <tr key={f.fund} style={{ borderTop: '1px solid var(--grid)' }} className={f.fund === 1306 ? 'font-semibold' : undefined}>
                  <td className="py-1.5 pr-4"><span className="tnum">{f.fund}</span> {f.name}</td><td className="py-1.5 pr-4 text-right tnum">{usd(f.opening)}</td><td className="py-1.5 pr-4 text-right tnum">{usd(f.revenue)}</td><td className="py-1.5 pr-4 text-right tnum">{usd(f.expenditure)}</td><td className="py-1.5 text-right tnum">{usd(f.available)}</td>
                </tr>))}</tbody>
            </table>
          </div>
          <p className="text-sm max-w-3xl mt-3" style={{ color: 'var(--text-secondary)' }}>
            Fund 1306 is the school department&rsquo;s facilities-use revolving fund; 1545 the turf fund; 1500 the Parks Commission&rsquo;s own revolving fund; 1301 the athletics fund whose full cash journal the archive holds &mdash; and which carries no receipt from any youth league, which is how the search for these payments started.
          </p>

          <H2 id="years">The facilities-use fund, FY2011 to FY2024, as the annual reports print it</H2>
          <p className="text-sm max-w-3xl" style={{ color: 'var(--text-secondary)' }}>
            Receipts and disbursements, read off each year&rsquo;s special-revenue schedule. <strong>Transcribed, not verified:</strong> the pages&rsquo; own totals do not reconcile in any year, so this is the shape of the fund and not a figure to quote. The FY2018 report prints a carried balance its own row does not support. The FY2024 report prints only a balance &mdash; $3,010.67 at 30 June 2024 &mdash; and the FY26 report opens the fund at $65,241.82 a year later; FY2025 itself is the year the archive cannot see.
          </p>
          <div style={{ width: '100%', height: 300 }} className="mt-4 avoid-break">
            <ResponsiveContainer>
              <BarChart data={series} margin={{ top: 8, right: 8, left: 0, bottom: 4 }}>
                <CartesianGrid stroke="var(--grid)" vertical={false} />
                <XAxis dataKey="fy" tick={AXIS} stroke="var(--axis)" />
                <YAxis tick={AXIS} stroke="var(--axis)" tickFormatter={(v: number) => usdShort(v)} width={56} />
                <Tooltip formatter={(v, n) => [usd(v as number), n === 'receipts' ? 'receipts' : 'disbursed']} contentStyle={{ background: 'var(--surface-1)', border: '1px solid var(--grid)', borderRadius: 10, fontSize: 12, color: 'var(--text-primary)' }} />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                <Bar dataKey="receipts" fill="var(--series-revenue)" isAnimationActive={false} />
                <Bar dataKey="disbursed" fill="var(--series-cost)" isAnimationActive={false} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="overflow-x-auto mt-4">
            <table className="text-sm" style={{ minWidth: 520 }}>
              <thead><tr className="text-[10px] font-bold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>
                <th className="text-left py-2 pr-4">year</th><th className="text-right py-2 pr-4">forward</th><th className="text-right py-2 pr-4">receipts</th><th className="text-right py-2 pr-4">disbursed</th><th className="text-right py-2 pr-4">carried</th><th className="text-left py-2">page check</th></tr></thead>
              <tbody>{d.series.map(y => (
                <tr key={y.fy} style={{ borderTop: '1px solid var(--grid)' }}>
                  <td className="py-1.5 pr-4 tnum">FY{y.fy}</td>
                  {[y.forward, y.receipts, y.disbursed, y.carried].map((v, i) => <td key={i} className="py-1.5 pr-4 text-right tnum">{v === null ? '—' : usd(v)}</td>)}
                  <td className="py-1.5 text-[11px]" style={{ color: 'var(--text-muted)' }}>{y.status}</td>
                </tr>))}</tbody>
            </table>
          </div>

          <H2 id="said">What the boards have said</H2>
          <p className="text-sm max-w-3xl" style={{ color: 'var(--text-secondary)' }}>
            From the recordings&rsquo; machine captions &mdash; a finding aid, not a record. Each line opens the video at the moment.
          </p>
          <ul className="mt-4 space-y-3 max-w-3xl">{d.said.slice().sort((a, b) => a.date.localeCompare(b.date)).map(s => (
            <li key={s.video + s.t} className="text-[13.5px] leading-relaxed">
              <a className="font-semibold underline" style={{ color: 'var(--series-cost)' }} href={`https://www.youtube.com/watch?v=${s.video}&t=${s.t}s`} target="_blank" rel="noreferrer">{s.board}, {nice(s.date)} &middot; {hms(s.t)}</a>
              <span className="block mt-0.5" style={{ color: 'var(--text-secondary)' }}>{s.what}</span>
            </li>))}</ul>

          <H2 id="leagues">The leagues</H2>
          <p className="text-sm max-w-3xl" style={{ color: 'var(--text-secondary)' }}>
            The town&rsquo;s Parks Commission page lists {d.leagues.length}, &ldquo;provided as a courtesy and not run or managed by the Parks Commission&rdquo;: {d.leagues.join('; ')}. Independent organisations that use town and school fields; only one of them has a records-request answer in this archive.
          </p>
        </section>

        <section data-section="raw">
          <NotEstablished rows={d.not_established} closes="The journal detail export for funds 1306 and 1545, FY2024–FY2026 — the same report the archive already holds for fund 1301 — and the FY2024 and FY2025 special-revenue reports." />
          <Provenance sources={d.sources} />
        </section>
      </FullVersion>

      <MoreReports here={TAB} />
    </>
  )
}

import { Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { Tab } from '../routes'
import { usd, usdShort } from '../model/engine'
import { GAP, GAPS, HEALTH, HEALTH_LEVERS, BENT_HEALTH, ATTRIBUTION } from '../model/answers'
import { DEFAULT_RATES, LEVY_CAP, INSURANCE_CASE, CANNOT_SKIP, decadeWorth } from '../model/rates'
import { ReportShell, ShortVersion, Insight, Stat, Grain, NotShown, H2, Body, MoreReports, useReport } from '../components/report'
import { FullVersion } from '../components/FullVersion'
import { WhoPays, DoesNot, Settles, LeverLinks, pct, n0 } from '../components/lever'

const TAB: Tab = 'healthlever'

/** WHAT CHANGING THE HEALTH PLAN DOES. TJ, 17 September 2026: "health insurance should
 *  go here ... make sure that page includes what adjusting health insurance looks like."
 *
 *  /health-insurance measures the COST -- what sits outside the school budget, how fast
 *  the town's insurance department grows. This page is the LEVER: what the rate is
 *  worth to the gap, what the routes to a lower rate actually are (a plan, a pool, an
 *  employee share), what each costs whom, and why it is the one line that changes the
 *  rate rather than the amount. Every figure is the model's (answers.ts, rates.ts). */
const AT_FOUR = decadeWorth({ ...DEFAULT_RATES, health: 0.04 })
const AT_CAP = decadeWorth({ ...DEFAULT_RATES, health: LEVY_CAP })
const H = ATTRIBUTION.health
const [today, better] = INSURANCE_CASE
const M = HEALTH_LEVERS.migration
const O = HEALTH_LEVERS.optOut

/** THE STATUTORY MENU AND THE STATEWIDE COMPARISON, from scripts/build_health_options.py.
 *  TJ, 18 September 2026: "I'm not following the options in terms of which insurance is
 *  available, at what %" -- so the options are data, each row linking the section of
 *  c.32B that permits or forbids it, rather than prose anybody has to take on trust. */
type Option = {
  id: string; option: string; statute: string; statute_url: string; who_decides: string; threshold: string
  available_to_lunenburg: string; effect_on_the_gap: string; who_it_lands_on: string; note: string
}
type Peer = { municipality: string; first: number; last: number; growth: number }
type Options = {
  options: Option[]; can: string[]; cannot: string[]; comparison_caveat: string
  town: { fy: number; spent: number; growth: number; rank: number; of: number; median_growth: number; faster_than_median: number; series: { fy: number; spent: number }[]
    rolling: { fy: number; growth: number }[]; decades_under_4: number; decades: number; last_decade_under_4: number | null; best_decade: { fy: number; growth: number } | null }
  achievable: { threshold: number; towns: number; of: number; share: number }[]
  recent_years: { fy: number; median: number; towns: number; over_4: number; over_4_share: number; town: number; rank: number }[]
  by_funding: { town_is: string; basis: string; not_available: string
    types: { funding: string; towns: number; median: number; quartile_low: number; quartile_high: number; under_4: number; under_4_share: number; has_town: boolean }[] }
  peers: { span_years: number; from_fy: number; to_fy: number; count: number; fastest: Peer[]; slowest: Peer[]
    histogram: { band: number; low: number; high: number; towns: number; has_town: boolean }[] }
  neighbours: { municipality: string; series: { fy: number; spent: number }[] }[]
}
const AXIS = { fontSize: 11, fill: 'var(--text-muted)' }
const LINE_COLOURS = ['var(--series-cost)', '#7c8a97', '#9aa7b1', '#b0bac2', '#c2cad0', '#8fa1ae', '#a8b4bd', '#96a3ad', '#bcc5cb', '#aab5bd', '#9ba8b2']

type PecEntry = { on: string; what: string; quote: string; basis: string; source: string; source_url: string }

export function HealthLever() {
  const { d } = useReport<Options>('health-options.json')
  return (
    <ReportShell tab={TAB} dataUrl="/data/model.json"
      title="Health insurance: what changing the plan does"
      standfirst={<>Health insurance is {pct(H.shareOfBudget, 0)} of the school budget and puts {pct(H.shareOfGap, 0)} of the gap into it, because it grows {pct(HEALTH.rise, 0)} a year against a levy capped at {pct(LEVY_CAP, 1)}. It is one of two lines that can change the <em>rate</em>. Nobody in town sets the premium; what the town can change is which plans it buys, who is in the pool, and who pays what share &mdash; and each of those lands on somebody.</>}>

      <Grain>
        A projection from the district&rsquo;s own rates and the town&rsquo;s own plan documents: what the gap does when the health line grows slower, and what the routes to slower actually are. Dollars of appropriation, not premiums paid. Every route here is priced; none is recommended.
      </Grain>

      <div className="mt-10 flex flex-wrap gap-x-12 gap-y-6">
        <Stat value={pct(H.shareOfGap, 0)} tone="var(--status-critical)">of the gap comes from health insurance, a line that is {pct(H.shareOfBudget, 0)} of the budget</Stat>
        <Stat value={usdShort(AT_FOUR.removed)}>taken out of the next ten years&rsquo; gaps if the line grew {pct(0.04, 0)} instead of {pct(HEALTH.rise, 0)}</Stat>
        <Stat value={usd(M.kept)}>kept by the town for each person moved from the broadest plan to the narrower one, after the employees&rsquo; share of the saving</Stat>
        <Stat value={`${better.buildings === null ? '—' : better.buildings.toFixed(0)} vs ${today.buildings === null ? '—' : today.buildings.toFixed(0)}`}>buildings a year of commercial growth to hold the line with insurance at {pct(0.04, 0)}, against at {pct(HEALTH.rise, 0)}</Stat>
      </div>

      <H2 id="conclusions">If you read nothing else</H2>
      <ShortVersion>
        <div className="grid gap-4 mt-5 md:grid-cols-2">
          <Insight n={1} figure={pct(H.shareOfGap, 0)} tone="var(--status-critical)"
            headline={<>The health plan is the largest single lever and not a solution on its own: {pct(H.shareOfGap, 0)} of next year&rsquo;s gap is this one line, from {pct(H.shareOfBudget, 0)} of the budget.</>}>
            Hold it to the levy cap and re-run the projection: {usdShort(GAP - Math.round(GAP * (1 - H.shareOfGap)))} of next year&rsquo;s {usdShort(GAP)} gap falls out. Salaries are {ATTRIBUTION.sizeRatio.toFixed(1)}&times; the size and contribute about the same, because they grow {pct(DEFAULT_RATES.salaries, 0)} and this grows {pct(HEALTH.rise, 0)}. Rule 4 on this site: weight times excess rate, not size.
          </Insight>
          <Insight n={2} figure={d ? `${d.achievable.find(a => a.threshold === 4)?.share.toFixed(0)}%` : '—'}
            headline={d ? <>Four per cent is not a wish: {d.achievable.find(a => a.threshold === 4)?.share.toFixed(0)}% of Massachusetts municipalities held health insurance under it for the decade &mdash; and Lunenburg did in {d.town.decades_under_4} of its own {d.town.decades} ten-year windows, the last ending FY{d.town.last_decade_under_4}.</> : <>Whether a lower rate is achievable at all.</>}>
            {d ? <>Every municipality files what it spends, so &ldquo;could we hold it to {pct(0.04, 0)}?&rdquo; has an answer rather than an opinion: {d.achievable.find(a => a.threshold === 4)?.towns} of {d.peers.count} towns did over FY{d.peers.from_fy}&ndash;FY{d.peers.to_fy}, and the median town grew {d.town.median_growth.toFixed(1)}%. Lunenburg&rsquo;s own ten-year rate was under {pct(0.04, 0)} in every window from FY2016 to FY{d.town.last_decade_under_4}, as low as 1.9%. <strong>What it does not establish is that anybody can choose the rate</strong> &mdash; a premium is claims and a pool. It establishes that the rate is not fixed.</> : null}
          </Insight>
          <Insight n={3} figure={d ? `${(d.recent_years[1].town / d.recent_years[1].median).toFixed(1)}×` : '—'} tone="var(--status-critical)"
            headline={d ? <>Every town&rsquo;s premium turned after FY2022 &mdash; the median went {d.recent_years[0].median.toFixed(1)}% to {d.recent_years[3].median.toFixed(1)}% &mdash; but Lunenburg&rsquo;s FY{d.recent_years[1].fy} and FY{d.recent_years[2].fy} came in about three times the median.</> : <>Whether the town is unusual, or the market turned.</>}>
            {d ? <>FY{d.recent_years[1].fy}: {d.recent_years[1].town.toFixed(1)}% here against {d.recent_years[1].median.toFixed(1)}% for the median municipality. FY{d.recent_years[2].fy}: {d.recent_years[2].town.toFixed(1)}% against {d.recent_years[2].median.toFixed(1)}%. Then FY{d.recent_years[3].fy}: {d.recent_years[3].town.toFixed(1)}% against {d.recent_years[3].median.toFixed(1)}% &mdash; below it, in the year {d.recent_years[3].over_4_share.toFixed(0)}% of all towns were over {pct(0.04, 0)}. So a rising premium here is not evidence of anything the town did; the size of those two years is the part that is the town&rsquo;s own, and why is not in this data.</> : null}
          </Insight>
          <Insight n={4} figure={usdShort(AT_FOUR.removed)}
            headline={<>What {pct(0.04, 0)} would be worth if it held: {usdShort(AT_FOUR.removed)} out of the next ten years&rsquo; gaps, and the FY{GAPS[GAPS.length - 1].fy} gap {pct(AT_FOUR.smallerBy, 0)} smaller.</>}>
            A rate change compounds the right way: {usdShort(AT_FOUR.firstYear)} in the first year, more every year after. At the levy cap itself it would be {usdShort(AT_CAP.removed)}. Neither closes the gap alone &mdash; salaries at {pct(DEFAULT_RATES.salaries, 0)} still outrun the cap &mdash; but it is the single largest rate move on the table, and the least painful column on <a className="underline" href="/what-solved-requires">the page that combines them</a>.
          </Insight>
          <Insight n={5} figure={d ? `${d.can.length} routes` : '—'}
            headline={<>There are {d ? d.can.length : ''} lawful routes and {d ? d.cannot.length : ''} things the town cannot do at any price &mdash; and the one everyone proposes, cutting the town&rsquo;s {pct(1 - 0.25, 0)} share, is among the latter.</>}>
            The routes: change the plan design up to the state plan&rsquo;s copays and deductibles (a Select Board decision, 30 days with the employee committee, then a binding panel); join the state&rsquo;s Group Insurance Commission, by agreement or without one; move Medicare-eligible retirees, which the town did in part in 2020; pay people with other coverage to decline. What is barred: the employer share may never go below 50% (§7A permits &ldquo;more, but not less&rdquo;), the plan-design process may not touch the split at all (§21(f)), coverage once accepted cannot be revoked (§10), and retirees cannot be dropped (<em>Galenski</em>, 2015). Every route and every bar is <a className="underline" href="#options">below, with the section that says so</a>.
          </Insight>
          <Insight n={6} figure={d ? `${d.town.growth.toFixed(1)}%` : '—'} tone="var(--status-critical)"
            headline={d ? <>Lunenburg&rsquo;s health insurance grew {d.town.growth.toFixed(1)}% a year for a decade while the median town grew {d.town.median_growth.toFixed(1)}% &mdash; {d.town.rank} of {d.town.of}.</> : <>How the town compares with every other in the state.</>}>
            {d ? <>All 351 municipalities file what they spend on Schedule A; Lunenburg spent {usd(d.town.spent)} in FY{d.town.fy}. Read the GROWTH and not the level &mdash; a self-insured town&rsquo;s figure includes the employee share and ours does not, which is <a className="underline" href="#funding">its own section below</a>.</> : null}
          </Insight>
          <Insight n={7} figure={usd(M.kept)}
            headline={<>Moving one person off the broadest plan keeps the town {usd(M.kept)} a year, and {n0(M.onBroadest)} are on it &mdash; bargained, not voted.</>}>
            The broadest plan ({M.from}) to the narrower one ({M.to}) saves {usd(M.gross)} a person in premium. We assume a quarter of the first year&rsquo;s saving is conceded back at the table, so the town keeps {usd(M.kept)} &mdash; an assumption, not a rule: the 25% cap in §21(f) governs plan design, and moving people between plans is bargained. Every enrollee moved: {usdShort(M.ifAll)} a year. The opt-out the committee voted in March 2026 pays {usd(O.incentive)} against a {usd(O.premium)} premium, netting {usd(O.net)} per person who takes it. And the employee share: each point of the premium shifted from the town to its staff is worth {usd(HEALTH.perPoint)} a year to the budget.
          </Insight>
        </div>
        <NotShown>
          Whether any of it is bargainable this year. Plan design goes through the insurance advisory committee and the unions under c.32B; the FY27 rate came in at {pct(HEALTH_LEVERS.actualFy27, 1)} against the {pct(HEALTH_LEVERS.assumed, 0)} assumed, and nothing here predicts next year&rsquo;s. This page prices the routes; it does not say which one the town should take.
        </NotShown>
      </ShortVersion>

      <FullVersion what="every route, priced">
        <H2 id="options">What the town can choose, and who decides</H2>
        <Body>Every row is a section of Chapter 32B. Follow the link and read the sentence rather than taking ours.</Body>
        {d ? (
          <>
            <div className="overflow-x-auto mt-4">
              <table className="text-sm" style={{ minWidth: 820 }}>
                <thead><tr className="text-[10px] font-bold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>
                  <th className="text-left py-2 pr-4">the option</th><th className="text-left py-2 pr-4">who decides</th><th className="text-left py-2 pr-4">the threshold</th><th className="text-left py-2 pr-4">who it lands on</th><th className="text-left py-2">the law</th></tr></thead>
                <tbody>{d.options.filter(o => o.available_to_lunenburg !== 'no').map(o => (
                  <tr key={o.id} style={{ borderTop: '1px solid var(--grid)' }}>
                    <td className="py-2 pr-4 align-top" style={{ minWidth: 220 }}><span className="font-semibold">{o.option}</span>
                      <span className="block text-[11.5px] mt-0.5" style={{ color: 'var(--text-muted)' }}>{o.note}</span></td>
                    <td className="py-2 pr-4 align-top">{o.who_decides}</td>
                    <td className="py-2 pr-4 align-top text-[12.5px]" style={{ color: 'var(--text-secondary)' }}>{o.threshold}</td>
                    <td className="py-2 pr-4 align-top text-[12.5px]" style={{ color: 'var(--text-secondary)' }}>{o.who_it_lands_on}</td>
                    <td className="py-2 align-top whitespace-nowrap"><a className="underline" href={o.statute_url} target="_blank" rel="noreferrer">{o.statute.replace('M.G.L. c.32B ', '')}</a></td>
                  </tr>))}</tbody>
              </table>
            </div>
            <H2 id="cannot">And what it cannot do, at any price</H2>
            <ul className="mt-3 space-y-2 max-w-3xl">
              {d.options.filter(o => o.available_to_lunenburg === 'no').map(o => (
                <li key={o.id} className="text-sm pl-4 border-l-2" style={{ borderColor: 'var(--status-critical)' }}>
                  <strong>{o.option}.</strong> <span style={{ color: 'var(--text-secondary)' }}>{o.note}</span>{' '}
                  <a className="underline text-[12px]" href={o.statute_url} target="_blank" rel="noreferrer">{o.statute.replace('M.G.L. c.32B ', '')}</a>
                </li>))}
            </ul>

            {/* HOW THE TOWN GOT THE ARRANGEMENT IT HAS. TJ asked for the PEC's history
                on this page, and it belongs immediately after the options: the table above
                says what the law permits, and this says which of those doors Lunenburg
                has actually walked through — which is the question every argument about
                health insurance in this town turns on.

                EVERY ENTRY IS A QUOTE, not a summary, and every entry carries what it
                does NOT establish. The §19 acceptance vote is not in the record we hold;
                the 2010 special act is a draft whose fate is unknown; no vote adopting
                §§21–23 has been found. Rule 7: the document is the fact, and the gap is
                said out loud rather than filled in. */}
            <H2 id="history">How Lunenburg got here</H2>
            <Body>
              Six moments, each quoted from the document it comes from. Where something is
              not established, the entry says so rather than reading as settled.
            </Body>
            <ol className="mt-4 space-y-4 list-none p-0 max-w-3xl">
              {((d as unknown as { pec_history?: PecEntry[] }).pec_history ?? []).map(h => (
                <li key={h.on} className="pl-4 border-l-2" style={{ borderColor: 'var(--series-cost)' }}>
                  <p className="m-0 text-[12px] font-semibold uppercase tracking-widest"
                    style={{ color: 'var(--text-muted)' }}>
                    {new Date(h.on + 'T12:00:00Z').toLocaleDateString('en-US',
                      { month: 'short', year: 'numeric' })}
                  </p>
                  <p className="m-0 text-[15px] font-semibold">{h.what}</p>
                  <blockquote className="mt-1 mb-1 text-[13.5px]" style={{ color: 'var(--text-secondary)' }}>
                    &ldquo;{h.quote}&rdquo;
                  </blockquote>
                  <p className="m-0 text-[12px]" style={{ color: 'var(--text-muted)' }}>
                    <a className="underline" href={h.source_url} target="_blank" rel="noreferrer">{h.source}</a>
                    {' — '}{h.basis}
                  </p>
                </li>
              ))}
            </ol>

            <H2 id="recent">The last four years, against every other municipality</H2>
            <Body>Whether the town is unusual or the market turned &mdash; and it is both. Each row is one year&rsquo;s change in what the town spent, beside the median municipality&rsquo;s and the share of all of them over 4%.</Body>
            <div className="overflow-x-auto mt-4">
              <table className="text-sm" style={{ minWidth: 560 }}>
                <thead><tr className="text-[10px] font-bold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>
                  <th className="text-left py-2 pr-6">year</th><th className="text-right py-2 pr-6">Lunenburg</th><th className="text-right py-2 pr-6">the median town</th><th className="text-right py-2 pr-6">towns over 4%</th><th className="text-right py-2">of</th></tr></thead>
                <tbody>{d.recent_years.map(r => (
                  <tr key={r.fy} style={{ borderTop: '1px solid var(--grid)' }}>
                    <td className="py-1.5 pr-6 tnum">FY{r.fy}</td>
                    <td className="py-1.5 pr-6 text-right tnum font-semibold" style={{ color: r.town > r.median ? 'var(--status-critical)' : 'var(--status-good)' }}>{r.town.toFixed(1)}%</td>
                    <td className="py-1.5 pr-6 text-right tnum">{r.median.toFixed(1)}%</td>
                    <td className="py-1.5 pr-6 text-right tnum">{r.over_4} <span style={{ color: 'var(--text-muted)' }}>({r.over_4_share.toFixed(0)}%)</span></td>
                    <td className="py-1.5 text-right tnum" style={{ color: 'var(--text-muted)' }}>{r.towns}</td>
                  </tr>))}</tbody>
              </table>
            </div>
            <p className="text-[12.5px] mt-2" style={{ color: 'var(--text-muted)' }}>
              The whole state turned after FY2022, so a rising premium here is not evidence of anything Lunenburg did. What is the town&rsquo;s own is the SIZE of FY2023 and FY2024 &mdash; about three times the median in both &mdash; and that FY2025 came in below it. Why any of those happened is not in this data: a premium is claims and a pool.
            </p>

            <H2 id="funding">By how a town buys it: claims, or premiums</H2>
            <Body>{d.by_funding.basis} <strong>{d.by_funding.not_available}</strong></Body>
            <div style={{ width: '100%', height: 230 }} className="mt-4 avoid-break">
              <ResponsiveContainer>
                <BarChart layout="vertical" data={d.by_funding.types.map(t => ({ name: `${t.funding} (${t.towns})`, median: t.median, mine: t.has_town }))}
                  margin={{ top: 8, right: 16, left: 8, bottom: 4 }}>
                  <CartesianGrid stroke="var(--grid)" horizontal={false} />
                  <XAxis type="number" tick={AXIS} stroke="var(--axis)" tickFormatter={(v: number) => `${v}%`} />
                  <YAxis type="category" dataKey="name" tick={AXIS} stroke="var(--axis)" width={170} />
                  <Tooltip formatter={(v) => [`${(v as number).toFixed(2)}% a year, median town`, '']} contentStyle={{ background: 'var(--surface-1)', border: '1px solid var(--grid)', borderRadius: 10, fontSize: 12, color: 'var(--text-primary)' }} />
                  <Bar dataKey="median" isAnimationActive={false}>
                    {d.by_funding.types.map((t, i) => <Cell key={i} fill={t.has_town ? 'var(--series-cost)' : 'var(--text-muted)'} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
            <div className="overflow-x-auto mt-3">
              <table className="text-sm" style={{ minWidth: 560 }}>
                <thead><tr className="text-[10px] font-bold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>
                  <th className="text-left py-2 pr-6">how it is funded</th><th className="text-right py-2 pr-6">towns</th><th className="text-right py-2 pr-6">median a year</th><th className="text-right py-2 pr-6">middle half</th><th className="text-right py-2">under 4%</th></tr></thead>
                <tbody>{d.by_funding.types.map(t => (
                  <tr key={t.funding} style={{ borderTop: '1px solid var(--grid)' }} className={t.has_town ? 'font-semibold' : undefined}>
                    <td className="py-1.5 pr-6">{t.funding}{t.has_town ? ' — Lunenburg' : ''}</td>
                    <td className="py-1.5 pr-6 text-right tnum">{t.towns}</td>
                    <td className="py-1.5 pr-6 text-right tnum">{t.median.toFixed(2)}%</td>
                    <td className="py-1.5 pr-6 text-right tnum" style={{ color: 'var(--text-muted)' }}>{t.quartile_low.toFixed(1)}–{t.quartile_high.toFixed(1)}%</td>
                    <td className="py-1.5 text-right tnum">{t.under_4} <span style={{ color: 'var(--text-muted)' }}>({t.under_4_share.toFixed(0)}%)</span></td>
                  </tr>))}</tbody>
              </table>
            </div>
            <p className="text-[12.5px] mt-2" style={{ color: 'var(--text-muted)' }}>
              The two groups are not measuring quite the same thing &mdash; a self-insured town&rsquo;s figure includes the employee share &mdash; so read the spread within each group rather than the gap between them. Nothing here says one arrangement causes a lower rate: the towns that self-insure are mostly the largest, and size is doing work this table cannot separate.
            </p>

            <H2 id="held">Lunenburg's own ten-year rate, window by window</H2>
            <Body>Each point is the compound annual rate over the ten years ending that fiscal year &mdash; the same measure the statewide comparison uses. The town was under 4% in {d.town.decades_under_4} of {d.town.decades} windows and crossed in FY2024.</Body>
            <div style={{ width: '100%', height: 240 }} className="mt-4 avoid-break">
              <ResponsiveContainer>
                <LineChart data={d.town.rolling.map(r => ({ fy: `FY${String(r.fy).slice(2)}`, growth: r.growth }))} margin={{ top: 8, right: 8, left: 0, bottom: 4 }}>
                  <CartesianGrid stroke="var(--grid)" vertical={false} />
                  <XAxis dataKey="fy" tick={AXIS} stroke="var(--axis)" />
                  <YAxis tick={AXIS} stroke="var(--axis)" tickFormatter={(v: number) => `${v}%`} width={44} />
                  <Tooltip formatter={(v) => [`${(v as number).toFixed(1)}% a year`, 'ten years to']} contentStyle={{ background: 'var(--surface-1)', border: '1px solid var(--grid)', borderRadius: 10, fontSize: 12, color: 'var(--text-primary)' }} />
                  <Line type="monotone" dataKey="growth" stroke="var(--series-cost)" strokeWidth={2} dot={{ r: 2 }} isAnimationActive={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>

            <H2 id="peers">Every town in the state, on growth</H2>
            <Body>{d.comparison_caveat}</Body>
            {/* THE DISTRIBUTION. A rank says where the town sits; the shape says whether
                the pack is tight. Lunenburg's band is the one in colour. */}
            <div style={{ width: '100%', height: 220 }} className="mt-4 avoid-break">
              <ResponsiveContainer>
                <BarChart data={d.peers.histogram.map(h => ({ name: h.high >= 100 ? `${h.low}%+` : h.low <= -100 ? 'fell' : `${h.low}–${h.high}%`, towns: h.towns, mine: h.has_town }))}
                  margin={{ top: 8, right: 8, left: 0, bottom: 4 }}>
                  <CartesianGrid stroke="var(--grid)" vertical={false} />
                  <XAxis dataKey="name" tick={AXIS} stroke="var(--axis)" />
                  <YAxis tick={AXIS} stroke="var(--axis)" width={40} />
                  <Tooltip formatter={(v) => [`${v} municipalities`, '']} contentStyle={{ background: 'var(--surface-1)', border: '1px solid var(--grid)', borderRadius: 10, fontSize: 12, color: 'var(--text-primary)' }} />
                  <Bar dataKey="towns" isAnimationActive={false}>
                    {d.peers.histogram.map((h, i) => <Cell key={i} fill={h.has_town ? 'var(--status-critical)' : 'var(--text-muted)'} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
            <p className="text-[12.5px] mt-1" style={{ color: 'var(--text-muted)' }}>
              How fast each of {d.peers.count} municipalities&rsquo; health insurance grew a year, FY{d.peers.from_fy}&ndash;FY{d.peers.to_fy}. Lunenburg is in the {d.town.growth.toFixed(1)}% band, in red.
            </p>

            {/* THE NEIGHBOURS, year by year. Levels are not comparable across towns for
                the reason above, so this is shown as what each town spent, not indexed --
                the eye should read the SHAPE of each curve, not the distance between them. */}
            <div style={{ width: '100%', height: 300 }} className="mt-6 avoid-break">
              <ResponsiveContainer>
                <LineChart margin={{ top: 8, right: 8, left: 0, bottom: 4 }}
                  data={(() => {
                    const fys = Array.from(new Set(d.neighbours.flatMap(n => n.series.map(x => x.fy)))).sort()
                    return fys.map(fy => Object.fromEntries([['fy', `FY${String(fy).slice(2)}`],
                      ...d.neighbours.map(n => [n.municipality, n.series.find(x => x.fy === fy)?.spent ?? null])]))
                  })()}>
                  <CartesianGrid stroke="var(--grid)" vertical={false} />
                  <XAxis dataKey="fy" tick={AXIS} stroke="var(--axis)" interval={2} />
                  <YAxis tick={AXIS} stroke="var(--axis)" tickFormatter={(v: number) => usdShort(v)} width={52} />
                  <Tooltip formatter={(v, n) => [usd(v as number), n as string]} contentStyle={{ background: 'var(--surface-1)', border: '1px solid var(--grid)', borderRadius: 10, fontSize: 12, color: 'var(--text-primary)' }} />
                  <Legend wrapperStyle={{ fontSize: 10 }} />
                  {d.neighbours.map((n, i) => (
                    <Line key={n.municipality} type="monotone" dataKey={n.municipality} dot={false} isAnimationActive={false}
                      stroke={LINE_COLOURS[i % LINE_COLOURS.length]} strokeWidth={n.municipality === 'Lunenburg' ? 2.5 : 1} connectNulls />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            </div>
            <p className="text-[12.5px] mt-1" style={{ color: 'var(--text-muted)' }}>
              What each neighbouring municipality spent, as filed on Schedule A. Fitchburg and Leominster are cities many times Lunenburg&rsquo;s size &mdash; the line to read is the shape of each curve, not the gap between them.
            </p>
            <div className="overflow-x-auto mt-4">
              <table className="text-sm" style={{ minWidth: 520 }}>
                <thead><tr className="text-[10px] font-bold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>
                  <th className="text-left py-2 pr-6">municipality</th><th className="text-right py-2 pr-6">FY{d.peers.from_fy}</th><th className="text-right py-2 pr-6">FY{d.peers.to_fy}</th><th className="text-right py-2">a year</th></tr></thead>
                <tbody>{[...d.peers.fastest.slice(0, 5), ...d.peers.slowest.slice(0, 5)].concat(
                  d.peers.fastest.concat(d.peers.slowest).some(p => p.municipality === 'Lunenburg') ? [] :
                  [{ municipality: 'Lunenburg', first: d.town.series.find(x => x.fy === d.peers.from_fy)?.spent ?? 0, last: d.town.spent, growth: d.town.growth }]).map(p => (
                  <tr key={p.municipality} style={{ borderTop: '1px solid var(--grid)' }} className={p.municipality === 'Lunenburg' ? 'font-bold' : undefined}>
                    <td className="py-1.5 pr-6">{p.municipality}</td>
                    <td className="py-1.5 pr-6 text-right tnum">{usd(p.first)}</td>
                    <td className="py-1.5 pr-6 text-right tnum">{usd(p.last)}</td>
                    <td className="py-1.5 text-right tnum" style={{ color: p.growth > d.town.median_growth ? 'var(--status-critical)' : 'var(--status-good)' }}>{p.growth.toFixed(1)}%</td>
                  </tr>))}</tbody>
              </table>
            </div>
            <p className="text-[12.5px] mt-2" style={{ color: 'var(--text-muted)' }}>The five fastest and five slowest of {d.peers.count} municipalities with a figure in both years, and Lunenburg. Median {d.town.median_growth.toFixed(1)}% a year.</p>
          </>
        ) : null}

        <H2 id="rate">What the rate is worth</H2>
        <Body>The projection holds every other line where it is and moves only health insurance. What the gap does is what the line is worth.</Body>
        <div className="overflow-x-auto mt-4">
          <table className="text-sm" style={{ minWidth: 520 }}>
            <thead><tr className="text-[10px] font-bold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>
              <th className="text-left py-2 pr-6">health insurance grows at</th><th className="text-right py-2 pr-6">first year</th><th className="text-right py-2 pr-6">ten years</th><th className="text-right py-2">FY{GAPS[GAPS.length - 1].fy} gap smaller by</th></tr></thead>
            <tbody>
              {[HEALTH.rise, 0.06, 0.04, LEVY_CAP].map(r => { const d = decadeWorth({ ...DEFAULT_RATES, health: r }); return (
                <tr key={r} style={{ borderTop: '1px solid var(--grid)' }} className={r === HEALTH.rise ? undefined : 'tnum'}>
                  <td className="py-1.5 pr-6">{pct(r, 1)}{r === HEALTH.rise ? ' (assumed)' : r === LEVY_CAP ? ' (the levy cap)' : ''}</td>
                  <td className="py-1.5 pr-6 text-right tnum">{r === HEALTH.rise ? '—' : usd(d.firstYear)}</td>
                  <td className="py-1.5 pr-6 text-right tnum">{r === HEALTH.rise ? '—' : usd(d.removed)}</td>
                  <td className="py-1.5 text-right tnum">{r === HEALTH.rise ? '—' : pct(d.smallerBy, 0)}</td>
                </tr>) })}
            </tbody>
          </table>
        </div>
        <Body>Set beside {pct(BENT_HEALTH.to, 1)} &mdash; the cap plus a point and a half, the most a serious plan change has reached in comparable towns &mdash; the saving by FY2032 is {usdShort(BENT_HEALTH.savedByFy32)}.</Body>

        <H2 id="routes">The three routes, and what each costs whom</H2>
        <div className="overflow-x-auto mt-4">
          <table className="text-sm" style={{ minWidth: 640 }}>
            <thead><tr className="text-[10px] font-bold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>
              <th className="text-left py-2 pr-6">route</th><th className="text-left py-2 pr-6">worth to the budget</th><th className="text-left py-2">who pays</th></tr></thead>
            <tbody>
              <tr style={{ borderTop: '1px solid var(--grid)' }}><td className="py-2 pr-6 align-top font-semibold">Plan design &mdash; a narrower network</td><td className="py-2 pr-6 align-top">{usd(M.kept)} a person a year; {usdShort(M.ifAll)} if all {n0(M.onBroadest)} on {M.from} moved to {M.to}</td><td className="py-2 align-top" style={{ color: 'var(--text-secondary)' }}>The employee: a family on the narrower plan pays {usd(M.familyGap)} a year less in premium and gives up {M.fromNetwork} for {M.toNetwork}. The highest-deductible plan on offer carries a {typeof HEALTH_LEVERS.highDeductible === 'number' ? usd(HEALTH_LEVERS.highDeductible) : HEALTH_LEVERS.highDeductible} deductible.</td></tr>
              <tr style={{ borderTop: '1px solid var(--grid)' }}><td className="py-2 pr-6 align-top font-semibold">The pool &mdash; the opt-out</td><td className="py-2 pr-6 align-top">{usd(O.net)} net per person who leaves the plan for a {usd(O.incentive)} payment</td><td className="py-2 align-top" style={{ color: 'var(--text-secondary)' }}>Nobody, directly: it pays people already covered elsewhere. The committee raised it from {usd(O.priorFamily)}/{usd(O.priorIndividual)} to {usd(O.family)}/{usd(O.individual)} in March 2026 and cut the wait from {O.priorWaitYears} years to {O.waitYears}.</td></tr>
              <tr style={{ borderTop: '1px solid var(--grid)' }}><td className="py-2 pr-6 align-top font-semibold">The share &mdash; employees pay more of the premium</td><td className="py-2 pr-6 align-top">{usd(HEALTH.perPoint)} a year for each point of the premium moved; closing the whole gap this way takes {HEALTH.pointsToClose.toFixed(0)} points, to a {pct(HEALTH.shareNeeded, 0)} employee share</td><td className="py-2 align-top" style={{ color: 'var(--text-secondary)' }}>Every employee: about {usd(HEALTH.costPerFamily)} a year on a family premium of {usd(HEALTH.familyPremium)} at that share. It is a pay cut in everything but name, and it is bargained.</td></tr>
            </tbody>
          </table>
        </div>

        <WhoPays>
          A narrower plan is paid by the person whose doctor is out of network. A higher deductible is paid by the person who gets sick. A higher share is paid by every employee, every month. The town&rsquo;s saving is the same money seen from the other side of the table; this page does not pretend otherwise.
        </WhoPays>
        <DoesNot>
          It does not close the gap by itself. With insurance at {pct(0.04, 0)} and every other line at the levy cap, salaries would still have to settle at {pct(better.salary, 1)} to hold &mdash; or the town would need {better.buildings === null ? 'more building than the model can find' : `${better.buildings.toFixed(0)} buildings a year`} of commercial growth. Leave insurance at {pct(HEALTH.rise, 0)} and the same job takes {today.buildings === null ? '—' : today.buildings.toFixed(0)}. It can be skipped, at about {today.buildings && better.buildings ? (today.buildings / better.buildings).toFixed(0) : '—'}&times; the building; it cannot be finished alone. {CANNOT_SKIP.health.consumes > 0 ? <>On its own it consumes {pct(CANNOT_SKIP.health.consumes, 2)} of the revenue rate.</> : null}
        </DoesNot>
        <Settles>the insurance advisory committee&rsquo;s plan-year rate letter for FY28 (the {pct(HEALTH_LEVERS.assumed, 0)} is an assumption; FY27&rsquo;s actual was {pct(HEALTH_LEVERS.actualFy27, 1)}), and the enrolment by plan after the March 2026 opt-out change &mdash; which would say whether the pool moved.</Settles>

        <LeverLinks measures="insurance" label="What health insurance costs" />
      </FullVersion>

      <MoreReports here={TAB} />
    </ReportShell>
  )
}

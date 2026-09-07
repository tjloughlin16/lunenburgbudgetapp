import { useEffect, useMemo, useState } from 'react'
import { usd, usdShort } from '../model/engine'
import {
  Flow, Held, Net, Movers, Chip, BAND_COLOUR, fy, IN, OUT,
  type YearRow, type BandRow, type BandDef, type MoverRow,
} from '../components/SpecialRevenueCharts'

/** The money outside the appropriation — the town's special revenue funds, FY2011–FY2023.
 *
 *  WHAT THIS PAGE IS FOR. Rule 11 says a budget line is NET: a line that rose because a
 *  grant ended looks exactly like a line that rose because the thing got dearer, and the
 *  budget documents cannot tell the two apart because they show the general fund and
 *  nothing else. This schedule is the *other side* — grants, revolving funds, gifts,
 *  enterprise funds — and it is the only published place in this archive where thirteen
 *  consecutive years of it can be read at all. It still does not map a fund to a budget
 *  line. Nothing published does, and the page says so.
 *
 *  RULE 2. Not one figure is typed into this file. Everything numeric — inside the
 *  sentences too, which is the half that keeps getting missed — arrives from
 *  /data/special-revenue.json, written by scripts/build_special_revenue.py, which refuses
 *  to write unless every year still ties to its own printed GRAND TOTAL.
 *
 *  RULE 7 IS THE WHOLE DIFFICULTY HERE. A balance that grows is a measurement. *Why* it
 *  grew is not: a fund can accumulate because the town charged more, because it spent
 *  less, because a grant arrived late in the year, or because the money is committed and
 *  not yet paid out. This schedule prints four columns of dollars and none of the four
 *  distinguishes those. Every claim on this page is stated as the movement of dollars,
 *  and the alternatives sit beside it rather than in a footnote.
 *
 *  RULE 7B. Insights first, then the organised categorical data, then the raw rows.
 *
 *  NO D1 AT PAGE LOAD. One static file. */

type Payload = {
  generated_by: string
  source: string
  provenance: string
  tables: string[]
  documents: string[]
  read_by: string[]
  coverage: {
    first_fy: number; last_fy: number; years: number[]; editions: number
    fund_years: number; fund_names: number
    names_every_year: number; names_one_year_only: number
    groups: number; merged_group_rows: number; printed_group_spellings: number
    span_histogram: { years: number; funds: number }[]
  }
  reconciliation: {
    fy: number; edition: string; page: string; quote: string; funds: number
    printed: Record<string, number>; summed: Record<string, number>; ties: boolean
  }[]
  chain: { fy: number; forward: number; prior_carried: number | null; gap: number | null; known_break: boolean }[]
  chain_break: { fy: number; amount: number }[]
  by_year: YearRow[]
  bands: BandDef[]
  band_series: BandRow[]
  by_group: {
    group: string
    series: YearRow[]
    first: YearRow; last: YearRow
    receipts_total: number; disbursements_total: number
  }[]
  school: YearRow[]
  movers: { first_fy: number; last_fy: number; in_both: number; risers: MoverRow[]; fallers: MoverRow[] }
  persistent: {
    fund: string; group: string; band: string
    receipts: number; disbursements: number; net: number
    years_drawn_down: number; years: number
    first_carried: number; last_carried: number
  }[]
  latest: {
    fund: string; group: string; band: string
    forward: number; receipts: number; disbursements: number; carried: number
  }[]
  rows: (number | string)[][]
  row_fields: string[]
}

const share = (x: number) => `${(x * 100).toFixed(x >= 0.1 ? 0 : 1)}%`
const times = (x: number) => `${x.toFixed(1)}×`

function H2({ id, children }: { id?: string; children: React.ReactNode }) {
  return (
    <h2 id={id} className="text-2xl font-bold tracking-tight mt-14 mb-3 max-w-3xl
                           scroll-mt-[calc(var(--header-h)+1rem)]">{children}</h2>
  )
}

function Body({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-[15px] leading-relaxed max-w-2xl mt-3"
      style={{ color: 'var(--text-secondary)' }}>{children}</p>
  )
}

function Stat({ value, tone, children }: {
  value: string; tone?: string; children: React.ReactNode
}) {
  return (
    <div>
      <div className="text-3xl font-bold tracking-tight" style={tone ? { color: tone } : undefined}>
        {value}
      </div>
      <div className="text-[13px] leading-snug mt-1 max-w-[15rem]"
        style={{ color: 'var(--text-secondary)' }}>{children}</div>
    </div>
  )
}

/** The half of a section that says what the measurement does NOT establish. A distinct
 *  shape on purpose: on this page the limit is as load-bearing as the finding, and a
 *  caveat set in the same grey as the paragraph above it gets skimmed. */
function NotShown({ children }: { children: React.ReactNode }) {
  return (
    <div className="card p-4 mt-5 max-w-2xl" style={{ borderLeft: '4px solid var(--axis)' }}>
      <p className="text-[11px] font-semibold uppercase tracking-widest mb-1.5"
        style={{ color: 'var(--text-muted)' }}>What this does not show</p>
      <div className="text-[14px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
        {children}
      </div>
    </div>
  )
}

/** One claim, at the top, with the measurement that carries it. */
function Insight({ n, headline, children }: {
  n: number; headline: React.ReactNode; children: React.ReactNode
}) {
  return (
    <li className="border-t pt-4 pb-1" style={{ borderColor: 'var(--grid)' }}>
      <p className="text-[11px] font-semibold tabular-nums mb-1"
        style={{ color: 'var(--text-muted)' }}>{n}</p>
      <p className="text-[17px] font-bold leading-snug max-w-2xl">{headline}</p>
      <p className="text-[14.5px] leading-relaxed max-w-2xl mt-1.5"
        style={{ color: 'var(--text-secondary)' }}>{children}</p>
    </li>
  )
}

export function SpecialRevenue() {
  const [d, setD] = useState<Payload | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [year, setYear] = useState<number | null>(null)
  const [group, setGroup] = useState<string>('all')

  useEffect(() => {
    let live = true
    fetch('/data/special-revenue.json')
      .then(r => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then(j => { if (live) { setD(j); setYear(j.coverage.last_fy) } })
      .catch(e => { if (live) setErr(String(e)) })
    return () => { live = false }
  }, [])

  /** The raw rows, filtered. Rebuilt only when a control moves — 1,882 rows is small
   *  enough to filter in the browser and far too many to put on a phone unfiltered. */
  const raw = useMemo(() => {
    if (!d || year === null) return []
    const [FY, G] = [d.row_fields.indexOf('fy'), d.row_fields.indexOf('group')]
    const C = d.row_fields.indexOf('carried')
    return d.rows
      .filter(r => r[FY] === year && (group === 'all' || r[G] === group))
      .sort((a, b) => (b[C] as number) - (a[C] as number))
  }, [d, year, group])

  if (err) {
    return (
      <div className="mx-auto max-w-6xl px-5 pt-14 pb-16">
        <h1 className="text-3xl font-bold tracking-tight">The money outside the budget</h1>
        <div className="card p-5 mt-8" style={{ borderLeft: '4px solid var(--status-warning)' }}>
          <p className="text-[15px] font-bold mb-1">The series did not load</p>
          <p className="text-[13.5px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
            {err}. Nothing on this page is typed into it, so with the file missing there is
            nothing to show rather than something stale. The figures themselves are at{' '}
            <a className="underline" style={{ color: 'var(--series-cost)' }}
              href="/data/special-revenue.json">/data/special-revenue.json</a>.
          </p>
        </div>
      </div>
    )
  }

  if (!d || year === null) {
    return (
      <div className="mx-auto max-w-6xl px-5 pt-14 pb-16">
        <h1 className="text-3xl font-bold tracking-tight">The money outside the budget</h1>
        <p className="mt-4 text-[15px]" style={{ color: 'var(--text-muted)' }}>
          Loading thirteen years of fund schedules&hellip;
        </p>
      </div>
    )
  }

  const c = d.coverage
  const first = d.by_year[0]
  const last = d.by_year[d.by_year.length - 1]
  const surplusYears = d.by_year.filter(r => r.net > 0)
  const deficitYears = d.by_year.filter(r => r.net <= 0)
  const bandsLast = d.band_series[d.band_series.length - 1]
  const pandemicBand = d.bands.find(b => b.id === 'pandemic')!
  const enterpriseBand = d.bands.find(b => b.id === 'enterprise')!
  const schoolGroup = d.by_group.find(g => g.group === 'SCHOOL DEPARTMENT')!
  const schoolLast = d.school[d.school.length - 1]
  const schoolDrawn = d.school.filter(r => r.net < 0)
  /** The drawdown before the most recent one, if the most recent year IS a drawdown.
   *  Null otherwise, and insight 4 changes what it says rather than asserting a
   *  "first since" that the data has stopped supporting. */
  const schoolPrevDrawn = schoolLast.net < 0
    ? schoolDrawn.filter(r => r.fy < schoolLast.fy).slice(-1)[0] ?? null
    : null
  const peakSchool = [...d.school].sort((a, b) => b.carried - a.carried)[0]
  const pandemicFirst = d.band_series.find(r => r.pandemic_receipts > 0)!
  const chainBreak = d.chain.find(r => r.known_break)!
  const groups = d.by_group.map(g => g.group)
  const drawers = d.persistent.filter(r => r.net < 0)
  const accumulators = [...d.persistent].sort((a, b) => b.net - a.net).slice(0, 5)

  return (
    <div className="mx-auto max-w-6xl px-5 pt-14 pb-16">
      <p className="text-xs font-semibold uppercase tracking-widest mb-3"
        style={{ color: 'var(--text-muted)' }}>The money</p>
      <h1 className="text-4xl sm:text-5xl font-bold tracking-tight leading-[1.05] max-w-3xl">
        There is {usdShort(last.carried)} outside the budget Town Meeting votes.
      </h1>
      <p className="mt-5 text-lg leading-relaxed max-w-2xl"
        style={{ color: 'var(--text-secondary)' }}>
        Town Meeting votes an appropriation. Beside it the town runs {last.funds} separate
        funds that take in money of their own &mdash; grants, fees, gifts, water and sewer
        charges &mdash; and carry whatever is left over into the next year. In{' '}
        {fy(last.fy)} they received {usd(last.receipts)} and were holding{' '}
        {usd(last.carried)} on 30 June. This is thirteen consecutive years of that
        schedule, {fy(c.first_fy)} to {fy(c.last_fy)}, read out of the town&rsquo;s own
        annual reports.
      </p>

      <div className="mt-10 flex flex-wrap gap-x-12 gap-y-6">
        <Stat value={usd(last.carried)}>
          held in these funds at the end of {fy(last.fy)}, against {usd(first.carried)} at
          the end of {fy(first.fy)}
        </Stat>
        <Stat value={`${surplusYears.length} of ${d.by_year.length}`} tone={IN}>
          years in which the funds took in more than they spent
        </Stat>
        <Stat value={`${c.fund_years}`}>
          fund-years, {c.editions} editions, every one tying to the GRAND TOTAL its own
          report prints
        </Stat>
      </div>

      {/* =========================================================== 1. INSIGHTS */}
      <H2 id="what-this-says">What the thirteen years say</H2>
      <Body>
        Four claims, each one a movement of dollars in this schedule and nothing more. Why
        any of them happened is a separate question the schedule cannot answer, and the
        boxes below each section say so specifically.
      </Body>

      <ul className="mt-6">
        <Insight n={1} headline={<>
          These funds took in more than they spent in {surplusYears.length} of{' '}
          {d.by_year.length} years, and what they hold multiplied{' '}
          {times(last.carried / first.carried)}.
        </>}>
          Receipts rose {times(last.receipts / first.receipts)} &mdash; from{' '}
          {usd(first.receipts)} in {fy(first.fy)} to {usd(last.receipts)} in{' '}
          {fy(last.fy)}. The balance carried at year end rose further, from{' '}
          {usd(first.carried)} to {usd(last.carried)}, because in{' '}
          {surplusYears.length} of the {d.by_year.length} years more came in than went out.
          The only exception is {deficitYears.map(r => fy(r.fy)).join(', ')}, when the
          funds spent {usd(Math.abs(deficitYears[0].net))} more than they received.
        </Insight>

        <Insight n={2} headline={<>
          {share(bandsLast.pandemic / bandsLast.total)} of what is being held is
          pandemic-era money, and this series ends before we can see whether it has gone.
        </>}>
          {bandsLast.pandemic_funds} funds &mdash; ARPA, the ESSER rounds and the rest of
          a list of {pandemicBand.funds!.length} names we identify as pandemic-era &mdash;
          held {usd(bandsLast.pandemic)} of the {usd(bandsLast.total)} carried into{' '}
          {fy(last.fy + 1)}. They received {usd(bandsLast.pandemic_receipts)} in{' '}
          {fy(last.fy)} and spent {usd(bandsLast.pandemic_disbursements)}. Before{' '}
          {fy(pandemicFirst.fy)} they did not exist. The schedule stops at {fy(c.last_fy)},
          so nothing here shows what happened when that money ran out &mdash; and which
          funds are &ldquo;pandemic&rdquo; is our reading of the printed names, listed in
          full below.
        </Insight>

        <Insight n={3} headline={<>
          Most of it is not school money, and a large part of it is not even the general
          town either &mdash; it is water, sewer and trash.
        </>}>
          The five enterprise funds sit inside this same schedule until {fy(c.last_fy)} and
          held {usd(bandsLast.enterprise)}, or {share(bandsLast.enterprise / bandsLast.total)}{' '}
          of the total. The school department&rsquo;s own funds held{' '}
          {usd(schoolGroup.last.carried)}, or{' '}
          {share(schoolGroup.last.carried / last.carried)}. Anyone quoting the{' '}
          {usd(last.carried)} as school reserves is quoting the sewer fund.
        </Insight>

        <Insight n={4} headline={schoolPrevDrawn ? <>
          {fy(schoolLast.fy)} was the first year since {fy(schoolPrevDrawn.fy)} that the
          school funds spent more than they took in.
        </> : <>
          The school funds have drawn their balances down in {schoolDrawn.length} of the{' '}
          {d.school.length} years on this page.
        </>}>
          In {fy(schoolLast.fy)} the district&rsquo;s funds received{' '}
          {usd(schoolLast.receipts)} and spent {usd(schoolLast.disbursements)} &mdash;{' '}
          {usd(Math.abs(schoolLast.net))} {schoolLast.net < 0 ? 'more out than in' : 'more in than out'}{' '}
          &mdash; and the balance stood at {usd(schoolLast.carried)} against{' '}
          {usd(peakSchool.carried)} at its highest, the end of {fy(peakSchool.fy)}. A year
          in which these funds spent more than they received has happened in{' '}
          {schoolDrawn.length} of the {d.school.length} years here:{' '}
          {schoolDrawn.map(r => fy(r.fy)).join(', ')}.
        </Insight>
      </ul>

      <NotShown>
        <p>
          <strong>Why any balance moved.</strong> A fund that accumulates may be charging
          more, spending less, holding money that is committed but not yet paid out, or
          receiving a grant late in the year that it will spend in the next one. Four
          columns of dollars cannot tell those apart, and this page never claims to.
        </p>
        <p className="mt-2.5">
          <strong>What the money bought.</strong> A disbursement is dollars leaving a fund.
          It is not a position, a programme or a service, and the schedule prints no
          headcount, no caseload and no purpose beside any of it.
        </p>
        <p className="mt-2.5">
          <strong>Which budget line any of this pays for.</strong> This is the missing
          half of the appropriation &mdash; and it is still not joined to it. The town
          publishes the general fund budget in one document and this schedule in another,
          and nothing published maps a fund to a line. That is the single number that would
          settle most of what this archive cannot answer: DESE&rsquo;s End of Year Financial
          Report separates spending by fund and is the nearest thing to it.
        </p>
      </NotShown>

      {/* ===================================================== 2. CATEGORICAL DATA */}
      <H2 id="in-and-out">Money in, money out</H2>
      <Body>
        Each pair of bars is one fiscal year: everything these {c.fund_names} named funds
        received, against everything they paid out. Both are the town&rsquo;s own printed
        column totals, and the reconciliation below shows every year tying to them.
      </Body>
      <div className="mt-6"><Flow rows={d.by_year} /></div>
      <p className="text-[12px] mt-3 max-w-2xl" style={{ color: 'var(--text-muted)' }}>
        A receipt here is money arriving in a fund, not revenue the town can spend on
        anything it likes. Most of these funds are restricted by the grant, the statute or
        the by-law that created them.
      </p>

      <H2 id="held">What is being held, and whose it is</H2>
      <Body>
        The same thirteen years, but the balance carried forward on 30 June rather than the
        year&rsquo;s flow &mdash; a stock, not a flow, which is why it is a second chart
        rather than a second axis. It is cut four ways. Three of the four are our reading
        of the printed fund names and are listed in full underneath; the fourth is the
        department heading the report itself prints.
      </Body>
      <div className="mt-6"><Held rows={d.band_series} bands={d.bands} /></div>

      <div className="card p-4 mt-5 max-w-2xl">
        <p className="text-[11px] font-semibold uppercase tracking-widest mb-2.5"
          style={{ color: 'var(--text-muted)' }}>Which funds are in which band</p>
        <div className="text-[13px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
          <p className="mb-2">
            <Chip color={BAND_COLOUR.enterprise}>{enterpriseBand.label}</Chip>{' '}
            &mdash; {enterpriseBand.funds!.join('; ')}. These are named by us; the report
            files them under its own department headings.
          </p>
          <p className="mb-2">
            <Chip color={BAND_COLOUR.pandemic}>{pandemicBand.label}</Chip>{' '}
            &mdash; {pandemicBand.funds!.join('; ')}. Named by us, from the printed fund
            names. An earlier cut of this used a text pattern and swept in a $200 fund
            called <em>Citizens Relief Fund</em> that has been in the schedule since{' '}
            {fy(c.first_fy)}; a list can be checked against the page, a pattern cannot.
          </p>
          <p className="mb-2">
            <Chip color={BAND_COLOUR.school}>School department</Chip>{' '}
            &mdash; every fund the report files under SCHOOL DEPARTMENT{' '}
            <em>except</em> the district&rsquo;s ESSER grants, which are counted in the
            pandemic band. The two together are what the schools held:{' '}
            {usd(schoolGroup.last.carried)} at the end of {fy(c.last_fy)}.
          </p>
          <p>
            <Chip color={BAND_COLOUR.other}>Everything else the town runs</Chip>{' '}
            &mdash; the residual, {bandsLast.other_funds} funds in {fy(c.last_fy)}. Grey
            rather than a colour, because it is not one thing.
          </p>
        </div>
      </div>

      <NotShown>
        <p>
          <strong>That a balance is available to spend.</strong> Nothing on this schedule
          says a carried balance is uncommitted. A grant balance is usually spoken for; a
          revolving fund balance may be a float the operation needs to run. &ldquo;Held on
          30 June&rdquo; is the only claim being made.
        </p>
        <p className="mt-2.5">
          <strong>Where the enterprise funds went after {fy(c.last_fy)}.</strong> They stop
          appearing in this schedule, and that is a change in how the report is laid out,
          not evidence about the funds. See the note on {fy(c.last_fy + 1)} below.
        </p>
      </NotShown>

      <H2 id="school">The school department&rsquo;s own funds</H2>
      <Body>
        School lunch, school choice, extended day, athletics, the special education tuition
        account, the federal grants and the gift funds &mdash; {schoolGroup.last.funds}{' '}
        of them in {fy(c.last_fy)} against {schoolGroup.first.funds} in {fy(c.first_fy)}.
        Each bar is a year&rsquo;s receipts minus its disbursements: above the line the
        balances grew, below it they were drawn down. Across all thirteen years these funds
        received {usd(schoolGroup.receipts_total)} and spent{' '}
        {usd(schoolGroup.disbursements_total)}.
      </Body>
      <div className="mt-6"><Net rows={d.school} what="school department funds" /></div>
      <p className="text-[12px] mt-3 max-w-2xl" style={{ color: 'var(--text-muted)' }}>
        These figures include the district&rsquo;s ESSER grants, which the band chart above
        counts separately. That is the whole of the difference between{' '}
        {usd(schoolGroup.last.carried)} here and {usd(bandsLast.school)} there.
      </p>

      <NotShown>
        <p>
          <strong>That a drawdown is a problem, or that a surplus is prudence.</strong>{' '}
          A grant fund is <em>supposed</em> to run down &mdash; that is what spending a
          grant looks like. {fy(schoolLast.fy)} is the year the ESSER rounds were being
          spent out, and a year in which a fund spends more than it receives is the normal
          shape of the end of a grant. It is also the shape of an operating account in
          trouble. This schedule cannot distinguish them.
        </p>
        <p className="mt-2.5">
          <strong>Anything about the appropriated school budget.</strong> None of this
          money is in it. A fund here paying for staff, and the general fund paying for the
          same staff next year, would show as an appropriation increase with no new
          service &mdash; which is rule 11&rsquo;s problem, visible from this side and
          still not solved from it.
        </p>
      </NotShown>

      <H2 id="movers">The biggest movers, {fy(d.movers.first_fy)} to {fy(d.movers.last_fy)}</H2>
      <Body>
        {d.movers.in_both} funds are printed under the same name in both the first and the
        last edition, and this is how far each one&rsquo;s carried balance moved between
        them. Only those {d.movers.in_both} can be compared at all: a fund whose name
        changed is a broken series, not a fund that closed.
      </Body>
      <div className="grid gap-4 mt-6 md:grid-cols-2">
        <div>
          <p className="text-[13px] font-semibold mb-2" style={{ color: IN }}>
            Grew the most
          </p>
          <Movers rows={d.movers.risers} firstFy={d.movers.first_fy} lastFy={d.movers.last_fy} />
        </div>
        <div>
          <p className="text-[13px] font-semibold mb-2" style={{ color: OUT }}>
            Fell the most
          </p>
          <Movers rows={d.movers.fallers} firstFy={d.movers.first_fy} lastFy={d.movers.last_fy} />
        </div>
      </div>

      <H2 id="persistent">Which funds accumulate, and which run themselves down</H2>
      <Body>
        The {c.names_every_year} funds printed in every one of the {c.editions} editions,
        by how much they took in over the whole period. A fund appearing twice can look
        like it always overspends on a sample of two, so these are the only ones long
        enough to have a habit. {drawers.length} of the {d.persistent.length} largest spent
        more than they received across the thirteen years;{' '}
        {accumulators.length > 0 && <>the largest net accumulation among them is{' '}
          {accumulators[0].fund}, {usd(accumulators[0].net)} over the period.</>}
      </Body>
      <div className="card p-4 mt-6 overflow-x-auto">
        <table className="w-full text-[12.5px] tnum">
          <thead>
            <tr className="text-left" style={{ color: 'var(--text-muted)' }}>
              <th className="py-1.5 pr-3 font-medium">Fund</th>
              <th className="py-1.5 pr-3 font-medium text-right">Received</th>
              <th className="py-1.5 pr-3 font-medium text-right">Spent</th>
              <th className="py-1.5 pr-3 font-medium text-right">Net</th>
              <th className="py-1.5 pr-3 font-medium text-right whitespace-nowrap">Years drawn down</th>
              <th className="py-1.5 font-medium text-right whitespace-nowrap">Held {fy(c.last_fy)}</th>
            </tr>
          </thead>
          <tbody>
            {d.persistent.map(r => (
              <tr key={r.fund} className="border-t" style={{ borderColor: 'var(--grid)' }}>
                <td className="py-1.5 pr-3">
                  <span className="inline-block w-2 h-2 rounded-[2px] mr-2 align-middle"
                    style={{ background: BAND_COLOUR[r.band] }} aria-hidden />
                  {r.fund}
                </td>
                <td className="py-1.5 pr-3 text-right">{usd(r.receipts)}</td>
                <td className="py-1.5 pr-3 text-right">{usd(r.disbursements)}</td>
                <td className="py-1.5 pr-3 text-right font-semibold"
                  style={{ color: r.net >= 0 ? IN : OUT }}>{usd(r.net)}</td>
                <td className="py-1.5 pr-3 text-right">{r.years_drawn_down} of {r.years}</td>
                <td className="py-1.5 text-right">{usd(r.last_carried)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <NotShown>
        <p>
          <strong>That &ldquo;drawn down&rdquo; means overspent.</strong> A fund that spends
          more than it receives in a year is spending a balance it already had, which is
          what a balance is for. The column counts years, not judgements.
        </p>
      </NotShown>

      {/* ============================================================ 3. RAW */}
      <H2 id="every-fund">Every fund, every year</H2>
      <Body>
        All {c.fund_years} rows, exactly as the reports print them: brought forward, plus
        receipts, minus disbursements, equals carried forward. Pick a year and a department.
      </Body>

      <div className="flex flex-wrap gap-2 mt-6">
        <label className="sr-only" htmlFor="sr-year">Fiscal year</label>
        <select id="sr-year" value={year} onChange={e => setYear(Number(e.target.value))}
          className="card px-3 min-h-[44px] text-[14px]"
          style={{ color: 'var(--text-primary)', background: 'var(--surface-1)' }}>
          {c.years.map(y => <option key={y} value={y}>{fy(y)}</option>)}
        </select>
        <label className="sr-only" htmlFor="sr-group">Department</label>
        <select id="sr-group" value={group} onChange={e => setGroup(e.target.value)}
          className="card px-3 min-h-[44px] text-[14px]"
          style={{ color: 'var(--text-primary)', background: 'var(--surface-1)' }}>
          <option value="all">All departments</option>
          {groups.map(g => <option key={g} value={g}>{g}</option>)}
        </select>
      </div>

      <div className="card p-4 mt-4 overflow-x-auto">
        <table className="w-full text-[12.5px] tnum">
          <thead>
            <tr className="text-left" style={{ color: 'var(--text-muted)' }}>
              <th className="py-1.5 pr-3 font-medium">Fund</th>
              <th className="py-1.5 pr-3 font-medium text-right whitespace-nowrap">Brought forward</th>
              <th className="py-1.5 pr-3 font-medium text-right">Receipts</th>
              <th className="py-1.5 pr-3 font-medium text-right">Disbursements</th>
              <th className="py-1.5 font-medium text-right whitespace-nowrap">Carried forward</th>
            </tr>
          </thead>
          <tbody>
            {raw.map((r, i) => (
              <tr key={`${r[2]}-${i}`} className="border-t" style={{ borderColor: 'var(--grid)' }}>
                <td className="py-1.5 pr-3">
                  {r[2]}
                  {group === 'all' && (
                    <span className="block text-[11px]" style={{ color: 'var(--text-muted)' }}>
                      {String(r[1]).toLowerCase()}
                    </span>
                  )}
                </td>
                <td className="py-1.5 pr-3 text-right">{usd(r[3] as number)}</td>
                <td className="py-1.5 pr-3 text-right">{usd(r[4] as number)}</td>
                <td className="py-1.5 pr-3 text-right">{usd(r[5] as number)}</td>
                <td className="py-1.5 text-right font-semibold">{usd(r[6] as number)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="text-[11.5px] mt-3" style={{ color: 'var(--text-muted)' }}>
          {raw.length} funds shown.
        </p>
      </div>

      {/* ------------------------------------------------------ how it was checked */}
      <H2 id="how-checked">How this was read, and how it was checked</H2>
      <Body>
        These figures were read off the rendered page of each annual report rather than
        run through OCR. That makes them an <em>instrument&rsquo;s output</em>, with
        exactly the standing of an OCR result &mdash; so two independent checks decide
        whether a year is publishable at all, and a year that fails either one is not on
        this page.
      </Body>
      <div className="grid gap-4 mt-6 sm:grid-cols-2 max-w-3xl">
        <div className="card p-4">
          <p className="text-[13.5px] font-bold mb-1">The town&rsquo;s own GRAND TOTAL</p>
          <p className="text-[13px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
            Every fund row is summed and compared to the four column totals the report
            itself prints at the bottom of the schedule. All {d.reconciliation.length}{' '}
            editions tie on all four columns, to the penny. The generator refuses to
            publish if one does not.
          </p>
        </div>
        <div className="card p-4">
          <p className="text-[13.5px] font-bold mb-1">The identity the table states</p>
          <p className="text-[13px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
            Brought forward + receipts &minus; disbursements = carried forward, on every one
            of the {c.fund_years} rows. Passing one check could be luck; a wrong digit that
            survives the row identity has to be cancelled by another wrong digit in the same
            row and still leave the column total unchanged.
          </p>
        </div>
      </div>

      <details className="card p-4 mt-4 max-w-3xl">
        <summary className="text-[13px] font-semibold cursor-pointer select-none
                            min-h-[44px] flex items-center">
          The reconciliation, year by year
        </summary>
        <div className="overflow-x-auto mt-2">
          <table className="w-full text-[12px] tnum">
            <thead>
              <tr className="text-left" style={{ color: 'var(--text-muted)' }}>
                <th className="py-1 pr-3 font-medium">Edition</th>
                <th className="py-1 pr-3 font-medium">Where</th>
                <th className="py-1 pr-3 font-medium text-right">Funds</th>
                <th className="py-1 pr-3 font-medium text-right">Printed receipts</th>
                <th className="py-1 pr-3 font-medium text-right">Our sum</th>
                <th className="py-1 font-medium">Ties</th>
              </tr>
            </thead>
            <tbody>
              {d.reconciliation.map(r => (
                <tr key={r.fy} className="border-t" style={{ borderColor: 'var(--grid)' }}>
                  <td className="py-1 pr-3">{r.edition}</td>
                  <td className="py-1 pr-3" style={{ color: 'var(--text-muted)' }}>{r.quote}</td>
                  <td className="py-1 pr-3 text-right">{r.funds}</td>
                  <td className="py-1 pr-3 text-right">{usd(r.printed.receipts)}</td>
                  <td className="py-1 pr-3 text-right">{usd(r.summed.receipts)}</td>
                  <td className="py-1" style={{ color: 'var(--status-good)' }}>
                    {r.ties ? 'all four columns' : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>

      {/* --------------------------------------------------------- the three caveats */}
      <H2 id="caveats">Three things to know before quoting any of this</H2>

      <div className="card p-4 mt-6 max-w-2xl" style={{ borderLeft: '4px solid var(--status-warning)' }}>
        <p className="text-[14.5px] font-bold mb-1">
          Fund names are not stable, so a series that breaks may be a renaming.
        </p>
        <p className="text-[13.5px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
          {c.fund_names} distinct fund names appear across the {c.editions} editions and
          only {c.names_every_year} of them appear in all thirteen;{' '}
          {c.names_one_year_only} appear exactly once. Between {fy(chainBreak.fy - 1)} and{' '}
          {fy(chainBreak.fy)} the town re-cut its grant funds by year, and{' '}
          {fy(chainBreak.fy)}&rsquo;s brought-forward column is {usd(chainBreak.gap!)}{' '}
          higher than {fy(chainBreak.fy - 1)}&rsquo;s carried column as a result &mdash; the
          one break in the chain, examined and pinned to the cent rather than smoothed over.
          A fund that disappears from these charts has not necessarily closed.
        </p>
      </div>

      <div className="card p-4 mt-4 max-w-2xl" style={{ borderLeft: '4px solid var(--status-warning)' }}>
        <p className="text-[14.5px] font-bold mb-1">
          The series stops at {fy(c.last_fy)}, and {fy(c.last_fy + 1)} is not a missing year
          &mdash; it is a different table.
        </p>
        <p className="text-[13.5px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
          {fy(c.last_fy + 1)} prints <em>Special Revenue Fund Balance Detail (Unaudited)</em>{' '}
          and {fy(c.last_fy + 2)} prints five columns. Neither prints brought forward, total
          receipts or total disbursements at all: they are a <strong>stock, not a flow</strong>,
          so nothing in either report says what a fund received or spent that year. The row
          identity that makes this dataset worth trusting has no counterpart in them, and
          the enterprise funds are absent, so the chain is not merely broken &mdash; it is
          not computable. Those two years belong in a separate dataset keyed on fund number,
          and appending them here would quietly weaken the guarantee for all{' '}
          {c.editions} years that do hold it.
        </p>
      </div>

      <div className="card p-4 mt-4 max-w-2xl" style={{ borderLeft: '4px solid var(--status-warning)' }}>
        <p className="text-[14.5px] font-bold mb-1">
          &ldquo;Special revenue&rdquo; here includes water, sewer, solid waste and PEG.
        </p>
        <p className="text-[13.5px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
          The enterprise funds sit inside this schedule for all {c.editions} editions, and
          they are {share(bandsLast.enterprise / bandsLast.total)} of what is held at the
          end of {fy(c.last_fy)}. Ratepayer money and school grant money are added together
          in the printed GRAND TOTAL, and every total on this page that is not explicitly
          split by band contains both. Do not present the headline as school money.
        </p>
      </div>

      {/* --------------------------------------------------------------- provenance */}
      <H2 id="where-from">Where this came from</H2>
      <Body>
        {c.editions} annual town reports, one schedule each. Every figure on this page is
        recomputed from{' '}
        <a className="underline" style={{ color: 'var(--series-cost)' }}
          href="/data/special-revenue.json">/data/special-revenue.json</a>{' '}
        when the site is built, by <code>{d.generated_by}</code>, from{' '}
        <code>{d.source}</code>. The dataset&rsquo;s own provenance note &mdash; what it is,
        how a year is added, and what it deliberately excludes &mdash; is{' '}
        <code>{d.provenance}</code>. In the published database the tables are{' '}
        {d.tables.map((t, i) => (
          <span key={t}><code>{t}</code>{i < d.tables.length - 1 ? ' and ' : ''}</span>
        ))}.
      </Body>
      <div className="card p-4 mt-5 max-w-3xl">
        <p className="text-[11px] font-semibold uppercase tracking-widest mb-2"
          style={{ color: 'var(--text-muted)' }}>The documents</p>
        <ul className="text-[12.5px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
          {d.documents.map(p => (
            <li key={p} className="border-t py-1.5" style={{ borderColor: 'var(--grid)' }}>
              <a className="underline break-all" style={{ color: 'var(--series-cost)' }}
                href={`/${p.replace(/^sources\//, 'docs/')}`}>{p}</a>
            </li>
          ))}
        </ul>
      </div>
      <p className="text-[12px] mt-4 max-w-2xl" style={{ color: 'var(--text-muted)' }}>
        Two spellings of one department appear in the printed schedules &mdash;{' '}
        HIGHWAY DEPT. in the early editions and HIGHWAY DEPARTMENT later &mdash; and{' '}
        {c.merged_group_rows} rows are merged into one heading here. That is our rendering
        of the town&rsquo;s page, not something the page says.
      </p>
    </div>
  )
}

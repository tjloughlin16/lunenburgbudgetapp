import type { Tab } from '../routes'
import { useEffect, useState } from 'react'
import { abs } from '../lib/abs'
import { usd } from '../model/engine'
import { Basis } from '../components/Basis'
import {
  BothFunds, GrantShare, MoveRows, SwapAndReduction, TableTwin, fy,
  type Move, type SeriesPoint, type YearRow,
} from '../components/GrantUnwindingCharts'
import {
  Body, H2, H3, Insight, Maybe, NotShown, Quote, Stat,
  ReportShell,
} from '../components/report'

/** The frame this report is drawn in. See components/report.tsx.
 *  TITLE is the report's NAME, used before the payload arrives; the h1 the
 *  reader lands on is the finding, which needs the data to state. */
const TAB: Tab = 'unwind'
const DATA = '/data/grant-unwinding.json'
const TITLE = 'When a grant ends'

/** When a grant ends, does the town pick up the bill?
 *
 *  WHY THIS PAGE EXISTS. CLAUDE.md rule 11 says a budget line is NET: it can rise because
 *  the thing got more expensive, or because a grant that was paying part of it ended, and
 *  the two are identical on the expense side. That has been a WARNING in this repo with
 *  one worked example beside it. DESE's End of Year Financial Report publishes the split —
 *  every dollar of district spending attributed to the general fund or to grants and
 *  revolving funds, by function code, FY2009 to FY2025 — and rule 11 names that document
 *  as the thing that would settle it. So this page is rule 11 finally being measurable
 *  rather than only warned about, at the grain the state publishes and no finer.
 *
 *  THE TRAP, AND IT IS THE POINT OF THE PAGE. Across FY2024→FY2025 the aggregate over
 *  every function present in both years reads: grants down, general fund up by almost
 *  exactly as much, total barely moved. That looks like the town replacing what the
 *  grants stopped paying and IT IS NOT WHAT HAPPENED. Decomposed, half the grant fall was
 *  replaced and half simply stopped, and the year's largest general fund increase is
 *  employee insurance, which no grant was paying. The near-identity is two unrelated
 *  movements landing on similar numbers. The page reports the aggregate ONLY inside the
 *  section that explains why it is wrong, and never as a finding — `is_a_finding: false`
 *  is carried in the payload for exactly that reason.
 *
 *  RULE 7 GOVERNS EVERY SENTENCE. "Grants fell $254,461 in function 2330 while the
 *  general fund rose $181,363" is a measurement. "The town picked up the paraprofessionals
 *  ESSER was paying for" is a hypothesis, and it is the sentence everybody will write. A
 *  fund total is not a grant, a dollar is not a post, and a general fund rise beside a
 *  grant fall in the same function fits the town picking up a cost exactly as well as it
 *  fits two unrelated things happening in one function in one year. Every section carries
 *  both halves.
 *
 *  RULE 7a. The page opens with the split and the four findings. Everything explaining
 *  how to read a fund attribution is under them.
 *
 *  RULE 7b. Conclusions, then the categorical breakdown, then the raw table and the
 *  method.
 *
 *  RULE 2. Not one figure is typed into this file. Everything arrives from
 *  /data/grant-unwinding.json, written by scripts/build_grant_unwinding.py, which refuses
 *  to write rather than publish a short series, an empty join, an unverified quote or a
 *  citation with no sha256.
 *
 *  NO D1 AT PAGE LOAD. One static file. */

type Said = {
  key: string; board: string; date: string; quote: string; why: string
  cite: string; town: string
}

type Payload = {
  about: string
  source: {
    table: string; publisher: string; lea: string; note: string
    path: string; sha256: string; bytes: number; url: string; docs_url: string
  }
  fy_first: number; fy_last: number
  series: SeriesPoint[]
  town_share_first: number; town_share_last: number; town_share_points: number
  counterfactual: {
    what: string; gen_fund_actual: number; gen_fund_at_first_share: number
    difference: number; is_measurement: boolean
  }
  by_year: YearRow[]
  latest_year: number
  latest_gen_fund_rises: Move[]
  latest_total_falls: Move[]
  latest_detail: { swap: Move[]; reduction: Move[]; grant_growth: Move[]; other: Move[] }
  biggest_swaps: Move[]
  said: Said[]
  searched: { term: string; documents: number }[]
  minutes: {
    published: number; held: number; searchable: number; unsearchable: number
    image_scan: number; searchable_share: number; text_files_present: number
    first_date: string; last_date: string
  }
  not_established: string[]
  closes: string
}

const share = (p: SeriesPoint) => 100 - p.town_share
/** The SIZE of a movement, for a sentence that already carries the direction in a verb.
 *  `usd` is signed, which is right beside a column heading and wrong after the word
 *  "fell" — "grants fell -$1,127,647" makes a reader do the double negative. Direction
 *  lives in exactly one place per sentence: either the sign or the verb, never both. */
const mag = (n: number) => usd(Math.abs(n))
const pct1 = (n: number) => `${n.toFixed(1)}%`

export function GrantUnwinding() {
  const [d, setD] = useState<Payload | null>(null)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    let live = true
    fetch('/data/grant-unwinding.json')
      .then(r => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then(j => { if (live) setD(j) })
      .catch(e => { if (live) setErr(String(e)) })
    return () => { live = false }
  }, [])

  if (err) return <ReportShell tab={TAB} title={TITLE} dataUrl={DATA} err={err} />

  if (!d) return <ReportShell tab={TAB} title={TITLE} dataUrl={DATA} loading />

  const S = d.series
  const first = S[0]
  const last = S[S.length - 1]
  const trough = S.reduce((a, b) => (share(b) < share(a) ? b : a))
  // The most recent local peak: the highest grant share after the trough. Named that way
  // rather than "the peak", because the highest share in the whole record is the first
  // year of it.
  const afterTrough = S.filter(p => p.fy > trough.fy)
  const rebound = afterTrough.reduce((a, b) => (share(b) > share(a) ? b : a))
  const beforeRebound = S.filter(p => p.fy < rebound.fy && share(p) >= share(rebound))
  const lastHigherFy = beforeRebound.length
    ? beforeRebound[beforeRebound.length - 1].fy : null

  const Y = d.by_year
  const latest = Y[Y.length - 1]
  const prior = Y.slice(0, -1)
  const worstPriorSwap = prior.reduce((a, b) => (b.swap.d_grants < a.swap.d_grants ? b : a))
  const worstPriorFall = prior.reduce(
    (a, b) => (b.aggregate.d_grants < a.aggregate.d_grants ? b : a))

  const swap = d.latest_detail.swap
  const reduction = d.latest_detail.reduction
  // Inside the swap class the general fund rose. It did not always rise by AS MUCH, and
  // that distinction is the difference between "the town picked it up" and "the town
  // picked some of it up". Counted, not asserted.
  const swapShort = swap.filter(m => m.d_total < 0)
  const biggestRise = d.latest_gen_fund_rises[0]
  const biggestFall = d.latest_total_falls.reduce(
    (a, b) => (b.d_total < a.d_total ? b : a))
  const paras = swap.find(m => /paraprofessional/i.test(m.func_desc))
  const guidance = swap.find(m => /guidance/i.test(m.func_desc))

  const say = (k: string) => d.said.find(q => q.key === k)
  const found = d.searched.filter(s => s.documents > 0)
  const empty = d.searched.filter(s => s.documents === 0)

  return (
    <ReportShell tab={TAB} dataUrl={DATA}
      title={<>
        In FY{d.latest_year} grants fell in {latest.swap.n + latest.reduction.n} parts of
        the school budget. The town&rsquo;s money rose in {latest.swap.n} of them.
      </>}
      standfirst={<>
        Every dollar the district spent, split by the fund that paid it, FY{d.fy_first} to
        FY{d.fy_last} &mdash; from the state&rsquo;s End of Year Financial Report.
      </>}
    >

      <div className="grid gap-7 mt-9"
        style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 12rem), 1fr))' }}>
        <Stat value={pct1(d.town_share_last)}>
          of school spending came out of the general fund in FY{d.fy_last}, against{' '}
          {pct1(d.town_share_first)} in FY{d.fy_first}
        </Stat>
        <Stat value={`${latest.swap.n} · ${usd(latest.swap.d_gen_fund)}`}
          tone="var(--series-cost)">
          functions where grants fell and the general fund rose &mdash; grants{' '}
          {usd(latest.swap.d_grants)}
        </Stat>
        <Stat value={`${latest.reduction.n} · ${usd(latest.reduction.d_gen_fund)}`}
          tone="var(--fund-enterprise)">
          functions where grants fell and the general fund did not rise &mdash; grants{' '}
          {usd(latest.reduction.d_grants)}
        </Stat>
        {/* THE GRANT FALL ALONE, AND DELIBERATELY WITHOUT ITS PARTNER. The aggregate
            general fund movement is a real figure and it is NOT in this row, because the
            two side by side are the near-identity that reads as a handover and is not one.
            One side of it is a measurement of what left. Both sides in one glance is the
            district-wide netting this page refuses to report, and the only place they
            appear together is inside the section that explains why. Do not "finish" this
            row. */}
        <Stat value={usd(latest.aggregate.d_grants)} tone="var(--status-warning)">
          the grant fall across every function present in both years &mdash; the largest in
          the record, against {usd(worstPriorFall.aggregate.d_grants)} in
          FY{worstPriorFall.fy}
        </Stat>
      </div>

      {/* THE CAVEAT THAT LEADS. Rule 7a's one exception: it changes whether the reader
          should trust anything below it. A fund total is not a grant and a dollar is not
          a post, and this page is otherwise very easy to over-read. */}
      <div className="card p-4 mt-9 max-w-3xl"
        style={{ borderLeft: '4px solid var(--status-warning)' }}>
        <p className="text-[14px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
          <strong>These are fund totals, not grants, and not people.</strong> The state
          collects what each district spent against each of its own function codes and
          splits it two ways: the general fund, and grants and revolving funds together.
          It does not name a grant, it does not name a post, and a general fund rise beside
          a grant fall in the same function is <em>consistent with</em> the town picking up
          a cost without establishing it. Nothing on this page says the town took over any
          particular thing, because nothing published says that.
        </p>
        <p className="mt-3">
          <Basis level="stated">the district&rsquo;s own statutory return to the state</Basis>
        </p>
      </div>

      {/* ------------------------------------------------------- 1. conclusions */}
      <H2 id="findings">What this establishes</H2>
      <div className="grid gap-4 mt-6"
        style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 20rem), 1fr))' }}>
        <Insight n={1} headline={
          <>The general fund carries {pct1(d.town_share_last)} of school spending, up{' '}
            {d.town_share_points.toFixed(1)} points since FY{d.fy_first} &mdash; and it did
            not get there in a straight line.</>}>
          Grants and revolving funds paid {pct1(share(first))} of everything the district
          spent in FY{first.fy} and {pct1(share(last))} in FY{last.fy}. In between they fell
          to {pct1(share(trough))} in FY{trough.fy} and came back to{' '}
          {pct1(share(rebound))} in FY{rebound.fy}
          {lastHigherFy ? <>, their highest share since FY{lastHigherFy}</> : null}. Whatever
          else this shows, the share the town carries is not fixed, and a budget that
          assumes it is will be wrong in both directions.
        </Insight>
        <Insight n={2} headline={
          <>FY{d.latest_year} is the biggest year on record for both things at once:{' '}
            {latest.swap.n} functions where the town&rsquo;s money replaced grant money,
            and {latest.reduction.n} where it did not.</>}>
          In the first group grants fell {mag(latest.swap.d_grants)} and the general fund
          rose {mag(latest.swap.d_gen_fund)}. In the second grants fell{' '}
          {mag(latest.reduction.d_grants)} and the general fund fell{' '}
          {mag(latest.reduction.d_gen_fund)} as well. No earlier year comes close on either
          count &mdash; the largest previous swap was {mag(worstPriorSwap.swap.d_grants)} of
          grants in FY{worstPriorSwap.fy}.
        </Insight>
        <Insight n={3} headline={
          <>Read district-wide, FY{d.latest_year} looks like an almost exact replacement.
            That reading is wrong, and it is the easiest mistake on this page to make.</>}>
          Across the {latest.aggregate.n} functions present in both years, grants fell{' '}
          {mag(latest.aggregate.d_grants)} and the general fund rose{' '}
          {mag(latest.aggregate.d_gen_fund)} &mdash; a total change of{' '}
          {usd(latest.aggregate.d_total)}. Two numbers that close to each other invite one
          sentence: the town picked up what the grants stopped paying. Decomposed, it is
          two unrelated movements landing on similar figures, and the section below shows
          which.
        </Insight>
        <Insight n={4} headline={
          <>Even where the town&rsquo;s money rose, it usually did not rise by as much
            &mdash; {swapShort.length} of the {swap.length} swaps still spent less in total
            than the year before.</>}>
          {guidance ? <>{guidance.func_desc} is the clearest: grants{' '}
            {usd(guidance.d_grants)}, general fund {usd(guidance.d_gen_fund)}, so{' '}
            {mag(guidance.d_total)} less was spent against that function across both funds
            than in FY{d.latest_year - 1}. </> : null}
          A function in the swap group is one where the general fund <em>rose</em>. It is
          not one where the town made the function whole, and the two are different claims.
        </Insight>
      </div>

      {/* -------------------------------------------------- the trap, as its own section */}
      <H2 id="trap">The number this page nearly published</H2>
      <Body>
        The first version of this analysis had one headline: <em>grants fell{' '}
        {mag(latest.aggregate.d_grants)}, the general fund rose{' '}
        {mag(latest.aggregate.d_gen_fund)}, and the district spent{' '}
        {mag(latest.aggregate.d_total)} less in all.</em> Those three figures are
        correct. The sentence anybody would build from them is not.
      </Body>
      <div className="grid gap-4 mt-6"
        style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 16rem), 1fr))' }}>
        <div className="card p-4">
          <p className="text-[11px] font-semibold uppercase tracking-widest mb-1.5"
            style={{ color: 'var(--text-muted)' }}>What the aggregate says</p>
          <p className="text-[14px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
            Grants {usd(latest.aggregate.d_grants)}. General fund{' '}
            {usd(latest.aggregate.d_gen_fund)}. Net {usd(latest.aggregate.d_total)} across{' '}
            {latest.aggregate.n} functions. It reads as a handover.
          </p>
        </div>
        <div className="card p-4">
          <p className="text-[11px] font-semibold uppercase tracking-widest mb-1.5"
            style={{ color: 'var(--text-muted)' }}>What the decomposition says</p>
          <p className="text-[14px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
            {latest.swap.n} functions swapped: {mag(latest.swap.d_grants)} of grants out,{' '}
            {mag(latest.swap.d_gen_fund)} of general fund in. {latest.reduction.n} functions
            simply lost the money: {mag(latest.reduction.d_grants)} of grants, and a further{' '}
            {mag(latest.reduction.d_gen_fund)} of general fund on top.
          </p>
        </div>
        <div className="card p-4">
          <p className="text-[11px] font-semibold uppercase tracking-widest mb-1.5"
            style={{ color: 'var(--text-muted)' }}>And what is actually the biggest number</p>
          <p className="text-[14px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
            {biggestRise.func_desc} rose {usd(biggestRise.d_gen_fund)} in the general fund
            &mdash; on its own, larger than the entire grant fall. Grants in that function
            moved {usd(biggestRise.d_grants)}. Meanwhile {biggestFall.func_desc} fell{' '}
            {mag(biggestFall.d_total)} across both funds.
          </p>
        </div>
      </div>
      <Body>
        So the aggregate is several things at once. {latest.swap.n} functions did hand
        over from one fund to the other. Across the{' '}
        {latest.grant_growth.n + latest.other.n} functions where grants did <em>not</em>{' '}
        fall, the general fund moved{' '}
        {usd(latest.grant_growth.d_gen_fund + latest.other.d_gen_fund)} &mdash; a movement
        with no grant fall anywhere behind it, and it is bigger than the swap. The total
        lands near zero because large changes in both directions cancel, not because one
        replaced the other. <strong>The near-identity is a coincidence of magnitudes, and
        it is the only thing on this page that would have been quoted at a
        meeting.</strong>
      </Body>
      <NotShown>
        This section does not establish that the aggregate is meaningless &mdash; it is a
        real total of real figures. It establishes that the aggregate cannot answer the
        question people ask of it. And the decomposition has its own limit: sorting a
        function into &ldquo;swapped&rdquo; or &ldquo;reduced&rdquo; is <strong>our</strong>
        {' '}classification, on the signs of two numbers, and the state publishes no such
        label.
      </NotShown>

      {/* ------------------------------------------------- 2. organised categorically */}
      <H2 id="split">Both funds, every year the state has collected them</H2>
      <Body>
        The two parts of one total &mdash; the state&rsquo;s own <code>total</code> column,
        which the extract reconciles to before any of this is published. The general fund
        is what the town appropriates and argues about at Town Meeting. Everything above it
        is money the district spends that never appears in that argument.
      </Body>
      <BothFunds series={S} />
      <TableTwin
        caption="The same figures"
        head={['Year', 'General fund', 'Grants and revolving', 'All funds',
               'General fund share']}
        rows={S.map(p => [fy(p.fy), usd(p.gen_fund), usd(p.grants), usd(p.total),
                          pct1(p.town_share)])} />

      <H3>The same thing as a share, plotted from zero</H3>
      <Body>
        The general fund share never drops below {pct1(Math.min(...S.map(p => p.town_share)))}
        {' '}across the whole record, so drawing it needs an axis that does not start at
        zero &mdash; and a truncated axis on a share turns a real move into a cliff. Its
        complement carries the same information and starts at zero.
      </Body>
      <GrantShare series={S} />
      <NotShown>
        A share moves when either part moves. Grants falling to{' '}
        {pct1(share(trough))} in FY{trough.fy} is consistent with grants shrinking, with
        general fund spending growing, and with both &mdash; and the dollar chart above is
        where to check which. Nor is a share a judgement: a district with more grant money
        is not thereby better funded, and one with less is not thereby cut.
      </NotShown>

      <H2 id="classes">Where grants fell, and what happened next</H2>
      <Body>
        Every function present in two consecutive years, sorted on the signs of two
        numbers. The top panel is the functions where grants fell <em>and</em> the general
        fund rose. The bottom is the functions where grants fell and the general fund did
        not. They share a scale so they can be compared &mdash; and they are drawn apart
        so they cannot be added, because adding them is the aggregate this page refuses to
        report.
      </Body>
      <SwapAndReduction years={Y} />
      <TableTwin
        caption="Every year, both classes, never netted"
        max={420}
        head={['Year', 'Swapped: functions', 'Swapped: grants', 'Swapped: general fund',
               'Reduced: functions', 'Reduced: grants', 'Reduced: general fund',
               'Functions matched']}
        rows={Y.map(y => [
          fy(y.fy), y.swap.n, usd(y.swap.d_grants), usd(y.swap.d_gen_fund),
          y.reduction.n, usd(y.reduction.d_grants), usd(y.reduction.d_gen_fund),
          y.aggregate.n,
        ])} />
      <H3>The largest single swaps in the whole record</H3>
      <Body>
        One function, one year, ranked on how far the grant money fell. The list is here
        because the year-by-year totals above are sums over many functions, and a reader
        should be able to see which individual movements are doing the work.
      </Body>
      <TableTwin
        head={['Year', 'Function', 'Code', 'Grants', 'General fund', 'All funds']}
        max={340}
        rows={d.biggest_swaps.map(m => [fy(m.fy), m.func_desc, m.func_code,
          usd(m.d_grants), usd(m.d_gen_fund), usd(m.d_total)])} />
      <NotShown>
        A function is a bucket, not a programme: <em>Teachers, Classroom</em> is one code
        covering every classroom teacher in the district. Both funds can move inside one
        code for reasons that have nothing to do with each other, and this classification
        cannot see that. It also has nothing to say about functions that appear in one year
        and not the next &mdash; those cannot be differenced at all, and are simply absent
        from both panels.
      </NotShown>

      <H2 id="functions">FY{d.latest_year}, function by function</H2>
      <H3>Grants fell and the general fund rose</H3>
      <Body>
        {swap.length} functions. Grants {usd(latest.swap.d_grants)}, general fund{' '}
        {usd(latest.swap.d_gen_fund)}. The signs are kept from here down: these are tables
        of movements rather than sentences about them.
      </Body>
      <MoveRows moves={swap} />
      <TableTwin
        head={['Function', 'Code', 'In or out of district', 'Grants', 'General fund',
               'All funds']}
        rows={swap.map(m => [m.func_desc, m.func_code, m.in_out, usd(m.d_grants),
                             usd(m.d_gen_fund), usd(m.d_total)])} />

      <H3>Grants fell and the general fund did not rise</H3>
      <Body>
        {reduction.length} functions. Grants {usd(latest.reduction.d_grants)}, general fund{' '}
        {usd(latest.reduction.d_gen_fund)}.
      </Body>
      <MoveRows moves={reduction} />
      <TableTwin
        head={['Function', 'Code', 'In or out of district', 'Grants', 'General fund',
               'All funds']}
        rows={reduction.map(m => [m.func_desc, m.func_code, m.in_out, usd(m.d_grants),
                                  usd(m.d_gen_fund), usd(m.d_total)])} />

      <H3>And the largest general fund increases, whatever the grants did</H3>
      <Body>
        The two lists above are selected on a grant falling, which is exactly the selection
        that makes a year look like a handover. These are the biggest general fund
        movements in FY{d.latest_year} without that filter.
      </Body>
      <TableTwin
        head={['Function', 'Code', 'General fund', 'Grants', 'All funds']}
        rows={d.latest_gen_fund_rises.map(m => [m.func_desc, m.func_code,
          usd(m.d_gen_fund), usd(m.d_grants), usd(m.d_total)])} />
      <TableTwin
        caption="And the largest falls across both funds"
        head={['Function', 'Code', 'All funds', 'Grants', 'General fund']}
        rows={d.latest_total_falls.map(m => [m.func_desc, m.func_code, usd(m.d_total),
          usd(m.d_grants), usd(m.d_gen_fund)])} />

      {paras && (
        <>
          <H3>The one line this project has flagged as load-bearing</H3>
          <Body>
            The in-district special education escalator in this project&rsquo;s model rests
            on a paraprofessional line, and the standing note beside it says the line cannot
            be distinguished from grant money unwinding. In FY{d.latest_year} function{' '}
            {paras.func_code}, {paras.func_desc}, moved {usd(paras.d_grants)} in grants and{' '}
            {usd(paras.d_gen_fund)} in the general fund &mdash; {usd(paras.d_total)} across
            both. This is as close as the published record gets, and it is not close enough:
            it shows the funding mix for a function moving. It does not show a post moving,
            or a person, or the same work being paid for from a different pocket.
          </Body>
          <Maybe settle={<>the district&rsquo;s grant award and payroll charge detail for
            these posts, by fund and fiscal year &mdash; which would say which post each
            grant paid and what happened to it, and which nothing published does.</>}>
            The obvious reading is that federal money which had been paying for
            paraprofessionals ran out and the town picked some of it up. It fits. So does a
            reallocation between codes, a change in how a post is classified, or an unrelated
            general fund increase in the same code in the same year. Nothing in the state
            return distinguishes them.
          </Maybe>
        </>
      )}

      {/* ------------------------------------------------------- what the town said */}
      <H2 id="said">What was said at the time</H2>
      <Body>
        This project&rsquo;s method requires it: for anything a report says rose or fell,
        search the meeting archive for what people said about that thing in the same year.
        This is the one page where the answer is abundant. The end of the federal money was
        discussed at length, by name, with figures attached, and well before it
        happened.
      </Body>
      <div className="grid gap-4 mt-6"
        style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 21rem), 1fr))' }}>
        {d.said.map(q => <Quote key={q.key} q={q} />)}
      </div>
      <NotShown>
        Every one of these is a statement of <strong>intent or of belief</strong>, made by
        people describing a budget they were about to vote. None of them is a measurement,
        and this page does not test any of them against the state&rsquo;s figures &mdash; a
        stated plan not to shift a cost onto the town and a function where the general fund
        rose are not the same quantity, are not on the same calendar, and would not be
        reconciled by putting them side by side. They are here because a reader is entitled
        to know that the thing being measured was discussed, and how.
      </NotShown>
      <Body>
        The terms run against the archive, with what each returned:{' '}
        {found.map((s, i) => (
          <span key={s.term}>{i > 0 ? ', ' : ''}<strong>{s.term}</strong> in{' '}
            {s.documents.toLocaleString()}</span>
        ))}
        {empty.length ? <> &mdash; and{' '}
          {empty.map((s, i) => (
            <span key={s.term}>{i > 0 ? ', ' : ''}<strong>{s.term}</strong></span>
          ))} in none</> : null}. Searched across{' '}
        {d.minutes.text_files_present.toLocaleString()} extracted documents, out of{' '}
        {d.minutes.held.toLocaleString()} the archive holds. Only{' '}
        {d.minutes.searchable.toLocaleString()} of those &mdash;{' '}
        {Math.round(d.minutes.searchable_share * 100)}% &mdash; carry readable text at all;
        the other {d.minutes.unsearchable.toLocaleString()} are mostly image scans
        ({d.minutes.image_scan.toLocaleString()} of them) awaiting OCR.{' '}
        <strong>An empty result above is a statement about the readable archive and never
        about the town.</strong>
      </Body>

      {/* WHAT A BOARD MEMBER CAME FOR. Added by the persona review: the Finance
          Committee reader's test is whether the report tells them one thing they could do
          differently, and the School Committee reader's is whether the question they will
          actually ask is answered before they have to ask it. Neither was, and no verifier
          can catch that. */}
      <H2 id="coming">What would have shown this coming</H2>
      <Body>
        <strong>The district said it, in public, with a figure, before the budget was
        voted.</strong> The loss was named to the School Committee on{' '}
        {say('loss')?.date} and again on {say('insurance')?.date}, alongside the insurance
        increase that was <em>not</em> anticipated. Whatever else is arguable here, naming a
        known cliff far enough ahead to plan around it is the thing a board most needs and
        does not always get, and the record shows it happening.
      </Body>
      <Body>
        <strong>And the fund split is published every year.</strong> The state has collected
        it since FY{d.fy_first}; it arrives after the year closes, so it is a check on what
        happened rather than a warning about what is coming. What neither source carries is
        which grant &mdash; and that is the number that would have let anybody test the
        claim being made at the time.
      </Body>
      <H3>One thing to ask for next year</H3>
      <Body>
        The district&rsquo;s <strong>end-of-year grant expenditure detail by grant
        code</strong> &mdash; or Schedule 19 of the End of Year Financial Report as filed,
        which lists each grant separately &mdash; alongside the budget rather than after it.
        That single document turns &ldquo;grants and revolving funds fell{' '}
        {mag(latest.aggregate.d_grants)}&rdquo; into a statement about named programmes
        with end dates, which is what a board is being asked to plan against. It is a
        report the accounting the district already files can produce.
      </Body>
      <H3>&ldquo;Were the cuts really only the grant money?&rdquo;</H3>
      <Body>
        It is the question this page will be read for, and the honest answer is that
        nothing here tests it. The claim is about posts and contracts; this source reports
        dollars against function codes, split two ways, with every grant and every
        revolving fund in one column. Those are different quantities on different calendars,
        and putting them beside each other would not reconcile them. What the state&rsquo;s
        figures do show is that in FY{d.latest_year} the money left{' '}
        {latest.swap.n + latest.reduction.n} functions and the general fund rose in{' '}
        {latest.swap.n} of them &mdash; which bounds the question and does not settle it.
      </Body>

      {/* --------------------------------------------------- 3. raw, method, caveats */}
      <H2 id="method">How this was measured</H2>
      <Body>
        One table. <code>{d.source.table}</code>, LEA <code>{d.source.lea}</code>. The
        FY{d.fy_first}&ndash;FY{d.fy_last} frame comes from the rows the state marks as the
        district total; every function-level figure comes from the detail rows, joined to
        themselves one year apart on the function code and on whether the spending is in or
        out of district. {latest.aggregate.n} functions matched across
        FY{d.latest_year - 1}&ndash;FY{d.latest_year}.
      </Body>
      <Body>
        Each matched function falls into exactly one of four classes, on the signs of two
        differences. <strong>These labels are ours.</strong> The state publishes the two
        columns and no classification of them.
      </Body>
      <TableTwin
        caption={`The four classes, and FY${latest.fy} in each`}
        head={['Class', 'What it means', 'Functions', 'Grants', 'General fund']}
        rows={[
          ['swapped', 'grants fell and the general fund rose', latest.swap.n,
           usd(latest.swap.d_grants), usd(latest.swap.d_gen_fund)],
          ['reduced', 'grants fell and the general fund did not rise', latest.reduction.n,
           usd(latest.reduction.d_grants), usd(latest.reduction.d_gen_fund)],
          ['grants grew', 'grants rose', latest.grant_growth.n,
           usd(latest.grant_growth.d_grants), usd(latest.grant_growth.d_gen_fund)],
          ['grants unchanged', 'no grant money moved either way', latest.other.n,
           usd(latest.other.d_grants), usd(latest.other.d_gen_fund)],
          ['every matched function', 'the aggregate — not a finding', latest.aggregate.n,
           usd(latest.aggregate.d_grants), usd(latest.aggregate.d_gen_fund)],
        ]} />
      <Body>
        The last row is in the table because the four classes have to be seen to account
        for every function &mdash; three of them adding to something short of the total,
        with no way to tell which functions were missing, is worse than printing the
        aggregate with a label on it. It is not a finding and the page does not use it as
        one.
      </Body>

      <H3>A figure we computed that is not a measurement</H3>
      <Body>
        {d.counterfactual.what} If grants and revolving funds had gone on paying{' '}
        {pct1(share(first))} of everything, the general fund would have carried{' '}
        {usd(d.counterfactual.gen_fund_at_first_share)} in FY{d.fy_last} rather than{' '}
        {usd(d.counterfactual.gen_fund_actual)} &mdash; a difference of{' '}
        {usd(d.counterfactual.difference)}.
      </Body>
      <NotShown>
        That is arithmetic on a counterfactual, not a saving and not a cost. It assumes the
        district would have spent the same total either way, which is the assumption most
        likely to be wrong: grant money is largely competitive and time-limited, and a
        district with less of it usually does less rather than the same for more. Quoting
        it as &ldquo;what the grants ending cost the town&rdquo; would be exactly the
        error this page is about.
      </NotShown>

      <H2 id="cannot">What this cannot say</H2>
      <div className="flex flex-col gap-3 mt-6 max-w-3xl">
        {d.not_established.map(n => (
          <div key={n} className="card p-4">
            <p className="text-[14px] leading-relaxed"
              style={{ color: 'var(--text-secondary)' }}>{n}</p>
          </div>
        ))}
      </div>
      <Body>
        <strong>Closes:</strong> {d.closes} These limits are rows in the register at{' '}
        <a className="underline" style={{ color: 'var(--series-cost)' }}
          href={abs('/what-we-cannot-answer')}>what we cannot answer</a>, which is what the
        records request reads &mdash; not prose written only here.
      </Body>

      <H2 id="source">The document behind this</H2>
      <Body>
        {d.source.publisher}. {d.source.note} Our copy is{' '}
        <a className="underline break-all" style={{ color: 'var(--series-cost)' }}
          href={abs(d.source.docs_url)}>{d.source.path.split('/').pop()}</a>{' '}
        ({(d.source.bytes / 1e6).toFixed(1)} MB), fetched from{' '}
        <a className="underline break-all" style={{ color: 'var(--series-cost)' }}
          href={d.source.url}>{d.source.url}</a>. Its sha256 is{' '}
        <code className="break-all">{d.source.sha256}</code>.
      </Body>
      <Body>
        The payload this page draws is published whole at{' '}
        <a className="underline" style={{ color: 'var(--series-cost)' }}
          href={abs('/data/grant-unwinding.json')}>/data/grant-unwinding.json</a>, and the
        rows behind it can be queried directly &mdash; see{' '}
        <a className="underline" style={{ color: 'var(--series-cost)' }}
          href={abs('/database')}>the database</a>. The same DESE split, for the categories
        where the district&rsquo;s own book took lines to zero, is on{' '}
        <a className="underline" style={{ color: 'var(--series-cost)' }}
          href={abs('/what-stopped-being-funded')}>what stopped being funded</a>.
      </Body>

      <div className="card p-4 mt-8 max-w-3xl" style={{ borderLeft: '4px solid var(--axis)' }}>
        <p className="text-[11px] font-semibold uppercase tracking-widest mb-1.5"
          style={{ color: 'var(--text-muted)' }}>One thing about scope</p>
        <p className="text-[14px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
          <strong>This is the school department only, and it is a statutory return.</strong>
          {' '}The district files it to the state&rsquo;s definitions rather than its own,
          which is what makes {d.series.length} comparable years possible at all &mdash; the
          district&rsquo;s own budget book changed shape twice in the same period.
          Nothing here compares the town side with the school side; the town codes its
          accounts by function and the district files against DESE&rsquo;s, and this
          project refuses to invent the mapping between them.
        </p>
      </div>
    </ReportShell>
  )
}

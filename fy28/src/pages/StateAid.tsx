import { useEffect, useState } from 'react'
import { usd } from '../model/engine'
import {
  ByAccount, Formula, Peers, Pupils, PupilTrend, Receipts, TableTwin, Variance, WhoPays,
  fy, pct, share, signed,
  type Account, type PeerRow, type PupilCount, type PupilPoint, type ReceiptYear,
  type VarYear,
} from '../components/StateAidCharts'

/** State aid — the part of the school budget Lunenburg does not vote on.
 *
 *  WHY THIS PAGE EXISTS. Rule 11's last paragraph, measured. Every other page in this area
 *  is about what the schools spend. This one is about the fact that an appropriation is not
 *  the town's bill: the bill is what is left after state aid, and state aid is decided in
 *  the Governor's budget and the Legislature's. A year where aid rises and the
 *  appropriation rises with it is not the same year as one where aid is flat and the town
 *  covers the difference — and nothing on the expense side can tell them apart.
 *
 *  THE CITIZEN QUESTION IT ANSWERS. "The schools want $26 million — where does that come
 *  from, and how much of it is up to us?" The answer, in one line, is that about a third
 *  arrives from the state on a formula nobody here writes, and the other two thirds is the
 *  tax bill.
 *
 *  SHAPE (rule 7b). Conclusions, then the organised categories, then the raw and the
 *  caveats. A reader who stops after the first screen should still carry away something
 *  they could repeat at a meeting.
 *
 *  RULE 1 IS THE DIFFICULTY HERE. This page holds an ACTUAL series (Chapter 70 received,
 *  from the annual town reports), a BUDGET figure (Chapter 70 estimated, from the FY2026
 *  ledger), and a FORMULA (DESE's FY27 calculation). They are never subtracted across each
 *  other and no growth rate is measured between two of them. Every chart says which stage
 *  it is. The one place the two stages ARE differenced is the Division of Local Services'
 *  own free cash proof line, and it is labelled as the state's arithmetic rather than ours.
 *
 *  RULE 7. A cherry sheet shortfall is a measurement. "The state cut aid" is a hypothesis,
 *  and so is "the town estimated badly" — the same figure fits both, because the estimate
 *  and the receipt both move. Both are given, and neither is stated as the finding.
 *
 *  RULE 2. Not one figure is typed into this file. Everything arrives from
 *  /data/state-aid.json, written by scripts/build_state_aid.py.
 *
 *  NO D1 AT PAGE LOAD. One static file. */

type Payload = {
  generated_by: string
  source: string
  ledger: {
    fy: number; period: number; doc_id: string
    accounts: Account[]
    aid_budgeted: number; aid_received: number
    school_named_budgeted: number; general_named_budgeted: number
    local_option_budgeted: number; local_option_received: number
    local_option_accounts: string[]
    ch70: Account & { still_to_come: number }
    with_a_figure: number
    revenue_total: number; revenue_accounts: number; aid_share_of_revenue: number
    school_appropriation: number
    school_departments: { dept: string; name: string; original: number }[]
    school_doc_id: string
    omnibus: number; omnibus_departments: number
    ch70_share_of_school: number; town_share_of_school: number; town_share_dollars: number
  }
  receipts: {
    series: ReceiptYear[]; span: number[]; checked: number[]
    not_checked: { fy: number; status: string; why: string | null
      unpublished_figure: number | null }[]
    growth: {
      first_fy: number; last_fy: number; first: number; last: number; years: number
      change: number; pct: number; cagr: number; stage: string
    }
  }
  variance: {
    line: string
    town: PeerRow & { series: VarYear[]; years: number[] }
    peers: PeerRow[]
    years: number[]; rank: number; of: number
    source_file: string; source_ref: string; peer_max_swing: number
    town_names: string[]
  }
  formula: {
    source: string; sheet: string; row: number; as_of: string | null; district: string
    cells: Record<string, string>
    enrollment: number; foundation: number; required: number; aid: number; nss: number
    aid_share: number; required_share: number
    aid_share_of_nss: number; required_share_of_nss: number
    aid_per_pupil: number; foundation_per_pupil: number
    operating_districts: number; median_aid_share: number
    rank: number; percentile: number
    fy: number
    lps_appropriation: number; enrollment_actual: number; appropriation_over_nss: number
    peers: { district: string; row: number; operating: boolean; aid: number
      foundation: number; aid_share: number | null }[]
  }
  pupils: {
    latest_fy: number; formula_fy: number; counts: PupilCount[]
    aid_per_foundation_pupil: number; spread: number
    spread_low: number; spread_high: number
    series: PupilPoint[]; series_years: number[]
  }
  assumption: {
    rate: number; base: number; governor: number | null
    enacted_above_governor: number; enacted_pct: number
    applies_to: string; ch70_share_of_base: number
    measured: number; measured_span: number[]; gap_points: number
  }
  said: { key: string; board: string; date: string; quote: string; why: string
    cite: string; town: string }[]
  corroboration: {
    stated: number; stated_by: string; stated_on: string; recomputed: number
    numerator: number; denominator: number; agrees: boolean; note: string
  }
  recomputed: { what: string; where: string; ours: string; why: string }[]
  gaps: { side: string; what: string; why: string; closes: string | null }[]
  related: { id: string; title: string; why: string; words: number; updated: string
    url: string; pdf: string | null }[]
}

function H2({ id, children }: { id?: string; children: React.ReactNode }) {
  return (
    <h2 id={id} className="text-2xl font-bold tracking-tight mt-14 mb-3 max-w-3xl
                           scroll-mt-[calc(var(--header-h)+1rem)]">{children}</h2>
  )
}

function H3({ children }: { children: React.ReactNode }) {
  return <h3 className="text-[15px] font-bold mt-9 mb-1 max-w-2xl">{children}</h3>
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
      <div className="text-3xl font-bold tracking-tight tnum"
        style={tone ? { color: tone } : undefined}>{value}</div>
      <div className="text-[13px] leading-snug mt-1 max-w-[15rem]"
        style={{ color: 'var(--text-secondary)' }}>{children}</div>
    </div>
  )
}

/** The half of every section that says what the measurement does NOT establish. */
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

/** A hypothesis, marked as one. Never rendered in the same voice as a measurement. */
function Maybe({ settle, children }: { settle: React.ReactNode; children: React.ReactNode }) {
  return (
    <div className="card p-4 mt-4 max-w-2xl"
      style={{ borderLeft: '4px solid var(--status-warning)' }}>
      <p className="text-[11px] font-semibold uppercase tracking-widest mb-1.5"
        style={{ color: 'var(--text-muted)' }}>
        A possible explanation &mdash; nothing here tests it
      </p>
      <div className="text-[14px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
        {children}
        <p className="mt-2.5"><strong>What would settle it:</strong> {settle}</p>
      </div>
    </div>
  )
}

/** One conclusion, at the top, in the shape somebody could repeat out loud. */
function Insight({ n, headline, children }: {
  n: number; headline: React.ReactNode; children: React.ReactNode
}) {
  return (
    <div className="card p-5">
      <div className="text-[11px] font-semibold uppercase tracking-widest mb-2"
        style={{ color: 'var(--text-muted)' }}>Finding {n}</div>
      <p className="text-[17px] font-bold leading-snug">{headline}</p>
      <p className="text-[14px] leading-relaxed mt-2.5" style={{ color: 'var(--text-secondary)' }}>
        {children}
      </p>
    </div>
  )
}

/** What somebody said at a public meeting, with the link to the minutes. */
function Said({ q }: { q: Payload['said'][number] }) {
  return (
    <div className="card p-4">
      <p className="text-[11px] font-semibold uppercase tracking-widest mb-2"
        style={{ color: 'var(--text-muted)' }}>{q.board} &middot; {q.date}</p>
      <blockquote className="text-[15px] leading-relaxed italic">&ldquo;{q.quote}&rdquo;</blockquote>
      <p className="text-[13.5px] leading-relaxed mt-2.5" style={{ color: 'var(--text-secondary)' }}>
        {q.why}
      </p>
      <p className="text-[12px] mt-2.5">
        <a className="underline" style={{ color: 'var(--series-cost)' }} href={q.cite}>
          the minutes, as text
        </a>
        {' · '}
        <a className="underline" style={{ color: 'var(--series-cost)' }} href={q.town}>
          the town&rsquo;s own copy
        </a>
      </p>
    </div>
  )
}

const money = (n: number) => usd(n)

export function StateAid() {
  const [d, setD] = useState<Payload | null>(null)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    let live = true
    fetch('/data/state-aid.json')
      .then(r => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then(j => { if (live) setD(j) })
      .catch(e => { if (live) setErr(String(e)) })
    return () => { live = false }
  }, [])

  if (err) {
    return (
      <div className="mx-auto max-w-6xl px-5 pt-14 pb-16">
        <h1 className="text-3xl font-bold tracking-tight">State aid</h1>
        <div className="card p-5 mt-8" style={{ borderLeft: '4px solid var(--status-warning)' }}>
          <p className="text-[15px] font-bold mb-1">The series did not load</p>
          <p className="text-[13.5px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
            {err}. Nothing on this page is typed into it, so with the file missing there is
            nothing to show rather than something stale. The underlying rows are published
            at{' '}
            <a className="underline" style={{ color: 'var(--series-cost)' }}
              href="/data/state-aid.json">/data/state-aid.json</a>.
          </p>
        </div>
      </div>
    )
  }

  if (!d) {
    return (
      <div className="mx-auto max-w-6xl px-5 pt-14 pb-16">
        <h1 className="text-3xl font-bold tracking-tight">State aid</h1>
        <p className="mt-4 text-[15px]" style={{ color: 'var(--text-muted)' }}>
          Loading the measured series&hellip;
        </p>
      </div>
    )
  }

  const L = d.ledger
  const R = d.receipts
  const V = d.variance
  const F = d.formula
  const P = d.pupils
  const A = d.assumption
  const C = d.corroboration
  const worst = V.town.series.reduce((a, b) => (b.amount < a.amount ? b : a))
  const best = V.town.series.reduce((a, b) => (b.amount > a.amount ? b : a))
  const allTowns = [V.town, ...V.peers].sort((a, b) => b.swing - a.swing)
  const regional = F.peers.filter(p => !p.operating)
  const trendMeasures = ['Student Headcount', 'In-District FTE Pupils', 'Total FTE Pupils']
  const scaleBroken = R.not_checked.filter(
    r => r.unpublished_figure != null && r.unpublished_figure < 1000)

  return (
    <div className="mx-auto max-w-6xl px-5 pt-14 pb-16">
      <p className="text-xs font-semibold uppercase tracking-widest mb-3"
        style={{ color: 'var(--text-muted)' }}>The money</p>
      <h1 className="text-4xl sm:text-5xl font-bold tracking-tight leading-[1.05] max-w-3xl">
        {share(L.ch70_share_of_school)} of the school budget arrives from the State House.
        Lunenburg votes on the rest.
      </h1>
      <p className="mt-5 text-lg leading-relaxed max-w-2xl"
        style={{ color: 'var(--text-secondary)' }}>
        In {fy(L.fy)} the town appropriated {money(L.school_appropriation)} to its schools
        and budgeted {money(L.ch70.budgeted)} of Chapter 70 aid to help pay for it. That
        figure is set in the Governor&rsquo;s budget and the Legislature&rsquo;s, on a
        formula written at the State House. So the school budget going up and the tax bill
        going up are two different events, and the spending side of the budget cannot tell
        them apart.
      </p>

      <div className="mt-10 flex flex-wrap gap-x-12 gap-y-6">
        <Stat value={money(L.ch70.budgeted)} tone="var(--series-cost)">
          Chapter 70 aid budgeted in {fy(L.fy)} &mdash; object{' '}
          <span className="tnum">{L.ch70.object}</span>, printed{' '}
          <code>{L.ch70.printed}</code>
        </Stat>
        <Stat value={money(L.town_share_dollars)} tone="var(--series-revenue)">
          the other {share(L.town_share_of_school)} of the school appropriation, which the
          town raises
        </Stat>
        <Stat value={share(L.aid_share_of_revenue)}>
          of all {money(L.revenue_total)} of budgeted general fund revenue is state aid
          &mdash; the second largest source after the tax levy
        </Stat>
        <Stat value={signed(worst.amount)} tone="var(--series-revenue)">
          the worst of {V.years.length} years of aid arriving below what the budget assumed
          &mdash; FY{String(worst.year).slice(2)}
        </Stat>
      </div>

      {/* ------------------------------------------------------------ 1. THE CONCLUSIONS */}
      <H2 id="findings">What this page establishes</H2>
      <Body>
        Five claims, each derived from the town&rsquo;s, the state&rsquo;s or the
        district&rsquo;s own documents, and each checkable from the tables further down.
      </Body>

      <div className="grid gap-4 mt-6"
        style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 20rem), 1fr))' }}>
        <Insight n={1} headline={
          <>Roughly a third of the school budget is not Lunenburg&rsquo;s decision, and the
            budget book never says so.</>
        }>
          {money(L.ch70.budgeted)} of Chapter 70 against a {money(L.school_appropriation)}{' '}
          appropriation is {share(L.ch70_share_of_school)}. Both figures are budget figures
          from the same {fy(L.fy)} ledger, which is what makes the ratio meaningful. A
          School Committee member put the same figure at{' '}
          {share(C.stated)} in public on {C.stated_on}; recomputed here it is{' '}
          {share(C.recomputed)}.
        </Insight>

        <Insight n={2} headline={
          <>Over five years the aid Lunenburg actually received differed from the aid its
            tax rate was set on by {money(V.town.mean_abs)} in an average year.</>
        }>
          The Division of Local Services publishes the difference on every town&rsquo;s free
          cash proof. Lunenburg&rsquo;s ran from {signed(worst.amount)} in FY
          {String(worst.year).slice(2)} to {signed(best.amount)} in FY
          {String(best.year).slice(2)} &mdash; a {money(V.town.swing)} span, the widest of
          the {V.of} towns this project holds proofs for. Aid came in above the estimate in{' '}
          {V.town.over} of {V.years.length} years and below it in {V.town.under}.
        </Insight>

        <Insight n={3} headline={
          <>The direction is far steadier than the size. In {V.town.over} of{' '}
            {V.years.length} years the surprise was in the town&rsquo;s favour.</>
        }>
          That is the answer to the question a board actually asks before it will look
          forward: is this stable enough to plan on? On the evidence here the aid estimate
          is usually beaten and occasionally missed badly, and the one bad year was large
          enough to matter &mdash; {signed(worst.amount)}, which is{' '}
          {share(Math.abs(worst.share_of_certified ?? 0))} of the free cash certified that
          year.
        </Insight>

        <Insight n={4} headline={
          <>The state decides both halves of the minimum: what it pays, and what
            Lunenburg must.</>
        }>
          DESE&rsquo;s {fy(F.fy)} Chapter 70 summary sets
          Lunenburg&rsquo;s required net school spending at {money(F.nss)} &mdash;{' '}
          {money(F.aid)} of Chapter 70 aid ({share(F.aid_share_of_nss)}) plus a required
          local contribution of {money(F.required)} ({share(F.required_share_of_nss)}).
          Neither number is decided in Lunenburg. The town&rsquo;s own vote decides only
          what it adds on top.
        </Insight>

        <Insight n={5} headline={
          <>Where it can be measured, Chapter 70 grew {pct(R.growth.cagr)} a year &mdash;
            more than double what the projection assumes.</>
        }>
          {money(R.growth.first)} received in {fy(R.growth.first_fy)} against{' '}
          {money(R.growth.last)} in {fy(R.growth.last_fy)}: {pct(R.growth.pct)} over{' '}
          {R.growth.years} years, actual against actual. This project&rsquo;s own projection
          grows <em>total</em> state aid at {pct(A.rate)} a year. Those are two different
          quantities over two different spans, so this is a flag and not a correction
          &mdash; but the {pct(A.rate)} has no stated source, and this is the first thing
          the archive has that bears on it.
        </Insight>
      </div>

      <NotShown>
        <p>
          None of the five says what state aid <em>bought</em>. The town&rsquo;s state aid
          accounts share no organisation code with any expense account &mdash; 0 of 222
          &mdash; so no aid dollar can be followed to a teacher, a bus or a building. Aid
          arrives as general revenue and is appropriated like any other dollar.
        </p>
        <p className="mt-2.5">
          Nor does a shortfall establish that the state cut anything. The gap between
          estimated and actual moves for two reasons at once: the state can revise what it
          sends, and the town can estimate differently. The same figure fits both, and the
          one line this archive holds cannot separate them &mdash; it reports every cherry
          sheet receipt together, so a miss cannot even be attributed to Chapter 70 rather
          than to one of the other {L.with_a_figure - 1} accounts.
        </p>
        <p className="mt-2.5">
          And {share(L.ch70_share_of_school)} is a ratio of two <em>budget</em> figures. It
          is not what share of what the schools <em>cost</em> the state pays: the
          appropriation is already net of grants, fees and revolving funds, and the state
          also pays into the schools through circuit breaker reimbursement and grants that
          appear in neither figure.
        </p>
      </NotShown>

      {/* ------------------------------------------------------- 2. ORGANISED CATEGORIES */}
      <H2 id="who-decides">Who decides the school dollar</H2>
      <Body>
        The {fy(L.fy)} school appropriation &mdash; departments{' '}
        {L.school_departments.map(x => x.dept).join(' and ')} of the town&rsquo;s own
        expense ledger &mdash; split by where the money to pay for it comes from. Both
        figures are budget figures, from the same ledger, at period {L.period}.
      </Body>
      <WhoPays
        total={L.school_appropriation} aid={L.ch70.budgeted}
        aidLabel={<>Chapter 70 aid. Set in the Governor&rsquo;s budget and the
          Legislature&rsquo;s, on a formula written at the State House.</>}
        townLabel={<>Everything else &mdash; overwhelmingly the property tax levy, which
          Town Meeting and the ballot decide.</>} />
      <TableTwin caption={`The two sides, FY${String(L.fy).slice(2)} period ${L.period}`}
        head={['', 'Amount', 'Share', 'Who decides it']}
        rows={[
          ['Chapter 70 aid', money(L.ch70.budgeted), share(L.ch70_share_of_school),
            'The Legislature'],
          ['Raised by the town', money(L.town_share_dollars),
            share(L.town_share_of_school), 'Town Meeting and the ballot'],
          ['School appropriation', money(L.school_appropriation), '100%', '—'],
        ]}
        note={<>The appropriation is departments{' '}
          {L.school_departments.map(x => `${x.dept} ${x.name.toLowerCase()}`).join(' and ')}.
          It excludes Monty Tech, which is a separate assessment, and it excludes school
          costs the town appropriates elsewhere &mdash; retiree health insurance is{' '}
          <a className="underline" style={{ color: 'var(--series-cost)' }}
            href="/health-insurance">its own page</a>.</>} />

      <Maybe settle={<>The Town&rsquo;s year-end recap beside the Cherry Sheet for the same
        year, which states estimated and actual receipts on one page.</>}>
        <p>
          It is tempting to read {share(L.ch70_share_of_school)} as &ldquo;the state pays a
          third of the schools&rdquo;. It may be roughly right and this page does not
          establish it. Chapter 70 is not earmarked: it arrives as general fund revenue, is
          appropriated with everything else, and the ledger provides no route from an aid
          account to any spending account.
        </p>
      </Maybe>

      <H2 id="ledger">Every state aid account in the {fy(L.fy)} budget</H2>
      <Body>
        {L.with_a_figure} of the {L.accounts.length} accounts in the state revenue range
        carry a figure this year, totalling {money(L.aid_budgeted)} budgeted and{' '}
        {money(L.aid_received)} received through period {L.period}. Chapter 70 is most of
        it; the accounts whose printed name says schools come to{' '}
        {money(L.school_named_budgeted)}.
      </Body>
      <ByAccount accounts={L.accounts} total={L.aid_budgeted + L.local_option_budgeted} />
      <TableTwin
        caption={`General fund revenue objects 45xx, FY${String(L.fy).slice(2)} period ${L.period}`}
        head={['Object', 'Printed', 'What it is', 'Budgeted', 'Received', '% in']}
        rows={L.accounts.filter(a => a.budgeted || a.received).map(a => [
          a.object, a.printed, a.meaning, money(a.budgeted), money(a.received),
          a.pct_received != null ? `${a.pct_received}%` : '—',
        ])}
        note={<>Two of these accounts are <strong>not aid</strong> and are excluded from
          every state aid total on this page: {L.local_option_accounts.join(' and ')}{' '}
          {L.local_option_accounts.length === 1 ? 'is a local tax' : 'are local taxes'} the
          town votes and the state merely collects and remits &mdash;{' '}
          {money(L.local_option_budgeted)} budgeted. Counting them as aid would inflate
          every figure above. Period {L.period} is not the year-end close: received figures
          will move, budgeted figures will not.</>} />

      <H2 id="received">Chapter 70 actually received, year by year</H2>
      <Body>
        What the town banked, from the Receipts page of the annual town report &mdash; an{' '}
        <strong>actual</strong>, never mixed with the budget figures above. Only{' '}
        {R.checked.length} of the {R.span.length} years in the span have a figure this
        project has established, and the rest are drawn as gaps rather than left out.
      </Body>
      <Receipts series={R.series} />
      <TableTwin caption="Chapter 70 received, and the years that are not established"
        head={['Year', 'Received', 'State of the extract', 'Report page']}
        rows={R.series.map(r => [
          fy(r.fy),
          r.amount != null ? money(r.amount) : '—',
          r.amount != null ? 'reconciled to the report’s own totals'
            : (r.why ?? r.status),
          r.page ?? '—',
        ])}
        note={<>Growth is measured inside one stage only: {money(R.growth.first)} in{' '}
          {fy(R.growth.first_fy)} to {money(R.growth.last)} in {fy(R.growth.last_fy)} is{' '}
          {pct(R.growth.pct)} over {R.growth.years} years, {pct(R.growth.cagr)} a year, an
          actual against an actual. No rate on this page runs from one of these to the{' '}
          {fy(L.fy)} budget figure: that difference would be partly growth and partly the
          step between an estimate and a receipt.</>} />

      {scaleBroken.length > 0 && (
        <NotShown>
          <p>
            {scaleBroken.map(r => fy(r.fy)).join(' and ')}{' '}
            {scaleBroken.length === 1 ? 'is' : 'are'} in the archive with{' '}
            {scaleBroken.length === 1 ? 'a figure' : 'figures'} of{' '}
            {scaleBroken.map(r => r.unpublished_figure?.toString()).join(' and ')} &mdash;
            visibly not dollars, because the extractor lost the thousands separators on
            those editions. A year whose figure is not dollars is exactly the year that
            must not be plotted, which is why the chart above shows a gap there rather
            than a bar. The other unestablished years hold plausible figures and are still
            drawn as gaps, because a figure nothing reconciles is not a figure this
            project publishes.
          </p>
        </NotShown>
      )}

      <H2 id="variance">How far the estimate misses</H2>
      <Body>
        This is the only place in the archive where an aid estimate and an aid receipt are
        subtracted, and it is the state that does the subtracting. Every year the Division
        of Local Services certifies a town&rsquo;s free cash it publishes a proof, and one
        line of it is <em>{V.line}</em> &mdash; the difference between the cherry sheet
        receipts the town budgeted and the ones that arrived. Above the line the town got
        more than it planned for; below it, the town covered the difference.
      </Body>
      <Variance series={V.town.series} />
      <TableTwin caption={`${V.town.town}, ${V.years.length} years — ${V.source_ref} of each year’s proof`}
        head={['Year', 'Over or short', 'Free cash certified', 'Share of it']}
        rows={V.town.series.map(r => [
          fy(r.year), signed(r.amount),
          r.certified != null ? money(r.certified) : '—',
          r.share_of_certified != null ? pct(r.share_of_certified) : '—',
        ])}
        note={<>The third column is there because it is the honest denominator: a cherry
          sheet surplus does not become spendable money, it becomes part of next
          year&rsquo;s certified free cash. The one shortfall year had to be absorbed the
          other way.</>} />

      <H3>Against eight comparison towns, on one dollar scale</H3>
      <Body>
        The same line from the same document for every town this project holds a free cash
        proof for. Each bar runs from that town&rsquo;s worst year to its best, and the tick
        is zero. {V.town.town} is the {V.rank === 1 ? 'widest' : `${V.rank}th widest`} of
        the {V.of}.
      </Body>
      <Peers rows={allTowns} town={V.town.town} />
      <TableTwin caption={`${V.line}, FY${String(V.years[0]).slice(2)}–FY${String(V.years[V.years.length - 1]).slice(2)}`}
        head={['Town', 'Worst year', 'Best year', 'Span', 'Average miss', 'Years over']}
        rows={allTowns.map(r => [
          r.town, signed(r.worst), signed(r.best), money(r.swing), money(r.mean_abs),
          `${r.over} of ${r.over + r.under}`,
        ])} />

      <NotShown>
        <p>
          These towns are not the same size, and a bigger town can miss by more dollars
          without missing by more proportionally. The panel is drawn in dollars because
          that is the unit the town budgets in and the unit a shortfall is felt in &mdash;
          not because the towns are equivalent. Nothing here normalises for population,
          levy or aid received, because this archive does not hold the cherry sheet totals
          that would be the denominator.
        </p>
        <p className="mt-2.5">
          And the line covers <em>all</em> cherry sheet receipts together. A year that came
          in short cannot be attributed to Chapter 70 rather than to Unrestricted General
          Government Aid or to any of the reimbursement accounts. That limit is registered
          below.
        </p>
      </NotShown>

      <H2 id="formula">The formula, and what it decides</H2>
      <Body>
        Chapter 70 is not a grant the town applies for. DESE calculates a{' '}
        <em>foundation budget</em> &mdash; what it judges an adequate education costs here
        &mdash; then decides how much of it Lunenburg must pay out of local taxes and pays
        the balance as aid. Row {F.row} of the {F.sheet} sheet, cells{' '}
        <code>{F.cells.foundation}</code> to <code>{F.cells.nss}</code>.
      </Body>
      <Formula required={F.required} aid={F.aid} nss={F.nss} />
      <TableTwin caption={`${F.source}, sheet ${F.sheet}, row ${F.row}${F.as_of ? ` — dated ${F.as_of}` : ''}`}
        head={['As DESE prints it', 'Cell', 'Value']}
        rows={[
          ['Foundation enrollment', F.cells.enrollment, F.enrollment.toLocaleString()],
          ['Foundation budget', F.cells.foundation, money(F.foundation)],
          ['Required contribution', F.cells.required, money(F.required)],
          ['Chapter 70 aid', F.cells.aid, money(F.aid)],
          ['Required net school spending', F.cells.nss, money(F.nss)],
        ]}
        note={<>The last three are an identity the sheet states itself &mdash;{' '}
          <code>{F.cells.required}</code> + <code>{F.cells.aid}</code> ={' '}
          <code>{F.cells.nss}</code>, exactly &mdash; and the build refuses to write if it
          stops holding. That identity is what licenses saying the state decides both
          halves rather than one.</>} />

      <H3>Against the {F.operating_districts} operating districts in the state</H3>
      <Body>
        Aid covers {share(F.aid_share)} of Lunenburg&rsquo;s foundation budget. The median
        operating district in the same table gets {share(F.median_aid_share)}, which puts
        Lunenburg {F.percentile > 0.5 ? 'above' : 'below'} the middle &mdash; rank{' '}
        {F.rank} of {F.operating_districts}. That is worth saying plainly, because the
        assumption in the room is usually the other way.
      </Body>
      <TableTwin caption="Lunenburg against the statewide distribution"
        head={['', 'Aid as a share of the foundation budget']}
        rows={[
          ['Lunenburg', share(F.aid_share)],
          [`Median of ${F.operating_districts} operating districts`,
            share(F.median_aid_share)],
          ['Lunenburg’s rank', `${F.rank} of ${F.operating_districts}`],
        ]}
        note={<>Aid per foundation pupil is {money(F.aid_per_pupil)} against a foundation
          budget of {money(F.foundation_per_pupil)} per pupil. Read the next section before
          treating either as a per-child figure.</>} />

      {regional.length > 0 && (
        <NotShown>
          <p>
            {regional.map(p => p.district).join(', ')} appear in the comparison panel above
            with {money(0)} of Chapter 70 in this table. That is not a town receiving no
            aid: {regional.length === 1 ? 'it is' : 'they are'} member{regional.length === 1 ? '' : 's'}{' '}
            of regional school districts, so their Chapter 70 is paid to the region rather
            than to the town, and the town&rsquo;s row on DESE&rsquo;s district table is
            zero. The two panels count different things and must not be read across.
          </p>
        </NotShown>
      )}

      <H2 id="pupils">How many children the aid is paid for</H2>
      <Body>
        Chapter 70 is calculated per pupil, and &ldquo;per pupil&rdquo; has more than one
        published answer. DESE runs the formula on a <em>foundation enrollment</em> of{' '}
        {F.enrollment.toLocaleString()} and separately publishes three other counts for the
        same district. In the latest year published they span{' '}
        {P.spread_low.toLocaleString()} to {P.spread_high.toLocaleString()} &mdash; a
        difference of {P.spread.toLocaleString()} children, from one agency.
      </Body>
      <Pupils counts={P.counts} />
      <TableTwin caption="Four published counts of the same district"
        head={['Count', 'Year', 'Value', 'Who publishes it, and why it differs']}
        rows={P.counts.map(c => [
          c.measure, fy(c.fy), c.value.toLocaleString(), c.who,
        ])}
        note={<>The aid-per-pupil figure in the previous section divides{' '}
          {money(F.aid)} by {F.enrollment.toLocaleString()}, the first of these. Divided by
          any of the others it is a different number, and no published document reconciles
          the foundation count to the children in the buildings.</>} />

      <H3>The counts DESE publishes, over every year it publishes them</H3>
      <PupilTrend series={P.series} measures={trendMeasures} />
      <TableTwin caption="DESE district profile, pupil counts by year"
        head={['Year', ...trendMeasures]}
        rows={P.series_years.map(y => [
          fy(y),
          ...trendMeasures.map(m => {
            const p = P.series.find(s => s.fy === y && s.measure === m)
            return p ? p.value.toLocaleString() : '—'
          }),
        ])} />

      <NotShown>
        <p>
          A pupil count is not a measure of what the schools do or of how much they cost.
          Two districts with the same count can have entirely different needs, and the
          foundation budget formula exists precisely because DESE does not treat them as
          equivalent &mdash; it weights for low income, English learners and students with
          disabilities. None of that weighting is on this page.
        </p>
      </NotShown>

      {/* --------------------------------------------------------------- 3. RAW AND CONTEXT */}
      <H2 id="said">What the town has said about it</H2>
      <Body>
        Every quote below was found by searching the meeting archive and is checked, on
        every build, to still be present in the document it is attributed to. They are here
        because they are the same subject from the other direction: what the people making
        these decisions say the constraint is.
      </Body>
      <div className="grid gap-4 mt-6"
        style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 22rem), 1fr))' }}>
        {d.said.map(q => <Said key={q.key} q={q} />)}
      </div>

      <div className="card p-5 mt-6 max-w-3xl"
        style={{ borderLeft: `4px solid ${C.agrees ? 'var(--series-cost)' : 'var(--status-warning)'}` }}>
        <p className="text-[11px] font-semibold uppercase tracking-widest mb-2"
          style={{ color: 'var(--text-muted)' }}>
          A figure stated in public, recomputed
        </p>
        <p className="text-[15px] leading-relaxed">
          The {C.stated_by} was told on {C.stated_on} that Chapter 70 covers{' '}
          <strong>{share(C.stated)}</strong> of the school budget. Recomputed from the
          town&rsquo;s own ledgers &mdash; {money(C.numerator)} against{' '}
          {money(C.denominator)} &mdash; it is <strong>{share(C.recomputed)}</strong>.{' '}
          {C.agrees ? 'The statement holds.' : 'The statement does not hold.'}
        </p>
        <p className="text-[13.5px] leading-relaxed mt-2.5"
          style={{ color: 'var(--text-secondary)' }}>{C.note}</p>
      </div>

      <H2 id="assumption">What the projection assumes, and what the record shows</H2>
      <Body>
        This project&rsquo;s own FY28 projection grows total state aid at{' '}
        <strong>{pct(A.rate)}</strong> a year from a {fy(F.fy)} base of {money(A.base)}.
        That rate is recorded in the method document as having no stated source and no
        derivation. Here is everything the archive holds that bears on it.
      </Body>
      <TableTwin caption="The assumption against the record"
        head={['', 'Figure', 'What it is']}
        rows={[
          ['The projection’s rate', pct(A.rate),
            `Forward, applied to ${A.applies_to}. No stated source.`],
          [`Chapter 70 received, FY${String(A.measured_span[0]).slice(2)}–FY${String(A.measured_span[1]).slice(2)}`,
            pct(A.measured), 'Measured, actual against actual, from the annual town reports'],
          ['The difference', `${A.gap_points > 0 ? '+' : ''}${A.gap_points} points`,
            'Not a correction — two different quantities over two different spans'],
          [`Chapter 70 as a share of the ${fy(F.fy)} aid base`, share(A.ch70_share_of_base),
            'Which is why the two are not interchangeable'],
          ['The FY27 enacted budget against the Governor’s proposal',
            `${signed(A.enacted_above_governor)} · ${pct(A.enacted_pct)}`,
            'One year’s move between the number a budget was drafted on and the one enacted'],
        ]}
        note={<>The last row is the one a resident can use directly: in the single year the
          town documented it, the enacted state budget landed{' '}
          {pct(A.enacted_pct)} above the Governor&rsquo;s proposal that the town&rsquo;s
          own revenue plan had been built on.</>} />

      <NotShown>
        <p>
          The measured rate is <em>Chapter 70 alone</em>, over FY
          {String(A.measured_span[0]).slice(2)}&ndash;FY{String(A.measured_span[1]).slice(2)},
          from five established observations in a twelve-year span. The projection&rsquo;s
          rate is for <em>total</em> state aid, forward from {fy(F.fy)}. Applying one to the
          other would be exactly the error this project keeps finding in its own work, so
          no rate is changed here and none is recommended. What is established is that the
          assumption has no stated basis and that the only measurement the archive holds
          runs well above it.
        </p>
      </NotShown>

      {d.recomputed.length > 0 && (
        <>
          <H2 id="disagreements">Where this page disagrees with something already written</H2>
          <Body>
            Both are carried here rather than reconciled away, because a figure quietly
            corrected is a figure nobody can check.
          </Body>
          <div className="grid gap-4 mt-5"
            style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 22rem), 1fr))' }}>
            {d.recomputed.map(r => (
              <div key={r.what} className="card p-4"
                style={{ borderLeft: '4px solid var(--status-warning)' }}>
                <p className="text-[14px] font-bold leading-snug">{r.what}</p>
                <p className="text-[13px] leading-relaxed mt-2"
                  style={{ color: 'var(--text-muted)' }}>{r.where}</p>
                <p className="text-[13.5px] leading-relaxed mt-2">
                  <strong>Recomputed:</strong> {r.ours}
                </p>
                <p className="text-[13.5px] leading-relaxed mt-2"
                  style={{ color: 'var(--text-secondary)' }}>{r.why}</p>
              </div>
            ))}
          </div>
        </>
      )}

      <H2 id="gaps">What cannot be answered, and the document that would</H2>
      <Body>
        These limits are registered in the project&rsquo;s gap register rather than only
        written here, so the next person to hit them finds them already named. They appear
        on{' '}
        <a className="underline" style={{ color: 'var(--series-cost)' }}
          href="/what-we-cannot-answer">what we cannot answer</a> and at{' '}
        <a className="underline" style={{ color: 'var(--series-cost)' }}
          href="/api/money_gaps.json">/api/money_gaps.json</a>.
      </Body>
      <div className="grid gap-4 mt-5"
        style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 20rem), 1fr))' }}>
        {d.gaps.map(g => (
          <div key={g.what} className="card p-4"
            style={{ borderLeft: `4px solid ${g.side === 'document_wanted' ? 'var(--series-cost)' : 'var(--status-warning)'}` }}>
            <p className="text-[11px] font-semibold uppercase tracking-widest mb-1.5"
              style={{ color: 'var(--text-muted)' }}>
              {g.side === 'document_wanted' ? 'A document we do not hold'
                : g.side === 'people' ? 'A limit on counting people'
                  : 'A conclusion we cannot draw'}
            </p>
            <p className="text-[14px] font-bold leading-snug">{g.what}</p>
            <p className="text-[13.5px] leading-relaxed mt-2"
              style={{ color: 'var(--text-secondary)' }}>{g.why}</p>
            {g.closes && (
              <p className="text-[13px] leading-relaxed mt-2.5"
                style={{ color: 'var(--text-secondary)' }}>
                <strong>Closes it:</strong> {g.closes}
              </p>
            )}
          </div>
        ))}
      </div>

      <H2 id="method">Where every figure came from</H2>
      <div className="card p-5 mt-4 max-w-3xl">
        <ul className="text-[14px] leading-relaxed space-y-2.5"
          style={{ color: 'var(--text-secondary)' }}>
          <li>
            <strong>The {fy(L.fy)} aid accounts</strong> &mdash; the town&rsquo;s own MUNIS
            revenue ledger, period {L.period}, at{' '}
            <a className="underline" style={{ color: 'var(--series-cost)' }}
              href={`/docs/${L.doc_id.replace(/^sources\//, '')}`}>
              {L.doc_id.split('/').pop()}
            </a>. The school appropriation is from the matching expense report,{' '}
            <a className="underline" style={{ color: 'var(--series-cost)' }}
              href={`/docs/${L.school_doc_id.replace(/^sources\//, '')}`}>
              {L.school_doc_id.split('/').pop()}
            </a>.
          </li>
          <li>
            <strong>Chapter 70 received</strong> &mdash; the Receipts page of the annual
            town reports. {R.checked.length} of {R.span.length} years reconcile to the
            totals those pages print; the rest are drawn as gaps and named in the table.
          </li>
          <li>
            <strong>The estimate error</strong> &mdash; the Division of Local Services free
            cash proofs, one line each ({V.source_ref}), for {V.of} towns over{' '}
            {V.years.length} years.
          </li>
          <li>
            <strong>The formula</strong> &mdash; <code>{F.source}</code>, sheet{' '}
            {F.sheet}, row {F.row}. The build asserts the sheet&rsquo;s column headings
            before reading a figure from them, and checks the whole row against the copy
            typed into <code>model/taxbase.py</code>: two independent routes to the same
            five numbers.
          </li>
          <li>
            <strong>The quotes</strong> &mdash; the meeting archive. Each is asserted, on
            every build, to still be present verbatim in the document it is attributed to.
          </li>
          <li>
            <strong>Everything on this page</strong> is written by{' '}
            <code>{d.generated_by}</code> into{' '}
            <a className="underline" style={{ color: 'var(--series-cost)' }}
              href="/data/state-aid.json">/data/state-aid.json</a>. No figure is typed into
            the page, and <code>scripts/check_generated.py</code> fails if the file stops
            reproducing.
          </li>
        </ul>
      </div>

      <H2 id="related">The written analyses behind this</H2>
      <div className="grid gap-4 mt-5"
        style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 20rem), 1fr))' }}>
        {d.related.map(r => (
          <div key={r.id} className="card p-4">
            <p className="text-[14px] font-bold leading-snug">
              <a className="underline" style={{ color: 'var(--series-cost)' }} href={r.url}>
                {r.title}
              </a>
            </p>
            <p className="text-[13.5px] leading-relaxed mt-2"
              style={{ color: 'var(--text-secondary)' }}>{r.why}</p>
            <p className="text-[12px] mt-2 tnum" style={{ color: 'var(--text-muted)' }}>
              {r.words.toLocaleString()} words &middot; updated {r.updated}
              {r.pdf && (
                <>
                  {' · '}
                  <a className="underline" style={{ color: 'var(--series-cost)' }}
                    href={r.pdf}>PDF</a>
                </>
              )}
            </p>
          </div>
        ))}
      </div>

      <p className="text-[12.5px] mt-8 max-w-2xl" style={{ color: 'var(--text-muted)' }}>
        The {fy(L.fy)} ledger is period {L.period}, not the year-end close. Received figures
        here are through that period and will move; budgeted figures will not. The DESE
        Chapter 70 summary is the {fy(F.fy)} calculation as published
        {F.as_of ? ` on ${F.as_of}` : ''}, and Chapter 70 is recalculated every year.
      </p>
    </div>
  )
}

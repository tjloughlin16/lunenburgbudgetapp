import { useEffect, useState } from 'react'
import { usd } from '../model/engine'
import {
  ByAccount, DistrictLine, Scenarios, TableTwin, TownOverTime, WhereItSits,
  SIDE_LABEL, fy, pct, share,
  type Account, type Point, type TownYear, type Variant,
} from '../components/InsuranceCharts'

/** Health insurance — the school cost that is not in the school budget.
 *
 *  WHY THIS PAGE EXISTS. It is rule 11 with a concrete number attached. A resident reading
 *  the district's $26M budget book does not see the school retirees' health insurance,
 *  because it is appropriated to the town's INSURANCE department rather than to the
 *  schools. That is ordinary municipal accounting and it is not concealment — retirees are
 *  a Chapter 32B obligation of the town — but it means the school budget is not what the
 *  schools cost, and this page puts the account number on it.
 *
 *  PRECISION ABOUT WHAT THE ACCOUNT IS. `SCHRETHLTH` is health insurance for RETIREES of
 *  the schools. Not current staff — the district budgets its own active-employee health
 *  insurance separately, inside its appropriation, and both figures are on this page so
 *  neither can be mistaken for the other. Nothing here extends the claim past the name the
 *  ledger prints.
 *
 *  SHAPE (rule 7b). Conclusions, then the organised categories, then the raw and the
 *  caveats. A reader who stops after the first screen should still have carried something
 *  away they could repeat at a meeting.
 *
 *  RULE 7 IS THE DIFFICULTY HERE, TWICE. "The department's undivided line fell 58% in the
 *  year three lines replaced it" is a measurement. "The town began separating school costs"
 *  is a hypothesis. And an account that names neither side is not evidence that the money
 *  is the town's — five of the seven accounts name no side at all, and that limit is
 *  registered in the gap register rather than argued away here.
 *
 *  RULE 1. The district's budgeted line and its later-reported actual are drawn together
 *  because they are the same unit, and are never differenced across each other. Every
 *  growth figure on this page is one stage measured against itself.
 *
 *  RULE 2. Not one figure is typed into this file. Everything arrives from
 *  /data/health-insurance.json, written by scripts/build_insurance_charts.py.
 *
 *  NO D1 AT PAGE LOAD. One static file. */

type Change = {
  first_fy: number; last_fy: number; first: number; last: number
  change: number; pct: number | null; years: number; cagr: number | null
} | null

type ReportRow = {
  key: string; label: string; appropriated: number | null
  expended: number | null; side: string
}

type ReportYear = {
  fy: number; page: string | null; line_no: string | null; source: string
  rows: ReportRow[]; carried_forward: number
  printed_total: number | null; printed_expended: number | null
  summed_components: number | null; difference: number | null
  checked: boolean; names_school_share: boolean
}

type Payload = {
  generated_by: string
  source: string
  ledger: {
    fy: number; period: number; dept: string; dept_name: string; doc_id: string
    department_row: number; department_doc_id: string
    accounts: (Account & { revised: number; transfers: number; encumbered: number; doc_id: string })[]
    total_original: number; total_expended: number
    school_original: number; school_share_of_dept: number
    unnamed_original: number; unnamed_accounts: number
    reconciles_department_row: boolean
  }
  school: {
    active: {
      account_id: string; printed: string; original: number
      expended: number; available: number; doc_id: string
    }
    retiree_account_id: string; retiree_original: number; total_original: number
    retiree_share_of_total: number
    appropriation: number
    appropriation_departments: { dept: string; name: string; original: number }[]
    retiree_share_of_appropriation: number
    health_share_of_appropriation: number
    omnibus: number; omnibus_departments: number
    district_book_agrees: boolean; district_book_settled: number
  }
  district: {
    line_key: string
    settled: Point[]; proposed: Point[]; actual: Point[]
    variants: Variant[]
    change_settled: Change; change_actual: Change
    stages_note: string
  }
  reports: {
    years: ReportYear[]; editions: number; checked: number[]
    not_checked: { fy: number; why: string }[]
    names_school_share: number[]
    school_years: number[]
    years_examined: number[]
    school_retirees_fy2023: number | null
    school_retirees_first_named_fy: number | null
    school_retirees_page: string | null
    school_retirees_source: string | null
    growth_since_named: {
      first_fy: number; last_fy: number; first: number; last: number
      pct: number; cagr: number
    } | null
    split: {
      fy: number; prev_fy: number
      undivided_before: number; undivided_after: number; undivided_pct: number
      total_before: number; total_after: number; total_pct: number
      named_rows: string[]
    } | null
  }
  town_series: TownYear[]
  town_change: Change
  gaps: { side: string; what: string; why: string; closes: string | null }[]
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

export function HealthInsurance() {
  const [d, setD] = useState<Payload | null>(null)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    let live = true
    fetch('/data/health-insurance.json')
      .then(r => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then(j => { if (live) setD(j) })
      .catch(e => { if (live) setErr(String(e)) })
    return () => { live = false }
  }, [])

  if (err) {
    return (
      <div className="mx-auto max-w-6xl px-5 pt-14 pb-16">
        <h1 className="text-3xl font-bold tracking-tight">Health insurance</h1>
        <div className="card p-5 mt-8" style={{ borderLeft: '4px solid var(--status-warning)' }}>
          <p className="text-[15px] font-bold mb-1">The series did not load</p>
          <p className="text-[13.5px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
            {err}. Nothing on this page is typed into it, so with the file missing there is
            nothing to show rather than something stale. The underlying rows are published
            at{' '}
            <a className="underline" style={{ color: 'var(--series-cost)' }}
              href="/data/health-insurance.json">/data/health-insurance.json</a>.
          </p>
        </div>
      </div>
    )
  }

  if (!d) {
    return (
      <div className="mx-auto max-w-6xl px-5 pt-14 pb-16">
        <h1 className="text-3xl font-bold tracking-tight">Health insurance</h1>
        <p className="mt-4 text-[15px]" style={{ color: 'var(--text-muted)' }}>
          Loading the measured series&hellip;
        </p>
      </div>
    )
  }

  const L = d.ledger
  const S = d.school
  const R = d.reports
  const retiree = L.accounts.find(a => a.account_id === S.retiree_account_id)!
  const split = R.split
  const growth = R.growth_since_named
  const settled = d.district.change_settled!
  // The scenario year, derived from the variants themselves rather than named. A year
  // typed into a page outlives the workbook it came from.
  const scenarioFy = d.district.variants.flatMap(v => v.points.map(p => p.fy))
    .sort((a, b) => b - a)[0]
  const lastSettled = d.district.settled[d.district.settled.length - 1]
  const notChecked = R.not_checked
  const gapDoc = d.gaps.find(g => g.side === 'document_wanted')

  return (
    <div className="mx-auto max-w-6xl px-5 pt-14 pb-16">
      <p className="text-xs font-semibold uppercase tracking-widest mb-3"
        style={{ color: 'var(--text-muted)' }}>The money</p>
      <h1 className="text-4xl sm:text-5xl font-bold tracking-tight leading-[1.05] max-w-3xl">
        {usd(retiree.original)} of school health insurance, appropriated to a department
        that is not the schools.
      </h1>
      <p className="mt-5 text-lg leading-relaxed max-w-2xl"
        style={{ color: 'var(--text-secondary)' }}>
        In {fy(L.fy)} the town appropriated {usd(S.appropriation)} to its schools and, in a
        different department of the same budget, {usd(retiree.original)} for the health
        insurance of people who used to work in them. The second figure appears nowhere in
        the district&rsquo;s budget book. Nothing is hidden &mdash; it is where municipal
        accounting puts it &mdash; but it means the schools cost the town{' '}
        {share(S.retiree_share_of_appropriation)} more than their own budget says, before
        anything else is counted.
      </p>

      <div className="mt-10 flex flex-wrap gap-x-12 gap-y-6">
        <Stat value={usd(retiree.original)} tone="var(--series-revenue)">
          school retiree health insurance, {fy(L.fy)} &mdash; account{' '}
          <span className="tnum">{retiree.account_id}</span>, printed{' '}
          <code>{retiree.printed}</code>
        </Stat>
        <Stat value={share(S.retiree_share_of_appropriation)}>
          of the {usd(S.appropriation)} school appropriation, sitting outside it
        </Stat>
        <Stat value={share(L.school_share_of_dept)}>
          of the town&rsquo;s whole {usd(L.total_original)} insurance department is that
          one school line
        </Stat>
        <Stat value={`${R.school_years.length} of ${R.years_examined.length}`}>
          years in which any published document separates the school share at all
        </Stat>
      </div>

      {/* ------------------------------------------------------------ 1. THE CONCLUSIONS */}
      <H2 id="findings">What this page establishes</H2>
      <Body>
        Four claims, each one derived from the town&rsquo;s own documents and each one
        checkable from the table at the bottom of this page.
      </Body>

      <div className="grid gap-4 mt-6"
        style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 20rem), 1fr))' }}>
        <Insight n={1} headline={
          <>The school budget is not what the schools cost, and this is the clearest
            {' '}{usd(retiree.original)} of the difference.</>
        }>
          The district&rsquo;s {fy(L.fy)} appropriation is {usd(S.appropriation)} across{' '}
          {S.appropriation_departments.map(x => x.dept).join(' and ')}. Account{' '}
          <span className="tnum">{retiree.account_id}</span> &mdash;{' '}
          {usd(retiree.original)}, printed <code>{retiree.printed}</code> &mdash; is in
          department {L.dept}, {L.dept_name.toLowerCase()}. Add it and the town&rsquo;s
          school cost rises {share(S.retiree_share_of_appropriation)} without a single
          service changing.
        </Insight>

        <Insight n={2} headline={
          <>Counting both, {share(S.retiree_share_of_total)} of the schools&rsquo; health
            insurance money is for people who have already retired.</>
        }>
          The district budgets {usd(S.active.original)} for active employees&rsquo; health
          insurance inside its own appropriation &mdash; account{' '}
          <span className="tnum">{S.active.account_id}</span>, and the district&rsquo;s
          budget book and the town&rsquo;s ledger{' '}
          {S.district_book_agrees ? 'agree on it to the dollar' : 'do not agree on it'}.
          Together with the retiree account that is {usd(S.total_original)} of school
          health insurance in the {fy(L.fy)} budget, in two departments.
        </Insight>

        {split && (
          <Insight n={3} headline={
            <>The school share is separable in {R.school_years.length} years out of{' '}
              {R.years_examined.length}, and only because the town changed how it prints
              one page.</>
          }>
            Through {fy(split.prev_fy)} the annual report shows a single undivided{' '}
            <em>Health Insurance CH&nbsp;32B</em> line. In {fy(split.fy)} that line falls{' '}
            {pct(split.undivided_pct)} to {usd(split.undivided_after)} while the
            department&rsquo;s own subtotal <em>rises</em> {pct(split.total_pct)} &mdash;
            because {split.named_rows.length} new lines appear beside it,{' '}
            {split.named_rows.join(' and ')}. No other edition names a school share.
          </Insight>
        )}

        {growth && (
          <Insight n={4} headline={
            <>Where it can be measured, school retiree health has grown {pct(growth.pct)}{' '}
              in {growth.last_fy - growth.first_fy} years.</>
          }>
            {usd(growth.first)} appropriated in {fy(growth.first_fy)} against{' '}
            {usd(growth.last)} in {fy(growth.last_fy)} &mdash;{' '}
            {pct(growth.cagr)} a year, appropriation against appropriation. Two
            observations from two different publishers is not a trend line; it is the
            longest run this archive can build, and the reason is on the gaps list below.
          </Insight>
        )}
      </div>

      <NotShown>
        <p>
          None of the four says anything about <em>people</em>. A budget line is dollars:
          the retiree account rising is consistent with more retirees, with the same
          retirees on costlier plans, with a change in the share of the premium the town
          pays, or with any mixture of the three. Nothing published here separates them.
        </p>
        <p className="mt-2.5">
          Nor does the {fy(split ? split.fy : L.fy)} split establish that anything changed
          in the world. A line being printed in three parts instead of one is a change in
          the report, and the earlier years are not thereby known.
        </p>
      </NotShown>

      {/* ------------------------------------------------------- 2. ORGANISED CATEGORIES */}
      <H2 id="where">Where the schools&rsquo; health insurance sits</H2>
      <Body>
        The same year, the same town, the same premiums &mdash; and two departments. The bar
        is drawn to scale: {usd(S.total_original)} of school health insurance in {fy(L.fy)},
        split by which department the money was appropriated to.
      </Body>
      <WhereItSits total={S.total_original} segments={[
        {
          key: 'active', label: 'Active employees', side: 'school',
          amount: S.active.original,
          where: `inside the school appropriation, account ${S.active.account_id}`,
        },
        {
          key: 'retiree', label: 'School retirees', side: 'school',
          amount: retiree.original,
          where: `department ${L.dept}, account ${retiree.account_id}`,
        },
      ]} />
      <TableTwin caption="The two accounts, as the ledger prints them"
        head={['Account', 'Printed', 'Department', 'Appropriated', 'Expended']}
        rows={[
          [S.active.account_id, S.active.printed,
            `${S.appropriation_departments[0].dept} ${S.appropriation_departments[0].name}`,
            usd(S.active.original), usd(S.active.expended)],
          [retiree.account_id, retiree.printed, `${L.dept} ${L.dept_name}`,
            usd(retiree.original), usd(retiree.expended)],
        ]} />

      <H2 id="department">The insurance department, account by account</H2>
      <Body>
        Department {L.dept}, {fy(L.fy)}, period {L.period} &mdash;{' '}
        {L.accounts.length} accounts totalling {usd(L.total_original)}, which is the
        department row the town&rsquo;s other report prints for the same money. Each bar is
        coloured by whose side of the town the account <em>names</em>: one says school, one
        says town, and {L.unnamed_accounts} say neither.
      </Body>
      <ByAccount accounts={L.accounts} total={L.total_original} />
      <TableTwin caption={`Department ${L.dept}, FY${String(L.fy).slice(2)} period ${L.period}`}
        head={['Account', 'Printed', 'What it is', 'Whose side it names', 'Appropriated', 'Expended']}
        rows={L.accounts.map(a => [
          a.account_id, a.printed, a.meaning, SIDE_LABEL[a.side], usd(a.original),
          usd(a.expended),
        ])} />

      <NotShown>
        <p>
          {L.unnamed_accounts} of the {L.accounts.length} accounts &mdash;{' '}
          {usd(L.unnamed_original)}, the larger part of the department &mdash; carry nothing
          in their names that says which side of the town they are for. It would be easy to
          read the unnamed active health insurance line as the town&rsquo;s, since the
          district budgets its own separately, and that reading may well be right. It is a
          reading. The account does not say it, and no document in this archive does either.
        </p>
      </NotShown>

      <H2 id="over-time">The department over sixteen years</H2>
      <Body>
        The appropriation for the whole insurance department, as the town printed it in each
        annual report, and for {fy(L.fy)} from the ledger. Where nothing is drawn, nothing is
        established &mdash; not zero.{' '}
        {d.town_change && (
          <>Across the established years it moves from {usd(d.town_change.first)} in{' '}
            {fy(d.town_change.first_fy)} to {usd(d.town_change.last)} in{' '}
            {fy(d.town_change.last_fy)}, {pct(d.town_change.pct!)} &mdash;{' '}
            {pct(d.town_change.cagr!)} a year.</>
        )}
      </Body>
      <TownOverTime years={d.town_series} missing={notChecked}
        splitFy={R.school_retirees_first_named_fy} />
      <TableTwin caption="Appropriated, by year, with the document each figure came from"
        head={['Year', 'Appropriated', 'From']}
        rows={d.town_series.map(t => [
          fy(t.fy), usd(t.appropriated!),
          t.source === 'ledger' ? `the FY${String(L.fy).slice(2)} ledger, period ${L.period}`
            : `annual town report, page ${t.page}`,
        ])} />

      <NotShown>
        <p>
          Two things break this series and both are on the chart rather than in a footnote.
          The years with no bar are{' '}
          {notChecked.map((m, i) => (
            <span key={m.fy}>
              {i > 0 ? (i === notChecked.length - 1 ? ' and ' : ', ') : ''}
              <strong>{fy(m.fy)}</strong> ({m.why})
            </span>
          ))}. And the composition of the bar is not constant: from{' '}
          {split ? fy(split.fy) : ''} onward the department contains lines it did not
          contain before, so a year-on-year step is partly the town changing what it prints
          under this heading.
        </p>
      </NotShown>

      <Maybe settle={
        <>The town&rsquo;s Chapter&nbsp;32B enrolment schedule &mdash; who is insured, in
          which department, in each year. It is on the list below.</>
      }>
        The obvious reading of {split ? fy(split.fy) : 'the split year'} is that the town
        started tracking school retirees separately because the amount had become worth
        tracking. That fits. So does a change of accounting software, a new auditor&rsquo;s
        recommendation, or the same practice always existing internally and only then
        reaching the printed page. Nothing in this archive distinguishes them, and the
        difference matters: the first reading implies the earlier years were smaller, and
        the third implies they were not.
      </Maybe>

      <H2 id="district">The district&rsquo;s own health-insurance line</H2>
      <Body>
        Inside the school budget, health insurance is a single line, and the district has
        published it every year since {fy(d.district.actual[0].fy)}. Two series are drawn:
        what was <em>budgeted</em>, and what was later <em>reported as actual</em>. They are
        two different documents about the same line and this page never subtracts one from
        the other &mdash; every growth figure here is one stage measured against itself.
      </Body>
      <DistrictLine settled={d.district.settled} actual={d.district.actual} />
      <Body>
        Budget against budget: {usd(settled.first)} settled in {fy(settled.first_fy)} to{' '}
        {usd(settled.last)} in {fy(settled.last_fy)} &mdash; {pct(settled.pct!)},{' '}
        {pct(settled.cagr!)} a year. That is the line growing faster than the levy cap on
        its own, in a budget where it is {share(S.health_share_of_appropriation)} of the
        appropriation.
      </Body>
      <TableTwin caption="The district's Health Insurance line, by stage"
        head={['Year', 'Budgeted (settled)', 'Actual, as later reported']}
        rows={[...new Set([...d.district.settled, ...d.district.actual].map(p => p.fy))]
          .sort((a, b) => a - b)
          .map(f => [
            fy(f),
            d.district.settled.find(p => p.fy === f)
              ? usd(d.district.settled.find(p => p.fy === f)!.value) : '—',
            d.district.actual.find(p => p.fy === f)
              ? usd(d.district.actual.find(p => p.fy === f)!.value) : '—',
          ])} />

      {d.district.variants.length > 0 && scenarioFy && lastSettled && (
        <>
          <H3>Four proposals for one year</H3>
          <Body>
            The {fy(scenarioFy)} workbook prices health insurance{' '}
            {d.district.variants.length} different ways, one for each budget scenario. Every one of them is above {fy(lastSettled.fy)}&rsquo;s
            settled {usd(lastSettled.value)}, which is the useful thing about the spread:
            the cheapest scenario the district drew is still an increase.
          </Body>
          <Scenarios variants={d.district.variants} fy={scenarioFy}
            baseline={lastSettled.value}
            baselineLabel={`FY${String(lastSettled.fy).slice(2)} settled`} />
        </>
      )}

      <NotShown>
        <p>
          Rule 11 applies to this line as much as any other: it is what the town has to
          raise, after everything else that pays for the thing has been subtracted. Staff
          paid from grants and revolving funds are insured too, and if a grant that was
          carrying part of the premium ends, this line rises with no change in headcount and
          no change in the plan. The budget book cannot tell the two apart.
        </p>
      </NotShown>

      {/* --------------------------------------------------------- 3. THE RAW AND CAVEATS */}
      <H2 id="raw">The raw pages, and how each year was checked</H2>
      <Body>
        The town&rsquo;s classification of appropriations is scanned, and every row of it in
        the analysis database is marked <code>check failed</code> &mdash; the column numbers
        there are positions on a page, not named columns. So the figures above were read off
        the pages directly and each year was reconciled against{' '}
        <strong>the identity the table itself prints</strong>: the component rows must sum,
        to the cent, to the <em>Total Insurance</em> the same page shows. A year that does
        not tie is not used, and there are {notChecked.length} of those.
      </Body>
      <TableTwin caption="Every edition, and whether its insurance block reconciles"
        head={['Year', 'Page', 'Rows', 'Components sum to', 'Page prints', 'Difference', 'Status']}
        rows={R.years.map(y => [
          fy(y.fy),
          y.page ?? '—',
          y.rows.length || '—',
          y.summed_components != null ? usd(y.summed_components) : '—',
          y.printed_total != null ? usd(y.printed_total) : '—',
          y.difference != null ? usd(y.difference) : '—',
          y.checked ? 'reconciles' : 'not established',
        ])} />

      {R.school_retirees_first_named_fy && (
        <>
          <H3>The one page that names it</H3>
          <Body>
            {fy(R.school_retirees_first_named_fy)} annual town report, page{' '}
            {R.school_retirees_page}, under <em>GENERAL FUND APPROPRIATIONS &mdash; SUMMARY
            &amp; CLASSIFICATION OF ACCOUNTS</em>. The block as printed:
          </Body>
          <TableTwin
            caption={`FY${String(R.school_retirees_first_named_fy).slice(2)} annual report, page ${R.school_retirees_page}`}
            head={['As printed', 'Whose side it names', 'Appropriated', 'Expended']}
            rows={[
              ...R.years.find(y => y.fy === R.school_retirees_first_named_fy)!.rows.map(r => [
                r.label, SIDE_LABEL[r.side],
                r.appropriated != null ? usd(r.appropriated) : '—',
                r.expended != null ? usd(r.expended) : '—',
              ]),
              ['Total Insurance (as printed)', '',
                usd(R.years.find(y => y.fy === R.school_retirees_first_named_fy)!.printed_total!),
                ''],
            ]} />
          <p className="text-[12.5px] mt-3 max-w-2xl" style={{ color: 'var(--text-muted)' }}>
            Only the appropriated column is published from these pages. It is the one the
            reconciliation establishes; the expended column is printed in two places on
            some editions and four on others, and a column this project has not established
            is not one it quotes.
          </p>
        </>
      )}

      <H2 id="gaps">What cannot be answered, and the document that would</H2>
      <Body>
        Three limits on this page are registered in the project&rsquo;s gap register rather
        than only written here, so that the next person to hit them finds them already
        named. They appear on{' '}
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
              {g.side === 'document_wanted' ? 'A document we do not hold' : 'A conclusion we cannot draw'}
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
            <strong>The {fy(L.fy)} accounts</strong> &mdash; the town&rsquo;s own general
            ledger, period {L.period}, at{' '}
            <a className="underline" style={{ color: 'var(--series-cost)' }}
              href={`/docs/${L.accounts[0].doc_id.replace(/^sources\//, '')}`}>
              {L.accounts[0].doc_id.split('/').pop()}
            </a>. The {L.accounts.length} accounts sum to {usd(L.total_original)} against a
            department row of {usd(L.department_row)} printed in a different MUNIS report
            &mdash; two grains of the same budget, and the build refuses to write if they
            stop agreeing.
          </li>
          <li>
            <strong>The historical department</strong> &mdash; the annual town reports,{' '}
            {R.checked.length} of {R.editions} editions reconciling to their own printed{' '}
            <em>Total Insurance</em>.
          </li>
          <li>
            <strong>The district&rsquo;s line</strong> &mdash; <code>budget_figure</code>,
            line <code>{d.district.line_key}</code>, {d.district.settled.length} settled and{' '}
            {d.district.actual.length} actual years out of the district&rsquo;s own budget
            books.
          </li>
          <li>
            <strong>Everything on this page</strong> is written by{' '}
            <code>{d.generated_by}</code> into{' '}
            <a className="underline" style={{ color: 'var(--series-cost)' }}
              href="/data/health-insurance.json">/data/health-insurance.json</a>, from{' '}
            <code>{d.source}</code>. No figure is typed into the page, and{' '}
            <code>scripts/check_generated.py</code> fails if the file stops reproducing.
          </li>
          {gapDoc && (
            <li>
              <strong>What is missing</strong> &mdash; {gapDoc.what}. {gapDoc.why}
            </li>
          )}
        </ul>
      </div>

      <p className="text-[12.5px] mt-8 max-w-2xl" style={{ color: 'var(--text-muted)' }}>
        The {fy(L.fy)} ledger is period {L.period}, not the year-end close. Expended figures
        here are through that period and will move; appropriations will not.
      </p>
    </div>
  )
}

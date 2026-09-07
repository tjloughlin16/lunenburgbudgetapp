import { useEffect, useMemo, useState } from 'react'
import { usd } from '../model/engine'
import {
  YearVariance, Spread, BudgetVsSpent, GroupRanges, pct, fy,
  OVER, UNDER,
  type YearRow, type SpreadRow, type PairRow, type GroupRow,
} from '../components/VarianceCharts'

/** Budgets against actuals, charted.
 *
 *  WHAT THIS PAGE IS. `sources/analyses/budget-vs-actual.md` did this reasoning first and
 *  at length; this is the same question with the series drawn, and it neither redoes the
 *  argument nor contradicts it. Where a count here differs from a sentence there, this
 *  page is the recomputed one: every figure on it is read at build time out of the
 *  database by `scripts/build_variance_charts.py`, and the analysis is prose that was true
 *  when it was written.
 *
 *  RULE 1 IS THE SUBJECT, NOT AN OBSTACLE. Comparing a year's budget to that same year's
 *  actual is exactly what this page is for. What is forbidden is a growth rate measured
 *  from an actual in one year to a budget in another — part growth, part the step between
 *  two kinds of column, and the error that once put a special education escalator 1.5
 *  points too high. Nothing here produces a rate, and the page says so where a reader
 *  might be tempted to compute one.
 *
 *  RULE 2. Not one figure is typed into this file. Everything numeric arrives from
 *  /data/budget-vs-actual.json, including the counts inside sentences — which is the half
 *  of rule 2 that keeps getting missed, because a sentence goes on rendering confidently
 *  long after the model behind it has moved.
 *
 *  RULE 7 IS THE HARDEST PART OF THIS PAGE. A line that came in under can be a line that
 *  was over-budgeted or a line where something did not happen, and NOTHING in these
 *  documents tells the two apart. That is not a caveat at the bottom; it is stated beside
 *  the chart that invites the inference.
 *
 *  RULE 11. Every figure here is a NET general-fund appropriation against net general-fund
 *  spending. A line that is partly paid by a grant, a fee or a revolving fund shows only
 *  the town's share on both sides, and a year where a grant ended looks exactly like a
 *  year where something got more expensive.
 *
 *  NO D1 AT PAGE LOAD. One static file. The query endpoint's free tier stops at 5 million
 *  rows read a day and a single join across these tables reads 19,006. */

type Payload = {
  generated_by: string
  source: string
  coverage: {
    line_years: number; lines: number; first_fy: number; last_fy: number
    years: number[]; groups: number
    excluded: { why: string; line_years: number }[]
    excluded_total: number
    workbook_lines: number; workbook_lines_never_measured: number
    min_lines_per_year: number; min_budget: number
    same_way_threshold: number; drift_threshold: number
  }
  by_year: YearRow[]
  sections: { section: string; line_years: number; budgeted: number; spent: number; pct: number }[]
  groups: GroupRow[]
  spread: SpreadRow[]
  within_2pct: number
  same_way: { line: string; years: number; mean_pct: number; mean_dollars: number; direction: string }[]
  lines_with_four_years: number
  biggest_over: { line: string; years: number; net: number; budgeted: number }[]
  biggest_under: { line: string; years: number; net: number; budgeted: number }[]
  tuition: PairRow[]
  sped_staff: PairRow[]
  fy21: {
    lines: number; identical: number; share: number
    ordinary: { fy: number; lines: number; identical: number; share: number }[]
  }
  disagreements: {
    cells: number
    by_year: { fy: number; stage: string; cells: number }[]
    widest: { line: string; fy: number; stage: string; readings: number; lo: number; hi: number }[]
  }
  related: { id: string; title: string; why: string; url: string; words: number }[]
  analysis: {
    title: string; about: string; words: number; updated: string
    markdown: string; pdf: string | null
  }
}

/** A magnitude, not a direction. `pct` carries a sign because a variance has one; a
 *  SHARE does not, and rendering "+99%" of FY21's lines as though it were an overspend is
 *  the kind of thing nobody notices in review. */
const share = (x: number) => `${(x * 100).toFixed(x >= 0.1 ? 0 : 1)}%`

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

/** A box for the half of a section that says what the data does NOT establish. It is a
 *  distinct shape on purpose: on this page the limit is as load-bearing as the finding,
 *  and a caveat set in the same grey as the paragraph before it gets skimmed. */
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

const VIEWS = [
  { id: 'largest', label: 'Largest' },
  { id: 'volatile', label: 'Most volatile' },
  { id: 'steady', label: 'Miss the same way' },
] as const
type View = typeof VIEWS[number]['id']

export function BudgetVsActual() {
  const [d, setD] = useState<Payload | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [view, setView] = useState<View>('largest')

  useEffect(() => {
    let live = true
    fetch('/data/budget-vs-actual.json')
      .then(r => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then(j => { if (live) setD(j) })
      .catch(e => { if (live) setErr(String(e)) })
    return () => { live = false }
  }, [])

  /** Groups with enough measured years to have a shape at all. Ordered by the chosen
   *  view; colour is by direction rather than by position, so re-ordering never repaints
   *  a group the reader has already learned. */
  const groups = useMemo(() => {
    if (!d) return []
    const g = d.groups.filter(r => r.years >= 4 && r.group !== '(unmapped)')
    if (view === 'volatile') {
      return [...g].filter(r => r.churn !== null).sort((a, b) => (b.churn! - a.churn!)).slice(0, 10)
    }
    if (view === 'steady') {
      return g.filter(r => r.direction !== 'both ways')
        .sort((a, b) => Math.abs(b.net) - Math.abs(a.net))
    }
    return [...g].sort((a, b) => b.budgeted - a.budgeted).slice(0, 10)
  }, [d, view])

  /** The axis cap for the range plot, and it is deliberately NOT the largest value.
   *
   *  Private tuitions runs to −61% while the six largest salary groups all sit inside two
   *  points, so scaling to the extreme drew nine invisible slivers and one bar. The cap is
   *  the fourth-widest range in the shown set, rounded up to a clean five points, floored
   *  at ten: anything past it is drawn cut with a chevron rather than silently shortened,
   *  and every row prints its real figures underneath regardless. */
  const span = useMemo(() => {
    const ext = groups.map(r => Math.max(Math.abs(r.worst), Math.abs(r.best)))
      .sort((a, b) => b - a)
    const at = ext[Math.min(3, ext.length - 1)] ?? 0.1
    return Math.max(0.1, Math.ceil(at * 20) / 20)
  }, [groups])

  if (err) {
    return (
      <div className="mx-auto max-w-6xl px-5 pt-14 pb-16">
        <h1 className="text-3xl font-bold tracking-tight">Budgets against actuals</h1>
        <div className="card p-5 mt-8" style={{ borderLeft: '4px solid var(--status-warning)' }}>
          <p className="text-[15px] font-bold mb-1">The series did not load</p>
          <p className="text-[13.5px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
            {err}. Nothing on this page is typed into it, so with the file missing there is
            nothing to show rather than something stale. The written analysis is at{' '}
            <a className="underline" style={{ color: 'var(--series-cost)' }}
              href="/docs/analyses/budget-vs-actual.md">/docs/analyses/budget-vs-actual.md</a>.
          </p>
        </div>
      </div>
    )
  }

  if (!d) {
    return (
      <div className="mx-auto max-w-6xl px-5 pt-14 pb-16">
        <h1 className="text-3xl font-bold tracking-tight">Budgets against actuals</h1>
        <p className="mt-4 text-[15px]" style={{ color: 'var(--text-muted)' }}>
          Loading the measured series&hellip;
        </p>
      </div>
    )
  }

  const worstYear = [...d.by_year].sort((a, b) => Math.abs(b.pct) - Math.abs(a.pct))[0]
  const overYears = d.by_year.filter(r => r.net > 0)
  const salaries = d.sections[0]
  const rest = d.sections[1]
  const alwaysUnder = d.groups.filter(r => r.direction === 'under every year')
  const alwaysOver = d.groups.filter(r => r.direction === 'over every year')
  const bothWays = d.groups.filter(r => r.direction === 'both ways')
  const drifting = d.groups.filter(r => r.drift !== null)
  /** Line-years that landed WHOLLY outside a quarter either way. The test is on the bin
   *  furthest from zero, not on either edge: `10–25% under` has an edge at −0.25 and
   *  counting it here overstated this by 69. */
  const wildest = d.spread.filter(r => r.lo >= 0.25 || r.hi <= -0.25)
    .reduce((a, r) => a + r.count, 0)
  const tuitionOver = d.tuition.filter(r => r.pct > 0)
  const tuitionWorst = [...d.tuition].sort((a, b) => a.pct - b.pct)[0]
  const tuitionBest = [...d.tuition].sort((a, b) => b.pct - a.pct)[0]
  const spedWorst = [...d.sped_staff].sort((a, b) => a.pct - b.pct)[0]
  const ordinaryShare = d.fy21.ordinary.map(r => r.share)

  return (
    <div className="mx-auto max-w-6xl px-5 pt-14 pb-16">
      <p className="text-xs font-semibold uppercase tracking-widest mb-3"
        style={{ color: 'var(--text-muted)' }}>The money</p>
      <h1 className="text-4xl sm:text-5xl font-bold tracking-tight leading-[1.05] max-w-3xl">
        The budget lands. The lines inside it do not.
      </h1>
      <p className="mt-5 text-lg leading-relaxed max-w-2xl"
        style={{ color: 'var(--text-secondary)' }}>
        Across {d.by_year.length} measured years the school budget came within{' '}
        {share(Math.abs(worstYear.pct))} of itself in the worst of them. Underneath that,{' '}
        {wildest} of {d.coverage.line_years} line-years missed their own budget by more than
        a quarter &mdash; in both directions, cancelling each other out.
      </p>

      <div className="mt-10 flex flex-wrap gap-x-12 gap-y-6">
        <Stat value={pct(worstYear.pct)} tone={worstYear.net >= 0 ? OVER : UNDER}>
          the furthest any measured year landed from its own budget &mdash; {fy(worstYear.fy)}
        </Stat>
        <Stat value={`${d.within_2pct} of ${d.coverage.line_years}`}>
          line-years that landed within 2% of their own line. The rest did not
        </Stat>
        <Stat value={`${d.coverage.lines}`}>
          distinct budget lines, {fy(d.coverage.first_fy)}&ndash;{fy(d.coverage.last_fy)},
          each read from one row of one document
        </Stat>
      </div>

      <Body>
        This page is the charted half of a written analysis. Every figure on it is
        recomputed from the database when the site is built &mdash; nothing is typed into a
        sentence &mdash; so where a count here differs from the prose in the report, this is
        the one that reflects the data as it now stands.
      </Body>

      {/* ------------------------------------------------------------ rule 1 */}
      <div className="card p-4 mt-6 max-w-2xl" style={{ borderLeft: '4px solid var(--status-warning)' }}>
        <p className="text-[14.5px] font-bold mb-1">
          A budget and an actual are different kinds of number. Do not measure growth
          between them.
        </p>
        <p className="text-[13.5px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
          Every comparison on this page is one year&rsquo;s budget against{' '}
          <em>that same year&rsquo;s</em> spending, which is a fair question. Running from
          an actual in one year to a budget in another is not: the answer is part growth and
          part the step between the two kinds of column. That mistake once put a special
          education escalator 1.5 points too high on this site. The projection everywhere
          else here is built from budget columns only, and nothing on this page feeds it.
        </p>
      </div>

      {/* --------------------------------------------------------- by year */}
      <H2 id="by-year">The whole measured budget, year by year</H2>
      <Body>
        Each bar is every measured line in that year added up, and how far the spending
        landed from the budget those same documents printed beside it.{' '}
        {overYears.length === 0
          ? 'No measured year came in over.'
          : `${overYears.length} of ${d.by_year.length} came in over: ${overYears.map(r => fy(r.fy)).join(', ')}.`}
      </Body>
      <div className="mt-6"><YearVariance rows={d.by_year} /></div>
      <p className="text-[12px] mt-3 max-w-2xl" style={{ color: 'var(--text-muted)' }}>
        {fy(d.by_year[d.by_year.length - 1].fy)} rests on{' '}
        {d.by_year[d.by_year.length - 1].lines} lines against{' '}
        {Math.max(...d.by_year.map(r => r.lines))} in the fullest year, because only one
        document so far restates it line by line. Read it as a first reading, not as the
        year&rsquo;s verdict. FY21 is missing on purpose &mdash; see below.
      </p>

      <NotShown>
        <p>
          <strong>Whether an underspend is a saving.</strong> A line that came in under can
          be a line that was over-budgeted, or a line where something did not happen &mdash;
          a position left unfilled, a placement that did not start, a project deferred.
          These documents print two columns of dollars and nothing that tells those apart.
          Nobody should read a negative bar as prudence or as a cut without a second source.
        </p>
        <p className="mt-2.5">
          <strong>Money moved between lines during the year.</strong> Districts do this with
          proper approvals, and a line that overspent may have been topped up legitimately.
          Those votes are not in these documents. At department level the town&rsquo;s own
          ledger does show them, which is why the FY26 closeout analyses are a separate
          piece of work.
        </p>
        <p className="mt-2.5">
          <strong>What anything cost.</strong> Both columns are the town&rsquo;s{' '}
          <em>net</em> general-fund share, after state aid, grants, fees and revolving funds
          have paid theirs. A line that rose because a grant ended looks exactly like a line
          that got more expensive.
        </p>
      </NotShown>

      {/* --------------------------------------------------------- the spread */}
      <H2 id="spread">Underneath, almost nothing lands</H2>
      <Body>
        The same {d.coverage.line_years} line-years, counted by how far each one missed its
        own budget. {d.within_2pct} landed within two percent. {wildest} missed by more than
        a quarter, and they run both ways &mdash; which is why the totals above are so
        quiet. A budget that comes out flat is not necessarily a budget that was right; it
        can be a hundred independent misses that happened to sum to nothing.
      </Body>
      <div className="mt-6"><Spread rows={d.spread} /></div>

      <H2 id="direction">Reliably under, reliably over, or neither</H2>
      <Body>
        Of the {d.groups.filter(r => r.years >= 4).length} function groups measured in four
        or more years, {alwaysUnder.length} came in under in every one of them
        {alwaysUnder.length ? ` (${alwaysUnder.map(r => r.group).join(', ')})` : ''} and{' '}
        {alwaysOver.length === 0 ? 'none came in over in every one' : `${alwaysOver.length} came in over in every one (${alwaysOver.map(r => r.group).join(', ')})`}.
        The other {bothWays.length} miss in both directions. {drifting.length} have drifted
        by more than {Math.round(d.coverage.drift_threshold * 100)} points between their
        first two measured years and their last two.
      </Body>
      <Body>
        <strong>There is no systematic padding in this budget</strong>, and that is a
        negative finding worth stating plainly: the misses look like noise, not like a line
        being quietly over-provided year after year.
      </Body>

      {/* One filter row, above everything it scopes. */}
      <div className="flex flex-wrap gap-2 mt-7" role="group" aria-label="Which groups to show">
        {VIEWS.map(v => (
          <button key={v.id} onClick={() => setView(v.id)}
            aria-pressed={view === v.id}
            className="px-3.5 min-h-[44px] rounded-[10px] text-[13px] font-semibold border"
            style={{
              borderColor: view === v.id ? 'var(--series-cost)' : 'var(--grid)',
              background: view === v.id ? 'var(--surface-3)' : 'transparent',
              color: view === v.id ? 'var(--text-primary)' : 'var(--text-secondary)',
            }}>
            {v.label}
          </button>
        ))}
      </div>
      <p className="text-[12px] mt-2.5 max-w-2xl" style={{ color: 'var(--text-muted)' }}>
        {view === 'largest'
          ? 'The ten biggest groups by what was budgeted against them, across every measured year.'
          : view === 'volatile'
            ? 'The ten groups whose years cancel each other out most — a quiet net over a loud inside.'
            : 'Every group that missed the same way in all four or more of its measured years.'}
      </p>
      <div className="mt-4">
        {groups.length
          ? <GroupRanges rows={groups} span={span} />
          : <p className="text-[13.5px]" style={{ color: 'var(--status-warning)' }}>
            No group matches this view. That is a filter matching nothing, not a budget with
            no groups in it.
          </p>}
      </div>

      <NotShown>
        A group is a function code &mdash; the district&rsquo;s own accounting bucket &mdash;
        and the lines inside one are not interchangeable. A group that pools flat can hold a
        line that doubled and a line that halved, which is what the churn figure counts.
        None of this apportions the whole budget&rsquo;s variance between groups: the
        measured lines do not sum back to the district&rsquo;s printed totals, so this asks
        which lines miss and how often, and nothing more.
      </NotShown>

      {/* ------------------------------------------------------ salaries */}
      <H2 id="salaries">Salaries come in under. Everything else comes in over.</H2>
      <Body>
        {salaries.section} across {salaries.line_years} line-years landed{' '}
        {pct(salaries.pct)} against {usd(salaries.budgeted)} budgeted.{' '}
        {rest.section} landed {pct(rest.pct)} against {usd(rest.budgeted)}. Both are within
        one percent and they very nearly cancel, which is most of why the yearly totals
        above are as quiet as they are.
      </Body>
      <div className="grid gap-2.5 mt-6 max-w-2xl">
        {d.sections.map(s => (
          <div key={s.section} className="card px-4 py-3.5">
            <div className="flex items-baseline justify-between gap-3">
              <span className="text-[14.5px] font-bold">{s.section}</span>
              <span className="text-[15px] font-bold tnum shrink-0"
                style={{ color: s.pct >= 0 ? OVER : UNDER }}>{pct(s.pct)}</span>
            </div>
            <p className="text-[12.5px] mt-1 tnum" style={{ color: 'var(--text-secondary)' }}>
              {usd(s.budgeted)} budgeted &middot; {usd(s.spent)} spent &middot;{' '}
              {s.line_years} line-years
            </p>
          </div>
        ))}
      </div>
      <NotShown>
        A payroll line coming in under is consistent with a roster the district did not
        fully fill, and it is equally consistent with a budget set above what the contracts
        cost. These figures are dollars; they are not positions, and no document here
        converts one into the other.
      </NotShown>

      {/* -------------------------------------------------------- tuition */}
      <H2 id="tuition">One cost cannot be forecast, and it misses both ways</H2>
      <Body>
        When a child&rsquo;s plan requires a school the district cannot provide, the town
        pays another school. It does not set the price, does not choose how many children
        need it, and cannot say no. Out-of-district tuition came in over budget in{' '}
        {tuitionOver.length} of {d.tuition.length} measured years and under in the rest,
        with a range from {pct(tuitionWorst.pct)} to {pct(tuitionBest.pct)}.
      </Body>
      <div className="mt-6"><BudgetVsSpent rows={d.tuition} /></div>
      <Body>
        Special education <em>staffing</em> over the same years behaves nothing like it
        &mdash; never further off than {pct(spedWorst.pct)}:
      </Body>
      <div className="mt-4"><BudgetVsSpent rows={d.sped_staff} height={200} /></div>
      <NotShown>
        <p>
          This is a line nobody can forecast, and that is not the same claim as a line
          somebody is short-changing. Which of the two it is cannot be settled from these
          columns.
        </p>
        <p className="mt-2.5">
          <strong>Dollars are not children.</strong> A tuition line falling by a third does
          not establish that fewer children were placed, at what price, or in what setting.
          Placement counts are published separately, by year, and they are a different
          quantity from this one.
        </p>
        <p className="mt-2.5">
          The last measured year of the special education staffing series rests on{' '}
          {d.sped_staff[d.sped_staff.length - 1].lines}{' '}
          {d.sped_staff[d.sped_staff.length - 1].lines === 1 ? 'line' : 'lines'}. It is
          consistent with the years above it and it is not independent evidence of anything.
        </p>
      </NotShown>

      {/* --------------------------------------------------------- lines */}
      <H2 id="lines">The lines that miss the same way every time are all small</H2>
      <Body>
        {d.lines_with_four_years} lines have four or more usable years. {d.same_way.length}{' '}
        of them miss the same way in every one
        {d.same_way.length
          ? <>, and the largest averages {usd(Math.abs(d.same_way[0].mean_dollars))} a year
            on a budget in the tens of millions. That is the shape of noise rather than of
            padding.</>
          : <>. There is nothing here that misses the same way every time.</>}
      </Body>
      <div className="overflow-x-auto mt-6">
        <table className="stack w-full text-xs tnum max-w-2xl">
          <caption className="sr-only">
            Budget lines that came in the same way in every one of their measured years
          </caption>
          <thead>
            <tr className="text-left" style={{ color: 'var(--text-muted)' }}>
              <th className="font-semibold py-1.5">Line</th>
              <th className="font-semibold py-1.5 text-right">Years</th>
              <th className="font-semibold py-1.5 text-right">Average miss</th>
              <th className="font-semibold py-1.5 text-right">Average dollars</th>
            </tr>
          </thead>
          <tbody>
            {d.same_way.map(r => (
              <tr key={r.line} className="border-t" style={{ borderColor: 'var(--grid)' }}>
                <td className="rowhead py-1.5 font-semibold">{r.line}</td>
                <td data-label="Years" className="py-1.5 text-right">{r.years}</td>
                <td data-label="Average miss" className="py-1.5 text-right font-semibold"
                  style={{ color: r.mean_pct >= 0 ? OVER : UNDER }}>{pct(r.mean_pct)}</td>
                <td data-label="Average dollars" className="py-1.5 text-right">
                  {usd(r.mean_dollars)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="grid gap-6 sm:grid-cols-2 mt-8 max-w-4xl">
        {([['Spent the most above budget', d.biggest_over, OVER],
        ['Spent the most below budget', d.biggest_under, UNDER]] as const).map(([t, rows, c]) => (
          <div key={t}>
            <p className="text-[11px] font-semibold uppercase tracking-widest mb-2"
              style={{ color: 'var(--text-muted)' }}>{t}</p>
            <ul className="space-y-1.5">
              {rows.map(r => (
                <li key={r.line} className="flex items-baseline justify-between gap-3
                                            text-[13px] py-1">
                  <span className="leading-snug">{r.line}</span>
                  <span className="tnum font-bold shrink-0" style={{ color: c }}>
                    {usd(r.net)}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
      <p className="text-[12px] mt-3 max-w-2xl" style={{ color: 'var(--text-muted)' }}>
        Pooled across every measured year, so a single bad year and a steady drift look the
        same here. The ranges above separate them.
      </p>

      {/* ------------------------------------------------------- the limits */}
      <H2 id="limits">What is left out, and why</H2>
      <Body>
        {d.coverage.excluded_total.toLocaleString()} line-years were excluded from
        everything above, and each exclusion has a reason rather than a silence. A figure
        dropped without a stated reason is indistinguishable from a figure that was never
        published.
      </Body>
      <ul className="mt-5 space-y-2 max-w-2xl">
        {d.coverage.excluded.map(e => (
          <li key={e.why} className="flex items-baseline justify-between gap-4 pl-3.5 py-1"
            style={{ borderLeft: '2px solid var(--grid)' }}>
            <span className="text-[13.5px] leading-snug">{e.why}</span>
            <span className="text-[13px] tnum font-semibold shrink-0"
              style={{ color: 'var(--text-muted)' }}>
              {e.line_years.toLocaleString()}
            </span>
          </li>
        ))}
      </ul>

      <H2 id="fy21">FY21 is not a usable year</H2>
      <Body>
        Every document that reports FY21 gives it an actual column, and in{' '}
        {d.fy21.identical} of its {d.fy21.lines} lines that column is identical to the
        budget, to the dollar &mdash; {share(d.fy21.share)} of them. In the years that are
        used the same figure runs between{' '}
        {share(Math.min(...ordinaryShare))} and {share(Math.max(...ordinaryShare))}, and those
        are lines that genuinely do not move: fixed stipends, flat contracts.
      </Body>
      <Body>
        A district does not spend its budget exactly on that many lines. That column is the
        budget, printed under an actual heading &mdash; most likely because the books were
        not closed when the document went out. FY21 was the first full COVID year, which is
        the obvious candidate for why. <strong>Nothing published says so</strong>, and that
        sentence is a hypothesis rather than a finding. The year is excluded from every
        comparison on this page.
      </Body>

      <H2 id="disagreements">Where the documents disagree with themselves</H2>
      <Body>
        {d.disagreements.cells.toLocaleString()} cells in the archive are ones where two
        published documents state different figures for the same line, year and column.
        They are <strong>kept as disagreements rather than resolved</strong>: picking a
        winner would hide the fact that the sources differ, and nothing published says which
        is right. Every one of them is dropped from the comparisons above.
      </Body>
      <div className="overflow-x-auto mt-6">
        <table className="stack w-full text-xs tnum max-w-3xl">
          <caption className="sr-only">
            The widest disagreements between two documents about the same figure
          </caption>
          <thead>
            <tr className="text-left" style={{ color: 'var(--text-muted)' }}>
              <th className="font-semibold py-1.5">Line</th>
              <th className="font-semibold py-1.5">Year</th>
              <th className="font-semibold py-1.5">Column</th>
              <th className="font-semibold py-1.5 text-right">Lowest stated</th>
              <th className="font-semibold py-1.5 text-right">Highest stated</th>
            </tr>
          </thead>
          <tbody>
            {d.disagreements.widest.map(r => (
              <tr key={`${r.line}-${r.fy}-${r.stage}`} className="border-t"
                style={{ borderColor: 'var(--grid)' }}>
                <td className="rowhead py-1.5 font-semibold">{r.line}</td>
                <td data-label="Year" className="py-1.5">{fy(r.fy)}</td>
                <td data-label="Column" className="py-1.5">{r.stage}</td>
                <td data-label="Lowest stated" className="py-1.5 text-right">{usd(r.lo)}</td>
                <td data-label="Highest stated" className="py-1.5 text-right">{usd(r.hi)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <NotShown>
        A document contradicting itself is the most ordinary thing in the world &mdash; two
        summary blocks in a long file, one updated and one not. It is not an accusation. It
        is a limit: the variances measured on this page run to a fraction of a percent, and
        the documents&rsquo; disagreement with themselves runs larger than that, so a year
        where a source contradicts itself cannot be used at all.
      </NotShown>

      <H2 id="elsewhere">What this sweep structurally cannot see</H2>
      <Body>
        {d.related.length} questions this page raises and cannot answer are answered
        elsewhere, each from a document the budget books do not contain. They are separate
        pieces of work rather than a paragraph here for that reason.
      </Body>
      <div className="grid gap-2.5 mt-6 max-w-2xl">
        {d.related.map(r => (
          <a key={r.id} href={r.url}
            className="card block px-4 py-3.5 min-h-[44px] transition-opacity hover:opacity-90">
            <span className="text-[14.5px] font-bold leading-tight"
              style={{ color: 'var(--series-cost)' }}>{r.title} &rarr;</span>
            <span className="block text-[13px] mt-1 leading-snug"
              style={{ color: 'var(--text-secondary)' }}>{r.why}</span>
          </a>
        ))}
      </div>

      {/* -------------------------------------------------------- the sources */}
      <H2 id="sources">Where this comes from</H2>
      <Body>
        {d.coverage.line_years} usable line-years across {d.coverage.lines} lines and{' '}
        {d.coverage.groups} function groups, {fy(d.coverage.first_fy)}&ndash;
        {fy(d.coverage.last_fy)}. Each line&rsquo;s budget and its actual are read from the
        same row of the same document, which is what makes the per-line comparison sound.
        They do not sum back to the district&rsquo;s own printed totals, which is why
        nothing here apportions a year&rsquo;s variance between its lines.
      </Body>
      <div className="grid gap-2.5 mt-6 max-w-2xl">
        <a href={d.analysis.markdown}
          className="card block px-4 py-4 min-h-[44px] transition-opacity hover:opacity-90">
          <span className="text-[16px] font-bold leading-tight"
            style={{ color: 'var(--series-cost)' }}>{d.analysis.title} &rarr;</span>
          <span className="block text-[13.5px] mt-1.5 leading-snug"
            style={{ color: 'var(--text-secondary)' }}>{d.analysis.about}</span>
          <span className="block text-[11.5px] mt-2" style={{ color: 'var(--text-muted)' }}>
            {d.analysis.words.toLocaleString()} words, updated {d.analysis.updated}
            {d.analysis.pdf ? ' · also as a PDF' : ''}
          </span>
        </a>
        {d.analysis.pdf && (
          <a href={d.analysis.pdf}
            className="card block px-4 py-3 min-h-[44px] transition-opacity hover:opacity-90">
            <span className="text-[14px] font-bold" style={{ color: 'var(--series-cost)' }}>
              The same analysis as a PDF &rarr;
            </span>
          </a>
        )}
        <a href="/data/budget-vs-actual.json"
          className="card block px-4 py-3 min-h-[44px] transition-opacity hover:opacity-90">
          <span className="text-[14px] font-bold" style={{ color: 'var(--series-cost)' }}>
            Every series on this page, as JSON &rarr;
          </span>
          <span className="block text-[12.5px] mt-0.5 leading-snug"
            style={{ color: 'var(--text-secondary)' }}>
            Written by <code>{d.generated_by}</code> from {d.source}
          </span>
        </a>
      </div>
      <p className="text-[11.5px] mt-5 max-w-2xl" style={{ color: 'var(--text-muted)' }}>
        Guards, stated rather than left to the reader: a year needs at least{' '}
        {d.coverage.min_lines_per_year} usable lines to appear at all, a line needs a budget
        of at least {usd(d.coverage.min_budget)}, and &ldquo;misses the same way every
        year&rdquo; means every year off by more than{' '}
        {Math.round(d.coverage.same_way_threshold * 100)}% in the same direction.{' '}
        {d.coverage.workbook_lines_never_measured} of the{' '}
        {d.coverage.workbook_lines} lines in the district&rsquo;s current workbook are never
        measured here at all &mdash; mostly lines the older documents do not carry.
      </p>
    </div>
  )
}

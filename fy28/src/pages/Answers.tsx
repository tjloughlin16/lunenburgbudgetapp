import type { ReactNode } from 'react'
import { MODEL, usd, usdShort } from '../model/engine'
import {
  GAPS, GAP, COST_GROWTH, REVENUE_CAP, RATE_GAP, yearsCovered, shortfallAfter,
  EXTRACURRICULAR, ADMIN, LEADERSHIP, PAYROLL, HEALTH, DEVELOPMENT, BILL, CONTRACT, SETTLEMENT, scaleAfterCut,
  RELIEF, BENT_HEALTH, OPTIONS,
} from '../model/answers'
import { Section, Note } from '../components/primitives'

const T = MODEL.taxBase
const pct = (x: number, d = 0) => `${(x * 100).toFixed(d)}%`

/** The same facts as the rest of the tool, written for somebody who has never opened a
 *  budget document.
 *
 *  Every other tab answers a question a person asks after they already understand the
 *  problem: which cuts, in what order, at what fee. This one answers the questions people
 *  ask before that — will it happen again, will cutting sports fix it, what would the
 *  administrators have to give up — and it answers them with a number and the arithmetic
 *  that produced it, in the fewest words that stay true.
 *
 *  The rule for this page: no sentence that needs a glossary, and no figure without its
 *  denominator visible. Where the honest answer is "we cannot know that from published
 *  documents", it says so rather than reaching for a plausible number. */
export function Answers({ onJump }: { onJump: (tab: 'why' | 'development' | 'adjust') => void }) {
  return (
    <div>
      <div className="mx-auto max-w-6xl px-5 pt-12 pb-2">
        <p className="text-xs font-semibold uppercase tracking-widest mb-3"
          style={{ color: 'var(--text-muted)' }}>Plain English</p>
        <h1 className="text-3xl sm:text-4xl font-bold tracking-tight leading-[1.1] max-w-3xl">
          Straight answers
        </h1>
        <p className="mt-4 text-[15px] leading-relaxed max-w-2xl"
          style={{ color: 'var(--text-secondary)' }}>
          Nine questions people in Lunenburg actually ask about the school budget, each
          answered with a number and the arithmetic that produced it. No jargon, no
          adjectives, and nothing you have to take on trust &mdash; the sums are small
          enough to check.
        </p>
        <Note>
          Every figure comes from the town&rsquo;s published FY27 budget and tax records,
          run through the same model as the rest of this site. FY28 and later are
          projections, not published numbers.
        </Note>
      </div>

      <Section id="scoreboard" eyebrow="Every idea, side by side"
        title="Every idea on one page"
        lede={<>Next year the schools need <strong>{usd(GAP)}</strong> more than the town
          can give them. Here is every answer anyone has proposed, priced the same way:
          what it saves, whether that closes next year, and how long it lasts before the
          question comes back. <strong>Nothing on this list lasts more than one year on its
          own.</strong> Each row links to the arithmetic behind it.</>}>
        <Scoreboard />
        <Note>
          &ldquo;Years it lasts&rdquo; assumes the saving is permanent and grows a little
          each year, because a job you never fill never gets its raise. The gap grows
          faster, from a much larger base &mdash; which is the reason the column reads the
          way it does, and the subject of the rest of this page.
        </Note>
      </Section>

      <Section id="short" eyebrow="Why any of this is necessary"
        title="The whole thing in four sentences">
        <FourSentences />
      </Section>

      <Section id="repeat" eyebrow="The pattern"
        title="What the hole looks like for the next six years"
        lede={<>Two numbers get called &ldquo;the gap&rdquo; and they are not the same.
          The right-hand column is the part that is <strong>new</strong> that year. The
          left-hand column is the running total &mdash; how much more the schools need than
          today&rsquo;s revenue provides, with every earlier year included.</>}>
        <GapTable />
      </Section>

      <Section id="questions" eyebrow="The questions" title="Answers, one at a time">
        <div className="space-y-4">
          <Q1 /><Q2 /><Q3 /><Q4 /><Q5 /><Q6 /><Q7 /><Q8 /><Q9 />
        </div>
      </Section>

      <Section id="works" eyebrow="The honest ending"
        title="The only two things that actually fix it"
        lede={<>Everything above buys time. Two things change the arithmetic itself, and
          both are slow.</>}>
        <WhatWorks onJump={onJump} />
      </Section>
    </div>
  )
}

/* ------------------------------------------------------------------ */
/* building blocks                                                     */

function Verdict({ word, tone }: { word: string; tone: 'no' | 'partly' | 'yes' }) {
  const map = {
    no: { glyph: '✕', color: 'var(--status-critical)' },
    partly: { glyph: '◐', color: 'var(--status-warning)' },
    yes: { glyph: '✓', color: 'var(--status-good)' },
  }[tone]
  return (
    <span className="inline-flex items-center gap-1.5 text-[12px] font-bold whitespace-nowrap
                     px-2 py-1 rounded-md"
      style={{ color: map.color, background: 'color-mix(in srgb, currentColor 12%, transparent)' }}>
      <span aria-hidden="true">{map.glyph}</span>{word}
    </span>
  )
}

/** One question, its verdict, the arithmetic, and what happens the year after.
 *  The shape is identical every time so a reader learns to read one and has read all nine. */
function QA({ n, q, verdict, tone, answer, children, next }: {
  n: number; q: string; verdict: string; tone: 'no' | 'partly' | 'yes'
  answer: ReactNode; children: ReactNode; next: ReactNode
}) {
  return (
    <article id={`q${n}`} className="card p-5 sm:p-6 scroll-mt-20">
      <div className="flex items-start justify-between gap-4 mb-3">
        <div className="flex items-baseline gap-3">
          <span className="text-[11px] font-bold tnum tracking-widest shrink-0"
            style={{ color: 'var(--text-muted)' }}>{String(n).padStart(2, '0')}</span>
          <h3 className="text-[17px] sm:text-xl font-bold leading-snug">{q}</h3>
        </div>
        <Verdict word={verdict} tone={tone} />
      </div>
      <p className="text-[15px] leading-relaxed mb-4 sm:ml-8"
        style={{ color: 'var(--text-primary)' }}>{answer}</p>
      <div className="sm:ml-8">{children}</div>
      <p className="text-[13px] leading-relaxed mt-4 sm:ml-8 pt-3 border-t"
        style={{ borderColor: 'var(--grid)', color: 'var(--text-secondary)' }}>
        <strong style={{ color: 'var(--text-primary)' }}>And the year after: </strong>{next}
      </p>
    </article>
  )
}

/** A named list of what a cut actually removes.
 *
 *  Aggregates make cuts sound easy, and "cut the extra administrators" is the clearest
 *  example in the whole budget: $736,468 reads as a rounding error until it is written
 *  out as ten people with jobs. So this goes in the body of the answer, at full size,
 *  not in a footnote under it. */
function Roster({ title, sub, rows, tone, muted }: {
  title: string; sub: string; tone: string; muted?: boolean
  rows: { id: string; label: string; sub: string; amount: number; fte: number }[]
}) {
  return (
    <div className="card p-4" style={muted ? { background: 'var(--surface-2)' } : undefined}>
      <p className="text-[13px] font-bold leading-snug" style={{ color: tone }}>{title}</p>
      <p className="text-[11px] mb-3" style={{ color: 'var(--text-muted)' }}>{sub}</p>
      <ul className="space-y-2">
        {rows.map(r => (
          <li key={r.id} className="flex items-baseline justify-between gap-3 border-t pt-2"
            style={{ borderColor: 'var(--grid)' }}>
            <span className="min-w-0">
              <span className="block text-[13px] font-medium leading-snug">{r.label}</span>
              {r.sub && (
                <span className="block text-[11px] leading-snug mt-0.5"
                  style={{ color: 'var(--text-muted)' }}>{r.sub}</span>
              )}
            </span>
            <span className="text-[13px] font-semibold tnum shrink-0">{usd(r.amount)}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}

interface LedgerRow { k: ReactNode; v: string; rule?: boolean; strong?: boolean; tone?: string }

/** The sum, shown. Nothing on this page states a figure it does not also add up. */
function Ledger({ rows }: { rows: LedgerRow[] }) {
  return (
    <dl className="text-[13px]" style={{ background: 'var(--surface-3)', borderRadius: 10 }}>
      {rows.map((r, i) => (
        <div key={i}
          className={`flex items-baseline justify-between gap-4 px-4 py-2 ${r.rule ? 'border-t' : ''}`}
          style={{ borderColor: 'var(--axis)' }}>
          <dt className={r.strong ? 'font-bold' : ''}
            style={{ color: r.strong ? 'var(--text-primary)' : 'var(--text-secondary)' }}>
            {r.k}
          </dt>
          <dd className={`tnum shrink-0 ${r.strong ? 'font-bold text-[15px]' : 'font-semibold'}`}
            style={{ color: r.tone ?? 'var(--text-primary)' }}>{r.v}</dd>
        </div>
      ))}
    </dl>
  )
}

/* ------------------------------------------------------------------ */
/* the opening                                                         */

function FourSentences() {
  const items = [
    { fig: usdShort(GAP), body: <>The schools need <strong>{usd(GAP)} more</strong> next year
      than the town can give them. That is the whole problem, in one number.</> },
    { fig: `${pct(RATE_GAP, 2)}`, body: <>The things schools buy get{' '}
      <strong>{pct(COST_GROWTH, 2)}</strong> more expensive each year. State law lets the
      town collect about <strong>{pct(REVENUE_CAP, 1)}</strong> more each year. Nobody
      overspent &mdash; the two numbers are simply different.</> },
    { fig: usdShort(GAPS[1].fresh), body: <>That difference opens a <strong>brand new
      hole every year</strong>, of roughly {usd(GAPS[1].fresh)} to {usd(GAPS[5].fresh)},
      whether or not you closed the last one.</> },
    { fig: '1 yr', body: <>So no single cut fixes this. Every cut on the table &mdash;
      sports, administrators, pay, insurance &mdash; buys <strong>one year</strong> at
      most, and then the question comes back larger.</> },
  ]
  return (
    <ol className="grid gap-3 sm:grid-cols-2">
      {items.map((it, i) => (
        <li key={i} className="card p-5 flex gap-4">
          <span className="text-xl font-bold tnum shrink-0 w-20 leading-snug"
            style={{ color: 'var(--status-critical)' }}>{it.fig}</span>
          <p className="text-[14px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
            {it.body}
          </p>
        </li>
      ))}
    </ol>
  )
}

function GapTable() {
  const max = Math.max(...GAPS.map(g => g.cumulative))
  return (
    <div>
      <div className="card overflow-hidden">
        <table className="w-full text-[13px]">
          <thead>
            <tr style={{ background: 'var(--surface-3)' }}>
              <th className="text-left px-4 py-2.5 font-semibold">Year</th>
              <th className="text-right px-4 py-2.5 font-semibold">
                Running total needed
              </th>
              <th className="text-right px-4 py-2.5 font-semibold">
                New that year
              </th>
              <th className="px-4 py-2.5 w-1/3" />
            </tr>
          </thead>
          <tbody>
            {GAPS.map(g => (
              <tr key={g.fy} className="border-t" style={{ borderColor: 'var(--grid)' }}>
                <td className="px-4 py-2.5 font-semibold">FY{g.fy}</td>
                <td className="px-4 py-2.5 text-right tnum font-bold"
                  style={{ color: 'var(--status-critical)' }}>{usd(g.cumulative)}</td>
                <td className="px-4 py-2.5 text-right tnum"
                  style={{ color: 'var(--text-secondary)' }}>+{usd(g.fresh)}</td>
                <td className="px-4 py-2.5">
                  <span className="block h-3 rounded-sm"
                    style={{ width: `${(g.cumulative / max) * 100}%`,
                             background: 'var(--series-cost)' }} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <Note>
        Read it this way: if the town found {usd(GAPS[0].cumulative)} of permanent new
        money for FY{GAPS[0].fy} and never had to find another dollar, it would still be{' '}
        {usd(GAPS[1].fresh)} short in FY{GAPS[1].fy}. The running total is not a debt that
        accumulates in a bank account &mdash; it is how far today&rsquo;s revenue line has
        fallen behind by that year.
      </Note>
    </div>
  )
}

/* ------------------------------------------------------------------ */
/* the nine                                                            */

function Q1() {
  return (
    <QA n={1} q="Why is there a hole every single year?"
      verdict="Two rates" tone="partly"
      answer={<>Because the town&rsquo;s income and the schools&rsquo; costs grow at
        different speeds, and they have for a long time. Nothing was mismanaged. These are
        just two numbers that were never going to meet.</>}
      next={<>Neither number changes because you closed last year&rsquo;s hole. So the same
        gap between them opens a new one, and it is slightly bigger because both sides are
        bigger.</>}>
      <Ledger rows={[
        { k: 'What schools buy costs more each year', v: pct(COST_GROWTH, 2) },
        { k: 'What the town is allowed to collect grows', v: pct(REVENUE_CAP, 1) },
        { k: 'Short, on every dollar, every year', v: `${(RATE_GAP * 100).toFixed(2)} cents`,
          rule: true, strong: true, tone: 'var(--status-critical)' },
      ]} />
      <Note>
        Health insurance rises {pct(MODEL.assumptions.health)} a year, out-of-district
        special education {pct(MODEL.assumptions.sped_tuition)}, buses{' '}
        {pct(MODEL.assumptions.transport)}, salaries {pct(MODEL.assumptions.salaries)}.
        The only thing on the list that grows slower than the town&rsquo;s income is
        &ldquo;everything else&rdquo; at {pct(MODEL.assumptions.other)}, and it is the
        smallest piece of the budget.
      </Note>
    </QA>
  )
}

function Q2() {
  return (
    <QA n={2} q="Will this happen again next year? And the year after?"
      verdict="Yes, bigger" tone="no"
      answer={<>Yes, both years, and every year after that. A new hole of roughly{' '}
        {usd(GAPS[1].fresh)} to {usd(GAPS[5].fresh)} opens each year on top of whatever
        was already fixed.</>}
      next={<>By FY{GAPS[4].fy} the schools need {usd(GAPS[4].cumulative)} a year more than
        today&rsquo;s revenue provides &mdash; more than five times next year&rsquo;s
        number. This is the single most important fact on the page.</>}>
      <Ledger rows={[
        ...GAPS.slice(0, 4).map(g => ({
          k: `New hole opening in FY${g.fy}`, v: usd(g.fresh) })),
        { k: `Total needed by FY${GAPS[3].fy}, over today's revenue`,
          v: usd(GAPS[3].cumulative), rule: true, strong: true,
          tone: 'var(--status-critical)' },
      ]} />
    </QA>
  )
}

function Q3() {
  const short = GAP - EXTRACURRICULAR.total
  return (
    <QA n={3} q="Will cutting sports, clubs, band and art close it?"
      verdict="No" tone="no"
      answer={<>No &mdash; not even for one year. Cutting <em>every</em> sport, every club,
        the whole high school band and chorus, and all art and music supplies saves{' '}
        {usd(EXTRACURRICULAR.total)}. Next year&rsquo;s hole is {usd(GAP)}. You would still
        be <strong>{usd(short)} short</strong>, with nothing left to cut.</>}
      next={<>Worse. FY{GAPS[1].fy} needs {usd(GAPS[1].cumulative)}, and the extracurriculars
        are already gone &mdash; you cannot cut them twice. Everything after this comes out
        of classrooms.</>}>
      <Ledger rows={[
        ...EXTRACURRICULAR.items.map(i => ({ k: i.label, v: usd(i.amount) })),
        { k: 'Everything, cut', v: usd(EXTRACURRICULAR.total), rule: true, strong: true },
        { k: `Next year's hole`, v: usd(GAP) },
        { k: 'Still short', v: usd(short), rule: true, strong: true,
          tone: 'var(--status-critical)' },
      ]} />
      <Note>
        Athletics as a whole costs {usd(EXTRACURRICULAR.wholeProgram)}, but the adopted
        FY27 budget already cut {usd(EXTRACURRICULAR.alreadyCut)} of it &mdash; the buses,
        half the trainer, the middle school and freshman teams, and part of the coaching
        stipends. Only what the town is still paying for can be saved. The district also
        does not publish whether these figures are before or after the fees families
        already pay, which would make the saving smaller, not larger.
      </Note>
    </QA>
  )
}

function Q4() {
  const left = ADMIN.lawful - GAP
  const after = shortfallAfter(ADMIN.lawful, MODEL.assumptions.salaries)
  return (
    <QA n={4} q="Will cutting the “extra” administrators close it?"
      verdict="One year" tone="partly"
      answer={<>For next year, yes &mdash; but only if &ldquo;extra&rdquo; means{' '}
        <em>every single administrator and school secretary the law allows the town to
        remove</em>, all at once. That is {usd(ADMIN.lawful)} across{' '}
        {ADMIN.lawfulCount} budget lines and {ADMIN.lawfulFte} jobs, and it closes FY
        {GAPS[0].fy} with {usd(left)} to spare. There is no smaller version of this that
        works.</>}
      next={<>It runs out immediately. FY{after.fy} needs {usd(GAPS[1].cumulative)} and this
        saving is worth about {usd(Math.round(ADMIN.lawful * 1.04))} by then &mdash;{' '}
        {usd(after.short)} short, with no administration left to cut.</>}>
      <p className="text-[14px] leading-relaxed mb-4">
        <strong>Here is the actual list.</strong> Not &ldquo;trim the administration&rdquo;
        &mdash; these ten named jobs and four budget lines, all of them, in one year.
      </p>

      <div className="grid gap-3 lg:grid-cols-2 items-start mb-4">
        <Roster title={`The ${ADMIN.people.length} jobs it removes`}
          sub={`${ADMIN.lawfulFte} full-time positions`}
          rows={ADMIN.people} tone="var(--status-critical)" />
        <div className="space-y-3">
          <Roster title={`The ${ADMIN.lines.length} lines that are not people`}
            sub="Paper, not staff — the cut everyone assumes is the whole answer"
            rows={ADMIN.lines} tone="var(--text-secondary)" />
          <Roster title="What it cannot touch, because the state requires it"
            sub={`${usd(ADMIN.protectedTotal)} that stays no matter what`}
            rows={ADMIN.protectedRoles} tone="var(--status-warning)" muted />
        </div>
      </div>

      <p className="text-[14px] leading-relaxed mb-4">
        Read together: that is <strong>every secretary and every clerk in all four
        schools</strong>, plus the district&rsquo;s only human resources person, its only
        payroll clerk, its only special education clerk, and its curriculum director. There
        is no second one of any of them, and the work does not leave with the post &mdash;
        IEP deadlines, payroll and state reporting are legal obligations with penalties
        attached. They land on teachers and principals instead.
      </p>

      <Ledger rows={[
        { k: 'Everything the district spends on administration',
          v: usd(ADMIN.total) },
        { k: 'As a share of the school budget', v: pct(ADMIN.shareOfBudget, 1) },
        { k: 'Of that, what the law lets the town remove', v: usd(ADMIN.lawful), rule: true,
          strong: true },
        { k: `Next year's hole`, v: usd(GAP) },
        { k: 'Left over', v: usd(left), rule: true, strong: true,
          tone: 'var(--status-good)' },
      ]} />
      <Note>
        If you take only the four paper lines and leave every job alone, that is{' '}
        {usd(ADMIN.paperOnly)} &mdash; about {pct(ADMIN.paperOnly / GAP)} of the hole. For
        scale on the whole question: {ADMIN.benchmark}.
      </Note>
    </QA>
  )
}

function Q5() {
  const c = LEADERSHIP.cutFor
  const over = c.find(x => x.pct > 1)
  return (
    <QA n={5} q="If the overpaid administrators take a pay cut, how deep does it go?"
      verdict={`${pct(c[0].pct)} — once`} tone="no"
      answer={<>Every administrator in the district &mdash; the superintendent, the business
        manager, the special education director, the curriculum director, the human
        resources specialist and all four principals&rsquo; offices &mdash; would have to
        take a <strong>{pct(c[0].pct)} pay cut</strong> to close next year&rsquo;s hole.
        Their nine budget lines come to {usd(LEADERSHIP.payroll)} in total.</>}
      next={<>{pct(c[1].pct)} in FY{c[1].fy}, and {pct(c[2].pct)} in FY{c[2].fy}
        {over && <> &mdash; which is more than they are paid. By FY{over.fy} the town could
          pay every administrator in the district <strong>nothing at all</strong> and still
          not close the hole.</>}</>}>
      <Ledger rows={[
        ...LEADERSHIP.lines.map(l => ({ k: l.label, v: usd(l.amount) })),
        { k: 'All administrator pay, together', v: usd(LEADERSHIP.payroll), rule: true,
          strong: true },
        ...c.map(x => ({ k: `Pay cut that closes FY${x.fy}`, v: pct(x.pct),
          rule: x.fy === c[0].fy,
          tone: x.pct > 1 ? 'var(--status-critical)' : undefined })),
      ]} />
      <Note>
        Two of these lines cover more than one person: each principal line includes that
        school&rsquo;s assistant principal, and the district does not publish the split.
        The FY27 budget already removed one assistant principal, so the Primary School and
        Turkey Hill now share the one that is left.
      </Note>
    </QA>
  )
}

function Q6() {
  const left = PAYROLL.fivePercent - GAP
  return (
    <QA n={6} q="If teachers take a 5% pay cut, does that close it?"
      verdict="One year" tone="partly"
      answer={<>Yes for next year, and only next year. A 5% cut across everyone who works
        in the schools saves {usd(PAYROLL.fivePercent)}, which covers the {usd(GAP)} hole
        with {usd(left)} left over. Holding it closed means cutting deeper every single
        year.</>}
      next={<>A {pct(PAYROLL.cutFor[1].pct, 1)} pay cut in FY{PAYROLL.cutFor[1].fy}, and{' '}
        {pct(PAYROLL.cutFor[2].pct, 1)} in FY{PAYROLL.cutFor[2].fy}. Not 5% again &mdash;
        deeper, because a pay cut does not slow down anything that is rising.</>}>
      <Ledger rows={[
        { k: 'Everyone the schools pay, in salary', v: usd(PAYROLL.total) },
        { k: 'A 5% cut', v: usd(PAYROLL.fivePercent), rule: true, strong: true },
        ...PAYROLL.cutFor.map(x => ({
          k: `Cut that actually closes FY${x.fy}`, v: pct(x.pct, 1),
          rule: x.fy === PAYROLL.cutFor[0].fy })),
      ]} />
      <Note>
        The budget publishes one salary total, not a teachers-only line, so this is every
        employee &mdash; teachers, aides, custodians, secretaries and administrators alike.
        Teachers are most of it.
      </Note>
      <Note>
        <strong>And nobody votes on this number.</strong> Pay is set by a bargained
        contract. The current teachers&rsquo; agreement runs July 2024 to{' '}
        {CONTRACT.expires} and raised the salary scale{' '}
        {CONTRACT.cola.map(c => pct(c.pct, 1)).join(', then ')} &mdash;{' '}
        {pct(CONTRACT.compound, 1)} over three years. On top of that, a teacher who is not
        yet at the top moves up one step a year, worth about {pct(CONTRACT.avgStep, 1)}.
        That is why the projection uses {pct(MODEL.assumptions.salaries)} for salaries
        rather than the {pct(CONTRACT.cola[2].pct, 1)} headline: the headline is the scale,
        and the people on it are climbing it at the same time.
      </Note>

      <h4 className="text-[15px] font-bold mt-6 mb-2">
        A 5% cut is not a cut from nowhere &mdash; here is what it takes back
      </h4>
      <div className="grid gap-3 lg:grid-cols-2 items-start">
        <div className="card p-4">
          <p className="text-[12px] mb-3" style={{ color: 'var(--text-secondary)' }}>
            Where the salary scale sits, with FY24 &mdash; the year before this contract
            &mdash; set to 100.
          </p>
          <Bars />
        </div>
        <div className="card p-4">
          <p className="text-[12px] mb-3" style={{ color: 'var(--text-secondary)' }}>
            And what it is, in a paycheck.
          </p>
          <ul className="space-y-2">
            {CONTRACT.samples.map(x => (
              <li key={x.label} className="flex items-baseline justify-between gap-3
                border-t pt-2" style={{ borderColor: 'var(--grid)' }}>
                <span className="text-[13px]">{x.label}
                  <span className="block text-[11px]" style={{ color: 'var(--text-muted)' }}>
                    {usd(x.pay)} today
                  </span>
                </span>
                <span className="text-[13px] font-bold tnum shrink-0"
                  style={{ color: 'var(--status-critical)' }}>
                  &minus;{usd(Math.round(x.pay * 0.05))}
                </span>
              </li>
            ))}
          </ul>
        </div>
      </div>

      <h4 className="text-[15px] font-bold mt-6 mb-2">
        The question nobody is asking, which is worth more than this one
      </h4>
      <p className="text-[14px] leading-relaxed mb-3">
        The teachers&rsquo; contract <strong>expires {CONTRACT.expires}</strong> &mdash; so
        FY{GAPS[0].fy} is the first year of an agreement that has not been negotiated yet.
        Nobody has to cut anyone&rsquo;s pay for that number to move. It is simply not
        written down, and every half a percentage point of it is worth{' '}
        <strong>{usd(SETTLEMENT.perHalfPoint)}</strong> against next year&rsquo;s hole.
        Either side must give notice by {CONTRACT.noticeBy} to open the talks.
      </p>
      <Ledger rows={[
        ...SETTLEMENT.rates.map(r => ({
          k: r.rate === SETTLEMENT.assumed
            ? <><strong>If the next contract settles at {pct(r.rate, 1)}</strong>{' '}
                &mdash; what this tool assumes</>
            : <>If the next contract settles at {pct(r.rate, 1)}
                {r.rate === 0 && ' — a total freeze, steps included'}
                {r.rate === 0.025 && ' — matching what the town may collect'}</>,
          v: r.gap <= 0 ? `${usd(-r.gap)} to spare` : usd(r.gap),
          strong: r.rate === SETTLEMENT.assumed,
          tone: r.gap <= 0 ? 'var(--status-good)'
            : r.gap < GAP ? 'var(--status-warning)' : 'var(--status-critical)',
        })),
      ]} />
      <Note>
        Read the top line carefully, because it is the whole argument of this page in one
        row: <strong>if pay stopped rising altogether &mdash; no raise and no step
        &mdash; the schools would not have a shortfall at all</strong>, next year or for
        the five after it. That is not a proposal. It is a measurement of where the gap
        comes from. The projection already assumes the salary line grows{' '}
        {pct(SETTLEMENT.assumed)}, which is {usd(SETTLEMENT.assumedCost)} next year &mdash;
        more than the {usd(GAP)} hole itself. <strong>The gap is smaller than the
        raise.</strong>
      </Note>
      <Note>
        The fair reading, which cuts both ways. Lunenburg&rsquo;s settlements are ordinary
        &mdash; 2.5%, 4% and 3.5% is roughly inflation, and the neighbouring districts
        settled in the same range. A settlement below inflation is a real pay cut, and the
        district competes for teachers with towns that are not offering one. But the town
        may only collect {pct(REVENUE_CAP, 1)} more each year. <strong>A 2.5% revenue cap
        cannot fund an ordinary wage settlement</strong>, and no one at the bargaining
        table did anything wrong to arrive here.
      </Note>
    </QA>
  )
}

/** One bar in the scale chart: a full-width track with the bar sized inside it. */
function Bar({ label, index, max, color, strong }: {
  label: string; index: number; max: number; color: string; strong?: boolean
}) {
  return (
    <li className="flex items-center gap-2">
      <span className="text-[11px] tnum w-10 shrink-0"
        style={{ color: strong ? color : 'var(--text-muted)',
                 fontWeight: strong ? 700 : 400 }}
        dangerouslySetInnerHTML={{ __html: label }} />
      <span className="flex-1 h-4 rounded-sm" style={{ background: 'var(--surface-3)' }}>
        <span className="block h-4 rounded-sm"
          style={{ width: `${(index / max) * 100}%`, background: color }} />
      </span>
      <span className={`text-[11px] tnum w-12 text-right shrink-0 ${strong ? 'font-bold' : 'font-semibold'}`}
        style={strong ? { color } : undefined}>{(index * 100).toFixed(1)}</span>
    </li>
  )
}

/** Delta against a named contract year, rather than a position in the array. */
const at = (vs: { fy: number; delta: number }[], fy: number) =>
  vs.find(v => v.fy === fy)?.delta ?? 0

/** The salary scale across the contract, and where a 5% cut lands on it.
 *
 *  Indexed to the year before the contract rather than to dollars: the point is the
 *  distance travelled, and a dollar axis starting at $50,000 would flatten it. */
function Bars() {
  const { years, after, vs } = scaleAfterCut(0.05)
  const rows = [{ fy: 24, index: 1 }, ...years]
  const max = Math.max(...rows.map(r => r.index))
  return (
    <div>
      <ul className="space-y-1.5">
        {rows.map(r => (
          <Bar key={r.fy} label={`FY${r.fy}`} index={r.index} max={max}
            color="var(--series-cost)" />
        ))}
        <li className="pt-1.5 border-t" style={{ borderColor: 'var(--grid)' }}>
          <ul><Bar label="&minus;5%" index={after} max={max}
            color="var(--status-critical)" strong /></ul>
        </li>
      </ul>
      <p className="text-[12px] leading-relaxed mt-3" style={{ color: 'var(--text-secondary)' }}>
        A 5% cut lands {pct(Math.abs(at(vs, 26)), 1)} <strong>below</strong> the FY26 scale
        and {pct(at(vs, 24), 1)} <strong>above</strong> the FY24 one. So it gives back the
        whole of this year&rsquo;s {pct(CONTRACT.cola[2].pct, 1)} raise and part of last
        year&rsquo;s {pct(CONTRACT.cola[1].pct, 1)} &mdash; and still leaves the scale
        higher than it was before the contract began.
      </p>
    </div>
  )
}

function Q7() {
  return (
    <QA n={7} q="How much would we have to cut health insurance?"
      verdict={`${pct(HEALTH.employeeShare)} → ${pct(HEALTH.shareNeeded, 1)}`} tone="partly"
      answer={<>You cannot really cut health insurance &mdash; the premium costs what it
        costs. All you can change is <em>who pays it</em>. Today the town pays{' '}
        {pct(MODEL.health.townShare)} of the bill and the employee pays{' '}
        {pct(HEALTH.employeeShare)}. To close next year&rsquo;s hole, the employee&rsquo;s
        share has to rise to <strong>{pct(HEALTH.shareNeeded, 1)}</strong> &mdash; which
        costs a family on the broadest plan roughly{' '}
        <strong>{usd(HEALTH.costPerFamily)} a year</strong> out of their pay.</>}
      next={<>Further still, and there is a ceiling. Even at a {pct(HEALTH.maxShare)}{' '}
        employee share &mdash; the most this tool models &mdash; the shift raises{' '}
        {usd(HEALTH.maxModelled)}, which is {usd(GAP - HEALTH.maxModelled)} short of next
        year&rsquo;s hole on its own.</>}>
      <Ledger rows={[
        { k: 'What the schools spend on health insurance', v: usd(HEALTH.budget) },
        { k: 'The employee pays this share of the premium today',
          v: pct(HEALTH.employeeShare) },
        { k: 'The employee would have to pay this share instead',
          v: pct(HEALTH.shareNeeded, 1), rule: true, strong: true,
          tone: 'var(--status-critical)' },
        { k: 'Moving 1% of the premium onto employees is worth',
          v: usd(HEALTH.grossPerPoint) },
        { k: 'Of which the schools keep (state law returns a quarter in year one)',
          v: usd(HEALTH.perPoint), rule: true },
        { k: 'Cost to one family on the broadest plan, per year',
          v: usd(HEALTH.costPerFamily), tone: 'var(--status-critical)' },
      ]} />
      <Note>
        This is a pay cut with a different name, it is bargained with every union, and the
        Town &mdash; not the school district &mdash; owns the insurance group, so the
        schools cannot do it on their own. Health insurance is also the fastest-rising
        thing in the budget at {pct(HEALTH.rise)} a year, which is why slowing it matters
        more than shifting it. That is the last section on this page.
      </Note>
    </QA>
  )
}

function Q8() {
  const one = DEVELOPMENT.oneYear
  const five = DEVELOPMENT.fiveYear
  const ten = DEVELOPMENT.tenYear
  const first = DEVELOPMENT.history[0]
  const last = DEVELOPMENT.history[DEVELOPMENT.history.length - 1]
  return (
    <QA n={8} q="How much new business do we have to build to close the gap?"
      verdict={`~${five.developments.toFixed(0)} a year`} tone="no"
      answer={<>There is good news first. Buildings stay on the tax roll, so the amount that
        closes next year is almost exactly the amount that holds the line for five years
        &mdash; {usd(five.needed)} a year of new growth, against the {usd(one.needed)} that
        closes FY{GAPS[0].fy} alone. The bad news is the size of it:{' '}
        <strong>{usdShort(five.value)} of brand new business value, every year</strong>{' '}
        &mdash; about {five.developments.toFixed(0)} typical developments a year, on top of
        what the town already expects.</>}
      next={<>The same rate holds through FY{GAPS[4].fy}. To hold it for ten years it has
        to rise to about {ten.developments.toFixed(0)} developments a year. And none of it
        helps next April: the buildings that pay FY{GAPS[0].fy}&rsquo;s taxes would have to
        be standing today.</>}>
      <Ledger rows={[
        { k: 'New business value needed each year, above what the town already assumes',
          v: usd(five.value), strong: true },
        { k: `Typical developments a year (${usdShort(DEVELOPMENT.mixValue)} each)`,
          v: five.developments.toFixed(1) },
        { k: 'Or, average Lunenburg businesses a year', v: Math.round(five.businesses).toString() },
        { k: 'All the business, industrial and equipment property the town has today',
          v: usd(DEVELOPMENT.existingBase), rule: true },
        { k: 'So, as a share of that, added every year',
          v: pct(five.shareOfBase), strong: true, tone: 'var(--status-critical)' },
      ]} />
      <Note>
        Two things make this harder than it sounds. First, only about{' '}
        {(DEVELOPMENT.share * 100).toFixed(0)} cents of each new tax dollar reaches the
        schools &mdash; the rest funds fire, police, roads and everything else the town
        does. Second, the town&rsquo;s actual record runs the other way. The projection
        already assumes {usd(T.currentNewGrowthRevenue)} of new growth a year, which is
        more than the town managed in FY{last.fy}; the figures above are on top of that.
        All in, it needs {usd(five.needed)} of new growth every year &mdash; about{' '}
        {five.vsBest.toFixed(1)} times its best year since FY{first.fy} ({usd(first.amount)})
        and {five.vsActual.toFixed(1)} times its most recent ({usd(last.amount)}). Housing
        would do it too, on paper &mdash; roughly {Math.round(five.homes)} new homes a
        year &mdash; except that homes send children, and the schools lose money on any
        home with more than {(T.schoolShareOfBill / T.localCostPerPupil).toFixed(2)} of a
        child in it.
      </Note>
    </QA>
  )
}

function Q9() {
  const net = RELIEF.total - BILL.overrideCost[0].cost
  const h = T.avgHomeHistory
  const first = h[0], last = h[h.length - 1]
  return (
    <QA n={9} q="Can we fund the schools and lower our tax bill at the same time?"
      verdict="Yes, for a while" tone="yes"
      answer={<>Yes &mdash; and this is the least understood thing in the whole
        conversation. Two levers lower the average tax bill without taking a dollar from
        the schools. Together they are worth about <strong>{usd(RELIEF.total)} a year</strong>{' '}
        off a {usd(BILL.average)} bill. Funding next year&rsquo;s school hole by townwide
        vote costs about {usd(BILL.overrideCost[0].cost)}. Do all three and the average
        homeowner pays roughly <strong>{usd(net)} a year less than today</strong>, with the
        schools whole.</>}
      next={<>The relief is a one-time step down; the school hole keeps growing into it. By
        FY{BILL.overrideCost[4].fy} funding the schools costs{' '}
        {usd(BILL.overrideCost[4].cost)} and you are still{' '}
        {usd(RELIEF.total - BILL.overrideCost[4].cost)} ahead. By FY{RELIEF.outrunBy} you
        are back above today&rsquo;s bill. So: a real reprieve of about five years, not a
        fix.</>}>
      <Ledger rows={[
        { k: <>Adopt the maximum split tax rate &mdash; homes pay{' '}
          ${BILL.splitResidentialRate.toFixed(2)} per $1,000 instead of $
          {BILL.rate.toFixed(2)}</>,
          v: `−${usd(BILL.splitSaving)}`, tone: 'var(--status-good)' },
        { k: <>Let the excluded building debt roll off, and vote no new debt behind it</>,
          v: `−${usd(BILL.debtSaving)}`, tone: 'var(--status-good)' },
        { k: 'Relief, on the average home', v: `−${usd(RELIEF.total)}`, rule: true,
          strong: true, tone: 'var(--status-good)' },
        { k: `Fund the FY${GAPS[0].fy} school hole by townwide vote`,
          v: `+${usd(BILL.overrideCost[0].cost)}` },
        { k: 'Net, against today’s bill', v: `−${usd(net)}`, rule: true, strong: true,
          tone: 'var(--status-good)' },
      ]} />
      <Note>
        The catches, in order. The split rate does not create money &mdash; it moves about{' '}
        {usd(BILL.splitBusinessCost)} a year onto the average business, which are the same
        businesses the town is trying to attract. The excluded debt leaves the bill only
        when those projects are paid off and only if nothing replaces them; the town has
        not published the payoff schedule, so treat the timing as unknown. And the town has
        already voted down two override questions &mdash;{' '}
        {usdShort(BILL.failedOverrides[0].amount)} and{' '}
        {usdShort(BILL.failedOverrides[1].amount)} &mdash; by better than two to one, which
        is a far larger ask than the {usd(BILL.overrideCost[0].cost)} above.
      </Note>
      <Note>
        <strong>One note on &ldquo;the rate&rdquo;.</strong> Lunenburg&rsquo;s tax rate has
        fallen every year since FY{first.fy} &mdash; from ${first.rate} per $1,000 to $
        {last.rate.toFixed(2)} in FY{last.fy}, and ${BILL.rate.toFixed(2)} today. Bills went up anyway, from{' '}
        {usd(first.bill)} to {usd(last.bill)} to {usd(BILL.average)}, because assessments
        rose faster than the rate fell. The rate is not the number that decides what you
        pay; the bill is. This tool holds no data on neighbouring towns&rsquo; rates or
        bills, so it makes no comparison to them.
      </Note>
    </QA>
  )
}

/* ------------------------------------------------------------------ */

function Scoreboard() {
  return (
    <div className="card overflow-x-auto">
      <table className="w-full text-[13px] min-w-[720px]">
        <thead>
          <tr style={{ background: 'var(--surface-3)' }}>
            <th className="text-left px-4 py-2.5 font-semibold">What you would do</th>
            <th className="text-right px-4 py-2.5 font-semibold whitespace-nowrap">
              Saves a year
            </th>
            <th className="text-center px-4 py-2.5 font-semibold whitespace-nowrap">
              Closes FY{GAPS[0].fy}?
            </th>
            <th className="text-center px-4 py-2.5 font-semibold whitespace-nowrap">
              Years it lasts
            </th>
            <th className="text-left px-4 py-2.5 font-semibold">What it costs</th>
          </tr>
        </thead>
        <tbody>
          {OPTIONS.map(o => {
            const yrs = o.permanent ? 5 : yearsCovered(o.saves, o.growth)
            const ok = o.saves >= GAP
            return (
              <tr key={o.id} className="border-t align-top"
                style={{ borderColor: 'var(--grid)' }}>
                <td className="px-4 py-3 font-medium">
                  {o.anchor
                    ? <a href={`#${o.anchor}`} className="hover:underline"
                        style={{ color: 'var(--series-cost)' }}>{o.label}</a>
                    : o.label}
                </td>
                <td className="px-4 py-3 text-right tnum font-semibold whitespace-nowrap">
                  {usd(o.saves)}
                </td>
                <td className="px-4 py-3 text-center whitespace-nowrap font-semibold"
                  style={{ color: ok ? 'var(--status-good)' : 'var(--status-critical)' }}>
                  {ok ? '✓ Yes' : `✕ ${pct(o.saves / GAP)}`}
                </td>
                <td className="px-4 py-3 text-center tnum font-bold"
                  style={{ color: yrs >= 5 ? 'var(--status-good)'
                    : yrs >= 1 ? 'var(--status-warning)' : 'var(--status-critical)' }}>
                  {yrs === 0 ? '—' : o.permanent ? `${yrs}+` : yrs}
                </td>
                <td className="px-4 py-3" style={{ color: 'var(--text-secondary)' }}>
                  {o.costs}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

function WhatWorks({ onJump }: {
  onJump: (tab: 'why' | 'development' | 'adjust') => void
}) {
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <div className="card p-5">
        <p className="text-[11px] font-semibold uppercase tracking-widest mb-1"
          style={{ color: 'var(--text-muted)' }}>Fix one</p>
        <h3 className="text-lg font-bold mb-2">Income that grows as fast as costs</h3>
        <p className="text-[13px] leading-relaxed mb-3" style={{ color: 'var(--text-secondary)' }}>
          There are only two forms of it. Build enough new business that the tax roll grows
          at the same speed as the cost of running schools &mdash; about{' '}
          {DEVELOPMENT.fiveYear.developments.toFixed(0)} developments a year, which is real
          and slow and worth starting. Or vote to raise taxes above the cap, repeatedly:{' '}
          {usd(BILL.overrideCost[0].cost)} on the average home for FY{GAPS[0].fy},{' '}
          {usd(BILL.overrideCost[4].cost)} to cover through FY{GAPS[4].fy}. The town said no
          twice in 2026, to much larger questions.
        </p>
        <button onClick={() => onJump('development')}
          className="text-[12px] font-semibold" style={{ color: 'var(--series-cost)' }}>
          See the development arithmetic &rarr;
        </button>
      </div>

      <div className="card p-5">
        <p className="text-[11px] font-semibold uppercase tracking-widest mb-1"
          style={{ color: 'var(--text-muted)' }}>Fix two</p>
        <h3 className="text-lg font-bold mb-2">Make something stop rising at 9%</h3>
        <p className="text-[13px] leading-relaxed mb-3" style={{ color: 'var(--text-secondary)' }}>
          The other permanent answer needs nobody&rsquo;s dollar. Health insurance is{' '}
          {pct(BENT_HEALTH.from)} a year and the biggest single driver in the budget. Hold
          it to {pct(BENT_HEALTH.to)} &mdash; through the Town&rsquo;s insurance group, plan
          design, or joining a larger pool &mdash; and next year&rsquo;s hole falls from{' '}
          {usd(GAPS[0].cumulative)} to {usd(BENT_HEALTH.gaps[0].cumulative)}, and
          FY{GAPS[4].fy}&rsquo;s from {usd(GAPS[4].cumulative)} to{' '}
          {usd(BENT_HEALTH.gaps[4].cumulative)}. That is {usd(BENT_HEALTH.savedByFy32)} a
          year, without cutting a single thing a student touches.
        </p>
        <button onClick={() => onJump('why')}
          className="text-[12px] font-semibold" style={{ color: 'var(--series-cost)' }}>
          See how the two rates compound &rarr;
        </button>
      </div>

      <div className="card p-5 lg:col-span-2" style={{ background: 'var(--surface-3)' }}>
        <p className="text-[14px] leading-relaxed">
          <strong>The bottom line.</strong> Next year will be settled with some combination
          of fees, savings and cuts, because that is all that can be arranged by April.
          Cutting every sport, every club, the whole front office of all four schools and
          60% of the technology budget &mdash; all of it at once &mdash; buys the town two
          years. What decides whether this conversation is still happening in 2035 is
          whether the town spends the next decade doing the two slow things above. Nothing
          on the cut list is a strategy; it is a way of paying for the year in which no
          strategy was chosen.
        </p>
        <button onClick={() => onJump('adjust')}
          className="text-[12px] font-semibold mt-3" style={{ color: 'var(--series-cost)' }}>
          Try your own combination on the Adjust page &rarr;
        </button>
      </div>
    </div>
  )
}

import { useMemo } from 'react'
import { MODEL, project, runCascade, usd } from '../model/engine'
import { Section, Stat, Note } from '../components/primitives'
import { Composition, FrillsCheck } from '../components/Composition'
import { Magnitude } from '../components/Magnitude'
import { PeerGrowth, PeerTable, PeerLessons } from '../components/Peers'
import { SportTable, FeeAccounting, CurrentFees, SplitReporting } from '../components/Athletics'
import { Recommendation } from '../components/Recommendation'

/** Set true to put our own recommendation back on the situation page. */
const SHOW_OUR_RECOMMENDATION = false
import { TaxStructure, ResidentialParadox } from '../components/TaxBase'
import { CommercialTrend, HomeValueParadox } from '../components/CommercialTrend'
import { BusinessFormation, BusinessCategories } from '../components/BusinessFormation'
import { Conclusions } from '../components/Conclusions'
import { Derivations } from '../components/Derivations'

export const CONTEXT_NAV = [
  ['conclusions', 'What we found'],
  ['where-we-are', 'Where we are'],
  ['the-money', 'The money'],
  ['neighbors', 'Neighbors'],
  ['fees', 'Fees today'],
  ['tax-base', 'Business growth'],
  ['derivations', 'Show the math'],
  ['method', 'Sources'],
] as const

/** Everything that is reading rather than deciding.
 *
 *  Nothing on this page changes a number anywhere else. It exists so that every dial on
 *  the adjustments page has somewhere to point when a reader asks "says who?". */
export function Context({ onRecommend, onSources, onAthletics }: {
  onRecommend: () => void; onSources: () => void; onAthletics: () => void
}) {
  // The context page argues from the district's own published assumptions, untouched by
  // anything the reader has done elsewhere — otherwise the prose and the chart disagree.
  const base = useMemo(() => runCascade(
    MODEL.presets.school_committee.order, MODEL.assumptions, 5), [])
  const plain = useMemo(() => project(5, MODEL.assumptions), [])
  const gap = base[0].deficit
  const f = MODEL.facts

  return (
    <div>
      {/* ---------- hero ---------- */}
      <div className="mx-auto max-w-6xl px-5 pt-14 pb-10">
        <p className="text-xs font-semibold uppercase tracking-widest mb-3"
          style={{ color: 'var(--status-critical)' }}>
          A projection, not a district budget
        </p>
        <h1 className="text-4xl sm:text-5xl font-bold tracking-tight leading-[1.05] max-w-3xl">
          What happens to Lunenburg&rsquo;s schools next year?
        </h1>
        <p className="mt-5 text-lg leading-relaxed max-w-2xl"
          style={{ color: 'var(--text-secondary)' }}>
          In May 2026 voters rejected both budget overrides about two to one. The schools
          absorbed the balanced budget: four classroom teachers gone, class sizes pushed
          toward 30, middle school sports and Grade&nbsp;5 band eliminated. This page is
          the evidence. The other two are where you decide what to do about it.
        </p>

        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 mt-9">
          <Stat label="FY27 school budget" value={usd(f.stmAmount + MODEL.fy27.lps_appropriation)}
            sub={`Balanced budget (${usd(MODEL.fy27.lps_appropriation)}) plus `
              + `${usd(f.stmAmount)} a Special Town Meeting has yet to vote on 3 September`} />
          <Stat label="Projected FY28 gap" value={usd(gap)} tone="critical"
            sub="Cost of today's services minus revenue likely to be available" />
          <Stat label="Cutting every sport saves" value={usd(f.athleticsRemaining)}
            sub={`A further ${usd(f.athleticsAlreadyCut)} of athletics is already cut`} />
          <Stat label="Override vote, May 2026" value="33% yes" tone="critical"
            sub={`${f.overrideQ1.yes.toLocaleString()} for, ${f.overrideQ1.no.toLocaleString()} against`} />
        </div>
      </div>

      <Section id="conclusions" eyebrow="The short version" title="What we found"
        lede={<>Six numbers, then {MODEL.conclusions.length} findings &mdash; from the
          published budgets, the town warrant, the Assessors&rsquo; own hearings, the Town
          Clerk&rsquo;s business records and five neighboring districts. These are our
          conclusions, not the district&rsquo;s and not the town&rsquo;s. Every one links to
          the section that shows the arithmetic.</>}>
        <Conclusions />
      </Section>

      <Section id="where-we-are" eyebrow="The starting point" title="How Lunenburg got here"
        lede={<>The town put three budgets to voters: a balanced budget that fit available
          revenue, and two override tiers that would have restored services. Town Meeting
          adopted the balanced budget on 2 May. Both override questions failed at the ballot
          on 16 May.</>}>
        <div className="grid gap-4 md:grid-cols-2">
          <div className="card p-5">
            <h3 className="text-sm font-bold mb-4">The ballot, 16 May 2026</h3>
            {[f.overrideQ1, f.overrideQ2].map((q: any, i: number) => {
              const pct = (q.yes / (q.yes + q.no)) * 100
              return (
                <div key={i} className="mb-4 last:mb-0">
                  <div className="flex items-baseline justify-between text-[13px] mb-1.5">
                    <span className="font-medium">
                      Question {i + 1} &mdash; {usd(q.amount)} override
                    </span>
                    <span className="font-bold tnum">{pct.toFixed(0)}% yes</span>
                  </div>
                  <div className="h-2.5 rounded-full overflow-hidden flex gap-0.5"
                    style={{ background: 'var(--surface-3)' }}>
                    <div style={{ width: `${pct}%`, background: 'var(--status-good)' }} />
                    <div style={{ width: `${100 - pct}%`, background: 'var(--status-critical)' }} />
                  </div>
                  <p className="text-[11px] mt-1 tnum" style={{ color: 'var(--text-muted)' }}>
                    ✓ {q.yes.toLocaleString()} yes &nbsp;·&nbsp; ✕ {q.no.toLocaleString()} no
                  </p>
                </div>
              )
            })}
            <Note>
              {f.ballotsCast.toLocaleString()} ballots cast of {f.registered.toLocaleString()}{' '}
              registered voters &mdash; {((f.ballotsCast / f.registered) * 100).toFixed(0)}%
              turnout. Both questions failed in all four precincts.
            </Note>
          </div>

          <div className="card p-5">
            <h3 className="text-sm font-bold mb-3">What the balanced budget cut</h3>
            <ul className="space-y-2 text-[13px]" style={{ color: 'var(--text-secondary)' }}>
              {[
                ['2.0 classroom teachers, Primary School', '$205,019'],
                ['2.0 classroom teachers, Turkey Hill', '$171,811'],
                ['1.0 Assistant Principal, through attrition', '$152,829'],
                ['1.5 interventionists', '$189,604'],
                ['1.0 occupational therapy assistant', '$74,147'],
                ['1.0 custodian, through attrition', '$48,630'],
                ['All athletic transportation', '$127,550'],
                ['Middle school and freshman sports', '$14,415'],
                ['0.2 music teacher — ends Grade 5 band', '$14,488'],
              ].map(([l, v]) => (
                <li key={l} className="flex justify-between gap-3">
                  <span>{l}</span><span className="tnum shrink-0">{v}</span>
                </li>
              ))}
            </ul>
            <Note>
              The district states class sizes now run 27&ndash;30 students, and that the
              Primary School and Turkey Hill share a single Assistant Principal.
            </Note>
          </div>
        </div>

        <div className="card p-5 mt-4">
          <h3 className="text-sm font-bold mb-2">One piece is being put back</h3>
          <p className="text-[13px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
            The enacted state budget gave Lunenburg {usd(f.enactedStateAid)} more than
            planned. A Special Town Meeting on 3 September 2026 will vote {usd(f.stmAmount)}
            {' '}of it to the schools: two reading specialists, the high school Assistant
            Principal back to full time, 52 Ignite tutoring seats and a 0.4 music teacher.
            {' '}<strong>This money is one-time.</strong> Keeping those five things in FY28
            is itself a new cost the district has to absorb &mdash; which is why they appear
            as choices on the adjustments page.
          </p>
        </div>
      </Section>

      <Section id="the-money" eyebrow="Reality check"
        title="You cannot cut your way out of this with the extras"
        lede={<>The most common suggestion at any budget meeting is to cut sports, or arts,
          or &ldquo;administration.&rdquo; Here is what those things are actually worth
          against what the budget actually is.</>}>
        <Magnitude years={base} />

        <h3 className="text-lg font-bold mt-12 mb-4">Why it is that small</h3>
        <div className="grid gap-4 lg:grid-cols-2">
          <div>
            <h3 className="text-sm font-bold mb-3">Where the {usd(MODEL.fy27.lps_appropriation)} goes</h3>
            <Composition />
            <Note>
              Salaries, health insurance, transportation and out-of-district tuition are
              roughly nine of every ten dollars &mdash; and each is set by contract, by the
              insurance market, or by law. Only the last band is genuinely discretionary.
            </Note>
          </div>
          <div>
            <h3 className="text-sm font-bold mb-3">Cutting everything people suggest cutting</h3>
            <FrillsCheck gap={gap} />
            <Note>
              Comparable districts learned the same thing. When Easthampton&rsquo;s override
              failed, {usd(2_500_000)} of its {usd(2_700_000)} in cuts &mdash; 93% &mdash;
              had to come from personnel. There is no other place large enough.
            </Note>
          </div>
        </div>
      </Section>

      <Section id="neighbors" eyebrow="Local comparison"
        title="Every district around us is squeezed. They chose differently."
        lede={<>Five neighboring districts built FY27 budgets under the same pressures:
          health insurance up 8&ndash;14%, Chapter 70 aid up 1.5&ndash;2%, retirement
          assessments up around 10%. None of them escaped it. What separates them is
          what they decided to protect.</>}>
        <div className="grid gap-4 lg:grid-cols-2 mb-10">
          <div>
            <h3 className="text-sm font-bold mb-3">Budget growth, FY26 to FY27</h3>
            <PeerGrowth />
            <Note>
              Lunenburg&rsquo;s schools grew <strong>1.08%</strong> in a year when
              neighboring districts grew 2.9% to 6.5% &mdash; and when everyone&rsquo;s
              fixed costs rose far faster than that. The gap between our bar and theirs is
              the reason the cut list exists.
            </Note>
          </div>
          <div>
            <h3 className="text-sm font-bold mb-3">What the comparison teaches</h3>
            <PeerLessons />
          </div>
        </div>

        <h3 className="text-sm font-bold mb-3">District by district</h3>
        <PeerTable />
      </Section>

      <Section id="fees" eyebrow="The lever that is already half-pulled"
        title="What athletics costs, and what families already pay"
        lede={<>Lunenburg <strong>already charges, and just raised the fee</strong> &mdash;
          {' '}$400 for a first child this year, up from $250, plus $180 a year for the bus.
          Town Meeting passed only the Balanced budget, so the athletics that exists costs{' '}
          {usd(MODEL.athletics.adopted)}, not the {usd(MODEL.athletics.levelService)} it
          would take to run every high school team &mdash; and not the{' '}
          {usd(MODEL.athletics.ladder.find(r => r.id === 'restoration')?.total ?? 0)} it
          would take to field the middle school teams as well, which is the only version
          that is a whole program. The fee slider itself lives on the
          adjustments page &mdash; this is what it is being asked to pay for.</>}>
        <CurrentFees />

        <h3 className="text-sm font-bold mt-10 mb-3">What each sport actually costs</h3>
        <SportTable fee={MODEL.currentFees.effectiveAthletic} />

        <h3 className="text-sm font-bold mt-10 mb-3">Where does the fee money actually go?</h3>
        <div className="mb-4"><SplitReporting /></div>
        <FeeAccounting />

        <button onClick={onAthletics}
          className="card p-4 mt-4 w-full text-left text-[13px]"
          style={{ color: 'var(--text-secondary)' }}>
          <strong style={{ color: 'var(--text-primary)' }}>Athletics, both sides of the
          money &rarr;</strong> Every line of the town&rsquo;s athletics budget and every
          line of the fee-funded revolving fund, thirteen years, side by side &mdash;
          including the four years nobody published the fund at all.
        </button>
      </Section>

      <Section id="tax-base" eyebrow="The revenue side"
        title="Can business growth fix this instead?"
        lede={<>Every budget argument in Lunenburg eventually reaches someone saying we need
          more commercial development. They are not wrong &mdash; but almost nobody in town
          knows how the mechanism actually works, or how long it takes. Here is the whole
          thing, with the arithmetic shown.</>}>
        <TaxStructure />

        <h3 className="text-lg font-bold mt-12 mb-1">Is the commercial base actually growing?</h3>
        <p className="text-[13px] mb-4 max-w-3xl" style={{ color: 'var(--text-secondary)' }}>
          This is the question behind every &ldquo;we need more business&rdquo; comment at
          Town Meeting. The Board of Assessors publishes the answer every year, and it is
          not encouraging.
        </p>
        <CommercialTrend />

        <h3 className="text-lg font-bold mt-12 mb-1">So are businesses actually leaving?</h3>
        <p className="text-[13px] mb-4 max-w-3xl" style={{ color: 'var(--text-secondary)' }}>
          No &mdash; and that is the surprise. The Town Clerk&rsquo;s business certificate
          records show a healthy number of businesses registering every year. The problem
          turns out to be a different one entirely.
        </p>
        <BusinessFormation />
        <div className="mt-4"><BusinessCategories /></div>

        <h3 className="text-lg font-bold mt-12 mb-1">Proof that rising values do not help</h3>
        <p className="text-[13px] mb-4 max-w-3xl" style={{ color: 'var(--text-secondary)' }}>
          If you take one thing from this page, take this table.
        </p>
        <HomeValueParadox />

        <h3 className="text-lg font-bold mt-12 mb-1">Why building houses makes it worse</h3>
        <p className="text-[13px] mb-4 max-w-3xl" style={{ color: 'var(--text-secondary)' }}>
          Under a single tax rate, a home and a business of equal value pay identical taxes
          &mdash; but only one of them sends children to school.
        </p>
        <ResidentialParadox />
      </Section>

      {/* Our own recommendation, kept and not shown.
       *
       * The rest of this site works by handing somebody the arithmetic and getting out of
       * the way, and a section headed "what we'd actually do" spends the credit that
       * earns. A reader who finds a prescription stops checking the sums and starts
       * agreeing or disagreeing with the author, which is a worse conversation and not the
       * one this tool is for.
       *
       * Deliberately still here, wired and rendering, one flag from returning. The
       * reasoning in it is sound; it is the position on the page that was wrong. */}
      {SHOW_OUR_RECOMMENDATION && (
        <Section id="recommendation" eyebrow="Our answer" title="What we’d actually do"
          lede={<>Everything else in this tool is for reaching your own conclusion. This is
            ours, with the reasoning exposed so you can disagree with it precisely.</>}>
          <Recommendation gap={gap} onApply={onRecommend} />
        </Section>
      )}

      <Section id="derivations" eyebrow="Show the math"
        title="How every rolled-up number was calculated"
        lede={<>&ldquo;How did you get to a {usd(MODEL.athletics.levelService)} athletics
          budget?&rdquo; is a fair question, and it deserves an answer you can check rather
          than a number you have to trust. Every figure in this app that is a roll-up of
          several budget lines is rebuilt here from the district&rsquo;s own line-item
          budget &mdash; every line named, every total added back up, and the judgment
          calls stated out loud.</>}>
        <Derivations />
      </Section>

      <Section id="method" eyebrow="Method" title="Where these numbers come from">
        <div className="grid gap-4 md:grid-cols-2 text-[13px] leading-relaxed"
          style={{ color: 'var(--text-secondary)' }}>
          <div className="card p-5">
            <h3 className="text-sm font-bold mb-3" style={{ color: 'var(--text-primary)' }}>
              What is published fact
            </h3>
            <ul className="space-y-2 list-disc pl-4">
              <li>The FY27 budget, line by line, in all four scenarios &mdash; from the
                district&rsquo;s own 23 March 2026 budget document.</li>
              <li>The cut and restoration lists, staffing counts and impact statements
                &mdash; from the district&rsquo;s Multi-Scenario Financial Analysis.</li>
              <li>The override results &mdash; from the town&rsquo;s unofficial tally sheet.</li>
              <li>The revenue formula, tax impact and category totals &mdash; from the Town
                Manager&rsquo;s 17 April 2026 press release.</li>
              <li>The September town meeting plan &mdash; from the district&rsquo;s
                Additional Town Revenue Spending Plan.</li>
              <li>Every neighboring district&rsquo;s figures &mdash; from that
                district&rsquo;s own published FY27 budget document or meeting minutes,
                cited on each card.</li>
            </ul>
          </div>
          <div className="card p-5">
            <h3 className="text-sm font-bold mb-3" style={{ color: 'var(--text-primary)' }}>
              What is our projection
            </h3>
            <ul className="space-y-2 list-disc pl-4">
              <li><strong>There is no FY28 budget yet.</strong> That work starts in
                January 2027. Everything after FY27 here is modeled.</li>
              <li>Costs are grown from the FY27 adopted budget using the growth rates on
                the adjustments page &mdash; defaulted to the district&rsquo;s own FY27
                assumptions.</li>
              <li>Revenue is grown using the town&rsquo;s published Proposition 2&frac12;
                formula, with the schools holding their current share.</li>
              <li>Programs marked <em>our estimate</em> &mdash; the AP catalogue, the high
                school music program, middle school electives &mdash; are costed by us. The
                district has not published a price for cutting them.</li>
              <li>The order of cuts is a model, not a plan. No one has decided any of this.</li>
            </ul>
          </div>
        </div>
        <p className="mt-6 text-[13px]">
          <button onClick={onSources} className="font-semibold underline"
            style={{ color: 'var(--series-cost)' }}>
            See every document this is built on &rarr;
          </button>
        </p>
        <Note>
          Built from public documents published by Lunenburg Public Schools and the Town of
          Lunenburg. Peer comparisons drawn from reporting on Easthampton,
          Bridgewater-Raynham, South Hadley, Groton-Dunstable, Winchester and Duxbury.
          This is an independent projection and is not affiliated with, endorsed by, or
          approved by the school district or the town. Level-service cost reaches{' '}
          {usd(plain.at(-1)?.levelService ?? 0)} by FY{plain.at(-1)?.fy} on the
          district&rsquo;s own growth rates.
        </Note>
      </Section>
    </div>
  )
}

import { useMemo, useState } from 'react'
import {
  MODEL, project, runCascade, usd, leverYield, leverStart,
  type Assumptions, type AppliedItem,
} from './model/engine'
import { Section, Stat, Note } from './components/primitives'
import { PriorityBuilder } from './components/PriorityBuilder'
import { CutLine, type Tick } from './components/CutLine'
import { YearChart } from './components/YearChart'
import { Composition, FrillsCheck } from './components/Composition'
import { Magnitude } from './components/Magnitude'
import { AssumptionsPanel } from './components/Assumptions'
import { Timeline, Landmarks } from './components/Timeline'
import { PeerGrowth, PeerTable, PeerLessons } from './components/Peers'
import { AthleticsFees, SportTable, FeeAccounting, CurrentFees } from './components/Athletics'
import { LeverWorkbench } from './components/Levers'
import { HealthInsurance } from './components/HealthInsurance'
import { Recommendation } from './components/Recommendation'
import { TaxStructure, GrowthCalculator, ResidentialParadox } from './components/TaxBase'
import { CommercialTrend, HomeValueParadox } from './components/CommercialTrend'
import { BusinessFormation, BusinessCategories } from './components/BusinessFormation'
import { Conclusions } from './components/Conclusions'
import { PriorityImpact, ActiveRanking } from './components/PriorityImpact'
import { Derivations } from './components/Derivations'
import { GapPanel } from './components/GapPanel'

const NAV = [
  ['conclusions', 'What we found'],
  ['where-we-are', 'Where we are'],
  ['the-money', 'The money'],
  ['neighbors', 'Neighbors'],
  ['priorities', 'Priorities'],
  ['cut-line', 'Cut line'],
  ['years', 'Year by year'],
  ['fees', 'Fees'],
  ['levers', 'Close the gap'],
  ['tax-base', 'Business growth'],
  ['recommendation', 'What we’d do'],
  ['assumptions', 'Assumptions'],
  ['derivations', 'Show the math'],
  ['method', 'Sources'],
]

export default function App() {
  const [order, setOrder] = useState<string[]>(MODEL.presets.school_committee.order)
  const [preset, setPreset] = useState<string | null>('school_committee')
  const [a, setA] = useState<Assumptions>({ ...MODEL.assumptions })
  const [target, setTarget] = useState<number | null>(null)

  // Every lever lives here, not inside the workbench, so the athletics fee slider on the
  // Fees tab and the athletics lever in the workbench are the SAME control, and so the
  // floating panel can total them up. Levers start at "nothing changed" — today's fee,
  // today's cost split — so every dollar the panel shows is a dollar the reader chose.
  const [leverVals, setLeverVals] = useState<Record<string, number>>(
    () => Object.fromEntries(MODEL.levers.map(l => [l.id, leverStart(l)])))
  const [leverBasis, setLeverBasis] = useState<Record<string, number>>(
    () => Object.fromEntries(MODEL.levers.map(l => [l.id, l.basis])))

  // The health panel's "employee share" slider IS the health_design lever, expressed as a
  // fraction rather than a percentage. One control, two places to reach it.
  const empShare = (leverVals.health_design ?? 25) / 100
  const setEmpShare = (n: number) =>
    setLeverVals({ ...leverVals, health_design: Math.round(n * 100) })
  // Plan migration is a genuinely separate saving from the contribution split, and the
  // workbench has no lever for it, so it is tracked here and reported to the panel.
  const [movers, setMovers] = useState(0)
  const [migrationSaving, setMigrationSaving] = useState(0)

  // New growth: the tax-base calculator sets it, in dollars of new value per year. The
  // projection consumes it as levy revenue.
  const [newValue, setNewValue] = useState(MODEL.taxBase.currentNewGrowthValue)
  const newGrowthRevenue = (newValue * MODEL.taxBase.rate) / 1000

  const leverItems = useMemo<AppliedItem[]>(() => MODEL.levers.map(l => ({
    id: l.id,
    label: l.name,
    detail: l.isPercent || l.isPercentPoint
      ? `${leverVals[l.id]}%${l.isPercentPoint ? ' employee share' : ' reduction'}`
      : `${usd(leverVals[l.id] ?? 0)} — ${l.unit}`,
    amount: Math.round(leverYield(l, leverVals[l.id] ?? 0, leverBasis[l.id] ?? l.basis)),
    kind: 'lever' as const,
    anchor: 'levers',
  })).filter(i => i.amount > 0), [leverVals, leverBasis])

  const leverTotal = leverItems.reduce((s2, i) => s2 + i.amount, 0)

  // Levers are revenue and savings, so they shrink the hole the cascade has to cut for.
  // This is the connection between the two halves of the tool.
  const aEff = useMemo<Assumptions>(
    () => ({
      ...a,
      athletic_fee_revenue: a.athletic_fee_revenue + leverTotal + migrationSaving,
      new_growth: newGrowthRevenue,
    }),
    [a, leverTotal, migrationSaving, newGrowthRevenue])

  const athFee = leverVals.athletic_fees ?? MODEL.currentFees.effectiveAthletic
  const setAthFee = (n: number) => setLeverVals({ ...leverVals, athletic_fees: n })

  const years = useMemo(() => runCascade(order, aEff, 5), [order, aEff])
  const plain = useMemo(() => project(5, aEff), [aEff])
  const f = MODEL.facts
  const presetName = preset ? MODEL.presets[preset].name : null

  const ticks: Tick[] = useMemo(() => {
    let cum = 0
    return years.map(y => ({ fy: y.fy, cumulative: (cum += y.deficit) }))
  }, [years])
  const maxTarget = Math.max(ticks.at(-1)?.cumulative ?? 0, 3_600_000)

  // Seed the slider at the FY28 gap; `null` means "untouched", so 0 stays draggable.
  const fy28Gap = years[0].deficit
  const effectiveTarget = target ?? fy28Gap
  // The panel reports the gap BEFORE any lever is pulled, then shows the levers closing
  // it. `fy28Gap` is already net of them, so adding the total back gives the true hole.
  const grossGap = fy28Gap + leverTotal

  const growthDelta = Math.round(newGrowthRevenue - MODEL.taxBase.currentNewGrowthRevenue)

  const applied: AppliedItem[] = [
    ...leverItems,
    ...(migrationSaving > 0 ? [{
      id: 'health_migration', kind: 'lever' as const,
      label: 'Health insurance — plan migration',
      detail: `${movers} employees moved to a cheaper plan`,
      amount: Math.round(migrationSaving), anchor: 'levers',
    }] : []),
    ...(growthDelta !== 0 ? [{
      id: 'new_growth', kind: 'lever' as const,
      label: growthDelta > 0 ? 'Extra commercial growth' : 'Less growth than assumed',
      detail: `${usd(newValue)} of new value a year, vs `
        + `${usd(MODEL.taxBase.currentNewGrowthValue)} assumed`,
      amount: growthDelta, anchor: 'tax-base',
    }] : []),
    ...years[0].cuts.filter(c => !c.blocked).map(c => ({
      id: `cut-${c.id}`, label: c.name,
      detail: c.fte > 0 ? `${c.fte.toFixed(1)} FTE · ${MODEL.categories[c.cat]?.label ?? c.cat}`
        : MODEL.categories[c.cat]?.label ?? c.cat,
      amount: Math.round(c.cost), kind: 'cut' as const, anchor: 'priorities',
    })),
  ]

  /** Put one control back to today's actual, without disturbing anything else. */
  const resetItem = (id: string) => {
    if (id === 'new_growth') return setNewValue(MODEL.taxBase.currentNewGrowthValue)
    if (id === 'health_migration') { setMovers(0); return setMigrationSaving(0) }
    const lever = MODEL.levers.find(l => l.id === id)
    if (lever) {
      setLeverVals({ ...leverVals, [id]: leverStart(lever) })
      setLeverBasis({ ...leverBasis, [id]: lever.basis })
    }
  }

  const resetAll = () => {
    setLeverVals(Object.fromEntries(MODEL.levers.map(l => [l.id, leverStart(l)])))
    setLeverBasis(Object.fromEntries(MODEL.levers.map(l => [l.id, l.basis])))
    setA({ ...MODEL.assumptions })
    setMovers(0)
    setMigrationSaving(0)
    setNewValue(MODEL.taxBase.currentNewGrowthValue)
    setTarget(null)
    setOrder(MODEL.presets.school_committee.order)
    setPreset('school_committee')
  }

  return (
    <div>
      {/* ---------- header ---------- */}
      <header className="sticky top-0 z-20 backdrop-blur border-b"
        style={{ background: 'color-mix(in srgb, var(--surface-2) 88%, transparent)',
                 borderColor: 'var(--grid)' }}>
        <nav className="mx-auto max-w-6xl px-5 h-12 flex items-center gap-1 overflow-x-auto">
          <span className="font-bold text-sm mr-3 shrink-0">Lunenburg FY28</span>
          {NAV.map(([id, label]) => (
            <a key={id} href={`#${id}`}
              className="text-xs px-2.5 py-1 rounded-md whitespace-nowrap shrink-0 hover:opacity-100 opacity-70"
              style={{ color: 'var(--text-secondary)' }}>{label}</a>
          ))}
        </nav>
      </header>

      {/* ---------- hero ---------- */}
      <div className="mx-auto max-w-6xl px-5 pt-16 pb-12">
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
          toward 30, middle school sports and Grade&nbsp;5 band eliminated. This tool
          projects what FY28 and the years after look like &mdash; and lets you decide
          what should be protected.
        </p>

        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 mt-9">
          <Stat label="FY27 school budget" value={usd(f.stmAmount + MODEL.fy27.lps_appropriation)}
            sub={`Balanced budget (${usd(MODEL.fy27.lps_appropriation)}) plus `
              + `${usd(f.stmAmount)} a Special Town Meeting has yet to vote on 3 September`} />
          <Stat label="Projected FY28 gap" value={usd(fy28Gap)} tone="critical"
            sub="Cost of today's services minus revenue likely to be available" />
          <Stat label="Cutting every sport saves" value={usd(f.athleticsRemaining)}
            sub={`A further ${usd(f.athleticsAlreadyCut)} of athletics is already cut`} />
          <Stat label="Override vote, May 2026" value="33% yes" tone="critical"
            sub={`${f.overrideQ1.yes.toLocaleString()} for, ${f.overrideQ1.no.toLocaleString()} against`} />
        </div>
      </div>

      {/* ---------- conclusions ---------- */}
      <Section id="conclusions" eyebrow="The short version"
        title="What we found"
        lede={<>Six numbers, then {MODEL.conclusions.length} findings &mdash; from the
          published budgets, the town warrant, the Assessors&rsquo; own hearings, the Town
          Clerk&rsquo;s business records and five neighbouring districts. These are our
          conclusions, not the district&rsquo;s and not the town&rsquo;s. Every one links to
          the section that shows the arithmetic.</>}>
        <Conclusions />
      </Section>

      {/* ---------- where we are ---------- */}
      <Section id="where-we-are" eyebrow="The starting point" title="How Lunenburg got here"
        lede={<>The town put three budgets to voters: a balanced budget that fit available
          revenue, and two override tiers that would have restored services. Town Meeting
          adopted the balanced budget on 2 May. Both override questions failed at the ballot
          on 16 May.</>}>
        <div className="grid gap-4 md:grid-cols-2">
          <div className="card p-5">
            <h3 className="text-sm font-bold mb-4">The ballot, 16 May 2026</h3>
            {[f.overrideQ1, f.overrideQ2].map((q, i) => {
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
            in the cut lists below.
          </p>
        </div>
      </Section>

      {/* ---------- the money ---------- */}
      <Section id="the-money" eyebrow="Reality check"
        title="You cannot cut your way out of this with the extras"
        lede={<>The most common suggestion at any budget meeting is to cut sports, or arts,
          or &ldquo;administration.&rdquo; Here is what those things are actually worth
          against what the budget actually is.</>}>
        <Magnitude years={years} />

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
            <FrillsCheck gap={fy28Gap} />
            <Note>
              Comparable districts learned the same thing. When Easthampton&rsquo;s override
              failed, {usd(2_500_000)} of its {usd(2_700_000)} in cuts &mdash; 93% &mdash;
              had to come from personnel. There is no other place large enough.
            </Note>
          </div>
        </div>
      </Section>

      {/* ---------- neighbors ---------- */}
      <Section id="neighbors" eyebrow="Local comparison"
        title="Every district around us is squeezed. They chose differently."
        lede={<>Five neighbouring districts built FY27 budgets under the same pressures:
          health insurance up 8&ndash;14%, Chapter 70 aid up 1.5&ndash;2%, retirement
          assessments up around 10%. None of them escaped it. What separates them is
          what they decided to protect.</>}>
        <div className="grid gap-4 lg:grid-cols-2 mb-10">
          <div>
            <h3 className="text-sm font-bold mb-3">Budget growth, FY26 to FY27</h3>
            <PeerGrowth />
            <Note>
              Lunenburg&rsquo;s schools grew <strong>1.08%</strong> in a year when
              neighbouring districts grew 2.9% to 6.5% &mdash; and when everyone&rsquo;s
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

      {/* ---------- priorities ---------- */}
      <Section id="priorities" eyebrow="Your turn" title="What should be protected?"
        lede={<>Every budget is a ranking, whether or not anyone writes it down. Below is
          the ranking Lunenburg&rsquo;s School Committee revealed through its own four FY27
          budget scenarios &mdash; the order in which it gave things up. Ashburnham-Westminster
          ranked the same list almost upside down. Change it to yours.</>}>
        <PriorityBuilder order={order} setOrder={setOrder}
          preset={preset} setPreset={setPreset} />
        <PriorityImpact years={years} />
      </Section>

      {/* ---------- cut line ---------- */}
      <Section id="cut-line" eyebrow="The consequence" title="Where the cut line falls"
        lede={<>Drag the slider to set how big a hole has to be closed, or click a year
          marker. Everything below the line is gone. The order comes from the priorities
          you set above &mdash; so if you dislike this outcome, the fix is upstream.</>}>
        <ActiveRanking order={order} presetName={presetName} />
        <CutLine order={order} target={effectiveTarget} setTarget={setTarget}
          ticks={ticks} max={maxTarget} />
      </Section>

      {/* ---------- years ---------- */}
      <Section id="years" eyebrow="The trajectory" title="What each year takes"
        lede={<>Costs rise faster than Proposition 2&frac12; lets revenue rise. Unless
          something changes, the gap reopens every year &mdash; and every year the cut line
          moves further up your priority list.</>}>
        <ActiveRanking order={order} presetName={presetName} />
        <YearChart years={plain} />

        <h3 className="text-sm font-bold mt-10 mb-3">The year each thing is lost</h3>
        <Landmarks years={years} />
        <Note>
          Based on the priorities you set. Reorder them and these dates move.
        </Note>

        <h3 className="text-sm font-bold mt-10 mb-3">Year by year</h3>
        <Timeline years={years} />
      </Section>

      {/* ---------- fees ---------- */}
      <Section id="fees" eyebrow="The lever that is already half-pulled"
        title="Could athletics pay for itself?"
        lede={<>Lunenburg <strong>already charges, and just raised the fee</strong> &mdash;
          {' '}$400 for a first child this year, up from $250, plus $180 a year for the bus.
          Town Meeting passed only the Balanced budget, so the athletics that exists costs{' '}
          {usd(MODEL.athletics.adopted)}, not the {usd(MODEL.athletics.levelService)} it
          would take to run the full programme. Against the smaller number the fee nearly
          works &mdash; which is less a success than a measure of how much was cut.</>}>
        <CurrentFees />

        <h3 className="text-sm font-bold mt-8 mb-3">Raising the fee — and where it stops working</h3>
        <AthleticsFees fee={athFee} setFee={setAthFee} />

        <h3 className="text-sm font-bold mt-10 mb-3">What each sport actually costs</h3>
        <SportTable fee={athFee} />

        <h3 className="text-sm font-bold mt-10 mb-3">Where does the fee money actually go?</h3>
        <FeeAccounting />
      </Section>

      {/* ---------- levers ---------- */}
      <Section id="levers" eyebrow="Everything except cutting"
        title="Close the gap without touching a programme"
        lede={<>Fees, savings and efficiencies, each with what it is genuinely worth and
          what it genuinely costs. Move the sliders until the bar fills. Then read the
          catch under each one, because every one of these has a catch.</>}>
        <LeverWorkbench gap={fy28Gap} vals={leverVals} setVals={setLeverVals}
          basis={leverBasis} setBasis={setLeverBasis} />

        <h3 className="text-lg font-bold mt-12 mb-1">
          Health insurance, in what it costs an employee
        </h3>
        <p className="text-[13px] mb-4 max-w-3xl" style={{ color: 'var(--text-secondary)' }}>
          &ldquo;Reduce health insurance costs&rdquo; is the vaguest line in any budget
          conversation. Lunenburg publishes its actual premiums, so it does not have to be
          vague. Here is exactly who pays what, and what each change would do to a family&rsquo;s
          pay packet.
        </p>
        <HealthInsurance empShare={empShare} setEmpShare={setEmpShare}
          movers={movers} setMovers={setMovers} onSaving={setMigrationSaving} />
      </Section>

      {/* ---------- tax base / business growth ---------- */}
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

        <h3 className="text-lg font-bold mt-12 mb-1">How much development would it take?</h3>
        <p className="text-[13px] mb-4 max-w-3xl" style={{ color: 'var(--text-secondary)' }}>
          Set how much new commercial value the town adds each year and watch what it is
          worth, now and in ten years.
        </p>
        <GrowthCalculator gap={fy28Gap} newValue={newValue} setNewValue={setNewValue} />

        <h3 className="text-lg font-bold mt-12 mb-1">Why building houses makes it worse</h3>
        <p className="text-[13px] mb-4 max-w-3xl" style={{ color: 'var(--text-secondary)' }}>
          This is the part that surprises people. Under a single tax rate, a home and a
          business of equal value pay identical taxes &mdash; but only one of them sends
          children to school.
        </p>
        <ResidentialParadox />
      </Section>

      {/* ---------- recommendation ---------- */}
      <Section id="recommendation" eyebrow="Our answer"
        title="What we’d actually do"
        lede={<>Everything above is a tool for reaching your own conclusion. This is ours,
          with the reasoning exposed so you can disagree with it precisely.</>}>
        <Recommendation gap={fy28Gap}
          onApply={() => {
            setOrder(MODEL.presets.our_recommendation.order)
            setPreset('our_recommendation')
            document.getElementById('cut-line')?.scrollIntoView({ behavior: 'smooth' })
          }} />
      </Section>

      {/* ---------- assumptions ---------- */}
      <Section id="assumptions" eyebrow="Argue with it" title="Every assumption, exposed"
        lede={<>Nothing here is hidden. These are the growth rates the projection uses,
          defaulted to what the district and town published for FY27. If you think a number
          is wrong, change it and watch everything above update.</>}>
        <AssumptionsPanel a={a} setA={setA} leverTotal={leverTotal} />
      </Section>

      {/* ---------- derivations ---------- */}
      <Section id="derivations" eyebrow="Show the math"
        title="How every rolled-up number was calculated"
        lede={<>&ldquo;How did you get to a {usd(MODEL.athletics.levelService)} athletics
          budget?&rdquo; is a fair question, and it deserves an answer you can check rather
          than a number you have to trust. Every figure in this app that is a roll-up of
          several budget lines is rebuilt here from the district&rsquo;s own line-item
          budget &mdash; every line named, every total added back up, and the judgement
          calls stated out loud.</>}>
        <Derivations />
      </Section>

      {/* ---------- method ---------- */}
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
              <li>Every neighbouring district&rsquo;s figures &mdash; from that
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
                January 2027. Everything after FY27 here is modelled.</li>
              <li>Costs are grown from the FY27 adopted budget using the rates in the
                panel above &mdash; defaulted to the district&rsquo;s own FY27 assumptions.</li>
              <li>Revenue is grown using the town&rsquo;s published Proposition 2&frac12;
                formula, with the schools holding their current share.</li>
              <li>Programs marked <em>our estimate</em> &mdash; the AP catalogue, the high
                school music program, middle school electives &mdash; are costed by us. The
                district has not published a price for cutting them.</li>
              <li>The order of cuts is a model, not a plan. No one has decided any of this.</li>
            </ul>
          </div>
        </div>
        <Note>
          Built from public documents published by Lunenburg Public Schools and the Town of
          Lunenburg. Peer comparisons drawn from reporting on Easthampton,
          Bridgewater-Raynham, South Hadley, Groton-Dunstable, Winchester and Duxbury.
          This is an independent projection and is not affiliated with, endorsed by, or
          approved by the school district or the town.
        </Note>
      </Section>

      <GapPanel gap={grossGap} items={applied} unclosed={years[0].unclosed}
        fte={years[0].cuts.filter(c => !c.blocked).reduce((n, c) => n + c.fte, 0)}
        onReset={resetAll} onResetItem={resetItem} />

      <footer className="border-t py-10" style={{ borderColor: 'var(--grid)' }}>
        <div className="mx-auto max-w-6xl px-5 text-xs" style={{ color: 'var(--text-muted)' }}>
          Lunenburg FY28 budget projection &mdash; an independent tool for residents.
          Figures for FY27 and earlier are from published documents; FY28 onward are
          projections. Last updated August 2026.
        </div>
      </footer>
    </div>
  )
}

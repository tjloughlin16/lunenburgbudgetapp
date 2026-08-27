import { MODEL, usd, usdShort, COST_GROWTH_BLENDED } from '../model/engine'
import {
  ALL_CUTS, CUT_OPTIONS, DEFAULT_SCENARIO, DEFAULT_RATES, LEVY_CAP, PACKAGES, RATE_LINES,
  SHARE, STATE_AID, aidGrowthToSustain, ch70OnlyGrowth, buildRateToHold,
  developmentsFor, longRunTarget, newGrowthValueFor, run, longRunRevenueGrowth,
  overrideForYears, overrideOnAverageHome, salaryRateToBalance, workforceShrink,
  type RateYear, type Scenario,
} from '../model/rates'
import { DEVELOPMENT } from '../model/answers'
import { ALREADY_CUT, LEVEL_SERVICE } from '../model/walk'

/** The conclusions, before the working.
 *
 *  The walkthrough was eleven rooms deep before it said anything a reader could carry
 *  away, and the commonest piece of feedback on it was that there is a lot of it. That is
 *  a real complaint and it is not fixed by cutting material: the material is the reason
 *  anybody believes the conclusions. It is fixed by saying the conclusions first and
 *  demoting the eleven rooms to what they always were — the working, available to anybody
 *  who wants to check a number.
 *
 *  So this block is allowed exactly four claims, two pictures and one door out. Every
 *  figure in it is derived from the same model as the rooms below, and every card links to
 *  the room that shows its arithmetic, so nothing here can drift away from what it
 *  summarises. If you find yourself adding a fifth claim, it belongs in a room. */

const YEARS = 12
const pct = (x: number, d = 2) => `${(x * 100).toFixed(d)}%`

const BASE = run(YEARS, DEFAULT_SCENARIO)
const LONG_RUN = longRunRevenueGrowth(BASE)
const SALARY_AND_HEALTH = RATE_LINES
  .filter(l => l.key === 'salaries' || l.key === 'health')
  .reduce((s, l) => s + l.weight, 0)

/** Consecutive years funded from the start. The only score any of this is kept by. */
const fundedYears = (r: RateYear[]) => {
  const i = r.findIndex(y => y.gap > 0)
  return i === -1 ? r.length : i
}

/** The one combination that holds for ever while assuming nothing about the State House
 *  or a developer — same aid growth and same new growth as the do-nothing projection.
 *
 *  Chosen by its assumptions rather than by its name, so that editing the package list
 *  cannot silently leave this page illustrating a route that no longer exists. It is
 *  deliberately the hardest of the twelve to agree to; the gentler ones are all on the
 *  packages page, and the caption says so rather than pretending this is the only door. */
const RATES_ONLY = PACKAGES.find(p =>
  p.forEver
  && p.scenario.stateAidGrowth === DEFAULT_SCENARIO.stateAidGrowth
  && p.scenario.newGrowth === DEFAULT_SCENARIO.newGrowth)
  ?? PACKAGES[PACKAGES.length - 1]

const OVERRIDE = overrideForYears(2)

/** The route nobody proposes, because nobody has to.
 *
 *  Leave insurance where it is and the bargained increase where it is, and the salary line
 *  is whatever is left — which is not enough to employ the people currently in it. This is
 *  the default, it is already running, and it is the reason "do nothing" is not the
 *  painless option on a page about pain. */
const RESIDUAL = Math.max(salaryRateToBalance(DEFAULT_RATES, longRunTarget(DEFAULT_SCENARIO)), 0)
const DEFAULT_PRICE = workforceShrink(RESIDUAL, DEFAULT_RATES.salaries)

/** The cheapest ballot question among the combinations that actually hold — the figure
 *  that makes "shared, each share is small" concrete rather than consoling. */
const CHEAPEST = PACKAGES
  .filter(p => (p.firstYears.overrideTownwide ?? 0) > 1000)
  .reduce((a, b) => ((a.firstYears.overrideTownwide ?? 0)
    <= (b.firstYears.overrideTownwide ?? 0) ? a : b))

/** The commercial build rate that would hold the whole chart, and what it is made of.
 *
 *  Development belongs on this page for the same reason state aid does: it is the answer
 *  people reach for that asks nothing of anybody in the schools, and it is real money. It
 *  is also the one option that moves the OTHER line, which is why it earns a panel of its
 *  own rather than a sentence. `null` if no build rate holds, which the panel handles by
 *  not appearing. */
const BUILD_RATE = buildRateToHold(DEFAULT_RATES, YEARS)
const BUILD = BUILD_RATE === null ? null : {
  levy: BUILD_RATE,
  value: newGrowthValueFor(BUILD_RATE),
  developments: developmentsFor(BUILD_RATE),
  assumedValue: newGrowthValueFor(DEFAULT_SCENARIO.newGrowth),
  multiple: BUILD_RATE / DEFAULT_SCENARIO.newGrowth,
  shareOfExisting: newGrowthValueFor(BUILD_RATE) / DEVELOPMENT.existingBase,
  /** A flat dollar figure is a shrinking share of a growing town, so the rate that holds
   *  for twelve years is not the rate that holds for thirty. The gap between the two is
   *  the whole argument about why building has to accelerate rather than continue. */
  forThirty: buildRateToHold(DEFAULT_RATES, 30),
}

/** What Chapter 70 alone would have to do, if the answer came entirely from the state.
 *
 *  The rate is steep for a reason that is not obvious and is worth carrying: aid is under
 *  a quarter of what the town collects, so moving a quarter of the revenue enough to fix a
 *  4.93% cost rate means moving that quarter very hard. */
const AID_RATE = aidGrowthToSustain(DEFAULT_SCENARIO)
const CH70_RATE = AID_RATE === null ? null : ch70OnlyGrowth(AID_RATE)
/** Said as a multiple because a rate on its own is not shocking and this one should be.
 *  Derived rather than written down: "four times faster" was typed, and it is five. */
const CH70_MULTIPLE = CH70_RATE === null ? null
  : Math.round(CH70_RATE / STATE_AID.ch70Assumed)
const SPELLED = ['no', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight',
                 'nine', 'ten']

interface Panel {
  label: string; sub: string; kind: 'level' | 'slope' | 'revenue'; s: Scenario
  /** What this option costs somebody, in something other than a percentage. Every panel
   *  has one. A panel without one is a panel that reads as free, and none of them is. */
  price: string
}
const PANELS: Panel[] = [
  { label: 'Cut everything nameable', kind: 'level',
    sub: `Every sport, the band, the clubs, 60% of technology and every administrative `
      + `line the law allows — ${usdShort(ALL_CUTS)}, taken out at once`,
    price: `${CUT_OPTIONS.length} whole categories of the thing the schools are for, gone `
      + `at once. After them, only classroom positions are large enough to cut.`,
    s: { ...DEFAULT_SCENARIO, cut: ALL_CUTS } },
  { label: 'Pass one override', kind: 'level',
    sub: `${usd(OVERRIDE.levy)} on the ballot, written for the schools alone so they keep `
      + `every dollar — $${OVERRIDE.onAverageHome} a year on the average home`,
    price: `$${OVERRIDE.onAverageHome} a year on the average home, permanently — from a `
      + `town that has just refused two smaller questions.`,
    s: { ...DEFAULT_SCENARIO, overrideLevy: OVERRIDE.levy } },
  { label: 'Change what things grow at', kind: 'slope',
    sub: `Salary settlements at ${pct(RATES_ONLY.scenario.rates.salaries, 0)} and health `
      + `insurance at ${pct(RATES_ONLY.scenario.rates.health, 0)} instead of `
      + `${pct(RATE_LINES.find(l => l.key === 'health')!.rate, 0)}`,
    /* Said in a sentence rather than assembled from the board's two consequence notes,
     * which together ran longer than the panel they were labelling. The numbers behind
     * this — what a teacher's scale reaches, how few people are left on the broadest
     * plan — are in the room, which is where there is room for them. */
    price: `Pay that rises more slowly than prices, bargained rather than decided; and `
      + `plan changes families feel, until the cheaper plans run out and holding the rate `
      + `means higher deductibles.`,
    s: RATES_ONLY.scenario },
  ...(BUILD ? [{ label: 'Build commercial value', kind: 'revenue' as const,
    sub: `${usdShort(BUILD.value)} of new taxable commercial value every year — about `
      + `${BUILD.developments.toFixed(0)} developments a year, sustained, for ever`,
    price: `${BUILD.multiple.toFixed(1)}× what the town actually builds, and about `
      + `${pct(BUILD.shareOfExisting, 0)} of its entire existing commercial base — added `
      + `again every year, with the traffic and services that come with it.`,
    s: { ...DEFAULT_SCENARIO, newGrowth: BUILD.levy } }] : []),
]

export function Upshot({ onJump }: { onJump: (tab: 'solved') => void }) {
  const runs = PANELS.map(p => ({ ...p, r: run(YEARS, p.s) }))
  const lo = Math.min(...runs.flatMap(p => p.r.flatMap(y => [y.cost, y.revenue])),
                      ...BASE.map(y => y.revenue)) * 0.98
  const hi = Math.max(...runs.flatMap(p => p.r.map(y => y.cost)),
                      ...BASE.map(y => y.cost)) * 1.02

  return (
    <section id="short-version" className="border-t"
      style={{ borderColor: 'var(--grid)', background: 'var(--surface-1)' }}>
      <div className="mx-auto max-w-6xl px-5 py-12">
        <p className="text-xs font-semibold uppercase tracking-widest mb-3"
          style={{ color: 'var(--text-muted)' }}>The short version</p>
        <h2 className="text-2xl sm:text-4xl font-bold tracking-tight leading-[1.1] max-w-3xl">
          If you read nothing else
        </h2>
        <p className="mt-4 text-[16px] leading-relaxed max-w-2xl"
          style={{ color: 'var(--text-secondary)' }}>
          Six things and two pictures. Everything after this is the working &mdash; the
          same facts in the order somebody has to meet them, with every number derived
          where you can disagree with it. Each card below links to the step that shows its
          arithmetic, and says whether it is the town&rsquo;s published record or this
          model&rsquo;s.
        </p>

        <ol className="grid gap-3 sm:grid-cols-2 mt-8">
          {/* Short on purpose.
            *
            * These cards were three and four sentences each, which is a summary that has
            * to be read the way the thing it summarises does. A claim card owes the
            * reader the claim, the number and the door to the working — the qualifying
            * clauses belong behind that door, and every one of them is there. */}

          <Claim n={1} figure={usdShort(LEVEL_SERVICE.gap)} tone="critical"
            eyebrow="Projected" href="#where-the-town-is"
            head="Projections show a deficit next year, and in every year after it.">
            No FY{BASE[0].fy} budget exists yet. Run the district&rsquo;s own published growth
            rates forward one year &mdash; same staff, same{' '}
            {LEVEL_SERVICE.enrollment.toLocaleString()} children &mdash; and they produce a
            shortfall of {usd(LEVEL_SERVICE.gap)}. The year after: {usdShort(BASE[1].gap)}.
          </Claim>

          <Claim n={2} figure={`${ALREADY_CUT.fte} FTE`} tone="critical"
            eyebrow="On the record" href="#two-rates"
            head="The town has already cut deeply, and the projection reopens anyway.">
            The budget now in force cut {ALREADY_CUT.fte} positions and{' '}
            {usd(ALREADY_CUT.cost)} &mdash; four classroom teachers, an interventionist and
            a half, an assistant principal, a custodian. The gap above opens on top of
            that. Not a failure: see the next card.
          </Claim>

          <Claim n={3} figure={pct(COST_GROWTH_BLENDED)}
            figureNote={`against ${pct(LONG_RUN)} revenue`}
            tone="critical" eyebrow="Projected" href="#two-rates"
            head="It is a rate problem, not a bad year.">
            Proposition 2&frac12; caps what the town may collect. Nothing caps insurance.
            Two things compounding at different speeds pull apart for ever, and the
            distance grows on its own with nobody doing anything wrong.
          </Claim>

          <Claim n={4} figure={pct(SALARY_AND_HEALTH, 0)} eyebrow="On the record"
            href="#the-cuts"
            head="Only two lines can change the direction — and neither is a School Committee vote.">
            Salaries and health insurance are {pct(SALARY_AND_HEALTH, 0)} of the budget:
            one bargained with the unions, one bought by the Town. Sports, clubs and
            administrators are an amount, not a direction.
          </Claim>

          {/* The two questions that get asked in every room, answered where they are
            * asked. Neither state aid nor development is a missing option — both are
            * already inside the revenue line of every chart on this page, which is
            * exactly why they keep coming back. So each card says which line it is in
            * before it says anything else. */}
          <Claim n={5} figure={CH70_RATE === null ? usdShort(STATE_AID.total)
                                                  : pct(CH70_RATE, 1)}
            figureNote="Chapter 70, every year"
            tone="critical" eyebrow="Record and projection" href="#the-state-house"
            head={`State aid is already in these charts, and would have to grow `
              + `${CH70_MULTIPLE !== null && CH70_MULTIPLE < SPELLED.length
                    ? SPELLED[CH70_MULTIPLE] : CH70_MULTIPLE}`
              + ` times faster.`}>
            Chapter 70 and the rest are {usdShort(STATE_AID.total)} a year,{' '}
            {pct(STATE_AID.shareOfTownRevenue, 0)} of everything the town collects. It is
            not missing from the charts below &mdash; it is inside the orange line, growing
            at {pct(STATE_AID.ch70Assumed, 0)}.
            {CH70_RATE !== null && <> Worth asking the delegation for; not worth planning
              around.</>}
          </Claim>

          {BUILD && (
            <Claim n={6} figure={`${BUILD.multiple.toFixed(1)}×`}
              figureNote="today’s build rate, for ever"
              tone="critical" eyebrow="Record and projection" href="#commercial-development"
              head="Commercial development is real money and the wrong order of magnitude.">
              New building raises that same orange line, and the schools keep{' '}
              {(SHARE * 100).toFixed(0)}&cent; of each dollar. Holding the projection from
              that side alone takes {usdShort(BUILD.value)} of new value a year &mdash;{' '}
              {pct(BUILD.shareOfExisting, 0)} of the town&rsquo;s whole commercial base,
              added again every year.
            </Claim>
          )}
        </ol>

        <TheWedge />
        <LevelOrSlope panels={runs} lo={lo} hi={hi} />

        {/* The ending this page owes the reader.
          *
          * Everything above it is a route, and a list of routes read in sequence quietly
          * implies that one of them is the good one. None of them is. The honest version
          * has to say three things in order: every option costs somebody something; the
          * option of not choosing costs the most and is already being paid; and no single
          * lever is enough, which is the only piece of good news on the page — a price
          * split three ways is a third of a price. */}
        <div className="card p-5 sm:p-6 mt-8" style={{ borderColor: 'var(--status-warning)',
                                                       borderWidth: 2 }}>
          <p className="text-[11px] font-semibold uppercase tracking-widest mb-2"
            style={{ color: 'var(--text-muted)' }}>What all of it adds up to</p>
          <h3 className="text-[19px] sm:text-2xl font-bold tracking-tight leading-snug
                         max-w-3xl">
            There is no painless version, and there is no single one
          </h3>
          <p className="text-[15px] leading-relaxed mt-3 max-w-3xl">
            Every route above is paid for by somebody: a child who loses a season, a
            household that pays ${OVERRIDE.onAverageHome} more a year for ever, an employee
            whose scale rises more slowly than prices, a family on a leaner health plan, a
            town with {BUILD ? `${BUILD.developments.toFixed(0)} more developments a year`
                             : 'far more commercial building'} in it. None of that is an
            argument against any of them. It is the argument against waiting for the one
            that costs nothing, because there isn&rsquo;t one.
          </p>

          <div className="mt-4 pl-3.5 max-w-3xl"
            style={{ borderLeft: '2px solid var(--status-critical)' }}>
            <p className="text-[10px] font-bold uppercase tracking-widest mb-1"
              style={{ color: 'var(--status-critical)' }}>
              Including the option nobody proposes
            </p>
            <p className="text-[15px] leading-relaxed">
              <strong>Doing nothing has a price too, and the town is already paying
              it.</strong> Leave insurance rising at{' '}
              {pct(DEFAULT_RATES.health, 0)} and the bargained increase where it is, and
              what is left for the whole salary line is {pct(RESIDUAL)} a year &mdash; less
              than the agreement it already signed. The district meets the difference by
              employing fewer people: about{' '}
              <strong>{DEFAULT_PRICE.positionsPerYear.toFixed(1)} positions in the first
              year</strong>, and more every year after, which is{' '}
              {pct(DEFAULT_PRICE.after20, 0)} of the workforce over twenty. Nobody ever
              votes for that total. It arrives one unfilled post at a time.
            </p>
          </div>

          <p className="text-[15px] leading-relaxed mt-4 max-w-3xl">
            <strong>And no single lever does it.</strong> Every one of the{' '}
            {PACKAGES.length} combinations that actually keeps the gap shut moves at least
            two lines at once &mdash; which is the one piece of good news here, because a
            price split between two or three parties is a fraction of a price paid by one.
            The cheapest of them asks a ballot question of about{' '}
            {usd(overrideOnAverageHome(CHEAPEST.firstYears.overrideTownwide ?? 0))} a year
            on the average home, against the{' '}
            {usd(Math.round(MODEL.facts.tier1TaxIncrease as number))} the town turned down
            in May.
          </p>
          {/* Reading on is the ask, not clicking away.
            *
            * The filled button used to be "see what would fix it", which sends somebody
            * who has just been told there is no painless answer straight to a page of
            * priced combinations — before they have any reason to believe the pricing.
            * The summary earns its credibility from the rooms below it, so the primary
            * action is to go and read them; the answer keeps its place as the second
            * button, for the reader who already knows all this. */}
          <div className="flex flex-wrap gap-2 mt-5">
            <a href="#the-working"
              className="text-[13px] font-bold px-3.5 py-2.5 rounded-md"
              style={{ background: 'var(--text-primary)', color: 'var(--surface-1)' }}>
              Keep reading to see why &darr;
            </a>
            <button onClick={() => onJump('solved')}
              className="text-[13px] font-semibold px-3.5 py-2.5 rounded-md"
              style={{ background: 'var(--surface-3)', color: 'var(--text-primary)' }}>
              Or skip to what would fix it &rarr;
            </button>
          </div>
        </div>
      </div>
    </section>
  )
}

/* ------------------------------------------------------------------ */

/** One claim, with the thing it is a claim ABOUT said in the corner.
 *
 *  The eyebrow is not decoration. Two of these four cards are the town's published record
 *  and two are this model's arithmetic, and a reader who cannot tell which is which will
 *  either believe the projection too much or the record too little. */
function Claim({ n, figure, figureNote, head, href, tone, eyebrow, wide, children }: {
  n: number; figure: string; head: string; href: string; eyebrow?: string
  /** A second, smaller quantity the headline figure is only meaningful against. Kept out
   *  of `figure` because anything long enough to need two numbers cannot be set at
   *  headline size in a half-width card without running off the end of it. */
  figureNote?: string
  /** Runs the width of the grid. For the one claim that is about the other four. */
  wide?: boolean
  tone?: 'critical'; children: React.ReactNode
}) {
  return (
    <li className={wide ? 'sm:col-span-2' : undefined}>
      <a href={href} className="card p-5 h-full flex flex-col hover:opacity-90
                                transition-opacity">
        {/* Top-aligned and allowed to wrap. The label and the figure are each as long as
            their own content needs to be, and on a narrow card the eyebrow gives way
            first rather than the number being pushed over the edge. */}
        <div className="flex items-start justify-between gap-3 mb-2">
          <span className="text-[11px] font-bold tnum tracking-widest min-w-0
                           leading-relaxed"
            style={{ color: 'var(--text-muted)' }}>
            {String(n).padStart(2, '0')}
            {eyebrow && (
              <span className="ml-2 font-semibold uppercase tracking-widest">
                {eyebrow}
              </span>
            )}
          </span>
          <span className="shrink-0 text-right">
            <span className="block text-xl sm:text-2xl font-bold tnum leading-none"
              style={{ color: tone === 'critical' ? 'var(--status-critical)'
                                                  : 'var(--text-primary)' }}>{figure}</span>
            {figureNote && (
              <span className="block text-[11px] font-semibold tnum mt-1 leading-none"
                style={{ color: 'var(--text-muted)' }}>{figureNote}</span>
            )}
          </span>
        </div>
        <h3 className="text-[16px] font-bold leading-snug mb-2">{head}</h3>
        <p className="text-[13px] leading-relaxed flex-1"
          style={{ color: 'var(--text-secondary)' }}>{children}</p>
        <span className="text-[11px] font-semibold mt-3"
          style={{ color: 'var(--series-cost)' }}>See the working &rarr;</span>
      </a>
    </li>
  )
}

/* ---- picture one: the problem -------------------------------------------- */

/** The projection as one still image, with nothing to drag.
 *
 *  It is the same two series the board in step six draws, and deliberately so — somebody
 *  who scrolls that far should recognise the shape rather than meet a new one. What it
 *  drops is every control, both axes' clutter and the tooltip: a reader who has not yet
 *  agreed that there is a problem is not going to discover it by hovering. The two lines
 *  are labelled where they end, and the only two numbers on it are the gap at each end of
 *  the wedge. */
function TheWedge() {
  const w = 720, h = 300
  const m = { t: 26, r: 18, b: 10, l: 18 }
  const lo = Math.min(...BASE.map(y => y.revenue)) * 0.97
  const hi = Math.max(...BASE.map(y => y.cost)) * 1.03
  const n = BASE.length
  const x = (i: number) => m.l + (i / (n - 1)) * (w - m.l - m.r)
  const y = (v: number) => m.t + (1 - (v - lo) / (hi - lo)) * (h - m.t - m.b)
  const line = (get: (yr: RateYear) => number) =>
    BASE.map((yr, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(get(yr)).toFixed(1)}`).join(' ')
  /* Where the two series get named. Offset from each other so the two labels are never
   * on the same vertical, and kept clear of both ends. */
  const COST_LABEL_AT = Math.round((n - 1) * 0.62)
  const REV_LABEL_AT = Math.round((n - 1) * 0.24)
  /* Cost is above revenue in every year of this run, so the wedge is a simple ribbon and
   * needs no clipping. That stops being true the moment anything is cut, which is why the
   * three panels below draw lines and no fill. */
  const wedge = `${line(yr => yr.cost)} `
    + BASE.slice().reverse()
        .map((yr, i) => `L${x(n - 1 - i).toFixed(1)},${y(yr.revenue).toFixed(1)}`).join(' ')
    + ' Z'
  const last = BASE[n - 1]

  return (
    <figure className="mt-10 max-w-3xl">
      <figcaption className="mb-3">
        <p className="text-[11px] font-semibold uppercase tracking-widest"
          style={{ color: 'var(--text-muted)' }}>The problem, in one picture</p>
        <h3 className="text-[17px] sm:text-xl font-bold leading-snug mt-1">
          What the same schools cost, against what the town is allowed to raise
        </h3>
      </figcaption>
      <div className="card p-3 sm:p-4">
        <svg viewBox={`0 0 ${w} ${h}`} width="100%" style={{ height: 'auto' }}
          role="img" aria-label={`Two lines from FY${BASE[0].fy} to FY${last.fy}. The cost `
            + `of today's services starts at ${usd(BASE[0].cost)} and the revenue `
            + `available starts at ${usd(BASE[0].revenue)}, a shortfall of `
            + `${usd(BASE[0].gap)}. The lines never meet; by FY${last.fy} the shortfall is `
            + `${usd(last.gap)}.`}>
          <path d={wedge} fill="var(--status-critical)" opacity={0.11} />
          {[0, n - 1].map(i => (
            <line key={i} x1={x(i)} x2={x(i)} y1={y(BASE[i].revenue)} y2={y(BASE[i].cost)}
              stroke="var(--status-critical)" strokeWidth={1.5} strokeDasharray="3 3"
              vectorEffect="non-scaling-stroke" />
          ))}
          <path d={line(yr => yr.cost)} fill="none" stroke="var(--series-cost)"
            strokeWidth={2.5} strokeLinejoin="round" vectorEffect="non-scaling-stroke" />
          <path d={line(yr => yr.revenue)} fill="none" stroke="var(--series-revenue)"
            strokeWidth={2.5} strokeLinejoin="round" vectorEffect="non-scaling-stroke" />

          {/* Direct labels rather than a legend box, each on the side of its own line that
              the line is moving away from. Both series rise to the right, so text set
              above one and running rightward is overtaken by it a few years along — which
              is what happened when these sat at the ends. Above-and-leftward for the top
              line, below-and-rightward for the bottom one, and neither can be caught.

              They are drawn in viewBox units, so on a phone they come out at about six
              pixels. There they give way to the key below, which is HTML and does not
              scale with the drawing. */}
          <g className="hidden sm:inline">
            <text x={x(COST_LABEL_AT)} y={y(BASE[COST_LABEL_AT].cost) - 11} textAnchor="end"
              fontSize={13} fontWeight={700} fill="var(--text-primary)">
              Cost of today&rsquo;s services
            </text>
            <text x={x(REV_LABEL_AT)} y={y(BASE[REV_LABEL_AT].revenue) + 20}
              fontSize={13} fontWeight={700} fill="var(--text-primary)">
              Revenue the town may raise
            </text>
          </g>
        </svg>
        <div className="sm:hidden flex flex-wrap gap-x-4 gap-y-1 pt-1 text-[12px]"
          style={{ color: 'var(--text-secondary)' }}>
          <Key colour="var(--series-cost)" label="Cost of today’s services" />
          <Key colour="var(--series-revenue)" label="Revenue the town may raise" />
        </div>
        {/* The two figures live under the plot rather than in it.
          *
          * The wedge they measure is nine pixels tall at one end and most of the card at
          * the other, so there is nowhere inside the chart that fits both — and a figure
          * that has to be squeezed reads as decoration. Under the axis, aligned with the
          * dashed marker each one belongs to, they are unambiguous and cost the plot no
          * height at all. */}
        <div className="flex items-baseline justify-between gap-3 px-1 pt-1">
          {[BASE[0], last].map((yr, i) => (
            <p key={yr.fy} className={`text-[12px] leading-tight ${i ? 'text-right' : ''}`}>
              <span className="font-semibold tnum" style={{ color: 'var(--text-muted)' }}>
                FY{yr.fy}
              </span>{' '}
              <span className="font-bold tnum" style={{ color: 'var(--status-critical)' }}>
                {usdShort(yr.gap)} short
              </span>
            </p>
          ))}
        </div>
      </div>
      <p className="text-[13px] leading-relaxed mt-3"
        style={{ color: 'var(--text-secondary)' }}>
        Neither line is a plan. Both are the published growth rates run forward: the blue
        one is what today&rsquo;s staff, buses and buildings cost as they get a year older,
        and the orange one is everything the town is allowed to collect. The shaded wedge
        is the gap. The point is not the size of the number on the right &mdash; it is
        that the wedge never closes on its own, and nothing in the picture is anybody
        misbehaving.
      </p>
      {/* What the orange line is made of, said once, here.
        *
        * "Revenue" is the word this whole argument hides inside. A reader who thinks it
        * means property tax concludes the town is choosing not to fund the schools; a
        * reader who does not know state aid is already in there asks why nobody has tried
        * the State House. Naming the four parts and their shares costs three lines and
        * pre-empts both. */}
      <div className="card p-4 mt-3">
        <p className="text-[11px] font-semibold uppercase tracking-widest mb-2"
          style={{ color: 'var(--text-muted)' }}>
          What is inside the orange line
        </p>
        <ul className="text-[13px] leading-relaxed space-y-1.5"
          style={{ color: 'var(--text-secondary)' }}>
          <li>
            <strong style={{ color: 'var(--text-primary)' }}>The property tax levy</strong>,
            which Proposition 2&frac12; caps at {pct(LEVY_CAP, 1)} more each year, whoever
            is on the ballot.
          </li>
          <li>
            <strong style={{ color: 'var(--text-primary)' }}>New growth</strong> &mdash;
            tax on buildings that did not exist last year. The only revenue rate the town
            actually owns.
          </li>
          <li>
            <strong style={{ color: 'var(--text-primary)' }}>State aid</strong>, Chapter 70
            and the rest: {usdShort(STATE_AID.total)} a year,{' '}
            {pct(STATE_AID.shareOfTownRevenue, 0)} of the whole line, assumed here to grow
            at {pct(STATE_AID.ch70Assumed, 0)}. It is already counted. Increasing it moves
            the orange line up; it does not change its angle unless the increase repeats
            every year.
          </li>
          <li>
            <strong style={{ color: 'var(--text-primary)' }}>Local receipts</strong> &mdash;
            fees, permits, excise.
          </li>
        </ul>
      </div>
    </figure>
  )
}

/* ---- picture two: why the usual answers do not work ---------------------- */

/** The same chart three times, which is the only way the distinction is visible.
 *
 *  A level change drops the blue line and leaves its angle alone, so it climbs back to
 *  the orange one at the speed it was climbing before. A rate change moves the angle. That
 *  sentence is true, is the whole argument of this site, and convinces nobody — it is a
 *  claim about shapes, and shapes have to be seen. Three panels on one shared scale is the
 *  cheapest honest way to show it, and it is static on purpose: step six is where you get
 *  to do it yourself, and this is the poster that makes you want to. */
function LevelOrSlope({ panels, lo, hi }: {
  panels: (Panel & { r: RateYear[] })[]; lo: number; hi: number
}) {
  return (
    <figure className="mt-10">
      <figcaption className="mb-3 max-w-3xl">
        <p className="text-[11px] font-semibold uppercase tracking-widest"
          style={{ color: 'var(--text-muted)' }}>The nature of the fixes</p>
        {/* Not "…and changing a rate does not".
          *
          * That sentence has two readings and the wrong one arrives first: it parses as a
          * complaint about rate changes rather than as the second half of "buy a year".
          * A heading with a trap in it is a heading that gets quoted against you. */}
        <h3 className="text-[17px] sm:text-xl font-bold leading-snug mt-1">
          Four answers, what each one buys, and what each one costs
        </h3>
        <p className="text-[14px] leading-relaxed mt-2"
          style={{ color: 'var(--text-secondary)' }}>
          The same chart four times, on one scale. Cutting and an override drop the blue
          line and leave its angle alone, so it climbs back to the orange one at the speed
          it was climbing before. Changing a rate bends the blue line. Building lifts the
          orange one. The grey dashes are what costs do if nothing is done.
        </p>
      </figcaption>
      <div className="grid gap-3 sm:grid-cols-2">
        {panels.map(p => <PanelCard key={p.label} panel={p} lo={lo} hi={hi} />)}
      </div>
    </figure>
  )
}

function PanelCard({ panel, lo, hi }: {
  panel: Panel & { r: RateYear[] }; lo: number; hi: number
}) {
  const w = 360, h = 132
  const m = { t: 10, r: 10, b: 6, l: 10 }
  const r = panel.r
  const n = r.length
  const x = (i: number) => m.l + (i / (n - 1)) * (w - m.l - m.r)
  const y = (v: number) => m.t + (1 - (v - lo) / (hi - lo)) * (h - m.t - m.b)
  const line = (get: (yr: RateYear) => number) =>
    r.map((yr, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(get(yr)).toFixed(1)}`).join(' ')
  const funded = fundedYears(r)
  const reopens = funded > 0 && funded < n ? r[funded] : null

  return (
    <div className="card p-4 flex flex-col">
      <div className="flex items-baseline justify-between gap-2">
        <h4 className="text-[15px] font-bold leading-snug">{panel.label}</h4>
        <Kind kind={panel.kind} />
      </div>
      <p className="text-[12px] mt-1 mb-3 flex-1" style={{ color: 'var(--text-secondary)' }}>
        {panel.sub}
      </p>

      <svg viewBox={`0 0 ${w} ${h}`} width="100%" style={{ height: 'auto' }}
        role="img" aria-label={`${panel.label}: cost against revenue, FY${r[0].fy} to `
          + `FY${r[n - 1].fy}. ${reopens
              ? `Funded for ${funded} years, then short again from FY${reopens.fy}.`
              : funded === n ? 'Funded in every year shown.'
                : `Short in every year, starting with ${usd(r[0].gap)}.`}`}>
        {/* The do-nothing cost line, kept in every panel so that what each option moved is
            visible as a displacement rather than having to be remembered. */}
        <path d={BASE.map((yr, i) =>
          `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(yr.cost).toFixed(1)}`).join(' ')}
          fill="none" stroke="var(--axis)" strokeWidth={1.5} strokeDasharray="4 4"
          vectorEffect="non-scaling-stroke" />
        {reopens && (
          <line x1={x(funded)} x2={x(funded)} y1={m.t} y2={h - m.b}
            stroke="var(--status-critical)" strokeWidth={1.5} strokeDasharray="3 3"
              vectorEffect="non-scaling-stroke" />
        )}
        <path d={line(yr => yr.cost)} fill="none" stroke="var(--series-cost)"
          strokeWidth={2.5} strokeLinejoin="round" vectorEffect="non-scaling-stroke" />
        <path d={line(yr => yr.revenue)} fill="none" stroke="var(--series-revenue)"
          strokeWidth={2.5} strokeLinejoin="round" vectorEffect="non-scaling-stroke" />
      </svg>
      {/* Outside the drawing, because text inside a viewBox is drawn in the viewBox's
          units: the same label is six pixels tall in a three-across grid and twenty-two
          in a stacked one. Everything in these panels that is words is HTML. */}
      <div className="flex items-baseline justify-between text-[11px] tnum px-0.5"
        style={{ color: 'var(--text-muted)' }}>
        <span>FY{r[0].fy}</span><span>FY{r[n - 1].fy}</span>
      </div>

      {/* The site's own vocabulary for funded and not, so the three panels can be compared
          with the board in step six without translating. Never colour alone. */}
      <ol className="grid gap-0.5 mt-2"
        style={{ gridTemplateColumns: `repeat(${n}, minmax(0, 1fr))` }}
        aria-label="Whether each year is funded">
        {r.map(yr => {
          const short = yr.gap > 0
          return (
            <li key={yr.fy} className="rounded-sm text-center py-0.5"
              title={short ? `FY${yr.fy}: short by ${usd(yr.gap)}` : `FY${yr.fy}: funded`}
              style={{ background: short ? 'var(--status-critical)' : 'var(--status-good)',
                       color: '#fff' }}>
              <span className="block text-[8px] font-bold leading-none" aria-hidden="true">
                {short ? '✕' : '✓'}
              </span>
              <span className="sr-only">
                FY{yr.fy} {short ? `not funded, short by ${usd(yr.gap)}` : 'funded'}
              </span>
            </li>
          )
        })}
      </ol>

      {/* What it costs, on every panel without exception.
        *
        * The third panel used to end its description with "no cut, no ballot question",
        * which is true and reads as free — and a page whose argument is "there is no
        * painless version" cannot have a painless-looking panel on it. Every option here
        * is paid for by somebody, and the panel says who before it says how long it
        * holds. */}
      <p className="text-[11px] leading-relaxed mt-2 pl-2.5"
        style={{ borderLeft: '2px solid var(--status-warning)',
                 color: 'var(--text-secondary)' }}>
        <span className="block text-[9px] font-bold uppercase tracking-widest mb-0.5"
          style={{ color: 'var(--status-warning)' }}>What it costs</span>
        {panel.price}
      </p>

      <p className="text-[12px] mt-2 font-semibold leading-snug">
        {reopens
          ? <>
              <span style={{ color: 'var(--status-good)' }}>
                Funded for {funded} {funded === 1 ? 'year' : 'years'}
              </span>
              <span style={{ color: 'var(--text-secondary)' }}>
                , then widening again at the same rate it was widening before &mdash;{' '}
                {usdShort(r[n - 1].gap)} short by FY{r[n - 1].fy}.
              </span>
            </>
          : fundedYears(r) === n
            ? <span style={{ color: 'var(--status-good)' }}>
                Funded in all {n} years, and it never reopens.
              </span>
            : <span style={{ color: 'var(--status-critical)' }}>
                Short in every year, starting with {usdShort(r[0].gap)}.
              </span>}
      </p>
    </div>
  )
}

/** Which of the three things an option is. The badge is the point of the panel.
 *
 *  Level and slope are both about the cost line. Building is neither: it is the only
 *  option here that moves the revenue line instead, which is why it gets its own colour
 *  rather than being filed under one of the other two. */
function Kind({ kind }: { kind: 'level' | 'slope' | 'revenue' }) {
  const map = {
    level: { label: 'A level', bg: 'var(--surface-3)', fg: 'var(--text-secondary)' },
    slope: { label: 'A slope', bg: 'var(--series-cost)', fg: '#fff' },
    revenue: { label: 'The other line', bg: 'var(--series-revenue)', fg: '#fff' },
  }[kind]
  return (
    <span className="text-[9px] font-bold uppercase tracking-widest px-2 py-1 rounded
                     shrink-0 leading-none"
      style={{ background: map.bg, color: map.fg }}>
      {map.label}
    </span>
  )
}

/** One line of a chart, named where the drawing itself cannot carry the name. */
function Key({ colour, label }: { colour: string; label: string }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <span aria-hidden="true" className="inline-block w-4 h-[2px] shrink-0"
        style={{ background: colour }} />
      {label}
    </span>
  )
}

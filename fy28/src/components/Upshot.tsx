import { usd, usdShort, COST_GROWTH_BLENDED } from '../model/engine'
import {
  ALL_CUTS, DEFAULT_SCENARIO, LEVY_CAP, PACKAGES, RATE_LINES, STATE_AID,
  aidGrowthToSustain, ch70OnlyGrowth, run, longRunRevenueGrowth, overrideForYears,
  type RateYear, type Scenario,
} from '../model/rates'
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

interface Panel { label: string; sub: string; kind: 'level' | 'slope'; s: Scenario }
const PANELS: Panel[] = [
  { label: 'Cut everything nameable', kind: 'level',
    sub: `Every sport, the band, the clubs, 60% of technology and every administrative `
      + `line the law allows — ${usdShort(ALL_CUTS)}, taken out at once`,
    s: { ...DEFAULT_SCENARIO, cut: ALL_CUTS } },
  { label: 'Pass one override', kind: 'level',
    sub: `${usd(OVERRIDE.levy)} on the ballot, written for the schools alone so they keep `
      + `every dollar — $${OVERRIDE.onAverageHome} a year on the average home`,
    s: { ...DEFAULT_SCENARIO, overrideLevy: OVERRIDE.levy } },
  { label: 'Change what things grow at', kind: 'slope',
    sub: `Salary settlements at ${pct(RATES_ONLY.scenario.rates.salaries, 0)} and health `
      + `insurance at ${pct(RATES_ONLY.scenario.rates.health, 0)} instead of `
      + `${pct(RATE_LINES.find(l => l.key === 'health')!.rate, 0)} — no cut, no ballot `
      + `question`,
    s: RATES_ONLY.scenario },
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
          Five things and two pictures. Everything after this is the working &mdash; the
          same facts in the order somebody has to meet them, with every number derived
          where you can disagree with it. Each card below links to the step that shows its
          arithmetic, and says whether it is the town&rsquo;s published record or this
          model&rsquo;s.
        </p>

        <ol className="grid gap-3 sm:grid-cols-2 mt-8">
          {/* Said as a projection, not as news.
            *
            * This card read "Next year is short", which is a claim about a budget nobody
            * has written — the one thing this site cannot afford to sound like it is
            * announcing. The figure is unchanged and so is the arithmetic; what changed is
            * that the sentence now says whose claim it is. */}
          <Claim n={1} figure={usdShort(LEVEL_SERVICE.gap)} tone="critical"
            eyebrow="Projected" href="#where-the-town-is"
            head="Projections show a deficit next year, and in every year after it.">
            There is no FY28 budget. No committee has published a figure and no meeting has
            argued about one. Run the district&rsquo;s own published growth rates forward
            one year &mdash; same staff, same buses, same{' '}
            {LEVEL_SERVICE.enrollment.toLocaleString()} children &mdash; and they produce a
            shortfall of {usd(LEVEL_SERVICE.gap)}. On the same arithmetic the year after is
            {' '}{usdShort(BASE[1].gap)}, and it keeps widening from there.
          </Claim>

          <Claim n={2} figure={`${ALREADY_CUT.fte} FTE`} tone="critical"
            eyebrow="On the record" href="#two-rates"
            head="The town has already cut deeply, and the projection reopens anyway.">
            The budget Lunenburg is running on right now cut {ALREADY_CUT.fte} positions
            and {usd(ALREADY_CUT.cost)} &mdash; four classroom teachers, an
            interventionist and a half, an assistant principal, a custodian. That part is a
            matter of record. The gap above still opens on top of it, which is not somebody
            failing; it is the next card.
          </Claim>

          {/* Two rates, one of them small.
            *
            * This card's figure was "4.93% vs 2.87%" set at the same size as "82%", which
            * is three times the characters and could not shrink, so on a narrow card it
            * ran off the edge. The comparison is the point and is kept — the second rate
            * just stops pretending to be a headline number. */}
          <Claim n={3} figure={pct(COST_GROWTH_BLENDED)}
            figureNote={`against ${pct(LONG_RUN)} revenue`}
            tone="critical" eyebrow="Projected" href="#two-rates"
            head="It is a rate problem, not a bad year.">
            Costs compound at {pct(COST_GROWTH_BLENDED)} a year. Revenue settles
            at {pct(LONG_RUN)}, because Proposition 2&frac12; caps the town&rsquo;s
            increase at {pct(LEVY_CAP, 1)} and nothing caps insurance. Two things
            compounding at different speeds pull apart for ever, and the distance grows on
            its own whether or not anybody does anything wrong.
          </Claim>

          <Claim n={4} figure={pct(SALARY_AND_HEALTH, 0)} eyebrow="On the record"
            href="#the-cuts"
            head="Only two lines can change the direction — and neither is a School Committee vote.">
            Salaries and health insurance are {pct(SALARY_AND_HEALTH, 0)} of the budget.
            One is bargained with the unions three years at a time; the other is insurance
            the Town buys, not the school district. Everything the argument is usually
            about &mdash; sports, clubs, administrators &mdash; is an amount, not a
            direction.
          </Claim>

          {/* The question that gets asked in every room, answered where it is asked.
            *
            * State aid is not a missing option here — it is already inside the revenue
            * line of every chart on this page, which is exactly why nobody can see it and
            * why "what about the state" keeps coming back. So the card says which line it
            * is in before it says anything else, and the two pictures below inherit the
            * answer rather than needing their own. */}
          <Claim n={5} figure={CH70_RATE === null ? usdShort(STATE_AID.total)
                                                  : pct(CH70_RATE, 1)}
            tone="critical" eyebrow="Record and projection" wide href="#the-state-house"
            head={`State aid is already in these charts — it is a quarter of the revenue `
              + `line, and closing the gap from that side alone would take `
              + `${CH70_MULTIPLE !== null && CH70_MULTIPLE < SPELLED.length
                    ? SPELLED[CH70_MULTIPLE] : CH70_MULTIPLE}`
              + ` times the growth the formula is expected to deliver.`}>
            Chapter 70 and the rest of state aid are {usdShort(STATE_AID.total)} a year
            &mdash; {pct(STATE_AID.shareOfTownRevenue, 0)} of everything the town collects
            and {pct(STATE_AID.shareOfSchoolBudget, 0)} of the school budget. That money is
            not missing from the picture below: it is inside the orange line, growing at
            the {pct(STATE_AID.ch70Assumed, 0)} a year this projection assumes, in that
            chart and in all three of the small ones under it.
            {CH70_RATE !== null && <>
              {' '}For the answer to come from that side alone, Chapter 70 would have to
              grow <strong>{pct(CH70_RATE, 1)} every year, for ever</strong> &mdash;
              starting with {usd(Math.round(STATE_AID.chapter70 * CH70_RATE
                - STATE_AID.chapter70 * STATE_AID.ch70Assumed))} more next year than the
              formula is expected to send. Worth asking the delegation for. Not worth
              planning around.
            </>}
          </Claim>
        </ol>

        <TheWedge />
        <LevelOrSlope panels={runs} lo={lo} hi={hi} />

        <div className="card p-4 sm:p-5 mt-8 max-w-3xl">
          <p className="text-[17px] leading-snug font-medium">
            Two of those three are levels. One is a slope. Only the slope ends it &mdash;
            and there are <strong>{PACKAGES.length}</strong> priced combinations that do,
            for five years, ten, a generation, or permanently.
          </p>
          <div className="flex flex-wrap gap-2 mt-4">
            <button onClick={() => onJump('solved')}
              className="text-[13px] font-bold px-3 py-2 rounded-md"
              style={{ background: 'var(--text-primary)', color: 'var(--surface-1)' }}>
              See what would actually fix it &rarr;
            </button>
            <a href="#where-the-town-is"
              className="text-[13px] font-semibold px-3 py-2 rounded-md"
              style={{ background: 'var(--surface-3)', color: 'var(--text-primary)' }}>
              Or start the eleven steps &darr;
            </a>
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
        <h3 className="text-[17px] sm:text-xl font-bold leading-snug mt-1">
          Why cutting and overrides buy a year, and changing a rate does not
        </h3>
        <p className="text-[14px] leading-relaxed mt-2"
          style={{ color: 'var(--text-secondary)' }}>
          The same chart three times, drawn to the same scale. The first two are the things
          the town actually argues about: both drop the blue line and leave its angle
          exactly where it was, so it climbs back to the orange one at the speed it was
          climbing before. The third leaves the line where it is and changes the angle.
        </p>
        <p className="text-[14px] leading-relaxed mt-2"
          style={{ color: 'var(--text-secondary)' }}>
          The orange line is the same one as in the chart above, state aid included, in all
          three panels &mdash; none of these options touches it. The grey dashed line is
          what costs do if nothing is done, kept in every panel so you can see how far each
          option moved them.
        </p>
      </figcaption>
      <div className="grid gap-3 lg:grid-cols-3">
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

/** Which of the two things an option is. The badge is the point of the panel. */
function Kind({ kind }: { kind: 'level' | 'slope' }) {
  const level = kind === 'level'
  return (
    <span className="text-[9px] font-bold uppercase tracking-widest px-2 py-1 rounded
                     shrink-0 leading-none"
      style={{ background: level ? 'var(--surface-3)' : 'var(--series-cost)',
               color: level ? 'var(--text-secondary)' : '#fff' }}>
      {level ? 'A level' : 'A slope'}
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

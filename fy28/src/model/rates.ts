import { MODEL, newGrowthPerDollar, expand, usd, usdShort } from './engine'
import { ADMIN, EXTRACURRICULAR, HEALTH_LEVERS, CONTRACT } from './answers'

/** The rate problem, made adjustable.
 *
 *  Every other page in this tool moves amounts. This one moves rates, because the amounts
 *  were never the problem: the district's costs compound at 4.94% a year and the town's
 *  revenue compounds at about 3.05%, and two exponentials with different exponents
 *  diverge forever no matter what you subtract from one of them.
 *
 *  That is the sentence residents cannot get to from a budget document, and it is the
 *  reason "we cut $600,000 last year and the hole is bigger this year" sounds like
 *  incompetence rather than arithmetic. A cut is a LEVEL change: it drops the cost curve
 *  once and leaves its angle alone, so the curves resume diverging at exactly the rate
 *  they were diverging before. Only a change in a growth RATE changes the angle.
 *
 *  So the interface has to make one contrast physical: tick boxes that cut real, named,
 *  painful things and watch the slope refuse to move; then drag one rate and watch it
 *  bend. Nothing else on this site says that, and it is the whole answer. */

const A = MODEL.assumptions
const F = MODEL.fy27
const E = MODEL.expenseBase as Record<string, number>
const T = MODEL.taxBase

export const LEVY_CAP = 0.025
/** What the schools keep of a dollar added to the town's levy. */
export const SHARE = newGrowthPerDollar(A)

export type Bucket = 'salaries' | 'health' | 'transport' | 'sped_tuition' | 'utilities' | 'other'
export const BUCKETS: Bucket[] = ['salaries', 'health', 'transport', 'sped_tuition',
                                  'utilities', 'other']

const BASE: Record<Bucket, number> = {
  salaries: E.salaries + F.stm_addbacks,
  health: E.health, transport: E.transport, sped_tuition: E.sped_tuition,
  utilities: E.utilities, other: E.other,
}
const TOTAL = BUCKETS.reduce((s, k) => s + BASE[k], 0)

/** One line of the budget, with the two facts that decide how much it matters: how big a
 *  share of the budget it is, and how fast it grows. Neither on its own tells you
 *  anything — a huge line growing at the cap is harmless, and a small line growing at 9%
 *  is not. */
export interface RateLine {
  key: Bucket
  label: string
  /** Share of the budget. */
  weight: number
  amount: number
  /** What the projection assumes it grows at today. */
  rate: number
  /** Who actually sets this number. The answer is rarely the School Committee. */
  controlledBy: string
  /** Whether it can realistically be moved, said plainly. */
  leverage: string
  /** Points off the blended rate if this line alone were held to the levy cap. */
  swing: number
}

export const RATE_LINES: RateLine[] = ([
  ['salaries', 'Salaries',
   'Bargained with the unions, three years at a time',
   'The largest single lever, because two thirds of the budget moves with it. The current teachers’ agreement expires June 30, 2027 — inside the first year of this problem.'],
  ['health', 'Health insurance',
   'The Town buys the insurance, not the school district',
   'The highest-leverage line in the budget relative to its size. Plan design and the contribution split go through the Public Employee Committee under c.32B §§21-23; joining the state GIC is the other route. None of it is a School Committee vote.'],
  ['transport', 'Transportation',
   'Contracted, and exposed to fuel',
   'Movable at contract renewal, and by routing. Special education transport inside it is required by law and cannot be reduced by choice.'],
  ['sped_tuition', 'Out-of-district special education',
   'Set by state rates and by which children enroll',
   'Essentially not controllable. The district must place a child where the child’s plan requires. The state circuit breaker reimburses part of it, late.'],
  ['utilities', 'Utilities',
   'The market, and the weather',
   'Movable slowly, through efficiency work and procurement. Too small to matter much either way.'],
  ['other', 'Everything else',
   'The School Committee, mostly',
   'The only line the district genuinely controls — supplies, materials, technology, athletics, clubs. It is also the smallest and the slowest-growing, which is exactly why cutting it does not change the trajectory.'],
] as [Bucket, string, string, string][]).map(([key, label, controlledBy, leverage]) => ({
  key, label, controlledBy, leverage,
  weight: BASE[key] / TOTAL,
  amount: Math.round(BASE[key]),
  rate: A[key] as number,
  swing: (BASE[key] / TOTAL) * ((A[key] as number) - LEVY_CAP),
}))

export const DEFAULT_RATES = Object.fromEntries(
  BUCKETS.map(k => [k, A[k] as number])) as Record<Bucket, number>

/** The weighted average the whole problem turns on. */
export const blendedOf = (r: Record<Bucket, number>) =>
  BUCKETS.reduce((s, k) => s + (BASE[k] / TOTAL) * r[k], 0)

/** Equals COST_GROWTH_BLENDED from engine.ts by construction — same weights, same
 *  rates. Asserted rather than assumed in the parity check below. */
export const BASELINE_BLENDED = blendedOf(DEFAULT_RATES)

/* ---- named cuts, for the half of the board that deliberately does nothing ---- */

/** Real cuts, at their real sizes, so that watching the slope ignore them lands.
 *
 *  These are not strawmen — they are the things actually on the table at meetings, and
 *  every one of them hurts. That is the point: you can take all of them and the angle of
 *  the cost curve is exactly what it was. */
export interface CutOption { id: string; label: string; amount: number; sub: string }
export const CUT_OPTIONS: CutOption[] = [
  { id: 'athletics', label: 'Every remaining sport', amount: MODEL.facts.athleticsRemaining,
    sub: '25 sports, 691 student-seasons, every coach' },
  { id: 'extras', label: 'Band, chorus, clubs and art supplies',
    amount: Math.round(EXTRACURRICULAR.total - MODEL.facts.athleticsRemaining),
    sub: 'Everything left outside the classroom' },
  { id: 'tech', label: '60% of software, licenses and devices', amount: 383_205,
    sub: 'As deep as the technology line can go' },
  { id: 'admin', label: 'Every administrator and office line the law allows',
    amount: ADMIN.lawful, sub: `${ADMIN.lawfulCount} lines, ${ADMIN.lawfulFte} FTE` },
]
export const ALL_CUTS = CUT_OPTIONS.reduce((s, c) => s + c.amount, 0)

/* ---- the projection ------------------------------------------------------ */

export interface Scenario {
  rates: Record<Bucket, number>
  /** Sustained new growth per year, in levy dollars. The one revenue rate the town owns. */
  newGrowth: number
  /** A permanent reduction in what the district spends, adopted for FY28. A level. */
  cut: number
  /** A one-time Prop 2½ override: the levy base rises once, then grows at the cap. */
  overrideLevy: number
}

export const DEFAULT_SCENARIO: Scenario = {
  rates: { ...DEFAULT_RATES }, newGrowth: A.new_growth, cut: 0, overrideLevy: 0,
}

export interface RateYear {
  fy: number; cost: number; revenue: number; gap: number; revenueGrowth: number
}

/** The same projection the rest of the site runs on, opened up at the rates.
 *
 *  Reproduces engine.project() exactly at the default scenario — there is a test for that
 *  in `matchesEngine` below, because a teaching tool that quietly disagrees with the
 *  model it is teaching about is worse than no teaching tool.
 *
 *  Two things engine.project() cannot express are added. A one-time override raises the
 *  levy base permanently and hands the schools their share of it that year, which is what
 *  a ballot question actually does — engine's `override_amount` is added every single
 *  year, which is a different and much rarer thing. And a cut is applied to the salary
 *  base, matching runCascade, so the money saved never gets its raise either. */
export function run(years: number, s: Scenario): RateYear[] {
  const b: Record<Bucket, number> = { ...BASE }
  b.salaries -= s.cut

  let levy = F.levy_limit + s.overrideLevy
  let aid = F.state_aid
  let receipts = F.local_receipts
  let approp = F.lps_appropriation + F.stm_appropriation + SHARE * s.overrideLevy
  const wedge = F.levy_limit + F.excluded_debt + F.state_aid + F.local_receipts - F.omnibus
  let prev = F.omnibus + s.overrideLevy

  const out: RateYear[] = []
  for (let i = 0; i < years; i++) {
    levy = levy * (1 + A.levy_growth) + s.newGrowth
    aid *= 1 + A.state_aid_growth
    receipts *= 1 + A.local_receipts_growth
    const townAvailable = levy + F.excluded_debt + aid + receipts - wedge
    const growth = townAvailable / prev - 1
    prev = townAvailable

    approp = approp * (1 + growth) + A.override_amount
    const revenue = approp + A.athletic_fee_revenue
    for (const k of BUCKETS) b[k] *= 1 + s.rates[k]
    const cost = BUCKETS.reduce((sum, k) => sum + b[k], 0)

    out.push({ fy: 28 + i, cost: Math.round(cost), revenue: Math.round(revenue),
               gap: Math.round(cost - revenue), revenueGrowth: growth })
    }
  return out
}

/** The rate the town's spendable revenue actually grows at — the levy cap plus whatever
 *  new growth adds, less the drag from state aid and local receipts rising more slowly.
 *  This, not 2.5%, is the line a cost rate has to get under. */
export const revenueGrowthOf = (newGrowth: number) =>
  run(1, { ...DEFAULT_SCENARIO, newGrowth })[0].revenueGrowth

export const BASELINE_REVENUE_GROWTH = revenueGrowthOf(A.new_growth)

/** Three states, and the difference between them is the entire lesson.
 *
 *  `widening` is today: costs outrun revenue, so the gap grows every year and no
 *  one-time answer survives. `held` is the thing nobody explains — the rates are fixed,
 *  so the gap has STOPPED growing, and a single cut or a single override now closes it
 *  permanently instead of buying a year. `solved` is held, with the residual closed.
 *
 *  The order matters and is the point: fixing the rate is what makes a one-time fix work
 *  at all. Do it the other way round and you buy twelve months. */
export type Verdict = 'widening' | 'held' | 'solved'

export function verdictOf(years: RateYear[], blended: number): Verdict {
  if (blended > longRunRevenueGrowth(years) + 0.0002) return 'widening'
  return years.every(y => y.gap <= 0) ? 'solved' : 'held'
}

/** The revenue rate that actually has to be beaten — and it is not the one showing today.
 *
 *  New growth is modeled the way the town budgets it: a fixed number of dollars added to
 *  the levy each year, not a percentage. A fixed dollar amount is a shrinking share of a
 *  growing base, so its contribution decays — revenue growth starts at 3.05% and drifts
 *  back toward the 2.5% cap for as long as the build rate stays flat.
 *
 *  Which means the intuition that Proposition 2½ is the bar is right in the long run,
 *  and comparing a cost rate against today's 3.05% quietly flatters every scenario. The
 *  verdict uses the last year on the horizon instead. */
export const longRunRevenueGrowth = (years: RateYear[]) =>
  years[years.length - 1].revenueGrowth

/** What one more year of doing nothing adds to the hole. */
export const freshGap = (years: RateYear[]) =>
  years.map((y, i) => ({
    fy: y.fy,
    fresh: Math.round(i === 0 ? y.gap : y.gap - years[i - 1].gap * (1 + y.revenueGrowth)),
  }))

/** The override that would have to pass THIS year, every year, to stand still.
 *
 *  Residents hear "an override fixes it" and reasonably assume one ballot question. What
 *  the arithmetic asks for is a new one every spring, forever, each in levy dollars
 *  roughly twice the school gap because the schools keep only about half of a levy
 *  dollar. Printed as a tax bill because that is the form a voter meets it in. */
export const overrideTreadmill = (years: RateYear[]) =>
  freshGap(years).map(g => {
    const levy = g.fresh / SHARE
    return {
      fy: g.fy, schools: g.fresh, levy: Math.round(levy),
      onAverageHome: Math.round((T.avgHomeValue * ((levy * 1000) / T.totalValue)) / 1000),
    }
  })

/** Guard rail: at the default scenario this must reproduce engine.project() to the
 *  dollar, or the page is teaching a different model from the one it cites. */
export function matchesEngine(engineGaps: number[]): { ok: boolean; detail: string } {
  const mine = run(engineGaps.length, DEFAULT_SCENARIO).map(y => y.gap)
  const bad = mine.map((v, i) => [i, v, engineGaps[i]] as const)
    .filter(([, v, e]) => Math.abs(v - e) > 1)
  return {
    ok: !bad.length,
    detail: bad.length
      ? bad.map(([i, v, e]) => `FY${28 + i}: ${usd(v)} vs ${usd(e)}`).join('; ')
      : 'matches engine.project() exactly',
  }
}

/* ---- what a rate actually is, in the world ------------------------------- */

/** Average cost of one position, from this budget's own catalogue.
 *
 *  43 catalogued positions and 48.9 FTE at $4.36M — salary and benefits together, which
 *  is what a position actually costs the district. Used to turn an abstract percentage
 *  into people, because "hold salaries to 2½%" and "employ twenty fewer people" are the
 *  same sentence and only one of them is honest about what is being proposed. */
const POSITIONS = expand(MODEL.programs).filter(p => p.fte > 0)
export const COST_PER_FTE = Math.round(
  POSITIONS.reduce((s, p) => s + p.cost, 0) / POSITIONS.reduce((s, p) => s + p.fte, 0))

/** The year the consequences are quoted at. Six years out: far enough that compounding
 *  is visible, near enough that a person can picture still working here. */
export const HORIZON = 6

const grow = (x: number, r: number, n = HORIZON) => x * (1 + r) ** n

export interface Consequence {
  /** What the change is, in something other than a percentage. */
  text: string
  /** The part that makes it hard, or impossible. Rendered in warning colour. */
  limit?: string
}

/** Translate a rate into the thing a rate is made of.
 *
 *  Every one of these is a real trade and none of them is a dial. The section exists
 *  because a slider is a lie by omission: dragging salaries from 4% to 2½% takes half a
 *  second and represents either twenty people's jobs or a smaller raise for everybody who
 *  works in the schools, bargained, three years at a time. */
export function consequenceOf(key: Bucket, rate: number): Consequence | null {
  const base = BASE[key]
  const was = DEFAULT_RATES[key]
  if (Math.abs(rate - was) < 1e-9) return null
  const softer = rate < was
  /** How much bigger or smaller the line is by the horizon year. */
  const delta = Math.round(Math.abs(grow(base, was) - grow(base, rate)))
  const fy = 28 + HORIZON - 1

  switch (key) {
    case 'salaries': {
      const fte = delta / COST_PER_FTE
      const t = CONTRACT.samples[1]
      const payWas = Math.round(grow(t.pay, was))
      const payNow = Math.round(grow(t.pay, rate))
      return {
        text: softer
          // Not "paid less" — at any of these rates the scale still rises. It rises less
          // far, which is a different and much more defensible sentence, and stating it
          // the other way would be the sort of thing this site exists to correct.
          ? `By FY${fy} the salary line is ${usdShort(delta)} smaller — about `
            + `${fte.toFixed(0)} fewer positions at ${usd(COST_PER_FTE)} each, or the same `
            + `people on smaller raises: a ${t.label.toLowerCase()} teacher reaches `
            + `${usd(payNow)} by FY${fy} rather than ${usd(payWas)}, from `
            + `${usd(t.pay)} today.`
          : `By FY${fy} the salary line is ${usdShort(delta)} larger — about `
            + `${fte.toFixed(0)} more positions, or ${t.label.toLowerCase()} reaching `
            + `${usd(payNow)} instead of ${usd(payWas)}.`,
        limit: softer
          ? `Bargained, not decided. At ${pctOf(rate)} the scale still rises — it rises `
            + `more slowly than it did, which is close to flat once inflation is taken out.`
          : undefined,
      }
    }
    case 'health': {
      const perYear = Math.round(base * Math.abs(was - rate))
      const movers = perYear / HEALTH_LEVERS.migration.gross
      const onBroadest = HEALTH_LEVERS.migration.onBroadest
      const runsOut = onBroadest / movers
      if (!softer) return { text: `Premiums rising faster costs another ${usdShort(delta)} by FY${fy}.` }
      return {
        text: `Roughly ${movers.toFixed(0)} people moved off ${HEALTH_LEVERS.migration.from} `
          + `(${HEALTH_LEVERS.migration.fromNetwork.toLowerCase()}) onto `
          + `${HEALTH_LEVERS.migration.to} (${HEALTH_LEVERS.migration.toNetwork.toLowerCase()}) `
          + `— every year, not once.`,
        limit: `Only ${onBroadest} people are on the broadest plan, so that runs out in `
          + `about ${runsOut.toFixed(1)} years. After it does, holding the rate means `
          + `higher deductibles — the cheapest plan on offer is `
          + `${HEALTH_LEVERS.highDeductible} — or a different insurer. The Town buys the `
          + `insurance, not the school district.`,
      }
    }
    case 'sped_tuition':
      return {
        text: `Out-of-district tuition is ${usdShort(delta)} lower by FY${fy}.`,
        limit: 'Nobody in Lunenburg sets this. The district must place a child where the '
          + 'child’s plan requires, at state-approved tuition rates. Moving this slider is '
          + 'a forecast about who enrolls, not a decision anybody gets to make.',
      }
    case 'transport': {
      const genEd = MODEL.buckets.transportGenEd
      return {
        text: `${usdShort(delta)} less by FY${fy} — routes, contract terms, and how far `
          + `buses go.`,
        limit: `Only the ${usdShort(genEd)} of general-education transport is reachable. `
          + `The ${usdShort(MODEL.buckets.transportSpEd)} of special education transport `
          + `inside this line is required by law and cannot be reduced by choice.`,
      }
    }
    case 'utilities':
      return {
        text: `${usdShort(delta)} less by FY${fy}, through efficiency work and procurement.`,
        limit: 'Real, slow, and too small to change the answer either way.',
      }
    case 'other':
      return {
        text: `${usdShort(delta)} less by FY${fy} of supplies, materials, technology, `
          + `athletics and clubs.`,
        limit: 'This is the line the district has actually been cutting, and the only one '
          + 'it fully controls. It is also the smallest and slowest-growing, which is why '
          + 'cutting it does not change the direction of anything.',
      }
  }
}

const pctOf = (x: number) => `${(x * 100).toFixed(2)}%`

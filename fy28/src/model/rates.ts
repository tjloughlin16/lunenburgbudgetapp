import { MODEL, newGrowthPerDollar, expand, usd, usdShort } from './engine'
import { ADMIN, DEVELOPMENT_MIX, EXTRACURRICULAR, HEALTH_LEVERS,
         CONTRACT } from './answers'

/** The rate problem, made adjustable.
 *
 *  Every other page in this tool moves amounts. This one moves rates, because the amounts
 *  were never the problem: the district's costs compound at 4.94% a year and the town's
 *  revenue compounds at about 3.05%, and two exponentials with different exponents
 *  diverge forever no matter what you subtract from one of them.
 *
 *  That is the sentence residents cannot get to from a budget document, and it is the
 *  reason "we just cut and the hole is bigger next year" sounds like
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
  /** A one-time Prop 2½ override earmarked for the schools: the levy base rises once,
   *  the whole of it goes to the school department, and it then grows at the cap. */
  overrideLevy: number
  /** What state aid grows at. Normally an assumption; a lever in the state-aid section. */
  stateAidGrowth: number
  /** New user-fee revenue per year, above what the town already charges.
   *
   *  A level, like a cut, and a weaker one: a cut lands on the salary base so the money
   *  saved never gets its raise either, while a fee is a flat number of dollars that does
   *  not grow at all unless somebody raises it again. It is here because it is the one
   *  answer that asks nothing of the union, the Town or a developer — and because it has
   *  a hard ceiling, which is the thing worth knowing about it. */
  feeRevenue: number
}

export const DEFAULT_SCENARIO: Scenario = {
  rates: { ...DEFAULT_RATES }, newGrowth: A.new_growth, cut: 0, overrideLevy: 0,
  stateAidGrowth: A.state_aid_growth, feeRevenue: 0,
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

  let levy = F.levy_limit
  let aid = F.state_aid
  let receipts = F.local_receipts
  let approp = F.lps_appropriation + F.stm_appropriation
  const wedge = F.levy_limit + F.excluded_debt + F.state_aid + F.local_receipts - F.omnibus
  let prev = F.omnibus

  const out: RateYear[] = []
  for (let i = 0; i < years; i++) {
    levy = levy * (1 + A.levy_growth) + s.newGrowth
    aid *= 1 + s.stateAidGrowth
    receipts *= 1 + A.local_receipts_growth
    const townAvailable = levy + F.excluded_debt + aid + receipts - wedge
    const growth = townAvailable / prev - 1
    prev = townAvailable

    approp = approp * (1 + growth) + A.override_amount

    /* A school override is earmarked money that grows with the levy limit, not with the
     * town's blended revenue rate.
     *
     * It used to be folded into the appropriation, which grows at whatever the town's
     * revenue does — about 3.05% while new growth is propping that up. But an override
     * raises the LEVY LIMIT, and the levy limit rises 2½% a year; new growth is separate
     * dollars that do not attach to the override. Folding it in also quietly inflated the
     * town's growth rate, so the override was helping twice. Kept outside the base
     * projection now: the whole of it reaches the schools in the first year, because a
     * ballot question may be written for a single department, and it compounds at the cap
     * after that.
     *
     * It matters for exactly the question people ask about overrides — how many years does
     * one buy — and it was making the answer slightly too generous. */
    const override = s.overrideLevy * (1 + A.levy_growth) ** i
    const revenue = approp + override + A.athletic_fee_revenue + s.feeRevenue
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
    // School-only, so the ballot question is exactly what the schools need. The townwide
    // figure is carried alongside because it is the one Lunenburg actually voted on and
    // lost: a general override has to be nearly twice the size to do the same work here,
    // since the schools only take their share of it.
    const levy = g.fresh
    const townwide = g.fresh / SHARE
    return {
      fy: g.fy, schools: g.fresh, levy: Math.round(levy), townwide: Math.round(townwide),
      onAverageHome: Math.round((T.avgHomeValue * ((levy * 1000) / T.totalValue)) / 1000),
      townwideOnAverageHome:
        Math.round((T.avgHomeValue * ((townwide * 1000) / T.totalValue)) / 1000),
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

/** Roughly how many people the salary line pays, at the catalogue's own cost per
 *  position. An estimate, and labelled as one wherever it appears — the district does not
 *  publish a headcount, and salary lines cover part-time and stipended roles too. */
export const HEADCOUNT = Math.round(BASE.salaries / COST_PER_FTE)

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

/* ---- what "forever" actually requires ------------------------------------ */

/** Long enough that nothing temporary survives it. A rate fix that only holds for a
 *  decade is a slower version of the same problem. */
export const LONG = 30

/** The revenue rate a cost rate has to live under, measured far enough out that the
 *  decaying contribution of a flat new-growth figure has finished decaying. */
export const longRunTarget = (s: Scenario) =>
  longRunRevenueGrowth(run(LONG, s))

/** Does this hold forever, rather than for a while?
 *
 *  Two conditions, and they are different. The rate condition is what makes it permanent:
 *  costs must compound no faster than revenue, or the two pull apart again eventually no
 *  matter how good the starting position is. The level condition is whether there is
 *  still a hole once the rates are right. */
export function stability(s: Scenario) {
  const y = run(LONG, s)
  const blended = blendedOf(s.rates)
  const target = longRunRevenueGrowth(y)
  return {
    blended, target,
    rateOk: blended <= target + 0.0002,
    /** The worst year in three decades — what a one-time fix would have to cover. */
    worst: Math.round(Math.max(...y.map(x => x.gap))),
    finalGap: y[y.length - 1].gap,
    years: y,
  }
}

/** The salary rate that balances the blend, given what every other line is doing.
 *
 *  Salaries are solved for rather than chosen because they are two thirds of the budget:
 *  whatever the other lines do, this is the number that has to absorb it. Returns a
 *  negative rate when no salary rate can balance — which is itself the answer. */
export function salaryRateToBalance(rates: Record<Bucket, number>, target: number): number {
  const wSal = BASE.salaries / TOTAL
  const others = BUCKETS.filter(k => k !== 'salaries')
    .reduce((s, k) => s + (BASE[k] / TOTAL) * rates[k], 0)
  return (target - others) / wSal
}

/** Holding the salary LINE below the rate the contract pays means employing fewer people.
 *
 *  The two are not alternatives, they are the same equation read from either end. If
 *  everyone still gets the bargained increase, the only way the line grows more slowly is
 *  that there are fewer of them each year — and it compounds, which is why this is the
 *  question that decides whether "hold salaries to 2½%" is a policy or a fantasy. */
export function workforceShrink(lineRate: number, contractRate: number) {
  const perYear = (1 + contractRate) / (1 + lineRate) - 1
  const after = (n: number) => 1 - ((1 + lineRate) / (1 + contractRate)) ** n
  return {
    perYear,
    positionsPerYear: (BASE.salaries * perYear) / COST_PER_FTE,
    after10: after(10), after20: after(20), after30: after(30),
  }
}

/** What the state would have to do instead.
 *
 *  Chapter 70 is the one number in this budget that could fix the rate without anybody in
 *  Lunenburg giving anything up, so it deserves a figure rather than a wish. Bisects for
 *  the aid growth rate at which the projection never falls behind, holding everything
 *  else at today's assumptions. Returns null when no rate inside a sane range does it. */
export function aidGrowthToSustain(s: Scenario): number | null {
  let lo = s.stateAidGrowth, hi = 0.30
  if (stability({ ...s, stateAidGrowth: hi }).finalGap > 0) return null
  for (let i = 0; i < 60; i++) {
    const mid = (lo + hi) / 2
    const st = stability({ ...s, stateAidGrowth: mid })
    if (st.rateOk && st.finalGap <= 0) hi = mid; else lo = mid
  }
  return hi
}

/** The extra state money that rate implies, year by year, against what today's assumption
 *  delivers. A rate is not a number anybody can lobby for; a dollar figure is. */
export function aidSchedule(s: Scenario, rate: number, years = 10) {
  let atRate = F.state_aid, atBase = F.state_aid
  const out: { fy: number; atRate: number; atBase: number; extra: number }[] = []
  for (let i = 0; i < years; i++) {
    atRate *= 1 + rate
    atBase *= 1 + s.stateAidGrowth
    out.push({ fy: 28 + i, atRate: Math.round(atRate), atBase: Math.round(atBase),
               extra: Math.round(atRate - atBase) })
  }
  return out
}

/** If the whole increase had to come from Chapter 70 alone.
 *
 *  The projection carries one state aid line — the cherry sheet total — and grows it as a
 *  unit, so `aidGrowthToSustain` is a rate on ALL state aid. Chapter 70 is 79% of that,
 *  and the rest (charter reimbursement, transport, lottery) is not school money the state
 *  would move for this reason. So the rate anybody would actually have to lobby for is
 *  higher than the headline one, and this is it: the constant Chapter 70 growth that
 *  delivers the same total, with everything else held at the assumed rate. Binding in the
 *  first year and easier after, so the maximum across the horizon is the honest figure. */
export function ch70OnlyGrowth(totalRate: number, baseRate = A.state_aid_growth): number {
  const other = F.state_aid - T.ch70.aid
  let g = 0
  for (let n = 1; n <= LONG; n++) {
    const need = F.state_aid * (1 + totalRate) ** n - other * (1 + baseRate) ** n
    if (need > 0) g = Math.max(g, (need / T.ch70.aid) ** (1 / n) - 1)
  }
  return g
}

/** State aid today, for scale. */
export const STATE_AID = {
  /** The cherry sheet total — what the projection actually grows. */
  total: F.state_aid,
  /** The school part of it. Named separately because the two get conflated constantly. */
  chapter70: T.ch70.aid,
  other: F.state_aid - T.ch70.aid,
  ch70Share: T.ch70.aid / F.state_aid,
  shareOfTownRevenue: F.state_aid / F.omnibus,
  shareOfSchoolBudget: T.ch70.aid / F.lps_appropriation,
  /** What the projection assumes Chapter 70 grows at — the same rate it grows the whole
   *  cherry sheet at, since it carries state aid as one line. The comparison point for any
   *  package that asks the State House for more. */
  ch70Assumed: A.state_aid_growth,
  foundationBudget: T.ch70.foundationBudget,
  aboveFoundation: F.lps_appropriation - T.ch70.foundationBudget,
}

/* ---- what it takes, priced ------------------------------------------------ */

/** The rate a cost curve has to get under to be safe *for ever*, as opposed to for a
 *  generation.
 *
 *  `longRunTarget` measures revenue growth at year thirty, and at year thirty a flat
 *  new-growth figure has not finished decaying — so 2.69% is the honest bar for a
 *  lifetime and a generous one for eternity. Push the same projection out far enough and
 *  the levy dominates everything else, state aid and local receipts shrink to nothing as
 *  a share of it, and revenue growth converges on the one number nobody can vote away:
 *  Proposition 2½ itself.
 *
 *  So there are two bars, and a route can clear one and fail the other. That is not
 *  pedantry — it is the difference between "we stop cutting for thirty years" and "we
 *  stop cutting", and it is what decides whether development is a solution or a reprieve. */
export const FOREVER_BAR = LEVY_CAP

/** Long enough that an option which merely defers the problem is seen deferring it.
 *  Thirty years is the bar; sixty is the clock. Exported so the board and the arithmetic
 *  cannot quietly disagree about what "for ever" was tested against. */
export const ROUTE_CLOCK = 60

/** The gap in the first year if nothing is done — the hole the town is arguing about
 *  right now, and the yardstick for how long a route buys. A route that puts the gap back
 *  to this size in FY29 has bought one year. */
export const TODAY_GAP = run(1, DEFAULT_SCENARIO)[0].gap

/** Doing nothing, for the whole clock. Every lever is worth what it takes off this. */
const BASELINE_YEARS = run(ROUTE_CLOCK, DEFAULT_SCENARIO)
/** The window a resident can actually picture, and the one the rest of the site uses. */
const DECADE = 10

/** What moving one line is worth, even when it does not close anything.
 *
 *  Insurance at 4% takes sixteen million dollars out of the next ten years and never
 *  shuts the gap for a single April, and a page that scores it only on whether the gap
 *  shut reports the most valuable uncontested move available as worth nothing. Both facts
 *  belong to it. */
export function decadeWorth(rates: Record<Bucket, number>) {
  const years = run(DECADE, { ...DEFAULT_SCENARIO, rates })
  const removed = BASELINE_YEARS.slice(0, DECADE)
    .reduce((sum, b, i) => sum + (b.gap - years[i].gap), 0)
  return {
    removed,
    firstYear: BASELINE_YEARS[0].gap - years[0].gap,
    gapAtDecade: years[DECADE - 1].gap,
    baselineAtDecade: BASELINE_YEARS[DECADE - 1].gap,
    smallerBy: 1 - years[DECADE - 1].gap / BASELINE_YEARS[DECADE - 1].gap,
  }
}

/** New growth expressed as buildings rather than as levy dollars.
 *
 *  A build rate quoted in levy dollars is unfalsifiable to a resident; quoted in
 *  developments a year it can be argued with, which is the point. Uses the same $3.005M
 *  mixed archetype the development page uses, so the two can never disagree. */
const MIX_VALUE = T.archetypes.find(a => a.id === 'mix')?.value ?? T.mixValue
/** Assessed value behind a figure of new growth, which is the unit the budget builder
 *  and the development page both hold their build rate in. */
export const newGrowthValueFor = (levyDollars: number) => (levyDollars * 1000) / T.rate
export const developmentsFor = (levyDollars: number) =>
  newGrowthValueFor(levyDollars) / MIX_VALUE

/** The smallest flat build rate that keeps the gap shut for the whole thirty years, with
 *  every cost rate left exactly where it is. The honest price of the answer everybody
 *  reaches for first. */
export function buildRateToHold(rates = DEFAULT_RATES, years = LONG): number | null {
  let lo = 0, hi = 30_000_000
  const holds = (ng: number) =>
    run(years, { ...DEFAULT_SCENARIO, newGrowth: ng, rates }).every(y => y.gap <= 0)
  if (!holds(hi)) return null
  for (let i = 0; i < 60; i++) {
    const mid = (lo + hi) / 2
    if (holds(mid)) hi = mid; else lo = mid
  }
  return hi
}

/** Whether insurance is optional, answered rather than asserted.
 *
 *  "Insurance alone is never enough" is true and gets heard as "insurance is a sideshow",
 *  which is the opposite of true. Both halves need the same treatment: five points off a
 *  seventh of the budget is three quarters of a point off a blend that has to come down
 *  two and a quarter, so it cannot finish the job — and every arrangement that skips it
 *  has to buy those three quarters of a point from somebody else, at a price this prices.
 *
 *  Strictly, no: a town that held its settlement to 1.3% for ever would get there with
 *  insurance untouched. The claim that survives being argued with is narrower and
 *  stronger — skipping it costs roughly five times as much building, or a point off
 *  everybody's pay, for the identical outcome. */
export function insuranceLeverage(rate: number) {
  const capped = { ...DEFAULT_RATES, health: rate, transport: LEVY_CAP,
                   sped_tuition: LEVY_CAP, utilities: LEVY_CAP, other: LEVY_CAP }
  const target = longRunTarget(DEFAULT_SCENARIO)
  const salary = salaryRateToBalance(capped, target)
  /** The other way to hold the same line: same contract, fewer people on it. */
  const shrink = workforceShrink(Math.max(salary, 0), DEFAULT_RATES.salaries)
  /** And the third: settle at the cap and buy the difference in development. */
  const build = buildRateToHold({ ...capped, salaries: LEVY_CAP })
  return {
    rate, salary, positionsPerYear: shrink.positionsPerYear,
    blendedAtCap: blendedOf({ ...capped, salaries: LEVY_CAP }),
    build,
    buildings: build === null ? null : buildScale(build).buildingsPerYear,
  }
}

/** Today's rate and the one a serious plan-design or insurer change might reach. */
export const INSURANCE_CASE = [DEFAULT_RATES.health, 0.04].map(insuranceLeverage)

/** Which lines can be left out of the answer, tested rather than asserted.
 *
 *  "Insurance alone is never enough" and "the settlement alone is never enough" are both
 *  true, and a reader who hears only that concludes neither is where the answer lives.
 *  The opposite is the case, and the test that shows it is the one nobody runs: leave the
 *  line exactly where it is, pin every other line in the budget to the levy cap, and see
 *  whether anything reaches.
 *
 *  For salaries the answer is arithmetic rather than judgement. The line is two thirds of
 *  the budget, so at a 4% settlement it consumes the whole of the revenue rate on its own
 *  — every other line would have to grow at nothing at all, for ever, and the town would
 *  still start the period behind. There is no arrangement of the other five that reaches
 *  the bar. For insurance the answer is softer and still decisive: it can be skipped, at
 *  roughly five times the building. */
export const CANNOT_SKIP = (() => {
  const bar = longRunTarget(DEFAULT_SCENARIO)
  const others = (key: Bucket, r: number) => Object.fromEntries(
    BUCKETS.map(k => [k, k === key ? DEFAULT_RATES[k] : r])) as Record<Bucket, number>

  const line = (key: Bucket) => {
    const l = RATE_LINES.find(x => x.key === key)!
    const othersAtCap = others(key, LEVY_CAP)
    const build = buildRateToHold(othersAtCap)
    return {
      key, label: l.label, weight: l.weight, rate: l.rate,
      /** What this line alone takes out of the revenue rate, before anything else is
       *  bought. Above the bar means nothing else in the budget may grow at all. */
      consumes: l.weight * l.rate,
      /** The best the other five can do while this one is left alone. */
      blendedOthersAtCap: blendedOf(othersAtCap),
      /** And if they were frozen outright, which nobody is proposing. */
      blendedOthersFrozen: blendedOf(others(key, 0)),
      /** What it would take in development to hold anyway, with the others at the cap. */
      buildIfOthersAtCap: build,
      buildingsIfOthersAtCap: build === null ? null : buildScale(build).buildingsPerYear,
    }
  }
  return { bar, salaries: line('salaries'), health: line('health') }
})()

/** What a build rate is, in buildings and against what the town has actually managed.
 *
 *  Every option that leans on development quotes its ask in levy dollars, which is the
 *  right unit for a budget and a useless one for judging whether it could happen. The
 *  same figure in developments a year, against the best year the town has ever had and
 *  against the whole commercial base it has accumulated since it was founded, is what
 *  makes an ask arguable — and in one case here, what makes it obviously impossible.
 *
 *  Uses the development page's own archetype and its own history, so the two pages cannot
 *  end up quoting different sizes for the same building. */
export function buildScale(newGrowth: number) {
  const best = (T.newGrowthHistory as { fy: number; amount: number }[])
    .reduce((a, b) => (b.amount > a.amount ? b : a))
  const developments = developmentsFor(newGrowth)
  const value = newGrowthValueFor(newGrowth)
  /* "81 developments a year" is a number without a unit — a reader cannot tell whether
   * that is a strip mall or a shed, and the answer changes the argument completely. The
   * development page makes exactly this point and then unpacks the archetype into real
   * buildings; the same unpacking belongs here, because this is where somebody decides
   * whether an option is possible. Same mix, same archetype values, one source. */
  const each = DEVELOPMENT_MIX.map(m => {
    const arch = T.archetypes.find(a => a.id === m.id)!
    const perYear = (value * m.share) / arch.value
    return { label: arch.name, short: m.label, unit: arch.value, perYear,
             overFive: Math.round(perYear * 5) }
  }).sort((a, b) => b.perYear - a.perYear)
  /** A "development" is $3.0M of mixed value, which is more than one building — so the
   *  building count is roughly 1.7× the development count, and printing the two side by
   *  side without saying so reads as an arithmetic error. */
  const buildingsPerYear = each.reduce((n, e) => n + e.perYear, 0)
  return {
    each, buildingsPerYear,
    /** The buildings, counted rather than estimated: the archetype total rounds, so the
     *  five-year figure is the sum of the rounded types rather than a rounded sum. */
    buildingsInFive: each.reduce((n, e) => n + e.overFive, 0),
    newGrowth,
    extra: newGrowth - DEFAULT_SCENARIO.newGrowth,
    timesToday: newGrowth / DEFAULT_SCENARIO.newGrowth,
    timesBest: newGrowth / best.amount,
    bestFy: best.fy, bestAmount: best.amount,
    developments,
    extraDevelopments: developmentsFor(newGrowth - DEFAULT_SCENARIO.newGrowth),
    /** One new building every this many days, without stopping. Buildings rather than
     *  developments, because a building is the thing somebody watches go up. */
    everyDays: Math.max(1, Math.round(365 / buildingsPerYear)),
    valuePerYear: value,
    /** Everything commercial, industrial and personal the town has, accumulated over its
     *  entire history. The thing an annual figure has to be read against. */
    existingBase: T.fy23.cipValue,
    existingCount: T.businesses,
  }
}

/* ---- the combinations that hold, priced ---------------------------------- */

/** How long a package keeps the gap shut. Not a verdict — a horizon somebody chooses.
 *
 *  A five-year answer is not a failed thirty-year answer. It is a smaller ask, bought
 *  with a smaller settlement concession and a smaller cheque, and a town that wants ten
 *  quiet years to negotiate in is entitled to know exactly what ten costs. */
export type Horizon = 5 | 10 | 30 | typeof ROUTE_CLOCK

/** The three interchangeable ways to cover the early years.
 *
 *  Fixing the rates stops the gap growing; it does not refund the year the town is
 *  already behind in. Something has to cover that, and there are exactly three somethings
 *  — cut once, pass one override, or build. They are alternatives rather than a list: any
 *  one of them does it, and printing all three is the difference between a plan and a
 *  demand. Null means no amount of that kind would do it. */
export interface FirstYears {
  /** A permanent reduction adopted once. It compounds with the salary line thereafter,
   *  which is why it stays closed instead of buying twelve months. */
  cut: number | null
  /** A school-only override, and the townwide question that delivers it — the schools
   *  keep only their share of a general one. */
  override: number | null
  overrideTownwide: number | null
  /** Or no cheque at all, and a build rate instead. */
  build: number | null
  buildings: number | null
  /** Or user fees, which have a ceiling — null where no reachable fee level does it. */
  fees: number | null
  /** How much of everything the three fees could ever raise this would use up. */
  feeShareOfCeiling: number | null
}

const holdsWith = (rates: Record<Bucket, number>, years: number,
                   over: Partial<Scenario>, stateAidGrowth = DEFAULT_SCENARIO.stateAidGrowth) =>
  run(years, { ...DEFAULT_SCENARIO, rates, stateAidGrowth, ...over })
    .every(y => y.gap <= 0)

/** Smallest x that works, or null if the largest sane x does not. */
function least(ok: (x: number) => boolean, hi: number): number | null {
  if (!ok(hi)) return null
  let lo = 0
  for (let i = 0; i < 50; i++) {
    const mid = (lo + hi) / 2
    if (ok(mid)) hi = mid; else lo = mid
  }
  return hi
}

export function firstYearsFor(rates: Record<Bucket, number>, years: number,
                              aid = DEFAULT_SCENARIO.stateAidGrowth): FirstYears {
  const cut = least(x => holdsWith(rates, years, { cut: x }, aid), 8_000_000)
  const override = least(x => holdsWith(rates, years, { overrideLevy: x }, aid), 12_000_000)
  const build = least(x => holdsWith(rates, years, { newGrowth: x }, aid), 30_000_000)
  /* Capped at the ceiling rather than solved without one: a fee figure above what the
   * fees can raise is not a smaller answer, it is a different answer. */
  const fees = least(x => holdsWith(rates, years, { feeRevenue: x }, aid), FEE_CEILING.total)
  return {
    cut, override, fees,
    feeShareOfCeiling: fees === null ? null : fees / FEE_CEILING.total,
    overrideTownwide: override === null ? null : override / SHARE,
    build: build === null ? null : Math.max(build, DEFAULT_SCENARIO.newGrowth),
    buildings: build === null ? null : buildScale(Math.max(build,
      DEFAULT_SCENARIO.newGrowth)).buildingsPerYear,
  }
}

/** Everything the three user fees could add, at the fee level that raises the most.
 *
 *  Not a policy proposal — a ceiling. Each lever's own peak is the point past which
 *  raising the fee loses more participants than it gains dollars, and the district
 *  already charges on two of the three. What is left is the headroom, and it is small
 *  enough that knowing the number settles the argument: fees are a real answer to a
 *  few hundred thousand and no answer at all to a few million.
 *
 *  The fee levels behind it are steep — the athletics peak is over a thousand dollars a
 *  season — which is why the ceiling is quoted with them rather than on its own. */
export const FEE_CEILING = (() => {
  const each = MODEL.levers
    .filter(l => l.kind === 'revenue' && l.peakYield != null)
    .map(l => ({
      id: l.id, name: l.name, unit: l.unit,
      peakFee: l.peakFee ?? null, currentFee: l.current ?? 0,
      headroom: Math.max(0, (l.peakYield ?? 0) - (l.currentYield ?? 0)),
    }))
  return { each, total: each.reduce((n, e) => n + e.headroom, 0) }
})()

/** What one more dollar on the levy does to the average tax bill.
 *
 *  An override is the only one of the three first-year answers whose cost lands on people
 *  who do not work in the schools, and quoting it in levy dollars hides that completely.
 *  Same arithmetic as the override treadmill above, so the two can never disagree. */
export const overrideOnAverageHome = (levyDollars: number) =>
  Math.round((T.avgHomeValue * ((levyDollars * 1000) / T.totalValue)) / 1000)

/** A cut, in the things a cut is made of.
 *
 *  "$1.21M, once" is a number a reader cannot argue with because they cannot picture it,
 *  and the word "once" makes it sound like a bad month rather than what it is: a
 *  reduction adopted in one budget that stays out of every budget after it. Three
 *  comparisons fix that, and the third is the one that matters — past a certain size
 *  there is nothing discretionary left to take it from, and the balance comes out of
 *  classrooms whatever anybody intended. */
export function cutInThings(amount: number) {
  return {
    amount,
    positions: amount / COST_PER_FTE,
    /* The comparison against the cut the town has just lived through is made where it is
     * printed: `ALREADY_CUT` lives in the walkthrough model, which imports this file, and
     * reaching back for it here would close the loop. */
    /** Against everything outside the classroom that could be cut at all: every sport,
     *  the band and the clubs, most of technology, and every administrator the law
     *  allows the district to lose. */
    shareOfDiscretionary: amount / ALL_CUTS,
    beyondDiscretionary: amount > ALL_CUTS,
    discretionaryTotal: ALL_CUTS,
    shareOfBudget: amount / F.lps_appropriation,
  }
}

export interface Package {
  id: string
  horizon: Horizon
  /** What this package is, in the terms somebody would argue about it in. */
  label: string
  /** Why you would pick this one over its siblings in the same band. */
  angle: string
  rates: Record<Bucket, number>
  /** What all state aid grows at under this package. Equal to the assumed rate except on
   *  the ones that ask the State House for something, where it is the whole point. */
  stateAid: number
  /** The same ask expressed as Chapter 70 alone, which is what a delegation is actually
   *  lobbied for — the rest of the cherry sheet is not money the state would move for
   *  this reason. Null where the package asks nothing of the state. */
  ch70: number | null
  whoSaysYes: string
  note: string
  blended: number
  firstYears: FirstYears
  /** The scenario the two boards load: the build version, since that is the one with no
   *  cheque in it and the one whose curve can be watched going flat. */
  scenario: Scenario
  /** True where the cost rate is under the levy cap, so nothing has to keep going right
   *  afterwards for it to keep working. */
  forEver: boolean
}

const mix = (over: Partial<Record<Bucket, number>>): Record<Bucket, number> =>
  ({ ...DEFAULT_RATES, transport: LEVY_CAP, sped_tuition: LEVY_CAP,
     utilities: LEVY_CAP, other: LEVY_CAP, ...over })

/** The packages that actually hold, arranged by how long they hold for.
 *
 *  This board used to be seven single levers, five of which did not work, which answered
 *  a question nobody had: it takes a lot of space to say that pulling one lever is not
 *  enough, and a reader who wants to know what to do is left with nothing to do. What
 *  belongs on a menu is things you could order.
 *
 *  So every entry here is a combination that keeps the gap shut for the horizon it is
 *  filed under, and the bands are horizons rather than verdicts. Within each band the
 *  entries differ in who is asked for what — one spares the settlement, one spares
 *  insurance, one shares it — because that is the actual decision, and because the
 *  comparison makes its own argument: sharing costs a fraction of what sparing either
 *  side costs, every time, at every horizon.
 *
 *  Why single levers are gone is answered underneath rather than here. It is analysis,
 *  and this is a menu. */
export const PACKAGES: Package[] = ([
  {
    id: 'five-shared', horizon: 5, label: 'Share it',
    angle: 'Everybody gives a little, and it costs a fraction of the alternatives',
    over: { salaries: 0.03, health: 0.05 },
    whoSaysYes: 'The union settles at 3%, the Town gets insurance to 5% through plan '
      + 'design or the GIC, and the district holds transport, special education, '
      + 'utilities and supplies to the levy cap',
    note: 'Look at what the other two cards in this band cost. Half a point off salary '
      + 'growth and four points off insurance, split between two parties, buys the same five '
      + 'years for roughly a third of the money.',
  },
  {
    id: 'five-spare-pay', horizon: 5, label: 'Leave pay alone',
    angle: 'No concession at the bargaining table at all',
    over: { health: 0.05 },
    whoSaysYes: 'The Town alone, on insurance, plus the district on its own four lines. '
      + 'Nothing is asked of the union',
    note: 'Salaries go on rising 4% and somebody else covers it. This is the version '
      + 'that can be agreed without reopening a contract, and it is the most expensive '
      + 'five years on the board.',
  },
  {
    id: 'five-spare-insurance', horizon: 5, label: 'Leave insurance alone',
    angle: 'Nothing asked of the Public Employee Committee',
    over: { salaries: 0.03 },
    whoSaysYes: 'The union settles at 3% and the district holds its own four lines to the '
      + 'cap. Insurance goes on rising 9% a year',
    note: 'The mirror image of the card above, and it costs almost exactly the same — '
      + 'which is the clearest evidence on this page that the two lines are '
      + 'interchangeable as arithmetic and only different as politics.',
  },
  {
    id: 'ten-shared', horizon: 10, label: 'Share it',
    angle: 'Salaries at the levy cap is what makes the cheque almost disappear',
    over: { salaries: LEVY_CAP, health: 0.05 },
    whoSaysYes: 'The union settles at the levy cap, the Town gets insurance to 5%, the '
      + 'district holds its own four lines',
    note: 'Half a point further on salaries than the five-year cards above, and the '
      + 'one-time money falls by more than nine tenths while the quiet doubles. This is '
      + 'the best-value package on the board.',
  },
  {
    id: 'ten-gentler', horizon: 10, label: 'Gentler on pay',
    angle: 'Salaries at 3%, paid for once',
    over: { salaries: 0.03, health: 0.05 },
    whoSaysYes: 'The same three parties, with half a point more left on the table for '
      + 'staff and the difference found once instead',
    note: 'The same rates as the five-year card, held for twice as long by covering more '
      + 'of the early years up front. Nothing about the rates changed — only how much of '
      + 'the head start was bought.',
  },
  {
    id: 'ten-spare-pay', horizon: 10, label: 'Leave pay alone',
    angle: 'Ten years without reopening the contract',
    over: { health: 0.05 },
    whoSaysYes: 'The Town on insurance and the district on its own lines. Nothing asked '
      + 'of the union',
    note: 'It can be done, and the price of not asking is on the card: several times the '
      + 'one-time money of the shared version, for the same ten years.',
  },
  {
    id: 'thirty-shared', horizon: 30, label: 'Share it, and build a little',
    angle: 'A generation, with no cheque at all',
    over: { salaries: 0.03, health: 0.05 },
    whoSaysYes: 'The union at 3%, the Town at 5% on insurance, the district on its four '
      + 'lines, and the Planning Board on a build rate the town has managed before',
    note: 'The same rates as the five and ten-year cards. What buys the extra twenty '
      + 'years is not holding salaries lower — it is development, at a rate roughly twice '
      + 'what the town does now. Note what the one-time column says instead: a cheque '
      + 'would have to be several million.',
  },
  {
    id: 'thirty-cheap', horizon: 30, label: 'Hold salaries harder, and almost nothing else',
    angle: 'The cheapest generation on the board, if salaries can carry it',
    over: { salaries: LEVY_CAP, health: 0.04 },
    whoSaysYes: 'The union at the levy cap, the Town at 4% on insurance, the district on '
      + 'its four lines',
    note: 'Half a point of salary growth and one point of insurance below the card above, '
      + 'and thirty years arrives with a token cheque or a handful of buildings. This is '
      + 'the shape of the whole problem in one comparison.',
  },
  {
    id: 'thirty-spare-pay', horizon: 30, label: 'Leave pay alone for a generation',
    angle: 'Salaries never move, and development pays for it',
    over: { health: LEVY_CAP },
    whoSaysYes: 'The Town holds insurance to the levy cap — the hardest version of that '
      + 'ask — the district holds its four lines, and the town builds',
    note: 'It is possible, and this is what it takes: every other line in the budget at '
      + 'the cap, insurance included, and a build rate the town has never come near. The '
      + 'salary line is the one no arrangement of the others can work around cheaply.',
  },
  {
    id: 'state-halfway', horizon: ROUTE_CLOCK, aid: 0.052,
    label: 'Meet the state halfway',
    angle: 'A gentler local agreement, and Chapter 70 doing the other half',
    over: { salaries: 0.03, health: 0.05 },
    whoSaysYes: 'The union at 3%, the Town at 5% on insurance, the district on its four '
      + 'lines — and the Legislature, in every budget from now on. Four of those five are '
      + 'in this town and the fifth is not',
    note: 'The same local agreement as the five and ten-year cards above, which needed a '
      + 'cheque to reach even five years. With Chapter 70 growing at a rate a good year '
      + 'already looks like, it needs nothing and never reopens. This is the honest form '
      + 'of the ask to take to the delegation — not "fix it", but "make this agreement '
      + 'enough".',
  },
  {
    id: 'state-spares-pay', horizon: ROUTE_CLOCK, aid: 0.072,
    label: 'The state carries it, and pay never moves',
    angle: 'Nothing asked at the bargaining table, and a great deal asked at the State House',
    over: { health: 0.05 },
    whoSaysYes: 'The Town on insurance, the district on its four lines, and the '
      + 'Legislature for very much more than the card above asks',
    note: 'Every point of settlement left on the table has to be found somewhere, and here '
      + 'it is found at the State House. Chapter 70 has not grown at this rate in any '
      + 'recent year, which is the point of putting the two cards side by side: the local '
      + 'agreement is what makes the state ask reasonable.',
  },
  {
    id: 'for-ever', horizon: ROUTE_CLOCK, label: 'The one that never reopens',
    angle: 'Under the levy cap on the cost side, so nothing has to keep going right',
    over: { salaries: 0.02, health: 0.04 },
    whoSaysYes: 'The union at 2%, the Town at 4% on insurance, the district on its four '
      + 'lines. Nobody else — no developer, no legislature, no decade of luck',
    note: 'No cheque, no override, no building. It is the hardest ask on the page and the '
      + 'only one that ends the conversation, and those two facts are the same fact: '
      + 'every cheaper package leans on something outside the town continuing to behave.',
  },
] as (Omit<Package, 'rates' | 'blended' | 'firstYears' | 'scenario' | 'forEver'
  | 'stateAid' | 'ch70'>
  & { over: Partial<Record<Bucket, number>>; aid?: number })[])
  .map(({ over, aid, ...p }) => {
    const rates = mix(over)
    const stateAid = aid ?? DEFAULT_SCENARIO.stateAidGrowth
    const firstYears = firstYearsFor(rates, p.horizon, stateAid)
    return {
      ...p, rates, firstYears, stateAid,
      ch70: aid === undefined ? null : ch70OnlyGrowth(aid),
      blended: blendedOf(rates),
      /* With the state carrying part of the revenue side, "for ever" is no longer a
       * question about the levy cap alone — the package holds because aid compounds
       * faster than the gap does, which the horizon it was solved for already records. */
      forEver: p.horizon === ROUTE_CLOCK
        || blendedOf(rates) <= FOREVER_BAR + 0.0002,
      scenario: { ...DEFAULT_SCENARIO, rates, stateAidGrowth: stateAid,
                  newGrowth: firstYears.build ?? DEFAULT_SCENARIO.newGrowth },
    }
  })

/** What a moderate improvement at the State House is worth to a local package.
 *
 *  State aid was on the old board as a lever of its own and came off with the rest of
 *  them, which lost the finding rather than the option. Alone it does nothing — the town
 *  is short in the early years while the aid ramps, so at any rate you like the gap is
 *  open next April. Paired with a package it is the strongest thing on the page: the same
 *  local agreement that needs a $372k cut at today's aid growth needs nothing at all if
 *  Chapter 70 grows at the rate a good year already looks like.
 *
 *  Quoted against one reference package rather than all of them, because the shape is the
 *  same for every package and ten copies of it would bury the point. Chapter 70 rates
 *  alongside the cherry-sheet rate the projection actually grows, since the delegation is
 *  asked for the first and the model moves the second. */
export const STATE_AID_TRADE = (() => {
  const reference = PACKAGES.find(p => p.id === 'five-shared')!
  const rows = [DEFAULT_SCENARIO.stateAidGrowth, 0.03, 0.04, 0.05, 0.06].map(aid => {
    const at = (over: Partial<Scenario>) =>
      run(reference.horizon, { ...DEFAULT_SCENARIO, rates: reference.rates,
                               stateAidGrowth: aid, ...over }).every(y => y.gap <= 0)
    let cut: number | null = null
    if (at({ cut: 8_000_000 })) {
      let lo = 0, hi = 8_000_000
      for (let i = 0; i < 50; i++) {
        const mid = (lo + hi) / 2
        if (at({ cut: mid })) hi = mid; else lo = mid
      }
      cut = hi
    }
    /** How long the package holds on the rates alone, with no cheque of any kind. */
    let free = 0
    for (const y of run(ROUTE_CLOCK, { ...DEFAULT_SCENARIO, rates: reference.rates,
                                       stateAidGrowth: aid })) {
      if (y.gap <= 0) free++; else break
    }
    return { aid, ch70: ch70OnlyGrowth(aid), cut, freeYears: free }
  })
  return { reference, rows, baseline: DEFAULT_SCENARIO.stateAidGrowth }
})()

/** The bands, in the order somebody meets them: the smallest ask first. */
export const HORIZONS: { h: Horizon; title: string; sub: string }[] = [
  { h: 5, title: 'Five years', sub: 'No cuts through FY32' },
  { h: 10, title: 'Ten years', sub: 'No cuts through FY37' },
  { h: 30, title: 'A generation', sub: 'No cuts for thirty years' },
  { h: ROUTE_CLOCK, title: 'For ever', sub: 'It never reopens, and nothing has to keep going right' },
]

/* ---- the raise, and what eats it ----------------------------------------- */

/** Next year priced as a budget of the increase rather than a budget of the total.
 *
 *  This is the same arithmetic as everything else on the page, said in the form people
 *  actually argue in. Nobody at a meeting disputes the total budget; they dispute whether
 *  a 2½% raise ought to be enough. So put the raise on the table as a fixed number of
 *  dollars, then let each cost line take its bite out of it in order, and the answer stops
 *  being a matter of opinion: the six lines want 162% of it, health insurance alone wants
 *  44%, and there is nothing left over because there was never enough to begin with.
 *
 *  Reconciles to engine.project()'s FY28 gap to the dollar — asserted in `reconciles`. */
export function nextYear() {
  const g = run(1, DEFAULT_SCENARIO)[0]

  // Where the town's extra money comes from. Excluded debt and the wedge are constant, so
  // the whole increase is these three, and the schools take a proportional share.
  const dLevy = F.levy_limit * A.levy_growth
  const dNewGrowth = DEFAULT_SCENARIO.newGrowth
  const dAid = F.state_aid * DEFAULT_SCENARIO.stateAidGrowth
  const dReceipts = F.local_receipts * A.local_receipts_growth
  const dTown = dLevy + dNewGrowth + dAid + dReceipts

  const appropFy27 = F.lps_appropriation + F.stm_appropriation
  /** Every extra dollar the schools have to spend next year. */
  const allowed = g.revenue - appropFy27

  const source = (label: string, amount: number, note: string) => ({
    label, note,
    share: amount / dTown,
    toSchools: Math.round((amount / dTown) * allowed),
  })

  const costs = RATE_LINES.map(l => {
    const amount = BASE[l.key] * l.rate
    /** What this line would get if the increase were split in proportion to what each
     *  line already costs — the fairest possible division, and the one that shows which
     *  lines are living inside their means and which are not. The shares sum to the whole
     *  increase exactly, so the overdrafts sum to exactly the shortfall. */
    const share = allowed * (BASE[l.key] / TOTAL)
    return {
      key: l.key, label: l.label, rate: l.rate, amount: Math.round(amount),
      /** The share of the entire increase that this one line consumes. */
      shareOfAllowed: amount / allowed,
      share: Math.round(share),
      /** Positive means the line takes more than its share. Negative means it fits. */
      overdraft: Math.round(amount - share),
      /** How many times its own share the line takes. */
      multiple: amount / share,
      fits: amount <= share,
    }
  }).sort((a, b) => b.amount - a.amount)

  const costTotal = costs.reduce((s2, c) => s2 + c.amount, 0)
  /** The schools are already spending more than they were appropriated before anything
   *  grows — the town meeting add-backs cost more than the town meeting appropriation. */
  const startingBehind = Math.round(TOTAL - appropFy27)

  return {
    fy: g.fy,
    growthRate: g.revenueGrowth,
    allowed: Math.round(allowed),
    /** The rate at which every line could grow if the increase were exactly used up.
     *
     *  This is what a line's "share" is, said as a rate: share = base x this. Slightly
     *  above the 2.5% levy cap because new growth, state aid and receipts top it up, and
     *  below what any line except one actually grows at. */
    affordableRate: allowed / TOTAL,
    appropFy27: Math.round(appropFy27),
    /** What level service costs at FY27 prices — the row the projection starts from. */
    costFy27: Math.round(TOTAL),
    sources: [
      source('The 2½% levy increase', dLevy, 'What Proposition 2½ allows on the existing base'),
      source('New growth', dNewGrowth, 'New construction added to the levy, at the assumed rate'),
      source('State aid', dAid, `Chapter 70 and the rest, at ${(DEFAULT_SCENARIO.stateAidGrowth * 100).toFixed(1)}%`),
      source('Local receipts', dReceipts, 'Fees, excise, permits'),
    ],
    costs,
    costTotal,
    startingBehind,
    /** What is left of the raise once the six lines have taken their share. Negative. */
    leftOver: Math.round(allowed - costTotal),
    /** Everything the six lines want, as a multiple of everything there is. */
    consumed: costTotal / allowed,
    gap: g.gap,
  }
}

/** The decomposition has to add up to the projection, or it is a nice picture of nothing. */
export function reconciles() {
  const n = nextYear()
  const rebuilt = n.startingBehind + n.costTotal - n.allowed
  return { rebuilt, actual: n.gap, ok: Math.abs(rebuilt - n.gap) <= 2 }
}

/** The one-vote alternative to the treadmill: how big must a single override be to hold
 *  for N years?
 *
 *  Worth computing because the obvious objection to "an override only buys a year" is
 *  correct — an override is not a one-off payment, it is a permanent lift to the levy
 *  limit that compounds at 2½% like the rest of it. So a big enough one really does cover
 *  many years, and saying otherwise would be as misleading as the thing it corrects.
 *
 *  What the arithmetic then shows is the price of that. The override compounds at 2½%
 *  while the gap compounds at nearly 5% from a base that is already growing, so buying
 *  each extra year costs disproportionately more than the last — and no finite override
 *  holds forever, because the two rates never cross. */
export function overrideForYears(
  years: number, base: Scenario = DEFAULT_SCENARIO,
): { levy: number; onAverageHome: number } {
  let lo = 0, hi = 80_000_000
  for (let i = 0; i < 80; i++) {
    const mid = (lo + hi) / 2
    const y = run(Math.max(years + 2, 12), { ...base, overrideLevy: mid })
    const funded = y.findIndex(x => x.gap > 0)
    if ((funded === -1 ? y.length : funded) >= years) hi = mid; else lo = mid
  }
  return {
    levy: Math.round(hi),
    onAverageHome: Math.round((T.avgHomeValue * ((hi * 1000) / T.totalValue)) / 1000),
  }
}

/** The override amounts that are actually worth landing on: one per year of coverage.
 *
 *  A continuous slider running to some round number invites a reader to stop at $2,000,000
 *  and wonder what it bought. These are the only values with an answer — the smallest
 *  override that funds through FY28, through FY29, and so on — so the control snaps to
 *  them and can say what each one buys.
 *
 *  Computed against whatever else is set on the board rather than against the default
 *  projection: cut $1.5M first and every one of these gets smaller, which is the point of
 *  having the two columns on the same page. */
export function overrideStops(base: Scenario, upTo = 8) {
  const out: { years: number; fy: number; levy: number }[] = []
  for (let n = 1; n <= upTo; n++) {
    const { levy } = overrideForYears(n, { ...base, overrideLevy: 0 })
    // Once the scenario funds a year on its own the stop is degenerate; and rounding to
    // the nearest thousand keeps the readout from printing false precision on a slider.
    const rounded = Math.ceil(levy / 1000) * 1000
    if (rounded <= 0) continue
    if (out.length && rounded <= out[out.length - 1].levy) continue
    out.push({ years: n, fy: 27 + n, levy: rounded })
  }
  return out
}

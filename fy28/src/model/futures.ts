import { MODEL, COST_GROWTH_BLENDED } from './engine'
import {
  BASELINE_REVENUE_GROWTH, COST_PER_FTE, DEFAULT_RATES, DEFAULT_SCENARIO, LEVY_CAP,
  PACKAGES, ROUTE_CLOCK, firstYearsFor, freshGap, overrideOnAverageHome,
  overrideTreadmill, run, workforceShrink, HEADCOUNT,
} from './rates'

/** THE DECISION MENU. Bend the curve is the parameter space -- every dial; this is the
 *  handful of things a resident could actually order from it, named the way they are
 *  argued about at a meeting. TJ, 12 September 2026: "packages like 'override every
 *  year', 'one big override', 'radical health insurance change'... Even 'cut staffing'."
 *
 *  Same engine as everything else: run() from rates.ts, PACKAGES where a card is one of
 *  the priced combinations already on /bend-the-curve. Nothing here is a new number.
 *  The one thing each card has to say plainly is whether it changes a RATE -- the only
 *  kind of answer that closes a gap that is itself a rate -- or an AMOUNT, which closes
 *  one year of it. */

export const MENU_YEARS = 5

export interface Future {
  id: string
  label: string
  /** One line: what this is, in the words somebody would propose it in. */
  angle: string
  whoSaysYes: string
  /** What it costs, and to whom -- a resident, an employee, a classroom. */
  costs: string
  /** How long the gap stays shut. */
  holds: string
  bends: boolean
  /** Where the working is. */
  more: string
}

const usd = (n: number) => '$' + Math.round(n).toLocaleString('en-US')
const pct = (x: number, d = 0) => `${(x * 100).toFixed(d)}%`
const n1 = (x: number) => x.toFixed(1)
const plural = (n: number, w: string) => `${n} ${w}${n === 1 ? '' : 's'}`

const base = run(MENU_YEARS, DEFAULT_SCENARIO)
const spread = COST_GROWTH_BLENDED - BASELINE_REVENUE_GROWTH

/* 1. Cut every year: the default. Each spring the fresh gap comes out of positions. */
const fresh = freshGap(base)
const cutsPerYear = fresh.map(g => g.fresh / COST_PER_FTE)
const cutsTotal = cutsPerYear.reduce((s, x) => s + x, 0)

/* 2. Cut once: the permanent reduction, adopted now, that holds MENU_YEARS at today's
 *    rates. A level on the salary base, so it compounds -- and then it reopens. */
const cutOnce = firstYearsFor(DEFAULT_RATES, MENU_YEARS).cut
const cutOnceTen = firstYearsFor(DEFAULT_RATES, 10).cut

/* 3. An override every spring: the treadmill. */
const treadmill = overrideTreadmill(base)
const treadmillBill = treadmill.reduce((s, t) => s + t.onAverageHome, 0)

/* 4. One big override: the levy that holds MENU_YEARS with nothing else changed. */
const overrideOnce = firstYearsFor(DEFAULT_RATES, MENU_YEARS).override
const overrideOnceTen = firstYearsFor(DEFAULT_RATES, 10).override

/* 5-8. The priced combinations, by id. */
const pkg = (id: string) => PACKAGES.find(p => p.id === id)!
const insuranceOnly = pkg('five-spare-pay'), insuranceOnlyTen = pkg('ten-spare-pay')
const shared = pkg('five-shared'), sharedTen = pkg('ten-gentler'), sharedThirty = pkg('thirty-shared')
const forever = pkg('for-ever')
const state = pkg('state-halfway')
const shrinkAtCap = workforceShrink(LEVY_CAP, MODEL.assumptions.salaries)
const shrinkAt3 = workforceShrink(0.03, MODEL.assumptions.salaries)

/** How many years a future holds when nothing else is done -- counted, not asserted. */
function yearsHeld(over: Partial<Parameters<typeof run>[1]>): number {
  const y = run(ROUTE_CLOCK, { ...DEFAULT_SCENARIO, ...over })
  let n = 0
  for (const r of y) { if (r.gap <= 0) n++; else break }
  return n
}

const cheque = (p: typeof shared) =>
  p.firstYears.cut === null || p.firstYears.cut < 1000 ? 'no one-time money'
    : `a one-time ${usd(p.firstYears.cut)} cut, or ${usd(p.firstYears.override ?? 0)} once on the levy`

export const FUTURES: Future[] = [
  {
    id: 'cut-every-year', label: 'Cut staff every spring',
    angle: 'What happens if nothing else is decided',
    whoSaysYes: 'The School Committee, every year, at budget time',
    costs: `About ${n1(cutsPerYear[0])} positions next year and ${n1(cutsTotal)} over ${MENU_YEARS} years, at the catalogue's own cost per position — from a staff of roughly ${HEADCOUNT}`,
    holds: 'Never closes. Each cut balances one year; the rates reopen it the next',
    bends: false,
    more: '/crisis',
  },
  {
    id: 'cut-once', label: 'One big staffing cut',
    angle: 'Cut deep once and stop cutting',
    whoSaysYes: 'The School Committee, once',
    costs: cutOnce === null ? 'No cut of any size holds five years'
      : `${usd(cutOnce)} a year, permanently — about ${n1(cutOnce / COST_PER_FTE)} positions. Holding ten years takes ${usd(cutOnceTen ?? 0)}, about ${n1((cutOnceTen ?? 0) / COST_PER_FTE)} positions`,
    holds: cutOnce === null ? '' : `${plural(yearsHeld({ cut: cutOnce }), 'year')}, then it reopens — a smaller budget growing at the same ${pct(COST_GROWTH_BLENDED, 2)}`,
    bends: false,
    more: '/bend-the-curve',
  },
  {
    id: 'override-every-year', label: 'An override every year',
    angle: 'Ask the voters each spring for that year’s gap',
    whoSaysYes: 'Town Meeting and the ballot, every year, and it has to pass every time',
    costs: `${usd(treadmill[0].onAverageHome)} on the average tax bill in year one, ${usd(treadmill[MENU_YEARS - 1].onAverageHome)} more in year ${MENU_YEARS}; ${usd(treadmillBill)} added to the bill over ${MENU_YEARS} years, and it keeps rising`,
    holds: 'Only while it keeps passing. Nothing about the rates changes, so the question comes back larger each spring',
    bends: false,
    more: '/bend-the-curve',
  },
  {
    id: 'override-once', label: 'One big override',
    angle: 'One ballot question, sized to last',
    whoSaysYes: 'Town Meeting and the ballot, once',
    costs: overrideOnce === null ? 'No override of any size holds five years'
      : `${usd(overrideOnce)} on the levy — about ${usd(overrideOnAverageHome(overrideOnce))} a year on the average tax bill, permanently. To last ten years: ${usd(overrideOnceTen ?? 0)}, about ${usd(overrideOnAverageHome(overrideOnceTen ?? 0))} a year`,
    holds: overrideOnce === null ? '' : `${plural(yearsHeld({ overrideLevy: overrideOnce }), 'year')}, then it reopens — the levy grows ${pct(LEVY_CAP, 1)} and the costs grow ${pct(COST_GROWTH_BLENDED, 2)}`,
    bends: false,
    more: '/bend-the-curve',
  },
  {
    id: 'insurance', label: 'Change health insurance, leave pay alone',
    angle: 'Plan design or the state GIC, so the line grows ' + pct(insuranceOnly.rates.health) + ' instead of ' + pct(MODEL.assumptions.health),
    whoSaysYes: 'The Town, which buys the insurance, through the Public Employee Committee; the district holds its own lines to the cap. Nothing is asked of the union on pay',
    costs: `Every employee on a narrower network or a higher deductible; ${cheque(insuranceOnly)} to bridge the first ${MENU_YEARS} years. Ten years: ${cheque(insuranceOnlyTen)}`,
    holds: `${MENU_YEARS} years with the cheque; ten with the larger one. Salaries still grow ${pct(MODEL.assumptions.salaries)}, so it does not close on its own`,
    bends: true,
    more: '/bend-the-curve',
  },
  {
    id: 'share', label: 'Everybody gives a little',
    angle: `Pay settles at ${pct(shared.rates.salaries)}, insurance held to ${pct(shared.rates.health)}, the district holds the rest at the cap`,
    whoSaysYes: 'The union, the Town and the School Committee — three parties, none of them alone',
    costs: `About ${n1(shrinkAt3.positionsPerYear)} fewer positions a year if raises stay at contract, or a smaller raise; a costlier plan for staff. To bridge ${MENU_YEARS} years, ${cheque(shared)}; ten years, ${cheque(sharedTen)}`,
    holds: `${MENU_YEARS} years, ten with the cheque, thirty if the town also builds about ${Math.round(sharedThirty.firstYears.buildings ?? 0)} developments a year`,
    bends: true,
    more: '/bend-the-curve',
  },
  {
    id: 'state', label: 'Meet the state halfway',
    angle: `The same local agreement, with Chapter 70 growing ${pct(state.ch70 ?? 0, 1)} a year`,
    whoSaysYes: 'The union, the Town, the School Committee — and the Legislature, in every budget from now on',
    costs: 'The same as the card above locally, and a delegation that has to win it at the State House every year',
    holds: 'For good, as long as the state keeps its side — which the town does not control',
    bends: true,
    more: '/state-aid',
  },
  {
    id: 'forever', label: 'The one that never reopens',
    angle: `Pay at ${pct(forever.rates.salaries)}, insurance at ${pct(forever.rates.health)}, everything else at the cap — under the levy cap on the cost side`,
    whoSaysYes: 'The union, the Town and the School Committee. Nobody else: no developer, no legislature, no override',
    costs: `About ${n1(shrinkAtCap.positionsPerYear)} fewer positions a year if raises stay at contract — ${pct(shrinkAtCap.after10)} of the staff in ten years — or raises under 2%; and the cheapest plan the group can bargain`,
    holds: 'For good. Nothing has to keep going right afterwards',
    bends: true,
    more: '/bend-the-curve',
  },
]

export const MENU = { spread, years: MENU_YEARS, todayGap: base[0].gap,
  /** Year one of the override treadmill, on the average bill -- the model's own figure. */
  overrideYearOne: treadmill[0].onAverageHome }

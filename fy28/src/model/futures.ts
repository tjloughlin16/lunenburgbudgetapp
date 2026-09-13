import { MODEL, COST_GROWTH_BLENDED } from './engine'
import {
  BASELINE_REVENUE_GROWTH, COST_PER_FTE, DEFAULT_RATES, DEFAULT_SCENARIO, LEVY_CAP,
  PACKAGES, RATE_LINES, ROUTE_CLOCK, firstYearsFor, overrideOnAverageHome,
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
 *  one year of it.
 *
 *  FIVE AND TEN YEARS, NOTHING LONGER. TJ, 13 September 2026: "I don't want forever. I'm
 *  talking even 10 years. All these solutions should be a 5 or 10 year proposed
 *  solution. Permanent is silly." So every card is priced to hold five years and to hold
 *  ten, and the two that used to say "for good" are gone. */

export const MENU_YEARS = 5

export interface Future {
  id: string
  label: string
  /** One line: what this is, in the words somebody would propose it in. */
  angle: string
  whoSaysYes: string
  /** What it costs, and to whom -- a resident, an employee, a classroom. */
  costs: string
  /** How long the gap stays shut -- the metric, short enough to be the card's number. */
  holdsFor: string
  /** ...and the sentence under it. */
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
const shared = pkg('five-shared'), sharedTen = pkg('ten-gentler')
const sharedTenNoCheque = pkg('ten-shared')
const shrinkAtCap = workforceShrink(LEVY_CAP, MODEL.assumptions.salaries)
const shrinkAt3 = workforceShrink(0.03, MODEL.assumptions.salaries)

/** The smallest cut made EVERY year (to the salary base, compounding) that holds N years.
 *  Same loop as scripts/build_big_picture.py `stabilise()`: revenue from run(), costs
 *  from the rate lines' own amounts, the cut subtracted before each year's growth. */
function everyYearCut(years: number): number | null {
  const revenue = run(years, DEFAULT_SCENARIO).map(y => y.revenue)
  const ok = (x: number) => {
    const b: Record<string, number> = Object.fromEntries(RATE_LINES.map(l => [l.key, l.amount]))
    for (let i = 0; i < years; i++) {
      b.salaries -= x
      for (const l of RATE_LINES) b[l.key] *= 1 + DEFAULT_RATES[l.key]
      const cost = RATE_LINES.reduce((s, l) => s + b[l.key], 0)
      if (Math.round(cost - revenue[i]) > 0) return false
    }
    return true
  }
  if (!ok(8_000_000)) return null
  let lo = 0, hi = 8_000_000
  for (let i = 0; i < 50; i++) { const mid = (lo + hi) / 2; if (ok(mid)) hi = mid; else lo = mid }
  return hi
}
const everyFive = everyYearCut(MENU_YEARS), everyTen = everyYearCut(10)

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
    costs: `About ${n1((everyFive ?? 0) / COST_PER_FTE)} positions a year to hold ${MENU_YEARS} years — ${n1((everyFive ?? 0) * MENU_YEARS / COST_PER_FTE)} in all; about ${n1((everyTen ?? 0) / COST_PER_FTE)} a year to hold ten — ${n1((everyTen ?? 0) * 10 / COST_PER_FTE)} in all, of roughly ${HEADCOUNT}`,
    holdsFor: '1 year at a time',
    holds: 'Each cut balances one year; the rates reopen it the next, so it is decided again every spring',
    bends: false,
    more: '/crisis',
  },
  {
    id: 'cut-once', label: 'One big staffing cut',
    angle: 'Cut deep once and stop cutting',
    whoSaysYes: 'The School Committee, once',
    costs: cutOnce === null ? 'No cut of any size holds five years'
      : `${usd(cutOnce)} a year, permanently — about ${n1(cutOnce / COST_PER_FTE)} positions. Holding ten years takes ${usd(cutOnceTen ?? 0)}, about ${n1((cutOnceTen ?? 0) / COST_PER_FTE)} positions`,
    holdsFor: '5 or 10 years',
    holds: `${plural(yearsHeld({ cut: cutOnce ?? 0 }), 'year')} at the smaller cut, ten at the larger; then it reopens — a smaller budget growing at the same ${pct(COST_GROWTH_BLENDED, 2)}`,
    bends: false,
    more: '/bend-the-curve',
  },
  {
    id: 'override-every-year', label: 'An override every year',
    angle: 'Ask the voters each spring for that year’s gap',
    whoSaysYes: 'Town Meeting and the ballot, every year, and it has to pass every time',
    costs: `${usd(treadmill[0].onAverageHome)} on the average tax bill in year one, ${usd(treadmill[MENU_YEARS - 1].onAverageHome)} more in year ${MENU_YEARS}; ${usd(treadmillBill)} added to the bill over ${MENU_YEARS} years, and it keeps rising`,
    holdsFor: '1 year at a time',
    holds: 'Only while it keeps passing. Nothing about the rates changes, so the question comes back larger each spring',
    bends: false,
    more: '/bend-the-curve',
  },
  {
    id: 'override-five', label: 'A five-year override',
    angle: 'One ballot question, sized to hold five years',
    whoSaysYes: 'Town Meeting and the ballot, once',
    costs: overrideOnce === null ? 'No override of any size holds five years'
      : `${usd(overrideOnce)} on the levy — about ${usd(overrideOnAverageHome(overrideOnce))} a year on the average tax bill, permanently`,
    holdsFor: plural(yearsHeld({ overrideLevy: overrideOnce ?? 0 }), 'year'),
    holds: `Then it reopens — the levy grows ${pct(LEVY_CAP, 1)} and the costs grow ${pct(COST_GROWTH_BLENDED, 2)}`,
    bends: false,
    more: '/bend-the-curve',
  },
  {
    id: 'override-ten', label: 'A ten-year override',
    angle: 'One ballot question, sized to hold ten years',
    whoSaysYes: 'Town Meeting and the ballot, once',
    costs: overrideOnceTen === null ? 'No override of any size holds ten years'
      : `${usd(overrideOnceTen)} on the levy — about ${usd(overrideOnAverageHome(overrideOnceTen))} a year on the average tax bill, permanently. More than twice the five-year question, because the gap keeps widening under it`,
    holdsFor: plural(yearsHeld({ overrideLevy: overrideOnceTen ?? 0 }), 'year'),
    holds: `Then it reopens — the same rates, a bigger base`,
    bends: false,
    more: '/bend-the-curve',
  },
  {
    id: 'insurance', label: 'Change health insurance, leave pay alone',
    angle: 'Plan design or the state GIC, so the line grows ' + pct(insuranceOnly.rates.health) + ' instead of ' + pct(MODEL.assumptions.health),
    whoSaysYes: 'The Town, which buys the insurance, through the Public Employee Committee; the district holds its own lines to the cap. Nothing is asked of the union on pay',
    costs: `Every employee on a narrower network or a higher deductible; ${cheque(insuranceOnly)} to bridge the first ${MENU_YEARS} years. Ten years: ${cheque(insuranceOnlyTen)}`,
    holdsFor: '5 or 10 years',
    holds: `${MENU_YEARS} years with the smaller cheque; ten with the larger. Salaries still grow ${pct(MODEL.assumptions.salaries)}, so it does not close on its own`,
    bends: true,
    more: '/bend-the-curve',
  },
  {
    id: 'share', label: 'Everybody gives a little',
    angle: `Pay settles at ${pct(shared.rates.salaries)}, insurance held to ${pct(shared.rates.health)}, the district holds the rest at the cap`,
    whoSaysYes: 'The union, the Town and the School Committee — three parties, none of them alone',
    costs: `About ${n1(shrinkAt3.positionsPerYear)} fewer positions a year if raises stay at contract, or a smaller raise; a costlier plan for staff. To bridge ${MENU_YEARS} years, ${cheque(shared)}; ten years, ${cheque(sharedTen)}`,
    holdsFor: '5 or 10 years',
    holds: `${MENU_YEARS} years nearly free; ten with the cheque`,
    bends: true,
    more: '/bend-the-curve',
  },
  {
    id: 'share-more', label: 'Everybody gives more — ten years, almost nothing else',
    angle: `Pay settles at the ${pct(sharedTenNoCheque.rates.salaries, 1)} levy cap, insurance held to ${pct(sharedTenNoCheque.rates.health)}, the district holds the rest`,
    whoSaysYes: 'The union, the Town and the School Committee — the same three, each asked for a little more than the card above',
    costs: `About ${n1(shrinkAtCap.positionsPerYear)} fewer positions a year if raises stay at contract, or raises at the cap; a costlier plan for staff; ${cheque(sharedTenNoCheque)}`,
    holdsFor: '10 years',
    holds: 'Ten years with a token one-time sum and no override — the cheapest ten years on the page',
    bends: true,
    more: '/bend-the-curve',
  },
]

export const MENU = { spread, years: MENU_YEARS, todayGap: base[0].gap,
  /** Year one of the override treadmill, on the average bill -- the model's own figure. */
  overrideYearOne: treadmill[0].onAverageHome }

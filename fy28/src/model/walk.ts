import { MODEL, expand, usd, usdShort, COST_GROWTH_BLENDED } from './engine'
import { ADMIN, FEES, GAPS } from './answers'
import {
  BASELINE_REVENUE_GROWTH, DEFAULT_SCENARIO, DEFAULT_RATES, LEVY_CAP, RATE_LINES,
  ALL_CUTS, run, overrideForYears, type Bucket,
} from './rates'

/** Derivations the walkthrough needs and no other page did.
 *
 *  Two of them exist because the exhibit asks questions the tabbed site never had to. A
 *  visitor arriving cold has to be told what the town has already given up before they
 *  will listen to why it did not work — nothing else here needed that. And the walkthrough
 *  wants every one-time answer on one table, priced identically, which is the argument the
 *  old site made across four pages. */

/* ---- what has already been given up ------------------------------------- */

/** Positions and lines the FY27 budget cut, and the ones it never funded.
 *
 *  This is the most persuasive material in the whole model and it was sitting unused: the
 *  town has already run the experiment the rest of the site argues about. It cut 9.2
 *  positions and the hole came back bigger. Everything about rates is easier to hear from
 *  somebody who has already paid that.
 *
 *  Covers the FY27 cycle only, which is what the catalogue records. If there were cuts in
 *  earlier years they are not here, and a multi-year count would be better still. */
const cutRows = expand(MODEL.programs).filter(p => p.status === 'cut')
const unfundedRows = expand(MODEL.programs).filter(p => p.status === 'unfunded')

const total = (rows: typeof cutRows) => ({
  count: rows.length,
  cost: Math.round(rows.reduce((s, p) => s + p.cost, 0)),
  fte: Math.round(rows.reduce((s, p) => s + p.fte, 0) * 10) / 10,
})

/** The catalogue's names are written for a budget reader. These are people. */
const PLAIN: Record<string, string> = {
  es_teachers_2fte: 'Two classroom teachers, Turkey Hill',
  ps_teachers_2fte: 'Two classroom teachers, Primary School',
  interventionist_ps: 'The Primary School reading and math interventionist',
  interventionist_thes: 'Half the Turkey Hill interventionist',
  asst_principal: 'An assistant principal — Primary and Turkey Hill now share one',
  cota: 'The occupational therapy assistant',
  custodian_hs: 'A high school custodian',
  music_thes_02: 'Part of the Turkey Hill music teacher',
  athletic_trainer_half: 'Half the athletic trainer',
}

export const ALREADY_CUT = {
  ...total(cutRows),
  /** The ones that were somebody's job, largest first. */
  people: cutRows.filter(p => p.fte > 0)
    .sort((a, b) => b.cost - a.cost)
    .map(p => ({ id: p.id, label: PLAIN[p.id] ?? p.name, fte: p.fte, cost: p.cost })),
  /** Asked for and never funded — a cut by another name. */
  unfunded: total(unfundedRows),
}

/* ---- every one-time answer, and the two that are not ---------------------- */

/** How many consecutive years a permanent saving of `amount` keeps the budget whole. */
const yearsFunded = (amount: number) => {
  const y = run(12, { ...DEFAULT_SCENARIO, cut: amount })
  const i = y.findIndex(x => x.gap > 0)
  return i === -1 ? 12 : i
}

/** The gap between the two rates, in points — the denominator for anything structural.
 *
 *  Measured against today's revenue growth, which is what the rate page's leverage section
 *  already uses. The thirty-year bar is lower (2.69%) and the spread against it is wider,
 *  and the "forever" room says so in its own words — but two pages quoting two different
 *  spreads for the same idea is exactly the confusion this site keeps having to fix. */
export const SPREAD = COST_GROWTH_BLENDED - BASELINE_REVENUE_GROWTH

const weightOf = (k: Bucket) => RATE_LINES.find(l => l.key === k)!.weight
const baseOf = (k: Bucket) =>
  (MODEL.expenseBase as Record<string, number>)[k] + (k === 'salaries' ? MODEL.fy27.stm_addbacks : 0)

/** Moving one line's growth rate: what it saves next year, and what it does to the slope. */
function rateMove(key: Bucket, to: number, label: string) {
  const from = DEFAULT_RATES[key]
  return {
    label, kind: 'rate' as const,
    amount: Math.round(baseOf(key) * (from - to)),
    years: null,
    points: weightOf(key) * (from - to),
  }
}

/** One table carrying the argument the old site made across four pages.
 *
 *  Everything anybody has proposed, priced the same way, with the two columns that
 *  matter side by side: what it is worth next year, and what it does to the rate. The
 *  point is not any row. It is that the column of zeros belongs to everything the town
 *  actually argues about. */
export const ONE_TIME_ANSWERS = [
  { label: 'Cut every remaining sport', kind: 'level' as const,
    amount: MODEL.facts.athleticsRemaining as number,
    years: yearsFunded(MODEL.facts.athleticsRemaining as number), points: 0 },
  { label: 'Raise all three user fees to their ceilings', kind: 'level' as const,
    amount: Math.round(FEES.total), years: yearsFunded(FEES.total), points: 0 },
  { label: 'Cut every administrative line the law allows', kind: 'level' as const,
    amount: ADMIN.lawful, years: yearsFunded(ADMIN.lawful), points: 0 },
  { label: 'Cut everything nameable, all at once', kind: 'level' as const,
    amount: ALL_CUTS, years: yearsFunded(ALL_CUTS), points: 0 },
  { label: 'Pass one school override', kind: 'level' as const,
    amount: overrideForYears(2).levy, years: 2, points: 0 },
  rateMove('health', 0.04, 'Hold health insurance to 4% instead of 9%'),
  rateMove('salaries', LEVY_CAP, 'Settle salaries at 2½% instead of 4%'),
]

/* ---- room 2: what level service means ------------------------------------ */

/** The definition the whole exhibit fails without, with its own arithmetic attached. */
export const LEVEL_SERVICE = {
  fy27: Math.round(MODEL.fy27.lps_appropriation + MODEL.fy27.stm_appropriation),
  costsNextYear: Math.round(run(1, DEFAULT_SCENARIO)[0].cost),
  increase: Math.round(run(1, DEFAULT_SCENARIO)[0].cost
    - (Object.values(MODEL.expenseBase).reduce((s, v) => s + v, 0) + MODEL.fy27.stm_addbacks)),
  enrollment: MODEL.taxBase.enrollment,
  gap: GAPS[0].cumulative,
}

/* ---- room 1: what the town has already said ------------------------------ */

export const ALREADY_SAID = {
  overrides: [
    { amount: MODEL.facts.overrideQ1.amount as number, yes: MODEL.facts.overrideQ1.yes as number,
      no: MODEL.facts.overrideQ1.no as number, cost: Math.round(MODEL.facts.tier1TaxIncrease as number) },
    { amount: MODEL.facts.overrideQ2.amount as number, yes: MODEL.facts.overrideQ2.yes as number,
      no: MODEL.facts.overrideQ2.no as number, cost: Math.round(MODEL.facts.tier2TaxIncrease as number) },
  ],
  ballotsCast: MODEL.facts.ballotsCast as number,
}

export { usd, usdShort, BASELINE_REVENUE_GROWTH, COST_GROWTH_BLENDED }

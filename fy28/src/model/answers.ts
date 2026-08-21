import { MODEL, project, newGrowthPerDollar, newGrowthToClose, usd, usdShort,
         type Assumptions } from './engine'

/** Every figure the plain-language answers page states, derived once.
 *
 *  The page is written for somebody who has never read a budget document, which makes it
 *  the easiest place in the tool to accidentally lie. So no number on it is typed by
 *  hand: each one is computed here from the same model the rest of the app runs on, and
 *  each answer names the arithmetic that produced it. If the model changes, the plain
 *  English changes with it. */

const A = MODEL.assumptions
const T = MODEL.taxBase
const F = MODEL.fy27
const LEVY_CAP = 0.025

/* ---- the gap, year by year ---------------------------------------------- */

const raw = project(6, A)

/** Two different numbers get called "the gap", and conflating them is the single most
 *  common error in this conversation.
 *
 *  `cumulative` is what the projection produces: how much more the schools need in that
 *  year than today's revenue line delivers. `fresh` is the part that is NEW that year —
 *  the cumulative figure less what last year's shortfall would already have grown to.
 *  A resident hearing "$1.2M in FY29" reasonably assumes it is on top of FY28's $613k.
 *  It is not; it includes it. */
export const GAPS = raw.map((y, i) => ({
  fy: y.fy,
  cumulative: Math.round(y.deficit),
  fresh: Math.round(i === 0 ? y.deficit : y.deficit - raw[i - 1].deficit * (1 + y.growthRate)),
  growthRate: y.growthRate,
}))

export const GAP = GAPS[0].cumulative

/** Blended rate at which everything the district buys gets more expensive. */
const expense = MODEL.expenseBase as Record<string, number>
const expenseTotal = Object.values(expense).reduce((s, v) => s + v, 0)
export const COST_GROWTH = (Object.keys(expense) as (keyof Assumptions)[])
  .reduce((s, k) => s + (expense[k] / expenseTotal) * (A[k] as number), 0)
export const REVENUE_CAP = LEVY_CAP
export const RATE_GAP = COST_GROWTH - LEVY_CAP

/** How long a permanent saving of `amount` keeps the gap closed.
 *
 *  A saving is not frozen: a job you do not fill never gets its raise, a contract you
 *  cancel never gets its increase. So the saving grows too, at `growth` — the rate the
 *  thing being given up would have grown at. It still loses, because the gap grows from a
 *  much larger base. That is the whole reason one-time answers do not stay closed. */
export function yearsCovered(amount: number, growth: number): number {
  let n = 0
  for (let i = 0; i < GAPS.length; i++) {
    if (amount * (1 + growth) ** i >= GAPS[i].cumulative) n++
    else break
  }
  return n
}

/** The first year a saving of `amount` stops covering the gap, and what is short by then. */
export function shortfallAfter(amount: number, growth: number) {
  const n = yearsCovered(amount, growth)
  const i = Math.min(n, GAPS.length - 1)
  return { fy: GAPS[i].fy, short: Math.round(GAPS[i].cumulative - amount * (1 + growth) ** i) }
}

/* ---- what each idea is actually worth ------------------------------------ */

const admin = MODEL.levers.find(l => l.id === 'admin_cut')!
const health = MODEL.levers.find(l => l.id === 'health_design')!
const tech = MODEL.levers.find(l => l.id === 'tech_cut')!

/** Sports, band, chorus, art and clubs — everything currently being paid for.
 *
 *  Only what is funded can be saved. Athletics as a whole costs $466,244; the adopted
 *  FY27 budget already cut $233,922 of that, and you cannot cut the same money twice. */
const extraItems = MODEL.programs.filter(p =>
  ['athletics', 'arts', 'activities'].includes(p.cat)
  && (p.status === 'funded' || p.status === 'restoring'))
  .sort((a, b) => b.cost - a.cost)

/** The catalogue's names are written for a budget reader — "0.6 -> 1.0 Music Teacher".
 *  This page is not for a budget reader. Same lines, same money, said out loud. */
const PLAIN: Record<string, string> = {
  athletics_remaining: 'Every sport still being paid for, and its coaches',
  hs_music_program: 'The high school band and chorus',
  art_supplies: 'Art supplies, all four schools',
  music_supplies: 'Instruments, sheet music, repairs',
  music_lhs_04: 'Putting the high school music teacher back to full time',
  hs_advisors: 'Every club and after-school advisor',
}

export const EXTRACURRICULAR = {
  items: extraItems.map(p => ({ label: PLAIN[p.id] ?? p.name, amount: p.cost })),
  total: Math.round(extraItems.reduce((s, p) => s + p.cost, 0)),
  fte: Math.round(extraItems.reduce((s, p) => s + p.fte, 0) * 10) / 10,
  alreadyCut: MODEL.facts.athleticsAlreadyCut as number,
  wholeProgram: MODEL.extras.find(e => e.cat === 'athletics')?.total ?? 0,
}

const lawfulRungs = admin.rungs!.filter(r => !r.blocked)

/** A few of the ladder's labels are budget-document shorthand. On a page written for
 *  somebody who has never seen the ladder, the line has to say what the person does. */
const ROLE_SUB: Record<string, string> = {
  hr: 'Hiring, contracts, benefits, licensure — for the whole district',
  business_clerical: 'Payroll and accounts payable for roughly 250 employees',
  sped_clerical: 'IEP scheduling, notices and compliance paperwork',
  curriculum: 'Curriculum, professional development and state testing, four schools',
  sec_ps: 'The Primary School has one office person. This is her.',
  sec_es: 'Turkey Hill has one office person. This is her.',
  sec_ms: 'The middle school front office',
  sec_hs: 'The high school front office',
  clerk_ms: 'Middle school attendance, scheduling and records',
  clerk_hs: 'High school attendance, scheduling, transcripts and records',
  office: 'Every school’s office supplies, plus dues, meetings, postage and ads',
  transition: 'A budgeted allowance for leadership transition work — not a person',
  legal: 'Mostly special education disputes and personnel matters',
  stipends: 'Remote coordinator, curriculum leadership, $800 of overtime per office',
  // The protected rungs carry long explanatory notes written for the ladder on the
  // Adjust page, including cross-references that mean nothing here. One line each.
  superintendent: 'Required by state law. A district without one is not a district.',
  business_mgr: 'Books, DESE filings and payroll. There is one.',
  sped_admin: 'Massachusetts requires a district special education administrator',
  principal_hs: 'One line covering both posts. Every school must have a principal.',
  principal_ms: 'One line covering both posts. Every school must have a principal.',
  principal_ps: 'One line covering both posts. Already shares its assistant principal.',
  principal_es: 'One line covering both posts. Already shares its assistant principal.',
}
const roster = (rs: typeof lawfulRungs) => rs
  .slice().sort((a, b) => b.amount - a.amount)
  .map(r => ({ id: r.id, label: r.label, sub: ROLE_SUB[r.id] ?? r.note,
               amount: r.amount, fte: r.fte }))

export const ADMIN = {
  /** The ten jobs, largest first. Named, because "cut the extra administrators" only
   *  sounds easy for as long as nobody has to read the list out. */
  people: roster(lawfulRungs.filter(r => r.fte > 0)),
  /** The four that are lines rather than people. */
  lines: roster(lawfulRungs.filter(r => r.fte === 0)),
  /** What the ladder cannot reach: roles the Commonwealth requires a district to have. */
  protectedRoles: roster(admin.rungs!.filter(r => r.blocked)),
  protectedTotal: Math.round(admin.rungs!.filter(r => r.blocked)
    .reduce((s, r) => s + r.amount, 0)),
  total: MODEL.buckets.admin,
  shareOfBudget: MODEL.buckets.admin / F.lps_appropriation,
  lawful: Math.round(lawfulRungs.reduce((s, r) => s + r.amount, 0)),
  lawfulCount: lawfulRungs.length,
  lawfulFte: lawfulRungs.reduce((s, r) => s + r.fte, 0),
  /** The rungs that are lines rather than people — the cut everybody assumes is there. */
  paperOnly: Math.round(lawfulRungs.filter(r => r.fte === 0)
    .reduce((s, r) => s + r.amount, 0)),
  benchmark: admin.benchmark,
}

/** "The overpaid admins" as residents mean it: the people with titles, not the clerks.
 *  Nine budget lines covering the superintendent, the business manager, the two district
 *  directors, the HR specialist and all four principals' offices. */
const LEADERS = ['superintendent', 'business_mgr', 'sped_admin', 'curriculum', 'hr',
                 'principal_ps', 'principal_es', 'principal_ms', 'principal_hs']
const leaderRungs = admin.rungs!.filter(r => LEADERS.includes(r.id))
  .sort((a, b) => b.amount - a.amount)
export const LEADERSHIP = {
  lines: leaderRungs.map(r => ({ label: r.label, amount: r.amount })),
  payroll: Math.round(leaderRungs.reduce((s, r) => s + r.amount, 0)),
  /** Pay cut, as a share of that payroll, needed to close each year's gap. */
  cutFor: GAPS.slice(0, 4).map((g, i) => ({
    fy: g.fy,
    pct: g.cumulative / (leaderRungs.reduce((s, r) => s + r.amount, 0) * 1.04 ** i),
  })),
}

/** Everyone the district pays, including the administrators above. The FY27 document
 *  publishes one salary total, not a teachers-only line, so this is the honest
 *  denominator and the answer has to say so. */
export const PAYROLL = {
  total: Math.round(expense.salaries + F.stm_addbacks),
  fivePercent: Math.round((expense.salaries + F.stm_addbacks) * 0.05),
  cutFor: GAPS.slice(0, 3).map((g, i) => ({
    fy: g.fy,
    pct: g.cumulative / ((expense.salaries + F.stm_addbacks) * 1.04 ** i),
  })),
}

const perPoint = health.basis * 0.01 * (health.mitigation ?? 1)
const familyPremium = MODEL.health.plans[0].family * 12
export const HEALTH = {
  budget: MODEL.health.budget,
  employeeShare: 1 - MODEL.health.townShare,
  perPoint: Math.round(perPoint),
  grossPerPoint: Math.round(health.basis * 0.01),
  /** Expressed as a share of the premium, never as "points" — a reader who does not
   *  already know the difference between 15% and 15 percentage points is exactly the
   *  reader this page is for. */
  pointsToClose: GAP / perPoint,
  shareNeeded: (1 - MODEL.health.townShare) + (GAP / perPoint) / 100,
  maxModelled: health.cap,
  maxShare: health.max / 100,
  costPerFamily: Math.round((GAP / perPoint) * familyPremium * 0.01),
  familyPremium: Math.round(familyPremium),
  pctOfBudget: GAP / MODEL.health.budget,
  rise: A.health,
}

export const TECH = {
  basis: tech.basis,
  atMax: tech.cap,
  pctToClose: GAP / tech.basis,
}

/* ---- development --------------------------------------------------------- */

/** Least new-growth revenue per year that keeps the gap closed for `years` running.
 *
 *  Bisection rather than algebra because new growth enters the levy limit, compounds
 *  inside it, and then reaches the schools only through their share of town revenue.
 *  Solving that by hand invites exactly the error this tool already made once. */
function growthToHold(years: number): number {
  let lo = 0, hi = 20_000_000
  for (let i = 0; i < 80; i++) {
    const mid = (lo + hi) / 2
    const worst = Math.max(...project(years, { ...A, new_growth: mid }).map(y => y.deficit))
    if (worst <= 0) hi = mid; else lo = mid
  }
  return hi
}

const mixValue = T.archetypes.find(a => a.id === 'mix')?.value ?? T.mixValue
const asValue = (revenue: number) => (revenue * 1000) / T.rate

function devPlan(years: number) {
  const needed = growthToHold(years)
  const extra = needed - T.currentNewGrowthRevenue
  const value = asValue(extra)
  return {
    needed: Math.round(needed),
    extra: Math.round(extra),
    value: Math.round(value),
    developments: value / mixValue,
    businesses: value / T.avgCommercialValue,
    homes: value / T.avgHomeValue,
    /** Against the entire commercial, industrial and personal base the town has today. */
    shareOfBase: value / T.fy23.cipValue,
    vsAssumed: needed / T.currentNewGrowthRevenue,
    vsActual: needed / T.fy23.newGrowth,
    vsBest: needed / Math.max(...T.newGrowthHistory.map(h => h.amount)),
  }
}

export const DEVELOPMENT = {
  share: newGrowthPerDollar(A),
  closeFy28: newGrowthToClose(A),
  oneYear: devPlan(1),
  fiveYear: devPlan(5),
  tenYear: devPlan(10),
  mixValue,
  oneDevelopment: (mixValue * T.rate) / 1000,
  existingBase: T.fy23.cipValue,
  existingCount: T.businesses,
  history: T.newGrowthHistory,
  best: T.newGrowthHistory.reduce((a, b) => (b.amount > a.amount ? b : a)),
}

/* ---- the tax bill -------------------------------------------------------- */

const perThousand = (levyDollars: number) => (levyDollars * 1000) / T.totalValue
const onAverageHome = (levyDollars: number) =>
  Math.round((T.avgHomeValue * perThousand(levyDollars)) / 1000)

export const BILL = {
  average: T.avgHomeBill,
  averageValue: T.avgHomeValue,
  rate: T.rate,
  /** Adopting the maximum split rate: homes pay less, business pays more, town collects
   *  exactly the same. It is the only lever here that costs the schools nothing. */
  splitSaving: Math.round((T.avgHomeValue * (T.rate - T.splitRate.residential)) / 1000),
  splitBusinessCost: Math.round(T.splitRate.avgCommercialIncrease),
  splitResidentialRate: T.splitRate.residential,
  splitCommercialRate: T.splitRate.commercial,
  /** Debt the voters excluded from the cap for specific projects. It is temporary by
   *  design and leaves the bill when the projects are paid off — if nothing replaces it. */
  debt: F.excluded_debt,
  debtSaving: onAverageHome(F.excluded_debt),
  /** What funding each year's gap by townwide vote costs the average homeowner. */
  overrideCost: GAPS.map(g => ({ fy: g.fy, cost: onAverageHome(g.cumulative) })),
  failedOverrides: [
    { amount: MODEL.facts.overrideQ1.amount, cost: MODEL.facts.tier1TaxIncrease,
      yes: MODEL.facts.overrideQ1.yes, no: MODEL.facts.overrideQ1.no },
    { amount: MODEL.facts.overrideQ2.amount, cost: MODEL.facts.tier2TaxIncrease,
      yes: MODEL.facts.overrideQ2.yes, no: MODEL.facts.overrideQ2.no },
  ],
}

/** Relief available without touching the schools at all, and the year the school gap
 *  grows past it. Both halves matter: the first is real money off the bill, the second
 *  is why it is a reprieve rather than a fix. */
export const RELIEF = {
  total: BILL.splitSaving + BILL.debtSaving,
  outrunBy: BILL.overrideCost.find(o => o.cost > BILL.splitSaving + BILL.debtSaving)?.fy
    ?? null,
}

/* ---- bending a cost curve ------------------------------------------------ */

/** The other permanent answer, and the only one that does not need a dollar from
 *  anybody: make a cost stop growing at 9%. Health insurance is the candidate because it
 *  is the fastest-rising thing in the budget and the town, not the district, buys it. */
const bent = project(6, { ...A, health: LEVY_CAP + 0.015 })
export const BENT_HEALTH = {
  from: A.health,
  to: LEVY_CAP + 0.015,
  gaps: bent.map(y => ({ fy: y.fy, cumulative: Math.round(y.deficit) })),
  savedByFy32: Math.round(GAPS[4].cumulative - bent[4].deficit),
}

/* ---- what the salary line is actually made of ---------------------------- */

/** The teachers' agreement, read off the contract rather than inferred from the budget.
 *
 *  Source: sources/contracts/pdf/lea-teachers-2024-2027.pdf — Article XX §A.1 for the
 *  scale adjustments, Article XVI §4 for step advancement, Article XXV §A for the term.
 *  Kept here rather than in model.json because it is document-sourced fact, not something
 *  the projection pipeline derives; the scale itself is in
 *  sources/contracts/data/lea-teacher-salary-schedule.csv.
 *
 *  It matters to the pay-cut question because "a 5% pay cut" is a proposal about a number
 *  nobody votes on: the scale is bargained three years at a time, and this one runs out
 *  in the middle of the budget it is being discussed in. */
export const CONTRACT = {
  union: 'Lunenburg Education Association',
  covers: 'teachers, nurses, athletics and stipends',
  cola: [{ fy: 25, pct: 0.025 }, { fy: 26, pct: 0.040 }, { fy: 27, pct: 0.035 }],
  compound: 1.025 * 1.04 * 1.035 - 1,
  /** Average step on the 13-step scale — paid on top of the scale adjustment, to anyone
   *  not yet at the maximum. */
  avgStep: 0.0332,
  expires: 'June 30, 2027',
  noticeBy: 'November 1, 2026',
  bottom: 50_790, top: 102_459,   // FY25 Bachelor step 1 · Doctorate step 13
  /** A handful of real cells at FY27 rates, so "5%" can be said in dollars a person
   *  would recognise as their own pay. From the schedule CSV. */
  samples: [
    { label: 'A new teacher, bachelor’s, step 1', pay: 54_670 },
    { label: 'Master’s, step 5', pay: 72_441 },
    { label: 'Master’s, top of the scale', pay: 93_369 },
    { label: 'Doctorate, top of the scale', pay: 110_287 },
  ],
}

/** Where a pay cut of `pct` puts the salary scale, against the years of the contract.
 *
 *  A cut is only legible next to what it is cutting. Five per cent sounds modest until it
 *  is set beside a scale that moved 10.33% in three years, and severe until you notice it
 *  still leaves the scale above where it started. Both readings are true and the reader
 *  should get to have both. */
export function scaleAfterCut(pct: number) {
  let idx = 1
  const years = CONTRACT.cola.map(c => ({ fy: c.fy, index: (idx *= 1 + c.pct) }))
  const after = idx * (1 - pct)
  return {
    years, after,
    /** Against each contract year's scale, where the cut lands. */
    vs: [{ fy: 24, index: 1 }, ...years].map(y => ({ fy: y.fy, delta: after / y.index - 1 })),
  }
}

/** The FY28 gap as a function of what the next teachers' contract settles at.
 *
 *  This is the lever the rest of the page does not have. Every other answer moves money
 *  that is already committed; the successor agreement is the one large number in FY28
 *  that nobody has written down yet — the current contract expires at the end of FY27. */
export const SETTLEMENT = {
  /** What the projection already assumes the salary line does. */
  assumed: A.salaries,
  assumedCost: Math.round((expense.salaries + F.stm_addbacks) * A.salaries),
  rates: [0, 0.025, 0.03, 0.035, A.salaries, 0.05].map(r => ({
    rate: r,
    gap: Math.round(project(6, { ...A, salaries: r })[0].deficit),
    fy32: Math.round(project(6, { ...A, salaries: r })[4].deficit),
  })),
  /** What half a percentage point on the settlement is worth in FY28. */
  perHalfPoint: Math.round(
    project(1, { ...A, salaries: A.salaries + 0.005 })[0].deficit
    - project(1, { ...A, salaries: A.salaries })[0].deficit),
}

/* ---- the scoreboard ------------------------------------------------------ */

export interface Option {
  id: string; label: string; saves: number; growth: number
  costs: string; permanent?: boolean
}

/** Every idea on the page, priced the same way, so they can be read against each other.
 *  `growth` is the rate the saved thing would itself have grown at — see yearsCovered. */
export const OPTIONS: Option[] = [
  { id: 'paper', label: 'Cut the office lines only — dues, legal, postage, supplies, stipends',
    saves: ADMIN.paperOnly, growth: A.other,
    costs: 'Nothing anybody would see' },
  { id: 'extras', label: 'Cut every sport, club, band, chorus and art supply',
    saves: EXTRACURRICULAR.total, growth: A.salaries,
    costs: `${EXTRACURRICULAR.fte} jobs · no teams, no band, no clubs` },
  { id: 'tech', label: 'Cut 60% of all software, licences and student devices',
    saves: TECH.atMax, growth: A.other,
    costs: 'State testing, IEP and payroll systems run on these' },
  { id: 'health', label: `Employees pay ${(HEALTH.maxShare * 100).toFixed(0)}% of the health premium instead of ${(HEALTH.employeeShare * 100).toFixed(0)}%`,
    saves: HEALTH.maxModelled, growth: A.health,
    costs: `About ${usd(Math.round((HEALTH.maxShare - HEALTH.employeeShare) * 100
      * familyPremium * 0.01))} a year out of a family’s pay` },
  { id: 'admin', label: 'Cut every administrator and school secretary the law allows',
    saves: ADMIN.lawful, growth: A.salaries,
    costs: `${ADMIN.lawfulFte} jobs · no front office in any of the four schools` },
  { id: 'leaders', label: `A ${(LEADERSHIP.cutFor[0].pct * 100).toFixed(0)}% pay cut for every administrator`,
    saves: GAP, growth: A.salaries,
    costs: 'Every one of them is below market the next morning' },
  { id: 'pay', label: 'A 5% pay cut for everyone who works in the schools',
    saves: PAYROLL.fivePercent, growth: A.salaries,
    costs: 'Roughly 250 employees, and a bargaining fight for each' },
  { id: 'override', label: `A townwide vote to raise taxes by ${usdShort(GAP)}`,
    saves: GAP, growth: 0.03,
    costs: `$${BILL.overrideCost[0].cost} a year on the average home` },
  { id: 'build', label: `Build ${DEVELOPMENT.fiveYear.developments.toFixed(0)} new commercial developments a year, every year`,
    saves: GAP, growth: 0.06, permanent: true,
    costs: `${usdShort(DEVELOPMENT.fiveYear.value)} of new business a year — `
      + `${DEVELOPMENT.fiveYear.vsBest.toFixed(1)}× the town’s best year since FY${DEVELOPMENT.history[0].fy}` },
]

import raw from '../data/model.json'

export type Mandate = 'legal' | 'contract' | 'discretionary'
export type Status = 'cut' | 'restoring' | 'unfunded' | 'funded'

export interface Sport {
  name: string; level: string; students: number; cost: number; deckCost: number
}
/** One nameable thing a ladder lever gives up, in the order it would be given up. */
export interface LeverRung {
  id: string; label: string; amount: number; fte: number; note: string; blocked: boolean
}
export interface Lever {
  id: string; name: string; kind: 'revenue' | 'saving'; unit: string
  max: number; step: number; default: number; basis: number; basisKnown?: boolean
  cap: number; isPercent?: boolean; what: string; caveat: string; benchmark: string
  current?: number; selfFunding?: number | null; isPercentPoint?: boolean
  peakFee?: number; peakYield?: number; currentYield?: number
  /** Share of the gross saving the district actually keeps (statutory giveback). */
  mitigation?: number
  /** Cut a named line at a time rather than a percentage of an aggregate. */
  isLadder?: boolean
  rungs?: LeverRung[]
}

/** One rolled-up figure, rebuilt from the lines that make it up. */
export interface Derivation {
  id: string; kind: 'lines' | 'arithmetic' | 'catalog' | 'ladder'
  question: string; label: string; answer: string; notes: string[]
  scenario: string; source: string
  total: number; expected: number; delta: number; reconciled: boolean
  lines?: { group: string; item: string; amount: number
            note?: string; history?: Record<string, number> }[]
  lineCount?: number
  terms?: { ref: string; label: string; sign: number; amount: number }[]
  entries?: { name: string; amount: number; status: string; source: string
              estimated: boolean }[]
  estimatedAmount?: number
  rungs?: (LadderRung & { running: number })[]
}

export interface ScenarioTotal {
  column: string; label: string; stated: number; detailLines: number
  salaryReserve: number; rebuilt: number; delta: number; reconciled: boolean
}

/** One rung on the ladder from "what was funded" to "what the whole program costs". */
export interface LadderRung {
  id: string; label: string; sub: string; scenario: string
  add: number | null; addLabel?: string; total: number
  published: boolean; selfFundFee: number | null; coverageNow: number
}

export interface Peer {
  id: string; name: string; subject: boolean; enrollment: number
  budget: number; changePct: number; healthPct: number | null
  chapter70Pct: number | null; overrideStatus: string
  protected: string[]; sacrificed: string[]; note: string; source: string
}

export interface Program {
  id: string; name: string; cat: string; cost: number; fte: number
  mandate: Mandate; status: Status; tier: number; source: string
  impact: string; repeatable?: number
}
export interface Assumptions {
  salaries: number; health: number; transport: number; sped_tuition: number
  utilities: number; other: number
  levy_growth: number; new_growth: number; state_aid_growth: number
  local_receipts_growth: number; school_share: number
  athletic_fee_revenue: number; override_amount: number
}

export const MODEL = raw as unknown as {
  categories: Record<string, { label: string; color: string }>
  programs: Program[]
  presets: Record<string, { name: string; why: string; order: string[] }>
  assumptions: Assumptions
  fy27: Record<string, number>
  expenseBase: Record<string, number>
  scenarios: Record<string, number>
  peers: Peer[]
  sports: Sport[]
  otherPrograms: { id: string; name: string; cost: number; participants: number
                   participantsKnown: boolean; note: string }[]
  feeBenchmarks: { district: string; fee: number | null; note: string; local: boolean }[]
  levers: Lever[]
  athletics: { levelService: number; adopted: number; travel: number; remaining: number
               participations: number; chargeableParticipations: number
               msParticipations: number; perSportTotal: number
               peakFee: number; peakRevenue: number; dropoffPer100: number
               ladder: LadderRung[] }
  buckets: Record<string, number>
  currentFees: {
    athletic: {
      effectiveFrom: string
      tiers: [string, number][]
      familyCap: number
      prior: { hs: [string, number][]; hsCap: number; ms: [string, number][]; source: string }
      source: string; sourcePublished: boolean; sourceNote: string
      notes: string[]; unresolved: string[]
    }
    bus: Record<string, number | string[]>
    hsParticipations: number; msParticipations: number
    effectiveAthletic: number; estimatedAthleticRevenue: number
    priorEffectiveAthletic: number; estimatedPriorAthleticRevenue: number
    feeIncreaseValue: number
    siblingMix: [string, number][]; waiverAssumption: number
    chargeableParticipations: number; estimatedFy26Revenue: number
  }
  feeAccounting: { established: string[]; unresolved: string[]; ask: string }
  taxBase: {
    rate: number; levy: number; totalValue: number
    residentialShare: number; cipShare: number
    avgHomeValue: number; avgHomeBill: number
    splitRate: { residential: number; commercial: number; avgCommercialIncrease: number }
    ch70: { foundationEnrollment: number; foundationBudget: number
            requiredContribution: number; aid: number; requiredNSS: number }
    archetypes: { id: string; name: string; value: number; plausible: boolean; note: string }[]
    localCostPerPupil: number; schoolShareOfBill: number; schoolShareOfBudget: number
    homesPerPupil: number; enrollment: number
    currentNewGrowthRevenue: number; currentNewGrowthValue: number; levyGrowth: number
    fy23: Record<string, number>
    businesses: number; employees: number; payroll: number
    avgCommercialValue: number; fy23NewValue: number
    commercialContext: { corridors: string[]; anchor: string; targets: string[]; constraint: string }
    newGrowthHistory: { fy: number; amount: number }[]
    valueByClass: { cls: string; fy23: number; fy22: number; change: number; pct: number }[]
    avgHomeHistory: { fy: number; rate: number; value: number; bill: number }[]
    excessLevyCapacity: { fy: number; amount: number }[]
    mixValue: number
    gapInBusinesses: Record<'fy28' | 'sustained', {
      value: number; developments: number; businesses: number; pctOfToday: number
      vsActualNewGrowth: number; fiveYearAdded: number; fiveYearTotal: number
      fiveYearPct: number
    }>
  }
  business: {
    formationHistory: { year: number; new: number; renewals: number; partial: boolean }[]
    summary: Record<string, number>
    categories: { category: string; count: number }[]
  }
  health: {
    plans: { id: string; name: string; deductible: string; network: string
             family: number; individual: number }[]
    townShare: number; rateIncrease: number
    enrolment: Record<string, number>; familyShare: number
    constraints: string[]; budget: number
  }
  headlines: { id: string; label: string; value: string; sub: string
               anchor: string; tone: 'critical' | 'good' | 'neutral' }[]
  conclusions: { n: number; anchor: string; headline: string; figure: string; body: string }[]
  headline: string
  extras: { cat: string; label: string; total: number; items: string[] }[]
  recommendation: {
    package: { id: string; name: string; value: number; why: string; difficulty: string }[]
    priorityWhy: string
    closing: string
  }
  peerLessons: { title: string; body: string }[]
  method: {
    derivations: Derivation[]
    scenarioTotals: ScenarioTotal[]
    scenarioNote: string
    sourceDoc: string
    sourceCodes: Record<string, string>
    scenarios: Record<string, string>
  }
  facts: Record<string, any>
  meta: Record<string, string>
}

/** Drop-off in participation per $100 charged ABOVE what is already charged, by lever.
 *  Fee levers are not interchangeable: a bus rider quits sooner than an athlete. */
export const LEVER_DROPOFF: Record<string, number> = {
  bus_fees: 8, activity_fees: 6, athletic_fees: 5,
}

/** Where a lever sits when nothing has been changed — today's fee, today's split, no cut.
 *  The app opens here so that "found so far" starts at $0 and every dollar on the panel is
 *  a dollar the user chose. */
export function leverStart(l: Lever): number {
  if (l.isLadder) return 0
  if (l.isPercentPoint) return l.current ?? 0
  if (l.isPercent) return 0
  return l.current ?? 0
}

/** What one lever is worth at value `v`. Shared by the workbench, the running total and
 *  the floating panel so the three cannot disagree. */
export function leverYield(l: Lever, v: number, payers?: number): number {
  // A ladder is worth the sum of the rungs actually taken. Blocked rungs are displayed
  // so the wall is visible, but they are never reachable and never counted.
  if (l.isLadder) return ladderTaken(l, v).reduce((s, r) => s + r.amount, 0)
  if (l.isPercentPoint) {
    const gross = l.basis * ((v - (l.current ?? 0)) / 100)
    return Math.min(gross * (l.mitigation ?? 1), l.cap)
  }
  if (l.isPercent) return Math.min(l.basis * (v / 100), l.cap)
  const n = payers ?? l.basis
  const cur = l.current ?? 0
  const drop = LEVER_DROPOFF[l.id] ?? 5
  const rev = (f: number) => {
    const inc = Math.max(0, f - cur)
    return f * n * 0.88 * Math.max(0, 1 - (inc / 100) * (drop / 100))
  }
  return Math.min(Math.max(0, rev(v) - rev(cur)), l.cap)
}

/** Every rung, in order — including the ones it is not lawful to take.
 *
 *  Blocking those in the interface was the wrong call: "what would cutting the
 *  superintendent even save?" is a question a resident is entitled to a number for, and
 *  refusing to compute it reads as evasion rather than as rigour. So they are selectable,
 *  they are counted, and they are flagged everywhere they appear. */
export const ladderRungs = (l: Lever): LeverRung[] => l.rungs ?? []

/** The rungs a budget the district could actually adopt can reach. */
export const ladderLawful = (l: Lever): LeverRung[] =>
  (l.rungs ?? []).filter(r => !r.blocked)

/** Selected rungs that a lawful budget could not include. */
export const ladderUnlawful = (l: Lever, mask: number): LeverRung[] =>
  ladderTaken(l, mask).filter(r => r.blocked)

/* A ladder lever's value is a bit set over its cuttable rungs, not a depth.
 *
 * Two things have to be true at once: the slider has to keep working as a slider —
 * drag it and you walk down the list in order — and each position has to be
 * independently cuttable, because "cut the HR specialist but keep the middle school
 * clerk" is a real position somebody holds. Storing the selection as a bit set gives
 * both, at the cost of the slider being lossy: drag it after hand-picking and it
 * overwrites your picks with the first N in order. That trade is deliberate. */
export const ladderTaken = (l: Lever, mask: number): LeverRung[] =>
  ladderRungs(l).filter((_, i) => (mask >> i) & 1)

/** The mask the slider produces at depth `n` — the first n rungs, in order. */
export const ladderMask = (n: number) => n <= 0 ? 0 : (1 << Math.round(n)) - 1

/** Flip one rung on or off without disturbing the others. */
export const ladderToggle = (mask: number, i: number) => mask ^ (1 << i)

/** How many rungs are taken — what the slider shows. */
export const ladderCount = (mask: number) => {
  let n = 0
  for (let m = mask; m; m >>= 1) n += m & 1
  return n
}

/** True when the taken rungs are exactly the first N, i.e. the slider still describes
 *  the selection. Once it is false the UI has to say so. */
export const ladderContiguous = (mask: number) =>
  mask === ladderMask(ladderCount(mask))

/** One line on the floating panel: something the reader has actually changed. */
export interface AppliedItem {
  id: string; label: string; detail: string; amount: number
  kind: 'lever' | 'cut' | 'override'
  /** Section id of the control that produced this, so the panel can jump you to it. */
  anchor?: string
}

const BUCKETS = ['salaries', 'health', 'transport', 'sped_tuition', 'utilities', 'other'] as const
type Bucket = typeof BUCKETS[number]

export interface YearProjection {
  fy: number; levelService: number; available: number
  appropriation: number; deficit: number; growthRate: number
}

/** Project level-service cost and available revenue, year by year.
 *  `cutsByYear` permanently reduces the salary base from the following year on. */
export function project(
  years: number, a: Assumptions, cutsByYear: Record<number, number> = {},
): YearProjection[] {
  const f = MODEL.fy27
  const buckets: Record<Bucket, number> = { ...MODEL.expenseBase } as Record<Bucket, number>
  buckets.salaries += f.stm_addbacks

  let levy = f.levy_limit
  let aid = f.state_aid
  let receipts = f.local_receipts
  let approp = f.lps_appropriation + f.stm_appropriation
  // constant wedge between gross revenue and what is left to appropriate
  const wedge = f.levy_limit + f.excluded_debt + f.state_aid + f.local_receipts - f.omnibus

  const out: YearProjection[] = []
  let prevTownAvailable = f.omnibus

  for (let i = 0; i < years; i++) {
    const fy = 28 + i
    levy = levy * (1 + a.levy_growth) + a.new_growth
    aid *= 1 + a.state_aid_growth
    receipts *= 1 + a.local_receipts_growth
    const townAvailable = levy + f.excluded_debt + aid + receipts - wedge
    const growthRate = townAvailable / prevTownAvailable - 1
    prevTownAvailable = townAvailable

    approp = approp * (1 + growthRate) + a.override_amount
    const available = approp + a.athletic_fee_revenue

    for (const k of BUCKETS) buckets[k] *= 1 + a[k]
    const levelService = BUCKETS.reduce((s, k) => s + buckets[k], 0)

    out.push({
      fy, levelService: Math.round(levelService), available: Math.round(available),
      appropriation: Math.round(approp), deficit: Math.round(levelService - available),
      growthRate,
    })
    const cut = cutsByYear[fy] ?? 0
    if (cut) buckets.salaries -= cut
  }
  return out
}

/** Repeatable programs become numbered instances. */
export function expand(programs: Program[]): Program[] {
  const out: Program[] = []
  for (const p of programs) {
    const n = p.repeatable ?? 1
    for (let i = 0; i < n; i++) {
      out.push(n > 1
        ? { ...p, id: `${p.id}_${i + 1}`, name: `${p.name.replace(' (each 1.0)', '').replace(' (each further 1.0)', '')} #${i + 1}` }
        : { ...p })
    }
  }
  return out
}

export interface CutRecord extends Program { blocked: boolean }
export interface YearResult {
  fy: number; deficit: number; levelService: number; available: number
  cuts: CutRecord[]; cutTotal: number; unclosed: number; cumFte: number
}

/** Close each year's gap by cutting from the bottom of the priority ranking upward. */
export function runCascade(
  order: string[], a: Assumptions, years = 5, includeRestoring = true,
): YearResult[] {
  const rank = new Map(order.map((c, i) => [c, i]))
  const pool = expand(MODEL.programs)
    .filter(p => p.status === 'funded' || (includeRestoring && p.status === 'restoring'))
    .sort((x, y) =>
      (rank.get(y.cat) ?? 99) - (rank.get(x.cat) ?? 99)
      || x.tier - y.tier
      || x.cost - y.cost)

  const results: YearResult[] = []
  const cutsByYear: Record<number, number> = {}
  let cumFte = 0
  let idx = 0

  for (let i = 0; i < years; i++) {
    const proj = project(i + 1, a, cutsByYear)[i]
    let gap = proj.deficit
    const cuts: CutRecord[] = []
    while (gap > 0 && idx < pool.length) {
      const p = pool[idx++]
      if (p.mandate === 'legal') { cuts.push({ ...p, blocked: true }); continue }
      cuts.push({ ...p, blocked: false })
      gap -= p.cost
    }
    const cutTotal = cuts.filter(c => !c.blocked).reduce((s, c) => s + c.cost, 0)
    cumFte += cuts.filter(c => !c.blocked).reduce((s, c) => s + c.fte, 0)
    cutsByYear[proj.fy] = cutTotal
    results.push({
      fy: proj.fy, deficit: proj.deficit, levelService: proj.levelService,
      available: proj.available, cuts, cutTotal,
      unclosed: Math.max(0, gap), cumFte: Math.round(cumFte * 10) / 10,
    })
  }
  return results
}

/** First year in which a given program falls below the cut line. */
export function yearCut(results: YearResult[], id: string): number | null {
  for (const y of results)
    if (y.cuts.some(c => !c.blocked && (c.id === id || c.id.startsWith(id + '_'))))
      return y.fy
  return null
}

export const usd = (n: number) =>
  (n < 0 ? '-' : '') + '$' + Math.abs(Math.round(n)).toLocaleString('en-US')
export const usdShort = (n: number) => {
  const x = Math.abs(n)
  if (x >= 1e6) return (n < 0 ? '-' : '') + '$' + (x / 1e6).toFixed(2) + 'M'
  if (x >= 1e3) return (n < 0 ? '-' : '') + '$' + Math.round(x / 1e3) + 'k'
  return usd(n)
}

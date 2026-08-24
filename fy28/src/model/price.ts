import { MODEL, newGrowthPerDollar, leverYield, expand, usd, usdShort,
         type Lever, type Program } from './engine'
import { GAPS, ADMIN, PAYROLL, FEES, CONTRACT } from './answers'

/** What one number costs, on every lever at once.
 *
 *  The rest of this site answers "what happens over the next six years", and the honest
 *  complaint about that is that you have to take the projection on trust: a chain of
 *  growth rates compounding out to FY33 is not something a resident can check at the
 *  kitchen table, so the conclusions land as assertion.
 *
 *  This section deliberately gives up the projection. It asks one flat question — you
 *  need to find $500,000 next year; what does that take? — and answers it once per lever
 *  with a single division that is printed next to the answer. No compounding, no year
 *  after next, nothing to believe. If you accept the price of a teacher, the number of
 *  athletes, and the tax rate, every line below follows by arithmetic.
 *
 *  The point it makes is not any one row. It is that most of the levers people name at
 *  meetings have a CEILING far below the number, and the ceiling is what the argument
 *  is usually missing. */

const A = MODEL.assumptions
const T = MODEL.taxBase

/** The rungs the reader is asked to price. $500,000 is roughly next year's hole; $2M is
 *  FY31. A lower rung was tried and dropped: no user fee reaches $250,000 either, so it
 *  bought nothing the "how far it gets" bar does not already say. */
export const TARGETS = [500_000, 1_000_000, 1_500_000, 2_000_000]

/** Which projected year a given target is about, so the abstract number has an address. */
export function targetYear(target: number): { fy: number; over: boolean } {
  const hit = GAPS.find(g => g.cumulative >= target)
  return hit ? { fy: hit.fy, over: false } : { fy: GAPS[GAPS.length - 1].fy, over: true }
}

export type Bears = 'overhead' | 'families' | 'services' | 'staff' | 'taxpayers' | 'town'

export interface PriceRow {
  id: string
  bears: Bears
  /** The lever, named the way somebody says it out loud. */
  label: string
  /** What it takes to raise the target on this lever alone. One line, no hedging. */
  ask: string
  /** The same thing said in a unit a person can picture. */
  detail: string
  /** The division that produced it, printed so it can be checked. */
  math: string
  /** The most this lever can produce in one year, or null where there is no arithmetic
   *  ceiling (a ballot can be written for any amount; a pay cut can be any percentage). */
  ceiling: number | null
  /** Why the ceiling is where it is. */
  ceilingNote: string
  /** False when the target is simply beyond the lever, at any price. */
  reachable: boolean
  /** Anchor of the question on this page that works the lever out in full. */
  anchor?: string
  /** The actual things being given up, named.
   *
   *  Aggregates make cuts sound easy. "$500,000 of programs" is a number somebody can
   *  nod along to; "every sport still funded, the band, the chorus, art supplies and the
   *  student laptops" is the same fact and nobody nods. Where a lever cuts nameable
   *  things, the card has to print their names at full size rather than a count. */
  items?: { label: string; amount: number }[]
  /** Something the card would mislead without. Rendered in the reader's face, not as a
   *  footnote: an overlap with another card, or money that leaves with the saving. */
  caveat?: string
}

/* ---- inversions ---------------------------------------------------------- */

/** The fee that raises `target` more than today's fee does.
 *
 *  Bisection rather than algebra: the yield curve bends, because raising a fee drives
 *  some families off the program, and the drop-off rate differs by program. The
 *  upper bound is the self-funding fee where one exists — a fee may not lawfully raise
 *  more than the program costs — and the revenue peak where it does not. */
function feeFor(l: Lever, target: number): number | null {
  const top = l.selfFunding ?? l.peakFee ?? l.max
  if (target > leverYield(l, top)) return null
  let lo = l.current ?? 0, hi = top
  for (let i = 0; i < 60; i++) {
    const mid = (lo + hi) / 2
    if (leverYield(l, mid) < target) lo = mid; else hi = mid
  }
  return Math.ceil(hi / 5) * 5
}

/** Administration lines, largest first, until the target is met. Largest first because
 *  that is the fewest people — the friendliest possible reading of the idea. */
function adminFor(target: number) {
  const rungs = ADMIN.people.concat(ADMIN.lines).sort((a, b) => b.amount - a.amount)
  const taken: typeof rungs = []
  let sum = 0
  for (const r of rungs) {
    if (sum >= target) break
    taken.push(r); sum += r.amount
  }
  return { taken, sum, jobs: taken.filter(r => r.fte > 0).length,
           fte: Math.round(taken.reduce((s, r) => s + r.fte, 0) * 10) / 10, enough: sum >= target }
}

/** A couple of the catalogue's names are written for a budget reader. Same lines, same
 *  money, said out loud — matching the plain-language names used on the answers page. */
const PLAIN_CUT: Record<string, string> = {
  athletics_remaining: 'Every sport still being paid for, and its coaches',
  music_lhs_04: 'The high school music teacher, back to full time',
  music_supplies: 'Instruments, sheet music, repairs',
  art_supplies: 'Art supplies, all four schools',
  hs_advisors: 'Every club and after-school advisor',
}

/** Services cut from the bottom of the School Committee's own revealed ranking, which is
 *  the order the district has actually been cutting in. Same pool and same sort as the
 *  cascade on the Priorities page, so the two cannot disagree. */
function cutsFor(target: number) {
  const order = MODEL.presets.school_committee.order
  const rank = new Map(order.map((c, i) => [c, i]))
  const pool = expand(MODEL.programs)
    .filter(p => p.status === 'funded' || p.status === 'restoring')
    .sort((x, y) => (rank.get(y.cat) ?? 99) - (rank.get(x.cat) ?? 99)
      || x.tier - y.tier || x.cost - y.cost)
  const taken: Program[] = []
  let sum = 0
  for (const p of pool) {
    if (sum >= target) break
    if (p.mandate === 'legal') continue
    taken.push(p); sum += p.cost
  }
  const total = pool.filter(p => p.mandate !== 'legal').reduce((s, p) => s + p.cost, 0)
  return {
    taken, sum, total, enough: sum >= target,
    fte: Math.round(taken.reduce((s, p) => s + p.fte, 0) * 10) / 10,
  }
}

/* ---- the tax bill and the tax base --------------------------------------- */

const onAverageHome = (levyDollars: number) =>
  Math.round((T.avgHomeValue * ((levyDollars * 1000) / T.totalValue)) / 1000)

/** Schools do not get a dollar of new growth; they get their share of the town's total
 *  available revenue, a bit over half. Pricing development against the school gap without
 *  that share roughly doubles what a building appears to be worth. */
const SHARE = newGrowthPerDollar(A)

/** One home is very nearly a wash, and the arithmetic is close enough that the section
 *  has to show both halves rather than assert a verdict. */
const HOME = {
  paysToSchools: Math.round(T.avgHomeValue * (T.rate / 1000) * T.schoolShareOfBudget),
  costsInPupils: Math.round(T.localCostPerPupil / T.homesPerPupil),
}

/* ---- the price list ------------------------------------------------------ */

const feeCase = (id: string) => {
  const l = MODEL.levers.find(x => x.id === id)!
  const c = FEES.cases.find(x => x.id === id)!
  return { l, ceiling: Math.max(0, Math.round(c.gain)) }
}

const health = MODEL.levers.find(l => l.id === 'health_design')!
const tech = MODEL.levers.find(l => l.id === 'tech_cut')!
const perPoint = health.basis * 0.01 * (health.mitigation ?? 1)
const familyPremium = MODEL.health.plans[0].family * 12
const k = (n: number) => usdShort(n)
/** usdShort stops at millions, and the town's whole tax base is billions. */
const big = (n: number) =>
  n >= 1e9 ? `$${(n / 1e9).toFixed(2)} billion` : usdShort(n)

export function priceOut(target: number): PriceRow[] {
  const rows: PriceRow[] = []

  /* --- overhead --- */
  const admin = adminFor(target)
  rows.push({
    id: 'admin', bears: 'overhead', anchor: 'q5',
    label: 'Cut administration and school office staff',
    ask: admin.enough
      ? admin.jobs === admin.taken.length
        ? `${admin.jobs} people's jobs`
        : `${admin.jobs} people's jobs and ${admin.taken.length - admin.jobs} other lines`
      : `Not possible — every lawful cut is ${k(ADMIN.lawful)}`,
    detail: admin.enough
      ? `Largest salaries first — ${admin.fte} FTE, every one of them somebody doing a job today`
      : `All ${ADMIN.lawfulCount} lawful lines and ${ADMIN.lawfulFte} FTE, and still ${k(target - ADMIN.lawful)} short`,
    math: admin.enough
      ? `${admin.taken.length} lines totaling ${usd(admin.sum)}, largest first`
      : `${usd(ADMIN.lawful)} is every line the law lets the district cut`,
    ceiling: ADMIN.lawful,
    ceilingNote: 'The rest of administration is roles the Commonwealth requires a district to have',
    reachable: admin.enough,
    items: (admin.enough ? admin.taken : ADMIN.people.concat(ADMIN.lines))
      .map(r => ({ label: r.label, amount: r.amount })),
  })

  const techPct = target / tech.basis
  rows.push({
    id: 'tech', bears: 'overhead',
    label: 'Cut software, licenses and student devices',
    ask: techPct <= 0.6 ? `${Math.round(techPct * 100)}% of everything technology`
      : `Not possible — 60% of it is ${k(tech.cap)}`,
    detail: techPct <= 0.6
      ? 'Device leases, networking, and the systems payroll and IEPs run on'
      : `Cutting technology to the bone leaves you ${k(target - tech.cap)} short`,
    math: techPct <= 0.6
      ? `${usd(target)} ÷ ${usd(tech.basis)} of technology spend = ${(techPct * 100).toFixed(0)}%`
      : `60% of ${usd(tech.basis)} of technology spend is ${usd(tech.cap)}`,
    ceiling: tech.cap,
    ceilingNote: 'Past 60% the state testing, IEP and payroll systems stop running',
    reachable: techPct <= 0.6,
  })

  /* --- families --- */
  for (const [id, label, unit, per] of [
    ['athletic_fees', 'Raise athletics fees', 'a season, per sport, per child', 'athlete'],
    ['activity_fees', 'Charge for band, music and clubs', 'per student, per activity', 'student'],
    ['bus_fees', 'Raise bus fares', 'a year, per rider', 'rider'],
  ] as const) {
    const { l, ceiling } = feeCase(id)
    const fee = feeFor(l, target)
    rows.push({
      id, bears: 'families', anchor: 'q4', label,
      ask: fee !== null ? `$${fee} ${unit}` : `Not possible — the most it can ever raise is ${k(ceiling)}`,
      detail: fee !== null
        ? `Up from $${l.current ?? 0} today, from about ${l.basis} ${per}s`
        : `Even at the highest fee that raises anything, you are ${k(target - ceiling)} short`,
      math: fee !== null
        ? `about ${l.basis} ${per}s × $${fee}, less the ones who stop, less what is already collected`
        : `${usd(ceiling)} is everything above today's $${l.current ?? 0}`,
      ceiling,
      ceilingNote: l.selfFunding !== null
        ? 'A fee may not lawfully raise more than the program costs'
        : 'Past this fee, enough riders quit that the money goes down, not up',
      reachable: fee !== null,
    })
  }

  /* --- services --- */

  /* Athletics gets its own card as well as its line inside the general one.
   *
   * It is the single most argued-about number in this budget and the one most often
   * quoted wrong, because three different figures all get called "athletics": what the
   * whole program costs, what the adopted budget still pays for, and what a fee could
   * raise against it. Left as one line among seven inside "cut programs" it is invisible;
   * given a card it can carry the fact that most of it has already been cut.
   *
   * Deliberately NOT removed from the cuts row. It genuinely is the first thing that
   * ranking gives up, and taking it out would misstate the order the district actually
   * cuts in. The overlap is real, so the card says so rather than hiding it. */
  const ath = MODEL.facts as Record<string, number>
  const athRemaining = ath.athleticsRemaining
  const athFees = Math.round(FEES.cases[0].currentYield)
  rows.push({
    id: 'athletics', bears: 'services', anchor: 'q3',
    label: 'Cut athletics — every remaining sport',
    ask: target <= athRemaining
      ? `All ${MODEL.sports.length} sports, and ${MODEL.athletics.participations} student-seasons`
      : `Not possible — everything still funded is ${k(athRemaining)}`,
    detail: target <= athRemaining
      ? `Every team, every coach, and the 1.5 jobs that run them`
      : `${MODEL.athletics.participations} student-seasons across `
        + `${MODEL.sports.length} sports, every coach, and the 1.5 jobs that run them — `
        + `all of it gone, and you are still ${k(target - athRemaining)} short`,
    math: `${usd(ath.athleticsTotal)} of athletics, less the ${usd(ath.athleticsAlreadyCut)} `
      + `the adopted FY27 budget already cut = ${usd(athRemaining)} still being paid for`,
    ceiling: athRemaining,
    ceilingNote: 'Transportation, half the trainer and middle school sports are already '
      + 'gone — the same money cannot be cut twice',
    reachable: target <= athRemaining,
    caveat: `This is the same money as the first line inside “cut programs” beside it — `
      + `the two cards overlap, so do not add them together. Athletics also collects about `
      + `${usd(athFees)} in fees today, which stops being collected the moment the sports `
      + `stop; how that revenue is accounted against this line is not published.`,
  })

  const cuts = cutsFor(target)
  rows.push({
    id: 'cuts', bears: 'services', anchor: 'q3',
    label: 'Cut programs, in the order the district already cuts them',
    ask: cuts.enough ? `${cuts.taken.length} programs and ${cuts.fte} jobs`
      : `Not possible — everything cuttable is ${k(cuts.total)}`,
    detail: cuts.enough
      ? `Taken lowest-priority first, in the order the School Committee's own budgets `
        + `have been cutting things:`
      : `That is every discretionary program in the district, and still ${k(target - cuts.total)} short`,
    math: cuts.enough
      ? `${cuts.taken.length} lines totaling ${usd(cuts.sum)} — the nearest you can land `
        + `without cutting a fraction of a teacher`
      : `${usd(cuts.total)} is every discretionary program the district funds`,
    ceiling: cuts.total,
    ceilingNote: 'What remains is special education and other services required by law',
    reachable: cuts.enough,
    items: cuts.taken.map(p => ({ label: PLAIN_CUT[p.id] ?? p.name, amount: p.cost })),
    caveat: 'The first line is athletics, which also has a card of its own. Same money '
      + 'counted once, shown twice — do not add the two cards together.',
  })

  /* --- staff --- */
  const points = target / perPoint
  const share = health.current! + points
  rows.push({
    id: 'health', bears: 'staff', anchor: 'q8',
    label: 'Move health premium onto employees',
    ask: share <= health.max ? `Employees pay ${share.toFixed(1)}% instead of ${health.current}%`
      : `Not possible — even at ${health.max}% it is ${k(health.cap)}`,
    detail: share <= health.max
      ? `About ${usd(Math.round(points * familyPremium * 0.01))} a year out of a school employee's pay`
      : `Doubling what employees pay leaves you ${k(target - health.cap)} short`,
    math: `${usd(target)} ÷ ${usd(Math.round(perPoint))} kept per point = ${points.toFixed(1)} points`,
    ceiling: health.cap,
    ceilingNote: 'Beyond about 40% the plan stops being competitive and the town cannot hire',
    reachable: share <= health.max,
  })

  const payPct = target / PAYROLL.total
  rows.push({
    id: 'pay', bears: 'staff', anchor: 'q7',
    label: 'Cut everyone’s pay',
    ask: `${(payPct * 100).toFixed(1)}% off every salary in the district`,
    detail: `${usd(Math.round(CONTRACT.samples[1].pay * payPct))} a year from a teacher `
      + `at the middle of the scale, and a bargaining fight for each of roughly 250 employees`,
    math: `${usd(target)} ÷ ${usd(PAYROLL.total)} of payroll = ${(payPct * 100).toFixed(1)}%`,
    ceiling: null,
    ceilingNote: 'No arithmetic ceiling — but every dollar of it is bargained, not decided',
    reachable: true,
  })

  /* --- taxpayers --- */
  const bill = onAverageHome(target)
  rows.push({
    id: 'override', bears: 'taxpayers', anchor: 'q10',
    label: 'Vote to raise taxes',
    ask: `$${bill} a year on the average home`,
    detail: `$${Math.round(bill / 12)} a month, on a bill of $${T.avgHomeBill.toLocaleString('en-US')} `
      + `— and it needs a townwide majority, which the last two asks did not get`,
    math: `${usd(target)} spread over ${big(T.totalValue)} of property = `
      + `$${((target * 1000) / T.totalValue).toFixed(2)} per $1,000 of value`,
    ceiling: null,
    ceilingNote: 'No arithmetic ceiling — an override can be written for any amount a majority will pass',
    reachable: true,
  })

  /* --- the town itself --- */
  const revenue = target / SHARE
  const value = (revenue * 1000) / T.rate
  const devs = value / T.mixValue
  rows.push({
    id: 'build', bears: 'town', anchor: 'q9',
    label: 'Build commercial development',
    ask: `${usdShort(value)} of new commercial value, built every year`,
    detail: `About ${devs.toFixed(0)} developments a year — one every ${Math.round(365 / devs)} days, `
      + `forever, against ${T.newGrowthHistory.length} recent years averaging `
      + `${usdShort(T.newGrowthHistory.reduce((s, h) => s + h.amount, 0) / T.newGrowthHistory.length)} of new growth`,
    math: `${usd(target)} ÷ ${(SHARE * 100).toFixed(0)}¢ the schools keep per dollar = `
      + `${usd(Math.round(revenue))} of new growth ÷ $${T.rate} per $1,000`,
    ceiling: null,
    ceilingNote: 'No ceiling in arithmetic — the ceiling is how much land the town has and what it wants to be',
    reachable: true,
  })

  rows.push({
    id: 'homes', bears: 'town',
    label: 'Build housing',
    ask: 'No number of homes raises it',
    detail: `The average home pays $${HOME.paysToSchools.toLocaleString('en-US')} a year toward `
      + `schools and brings $${HOME.costsInPupils.toLocaleString('en-US')} of school cost with it, `
      + `at ${T.homesPerPupil} homes per pupil. Housing grows the town; it does not close this.`,
    math: `$${T.avgHomeValue.toLocaleString('en-US')} × $${T.rate}/$1,000 × `
      + `${(T.schoolShareOfBudget * 100).toFixed(0)}% to schools = $${HOME.paysToSchools.toLocaleString('en-US')} `
      + `vs $${T.localCostPerPupil.toLocaleString('en-US')} ÷ ${T.homesPerPupil}`,
    // Deliberately not a ceiling of 0: a zero-width bar reading "gets you 0% of the way"
    // implies housing is a weak version of the same lever. It is not one — it is a wash,
    // and the two halves of the arithmetic above say so better than a bar can.
    ceiling: null,
    ceilingNote: 'Residential growth is roughly a wash — it pays about what it costs',
    reachable: false,
  })

  return rows
}

/** Everything that can reach the target, and everything that cannot. The headline of the
 *  section is this count, not any individual row. */
export function verdict(target: number) {
  const rows = priceOut(target)
  const short = rows.filter(r => !r.reachable)
  return {
    rows, short,
    reachable: rows.filter(r => r.reachable),
    /** The five overhead-and-fee levers at their ceilings, all at once.
     *
     *  Named for its contents rather than for what it represents. It was called
     *  "everything the district controls", which is plainly false — the School Committee
     *  also controls cutting programs, and does. What this actually is: the most that
     *  can be found without ending a program, cutting somebody's pay, or asking the
     *  Town. Smaller than most people expect, and the same number every year. */
    overheadAndFees: Math.round(rows
      .filter(r => r.bears === 'overhead' || r.bears === 'families')
      .reduce((s, r) => s + (r.ceiling ?? 0), 0)),
  }
}

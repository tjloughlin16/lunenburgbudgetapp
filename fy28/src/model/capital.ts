import { MODEL, usd } from './engine'

/** The FY27 capital programme, and what a free cash redirect strands.
 *
 *  This is the same rule as `capital_consequence()` in `model/freecash.py`, written a
 *  second time in a second language, which this project's own notes call a drift waiting
 *  to happen. It is here anyway for one reason: the model exports the answer at nine draw
 *  stops, $511,900 apart, and the slider a reader drags moves in hundreds. Snapping a
 *  popup to the nearest stop would show the wrong projects for almost every position of
 *  the control.
 *
 *  So the rule is duplicated and then CHECKED against the exported answers at every stop
 *  the model does publish — `CAPITAL_AGREEMENT` below, surfaced in the dialog when it
 *  fails rather than left as a function nobody calls.
 */
const CAP = MODEL.freeCash.capital

export type CapitalItem = NonNullable<typeof CAP>['items'][number]

/** Funded, and payable from money the schools could otherwise have had.
 *
 *  Ordered bottom-of-the-ranking first, which is the order things come off. The Vehicle
 *  Use Special Purpose Stabilization Fund is excluded: it is restricted to vehicles and
 *  equipment, so cancelling what it pays for frees nothing for the schools and it cannot
 *  be stranded by a free cash draw. */
export const CONVERTIBLE: CapitalItem[] = CAP
  ? CAP.items.filter(i => i.funded && i.funding !== 'stabilization')
      .sort((a, b) => b.rank - a.rank)
  : []

/** What stops, taken strictly off the bottom of the committee's own ranking.
 *
 *  No backfill and no re-sequencing: this is deliberately the rigid reading, because it
 *  is the one a reader can check against the published list themselves. It OVERSHOOTS —
 *  the items are indivisible, so finding $300,000 removes $693,949 — and the dialog says
 *  so rather than letting the number stand as the cost. */
export function strandedAt(redirect: number): { lost: number; projects: CapitalItem[] } {
  let lost = 0
  const projects: CapitalItem[] = []
  for (const it of CONVERTIBLE) {
    if (lost >= redirect) break
    lost += it.cost
    projects.push(it)
  }
  return { lost, projects }
}

/** The least the programme can lose and still find `redirect`, if the committee
 *  re-sequences instead of holding its ranking. Ten convertible items, so this enumerates
 *  all 1,024 subsets rather than approximating. Reported beside the rigid figure so
 *  neither is presented as the answer. */
export function resequencedAt(redirect: number): number {
  if (redirect <= 0) return 0
  const costs = CONVERTIBLE.map(i => i.cost)
  let best: number | null = null
  for (let mask = 1; mask < (1 << costs.length); mask++) {
    let sum = 0
    for (let i = 0; i < costs.length; i++) if (mask & (1 << i)) sum += costs[i]
    if (sum >= redirect && (best === null || sum < best)) best = sum
  }
  return best ?? CONVERTIBLE.reduce((s, i) => s + i.cost, 0)
}

/** Does this agree with the model at every stop the model publishes? */
export const CAPITAL_AGREEMENT: { ok: boolean; detail: string } = (() => {
  if (!CAP) return { ok: true, detail: 'no capital plan in the model' }
  const bad: string[] = []
  for (const d of CAP.atDraw) {
    const r = Math.max(d.redirect, 0)
    const mine = strandedAt(r)
    if (Math.abs(mine.lost - d.strictLost) > 1) {
      bad.push(`at ${usd(r)}: ${usd(mine.lost)} vs ${usd(d.strictLost)}`)
    } else if (mine.projects.length !== d.projects.length) {
      bad.push(`at ${usd(r)}: ${mine.projects.length} projects vs ${d.projects.length}`)
    }
  }
  return { ok: !bad.length, detail: bad.length ? bad.join('; ') : 'matches model/freecash.py' }
})()

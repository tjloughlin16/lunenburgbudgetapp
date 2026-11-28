/** THE POLICY CALCULATOR'S ARITHMETIC, with no React in it, so scripts/build_policy_calculator.py
 *  can bundle this file and run it on the payload's defaults: its --check fails if any figure here
 *  differs from the Python worked beside the payload (rule 9). Nothing here is a typed figure.
 *
 *  ONE SET OF DIALS, TWO STARTING POSITIONS. TJ, 27 November 2026: "i assumed i would have dials
 *  to move". Every rule is a dial; today's rules and the state draft are two settings of the same
 *  dials. The dials are applied IN ORDER, each taking from what the ones before it left, which is
 *  how today's policy 3.03 is written (a priority list). The draft's shares are each of the whole
 *  certification and add to less than all of it, so the order never changes what they produce. */

export type DialKey =
  | 'general_target' | 'opeb' | 'special_dollars' | 'general' | 'special' | 'keep' | 'capital' | 'other' | 'other_cap'

/** A dial's setting: a fraction (of free cash, or of the budget for general_target) or dollars. */
export type Dials = Record<DialKey, number>

export type Inputs = {
  fc: number; budget: number; general: number; special: number; opeb_trust: number; opeb_liability: number
}

export type UseKey = 'keep' | 'general' | 'special' | 'opeb' | 'capital' | 'other' | 'left'
export type Uses = Record<UseKey, number> & { short: number; by: Partial<Record<DialKey, number>> }

/** Apply the dials in order. `short` is what the dials asked for beyond the free cash there was. */
export function allocate(x: Inputs, d: Dials): Uses {
  let rem = x.fc, asked = 0
  const take = (want: number) => { const w = Math.max(0, want); asked += w; const t = Math.min(rem, w); rem -= t; return t }
  const topup = take(d.general_target * x.budget - x.general)
  const opeb = take(d.opeb * x.fc)
  const special_dollars = take(d.special_dollars)
  const general = take(d.general * x.fc)
  const special = take(d.special * x.fc)
  const keep = take(d.keep * x.fc)
  const capital = take(d.capital * x.fc)
  const other = take(Math.min(d.other * x.fc, d.other_cap))
  return {
    keep, general: topup + general, special: special_dollars + special, opeb, capital, other,
    left: rem, short: Math.max(0, asked - x.fc),
    // What each dial produced, for its card. The cap produces nothing of its own: it limits `other`.
    by: { general_target: topup, opeb, special_dollars, general, special, keep, capital, other },
  }
}

export type After = {
  general_pct: number; special_pct: number; all_pct: number; deposits_pct: number
  opeb_trust: number; funded: number; next_fc: number; next_fc_pct: number
}

/** The balances once the deposits are made, against the one budget figure. */
export function after(x: Inputs, u: Uses): After {
  const g = x.general + u.general, s = x.special + u.special, t = x.opeb_trust + u.opeb
  return {
    general_pct: g / x.budget, special_pct: s / x.budget, all_pct: (g + s) / x.budget,
    deposits_pct: (u.general + u.special) / x.budget,
    opeb_trust: t, funded: t / x.opeb_liability,
    next_fc: u.keep, next_fc_pct: u.keep / x.budget,
  }
}

/** THE SAME SETTINGS, YEAR AFTER YEAR (TJ, 28 November 2026: "an estimate of how long before the target
 *  topoffs are hit"). Each year applies the dials as set to the balances the year before left, with the
 *  free cash and the budget held at the starting figures -- an assumption the panel states, since
 *  neither is known ahead. A top-up dial deposits only the gap, so it stops once its line is met; a
 *  share-of-free-cash dial deposits the same each year and never stops at a target. Index 0 is this
 *  year, the same figures as after(x, allocate(x, d)). */
export function project(x: Inputs, d: Dials, years: number): After[] {
  let s = { ...x }
  const out: After[] = []
  for (let i = 0; i < years; i++) {
    const u = allocate(s, d)
    out.push(after(s, u))
    s = { ...s, general: s.general + u.general, special: s.special + u.special, opeb_trust: s.opeb_trust + u.opeb }
  }
  return out
}

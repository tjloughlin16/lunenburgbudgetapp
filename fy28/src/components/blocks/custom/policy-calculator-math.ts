/** THE POLICY CALCULATOR'S ARITHMETIC, with no React in it, so scripts/build_policy_calculator.py
 *  can bundle this file and run it on the payload's defaults: its --check fails if any figure here
 *  differs from the Python worked beside the payload (rule 9). Every share comes from `params`,
 *  which the generator read off the documents; nothing here is a typed figure. */

export type Params = {
  today: { general: number; opeb: number; floor: number; cap: number }
  draft: {
    keep: number; general: number; special: number; opeb: number; capital: [number, number]
    other: number; other_cap: number; cap: number; stab_annual: [number, number]
  }
  bands: { general_draft: [number, number]; special_draft: [number, number]; fc_draft: [number, number]; general_today: number }
}

/** What the user can change. `capital_share` is the draft's cash capital share (20% to 30%). */
export type Inputs = {
  fc: number; budget: number; general: number; special: number; opeb_trust: number
  opeb_liability: number; special_plan: number; capital_share: number
}

export type UseKey = 'keep' | 'general' | 'special' | 'opeb' | 'capital' | 'other' | 'left'
export type Uses = Record<UseKey, number>
export type Shares = Record<Exclude<UseKey, 'left'>, number>

/** Today's rules (Select Board 3.03), in their order: each step takes from what the last left. */
function today(p: Params, x: Inputs): Uses {
  let rem = x.fc
  const general = Math.min(rem, Math.max(0, p.today.general * x.budget - x.general)); rem -= general
  const opeb = Math.min(rem, p.today.opeb * x.fc); rem -= opeb
  const special = Math.min(rem, Math.max(0, x.special_plan)); rem -= special
  return { keep: 0, general, special, opeb, capital: 0, other: 0, left: rem }
}

/** The draft's floors, each a share of the whole certification (pdf pages 29-30). */
function draft(p: Params, x: Inputs): Uses {
  const u = {
    keep: p.draft.keep * x.fc, general: p.draft.general * x.fc, special: p.draft.special * x.fc,
    opeb: p.draft.opeb * x.fc, capital: x.capital_share * x.fc,
    other: Math.min(p.draft.other * x.fc, p.draft.other_cap),
  }
  return { ...u, left: x.fc - (u.keep + u.general + u.special + u.opeb + u.capital + u.other) }
}

/** The user's own shares of the free cash. */
export function custom(x: Inputs, s: Shares): Uses {
  const u = {
    keep: s.keep * x.fc, general: s.general * x.fc, special: s.special * x.fc,
    opeb: s.opeb * x.fc, capital: s.capital * x.fc, other: s.other * x.fc,
  }
  return { ...u, left: x.fc - (u.keep + u.general + u.special + u.opeb + u.capital + u.other) }
}

export function uses(preset: 'today' | 'draft', p: Params, x: Inputs): Uses {
  return preset === 'today' ? today(p, x) : draft(p, x)
}

/** The draft's shares as a starting point for the custom preset. */
export function draftShares(p: Params, x: Inputs): Shares {
  const d = draft(p, x)
  const f = x.fc > 0 ? x.fc : 1
  return { keep: d.keep / f, general: d.general / f, special: d.special / f, opeb: d.opeb / f, capital: d.capital / f, other: d.other / f }
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

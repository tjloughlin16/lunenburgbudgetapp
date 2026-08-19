import { MODEL, expand, type Mandate, type Program, type Sport, type Status } from './engine'

/* ---------------------------------------------------------------------------
 * Athletics, split into the part that varies with the number of teams and the
 * part that does not.
 *
 * "Cut Golf" is the single most common budget suggestion in town, and answering
 * it honestly needs this split. The FY27 adopted athletics budget is $217,908,
 * but the Athletic Director, the trainer, the secretary, insurance and league
 * dues are all paid whether the school fields twenty teams or nineteen. Only
 * coaching stipends and equipment actually fall when a team folds. Both halves
 * come from the district's own line-item budget, via the athletics_remaining
 * derivation, and they add back to the published total exactly.
 * ------------------------------------------------------------------------- */

const FIXED_LINES = new Set([
  'Athletic Insurance', 'Athletic Dues & Fees', 'Athletic Director',
  'Athletic Trainer', 'Athletic Secretary', 'Special Detail/Athletic Events',
])

export const ATHLETICS_SPLIT = (() => {
  const d = MODEL.method.derivations.find(x => x.id === 'athletics_remaining')
  const lines = d?.lines ?? []
  const fixed = lines.filter(l => FIXED_LINES.has(l.item))
  const variable = lines.filter(l => !FIXED_LINES.has(l.item))
  const sum = (ls: typeof lines) => ls.reduce((s, l) => s + l.amount, 0)
  return {
    fixedLines: fixed, variableLines: variable,
    fixed: sum(fixed), variable: sum(variable), total: d?.total ?? 0,
    source: d?.source ?? '', scenario: d?.scenario ?? '',
  }
})()

export const HS_SPORTS = MODEL.sports.filter(s => s.level === 'HS')
export const MS_SPORTS = MODEL.sports.filter(s => s.level === 'MS')
const HS_WEIGHT = HS_SPORTS.reduce((s, x) => s + x.cost, 0)

/** Middle school and freshman coaching stipends, cut in the FY27 balanced budget.
 *  Middle school sports cannot be cut again — they are already gone. */
export const MS_RESTORE_COST =
  MODEL.programs.find(p => p.id === 'ms_freshman_coaches')?.cost ?? 0

export const sportId = (s: Sport) => `sport:${s.name}`

/* ---------------------------------------------------------------------------
 * The overhead, itemized.
 *
 * "Cost per athlete climbs as you cut teams" is the most surprising thing this tool
 * says, and the reason is a single number — the part of athletics that is paid whether
 * the school fields twenty teams or one. Leaving that as one opaque $110,766 block makes
 * the finding unarguable in the wrong way. These are the six lines it is made of, from
 * the same FY27 balanced column, and each is its own decision.
 * ------------------------------------------------------------------------- */

export interface OverheadLine {
  id: string; label: string; amount: number; fte: number
  note: string
  /** Cutting this does not shrink athletics — it ends it. Flagged, still selectable. */
  endsProgram: boolean
}

const OVERHEAD_NOTES: Record<string, Omit<OverheadLine, 'id' | 'label' | 'amount'>> = {
  'Athletic Director': {
    fte: 0, endsProgram: false,
    note: 'Budgeted as a $20,000 stipend, not a salary — the salaried post ran $85,977 to '
      + '$96,044 in FY23–FY25 actuals and $74,406 in FY26, then drops to $20,000 in all '
      + 'four FY27 scenarios. Someone still has to schedule games, arrange officials and '
      + 'file MIAA paperwork.',
  },
  'Athletic Trainer': {
    fte: 0.5, endsProgram: false,
    note: 'Half a trainer — the other half was cut in FY27. Trainers run concussion '
      + 'protocol and injury response at games. Cutting the remaining half is the one '
      + 'line here with a direct safety argument against it.',
  },
  'Athletic Secretary': {
    fte: 0.5, endsProgram: false,
    note: 'Eligibility records, transport bookings, game-day logistics and MIAA filings '
      + 'for every team.',
  },
  'Athletic Insurance': {
    fte: 0, endsProgram: true,
    note: 'Liability cover for interscholastic play. Cutting it does not make athletics '
      + 'cheaper — it makes fielding a team impossible.',
  },
  'Athletic Dues & Fees': {
    fte: 0, endsProgram: true,
    note: 'MIAA and league membership. Without it there is no league, no schedule and no '
      + 'post-season, so this is not a saving that leaves teams standing.',
  },
  'Special Detail/Athletic Events': {
    fte: 0, endsProgram: false,
    note: 'Police details and event staffing at home games. Cutting it means games '
      + 'without paid coverage, which some venues and events require.',
  },
}

export const OVERHEAD_LINES: OverheadLine[] = ATHLETICS_SPLIT.fixedLines.map(l => ({
  id: l.item.toLowerCase().replace(/[^a-z]+/g, '_').replace(/^_|_$/g, ''),
  label: l.item,
  amount: l.amount,
  ...(OVERHEAD_NOTES[l.item] ?? { fte: 0, endsProgram: false, note: '' }),
}))

export const overheadId = (id: string) => `ovh:${id}`

/** Overhead lines that are gone. Cutting every team takes all of them with it — there is
 *  no director, trainer or league membership for a program that no longer exists. */
export function overheadCut(state: CutState): OverheadLine[] {
  const allTeamsGone = teamsCut(state).length === HS_SPORTS.length
  if (allTeamsGone) return OVERHEAD_LINES
  return OVERHEAD_LINES.filter(l => (state[overheadId(l.id)] ?? 0) > 0)
}

export const overheadSaving = (state: CutState): number =>
  overheadCut(state).reduce((n, l) => n + l.amount, 0)

/** What one team's coaches and equipment cost the FY27 budget.
 *
 *  The district's per-sport figures come from an FY24 athletics document and total
 *  $275,948 across all 25 teams — more than the entire FY27 athletics budget, because
 *  they are a different year and include things the adopted budget no longer funds.
 *  They are still the only published statement of relative cost, so they are used as
 *  weights to spread the FY27 coaching-and-equipment pool across the teams that are
 *  actually funded. Cut every high school team and the weights sum back to the pool. */
export function sportSaving(s: Sport): number {
  if (s.level === 'MS') return 0
  return (s.cost / HS_WEIGHT) * ATHLETICS_SPLIT.variable
}
/* ---------------------------------------------------------------------------
 * The order a slider walks the teams in.
 *
 * Athletics has no equivalent of the administration ladder's "least painful first",
 * because no ranking of teams is neutral — every one of them is somebody's kid. The
 * least-bad available ordering is arithmetic rather than sentiment: give up the teams
 * that serve the fewest athletes per dollar first, so each step down displaces as few
 * students as the money allows. It is still a judgement, and the app says so.
 * ------------------------------------------------------------------------- */

export const perAthlete = (s: Sport) => sportSaving(s) / Math.max(1, s.students)

export const TEAM_ORDER: Sport[] = [...HS_SPORTS]
  .sort((a, b) => perAthlete(b) - perAthlete(a) || sportSaving(b) - sportSaving(a))

/** Where a team sits in that order, 1-based, for display next to its checkbox. */
export const teamRank = (s: Sport) => TEAM_ORDER.indexOf(s) + 1

export const teamsCut = (state: CutState): Sport[] =>
  HS_SPORTS.filter(s => (state[sportId(s)] ?? 0) > 0)

/** Participations on teams that have been cut.
 *
 *  A fee is charged per participation, so cutting a team does not just save its coaching
 *  stipend — it removes its athletes from the pool the fee can be charged on. Leaving
 *  that out lets the tool cut Football and go on collecting Football's fees, which is the
 *  kind of error that makes a whole model untrustworthy. */
export const participationsCut = (state: CutState): number =>
  teamsCut(state).reduce((n, s) => n + s.students, 0)

/* ---------------------------------------------------------------------------
 * What athletics costs once teams have been cut.
 *
 * The other half of the participation problem. Shrinking the pool a fee is charged on
 * while holding the target fixed asks each surviving athlete to fund teams that no longer
 * exist — so "full cost per participant" climbs as you cut, which is backwards. Each rung
 * of the ladder is therefore split into the part that follows the teams and the part that
 * does not, using the same line-item split the per-team savings already use.
 *
 * What follows the teams: coaching stipends, equipment, and athletic transportation —
 * fewer teams means fewer buses to away games. What does not: the director, the trainer,
 * the secretary, insurance and league dues, which are paid whether the school fields
 * twenty teams or one. Middle school coaching stipends sit on the fixed side because
 * middle school teams are already cut and this board cannot cut them again.
 * ------------------------------------------------------------------------- */

/** Which side of the split each ladder step's addition falls on. */
const RUNG_ADD_SCALES: Record<string, boolean> = {
  travel: true,          // athletic transportation — fewer teams, fewer buses
  trainer: false,        // the other half of the trainer
  level_service: true,   // full coaching stipends
  restoration: false,    // middle school coaches, for teams this board cannot cut
}

/** Every rung, split into what follows the teams and what does not. */
export const RUNG_COST = (() => {
  const out: Record<string, { fixed: number; variable: number; total: number }> = {}
  let fixed = ATHLETICS_SPLIT.fixed
  let variable = ATHLETICS_SPLIT.variable
  for (const r of MODEL.athletics.ladder) {
    if (r.add) {
      if (RUNG_ADD_SCALES[r.id]) variable += r.add
      else fixed += r.add
    }
    out[r.id] = { fixed, variable, total: fixed + variable }
  }
  return out
})()

/** Share of high school participations still playing. */
export const teamScale = (state: CutState): number => {
  const all = HS_SPORTS.reduce((n, s) => n + s.students, 0)
  return all === 0 ? 0 : (all - participationsCut(state)) / all
}

/** What one version of the program costs given the teams that survive.
 *
 *  With every team gone there is no program and no overhead to run one, which is the same
 *  answer the per-team savings give when the last team goes. */
export function programCost(rungId: string, state: CutState): number {
  const r = RUNG_COST[rungId] ?? RUNG_COST.adopted
  if (!r) return 0
  if (teamsCut(state).length === HS_SPORTS.length) return 0
  return Math.max(0, r.fixed - overheadSaving(state)) + r.variable * teamScale(state)
}

/** True when the teams cut are exactly the first N of the order — i.e. the slider still
 *  describes the selection. Same contract as the administration ladder. */
export const teamsInOrder = (state: CutState): boolean => {
  const n = teamsCut(state).length
  return TEAM_ORDER.slice(0, n).every(s => (state[sportId(s)] ?? 0) > 0)
}

/** What the slider does at depth `n`: cut the first n teams in order, and only those. */
export function setTeamDepth(state: CutState, n: number): CutState {
  const next = { ...state }
  for (const s of HS_SPORTS) delete next[sportId(s)]
  for (const s of TEAM_ORDER.slice(0, Math.max(0, Math.round(n)))) next[sportId(s)] = 1
  return next
}

/* ---------------------------------------------------------------------------
 * The catalog of things a reader can switch off by hand.
 * ------------------------------------------------------------------------- */

export interface CutItem {
  id: string
  label: string
  cat: string
  cost: number
  fte: number
  mandate: Mandate
  status: Status
  impact: string
  source: string
  repeatable: number
}

const toItem = (p: Program): CutItem => ({
  id: p.id, label: p.name, cat: p.cat, cost: p.cost, fte: p.fte,
  mandate: p.mandate, status: p.status, impact: p.impact, source: p.source,
  repeatable: p.repeatable ?? 1,
})

/** Everything the budget still pays for, and could stop paying for. Athletics is
 *  excluded: it has its own team-by-team board and would otherwise be counted twice. */
export const CUTTABLE: CutItem[] = MODEL.programs
  .filter(p => (p.status === 'funded' || p.status === 'restoring') && p.cat !== 'athletics')
  .map(toItem)

export const BY_ID = new Map(CUTTABLE.map(i => [i.id, i]))

/* ---------------------------------------------------------------------------
 * Putting things back.
 *
 * Every item the FY27 balanced budget eliminated is still a live question, because
 * nothing stops a future budget funding it again — and several of them (athletic
 * transportation, middle school sports, Grade 5 band) are the things people most want
 * back. Restoring one is a cost, not a saving: it makes the hole bigger, and the model
 * says so rather than pretending the choice is free.
 * ------------------------------------------------------------------------- */

export const RESTORABLE: CutItem[] = MODEL.programs
  .filter(p => p.status === 'cut')
  .map(toItem)

export const RESTORE_BY_ID = new Map(RESTORABLE.map(i => [i.id, i]))
export const restoreId = (id: string) => `restore:${id}`

/** The athletics pieces the balanced budget cut. They live on the athletics board with
 *  the teams rather than in the general put-back list. */
export const ATHLETIC_RESTORES = RESTORABLE.filter(i => i.cat === 'athletics')
export const OTHER_RESTORES = RESTORABLE.filter(i => i.cat !== 'athletics')

export interface CutGroup {
  id: string
  title: string
  blurb: string
  /** Where on the context page the argument for this group lives. */
  anchor: string
  ids: string[]
}

/** The groups shown up front, in the order people actually raise them. Everything
 *  not named here is still cuttable — it sits behind "every other line" below. */
export const CURATED: CutGroup[] = [
  {
    id: 'arts', title: 'Arts, music and clubs',
    blurb: 'The things cut first in almost every district that loses an override.',
    anchor: 'the-money',
    ids: ['hs_music_program', 'music_supplies', 'art_supplies', 'hs_advisors'],
  },
  {
    id: 'academics', title: 'Electives, advanced courses and libraries',
    blurb: 'Not required by law, and the largest discretionary money in the budget.',
    anchor: 'the-money',
    ids: ['hs_electives_ap', 'ms_electives', 'libraries'],
  },
  {
    id: 'overhead', title: 'Administration, technology and buildings',
    blurb: '“Cut administration” is the most common suggestion at any budget meeting. '
      + 'These are the lines it actually means.',
    anchor: 'the-money',
    ids: ['hs_dept_heads', 'prof_dev', 'substitutes', 'device_refresh',
          'building_maint', 'grounds_maint'],
  },
  {
    id: 'restorations', title: 'The September restorations',
    blurb: 'One-time state money puts these five back for FY27 only. Keeping any of them '
      + 'in FY28 is a new cost the district has to find — so not keeping them is a choice '
      + 'available to you here.',
    anchor: 'where-we-are',
    ids: ['reading_spec_ps', 'reading_spec_thes', 'lhs_ap_half', 'ignite_seats',
          'music_lhs_04'],
  },
]

const CURATED_IDS = new Set(CURATED.flatMap(g => g.ids))

/** Everything else, grouped by category, for the reader who wants the whole budget. */
export const REST_BY_CAT: { cat: string; label: string; items: CutItem[] }[] =
  Object.keys(MODEL.categories)
    .filter(c => c !== 'athletics')
    .map(cat => ({
      cat, label: MODEL.categories[cat].label,
      items: CUTTABLE.filter(i => i.cat === cat && !CURATED_IDS.has(i.id)),
    }))
    .filter(g => g.items.length > 0)

export const REST_COUNT = REST_BY_CAT.reduce((n, g) => n + g.items.length, 0)

/* ---------------------------------------------------------------------------
 * Scoring a hand-built scenario.
 * ------------------------------------------------------------------------- */

/** How many units of a program are switched off. Most things are one unit; a few —
 *  classroom teachers, custodians, SPED paraprofessionals — are a count. */
export type CutState = Record<string, number>

export interface ScoredCut {
  id: string; label: string; detail: string; amount: number; fte: number
  cat: string; blocked: boolean
}

export interface CutScore {
  items: ScoredCut[]
  total: number
  fte: number
  /** Picks a district could not lawfully make, counted but flagged. */
  unlawful: ScoredCut[]
  unlawfulTotal: number
  /** Things put back, which cost money rather than saving it. */
  restores: ScoredCut[]
  restoreTotal: number
  restoreFte: number
  /** Fixed athletics overhead released only when every team is gone. */
  overheadReleased: number
  teamsCut: number
}

export function scoreCuts(state: CutState): CutScore {
  const items: ScoredCut[] = []

  // --- teams -------------------------------------------------------------
  const cutTeams = HS_SPORTS.filter(s => state[sportId(s)] > 0)
  for (const s of cutTeams) {
    items.push({
      id: sportId(s), label: s.name, cat: 'athletics',
      detail: `${s.students} participations · coaching and equipment share`,
      amount: sportSaving(s), fte: 0, blocked: false,
    })
  }
  const allTeamsGone = cutTeams.length === HS_SPORTS.length
  for (const l of overheadCut(state)) {
    items.push({
      id: overheadId(l.id), label: l.label, cat: 'athletics',
      detail: allTeamsGone
        ? 'Goes with the last team — nothing left to run'
        : l.endsProgram
          ? 'Cutting this ends interscholastic play altogether'
          : 'Athletics overhead — paid regardless of how many teams there are',
      amount: l.amount, fte: l.fte, blocked: false,
    })
  }
  const overheadReleased = overheadSaving(state)

  // --- things put back ---------------------------------------------------
  const restores: ScoredCut[] = []
  for (const [key, n] of Object.entries(state)) {
    if (!n || !key.startsWith('restore:')) continue
    const p = RESTORE_BY_ID.get(key.slice('restore:'.length))
    if (!p) continue
    restores.push({
      id: key, label: p.label, cat: p.cat,
      detail: p.fte > 0
        ? `${p.fte} FTE · cut in the FY27 balanced budget`
        : 'Cut in the FY27 balanced budget',
      amount: p.cost, fte: p.fte, blocked: false,
    })
  }
  restores.sort((a, b) => b.amount - a.amount)

  // --- programs ----------------------------------------------------------
  for (const [id, n] of Object.entries(state)) {
    if (!n || id.startsWith('sport:') || id.startsWith('restore:')) continue
    const p = BY_ID.get(id)
    if (!p) continue
    const units = Math.min(n, p.repeatable)
    // A legally required program can be switched off here and it counts, because
    // refusing to compute "what would that even save" reads as evasion. The flag rides
    // along so nothing downstream can present it as an adoptable budget.
    const blocked = p.mandate === 'legal'
    items.push({
      id, label: p.label, cat: p.cat,
      detail: blocked
        ? `Required by law — not a budget the district may adopt${
            p.repeatable > 1 ? ` · ${units} of ${p.repeatable}` : ''}`
        : p.repeatable > 1
          ? `${units} of ${p.repeatable} · ${units * p.fte} FTE`
          : p.status === 'restoring' ? 'Not kept for FY28' : MODEL.categories[p.cat]?.label ?? p.cat,
      amount: p.cost * units,
      fte: p.fte * units,
      blocked,
    })
  }

  items.sort((a, b) => b.amount - a.amount)
  return {
    items,
    total: items.reduce((s, i) => s + i.amount, 0),
    fte: items.reduce((s, i) => s + i.fte, 0),
    unlawful: items.filter(i => i.blocked),
    unlawfulTotal: items.filter(i => i.blocked).reduce((s, i) => s + i.amount, 0),
    restores,
    restoreTotal: restores.reduce((s, i) => s + i.amount, 0),
    restoreFte: restores.reduce((s, i) => s + i.fte, 0),
    overheadReleased, teamsCut: cutTeams.length,
  }
}

/* ---------------------------------------------------------------------------
 * Seeding the board from a priority ranking.
 * ------------------------------------------------------------------------- */

/** Turn one year of cascade cuts into a hand-editable board state.
 *
 *  The priorities page and this page are separate scenarios on purpose — one asks
 *  "what does this ranking give up", the other asks "what would you actually do".
 *  This is the bridge: start from what a ranking produces, then argue with it. */
export function seedFromCuts(cuts: { id: string; blocked: boolean; cat: string }[]): CutState {
  const state: CutState = {}
  for (const c of cuts) {
    if (c.blocked) continue
    // expand() numbers repeatable programs id_1, id_2 …; fold them back to a count.
    const base = BY_ID.has(c.id) ? c.id : c.id.replace(/_\d+$/, '')
    if (c.cat === 'athletics') {
      // The cascade cuts athletics as one block. On this board that is every team.
      for (const s of HS_SPORTS) state[sportId(s)] = 1
      continue
    }
    if (!BY_ID.has(base)) continue
    state[base] = (state[base] ?? 0) + 1
  }
  return state
}

/** Programs the cascade would reach, for the "load a ranking" preview. */
export const expandedPool = () => expand(MODEL.programs)

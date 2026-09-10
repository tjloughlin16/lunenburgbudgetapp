/** The blocks the staffing generator publishes, and the two lookups the pages share.
 *
 *  WHY THIS FILE EXISTS. `scripts/build_staffing_charts.py` computes one body of data and
 *  selects three payloads out of it — /school-staffing, /who-works-in-each-school and
 *  /the-paraprofessionals. The blocks are therefore the SAME blocks wherever they appear,
 *  and typing them in three places would be three chances for the three pages to disagree
 *  about the shape of a thing that is computed once.
 *
 *  Nothing here holds a figure. These are types, two name tables the town itself uses, and
 *  one derivation over a series — rule 2 applies to a page file and to this one equally.
 */
import type {
  Peer, RosterYear, RoleRow, StatePoint, DistrictPoint, SchoolRow, SubjectMove,
  HeadFte, ParaSplitPoint, PeerHead, Board,
} from '../components/StaffingCharts'

export type Change = {
  first_fy: number; last_fy: number; first: number; last: number
  change: number; pct: number | null
} | null

export type Rank = {
  fy: number; of: number; rank: number; value: number
  highest: string; highest_value: number; lowest: string; lowest_value: number
}

export type Panel = {
  key: string; label: string; stage: string; source: string; lines: number
  line_labels: string[]; first_fy: number; last_fy: number; years_dropped: number[]
  points: { fy: number; dollars: number }[]
  change: Change
  documents_disagree?: number
}

export type Window = {
  why: string; first_fy: number; last_fy: number; first: number; last: number
  change: number; pct: number | null; up: number; steps: number
  students: Change; per_100: Change; high_needs: Change; per_100_high_needs: Change
}

export type Composition = {
  first_fy: number; last_fy: number
  eras: { total: number; school: number; subject: number
    why_total: string; why_school: string; why_subject: string }
  district: DistrictPoint[]
  peak: { fy: number; fte: number }
  windows: Record<string, Window>
  every_window: { pairs: number; rose: number; fell: number; flat: number
    years: number[]; rows: { fy: number; to: (number | null)[] }[] }
  schools: {
    era: number; rows: SchoolRow[]; open_now: string[]
    reconciliation: { fy: number; district: number; schools: number; difference: number }[]
    worst: { fy: number; district: number; schools: number; difference: number }
    biggest_fall: SchoolRow; steady: string[]
  }
  subjects: {
    era: number
    rows: { subject: string; level: string; is_programme: boolean
      first_fy: number; last_fy: number; latest: number
      points: { fy: number; fte: number }[] }[]
    windows: { key: string; label: string; why: string; first_fy: number; last_fy: number
      rows: SubjectMove[]; up: number; down: number; gross: number; net: number
      subjects: number }[]
    agreement: { compared: number; agree: number; disagree: number; largest: number }
    source: string; checked_against: string
  }
  programme: { rows: { fy: number; gen_ed_fte: number | null; sped_fte: number | null
    career_tech_fte: number | null; el_fte: number | null
    total_fte: number | null }[]; registered_gap: string }
  not_counted: {
    first_fy: number; last_fy: number; years: number; job_classes: string[]
    rollup_trap: string
    roster: { first_fy: number; last_fy: number
      roles: (RoleRow & { first: number; last: number; change: number
        peak: number; trough: number; up: number; steps: number })[] }
  }
}

export type Headcount = {
  first_fy: number; last_fy: number; years: number; job_classes: string[]
  grain: string; rollup_trap: string
  rows: { fy: number; job_class: string; educators_headcount: number
    hires_headcount: number | null; retained_headcount: number | null
    retained_pct: number | null }[]
  vs_fte: HeadFte[]
  churn: { fy: number; job_class: string; headcount: number; hires: number | null
    retained: number | null; retained_pct: number | null; hire_share: number | null }[]
  peers: { fy: number; districts: number; rows: PeerHead[]; state: PeerHead[]
    ranks: Record<string, { fy: number; of: number; rank: number; value: number
      headcount: number; highest: string; highest_value: number
      lowest: string; lowest_value: number }> }
  naive: { fy: number; job_class: string; naive: number; published: number }[]
}

export type SpedStaffing = {
  first_fy: number; last_fy: number; rows: ParaSplitPoint[]
  all_programmes: Window; special_education: Window; implied: Window; swd: Window
  sped_total: { fy: number; fte: number; swd: number; per_100: number }[]
  reproduces: { checked: number; failed: number }
  two_files: { a: string; b: string; warning: string }
}

export type State = {
  lea: string; docs: string[]; reconciles: Record<string, number>
  first_fy: number; last_fy: number
  points: (StatePoint & {
    student_headcount: number; pct_disabilities: number | null
    pct_low_income: number | null; average_teacher_salary: number | null
    instructional_support_fte: number | null; pupils_out_of_district: number | null
  })[]
  change: Record<string, Change>
  change_over_roster_years: Record<string, Change>
  trough: StatePoint
  ranks: { paras: Rank[]; teachers: Rank[] }
  latest: StatePoint & { student_headcount: number }
}

export type Roster = {
  years: RosterYear[]
  roles: RoleRow[]
  buildings: string[]
  by_school: { fy: number; rows: { school: string; names: number }[] }
  entries_total: number; entries_in_panel: number
  excluded: { school: string; entries: number; years: number[]; why: string }[]
  unclassified: number; unclassified_share: number
  doubled: { fy: number; school: string; pages: string[]; names: number[]; shared: number }[]
  ocr_defects: { printed: string; rows: number; years: number[]; schools: string[] }[]
  ocr_rows: number; grade_headed_rows: number
  shared_staff: { fy: number; names: number }[]
  first_fy: number; last_fy: number
}

export type Dollars = {
  stage: string
  panels: Panel[]
  sped_common_window: {
    first_fy: number; last_fy: number
    panels: { key: string; label: string; lines: number; change: Change
      points: { fy: number; dollars: number }[] }[]
  }
  reconciled: {
    a: string; b: string; years: number; agree: number; first_fy: number; last_fy: number
    disagree: { fy: number; a: number; b: number; difference: number }[]
  }[]
}

export type Wages = {
  rows: number; years: number; school_tagged: number; statuses: string[]
  by_year: { fy: number; rows: number; school_tagged: number }[]
}

export type { Peer, RosterYear, RoleRow, StatePoint, DistrictPoint, SchoolRow, SubjectMove,
  HeadFte, ParaSplitPoint, PeerHead, Board }

/** The town's own names for its schools, so a slug never reaches the page. */
export const SCHOOL: Record<string, string> = {
  primary: 'Lunenburg Primary School',
  'turkey-hill': 'Turkey Hill Elementary School',
  middle: 'Lunenburg Middle School',
  high: 'Lunenburg High School',
  passios: 'Passios Elementary School',
  'central-office': 'Central office',
  'monty-tech': 'Monty Tech (regional vocational)',
}
export const school = (s: string) => SCHOOL[s] ?? s

export const ROLE: Record<string, string> = {
  teacher: 'Teachers', paraprofessional: 'Paraprofessionals', specialist: 'Specialists',
  administrator: 'Administrators', custodian: 'Custodial', cafeteria: 'Food service',
  counselor: 'Counsellors', secretary: 'Office staff', speech_therapist: 'Speech',
  nurse: 'Nurses', psychologist: 'Psychologists', therapist: 'OT / PT',
  librarian: 'Librarians', social_worker: 'Social workers', technology: 'Technology',
  unknown: 'Title not recognised',
}
export const role = (r: string) => ROLE[r] ?? r

/** The longest run of consecutive years at a given rank, derived rather than picked.
 *  A rank quoted at two chosen years is a rank the writer chose. */
export function longestRun(ranks: Rank[], test: (r: Rank) => boolean) {
  let best: Rank[] = [], cur: Rank[] = []
  for (const r of ranks) {
    if (test(r)) { cur.push(r); if (cur.length > best.length) best = [...cur] }
    else cur = []
  }
  return best
}

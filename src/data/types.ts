// FiscalYear is a plain string key derived at parse time (e.g. "fy27").
// It is NOT a fixed union so the app works with any future spreadsheet
// that adds new years or drops old ones.
export type FiscalYear = string

// Describes one year column discovered in the spreadsheet header rows.
export interface YearColumn {
  key: FiscalYear   // normalised key, e.g. "fy27"
  short: string     // e.g. "FY27"
  label: string     // e.g. "FY27 Proposed"
  col: number       // 0-based column index in the sheet
  isProjected: boolean // true for the last (proposed/budget) column
}

export type Section = 'expenses' | 'salaries' | 'summary'

export type CategoryCode = '1' | '2' | '3' | '4' | '5' | '7' | '9'

export const CATEGORY_CODES: CategoryCode[] = ['1', '2', '3', '4', '5', '7', '9']

export const CATEGORY_LABELS: Record<CategoryCode, string> = {
  '1': 'Administration',
  '2': 'Instructional',
  '3': 'Student Services',
  '4': 'Facilities',
  '5': 'Fixed Costs',
  '7': 'Capital',
  '9': 'Tuitions',
}

export const CATEGORY_DESCRIPTIONS: Record<CategoryCode, string> = {
  '1': 'School Committee, Superintendent, business office, HR, legal, and technology infrastructure.',
  '2': 'Classroom teachers, curriculum directors, libraries, instructional technology, and tutoring.',
  '3': 'Guidance counselors, school psychologists, nurses, special education, and transportation.',
  '4': 'Custodians, groundskeeping, building repairs, energy, and security.',
  '5': 'Health insurance, retirement contributions, workers\' comp, and property insurance.',
  '7': 'Major equipment purchases, building renovations, and vehicle replacements.',
  '9': 'Tuition payments to other districts for out-of-district special education placements.',
}

export const CATEGORY_COLORS: Record<CategoryCode, string> = {
  '1': '#3b82f6',
  '2': '#10b981',
  '3': '#f59e0b',
  '4': '#8b5cf6',
  '5': '#ef4444',
  '7': '#06b6d4',
  '9': '#f97316',
}

export interface LineItem {
  id: string
  budgetCode: string | null
  description: string
  section: Section
  categoryCode: CategoryCode | null
  categoryLabel: string | null
  isGroupHeader: boolean
  parentCode: string | null
  values: Record<FiscalYear, number | null>
  pctChange: number | null  // penultimate vs final year; null if not computable
  rawRow: number
}

export interface BudgetGroup {
  code: string
  label: string
  section: Section
  categoryCode: CategoryCode | null
  categoryLabel: string | null
  lineItems: LineItem[]
  totals: Record<FiscalYear, number>
}

export interface BudgetData {
  lineItems: LineItem[]
  groups: BudgetGroup[]
  grandTotals: Record<FiscalYear, number>
  sections: {
    expenses: LineItem[]
    salaries: LineItem[]
  }
  years: YearColumn[]        // discovered year columns in sheet order
  freeCash: Partial<Record<FiscalYear, number>>  // one-time free cash offsets keyed by year (negative = reduces levy)
  parseWarnings: string[]
}

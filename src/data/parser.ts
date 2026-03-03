import * as XLSX from 'xlsx'
import type {
  BudgetData,
  LineItem,
  BudgetGroup,
  FiscalYear,
  YearColumn,
  CategoryCode,
  Section,
  SupplementalRow,
} from './types'
import { CATEGORY_LABELS } from './types'

// ── Fixed column indices (structural, not year-dependent) ─────────────────────
const COL_BUDGET_CODE = 0  // A — budget group code (e.g. "1110 - School Committee")
const COL_DESCRIPTION = 1  // B — line item description

// ── Cell helpers ─────────────────────────────────────────────────────────────

type RawCell = XLSX.CellObject | undefined

function cellToString(cell: RawCell): string {
  if (!cell || cell.t === 'e') return ''
  return String(cell.v ?? '')
}

function parseValue(cell: RawCell): number | null {
  if (!cell || cell.t === 'e') return null
  if (cell.t === 'n') {
    const v = cell.v as number
    return isFinite(v) ? v : null
  }
  if (cell.t === 's') {
    const s = (cell.v as string).trim()
    if (s === '-' || s === '' || s.toLowerCase() === 'n/a') return null
    const n = parseFloat(s.replace(/[$,\s]/g, ''))
    return isNaN(n) ? null : n
  }
  return null
}

// ── Dynamic year-column discovery ─────────────────────────────────────────────

/**
 * Scan the first SCAN_ROWS rows of the sheet looking for cells that contain a
 * year label matching "FY" + 2–4 digits (e.g. "FY27", "FY2027").
 * Collects the year header row and the sub-label row immediately below it
 * (e.g. "Actuals", "Proposed") to build a full label.
 * Returns columns in left-to-right order.
 */
function discoverYearColumns(rawRows: RawCell[][]): YearColumn[] {
  const SCAN_ROWS = 12
  const FY_PATTERN = /^FY\d{2,4}$/i

  for (let r = 0; r < Math.min(SCAN_ROWS, rawRows.length); r++) {
    const row = rawRows[r]
    const found: { col: number; short: string }[] = []

    for (let c = COL_DESCRIPTION + 1; c < (row?.length ?? 0); c++) {
      const text = cellToString(row?.[c]).trim()
      if (FY_PATTERN.test(text)) {
        found.push({ col: c, short: text.toUpperCase() })
      }
    }

    if (found.length < 2) continue // need at least 2 year columns

    // Read sub-labels from the row directly below (e.g. "Actuals", "Proposed")
    const subRow = rawRows[r + 1] ?? []
    const years: YearColumn[] = found.map((f, idx) => {
      const sub = cellToString(subRow[f.col]).trim()
      const label = sub ? `${f.short} ${sub}` : f.short
      const key = f.short.toLowerCase().replace(/\s+/g, '') // "FY27" → "fy27"
      const isProjected = idx === found.length - 1
      return { key, short: f.short, label, col: f.col, isProjected }
    })

    return years
  }

  return []
}

// ── Dynamic section-boundary detection ───────────────────────────────────────

interface Boundaries {
  dataStart: number    // first data row (0-based)
  expensesEnd: number  // first row of salary section
  salaryEnd: number    // first row of summary section
}

/**
 * Scan column A for known section markers to determine row boundaries.
 *
 * Markers looked for (case-insensitive):
 *   "DISTRICT EXPENSES"  → data begins on the NEXT row
 *   "DISTRICT SALARIES"  → salary section starts here; expenses end here
 *   "TOTAL SALARIES"     → look a few rows ahead for "Salary Reserve";
 *                          salaryEnd = row after reserve (or row of TOTAL SALARIES)
 *
 * Falls back to safe defaults if a marker is not found.
 */
function discoverBoundaries(rawRows: RawCell[][]): Boundaries {
  let dataStart = 6        // safe default: Excel row 7
  let expensesEnd = -1
  let totalSalariesRow = -1

  for (let r = 0; r < rawRows.length; r++) {
    const colA = cellToString(rawRows[r]?.[COL_BUDGET_CODE]).trim().toUpperCase()

    if (colA.startsWith('DISTRICT EXPENSES')) {
      dataStart = r + 1
    } else if (colA.startsWith('DISTRICT SALARIES')) {
      expensesEnd = r           // salary section begins here
    } else if (colA === 'TOTAL SALARIES') {
      totalSalariesRow = r
      break                     // nothing useful below this in the salary section
    }
  }

  // Determine salaryEnd: include the Salary Reserve row if it exists
  let salaryEnd = totalSalariesRow > 0 ? totalSalariesRow : (expensesEnd > 0 ? expensesEnd + 200 : 400)

  if (totalSalariesRow > 0) {
    // Look up to 5 rows past "TOTAL SALARIES" for a "Salary Reserve" row
    for (let r = totalSalariesRow + 1; r <= Math.min(totalSalariesRow + 5, rawRows.length - 1); r++) {
      const desc = cellToString(rawRows[r]?.[COL_DESCRIPTION]).trim().toLowerCase()
      if (desc.includes('salary reserve')) {
        salaryEnd = r + 1   // include the reserve row; summary starts after it
        break
      }
    }
  }

  return {
    dataStart,
    expensesEnd: expensesEnd > 0 ? expensesEnd : dataStart + 200,
    salaryEnd,
  }
}

// ── Sheet → raw array ─────────────────────────────────────────────────────────

function sheetToRaw(sheet: XLSX.WorkSheet): RawCell[][] {
  const ref = sheet['!ref']
  if (!ref) return []
  const range = XLSX.utils.decode_range(ref)
  const rows: RawCell[][] = []
  for (let r = range.s.r; r <= range.e.r; r++) {
    const row: RawCell[] = []
    for (let c = range.s.c; c <= range.e.c; c++) {
      row.push(sheet[XLSX.utils.encode_cell({ r, c })])
    }
    rows.push(row)
  }
  return rows
}

// ── Merged-cell value propagation ─────────────────────────────────────────────

function buildMergeMap(sheet: XLSX.WorkSheet): Map<string, string> {
  const merges: XLSX.Range[] = sheet['!merges'] || []
  const map = new Map<string, string>()
  for (const merge of merges) {
    const topLeft = sheet[XLSX.utils.encode_cell({ r: merge.s.r, c: merge.s.c })]
    const value = cellToString(topLeft)
    for (let r = merge.s.r; r <= merge.e.r; r++) {
      for (let c = merge.s.c; c <= merge.e.c; c++) {
        map.set(`${r},${c}`, value)
      }
    }
  }
  return map
}

// ── Line-item helpers ─────────────────────────────────────────────────────────

function isGroupHeaderRow(rawCode: string): boolean {
  // Group headers always have a 4-digit budget code in column A.
  // Line items have an empty col A and their description in col B.
  return /^\d{4}/.test(rawCode.trim())
}

function extractCategoryCode(code: string | null): CategoryCode | null {
  if (!code) return null
  const match = code.trim().match(/^([12345679])/)
  return match ? (match[1] as CategoryCode) : null
}

function computePctChange(prev: number | null, curr: number | null): number | null {
  if (prev === null || curr === null) return null
  if (Math.abs(prev) < 0.005) return null
  return (curr - prev) / prev
}

// ── Post-parse passes ─────────────────────────────────────────────────────────

function assignParentCodes(items: LineItem[]): void {
  let currentExpenseHeader: string | null = null
  let currentSalaryHeader: string | null = null

  for (const item of items) {
    if (item.section === 'summary') continue

    if (item.isGroupHeader && item.budgetCode) {
      if (item.section === 'expenses') currentExpenseHeader = item.budgetCode
      else currentSalaryHeader = item.budgetCode
      item.parentCode = null
    } else {
      // Salary Reserve is a district-level item, not tied to any department group.
      if (item.description.toLowerCase().includes('salary reserve')) {
        item.parentCode = null
      } else {
        item.parentCode =
          item.section === 'expenses' ? currentExpenseHeader : currentSalaryHeader
      }
    }
  }
}

function buildGroups(items: LineItem[], years: YearColumn[]): BudgetGroup[] {
  const yearKeys = years.map(y => y.key)
  const emptyTotals = () => Object.fromEntries(yearKeys.map(k => [k, 0])) as Record<FiscalYear, number>
  const groupMap = new Map<string, BudgetGroup>()

  for (const item of items) {
    if (item.section === 'summary' || !item.isGroupHeader) continue
    const code = item.budgetCode!
    if (!groupMap.has(code)) {
      // Expenses-section group headers have the name only in col A (e.g. "1110 - School Committee")
      // while col B is empty, leaving item.description = "". Fall back to stripping the numeric
      // prefix from the budget code string so the label is always non-empty.
      const label = item.description ||
        item.budgetCode?.replace(/^\d+\s*[-–]\s*/, '').trim() ||
        item.budgetCode ||
        code
      groupMap.set(code, {
        code,
        label,
        section: item.section,
        categoryCode: item.categoryCode,
        categoryLabel: item.categoryLabel,
        lineItems: [],
        totals: emptyTotals(),
      })
    }
  }

  for (const item of items) {
    if (item.section === 'summary' || item.isGroupHeader || !item.parentCode) continue
    const group = groupMap.get(item.parentCode)
    if (group) {
      group.lineItems.push(item)
      for (const key of yearKeys) {
        group.totals[key] += item.values[key] ?? 0
      }
    }
  }

  return Array.from(groupMap.values())
}

function computeGrandTotals(items: LineItem[], years: YearColumn[]): Record<FiscalYear, number> {
  const totals = Object.fromEntries(years.map(y => [y.key, 0])) as Record<FiscalYear, number>
  for (const item of items) {
    if (item.section === 'summary' || item.isGroupHeader) continue
    for (const y of years) {
      totals[y.key] += item.values[y.key] ?? 0
    }
  }
  return totals
}

// ── Supplemental CSV loader ───────────────────────────────────────────────────
//
// Parses a simple two-column CSV (label, dollar-value) from an adjacent file.
// Fails gracefully — returns [] if the file is missing or unparseable so the
// rest of the app continues working without it.

async function loadSupplemental(url: string): Promise<SupplementalRow[]> {
  try {
    const resp = await fetch(url)
    if (!resp.ok) return []
    const text = await resp.text()
    const rows: SupplementalRow[] = []
    for (const rawLine of text.split('\n')) {
      const line = rawLine.trim()
      if (!line) continue
      const commaIdx = line.indexOf(',')
      if (commaIdx < 0) continue
      const label = line.substring(0, commaIdx).trim()
      const rawVal = line.substring(commaIdx + 1).trim()
      const num = parseFloat(rawVal.replace(/[$,\s]/g, ''))
      if (label && isFinite(num)) rows.push({ label, value: num })
    }
    return rows
  } catch {
    return []
  }
}

// ── Main entry point ──────────────────────────────────────────────────────────

export async function parseBudgetFile(url: string): Promise<BudgetData> {
  const response = await fetch(url)
  if (!response.ok) throw new Error(`Failed to fetch budget file: ${response.statusText}`)

  const arrayBuffer = await response.arrayBuffer()
  const workbook = XLSX.read(arrayBuffer, {
    type: 'array',
    cellDates: false,
    cellNF: false,
    sheetStubs: true,
    cellFormula: false,
  })

  const sheet = workbook.Sheets[workbook.SheetNames[0]]
  const rawRows = sheetToRaw(sheet)
  const mergeMap = buildMergeMap(sheet)

  // ── Auto-detect year columns and section boundaries ───────────────────────
  const years = discoverYearColumns(rawRows)
  if (years.length === 0) {
    throw new Error('Could not find any fiscal year columns in the spreadsheet header. Expected cells like "FY27" in the first 12 rows.')
  }

  const { dataStart, expensesEnd, salaryEnd } = discoverBoundaries(rawRows)

  // The two most recent years are used for % change (penultimate vs last)
  const prevYear = years.length >= 2 ? years[years.length - 2] : null
  const lastYear = years[years.length - 1]

  const warnings: string[] = []
  warnings.push(`Discovered years: ${years.map(y => y.label).join(', ')}`)
  warnings.push(`Section boundaries — dataStart:${dataStart} expensesEnd:${expensesEnd} salaryEnd:${salaryEnd}`)

  const lineItems: LineItem[] = []

  for (let r = dataStart; r < rawRows.length; r++) {
    const row = rawRows[r]
    if (!row) continue

    const section: Section =
      r < expensesEnd ? 'expenses' :
      r < salaryEnd   ? 'salaries' : 'summary'

    const rawCode =
      mergeMap.get(`${r},${COL_BUDGET_CODE}`) ??
      cellToString(row[COL_BUDGET_CODE])
    const rawDesc =
      mergeMap.get(`${r},${COL_DESCRIPTION}`) ??
      cellToString(row[COL_DESCRIPTION])

    if (!rawCode.trim() && !rawDesc.trim()) continue

    // Skip aggregate/section-header rows embedded in the data
    const codeUpper = rawCode.trim().toUpperCase()
    if (
      codeUpper.startsWith('TOTAL') ||
      codeUpper.startsWith('DISTRICT EXPENSES') ||
      codeUpper.startsWith('DISTRICT SALARIES')
    ) continue

    // Build values map keyed by discovered year keys (e.g. { fy27: 98031 })
    const values: Record<FiscalYear, number | null> = {}
    for (const y of years) {
      values[y.key] = parseValue(row[y.col])
    }

    const pctChange = prevYear
      ? computePctChange(values[prevYear.key], values[lastYear.key])
      : null

    const budgetCode = rawCode.trim() || null
    const description = rawDesc.trim()
    const categoryCode = extractCategoryCode(budgetCode)

    lineItems.push({
      id: budgetCode ? `${budgetCode}-${r}` : `row-${r}`,
      budgetCode,
      description,
      section,
      categoryCode,
      categoryLabel: categoryCode ? (CATEGORY_LABELS[categoryCode] ?? null) : null,
      isGroupHeader: isGroupHeaderRow(rawCode),
      parentCode: null,
      values,
      pctChange,
      rawRow: r + 1,
    })
  }

  assignParentCodes(lineItems)

  const groups = buildGroups(lineItems, years)
  const grandTotals = computeGrandTotals(lineItems, years)

  // Scan all rows for "FREE CASH" text (may appear in any column in the summary area)
  const freeCash: Partial<Record<FiscalYear, number>> = {}
  for (let r = 0; r < rawRows.length; r++) {
    const row = rawRows[r]
    if (!row) continue
    let found = false
    for (let c = 0; c < row.length; c++) {
      if (cellToString(row[c]).trim().toUpperCase() === 'FREE CASH') { found = true; break }
    }
    if (found) {
      for (const y of years) {
        const val = parseValue(row[y.col])
        if (val !== null && val !== 0) freeCash[y.key] = val
      }
    }
  }

  // Load supplemental.csv from the same directory as the budget file
  const budgetBaseUrl = url.substring(0, url.lastIndexOf('/') + 1)
  const supplemental = await loadSupplemental(budgetBaseUrl + 'supplemental.csv')

  return {
    lineItems,
    groups,
    grandTotals,
    sections: {
      expenses: lineItems.filter(i => i.section === 'expenses'),
      salaries: lineItems.filter(i => i.section === 'salaries'),
    },
    years,
    freeCash,
    supplemental,
    parseWarnings: warnings,
  }
}

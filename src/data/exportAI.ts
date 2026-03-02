import Papa from 'papaparse'
import type { BudgetData, FiscalYear } from './types'
import { CATEGORY_LABELS } from './types'

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmt$(n: number): string {
  return n.toLocaleString('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 })
}

function fmtPct(n: number): string {
  return `${n >= 0 ? '+' : ''}${(n * 100).toFixed(1)}%`
}

function direction(delta: number): string {
  if (delta > 500)  return 'Increase'
  if (delta < -500) return 'Decrease'
  return 'Flat'
}

function triggerDownload(content: string, filename: string, mimeType: string) {
  const blob = new Blob([content], { type: mimeType })
  const url  = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

// ── AI-Ready CSV ──────────────────────────────────────────────────────────────
//
// Produces a flat, self-contained CSV designed for easy analysis by humans
// or AI assistants (ChatGPT, Claude, etc.).  Every row contains the full
// context (section, category, budget group, description) so no implicit
// parent-row knowledge is required.
//
// Structure
//   • Comment block  — "#" lines at the top with district / year context
//   • SUMMARY rows   — one row per category showing rolled-up totals
//   • LINE_ITEM rows — one row per actual budget line item, fully annotated

export function downloadAIReadyCSV(
  data: BudgetData,
  primaryYear: FiscalYear,
  compareYear: FiscalYear,
): void {
  const { lineItems, groups, grandTotals, years, freeCash } = data

  const primaryLabel = years.find(y => y.key === primaryYear)?.label ?? primaryYear.toUpperCase()
  const compareLabel = years.find(y => y.key === compareYear)?.label ?? compareYear.toUpperCase()

  const totalPrimary   = grandTotals[primaryYear] ?? 0
  const totalCompare   = grandTotals[compareYear] ?? 0
  const freeCashAdjust = freeCash[compareYear] ?? 0
  const adjustedBase   = totalCompare + freeCashAdjust
  const levyDelta      = totalPrimary - adjustedBase
  const levyPct        = adjustedBase > 0 ? levyDelta / adjustedBase : 0

  // ── METADATA rows (valid CSV rows, not comment lines) ─────────────────────
  // Record_Type=METADATA rows carry context. Field/Value columns hold the key
  // and value; all budget-data columns are left blank on these rows.
  const metaRows: Record<string, string | number>[] = [
    { Field: 'District',            Value: 'Lunenburg Public Schools' },
    { Field: 'Primary Year',        Value: primaryLabel },
    { Field: 'Compare Year',        Value: compareLabel },
    { Field: `${primaryLabel} Proposed Total`, Value: fmt$(totalPrimary) },
    { Field: `${compareLabel} Levy Base`,
      Value: freeCashAdjust < 0
        ? `${fmt$(adjustedBase)} (gross ${fmt$(totalCompare)} minus ${fmt$(Math.abs(freeCashAdjust))} one-time free cash)`
        : fmt$(adjustedBase) },
    { Field: 'Year-over-Year Levy Change',
      Value: `${levyDelta >= 0 ? '+' : ''}${fmt$(levyDelta)} (${fmtPct(levyPct)})` },
    ...(freeCashAdjust < 0 ? [{
      Field: 'Free Cash Note',
      Value: `${compareLabel} used ${fmt$(Math.abs(freeCashAdjust))} in one-time free cash. This does NOT carry into ${primaryLabel}. Use the Levy Base above (not the gross total) for year-over-year comparisons.`,
    }] : []),
    { Field: 'Column Guide — Record_Type', Value: 'METADATA = context rows (this section) | SUMMARY = category-level roll-ups | LINE_ITEM = individual budget lines' },
    { Field: 'Column Guide — Section',     Value: 'Expenses = non-salary operating costs | Salaries = staff compensation' },
    { Field: 'Column Guide — Dollar_Change / Pct_Change', Value: `${compareLabel} → ${primaryLabel}` },
    { Field: 'Column Guide — Direction',   Value: 'Increase | Decrease | Flat (±$500 threshold)' },
    { Field: 'Source', Value: 'Official Lunenburg Public Schools budget documents — lunenburgbudgetapp.netlify.app' },
  ].map(r => ({ Record_Type: 'METADATA', ...r }))

  // ── Column order (years in sheet order) ────────────────────────────────────
  const yrCols = years.map(y => y.label)

  // ── Group lookup ────────────────────────────────────────────────────────────
  const groupMap  = new Map(groups.map(g => [g.code, g]))

  // ── SUMMARY rows (one per category, rolled up from all groups) ─────────────
  type CatAccum = { a: number; b: number; years: Record<string, number> }
  const catAccum = new Map<string, CatAccum>()

  for (const g of groups) {
    if (g.section === 'summary' || !g.categoryCode) continue
    const key = `${g.section}__${g.categoryCode}`
    if (!catAccum.has(key)) {
      catAccum.set(key, { a: 0, b: 0, years: Object.fromEntries(years.map(y => [y.label, 0])) })
    }
    const acc = catAccum.get(key)!
    acc.a += g.totals[compareYear] ?? 0
    acc.b += g.totals[primaryYear] ?? 0
    for (const y of years) acc.years[y.label] += g.totals[y.key] ?? 0
  }

  const summaryRows = Array.from(catAccum.entries()).map(([key, acc]) => {
    const [section, catCode] = key.split('__')
    const delta = acc.b - acc.a
    const pct   = Math.abs(acc.a) > 0.005 ? delta / acc.a : null
    const row: Record<string, string | number> = {
      Record_Type: 'SUMMARY',
      Field: '',
      Value: '',
      Section: section === 'expenses' ? 'Expenses' : 'Salaries',
      Category: CATEGORY_LABELS[catCode as keyof typeof CATEGORY_LABELS] ?? catCode,
      Category_Code: catCode,
      Group_Code: '',
      Group: '(all groups in category)',
      Description: '— Category Total —',
    }
    for (const y of years) row[y.label] = acc.years[y.label] || ''
    row['Dollar_Change'] = delta
    row['Pct_Change']    = pct !== null ? fmtPct(pct) : ''
    row['Direction']     = direction(delta)
    return row
  }).sort((a, b) => {
    if (a['Section'] !== b['Section']) return String(a['Section']).localeCompare(String(b['Section']))
    return String(a['Category']).localeCompare(String(b['Category']))
  })

  // ── LINE_ITEM rows ──────────────────────────────────────────────────────────
  const lineRows = lineItems
    .filter(i => !i.isGroupHeader && i.section !== 'summary')
    .map(item => {
      const group    = item.parentCode ? groupMap.get(item.parentCode) : null
      const catCode  = group?.categoryCode ?? item.categoryCode
      const catLabel = catCode ? (CATEGORY_LABELS[catCode as keyof typeof CATEGORY_LABELS] ?? catCode) : ''
      const groupName = group
        ? group.label.replace(/^\d+\s*[-–]\s*/, '').trim()
        : ''

      const a     = item.values[compareYear] ?? 0
      const b     = item.values[primaryYear] ?? 0
      const delta = b - a
      const pct   = Math.abs(a) > 0.005 ? delta / a : null

      const row: Record<string, string | number> = {
        Record_Type: 'LINE_ITEM',
        Field: '',
        Value: '',
        Section: item.section === 'expenses' ? 'Expenses' : 'Salaries',
        Category: catLabel,
        Category_Code: catCode ?? '',
        Group_Code: item.parentCode ?? '',
        Group: groupName,
        Description: item.description,
      }

      for (const y of years) {
        const v = item.values[y.key]
        row[y.label] = v !== null && v !== 0 ? v : ''
      }

      row['Dollar_Change'] = delta !== 0 ? delta : ''
      row['Pct_Change']    = pct !== null ? fmtPct(pct) : (b > 0 && a === 0 ? 'New' : '')
      row['Direction']     = direction(delta)
      return row
    })

  // ── Assemble CSV ────────────────────────────────────────────────────────────
  const allRows = [...metaRows, ...summaryRows, ...lineRows]
  const columns = [
    'Record_Type', 'Field', 'Value',
    'Section', 'Category', 'Category_Code',
    'Group_Code', 'Group', 'Description',
    ...yrCols,
    'Dollar_Change', 'Pct_Change', 'Direction',
  ]

  const csv = Papa.unparse(allRows, { columns })

  triggerDownload(
    csv,
    `lunenburg-budget-ai-ready-${primaryYear}.csv`,
    'text/csv;charset=utf-8;',
  )
}

// ── Original XLSX passthrough ─────────────────────────────────────────────────

export function downloadOriginalXLSX(): void {
  const link = document.createElement('a')
  link.href = '/data/budget.xlsx'
  link.download = 'lunenburg-budget-source.xlsx'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

import type { BudgetGroup, FiscalYear, CategoryCode, LineItem, Section, YearColumn } from './types'
import { CATEGORY_LABELS, CATEGORY_COLORS } from './types'

export function formatDollar(value: number): string {
  const abs = Math.abs(value)
  if (abs >= 1_000_000) return `$${(value / 1_000_000).toFixed(2)}M`
  if (abs >= 1_000) return `$${(value / 1_000).toFixed(1)}K`
  return `$${value.toFixed(0)}`
}

export function formatDollarShort(value: number): string {
  const abs = Math.abs(value)
  if (abs >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`
  if (abs >= 1_000) return `$${(value / 1_000).toFixed(0)}K`
  return `$${value.toFixed(0)}`
}

export function formatPct(value: number | null): string {
  if (value === null) return 'N/A'
  const sign = value >= 0 ? '+' : ''
  return `${sign}${(value * 100).toFixed(1)}%`
}

// ── Treemap ──────────────────────────────────────────────────────────────────

export interface TreemapLeaf {
  name: string
  size: number
  code: string
  categoryCode: CategoryCode | null
  color: string
  compareValue: number   // penultimate year value
  compareLabel: string   // e.g. "FY26 Budget"
  primaryLabel: string   // e.g. "FY27 Proposed"
  pctChange: number | null
}

export interface TreemapCategory {
  name: string
  categoryCode: CategoryCode
  color: string
  children: TreemapLeaf[]
}

export function buildTreemapData(
  groups: BudgetGroup[],
  year: FiscalYear,
  section: Section | 'both' = 'both',
  activeCats: CategoryCode[] = [],
  years: YearColumn[] = [],
): TreemapCategory[] {
  const compareYearCol = years.length >= 2 ? years[years.length - 2] : null
  const primaryYearCol = years.length >= 1 ? years[years.length - 1] : null

  const filtered = groups.filter(g => {
    if (section !== 'both' && g.section !== section) return false
    if (activeCats.length > 0 && g.categoryCode && !activeCats.includes(g.categoryCode)) return false
    return true
  })

  const catMap = new Map<CategoryCode | 'other', TreemapLeaf[]>()

  for (const group of filtered) {
    const size = group.totals[year]
    if (size <= 0) continue

    const catKey = group.categoryCode ?? 'other'
    if (!catMap.has(catKey)) catMap.set(catKey, [])

    const compareVal = compareYearCol ? (group.totals[compareYearCol.key] ?? 0) : 0
    const primaryVal = primaryYearCol ? (group.totals[primaryYearCol.key] ?? 0) : 0
    const pctChange = Math.abs(compareVal) < 0.005 ? null : (primaryVal - compareVal) / compareVal

    catMap.get(catKey)!.push({
      name: group.label,
      size,
      code: group.code,
      categoryCode: group.categoryCode,
      color: group.categoryCode ? CATEGORY_COLORS[group.categoryCode] : '#6b7280',
      compareValue: compareVal,
      compareLabel: compareYearCol?.label ?? 'Prior Year',
      primaryLabel: primaryYearCol?.label ?? 'Current Year',
      pctChange,
    })
  }

  const result: TreemapCategory[] = []
  for (const [catCode, children] of catMap.entries()) {
    if (catCode === 'other') continue
    result.push({
      name: CATEGORY_LABELS[catCode as CategoryCode],
      categoryCode: catCode as CategoryCode,
      color: CATEGORY_COLORS[catCode as CategoryCode],
      children: children.sort((a, b) => b.size - a.size),
    })
  }

  return result.sort((a, b) => {
    const aTotal = a.children.reduce((s, c) => s + c.size, 0)
    const bTotal = b.children.reduce((s, c) => s + c.size, 0)
    return bTotal - aTotal
  })
}

// ── Bar chart ────────────────────────────────────────────────────────────────

export interface CategoryBarDatum {
  category: string
  categoryCode: CategoryCode
  compare: number     // penultimate year total
  primary: number     // last year total
  compareLabel: string
  primaryLabel: string
}

export function buildCategoryBarData(
  groups: BudgetGroup[],
  section: Section | 'both' = 'both',
  years: YearColumn[] = [],
): CategoryBarDatum[] {
  const compareYearCol = years.length >= 2 ? years[years.length - 2] : null
  const primaryYearCol = years.length >= 1 ? years[years.length - 1] : null
  const compareKey = compareYearCol?.key ?? ''
  const primaryKey = primaryYearCol?.key ?? ''
  const compareLabel = compareYearCol?.label ?? 'Prior Year'
  const primaryLabel = primaryYearCol?.label ?? 'Current Year'

  const catMap = new Map<CategoryCode, CategoryBarDatum>()

  for (const group of groups) {
    if (section !== 'both' && group.section !== section) continue
    if (!group.categoryCode) continue

    const key = group.categoryCode
    if (!catMap.has(key)) {
      catMap.set(key, {
        category: CATEGORY_LABELS[key],
        categoryCode: key,
        compare: 0,
        primary: 0,
        compareLabel,
        primaryLabel,
      })
    }
    const entry = catMap.get(key)!
    if (compareKey) entry.compare += group.totals[compareKey] ?? 0
    if (primaryKey) entry.primary += group.totals[primaryKey] ?? 0
  }

  return Array.from(catMap.values()).sort((a, b) => b.primary - a.primary)
}

// ── Trend line ───────────────────────────────────────────────────────────────

export interface TrendDatum {
  year: string
  fy: FiscalYear
  value: number
  isProjected: boolean
}

export function buildTrendData(
  source: BudgetGroup | { totals: Record<FiscalYear, number> } | null,
  years: YearColumn[] = [],
): TrendDatum[] {
  if (!source) return []
  return years.map(y => ({
    year: y.short,
    fy: y.key,
    value: source.totals[y.key] ?? 0,
    isProjected: y.isProjected,
  }))
}

// ── Comparison ───────────────────────────────────────────────────────────────

export interface ComparisonRow {
  code: string
  label: string
  categoryLabel: string | null
  section: Section
  yearA: number
  yearB: number
  delta: number
  pctChange: number | null
}

export function buildComparisonData(
  groups: BudgetGroup[],
  yearA: FiscalYear,
  yearB: FiscalYear,
  section: Section | 'both' = 'both',
): ComparisonRow[] {
  return groups
    .filter(g => section === 'both' || g.section === section)
    .map(g => {
      const a = g.totals[yearA]
      const b = g.totals[yearB]
      const delta = b - a
      const pctChange = Math.abs(a) < 0.005 ? null : delta / a
      return {
        code: g.code,
        label: g.label,
        categoryLabel: g.categoryLabel,
        section: g.section,
        yearA: a,
        yearB: b,
        delta,
        pctChange,
      }
    })
    .sort((a, b) => Math.abs(b.delta) - Math.abs(a.delta))
}

// ── Category-level comparison (combines expenses + salaries per category) ─────

export interface CategoryComparisonRow {
  categoryCode: CategoryCode
  categoryLabel: string
  color: string
  yearA: number
  yearB: number
  delta: number
  pctChange: number | null
}

export function buildCategoryComparisonData(
  groups: BudgetGroup[],
  yearA: FiscalYear,
  yearB: FiscalYear,
  section: Section | 'both' = 'both',
): CategoryComparisonRow[] {
  const map = new Map<CategoryCode, CategoryComparisonRow>()

  for (const g of groups) {
    if (!g.categoryCode) continue
    if (section !== 'both' && g.section !== section) continue

    const a = g.totals[yearA] ?? 0
    const b = g.totals[yearB] ?? 0

    if (!map.has(g.categoryCode)) {
      map.set(g.categoryCode, {
        categoryCode: g.categoryCode,
        categoryLabel: CATEGORY_LABELS[g.categoryCode],
        color: CATEGORY_COLORS[g.categoryCode],
        yearA: 0,
        yearB: 0,
        delta: 0,
        pctChange: null,
      })
    }

    const row = map.get(g.categoryCode)!
    row.yearA += a
    row.yearB += b
  }

  return Array.from(map.values())
    .map(row => ({
      ...row,
      delta: row.yearB - row.yearA,
      pctChange: Math.abs(row.yearA) < 0.005 ? null : (row.yearB - row.yearA) / row.yearA,
    }))
    .sort((a, b) => Math.abs(b.delta) - Math.abs(a.delta))
}

// ── Line-item-level comparison ────────────────────────────────────────────────

export interface LineItemComparisonRow {
  id: string
  budgetCode: string | null
  parentCode: string | null
  description: string
  section: Section
  categoryCode: CategoryCode | null
  categoryLabel: string | null
  yearA: number | null
  yearB: number | null
  delta: number
  pctChange: number | null
}

export function buildLineItemComparisonData(
  items: LineItem[],
  yearA: FiscalYear,
  yearB: FiscalYear,
  section: Section | 'both' = 'both',
  activeCats: CategoryCode[] = [],
): LineItemComparisonRow[] {
  return items
    .filter(item => {
      if (item.section === 'summary' || item.isGroupHeader) return false
      if (section !== 'both' && item.section !== section) return false
      if (activeCats.length > 0 && item.categoryCode && !activeCats.includes(item.categoryCode)) return false
      return true
    })
    .map(item => {
      const a = item.values[yearA] ?? null
      const b = item.values[yearB] ?? null
      const aNum = a ?? 0
      const bNum = b ?? 0
      const delta = bNum - aNum
      const pctChange = Math.abs(aNum) < 0.005 ? null : delta / aNum
      return {
        id: item.id,
        budgetCode: item.budgetCode,
        parentCode: item.parentCode,
        description: item.description,
        section: item.section,
        categoryCode: item.categoryCode,
        categoryLabel: item.categoryLabel,
        yearA: a,
        yearB: b,
        delta,
        pctChange,
      }
    })
    .sort((a, b) => Math.abs(b.delta) - Math.abs(a.delta))
}

// ── Search ────────────────────────────────────────────────────────────────────

export function searchLineItems(
  items: LineItem[],
  query: string,
  section: Section | 'both' = 'both',
  activeCats: CategoryCode[] = [],
): LineItem[] {
  const q = query.toLowerCase().trim()
  return items.filter(item => {
    if (item.section === 'summary') return false
    if (section !== 'both' && item.section !== section) return false
    if (activeCats.length > 0 && item.categoryCode && !activeCats.includes(item.categoryCode)) return false
    if (!q) return true
    return (
      item.description.toLowerCase().includes(q) ||
      (item.budgetCode?.toLowerCase().includes(q) ?? false)
    )
  })
}

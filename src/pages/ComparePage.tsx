import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useBudgetStore } from '../store/budgetStore'
import { useBudgetData } from '../hooks/useBudgetData'
import {
  buildCategoryComparisonData,
  buildLineItemComparisonData,
  formatDollar,
} from '../data/transforms'
import type { LineItemComparisonRow } from '../data/transforms'
import { DeltaBadge } from '../components/charts/DeltaBadge'
import { LoadingSpinner } from '../components/ui/LoadingSpinner'
import { ErrorBanner } from '../components/ui/ErrorBanner'
import { CATEGORY_COLORS, CATEGORY_DESCRIPTIONS } from '../data/types'
import type { CategoryCode } from '../data/types'
import { InfoTooltip } from '../components/ui/InfoTooltip'
import { SectionToggle } from '../components/filters/SectionToggle'
import { CategoryFilter } from '../components/filters/CategoryFilter'

const PAGE_SIZE = 50

// ── Sortable column header ────────────────────────────────────────────────────

type SortKey = 'description' | 'yearA' | 'yearB' | 'delta' | 'pctChange'

function SortTh({
  col, label, sort, onSort, right = false,
}: {
  col: SortKey
  label: string
  sort: { key: SortKey; dir: 'asc' | 'desc' }
  onSort: (k: SortKey) => void
  right?: boolean
}) {
  const active = sort.key === col
  return (
    <th
      onClick={() => onSort(col)}
      className={`px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide cursor-pointer select-none whitespace-nowrap hover:text-gray-800 ${right ? 'text-right' : 'text-left'}`}
    >
      {label}{active ? (sort.dir === 'asc' ? ' ↑' : ' ↓') : ''}
    </th>
  )
}

// ── Section badge ─────────────────────────────────────────────────────────────

function SectionBadge({ section }: { section: 'expenses' | 'salaries' }) {
  return (
    <span className={`inline-block text-xs px-1.5 py-0.5 rounded font-medium ${
      section === 'salaries'
        ? 'bg-purple-100 text-purple-700'
        : 'bg-blue-100 text-blue-700'
    }`}>
      {section}
    </span>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────

export function ComparePage() {
  const { data, loading, error } = useBudgetData()
  const { primaryYear, compareYear, activeSection, activeCategories, years } = useBudgetStore()
  const navigate = useNavigate()

  const [sort, setSort] = useState<{ key: SortKey; dir: 'asc' | 'desc' }>({
    key: 'delta',
    dir: 'desc',
  })
  const [showAll, setShowAll] = useState(false)

  const compareLabel = years.find(y => y.key === compareYear)?.label ?? compareYear
  const primaryLabel = years.find(y => y.key === primaryYear)?.label ?? primaryYear

  const catRows = useMemo(
    () => data ? buildCategoryComparisonData(data.groups, compareYear, primaryYear, activeSection) : [],
    [data, compareYear, primaryYear, activeSection]
  )

  const allLineItems = useMemo(
    () => data ? buildLineItemComparisonData(data.lineItems, compareYear, primaryYear, activeSection, activeCategories) : [],
    [data, compareYear, primaryYear, activeSection, activeCategories]
  )

  const sortedLineItems = useMemo(() => {
    const sorted = [...allLineItems].sort((a, b) => {
      let av: number, bv: number
      if (sort.key === 'description') {
        return sort.dir === 'asc'
          ? a.description.localeCompare(b.description)
          : b.description.localeCompare(a.description)
      }
      if (sort.key === 'yearA') { av = a.yearA ?? 0; bv = b.yearA ?? 0 }
      else if (sort.key === 'yearB') { av = a.yearB ?? 0; bv = b.yearB ?? 0 }
      else if (sort.key === 'pctChange') { av = a.pctChange ?? 0; bv = b.pctChange ?? 0 }
      else { av = a.delta; bv = b.delta } // 'delta'
      return sort.dir === 'asc' ? av - bv : bv - av
    })
    return sorted
  }, [allLineItems, sort])

  const visibleLineItems = showAll ? sortedLineItems : sortedLineItems.slice(0, PAGE_SIZE)

  const handleSort = (key: SortKey) => {
    setSort(prev =>
      prev.key === key
        ? { key, dir: prev.dir === 'asc' ? 'desc' : 'asc' }
        : { key, dir: 'desc' }
    )
    setShowAll(false)
  }

  if (loading) return <LoadingSpinner />
  if (error) return <ErrorBanner message={error} />
  if (!data) return null

  const totalA = catRows.reduce((s, r) => s + r.yearA, 0)
  const totalB = catRows.reduce((s, r) => s + r.yearB, 0)
  const totalDelta = totalB - totalA
  const totalPct = Math.abs(totalA) > 0.005 ? totalDelta / totalA : null

  return (
    <div className="p-6 space-y-8">

      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Year Comparison</h1>
          <p className="text-gray-500 mt-0.5">
            {compareLabel} → {primaryLabel}
          </p>
        </div>
        <div className="flex items-center gap-3 flex-wrap">
          <SectionToggle />
        </div>
      </div>

      {/* ── Filters ────────────────────────────────────────────────────────── */}
      <CategoryFilter />

      {/* ── Totals banner ──────────────────────────────────────────────────── */}
      <div className="bg-white rounded-xl border border-gray-200 p-4 grid grid-cols-3 gap-4">
        <div>
          <p className="text-xs text-gray-500 uppercase tracking-wide">{compareLabel}</p>
          <p className="text-xl font-bold text-gray-900 mt-1">{formatDollar(totalA)}</p>
        </div>
        <div>
          <p className="text-xs text-gray-500 uppercase tracking-wide">{primaryLabel}</p>
          <p className="text-xl font-bold text-gray-900 mt-1">{formatDollar(totalB)}</p>
        </div>
        <div>
          <p className="text-xs text-gray-500 uppercase tracking-wide">Change</p>
          <p className={`text-xl font-bold mt-1 ${totalDelta >= 0 ? 'text-red-600' : 'text-green-600'}`}>
            {totalDelta >= 0 ? '+' : ''}{formatDollar(totalDelta)}
          </p>
          <DeltaBadge value={totalPct} size="sm" />
        </div>
      </div>

      {/* ── Section 1: By Category ─────────────────────────────────────────── */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-100 bg-gray-50">
          <h2 className="text-base font-bold text-gray-900">By Category</h2>
          <p className="text-xs text-gray-500 mt-0.5">
            Expenses and salaries combined per category — click a row to explore departments
          </p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 bg-gray-50">
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Category</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wide whitespace-nowrap">{compareLabel}</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wide whitespace-nowrap">{primaryLabel}</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wide">Delta ($)</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wide">Change</th>
              </tr>
            </thead>
            <tbody>
              {catRows.map(row => (
                <tr
                  key={row.categoryCode}
                  onClick={() => navigate(`/?cats=${row.categoryCode}`)}
                  className="border-b border-gray-100 hover:bg-gray-50 cursor-pointer"
                >
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <span
                        className="w-3 h-3 rounded-sm flex-shrink-0"
                        style={{ backgroundColor: CATEGORY_COLORS[row.categoryCode as CategoryCode] }}
                      />
                      <span className="font-medium text-gray-900">{row.categoryLabel}</span>
                      <InfoTooltip
                        title={`${row.categoryCode}xxx — ${row.categoryLabel}`}
                        text={CATEGORY_DESCRIPTIONS[row.categoryCode as CategoryCode]}
                      />
                    </div>
                  </td>
                  <td className="px-4 py-3 text-right tabular-nums text-gray-600">{formatDollar(row.yearA)}</td>
                  <td className="px-4 py-3 text-right tabular-nums font-medium text-gray-900">{formatDollar(row.yearB)}</td>
                  <td className={`px-4 py-3 text-right tabular-nums font-medium ${
                    row.delta > 0 ? 'text-red-600' : row.delta < 0 ? 'text-green-600' : 'text-gray-400'
                  }`}>
                    {row.delta !== 0 ? `${row.delta > 0 ? '+' : ''}${formatDollar(row.delta)}` : '—'}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <DeltaBadge value={row.pctChange} size="sm" />
                  </td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr className="border-t-2 border-gray-300 bg-gray-50">
                <td className="px-4 py-3 font-bold text-gray-900">Total</td>
                <td className="px-4 py-3 text-right tabular-nums font-semibold text-gray-600">{formatDollar(totalA)}</td>
                <td className="px-4 py-3 text-right tabular-nums font-bold text-gray-900">{formatDollar(totalB)}</td>
                <td className={`px-4 py-3 text-right tabular-nums font-bold ${totalDelta >= 0 ? 'text-red-600' : 'text-green-600'}`}>
                  {totalDelta >= 0 ? '+' : ''}{formatDollar(totalDelta)}
                </td>
                <td className="px-4 py-3 text-right">
                  <DeltaBadge value={totalPct} size="sm" />
                </td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>

      {/* ── Section 2: Line Items ──────────────────────────────────────────── */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-100 bg-gray-50 flex items-center justify-between gap-4 flex-wrap">
          <div>
            <h2 className="text-base font-bold text-gray-900">Line-by-Line Comparison</h2>
            <p className="text-xs text-gray-500 mt-0.5">
              Every individual budget line, sorted by largest change. Click a row to see its department.
            </p>
          </div>
          <span className="text-sm text-gray-500">
            {allLineItems.length} line items
          </span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 bg-gray-50">
                <SortTh col="description" label="Description" sort={sort} onSort={handleSort} />
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Type</th>
                <SortTh col="yearA" label={compareLabel} sort={sort} onSort={handleSort} right />
                <SortTh col="yearB" label={primaryLabel} sort={sort} onSort={handleSort} right />
                <SortTh col="delta" label="Delta ($)" sort={sort} onSort={handleSort} right />
                <SortTh col="pctChange" label="Change" sort={sort} onSort={handleSort} right />
              </tr>
            </thead>
            <tbody>
              {visibleLineItems.map(row => (
                <LineItemRow
                  key={row.id}
                  row={row}
                  onClick={() => {
                    if (row.parentCode) navigate(`/category/${encodeURIComponent(row.parentCode)}`)
                  }}
                />
              ))}
            </tbody>
          </table>
        </div>

        {/* Show more / collapse */}
        {sortedLineItems.length > PAGE_SIZE && (
          <div className="px-6 py-3 border-t border-gray-100 bg-gray-50 flex items-center justify-between">
            <span className="text-sm text-gray-500">
              Showing {showAll ? sortedLineItems.length : Math.min(PAGE_SIZE, sortedLineItems.length)} of {sortedLineItems.length}
            </span>
            <button
              onClick={() => setShowAll(v => !v)}
              className="text-sm text-blue-600 hover:text-blue-800 font-medium"
            >
              {showAll ? 'Show fewer' : `Show all ${sortedLineItems.length}`}
            </button>
          </div>
        )}
      </div>

    </div>
  )
}

// ── Line item row ─────────────────────────────────────────────────────────────

function LineItemRow({ row, onClick }: { row: LineItemComparisonRow; onClick: () => void }) {
  return (
    <tr
      onClick={onClick}
      className={`border-b border-gray-100 ${row.parentCode ? 'hover:bg-blue-50 cursor-pointer' : ''}`}
    >
      <td className="px-4 py-2">
        <div>
          <span className="text-gray-800">{row.description}</span>
          {row.parentCode && (
            <span className="ml-2 text-xs font-mono text-gray-400">{row.parentCode}</span>
          )}
        </div>
        {row.categoryLabel && (
          <div className="flex items-center gap-1.5 mt-0.5">
            <span
              className="w-2 h-2 rounded-sm"
              style={{ backgroundColor: row.categoryCode ? CATEGORY_COLORS[row.categoryCode as CategoryCode] : '#9ca3af' }}
            />
            <span className="text-xs text-gray-400">{row.categoryLabel}</span>
          </div>
        )}
      </td>
      <td className="px-4 py-2">
        <SectionBadge section={row.section as 'expenses' | 'salaries'} />
      </td>
      <td className="px-4 py-2 text-right tabular-nums text-gray-500">
        {row.yearA !== null ? formatDollar(row.yearA) : <span className="text-gray-300">—</span>}
      </td>
      <td className="px-4 py-2 text-right tabular-nums text-gray-900 font-medium">
        {row.yearB !== null ? formatDollar(row.yearB) : <span className="text-gray-300">—</span>}
      </td>
      <td className={`px-4 py-2 text-right tabular-nums font-medium ${
        row.delta > 0 ? 'text-red-600' : row.delta < 0 ? 'text-green-600' : 'text-gray-400'
      }`}>
        {row.delta !== 0 ? `${row.delta > 0 ? '+' : ''}${formatDollar(row.delta)}` : '—'}
      </td>
      <td className="px-4 py-2 text-right">
        <DeltaBadge value={row.pctChange} size="sm" />
      </td>
    </tr>
  )
}

import { useMemo, useState } from 'react'
import { useSearchParams, useNavigate, Link } from 'react-router-dom'
import type { YearColumn } from '../data/types'
import { useBudgetData } from '../hooks/useBudgetData'
import { useBudgetStore } from '../store/budgetStore'
import { LoadingSpinner } from '../components/ui/LoadingSpinner'
import { ErrorBanner } from '../components/ui/ErrorBanner'
import { DeltaBadge } from '../components/charts/DeltaBadge'
import { formatDollar, formatPct } from '../data/transforms'
import {
  DEPARTMENTS,
  filterItemsForDepartment,
  downloadDepartmentCSV,
} from '../data/departments'
import type { DeptLineItem } from '../data/departments'

// ── Color maps ────────────────────────────────────────────────────────────────

const BORDER_COLOR: Record<string, string> = {
  sky:    'border-sky-400',    amber:  'border-amber-400',
  violet: 'border-violet-400', rose:   'border-rose-400',
  purple: 'border-purple-400', green:  'border-green-500',
  slate:  'border-slate-400',  teal:   'border-teal-400',
  emerald:'border-emerald-400',orange: 'border-orange-400',
  cyan:   'border-cyan-400',   stone:  'border-stone-400',
  indigo: 'border-indigo-400',
}

const BADGE_COLOR: Record<string, string> = {
  sky:    'bg-sky-100 text-sky-700',    amber:  'bg-amber-100 text-amber-700',
  violet: 'bg-violet-100 text-violet-700', rose: 'bg-rose-100 text-rose-700',
  purple: 'bg-purple-100 text-purple-700', green:'bg-green-100 text-green-700',
  slate:  'bg-slate-100 text-slate-600',   teal: 'bg-teal-100 text-teal-700',
  emerald:'bg-emerald-100 text-emerald-700',orange:'bg-orange-100 text-orange-700',
  cyan:   'bg-cyan-100 text-cyan-700',   stone: 'bg-stone-100 text-stone-600',
  indigo: 'bg-indigo-100 text-indigo-700',
}

const ACTIVE_BG: Record<string, string> = {
  sky:    'bg-sky-500 text-white border-sky-500',
  amber:  'bg-amber-500 text-white border-amber-500',
  violet: 'bg-violet-500 text-white border-violet-500',
  rose:   'bg-rose-500 text-white border-rose-500',
  purple: 'bg-purple-500 text-white border-purple-500',
  green:  'bg-green-500 text-white border-green-500',
  slate:  'bg-slate-500 text-white border-slate-500',
  teal:   'bg-teal-500 text-white border-teal-500',
  emerald:'bg-emerald-500 text-white border-emerald-500',
  orange: 'bg-orange-500 text-white border-orange-500',
  cyan:   'bg-cyan-500 text-white border-cyan-500',
  stone:  'bg-stone-500 text-white border-stone-500',
  indigo: 'bg-indigo-500 text-white border-indigo-500',
}

// ── Sortable column header ────────────────────────────────────────────────────

function SortTh({
  col, label, sort, onSort, right = false,
}: {
  col: string; label: string
  sort: { key: string; dir: 'asc' | 'desc' }
  onSort: (k: string) => void
  right?: boolean
}) {
  const active = sort.key === col
  return (
    <th
      onClick={() => onSort(col)}
      className={`px-3 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide cursor-pointer select-none whitespace-nowrap hover:text-gray-800 ${right ? 'text-right' : 'text-left'}`}
    >
      {label}{active ? (sort.dir === 'asc' ? ' ↑' : ' ↓') : ''}
    </th>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────

export function DepartmentsPage() {
  const { data, loading, error } = useBudgetData()
  const { primaryYear, compareYear } = useBudgetStore()
  const [searchParams, setSearchParams] = useSearchParams()
  const [sort, setSort] = useState<{ key: string; dir: 'asc' | 'desc' }>({ key: 'delta', dir: 'desc' })

  const activeDeptId = searchParams.get('view') ?? 'ps'
  const activeDept = DEPARTMENTS.find(d => d.id === activeDeptId) ?? DEPARTMENTS[0]

  const handleSelect = (id: string) => {
    setSearchParams({ view: id }, { replace: true })
    setSort({ key: 'delta', dir: 'desc' })
  }

  const handleSort = (key: string) => {
    setSort(prev =>
      prev.key === key
        ? { key, dir: prev.dir === 'asc' ? 'desc' : 'asc' }
        : { key, dir: key === 'description' || key === 'section' ? 'asc' : 'desc' }
    )
  }

  const items = useMemo(
    () => data ? filterItemsForDepartment(activeDeptId, data, primaryYear, compareYear) : [],
    [data, activeDeptId, primaryYear, compareYear]
  )

  const sortedItems = useMemo(() => {
    return [...items].sort((a, b) => {
      let av: number, bv: number
      if (sort.key === 'description') {
        return sort.dir === 'asc'
          ? a.description.localeCompare(b.description)
          : b.description.localeCompare(a.description)
      }
      if (sort.key === 'section') {
        return sort.dir === 'asc'
          ? a.section.localeCompare(b.section)
          : b.section.localeCompare(a.section)
      }
      if (sort.key === 'delta')     { av = a.delta;            bv = b.delta }
      else if (sort.key === 'pctChange') { av = a.pctChange ?? 0; bv = b.pctChange ?? 0 }
      else {
        // Year column sort
        av = a.values[sort.key] ?? 0
        bv = b.values[sort.key] ?? 0
      }
      return sort.dir === 'asc' ? av - bv : bv - av
    })
  }, [items, sort])

  // ── Insight items: noise-floor filtered, sorted by |delta| ─────────────────
  // Threshold: |delta| >= $1k (noise floor) — dept-scoped so all items are
  // already relevant; the higher keyword-search thresholds don't apply here.
  const insightItems = useMemo(() => {
    return items.filter(i => Math.abs(i.delta) >= 1_000)
  }, [items])

  const insightIncreases = useMemo(
    () => insightItems.filter(i => i.delta > 0).sort((a, b) => b.delta - a.delta).slice(0, 6),
    [insightItems]
  )
  const insightDecreases = useMemo(
    () => insightItems.filter(i => i.delta < 0).sort((a, b) => a.delta - b.delta).slice(0, 6),
    [insightItems]
  )

  // ── Cross-department comparison stats ─────────────────────────────────────
  const deptStats = useMemo((): DeptStat[] => {
    if (!data) return []
    return DEPARTMENTS.map(dept => {
      const deptItems  = filterItemsForDepartment(dept.id, data, primaryYear, compareYear)
      const increases  = deptItems.filter(i => i.delta > 0).reduce((s, i) => s + i.delta, 0)
      const cuts       = Math.abs(deptItems.filter(i => i.delta < 0).reduce((s, i) => s + i.delta, 0))
      const baseTotal    = deptItems.reduce((s, i) => s + (i.values[compareYear] ?? 0), 0)
      const primaryTotal = deptItems.reduce((s, i) => s + (i.values[primaryYear]  ?? 0), 0)
      const churn        = increases + cuts
      const churnPct     = baseTotal > 0 ? churn / baseTotal : null
      const topIncrease  = deptItems.filter(i => i.delta > 0).sort((a, b) => b.delta - a.delta)[0] ?? null
      const topCut       = deptItems.filter(i => i.delta < 0).sort((a, b) => a.delta - b.delta)[0] ?? null
      return {
        id: dept.id, label: dept.label, abbrev: dept.abbrev,
        group: dept.group, colorClass: dept.colorClass,
        increases, cuts, net: increases - cuts, churn, baseTotal, primaryTotal, churnPct,
        topIncrease: topIncrease ? { description: topIncrease.description, delta: topIncrease.delta } : null,
        topCut:      topCut      ? { description: topCut.description,      delta: topCut.delta      } : null,
      }
    })
  }, [data, primaryYear, compareYear])

  if (loading) return <LoadingSpinner />
  if (error)   return <ErrorBanner message={error} />
  if (!data)   return null

  const years = data.years
  const primaryLabel = years.find(y => y.key === primaryYear)?.label ?? primaryYear
  const compareLabel = years.find(y => y.key === compareYear)?.label ?? compareYear

  const expItems = items.filter(i => i.section === 'expenses')
  const salItems = items.filter(i => i.section === 'salaries')

  const sum = (arr: DeptLineItem[], yr: string) => arr.reduce((s, i) => s + (i.values[yr] ?? 0), 0)

  const expPrimary = sum(expItems, primaryYear)
  const expCompare = sum(expItems, compareYear)
  const salPrimary = sum(salItems, primaryYear)
  const salCompare = sum(salItems, compareYear)

  const totalPrimary = expPrimary + salPrimary
  const totalCompare = expCompare + salCompare
  const totalDelta   = totalPrimary - totalCompare
  const totalPct     = Math.abs(totalCompare) > 0.005 ? totalDelta / totalCompare : null

  const totalIncreases = items.filter(i => i.delta > 0).reduce((s, i) => s + i.delta, 0)
  const totalCuts      = Math.abs(items.filter(i => i.delta < 0).reduce((s, i) => s + i.delta, 0))

  const schools  = DEPARTMENTS.filter(d => d.group === 'school')
  const programs = DEPARTMENTS.filter(d => d.group === 'program')

  const color = activeDept.colorClass

  // ── Insight panel narrative lede ───────────────────────────────────────────
  const topUp   = insightIncreases[0] ?? null
  const topDown = insightDecreases[0] ?? null
  const insightLede = (() => {
    const parts: string[] = []
    if (topUp) {
      const pctStr = topUp.pctChange !== null && Math.abs(topUp.pctChange) < 10
        ? ` (${formatPct(topUp.pctChange)})`
        : ''
      parts.push(`${topUp.description} is the largest investment this year, up ${formatDollar(topUp.delta)}${pctStr}.`)
    }
    if (topDown) {
      const pctStr = topDown.pctChange !== null && Math.abs(topDown.pctChange) < 10
        ? ` (${formatPct(topDown.pctChange)})`
        : ''
      parts.push(`${topDown.description} saw the largest reduction at ${formatDollar(Math.abs(topDown.delta))}${pctStr}.`)
    }
    if (parts.length === 0) return null
    return parts.join(' ')
  })()

  const hasInsights = insightIncreases.length > 0 || insightDecreases.length > 0

  return (
    <div className="p-6 space-y-6">

      {/* ── Header ────────────────────────────────────────────────────────── */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Department View</h1>
          <p className="text-gray-500 mt-0.5 text-sm">
            Line-by-line breakdown for each school and program — download as CSV
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => downloadDepartmentCSV(activeDept.label, items, years, primaryYear, compareYear)}
            className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 hover:border-gray-400 shadow-sm"
          >
            <svg className="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
            Download {activeDept.abbrev} CSV
            <span className="text-xs text-gray-400 font-normal">({items.length} rows)</span>
          </button>
        </div>
      </div>

      {/* ── Cross-department comparison ───────────────────────────────────── */}
      {deptStats.length > 0 && (
        <DeptComparisonPanel
          deptStats={deptStats}
          primaryLabel={primaryLabel}
          compareLabel={compareLabel}
          grandTotal={data.grandTotals[primaryYear] ?? 0}
        />
      )}

      {/* ── Department selector ───────────────────────────────────────────── */}
      <div className="bg-white rounded-xl border border-gray-200 p-4 space-y-3">
        {/* Schools row */}
        <div>
          <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">Schools</p>
          <div className="flex flex-wrap gap-2">
            {schools.map(dept => {
              const isActive = dept.id === activeDeptId
              return (
                <button
                  key={dept.id}
                  onClick={() => handleSelect(dept.id)}
                  className={`px-3 py-1.5 rounded-lg text-sm font-medium border transition-colors ${
                    isActive
                      ? ACTIVE_BG[dept.colorClass]
                      : `bg-white text-gray-700 border-gray-200 hover:border-gray-300 hover:bg-gray-50`
                  }`}
                >
                  {dept.abbrev}
                </button>
              )
            })}
          </div>
        </div>

        {/* Programs row */}
        <div>
          <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">Programs</p>
          <div className="flex flex-wrap gap-2">
            {programs.map(dept => {
              const isActive = dept.id === activeDeptId
              return (
                <button
                  key={dept.id}
                  onClick={() => handleSelect(dept.id)}
                  className={`px-3 py-1.5 rounded-lg text-sm font-medium border transition-colors ${
                    isActive
                      ? ACTIVE_BG[dept.colorClass]
                      : `bg-white text-gray-700 border-gray-200 hover:border-gray-300 hover:bg-gray-50`
                  }`}
                >
                  {dept.abbrev}
                </button>
              )
            })}
          </div>
        </div>
      </div>

      {/* ── Active dept header + summary ──────────────────────────────────── */}
      <div className={`bg-white rounded-xl border-l-4 border border-gray-200 overflow-hidden ${BORDER_COLOR[color]}`}>
        {/* Name + description */}
        <div className="px-4 sm:px-6 py-4 border-b border-gray-100">
          <div className="flex items-center gap-2 mb-1">
            <span className={`text-xs font-bold px-2 py-0.5 rounded ${BADGE_COLOR[color]}`}>
              {activeDept.abbrev}
            </span>
            <h2 className="text-lg font-bold text-gray-900">{activeDept.label}</h2>
          </div>
          <p className="text-sm text-gray-500">{activeDept.description}</p>
        </div>

        {/* ── Big metrics ───────────────────────────────────────────────────── */}
        <div className="grid grid-cols-2 sm:grid-cols-4 divide-x divide-gray-100 border-b border-gray-100">
          <div className="px-4 sm:px-6 py-4">
            <p className="text-xs text-gray-400 uppercase tracking-wide mb-1">{primaryLabel} Budget</p>
            <p className="text-2xl font-bold text-gray-900 tabular-nums">
              {formatDollar(totalPrimary)}
            </p>
            {data.grandTotals[primaryYear] > 0 && (
              <p className="text-sm text-gray-500 mt-0.5 tabular-nums">
                {formatPct(totalPrimary / data.grandTotals[primaryYear])} of district
              </p>
            )}
          </div>
          <div className="px-4 sm:px-6 py-4">
            <p className="text-xs text-gray-400 uppercase tracking-wide mb-1">Total Increases</p>
            <p className="text-2xl font-bold text-red-600 tabular-nums">
              {totalIncreases > 0 ? `+${formatDollar(totalIncreases)}` : '—'}
            </p>
          </div>
          <div className="px-4 sm:px-6 py-4">
            <p className="text-xs text-gray-400 uppercase tracking-wide mb-1">Total Cuts</p>
            <p className="text-2xl font-bold text-green-600 tabular-nums">
              {totalCuts > 0 ? `−${formatDollar(totalCuts)}` : '—'}
            </p>
          </div>
          <div className="px-4 sm:px-6 py-4">
            <p className="text-xs text-gray-400 uppercase tracking-wide mb-1">Net Effect</p>
            <p className={`text-2xl font-bold tabular-nums ${totalDelta >= 0 ? 'text-red-600' : 'text-green-600'}`}>
              {totalDelta >= 0 ? '+' : ''}{formatDollar(totalDelta)}
            </p>
            {totalPct !== null && (
              <p className={`text-sm font-semibold tabular-nums mt-0.5 ${totalDelta >= 0 ? 'text-red-500' : 'text-green-500'}`}>
                {formatPct(totalPct)} changed
              </p>
            )}
          </div>
        </div>

        {/* Expenses / Salaries / Total breakdown */}
        <div className="border-b border-gray-100 overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 border-b border-gray-100">
                <th className="px-6 py-2 text-left text-xs font-semibold text-gray-400 uppercase tracking-wide w-32" />
                <th className="px-4 py-2 text-right text-xs font-semibold text-gray-400 uppercase tracking-wide whitespace-nowrap">{compareLabel}</th>
                <th className="px-4 py-2 text-right text-xs font-semibold text-gray-400 uppercase tracking-wide whitespace-nowrap">{primaryLabel}</th>
                <th className="px-4 py-2 text-right text-xs font-semibold text-gray-400 uppercase tracking-wide">Δ Change</th>
                <th className="px-4 py-2 text-right text-xs font-semibold text-gray-400 uppercase tracking-wide">%</th>
              </tr>
            </thead>
            <tbody>
              {expItems.length > 0 && (
                <SummaryRow
                  label="Expenses"
                  badge="bg-blue-100 text-blue-700"
                  compare={expCompare}
                  primary={expPrimary}
                />
              )}
              {salItems.length > 0 && (
                <SummaryRow
                  label="Salaries"
                  badge="bg-purple-100 text-purple-700"
                  compare={salCompare}
                  primary={salPrimary}
                />
              )}
            </tbody>
            <tfoot>
              <tr className="border-t-2 border-gray-200 bg-gray-50">
                <td className="px-6 py-2.5 font-bold text-gray-900 text-sm">Total</td>
                <td className="px-4 py-2.5 text-right tabular-nums font-semibold text-gray-600">{formatDollar(totalCompare)}</td>
                <td className="px-4 py-2.5 text-right tabular-nums font-bold text-gray-900">{formatDollar(totalPrimary)}</td>
                <td className={`px-4 py-2.5 text-right tabular-nums font-bold ${totalDelta >= 0 ? 'text-red-600' : 'text-green-600'}`}>
                  {totalDelta >= 0 ? '+' : ''}{formatDollar(totalDelta)}
                </td>
                <td className="px-4 py-2.5 text-right">
                  <DeltaBadge value={totalPct} size="sm" />
                </td>
              </tr>
            </tfoot>
          </table>
        </div>

        {/* ── Key Changes insight panel ─────────────────────────────────────── */}
        {hasInsights && (
          <div className="border-b border-gray-200">
            {/* Panel header */}
            <div className="px-6 py-3 bg-gray-50 border-b border-gray-100 flex items-center gap-3">
              <span className="text-sm font-semibold text-gray-700">Key Changes</span>
              <span className="text-xs text-gray-400">{primaryLabel} vs {compareLabel}</span>
            </div>

            {/* Narrative lede */}
            {insightLede && (
              <div className="px-6 py-3 border-b border-gray-100 bg-blue-50">
                <p className="text-sm text-blue-900 leading-relaxed">{insightLede}</p>
              </div>
            )}

            {/* Increases / Cuts two-column layout */}
            <div className="grid sm:grid-cols-2 divide-y sm:divide-y-0 sm:divide-x divide-gray-100">
              {/* Increases */}
              <div>
                {insightIncreases.length > 0 ? (
                  <>
                    <div className="px-4 py-2 text-xs font-semibold text-red-500 uppercase tracking-wide bg-red-50 border-b border-red-100">
                      ▲ Increases ({insightIncreases.length}{insightItems.filter(i => i.delta > 0).length > 6 ? '+' : ''})
                    </div>
                    {insightIncreases.map(item => (
                      <DeptInsightRow key={item.id} item={item} compareYear={compareYear} primaryYear={primaryYear} />
                    ))}
                  </>
                ) : (
                  <p className="px-4 py-4 text-xs text-gray-400 italic">No meaningful increases this year.</p>
                )}
              </div>

              {/* Cuts */}
              <div>
                {insightDecreases.length > 0 ? (
                  <>
                    <div className="px-4 py-2 text-xs font-semibold text-green-600 uppercase tracking-wide bg-green-50 border-b border-green-100">
                      ▼ Cuts ({insightDecreases.length}{insightItems.filter(i => i.delta < 0).length > 6 ? '+' : ''})
                    </div>
                    {insightDecreases.map(item => (
                      <DeptInsightRow key={item.id} item={item} compareYear={compareYear} primaryYear={primaryYear} />
                    ))}
                  </>
                ) : (
                  <p className="px-4 py-4 text-xs text-gray-400 italic">No meaningful cuts this year.</p>
                )}
              </div>
            </div>

            {/* Footer note */}
            <div className="px-6 py-2 border-t border-gray-100 bg-gray-50">
              <p className="text-xs text-gray-400">
                Showing top 6 by dollar change. Items under $1,000 change excluded.{' '}
                {insightItems.filter(i => i.delta > 0).length > 6 || insightItems.filter(i => i.delta < 0).length > 6
                  ? 'See the full table below for all changes.'
                  : ''}
              </p>
            </div>
          </div>
        )}

        {/* ── Line items table ─────────────────────────────────────────────── */}
        {items.length === 0 ? (
          <p className="px-6 py-8 text-sm text-gray-400 text-center">
            No line items found for {activeDept.label} in this budget.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200 bg-gray-50">
                  <SortTh col="description" label="Description" sort={sort} onSort={handleSort} />
                  <SortTh col="section"     label="Type"        sort={sort} onSort={handleSort} />
                  <th className="px-3 py-3 text-left text-xs font-semibold text-gray-400 uppercase tracking-wide whitespace-nowrap">
                    Group
                  </th>
                  {years.map(y => (
                    <SortTh
                      key={y.key}
                      col={y.key}
                      label={y.short}
                      sort={sort}
                      onSort={handleSort}
                      right
                    />
                  ))}
                  <SortTh col="delta"     label={`Δ (${compareYear.replace('fy','FY')}→${primaryYear.replace('fy','FY')})`} sort={sort} onSort={handleSort} right />
                  <SortTh col="pctChange" label="% Chg"  sort={sort} onSort={handleSort} right />
                </tr>
              </thead>
              <tbody>
                {sortedItems.map(item => (
                  <DeptRow
                    key={item.id}
                    item={item}
                    years={years}
                    compareYear={compareYear}
                    primaryYear={primaryYear}
                  />
                ))}
              </tbody>
              <tfoot>
                <tr className="border-t-2 border-gray-300 bg-gray-50">
                  <td className="px-3 py-3 font-bold text-gray-900" colSpan={3}>
                    Total ({items.length} line items)
                  </td>
                  {years.map(y => {
                    const sum = items.reduce((s, i) => s + (i.values[y.key] ?? 0), 0)
                    const isCompare  = y.key === compareYear
                    const isPrimary  = y.key === primaryYear
                    return (
                      <td key={y.key} className={`px-3 py-3 text-right tabular-nums ${isPrimary ? 'font-bold text-gray-900' : isCompare ? 'font-semibold text-gray-600' : 'text-gray-400'}`}>
                        {formatDollar(sum)}
                      </td>
                    )
                  })}
                  <td className={`px-3 py-3 text-right tabular-nums font-bold ${totalDelta >= 0 ? 'text-red-600' : 'text-green-600'}`}>
                    {totalDelta >= 0 ? '+' : ''}{formatDollar(totalDelta)}
                  </td>
                  <td className="px-3 py-3 text-right">
                    <DeltaBadge value={totalPct} size="sm" />
                  </td>
                </tr>
              </tfoot>
            </table>
          </div>
        )}
      </div>

      <p className="text-xs text-gray-400 text-center pb-2">
        Note: some line items (e.g. special ed paraprofessionals) may appear in both a school view and a program view — this is intentional. Click any row to explore the parent department.
      </p>
    </div>
  )
}

// ── Summary row (expenses / salaries) ────────────────────────────────────────

function SummaryRow({ label, badge, compare, primary }: {
  label: string
  badge: string
  compare: number
  primary: number
}) {
  const delta = primary - compare
  const pct   = Math.abs(compare) > 0.005 ? delta / compare : null
  return (
    <tr className="border-b border-gray-50">
      <td className="px-6 py-2.5">
        <span className={`text-xs font-semibold px-2 py-0.5 rounded ${badge}`}>{label}</span>
      </td>
      <td className="px-4 py-2.5 text-right tabular-nums text-gray-500">{formatDollar(compare)}</td>
      <td className="px-4 py-2.5 text-right tabular-nums text-gray-700 font-medium">{formatDollar(primary)}</td>
      <td className={`px-4 py-2.5 text-right tabular-nums font-medium ${delta >= 0 ? 'text-red-600' : 'text-green-600'}`}>
        {delta !== 0 ? `${delta > 0 ? '+' : ''}${formatDollar(delta)}` : '—'}
      </td>
      <td className="px-4 py-2.5 text-right">
        <DeltaBadge value={pct} size="sm" />
      </td>
    </tr>
  )
}

// ── Insight panel row ─────────────────────────────────────────────────────────

function DeptInsightRow({ item, compareYear, primaryYear }: {
  item: DeptLineItem
  compareYear: string
  primaryYear: string
}) {
  const isIncrease = item.delta > 0
  const a = item.values[compareYear] ?? 0
  const b = item.values[primaryYear] ?? 0
  const href = item.parentCode ? `/category/${encodeURIComponent(item.parentCode)}` : undefined

  const row = (
    <div className={`flex items-start gap-3 py-2.5 px-4 border-b border-gray-50 last:border-0 ${href ? 'hover:bg-gray-50 cursor-pointer' : ''}`}>
      <div className={`mt-1.5 w-1.5 h-1.5 rounded-full flex-shrink-0 ${isIncrease ? 'bg-red-400' : 'bg-green-500'}`} />
      <div className="flex-1 min-w-0">
        <p className="text-sm text-gray-800 leading-snug">{item.description}</p>
        {item.parentLabel && (
          <p className="text-xs text-gray-400 mt-0.5">
            {item.parentLabel}
            <span className={`ml-1.5 text-xs px-1 rounded ${item.section === 'salaries' ? 'bg-purple-100 text-purple-600' : 'bg-blue-100 text-blue-600'}`}>
              {item.section}
            </span>
          </p>
        )}
      </div>
      <div className="text-right flex-shrink-0 space-y-0.5">
        <div className={`text-sm font-semibold tabular-nums ${isIncrease ? 'text-red-600' : 'text-green-600'}`}>
          {isIncrease ? '+' : ''}{formatDollar(item.delta)}
        </div>
        {item.pctChange !== null && Math.abs(item.pctChange) > 0.005 && (
          <div className={`text-xs tabular-nums ${isIncrease ? 'text-red-400' : 'text-green-500'}`}>
            {formatPct(item.pctChange)}
          </div>
        )}
        {(a !== 0 || b !== 0) && (
          <div className="text-xs text-gray-400 tabular-nums">
            {formatDollar(a)} → {formatDollar(b)}
          </div>
        )}
      </div>
    </div>
  )

  return href ? <Link to={href}>{row}</Link> : <>{row}</>
}

// ── Line item row ─────────────────────────────────────────────────────────────

function DeptRow({ item, years, compareYear, primaryYear }: {
  item: DeptLineItem
  years: YearColumn[]
  compareYear: string
  primaryYear: string
}) {
  const navigate   = useNavigate()
  const isIncrease = item.delta > 0
  const isDecrease = item.delta < 0
  const clickable  = Boolean(item.parentCode)

  return (
    <tr
      onClick={() => clickable && navigate(`/category/${encodeURIComponent(item.parentCode!)}`)}
      className={`border-b border-gray-50 ${clickable ? 'hover:bg-blue-50 cursor-pointer' : ''}`}
    >
      {/* Description */}
      <td className="px-3 py-2">
        <span className="text-gray-800 leading-snug">{item.description}</span>
      </td>
      {/* Section badge */}
      <td className="px-3 py-2 whitespace-nowrap">
        <span className={`inline-block text-xs px-1.5 py-0.5 rounded font-medium ${
          item.section === 'salaries' ? 'bg-purple-100 text-purple-700' : 'bg-blue-100 text-blue-700'
        }`}>
          {item.section}
        </span>
      </td>
      {/* Parent group */}
      <td className="px-3 py-2 text-xs text-gray-400 max-w-[160px] truncate whitespace-nowrap" title={item.parentLabel}>
        {item.parentLabel}
      </td>
      {/* Year values */}
      {years.map(y => {
        const v = item.values[y.key]
        const isCompare = y.key === compareYear
        const isPrimary = y.key === primaryYear
        return (
          <td key={y.key} className={`px-3 py-2 text-right tabular-nums whitespace-nowrap ${
            isPrimary ? 'font-medium text-gray-900' : isCompare ? 'text-gray-600' : 'text-gray-300'
          }`}>
            {v !== null && v !== 0 ? formatDollar(v) : <span className="text-gray-200">—</span>}
          </td>
        )
      })}
      {/* Delta */}
      <td className={`px-3 py-2 text-right tabular-nums font-medium whitespace-nowrap ${
        isIncrease ? 'text-red-600' : isDecrease ? 'text-green-600' : 'text-gray-400'
      }`}>
        {item.delta !== 0
          ? `${isIncrease ? '+' : ''}${formatDollar(item.delta)}`
          : <span className="text-gray-300">—</span>}
      </td>
      {/* % Change */}
      <td className="px-3 py-2 text-right whitespace-nowrap">
        <DeltaBadge value={item.pctChange} size="sm" />
      </td>
    </tr>
  )
}

// ── Cross-department comparison ───────────────────────────────────────────────

interface DeptStat {
  id: string
  label: string
  abbrev: string
  group: 'school' | 'program'
  colorClass: string
  increases: number
  cuts: number
  net: number
  churn: number
  baseTotal: number
  primaryTotal: number
  churnPct: number | null  // churn / baseTotal — dollars moved as % of prior-year budget
  topIncrease: { description: string; delta: number } | null
  topCut:      { description: string; delta: number } | null
}

const BAR_HALF_PX = 96 // max px for each side of the diverging bar

// Tailwind bg class for each colorClass key
const BAR_BG: Record<string, string> = {
  sky:     'bg-sky-400',    amber:   'bg-amber-400',  violet:  'bg-violet-500',
  rose:    'bg-rose-500',   purple:  'bg-purple-500', green:   'bg-green-500',
  slate:   'bg-slate-400',  teal:    'bg-teal-400',   emerald: 'bg-emerald-500',
  orange:  'bg-orange-400', cyan:    'bg-cyan-400',   stone:   'bg-stone-400',
  indigo:  'bg-indigo-400',
}

function churnImpactBadge(pct: number | null): { label: string; className: string } | null {
  if (pct === null) return null
  if (pct >= 0.20) return { label: `${formatPct(pct)} changed`, className: 'bg-orange-100 text-orange-700' }
  if (pct >= 0.08) return { label: `${formatPct(pct)} changed`, className: 'bg-amber-100 text-amber-700' }
  if (pct >= 0.02) return { label: `${formatPct(pct)} changed`, className: 'bg-gray-100 text-gray-500' }
  return null // below 2% — noise, not worth showing
}

// ── Proportion bars (budget share + movement share) ───────────────────────────

function PropBarGroup({ label, stats, staggerLabels = false }: {
  label: string
  stats: DeptStat[]
  staggerLabels?: boolean
}) {
  const budgetTotal = stats.reduce((s, d) => s + d.primaryTotal, 0)

  // Sort biggest budget first so largest segments land on the left
  const sorted = [...stats].sort((a, b) => b.primaryTotal - a.primaryTotal)

  // Pre-compute segment center positions (as % of total width) for label placement
  let cumPct = 0
  const budgetSegs = sorted.map(d => {
    const pct = budgetTotal > 0 ? d.primaryTotal / budgetTotal : 0
    const center = cumPct + pct / 2
    cumPct += pct
    return { ...d, pct, center }
  }).filter(s => s.pct >= 0.003)

  const BAR_H = staggerLabels ? 'h-9' : 'h-9'

  return (
    <div>
      <div className="flex items-baseline justify-between mb-2">
        <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">{label}</p>
        <p className="text-xs text-gray-400 tabular-nums">{formatDollar(budgetTotal)} total</p>
      </div>

      {/* Budget share bar */}
      <div className="text-xs text-gray-400 mb-0.5">Budget share</div>
      <div
        className="relative mb-1"
        style={{ paddingBottom: staggerLabels ? '3.5rem' : '0' }}
      >
        <div className={`flex ${BAR_H} rounded-lg overflow-hidden gap-px bg-gray-200`}>
          {budgetSegs.map(s => (
            <div
              key={s.id}
              style={{ width: `${(s.pct * 100).toFixed(2)}%` }}
              className={`${BAR_BG[s.colorClass]} flex items-center justify-center overflow-hidden`}
              title={`${s.label}: ${formatDollar(s.primaryTotal)} (${formatPct(s.pct)})`}
            >
              {/* Inside label — only for wide segments when not using stagger mode */}
              {!staggerLabels && s.pct >= 0.09 && (
                <span className="text-xs font-bold text-white drop-shadow px-1 truncate select-none">
                  {s.abbrev}
                </span>
              )}
              {/* Inside label for stagger mode only on very wide segments */}
              {staggerLabels && s.pct >= 0.18 && (
                <span className="text-xs font-bold text-white drop-shadow px-1 truncate select-none">
                  {s.abbrev}
                </span>
              )}
            </div>
          ))}
        </div>

        {/* Staggered below-bar labels — every segment gets a label */}
        {staggerLabels && budgetSegs.map((s, i) => {
          const row = i % 2  // 0 = close row, 1 = far row
          return (
            <div
              key={s.id}
              className="absolute flex flex-col items-center pointer-events-none"
              style={{
                left: `${(s.center * 100).toFixed(2)}%`,
                top: '36px',
                transform: 'translateX(-50%)',
              }}
            >
              {/* Tick line — longer for far-row labels so they align better */}
              <div
                className="w-px bg-gray-300 flex-shrink-0"
                style={{ height: row === 0 ? '4px' : '16px' }}
              />
              <span className={`text-xs font-medium whitespace-nowrap leading-none ${
                s.pct < 0.06 ? 'text-gray-500' : 'text-gray-700'
              }`}>
                {s.abbrev}
              </span>
            </div>
          )
        })}
      </div>

      {/* Legend — schools bar only (programs bar has staggered labels already) */}
      {!staggerLabels && (
        <div className="flex flex-wrap gap-x-4 gap-y-1">
          {budgetSegs.map(s => (
            <div key={s.id} className="flex items-center gap-1.5">
              <div className={`w-2.5 h-2.5 rounded-sm flex-shrink-0 ${BAR_BG[s.colorClass]}`} />
              <span className="text-xs text-gray-700 font-medium">{s.abbrev}</span>
              <span className="text-xs text-gray-400 tabular-nums">{formatPct(s.pct)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function DeptBarRow({ d, maxBar, grandTotal }: { d: DeptStat; maxBar: number; grandTotal: number }) {
  const cutPx    = maxBar > 0 ? Math.round((d.cuts      / maxBar) * BAR_HALF_PX) : 0
  const incPx    = maxBar > 0 ? Math.round((d.increases / maxBar) * BAR_HALF_PX) : 0
  const netColor = d.net > 0 ? 'text-red-600' : d.net < 0 ? 'text-green-600' : 'text-gray-400'
  const impact   = churnImpactBadge(d.churnPct)

  return (
    <div className="flex items-center gap-3 px-4 py-2 hover:bg-gray-50 border-b border-gray-50 last:border-0">
      {/* Name */}
      <div className="w-28 flex-shrink-0 text-sm text-gray-700 font-medium truncate" title={d.label}>
        {d.abbrev}
      </div>

      {/* Total budget */}
      <div className="w-24 flex-shrink-0 text-right text-sm tabular-nums text-gray-600 font-medium">
        {formatDollar(d.primaryTotal)}
      </div>

      {/* % of district — prominent callout */}
      {grandTotal > 0 && (
        <div className="w-20 flex-shrink-0 hidden sm:flex justify-center">
          <div className="bg-indigo-50 rounded-lg px-2 py-1 text-center min-w-[56px]">
            <div className="text-base font-bold text-indigo-700 tabular-nums leading-tight">
              {formatPct(d.primaryTotal / grandTotal)}
            </div>
            <div className="text-xs text-indigo-400 leading-tight whitespace-nowrap">of district</div>
          </div>
        </div>
      )}

      {/* Diverging bar */}
      <div className="flex items-center flex-shrink-0">
        {/* Cuts side — right-aligned */}
        <div style={{ width: BAR_HALF_PX }} className="flex justify-end">
          {d.cuts > 0 && (
            <div
              className="h-4 bg-green-400 rounded-l-full opacity-80"
              style={{ width: cutPx }}
              title={`Cuts: −${formatDollar(d.cuts)}`}
            />
          )}
        </div>
        {/* Center divider */}
        <div className="w-px h-5 bg-gray-300 mx-0.5 flex-shrink-0" />
        {/* Increases side — left-aligned */}
        <div style={{ width: BAR_HALF_PX }}>
          {d.increases > 0 && (
            <div
              className="h-4 bg-red-400 rounded-r-full opacity-80"
              style={{ width: incPx }}
              title={`Increases: +${formatDollar(d.increases)}`}
            />
          )}
        </div>
      </div>

      {/* Net */}
      <div className={`w-20 flex-shrink-0 text-right text-sm font-semibold tabular-nums ${netColor}`}>
        {d.net !== 0 ? `${d.net > 0 ? '+' : ''}${formatDollar(d.net)}` : '—'}
      </div>

      {/* Impact badge */}
      <div className="w-32 flex-shrink-0 hidden sm:flex items-center">
        {impact && (
          <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${impact.className}`}>
            {impact.label}
          </span>
        )}
      </div>
    </div>
  )
}

function DeptComparisonPanel({ deptStats, primaryLabel, compareLabel, grandTotal }: {
  deptStats: DeptStat[]
  primaryLabel: string
  compareLabel: string
  grandTotal: number
}) {
  const maxBar = Math.max(...deptStats.map(d => Math.max(d.increases, d.cuts)), 1)

  const topAdded    = [...deptStats].filter(d => d.increases > 0).sort((a, b) => b.increases - a.increases)[0] ?? null
  const topCut      = [...deptStats].filter(d => d.cuts > 0).sort((a, b) => b.cuts - a.cuts)[0] ?? null
  // "Most turbulent" = most churn where BOTH sides are non-zero
  const topChurn    = [...deptStats].filter(d => d.increases > 0 && d.cuts > 0).sort((a, b) => b.churn - a.churn)[0] ?? null
  // "Most impacted" = highest churn as % of base budget
  const topImpacted = [...deptStats].filter(d => d.churnPct !== null).sort((a, b) => (b.churnPct ?? 0) - (a.churnPct ?? 0))[0] ?? null

  const schools  = deptStats.filter(d => d.group === 'school')
  const programs = [...deptStats.filter(d => d.group === 'program')].sort((a, b) => b.churn - a.churn)

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">

      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-100">
        <h2 className="text-base font-bold text-gray-900">Budget Movement by Department</h2>
        <p className="text-xs text-gray-400 mt-0.5">
          {primaryLabel} vs {compareLabel} — bars show dollars added
          <span className="inline-block w-3 h-2.5 bg-red-400 rounded-sm opacity-80 mx-1 align-middle" />
          and cut
          <span className="inline-block w-3 h-2.5 bg-green-400 rounded-sm opacity-80 mx-1 align-middle" />
          in each department. A modest net can hide significant churn in both directions.
        </p>
      </div>

      {/* Proportion bars — budget share & movement share by group */}
      <div className="px-6 py-5 border-b border-gray-100 space-y-8">
        <PropBarGroup label="Schools" stats={deptStats.filter(d => d.group === 'school')} />
        <PropBarGroup label="Programs" stats={deptStats.filter(d => d.group === 'program')} staggerLabels />
      </div>

      {/* Spotlight row */}
      {(topAdded || topCut || topChurn || topImpacted) && (
        <div className="grid grid-cols-2 sm:grid-cols-4 divide-x divide-gray-100 border-b border-gray-100">
          {topAdded && (
            <div className="px-4 py-3">
              <p className="text-xs text-gray-400 uppercase tracking-wide mb-0.5">Most Added</p>
              <p className="text-sm font-semibold text-gray-800">{topAdded.label}</p>
              <p className="text-xl font-bold text-red-600 tabular-nums">+{formatDollar(topAdded.increases)}</p>
              {topAdded.topIncrease && (
                <p className="text-xs text-gray-500 mt-1 leading-snug">
                  Led by <span className="font-medium text-gray-700">{topAdded.topIncrease.description}</span>
                  {' '}(+{formatDollar(topAdded.topIncrease.delta)})
                </p>
              )}
            </div>
          )}
          {topCut && (
            <div className="px-4 py-3">
              <p className="text-xs text-gray-400 uppercase tracking-wide mb-0.5">Most Cut</p>
              <p className="text-sm font-semibold text-gray-800">{topCut.label}</p>
              <p className="text-xl font-bold text-green-600 tabular-nums">−{formatDollar(topCut.cuts)}</p>
              {topCut.topCut && (
                <p className="text-xs text-gray-500 mt-1 leading-snug">
                  Led by <span className="font-medium text-gray-700">{topCut.topCut.description}</span>
                  {' '}({formatDollar(topCut.topCut.delta)})
                </p>
              )}
            </div>
          )}
          {topChurn && (
            <div className="px-4 py-3">
              <p className="text-xs text-gray-400 uppercase tracking-wide mb-0.5">Most Turbulent</p>
              <p className="text-sm font-semibold text-gray-800">{topChurn.label}</p>
              <p className="text-sm font-bold text-amber-600 tabular-nums">{formatDollar(topChurn.churn)} moved</p>
              <p className="text-xs text-gray-400 mt-0.5">
                +{formatDollar(topChurn.increases)} added, −{formatDollar(topChurn.cuts)} cut
              </p>
              {(() => {
                const top = topChurn.topIncrease && topChurn.topCut
                  ? (topChurn.topIncrease.delta >= Math.abs(topChurn.topCut.delta) ? topChurn.topIncrease : topChurn.topCut)
                  : (topChurn.topIncrease ?? topChurn.topCut)
                return top ? (
                  <p className="text-xs text-gray-500 mt-1 leading-snug">
                    Biggest mover: <span className="font-medium text-gray-700">{top.description}</span>
                    {' '}({top.delta > 0 ? '+' : ''}{formatDollar(top.delta)})
                  </p>
                ) : null
              })()}
            </div>
          )}
          {topImpacted && topImpacted.churnPct !== null && (
            <div className="px-4 py-3">
              <p className="text-xs text-gray-400 uppercase tracking-wide mb-0.5">Most Impacted</p>
              <p className="text-sm font-semibold text-gray-800">{topImpacted.label}</p>
              <p className="text-xl font-bold text-orange-600 tabular-nums">{formatPct(topImpacted.churnPct)}</p>
              <p className="text-xs text-gray-400 mt-0.5">of budget in motion</p>
              {(() => {
                const top = topImpacted.topIncrease && topImpacted.topCut
                  ? (topImpacted.topIncrease.delta >= Math.abs(topImpacted.topCut.delta) ? topImpacted.topIncrease : topImpacted.topCut)
                  : (topImpacted.topIncrease ?? topImpacted.topCut)
                return top ? (
                  <p className="text-xs text-gray-500 mt-1 leading-snug">
                    Biggest mover: <span className="font-medium text-gray-700">{top.description}</span>
                    {' '}({top.delta > 0 ? '+' : ''}{formatDollar(top.delta)})
                  </p>
                ) : null
              })()}
            </div>
          )}
        </div>
      )}

      {/* Column headers */}
      <div className="flex items-center gap-3 px-4 py-1.5 border-b border-gray-100 bg-gray-50">
        <div className="w-28 flex-shrink-0" />
        <div className="w-24 flex-shrink-0 text-right text-xs font-semibold text-gray-400 uppercase tracking-wide">Total Budget</div>
        <div className="w-20 flex-shrink-0 hidden sm:block text-center text-xs font-semibold text-indigo-400 uppercase tracking-wide">District %</div>
        <div className="flex items-center flex-shrink-0">
          <div style={{ width: BAR_HALF_PX }} className="text-right pr-1">
            <span className="text-xs font-semibold text-green-600 uppercase tracking-wide">◄ Cuts</span>
          </div>
          <div className="w-px mx-0.5" />
          <div style={{ width: BAR_HALF_PX }} className="pl-1">
            <span className="text-xs font-semibold text-red-500 uppercase tracking-wide">Adds ►</span>
          </div>
        </div>
        <div className="w-20 flex-shrink-0 text-right text-xs font-semibold text-gray-400 uppercase tracking-wide">Net</div>
        <div className="w-32 flex-shrink-0 hidden sm:block text-xs font-semibold text-gray-400 uppercase tracking-wide">% Changed</div>
      </div>

      {/* Schools */}
      <div>
        <div className="px-4 py-1 bg-gray-50 border-b border-gray-100">
          <span className="text-xs font-semibold text-gray-400 uppercase tracking-wide">Schools</span>
        </div>
        {schools.map(d => <DeptBarRow key={d.id} d={d} maxBar={maxBar} grandTotal={grandTotal} />)}
      </div>

      {/* Programs — sorted by churn so most turbulent float up */}
      <div>
        <div className="px-4 py-1 bg-gray-50 border-b border-gray-100">
          <span className="text-xs font-semibold text-gray-400 uppercase tracking-wide">Programs</span>
          <span className="ml-2 text-xs text-gray-400 normal-case">sorted by total movement</span>
        </div>
        {programs.map(d => <DeptBarRow key={d.id} d={d} maxBar={maxBar} grandTotal={grandTotal} />)}
      </div>
    </div>
  )
}

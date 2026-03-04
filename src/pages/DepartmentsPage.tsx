import { useMemo, useState } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import type { YearColumn } from '../data/types'
import { useBudgetData } from '../hooks/useBudgetData'
import { useBudgetStore } from '../store/budgetStore'
import { LoadingSpinner } from '../components/ui/LoadingSpinner'
import { ErrorBanner } from '../components/ui/ErrorBanner'
import { DeltaBadge } from '../components/charts/DeltaBadge'
import { formatDollar } from '../data/transforms'
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

  const schools  = DEPARTMENTS.filter(d => d.group === 'school')
  const programs = DEPARTMENTS.filter(d => d.group === 'program')

  const color = activeDept.colorClass

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

        {/* ── Big picture metric ────────────────────────────────────────────── */}
        <div className="px-4 sm:px-6 py-4 border-b border-gray-100 flex items-center justify-between gap-4 flex-wrap">
          <div>
            <p className="text-xs text-gray-400 uppercase tracking-wide mb-0.5">{primaryLabel} Budget</p>
            <p className="text-3xl font-bold text-gray-900 tabular-nums">{formatDollar(totalPrimary)}</p>
          </div>
          <div className="text-right">
            <p className="text-xs text-gray-400 uppercase tracking-wide mb-0.5">vs {compareLabel}</p>
            <p className={`text-2xl font-bold tabular-nums ${totalDelta >= 0 ? 'text-red-600' : 'text-green-600'}`}>
              {totalDelta >= 0 ? '+' : ''}{formatDollar(totalDelta)}
            </p>
            <div className="mt-1">
              <DeltaBadge value={totalPct} size="sm" />
            </div>
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

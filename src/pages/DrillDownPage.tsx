import { useMemo } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useBudgetStore } from '../store/budgetStore'
import { useBudgetData } from '../hooks/useBudgetData'
import { buildTrendData, formatDollar } from '../data/transforms'
import { LineItemTable } from '../components/tables/LineItemTable'
import { YearTrendLine } from '../components/charts/YearTrendLine'
import { DeltaBadge } from '../components/charts/DeltaBadge'
import { LoadingSpinner } from '../components/ui/LoadingSpinner'
import { ErrorBanner } from '../components/ui/ErrorBanner'

export function DrillDownPage() {
  const { code } = useParams<{ code: string }>()
  const { data, loading, error } = useBudgetData()
  const { primaryYear, compareYear } = useBudgetStore()

  const group = useMemo(
    () => data?.groups.find(g => g.code === decodeURIComponent(code ?? '')),
    [data, code]
  )

  const trendData = useMemo(
    () => (data && group) ? buildTrendData(group, data.years) : [],
    [data, group]
  )

  const lineItems = useMemo(
    () => group ? group.lineItems : [],
    [group]
  )

  if (loading) return <LoadingSpinner />
  if (error) return <ErrorBanner message={error} />
  if (!data) return null
  if (!group) {
    return (
      <div className="p-6">
        <div className="text-center py-12">
          <p className="text-gray-500">Budget category not found: <code>{code}</code></p>
          <Link to="/" className="text-blue-500 hover:underline mt-2 inline-block">← Back to Dashboard</Link>
        </div>
      </div>
    )
  }

  const primaryYearLabel = data.years.find(y => y.key === primaryYear)?.label ?? primaryYear
  const compareVal = group.totals[compareYear] ?? 0
  const primaryVal = group.totals[primaryYear] ?? 0
  const pctChange = Math.abs(compareVal) > 0.005 ? (primaryVal - compareVal) / compareVal : null

  return (
    <div className="p-6 space-y-6">
      {/* Breadcrumb */}
      <nav className="flex items-center gap-2 text-sm text-gray-500">
        <Link to="/" className="hover:text-blue-600">Dashboard</Link>
        <span>/</span>
        <span className="text-gray-400">{group.categoryLabel}</span>
        <span>/</span>
        <span className="text-gray-900 font-medium">{group.label}</span>
      </nav>

      {/* Header */}
      <div className="flex items-start justify-between flex-wrap gap-4">
        <div>
          <p className="text-xs font-mono text-gray-400 mb-1">{group.code}</p>
          <h1 className="text-2xl font-bold text-gray-900">{group.label}</h1>
          <p className="text-gray-500 mt-1 capitalize">{group.section} · {group.categoryLabel}</p>
        </div>
        <div className="text-right">
          <p className="text-xs text-gray-500 uppercase tracking-wide">{primaryYearLabel}</p>
          <p className="text-2xl font-bold text-gray-900">{formatDollar(primaryVal)}</p>
          <DeltaBadge value={pctChange} />
        </div>
      </div>

      {/* KPIs — one card per discovered year */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        {data.years.map(y => (
          <div
            key={y.key}
            className={`rounded-lg border p-3 ${y.key === primaryYear ? 'border-blue-200 bg-blue-50' : 'border-gray-200 bg-white'}`}
          >
            <p className="text-xs text-gray-500 uppercase tracking-wide">{y.short}</p>
            <p className={`font-semibold mt-1 ${y.key === primaryYear ? 'text-blue-700' : 'text-gray-800'}`}>
              {formatDollar(group.totals[y.key] ?? 0)}
            </p>
          </div>
        ))}
      </div>

      {/* Trend chart */}
      <div className="bg-white rounded-xl border border-gray-200 p-4">
        <h2 className="font-semibold text-gray-900 mb-4">Budget Trend</h2>
        <YearTrendLine data={trendData} />
      </div>

      {/* Line items */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="px-4 py-3 border-b border-gray-200 flex items-center justify-between">
          <h2 className="font-semibold text-gray-900">Line Items</h2>
          <span className="text-sm text-gray-500">{lineItems.length} items</span>
        </div>
        <LineItemTable items={lineItems} showGroupHeader={false} />
      </div>
    </div>
  )
}

import { useMemo } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useBudgetStore } from '../store/budgetStore'
import { useBudgetData } from '../hooks/useBudgetData'
import { formatDollar } from '../data/transforms'
import type { TrendDatum } from '../data/transforms'
import { YearTrendLine } from '../components/charts/YearTrendLine'
import { DeltaBadge } from '../components/charts/DeltaBadge'
import { LoadingSpinner } from '../components/ui/LoadingSpinner'
import { ErrorBanner } from '../components/ui/ErrorBanner'

export function LineItemDetailPage() {
  const { id } = useParams<{ id: string }>()
  const { data, loading, error } = useBudgetData()
  const { primaryYear } = useBudgetStore()
  const navigate = useNavigate()

  const item = useMemo(
    () => data?.lineItems.find(i => i.id === decodeURIComponent(id ?? '')),
    [data, id],
  )

  const trendData = useMemo((): TrendDatum[] => {
    if (!data || !item) return []
    return data.years.map(y => ({
      year: y.short,
      fy: y.key,
      value: item.values[y.key] ?? 0,
      isProjected: y.isProjected,
    }))
  }, [data, item])

  if (loading) return <LoadingSpinner />
  if (error) return <ErrorBanner message={error} />
  if (!data) return null

  if (!item) {
    return (
      <div className="p-6 text-center py-12">
        <p className="text-gray-500">Line item not found.</p>
        <button onClick={() => navigate(-1)} className="text-blue-500 hover:underline mt-2 inline-block">
          ← Back
        </button>
      </div>
    )
  }

  const primaryIdx = data.years.findIndex(y => y.key === primaryYear)
  const priorYearKey = primaryIdx > 0 ? data.years[primaryIdx - 1].key : data.years[0].key

  const primaryVal = item.values[primaryYear] ?? 0
  const priorVal = item.values[priorYearKey] ?? 0
  const pctChange = Math.abs(priorVal) > 0.005 ? (primaryVal - priorVal) / priorVal : null

  return (
    <div className="p-6 space-y-6">
      {/* Back button */}
      <button
        onClick={() => navigate(-1)}
        className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-blue-600 transition-colors"
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
        </svg>
        Back
      </button>

      {/* Header */}
      <div className="flex items-start justify-between flex-wrap gap-4">
        <div>
          {item.budgetCode && (
            <p className="text-xs font-mono text-gray-400 mb-1">{item.budgetCode}</p>
          )}
          <h1 className="text-2xl font-bold text-gray-900">{item.description}</h1>
          <p className="text-gray-500 mt-1 capitalize">
            {item.section} · {item.categoryLabel ?? 'Uncategorized'}
          </p>
        </div>
        <div className="text-right">
          <p className="text-xs text-gray-500 uppercase tracking-wide">
            {data.years.find(y => y.key === primaryYear)?.label ?? primaryYear}
          </p>
          <p className="text-2xl font-bold text-gray-900">{formatDollar(primaryVal)}</p>
          <DeltaBadge value={pctChange} />
        </div>
      </div>

      {/* Year-by-year values */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        {data.years.map(y => (
          <div
            key={y.key}
            className={`rounded-lg border p-3 ${
              y.key === primaryYear ? 'border-blue-200 bg-blue-50' : 'border-gray-200 bg-white'
            }`}
          >
            <p className="text-xs text-gray-500 uppercase tracking-wide">{y.short}</p>
            <p className={`font-semibold mt-1 ${y.key === primaryYear ? 'text-blue-700' : 'text-gray-800'}`}>
              {item.values[y.key] != null ? formatDollar(item.values[y.key]!) : '—'}
            </p>
          </div>
        ))}
      </div>

      {/* Trend chart */}
      <div className="bg-white rounded-xl border border-gray-200 p-4">
        <h2 className="font-semibold text-gray-900 mb-4">Budget Trend</h2>
        <YearTrendLine data={trendData} />
      </div>
    </div>
  )
}

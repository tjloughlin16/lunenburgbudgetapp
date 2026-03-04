import { useMemo, useState } from 'react'
import { useBudgetStore } from '../store/budgetStore'
import { useBudgetData } from '../hooks/useBudgetData'
import { buildTreemapData, buildCategoryBarData, buildTrendData } from '../data/transforms'
import { formatDollar } from '../data/transforms'
import { BudgetTreemap } from '../components/charts/BudgetTreemap'
import { CategoryBarChart } from '../components/charts/CategoryBarChart'
import { YearTrendLine } from '../components/charts/YearTrendLine'
import { SummaryTable } from '../components/tables/SummaryTable'
import { LoadingSpinner } from '../components/ui/LoadingSpinner'
import { ErrorBanner } from '../components/ui/ErrorBanner'
import { DeltaBadge } from '../components/charts/DeltaBadge'
import { SectionToggle } from '../components/filters/SectionToggle'
import { CategoryFilter } from '../components/filters/CategoryFilter'
import { ExportButton } from '../components/ui/ExportButton'

export function DashboardPage() {
  const { data, loading, error } = useBudgetData()
  const { primaryYear, activeSection, activeCategories } = useBudgetStore()
  const [activeTab, setActiveTab] = useState<'treemap' | 'bar' | 'trend'>('treemap')

  const priorYearKey = useMemo(() => {
    if (!data) return ''
    const idx = data.years.findIndex(y => y.key === primaryYear)
    return idx > 0 ? data.years[idx - 1].key : data.years[0].key
  }, [data, primaryYear])

  const treemapData = useMemo(
    () => (data ? buildTreemapData(data.groups, primaryYear, activeSection, activeCategories, data.years) : []),
    [data, primaryYear, activeSection, activeCategories]
  )

  const barData = useMemo(
    () => (data ? buildCategoryBarData(data.groups, activeSection, data.years) : []),
    [data, activeSection]
  )

  const trendData = useMemo(
    () => data ? buildTrendData({ totals: data.grandTotals }, data.years) : [],
    [data]
  )

  if (loading) return <LoadingSpinner />
  if (error) return <ErrorBanner message={error} />
  if (!data) return null

  const primaryYearLabel = data.years.find(y => y.key === primaryYear)?.label ?? primaryYear
  const compareYearLabel = data.years.find(y => y.key === priorYearKey)?.label ?? priorYearKey

  const pctChange =
    Math.abs(data.grandTotals[priorYearKey] ?? 0) > 0.005
      ? ((data.grandTotals[primaryYear] ?? 0) - (data.grandTotals[priorYearKey] ?? 0)) / (data.grandTotals[priorYearKey] ?? 0)
      : null

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Budget Breakdown</h1>
          <p className="text-gray-500 mt-0.5">{primaryYearLabel} — Lunenburg Public Schools</p>
        </div>
        <div className="flex items-center gap-3">
          <ExportButton />
          <SectionToggle />
        </div>
      </div>

      {/* Category filter */}
      <CategoryFilter />

      {/* KPI cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          {
            label: primaryYearLabel,
            value: formatDollar(data.grandTotals[primaryYear] ?? 0),
            sub: <DeltaBadge value={pctChange} size="sm" />,
            highlight: true,
          },
          {
            label: compareYearLabel,
            value: formatDollar(data.grandTotals[priorYearKey] ?? 0),
            sub: 'Prior year',
          },
          {
            label: 'Total Salaries',
            value: formatDollar(
              data.sections.salaries
                .filter(i => !i.isGroupHeader)
                .reduce((s, i) => s + (i.values[primaryYear] ?? 0), 0)
            ),
            sub: data.years.at(-1)?.short ?? '',
          },
          {
            label: 'Total Expenses',
            value: formatDollar(
              data.sections.expenses
                .filter(i => !i.isGroupHeader)
                .reduce((s, i) => s + (i.values[primaryYear] ?? 0), 0)
            ),
            sub: data.years.at(-1)?.short ?? '',
          },
        ].map(card => (
          <div
            key={card.label}
            className={`rounded-xl p-4 border ${
              card.highlight
                ? 'bg-blue-600 border-blue-600 text-white'
                : 'bg-white border-gray-200'
            }`}
          >
            <p className={`text-xs font-medium uppercase tracking-wide ${card.highlight ? 'text-blue-100' : 'text-gray-500'}`}>
              {card.label}
            </p>
            <p className={`text-xl font-bold mt-1 ${card.highlight ? 'text-white' : 'text-gray-900'}`}>
              {card.value}
            </p>
            <div className={`text-xs mt-0.5 ${card.highlight ? 'text-blue-100' : 'text-gray-400'}`}>
              {card.sub}
            </div>
          </div>
        ))}
      </div>

      {/* Chart tabs */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="flex items-center gap-1 px-4 py-3 border-b border-gray-200">
          <div className="flex gap-1 bg-gray-100 rounded-lg p-1">
            {([
              { id: 'treemap', label: 'Spending Map' },
              { id: 'bar', label: 'By Category' },
              { id: 'trend', label: 'Trend' },
            ] as const).map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-3 py-1.5 rounded-md text-sm transition-colors ${
                  activeTab === tab.id
                    ? 'bg-white text-blue-600 font-medium shadow-sm'
                    : 'text-gray-600 hover:text-gray-800'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
          <p className="ml-auto text-xs text-gray-400">{primaryYearLabel}</p>
        </div>

        <div className="p-4">
          {activeTab === 'treemap' && <BudgetTreemap data={treemapData} />}
          {activeTab === 'bar' && <CategoryBarChart data={barData} />}
          {activeTab === 'trend' && (
            <YearTrendLine data={trendData} title="Total Budget Over Time" />
          )}
        </div>
      </div>

      {/* Summary table */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="px-4 py-3 border-b border-gray-200">
          <h2 className="font-semibold text-gray-900">Summary Totals</h2>
        </div>
        <SummaryTable data={data} />
      </div>
    </div>
  )
}

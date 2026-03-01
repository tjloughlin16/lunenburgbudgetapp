import { useMemo } from 'react'
import { useBudgetStore } from '../store/budgetStore'
import { useBudgetData } from '../hooks/useBudgetData'
import { searchLineItems } from '../data/transforms'
import { LineItemTable } from '../components/tables/LineItemTable'
import { LoadingSpinner } from '../components/ui/LoadingSpinner'
import { ErrorBanner } from '../components/ui/ErrorBanner'
import { ExportButton } from '../components/ui/ExportButton'

export function SearchPage() {
  const { data, loading, error } = useBudgetData()
  const { searchQuery, activeSection, activeCategories } = useBudgetStore()

  const results = useMemo(
    () =>
      data
        ? searchLineItems(data.lineItems, searchQuery, activeSection, activeCategories)
        : [],
    [data, searchQuery, activeSection, activeCategories]
  )

  if (loading) return <LoadingSpinner />
  if (error) return <ErrorBanner message={error} />

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Search Results</h1>
          {searchQuery ? (
            <p className="text-gray-500 mt-0.5">
              {results.length} result{results.length !== 1 ? 's' : ''} for{' '}
              <span className="font-medium text-gray-800">"{searchQuery}"</span>
            </p>
          ) : (
            <p className="text-gray-500 mt-0.5">
              Showing all {results.length} line items — type in the search bar to filter
            </p>
          )}
        </div>
        <ExportButton />
      </div>

      {!data ? null : results.length === 0 ? (
        <div className="text-center py-16 text-gray-400">
          <svg className="w-12 h-12 mx-auto mb-4 opacity-30" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <p className="text-lg">No results found</p>
          <p className="text-sm mt-1">Try a different search term or adjust your filters</p>
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <LineItemTable items={results} />
        </div>
      )}
    </div>
  )
}

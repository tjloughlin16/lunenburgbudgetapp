import { useMemo, useRef, useEffect } from 'react'
import { useBudgetStore } from '../store/budgetStore'
import { useBudgetData } from '../hooks/useBudgetData'
import { searchLineItems } from '../data/transforms'
import { LineItemTable } from '../components/tables/LineItemTable'
import { LoadingSpinner } from '../components/ui/LoadingSpinner'
import { ErrorBanner } from '../components/ui/ErrorBanner'
import { ExportButton } from '../components/ui/ExportButton'
import { SectionToggle } from '../components/filters/SectionToggle'
import { CategoryFilter } from '../components/filters/CategoryFilter'

export function SearchPage() {
  const { data, loading, error } = useBudgetData()
  const { searchQuery, setSearchQuery, activeSection, activeCategories } = useBudgetStore()
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    inputRef.current?.focus()
  }, [])

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
      <div className="flex items-start justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Search</h1>
          {searchQuery ? (
            <p className="text-gray-500 mt-0.5">
              {results.length} result{results.length !== 1 ? 's' : ''} for{' '}
              <span className="font-medium text-gray-800">"{searchQuery}"</span>
            </p>
          ) : (
            <p className="text-gray-500 mt-0.5">
              Search line items across all departments and years
            </p>
          )}
        </div>
        <div className="flex items-center gap-3">
          <SectionToggle />
          <ExportButton />
        </div>
      </div>

      {/* Search input */}
      <div className="relative max-w-lg">
        <svg
          className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400"
          fill="none" stroke="currentColor" viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
            d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
        <input
          ref={inputRef}
          type="text"
          placeholder="Search line items…"
          value={searchQuery}
          onChange={e => setSearchQuery(e.target.value)}
          className="w-full pl-9 pr-8 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
        {searchQuery && (
          <button
            onClick={() => { setSearchQuery(''); inputRef.current?.focus() }}
            className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        )}
      </div>

      <CategoryFilter />

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

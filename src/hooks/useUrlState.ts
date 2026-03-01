import { useEffect, useRef } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useBudgetStore } from '../store/budgetStore'
import type { FiscalYear, Section, CategoryCode } from '../data/types'
import { CATEGORY_CODES } from '../data/types'

export function useUrlState() {
  const [searchParams, setSearchParams] = useSearchParams()
  const store = useBudgetStore()
  const initialized = useRef(false)

  // On mount: read URL → store
  useEffect(() => {
    if (initialized.current) return
    initialized.current = true

    const year = searchParams.get('year') as FiscalYear | null
    const compare = searchParams.get('compare') as FiscalYear | null
    const section = searchParams.get('section') as Section | null
    const cats = searchParams.get('cats')
    const q = searchParams.get('q')

    if (year && store.years.some(y => y.key === year)) store.setPrimaryYear(year)
    if (compare && store.years.some(y => y.key === compare)) store.setCompareYear(compare)
    if (section && ['expenses', 'salaries', 'both'].includes(section))
      store.setActiveSection(section as Section | 'both')
    if (cats) {
      cats.split(',').forEach(c => {
        if (CATEGORY_CODES.includes(c as CategoryCode)) store.toggleCategory(c as CategoryCode)
      })
    }
    if (q) store.setSearchQuery(q)
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // On store change: write store → URL
  useEffect(() => {
    if (!initialized.current) return
    const params: Record<string, string> = {}
    const defaultPrimary = store.years.at(-1)?.key ?? ''
    const defaultCompare = store.years.at(-2)?.key ?? ''
    if (store.primaryYear && store.primaryYear !== defaultPrimary) params.year = store.primaryYear
    if (store.compareYear && store.compareYear !== defaultCompare) params.compare = store.compareYear
    if (store.activeSection !== 'both') params.section = store.activeSection
    if (store.activeCategories.length > 0) params.cats = store.activeCategories.join(',')
    if (store.searchQuery) params.q = store.searchQuery
    setSearchParams(params, { replace: true })
  }, [
    store.primaryYear,
    store.compareYear,
    store.activeSection,
    store.activeCategories,
    store.searchQuery,
  ]) // eslint-disable-line react-hooks/exhaustive-deps
}

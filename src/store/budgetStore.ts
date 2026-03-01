import { create } from 'zustand'
import { parseBudgetFile } from '../data/parser'
import type { BudgetData, FiscalYear, YearColumn, Section, CategoryCode } from '../data/types'

interface BudgetStore {
  data: BudgetData | null
  loading: boolean
  error: string | null
  loadData: (url: string) => Promise<void>

  // Derived from the parsed spreadsheet; empty until data loads
  years: YearColumn[]

  // Filter state (all synced to URL)
  primaryYear: FiscalYear        // the "current" year shown in charts/treemap
  compareYear: FiscalYear        // the "baseline" year used in comparisons
  activeSection: Section | 'both'
  activeCategories: CategoryCode[]
  searchQuery: string

  setPrimaryYear: (y: FiscalYear) => void
  setCompareYear: (y: FiscalYear) => void
  setActiveSection: (s: Section | 'both') => void
  toggleCategory: (c: CategoryCode) => void
  setSearchQuery: (q: string) => void
  resetFilters: () => void
}

export const useBudgetStore = create<BudgetStore>((set, get) => ({
  data: null,
  loading: false,
  error: null,
  years: [],

  // These will be overwritten by real values once data loads
  primaryYear: '',
  compareYear: '',
  activeSection: 'both',
  activeCategories: [],
  searchQuery: '',

  loadData: async (url: string) => {
    set({ loading: true, error: null })
    try {
      const data = await parseBudgetFile(url)
      if (data.parseWarnings.length > 0) {
        console.info('[BudgetParser]', data.parseWarnings.join(' | '))
      }

      // Default to last year as primary, penultimate as compare
      const years = data.years
      const primaryYear = years.at(-1)?.key ?? ''
      const compareYear = years.at(-2)?.key ?? primaryYear

      set({ data, years, loading: false, primaryYear, compareYear })
    } catch (e) {
      set({ error: String(e), loading: false })
    }
  },

  setPrimaryYear: (y) => set({ primaryYear: y }),
  setCompareYear: (y) => set({ compareYear: y }),
  setActiveSection: (s) => set({ activeSection: s }),
  toggleCategory: (c) => {
    const current = get().activeCategories
    const next = current.includes(c)
      ? current.filter(x => x !== c)
      : [...current, c]
    set({ activeCategories: next })
  },
  setSearchQuery: (q) => set({ searchQuery: q }),
  resetFilters: () => {
    const { years } = get()
    set({
      primaryYear: years.at(-1)?.key ?? '',
      compareYear: years.at(-2)?.key ?? '',
      activeSection: 'both',
      activeCategories: [],
      searchQuery: '',
    })
  },
}))

import { useBudgetStore } from '../../store/budgetStore'
import type { FiscalYear } from '../../data/types'

interface Props {
  mode?: 'primary' | 'compare'
  label?: string
}

export function YearSelector({ mode = 'primary', label }: Props) {
  const { years, primaryYear, compareYear, setPrimaryYear, setCompareYear } = useBudgetStore()
  const value        = mode === 'primary' ? primaryYear : compareYear
  const defaultLabel = mode === 'primary' ? 'Year' : 'Compare to'

  // "To" shows all years; "From" only shows years before the current "To"
  const availableYears = mode === 'primary'
    ? years
    : years.filter(y => y.key < primaryYear)

  const handleChange = (newKey: FiscalYear) => {
    if (mode === 'primary') {
      setPrimaryYear(newKey)
      // If From is now >= To, auto-set From to the year immediately before the new To
      if (compareYear >= newKey) {
        const idx = years.findIndex(y => y.key === newKey)
        setCompareYear(idx > 0 ? years[idx - 1].key : years[0].key)
      }
    } else {
      setCompareYear(newKey)
    }
  }

  return (
    <div className="flex items-center gap-2">
      <label className="text-sm text-gray-500 whitespace-nowrap">{label ?? defaultLabel}:</label>
      <select
        value={value}
        onChange={e => handleChange(e.target.value as FiscalYear)}
        className="text-sm border border-gray-300 rounded px-2 py-1 bg-white"
      >
        {availableYears.map(y => (
          <option key={y.key} value={y.key}>{y.short}</option>
        ))}
      </select>
    </div>
  )
}

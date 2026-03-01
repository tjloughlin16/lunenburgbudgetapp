import { useBudgetStore } from '../../store/budgetStore'
import type { FiscalYear } from '../../data/types'

interface Props {
  mode?: 'primary' | 'compare'
}

export function YearSelector({ mode = 'primary' }: Props) {
  const { years, primaryYear, compareYear, setPrimaryYear, setCompareYear } = useBudgetStore()
  const value = mode === 'primary' ? primaryYear : compareYear
  const onChange = mode === 'primary' ? setPrimaryYear : setCompareYear
  const label = mode === 'primary' ? 'Year' : 'Compare to'

  return (
    <div className="flex items-center gap-2">
      <label className="text-sm text-gray-500 whitespace-nowrap">{label}:</label>
      <select
        value={value}
        onChange={e => onChange(e.target.value as FiscalYear)}
        className="text-sm border border-gray-300 rounded px-2 py-1 bg-white"
      >
        {years.map(y => (
          <option key={y.key} value={y.key}>{y.short}</option>
        ))}
      </select>
    </div>
  )
}

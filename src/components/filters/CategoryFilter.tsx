import { useBudgetStore } from '../../store/budgetStore'
import { CATEGORY_CODES, CATEGORY_LABELS, CATEGORY_COLORS } from '../../data/types'
import type { CategoryCode } from '../../data/types'

export function CategoryFilter() {
  const { activeCategories, toggleCategory } = useBudgetStore()

  return (
    <div className="flex flex-wrap items-center gap-1.5">
      {CATEGORY_CODES.map(code => {
        const active = activeCategories.length === 0 || activeCategories.includes(code)
        return (
          <button
            key={code}
            onClick={() => toggleCategory(code as CategoryCode)}
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs border transition-colors ${
              active
                ? 'border-transparent bg-gray-100 text-gray-800 hover:bg-gray-200'
                : 'border-gray-200 text-gray-400 hover:bg-gray-50'
            }`}
          >
            <span
              className="w-2.5 h-2.5 rounded-sm flex-shrink-0"
              style={{ backgroundColor: active ? CATEGORY_COLORS[code as CategoryCode] : '#d1d5db' }}
            />
            {CATEGORY_LABELS[code as CategoryCode]}
          </button>
        )
      })}
      {activeCategories.length > 0 && (
        <button
          onClick={() => activeCategories.forEach(c => toggleCategory(c))}
          className="text-xs text-blue-500 hover:text-blue-700 px-1.5 py-1"
        >
          Clear
        </button>
      )}
    </div>
  )
}

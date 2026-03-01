import { useBudgetStore } from '../../store/budgetStore'
import { CATEGORY_CODES, CATEGORY_LABELS, CATEGORY_COLORS } from '../../data/types'
import type { CategoryCode } from '../../data/types'

export function CategoryFilter() {
  const { activeCategories, toggleCategory } = useBudgetStore()

  return (
    <div className="space-y-1">
      <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide px-2 mb-2">
        Categories
      </p>
      {CATEGORY_CODES.map(code => {
        const active = activeCategories.length === 0 || activeCategories.includes(code)
        return (
          <button
            key={code}
            onClick={() => toggleCategory(code as CategoryCode)}
            className={`flex items-center gap-2 w-full px-2 py-1.5 rounded text-sm transition-colors text-left ${
              active ? 'text-gray-800' : 'text-gray-400'
            } hover:bg-gray-100`}
          >
            <span
              className="w-3 h-3 rounded-sm flex-shrink-0"
              style={{ backgroundColor: active ? CATEGORY_COLORS[code as CategoryCode] : '#d1d5db' }}
            />
            {CATEGORY_LABELS[code as CategoryCode]}
          </button>
        )
      })}
      {activeCategories.length > 0 && (
        <button
          onClick={() => activeCategories.forEach(c => toggleCategory(c))}
          className="text-xs text-blue-500 hover:text-blue-700 px-2 py-1"
        >
          Clear filter
        </button>
      )}
    </div>
  )
}

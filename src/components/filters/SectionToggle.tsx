import { useBudgetStore } from '../../store/budgetStore'
import type { Section } from '../../data/types'

const OPTIONS: { value: Section | 'both'; label: string }[] = [
  { value: 'both', label: 'All' },
  { value: 'expenses', label: 'Expenses' },
  { value: 'salaries', label: 'Salaries' },
]

export function SectionToggle() {
  const { activeSection, setActiveSection } = useBudgetStore()

  return (
    <div className="flex items-center gap-1 bg-gray-100 rounded-lg p-1">
      {OPTIONS.map(opt => (
        <button
          key={opt.value}
          onClick={() => setActiveSection(opt.value)}
          className={`px-3 py-1 text-sm rounded-md transition-colors ${
            activeSection === opt.value
              ? 'bg-white text-blue-600 font-medium shadow-sm'
              : 'text-gray-600 hover:text-gray-800'
          }`}
        >
          {opt.label}
        </button>
      ))}
    </div>
  )
}

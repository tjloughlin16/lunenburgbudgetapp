import Papa from 'papaparse'
import { useBudgetStore } from '../store/budgetStore'
import { searchLineItems } from '../data/transforms'

export function useExport() {
  const { data, activeSection, activeCategories, searchQuery } = useBudgetStore()

  function getFilteredItems() {
    if (!data) return []
    return searchLineItems(data.lineItems, searchQuery, activeSection, activeCategories)
  }

  function exportCSV(filename = 'lunenburg-budget-export.csv') {
    const items = getFilteredItems()
    const years = data?.years ?? []
    const prevLabel = years.at(-2)?.short ?? 'Prior'
    const lastLabel = years.at(-1)?.short ?? 'Current'

    const rows = items.map(item => ({
      'Budget Code': item.budgetCode ?? '',
      Description: item.description,
      Section: item.section,
      Category: item.categoryLabel ?? '',
      ...Object.fromEntries(
        years.map(y => [
          y.label,
          item.values[y.key] !== null ? item.values[y.key]!.toFixed(2) : '',
        ])
      ),
      [`% Change (${prevLabel}→${lastLabel})`]:
        item.pctChange !== null ? `${(item.pctChange * 100).toFixed(1)}%` : '',
    }))

    const csv = Papa.unparse(rows)
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  }

  return { exportCSV, filteredCount: getFilteredItems().length }
}

import { useEffect } from 'react'
import { useBudgetStore } from '../store/budgetStore'

export function useBudgetData() {
  const { loadData, data, loading, error } = useBudgetStore()

  useEffect(() => {
    if (!data && !loading) {
      loadData('./data/budget.xlsx')
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  return { data, loading, error }
}

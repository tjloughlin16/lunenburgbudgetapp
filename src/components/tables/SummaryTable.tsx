import type { BudgetData } from '../../data/types'
import { formatDollar } from '../../data/transforms'
import { DeltaBadge } from '../charts/DeltaBadge'

interface Props {
  data: BudgetData
}

export function SummaryTable({ data }: Props) {
  const { years } = data
  const prevYearKey = years.at(-2)?.key
  const lastYearKey = years.at(-1)?.key

  const emptyTotals = () => Object.fromEntries(years.map(y => [y.key, 0])) as Record<string, number>

  const expenseTotals = data.sections.expenses.reduce((acc, item) => {
    if (item.isGroupHeader) return acc
    for (const y of years) acc[y.key] = (acc[y.key] ?? 0) + (item.values[y.key] ?? 0)
    return acc
  }, emptyTotals())

  const salaryTotals = data.sections.salaries.reduce((acc, item) => {
    if (item.isGroupHeader) return acc
    for (const y of years) acc[y.key] = (acc[y.key] ?? 0) + (item.values[y.key] ?? 0)
    return acc
  }, emptyTotals())

  const rows = [
    { label: 'Total Expenses', totals: expenseTotals, indent: true },
    { label: 'Total Salaries', totals: salaryTotals, indent: true },
    { label: 'Grand Total', totals: data.grandTotals as Record<string, number>, indent: false },
  ]

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-200 bg-gray-50">
            <th className="px-4 py-2 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">
              Category
            </th>
            {years.map(y => (
              <th
                key={y.key}
                className="px-4 py-2 text-right text-xs font-semibold text-gray-500 uppercase tracking-wide whitespace-nowrap"
              >
                {y.short}
              </th>
            ))}
            <th className="px-4 py-2 text-right text-xs font-semibold text-gray-500 uppercase tracking-wide">
              Change
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map(row => {
            const pct =
              prevYearKey && lastYearKey && Math.abs(row.totals[prevYearKey] ?? 0) > 0.005
                ? ((row.totals[lastYearKey] ?? 0) - (row.totals[prevYearKey] ?? 0)) / (row.totals[prevYearKey] ?? 0)
                : null
            return (
              <tr
                key={row.label}
                className={`border-b border-gray-100 ${!row.indent ? 'bg-gray-50 font-semibold' : ''}`}
              >
                <td className={`px-4 py-2 ${row.indent ? 'pl-8 text-gray-600' : 'text-gray-900'}`}>
                  {row.label}
                </td>
                {years.map(y => (
                  <td key={y.key} className="px-4 py-2 text-right tabular-nums">
                    {formatDollar(row.totals[y.key] ?? 0)}
                  </td>
                ))}
                <td className="px-4 py-2 text-right">
                  <DeltaBadge value={pct} size="sm" />
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  flexRender,
  createColumnHelper,
  type SortingState,
} from '@tanstack/react-table'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import type { LineItem } from '../../data/types'
import { formatDollar } from '../../data/transforms'
import { DeltaBadge } from '../charts/DeltaBadge'
import { useBudgetStore } from '../../store/budgetStore'

interface Props {
  items: LineItem[]
  showGroupHeader?: boolean // reserved for future use
}

const columnHelper = createColumnHelper<LineItem>()

export function LineItemTable({ items }: Props) {
  const [sorting, setSorting] = useState<SortingState>([])
  const navigate = useNavigate()
  const { years } = useBudgetStore()

  const columns = [
    columnHelper.accessor('budgetCode', {
      header: 'Code',
      cell: info => (
        <span className="text-xs font-mono text-gray-500">{info.getValue() ?? '—'}</span>
      ),
      size: 90,
    }),
    columnHelper.accessor('description', {
      header: 'Description',
      cell: info => {
        const row = info.row.original
        const isHeader = row.isGroupHeader
        return (
          <span className={isHeader ? 'font-semibold text-gray-900' : 'text-gray-700'}>
            {info.getValue()}
          </span>
        )
      },
    }),
    ...years.map(y =>
      columnHelper.accessor(row => row.values[y.key], {
        id: y.key,
        header: y.short,
        cell: info => {
          const v = info.getValue()
          return v !== null ? (
            <span className="text-right tabular-nums">{formatDollar(v)}</span>
          ) : (
            <span className="text-gray-300">—</span>
          )
        },
        size: 110,
      })
    ),
    columnHelper.accessor('pctChange', {
      header: 'Change',
      cell: info => <DeltaBadge value={info.getValue()} size="sm" />,
      size: 80,
    }),
  ]

  const table = useReactTable({
    data: items,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  })

  if (!items.length) {
    return (
      <div className="text-center py-12 text-gray-400 text-sm">
        No line items found
      </div>
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm border-collapse">
        <thead>
          {table.getHeaderGroups().map(hg => (
            <tr key={hg.id} className="border-b border-gray-200 bg-gray-50">
              {hg.headers.map(header => (
                <th
                  key={header.id}
                  className={`px-3 py-2 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide whitespace-nowrap ${
                    header.column.getCanSort() ? 'cursor-pointer select-none hover:text-gray-700' : ''
                  }`}
                  style={{ width: header.getSize() }}
                  onClick={header.column.getToggleSortingHandler()}
                >
                  <div className="flex items-center gap-1">
                    {flexRender(header.column.columnDef.header, header.getContext())}
                    {{
                      asc: ' ↑',
                      desc: ' ↓',
                    }[header.column.getIsSorted() as string] ?? ''}
                  </div>
                </th>
              ))}
            </tr>
          ))}
        </thead>
        <tbody>
          {table.getRowModel().rows.map(row => {
            const item = row.original
            const isHeader = item.isGroupHeader
            return (
              <tr
                key={row.id}
                onClick={() => {
                  if (isHeader && item.budgetCode) {
                    navigate(`/category/${encodeURIComponent(item.budgetCode)}`)
                  } else if (!isHeader) {
                    navigate(`/item/${encodeURIComponent(item.id)}`)
                  }
                }}
                className={`border-b border-gray-100 transition-colors cursor-pointer ${
                  isHeader
                    ? 'bg-gray-50 font-semibold hover:bg-blue-50'
                    : 'hover:bg-blue-50'
                }`}
              >
                {row.getVisibleCells().map(cell => (
                  <td key={cell.id} className="px-3 py-2 whitespace-nowrap">
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </td>
                ))}
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

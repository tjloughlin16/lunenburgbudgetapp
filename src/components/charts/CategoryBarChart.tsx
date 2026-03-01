import {
  BarChart,
  Bar,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'
import type { CategoryBarDatum } from '../../data/transforms'
import { formatDollar, formatDollarShort } from '../../data/transforms'
import { CATEGORY_COLORS } from '../../data/types'
import type { CategoryCode } from '../../data/types'

interface Props {
  data: CategoryBarDatum[]
}

function CustomTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean
  payload?: { name: string; value: number; fill: string }[]
  label?: string
}) {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-lg p-3 text-sm">
      <p className="font-semibold text-gray-900 mb-2">{label}</p>
      {payload.map(p => (
        <div key={p.name} className="flex items-center gap-2 justify-between">
          <div className="flex items-center gap-1.5">
            <div className="w-2.5 h-2.5 rounded-sm" style={{ backgroundColor: p.fill }} />
            <span className="text-gray-600">{p.name}</span>
          </div>
          <span className="font-medium ml-4">{formatDollar(p.value)}</span>
        </div>
      ))}
    </div>
  )
}

export function CategoryBarChart({ data }: Props) {
  if (!data.length) {
    return (
      <div className="flex items-center justify-center h-48 text-gray-400">
        No data available
      </div>
    )
  }

  return (
    <ResponsiveContainer width="100%" height={320}>
      <BarChart data={data} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
        <XAxis
          dataKey="category"
          tick={{ fontSize: 11 }}
          tickFormatter={v => (v as string).replace('Administration', 'Admin').replace('Instructional', 'Instr.')}
        />
        <YAxis
          tickFormatter={v => formatDollarShort(v as number)}
          tick={{ fontSize: 11 }}
          width={60}
        />
        <Tooltip content={<CustomTooltip />} />
        <Legend iconSize={10} wrapperStyle={{ fontSize: 12 }} />
        <Bar dataKey="compare" name={data[0]?.compareLabel ?? 'Prior Year'} fill="#9ca3af" radius={[2, 2, 0, 0]} />
        <Bar
          dataKey="primary"
          name={data[0]?.primaryLabel ?? 'Current Year'}
          fill="#3b82f6"
          radius={[2, 2, 0, 0]}
          label={false}
        />
      </BarChart>
    </ResponsiveContainer>
  )
}

export function CategoryColoredBarChart({ data }: Props) {
  if (!data.length) return null
  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart data={data} layout="vertical" margin={{ top: 0, right: 20, left: 10, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" horizontal={false} />
        <XAxis
          type="number"
          tickFormatter={v => formatDollarShort(v as number)}
          tick={{ fontSize: 11 }}
        />
        <YAxis
          type="category"
          dataKey="category"
          tick={{ fontSize: 11 }}
          width={100}
        />
        <Tooltip content={<CustomTooltip />} />
        <Bar dataKey="primary" name={data[0]?.primaryLabel ?? 'Current Year'} radius={[0, 2, 2, 0]}>
          {data.map(entry => (
            <Cell
              key={entry.category}
              fill={CATEGORY_COLORS[entry.categoryCode as CategoryCode] ?? '#6b7280'}
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}

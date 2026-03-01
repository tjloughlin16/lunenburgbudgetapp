import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
} from 'recharts'
import type { TrendDatum } from '../../data/transforms'
import { formatDollar, formatDollarShort } from '../../data/transforms'

interface Props {
  data: TrendDatum[]
  color?: string
  title?: string
  height?: number
}

function CustomTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean
  payload?: { value: number; payload: TrendDatum }[]
  label?: string
}) {
  if (!active || !payload?.length) return null
  const d = payload[0]
  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-lg p-3 text-sm">
      <p className="font-semibold text-gray-900 mb-1">{label}</p>
      <p className="text-gray-700">{formatDollar(d.value)}</p>
      {d.payload?.isProjected && (
        <p className="text-xs text-amber-500 mt-1">Proposed (not actual)</p>
      )}
    </div>
  )
}

export function YearTrendLine({ data, color = '#3b82f6', title, height = 260 }: Props) {
  if (!data.length) return null

  // Split into actual vs projected
  const actuals = data.filter(d => !d.isProjected)
  const projected = data.filter(d => d.isProjected)

  // For the dashed projected segment, include the last actual point as the start
  const lastActual = actuals[actuals.length - 1]
  const projectedWithBridge = lastActual
    ? [lastActual, ...projected]
    : projected

  // Reference line at the boundary between actuals and projected
  const refYear = [...data].reverse().find(d => !d.isProjected)?.year

  return (
    <div>
      {title && <p className="text-sm font-medium text-gray-700 mb-2">{title}</p>}
      <ResponsiveContainer width="100%" height={height}>
        <LineChart data={data} margin={{ top: 10, right: 20, left: 10, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis dataKey="year" tick={{ fontSize: 12 }} />
          <YAxis
            tickFormatter={v => formatDollarShort(v as number)}
            tick={{ fontSize: 11 }}
            width={65}
          />
          <Tooltip content={<CustomTooltip />} />
          {refYear && (
            <ReferenceLine
              x={refYear}
              stroke="#f59e0b"
              strokeDasharray="4 4"
              label={{ value: 'Budget', position: 'top', fontSize: 10, fill: '#f59e0b' }}
            />
          )}
          {/* Solid line for actuals */}
          <Line
            data={actuals}
            type="monotone"
            dataKey="value"
            stroke={color}
            strokeWidth={2.5}
            dot={{ r: 5, fill: color, strokeWidth: 0 }}
            activeDot={{ r: 7 }}
            name="Actuals"
            legendType="line"
          />
          {/* Dashed line for projected */}
          {projectedWithBridge.length > 1 && (
            <Line
              data={projectedWithBridge}
              type="monotone"
              dataKey="value"
              stroke={color}
              strokeWidth={2.5}
              strokeDasharray="6 4"
              dot={{ r: 5, fill: '#fff', stroke: color, strokeWidth: 2.5 }}
              activeDot={{ r: 7 }}
              name="Proposed"
              legendType="plainline"
            />
          )}
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

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

// Merge into a single array with two value keys so both Line components share
// the same x-axis positions. Passing separate `data` arrays to individual
// <Line>s maps by array index, not by year label, which puts the projected
// segment at the wrong positions.
interface ChartPoint {
  year: string
  isProjected: boolean
  actualValue: number | null
  projectedValue: number | null
}

function buildChartPoints(data: TrendDatum[]): ChartPoint[] {
  const lastActualIdx = [...data].reverse().findIndex(d => !d.isProjected)
  const bridgeIdx = lastActualIdx >= 0 ? data.length - 1 - lastActualIdx : -1

  return data.map((d, i) => ({
    year: d.year,
    isProjected: d.isProjected,
    // Solid line: all actual years
    actualValue: !d.isProjected ? d.value : null,
    // Dashed line: the bridge (last actual) + all projected years
    projectedValue: (d.isProjected || i === bridgeIdx) ? d.value : null,
  }))
}

function CustomTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean
  payload?: { value: number; payload: ChartPoint }[]
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

  const hasProjected = data.some(d => d.isProjected)
  const chartPoints = buildChartPoints(data)

  // Reference line at the last actual year
  const refYear = [...data].reverse().find(d => !d.isProjected)?.year

  return (
    <div>
      {title && <p className="text-sm font-medium text-gray-700 mb-2">{title}</p>}
      {hasProjected && (
        <div className="flex items-center gap-5 mb-3 text-xs text-gray-400">
          <div className="flex items-center gap-1.5">
            <svg width="24" height="10">
              <line x1="0" y1="5" x2="24" y2="5" stroke={color} strokeWidth="2.5" strokeLinecap="round" />
            </svg>
            <span>Actual</span>
          </div>
          <div className="flex items-center gap-1.5">
            <svg width="24" height="10">
              <line x1="0" y1="5" x2="24" y2="5" stroke={color} strokeWidth="2.5" strokeDasharray="6 4" strokeLinecap="round" />
            </svg>
            <span>Proposed</span>
          </div>
        </div>
      )}
      <ResponsiveContainer width="100%" height={height}>
        <LineChart data={chartPoints} margin={{ top: 10, right: 20, left: 10, bottom: 5 }}>
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
            type="monotone"
            dataKey="actualValue"
            stroke={color}
            strokeWidth={2.5}
            dot={{ r: 5, fill: color, strokeWidth: 0 }}
            activeDot={{ r: 7 }}
            connectNulls={false}
            name="Actual"
            legendType="none"
          />
          {/* Dashed line for proposed — shares the same x-axis so positions are correct */}
          {hasProjected && (
            <Line
              type="monotone"
              dataKey="projectedValue"
              stroke={color}
              strokeWidth={2.5}
              strokeDasharray="6 4"
              dot={{ r: 5, fill: '#fff', stroke: color, strokeWidth: 2.5 }}
              activeDot={{ r: 7 }}
              connectNulls={false}
              name="Proposed"
              legendType="none"
            />
          )}
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'

export type ShareDatum = {
  year: string
  share: number       // 0–100 (percentage points)
  isProjected: boolean
}

interface ChartPoint {
  year: string
  isProjected: boolean
  actualShare: number | null
  projectedShare: number | null
}

function buildChartPoints(data: ShareDatum[]): ChartPoint[] {
  const lastActualIdx = [...data].reverse().findIndex(d => !d.isProjected)
  const bridgeIdx = lastActualIdx >= 0 ? data.length - 1 - lastActualIdx : -1

  return data.map((d, i) => ({
    year: d.year,
    isProjected: d.isProjected,
    actualShare:    !d.isProjected ? d.share : null,
    projectedShare: (d.isProjected || i === bridgeIdx) ? d.share : null,
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
      <p className="text-gray-700">{d.value.toFixed(2)}% of total budget</p>
      {d.payload?.isProjected && (
        <p className="text-xs text-amber-500 mt-1">Proposed (not actual)</p>
      )}
    </div>
  )
}

interface Props {
  data: ShareDatum[]
  color?: string
  height?: number
}

export function BudgetShareChart({ data, color = '#7c3aed', height = 220 }: Props) {
  if (!data.length) return null

  const hasProjected  = data.some(d => d.isProjected)
  const chartPoints   = buildChartPoints(data)

  // Y-axis domain: pad a bit above/below the actual range
  const values = data.map(d => d.share)
  const minVal = Math.max(0, Math.min(...values) - 0.3)
  const maxVal = Math.max(...values) + 0.3

  return (
    <div>
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
            tickFormatter={v => `${(v as number).toFixed(1)}%`}
            domain={[minVal, maxVal]}
            tick={{ fontSize: 11 }}
            width={50}
          />
          <Tooltip content={<CustomTooltip />} />
          <Line
            type="monotone"
            dataKey="actualShare"
            stroke={color}
            strokeWidth={2.5}
            dot={{ r: 5, fill: color, strokeWidth: 0 }}
            activeDot={{ r: 7 }}
            connectNulls={false}
            legendType="none"
          />
          {hasProjected && (
            <Line
              type="monotone"
              dataKey="projectedShare"
              stroke={color}
              strokeWidth={2.5}
              strokeDasharray="6 4"
              dot={{ r: 5, fill: '#fff', stroke: color, strokeWidth: 2.5 }}
              activeDot={{ r: 7 }}
              connectNulls={false}
              legendType="none"
            />
          )}
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

import { useNavigate } from 'react-router-dom'
import {
  Treemap,
  ResponsiveContainer,
  Tooltip,
} from 'recharts'
import type { TreemapCategory, TreemapLeaf } from '../../data/transforms'
import { formatDollar, formatDollarShort, formatPct } from '../../data/transforms'

interface Props {
  data: TreemapCategory[]
}

interface ContentProps {
  x?: number
  y?: number
  width?: number
  height?: number
  name?: string
  color?: string
  size?: number
  code?: string
  root?: boolean
}

function CustomContent(navigate: (path: string) => void) {
  return function Content(props: ContentProps) {
    const { x = 0, y = 0, width = 0, height = 0, name, color, size, code } = props

    if (width < 8 || height < 8) return null

    const handleClick = () => {
      if (code) navigate(`/category/${encodeURIComponent(code)}`)
    }

    // Fit as many characters as the width allows (~7.5 px per char)
    const maxChars = Math.max(3, Math.floor(width / 7.5))
    const displayName = name
      ? name.length > maxChars ? name.slice(0, maxChars - 1) + '…' : name
      : ''

    // Show name whenever there is meaningful room (even heavily truncated)
    const showName = height > 22 && width > 36
    // Show value below the name only in larger blocks; or alone in blocks too narrow for name
    const showBoth = showName && width > 90 && height > 50
    const showValueAlone = !showName && width > 45 && height > 22

    const nameFontSize = width > 130 ? 13 : width > 80 ? 11 : 9

    return (
      <g>
        <rect
          x={x + 1}
          y={y + 1}
          width={width - 2}
          height={height - 2}
          style={{
            fill: color ?? '#6b7280',
            stroke: '#fff',
            strokeWidth: 2,
            cursor: code ? 'pointer' : 'default',
          }}
          onClick={handleClick}
        />
        {showName && (
          <text
            x={x + width / 2}
            y={y + height / 2 - (showBoth ? 9 : 0)}
            textAnchor="middle"
            dominantBaseline="middle"
            style={{
              fill: '#fff',
              fontSize: nameFontSize,
              fontWeight: 600,
              pointerEvents: 'none',
            }}
          >
            {displayName}
          </text>
        )}
        {(showBoth || showValueAlone) && size !== undefined && (
          <text
            x={x + width / 2}
            y={y + height / 2 + (showBoth ? 9 : 0)}
            textAnchor="middle"
            dominantBaseline="middle"
            style={{
              fill: showBoth ? 'rgba(255,255,255,0.85)' : '#fff',
              fontSize: 10,
              pointerEvents: 'none',
            }}
          >
            {formatDollarShort(size)}
          </text>
        )}
      </g>
    )
  }
}

function CustomTooltip({
  active,
  payload,
}: {
  active?: boolean
  payload?: { payload: TreemapLeaf }[]
}) {
  if (!active || !payload?.length) return null
  const d = payload[0].payload
  if (!d?.name) return null

  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-lg p-3 text-sm max-w-xs">
      <p className="font-semibold text-gray-900 mb-1">{d.name}</p>
      <div className="space-y-1">
        <div className="flex justify-between gap-4">
          <span className="text-gray-500">{d.compareLabel}</span>
          <span className="font-medium">{formatDollar(d.compareValue ?? 0)}</span>
        </div>
        <div className="flex justify-between gap-4">
          <span className="text-gray-500">{d.primaryLabel}</span>
          <span className="font-medium">{formatDollar(d.size ?? 0)}</span>
        </div>
        {d.pctChange !== null && (
          <div className="flex justify-between gap-4 pt-1 border-t border-gray-100">
            <span className="text-gray-500">Change</span>
            <span className={d.pctChange >= 0 ? 'text-red-600 font-medium' : 'text-green-600 font-medium'}>
              {formatPct(d.pctChange)}
            </span>
          </div>
        )}
      </div>
      <p className="text-xs text-blue-500 mt-2">Click to drill down</p>
    </div>
  )
}

export function BudgetTreemap({ data }: Props) {
  const navigate = useNavigate()

  // Flatten for Recharts: it expects a flat array with 'name' and 'size'
  const flat = data.flatMap(cat =>
    cat.children.map(leaf => ({
      ...leaf,
      color: leaf.color ?? cat.color,
    }))
  )

  if (flat.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-400">
        No data available for selected filters
      </div>
    )
  }

  return (
    <ResponsiveContainer width="100%" height={420}>
      <Treemap
        data={flat}
        dataKey="size"
        aspectRatio={4 / 3}
        content={CustomContent(navigate) as never}
      >
        <Tooltip content={<CustomTooltip />} />
      </Treemap>
    </ResponsiveContainer>
  )
}

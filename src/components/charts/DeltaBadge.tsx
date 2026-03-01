import { formatPct } from '../../data/transforms'

interface Props {
  value: number | null
  size?: 'sm' | 'md'
}

export function DeltaBadge({ value, size = 'md' }: Props) {
  if (value === null) {
    return <span className="text-gray-400 text-xs">N/A</span>
  }

  const isPositive = value >= 0
  const textSize = size === 'sm' ? 'text-xs' : 'text-sm'

  return (
    <span
      className={`inline-flex items-center gap-0.5 font-medium ${textSize} ${
        isPositive ? 'text-red-600' : 'text-green-600'
      }`}
    >
      {isPositive ? '▲' : '▼'}
      {formatPct(value)}
    </span>
  )
}

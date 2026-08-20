import { MODEL, usd, usdShort } from '../model/engine'

const T = MODEL.taxBase

/** Commercial growth, as a dial.
 *
 *  Sits with the fees and the cut ladders because it is the same kind of control: one
 *  number, dragged, with the argument in a panel underneath. The only thing it has to get
 *  right on its own face is that a dollar of new growth is not a dollar to the schools. */
export function GrowthDial({ value, setValue, gap, share, max }: {
  value: number; setValue: (n: number) => void
  gap: number
  /** Fraction of new-growth revenue that reaches the school gap. */
  share: number
  max: number
}) {
  const annual = (value * T.rate) / 1000
  const extra = annual - T.currentNewGrowthRevenue
  const toSchools = extra * share
  const mix = T.archetypes.find(a => a.id === 'mix')?.value ?? 3_005_000
  const closesAt = T.currentNewGrowthValue + ((gap / share) * 1000) / T.rate
  const moved = value !== T.currentNewGrowthValue

  return (
    <div className="card p-4">
      <div className="flex items-baseline justify-between gap-3 mb-1">
        <h3 className="text-[13px] font-bold">Commercial growth</h3>
        <span className="text-[10px] font-bold uppercase tracking-widest shrink-0"
          style={{ color: 'var(--series-cost)' }}>New revenue</span>
      </div>

      <div className="flex items-baseline justify-between gap-3 mb-1">
        <span className="text-[11px]" style={{ color: 'var(--text-muted)' }}>
          new commercial value added per year
          <strong> · today {usdShort(T.currentNewGrowthValue)}</strong>
        </span>
        <span className="flex items-baseline gap-1.5 shrink-0">
          <span className="text-sm font-bold tnum">{usdShort(value)}</span>
          {moved && (
            <button onClick={() => setValue(T.currentNewGrowthValue)}
              className="text-[10px] font-semibold underline"
              style={{ color: 'var(--text-secondary)' }}>reset</button>
          )}
        </span>
      </div>

      <input type="range" min={0} max={max} step={1_000_000} value={Math.min(value, max)}
        aria-label="New commercial value added per year"
        onChange={e => setValue(Number(e.target.value))} className="w-full" />

      <div className="relative h-7">
        <button onClick={() => setValue(T.currentNewGrowthValue)}
          className="absolute top-0 text-[10px] leading-tight text-center hover:opacity-70"
          style={{ left: `${(T.currentNewGrowthValue / max) * 100}%`,
                   transform: 'translateX(-50%)', color: 'var(--text-muted)' }}>
          <span className="block w-px h-1.5 mb-0.5 mx-auto"
            style={{ background: 'var(--axis)' }} aria-hidden="true" />
          today
        </button>
        {closesAt <= max && (
          <button onClick={() => setValue(Math.round(closesAt / 1e6) * 1e6)}
            className="absolute top-0 text-[10px] leading-tight text-center hover:opacity-70"
            style={{ left: `${(closesAt / max) * 100}%`,
                     transform: 'translateX(-50%)', color: 'var(--status-good)' }}>
            <span className="block w-px h-1.5 mb-0.5 mx-auto"
              style={{ background: 'var(--status-good)' }} aria-hidden="true" />
            <span className="whitespace-nowrap font-semibold">closes it</span>
          </button>
        )}
      </div>

      <div className="mt-1 pt-2 border-t text-[11px] leading-snug"
        style={{ borderColor: 'var(--grid)' }}>
        <span style={{ color: 'var(--text-muted)' }}>
          {(value / mix).toFixed(0)} typical developments a year, every year —{' '}
          {(value / T.avgCommercialValue).toFixed(0)} businesses.
        </span>
        <span className="block" style={{ color: 'var(--text-muted)' }}>
          Worth {usd(Math.max(0, extra))} to the town, of which{' '}
          <strong>{(share * 100).toFixed(0)}%</strong> reaches the schools.
        </span>
      </div>

      <p className="text-lg font-bold tnum mt-2"
        style={{ color: toSchools > 0 ? 'var(--status-good)' : 'var(--text-muted)' }}>
        {usd(Math.max(0, toSchools))}
        <span className="text-[10px] font-normal ml-1.5" style={{ color: 'var(--text-muted)' }}>
          {toSchools > 0 ? 'against this gap, above today’s growth' : ''}
        </span>
      </p>
    </div>
  )
}

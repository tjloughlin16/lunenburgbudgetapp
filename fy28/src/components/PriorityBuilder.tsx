import { MODEL } from '../model/engine'

export function PriorityBuilder({ order, setOrder, preset, setPreset }: {
  order: string[]
  setOrder: (o: string[]) => void
  preset: string | null
  setPreset: (p: string | null) => void
}) {
  const move = (i: number, dir: -1 | 1) => {
    const j = i + dir
    if (j < 0 || j >= order.length) return
    const next = [...order]
    ;[next[i], next[j]] = [next[j], next[i]]
    setOrder(next)
    setPreset(null)
  }

  return (
    <div>
      <div className="flex flex-wrap gap-2 mb-5">
        {Object.entries(MODEL.presets).map(([key, p]) => (
          <button key={key}
            onClick={() => { setOrder(p.order); setPreset(key) }}
            className="px-3 py-1.5 rounded-lg text-xs font-semibold border transition-colors"
            style={{
              borderColor: preset === key ? 'var(--series-cost)' : 'var(--grid)',
              background: preset === key ? 'var(--series-cost)' : 'var(--surface-1)',
              color: preset === key ? '#fff' : 'var(--text-secondary)',
            }}>
            {p.name}
          </button>
        ))}
      </div>

      {preset && (
        <p className="text-[13px] leading-relaxed mb-5 pl-3 border-l-2"
          style={{ color: 'var(--text-secondary)', borderColor: 'var(--series-cost)' }}>
          {MODEL.presets[preset].why}
        </p>
      )}

      <ol className="space-y-1.5">
        {order.map((cat, i) => (
          <li key={cat}
            className="card flex items-center gap-3 px-3 py-2.5">
            <span className="tnum text-xs font-bold w-6 text-center shrink-0"
              style={{ color: 'var(--text-muted)' }}>{i + 1}</span>
            <span className="flex-1 text-sm font-medium">
              {MODEL.categories[cat]?.label ?? cat}
            </span>
            <span className="text-[10px] font-semibold uppercase tracking-wider shrink-0 hidden sm:block"
              style={{ color: 'var(--text-muted)' }}>
              {i === 0 ? 'protected longest' : i === order.length - 1 ? 'cut first' : ''}
            </span>
            <span className="flex gap-1 shrink-0">
              <button onClick={() => move(i, -1)} disabled={i === 0}
                aria-label={`Move ${MODEL.categories[cat]?.label} up`}
                className="w-7 h-7 rounded-md border text-xs disabled:opacity-25"
                style={{ borderColor: 'var(--grid)' }}>▲</button>
              <button onClick={() => move(i, 1)} disabled={i === order.length - 1}
                aria-label={`Move ${MODEL.categories[cat]?.label} down`}
                className="w-7 h-7 rounded-md border text-xs disabled:opacity-25"
                style={{ borderColor: 'var(--grid)' }}>▼</button>
            </span>
          </li>
        ))}
      </ol>
      <p className="text-xs mt-4" style={{ color: 'var(--text-muted)' }}>
        Top of the list is defended longest. Bottom is cut first. Reorder to see how the
        outcome changes — or pick a preset above to start from someone else's priorities.
      </p>
    </div>
  )
}

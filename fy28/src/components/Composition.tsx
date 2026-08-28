import { MODEL, usd } from '../model/engine'

// Ordinal ramp on one hue (blue), lightest step no lighter than 250 on light surface.
const RAMP = ['#0d366b', '#184f95', '#256abf', '#2a78d6', '#5598e7', '#86b6ef']

const LABELS: Record<string, { label: string; note: string }> = {
  salaries: { label: 'Salaries & wages', note: 'Set by collective bargaining agreements' },
  health: { label: 'Health insurance', note: 'Rate set by the town’s insurance trust' },
  transport: { label: 'Transportation', note: 'General education routes; special education routes are counted below' },
  sped: { label: 'Special education, in district', note: 'Staffing set by each child’s plan, not by a vote' },
  sped_tuition: { label: 'Out-of-district tuition', note: 'Court- and IEP-mandated placements' },
  utilities: { label: 'Heat, power & water', note: 'Market rates' },
  other: { label: 'Everything else', note: 'Supplies, materials, contracts, equipment' },
}

export function Composition() {
  const base = MODEL.expenseBase
  const total = Object.values(base).reduce((a, b) => a + b, 0)
  const rows = Object.entries(base).sort((a, b) => b[1] - a[1])

  return (
    <div className="card p-5">
      <ul className="space-y-3.5">
        {rows.map(([k, v], i) => {
          const pct = (v / total) * 100
          return (
            <li key={k}>
              <div className="flex items-baseline justify-between gap-3 mb-1">
                <span className="text-sm font-medium">{LABELS[k]?.label ?? k}</span>
                <span className="text-sm font-bold tnum shrink-0">
                  {usd(v)} <span className="font-normal"
                    style={{ color: 'var(--text-muted)' }}>{pct.toFixed(1)}%</span>
                </span>
              </div>
              <div className="h-2.5 rounded-full overflow-hidden"
                style={{ background: 'var(--surface-3)' }}>
                <div className="h-full rounded-full"
                  style={{ width: `${pct}%`, background: RAMP[i] }} />
              </div>
              <p className="text-[11px] mt-1" style={{ color: 'var(--text-muted)' }}>
                {LABELS[k]?.note}
              </p>
            </li>
          )
        })}
      </ul>
    </div>
  )
}

/** The "just cut the frills" reality check. */
export function FrillsCheck({ gap }: { gap: number }) {
  const f = MODEL.facts
  const items = [
    { label: 'Every remaining sport, coach, trainer and athletic fee', v: f.athleticsRemaining },
    { label: 'All band & music supplies, equipment and repairs', v: f.musicSupplies },
    { label: 'All art supplies, four schools', v: f.artSupplies },
    { label: 'Every club and after-school advisor', v: f.clubs },
  ]
  const sum = items.reduce((a, b) => a + b.v, 0)
  return (
    <div className="card p-5">
      <ul className="space-y-2.5">
        {items.map(it => (
          <li key={it.label} className="flex items-baseline justify-between gap-4 text-sm">
            <span style={{ color: 'var(--text-secondary)' }}>{it.label}</span>
            <span className="font-bold tnum shrink-0">{usd(it.v)}</span>
          </li>
        ))}
        <li className="flex items-baseline justify-between gap-4 text-sm pt-2.5 border-t font-bold"
          style={{ borderColor: 'var(--grid)' }}>
          <span>Everything above, eliminated</span>
          <span className="tnum shrink-0">{usd(sum)}</span>
        </li>
        <li className="flex items-baseline justify-between gap-4 text-sm">
          <span style={{ color: 'var(--status-critical)' }}>Projected FY28 gap</span>
          <span className="font-bold tnum shrink-0" style={{ color: 'var(--status-critical)' }}>
            {usd(gap)}
          </span>
        </li>
        <li className="flex items-baseline justify-between gap-4 text-sm pt-2.5 border-t font-bold"
          style={{ borderColor: 'var(--grid)' }}>
          <span>Still to find</span>
          <span className="tnum shrink-0" style={{ color: 'var(--status-critical)' }}>
            {usd(Math.max(0, gap - sum))}
          </span>
        </li>
      </ul>
    </div>
  )
}

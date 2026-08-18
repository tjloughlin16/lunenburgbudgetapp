import { MODEL, usd } from '../model/engine'

export function Recommendation({ gap, onApply }: {
  gap: number; onApply: () => void
}) {
  const pkg = MODEL.recommendation.package
  const found = pkg.reduce((s, p) => s + p.value, 0)
  const left = Math.max(0, gap - found)
  const teachers = left / 102_510

  return (
    <div>
      <div className="card p-5 mb-5">
        <div className="grid gap-4 sm:grid-cols-3 mb-4">
          <Fig label="Found without cutting" value={usd(found)} tone="good" />
          <Fig label="Share of the FY28 gap" value={`${((found / gap) * 100).toFixed(0)}%`} />
          <Fig label="Still to find" value={usd(left)} tone="critical"
            sub={`about ${teachers.toFixed(1)} teaching positions, at the $102,510 the `
              + `district costed a Primary School teacher at`} />
        </div>
        <div className="h-3 rounded-full overflow-hidden flex gap-0.5"
          style={{ background: 'var(--surface-3)' }}>
          <div style={{ width: `${(found / gap) * 100}%`, background: 'var(--status-good)' }} />
          <div style={{ width: `${(left / gap) * 100}%`, background: 'var(--status-critical)' }} />
        </div>
      </div>

      <ol className="space-y-3 mb-5">
        {pkg.map((p, i) => (
          <li key={p.id} className="card p-5">
            <div className="flex flex-wrap items-baseline justify-between gap-3 mb-2">
              <h3 className="text-[15px] font-bold">
                <span className="tnum mr-2" style={{ color: 'var(--text-muted)' }}>{i + 1}.</span>
                {p.name}
              </h3>
              <span className="text-lg font-bold tnum shrink-0"
                style={{ color: p.value > 0 ? 'var(--status-good)' : 'var(--text-muted)' }}>
                {p.value > 0 ? usd(p.value) : 'FY30, not FY28'}
              </span>
            </div>
            <p className="text-[13px] leading-relaxed mb-2"
              style={{ color: 'var(--text-secondary)' }}>{p.why}</p>
            <p className="text-[11px]" style={{ color: 'var(--text-muted)' }}>
              <strong>What it takes: </strong>{p.difficulty}
            </p>
          </li>
        ))}
      </ol>

      <div className="card p-5" style={{ borderColor: 'var(--status-critical)' }}>
        <h3 className="text-sm font-bold mb-2">The part nobody wants to say</h3>
        <p className="text-[14px] leading-relaxed mb-4">{MODEL.recommendation.closing}</p>
        <h3 className="text-sm font-bold mb-2">And on what to protect</h3>
        <p className="text-[14px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
          {MODEL.recommendation.priorityWhy}
        </p>
        <button onClick={onApply}
          className="mt-4 px-3.5 py-2 rounded-lg text-xs font-semibold"
          style={{ background: 'var(--series-cost)', color: '#fff' }}>
          Load this ranking into the tool
        </button>
      </div>

      <p className="text-xs leading-relaxed mt-5" style={{ color: 'var(--text-muted)' }}>
        This is our analysis, not the district&rsquo;s and not the town&rsquo;s. Nobody has
        proposed it. The fee yields assume a 5&ndash;8% participation drop per $100 charged
        above what is <em>already</em> charged, and 12&ndash;15% of students on hardship
        waivers &mdash; assumptions, not Lunenburg measurements. These package figures are
        fixed at those rates; the workbench above lets you test different ones, but it does
        not rewrite this list. Bus rider counts and club participation are placeholders the
        district does not publish, so those two lines are the softest here.
      </p>
    </div>
  )
}

function Fig({ label, value, sub, tone }: {
  label: string; value: string; sub?: string; tone?: 'good' | 'critical'
}) {
  const color = tone === 'good' ? 'var(--status-good)'
    : tone === 'critical' ? 'var(--status-critical)' : 'var(--text-primary)'
  return (
    <div>
      <p className="text-[11px] font-semibold uppercase tracking-widest mb-1"
        style={{ color: 'var(--text-muted)' }}>{label}</p>
      <p className="text-2xl font-bold tnum leading-none" style={{ color }}>{value}</p>
      {sub && <p className="text-[11px] mt-1" style={{ color: 'var(--text-secondary)' }}>{sub}</p>}
    </div>
  )
}

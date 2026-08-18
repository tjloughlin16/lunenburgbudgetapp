import { MODEL, usd } from '../model/engine'

const STATUS: Record<string, { label: string; tone: string }> = {
  failed: { label: 'Override failed', tone: 'var(--status-critical)' },
  needed: { label: 'Override needed', tone: 'var(--status-serious)' },
  unlikely: { label: 'Override unlikely', tone: 'var(--status-serious)' },
  none: { label: 'No override sought', tone: 'var(--text-muted)' },
  unknown: { label: 'Not stated', tone: 'var(--text-muted)' },
}

/** Budget growth across local districts. One measure, one axis, subject highlighted. */
export function PeerGrowth() {
  const peers = [...MODEL.peers].sort((a, b) => b.changePct - a.changePct)
  const max = Math.max(...peers.map(p => p.changePct))
  return (
    <div className="card p-5">
      <ul className="space-y-3">
        {peers.map(p => (
          <li key={p.id}>
            <div className="flex items-baseline justify-between gap-3 mb-1">
              <span className="text-sm"
                style={{ fontWeight: p.subject ? 700 : 500 }}>
                {p.name}{p.subject && ' — us'}
              </span>
              <span className="text-sm font-bold tnum shrink-0">
                +{p.changePct.toFixed(2)}%
              </span>
            </div>
            <div className="h-2.5 rounded-full overflow-hidden"
              style={{ background: 'var(--surface-3)' }}>
              <div className="h-full rounded-full"
                style={{
                  width: `${(p.changePct / max) * 100}%`,
                  background: p.subject ? 'var(--status-critical)' : 'var(--series-cost)',
                }} />
            </div>
          </li>
        ))}
      </ul>
      <p className="text-[11px] mt-4" style={{ color: 'var(--text-muted)' }}>
        Operating budget growth, FY26 to FY27, as each district published it. Health
        insurance rose 8&ndash;14% and Chapter 70 aid rose 1.5&ndash;2% across all of them.
      </p>
    </div>
  )
}

export function PeerTable() {
  return (
    <div className="space-y-3">
      {MODEL.peers.map(p => {
        const st = STATUS[p.overrideStatus]
        return (
          <div key={p.id} className="card p-5"
            style={p.subject ? { borderColor: 'var(--status-critical)' } : undefined}>
            <div className="flex flex-wrap items-baseline justify-between gap-2 mb-2">
              <h3 className="text-base font-bold">
                {p.name}{p.subject && (
                  <span className="ml-2 text-[10px] font-bold uppercase tracking-widest align-middle"
                    style={{ color: 'var(--status-critical)' }}>Our district</span>
                )}
              </h3>
              <span className="text-[11px] font-semibold" style={{ color: st.tone }}>
                {st.label}
              </span>
            </div>

            <div className="flex flex-wrap gap-x-6 gap-y-1 text-xs mb-3 tnum"
              style={{ color: 'var(--text-secondary)' }}>
              <span>{p.enrollment.toLocaleString()} students</span>
              <span>{usd(p.budget)} budget</span>
              <span>+{p.changePct.toFixed(2)}% over FY26</span>
              {p.healthPct !== null && <span>health insurance +{p.healthPct}%</span>}
              {p.chapter70Pct !== null && <span>Chapter 70 +{p.chapter70Pct}%</span>}
            </div>

            <p className="text-[13px] leading-relaxed mb-3"
              style={{ color: 'var(--text-secondary)' }}>{p.note}</p>

            <div className="grid gap-3 sm:grid-cols-2">
              {p.protected.length > 0 && (
                <div>
                  <p className="text-[10px] font-bold uppercase tracking-widest mb-1.5"
                    style={{ color: 'var(--status-good)' }}>
                    <span aria-hidden="true">✓ </span>Protected
                  </p>
                  <ul className="text-xs space-y-0.5" style={{ color: 'var(--text-secondary)' }}>
                    {p.protected.map(x => <li key={x}>{x}</li>)}
                  </ul>
                </div>
              )}
              {p.sacrificed.length > 0 && (
                <div>
                  <p className="text-[10px] font-bold uppercase tracking-widest mb-1.5"
                    style={{ color: 'var(--status-critical)' }}>
                    <span aria-hidden="true">✕ </span>Given up
                  </p>
                  <ul className="text-xs space-y-0.5" style={{ color: 'var(--text-secondary)' }}>
                    {p.sacrificed.map(x => <li key={x}>{x}</li>)}
                  </ul>
                </div>
              )}
            </div>

            <p className="text-[10px] mt-3 pt-2 border-t"
              style={{ color: 'var(--text-muted)', borderColor: 'var(--grid)' }}>
              Source: {p.source}
            </p>
          </div>
        )
      })}
    </div>
  )
}

export function PeerLessons() {
  return (
    <div className="grid gap-3 md:grid-cols-2">
      {MODEL.peerLessons.map(l => (
        <div key={l.title} className="card p-4">
          <h3 className="text-sm font-bold mb-1.5">{l.title}</h3>
          <p className="text-[13px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
            {l.body}
          </p>
        </div>
      ))}
    </div>
  )
}

import { useState, type ReactNode } from 'react'

export function Section({ id, eyebrow, title, lede, children }: {
  id: string; eyebrow?: string; title: string; lede?: ReactNode; children: ReactNode
}) {
  return (
    <section id={id} className="scroll-mt-16 py-14 border-t"
      style={{ borderColor: 'var(--grid)' }}>
      <div className="mx-auto max-w-6xl px-5">
        {eyebrow && (
          <p className="text-xs font-semibold uppercase tracking-widest mb-2"
            style={{ color: 'var(--text-muted)' }}>{eyebrow}</p>
        )}
        <h2 className="text-2xl sm:text-3xl font-bold tracking-tight mb-3">{title}</h2>
        {lede && (
          <div className="max-w-3xl text-[15px] leading-relaxed mb-8"
            style={{ color: 'var(--text-secondary)' }}>{lede}</div>
        )}
        {children}
      </div>
    </section>
  )
}

export function Stat({ label, value, sub, tone }: {
  label: string; value: string; sub?: string; tone?: 'critical' | 'good' | 'neutral'
}) {
  const color = tone === 'critical' ? 'var(--status-critical)'
    : tone === 'good' ? 'var(--status-good)' : 'var(--text-primary)'
  return (
    <div className="card p-4">
      <p className="text-[11px] font-semibold uppercase tracking-widest mb-1.5"
        style={{ color: 'var(--text-muted)' }}>{label}</p>
      <p className="text-2xl font-bold tnum leading-none" style={{ color }}>{value}</p>
      {sub && <p className="text-xs mt-1.5" style={{ color: 'var(--text-secondary)' }}>{sub}</p>}
    </div>
  )
}

/** Status is never carried by color alone — every badge pairs a glyph with a word. */
export function StatusBadge({ kind }: { kind: 'kept' | 'cut' | 'mandated' }) {
  const map = {
    kept: { glyph: '✓', word: 'Kept', color: 'var(--status-good)' },
    cut: { glyph: '✕', word: 'Cut', color: 'var(--status-critical)' },
    mandated: { glyph: '⚖', word: 'Protected by law', color: 'var(--status-warning)' },
  }[kind]
  return (
    <span className="inline-flex items-center gap-1 text-[11px] font-semibold whitespace-nowrap"
      style={{ color: map.color }}>
      <span aria-hidden="true">{map.glyph}</span>{map.word}
    </span>
  )
}

export function Note({ children }: { children: ReactNode }) {
  return (
    <p className="text-xs leading-relaxed mt-3" style={{ color: 'var(--text-muted)' }}>
      {children}
    </p>
  )
}

/** A block of detail that is available but not in the way.
 *
 *  The adjustments page is meant to be a board of dials, not an essay. Anything that
 *  needs more than a slider and a caption goes behind one of these. */
export function Disclose({ title, sub, children, defaultOpen = false }: {
  title: string; sub?: string; children: ReactNode; defaultOpen?: boolean
}) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="card p-4">
      <button onClick={() => setOpen(o => !o)} aria-expanded={open}
        className="w-full flex items-baseline justify-between gap-3 text-left">
        <span>
          <span className="block text-[13px] font-bold">{title}</span>
          {sub && !open && (
            <span className="block text-[12px] mt-0.5" style={{ color: 'var(--text-secondary)' }}>
              {sub}
            </span>
          )}
        </span>
        <span className="text-[11px] font-semibold shrink-0"
          style={{ color: 'var(--series-cost)' }}>{open ? 'Hide' : 'Open'}</span>
      </button>
      {open && <div className="mt-4">{children}</div>}
    </div>
  )
}

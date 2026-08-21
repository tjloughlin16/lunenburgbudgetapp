import { useState } from 'react'
import { usd, usdShort, type AppliedItem } from '../model/engine'

export interface YearRemainder { fy: number; gap: number; remaining: number }

/** The arithmetic, pinned to the top of the adjustments page.
 *
 *  One gap, the things you have done about it, and what is left. It is a bar rather than a
 *  floating card because on this page it is not an aside — it is the answer, and every
 *  control below it is an input to this line. */
export function ScenarioBar({ gap, found, cuts, restored, fte, years, warnings,
  onReset, onResetItem }: {
  gap: number
  found: AppliedItem[]
  cuts: AppliedItem[]
  /** Things put back — they enlarge the hole rather than closing it. */
  restored: AppliedItem[]
  fte: number
  years: YearRemainder[]
  warnings: string[]
  onReset: () => void
  onResetItem: (id: string) => void
}) {
  const [open, setOpen] = useState(false)

  const foundTotal = found.reduce((s, i) => s + i.amount, 0)
  const cutTotal = cuts.reduce((s, i) => s + i.amount, 0)
  const restoreTotal = restored.reduce((s, i) => s + i.amount, 0)
  // Putting something back is not a cut with a minus sign in front of it — it is a bigger
  // hole to close. Keeping it on the left of the equals sign is the only honest place.
  const hole = gap + restoreTotal
  const remaining = hole - foundTotal - cutTotal
  const closed = remaining <= 0
  const changes = found.length + cuts.length + restored.length

  const pctFound = Math.max(0, Math.min(100, (foundTotal / hole) * 100))
  const pctCut = Math.max(0, Math.min(100 - pctFound, (cutTotal / hole) * 100))

  return (
    <div className="sticky z-20 border-b print:static"
      style={{ top: 'var(--header-h)',
               background: 'var(--surface-1)', borderColor: 'var(--grid)' }}>
      <div className="mx-auto max-w-6xl px-5 py-3">
        <div className="flex flex-wrap items-end gap-x-6 gap-y-2">
          <span className="hidden lg:block">
            <Figure label="FY28 gap" value={usd(gap)} tone="var(--text-primary)" />
          </span>
          {restoreTotal > 0 && <>
            <Op>+</Op>
            <Figure label="Put back" value={usd(restoreTotal)}
              tone="var(--series-revenue)" />
          </>}
          <Op>−</Op>
          <Figure label="Raised or saved" value={usd(foundTotal)}
            tone={foundTotal > 0 ? 'var(--status-good)' : 'var(--text-muted)'} />
          <Op>−</Op>
          <Figure label={`Cut${fte > 0 ? ` · ${fte.toFixed(1)} FTE` : ''}`} value={usd(cutTotal)}
            tone={cutTotal > 0 ? 'var(--status-critical)' : 'var(--text-muted)'} />
          <Op>=</Op>
          <Figure label={closed ? 'Gap closed' : 'Still to find'}
            value={closed ? (remaining < -1000 ? `${usd(-remaining)} spare` : usd(0)) : usd(remaining)}
            big tone={closed ? 'var(--status-good)' : 'var(--status-critical)'} />

          <span className="ml-auto flex items-center gap-3 shrink-0">
            {changes > 0 && (
              <button onClick={onReset} className="text-[11px] font-semibold underline"
                style={{ color: 'var(--text-muted)' }}>Reset</button>
            )}
            <button onClick={() => setOpen(o => !o)} aria-expanded={open}
              className="text-[11px] font-semibold underline"
              style={{ color: 'var(--series-cost)' }}>
              {open ? 'Hide the list' : `${changes} change${changes === 1 ? '' : 's'}`}
            </button>
          </span>
        </div>

        <div className="flex h-2 rounded-full overflow-hidden gap-0.5 mt-2.5"
          style={{ background: 'var(--surface-3)' }}>
          <span style={{ width: `${pctFound}%`, background: 'var(--status-good)' }} />
          <span style={{ width: `${pctCut}%`, background: 'var(--status-critical)' }} />
        </div>

        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mt-1.5 text-[10px]"
          style={{ color: 'var(--text-muted)' }}>
          {years.map(y => (
            <span key={y.fy} className="tnum">
              FY{y.fy}{' '}
              <strong style={{ color: y.remaining <= 0 ? 'var(--status-good)' : 'var(--status-critical)' }}>
                {y.remaining <= 0 ? 'closed' : usdShort(y.remaining)}
              </strong>
            </span>
          ))}
          <span className="hidden lg:inline">
            — what is still open each year if you hold these same choices
          </span>
        </div>

        {warnings.map(w => (
          <p key={w} className="text-[11px] mt-1.5" style={{ color: 'var(--status-serious)' }}>
            <span aria-hidden="true">⚠ </span>{w}
          </p>
        ))}

        {open && (
          <div className="mt-3 pt-3 border-t grid gap-4 sm:grid-cols-2 max-h-[45vh] overflow-y-auto"
            style={{ borderColor: 'var(--grid)' }}>
            {changes === 0 ? (
              <p className="text-[12px] leading-relaxed sm:col-span-2"
                style={{ color: 'var(--text-secondary)' }}>
                Nothing changed yet, so the whole {usdShort(gap)} is still open. Move any
                dial below, or load a ranking, and every change lands here. Nothing you do
                is saved or sent anywhere.
              </p>
            ) : (
              <>
                <Group title="Raised or saved" items={found} tone="var(--status-good)"
                  onResetItem={onResetItem} />
                <Group title="Cut" items={cuts} tone="var(--status-critical)"
                  onResetItem={onResetItem} />
                <Group title="Put back — adds to the gap" items={restored}
                  tone="var(--series-revenue)" onResetItem={onResetItem} />
              </>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

const Op = ({ children }: { children: string }) => (
  <span className="text-lg font-bold pb-0.5 hidden sm:block"
    style={{ color: 'var(--text-muted)' }} aria-hidden="true">{children}</span>
)

function Figure({ label, value, tone, big }: {
  label: string; value: string; tone: string; big?: boolean
}) {
  return (
    <span className="block">
      <span className="block text-[10px] font-semibold uppercase tracking-widest"
        style={{ color: 'var(--text-muted)' }}>{label}</span>
      <span className={`block font-bold tnum leading-none ${big ? 'text-2xl' : 'text-lg'}`}
        style={{ color: tone }}>{value}</span>
    </span>
  )
}

function Group({ title, items, tone, onResetItem }: {
  title: string; items: AppliedItem[]; tone: string
  onResetItem: (id: string) => void
}) {
  if (items.length === 0) return null
  const total = items.reduce((s, i) => s + i.amount, 0)
  return (
    <div>
      <div className="flex items-baseline justify-between gap-3 mb-1">
        <span className="text-[10px] font-bold uppercase tracking-widest" style={{ color: tone }}>
          {title}
        </span>
        <span className="text-[11px] font-bold tnum" style={{ color: tone }}>{usd(total)}</span>
      </div>
      <ul className="space-y-1.5">
        {items.map(i => (
          <li key={i.id} className="flex items-baseline justify-between gap-2 text-[12px]">
            <span className="min-w-0">
              <span className="block truncate">{i.label}</span>
              <span className="block text-[10px]" style={{ color: 'var(--text-muted)' }}>
                {i.detail}
              </span>
            </span>
            <span className="flex items-baseline gap-1.5 shrink-0">
              <span className="tnum" style={{ color: 'var(--text-secondary)' }}>
                {usd(i.amount)}
              </span>
              <button onClick={() => onResetItem(i.id)}
                aria-label={`Undo ${i.label}`} title="Undo"
                className="px-1 rounded text-[13px] leading-none"
                style={{ color: 'var(--text-muted)' }}>×</button>
            </span>
          </li>
        ))}
      </ul>
    </div>
  )
}

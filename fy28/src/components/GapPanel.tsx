import { useState } from 'react'
import { usd, usdShort, type AppliedItem } from '../model/engine'

/** The running answer, always on screen.
 *
 *  Everything in this tool is one arithmetic problem — a gap, the things you do about it,
 *  and what is left. Spread across five sections that is impossible to hold in your head,
 *  and the levers look unrelated to the cuts. This panel is the single place where they
 *  add up, and every line in it is something the reader actually changed. */
export function GapPanel({ gap, items, unclosed, fte, onReset, onResetItem }: {
  gap: number
  items: AppliedItem[]
  unclosed: number
  fte: number
  onReset: () => void
  onResetItem: (id: string) => void
}) {
  const [open, setOpen] = useState(false)

  const levers = items.filter(i => i.kind !== 'cut')
  const cuts = items.filter(i => i.kind === 'cut')
  const found = levers.reduce((s, i) => s + i.amount, 0)
  const cutTotal = cuts.reduce((s, i) => s + i.amount, 0)

  // The gap always closes — the priority cascade keeps cutting until it does. So the
  // question this panel answers is not "is it closed" but "what is it costing you".
  const noCuts = cutTotal === 0 && unclosed === 0
  const pctFound = Math.min(100, (found / gap) * 100)
  const pctCut = Math.min(100 - pctFound, (cutTotal / gap) * 100)

  return (
    <div className="fixed z-30 left-3 right-3 bottom-3 sm:left-auto sm:right-4 sm:bottom-4
      sm:w-[22rem] rounded-xl border shadow-lg print:hidden"
      style={{ background: 'var(--surface-1)', borderColor: 'var(--grid)' }}>

      <button onClick={() => setOpen(o => !o)} aria-expanded={open}
        className="w-full text-left px-4 py-3">
        <span className="flex items-baseline justify-between gap-3">
          <span className="text-[10px] font-bold uppercase tracking-widest"
            style={{ color: 'var(--text-muted)' }}>
            Closing the {usdShort(gap)} FY28 gap
          </span>
          <span className="text-[11px]" style={{ color: 'var(--text-muted)' }}>
            {open ? 'hide' : `${items.length} change${items.length === 1 ? '' : 's'}`}
          </span>
        </span>

        <span className="flex items-baseline justify-between gap-3 mt-0.5">
          <span className="text-2xl font-bold tnum leading-none"
            style={{ color: noCuts ? 'var(--status-good)' : 'var(--status-critical)' }}>
            {noCuts ? 'No cuts needed' : usd(cutTotal)}
          </span>
          {!noCuts && (
            <span className="text-[11px] tnum text-right" style={{ color: 'var(--text-secondary)' }}>
              cut from programmes
              {fte > 0 && <span className="block">{fte.toFixed(1)} staff positions</span>}
            </span>
          )}
        </span>

        <span className="flex h-2 rounded-full overflow-hidden gap-0.5 mt-2"
          style={{ background: 'var(--surface-3)' }}>
          <span style={{ width: `${pctFound}%`, background: 'var(--status-good)' }} />
          <span style={{ width: `${pctCut}%`, background: 'var(--status-critical)' }} />
        </span>

        <span className="flex flex-wrap gap-x-3 text-[10px] mt-1.5"
          style={{ color: 'var(--text-muted)' }}>
          <span><span aria-hidden="true" style={{ color: 'var(--status-good)' }}>■ </span>
            raised or saved {usdShort(found)}</span>
          <span><span aria-hidden="true" style={{ color: 'var(--status-critical)' }}>■ </span>
            cut {usdShort(cutTotal)}</span>
          {unclosed > 0 && (
            <span style={{ color: 'var(--status-critical)' }}>
              {usdShort(unclosed)} still unclosed
            </span>
          )}
        </span>
      </button>

      {open && (
        <div className="px-4 pb-4 border-t pt-3 max-h-[50vh] overflow-y-auto"
          style={{ borderColor: 'var(--grid)' }}>
          {items.length === 0 ? (
            <p className="text-[12px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
              Nothing changed yet, and nothing raised — so the whole {usdShort(gap)} gap
              is being closed by cutting. Every fee, saving and priority you set anywhere
              on this page lands here, so the arithmetic is in one place. Nothing you do is
              saved or sent anywhere.
            </p>
          ) : (
            <>
              <Group title="Raised or saved instead of cutting" items={levers}
                tone="var(--status-good)" onResetItem={onResetItem} />
              <Group title="Cut to close the rest" items={cuts}
                tone="var(--status-critical)"
                note="Cuts are a consequence of the ranking, not a control — reorder your
                      priorities and different things fall." />
              {found + cutTotal > gap * 1.02 && (
                <p className="text-[11px] pt-2 mt-2 border-t"
                  style={{ borderColor: 'var(--grid)', color: 'var(--text-muted)' }}>
                  Raised plus cut comes to more than the gap because programmes come in
                  whole units — you cannot cut 60% of a teacher. The cascade cuts until the
                  hole is covered, and the last thing cut usually overshoots.
                </p>
              )}
              {unclosed > 0 && (
                <p className="text-[12px] pt-2 mt-2 border-t"
                  style={{ borderColor: 'var(--grid)', color: 'var(--status-critical)' }}>
                  <strong>{usd(unclosed)} still unclosed.</strong> Every programme in the
                  model has been cut and the gap is still open. Past this point the answer
                  is an override or classroom teachers.
                </p>
              )}
            </>
          )}
          <button onClick={onReset}
            className="mt-3 text-[11px] font-semibold underline"
            style={{ color: 'var(--text-secondary)' }}>
            Reset everything to today
          </button>
          <p className="text-[10px] leading-relaxed mt-3"
            style={{ color: 'var(--text-muted)' }}>
            One year — FY28. The gap itself moves with the growth rates on the Assumptions
            tab. Cuts are what your priority ranking gives up to close whatever the fees
            and savings do not — reorder the ranking and different things fall.
          </p>
        </div>
      )}
    </div>
  )
}

function Group({ title, items, tone, onResetItem, note }: {
  title: string; items: AppliedItem[]; tone: string
  onResetItem?: (id: string) => void
  note?: string
}) {
  if (items.length === 0) return null
  const total = items.reduce((s, i) => s + i.amount, 0)
  return (
    <div className="mb-3">
      <div className="flex items-baseline justify-between gap-3 mb-1">
        <span className="text-[10px] font-bold uppercase tracking-widest"
          style={{ color: tone }}>{title}</span>
        <span className="text-[11px] font-bold tnum" style={{ color: tone }}>
          {usd(total)}
        </span>
      </div>
      <ul className="space-y-1.5">
        {items.map(i => (
          <li key={i.id} className="flex items-baseline justify-between gap-2 text-[12px]">
            <span className="min-w-0">
              {i.anchor
                ? <a href={`#${i.anchor}`} className="block truncate underline"
                    style={{ color: 'var(--text-primary)' }}
                    title="Go to the control that sets this">{i.label}</a>
                : <span className="block truncate"
                    style={{ color: 'var(--text-primary)' }}>{i.label}</span>}
              <span className="block text-[10px]" style={{ color: 'var(--text-muted)' }}>
                {i.detail}
              </span>
            </span>
            <span className="flex items-baseline gap-1.5 shrink-0">
              <span className="tnum" style={{ color: 'var(--text-secondary)' }}>
                {usd(i.amount)}
              </span>
              {onResetItem && (
                <button onClick={() => onResetItem(i.id)}
                  aria-label={`Reset ${i.label} to today's level`}
                  title="Back to today's level"
                  className="px-1 rounded text-[13px] leading-none"
                  style={{ color: 'var(--text-muted)' }}>×</button>
              )}
            </span>
          </li>
        ))}
      </ul>
      {note && (
        <p className="text-[10px] mt-1.5" style={{ color: 'var(--text-muted)' }}>{note}</p>
      )}
    </div>
  )
}

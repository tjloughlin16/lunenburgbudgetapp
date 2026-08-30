import { useEffect, useRef } from 'react'
import { MODEL, usd } from '../model/engine'
import { CAPITAL_AGREEMENT, resequencedAt, strandedAt } from '../model/capital'

const CAP = MODEL.freeCash.capital

/** The FY27 capital programme, with what a given redirect stops marked on it.
 *
 *  Why a dialog and not a section: the reader is dragging a slider. The question "what
 *  does this cost" is asked mid-drag and answered by looking at a list, and a list that
 *  long shoved under the control would push the control off the screen. It opens over the
 *  top and closes back onto the same slider at the same value.
 *
 *  What it shows is the RIGID reading — items off the bottom of the committee's own
 *  ranking, no backfill — because that is the version a reader can check for themselves
 *  against the published plan. It is not the only reading and the footer says so: the
 *  same money re-sequenced against the queue stops far less work, and nothing published
 *  says which the committee would do. Presenting one without the other is what this
 *  section got wrong the first time. */
export function CapitalPlanDialog({ open, onClose, redirect }: {
  open: boolean; onClose: () => void; redirect: number
}) {
  const ref = useRef<HTMLDialogElement>(null)

  useEffect(() => {
    const el = ref.current
    if (!el) return
    if (open && !el.open) el.showModal()
    if (!open && el.open) el.close()
  }, [open])

  if (!CAP) return null

  const draw = Math.max(redirect, 0)
  const { lost, projects } = strandedAt(draw)
  const reseq = resequencedAt(draw)
  const stopped = new Set(projects.map(p => p.rank))
  const funded = [...CAP.items].filter(i => i.funded).sort((a, b) => a.rank - b.rank)
  const queue = [...CAP.items].filter(i => !i.funded).sort((a, b) => a.rank - b.rank)

  return (
    <dialog ref={ref} onClose={onClose}
      onClick={e => { if (e.target === ref.current) onClose() }}
      className="p-0 rounded-xl border backdrop:bg-black/50"
      /* Same restoration as the release-notes dialog: the CSS reset drops the user
         agent's centring margins along with every other margin. */
      style={{ borderColor: 'var(--grid)', background: 'var(--surface-1)',
               color: 'var(--text-primary)', width: 'min(44rem, 94vw)',
               maxWidth: 'none', maxHeight: '86vh',
               position: 'fixed', inset: 0, margin: 'auto' }}>
      <div className="flex items-baseline justify-between gap-3 px-5 py-3.5 border-b
                      sticky top-0 z-10" style={{ borderColor: 'var(--grid)',
                                                  background: 'var(--surface-1)' }}>
        <div className="min-w-0">
          <p className="text-xs font-semibold" style={{ color: 'var(--series-cost)' }}>
            FY27 capital programme
          </p>
          <p className="text-[12px]" style={{ color: 'var(--text-muted)' }}>
            {usd(draw)} redirected &mdash; {projects.length}{' '}
            {projects.length === 1 ? 'project stops' : 'projects stop'}, {usd(lost)} of work
          </p>
        </div>
        <button onClick={onClose} aria-label="Close"
          className="shrink-0 px-2 py-1 leading-none text-[18px] rounded hover:underline"
          style={{ color: 'var(--text-muted)' }}>&times;</button>
      </div>

      <div className="p-5 overflow-y-auto">
        <p className="text-[12.5px] leading-relaxed mb-4"
          style={{ color: 'var(--text-secondary)' }}>
          The committee ranks every request and the money runs out at rank 12. Taken
          strictly in that order and with nothing moved up to fill the space, {usd(draw)}
          {' '}removed stops the {projects.length}{' '}
          {projects.length === 1 ? 'project' : 'projects'} marked below &mdash;{' '}
          <strong>{usd(lost)} of work for {usd(draw)} taken</strong>, because the items are
          indivisible.
        </p>

        <p className="text-[11px] font-semibold uppercase tracking-widest mb-2"
          style={{ color: 'var(--text-muted)' }}>Funded &mdash; ranks 1 to {funded.length}</p>
        <ol className="mb-5">
          {funded.map(i => {
            const stops = stopped.has(i.rank)
            const locked = i.funding === 'stabilization'
            return (
              <li key={i.rank}
                className="flex items-baseline gap-3 py-1.5 border-b text-[12.5px]"
                style={{ borderColor: 'var(--grid)',
                         color: stops ? 'var(--status-bad)' : 'var(--text-primary)' }}>
                <span className="tnum shrink-0 w-6 text-right font-semibold"
                  style={{ color: 'var(--text-muted)' }}>{i.rank}</span>
                <span className="shrink-0 w-16 text-[11px] uppercase tracking-wide"
                  style={{ color: 'var(--text-muted)' }}>{i.dept}</span>
                <span className="flex-1 min-w-0"
                  style={{ textDecoration: stops ? 'line-through' : undefined }}>
                  {i.project}
                  {locked && (
                    <span className="ml-2 text-[10.5px] whitespace-nowrap"
                      style={{ color: 'var(--text-muted)' }}>
                      &mdash; vehicle stabilization, not school money
                    </span>
                  )}
                </span>
                <span className="tnum shrink-0 font-semibold">{usd(i.cost)}</span>
                <span className="shrink-0 w-14 text-right text-[10.5px] uppercase
                                 tracking-wide font-semibold"
                  style={{ color: stops ? 'var(--status-bad)' : 'var(--text-muted)' }}>
                  {stops ? 'stops' : locked ? 'locked' : ''}
                </span>
              </li>
            )
          })}
        </ol>

        <p className="text-[11px] font-semibold uppercase tracking-widest mb-2"
          style={{ color: 'var(--text-muted)' }}>
          Already below the line &mdash; {usd(CAP.queueValue)}, before any of this
        </p>
        <ol className="mb-5">
          {queue.map(i => (
            <li key={i.rank}
              className="flex items-baseline gap-3 py-1 border-b text-[12px]"
              style={{ borderColor: 'var(--grid)', color: 'var(--text-muted)' }}>
              <span className="tnum shrink-0 w-6 text-right font-semibold">{i.rank}</span>
              <span className="shrink-0 w-16 text-[11px] uppercase tracking-wide">
                {i.dept}
              </span>
              <span className="flex-1 min-w-0">{i.project}</span>
              <span className="tnum shrink-0">{usd(i.cost)}</span>
              <span className="shrink-0 w-14" />
            </li>
          ))}
        </ol>

        {/* Rule 7, in the place a reader is most likely to quote a number from. The list
            above is one assumption about a committee, not a measurement of one. */}
        <div className="card p-4 text-[12px] leading-relaxed"
          style={{ color: 'var(--text-secondary)' }}>
          <p className="mb-2">
            <strong style={{ color: 'var(--text-primary)' }}>This is one assumption, and
            it is the pessimistic one.</strong> It holds the committee to its published
            ranking and lets nothing move up. Re-sequenced against the {CAP.queueCount}{' '}
            projects already below the line, the same {usd(draw)} stops about{' '}
            {usd(reseq)} of work instead of {usd(lost)}. Nothing published says which the
            committee would do, and this project holds no year in which it had to choose.
          </p>
          <p>
            {usd(CAP.restrictedTotal)} of the {usd(CAP.programmeTotal)} programme is the
            Vehicle Use Special Purpose Stabilization Fund, restricted to vehicles and
            equipment. It could not have gone to the schools under any vote, so it is
            marked locked above and never stops. What a redirect can reach is{' '}
            {usd(CAP.convertibleTotal)}.
          </p>
          {!CAPITAL_AGREEMENT.ok && (
            <p className="mt-2 font-semibold" style={{ color: 'var(--status-bad)' }}>
              This list disagrees with the published model: {CAPITAL_AGREEMENT.detail}.
              Trust the model, not this list.
            </p>
          )}
        </div>
      </div>
    </dialog>
  )
}

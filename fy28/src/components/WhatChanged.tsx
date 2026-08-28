import { useEffect, useRef, useState } from 'react'
import { MODEL } from '../model/engine'

/** What changed since the reader was last here.
 *
 *  A site that keeps being corrected owes returning readers a way to tell which version
 *  they are looking at. Without one, somebody who read a figure in August and quotes it in
 *  October has no way to know it moved -- and the people most likely to quote a number are
 *  the ones least likely to re-read the whole page to check.
 *
 *  So: a stamp that always says which build this is, and a one-line strip that appears
 *  once when the build has changed under somebody who has been here before.
 *
 *  The strip is deliberately small and deliberately dismissible. A banner that survives
 *  being dismissed is an advertisement, and this is a courtesy. */

const R = MODEL.releases
const KEY = 'lbp:seen-version'

export const VERSION = R.current
export const UPDATED = R.updated

/** The tag as a reader says it. Git calls it `v2`; a sentence calls it "Version 2", and
 *  "Version v2" is neither. Anything that is not a plain vN tag is printed as it stands. */
const LABEL = /^v\d+$/.test(R.current) ? `Version ${R.current.slice(1)}` : R.current

/** An ISO date as somebody says it out loud, not as a machine stores it.
 *
 *  Built from the parts rather than parsed, because `new Date('2026-08-28')` is read as
 *  UTC midnight and renders as the previous day for every reader west of Greenwich --
 *  which is all of them. */
export function longDate(iso: string): string {
  const [y, m, d] = iso.split('-').map(Number)
  return new Date(y, m - 1, d).toLocaleDateString('en-US',
    { day: 'numeric', month: 'long', year: 'numeric' })
}

export const updatedLong = () => longDate(R.updated)

/** Which build this is, said in the footer of every page. */
export function VersionStamp({ onOpen }: { onOpen?: () => void }) {
  return (
    <span>
      {LABEL} &mdash; updated {updatedLong()}
      {onOpen && <>{' '}
        <button onClick={onOpen} className="font-semibold hover:underline"
          style={{ color: 'var(--series-cost)' }}>what changed &rarr;</button>
      </>}
    </span>
  )
}

/** The line at the top of every page saying which build this is.
 *
 *  One element with two states rather than two elements. Settled, it is a quiet stamp: the
 *  date, and a way in to the history. When the build has moved since the reader was last
 *  here it says the one sentence they need in order to read the rest correctly, and offers
 *  to be dismissed back to the quiet form.
 *
 *  Two states, not two components, because a banner that appears next to a permanent stamp
 *  saying the same date is the site talking to itself.
 *
 *  Storage can be absent for two reasons and they are not distinguishable: a first-time
 *  reader, and somebody who read an earlier build before this existed. The second is
 *  exactly who this is for, so an absent key counts as "has not seen this build". The cost
 *  to a genuinely new reader is one sentence about a site they are reading for the first
 *  time anyway.
 *
 *  Storage also throws outright in some contexts -- a private window, a browser set to
 *  block site data, a thumbnail capture. Every read and write is guarded; on failure the
 *  bar stays in its settled form rather than taking the page down. */
export function UpdatedBar({ onOpen }: { onOpen: () => void }) {
  const [isNew, setIsNew] = useState(false)

  useEffect(() => {
    try {
      if (localStorage.getItem(KEY) !== R.current) setIsNew(true)
    } catch { /* storage unavailable; stay in the settled form */ }
  }, [])

  const settle = () => {
    setIsNew(false)
    try { localStorage.setItem(KEY, R.current) } catch { /* nothing to do */ }
  }

  const rel = R.items[0]

  return (
    <div className="border-b" style={{ borderColor: 'var(--grid)',
      background: isNew ? 'var(--surface-2)' : 'transparent' }}>
      {/* One row, always. The date and the way in are fixed width and never shrink; the
          only flexible part is the short note, which truncates rather than wrapping. A
          bar that becomes two rows on a phone is furniture above the actual page. */}
      <div className="mx-auto max-w-6xl px-5 flex items-center gap-2 text-[12px] py-2
                      whitespace-nowrap">
        <span className="shrink-0"
          style={{ color: isNew ? 'var(--text-primary)' : 'var(--text-secondary)',
                   fontWeight: isNew ? 600 : 400 }}>
          Updated {updatedLong()}
        </span>
        <span className="min-w-0 truncate" style={{ color: 'var(--text-secondary)' }}>
          &mdash; {isNew ? rel.short : LABEL}
        </span>
        {/* The same words in both states. A link whose label changes with the state is a
            link somebody has to read before they know whether they have clicked it
            before. */}
        <button onClick={() => { settle(); onOpen() }}
          className="shrink-0 font-semibold hover:underline ml-auto"
          style={{ color: 'var(--series-cost)' }}>
          What changed &rarr;
        </button>
        {isNew && (
          <button onClick={settle} aria-label="Dismiss"
            className="shrink-0 px-1 leading-none text-[15px]"
            style={{ color: 'var(--text-muted)' }}>&times;</button>
        )}
      </div>
    </div>
  )
}

/** The full history, over the page rather than instead of it.
 *
 *  A reader who wants to know what moved is in the middle of reading something. Sending
 *  them to another page to find out costs them their place and their scroll position, and
 *  the back button only returns the first of those. So it opens over the top and closes
 *  back onto the same paragraph.
 *
 *  Native <dialog>, so Escape closes it and focus is handled by the browser rather than
 *  by us doing it worse. The backdrop is clickable because people expect it to be. */
export function ReleaseNotesDialog({ open, onClose }: {
  open: boolean; onClose: () => void
}) {
  const ref = useRef<HTMLDialogElement>(null)

  useEffect(() => {
    const el = ref.current
    if (!el) return
    if (open && !el.open) el.showModal()
    if (!open && el.open) el.close()
  }, [open])

  return (
    <dialog ref={ref} onClose={onClose}
      onClick={e => { if (e.target === ref.current) onClose() }}
      className="p-0 rounded-xl border backdrop:bg-black/50"
      /* A modal <dialog> is centred by the user agent with `inset: 0; margin: auto` --
         which the CSS reset drops along with every other margin, landing it top left.
         Restored explicitly rather than relying on a default that a reset is entitled
         to remove. */
      style={{ borderColor: 'var(--grid)', background: 'var(--surface-1)',
               color: 'var(--text-primary)', width: 'min(46rem, 92vw)',
               maxWidth: 'none', maxHeight: '85vh',
               position: 'fixed', inset: 0, margin: 'auto' }}>
      <div className="flex items-baseline justify-between gap-3 px-5 py-3.5 border-b
                      sticky top-0" style={{ borderColor: 'var(--grid)',
                                             background: 'var(--surface-1)' }}>
        <div>
          <p className="text-xs font-semibold" style={{ color: 'var(--series-cost)' }}>
            What changed
          </p>
          <p className="text-[12px]" style={{ color: 'var(--text-muted)' }}>
            {LABEL} &mdash; updated {updatedLong()}
          </p>
        </div>
        <button onClick={onClose} aria-label="Close"
          className="shrink-0 px-2 py-1 leading-none text-[18px] rounded hover:underline"
          style={{ color: 'var(--text-muted)' }}>&times;</button>
      </div>
      <div className="p-5 overflow-y-auto">
        <ReleaseNotes />
      </div>
    </dialog>
  )
}

/** The list itself, so it can also be read inline where a page wants it. */
export function ReleaseNotes() {
  return (
    <div className="space-y-4">
      {R.items.map((r, i) => (
        <div key={r.tag} className="card p-4">
          <div className="flex items-baseline justify-between gap-3 mb-1">
            <p className="text-[15px] font-bold">{r.title}</p>
            <p className="text-[11px] font-semibold tnum shrink-0"
              style={{ color: i === 0 ? 'var(--series-cost)' : 'var(--text-muted)' }}>
              {r.tag}{i === 0 && ' · current'}
            </p>
          </div>
          <p className="text-[11px] mb-2" style={{ color: 'var(--text-muted)' }}>
            {longDate(r.date)}
          </p>
          <p className="text-[13px] leading-relaxed mb-2.5"
            style={{ color: 'var(--text-secondary)' }}>{r.headline}</p>
          <ul className="space-y-1.5">
            {r.changes.map((c, j) => (
              <li key={j} className="text-[12.5px] leading-relaxed flex gap-2"
                style={{ color: 'var(--text-secondary)' }}>
                <span aria-hidden="true" style={{ color: 'var(--text-muted)' }}>&mdash;</span>
                <span>{c}</span>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  )
}

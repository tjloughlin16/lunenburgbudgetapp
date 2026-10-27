import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { pathFor } from '../routes'
import { AskForm, type About } from './AskForm'

/** "Ask about this page", in the breadcrumb row of every page.
 *
 *  TJ, 27 October 2026: *"at the top of every page ... an ask a question about this page
 *  button, which just brings them to the normal question page, but filled in with the page
 *  they're looking at. That way, they don't even have to know that the question page
 *  exists ... I don't think it should be a CTA in particular, but it should be obvious
 *  enough that they could click it if they're confused about something."*
 *
 *  So it is a quiet link in the row every page already has, not a button: the place a
 *  confused reader's eye goes is the top of the page, and a coloured button there would
 *  compete with the page's own title.
 *
 *  IT OPENS A DRAWER, NOT THE QUESTION PAGE. TJ, the same day: *"it should maybe open up a
 *  sidebar that mimics the question page and keep it easier."* Leaving the page takes the
 *  reader away from the thing that confused them. The drawer is NON-MODAL -- no backdrop,
 *  the page still scrolls -- so they can look back at the chart while they write. The link
 *  keeps the question page as its real address, so a new tab or a middle-click still lands
 *  on the same form with the page filled in (pages/AskUs.tsx reads `page` and `title`).
 *
 *  The title is the page's own <h1>, watched until it appears, because most pages fetch
 *  their payload before they draw a heading. A topic page passes its title in directly. */
export function AskAboutPage({ title }: { title?: string | null }) {
  const [heading, setHeading] = useState('')
  useEffect(() => {
    if (title) return
    const read = () => setHeading(document.querySelector('h1')?.textContent?.trim() ?? '')
    read()
    const mo = new MutationObserver(read)
    mo.observe(document.body, { childList: true, subtree: true, characterData: true })
    return () => mo.disconnect()
  }, [title])
  const name = (title || heading).slice(0, 160)
  const q = new URLSearchParams({ page: window.location.pathname })
  if (name) q.set('title', name)
  const [open, setOpen] = useState(false)
  return (<>
    <a data-no-count href={`${pathFor('askus')}?${q}`}
      onClick={e => {
        if (e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return
        e.preventDefault(); setOpen(true)
      }}
      aria-expanded={open}
      title="Ask us a question about this page. A person reads every one."
      className="text-[12px] font-semibold whitespace-nowrap shrink-0 inline-flex items-center gap-1
                 rounded-full px-2.5 py-0.5 border hover:underline"
      style={{ color: 'var(--series-cost)', borderColor: 'var(--grid)' }}>
      <span aria-hidden="true">?</span>
      <span className="sm:hidden">Ask</span>
      <span className="hidden sm:inline">Ask about this page</span>
    </a>
    {open && createPortal(
      <AskDrawer about={{ page: window.location.pathname, title: name }} onClose={() => setOpen(false)} />,
      document.body)}
  </>)
}

function AskDrawer({ about: from, onClose }: { about: About; onClose: () => void }) {
  const [about, setAbout] = useState<About | null>(from)
  const panel = useRef<HTMLDivElement | null>(null)
  useEffect(() => {
    const key = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', key)
    return () => window.removeEventListener('keydown', key)
  }, [onClose])
  // Focus the box as soon as the form draws (it waits on the server saying it is open).
  useEffect(() => {
    if (!panel.current) return
    const mo = new MutationObserver(() => {
      const t = panel.current?.querySelector('textarea')
      if (t) { t.focus(); mo.disconnect() }
    })
    mo.observe(panel.current, { childList: true, subtree: true })
    return () => mo.disconnect()
  }, [])
  return (
    <aside ref={panel} role="dialog" aria-modal="false" aria-label="Ask about this page"
      data-no-count
      className="fixed inset-y-0 right-0 z-[60] w-full sm:w-[440px] overflow-y-auto border-l
                 px-5 pt-5 pb-10 shadow-2xl"
      style={{ background: 'var(--surface-2)', borderColor: 'var(--grid)' }}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-[19px] font-bold leading-tight">Ask about this page</p>
          <p className="text-[13.5px] mt-1" style={{ color: 'var(--text-secondary)' }}>
            Something confusing, missing or wrong? <strong>A person reads every one.</strong>
          </p>
        </div>
        <button type="button" onClick={onClose} aria-label="Close"
          className="text-[22px] leading-none px-2 py-1 -mr-2 rounded hover:opacity-70"
          style={{ color: 'var(--text-muted)' }}>&times;</button>
      </div>
      <AskForm about={about} onClearAbout={() => setAbout(null)} />
      <p className="text-[12.5px] mt-6" style={{ color: 'var(--text-muted)' }}>
        Your question is not published. What we keep, and what happens to it:{' '}
        <a href={pathFor('askus')} className="underline">the question page</a>.
      </p>
    </aside>
  )
}

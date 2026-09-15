import { useEffect, useRef, useState } from 'react'
import { countWords, label } from './ReadingTime'

/** THE FOLD: everything after the short version, behind one control.
 *
 *  TJ, 15 September 2026: *"'The working' is not a phrase people will understand ...
 *  that separation isn't clear. it just flows right into that sections."* Both true. A
 *  rule between two sections is not a boundary; the eye keeps going. And "the working"
 *  is rule 7b's word, not a resident's.
 *
 *  This is the DISCLOSURE pattern -- GOV.UK's Details component, Wikipedia's collapsed
 *  sections on a phone -- done with the two things a "read more" usually gets wrong:
 *
 *   1. THE LABEL SAYS WHAT YOU GET AND HOW MUCH. "Read the full analysis · 21 min". The
 *      minutes are counted from the content behind the control, by the same code the
 *      breadcrumb row uses, so the choice is informed and the figure cannot be typed
 *      wrong.
 *   2. IT OPENS ITSELF WHEN SOMETHING INSIDE IT IS ASKED FOR. A shared link with a
 *      `#hash` into a room, a citation marker `[16]` on a card, "How this was worked
 *      out →", the print button: every one of those lands inside the fold, and a fold
 *      that stays shut on them is a page that opens to nothing. So: on mount and on
 *      hashchange, if the target is inside, open first and scroll after; on any click
 *      of an in-page anchor whose target is inside, open before the browser jumps; on
 *      `beforeprint`, open, and restore after.
 *
 *  A native <details>: no JavaScript needed to open it by hand, it works before
 *  hydration, and the prerendered HTML carries the whole long version inside it, so an
 *  agent or a crawler reads everything. Inside, an "On this page" list of the sections
 *  with ids, so a reader who did open it can navigate rather than scroll. */
export function FullVersion({ what = 'the full analysis', children }: {
  /** What the control offers: "the full analysis" (a report), "the whole argument" (the crisis page). */
  what?: string
  children: React.ReactNode
}) {
  const ref = useRef<HTMLDetailsElement>(null)
  const [words, setWords] = useState<number | null>(null)
  const [heads, setHeads] = useState<{ id: string; text: string }[]>([])

  useEffect(() => {
    const el = ref.current
    if (!el) return
    let live = true
    let timer: number | undefined
    const inside = (id: string) => {
      const t = id ? document.getElementById(id) : null
      return t && el.contains(t) ? t : null
    }
    const open = () => { if (!el.open) el.open = true }

    // The count and the section list, settled with the content.
    const measure = () => {
      if (!live) return
      setWords(countWords(el).all)
      // A heading with an id, or the first heading of a section with one (the crisis
      // page's rooms). Deduplicated by id, in document order.
      const seen = new Set<string>()
      const found: { id: string; text: string }[] = []
      for (const n of el.querySelectorAll<HTMLElement>('h2[id], section[id]')) {
        const h = n.tagName === 'H2' ? n : n.querySelector('h2')
        const id = n.id
        if (!h || !id || seen.has(id)) continue
        seen.add(id)
        found.push({ id, text: (h.textContent || '').trim() })
      }
      setHeads(found.filter(h => h.text))
    }
    const later = () => { window.clearTimeout(timer); timer = window.setTimeout(measure, 250) }
    measure()
    const mo = new MutationObserver(later)
    mo.observe(el, { childList: true, subtree: true, characterData: true })

    // A link into the fold opens it. On arrival, on a hash change, and on the click
    // itself -- the click matters because a repeated hash fires no hashchange, and
    // because the browser jumps before it fires, to an element that is still hidden.
    const onHash = () => {
      const t = inside(window.location.hash.slice(1))
      if (t) { open(); requestAnimationFrame(() => t.scrollIntoView()) }
    }
    const onClick = (e: MouseEvent) => {
      const a = (e.target as Element | null)?.closest?.('a[href^="#"]') as HTMLAnchorElement | null
      if (!a) return
      const t = inside(a.getAttribute('href')!.slice(1))
      if (t) { open(); requestAnimationFrame(() => t.scrollIntoView({ behavior: 'smooth' })) }
    }
    onHash()
    window.addEventListener('hashchange', onHash)
    document.addEventListener('click', onClick, true)

    // Paper has no fold. TJ's readers print these for meetings.
    let wasOpen = false
    const before = () => { wasOpen = el.open; el.open = true }
    const after = () => { el.open = wasOpen }
    window.addEventListener('beforeprint', before)
    window.addEventListener('afterprint', after)

    return () => {
      live = false
      mo.disconnect(); window.clearTimeout(timer)
      window.removeEventListener('hashchange', onHash)
      document.removeEventListener('click', onClick, true)
      window.removeEventListener('beforeprint', before)
      window.removeEventListener('afterprint', after)
    }
  }, [])

  return (
    <details ref={ref} className="fold mt-10">
      <summary className="fold-summary list-none cursor-pointer select-none">
        <span className="fold-closed">
          <span className="text-[16px] font-bold">Read {what}</span>
          <span aria-hidden="true" className="ml-1.5">&darr;</span>
        </span>
        <span className="fold-open">
          <span className="text-[16px] font-bold">The full version</span>
          <span aria-hidden="true" className="ml-1.5">&uarr;</span>
        </span>
        {words !== null && (
          <span data-no-count className="text-[13px] tnum ml-3" style={{ color: 'var(--text-muted)' }}>
            {label(words)}
          </span>
        )}
      </summary>
      {/* A TABLE OF CONTENTS, SET LIKE ONE. The first version was a stack of underlined
          sentences -- TJ: "i thought this was a bug, but its the styling." Numbered,
          in the secondary colour, no underline until hover, two columns where there is
          room, inside a quiet card so it reads as an instrument and not as prose. */}
      {heads.length > 1 && (
        <nav aria-label="On this page" data-no-count className="toc card mt-4 mb-6 px-5 py-4">
          <p className="text-[11px] font-bold uppercase tracking-widest mb-2" style={{ color: 'var(--text-muted)' }}>
            On this page <span className="tnum font-semibold normal-case tracking-normal">&middot; {heads.length} sections</span>
          </p>
          <ol className="toc-list text-[13.5px] leading-snug">
            {heads.map((h, i) => (
              <li key={h.id} className="flex gap-2 py-0.5">
                <span className="tnum shrink-0 w-5 text-right" style={{ color: 'var(--text-muted)' }}>{i + 1}</span>
                <a className="toc-link min-w-0" href={`#${h.id}`}>{h.text}</a>
              </li>
            ))}
          </ol>
        </nav>
      )}
      {children}
    </details>
  )
}

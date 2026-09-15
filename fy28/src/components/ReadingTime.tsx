import { useEffect, useState } from 'react'

/** "Est. reading time: 12 min", on every page, measured from the page itself.
 *
 *  TJ, 15 September 2026, after seeing notes/generated/reading-time.csv: "can you
 *  actually add that to every one of these pages, like other blogs do?"
 *
 *  MEASURED, NOT TYPED (rule 2). Nothing here knows how long any page is. It counts the
 *  words actually in the document -- everything under #root except the furniture every
 *  page carries (the sticky header, the breadcrumb row this sits in, the footer) -- and
 *  keeps counting as the page fills in, because most pages fetch their payload after
 *  mount and are a loading line for the first hundred milliseconds. A MutationObserver on
 *  the root, debounced, so the figure settles with the page and a chart that measures
 *  itself late is still counted. The prerenderer runs timers to completion under a
 *  virtual-time budget, so the static HTML carries the settled figure too.
 *
 *  THE SAME PACE AS THE TABLE. 230 words a minute, the figure scripts/build_reading_time.py
 *  uses, so the number on a page and the number in the review CSV agree. It is a reading
 *  pace, not a skimming one; the point of stating it is that a page saying "46 min" is a
 *  page telling its author something.
 *
 *  Words in a collapsed <details> are counted. They are on the page, and a page that
 *  hides half of itself behind expanders is that long. */
export const WORDS_PER_MINUTE = 230

/** Elements whose text is not the page: the app header, the breadcrumb, the footer, and
 *  anything that opts out with `data-no-count` (this component's own output does). */
const SKIP = 'header, footer, nav[aria-label="Breadcrumb"], script, style, noscript, svg, [data-no-count]'

function countWords(root: HTMLElement): number {
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
    acceptNode: node => {
      const el = node.parentElement
      if (!el || el.closest(SKIP)) return NodeFilter.FILTER_REJECT
      return NodeFilter.FILTER_ACCEPT
    },
  })
  let n = 0
  for (let t = walker.nextNode(); t; t = walker.nextNode()) {
    const s = (t.nodeValue || '').trim()
    if (s) n += s.split(/\s+/).length
  }
  return n
}

export function label(words: number): string {
  const min = words / WORDS_PER_MINUTE
  if (min < 1) return 'under a minute'
  if (min < 1.5) return '1 min'
  return `${Math.round(min)} min`
}

/** `tab` only so the count restarts when the page changes; the observer does the rest. */
export function ReadingTime({ tab }: { tab: string }) {
  const [words, setWords] = useState<number | null>(null)

  useEffect(() => {
    const root = document.getElementById('root')
    if (!root) return
    let timer: number | undefined
    let live = true
    const measure = () => { if (live) setWords(countWords(root)) }
    const later = () => { window.clearTimeout(timer); timer = window.setTimeout(measure, 250) }
    measure()
    const mo = new MutationObserver(later)
    mo.observe(root, { childList: true, subtree: true, characterData: true })
    return () => { live = false; mo.disconnect(); window.clearTimeout(timer) }
  }, [tab])

  if (words === null) return null
  return (
    <span data-no-count className="text-[12px] tnum whitespace-nowrap shrink-0"
      style={{ color: 'var(--text-muted)' }}
      title={`${words.toLocaleString('en-US')} words on this page at ${WORDS_PER_MINUTE} a minute, counted from the page itself`}>
      Est. reading time: <span style={{ color: 'var(--text-secondary)' }}>{label(words)}</span>
    </span>
  )
}

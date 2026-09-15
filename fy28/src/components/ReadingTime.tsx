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

/** The page's SHORT VERSION -- the part sized to one sitting. Marked with `data-short`
 *  by components/report.tsx (a conclusions section, a Conclusions block, ShortVersion).
 *  Counted once however many marks nest. `null` when the page declares none. */
const SHORT = '[data-short]'

export function countWords(root: HTMLElement): { all: number; short: number | null; rows: number } {
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
    acceptNode: node => {
      const el = node.parentElement
      if (!el || el.closest(SKIP)) return NodeFilter.FILTER_REJECT
      return NodeFilter.FILTER_ACCEPT
    },
  })
  let all = 0, short = 0
  for (let t = walker.nextNode(); t; t = walker.nextNode()) {
    const s = (t.nodeValue || '').trim()
    if (!s) continue
    const n = s.split(/\s+/).length
    all += n
    if (t.parentElement!.closest(SHORT)) short += n
  }
  return { all, short: root.querySelector(SHORT) ? short : null,
           rows: root.querySelectorAll('tbody tr').length }
}

export function label(words: number): string {
  const min = words / WORDS_PER_MINUTE
  if (min < 1) return 'under a minute'
  if (min < 1.5) return '1 min'
  return `${Math.round(min)} min`
}

/** `tab` only so the count restarts when the page changes; the observer does the rest. */
export function ReadingTime({ tab, reference }: { tab: string; reference?: boolean }) {
  const [words, setWords] = useState<{ all: number; short: number | null; rows: number } | null>(null)

  useEffect(() => {
    const root = document.getElementById('root')
    if (!root) return
    let timer: number | undefined
    let live = true
    // Only set when the count moved: a re-render is itself a mutation the observer sees,
    // and a state change on every pass would be a loop that never settles.
    const measure = () => {
      if (!live) return
      const c = countWords(root)
      setWords(prev => (prev && prev.all === c.all && prev.short === c.short && prev.rows === c.rows) ? prev : c)
    }
    const later = () => { window.clearTimeout(timer); timer = window.setTimeout(measure, 250) }
    measure()
    const mo = new MutationObserver(later)
    mo.observe(root, { childList: true, subtree: true, characterData: true })
    return () => { live = false; mo.disconnect(); window.clearTimeout(timer) }
  }, [tab])

  if (words === null) return null
  const n = (x: number) => x.toLocaleString('en-US')
  // AN INSTRUMENT IS NOT A READ. A register, an index, a search box: the honest label is
  // what it is and how big, not how long it would take to read every row.
  if (reference) {
    return (
      <span data-no-count className="text-[12px] tnum whitespace-nowrap shrink-0"
        style={{ color: 'var(--text-muted)' }}
        title={`A reference page, for looking things up rather than reading through: ${n(words.all)} words${words.rows ? `, ${n(words.rows)} table rows` : ''}`}>
        Reference{words.rows ? <> &middot; <span style={{ color: 'var(--text-secondary)' }}>{n(words.rows)} rows</span></> : null}
      </span>
    )
  }
  // TWO FIGURES WHERE THE PAGE HAS TWO LAYERS. "Short version: 3 min · In full: 47 min"
  // tells a reader what they are committing to, and a page that can only say "In full"
  // is a page with no short version -- which is the shame line, on purpose.
  return (
    <span data-no-count className="text-[12px] tnum whitespace-nowrap shrink-0"
      style={{ color: 'var(--text-muted)' }}
      title={(words.short !== null ? `${n(words.short)} words in the short version, ` : '')
        + `${n(words.all)} words on the whole page, at ${WORDS_PER_MINUTE} a minute, counted from the page itself`}>
      {words.short !== null ? (
        <>Short version: <span style={{ color: 'var(--text-secondary)' }}>{label(words.short)}</span>
          <span aria-hidden="true"> · </span></>
      ) : null}
      {words.short !== null ? 'In full: ' : 'Est. reading time: '}
      <span style={{ color: 'var(--text-secondary)' }}>{label(words.all)}</span>
    </span>
  )
}

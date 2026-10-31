import { useEffect } from 'react'
import { abs } from '../lib/abs'

/** EVERY LINK TO A SCANNED PDF OPENS OUR SEARCHABLE COPY, WITH THE RAW ONE BESIDE IT.
 *
 *  TJ, 31 October 2026: *"where we show the pdfs, id like to show the searchable PDF (with the
 *  'raw pdf' link also available)"*.
 *
 *  WHY ONE COMPONENT AT THE ROOT AND NOT A <DocLink> AT EACH SITE. There are ~420 file links in
 *  ~100 components, and most PDF links are not written in the source at all: they arrive in a
 *  generated payload (`href={abs(r.url)}`) or in an analysis's markdown. abs.ts records what
 *  happened the last time a link rule was applied call site by call site -- ten problems became
 *  seven, and the seven were the constructed ones. So this watches the DOM: whatever rendered the
 *  link, a page written next month included, gets the same treatment.
 *
 *  WHAT IT DOES TO A LINK. Only to a link whose PDF has a searchable copy -- the `built` rows of
 *  sources/data/searchable-pdfs.csv, published as /data/searchable-pdfs.json. Its href becomes
 *  `/docs/searchable/<key>`, and a small `raw PDF` link to the original is put right after it.
 *  The original's address is unchanged everywhere else -- llms.txt, the API, the sitemap -- and
 *  it is the one a sha256 is published for; the copy is a reading aid, not a replacement.
 *
 *  WHY THIS DOES NOT FIGHT REACT. The app is mounted with createRoot, not hydrated, so a prerendered
 *  page carrying these links is simply replaced. React never moves its own nodes to make room for
 *  one it did not create; it sets an href only when its prop changes, and when it does, the
 *  observer sees the attribute change and redoes the link -- dropping the old raw link first.
 *  An anchor laid out as a block or a card is left alone: a sibling inserted into a grid or a
 *  flex row would move the layout, and there the original is still the link.
 */

type List = { prefix: string; keys: string[] }

const MARK = 'data-searchable'
// /docs/minutes/... is the published address of a key under meetings/ (functions/docs/_bucket.js)
const URL_TO_KEY: [string, string][] = [['minutes/', 'meetings/']]
const DOC = /^(?:https?:\/\/[^/]+)?\/docs\/(.+\.pdf)$/i

function keyOf(href: string): string | null {
  const m = DOC.exec(href.split(/[?#]/)[0])
  if (!m) return null
  let p = decodeURIComponent(m[1])
  if (p.startsWith('searchable/')) return null
  for (const [from, to] of URL_TO_KEY) if (p.startsWith(from)) p = to + p.slice(from.length)
  return p
}

const rawFor = new WeakMap<HTMLAnchorElement, HTMLElement>()

function enhance(a: HTMLAnchorElement, keys: Set<string>, prefix: string) {
  if (a.closest('.raw-pdf')) return
  const href = a.getAttribute('href') || ''
  // already done, and React has not changed the href since
  if (a.getAttribute(MARK) === href) return
  const old = rawFor.get(a)
  if (old) { old.remove(); rawFor.delete(a) }
  a.removeAttribute(MARK)
  const key = keyOf(href)
  if (!key || !keys.has(key)) return
  const display = getComputedStyle(a).display
  if (display !== 'inline' && display !== 'inline-block' && display !== 'contents') return

  const wrap = document.createElement('span')
  wrap.className = 'raw-pdf no-print'
  const raw = document.createElement('a')
  raw.href = href
  raw.textContent = 'raw PDF'
  raw.title = 'The PDF exactly as the publisher released it'
  if (a.target) raw.target = a.target
  if (a.rel) raw.rel = a.rel
  wrap.append('\u00a0', raw)
  // a page anchor (#page=5) is kept on both links: the copy has the same pages in the same order
  const tail = href.slice(href.split(/[?#]/)[0].length)
  const searchable = abs(prefix + key) + tail
  a.setAttribute('href', searchable)
  a.setAttribute(MARK, searchable)
  a.title = a.title || 'Searchable copy: the publisher\u2019s pages, with a text layer we added'
  a.after(wrap)
  rawFor.set(a, wrap)
}

export function SearchableLinks() {
  useEffect(() => {
    let stop = false
    let observer: MutationObserver | null = null
    fetch('/data/searchable-pdfs.json')
      .then(r => (r.ok ? r.json() : null))
      .then((list: List | null) => {
        if (stop || !list || !list.keys.length) return
        const keys = new Set(list.keys)
        const sweep = (root: ParentNode) =>
          root.querySelectorAll<HTMLAnchorElement>('a[href*=".pdf" i]').forEach(a => enhance(a, keys, list.prefix))
        sweep(document)
        observer = new MutationObserver(muts => {
          for (const m of muts) {
            if (m.type === 'attributes' && m.target instanceof HTMLAnchorElement) {
              enhance(m.target, keys, list.prefix)
            } else {
              m.addedNodes.forEach(n => {
                if (n instanceof HTMLAnchorElement) enhance(n, keys, list.prefix)
                else if (n instanceof Element) sweep(n)
              })
              // a link React removed takes its raw link with it
              m.removedNodes.forEach(n => {
                if (n instanceof HTMLAnchorElement) { rawFor.get(n)?.remove(); rawFor.delete(n) }
              })
            }
          }
        })
        observer.observe(document.body, { subtree: true, childList: true, attributes: true, attributeFilter: ['href'] })
      })
      .catch(() => {})
    return () => { stop = true; observer?.disconnect() }
  }, [])
  return null
}

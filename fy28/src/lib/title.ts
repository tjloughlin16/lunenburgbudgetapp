import { useEffect } from 'react'

/** EVERY PAGE HAD THE SAME `<title>`. All 157 of them: "The Lunenburg Budget Project —
 *  FY28 and beyond", from the shared index.html. So the browser tab, the bookmark, the
 *  history entry, the share preview and the search-engine result for a report on
 *  paraprofessionals all said the same thing as the front page, and a reader with three
 *  tabs open could not tell them apart. Found on 15 September 2026 while fixing the
 *  search index, which had fallen back to the H1 for the same reason.
 *
 *  The prerenderer dumps the DOM after the app has run, so a title set here lands in
 *  the static HTML too. */
export const SITE_NAME = 'Lunenburg Budget Project'

export function pageTitle(name: string | null | undefined): string | null {
  if (!name) return null
  return name.includes(SITE_NAME) ? name : `${name} — ${SITE_NAME}`
}

/** Set the document title for as long as the caller is mounted. A child that knows its
 *  own name (a report, a post, a meeting) calls this and wins over the app-level default,
 *  because the app sets its default in a layout effect and this is a passive effect,
 *  which runs after. */
export function useDocumentTitle(name: string | null | undefined) {
  useEffect(() => {
    const t = pageTitle(name)
    if (t) document.title = t
  }, [name])
}

/* ---- share metadata ----------------------------------------------------------------
 *
 * EVERY PAGE CARRIED THE FRONT PAGE'S DESCRIPTION. TJ, 17 September 2026: "Every page
 * needs a metadata field so that when posting online like FB, each link (like every
 * meeting link, report, etc) has a description instead of just the overall site metadata
 * description." The term for what Facebook, Slack and the rest read is the OPEN GRAPH
 * tags -- og:title, og:description, og:url -- and the same text goes into <meta
 * name="description"> for search engines. The prerenderer dumps the DOM after the app has
 * run, so tags set here land in the static HTML a scraper fetches.
 *
 * Two layers. A page that knows its own summary (ReportShell's standfirst; a post; a
 * meeting) sets it and MARKS the tags as page-specific. The app sets a generic fallback
 * on every navigation first, and after the page has rendered fills in from the first
 * paragraph under the H1 only where nothing more specific was set. */
const SITE_DESCRIPTION = (document.querySelector('meta[name="description"]') as HTMLMetaElement | null)?.content ?? ''
const MARK = 'data-share-page'

function upsert(attr: 'name' | 'property', key: string, content: string, page: boolean) {
  let el = document.head.querySelector<HTMLMetaElement>(`meta[${attr}="${key}"]`)
  if (!el) {
    el = document.createElement('meta')
    el.setAttribute(attr, key)
    document.head.appendChild(el)
  }
  el.content = content
  if (page) el.setAttribute(MARK, '1'); else el.removeAttribute(MARK)
}

/** Trim a description to what a link preview shows: one or two sentences, ~200 chars,
 *  cut at a sentence end where one falls in range. */
export function clip(text: string, max = 200): string {
  const t = text.replace(/\s+/g, ' ').trim()
  if (t.length <= max) return t
  const cut = t.slice(0, max)
  const end = Math.max(cut.lastIndexOf('. '), cut.lastIndexOf('; '), cut.lastIndexOf(' — '))
  return (end > max * 0.5 ? cut.slice(0, end + 1) : cut.slice(0, cut.lastIndexOf(' ')) + '…').trim()
}

export function setShareMeta(o: { title?: string | null; description?: string | null; page?: boolean; type?: 'website' | 'article' }) {
  const title = o.title ?? document.title
  const description = clip(o.description || SITE_DESCRIPTION)
  const page = Boolean(o.page)
  upsert('name', 'description', description, page)
  upsert('property', 'og:title', title, page)
  upsert('property', 'og:description', description, page)
  upsert('property', 'og:url', window.location.origin + window.location.pathname, page)
  upsert('property', 'og:type', o.type ?? 'website', page)
  upsert('property', 'og:site_name', SITE_NAME, page)
  upsert('name', 'twitter:card', 'summary', page)
  upsert('name', 'twitter:title', title, page)
  upsert('name', 'twitter:description', description, page)
}

/** Has a page set its own share text since the last navigation? */
export function sharePageSet(): boolean {
  return Boolean(document.head.querySelector(`meta[property="og:description"][${MARK}]`))
}

/** The generic fallback, from the page itself: the first paragraph after the first H1. */
export function shareFromPage() {
  if (sharePageSet()) return
  const h1 = document.querySelector('main h1, article h1, h1')
  let p: Element | null = h1?.nextElementSibling ?? null
  while (p && !(p.tagName === 'P' && (p.textContent ?? '').trim().length > 40)) p = p.nextElementSibling
  const text = p?.textContent?.trim()
  setShareMeta({ description: text || null, page: false })
}

/** For a component that knows its summary: set it for as long as it is mounted. */
export function useShareMeta(description: string | null | undefined, type: 'website' | 'article' = 'website') {
  useEffect(() => {
    if (description) setShareMeta({ description, page: true, type })
  }, [description, type])
}

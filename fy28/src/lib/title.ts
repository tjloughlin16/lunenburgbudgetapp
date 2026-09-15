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

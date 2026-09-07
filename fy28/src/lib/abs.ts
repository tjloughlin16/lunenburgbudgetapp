import MANIFEST from '../data/agent-manifest.json'

/** A link to a FILE is written out in full. Always.
 *
 *  Pages a person navigates stay relative — they are inside the app and the router owns
 *  them. Anything under /docs, /data, /api or /minutes is a file for a PROGRAM, and a
 *  program cannot follow a path with no site in front of it.
 *
 *  THIS HAS BROKEN THREE TIMES AND EVERY TIME IT LOOKED FINE IN A BROWSER, which is the
 *  whole problem: a browser resolves `/data/x.csv` against the page it is on, so a
 *  relative file link is invisible to every human who checks it. It is only broken for
 *  the readers who cannot click. `model.json` records the first two — 100 links across 18
 *  pages, then 13 more — and the failure was identical each time. An assistant was told
 *  exactly where the data was, could not fetch it because its tool only accepts addresses
 *  it has seen written out, reported the data missing from the very page built to hand it
 *  over, and went to the source repository instead.
 *
 *  `scripts/check-agents.mjs` is the gate: it fetches every route and fails the deploy on
 *  any `href` to those four prefixes that is not absolute.
 *
 *  WHY IT GUARDS ON THE PREFIX RATHER THAN TRUSTING THE CALLER.
 *
 *  The third occurrence was nine pages, and half of those links were not written as
 *  literals at all — they were built at runtime out of a JSON field (`href={r.url}`,
 *  `href={q.cite}`). A rewrite that only catches `href="/docs/…"` in the source misses
 *  every one of them, which is exactly what happened on the first pass here: ten problems
 *  became seven and the seven were all constructed.
 *
 *  So this is safe to wrap around ANY href, and the call sites do not have to know which
 *  kind they hold:
 *
 *    - a file path under those four prefixes gets the site name
 *    - an in-app route (`/what-sports-cost`) is returned untouched, because prefixing it
 *      would turn a client-side navigation into a full page load
 *    - anything already absolute, or external, or a fragment, is returned untouched, so
 *      applying it twice is the same as applying it once
 *
 *  DERIVED, NOT TYPED (rule 2). The site name comes from `agent-manifest.json`, the same
 *  value `llms.txt`, the footer and the agent prompt read. Typing the domain here would
 *  make this file one more place it is written down and the first one to go stale.
 */
const FILE_PREFIX = /^\/(?:docs|data|api|minutes)\//

export const abs = (p: string | undefined | null): string => {
  if (!p) return ''
  return FILE_PREFIX.test(p) ? `${MANIFEST.site}${p}` : p
}

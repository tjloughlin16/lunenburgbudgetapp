import analytics from '../data/analytics.json'

/** TWO LAYERS OF ANALYTICS, NEITHER WITH A COOKIE.
 *
 *  TJ, 16 September 2026: "do we have analytics set up to see how people are flowing
 *  through the site and where they are landing?" No. Now:
 *
 *  1. CLOUDFLARE WEB ANALYTICS, loaded here as a script tag rather than injected by the
 *     zone. Zone injection once altered the bytes of archived HTML documents and broke
 *     their published sha256s (functions/docs/_bucket.js); a tag the app adds can only
 *     ever be on the app's own pages. It answers: where do people land, from where, and
 *     which pages get read. It follows in-app navigation on its own. The token is in
 *     src/data/analytics.json; empty means nothing loads.
 *
 *  2. FIRST-PARTY EVENTS to /api/event (functions/api/event.js) for what the beacon
 *     cannot see: which door on the front page, whether the fold was opened and on which
 *     page, which exit under the wedge, a search that found nothing. Sent with
 *     sendBeacon, fire-and-forget, never awaited, never blocking a click.
 *
 *  No identifier is assigned and nothing is stored in the browser except a per-tab
 *  sessionStorage flag that says "this tab has already sent its landing view" -- so
 *  the first page of a visit can be told from the rest without following anybody. */

export type EventName = 'view' | 'door' | 'fold_open' | 'exit' | 'search_zero' | 'question'

const LANDED = 'lbp-landed'

function landing(): boolean {
  try {
    if (sessionStorage.getItem(LANDED)) return false
    sessionStorage.setItem(LANDED, '1')
    return true
  } catch { return false }
}

function refHost(): string {
  try { return document.referrer ? new URL(document.referrer).host : '' } catch { return '' }
}

/** Record one event. Safe to call anywhere; does nothing during prerender (no beacon
 *  API in headless dump mode is fine -- it would send to a local server) or in dev. */
export function track(name: EventName, detail = ''): void {
  if (typeof navigator === 'undefined' || !('sendBeacon' in navigator)) return
  if (import.meta.env.DEV) return
  if (navigator.webdriver) return  // the prerenderer and any headless check
  const body = JSON.stringify({
    name, detail, page: window.location.pathname,
    ref: name === 'view' ? refHost() : '',
    landing: name === 'view' ? landing() : false,
  })
  try { navigator.sendBeacon('/api/event', new Blob([body], { type: 'application/json' })) } catch { /* nothing */ }
}

/** Layer 1. Called once from main.tsx. */
export function installBeacon(): void {
  const token = (analytics as { cfBeaconToken?: string }).cfBeaconToken
  if (!token || import.meta.env.DEV || typeof document === 'undefined') return
  if (document.querySelector('script[data-cf-beacon]')) return
  const s = document.createElement('script')
  s.defer = true
  s.src = 'https://static.cloudflareinsights.com/beacon.min.js'
  s.setAttribute('data-cf-beacon', JSON.stringify({ token }))
  document.head.appendChild(s)
}

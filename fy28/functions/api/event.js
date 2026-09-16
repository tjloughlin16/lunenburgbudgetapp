/**
 * POST /api/event -- one first-party analytics event, into Workers Analytics Engine.
 *
 * WHY THIS EXISTS. TJ, 16 September 2026: "do we have analytics set up to see how people
 * are flowing through the site and where they are landing?" There was nothing. Cloudflare
 * Web Analytics (the beacon in src/lib/track.ts) answers where people land and from where;
 * it cannot say whether anybody opened the fold, which door they took, or what they
 * searched for and did not find. Those are the questions this site cares about, and they
 * are the ones this endpoint records.
 *
 * WHAT IS RECORDED, AND WHAT IS NOT. Six event names, allow-listed below; the page path;
 * a short detail string (a door name, a route, a search term); the referrer's HOST only
 * (never the full URL); the two-letter country Cloudflare attaches; and a flag saying
 * whether this was the first page of the visit. NO cookie is set, NO identifier is
 * assigned, no IP address or user agent is stored -- so two events from one person cannot
 * be joined, and that is the deliberate price. A resident checking the town's arithmetic
 * should not have to be tracked to do it. What that costs: no true per-visitor paths,
 * only counts at each step. scripts/report_site_events.py reads the counts as a funnel.
 *
 * WHY ANALYTICS ENGINE AND NOT D1. D1 on the Free plan stops at 100,000 writes a day,
 * shared with the search-index push and the question inbox; a busy launch day would take
 * the search sync dark. Analytics Engine is built for exactly this write pattern, has its
 * own budget, and is queried with SQL through the API.
 *
 * FAILS QUIET. The client sends with sendBeacon and never waits. A bad body, a name
 * that is not on the list, or a missing binding returns 204 and records nothing; an
 * analytics endpoint that can be made to error is a way to fill a log.
 */

const NAMES = new Set(['view', 'door', 'fold_open', 'exit', 'search_zero', 'question'])
const clip = (s, n) => (typeof s === 'string' ? s.slice(0, n) : '')

export async function onRequestPost({ request, env }) {
  const ok = new Response(null, { status: 204 })
  let body
  try { body = await request.json() } catch { return ok }
  if (!body || !NAMES.has(body.name)) return ok
  if (!env.EVENTS || typeof env.EVENTS.writeDataPoint !== 'function') return ok
  try {
    env.EVENTS.writeDataPoint({
      // blobs: name, page, detail, referrer host, country, landing
      blobs: [
        body.name,
        clip(body.page, 200),
        clip(body.detail, 200),
        clip(body.ref, 100),
        request.cf?.country || '',
        body.landing ? 'landing' : '',
      ],
      doubles: [1],
      // The index is what a query filters on cheaply; the event name is the axis of
      // every question this is asked.
      indexes: [body.name],
    })
  } catch { /* recorded nothing; see FAILS QUIET */ }
  return ok
}

// Every other method. Pages routes a POST to onRequestPost above before falling here.
export async function onRequestGet({ env }) {
  // A GET says whether the Analytics Engine binding reached this deployment -- the
  // one thing a 204 from the POST cannot say, since the POST fails quiet without it.
  return new Response(JSON.stringify({ post: 'one event: {name, page, detail?, ref?, landing?}',
    bound: Boolean(env.EVENTS && typeof env.EVENTS.writeDataPoint === 'function') }),
    { status: 200, headers: { 'content-type': 'application/json' } })
}

/**
 * `/version.json`, served no-store — the one file that must never be cached.
 *
 * You cannot stop an agent caching a response. The cache sits in its fetch layer rather
 * than in HTTP: Claude Code's own tool states that responses are cached for 15 minutes per
 * URL, and it does not consult `cache-control`. A cache-busting query parameter does not
 * reliably help either -- an assistant sent `?v=923` on eight requests to this site and its
 * tool reported the parameter stripped from seven of them, so seven fetches looked fresh
 * and were not.
 *
 * So staleness is made detectable instead. `version.json` states this build's tag, commit
 * and the counts that other files repeat; a caller fetches it first and compares. That only
 * works if THIS file is current, which is why it alone is `no-store`: a cached canary is
 * worse than none, because it confirms a stale view as current.
 *
 * The rest of the site keeps its existing cache headers deliberately. Once the archive
 * settles, caching it is wanted.
 */
export async function onRequest(context) {
  const res = await context.env.ASSETS.fetch(
    new URL('/version.json', context.request.url))
  return new Response(res.body, {
    status: res.status,
    headers: {
      'content-type': 'application/json; charset=utf-8',
      'cache-control': 'no-store, no-cache, must-revalidate, max-age=0',
      'access-control-allow-origin': '*',
    },
  })
}

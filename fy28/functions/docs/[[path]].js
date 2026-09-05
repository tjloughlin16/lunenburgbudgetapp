// Everything under /docs is an archive file — never an HTML page. If the asset server
// answered with the app shell, the document is missing and must say so.
// See functions/_notfound.js for why this is a Function and not a _redirects rule.
import { assetOr404 } from '../_notfound.js'
import { movedTo } from './_moved.js'
import { fromBucket } from './_bucket.js'

export async function onRequest(context) {
  const res = await context.next()

  // A document that is genuinely here.
  const type = res.headers.get('content-type') || ''
  if (res.status === 200 && !type.includes('text/html')) return res

  // Not here. Before answering 404, check whether it MOVED. The archive was reorganised
  // on 4 September 2026 and llms.txt tells agents to cite `/docs/<path>` URLs, so an
  // address published before that date is a promise this file keeps.
  const path = Array.isArray(context.params.path)
    ? context.params.path.join('/')
    : String(context.params.path || '')
  const to = movedTo(path)
  if (to && to !== path) {
    const url = new URL(context.request.url)
    url.pathname = '/docs/' + to
    // 301, not a silent rewrite: an agent that got content back with no signal would go
    // on citing an address that works only because of this map.
    return Response.redirect(url.toString(), 301)
  }

  // Not in the build and not moved. It may still be in the archive: the binaries were
  // taken out of git and out of the build on 5 September 2026, and the bucket is where
  // they went. Same URL, same bytes, same sha256 -- the only thing that changed is which
  // machine holds them.
  const stored = await fromBucket(context, path)
  if (stored) return stored

  return assetOr404(context)
}

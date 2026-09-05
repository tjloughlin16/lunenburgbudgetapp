// Serving a document out of the R2 archive.
//
// The 912MB of binaries this archive mirrors are no longer in git and no longer copied
// into the build. They live in a public, locked R2 bucket, and this is what puts them
// back under the URL they have always had: `/docs/<path>` is a contract llms.txt
// publishes and `documents.json` embeds, and moving where the bytes are kept should cost
// nobody a link.
//
// KEYS MIRROR THE ARCHIVE PATH, with one exception, and the exception is deliberate.
// `sources/minutes/` was renamed `sources/meetings/` on 4 September 2026 and the
// published URL stayed `/docs/minutes/...`, because a folder name is internal and a URL
// is a promise. The bucket follows the folder, so the URL has to be translated here.
const KEY_PREFIX = [['minutes/', 'meetings/']]

/** The bucket key for a published /docs/ path. */
export function bucketKey(path) {
  for (const [from, to] of KEY_PREFIX) {
    if (path.startsWith(from)) return to + path.slice(from.length)
  }
  return path
}

/**
 * Stream a document out of the bucket, or null if it is not there.
 *
 * Range and conditional requests are passed straight through to R2 rather than
 * reimplemented: a browser opening a 79MB annual report asks for it a slice at a time,
 * and answering every one of those with the whole file is the difference between a PDF
 * that opens and one that appears to hang.
 *
 * Every response says `x-archive-source: r2`. That is not decoration — the same URL can
 * be answered by a build asset or by the bucket, the bytes are identical either way, and
 * without a header saying which, a test that fetches every document cannot tell whether
 * it exercised the bucket at all. `scripts/check_archive_urls.py` asserts on it.
 */
export async function fromBucket(context, path) {
  const bucket = context.env && context.env.ARCHIVE
  if (!bucket) return null

  const key = bucketKey(path)
  const { request } = context

  if (request.method === 'HEAD') {
    const head = await bucket.head(key)
    if (!head) return null
    const headers = new Headers()
    head.writeHttpMetadata(headers)
    headers.set('etag', head.httpEtag)
    headers.set('content-length', String(head.size))
    headers.set('cache-control', CACHE)
    headers.set('x-archive-source', 'r2')
    return new Response(null, { headers })
  }

  let object
  try {
    object = await bucket.get(key, {
      range: request.headers,
      onlyIf: request.headers,
    })
  } catch (err) {
    // An unsatisfiable Range throws rather than returning null. Only answer 416 if the
    // caller actually asked for a range — anything else that throws here is the bucket
    // failing, and reporting that as a bad request would put the blame on the reader.
    if (request.headers.get('range')) {
      return new Response('Range not satisfiable', { status: 416 })
    }
    throw err
  }
  if (object === null) return null

  const headers = new Headers()
  object.writeHttpMetadata(headers)
  headers.set('etag', object.httpEtag)
  headers.set('cache-control', CACHE)
  headers.set('x-archive-source', 'r2')
  headers.set('accept-ranges', 'bytes')

  if (!object.body) {
    // A conditional request whose condition failed: If-None-Match matched, so the caller
    // already has these bytes.
    return new Response(null, { status: 304, headers })
  }
  if (object.range && request.headers.get('range')) {
    const { offset = 0, length = object.size } = object.range
    const end = offset + length - 1
    headers.set('content-range', `bytes ${offset}-${end}/${object.size}`)
    headers.set('content-length', String(length))
    return new Response(object.body, { status: 206, headers })
  }
  headers.set('content-length', String(object.size))
  return new Response(object.body, { headers })
}

// A week, and deliberately not `immutable`.
//
// Almost everything served from here is a published document, which does not change: the
// lock forbids overwriting it, and if our copy ever differed from what was uploaded that
// would be a defect rather than a new version. A year and `immutable` would be right for
// those. But the bucket also holds working files we re-derive -- OCR geometry, page text,
// the roster dumps -- and a reader holding a year-old copy of one of those has no way to
// find out. One rule has to cover both, so it is set by the shorter-lived half.
const CACHE = 'public, max-age=604800'

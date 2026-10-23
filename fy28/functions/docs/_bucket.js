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

// TAKEN DOWN. A key in sources/data/takedowns.csv is a document we published and then
// withdrew -- because it holds private information about a person. The register is
// compiled into `_takedowns.js` by scripts/takedown.py (never read at runtime), and every
// such key answers 410 Gone WITH THE REASON, whether or not the bucket still holds it.
// 410 rather than 404: the address existed, it was withdrawn on purpose, and a reader or
// a crawler should be told so rather than told it was never there.
import { TAKEN_DOWN } from './_takedowns.js'

/** A 410 response for a taken-down /docs/ path, or null if the path is not taken down. */
export function goneFor(path) {
  const entry = TAKEN_DOWN[bucketKey(path)]
  if (!entry) return null
  const lines = [
    'This document has been withdrawn from the archive (410 Gone).',
    '',
    entry.reason,
    '',
    `Withdrawn: ${entry.decided_on}`,
  ]
  if (entry.replacement) {
    lines.push(`What is published instead: https://lunenburgbudgetproject.org${entry.replacement}`)
  }
  lines.push('', 'Every takedown is recorded in https://lunenburgbudgetproject.org/docs/data/takedowns.csv')
  return new Response(lines.join('\n') + '\n', {
    status: 410,
    headers: {
      'content-type': 'text/plain; charset=utf-8',
      // An hour, like every other answer this site may later change its mind about.
      'cache-control': 'public, max-age=3600',
      'x-robots-tag': 'noindex',
      'x-archive-source': 'takedown',
    },
  })
}

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

  const gone = goneFor(path)
  if (gone) return gone

  return serveObject(context, bucket, bucketKey(path), 'r2')
}

// OUR EXTRACTED TEXT OF THE MEETING DOCUMENTS, OUT OF THE SECOND BUCKET.
//
// 12,175 `.txt` files under /docs/minutes/text/ were most of a build that Pages' 20,000-file
// limit refused on 21 October 2026. They are ours -- our reading of the town's PDFs -- so they
// may change when an extractor improves, and they do not belong in the locked archive bucket
// beside the documents they were read from (TJ, 22 October: theirs in the archive, ours where
// it can be replaced). `lunenburg-derived` is unlocked; scripts/sync_derived.py fills it from
// fy28/dist before every deploy, and the deploy leaves these files out.
//
// The key is the published path itself. And a miss here is a 404, NEVER a fall-through to the
// archive bucket: that bucket holds a 5 September 2026 snapshot of these same paths, older
// renderings of about two thousand of them, and serving one would be serving a superseded
// reading under the current address with nothing to say so.
export const DERIVED_PREFIX = 'minutes/text/'

export async function fromDerived(context, path) {
  const bucket = context.env && context.env.DERIVED
  if (!bucket) return null
  return serveObject(context, bucket, path, 'r2-derived')
}

async function serveObject(context, bucket, key, source) {
  const { request } = context

  if (request.method === 'HEAD') {
    const head = await bucket.head(key)
    if (!head) return null
    const headers = new Headers()
    head.writeHttpMetadata(headers)
    headers.set('etag', head.httpEtag)
    headers.set('content-length', String(head.size))
    headers.set('cache-control', cacheFor(key))
    headers.set('x-archive-source', source)
    asDocumentNotPage(headers, key)
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
  headers.set('cache-control', cacheFor(key))
  headers.set('x-archive-source', source)
  headers.set('accept-ranges', 'bytes')
  asDocumentNotPage(headers, key)

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

/**
 * Nine documents in this archive are HTML — the state's own school finance profiles,
 * saved as the page the state served. Handing them back as `text/html` had them modified
 * in transit: Cloudflare Web Analytics injects a 367-byte beacon script into every HTML
 * response on this zone, so a reader who downloaded one and hashed it got a different
 * sha256 from the one we publish. The archive's whole promise is that our copy is the
 * document and you can check it yourself, and that promise cannot survive the delivery
 * changing the bytes.
 *
 * It was found by `scripts/check_archive_urls.py` fetching every published address and
 * hashing the answer. It could not have been found by testing the preview deploy, because
 * `*.pages.dev` is not in the zone and nothing is injected there — the instrument that
 * reformats before you see it is part of the finding.
 *
 * So an archived HTML file is served as an attachment rather than as a page. Three things
 * that buys, in order of importance: the bytes are the document's bytes; a page somebody
 * else wrote no longer executes on this origin; and it reads as what it is — a document
 * we hold, not a page of this site.
 */
function asDocumentNotPage(headers, key) {
  // NOT A SEARCH RESULT. Everything under /docs/ is a source document or one of our own
  // markdown renderings, and a person who arrives at one from a search engine sees raw
  // text -- pipes, hashes, front matter -- and concludes the site is broken.
  //
  // TJ, 27 September 2026: *"people are finding markdown (from search?!) and saying 'I see
  // code... I am overwhelmed'"*. 147 of 967 sitemap URLs were raw .md and .csv files and
  // were pushed to IndexNow on every run.
  //
  // `noindex` is the precise tool: the document stays fetchable, citable and hashed, so
  // rule 12 is untouched and llms.txt can go on pointing agents here -- it simply stops
  // appearing in results, and, unlike removing it from the sitemap, it REMOVES the copies
  // already indexed. Removal needs the crawler to fetch the URL and see this header, which
  // is exactly why /docs/ is not disallowed in robots.txt: a blocked URL is never re-read,
  // so a noindex on it is never seen and a stale result can sit there for months.
  headers.set('x-robots-tag', 'noindex')

  const type = headers.get('content-type') || ''
  if (!type.includes('text/html')) return
  headers.set('content-type', 'application/octet-stream')
  headers.set('content-disposition',
    `attachment; filename="${key.slice(key.lastIndexOf('/') + 1)}"`)
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

// ONE RULE COULD NOT COVER BOTH, AND THE WEEK WAS WRONG FOR HALF OF IT.
//
// Everything under `analyses/` is written by this project and rewritten whenever a
// generator improves -- the analysis documents, and the chart SVGs they embed. On 21
// September the stabilization charts were corrected to show every year proven, deployed,
// and a reader was still being served a 5.7-hour-old copy with dashed segments across
// gaps that no longer exist. Cached for a week, that is a week of a chart contradicting
// the page around it.
//
// A published document genuinely does not change -- the bucket lock forbids overwriting
// it, and a difference would be a defect rather than a revision -- so a week is right
// for those and stays. Our own derived files get an hour, which is the same bound the
// moved-document redirect already uses and for the same reason: an hour is how long this
// site may be wrong about something it controls.
const DERIVED_CACHE = 'public, max-age=3600'

export function cacheFor(key) {
  return key.startsWith('analyses/') || key.startsWith(DERIVED_PREFIX) ? DERIVED_CACHE : CACHE
}

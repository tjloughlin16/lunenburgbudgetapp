import { fromBucket } from '../docs/_bucket.js'

// The whole database, served out of R2 rather than shipped in the build.
//
// WHY IT MOVED. Cloudflare Pages caps a static asset at 25MB, and that is a platform
// limit rather than a quota -- no plan raises it. The database passed it on 8 September
// 2026 when the DESE ingest took it from 21.2MB to 29.3MB, and a build that ships it
// would fail at DEPLOY time, not at build time, which is the worst place to find out.
//
// R2 has no such cap. This is the same move `/docs/` made when seven documents were
// catalogued and unserveable -- the largest a 79MB annual town report -- and it works for
// the same reason: a URL is an interface and where the bytes are kept is an
// implementation detail. `https://lunenburgbudgetproject.org/data/lunenburg.db` is
// published in llms.txt and in /api/index, and it does not move.
//
// THE BUCKET LOCK DOES NOT BIND HERE, and that is by design rather than luck.
// `archive_storage.frozen()` treats `data/` as ours: a document somebody else published
// must never change, but everything we DERIVE from those documents changes whenever an
// extractor improves. The database is derived, so it can be overwritten in place on each
// rebuild. A frozen database would be unusable -- it is rebuilt from scratch every run.
//
// FALLING BACK IS DELIBERATE. If the bucket has no copy -- a fresh environment, a push
// that has not run -- this returns 404 with a message saying which command fixes it,
// rather than 500 or an empty body. A missing database and a broken database should not
// look the same to whoever is debugging it.
export async function onRequest(context) {
  const hit = await fromBucket(context, 'data/lunenburg.db')
  if (hit) return hit

  return new Response(
    'The database is not in the archive bucket yet.\n\n' +
    'It is served from R2 rather than from the build because it exceeds the 25MB\n' +
    'Cloudflare Pages asset limit. Publish it with:\n\n' +
    '    python3 scripts/sync_archive.py --push\n\n' +
    'Everything in it is also reachable through /api/query and /api/tables.\n',
    {
      status: 404,
      headers: {
        'content-type': 'text/plain; charset=utf-8',
        'cache-control': 'no-store',
        'x-archive-miss': 'database not in the bucket',
      },
    })
}

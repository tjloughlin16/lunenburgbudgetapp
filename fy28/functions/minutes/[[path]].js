/**
 * The meeting archive — and a 404 that tells a program what to fetch instead.
 *
 * WHY THIS EXISTS
 *
 * `/minutes/` returned **200 OK with 252KB of the app shell**. So did `/minutes`,
 * `/minutes/school-committee` and `/minutes/index.txt`. Every one of those is a path an
 * agent guesses first, and every one of them looked like a successful fetch of a page.
 *
 * An agent asked to review the minutes tried `/minutes/`, got HTML with a 200, and
 * reported: *"I can't reach the minutes. /minutes/ returns the SPA shell — same HTML as
 * the homepage. There's no fetchable per-document text URL on the site."* It was wrong —
 * `/minutes/school-committee.txt` is 920KB of exactly what it wanted, and llms.txt
 * documents the pattern — but nothing it could reach said so. That is the second time an
 * assistant has concluded this site does not hold the minutes while standing on top of
 * them.
 *
 * `functions/_notfound.js` already fixed this for `/docs` and `/data`. It was never
 * applied to `/minutes`, which is the prefix an agent is most likely to try.
 *
 * WHAT MAKES THIS DIFFERENT FROM A PLAIN 404
 *
 * The body is instructions. For a human a 404 is a dead end; for a program it is the only
 * message it will ever read, so it carries the three URL patterns that work and a real
 * example of each. A 404 that teaches costs nothing and saves the request that would
 * otherwise never be made.
 */

/** Everything a caller needs to get what they were reaching for. */
function guidance(requested) {
  const site = 'https://lunenburgbudgetproject.org'
  return `Not found: /minutes/${requested}

The meeting archive IS published as plain text — 1,383 agendas and sets of minutes
across 40 town boards. You are one URL away. There are three shapes and no others:

1. ONE FILE PER BOARD, every document concatenated. This is the one to fetch if you
   want to search. You cannot grep a website; you can read one file.
       ${site}/minutes/school-committee.txt      (920 KB)
       ${site}/minutes/finance-committee.txt
       ${site}/minutes/select-board.txt
   The full list of boards, with sizes:
       ${site}/minutes/INDEX.txt

2. ONE DOCUMENT, for citing. Note the /docs/ prefix — this is a different path from
   the bundles above.
       ${site}/docs/minutes/text/<board>/<date>-<kind>-<id>.txt
   for example:
       ${site}/docs/minutes/text/school-committee/2025-09-17-minutes-7408.txt

3. THE INDEX AS DATA, to filter by board or date before fetching anything:
       ${site}/data/minutes-index.csv
   Columns: board, board_id, date, kind, file_id, path, url — where url is the
   town's own copy.

A directory path such as /minutes/ is not a file and never was. Nothing is served
from it.

Start here if you are a program: ${site}/llms.txt
Everything as JSON:               ${site}/api/index
`
}

const HEADERS = {
  'content-type': 'text/plain; charset=utf-8',
  'cache-control': 'no-store',
  'access-control-allow-origin': '*',
  // Named so anything reading headers can see which rule fired, matching _notfound.js.
  'x-archive-miss': 'not a document in the meeting archive',
}

export async function onRequest(context) {
  const { request, env, params } = context
  const parts = Array.isArray(params.path) ? params.path : [params.path].filter(Boolean)
  const path = parts.join('/')

  // A bare /minutes or /minutes/ is a directory, not a file. Answer with the map.
  if (path === '') {
    return new Response(guidance(''), { status: 404, headers: HEADERS })
  }
  if (path.includes('..')) {
    return new Response(guidance(path), { status: 404, headers: HEADERS })
  }

  const res = await env.ASSETS.fetch(new URL(`/minutes/${path}`, request.url))
  // Nothing under /minutes is ever an HTML page — the bundles are plain text. So a 200
  // with text/html is the asset server falling through to the app shell, which is the
  // same tell _notfound.js relies on.
  const type = res.headers.get('content-type') || ''
  if (res.status !== 200 || type.includes('text/html')) {
    return new Response(guidance(path), { status: 404, headers: HEADERS })
  }
  return res
}

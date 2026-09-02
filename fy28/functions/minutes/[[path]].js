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
 *
 * WHY IT IS ALSO SERVED AS HTML
 *
 * Because instructions were not enough, and the reason is precise. Assistants commonly
 * refuse to fetch a URL that has not appeared in something they already fetched. This body
 * was `text/plain`, so the three URLs it recommends were TEXT, not links -- it told an
 * agent exactly what to fetch and simultaneously failed to authorize it. One said so in as
 * many words: "my fetcher will only take URLs it's already seen in a page or search
 * result... /minutes/school-committee.txt, /minutes/INDEX.txt come back as 'not in a prior
 * result'." It had read this page.
 *
 * So the same words are served as HTML with real anchors when the caller accepts HTML, and
 * as plain text when it does not. Content negotiation, not a redesign: a `curl` still gets
 * the text it always got.
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

/** The same guidance as HTML, so that every URL in it is a link a fetcher will accept. */
function guidanceHtml(requested) {
  const site = 'https://lunenburgbudgetproject.org'
  const esc = (t) => String(t).replace(/[&<>"]/g, (c) =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]))
  const a = (path, label) => `<a href="${esc(path)}">${esc(label || site + path)}</a>`
  return `<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>Not found: /minutes/${esc(requested)} — the meeting archive is one URL away</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>body{font:16px/1.5 system-ui,sans-serif;max-width:44rem;margin:2rem auto;padding:0 1rem}
code,a{font-family:ui-monospace,Menlo,monospace}li{margin:.35rem 0}</style></head><body>
<h1>Not found: <code>/minutes/${esc(requested)}</code></h1>
<p>The meeting archive <strong>is</strong> published as plain text — 1,383 agendas and sets
of minutes across 40 town boards. You are one URL away. There are three shapes and no
others.</p>

<h2>1. One file per board, every document concatenated</h2>
<p>This is the one to fetch if you want to search. You cannot grep a website; you can read
one file.</p>
<ul>
  <li>${a('/minutes/school-committee.txt')} (920 KB)</li>
  <li>${a('/minutes/finance-committee.txt')}</li>
  <li>${a('/minutes/select-board.txt')}</li>
</ul>
<p>The full list of boards, with sizes: ${a('/minutes/INDEX.txt')} — or as a page of links,
${a('/agents')}.</p>

<h2>2. One document, for citing</h2>
<p>Note the <code>/docs/</code> prefix — a different path from the bundles above.</p>
<p><code>${site}/docs/minutes/text/&lt;board&gt;/&lt;date&gt;-&lt;kind&gt;-&lt;id&gt;.txt</code><br>
for example ${a('/docs/minutes/text/school-committee/2025-09-17-minutes-7408.txt')}</p>

<h2>3. The index as data, to filter before fetching</h2>
<p>${a('/data/minutes-index.csv')} — columns: board, board_id, date, kind, file_id, path,
url, where <code>url</code> is the town's own copy.</p>

<p>A directory path such as <code>/minutes/</code> is not a file and never was. Nothing is
served from it.</p>
<p>Start here if you are a program: ${a('/llms.txt')}. Everything as JSON:
${a('/api/index')}. Every address on this site, as links: ${a('/agents')}.</p>
</body></html>
`
}

const HEADERS = {
  'content-type': 'text/plain; charset=utf-8',
  'cache-control': 'no-store',
  'access-control-allow-origin': '*',
  // Named so anything reading headers can see which rule fired, matching _notfound.js.
  'x-archive-miss': 'not a document in the meeting archive',
}

/** Plain text, or HTML when the caller said it takes HTML. Same words either way. */
function miss(request, requested) {
  const accept = request.headers.get('accept') || ''
  return accept.includes('text/html')
    ? new Response(guidanceHtml(requested), {
      status: 404,
      headers: { ...HEADERS, 'content-type': 'text/html; charset=utf-8' },
    })
    : new Response(guidance(requested), { status: 404, headers: HEADERS })
}

export async function onRequest(context) {
  const { request, env, params } = context
  const parts = Array.isArray(params.path) ? params.path : [params.path].filter(Boolean)
  const path = parts.join('/')

  // A bare /minutes or /minutes/ is a directory, not a file. Answer with the map.
  if (path === '') {
    return miss(request, '')
  }
  if (path.includes('..')) {
    return miss(request, path)
  }

  const res = await env.ASSETS.fetch(new URL(`/minutes/${path}`, request.url))
  // Nothing under /minutes is ever an HTML page — the bundles are plain text. So a 200
  // with text/html is the asset server falling through to the app shell, which is the
  // same tell _notfound.js relies on.
  const type = res.headers.get('content-type') || ''
  if (res.status !== 200 || type.includes('text/html')) {
    return miss(request, path)
  }
  return res
}

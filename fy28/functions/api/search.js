/**
 * Search everything this project holds, and say how much of it was searched.
 *
 *     GET /api/search?q=helmets
 *     GET /api/search?q="class size"&corpus=transcript,minutes&board=school-committee&since=2025-07-01
 *
 * WHAT IT SEARCHES, AND THE LINE THAT RUNS THROUGH IT
 *
 * One FTS5 table in its own D1 database (`lunenburg-search`, pushed by
 * scripts/sync_search_d1.py from the index scripts/build_search_index.py builds). Five
 * corpora share it and every row says which it is in:
 *
 *   minutes     text out of a file THE TOWN PUBLISHED. A record.
 *   transcript  machine captions of a recording. OURS, derived, a FINDING AID. A hit
 *               is cited as the video at a timestamp and is styled as a transcript, so a
 *               reader cannot mistake it for minutes. A caption model hears *fifteen
 *               hundred*, *$1,500* and *$50* alike; a figure read off one is never the
 *               record.
 *   source      a page of a document in the archive -- a budget, an annual report.
 *   page        a page of this site.
 *   recorded    OUR minutes of a recording, written from the captions. Cited to the
 *               page, which cites the video by the second.
 *   post        a published blog post. Drafts are not on the site and are not here.
 *
 * Every response carries a count PER CORPUS, against that corpus's own size, and the
 * date the index was built. Including on a search with no hits -- which is when it
 * matters most, because "nothing found" and "nobody ever said it" look alike, and the
 * denominator is the only thing that tells them apart.
 *
 * COST, WHICH IS BOUNDED RATHER THAN HOPED ABOUT
 *
 * D1 bills in ROWS READ, 5 million a day on the free plan, and an FTS match reads about
 * one row per matching chunk when it ranks them (measured: `budget` over 1,000 chunks
 * read 222 for 111 hits). A common word over 97,000 rows could read tens of thousands per
 * call, and a public search box is many calls. So each corpus is searched through a
 * subselect capped at CANDIDATES rows, ranked within that, and the count is reported as
 * "2,000+" when it hits the cap. Ranking is therefore global for any term with fewer
 * than 2,000 hits in a corpus and local past that -- stated in the response rather than
 * hidden. Identical queries are served from the edge for ten minutes, as /api/query is.
 *
 * THE QUERY IS REWRITTEN, NOT PASSED THROUGH
 *
 * FTS5's MATCH syntax throws on an unbalanced quote or a stray colon, and a resident
 * typing `sped: para's` should get results, not a syntax error. So the input is turned
 * into a safe expression: quoted phrases stay phrases, every other word becomes a quoted
 * term, and terms are ANDed. NEAR, OR and column filters are not offered here; the
 * command-line tool has them.
 */

const SITE = 'https://lunenburgbudgetproject.org'
const CORPORA = ['post', 'page', 'recorded', 'source', 'minutes', 'transcript']
const PER_CORPUS = 12          // hits returned per corpus
const CANDIDATES = 2000        // rows a corpus search may read before ranking
const CACHE_SECONDS = 600
const MAX_Q = 200

const HEADERS = {
  'content-type': 'application/json; charset=utf-8',
  'access-control-allow-origin': '*',
  'access-control-allow-methods': 'GET, OPTIONS',
}

const json = (obj, status = 200, extra = {}) =>
  new Response(JSON.stringify(obj, null, 1) + '\n', { status, headers: { ...HEADERS, ...extra } })

/** A user's words, as an FTS5 expression that cannot throw. */
export function ftsExpression(q) {
  const terms = []
  const re = /"([^"]+)"|(\S+)/g
  let m
  while ((m = re.exec(q)) !== null) {
    const raw = (m[1] !== undefined ? m[1] : m[2]).replace(/"/g, '')
    // Strip FTS operators and punctuation that carry no meaning to a reader's search.
    // `para's` tokenises as `para` + `s`, and as a phrase that matches nothing; the
    // possessive carries no meaning to a search, so it goes. Likewise trailing punctuation.
    const clean = raw.replace(/[’']s\b/g, '').replace(/[^\p{L}\p{N}\s$%.,-]/gu, ' ')
      .replace(/[.,]+(\s|$)/g, '$1').replace(/\s+/g, ' ').trim()
    if (!clean) continue
    if (m[1] !== undefined) terms.push('"' + clean + '"')
    else for (const w of clean.split(' ')) if (w) terms.push('"' + w + '"')
  }
  return terms.join(' ')
}

export async function onRequest(context) {
  const { request, env } = context
  if (request.method === 'OPTIONS') return new Response(null, { status: 204, headers: HEADERS })
  if (request.method !== 'GET') return json({ error: 'method_not_allowed' }, 405)
  const db = env.SEARCH
  if (!db) return json({ error: 'unavailable', message: 'The search database is not bound to this deployment.' }, 503)

  const url = new URL(request.url)
  const q = (url.searchParams.get('q') || '').trim().slice(0, MAX_Q)
  const corpusParam = (url.searchParams.get('corpus') || '').split(',').map(s => s.trim()).filter(Boolean)
  const corpora = corpusParam.length ? CORPORA.filter(c => corpusParam.includes(c)) : CORPORA
  const board = (url.searchParams.get('board') || '').trim().slice(0, 80)
  const since = (url.searchParams.get('since') || '').trim().slice(0, 10)
  const expr = ftsExpression(q)

  // The index's own statement of what it holds, written by the push. Read, never counted
  // here: a COUNT(*) per corpus would read every row on every call.
  const metaRows = (await db.prepare('SELECT k, v FROM build_meta').all()).results || []
  const meta = Object.fromEntries(metaRows.map(r => [r.k, r.v]))
  const holds = Object.fromEntries(CORPORA.map(c => [c, Number(meta['rows:' + c] || 0)]))
  const index = {
    built: meta.built || null,
    holds,
    note: 'minutes = documents the town published; transcript = our machine captions of '
      + 'recordings, a finding aid cited to the video at a timestamp; recorded = our minutes '
      + 'of a recording; source = pages of '
      + 'archive documents; page = this site; post = published posts.',
  }

  if (!expr) return json({ resource: 'search', q, expression: '', index, results: {}, counts: {} })

  const cache = caches.default
  const cacheKey = new Request(`https://search.invalid/${encodeURIComponent(expr)}|${corpora.join(',')}|${board}|${since}`, { method: 'GET' })
  const hit = await cache.match(cacheKey)
  if (hit) {
    return new Response(await hit.text(), { headers: { ...HEADERS, 'cache-control': `public, max-age=${CACHE_SECONDS}`, 'x-query-cache': 'hit' } })
  }

  const started = Date.now()
  let rowsRead = 0
  const results = {}
  const counts = {}
  const filters = []
  const binds = []
  if (board) { filters.push('board_slug = ?'); binds.push(board) }
  if (since) { filters.push("date >= ?"); binds.push(since) }
  const where = filters.length ? ' AND ' + filters.join(' AND ') : ''

  // AFFINITY, first. A small curated table of what each page is ABOUT -- TJ: "certain
  // words hit more with certain pages ... even if the words don't show up as much". A
  // page matched here is pinned to the top of its corpus and marked as matched by
  // topic, so curation reads as curation and never as the text having said it.
  const pinned = {}
  try {
    const a = await db.prepare(
      `SELECT doc_key, corpus, title, cite_url, snippet(affinity, 0, '‹', '›', ' · ', 12) AS snippet
       FROM affinity WHERE affinity MATCH ?1 ORDER BY bm25(affinity) LIMIT 8`).bind(expr).all()
    rowsRead += (a.meta && a.meta.rows_read) || 0
    for (const row of a.results || []) (pinned[row.corpus] ||= []).push(row)
  } catch (e) {
    // No affinity table yet, or a bad expression: the text search still answers.
  }

  try {
    for (const c of corpora) {
      const sql = `
        SELECT * FROM (
          SELECT corpus, doc_key, title, board, board_slug, date, kind, cite_url, source_url,
                 start_s, chars, bm25(search) AS rank,
                 snippet(search, 0, '‹', '›', '…', 20) AS snippet
          FROM search WHERE search MATCH ?1 AND corpus = ?2${where}
          LIMIT ${CANDIDATES}
        ) ORDER BY rank LIMIT ${PER_CORPUS}`
      const countSql = `SELECT COUNT(*) AS n FROM (SELECT rowid FROM search WHERE search MATCH ?1 AND corpus = ?2${where} LIMIT ${CANDIDATES})`
      const [r, n] = await Promise.all([
        db.prepare(sql).bind(expr, c, ...binds).all(),
        db.prepare(countSql).bind(expr, c, ...binds).all(),
      ])
      rowsRead += (r.meta && r.meta.rows_read || 0) + (n.meta && n.meta.rows_read || 0)
      const count = (n.results && n.results[0] && n.results[0].n) || 0
      counts[c] = { hits: count, capped: count >= CANDIDATES, holds: holds[c] }
      // A transcript hit is cited at its CHUNK's start -- within sixty seconds before the
      // words, since a chunk is ~60s of captions. The command-line tool resolves the
      // exact segment; doing that here would mean reading the chunk body per hit.
      // One entry per citation: a long page is indexed in parts and every part carries
      // the page's address, so the best-ranked part stands for the page.
      const seen = new Set()
      const byTopic = (pinned[c] || []).map(row => ({
        ...row, board: null, board_slug: null, date: '', kind: 'page', source_url: null,
        start_s: null, chars: 0, rank: -1e9, via: 'topic',
        matched: [...row.snippet.matchAll(/‹([^›]+)›/g)].map(m => m[1].toLowerCase())
          .filter((w, i, a) => a.indexOf(w) === i),
      }))
      for (const row of byTopic) seen.add(row.cite_url)
      results[c] = byTopic.concat((r.results || []).filter(row => {
        if (seen.has(row.cite_url)) return false
        seen.add(row.cite_url)
        return true
      }).map(row => ({
        ...row,
        via: 'text',
        matched: [...row.snippet.matchAll(/‹([^›]+)›/g)].map(m => m[1].toLowerCase())
          .filter((w, i, a) => a.indexOf(w) === i),
      })))
      if (byTopic.length) counts[c].hits += byTopic.filter(t => !(r.results || []).some(x => x.cite_url === t.cite_url)).length
    }
  } catch (e) {
    return json({
      error: 'query_failed',
      message: String(e && e.message ? e.message : e),
      hint: 'If this says the daily limit was reached, the index has not gone anywhere: '
        + 'the same corpora are searchable offline with scripts/search_minutes.py in the '
        + 'repository, and every document is at /docs/.',
      q, expression: expr, index,
    }, 503)
  }

  const payload = {
    resource: 'search',
    q,
    expression: expr,
    corpora,
    board: board || null,
    since: since || null,
    perCorpus: PER_CORPUS,
    candidates: CANDIDATES,
    ranking: `bm25 within the first ${CANDIDATES} matching rows of each corpus; a count of ${CANDIDATES}+ means the cap was hit and ranking is local to those rows`,
    index,
    counts,
    results,
    rowsRead,
    ms: Date.now() - started,
    cite: 'A transcript hit locates a moment in a recording. Cite the video at its timestamp, never as a document, and never quote a figure from a caption as the record.',
  }
  const res = json(payload, 200, { 'cache-control': `public, max-age=${CACHE_SECONDS}`, 'x-query-cache': 'miss' })
  context.waitUntil(cache.put(cacheKey, res.clone()))
  return res
}

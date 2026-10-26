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
 * THE ORDER IS A PARAMETER, AND IT IS PER CORPUS -- AND IT COSTS NOTHING
 *
 *     &sort=newest     newest first, in the corpora whose rows carry a date
 *     &sort=relevance  bm25 everywhere (the default, and what every caller got before)
 *
 * `sort=newest` changes ONLY the OUTER `ORDER BY` of the query that was already running:
 * the inner subselect still reads the same `LIMIT CANDIDATES` rows, so rows read -- the
 * thing D1 bills and rations -- is identical. Reordering rows already in memory is free.
 *
 * It is applied PER CORPUS because a date is not a thing every corpus has. Measured on the
 * index: 0 of 11,928 `source` rows and 0 of 1,233 `page` rows carry a date, and every row
 * of `minutes`, `recorded` and `transcript` does. So a GLOBAL newest-first would hand back
 * the archive's documents in whatever order an empty date string sorts in, and bury the
 * contract a reader came for under hundreds of recent minutes -- silently, which is the
 * failure mode this endpoint exists to refuse. `sortedBy` in the response names the order
 * each corpus actually came back in, so a caller never has to infer it, and a row with a
 * missing or malformed date sorts LAST within its corpus rather than first.
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
const CORPORA = ['report', 'post', 'page', 'job', 'person', 'recorded', 'source', 'minutes', 'transcript']
/** `report` IS NOT IN THE INDEX. It is the `page` rows whose address is a report in
 *  /data/reports.json, split out at query time. TJ, 11 October 2026: *"Does search not
 *  have a REPORTS category? I'm looking for a particular report but it's buried under all
 *  the minutes and documents."* Reports were `page` rows, ranked against two thousand
 *  board and meeting pages and drawn fifth. Splitting here needs no index rebuild and no
 *  D1 writes; `page` then means every OTHER page on the site. */
const SPLIT_FROM_PAGE = 'report'
let reportUrls = null
async function loadReportUrls(env, request) {
  if (reportUrls) return reportUrls
  try {
    const res = await (env.ASSETS ? env.ASSETS.fetch(new URL('/data/reports.json', request.url))
                                  : fetch(new URL('/data/reports.json', request.url)))
    const d = await res.json()
    reportUrls = [...(d.reports || []), ...(d.pages || [])].map(r => SITE + r.url)
  } catch (e) { reportUrls = [] }
  // THE TOPIC PAGES ARE REPORTS TOO. TJ, 14 October 2026: "I searched for free cash but no
  // report came up" -- five free-cash topics and their hub existed, but this list was only
  // the fourteen long reports, so every hub and topic page ranked as an ordinary `page`
  // under two thousand meeting pages. Every hub and every ready topic in topics.json joins
  // the Reports results.
  try {
    const res = await (env.ASSETS ? env.ASSETS.fetch(new URL('/data/topics.json', request.url))
                                  : fetch(new URL('/data/topics.json', request.url)))
    const t = await res.json()
    const paths = [...(t.categories || []).filter(c => c.ready !== false).map(c => c.path),
                   ...Object.values(t.topics || {}).filter(x => x.ready).map(x => x.path)]
    reportUrls = [...new Set([...reportUrls, ...paths.map(p => SITE + p)])]
  } catch (e) { /* the long reports alone, as before */ }
  return reportUrls
}
const sqlList = urls => urls.map(u => "'" + u.replace(/'/g, "''") + "'").join(',') || "''"
/** The only corpora whose rows carry a date. Measured on the index, not assumed:
 *  every `minutes`, `recorded` and `transcript` row has one, and every `job` row carries
 *  the date SchoolSpring prints as posted; no `source`, `page` or `person` row does. A date
 *  sort is offered for these four and refused for the rest. */
const DATED = ['job', 'minutes', 'recorded', 'transcript']
const PER_CORPUS = 12          // hits returned per corpus, unless the caller asks for more
const PER_CORPUS_MAX = 60      // `per=` -- a thread built from a search wants a timeline, not twelve
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

/** WORD FAMILIES. `custodian` must find `custodial`: TJ, 26 October 2026, searched
 *  `custodian contract` and the meeting that approved it never says either word -- its minutes
 *  say "Custodial MOU" and "the custodial agreement". A starts-with match on `custodian` cannot
 *  reach `custodial`; the shared stem `custod` can. A word of six letters or more loses one
 *  common English ending, and only if five letters remain -- `special` stays `special`, so it
 *  never becomes `spec` and matches `specific`. This is light STEMMING done at query time. */
const ENDING = /(ians|ian|ials|ial|ions|ion|ings|ing|ers|er|ed|es|s)$/
export function family(w) {
  const lw = w.toLowerCase()
  if (!/^\p{L}{6,}$/u.test(lw)) return lw
  const stem = lw.replace(ENDING, '')
  return stem.length >= 5 ? stem : lw
}
const termFor = f => '"' + f + '"' + (/^\p{L}{3,}$/u.test(f) && !SHORT_EXACT.has(f) ? '*' : '')
// Acronyms in the table below match as words, not as starts: `mou*` would reach `mount`.
const SHORT_EXACT = new Set(['mou', 'moa', 'cba'])

/** WORDS THAT MEAN THE SAME THING IN THE TOWN'S RECORDS. Kept small on purpose, and only for
 *  a pairing that has failed a real search: a contract is written up as an AGREEMENT, an MOU
 *  or an MOA far more often than as a contract (the custodians' contract, 29 July 2026, is
 *  "Custodial MOU" on the agenda and "the custodial agreement" in the vote). A group widens
 *  only the WORDS-TOGETHER tier below; it never adds a row on its own. */
const SAME = [['contract', 'agreement', 'mou', 'moa', 'cba', 'memorandum']]
function alternatives(w) {
  const f = family(w)
  for (const g of SAME) if (g.some(x => family(x) === f)) return [...new Set(g.map(family))]
  return [f]
}

/** THE WORDS-TOGETHER TIER: an exact phrase, or every word -- in its family or one of its
 *  same-meaning alternatives -- within five words of the others. A row matching this is
 *  ranked above every row that merely holds the words somewhere, IN BOTH ORDERS: newest-first
 *  used to throw proximity away entirely, so nine pages of minutes with `custodian` on page
 *  three and `Contracted Services` on page two sorted level with the passage that approved
 *  the contract. Two to four plain words only; '' otherwise. */
export function nearExpression(q) {
  if (/"/.test(q)) return ''
  const words = (q.replace(/[’']s\b/g, '').match(/[\p{L}\p{N}$%.-]+/gu) || [])
    .map(w => w.replace(/[.,]+$/, '')).filter(Boolean)
  if (words.length < 2 || words.length > 4) return ''
  let combos = [[]]
  for (const w of words) {
    const alts = /^\p{L}+$/u.test(w) ? alternatives(w) : [w.toLowerCase()]
    combos = combos.flatMap(c => alts.map(a => [...c, a]))
    if (combos.length > 12) combos = combos.slice(0, 12)
  }
  const near = combos.map(c => `NEAR(${c.map(termFor).join(' ')}, 5)`)
  return [phraseOf(q), ...near].join(' OR ')
}

/** THE EXACT WORDS, IN ORDER -- the top tier. A synonym widens what is found; it must not
 *  outrank what was typed. Without this, `custodian contract` put the Conservation
 *  Commission's "custodial agreement" (a caretaker's licence on Hollis Road) above the
 *  School Committee recording that says "the custodian contract", because it was newer. */
export function phraseOf(q) {
  const words = (q.replace(/[’']s\b/g, '').match(/[\p{L}\p{N}$%.-]+/gu) || [])
    .map(w => w.replace(/[.,]+$/, '')).filter(Boolean)
  return words.length > 1 && !/"/.test(q) ? `"${words.join(' ')}"` : ''
}

/** A user's words, as an FTS5 expression that cannot throw -- and that finds what a person
 *  means rather than only what they typed.
 *
 *  TJ, 10 October 2026, after `kim gauvin` found nothing because the name is Kimberly: *"i
 *  wanted a more flexible non-full word search match"* and *"the ability to combine words and
 *  check combinations together as a more direct match"*. Three things, in one expression:
 *
 *  1. STARTS-WITH MATCHING, ALWAYS. Every typed word of three letters or more is a PREFIX:
 *     `kim` -> `"kim"*`, which reaches Kimberly; `transp` reaches transportation. One- and
 *     two-letter words and numbers stay exact: `"ab"*` would match half the index and read it
 *     all, which is what D1 bills. A quoted phrase stays exactly as typed.
 *  2. ALL THE WORDS MUST APPEAR -- in any order, anywhere in the row. That is the match.
 *  3. WORDS TOGETHER RANK FIRST. The same words are also offered as an EXACT PHRASE and as a
 *     NEAR group (within three words of each other), OR'd with the plain match. A row matching
 *     only the plain group still qualifies; a row where the words sit together matches the
 *     NEAR group too, and FTS5's bm25 scores every phrase it matched, so it rises -- measured
 *     on the local index: for `line item transfer` the Finance Committee agenda with the words
 *     scattered dropped out of the top six and School Committee minutes rose. The term for
 *     this is PROXIMITY RANKING. It costs no second query.
 */
export function ftsExpression(q, { together = false } = {}) {
  const terms = [], words = []
  let quoted = false
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
    if (m[1] !== undefined) { terms.push('"' + clean + '"'); quoted = true; continue }
    for (const w of clean.split(' ')) {
      if (!w) continue
      words.push(w)
      terms.push(termFor(family(w)))
    }
  }
  if (!terms.length) return ''
  const all = terms.join(' ')
  // One word, or a reader who quoted something: they said exactly what they meant.
  if (terms.length < 2 || terms.length > 6 || quoted) return all
  // TOGETHER: only rows where the words sit within a few words of each other. A thread built
  // from a search uses this -- `turkey hill roof` otherwise pulled in every set of minutes
  // that said Turkey Hill on page one and roof on page four (measured, 10 October 2026).
  if (together) return `"${words.join(' ')}" OR NEAR(${all}, 5)`
  return `"${words.join(' ')}" OR NEAR(${all}, 3) OR (${all})`
}

export async function onRequest(context) {
  const { request, env } = context
  if (request.method === 'OPTIONS') return new Response(null, { status: 204, headers: HEADERS })
  if (request.method !== 'GET') return json({ error: 'method_not_allowed' }, 405)
  const db = env.SEARCH
  if (!db) return json({ error: 'unavailable', message: 'The search database is not bound to this deployment.' }, 503)

  const url = new URL(request.url)
  const q = (url.searchParams.get('q') || '').trim().slice(0, MAX_Q)
  // The query's plain words, for ranking report TITLES (see the report ORDER BY). Letters
  // and digits only, so they can be written into SQL as literals with nothing to escape.
  const titleTerms = [...new Set(q.toLowerCase().match(/[a-z0-9]+/g) || [])].filter(w => w.length > 1).slice(0, 6)
  const corpusParam = (url.searchParams.get('corpus') || '').split(',').map(s => s.trim()).filter(Boolean)
  const corpora = corpusParam.length ? CORPORA.filter(c => corpusParam.includes(c)) : CORPORA
  const board = (url.searchParams.get('board') || '').trim().slice(0, 80)
  const since = (url.searchParams.get('since') || '').trim().slice(0, 10)
  // Default `relevance`, so a caller that does not ask gets exactly what it got before.
  const sort = (url.searchParams.get('sort') || '').trim() === 'newest' ? 'newest' : 'relevance'
  // HOW MANY PER KIND. The search page wants the best twelve; a thread built from a search
  // (pages/Threads, DynamicThread) wants every dated mention it can lay on a timeline. The
  // rows READ are bounded by CANDIDATES either way -- this changes how many come back, not
  // how many are scanned, which is what D1 bills.
  const per = Math.max(1, Math.min(PER_CORPUS_MAX, parseInt(url.searchParams.get('per') || '', 10) || PER_CORPUS))
  // `match=together` -- see ftsExpression. Default unchanged.
  const together = (url.searchParams.get('match') || '').trim() === 'together'
  // THE MATCH: every word somewhere, OR the words together (nearExpression), so a passage
  // that says `custodial agreement` qualifies for `custodian contract` even though the plain
  // match cannot reach it. `near` also decides the ranking tier and the snippet below.
  const near = together ? '' : nearExpression(q)
  const plain = ftsExpression(q, { together })
  const expr = plain && near ? `(${plain}) OR (${near})` : plain

  // The index's own statement of what it holds, written by the push. Read, never counted
  // here: a COUNT(*) per corpus would read every row on every call.
  const metaRows = (await db.prepare('SELECT k, v FROM build_meta').all()).results || []
  const meta = Object.fromEntries(metaRows.map(r => [r.k, r.v]))
  const reports = await loadReportUrls(env, request)
  const inReports = new Set(reports)
  const holds = Object.fromEntries(CORPORA.map(c => [c, Number(meta['rows:' + c] || 0)]))
  holds[SPLIT_FROM_PAGE] = reports.length   // reports, not rows: a long one is indexed in parts
  const index = {
    built: meta.built || null,
    holds,
    note: 'minutes = documents the town published; transcript = our machine captions of '
      + 'recordings, a finding aid cited to the video at a timestamp; recorded = our minutes '
      + 'of a recording; source = pages of '
      + 'archive documents; page = this site; post = published posts; job = job postings, the '
      + 'town\'s (its own job board) and the school district\'s (SchoolSpring); person = a name on the org '
      + 'charts, with every role and year it appears under (the same name is not proven to '
      + 'be one person).',
  }

  if (!expr) return json({ resource: 'search', q, expression: '', index, results: {}, counts: {} })

  const cache = caches.default
  const cacheKey = new Request(`https://search.invalid/${encodeURIComponent(expr)}|${corpora.join(',')}|${board}|${since}|${sort}|${per}`, { method: 'GET' })
  const hit = await cache.match(cacheKey)
  if (hit) {
    return new Response(await hit.text(), { headers: { ...HEADERS, 'cache-control': `public, max-age=${CACHE_SECONDS}`, 'x-query-cache': 'hit' } })
  }

  const started = Date.now()
  let rowsRead = 0
  const results = {}
  const counts = {}
  const sortedBy = {}
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
    for (const row of a.results || []) {
      const c = row.corpus === 'page' && inReports.has(row.cite_url) ? SPLIT_FROM_PAGE : row.corpus
      ;(pinned[c] ||= []).push(row)
    }
  } catch (e) {
    // No affinity table yet, or a bad expression: the text search still answers.
  }

  try {
    // EVERY KIND AT ONCE. This was a `for ... await` loop: two queries per kind, one kind
    // after another, so eight kinds were sixteen round trips end to end, and starts-with
    // matching (10 October 2026) made each of them heavier -- TJ: "search is SLOW". In
    // parallel the wait is the slowest kind, not the sum. Rows READ are identical, which is
    // what D1 bills; only the waiting changes.
    await Promise.all(corpora.map(async c => {
      // The outer ORDER BY, over rows the subselect has already read. A row whose date is
      // missing, empty OR NOT AN ISO DATE goes LAST, and the test is the shape of the
      // string rather than its emptiness. '' sorts before every real date, so a bare DESC
      // would put undated rows on TOP of a newest-first list; and anything non-numeric --
      // 'undated', 'n.d.' -- sorts AFTER '2026', so emptiness alone is not enough. Every
      // dated row in the index today is ISO (checked: 0 of 290,720 are not), which is
      // exactly why a guard is cheap now and would be archaeology later.
      const byDate = sort === 'newest' && DATED.includes(c)
      sortedBy[c] = byDate ? 'date' : 'rank'
      // `together`: 2 = the exact words typed, 1 = together in a family or synonym form,
      // 0 = somewhere in the row (nearExpression). It LEADS a relevance order and only breaks
      // ties in a date order: newest first means newest. TJ, 26 October 2026: "the sort is
      // 'newest first' so why would 7-29 EVER show up before 10-7?"
      const order = byDate
        ? "ORDER BY (date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]') DESC, date DESC, together DESC, rank"
        : 'ORDER BY together DESC, ' + (c === SPLIT_FROM_PAGE && titleTerms.length
          // A REPORT TITLED WITH YOUR WORDS COMES FIRST. "free cash" ranked /this-week and
          // /meeting-minutes -- long pages that mention it in passing -- above the five
          // pages named for it. Titles hit by more of the words first, then bm25.
          ? `(${titleTerms.map(w => `(instr(lower(title), '${w}') > 0)`).join(' + ')}) DESC, rank`
          : 'rank')
      // `report` and `page` both read the page rows; the address list decides which side.
      const real = c === SPLIT_FROM_PAGE ? 'page' : c
      const split = c === SPLIT_FROM_PAGE ? ` AND cite_url IN (${sqlList(reports)})`
        : c === 'page' ? ` AND cite_url NOT IN (${sqlList(reports)})` : ''
      const sql = `
        SELECT * FROM (
          SELECT rowid AS id, corpus, doc_key, title, board, board_slug, date, kind, cite_url, source_url,
                 start_s, chars, bm25(search) AS rank,
                 ${near ? `((rowid IN (SELECT rowid FROM search WHERE search MATCH ?3 AND corpus = ?2))
                   + (rowid IN (SELECT rowid FROM search WHERE search MATCH ?4 AND corpus = ?2)))` : '0'} AS together,
                 snippet(search, 0, '‹', '›', '…', 20) AS snippet
          FROM search WHERE search MATCH ?1 AND corpus = ?2${split}${where}
          LIMIT ${CANDIDATES}
        ) ${order} LIMIT ${per}`
      // A report indexed in parts would count once per part; count ADDRESSES for reports.
      const countSql = c === SPLIT_FROM_PAGE
        ? `SELECT COUNT(DISTINCT cite_url) AS n FROM (SELECT cite_url FROM search WHERE search MATCH ?1 AND corpus = ?2${split}${where} LIMIT ${CANDIDATES})`
        : `SELECT COUNT(*) AS n FROM (SELECT rowid FROM search WHERE search MATCH ?1 AND corpus = ?2${split}${where} LIMIT ${CANDIDATES})`
      const [r, n] = await Promise.all([
        db.prepare(sql).bind(expr, real, ...(near ? [near, phraseOf(q)] : []), ...binds).all(),
        db.prepare(countSql).bind(expr, real, ...binds).all(),
      ])
      rowsRead += (r.meta && r.meta.rows_read || 0) + (n.meta && n.meta.rows_read || 0)
      // THE PASSAGE WHERE THE WORDS MEET. snippet() picks its fragment against the whole
      // expression, so a row that qualified on the words together still showed whichever
      // fragment held the most single words -- the 29 July minutes opened on "Contracted
      // Services" instead of the custodial agreement. Re-cut against the together tier, for
      // the rows that matched it. A rowid lookup per returned row: cheap.
      const close = (r.results || []).filter(x => x.together).map(x => Number(x.id)).filter(Number.isInteger)
      if (near && close.length) {
        const s = await db.prepare(`SELECT rowid AS id, snippet(search, 0, '‹', '›', '…', 20) AS snippet
          FROM search WHERE search MATCH ?1 AND rowid IN (${close.join(',')})`).bind(near).all()
        rowsRead += (s.meta && s.meta.rows_read) || 0
        const cut = new Map((s.results || []).map(x => [Number(x.id), x.snippet]))
        for (const x of r.results) if (cut.has(Number(x.id))) x.snippet = cut.get(Number(x.id))
      }
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
    }))
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
    sort,
    sortedBy,
    dated: DATED,
    perCorpus: per,
    candidates: CANDIDATES,
    ranking: `${sort === 'newest' ? 'newest first in ' + DATED.join(', ') + ' (the exact words, then the words together, breaking ties) and ' : ''}${near ? 'the exact words first, then the words together (in a family or same-meaning form), then the words anywhere, then bm25' : 'bm25'}${sort === 'newest' ? ' in the rest' : ''}, within the first ${CANDIDATES} matching rows of each corpus; a count of ${CANDIDATES}+ means the cap was hit and the order is local to those rows`,
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

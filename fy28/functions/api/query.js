/**
 * Ask the database a question, instead of downloading it.
 *
 * WHY THIS EXISTS
 *
 * Everything else under /api is a static JSON file, written at build time. That is right
 * for a known question and wrong for an unknown one. An assistant asked how many
 * kindergarten paraprofessionals the town printed in each year had three routes and all
 * three failed: the 435KB CSV truncated at 40% with no marker saying so; the per-year API
 * files meant fifteen fetches to count three numbers; and the 16MB SQLite download was
 * larger than anything it could hold. It wanted twelve rows and there was no way to ask
 * for twelve rows.
 *
 *     POST /api/query   {"sql": "SELECT ...", "params": [...]}
 *     GET  /api/query?sql=SELECT%20...
 *
 * READ-ONLY, AND ENFORCED RATHER THAN REQUESTED
 *
 * The binding is D1 with a database that holds nothing but published public records, so
 * the risk here is not disclosure -- every row is already downloadable -- it is somebody
 * spending our compute or getting a confidently wrong answer. So:
 *
 *   * one statement, and it must begin SELECT or WITH
 *   * no semicolons beyond a single trailing one: no statement stacking
 *   * PRAGMA, ATTACH, and the write verbs are refused by name as well as by the prefix
 *     rule, because defence that depends on one test passing is not defence
 *   * a LIMIT is imposed if the caller did not give one, and capped if they did
 *   * parameters are bound, never interpolated
 *
 * PROVENANCE, WHICH IS THE PART THAT MATTERS
 *
 * Every other endpoint returns the documents its rows came from. A SQL result cannot do
 * that automatically -- an aggregate has no doc_id -- and the honest thing is to SAY so
 * rather than return a figure with no address. So every response carries a `provenance`
 * block that either names the documents, or states in words that this query cannot be
 * traced and how to write one that can. `dataset_document` is in the database for exactly
 * this, and the message names it.
 *
 * A figure with no route back to a document is the thing this project exists not to
 * publish. An endpoint that can produce one has to admit when it has.
 */

import { ROWS } from './_tablesizes.js'

const SITE = 'https://lunenburgbudgetproject.org'
const MAX_ROWS = 1000
const MAX_SQL = 4000
// How long an identical query is served from cache.
//
// COST CONTROL, and the cheapest kind there is. The billable unit on D1 is ROWS READ, and
// a public endpoint answering the same question repeatedly pays for it every time. The
// data changes only when the database is redeployed, so two identical queries an hour
// apart must return the same rows -- there is nothing to be gained by asking twice.
//
// On the free plan this is availability rather than money: D1 stops answering at 5 million
// rows read in a day and starts again tomorrow, it does not bill. Caching is what keeps a
// day's budget from being spent on repeats.
const CACHE_SECONDS = 600

// The most rows one query may be ESTIMATED to read.
//
// D1 bills on rows read and caps nothing: the free plan stops at 5 million a day. One
// join across two large tables here reads 19,006, so 263 of them would take the endpoint
// dark until tomorrow. Cloudflare offers no spending or usage cap, so this is ours.
//
// 250,000 leaves room for about twenty of the heaviest legitimate queries a day and
// refuses the shapes that could not be legitimate. It is an ESTIMATE from table sizes,
// not a measurement -- a real cost is only known after the fact, and `rowsRead` reports
// that -- so it errs toward allowing rather than refusing.
const MAX_ESTIMATED_ROWS = 250000

/**
 * An upper estimate of what a statement will read, from the tables it names.
 *
 * Nothing can know the true cost before running it: an index may make a scan cheap, and a
 * WHERE may cut it to nothing. What IS known at build time is the row count of every
 * table, which bounds the worst case -- a full scan of each table named, multiplied for
 * each join, because a join can in principle pair every row with every row.
 */
function estimate(sql) {
  const names = [...sql.matchAll(/\b(?:from|join)\s+["'`]?([a-z_][a-z0-9_]*)["'`]?/gi)]
    .map(m => m[1].toLowerCase())
  if (!names.length) return { rows: 0, tables: [] }
  const known = names.filter(n => n in ROWS)
  if (!known.length) return { rows: 0, tables: [] }
  // First table scanned; each further table is a join, so multiply -- capped so a
  // three-way join of small tables is not refused for arithmetic reasons alone.
  let rows = ROWS[known[0]]
  for (const n of known.slice(1)) rows = Math.min(rows * Math.max(ROWS[n], 1), 1e9)
  return { rows, tables: known }
}

const FORBIDDEN =
  /\b(insert|update|delete|drop|alter|create|replace|attach|detach|pragma|vacuum|reindex|analyze)\b/i

const HEADERS = {
  'content-type': 'application/json; charset=utf-8',
  'access-control-allow-origin': '*',
  'access-control-allow-methods': 'GET, POST, OPTIONS',
  'access-control-allow-headers': 'content-type',
  // A query is computed per request, so it is never cached.
  'cache-control': 'no-store',
}

const json = (body, status = 200) =>
  new Response(JSON.stringify(body, null, 1) + '\n', { status, headers: HEADERS })

/** Same, with extra headers -- used for Retry-After on a 429. */
const jsonWith = (extra, body, status = 200) =>
  new Response(JSON.stringify(body, null, 1) + '\n',
    { status, headers: { ...HEADERS, ...extra } })

const HELP = {
  endpoint: '/api/query',
  how: 'GET /api/query?sql=<url-encoded SQL> — works with any fetch tool, including one '
    + 'that cannot POST. Or POST {"sql": "SELECT ...", "params": []} if you can.',
  limits: {
    rate: 'About ten requests per ten seconds per IP. A fourth is refused by the edge with '
      + 'HTTP 429 and a seventeen-byte body reading `error code: 1015` — that is a rate '
      + 'limit, not an error and not a gap in the data. Wait ten seconds.',
    daily: 'This endpoint computes on request and has a daily usage limit. Static files '
      + 'have none.',
    unlimited: `${SITE}/api/tables and everything it lists are static and never limited.`,
  },
  rules: [
    'One statement. It must start with SELECT or WITH.',
    `A LIMIT is added if you omit one, and capped at ${MAX_ROWS} rows.`,
    'Use ? placeholders and pass `params`; values are bound, never interpolated.',
  ],
  readFirst: 'https://lunenburgbudgetproject.org/api/schema',
  tables: 'https://lunenburgbudgetproject.org/api/tables',
  example: {
    sql: "SELECT fy, COUNT(*) AS paras FROM staff_roster_entries "
      + "WHERE position = 'Paraprofessional' AND grade_or_dept LIKE ? "
      + 'GROUP BY fy ORDER BY fy',
    params: ['%indergarten%'],
  },
  provenance:
    'Join `dataset_document` to keep the address of the document a row came from: '
    + "JOIN dataset_document d ON d.dataset = 'report-appropriations' "
    + 'AND d.edition = r.edition. Without it a result has no route back to a source, '
    + 'and this endpoint will say so.',
}

/** Reject anything that is not a single read. */
function refuse(sql) {
  if (!sql) return 'No `sql` given.'
  if (sql.length > MAX_SQL) return `Query is ${sql.length} characters; the limit is ${MAX_SQL}.`
  const bare = sql.trim().replace(/;\s*$/, '')
  if (bare.includes(';')) return 'One statement only — no semicolons except a trailing one.'
  if (!/^\s*(select|with)\b/i.test(bare)) return 'Read-only: a query must start with SELECT or WITH.'
  const bad = bare.match(FORBIDDEN)
  if (bad) return `Read-only: \`${bad[0]}\` is not allowed.`
  return null
}

/** Impose a bound the caller may not have. */
function bounded(sql) {
  const bare = sql.trim().replace(/;\s*$/, '')
  const m = bare.match(/\blimit\s+(\d+)\s*$/i)
  if (!m) return { sql: `${bare} LIMIT ${MAX_ROWS}`, imposed: MAX_ROWS }
  const asked = parseInt(m[1], 10)
  if (asked <= MAX_ROWS) return { sql: bare, imposed: null }
  return { sql: bare.replace(/\blimit\s+\d+\s*$/i, `LIMIT ${MAX_ROWS}`), imposed: MAX_ROWS }
}

/** The documents behind a result, or an honest statement that there are none. */
async function provenanceFor(db, rows) {
  const ids = [...new Set(rows.flatMap(r =>
    ['doc_id', 'document'].map(k => r[k]).filter(v => typeof v === 'string' && v)))]
  if (!ids.length) {
    return {
      documents: [],
      warning:
        'This result carries no document reference, so no figure in it can be traced to '
        + 'a source from this response alone. That is a property of the query, not of the '
        + 'archive: select `doc_id`, or join `dataset_document` on (dataset, edition), and '
        + 'the address and sha256 of every source document come back with the rows.',
    }
  }
  // Resolve by doc_id OR by bare filename, because the two do not agree.
  //
  // `document.doc_id` is an archive path; the tables that cite a document mostly carry
  // the filename it was read under. `build_api.py` learned this the hard way -- "all 20
  // of them resolve by basename and none resolves exactly, so a straight IN () lookup
  // returned NOTHING and every per-line file shipped with an empty provenance block, the
  // one guarantee this API makes, quietly broken" -- and this code was written without
  // inheriting that. It shipped empty on its first real test.
  //
  // The document table is 600 rows, so it is read whole and indexed here rather than
  // attempting the join in SQL.
  const all = await db.prepare(
    `SELECT doc_id, path, url, local_sha256 AS sha256, basis, copy_state
     FROM document`).all()
  const index = new Map()
  for (const r of all.results || []) {
    index.set(r.doc_id, r)
    const base = String(r.path || r.doc_id).split('/').pop()
    if (base && !index.has(base)) index.set(base, r)
  }
  const results = []
  const unresolved = []
  for (const id of ids) {
    const hit = index.get(id)
    if (hit) results.push({ ...hit, cited_as: id })
    else unresolved.push(id)
  }
  const out = { documents: results, count: results.length }
  if (unresolved.length) {
    out.unresolved = unresolved
    out.warning = 'These rows cite a document with no row in `document`, so no address '
      + 'can be given for them. Treat any figure resting on them as uncheckable.'
  }
  return out
}

export async function onRequest(context) {
  const { request, env } = context
  const db = env.DB

  if (request.method === 'OPTIONS') return new Response(null, { status: 204, headers: HEADERS })
  if (!db) {
    return json({ error: 'unavailable', message: 'The query database is not bound to this deployment.', ...HELP }, 503)
  }

  let sql = null
  let params = []
  if (request.method === 'GET') {
    sql = new URL(request.url).searchParams.get('sql')
    if (!sql) return json(HELP)
  } else if (request.method === 'POST') {
    let body
    try {
      body = await request.json()
    } catch {
      return json({ error: 'bad_request', message: 'Body must be JSON.', ...HELP }, 400)
    }
    sql = body && body.sql
    params = (body && body.params) || []
    if (!Array.isArray(params)) {
      return json({ error: 'bad_request', message: '`params` must be an array.', ...HELP }, 400)
    }
  } else {
    return json({ error: 'method_not_allowed', ...HELP }, 405)
  }

  const why = refuse(sql)
  if (why) return json({ error: 'refused', message: why, ...HELP }, 400)

  const { sql: finalSql, imposed } = bounded(sql)

  // Refuse what we can see will be too expensive, BEFORE reading anything.
  const cost = estimate(finalSql)
  if (cost.rows > MAX_ESTIMATED_ROWS) {
    return json({
      error: 'too_expensive',
      message: `This query could read about ${cost.rows.toLocaleString()} rows, and the `
        + `limit is ${MAX_ESTIMATED_ROWS.toLocaleString()}. It is an estimate from the `
        + `size of the tables named (${cost.tables.join(', ')}), so it may be pessimistic `
        + `— but D1 charges for rows read and caps nothing, and one endpoint should not be `
        + `able to spend a whole day's budget.`,
      fix: 'Add a WHERE that narrows it, query one table at a time, or fetch the '
        + 'pre-built per-year files instead — https://lunenburgbudgetproject.org/api/tables '
        + 'lists every dataset with the years it covers.',
      estimatedRows: cost.rows,
      limit: MAX_ESTIMATED_ROWS,
    }, 400)
  }

  // Identical question, identical answer: serve it from the edge and read no rows.
  // Keyed on the statement and its parameters, on a URL of our own making so that a POST
  // and a GET of the same query share one entry.
  const cache = caches.default
  const cacheKey = new Request(
    `https://query.invalid/${encodeURIComponent(finalSql)}|${encodeURIComponent(JSON.stringify(params))}`,
    { method: 'GET' })
  const hit = await cache.match(cacheKey)
  if (hit) {
    const body = await hit.text()
    return new Response(body, {
      headers: { ...HEADERS, 'cache-control': `public, max-age=${CACHE_SECONDS}`,
                 'x-query-cache': 'hit' },
    })
  }

  const started = Date.now()
  let out
  try {
    out = await db.prepare(finalSql).bind(...params).all()
  } catch (e) {
    const detail = String(e && e.message ? e.message : e)
    // A LIMIT IS NOT AN ABSENCE, AND MUST NOT READ LIKE ONE.
    //
    // D1's free plan stops at 5 million rows read a day and then refuses queries until
    // tomorrow. That is an acceptable outcome -- but only if the caller understands what
    // happened. An assistant handed a bare "query failed" reports that this site cannot
    // answer, or worse that the data does not exist, and a reader is told something false
    // about a public archive because of a usage counter.
    //
    // Every failure here therefore carries the routes that still work. The data has not
    // gone anywhere: it is the same rows, published as static files, which no quota
    // touches.
    const quota = /limit|exceeded|quota|too many|overloaded|429/i.test(detail)
    const fallback = {
      theDataIsStillHere:
        'Nothing is missing. This endpoint computes an answer on request and has a daily '
        + 'usage limit; the same rows are published as static files that no limit '
        + 'touches.',
      instead: {
        everyDataset: `${SITE}/api/tables`,
        oneTablePerYear: `${SITE}/api/<table>/<fiscal year> — e.g. `
          + `${SITE}/api/staff_roster_entries/2022`,
        workedExamples: `${SITE}/api/questions`,
        theWholeDatabase: `${SITE}/data/lunenburg.db`,
        ifThisHostIsBlocked:
          'https://raw.githubusercontent.com/tjloughlin16/lunenburgbudgetapp/main/'
          + 'fy28/public/api/tables.json — every static file here is mirrored on GitHub.',
      },
      pleaseTellTheReader:
        'If you are answering somebody, say the query API was unavailable rather than '
        + 'that the archive lacks the data. It does not.',
    }
    if (quota) {
      // Retry-After, because a 429 without one tells a caller to stop and not when to
      // start. The daily counter resets at UTC midnight, so that is what is offered --
      // an honest number rather than a guess at a few seconds.
      const now = new Date()
      const reset = Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate() + 1)
      const seconds = Math.max(60, Math.round((reset - now.getTime()) / 1000))
      return jsonWith({ 'retry-after': String(seconds) }, {
        error: 'daily_limit_reached',
        retryAfterSeconds: seconds,
        retryAt: new Date(reset).toISOString(),
        message: 'The query API has reached its daily usage limit and will answer again '
          + 'tomorrow. THIS IS A LIMIT ON THIS ENDPOINT, NOT A GAP IN THE ARCHIVE.',
        detail,
        ...fallback,
      }, 429)
    }
    return json({
      error: 'query_failed',
      message: detail,
      sql: finalSql,
      hint: 'Fetch /api/schema for the grain of every table and the ways to get a '
        + 'confident wrong answer out of this data. If the message names a missing table, '
        + 'check /api/tables for its real name.',
      ...fallback,
    }, 400)
  }

  const rows = out.results || []
  const payload = {
    resource: 'query',
    sql: finalSql,
    params,
    rowCount: rows.length,
    truncated: imposed !== null && rows.length === imposed,
    limitImposed: imposed,
    ms: Date.now() - started,
    // What this query cost, stated. Rows READ is the billable unit on D1 and it is not
    // the number of rows you got back: a COUNT over 4,665 rows returns one row and reads
    // all of them. Published so an expensive query is visible as expensive.
    rowsRead: (out.meta && out.meta.rows_read) ?? null,
    estimatedRows: cost.rows,
    provenance: await provenanceFor(db, rows),
    readFirst: 'https://lunenburgbudgetproject.org/api/schema',
    rows,
  }
  const body = JSON.stringify(payload, null, 1) + '\n'
  const res = new Response(body, {
    headers: { ...HEADERS, 'cache-control': `public, max-age=${CACHE_SECONDS}`,
               'x-query-cache': 'miss' },
  })
  context.waitUntil(cache.put(cacheKey, res.clone()))
  return res
}

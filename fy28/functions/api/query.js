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

const MAX_ROWS = 1000
const MAX_SQL = 4000

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

const HELP = {
  endpoint: '/api/query',
  how: 'GET /api/query?sql=<url-encoded SQL> — works with any fetch tool, including one '
    + 'that cannot POST. Or POST {"sql": "SELECT ...", "params": []} if you can.',
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
  const started = Date.now()
  let out
  try {
    out = await db.prepare(finalSql).bind(...params).all()
  } catch (e) {
    return json({
      error: 'query_failed',
      message: String(e && e.message ? e.message : e),
      sql: finalSql,
      hint: 'Fetch /api/schema for the grain of every table and the ways to get a '
        + 'confident wrong answer out of this data.',
    }, 400)
  }

  const rows = out.results || []
  return json({
    resource: 'query',
    sql: finalSql,
    params,
    rowCount: rows.length,
    truncated: imposed !== null && rows.length === imposed,
    limitImposed: imposed,
    ms: Date.now() - started,
    provenance: await provenanceFor(db, rows),
    readFirst: 'https://lunenburgbudgetproject.org/api/schema',
    rows,
  })
}

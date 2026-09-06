/**
 * The rules that make a wrong query impossible, shared by every tool.
 *
 * These are the same guards `fy28/functions/api/query.js` applies, for the same reasons,
 * and they are duplicated deliberately: two endpoints onto one database that disagreed
 * about what is allowed would be worse than a little repetition.
 */
export const MAX_ROWS = 1000
export const MAX_ESTIMATED_ROWS = 250000

const FORBIDDEN =
  /\b(insert|update|delete|drop|alter|create|replace|attach|detach|pragma|vacuum|reindex|analyze)\b/i

/** Why this statement is not allowed, or null. */
export function refuse(sql: string): string | null {
  if (!sql) return 'No SQL given.'
  if (sql.length > 4000) return `Query is ${sql.length} characters; the limit is 4000.`
  const bare = sql.trim().replace(/;\s*$/, '')
  if (bare.includes(';')) return 'One statement only — no semicolons except a trailing one.'
  if (!/^\s*(select|with)\b/i.test(bare)) return 'Read-only: a query must start with SELECT or WITH.'
  const bad = bare.match(FORBIDDEN)
  if (bad) return `Read-only: \`${bad[0]}\` is not allowed.`
  return null
}

/** Impose a bound the caller may not have given. */
export function bounded(sql: string): string {
  const bare = sql.trim().replace(/;\s*$/, '')
  const m = bare.match(/\blimit\s+(\d+)\s*$/i)
  if (!m) return `${bare} LIMIT ${MAX_ROWS}`
  return parseInt(m[1], 10) <= MAX_ROWS
    ? bare
    : bare.replace(/\blimit\s+\d+\s*$/i, `LIMIT ${MAX_ROWS}`)
}

/**
 * The documents a result rests on, or an honest statement that it has none.
 *
 * Every tool returns this. A figure with no route back to a document is the thing this
 * project exists not to publish, and an answer that cannot be checked should say so
 * rather than look complete.
 */
export async function provenance(db: D1Database, rows: Record<string, unknown>[]) {
  const ids = [...new Set(rows.flatMap(r =>
    ['doc_id', 'document'].map(k => r[k]).filter(v => typeof v === 'string' && v)))] as string[]
  if (!ids.length) {
    return {
      documents: [],
      note: 'This result carries no document reference, so nothing in it can be traced to '
        + 'a source from this answer alone. Select doc_id, or join dataset_document on '
        + '(dataset, edition), if the figure is one somebody will want to check.',
    }
  }
  const all = await db.prepare(
    'SELECT doc_id, path, url, local_sha256 AS sha256, basis FROM document').all()
  const index = new Map<string, unknown>()
  for (const r of (all.results ?? []) as Record<string, string>[]) {
    index.set(r.doc_id, r)
    const base = String(r.path ?? r.doc_id).split('/').pop()
    if (base && !index.has(base)) index.set(base, r)
  }
  const found = ids.map(i => index.get(i)).filter(Boolean)
  return { documents: found, count: found.length }
}

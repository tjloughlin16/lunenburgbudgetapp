/** /api/search ON THE DEV SERVER, run through the REAL Pages Function.
 *
 *  Why this exists. `/api/search` is a Cloudflare Pages Function bound to the D1 database
 *  `lunenburg-search`. Under `vite` there is no Function and no binding, so the search
 *  page's fetch came back as the site's own HTML -- the exact failure its retry loop
 *  apologises for -- and the one page on this site that CANNOT be judged by reading its
 *  source was the one page nobody could open locally. Rule: do not report that a filter
 *  works; use it.
 *
 *  Why it imports the Function rather than reimplementing it. The ranking, the candidate
 *  cap, the FTS expression rewrite and the per-corpus counts are the thing under test. A
 *  second copy of them here would make the dev server a different search engine from the
 *  live one, which is worse than having none. So this is a SHIM, not a server: ~40 lines
 *  of D1's `prepare/bind/all` over the local `sources/data/search-fts.db`, opened
 *  READ-ONLY, plus a no-op `caches` because Workers has one and node does not.
 *
 *  What it is not. It contributes nothing to a build -- `apply: 'serve'`, no transform, no
 *  bundle hook -- so `npm run build` cannot emit it even by accident, the same trade
 *  `devOnlyBlogPreview` already makes in vite.config.ts.
 *
 *  AND IT IS THE LOCAL INDEX, WHICH IS NOT THE LIVE ONE. The local db is rebuilt by
 *  `scripts/build_search_index.py` and pushed to D1 separately, so a row added to
 *  `search-affinity.csv` answers here before it answers in production. Read a count off
 *  this and you are reading this checkout, never the archive -- the same warning
 *  `archive_storage.incomplete()` exists for.
 */
import { DatabaseSync } from 'node:sqlite'
import { existsSync } from 'node:fs'
import { join } from 'node:path'
import { pathToFileURL } from 'node:url'
import type { Plugin } from 'vite'

/** D1's surface, as much of it as functions/api/search.js actually uses. */
function d1(dbPath: string) {
  const db = new DatabaseSync(dbPath, { readOnly: true })
  const run = (sql: string, binds: unknown[]) => {
    const rows = sql.includes('FROM build_meta')
      ? [...db.prepare(sql).all(...(binds as never[])), ...localHolds()]
      : db.prepare(sql).all(...(binds as never[]))
    // D1 reports rows_read; SQLite here does not, and a made-up number would be worse
    // than none, so the dev server reports what it actually knows: rows returned.
    return { results: rows, meta: { rows_read: rows.length, served_by: 'dev-shim' } }
  }
  // THE DENOMINATORS ARE WRITTEN BY THE PUSH, NOT BY THE BUILD. `sync_search_d1.py`
  // writes `rows:<corpus>` into build_meta when it sends the rows; the local build does
  // not, so without this every "N of 0 searched" reads zero and the one invariant this
  // page must never lose -- a count against its own corpus's size -- cannot be seen
  // locally at all. Counted here with a real COUNT(*), which costs nothing on a local
  // file and would be unthinkable against D1.
  const localHolds = () => {
    const rows = db.prepare('SELECT corpus, COUNT(*) AS n FROM search GROUP BY corpus')
      .all() as { corpus: string; n: number }[]
    return rows.map(r => ({ k: 'rows:' + r.corpus, v: String(r.n) }))
  }
  const stmt = (sql: string, binds: unknown[] = []) => ({
    bind: (...b: unknown[]) => stmt(sql, b),
    all: async () => run(sql, binds),
    first: async () => run(sql, binds).results[0] ?? null,
  })
  return { prepare: (sql: string) => stmt(sql) }
}

export default function devApiSearch(): Plugin {
  return {
    name: 'lunenburg-dev-api-search',
    apply: 'serve',
    configureServer(server) {
      const dbPath = join(server.config.root, '..', 'sources', 'data', 'search-fts.db')
      server.middlewares.use(async (req, res, next) => {
        if (!(req.url || '').startsWith('/api/search')) return next()
        res.setHeader('content-type', 'application/json; charset=utf-8')
        if (!existsSync(dbPath)) {
          res.statusCode = 503
          res.end(JSON.stringify({
            error: 'unavailable',
            message: 'No local search index. Build one: python3 scripts/build_search_index.py',
          }))
          return
        }
        try {
          // Workers has a global cache; node does not. A no-op means every dev request
          // actually runs the query, which is what you want while changing it.
          const g = globalThis as unknown as { caches?: unknown }
          if (!g.caches) g.caches = { default: { match: async () => undefined, put: async () => {} } }
          const fn = join(server.config.root, 'functions', 'api', 'search.js')
          const { onRequest } = await import(pathToFileURL(fn).href + '?t=' + Date.now())
          const out: Response = await onRequest({
            request: new Request('http://localhost' + req.url),
            env: { SEARCH: d1(dbPath) },
            waitUntil: () => {},
          })
          res.statusCode = out.status
          res.end(await out.text())
        } catch (e) {
          res.statusCode = 500
          res.end(JSON.stringify({ error: 'dev_shim_failed', message: String(e) }))
        }
      })
    },
  }
}

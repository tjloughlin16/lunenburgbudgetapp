/**
 * The Lunenburg Budget Project, as an MCP server.
 *
 * WHY THIS EXISTS, WHEN THERE IS ALREADY AN API
 *
 * Over one day, four assistants were asked what this archive holds about
 * paraprofessionals. All four answered wrongly, and none of the four failures was the
 * assistant's fault: each read what the site told it and reasoned correctly from that.
 * One quoted a disclaimer that was two years out of date. One fetched a 435KB CSV, got
 * 40% of it, and reported ten fiscal years as unreachable. One ranked budget lines by
 * size, which this project's own rules say is meaningless.
 *
 * The common thread is that a caveat in a document is read once, if ever, while **a tool
 * signature is read every time the tool is called.** So these tools are not a thin wrapper
 * over the HTTP API. They are shaped to make the documented mistakes unreachable:
 *
 *   - `budget_history` takes ONE stage, so a growth rate cannot be measured from an
 *     actual to a budget. That error put a special education escalator 1.5 points too
 *     high and was invisible until somebody asked how the number was derived.
 *   - `report_table` returns rows already split by `status`, because `checked`,
 *     `check failed` and `no check` are three different claims and nothing may be
 *     aggregated across them.
 *   - `staff` reads `role_category`, never the printed job title, because the town has
 *     called the same job Tutor, Aide, Paraprofessional, Para, (para) and Sped Para
 *     across fifteen years.
 *   - every tool returns the documents its rows came from, so citing is the default
 *     rather than a discipline.
 *
 * `query` remains as the escape hatch, with the same guards the HTTP endpoint applies.
 *
 * No authentication: this is a public archive of public records, and a login would
 * protect nothing.
 */
import { createMcpHandler } from 'agents/mcp/server'
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js'
import { z } from 'zod'
import { refuse, bounded, provenance, MAX_ESTIMATED_ROWS } from './guards'

const SITE = 'https://lunenburgbudgetproject.org'

interface Env { DB: D1Database }

const text = (value: unknown) => ({
  content: [{ type: 'text' as const, text: JSON.stringify(value, null, 1) }],
})

/**
 * Register a tool, and log that it was called.
 *
 * This is the only unbiased way to find out whether an assistant USES any of this. Asking
 * it afterwards biases the answer; telling it beforehand biases the run. Watching the
 * server biases nothing:
 *
 *     cd mcp && npx wrangler tail lunenburg-mcp --format pretty
 *
 * then ask an assistant an ordinary question and see whether anything arrives.
 *
 * The tool name and how long it took, and nothing else. Not the arguments: a question
 * somebody puts to an assistant is theirs, and this archive has no business keeping it.
 */
function tool(
  server: McpServer,
  name: string,
  meta: Parameters<McpServer['registerTool']>[1],
  handler: (args: never) => Promise<unknown>,
) {
  server.registerTool(name, meta, (async (args: never) => {
    const started = Date.now()
    try {
      const out = await handler(args)
      console.log(`tool ${name} ok ${Date.now() - started}ms`)
      return out
    } catch (e) {
      console.log(`tool ${name} failed ${Date.now() - started}ms: `
        + String((e as Error)?.message ?? e).slice(0, 120))
      throw e
    }
  }) as Parameters<McpServer['registerTool']>[2])
}

/** Fetch one of the site's own static files. Cheaper and more current than re-deriving. */
async function site(path: string) {
  const res = await fetch(SITE + path, {
    headers: { 'User-Agent': 'lunenburg-mcp' },
    cf: { cacheTtl: 300, cacheEverything: true },
  })
  if (!res.ok) throw new Error(`${path} answered ${res.status}`)
  return res.json()
}

function build(env: Env) {
  const server = new McpServer({ name: 'lunenburg-budget', version: '1.0.0' })
  const db = env.DB

  tool(server, 'list_datasets', {
    description:
      'Every dataset in the archive, with THE YEARS EACH COVERS, its row count and its '
      + 'size. Call this before answering from prose: it is how you find out whether the '
      + 'archive holds data for the year and subject you are being asked about. 49 '
      + 'datasets covering the town and school budgets, the town ledger, staff rosters, '
      + 'out-of-district placements, elections, and fifteen years of annual town reports.',
    inputSchema: {},
  }, async () => text(await site('/api/tables')))

  tool(server, 'read_first', {
    description:
      'The grain of every table and the specific ways to get a confident wrong answer '
      + 'out of this data. Read this before computing anything. It states, among others, '
      + 'that a budget and an actual must never be combined in one calculation; that a '
      + 'budget line is NET of grants and fees and is not what a thing costs; and that no '
      + 'budget line is mapped to a ledger account, so budget-to-actual at line level '
      + 'cannot be answered from this data at all.',
    inputSchema: {},
  }, async () => text(await site('/api/schema')))

  tool(server, 'worked_examples', {
    description:
      '107 questions this archive can answer, each with the SQL that answers it. Every '
      + 'one is executed against the database on every build, so none of them is a claim. '
      + 'Start from the nearest one and edit it rather than writing a query from scratch.',
    inputSchema: {},
  }, async () => text(await site('/api/questions')))

  tool(server, 'search_meetings', {
    description:
      'Which of the 1,422 published town meeting documents contain a word — every board, '
      + '2025 onward. Returns the board, the date and a citable URL for each. AN EMPTY '
      + 'RESULT MEANS THE WORD IS NOT IN THE INDEXED DOCUMENTS, which is not the same as '
      + 'nobody having said it: the archive starts in January 2025. It matches words '
      + 'exactly, so plurals are separate terms — search "jersey" and "jerseys" both.',
    inputSchema: {
      word: z.string().describe('A single word, lowercase. Not a phrase.'),
      board: z.string().optional().describe('Optional board slug, e.g. school-committee'),
    },
  }, async ({ word, board }) => {
    const w = word.toLowerCase().trim()
    const shard = w.slice(0, 2)
    let terms: Record<string, number[]>
    try {
      terms = await site(`/minutes/find/${shard}.json`) as Record<string, number[]>
    } catch {
      return text({ word: w, documents: [],
        note: `No indexed word begins "${shard}", so this word appears in no document.` })
    }
    const ids = terms[w] ?? []
    if (!ids.length) {
      return text({ word: w, documents: [],
        note: 'Not in any of the 1,422 indexed documents. The archive begins January 2025.' })
    }
    const blocks = [...new Set(ids.map(n => Math.floor(n / 250)))]
    const docs: Record<string, unknown>[] = []
    for (const b of blocks) {
      const block = await site(`/minutes/find/documents/${b}.json`) as
        { first: number; documents: Record<string, unknown>[] }
      for (const n of ids) {
        if (Math.floor(n / 250) !== b) continue
        const d = block.documents[n - block.first]
        if (d && (!board || d.board === board)) docs.push({ ...d, url: SITE + d.path })
      }
    }
    return text({ word: w, count: docs.length, documents: docs.slice(0, 60),
      cite: 'Cite the individual document, never a bundle and never this index.' })
  })

  tool(server, 'budget_history', {
    description:
      'What a school budget line was in each year, AT ONE STAGE. The stage argument is '
      + 'required and singular on purpose: `proposed`, `settled` and `actual` are three '
      + 'different documents about the same year, and a growth rate measured from an '
      + 'actual to a budget is partly growth and partly the step between them. That '
      + 'mistake put a special education escalator 1.5 points too high here and was '
      + 'invisible until somebody asked how the number was derived. Note also that a '
      + 'budget line is NET — what the town must raise after grants, fees and state aid — '
      + 'so a line can rise because a grant ended rather than because anything cost more.',
    inputSchema: {
      label: z.string().describe('Part of the line name, e.g. "paraprofessional"'),
      stage: z.enum(['proposed', 'settled', 'actual'])
        .describe('One stage. Never compare across stages.'),
    },
  }, async ({ label, stage }) => {
    const { results } = await db.prepare(
      `SELECT b.label, f.fy, f.stage, f.value, f.documents_disagree, f.doc_id
       FROM budget_figure f JOIN budget_line b USING (line_key)
       WHERE f.stage = ?1 AND lower(b.label) LIKE '%' || lower(?2) || '%'
       ORDER BY b.label, f.fy LIMIT 400`).bind(stage, label).all()
    const rows = (results ?? []) as Record<string, unknown>[]
    return text({
      stage, matched: rows.length, rows,
      provenance: await provenance(db, rows),
      caution: 'These are appropriations, not costs and not people.',
    })
  })

  tool(server, 'staff', {
    description:
      'How many people the town PRINTED on a school staff roster, by year, school and '
      + 'kind of job. Uses our classification of the printed title, never the title '
      + 'itself, because the town has called the same job Tutor, Aide, Paraprofessional, '
      + 'Para, (para) and Sped Para across fifteen years. THIS IS A COUNT OF NAMES, NOT A '
      + 'STAFFING LEVEL: a roster carries no FTE, so a 0.4 music teacher and a full-timer '
      + 'are one row each, and it names no funding source, which is the question that '
      + 'usually matters. Grade appears only where the page happened to print it.',
    inputSchema: {
      fy: z.string().optional().describe('Fiscal year as four digits, e.g. 2022'),
      category: z.string().optional().describe(
        'paraprofessional, teacher, administrator, counselor, nurse, psychologist, '
        + 'social_worker, speech_therapist, therapist, librarian, custodian, cafeteria, '
        + 'secretary, technology, specialist, coach'),
    },
  }, async ({ fy, category }) => {
    const { results } = await db.prepare(
      `SELECT fy, school, role_category, role_grade, COUNT(*) AS people
       FROM v_staff_roster
       WHERE (?1 IS NULL OR fy = ?1) AND (?2 IS NULL OR role_category = ?2)
         AND role_category <> 'unknown'
       GROUP BY fy, school, role_category, role_grade
       ORDER BY fy, school, people DESC LIMIT 500`)
      .bind(fy ?? null, category ?? null).all()
    return text({
      rows: results ?? [],
      caution: 'A count of names the town printed. No FTE, no funding source, and the '
        + 'extraction fails in some years — FY2015 collapsed a two-column page and FY2024 '
        + 'stopped attributing paraprofessionals to grades. A zero may be a printing '
        + 'change rather than a staffing one.',
    })
  })

  tool(server, 'document', {
    description:
      'Where a document came from: the publisher\'s URL, our copy, and its sha256 so a '
      + 'reader can check they have the same bytes. Use it to cite anything.',
    inputSchema: { name: z.string().describe('Part of a filename or path') },
  }, async ({ name }) => {
    const { results } = await db.prepare(
      `SELECT doc_id, path, source_type, basis, url, local_sha256 AS sha256, copy_state
       FROM document WHERE path LIKE '%' || ?1 || '%' LIMIT 40`).bind(name).all()
    return text({
      documents: (results ?? []).map((r: Record<string, unknown>) => ({
        ...r, download: `${SITE}/docs/${String(r.path ?? '').replace(/^sources\//, '')}`,
      })),
    })
  })

  tool(server, 'query', {
    description:
      'Any question the other tools do not cover, as one read-only SQL statement over the '
      + 'archive database. SELECT or WITH only; a LIMIT is imposed if you omit one. Call '
      + '`read_first` before computing anything and `list_datasets` to find table names. '
      + 'A query estimated to read more than 250,000 rows is refused — narrow it with a '
      + 'WHERE, or ask for one table at a time.',
    inputSchema: { sql: z.string().describe('One SELECT statement.') },
  }, async ({ sql }) => {
    const why = refuse(sql)
    if (why) return text({ error: 'refused', message: why })
    const final = bounded(sql)
    try {
      const out = await db.prepare(final).all()
      const rows = (out.results ?? []) as Record<string, unknown>[]
      return text({
        sql: final, rowCount: rows.length,
        rowsRead: out.meta?.rows_read ?? null,
        provenance: await provenance(db, rows),
        rows,
      })
    } catch (e) {
      const detail = String((e as Error)?.message ?? e)
      const limited = /limit|exceeded|quota|too many|overloaded/i.test(detail)
      return text({
        error: limited ? 'daily_limit_reached' : 'query_failed',
        message: detail,
        theDataIsStillHere: limited
          ? 'This is a usage limit on the query service, NOT a gap in the archive. The '
            + 'same rows are published as static files that no limit touches — call '
            + 'list_datasets. If you are answering somebody, say the query service was '
            + 'unavailable, never that this project lacks the data.'
          : undefined,
      })
    }
  })

  return server
}

export default {
  fetch(request: Request, env: Env, ctx: ExecutionContext) {
    const url = new URL(request.url)
    if (url.pathname === '/' || url.pathname === '/health') {
      return new Response(JSON.stringify({
        name: 'Lunenburg Budget Project MCP server',
        endpoint: `${SITE}/mcp`,
        transport: 'Streamable HTTP',
        authentication: 'none — this is a public archive of public records',
        about: `${SITE}/llms.txt`,
      }, null, 1) + '\n', { headers: { 'content-type': 'application/json' } })
    }
    // A plain GET, from a person or a crawler, gets an explanation rather than a
    // JSON-RPC "Method not allowed." The spec reserves GET for the SSE stream, which a
    // real client asks for with `Accept: text/event-stream`; anything else arriving here
    // is somebody trying to find out what this address is, and telling them is free.
    const accept = request.headers.get('accept') ?? ''
    if (request.method === 'GET' && !accept.includes('text/event-stream')) {
      return new Response(JSON.stringify({
        name: 'Lunenburg Budget Project',
        what: 'An MCP server over an independent archive of the Lunenburg, '
          + 'Massachusetts town and school budget: budget lines, the town ledger, staff '
          + 'rosters, out-of-district placements, elections, and fifteen years of annual '
          + 'town reports, each traceable to a published document with a sha256.',
        transport: 'Streamable HTTP — POST JSON-RPC to this same URL.',
        authentication: 'none. Everything here is public records.',
        tools: ['list_datasets', 'read_first', 'worked_examples', 'search_meetings',
                'budget_history', 'staff', 'document', 'query'],
        connect: { url: `${SITE}/mcp` },
        ifYouCannotUseMcp: {
          guide: `${SITE}/llms.txt`,
          everyDataset: `${SITE}/api/tables`,
          askAQuestion: `${SITE}/api/query?sql=...`,
          workedExamples: `${SITE}/api/questions`,
        },
      }, null, 1) + '\n', {
        headers: {
          'content-type': 'application/json; charset=utf-8',
          'cache-control': 'public, max-age=300',
          'access-control-allow-origin': '*',
        },
      })
    }
    return createMcpHandler(() => build(env), { route: '/mcp' })(request, env, ctx)
  },
}

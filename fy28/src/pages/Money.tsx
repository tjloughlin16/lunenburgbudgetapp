import { useEffect, useState } from 'react'
import type { Tab } from '../routes'
// Derived, not typed. The area was renamed to "Budget Crisis" and this page was
// the one place still saying the old name, because it had written it into a
// sentence instead of reading AREA_LABEL like the header and the front page do.
import { AREA_LABEL } from '../routes'

/** The front door to "The money".
 *
 *  This area held one link — /reports — and a front page that said "Being built". Behind
 *  it, five reference documents were already published as raw files under /reference/,
 *  generated and `--check`ed, and reachable only by somebody who knew the filename. That is
 *  the condition `build_reference_pages.py` rescued them FROM, one level up: published,
 *  correct, and findable by nobody.
 *
 *  WHAT THIS PAGE IS FOR, and why it is not a summary.
 *
 *  The crisis pages answer "what should the town do". This area answers a different
 *  question — how the money actually moves — and the honest version of that answer is
 *  mostly about where the trail goes cold. So the page does two things and neither is a
 *  conclusion: it hands over the five documents, and it states what the published records
 *  cannot answer.
 *
 *  NOT ONE FIGURE IS TYPED HERE (CLAUDE.md rule 2). Every number, title and description on
 *  this page arrives at runtime from two generated files:
 *
 *    /data/reference.json   written by scripts/build_reference_pages.py — the published
 *                           reference documents, each with the `door` it belongs to, the
 *                           scripts that regenerate it, and a one-line description. The
 *                           title is read out of the document itself.
 *    /api/money_gaps.json   the `money_gaps` table, published whole by build_api.py. It is
 *                           the project's own list of what the records do not answer.
 *
 *  Static files, both of them: no D1 read budget is spent by opening this page.
 *
 *  Each of the five documents was read before this shipped, and the descriptions shown are
 *  the ones in reference.json rather than a second set written here — a second set is a
 *  second thing to go stale when a page is rewritten underneath it.
 *
 *  A FILTER THAT MATCHES NOTHING LOOKS EXACTLY LIKE DATA THAT IS ABSENT, so both lists say
 *  so out loud rather than rendering as an empty space.
 *
 *  RULE 7 AND RULE 11 BOTH APPLY TO THE COPY. What is stated here is what the documents
 *  show: the budget documents carry the general-fund appropriation, the district's own
 *  workbook comment records one line being netted down by expected fee revenue, and nothing
 *  marks which other lines are. What is NOT stated: that any particular source pays for any
 *  particular line. Chapter 70 cannot be traced past the general fund, and no document in
 *  the archive closes that. See notes/HANDOFF-MONEY-IN.md, "Claims NOT established". */

type RefPage = {
  name: string; title: string; about: string; url: string; format: string
  door: string; bytes: number; generators: string[]
}
type RefIndex = { about: string; caveat: string; pages: RefPage[] }

type Gap = { side: string; what: string; why: string }
type GapIndex = { count: number; rows: Gap[] }

const DOOR = 'the money'

const kb = (n: number) => (n >= 1e6 ? `${(n / 1e6).toFixed(1)} MB` : `${Math.round(n / 1024)} KB`)

/** The town's own records use `money_in` / `money_out` / `document_wanted`. Rendered from
 *  the value rather than mapped through a table typed here, so a fourth kind of gap
 *  appears on this page the day it appears in the data. */
const sideLabel = (s: string) => s.replace(/_/g, ' ')

/** The gap descriptions carry `**bold**` from the CSV. Rendered, not stripped — the
 *  emphasis is the author's and it lands on the load-bearing half of the sentence. */
function Emphasised({ text }: { text: string }) {
  return (
    <>
      {text.split(/\*\*/).map((part, i) =>
        i % 2 ? <strong key={i}>{part}</strong> : <span key={i}>{part}</span>)}
    </>
  )
}

function H2({ children }: { children: React.ReactNode }) {
  return <h2 className="text-2xl font-bold tracking-tight mt-14 mb-3 max-w-3xl">{children}</h2>
}

function Body({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-[15px] leading-relaxed max-w-2xl mt-3"
      style={{ color: 'var(--text-secondary)' }}>{children}</p>
  )
}

/** One document, as a row. The whole row is the target — 44px is the floor and these are
 *  taller than that on every width, because the description wraps to at least two lines
 *  on a phone. */
function PageRow({ p }: { p: RefPage }) {
  return (
    <a href={p.url} className="card block px-4 py-4 min-h-[44px] transition-opacity hover:opacity-90">
      {/* The arrow is not decoration. Until it was here a document row and a GAP row
          were the same `card` with the same bold title over the same muted sentence,
          and only one of them did anything — TJ: "The Town Manager's revenue
          apportionment worksheet looks identical and is NOT a link." Two things that
          look alike must not behave differently, so the link gained an affordance and
          the gaps lost their card. */}
      <span className="flex items-baseline gap-2 flex-wrap">
        <span className="text-[16px] font-bold leading-tight"
          style={{ color: 'var(--series-cost)' }}>{p.title} &rarr;</span>
        <span className="text-[10.5px] font-semibold uppercase tracking-wider tnum"
          style={{ color: 'var(--text-muted)' }}>{p.format} · {kb(p.bytes)}</span>
      </span>
      <span className="block text-[13.5px] mt-1.5 leading-snug"
        style={{ color: 'var(--text-secondary)' }}>{p.about}</span>
      <span className="block text-[11.5px] mt-2" style={{ color: 'var(--text-muted)' }}>
        {p.generators.length
          ? <>regenerated by {p.generators.map((g, i) => (
            <span key={g}>{i > 0 ? ', ' : ''}<code>{g}</code></span>))}</>
          : 'hand-written — nothing regenerates it, so nothing will tell it when the data moves'}
      </span>
    </a>
  )
}

export function Money({ onJump }: { onJump: (t: Tab) => void }) {
  const [ref, setRef] = useState<RefIndex | null>(null)
  const [gaps, setGaps] = useState<GapIndex | null>(null)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    let live = true
    const get = (u: string) =>
      fetch(u).then(r => (r.ok ? r.json() : Promise.reject(new Error(`${u}: HTTP ${r.status}`))))
    Promise.all([get('/data/reference.json'), get('/api/money_gaps.json')])
      .then(([r, g]) => { if (live) { setRef(r); setGaps(g) } })
      .catch(e => { if (live) setErr(String(e)) })
    return () => { live = false }
  }, [])

  const pages = (ref?.pages ?? []).filter(p => p.door === DOOR)
  const sides = [...new Set((gaps?.rows ?? []).map(g => g.side))]

  return (
    <div className="mx-auto max-w-6xl px-5 pt-14 pb-16">
      <p className="text-xs font-semibold uppercase tracking-widest mb-3"
        style={{ color: 'var(--text-muted)' }}>The money</p>
      <h1 className="text-4xl sm:text-5xl font-bold tracking-tight leading-[1.05] max-w-3xl">
        How the money actually moves
      </h1>
      <p className="mt-5 text-lg leading-relaxed max-w-2xl"
        style={{ color: 'var(--text-secondary)' }}>
        A budget line is not what a thing costs. It is what the town has to <em>raise</em>{' '}
        &mdash; what is left after state aid, grants, fees and the district&rsquo;s own
        revolving funds have paid their share. The budget documents show that one number and
        none of the others.
      </p>

      <Body>
        So a line can rise because the thing got more expensive, because a grant that was
        paying part of it ended, or because a fee stopped being collected &mdash; and all
        three look identical on the page. Beside general education transportation the
        district&rsquo;s own workbook asks, in its comments column, whether that line already
        reflects a reduction for money expected from busing fees &mdash; and nothing on the
        page marks which other lines are net of anything.
      </Body>
      <Body>
        These pages are about the <strong>routes</strong>, not about what to do next. Where a
        route can be followed in the town&rsquo;s ledger, they follow it. Where it cannot,
        they say where it stops instead of estimating across the gap. Nothing here tells you
        which source paid for which line: money in the general fund loses its origin on
        arrival, and no record in the archive puts it back.
      </Body>
      <Body>
        What the town should <em>do</em> about any of it is the other door &mdash;{' '}
        <button onClick={() => onJump('walk')} className="underline"
          style={{ color: 'var(--series-cost)' }}>{AREA_LABEL.crisis}</button>.
      </Body>

      {err && (
        <div className="card p-5 mt-10" style={{ borderLeft: '4px solid var(--status-warning)' }}>
          <p className="text-[15px] font-bold mb-1">This page&rsquo;s index did not load</p>
          <p className="text-[13.5px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
            {err}. The documents themselves are still at <code>/reference/</code> and the
            gap list at <code>/api/money_gaps.json</code>.
          </p>
        </div>
      )}

      <H2>The documents</H2>
      <Body>
        {ref
          ? ref.caveat
          : 'Loading the published reference index…'}
      </Body>
      <div className="grid gap-2.5 mt-6">
        {pages.map(p => <PageRow key={p.name} p={p} />)}
      </div>
      {ref && !pages.length && (
        <p className="text-[13.5px] mt-4" style={{ color: 'var(--status-warning)' }}>
          The reference index loaded and no page in it is filed under &ldquo;{DOOR}&rdquo;.
          That is a broken filter, not an empty shelf &mdash; see{' '}
          <code>scripts/build_reference_pages.py</code>.
        </p>
      )}

      <H2>What is not in here</H2>
      <Body>
        The most useful thing this project can say about the town&rsquo;s money is which
        parts of it the published records cannot answer. This list is kept as data rather
        than as prose, so it is the same list the diagrams are built against.
      </Body>
      <div className="mt-6 space-y-8">
        {sides.map(side => (
          <div key={side}>
            <p className="text-[11px] font-semibold uppercase tracking-widest mb-2"
              style={{ color: 'var(--text-muted)' }}>{sideLabel(side)}</p>
            <ul className="space-y-2.5">
              {gaps!.rows.filter(g => g.side === side).map(g => (
                <li key={g.what} className="pl-3.5 py-1"
                  style={{ borderLeft: '2px solid var(--grid)' }}>
                  <p className="text-[14.5px] font-bold leading-snug">
                    <Emphasised text={g.what} />
                  </p>
                  <p className="text-[13px] leading-snug mt-1"
                    style={{ color: 'var(--text-secondary)' }}>
                    <Emphasised text={g.why} />
                  </p>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
      {gaps && !gaps.rows.length && (
        <p className="text-[13.5px] mt-4" style={{ color: 'var(--status-warning)' }}>
          <code>/api/money_gaps.json</code> answered with no rows. An empty gap list means
          the endpoint changed shape, not that nothing is missing.
        </p>
      )}
      {gaps && (
        <p className="text-xs leading-relaxed mt-6" style={{ color: 'var(--text-muted)' }}>
          {gaps.count.toLocaleString()} entries, published as{' '}
          <a href="/api/money_gaps.json" className="underline"
            style={{ color: 'var(--text-secondary)' }}><code>/api/money_gaps.json</code></a>{' '}
          and queryable as <code>money_gaps</code>. Each is something we went looking for and
          could not establish &mdash; not a claim about anybody.
        </p>
      )}
    </div>
  )
}

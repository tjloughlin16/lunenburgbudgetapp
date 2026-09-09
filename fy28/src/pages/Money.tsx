import { abs } from '../lib/abs'
import { useEffect, useState } from 'react'
import type { Tab } from '../routes'
// Derived, not typed. The area was renamed to "Budget Crisis" and this page was
// the one place still saying the old name, because it had written it into a
// sentence instead of reading AREA_LABEL like the header and the front page do.
import { AREA_LABEL, AREA_TABS, LABEL } from '../routes'

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
 *  conclusion: it hands over the five documents, and it hands over the gaps.
 *
 *  THE GAP LIST ITSELF MOVED. It was rendered at the bottom of this page and is now
 *  /what-we-cannot-answer, with two bodies of material it belongs beside: what has been
 *  extracted and never checked against a printed total, and what the Town has been asked
 *  for and has not sent. This page still READS `money_gaps` -- for the count on the link,
 *  which is derived rather than typed, and for the empty-list warning, because a link
 *  promising a list that is empty is worse than no link.
 *
 *  NOT ONE FIGURE IS TYPED HERE (CLAUDE.md rule 2). Every number, title and description on
 *  this page arrives at runtime from two generated files:
 *
 *    /data/reference.json   written by scripts/build_reference_pages.py — the published
 *                           reference documents, each with the `door` it belongs to, the
 *                           scripts that regenerate it, and a one-line description. The
 *                           title is read out of the document itself.
 *    /api/money_gaps.json   the `money_gaps` table, published whole by build_api.py. Only
 *                           its COUNT is shown here; the rows are on /what-we-cannot-answer.
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
  door: string; tier: string; bytes: number; generators: string[]
}
type RefIndex = { about: string; caveat: string; pages: RefPage[] }

type Gap = { side: string; what: string; why: string }
type GapIndex = { count: number; rows: Gap[] }

/** One line per analysis, saying what it ESTABLISHES rather than what it contains.
 *
 *  No figure is typed here (rule 2). Every number on those pages is computed and can move;
 *  a headline quoted in this list would be the one thing on the page that does not.
 *  Anything not named here renders with no description rather than a wrong one. */
const ABOUT: Partial<Record<Tab, string>> = {
  stateaid: 'The share of the school budget nobody here votes on, and how far it misses '
          + 'its own estimate.',
  leaving: 'What school choice would cost the town if students transferred out — a '
         + 'scenario put to this site, with every input a dial.',
  families: 'Every school fee a household can be charged, priced for one to four '
         + 'children — and the three places the published record runs out.',
  staffing: 'What the town publishes about who works in the schools — and why a list of '
          + 'names is not a staffing level.',
  insurance: 'The line that grows fastest, budgeted against what was later reported.',
  sportsmoney: 'Both sides of school athletics: what the town appropriates, and what the '
             + 'district says the same categories cost.',
  variance: 'Budgets against what was later reported spent, line by line, and where the '
          + 'two documents disagree.',
  funds: 'Grants, gifts, revolving and enterprise funds — the money that never appears in '
       + 'the budget everyone argues about.',
  stopped: 'Every school line the district’s own book took to zero, when, and how often '
         + 'the money came back the following year.',
  unwind: 'Every school dollar split by the fund that paid it — and what happened in each '
        + 'part of the budget when the grant money stopped.',
  minaid: 'Chapter 70’s formula, term by term, for twenty years — and why four of the last '
        + 'five increases are a flat per-pupil floor the Legislature sets rather than '
        + 'anything the formula produced.',
  montytech: 'The larger of the two routes out of Lunenburg’s own schools, and an '
          + 'assessment rather than an appropriation — what sets it, and why 95% of it is '
          + 'a figure the state calculates.',
  peers: 'What DESE says every Massachusetts district spends for each pupil, with '
       + 'Lunenburg drawn through it — and the arithmetic that says how much of the '
       + 'difference is money and how much is children.',
  // The ONE measure the state enforces, and the description says so first — because
  // every other line in this list is a budget somebody chose, and a reader has no way to
  // know that this one is different.
  required: 'The one school spending figure Massachusetts enforces rather than observes, '
          + 'and where Lunenburg has sat against every other district for three decades. '
          + 'The town has never been below the floor, and its position against the state '
          + 'was at the median more recently than the usual story allows.',
  // FOUR reports behind one door, and the description says so, because the thing a reader
  // most needs to know before opening any of them is that they do not combine.
  sped: 'Four separate reports on the quarter of the budget nobody was measuring: how many '
      + 'children, who leaves and where they go, what it costs and what the state '
      + 'reimburses, and the route into out-of-district placement. They are four because '
      + 'a student is not a dollar and a placement is not a cost.',
}

const DOOR = 'the money'

const kb = (n: number) => (n >= 1e6 ? `${(n / 1e6).toFixed(1)} MB` : `${Math.round(n / 1024)} KB`)

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
    <a href={abs(p.url)} className="card block px-4 py-4 min-h-[44px] transition-opacity hover:opacity-90">
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
  /** Two tiers, because these are not alternatives. The flow diagrams answer the question
   *  somebody walks in with; the rest answer questions you only have once you have seen
   *  them — which route exactly, who signs, how the ledger is named. Presenting five
   *  documents as equals makes a reader choose between things that are not choices. */
  const primary = pages.filter(p => p.tier === 'primary')
  const secondary = pages.filter(p => p.tier !== 'primary')

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

      <H2>Core documents</H2>
      <Body>
        {ref
          ? ref.caveat
          : 'Loading the published reference index…'}
      </Body>
      <div className="grid gap-2.5 mt-6">
        {primary.map(p => <PageRow key={p.name} p={p} />)}
      </div>

      <H2>Where the money comes from</H2>
      <Body>
        The routes in, and the money that never reaches the budget everyone argues about.
        The reports that read the spending side are below.
      </Body>
      {/* DERIVED FROM THE AREA'S OWN TAB LIST, not typed.
          These pages existed for hours reachable only from the header bar, because this
          page listed the five reference documents and nothing else — the same "published,
          correct, and findable by nobody" condition it was built to rescue those documents
          FROM. TJ: "do those drill-ins have links on The Money page? I expected to see them
          there, but I dont."
          Reading AREA_TABS means the next drill-in appears here the day it is routed,
          rather than the day somebody remembers to add it. */}
      <div className="grid gap-2.5 mt-6 sm:grid-cols-2">
        {AREA_TABS.money
          .filter(t => t !== 'themoney' && t !== 'reports' && t !== 'gaps' && t !== 'askus')
          .map(t => (
            <button key={t} onClick={() => onJump(t)}
              className="card block w-full text-left px-4 py-4 min-h-[44px]
                         transition-opacity hover:opacity-90">
              <span className="text-[15.5px] font-bold leading-tight block"
                style={{ color: 'var(--series-cost)' }}>{LABEL[t]} &rarr;</span>
              <span className="block text-[13px] mt-1.5 leading-snug"
                style={{ color: 'var(--text-secondary)' }}>{ABOUT[t] ?? ''}</span>
            </button>
          ))}
      </div>

      {/* THE DRILL-INS, WHICH ARE NO LONGER IN THIS AREA.
          Splitting `money` in two on 8 September moved eight pages out of AREA_TABS.money,
          and because the grid above is derived from that list they would have vanished
          from this page the same commit — the exact "reachable only from the header bar"
          condition the comment above records TJ catching once already.
          A split must leave a door behind it. Same derivation, so a report added to the
          analyses area appears here the day it is routed. */}
      <H2>The reports</H2>
      <Body>
        Each takes one question as far as the published records carry it, and then says
        where it stops. They have an area of their own.
      </Body>
      <div className="grid gap-2.5 mt-6 sm:grid-cols-2">
        {AREA_TABS.analyses.filter(t => t !== 'reports').map(t => (
          <button key={t} onClick={() => onJump(t)}
            className="card block w-full text-left px-4 py-4 min-h-[44px]
                       transition-opacity hover:opacity-90">
            <span className="text-[15.5px] font-bold leading-tight block"
              style={{ color: 'var(--series-cost)' }}>{LABEL[t]} &rarr;</span>
            <span className="block text-[13px] mt-1.5 leading-snug"
              style={{ color: 'var(--text-secondary)' }}>{ABOUT[t] ?? ''}</span>
          </button>
        ))}
      </div>

      {secondary.length > 0 && (
        <>
          <H2>Going further</H2>
          <Body>
            The routes in detail — which one exactly, who signs, and how the ledger is
            named. These answer questions you only have once you have read the two above.
          </Body>
          {/* A SECTION, not an eyebrow. These sat as small rows tucked under the core
              documents, which made them read as a footnote to those rather than as their
              own shelf. TJ: "Going further as a section itself, same as the others". */}
          <div className="grid gap-2.5 mt-6">
            {secondary.map(p => (
              <a key={p.name} href={abs(p.url)}
                className="card block px-4 py-4 min-h-[44px] transition-opacity
                           hover:opacity-90">
                <span className="text-[15.5px] font-bold leading-tight"
                  style={{ color: 'var(--series-cost)' }}>{p.title} &rarr;</span>
                <span className="block text-[12.5px] mt-0.5 leading-snug"
                  style={{ color: 'var(--text-secondary)' }}>{p.about}</span>
              </a>
            ))}
          </div>
        </>
      )}
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
        parts of it the published records cannot answer. That list is kept as data rather
        than as prose, so it is the same list the diagrams are built against &mdash; and it
        has a page of its own, alongside what has been read without being checked and what
        the Town has been asked for and has not sent.
      </Body>
      <button onClick={() => onJump('gaps')}
        className="card block w-full text-left px-4 py-4 min-h-[44px] mt-6
                   transition-opacity hover:opacity-90">
        <span className="text-[16px] font-bold leading-tight"
          style={{ color: 'var(--series-cost)' }}>{LABEL.gaps} &rarr;</span>
        <span className="block text-[13.5px] mt-1.5 leading-snug"
          style={{ color: 'var(--text-secondary)' }}>
          {gaps
            ? <>{gaps.count.toLocaleString()} questions this project went looking for and
              could not settle from the published records, each with the document that
              would close it &mdash; with what we hold and have not checked, and what is
              still outstanding from the Town.</>
            : 'What the published records cannot answer, and what would close each gap.'}
        </span>
      </button>
      {gaps && !gaps.rows.length && (
        <p className="text-[13.5px] mt-4" style={{ color: 'var(--status-warning)' }}>
          <code>/api/money_gaps.json</code> answered with no rows. An empty gap list means
          the endpoint changed shape, not that nothing is missing.
        </p>
      )}
    </div>
  )
}

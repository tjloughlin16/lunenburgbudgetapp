import { abs } from '../lib/abs'
import { Go } from '../lib/nav'
import { useEffect, useState } from 'react'
import type { Tab } from '../routes'
// Derived, not typed. The area was renamed to "Budget Crisis" and this page was
// the one place still saying the old name, because it had written it into a
// sentence instead of reading AREA_LABEL like the header and the front page do.
import { AREA_TABS, LABEL } from '../routes'

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

/** The report groups, as the reports index declares them. Read from the same payload
 *  /reports draws, so the two pages cannot disagree about what exists or where it files. */
type ReportsPayload = {
  reports: { id: string; title: string; about: string; url: string }[]
  pages: { id: string; title: string; about: string; url: string }[]
  groups: { key: string; title: string; sections: { title: string; ids: string[] }[] }[]
}

/** Groups that are TOOLING, not money reports -- the blog, this week, the boards, the
 *  minutes. They filed here as equals of "who ends up out of district" and made the
 *  shelf a sitemap. They have the front page and /reports; this page is about money. */
const NOT_MONEY = new Set(['cards', 'week'])

function H2({ children }: { children: React.ReactNode }) {
  return <h2 className="text-2xl font-bold tracking-tight mt-14 mb-3 max-w-3xl">{children}</h2>
}

function H3({ children }: { children: React.ReactNode }) {
  return <h3 className="text-[11px] font-bold uppercase tracking-widest mt-8 mb-3" style={{ color: 'var(--text-muted)' }}>{children}</h3>
}

function Body({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-[15px] leading-relaxed max-w-2xl mt-3"
      style={{ color: 'var(--text-secondary)' }}>{children}</p>
  )
}

/** One card, one place to go. The title carries the `door-title` class so a card the
 *  reader has already opened shows in the secondary colour -- on a shelf of thirty, the
 *  visited state is how anybody keeps their place, and it only exists on a real link. */
function LinkCard({ href, title, about, meta }: { href: string; title: string; about?: string; meta?: string }) {
  return (
    <a href={href} className="card block px-4 py-4 min-h-[44px] transition-opacity hover:opacity-90">
      <span className="flex items-baseline gap-2 flex-wrap">
        <span className="door-title text-[15.5px] font-bold leading-tight">{title} &rarr;</span>
        {meta && <span className="text-[10.5px] font-semibold uppercase tracking-wider tnum" style={{ color: 'var(--text-muted)' }}>{meta}</span>}
      </span>
      {about && <span className="block text-[13px] mt-1.5 leading-snug" style={{ color: 'var(--text-secondary)' }}>{about}</span>}
    </a>
  )
}

function TabCard({ t }: { t: Tab }) {
  return (
    <Go to={t} className="card block px-4 py-4 min-h-[44px] transition-opacity hover:opacity-90">
      <span className="door-title text-[15.5px] font-bold leading-tight block">{LABEL[t]} &rarr;</span>
      {ABOUT[t] && <span className="block text-[13px] mt-1.5 leading-snug" style={{ color: 'var(--text-secondary)' }}>{ABOUT[t]}</span>}
    </Go>
  )
}

/** THE THING FIRST (rule 7a). This page opened with four paragraphs explaining what a
 *  budget line is, then two generated diagrams described by their file size and the
 *  script that regenerates them, then thirty-two identical cards. The walk as a resident
 *  called it "a sitemap wearing a page's clothes". It is now: one line, the two pages
 *  about where money comes from, the two diagrams by what they show, the reports grouped
 *  the way /reports groups them with the tooling removed, the gaps -- and the
 *  explanation of what a budget line is at the foot, where it qualifies what a reader
 *  has just seen rather than standing in front of it. */
export function Money() {
  const [ref, setRef] = useState<RefIndex | null>(null)
  const [gaps, setGaps] = useState<GapIndex | null>(null)
  const [reports, setReports] = useState<ReportsPayload | null>(null)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    let live = true
    const get = (u: string) =>
      fetch(u).then(r => (r.ok ? r.json() : Promise.reject(new Error(`${u}: HTTP ${r.status}`))))
    Promise.all([get('/data/reference.json'), get('/api/money_gaps.json'), get('/data/reports.json')])
      .then(([r, g, rep]) => { if (live) { setRef(r); setGaps(g); setReports(rep) } })
      .catch(e => { if (live) setErr(String(e)) })
    return () => { live = false }
  }, [])

  const pages = (ref?.pages ?? []).filter(p => p.door === DOOR)
  const primary = pages.filter(p => p.tier === 'primary')
  const secondary = pages.filter(p => p.tier !== 'primary')
  const byId: Record<string, { title: string; about: string; url: string }> =
    Object.fromEntries([...(reports?.reports ?? []), ...(reports?.pages ?? [])].map(r => [r.id, r]))
  const groups = (reports?.groups ?? []).filter(g => !NOT_MONEY.has(g.key))

  return (
    <div className="mx-auto max-w-6xl px-5 pt-14 pb-16">
      <p className="text-xs font-semibold uppercase tracking-widest mb-3"
        style={{ color: 'var(--text-muted)' }}>The money</p>
      <h1 className="text-4xl sm:text-5xl font-bold tracking-tight leading-[1.05] max-w-3xl">
        How the money actually moves
      </h1>
      <p className="mt-5 text-lg leading-relaxed max-w-2xl"
        style={{ color: 'var(--text-secondary)' }}>
        Where every dollar comes from, what it buys, and where the published record stops
        being able to say. What the town should <em>do</em> about any of it is on{' '}
        <Go to="solutions" className="underline" style={{ color: 'var(--series-cost)' }}>Solutions</Go>.
      </p>

      {err && (
        <div className="card p-5 mt-10" style={{ borderLeft: '4px solid var(--status-warning)' }}>
          <p className="text-[15px] font-bold mb-1">This page&rsquo;s index did not load</p>
          <p className="text-[13.5px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
            {err}. The documents themselves are still at <code>/reference/</code> and the
            gap list at <code>/api/money_gaps.json</code>.
          </p>
        </div>
      )}

      <H2>Where the money comes from</H2>
      {/* DERIVED FROM THE AREA'S OWN TAB LIST, not typed, so the next revenue-side page
          appears here the day it is routed. TJ once found these reachable only from the
          header bar: "do those drill-ins have links on The Money page? I expected to see
          them there, but I dont." */}
      <div className="grid gap-2.5 mt-4 sm:grid-cols-2">
        {AREA_TABS.money
          .filter(t => t !== 'themoney' && t !== 'reports' && t !== 'gaps' && t !== 'askus')
          .map(t => <TabCard key={t} t={t} />)}
      </div>

      <H2>The whole thing, drawn</H2>
      <Body>Every source the town budgets, every account the schools spend from, and the join in the middle that no record makes.</Body>
      <div className="grid gap-2.5 mt-4 sm:grid-cols-2">
        {primary.map(p => (
          <LinkCard key={p.name} href={abs(p.url)} title={p.title} about={p.about} meta={`${p.format} · ${kb(p.bytes)}`} />
        ))}
        {ref && !pages.length && (
          <p className="text-[13.5px]" style={{ color: 'var(--status-warning)' }}>
            The reference index loaded and no page in it is filed under &ldquo;{DOOR}&rdquo;.
            That is a broken filter, not an empty shelf &mdash; see{' '}
            <code>scripts/build_reference_pages.py</code>.
          </p>
        )}
      </div>

      {/* THE REPORTS, GROUPED THE WAY /reports GROUPS THEM. The list used to be the
          analyses area's whole tab strip, flat, which put "the blog" and "this week in
          town" beside "who ends up out of district" as thirty-two equals. The groups are
          declared once, in build_reports_index.py, and read here. */}
      <H2>The reports</H2>
      <Body>Each takes one question as far as the published records carry it, then says where it stops.</Body>
      {groups.map(g => (
        <section key={g.key} aria-label={g.title}>
          <h3 className="text-[19px] font-bold tracking-tight mt-10">{g.title}</h3>
          {g.sections.map(sec => (
            <div key={sec.title || g.key}>
              {sec.title && <H3>{sec.title}</H3>}
              <div className={'grid gap-2.5 sm:grid-cols-2' + (sec.title ? '' : ' mt-4')}>
                {sec.ids.map(id => byId[id]).filter(Boolean).map(r => (
                  <LinkCard key={r.url} href={r.url} title={r.title} about={r.about} />
                ))}
              </div>
            </div>
          ))}
        </section>
      ))}
      {reports && !groups.length && (
        <p className="text-[13.5px] mt-4" style={{ color: 'var(--status-warning)' }}>
          <code>/data/reports.json</code> loaded with no groups. That is a broken index, not an empty shelf.
        </p>
      )}

      <H2>What is not in here</H2>
      <Go to="gaps" className="card block px-4 py-4 min-h-[44px] mt-4 transition-opacity hover:opacity-90">
        <span className="door-title text-[16px] font-bold leading-tight">{LABEL.gaps} &rarr;</span>
        <span className="block text-[13.5px] mt-1.5 leading-snug" style={{ color: 'var(--text-secondary)' }}>
          {gaps
            ? <>{gaps.count.toLocaleString()} questions this project went looking for and
              could not settle from the published records, each with the document that
              would close it.</>
            : 'What the published records cannot answer, and what would close each gap.'}
        </span>
      </Go>
      {gaps && !gaps.rows.length && (
        <p className="text-[13.5px] mt-4" style={{ color: 'var(--status-warning)' }}>
          <code>/api/money_gaps.json</code> answered with no rows. An empty gap list means
          the endpoint changed shape, not that nothing is missing.
        </p>
      )}

      {secondary.length > 0 && (
        <>
          <H2>Going further</H2>
          <Body>The routes in detail &mdash; which one exactly, who signs, how the ledger is named.</Body>
          <div className="grid gap-2.5 mt-4">
            {secondary.map(p => <LinkCard key={p.name} href={abs(p.url)} title={p.title} about={p.about} />)}
          </div>
        </>
      )}

      {/* THE EXPLANATION, AT THE FOOT. This is what used to open the page. It is the most
          important idea on it -- rule 11, a budget line is net -- and it belongs after
          the reader has seen a budget line, not before (rule 7a). TJ: "Caveats should
          always go at the bottom." */}
      <H2>What a budget line is, and is not</H2>
      <Body>
        A budget line is not what a thing costs. It is what the town has to <em>raise</em>{' '}
        &mdash; what is left after state aid, grants, fees and the district&rsquo;s own
        revolving funds have paid their share. The budget documents show that one number and
        none of the others.
      </Body>
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
        {ref?.caveat ? <> {ref.caveat}</> : null}
      </Body>
    </div>
  )
}

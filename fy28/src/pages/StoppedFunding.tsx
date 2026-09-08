import { useEffect, useState } from 'react'
import { abs } from '../lib/abs'
import { usd } from '../model/engine'
import { Basis } from '../components/Basis'
import {
  ByCategory, FundSplit, NamedLines, ShapeOfTheBook, TableTwin, ZeroedByYear,
  fy, type Cover, type Cut, type FundPoint, type Named, type Year,
} from '../components/StoppedFundingCharts'

/** What stopped being funded — every school line the district's own book took to zero.
 *
 *  WHY THIS PAGE EXISTS, AND WHY IT SURVIVES A LIMIT ITS NEIGHBOUR DOES NOT. The twelve
 *  years of line-level school figures here are RESTATEMENTS: a closed year re-presented
 *  inside a district budget book, by the party that spent it. That is why
 *  /budget-vs-actual cannot settle over-budgeting before FY2026 — both sides of that
 *  comparison come out of the same document, and a document cannot audit itself. This page
 *  asks a different question. It asks what the district's own reporting shows it stopped
 *  funding, year on year, and a restatement is a perfectly fair source for a claim about
 *  what the district REPORTS. The page says that in one sentence, near the top, in those
 *  words.
 *
 *  RULE 7 IS THE WHOLE DIFFICULTY. "This line went to a printed zero in FY2017" is a
 *  measurement. "The service stopped" is a hypothesis, and so is "the town cut it". A line
 *  can leave a book because a grant took it over (rule 11 — a budget line is NET), because
 *  it merged into another line, because it was renamed, or because the entire book changed
 *  shape. All four look identical on the page: an absence. So every section carries both
 *  halves, and the rename check is not a footnote — it is section 2.
 *
 *  RULE 6 IS THE TRAP THIS PAGE WAS BUILT AROUND. "Lines that go to zero and reappear
 *  renamed produce −100% rates that look like findings." Renames are established here
 *  ARITHMETICALLY — two spellings carrying the identical value in every year they share —
 *  and a weaker set is proposed on the words alone and labelled as ours. The counts are
 *  in the payload, not in this comment: a number written down beside code is the same
 *  defect as a number written down beside prose.
 *
 *  RULE 7a. The page opens with the count and the split. Everything explaining how to read
 *  a restatement is under it.
 *
 *  RULE 2. Not one figure is typed into this file. Everything arrives from
 *  /data/stopped-funding.json, written by scripts/build_stopped_funding.py, which refuses
 *  to write on five separate conditions rather than publishing an empty page.
 *
 *  NO D1 AT PAGE LOAD. One static file. */

type Event = {
  line_key: string; label: string; fy: number; was: number
  returned: boolean; returned_fy: number | null; returned_value: number | null
  buys: string; school: string
}

type Permanent = {
  line_key: string; label: string; last_funded_fy: number; last_funded: number
  zero_years: number[]; last_seen_fy: number; buys: string; school: string
}

type Vanished = {
  line_key: string; label: string; last_fy: number; last_value: number
  buys: string; school: string
}

type Rename = {
  older: string; newer: string; older_last_fy: number; newer_first_fy: number
  newer_last_fy: number; shared_years: number[]; shared: number; value: number
  tier: string; basis: string; strength: string
}

type Spelling = {
  older: string; newer: string; older_last_fy: number; newer_first_fy: number
  newer_last_fy: number; older_value: number; newer_value: number
  similarity: number; tier: string; basis: string; strength: string
}

type Decline = {
  line_key: string; label: string; peak_fy: number; peak: number; recent: number
  recent_years: number[]; fall: number; fall_share: number; buys: string; school: string
}

type Payload = {
  generated_by: string
  source: string
  stage: string
  stage_note: string
  span: { first_fy: number; last_fy: number; years: number; documents: number }
  documents: string[]
  excluded: string[]
  definitions: Record<string, string | number>
  coverage: Cover[]
  totals: {
    lines: number; events: number; event_dollars: number
    returned: number; returned_dollars: number
    stayed: number; stayed_dollars: number
    permanent: number; permanent_dollars: number
    vanished: number; vanished_dollars: number
    declines: number; decline_dollars: number
    renames: number; twins: number; spelling_candidates: number
    disagreeing_rows: number
    biggest_permanent: Permanent; biggest_decline: Decline
    silent_years: number[]
  }
  per_year: Year[]
  vanished_by_year: { fy: number; n: number; dollars: number }[]
  events: Event[]
  permanent: Permanent[]
  vanished: Vanished[]
  renames: Rename[]
  spelling_candidates: Spelling[]
  declines: Decline[]
  categories: Record<string, Cut[]>
  shape: {
    fy: number; next_fy: number; lines_stopped: number; dollars: number
    lines_before: number; lines_after: number
    total_before: number; total_after: number; total_change: number
    renames_across: number
    documents_before: string[]; documents_after: string[]
  }
  dese: {
    code: string; name: string; family: string; question: string
    points: FundPoint[]
    first_fy: number; last_fy: number
    overlap_first_fy: number; overlap_last_fy: number
    gen_fund_first: number; gen_fund_last: number; gen_fund_change: number
    grants_first: number; grants_last: number
    grant_share_last: number | null; grant_share_max: number | null
    documents: string[]
  }[]
  minutes_coverage: {
    board: string; first_year: number; last_year: number
    agendas: number; minutes: number; share: number | null
    years_with_none: number[]; years_under_half: number[]
    per_year: { year: number; agendas: number; minutes: number; share: number | null }[]
  }
  guidance: Named[]
  prof_development: Named[]
  prof_development_split: {
    fy: number; per_school: number; system: number
    per_school_lines: number; lines_printed: number
  }[]
  prof_development_zero_from: number
  said: {
    key: string; board: string; date: string; quote: string; why: string
    cite: string; town: string
  }[]
  searched: { term: string; documents: number }[]
  minutes: {
    readable: number; published: number; first_date: string; last_date: string
  }
  searchable_from: number
  gaps: { side: string; what: string; why: string; closes: string | null }[]
}

function H2({ id, children }: { id?: string; children: React.ReactNode }) {
  return (
    <h2 id={id} className="text-2xl font-bold tracking-tight mt-14 mb-3 max-w-3xl
                           scroll-mt-[calc(var(--header-h)+1rem)]">{children}</h2>
  )
}

function H3({ children }: { children: React.ReactNode }) {
  return <h3 className="text-[15px] font-bold mt-9 mb-1 max-w-2xl">{children}</h3>
}

function Body({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-[15px] leading-relaxed max-w-2xl mt-3"
      style={{ color: 'var(--text-secondary)' }}>{children}</p>
  )
}

function Stat({ value, tone, children }: {
  value: string; tone?: string; children: React.ReactNode
}) {
  return (
    <div>
      <div className="text-3xl font-bold tracking-tight tnum"
        style={tone ? { color: tone } : undefined}>{value}</div>
      <div className="text-[13px] leading-snug mt-1 max-w-[15rem]"
        style={{ color: 'var(--text-secondary)' }}>{children}</div>
    </div>
  )
}

/** The half of every section that says what the measurement does NOT establish. */
function NotShown({ children }: { children: React.ReactNode }) {
  return (
    <div className="card p-4 mt-5 max-w-2xl" style={{ borderLeft: '4px solid var(--axis)' }}>
      <p className="text-[11px] font-semibold uppercase tracking-widest mb-1.5"
        style={{ color: 'var(--text-muted)' }}>What this does not show</p>
      <div className="text-[14px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
        {children}
      </div>
    </div>
  )
}

/** A hypothesis, marked as one. Never rendered in the same voice as a measurement. */
function Maybe({ settle, children }: { settle: React.ReactNode; children: React.ReactNode }) {
  return (
    <div className="card p-4 mt-4 max-w-2xl"
      style={{ borderLeft: '4px solid var(--status-warning)' }}>
      <p className="text-[11px] font-semibold uppercase tracking-widest mb-1.5"
        style={{ color: 'var(--text-muted)' }}>
        A possible explanation &mdash; nothing here tests it
      </p>
      <div className="text-[14px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
        {children}
        <p className="mt-2.5"><strong>What would settle it:</strong> {settle}</p>
      </div>
    </div>
  )
}

/** One conclusion, at the top, in the shape somebody could repeat out loud. */
function Insight({ n, headline, children }: {
  n: number; headline: React.ReactNode; children: React.ReactNode
}) {
  return (
    <div className="card p-5">
      <div className="text-[11px] font-semibold uppercase tracking-widest mb-2"
        style={{ color: 'var(--text-muted)' }}>Finding {n}</div>
      <p className="text-[17px] font-bold leading-snug">{headline}</p>
      <p className="text-[14px] leading-relaxed mt-2.5" style={{ color: 'var(--text-secondary)' }}>
        {children}
      </p>
    </div>
  )
}

const docName = (p: string) => p.split('/').pop() ?? p

export function StoppedFunding() {
  const [d, setD] = useState<Payload | null>(null)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    let live = true
    fetch('/data/stopped-funding.json')
      .then(r => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then(j => { if (live) setD(j) })
      .catch(e => { if (live) setErr(String(e)) })
    return () => { live = false }
  }, [])

  if (err) {
    return (
      <div className="mx-auto max-w-6xl px-5 pt-14 pb-16">
        <h1 className="text-3xl font-bold tracking-tight">What stopped being funded</h1>
        <div className="card p-5 mt-8" style={{ borderLeft: '4px solid var(--status-warning)' }}>
          <p className="text-[15px] font-bold mb-1">The series did not load</p>
          <p className="text-[13.5px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
            {err}. Nothing on this page is typed into it, so with the file missing there is
            nothing to show rather than something stale. The underlying rows are published
            at{' '}
            <a className="underline" style={{ color: 'var(--series-cost)' }}
              href={abs('/data/stopped-funding.json')}>/data/stopped-funding.json</a>.
          </p>
        </div>
      </div>
    )
  }

  if (!d) {
    return (
      <div className="mx-auto max-w-6xl px-5 pt-14 pb-16">
        <h1 className="text-3xl font-bold tracking-tight">What stopped being funded</h1>
        <p className="mt-4 text-[15px]" style={{ color: 'var(--text-muted)' }}>
          Loading the measured series&hellip;
        </p>
      </div>
    )
  }

  const t = d.totals
  const S = d.shape
  const span = Array.from(
    { length: d.span.last_fy - d.span.first_fy + 1 }, (_, i) => d.span.first_fy + i)
  const silent = t.silent_years
  const guidanceQuote = d.said.find(q => q.key === 'guidance')!
  const socialQuote = d.said.find(q => q.key === 'social-workers')!
  const pdQuote = d.said.find(q => q.key === 'prof-development')!
  const psyQuote = d.said.find(q => q.key === 'psychologist')!
  const MC = d.minutes_coverage
  const pdev = d.dese.find(c => c.code === 'PDEV')!
  const roseEverywhere = d.dese.every(c => c.gen_fund_change > 0)
  const pdZero = d.prof_development_zero_from
  const pdLast = d.prof_development_split[d.prof_development_split.length - 1]
  const pdPeak = d.prof_development_split.reduce(
    (a, b) => (b.per_school > a.per_school ? b : a))
  const guidanceStopped = d.guidance.filter(g => g.last_fy < d.span.last_fy)
  const guidanceRunning = d.guidance.filter(g => g.last_fy === d.span.last_fy)
  const found = d.searched.filter(s => s.documents > 0)
  const empty = d.searched.filter(s => s.documents === 0)
  const gapShape = d.gaps[0]
  const gapRecent = d.gaps[1]
  const gapFilled = d.gaps[2]
  const gapLedger = d.gaps[3]
  const renames = d.renames.filter(r => r.tier === 'rename')
  const twins = d.renames.filter(r => r.tier === 'twin')

  return (
    <div className="mx-auto max-w-6xl px-5 pt-14 pb-16">
      <p className="text-xs font-semibold uppercase tracking-widest mb-3"
        style={{ color: 'var(--text-muted)' }}>The money</p>
      <h1 className="text-4xl sm:text-5xl font-bold tracking-tight leading-[1.05] max-w-3xl">
        {t.events} times a school line went to zero &mdash; and {t.returned} of them
        came back
      </h1>
      <p className="text-[16px] leading-relaxed max-w-2xl mt-5"
        style={{ color: 'var(--text-secondary)' }}>
        {d.span.years} years of the district restating its own book, {t.lines} lines,
        FY{d.span.first_fy} to FY{d.span.last_fy}.
      </p>

      <div className="grid gap-7 mt-9"
        style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 12rem), 1fr))' }}>
        <Stat value={String(t.stayed)} tone="var(--series-revenue)">
          lines went to a printed zero and were never funded again &mdash;{' '}
          {usd(t.stayed_dollars)} of the year before
        </Stat>
        <Stat value={String(t.returned)}>
          went to zero and were funded again later &mdash; {usd(t.returned_dollars)}
        </Stat>
        <Stat value={String(t.renames + t.spelling_candidates)}>
          endings that are a line being spelled differently, not a line ending
        </Stat>
        <Stat value={silent.map(fy).join(', ')} tone="var(--status-warning)">
          years where the book prints almost no zeros, so nothing can be measured
        </Stat>
      </div>

      {/* THE CAVEAT THAT LEADS, because it changes whether the reader should trust the
          page at all — rule 3's territory, and the one exception rule 7a allows. */}
      <div className="card p-4 mt-9 max-w-3xl"
        style={{ borderLeft: '4px solid var(--status-warning)' }}>
        <p className="text-[14px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
          <strong>This is the district&rsquo;s own reporting, not the town&rsquo;s
          accounting system.</strong> Every figure here comes from a column inside a
          district budget book &mdash; {d.stage_note.toLowerCase()} That is why this
          question can be asked and{' '}
          <a className="underline" style={{ color: 'var(--series-cost)' }}
            href={abs('/budget-vs-actual')}>did they spend what they budgeted</a>{' '}
          cannot: a claim about what the district <em>reports</em> is fairly settled by the
          district&rsquo;s own book, and a claim about whether that book is right is not.
        </p>
        <p className="mt-3">
          <Basis level="stated">the district&rsquo;s restatement of its own closed years</Basis>
        </p>
      </div>

      {/* ------------------------------------------------------- 1. conclusions */}
      <H2 id="findings">What this establishes</H2>
      <div className="grid gap-4 mt-6"
        style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 20rem), 1fr))' }}>
        <Insight n={1} headline={
          <>A line hitting zero in this book is usually a pause, not an ending.
            {' '}{t.returned} of {t.events} were funded again.</>}>
          Across FY{d.per_year[0].fy} to FY{silent.length ? silent[0] - 1 : d.span.last_fy},
          {' '}{t.events} lines went from a positive figure to a printed zero, carrying
          {' '}{usd(t.event_dollars)} the year before. {usd(t.returned_dollars)} of that
          came back on the same line in a later year. Anyone quoting a single year&rsquo;s
          zero as a cut is quoting the {Math.round(t.returned / t.events * 100)}% case.
        </Insight>
        <Insight n={2} headline={
          <>{t.stayed} lines went to zero and stayed there &mdash;{' '}
            {usd(t.stayed_dollars)} in all, the largest of them {usd(
              t.biggest_permanent.last_funded)}.</>}>
          The largest is <strong>{t.biggest_permanent.label}</strong>, last funded in
          FY{t.biggest_permanent.last_funded_fy} and printed at zero in every year the book
          shows it afterwards. That is a small sum against a budget that ran from{' '}
          {usd(d.coverage[0].total)} to {usd(d.coverage[d.coverage.length - 1].total)} over
          the same span &mdash; the endings in this book are many and small.
        </Insight>
        <Insight n={3} headline={
          <>The biggest apparent mass ending is the book changing shape.
            {' '}{S.lines_stopped} lines stop after FY{S.fy} while the reported total
            rises.</>}>
          Between FY{S.fy} and FY{S.next_fy} the restated figures move to a different
          district document. The line count falls from {S.lines_before} to {S.lines_after}
          {' '}and the reported total goes <em>up</em> by {usd(S.total_change)}. Lines that
          disappear at that boundary did not take their money with them, and{' '}
          {S.renames_across} of them can be shown to be the same line spelled differently.
        </Insight>
        <Insight n={4} headline={
          <>And the state&rsquo;s own figures do not show the money leaving.
            {roseEverywhere ? ' In all three categories where district lines stopped, '
              + 'DESE reports MORE general fund spending at the end of the span than at '
              + 'the start.' : ''}</>}>
          DESE collects spending from every district to its own definitions and splits it
          into general fund and grants. For {pdev.name.toLowerCase()} the general fund
          figure moves from {usd(pdev.gen_fund_first)} in FY{pdev.overlap_first_fy} to{' '}
          {usd(pdev.gen_fund_last)} in FY{pdev.overlap_last_fy}, and grants reach{' '}
          {Math.round((pdev.grant_share_max ?? 0) * 100)}% of the category at their peak.
          The grains do not join &mdash; a budget line is not a function code &mdash; so
          this corroborates at the category level and settles nothing line by line.
        </Insight>
        <Insight n={5} headline={
          <>For FY{silent[0]} onward this question has no answer in this source.</>}>
          The documents restating the most recent years print almost no zeros &mdash;{' '}
          {d.per_year.find(p => p.fy === silent[0])!.zeros_printed} in a book of{' '}
          {d.coverage.find(c => c.fy === silent[0])!.lines} lines &mdash; and not one line
          in them goes from funded to zero. That is a property of which document restates
          which year. It is not a finding that nothing stopped.
        </Insight>
      </div>

      {/* ------------------------------------------------- 2. organised categorically */}
      <H2 id="by-year">How much stopped, year by year</H2>
      <Body>
        Each bar is the previous year&rsquo;s funding on every line the book took to zero
        that year, split by whether the line was ever funded again. The shaded years print
        so few zeros that nothing can be measured in them either way.
      </Body>
      <ZeroedByYear years={d.per_year} silent={silent} />
      <TableTwin
        caption="The same figures"
        head={['Year', 'Lines in both years', 'Zeros printed', 'Went to zero',
               'Prior-year funding', 'Funded again', 'Stayed at zero']}
        rows={d.per_year.map(p => [
          fy(p.fy), p.lines_both_years, p.zeros_printed,
          silent.includes(p.fy) ? 'not measurable' : p.n,
          silent.includes(p.fy) ? '—' : usd(p.dollars),
          silent.includes(p.fy) ? '—' : `${p.returned_n} · ${usd(p.returned_dollars)}`,
          silent.includes(p.fy) ? '—' : `${p.stayed_n} · ${usd(p.stayed_dollars)}`,
        ])} />
      <NotShown>
        A year&rsquo;s total here is the funding those lines carried <em>the year before</em>
        {' '}they were printed at zero. It is not a saving, and it is not a cut to the
        budget: money removed from one line frequently appears on another, and this book
        does not say which. It is also <strong>net</strong> &mdash; a district budget line
        is what the town has to raise after grants, fees and reimbursements have paid their
        share, so a line falling to zero is equally consistent with a grant taking it over.
      </NotShown>

      <H2 id="what-it-bought">What the money bought</H2>
      <Body>
        The same {usd(t.event_dollars)}, cut by what the district&rsquo;s own line name
        says the money was for. The grouping is <strong>ours</strong>, read off the label
        text; the district publishes no category for these lines.
      </Body>
      <ByCategory cuts={d.categories.zeroed_by_buys} unit="lines" />
      <TableTwin
        caption="Zeroed funding by what the line names"
        head={['What the line names', 'Lines', 'Prior-year funding']}
        rows={d.categories.zeroed_by_buys.map(c => [c.name, c.n, usd(c.dollars)])} />

      <H3>And by the school the line is named for</H3>
      <Body>
        Read off the district&rsquo;s own prefix &mdash; H.S., M.S., E.S., P.S. Lines
        naming no school are district-wide or central, and are reported as naming no
        school rather than assigned to one.
      </Body>
      <TableTwin
        head={['Named for', 'Lines zeroed', 'Prior-year funding']}
        rows={d.categories.zeroed_by_school.map(c => [c.name, c.n, usd(c.dollars)])} />
      <NotShown>
        A school prefix on a budget line says which school the money was budgeted against.
        It does not say where a person worked, and several of these lines are central
        services allocated to a building. Nothing here is a per-school spending total.
      </NotShown>

      <H2 id="shape">The book changed shape, and that is not a cut</H2>
      <Body>
        {S.lines_stopped} line names present in FY{S.fy} are absent from FY{S.next_fy}.
        That is by far the largest apparent ending in the series, and the two panels below
        are why it is not one: the count of printed lines falls and the money does not.
      </Body>
      <ShapeOfTheBook coverage={d.coverage} markFy={S.fy} />
      <TableTwin
        caption="Every year of the restated series"
        head={['Year', 'Lines printed', 'Zeros printed', 'Restated total', 'Documents']}
        rows={d.coverage.map(c => [
          fy(c.fy), c.lines, c.zeros, usd(c.total), c.documents])} />
      <Body>
        FY{S.fy} is restated by {S.documents_before.map(docName).join(', ')}. FY{S.next_fy}
        {' '}is restated by {S.documents_after.map(docName).join(' and ')}. Different
        documents, different line lists, the same district.
      </Body>

      <H3>The rename check, and what it caught</H3>
      <Body>
        Rule 6 of this project exists because a line that goes to zero and reappears under
        a new name produces a &minus;100% rate that looks like a finding. So renames are
        tested for arithmetically rather than by reading the words: two differently-spelled
        lines carrying the <strong>identical value in every fiscal year they share</strong>
        {' '}are one line under two spellings. {renames.length} pairs pass that test.
      </Body>
      <TableTwin
        caption="Established by value — the figures agree to the dollar"
        head={['Stops', 'Last printed', 'Starts', 'First printed', 'Years agreeing',
               'Largest shared figure']}
        rows={renames.map(r => [
          r.older, fy(r.older_last_fy), r.newer, fy(r.newer_first_fy),
          r.shared_years.map(fy).join(', '), usd(r.value)])} />
      <H3>Where no shared year exists, the words are all there is</H3>
      <Body>
        Three of the lines that stop at the FY{S.fy} boundary reappear the next year with a
        letter changed, and there is no overlapping year to settle it arithmetically. These
        are <strong>ours and they are candidates</strong>: near-identical labels for the
        same school, the successor first printed after the predecessor&rsquo;s last year.
      </Body>
      <TableTwin
        caption="Proposed on the labels alone — our reading, not the district's"
        head={['Stops', 'Last printed', 'Last figure', 'Starts', 'First printed',
               'First figure', 'Label similarity']}
        rows={d.spelling_candidates.map(s => [
          s.older, fy(s.older_last_fy), usd(s.older_value), s.newer,
          fy(s.newer_first_fy), usd(s.newer_value), s.similarity.toFixed(3)])} />
      {twins.length > 0 && (
        <>
          <H3>And {twins.length} pairs that are not renames at all</H3>
          <Body>
            The same test also finds pairs where <em>both</em> labels run to the end of the
            series carrying identical figures. That is not a rename and it is not evidence
            of one. Nothing in the document says whether it is one line printed twice or
            two lines that happen to be paid the same.
          </Body>
          <TableTwin
            head={['One label', 'The other', 'Years agreeing', 'Largest shared figure']}
            rows={twins.map(r => [
              r.older, r.newer, r.shared_years.map(fy).join(', '), usd(r.value)])} />
        </>
      )}
      <NotShown>
        A rename check can only find renames where the figures or the words survived. A
        line merged into a larger one, split across two, or moved to a grant leaves no
        trace either test can see. So {d.totals.vanished} lines stop appearing in this
        book across the span and this page does not claim any of them ended &mdash; only
        that {t.renames + t.spelling_candidates} of them demonstrably did not.
      </NotShown>
      <Maybe settle={<>the district&rsquo;s own crosswalk from the FY{S.fy} line list to the
        FY{S.next_fy} presentation, or the MUNIS year-end expense report for those years,
        which is keyed on accounts rather than on printed line names &mdash; registered as
        a gap: <em>{gapShape.what}</em>.</>}>
        The FY{S.next_fy} book may simply present the same spending in fewer, broader lines.
        The rising total is consistent with that, and so is the fact that the categories
        with the most disappearances are the smallest ones. Nothing on this page tests it,
        and the alternative &mdash; that some of those lines really did end &mdash; fits
        the same figures.
      </Maybe>

      <H2 id="dese">A second source, and it does not show the money leaving</H2>
      <Body>
        Everything above this line comes out of the district&rsquo;s own book, which shows
        the general fund and nothing else. DESE collects spending from every district in
        the state to its own definitions and publishes it{' '}
        <strong>split by fund</strong> &mdash; which is precisely the thing the budget book
        structurally cannot show. So for each family of lines that stops on this page, the
        state&rsquo;s figures for the same kind of spending are set beside it.{' '}
        <Basis level="cross-checked">two independent sources, at different grains</Basis>
      </Body>
      <div className="card p-4 mt-5 max-w-2xl" style={{ borderLeft: '4px solid var(--axis)' }}>
        <p className="text-[11px] font-semibold uppercase tracking-widest mb-1.5"
          style={{ color: 'var(--text-muted)' }}>This is not a join, and must not become one</p>
        <p className="text-[14px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
          A district budget line is not a DESE function code. The mapping between them is
          not published by anybody, and this project keeps its <code>crosswalk</code> table
          deliberately empty rather than record an inference as a mapping. The pairing of
          each category to each family of lines below is <strong>ours</strong>, it is read
          at the category level only, and no figure here is subtracted from any figure
          above.
        </p>
      </div>
      {d.dese.map(c => (
        <div key={c.code} className="mt-10">
          <H3>{c.name}</H3>
          <Body>{c.question}</Body>
          <Body>
            Set beside {c.family}. Over the same span as the district&rsquo;s own series,
            FY{c.overlap_first_fy} to FY{c.overlap_last_fy}, the general fund figure goes
            from {usd(c.gen_fund_first)} to {usd(c.gen_fund_last)} &mdash;{' '}
            {c.gen_fund_change >= 0 ? 'up' : 'down'} {usd(Math.abs(c.gen_fund_change))}.
            Grants and revolving funds reach{' '}
            {Math.round((c.grant_share_max ?? 0) * 100)}% of all spending in this category
            at their peak.
          </Body>
          <FundSplit points={c.points} />
          <TableTwin
            caption={`${c.name} — DESE, FY${c.first_fy} to FY${c.last_fy}`}
            head={['Year', 'General fund', 'Grants and revolving', 'All funds',
                   'Grant share']}
            rows={c.points.map(p => [
              fy(p.fy), usd(p.gen_fund), usd(p.grants), usd(p.total),
              p.total ? `${Math.round((p.grants / p.total) * 100)}%` : '—'])} />
        </div>
      ))}
      <NotShown>
        A category total holding up does not mean every service inside it held up.
        DESE&rsquo;s categories are broad, they are collected to the state&rsquo;s
        definitions rather than the district&rsquo;s, and a category can be flat while one
        thing inside it ended and another grew. What this does establish is narrower and
        still worth having: <strong>the money did not leave the category</strong> in the
        years the district&rsquo;s lines for it stopped.
      </NotShown>

      {/* ------------------------------------------------- lines that fell and stayed down */}
      <H2 id="declines">Lines that fell sharply and did not recover</H2>
      <Body>
        Going to zero is the loud version. {t.declines} lines are still printed in
        FY{d.span.last_fy} at half or less of their own peak &mdash; {usd(t.decline_dollars)}
        {' '}of annual funding below where those lines once stood. The test is stated in
        full below the table.
      </Body>
      <TableTwin
        caption={`Still printed in FY${d.span.last_fy}, at or under half their own peak`}
        head={['Line', 'Peak', 'Peak year', 'Recent', 'Fall', 'Down by']}
        rows={d.declines.map(x => [
          x.label, usd(x.peak), fy(x.peak_fy), usd(x.recent), usd(x.fall),
          `${Math.round(x.fall_share * 100)}%`])} />
      <Body>
        <em>Recent</em> is the mean of the last{' '}
        {String(d.definitions.decline_tail)} years the book prints for that line; a line
        qualifies if its own peak reached {usd(Number(d.definitions.decline_floor))} and its
        recent level is at or under {Math.round(Number(d.definitions.decline_share) * 100)}%
        {' '}of it. Those thresholds are <strong>ours</strong>.
      </Body>
      <NotShown>
        The largest fall on this table is {t.biggest_decline.label}, and a tuition line
        falling is not the same kind of event as a supplies line falling: it moves with how
        many children are placed where, which the district does not choose. Falls here are
        equally consistent with fewer placements, with a placement moving to a different
        line, with a reimbursement covering more of the cost, or with the line having been
        over-budgeted. None of those is tested here.
      </NotShown>

      {/* -------------------------------------------- what the town said (rule 15a) */}
      <H2 id="said">What the town said about one of these</H2>
      <Body>
        The meeting archive now runs from {d.minutes.first_date} to{' '}
        {d.minutes.last_date} &mdash; {d.minutes.readable} readable documents out of{' '}
        {d.minutes.published} the town has published &mdash; so it reaches back over the
        whole of the series above. Three things people said sit close enough to a line on
        this page to be worth setting beside it. None of them explains a figure; each of
        them is what a figure looks like from the other side.
      </Body>
      <div className="card p-5 mt-6 max-w-3xl">
        <p className="text-[15px] leading-relaxed italic">&ldquo;{guidanceQuote.quote}&rdquo;</p>
        <p className="text-[12.5px] mt-3" style={{ color: 'var(--text-muted)' }}>
          {guidanceQuote.board}, {guidanceQuote.date} &middot;{' '}
          <a className="underline" style={{ color: 'var(--series-cost)' }}
            href={abs(guidanceQuote.cite)}>our copy</a>{' '}&middot;{' '}
          <a className="underline" style={{ color: 'var(--series-cost)' }}
            href={guidanceQuote.town}>the town&rsquo;s</a>
        </p>
      </div>
      <NamedLines lines={d.guidance} span={span} />
      <TableTwin
        caption="Every guidance counsellor line in the book — a blank is a year the book does not print the line"
        head={['Line', ...span.map(fy)]}
        rows={d.guidance.map(g => [
          g.label,
          ...span.map(f => {
            const p = g.points.find(x => x.fy === f)
            return p ? usd(p.value) : '—'
          })])} />
      <Body>
        {guidanceStopped.length} of the {d.guidance.length} guidance counsellor lines stop
        appearing after FY{Math.max(...guidanceStopped.map(g => g.last_fy))}. The other{' '}
        {guidanceRunning.length} are still printed in FY{d.span.last_fy} &mdash; including{' '}
        {guidanceRunning.map(g => g.label).join(' and ')}. In the same meeting, the same
        speaker said: &ldquo;{socialQuote.quote}&rdquo;
      </Body>
      <NotShown>
        <strong>A budget line is not a filled post.</strong> The Superintendent&rsquo;s
        statement is about people; the book is about dollars, and it is a restatement of a
        year that closed before the meeting. Both can be true at once: a line can be
        printed and unfilled, printed and paid from a grant, or printed under a name that
        no longer describes the job. This project cannot join the two, and that limit is
        registered: <em>{gapFilled.what}</em>.
      </NotShown>
      <H3>The largest permanent ending, and a board meeting five years later</H3>
      <Body>
        {t.biggest_permanent.label} is the largest line on this page that went to a printed
        zero and stayed at zero, last funded in FY{t.biggest_permanent.last_funded_fy}. The
        meeting archive now reaches back far enough to have something to say near it.
      </Body>
      <div className="card p-5 mt-6 max-w-3xl">
        <p className="text-[15px] leading-relaxed italic">&ldquo;{psyQuote.quote}&rdquo;</p>
        <p className="text-[12.5px] mt-3" style={{ color: 'var(--text-muted)' }}>
          {psyQuote.board}, {psyQuote.date} &middot;{' '}
          <a className="underline" style={{ color: 'var(--series-cost)' }}
            href={abs(psyQuote.cite)}>our copy</a>{' '}&middot;{' '}
          <a className="underline" style={{ color: 'var(--series-cost)' }}
            href={psyQuote.town}>the town&rsquo;s</a>
        </p>
      </div>
      <NotShown>
        These are two facts five years apart about posts that may be entirely different
        people in entirely different roles. The page does not join them. What the pair
        shows is the shape of the problem: a post can exist, be paid for, and appear
        nowhere in the document this page is built on, because that document is the
        general fund and nothing else.
      </NotShown>

      <H3>Professional development: five lines to zero, one line up</H3>
      <Body>
        Every per-school professional development line in the book is printed at zero from
        FY{pdZero} onward. The district-wide line is not: it carried{' '}
        {usd(d.prof_development_split.find(r => r.fy === pdZero)!.system)} in FY{pdZero}
        {' '}and {usd(pdLast.system)} in FY{pdLast.fy}. The per-school lines came to{' '}
        {usd(pdPeak.per_school)} at their peak in FY{pdPeak.fy}.
      </Body>
      <NamedLines lines={d.prof_development} span={span} />
      <TableTwin
        caption="Professional development, per school against district-wide"
        head={['Year', `The ${pdLast.per_school_lines} per-school lines`,
               'The district-wide line', 'Lines the book prints']}
        rows={d.prof_development_split.map(r => [
          fy(r.fy), usd(r.per_school), usd(r.system), r.lines_printed])} />
      <div className="card p-5 mt-6 max-w-3xl">
        <p className="text-[15px] leading-relaxed italic">&ldquo;{pdQuote.quote}&rdquo;</p>
        <p className="text-[12.5px] mt-3" style={{ color: 'var(--text-muted)' }}>
          {pdQuote.board}, {pdQuote.date} &mdash; of a DESE grant &middot;{' '}
          <a className="underline" style={{ color: 'var(--series-cost)' }}
            href={abs(pdQuote.cite)}>our copy</a>{' '}&middot;{' '}
          <a className="underline" style={{ color: 'var(--series-cost)' }}
            href={pdQuote.town}>the town&rsquo;s</a>
        </p>
      </div>
      <NotShown>
        Three separate facts sit next to each other here and none of them explains
        another. Five lines go to zero. One line rises. A grant pays for professional
        development in a later year. This page cannot say that the district-wide line
        absorbed the per-school ones, nor that the grant replaced anything &mdash; a
        budget line is <strong>net</strong>, the book shows only the general fund, and no
        published document maps a grant onto a budget line.
      </NotShown>
      <Maybe settle={<>DESE&rsquo;s End of Year Financial Report, which separates spending
        by fund &mdash; registered as <em>{gapLedger.what}</em> in the money-in half of the
        register, and as the grant question throughout this project.</>}>
        The simplest reading is that professional development was consolidated onto one
        district-wide line and that grants now carry part of it. That fits every figure
        above. So does a reading in which the per-school activity stopped and the
        district-wide line grew for its own reasons, and the figures here cannot separate
        the two.
      </Maybe>

      <H3>What was searched, and what came back empty</H3>
      <Body>
        A search that finds nothing prints nothing, and nothing reads as <em>nobody said
        it</em>. It is not: it means nobody said it in the{' '}
        {d.minutes.readable} documents that can be read. Terms that returned meeting
        documents:{' '}
        {found.map(s => `${s.term} (${s.documents})`).join(', ')}.
        {empty.length > 0
          ? ` Terms that returned none at all: ${empty.map(s => s.term).join(', ')}.`
          : ' Every term searched returned at least one document.'}
      </Body>
      <Body>
        And the record itself is thin in places. Of {MC.agendas} School Committee meetings
        the town lists between {MC.first_year} and {MC.last_year}, minutes are published
        for {MC.minutes} &mdash; {Math.round((MC.share ?? 0) * 100)}%. In{' '}
        {MC.years_with_none.join(' and ')} there are none at all, and{' '}
        {MC.years_under_half.length} years sit under half.{' '}
        <strong>A search finding nothing in a year like that is not evidence that nobody
        discussed it.</strong> {d.minutes.published - d.minutes.readable} of the{' '}
        {d.minutes.published} documents cannot be read at all, so no search here covers
        them either.
      </Body>
      <TableTwin
        caption={`${MC.board} minutes published, against meetings listed`}
        head={['Year', 'Meetings listed', 'Minutes published', 'Share']}
        rows={MC.per_year.map(r => [
          r.year, r.agendas, r.minutes,
          r.share === null ? '—' : `${Math.round(r.share * 100)}%`])} />

      {/* --------------------------------------------------------- 3. the raw and the method */}
      <H2 id="permanent">Every line that went to zero and stayed there</H2>
      <TableTwin
        max={520}
        caption={`${t.permanent} lines, ranked by the last figure the book printed for them`}
        head={['Line', 'Last funded', 'Last funded year', 'Printed at zero',
               'What it names', 'School']}
        rows={d.permanent.map(p => [
          p.label, usd(p.last_funded), fy(p.last_funded_fy),
          p.zero_years.map(fy).join(', '), p.buys, p.school])} />

      <H2 id="events">Every zeroing, all {t.events} of them</H2>
      <TableTwin
        max={620}
        head={['Year', 'Line', 'Funding the year before', 'Funded again?', 'What it names']}
        rows={d.events.map(e => [
          fy(e.fy), e.label, usd(e.was),
          e.returned ? `yes — ${fy(e.returned_fy!)} · ${usd(e.returned_value!)}` : 'no',
          e.buys])} />

      <H2 id="vanished">Lines that stop appearing altogether</H2>
      <Body>
        Not the same thing as going to zero, and much weaker evidence. {t.vanished} lines
        stop being printed at some point in the series, carrying {usd(t.vanished_dollars)}
        {' '}in their last printed year &mdash; and {S.lines_stopped} of them stop at the
        single document boundary above.
      </Body>
      <TableTwin
        caption="By the last year the line appears"
        head={['Last printed in', 'Lines', 'Their last figures']}
        rows={d.vanished_by_year.map(v => [fy(v.fy), v.n, usd(v.dollars)])} />
      <NotShown>
        Absence is a fact about a document. Every one of these lines could have been
        renamed, merged, moved to a grant or re-presented, and the count above should be
        read as an upper bound on endings rather than as a count of them. Registered:{' '}
        <em>{gapShape.what}</em>.
      </NotShown>

      <H2 id="what-to-ask">What a board member could do with this</H2>
      <Body>
        One thing, and it is small. <strong>A zero in this book means the line was
        printed at zero. It does not mean the money stopped.</strong> The three routes
        that produce an identical zero &mdash; consolidation onto another line, a grant
        picking it up, and a re-presentation of the whole book &mdash; are all visible
        somewhere in the {d.span.years} years above, and none of them is a cut.
      </Body>
      <Body>
        So the question worth asking when a line shows zero is not <em>why was this
        cut</em>. It is <em>which line is it on now, and which fund is paying</em>. The
        second half of that is the one nobody can currently answer from anything
        published, and it is why {gapLedger.what.toLowerCase()} sits in the register.
      </Body>
      <Body>
        And the thing that would make next year&rsquo;s version of this page far
        stronger costs the district nothing it does not already do: a prior-year column
        printed in the <em>same</em> line shape as the current year. The break at
        FY{S.next_fy} is the whole reason {S.lines_stopped} lines look like endings and
        are not.
      </Body>
      <div className="card p-4 mt-6 max-w-3xl"
        style={{ borderLeft: '4px solid var(--axis)' }}>
        <p className="text-[11px] font-semibold uppercase tracking-widest mb-1.5"
          style={{ color: 'var(--text-muted)' }}>Two things about scope</p>
        <p className="text-[14px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
          <strong>This is the school department only.</strong> Nothing here compares the
          town side with the school side, and nothing here supports that comparison: the
          town codes its accounts by function and the district names its lines, and this
          project refuses to invent the mapping between them.
          {' '}
          <strong>And the district is why this page exists at all.</strong> Publishing a
          restated prior-year column, line by line, for {d.span.years} years is more than
          most districts print &mdash; it is the only reason anyone can see that{' '}
          {t.returned} of {t.events} zeros came back, or that the professional development
          money moved rather than left.
        </p>
      </div>

      <H2 id="method">How this was measured</H2>
      <Body>
        One query, over one table. <code>budget_figure</code> where{' '}
        <code>stage=&lsquo;{d.stage}&rsquo;</code>: {t.lines} lines,
        FY{d.span.first_fy} to FY{d.span.last_fy}, out of {d.span.documents} district
        documents. The same <code>line_key</code> is compared across years and nothing is
        compared across stages &mdash; a budget and a restatement are different quantities
        and this page never differences one against the other.
      </Body>
      <TableTwin
        caption="The words used on this page, as the generator defines them"
        head={['Term', 'What it means here']}
        rows={['zeroing', 'returned', 'permanent', 'vanished', 'rename', 'twin',
               'spelling_candidate', 'decline']
          .filter(k => typeof d.definitions[k] === 'string')
          .map(k => [k.replace(/_/g, ' '), String(d.definitions[k])])} />
      <Body>
        Two rows in the table are printed <em>totals</em> that the extractor read as though
        they were budget lines &mdash; {d.excluded.map(e => `“${e}”`).join(' and ')} &mdash;
        and both are excluded by name. {t.disagreeing_rows} rows are flagged in the database
        as ones where two documents restate the same line and year differently.
      </Body>

      <H2 id="documents">The documents behind this</H2>
      <div className="grid gap-1.5 mt-5">
        {d.documents.map(p => (
          <a key={p} className="text-[13px] underline break-all"
            style={{ color: 'var(--series-cost)' }}
            href={abs(`/docs/${p.replace(/^sources\//, '')}`)}>{docName(p)}</a>
        ))}
      </div>
      <Body>
        The payload this page draws is published whole at{' '}
        <a className="underline" style={{ color: 'var(--series-cost)' }}
          href={abs('/data/stopped-funding.json')}>/data/stopped-funding.json</a>, and the
        rows behind it can be queried directly &mdash; see{' '}
        <a className="underline" style={{ color: 'var(--series-cost)' }}
          href={abs('/database')}>the database</a>.
      </Body>

      <H2 id="cannot">What we still cannot answer</H2>
      <div className="flex flex-col gap-4 mt-6 max-w-3xl">
        {[gapShape, gapRecent, gapFilled, gapLedger].map(g => (
          <div key={g.what} className="card p-4">
            <p className="text-[15px] font-bold leading-snug">{g.what}</p>
            <p className="text-[13.5px] leading-relaxed mt-2"
              style={{ color: 'var(--text-secondary)' }}>{g.why}</p>
            {g.closes && (
              <p className="text-[13.5px] leading-relaxed mt-2">
                <strong>Closes:</strong>{' '}
                <span style={{ color: 'var(--text-secondary)' }}>{g.closes}</span>
              </p>
            )}
          </div>
        ))}
      </div>
      <Body>
        All four are rows in the register at{' '}
        <a className="underline" style={{ color: 'var(--series-cost)' }}
          href={abs('/what-we-cannot-answer')}>what we cannot answer</a>, which is what the
        records request reads &mdash; not prose written only here.
      </Body>
    </div>
  )
}

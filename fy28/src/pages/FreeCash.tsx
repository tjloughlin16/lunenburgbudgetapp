import { useEffect, useState } from 'react'
import { MODEL, usd } from '../model/engine'
import {
  AidSwing, Composition, Multiples, PeerComposition, ThreeNumbers,
  Card, FC, STATE_C, pc,
  type CompRow, type Multiple, type PeerRow, type Versus,
} from '../components/FreeCashCharts'

/** Free cash: where it comes from, whether it is unusual, and why it cannot bend the curve.
 *
 *  WHAT CHANGED AND WHY IT IS ONE PAGE. This was a policy simulator: how much is spendable
 *  and what drawing it down would buy. It is now a drill-in in the shape rule 7b asks for
 *  — conclusions, then the organised data, then the raw — with the simulator kept whole
 *  inside it. It is deliberately NOT a second page: a resident should never have to know
 *  which of two free-cash pages to open, and "where does this money come from" and "what
 *  can it do" are two halves of one question rather than two subjects.
 *
 *  TWO SOURCES, AND THEY ARE KEPT APART. Everything about the projection — the gap, the
 *  ladder, the override contrast — comes from `MODEL.freeCash`, computed by
 *  `model/freecash.py` against `finance.project`. Everything about where free cash comes
 *  from comes from `/data/free-cash.json`, written by `scripts/build_free_cash_charts.py`
 *  out of the Division of Local Services' own proof and the Town's own annual report. The
 *  second is fetched, so if it never arrives the original page still renders whole.
 *
 *  RULE 1. The projection is built from budget columns. Free cash is derived from actuals.
 *  They are subtracted here and nowhere else, and the result is labelled deferral rather
 *  than a closed gap, because the money is one-time by construction.
 *
 *  RULE 11, POINTED AT A RESERVE. A free cash figure is net of everything that has already
 *  claimed it, and the proof shows what it is actually made of: nearly half of five years
 *  of it is money appropriated and not spent, and another ninth is last year's free cash
 *  arriving for a second time. "The town has $X" is never "the town can spend $X a year",
 *  and the page says so at the top rather than in a footnote.
 *
 *  RULE 2. Not one figure in the new material is typed. The old material was already
 *  derived from MODEL, with two exceptions this commit removed: a "2.49×" and a "two of
 *  them fell" that were typed into the prose beside computed figures. Both now come off
 *  the recomputed peer table.
 *
 *  ON THE STYLING, because it was wrong in public for a while. This page and the rate
 *  register shipped with inline styles and no class names at all, which meant neither got
 *  the site's container: content ran to the left edge of the window, headings rendered at
 *  the browser's default size so they read as body text, and sections had no space between
 *  them. Every other page opens with `mx-auto max-w-6xl px-5`, and now so does this one. */

const F = MODEL.freeCash
const pct = (x: number) => `${(x * 100).toFixed(2)}%`
const OC = MODEL.freeCash.overrideContrast!
const LADDER = MODEL.freeCash.policyLadder

/** The roll-forward is printed to the cent and quoted to the cent. `usd` rounds, which is
 *  right for a projection and wrong for a worksheet a reader is checking line by line. */
const usdc = (n: number) =>
  (n < 0 ? '-' : '') + '$' + Math.abs(n).toLocaleString('en-US',
    { minimumFractionDigits: 2, maximumFractionDigits: 2 })

type Payload = {
  generated_by: string
  source: string
  document: {
    what: string; our_copy: string; publisher_filename: string; provenance: string
    sheet: string; rows: string; year_columns: string; ref_note: string
  }
  coverage: {
    towns: string[]; years: number[]; rows: number; town_years: number; lines: number
    cells_checked_against_workbook: number
  }
  crossfoot: {
    tested: number; tied: number; ties_to: string; against: string
    certified_differs: number; chained: number
    rows: {
      town: string; year: number; components: number; identified: number
      certified: number; gap: number; gap_share: number | null
    }[]
  }
  proof: {
    line: string; role: string
    by_year: { year: number; amount: number; ref: string }[]
  }[]
  line_order: string[]
  composition: CompRow[]
  part_order: string[]
  part_labels: Record<string, string>
  totals: {
    years: number; identified: number; certified: number
    by_line: { line: string; amount: number; share: number | null }[]
  }
  peers: PeerRow[]
  multiples: Multiple[]
  receipts: { town_years: number; beat_estimate: number; towns: number; years: number }
  denominator_note: string
  rollforward: {
    fy: number; document: string; url: string; reader: string; reader_path: string
    page: string; printed_page: string; pages_note: string; as_of: string
    opening: { label: string; amount: number }
    above: { label: string; sign: number; amount: number }[]
    subtotal: { label: string; amount: number }
    below: { label: string; sign: number; amount: number }[]
    total: { label: string; amount: number }
  }[]
  versus_dls: Versus[]
  said: {
    key: string; board: string; date: string; agenda: string; quote: string
    beside: string; cite: string; town: string
  }[]
  gaps: { side: string; what: string; why: string }[]
}

/** One figure and its caption, the way every other page states a headline number. */
function Stat({ value, tone, children }: {
  value: string; tone?: string; children: React.ReactNode
}) {
  return (
    <div>
      <div className="text-3xl font-bold tnum tracking-tight"
        style={tone ? { color: tone } : undefined}>{value}</div>
      <div className="text-[13px] leading-snug mt-1 max-w-[15rem]"
        style={{ color: 'var(--text-secondary)' }}>{children}</div>
    </div>
  )
}

function H2({ id, children }: { id?: string; children: React.ReactNode }) {
  return (
    <h2 id={id} className="text-2xl font-bold tracking-tight mt-14 mb-3 max-w-3xl
                           scroll-mt-[calc(var(--header-h)+1rem)]">{children}</h2>
  )
}

function Body({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-[15px] leading-relaxed max-w-2xl mt-3"
      style={{ color: 'var(--text-secondary)' }}>{children}</p>
  )
}

/** The half of a section that says what the data does NOT establish. A distinct shape on
 *  purpose: here the limit is as load-bearing as the finding, and a caveat set in the same
 *  grey as the paragraph above it gets skimmed. */
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

/** An insight, in the shape rule 7b asks for: a claim a reader could repeat, the figure
 *  it rests on, and the query that produced it. */
function Insight({ n, claim, figure, tone, children }: {
  n: number; claim: React.ReactNode; figure: string; tone?: string
  children: React.ReactNode
}) {
  return (
    <div className="card p-5">
      <div className="flex items-baseline gap-3">
        <span className="text-[11px] font-bold tabular-nums"
          style={{ color: 'var(--text-muted)' }}>{String(n).padStart(2, '0')}</span>
        <span className="text-2xl font-bold tracking-tight tnum"
          style={tone ? { color: tone } : undefined}>{figure}</span>
      </div>
      <p className="text-[15.5px] font-semibold leading-snug mt-2">{claim}</p>
      <div className="text-[13.5px] leading-relaxed mt-2"
        style={{ color: 'var(--text-secondary)' }}>{children}</div>
    </div>
  )
}

/** The gap register writes emphasis as `**like this**`, because it is a CSV read by the
 *  API and by the request letter as well as by this page. Rendered by splitting on the
 *  marker rather than by setting HTML: the field is data, and data does not get to choose
 *  what tags a page emits. */
function Marked({ text }: { text: string }) {
  return (
    <>{text.split(/\*\*(.+?)\*\*/g).map((part, i) => (
      i % 2 ? <strong key={i}>{part}</strong> : <span key={i}>{part}</span>
    ))}</>
  )
}

/** What somebody said at a meeting, with the address of the minutes. Every quote here is
 *  checked verbatim against the file it names when the page's data is built — rule 15a
 *  puts what was said beside the measurement, and a quote nobody can find is worse than
 *  no quote at all. */
function Said({ q }: { q: Payload['said'][number] }) {
  return (
    <blockquote className="border-l-[3px] pl-4 text-[15px] leading-relaxed"
      style={{ borderColor: 'var(--surface-3)', color: 'var(--text-secondary)' }}>
      &ldquo;{q.quote}&rdquo;
      <div className="text-[12px] mt-2" style={{ color: 'var(--text-muted)' }}>
        &mdash; {q.board}, {q.date}{q.agenda ? ` · ${q.agenda}` : ''} ·{' '}
        <a className="underline" href={q.cite}>our copy</a> ·{' '}
        <a className="underline" href={q.town}>the Town&rsquo;s</a>
      </div>
    </blockquote>
  )
}

export function FreeCash() {
  // OFF by default. Nothing on this page or anywhere else changes until somebody asks.
  const [on, setOn] = useState(false)
  // LADDER runs high target -> low. Default to the bottom of the recommended band.
  const [idx, setIdx] = useState(LADDER.findIndex(l => Math.abs(l.target - 0.05) < 1e-9))
  const P = LADDER[idx] ?? LADDER[0]

  const [d, setD] = useState<Payload | null>(null)
  const [err, setErr] = useState<string | null>(null)
  useEffect(() => {
    let live = true
    fetch('/data/free-cash.json')
      .then(r => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then(j => { if (live) setD(j) })
      .catch(e => { if (live) setErr(String(e)) })
    return () => { live = false }
  }, [])

  const last = d?.composition[d.composition.length - 1]
  const first = d?.composition[0]
  const lunenburg = d?.peers.find(p => p.town === 'Lunenburg')
  const mult = d?.multiples.find(m => m.town === 'Lunenburg')
  const fell = d?.multiples.filter(m => m.multiple < 1) ?? []
  const unspentTotal = d?.totals.by_line.find(l => l.line.includes('CL#11'))
  const receiptsTotal = d?.totals.by_line.find(l => l.line.includes('CL#6'))
  const recycledTotal = d?.totals.by_line.find(l => l.line.includes('CL#12'))
  const aidTotal = d?.totals.by_line.find(l => l.line.includes('CL#8'))
  const v25 = d?.versus_dls[d.versus_dls.length - 1]
  const swingRank = d ? [...d.peers].sort((a, b) => b.aid_max_swing - a.aid_max_swing) : []
  const said = (k: string) => d?.said.find(s => s.key === k)

  return (
    <div className="mx-auto max-w-6xl px-5 pt-14 pb-16">
      <p className="text-xs font-semibold uppercase tracking-widest mb-3"
        style={{ color: 'var(--text-muted)' }}>One-time money</p>
      <h1 className="text-4xl sm:text-5xl font-bold tracking-tight leading-[1.05] max-w-3xl">
        Free cash &mdash; where it comes from, and how much is actually spendable
      </h1>
      <p className="mt-5 text-lg leading-relaxed max-w-2xl"
        style={{ color: 'var(--text-secondary)' }}>
        Money the town may spend without raising taxes, left over when the books close. It
        is <strong>one-time money by construction</strong> &mdash; a variance, not an income
        stream.
      </p>

      <div className="mt-10 flex flex-wrap gap-x-12 gap-y-6">
        <Stat value={usd(F.certified)}>certified, 1 July 2025 &mdash; a record</Stat>
        <Stat value={pct(F.currentShare)}>
          of a {usd(F.budgetBase)} budget &middot; band is{' '}
          {(F.bandLow * 100).toFixed(0)}&ndash;{(F.bandHigh * 100).toFixed(0)}%
        </Stat>
        {unspentTotal?.share != null && (
          <Stat value={pc(unspentTotal.share)} tone={FC.underspend}>
            of {d!.totals.years} years of it is money the town appropriated and did not spend
          </Stat>
        )}
        {d && (
          <Stat value={`${d.receipts.beat_estimate} of ${d.receipts.town_years}`}
            tone={FC.receipts}>
            town-years in which local receipts came in <em>above</em> the estimate &mdash;
            every year, in every one of the {d.receipts.towns} towns
          </Stat>
        )}
        <Stat value={pct(F.normalShare)}>what a <em>normal</em> year generates</Stat>
      </div>

      {err && (
        <div className="card p-5 mt-8" style={{ borderLeft: '4px solid var(--status-warning)' }}>
          <p className="text-[15px] font-bold mb-1">
            The Division of Local Services series did not load
          </p>
          <p className="text-[13.5px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
            {err}. Nothing on this page is typed into it, so with the file missing there is
            nothing to show rather than something stale. Everything below that is built from
            the projection still renders. The written analysis is at{' '}
            <a className="underline" style={{ color: 'var(--series-cost)' }}
              href="/docs/analyses/free-cash.md">/docs/analyses/free-cash.md</a>.
          </p>
        </div>
      )}

      {/* ==================================================== 1. WHAT THIS ESTABLISHES */}
      {d && last && first && mult && lunenburg && v25 && unspentTotal && receiptsTotal && (
        <>
          <H2 id="insights">What this establishes</H2>
          <Body>
            Four claims a resident could repeat at a meeting. Each is recomputed from the
            Division of Local Services&rsquo; own free cash proof when this page is built,
            and each names the rows it came out of.
          </Body>

          <div className="grid gap-4 mt-6 sm:grid-cols-2">
            <Insight n={1} figure={pc(unspentTotal.share ?? 0)} tone={FC.underspend}
              claim={<>Free cash is not money the town saved. It is mostly money the town
                budgeted and did not spend.</>}>
              Across {d.totals.years} years the largest component is{' '}
              <strong>{d.part_labels.underspend.toLowerCase()}</strong> &mdash;{' '}
              {usd(unspentTotal.amount)} of {usd(d.totals.identified)}. Local receipts coming
              in above the estimate add {usd(receiptsTotal.amount)} (
              {pc(receiptsTotal.share ?? 0)}). Those two lines are{' '}
              {pc((unspentTotal.share ?? 0) + (receiptsTotal.share ?? 0))} of it between
              them.{' '}
              <span style={{ color: 'var(--text-muted)' }}>
                <code>free_cash_proof</code>, {TOWN_LABEL}, rows summed by{' '}
                <code>line</code> across {d.coverage.years[0]}&ndash;
                {d.coverage.years[d.coverage.years.length - 1]}.
              </span>
            </Insight>

            <Insight n={2} figure={`${d.receipts.beat_estimate} of ${d.receipts.town_years}`}
              tone={FC.receipts}
              claim={<>Local receipts have beaten the estimate every single year &mdash; and
                so have all {d.receipts.towns} towns.</>}>
              Lunenburg took in {usd(lunenburg.receipts_total)} more in local receipts than
              it budgeted over {d.receipts.years} years, and never once less. That is the
              measurement behind the local argument that the town estimates too
              conservatively.{' '}
              <strong>It is also true of every town in this set, in every year</strong>, so
              the data cannot tell a Lunenburg stance apart from how municipal revenue is
              estimated in Massachusetts generally.{' '}
              <span style={{ color: 'var(--text-muted)' }}>
                <code>free_cash_proof</code> where <code>line</code> is{' '}
                <code>Excess/Shortfall Local Receipts (CL#6)</code>, all towns, all years.
              </span>
            </Insight>

            <Insight n={3} figure={`${mult.multiple.toFixed(2)}×`} tone={FC.underspend}
              claim={<>The record year was an event, not a stance. Underspending in{' '}
                {d.coverage.years[d.coverage.years.length - 1]} was{' '}
                {mult.multiple.toFixed(2)} times Lunenburg&rsquo;s own recent average.</>}>
              {usd(mult.latest)} against a {d.coverage.years[0]}&ndash;
              {d.coverage.years[d.coverage.years.length - 2]} average of {usd(mult.average)}
              . It is the largest multiple of the {d.multiples.length} towns, and{' '}
              {fell.length} of them <em>fell</em> below their own average in the same year.{' '}
              <span style={{ color: 'var(--text-muted)' }}>
                <code>Add Unencumbered/Unexpended Appropriations (CL#11)</code>, latest year
                divided by each town&rsquo;s own four-year mean.
              </span>
            </Insight>

            <Insight n={4} figure={usd(v25.identified_minus_certified)} tone={STATE_C}
              claim={<>The state&rsquo;s proof adds up exactly &mdash; to a figure that is
                not the one it certifies.</>}>
              In all {d.crossfoot.tested} town-years the component lines sum, to the cent, to
              the workbook&rsquo;s own <code>{d.crossfoot.ties_to}</code>. In all{' '}
              {d.crossfoot.certified_differs} of them the amount actually certified is a
              different number: for Lunenburg in {v25.year} it is{' '}
              {usd(v25.certified)} against {usd(v25.identified)} identified. The workbook
              prints no line reconciling them, and this project holds no document that
              explains the difference.{' '}
              <span style={{ color: 'var(--text-muted)' }}>
                <code>role = 'component'</code> summed against <code>role =
                'identified_total'</code> and <code>role = 'certified'</code>.
              </span>
            </Insight>
          </div>

          <div className="card p-5 mt-6" style={{ borderLeft: '4px solid var(--axis)' }}>
            <p className="text-[14.5px] font-bold mb-1">
              These agree with what this project has already published, and that is worth
              saying.
            </p>
            <p className="text-[13.5px] leading-relaxed"
              style={{ color: 'var(--text-secondary)' }}>
              Every figure above is recomputed from the database at build time rather than
              read off <a className="underline" style={{ color: 'var(--series-cost)' }}
                href="/docs/analyses/free-cash.md">free-cash.md</a>, and the recomputation
              found nothing to correct in it. The generator also re-derives the five figures{' '}
              <code>model/freecash.py</code> carries as typed constants &mdash; the certified
              and identified amounts, the {d.coverage.years[d.coverage.years.length - 1]}{' '}
              unspent line, its four-year average, and all {d.multiples.length} peer
              multiples &mdash; and refuses to write if any of them has drifted from the
              proof it was copied out of.
            </p>
          </div>

          {/* ================================== 2. THE ORGANISED CATEGORICAL DATA */}
          <H2 id="where">Where the money comes from</H2>
          <Body>
            The Division of Local Services publishes a <em>proof</em>, not a summary: the
            components and the total, so the arithmetic can be shown rather than asserted.
            Five years, 1 July {d.coverage.years[0]} to 1 July{' '}
            {d.coverage.years[d.coverage.years.length - 1]}.
          </Body>
          <div className="mt-6">
            <Composition rows={d.composition} labels={d.part_labels} />
          </div>
          <Body>
            The share that is money appropriated and not spent went from{' '}
            {pc(first.shares.underspend ?? 0)} in {first.year} to{' '}
            {pc(last.shares.underspend ?? 0)} in {last.year}. Underneath the whole series,
            local receipts came in above estimate in every one of the {d.receipts.years}{' '}
            years.
          </Body>
          <NotShown>
            <p>
              <strong>Which departments underspent, or why.</strong>{' '}
              {usd(last.underspend)} is one town-wide figure across 67 departments.
              Prudence, a post left vacant, a project that slipped into the next year and a
              line that was over-budgeted from the start are four different facts about the
              world and one number on this page &mdash; and nothing here distinguishes them.
            </p>
            <p className="mt-2">
              <strong>Whether it is the schools&rsquo;.</strong> Free cash is certified for
              the town as a whole. No component is attributed to any department by either
              publisher, so how much of this the school department produced, and how much of
              any appropriation of it reaches the schools, are both unanswered.
            </p>
            <p className="mt-2">
              <strong>That five years of it is five years of new money.</strong> It is not:{' '}
              {recycledTotal && <>{usd(recycledTotal.amount)} of the total (
                {pc(recycledTotal.share ?? 0)}) is <em>last year&rsquo;s</em> free cash,
                certified again because it was never appropriated. </>}
              A stock that rolls forward is counted in each year it rolls through.
            </p>
          </NotShown>

          <H2 id="aid">The state&rsquo;s share is the small one, and the one that swings</H2>
          <Body>
            Cherry sheet receipts &mdash; what the state actually paid against what the
            budget assumed it would &mdash; are {pc(aidTotal?.share ?? 0)} of five years of
            Lunenburg&rsquo;s free cash. They are also the only named component that goes
            negative, and the town has the largest single-year move of the{' '}
            {d.peers.length}: {usd(swingRank[0].aid_max_swing)}.
          </Body>
          <div className="mt-6">
            <AidSwing rows={d.composition} peers={d.peers} town="Lunenburg" />
          </div>
          <NotShown>
            <p>
              <strong>Why the estimate missed.</strong> A cherry sheet shortfall can be the
              state paying less, the Governor&rsquo;s budget landing below what the town
              assumed, a mid-year 9C cut, or a reimbursement programme changing its rules.
              This line is the difference between two numbers and it does not carry the
              reason for either. What the state aid itself does is a different page.
            </p>
          </NotShown>

          {/* ================================= 3. TWO PUBLISHERS, THREE NUMBERS */}
          <H2 id="two-proofs">Two publishers, one balance sheet, three different numbers</H2>
          <Body>
            The Town prints its own version of this arithmetic in the annual report &mdash;
            an <em>Undesignated Fund Balance Roll-forward</em>, for the same 30 June. Both
            worksheets cross-foot exactly to their own printed totals, and one year&rsquo;s
            closing balance is the next year&rsquo;s opening one to the cent. They still
            land on different figures, and nothing published bridges them.
          </Body>
          <Body>
            <strong>Neither document is wrong, and the Town&rsquo;s is worth crediting.</strong>{' '}
            An add/deduct worksheet that ties to its own printed total in both places it
            claims to, in two consecutive annual reports, and hands its closing balance to
            the next year&rsquo;s opening one to the cent, is a well-kept book. The
            difficulty below is that two well-kept books describe the same date and no
            third document joins them.
          </Body>
          <div className="mt-6">
            <ThreeNumbers rows={d.composition} versus={d.versus_dls} />
          </div>
          <div className="grid gap-4 mt-6 lg:grid-cols-2">
            {d.rollforward.map(r => (
              <Card key={r.fy}>
                <p className="text-[13px] font-bold">
                  {r.opening.label.replace(/^Beginning /, 'The Town’s roll-forward, ')} as of{' '}
                  {r.as_of}
                </p>
                <p className="text-[11.5px] mt-0.5 mb-3" style={{ color: 'var(--text-muted)' }}>
                  <code>{r.document}</code> · {r.pages_note} · read from {r.reader}
                </p>
                <table className="w-full text-[12.5px] tnum">
                  <tbody>
                    <tr className="border-t" style={{ borderColor: 'var(--grid)' }}>
                      <td className="py-1">{r.opening.label}</td>
                      <td className="py-1 text-right">{usdc(r.opening.amount)}</td>
                    </tr>
                    {r.above.map(s => (
                      <tr key={s.label} className="border-t" style={{ borderColor: 'var(--grid)' }}>
                        <td className="py-1 pl-4" style={{ color: 'var(--text-secondary)' }}>
                          {s.sign > 0 ? '+' : '−'} {s.label}
                        </td>
                        <td className="py-1 text-right">{usdc(s.amount)}</td>
                      </tr>
                    ))}
                    <tr className="border-t font-semibold"
                      style={{ borderColor: 'var(--axis)' }}>
                      <td className="py-1">{r.subtotal.label}</td>
                      <td className="py-1 text-right">{usdc(r.subtotal.amount)}</td>
                    </tr>
                    {r.below.map(s => (
                      <tr key={s.label} className="border-t" style={{ borderColor: 'var(--grid)' }}>
                        <td className="py-1 pl-4" style={{ color: 'var(--text-secondary)' }}>
                          {s.sign > 0 ? '+' : '−'} {s.label}
                        </td>
                        <td className="py-1 text-right">{usdc(s.amount)}</td>
                      </tr>
                    ))}
                    <tr className="border-t-2 font-bold" style={{ borderColor: 'var(--text-muted)' }}>
                      <td className="py-1.5">{r.total.label}</td>
                      <td className="py-1.5 text-right">{usdc(r.total.amount)}</td>
                    </tr>
                  </tbody>
                </table>
                <p className="text-[11.5px] mt-2" style={{ color: 'var(--text-muted)' }}>
                  Checked when this page was built: the steps sum to both totals the page
                  prints. <a className="underline" href={r.url}>the report</a>
                </p>
              </Card>
            ))}
          </div>
          <NotShown>
            <p>
              <strong>Which of the three is &ldquo;the&rdquo; number, or why they differ.</strong>{' '}
              At 30 June {v25.year} the Town&rsquo;s undesignated fund balance is{' '}
              {usdc(v25.undesignated)}, the state identifies {usd(v25.identified)} of free
              cash, and the state certifies {usd(v25.certified)}. Each worksheet is internally
              exact. <strong>No document in this archive prints a line between any pair of
              them.</strong> An undesignated fund balance and certified free cash are not
              the same quantity &mdash; receivables and deferred revenue sit between them
              &mdash; but the size of that adjustment is not published, and it is not stable:
              it is {usd(Math.abs(v25.undesignated_minus_identified))} in {v25.year} and{' '}
              {usd(Math.abs(d.versus_dls[0].undesignated_minus_identified))} in{' '}
              {d.versus_dls[0].year}.
            </p>
            <p className="mt-2">
              <strong>Earlier years.</strong> The Town has published a roll-forward every
              year; this project has read {d.rollforward.length} of them. The years before
              that are drawn as absent rather than as zero, because the balance existed and
              nobody here has read the page it is printed on.
            </p>
            <p className="mt-2">
              <strong>And the instrument is part of the finding.</strong> The{' '}
              {d.rollforward[0].fy} page has no text layer and is read from{' '}
              {d.rollforward[0].reader}; the {d.rollforward[1].fy} page is read from{' '}
              {d.rollforward[1].reader}. Two different readers, and both are named above
              rather than presented as one source.
            </p>
          </NotShown>

          {/* ========================================== 4. IS LUNENBURG UNUSUAL? */}
          <H2 id="peers">Is Lunenburg unusual? Only in composition &mdash; the level cannot be compared</H2>
          <div className="card p-4 mt-4 max-w-2xl"
            style={{ borderLeft: '4px solid var(--status-warning)' }}>
            <p className="text-[14px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
              {d.denominator_note}
            </p>
          </div>
          <Body>
            So what compares is what each town&rsquo;s free cash is <em>made of</em>, as a
            share of that town&rsquo;s own identified total. One denominator per bar, and it
            is the town&rsquo;s own.
          </Body>
          <div className="mt-6">
            <PeerComposition peers={d.peers}
              year={d.coverage.years[d.coverage.years.length - 1]} />
          </div>
          <Body>
            On this measure Lunenburg is the {ordinal(rank(d.peers, 'Lunenburg',
              d.coverage.years[d.coverage.years.length - 1]))} of {d.peers.length} in{' '}
            {d.coverage.years[d.coverage.years.length - 1]} &mdash; but by a short way, in a
            cluster: {cluster(d.peers, 'Lunenburg',
              d.coverage.years[d.coverage.years.length - 1])}. Averaged over all{' '}
            {d.coverage.years.length} years it is {ordinal(meanRank(d.peers, 'Lunenburg'))}.
            The measure on which it <em>is</em> plainly an outlier is the next one.
          </Body>

          <H2 id="multiples">Against its own history, the record year is the outlier</H2>
          <div className="mt-6">
            <Multiples rows={d.multiples}
              year={d.coverage.years[d.coverage.years.length - 1]}
              base={`${d.coverage.years[0]}–${d.coverage.years[d.coverage.years.length - 2]}`} />
          </div>
          <NotShown>
            <p>
              <strong>Whether these nine towns are the right comparison.</strong> They were
              chosen as comparable and the choice is ours; nothing in the data makes them a
              peer group. A ratio against a town&rsquo;s own history does not depend on that
              choice, which is why the page leans on it.
            </p>
            <p className="mt-2">
              <strong>Whether {mult.multiple.toFixed(2)}× means anything went wrong.</strong>{' '}
              It does not. A multiple is a comparison with a four-year average and a
              four-year average is a short one; one large project slipping across a year end
              would produce this. What it rules out is the reading that this level of free
              cash is normal for Lunenburg and can be counted on again.
            </p>
          </NotShown>

          {/* ==================================== 5. WHAT THE TOWN SAID ABOUT IT */}
          <H2 id="said">What the town said, in the same years</H2>
          <Body>
            Both halves of the local argument are on the record, and the measurements above
            are the test of one of them. Every quote is checked against the minutes file it
            names when this page is built.
          </Body>
          <div className="grid gap-5 mt-6 max-w-3xl">
            {['missing_out', 'not_lost', 'conservative', 'review_policy',
              'budgeted_conservatively', 'stopgap', 'certified'].map(k => {
                const q = said(k)
                return q ? <Said key={k} q={q} /> : null
              })}
          </div>
          <div className="card p-5 mt-6 max-w-3xl"
            style={{ borderLeft: '4px solid var(--axis)' }}>
            <p className="text-[14.5px] font-bold mb-1">
              &ldquo;Where did our money go?&rdquo; &mdash; what this page can and cannot
              tell a School Committee member
            </p>
            <p className="text-[13.5px] leading-relaxed"
              style={{ color: 'var(--text-secondary)' }}>
              It can tell them the size and the shape of the town-wide figure: in{' '}
              {last.year}, {usd(last.underspend)} of appropriations went unspent, which is{' '}
              {pc(last.shares.underspend ?? 0)} of the free cash certified from that year.
              It cannot tell them <strong>how much of that was the schools&rsquo;</strong>,
              because neither the state&rsquo;s proof nor the Town&rsquo;s roll-forward
              attributes a single dollar of it to a department &mdash; and that is a
              registered gap with a named remedy below, not a matter of interpretation.
              The school department&rsquo;s own year-end position, at the level of accounts,
              is a different measurement and it is on{' '}
              <a className="underline" style={{ color: 'var(--series-cost)' }}
                href="/budget-vs-actual">budgets against actuals</a>.
            </p>
          </div>
          <Body>
            The Finance Committee&rsquo;s own reading of local receipts and the state&rsquo;s
            proof are two independent routes to the same measurement, and they agree: the
            estimate has been beaten every year. What neither settles is whether that is a
            choice.{' '}
            <strong>Every one of the {d.receipts.towns} towns did the same thing in every
            one of the {d.receipts.years} years</strong>, which is what a convention looks
            like and also what nine independently conservative towns would look like.
          </Body>
        </>
      )}

      {/* ================================= 6. SO WHAT CAN BE DONE WITH IT (as before) */}
      <H2 id="policy">So what could the town actually do with it?</H2>
      <Body>
        Everything below is the projection, which is built from <strong>budget</strong>{' '}
        columns; everything above is derived from <strong>actuals</strong>. They are
        subtracted once, here, and the result is a deferral rather than a closed gap.
      </Body>

      <section className="card p-5 mt-6 max-w-3xl">
        <label className="flex gap-2 items-center font-bold text-[15px]">
          <input type="checkbox" checked={on} onChange={e => setOn(e.target.checked)} />
          Try it as a policy
        </label>
        <p className="text-[13px] leading-relaxed mt-2 mb-5"
          style={{ color: 'var(--text-secondary)' }}>
          Off by default, and off everywhere else on this site. The published projection is
          built without free cash.
        </p>

        <div style={{ opacity: on ? 1 : .45, pointerEvents: on ? 'auto' : 'none' }}>
          <label htmlFor="fc" className="block font-bold text-[15px]">
            Hold the balance at {(P.target * 100).toFixed(0)}% of the budget
          </label>
          <div className="text-[13px] mt-0.5 mb-2"
            style={{ color: P.inBand ? 'var(--status-good)' : 'var(--text-secondary)' }}>
            {P.label}
          </div>
          <input id="fc" type="range" min={0} max={LADDER.length - 1} step={1}
            className="w-full"
            value={LADDER.length - 1 - idx}
            onChange={e => setIdx(LADDER.length - 1 - Number(e.target.value))} />
          <div className="flex justify-between text-[11px] mt-1"
            style={{ color: 'var(--text-muted)' }}>
            <span>0% &mdash; nothing held</span><span>5&ndash;7% band</span><span>8%</span>
          </div>
        </div>

        {on && (
          <div className="mt-6">
            <div className="flex flex-wrap gap-x-10 gap-y-4 mb-5">
              <div>
                <div className="text-xl font-bold tnum">{usd(P.oneTime)}</div>
                <div className="text-[12px] mt-0.5 max-w-[16rem]"
                  style={{ color: 'var(--text-secondary)' }}>
                  released once, by moving to this level
                </div>
              </div>
              <div>
                <div className="text-xl font-bold tnum">{usd(P.annual)}</div>
                <div className="text-[12px] mt-0.5 max-w-[16rem]"
                  style={{ color: 'var(--text-secondary)' }}>
                  every year, by holding it there instead of accumulating
                </div>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-[13px] tnum">
                <thead>
                  <tr style={{ color: 'var(--text-muted)' }}>
                    <th className={TH_L}>FY</th>
                    <th className={TH}>gap</th>
                    <th className={TH}>free cash used</th>
                    <th className={TH}>gap after</th>
                  </tr>
                </thead>
                <tbody>
                  {P.years.map(y => (
                    <tr key={y.fy} className="border-t"
                      style={{ borderColor: 'var(--surface-3)' }}>
                      <td className="py-1 font-semibold">FY{y.fy}</td>
                      <td className="py-1 pl-3 text-right">{usd(y.before)}</td>
                      <td className="py-1 pl-3 text-right"
                        style={{ color: y.applied > 0 ? 'var(--status-good)' : 'inherit' }}>
                        {y.applied > 0 ? `−${usd(y.applied)}` : '—'}
                      </td>
                      <td className="py-1 pl-3 text-right">{usd(y.after)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </section>

      <H2>The level you hold barely matters. The policy is everything.</H2>
      <Body>
        Move the slider and watch the second number stay still. That is the finding, and it
        is the opposite of how the argument is usually made.
      </Body>
      <ul className="mt-4 grid gap-3 max-w-2xl">
        <li className="card p-4 text-[14px] leading-relaxed"
          style={{ color: 'var(--text-secondary)' }}>
          <strong style={{ color: 'var(--text-primary)' }}>Holding a lower balance is a
          one-off.</strong> Going from today&rsquo;s {pct(F.currentShare)} to the bottom of
          the band releases{' '}
          {usd(LADDER.find(l => Math.abs(l.target - F.bandLow) < 1e-9)!.oneTime)} &mdash;
          once. Going below that releases more on paper and achieves nothing, because you
          cannot apply more free cash to a year than that year&rsquo;s gap, and
          FY{F.deficits[0].fy}&rsquo;s gap is only {usd(F.deficits[0].amount)}.
        </li>
        <li className="card p-4 text-[14px] leading-relaxed"
          style={{ color: 'var(--text-secondary)' }}>
          <strong style={{ color: 'var(--text-primary)' }}>Appropriating the flow every year
          is the policy</strong>, and it is worth far more: it takes the six-year gap from{' '}
          {usd(LADDER[0].gapLeftOneTimeOnly)} to {usd(LADDER[0].gapLeftWithPolicy)}.{' '}
          <strong style={{ color: 'var(--text-primary)' }}>And it does not depend on the
          target at all.</strong> A lower target does not generate more money. It releases
          the accumulated stock sooner, and then you are living on the flow either way.
        </li>
      </ul>

      <H2>The catch, and it is the whole argument</H2>
      <Body>
        That {usd(F.sustainableDraw)} a year is what an ordinary year generates &mdash;{' '}
        {pct(F.normalShare)} of the budget, <strong>below the bottom of the band</strong>.
        And two thirds of it is money that was appropriated and never spent.
      </Body>
      <p className="text-[15px] leading-relaxed max-w-2xl mt-4 font-semibold">
        So the policy is self-cancelling at the edges: the flow you would spend every year is
        produced by the over-appropriating you would be trying to stop. Budget more tightly
        and the gap shrinks &mdash; but so does the free cash you were going to close it
        with. You cannot bank on both.
      </p>

      <H2>It changes the amount, not the direction</H2>
      <Body>
        This site&rsquo;s argument is that cuts change the amount and only rates change the
        direction. <strong>Free cash is in the same category as a cut, and weaker</strong>
        {' '}&mdash; a cut persists year after year; free cash is spent once and gone. The gap
        grows by roughly {usd(Math.round(F.deficits[1].amount - F.deficits[0].amount))} a
        year, so even <em>emptying the entire reserve</em> &mdash; drawing to 0%, which
        nobody proposes &mdash; defers the problem two years and leaves the town with no
        reserve at all.
      </Body>

      <H2>Is this the same as an override? No &mdash; they are opposites</H2>
      <Body>
        The same dollars, spent once versus raised permanently. An override lifts the levy
        limit for good and the schools keep it every year after, growing at the{' '}
        {(OC.levyCap * 100).toFixed(1)}% cap. Free cash is spent and gone.
      </Body>
      <div className="overflow-x-auto mt-5 max-w-3xl">
        <table className="w-full text-[13px] tnum">
          <thead>
            <tr style={{ color: 'var(--text-muted)' }}>
              <th className={TH_L}>FY</th>
              <th className={TH}>gap</th>
              <th className={TH}>after {usd(OC.amount)} of free cash</th>
              <th className={TH}>after the same as an override</th>
            </tr>
          </thead>
          <tbody>
            {OC.years.map(y => (
              <tr key={y.fy} className="border-t" style={{ borderColor: 'var(--surface-3)' }}>
                <td className="py-1 font-semibold">FY{y.fy}</td>
                <td className="py-1 pl-3 text-right">{usd(y.deficit)}</td>
                <td className="py-1 pl-3 text-right">{usd(y.afterFreeCash)}</td>
                <td className="py-1 pl-3 text-right">{usd(y.afterOverride)}</td>
              </tr>
            ))}
            <tr className="border-t-2 font-bold" style={{ borderColor: 'var(--text-muted)' }}>
              <td className="py-1.5">six-year total</td>
              <td className="py-1.5 pl-3 text-right">{usd(OC.cumulativeNone)}</td>
              <td className="py-1.5 pl-3 text-right">{usd(OC.cumulativeFreeCash)}</td>
              <td className="py-1.5 pl-3 text-right">{usd(OC.cumulativeOverride)}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <Body>
        Identical dollars. Over six years the override is worth{' '}
        <strong>{usd(OC.cumulativeFreeCash - OC.cumulativeOverride)}</strong> more, because
        it arrives every year and free cash arrives once.
      </Body>
      <Body>
        <strong>But look at the last column, not the total.</strong> Even the override does
        not close the gap &mdash; it leaves{' '}
        {usd(OC.years[OC.years.length - 1].afterOverride)} in
        FY{OC.years[OC.years.length - 1].fy}, and the shortfall grows every year. An override
        rises at {(OC.levyCap * 100).toFixed(1)}%; the cost of running the schools rises
        faster. A permanent revenue increase loses ground more slowly than one-time money
        does, and still loses ground. That is the whole argument of this site in one table:
        only a change in the growth rates changes the direction.
      </Body>

      <H2>And a normal year does not refill it</H2>
      <Body>
        The {pct(F.currentShare)} exists because one component was unusually large. Unspent
        appropriations in 2025 were <strong>{usd(F.unspent2025)}</strong> against a
        2021&ndash;24 average of {usd(F.unspentAvg)}
        {mult ? <> &mdash; <strong>{mult.multiple.toFixed(2)}&times;</strong>, the biggest
          jump of {d!.multiples.length} comparable towns, while {fell.length} of them
          fell</> : null}
        . Hold everything else constant and put that one line back at its own average, and
        the town certifies <strong>{usd(F.normalCertified)}</strong>, which is{' '}
        <strong>{pct(F.normalShare)}</strong> &mdash; below the bottom of the band.
      </Body>
      <Body>
        That is the strongest thing in this data. Not that the balance is low, but that{' '}
        <strong>the flow which refills it does not clear the floor in an ordinary
        year</strong>. You can draw down to 5% once. Holding 5% while spending requires the
        underspending to continue &mdash; which would mean the budgeting problem continuing.
      </Body>

      <H2>Two claims, both true, different windows</H2>
      <blockquote className="border-l-[3px] pl-4 mt-5 max-w-2xl text-[15px] leading-relaxed"
        style={{ borderColor: 'var(--surface-3)', color: 'var(--text-secondary)' }}>
        &ldquo;This year, Lunenburg certified a record $3.354 million in free cash &mdash;
        6.65% of the operating budget &mdash; well within DLS recommendations.{' '}
        {F.townHistory}&rdquo;
        <div className="text-[12px] mt-2" style={{ color: 'var(--text-muted)' }}>
          &mdash; Town of Lunenburg, FY27 budget press release, page 6
        </div>
      </blockquote>
      <Body>
        Somebody saying the town is sitting on money is describing this year. Somebody saying
        it is rebuilding is describing the decade. Neither has to be wrong.
      </Body>

      {/* ==================================================== 7. THE RAW, AND THE SOURCE */}
      {d && (
        <>
          <H2 id="raw">The proof itself, cell by cell</H2>
          <Body>
            Every row of Lunenburg&rsquo;s free cash proof, with the coordinate each amount
            was read from. {d.coverage.cells_checked_against_workbook} of these cells are
            re-opened in the workbook and matched against this table when the page is built.
          </Body>
          <div className="card p-4 mt-6 overflow-x-auto">
            <table className="w-full text-[12.5px] tnum">
              <caption className="sr-only">
                Lunenburg free cash proof, every line, every year, with cell references
              </caption>
              <thead>
                <tr className="text-left" style={{ color: 'var(--text-muted)' }}>
                  <th className="font-semibold py-1.5">Line, as the workbook prints it</th>
                  {d.coverage.years.map(y => (
                    <th key={y} className="font-semibold py-1.5 text-right">{y}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {d.proof.map(r => (
                  <tr key={r.line} className="border-t" style={{ borderColor: 'var(--grid)' }}>
                    <td className="py-1.5 pr-3"
                      style={{
                        fontWeight: r.role === 'component' ? 400 : 700,
                        color: r.role === 'component'
                          ? 'var(--text-secondary)' : 'var(--text-primary)',
                      }}>
                      {r.line}
                    </td>
                    {r.by_year.map(v => (
                      <td key={v.year} className="py-1.5 text-right">
                        <span title={v.ref}>{usd(v.amount)}</span>
                        <span className="block text-[10px]" style={{ color: 'var(--text-muted)' }}>
                          {v.ref}
                        </span>
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="card p-4 mt-5 max-w-3xl text-[13px] leading-relaxed"
            style={{ color: 'var(--text-secondary)' }}>
            <p className="font-bold text-[14px]" style={{ color: 'var(--text-primary)' }}>
              Where this came from
            </p>
            <p className="mt-2">
              {d.document.what}. Our copy:{' '}
              <a className="underline" style={{ color: 'var(--series-cost)' }}
                href={d.document.our_copy}>{d.document.our_copy}</a>; the publisher&rsquo;s
              own filename was <code>{d.document.publisher_filename}</code>. How it reached
              us, and what is still unknown about that, is in{' '}
              <a className="underline" style={{ color: 'var(--series-cost)' }}
                href={d.document.provenance}>PROVENANCE.md</a>. Sheet{' '}
              <code>{d.document.sheet}</code>, rows {d.document.rows}, with the years across{' '}
              <code>{d.document.year_columns}</code>.
            </p>
            <p className="mt-2">
              <strong>One note about the coordinates, because it is exactly the kind of
              thing this project gets wrong.</strong> {d.document.ref_note}
            </p>
            <p className="mt-2">
              Two identities are re-checked before this page will build:{' '}
              {d.crossfoot.tied} of {d.crossfoot.tested} town-years in which the components
              sum to <code>{d.crossfoot.ties_to}</code>, and {d.crossfoot.chained} in which
              one year&rsquo;s <code>{d.crossfoot.against}</code> is the next year&rsquo;s{' '}
              <code>Free Cash Certified Prior Year</code>. Both tie to the dollar across all{' '}
              {d.coverage.towns.length} towns.
            </p>
          </div>

          <H2 id="cannot">What this cannot answer</H2>
          <Body>
            Every limit above is registered rather than only written here, so it reaches the
            request letter, the API and{' '}
            <a className="underline" style={{ color: 'var(--series-cost)' }}
              href="/what-we-cannot-answer">/what-we-cannot-answer</a> as well as this page.
          </Body>
          <ul className="mt-5 grid gap-3 max-w-3xl">
            {d.gaps.map(g => (
              <li key={g.what} className="card p-4 text-[14px] leading-relaxed"
                style={{ color: 'var(--text-secondary)' }}>
                <span className="text-[10.5px] font-bold uppercase tracking-widest mr-2"
                  style={{ color: 'var(--text-muted)' }}>{g.side.replace('_', ' ')}</span>
                <strong style={{ color: 'var(--text-primary)' }}>{g.what}.</strong>{' '}
                <Marked text={g.why} />
              </li>
            ))}
          </ul>
        </>
      )}

      <H2>What is ours, and what is not</H2>
      <ul className="mt-4 grid gap-3 max-w-2xl">
        {[
          [<>The band is single-sourced.</>, <>{F.bandSource} At a lower threshold this
            balance is above the range rather than inside it, and the count of years the
            town fell short moves with it.</>],
          [<>The denominator is soft.</>, <>The Town publishes 6.65%, implying a base of{' '}
            {usd(F.townImpliedBase)}; the FY26 original appropriation gives{' '}
            {pct(F.currentShare)} and the revised budget slightly less. We cannot reproduce
            the Town&rsquo;s base.</>],
          [<>The years are labelled differently.</>, <>{F.yearOffsetNote}</>],
          [<>The projection and free cash never meet in a calculation.</>, <>The gap is
            built from budget columns; free cash is derived from actuals. They are placed
            side by side and subtracted, and the result is deferral, not a closed gap.</>],
          [<>No breakdown exists.</>, <>For the {usd(F.unspent2025)} of unspent
            appropriations there is a town-wide total across 67 departments and nothing
            more. Whether it is a few departments with vacancies or a systematic
            over-appropriation is the one question that would settle the argument, and
            nobody publishes it.</>],
        ].map(([head, body], i) => (
          <li key={i} className="card p-4 text-[14px] leading-relaxed"
            style={{ color: 'var(--text-secondary)' }}>
            <strong style={{ color: 'var(--text-primary)' }}>{head}</strong> {body}
          </li>
        ))}
      </ul>

      {d && (
        <p className="text-[12px] mt-10 max-w-3xl" style={{ color: 'var(--text-muted)' }}>
          The series on this page are generated by <code>{d.generated_by}</code> from{' '}
          {d.source}. {d.coverage.rows} rows, {d.coverage.towns.length} towns,{' '}
          {d.coverage.years.length} years, {d.coverage.lines} lines each.
        </p>
      )}
    </div>
  )
}

const TH = 'text-right font-bold uppercase tracking-widest text-[10px] pb-1 pl-3'
const TH_L = 'text-left font-bold uppercase tracking-widest text-[10px] pb-1'
const TOWN_LABEL = <code>town = 'Lunenburg'</code>

/** Where a town sits on the underspending share in a given year, 1 being the highest. */
function rank(peers: PeerRow[], town: string, year: number): number {
  const at = (p: PeerRow) => p.unspent_share.find(x => x.year === year)?.share ?? 0
  return [...peers].sort((a, b) => at(b) - at(a)).findIndex(p => p.town === town) + 1
}

/** The towns within five points of a given town on the same measure, named with their
 *  figures. A rank on its own says "first of nine" and hides whether first is a long way
 *  clear or a rounding away from second — which is the difference between an outlier and
 *  a member of a cluster. */
function cluster(peers: PeerRow[], town: string, year: number): string {
  const at = (p: PeerRow) => p.unspent_share.find(x => x.year === year)?.share ?? 0
  const me = at(peers.find(p => p.town === town)!)
  const near = peers.filter(p => p.town !== town && Math.abs(at(p) - me) <= 0.05)
    .sort((a, b) => at(b) - at(a))
  return near.length
    ? `${pc(me)} against ${near.map(p => `${p.town} ${pc(at(p))}`).join(', ')}`
    : `${pc(me)}, with no other town within five points`
}

/** Where a town sits on the mean over every year, which is a different question from
 *  where it sits in the latest one — and here the two answers differ. */
function meanRank(peers: PeerRow[], town: string): number {
  return [...peers].sort((a, b) => b.unspent_mean - a.unspent_mean)
    .findIndex(p => p.town === town) + 1
}

const ORDINALS = ['', 'highest', 'second highest', 'third highest', 'fourth highest',
  'fifth highest', 'sixth highest', 'seventh highest', 'eighth highest', 'ninth highest']
const ordinal = (n: number) => ORDINALS[n] ?? `${n}th highest`

import { useMemo, useState } from 'react'
import type { Tab } from '../routes'
import { abs } from '../lib/abs'
import { usd } from '../model/engine'
import { Basis } from '../components/Basis'
import {
  Body, Conclusions, Coverage, H2, H3, Insight, Maybe, NotEstablished, NotShown,
  Quote, ReportShell, Section, Stat, useReport,
} from '../components/report'
import type { Conclusion, Minutes, Said } from '../components/report'

/** THE CUT REGISTER — what the schools said they were cutting, and whether it shows.
 *
 *  TWO LAYERS, DRAWN DIFFERENTLY ON PURPOSE, AND NEVER ADDED TOGETHER.
 *
 *  Layer one is a CLAIM: a reduction list is a document somebody assembled to argue for a
 *  budget, and rule 13a says the slide number and the letterhead are not provenance. It is
 *  the district's own words about its own intent, which is exactly why it is worth
 *  publishing — and it is not evidence that a post was removed. Every row on this page
 *  carries `stated`.
 *
 *  Layer two is what an INSTRUMENT recorded afterwards, by somebody who was not in the
 *  argument: DESE's teacher FTE by school and subject, submitted through EPIMS on the
 *  first of October. It reaches a minority of these rows and the page says so in the
 *  second sentence rather than in a footnote.
 *
 *  RULE 8 IS THE HARD PART HERE AND IT GOVERNS EVERY SECTION. A cut announced and not
 *  visible afterwards is not a lie. The district's own FY25 slides say twice that a
 *  reduction "will be absorbed by a retirement"; the FY2020 record shows two positions
 *  withdrawn in public three weeks after they were listed; a grant can pay for a post and
 *  a timetable can move FTE between subjects. The page names those readings every time it
 *  reports a divergence, and it never says anybody got anything wrong.
 *
 *  RULE 7a. It opens with the register and the two counts. The method is at the bottom.
 *
 *  RULE 2. Not one figure is typed into this file. Everything arrives from
 *  /data/cut-register.json, written by scripts/build_cut_register.py, which refuses to
 *  write on eight separate conditions rather than publishing a page about nothing.
 *
 *  NO D1 AT PAGE LOAD. One static file. */

const TAB: Tab = 'cuts'
const DATA = '/data/cut-register.json'
const TITLE = 'The cut register'

type Row = {
  fy: number; doc_date: string; doc_title: string; stage: string; block: string
  direction: string; conditional_on: string; printed: string; position: string
  school: string; school_printed: string; fte: number | null; amount: number | null
  consequence: string; page: number; doc_text: string; doc_pdf: string; sha256: string
  basis: string; operative: boolean; verdict: string; instrument: string
  subject?: string | null; before?: number | null; after?: number | null
  change?: number | null; before_fy?: number | null; after_fy?: number | null
  reason?: string | null
}

type Doc = {
  doc_date: string; fy: number; title: string; stage: string; path: string
  text: string; sha256: string; docs_url: string; rows: number
}

type CycleDoc = {
  doc_date: string; doc_title: string; stage: string; doc_text: string; doc_pdf: string
  sha256: string; rows: number; reductions: number; restorations: number
  with_amount: number; with_fte: number; with_consequence: number
}

type Payload = {
  conclusions: Conclusion[]
  generated_by: string
  source: string
  about: string
  grain: string
  span: {
    first_fy: number; last_fy: number; cycles: number; documents: number; rows: number
    instrument_first_fy: number; instrument_last_fy: number
  }
  definitions: {
    stated: string; operative: string; instrument: string; moved_with: string
    other_way: string; unresolved: string; blind: string
    tolerance: number; unstated_move: number
    subject_map: { subject: string; pattern: string }[]
    unmeasured_pattern: string
  }
  documents: Doc[]
  cycles: {
    fy: number; documents: CycleDoc[]; n_documents: number; rows: number
    operative_date: string; operative_conditional: string
  }[]
  per_year: {
    fy: number; rows: number; documents: number; reductions: number
    restorations: number; operative: number; operative_fte: number
    operative_amount: number; moved_with: number; moved_other: number
    unresolved: number; blind: number; not_yet: number
  }[]
  categories: {
    by_school: { name: string; n: number }[]
    by_verdict: { name: string; n: number }[]
    operative_by_school: { name: string; n: number }[]
    by_direction: { name: string; n: number }[]
  }
  rows: Row[]
  totals: {
    rows: number; reductions: number; restorations: number; documents: number
    cycles: number; with_amount: number; with_fte: number; with_consequence: number
    operative: number; measurable: number; moved_with: number; moved_other: number
    unresolved: number; blind: number; not_yet: number
    blind_share: number; agree_share: number
  }
  fy2020: {
    named_march: number; named_april: number
    withdrawn: { school: string; printed: string; position: string; consequence: string
      fte: number | null; page: number; doc_text: string }[]
    restored_by_memo: { printed: string; school: string; page: number; doc_text: string
      consequence: string }[]
    march_date: string; memo_date: string; final_date: string
    march_schools: number; weeks_between: number
    lhs_foreign: Series; lms_foreign: Series
    primary_librarian: {
      label: string; stage: string; points: { fy: number; value: number }[]
      first_funded_fy: number
    }
  }
  fy2025: {
    without: number; with_override: number; saved: number; esser: number; paired: number
    pairs: { esser: string; with_override: string; esser_page: number
      override_page: number }[]
    unpaired: string
    stated_full_time_cut: number; stated_full_time_retained: number
    reconciles: string; excluded_not_a_post: string
    ballot: { date: string; yes: number; no: number; result: string; purpose: string }
    without_rows: { printed: string; school: string; page: number }[]
    with_rows: { printed: string; school: string; page: number; verdict: string
      instrument: string; reason: string }[]
  }
  fy2026: {
    row: { printed: string; school: string; page: number; doc_text: string
      verdict: string; instrument: string; before: number; after: number; change: number }
    approved: number
    district: { before_fy: number; after_fy: number; before: number; after: number
      change: number }
    other_way: { printed: string; school: string; instrument: string; before: number
      after: number; change: number }[]
  }
  said: Said[]
  searched: { term: string; documents: number }[]
  minutes: Minutes
  gaps: { side: string; what: string; why: string; closes: string | null }[]
  not_established: string[]
  closes: string
}

type Series = {
  subject: string; org: string; before_fy: number; after_fy: number
  before: number; after: number; change: number
}

const SCHOOL_LABEL: Record<string, string> = {
  'primary': 'Primary School',
  'turkey-hill': 'Turkey Hill Elementary',
  'middle': 'Middle School',
  'high': 'High School',
  'mid-high': 'Middle/High School',
  'ace': 'ACE',
  'district': 'District wide',
  'athletics': 'Athletics',
  'primary-and-turkey-hill': 'Primary and Turkey Hill',
  'high-and-primary': 'High School and Primary',
  'middle-and-high': 'Middle and High School',
  'not stated': 'No school named',
}
const school = (k: string) => SCHOOL_LABEL[k] ?? k

/** The verdict palette. A confirmation and a contradiction must not read as the same kind
 *  of statement, and `cannot see` must not read as a failure — it is the honest majority
 *  answer on this page and it is drawn as a neutral, not as a warning. */
const VERDICT_TONE: Record<string, string> = {
  'the instrument moved with it': 'var(--status-good)',
  'the instrument moved the other way': 'var(--status-bad)',
  'the instrument does not resolve it': 'var(--status-warning)',
  'cannot see at this grain': 'var(--text-muted)',
  'not yet measurable': 'var(--text-muted)',
}
const VERDICT_SHORT: Record<string, string> = {
  'the instrument moved with it': 'moved with it',
  'the instrument moved the other way': 'moved the other way',
  'the instrument does not resolve it': 'does not resolve',
  'cannot see at this grain': 'cannot see',
  'not yet measurable': 'too early',
}

const fyLabel = (n: number) => `FY${n}`
const num = (n: number) => n.toLocaleString()
const fte = (n: number | null | undefined) =>
  n === null || n === undefined ? '' : String(n)

function Tag({ tone, children }: { tone: string; children: React.ReactNode }) {
  return (
    <span className="text-[10.5px] font-bold uppercase tracking-wider px-1.5 py-0.5
                     rounded border whitespace-nowrap"
      style={{ color: tone, borderColor: tone }}>{children}</span>
  )
}

export function CutRegister() {
  const { d, err } = useReport<Payload>('cut-register.json')
  const [openFy, setOpenFy] = useState<number | null>(null)
  const [onlyAdopted, setOnlyAdopted] = useState(false)

  const rows = useMemo(
    () => (d ? d.rows.filter(r => !onlyAdopted || r.operative) : []),
    [d, onlyAdopted])

  if (err) return <ReportShell tab={TAB} title={TITLE} dataUrl={DATA} err={err} />
  if (!d) return <ReportShell tab={TAB} title={TITLE} dataUrl={DATA} loading />

  const t = d.totals
  const tested = t.moved_with + t.moved_other + t.unresolved
  const a = d.fy2020
  const b = d.fy2025
  const c = d.fy2026
  const retirement = d.said.find(q => q.key === 'retirement')!
  const layoffs = d.said.find(q => q.key === 'layoffs')!
  const dispute = d.said.find(q => q.key === 'staffing-dispute')!
  const restores = d.said.filter(q => q.key.startsWith('restore-'))
  const shown = openFy === null ? rows : rows.filter(r => r.fy === openFy)

  return (
    <ReportShell tab={TAB} dataUrl={DATA}
      title={<>
        {num(t.reductions)} cuts announced in writing &mdash; and what the record can and
        cannot say about them
      </>}
      standfirst={<>
        Every reduction and restoration named in {num(t.documents)} of the district&rsquo;s
        own budget documents, {fyLabel(d.span.first_fy)} to {fyLabel(d.span.last_fy)},
        quoted at its page. Most name a job no published series counts &mdash; so for{' '}
        {num(t.blind)} of the {num(t.measurable)} adopted cuts old enough to check, the
        honest answer is that nobody can tell.
      </>}
    >

      <div className="grid gap-7 mt-9"
        style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 12rem), 1fr))' }}>
        <Stat value={num(t.rows)}>
          reductions, restorations and additions named in writing across{' '}
          {num(t.cycles)} budget cycles
        </Stat>
        <Stat value={num(t.operative)} tone="var(--series-cost)">
          of them are reductions on the list each cycle actually adopted &mdash; the rest
          are drafts that changed
        </Stat>
        <Stat value={num(t.blind)} tone="var(--text-muted)">
          adopted cuts no published series can see at all, because the job is not a
          teaching post
        </Stat>
        <Stat value={`${num(t.moved_with)} of ${num(tested)}`}
          tone="var(--status-good)">
          adopted cuts the state&rsquo;s teacher counts move with, of the ones it can
          reach
        </Stat>
      </div>

      {/* THE CAVEAT THAT LEADS, because it changes whether the reader should trust
          anything below — rule 3's territory and rule 7a's one exception. */}
      <div className="card p-4 mt-9 max-w-3xl"
        style={{ borderLeft: '4px solid var(--status-warning)' }}>
        <p className="text-[14px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
          <strong>A cut list is a claim, not a record.</strong> Every row here comes from a
          document the district assembled to argue for a budget. It is the district&rsquo;s
          own words about what it intended, which is why it is worth publishing &mdash; and
          it is not evidence that any post was removed. Where a cut is not visible
          afterwards there are several innocent readings and this page names them: a grant
          appeared, a retirement absorbed the reduction (the district&rsquo;s own slides
          say so twice), enrolment moved, or the position was restored in public by a later
          vote &mdash; which is exactly what the {fyLabel(2020)} record shows happening.
        </p>
        <p className="text-[14px] leading-relaxed mt-3"
          style={{ color: 'var(--text-secondary)' }}>
          <strong>And the lists exist because the district publishes them.</strong>{' '}
          {num(t.with_consequence)} of these rows carry the district&rsquo;s own written
          account of what losing the post would do &mdash; not a summary of it, the
          sentence itself. Nothing obliges a school district to print that, and this
          register would be impossible without it. No row here is about a person; every one
          is about a line on a document.
        </p>
        <p className="mt-3">
          <Basis level="stated">the district&rsquo;s own budget documents</Basis>
        </p>
      </div>

      {/* PERSONA 5, the School Committee member: the question they arrive with is
          "did the cuts we voted actually happen?", and it is answered here rather than
          discovered on the way down. */}
      <div className="card p-5 mt-6 max-w-3xl"
        style={{ borderLeft: '4px solid var(--fund-school)' }}>
        <p className="text-[11px] font-semibold uppercase tracking-widest mb-1.5"
          style={{ color: 'var(--text-muted)' }}>
          Did the cuts we voted actually happen?
        </p>
        <p className="text-[14.5px] leading-relaxed"
          style={{ color: 'var(--text-secondary)' }}>
          For most of them <strong>this record cannot say, and neither can any other one
          that is published.</strong> Of the {num(t.measurable)} adopted reductions old
          enough to check, {num(t.blind)} name a job &mdash; a paraprofessional, a
          secretary, a custodian, a counsellor &mdash; that no series counts by school.{' '}
          {num(t.moved_with)} of the remaining {num(tested)} are matched by a fall in the
          state&rsquo;s teacher count, {num(t.moved_other)} by a rise, and{' '}
          {num(t.unresolved)} by a movement smaller than the document stated. What the
          register <em>can</em> show is the part nobody had assembled: which list each
          cycle actually adopted, and how far that list moved from the one before it.
        </p>
      </div>

      {/* ------------------------------------------------ 1. CONCLUSIONS (rule 7b) */}
      {/* NOT WRITTEN HERE. Every word and figure comes out of this report's own payload,
          computed by the generator that computed the figures — scripts/conclusions.py. */}
      <Section kind="conclusions">
        <H2 id="conclusions">If you read nothing else</H2>
        <Conclusions rows={d.conclusions} />
      </Section>

      {/* ------------------------------------------------ 2. THE CATEGORICAL DATA */}
      <Section kind="categorical">
        <H2 id="cycles">Cycle by cycle, and how the list changed inside each one</H2>
        <Body>
          The register keeps every list, not only the last one, because the changes between
          them are the finding. In {fyLabel(2020)} the district published three in four
          weeks; in {fyLabel(2025)} it published two on one page and let a ballot choose
          between them. The <strong>adopted</strong> list is the one that was voted or
          presented for adoption, and it is the only one the outcome section tests.
        </Body>

        <div className="mt-6 space-y-5">
          {d.cycles.map(cy => {
            const py = d.per_year.find(p => p.fy === cy.fy)!
            return (
              <div key={cy.fy} className="card p-5 avoid-break">
                <div className="flex flex-wrap items-baseline justify-between gap-3">
                  <h3 className="text-lg font-bold tracking-tight">
                    {fyLabel(cy.fy)} &mdash; {num(cy.n_documents)}{' '}
                    {cy.n_documents === 1 ? 'document' : 'documents'}, {num(cy.rows)} named
                    changes
                  </h3>
                  <span className="text-[12.5px]" style={{ color: 'var(--text-muted)' }}>
                    {num(py.operative)} adopted reductions
                    {py.operative_fte > 0 ? ` · ${py.operative_fte} FTE stated` : ''}
                    {py.operative_amount > 0
                      ? ` · ${usd(py.operative_amount)} stated` : ''}
                  </span>
                </div>
                <div className="mt-4 overflow-x-auto">
                  <table className="w-full text-[13px] border-collapse">
                    <thead>
                      <tr className="text-left" style={{ color: 'var(--text-muted)' }}>
                        <th className="py-1.5 pr-3 font-semibold">date</th>
                        <th className="py-1.5 pr-3 font-semibold">what the document is</th>
                        <th className="py-1.5 pr-3 font-semibold text-right">cuts</th>
                        <th className="py-1.5 pr-3 font-semibold text-right">adds</th>
                        <th className="py-1.5 pr-3 font-semibold text-right">with $</th>
                        <th className="py-1.5 pr-3 font-semibold text-right">with FTE</th>
                        <th className="py-1.5 font-semibold">&nbsp;</th>
                      </tr>
                    </thead>
                    <tbody>
                      {cy.documents.map(doc => (
                        <tr key={doc.doc_date + doc.doc_title}
                          className="border-t" style={{ borderColor: 'var(--grid)' }}>
                          <td className="py-2 pr-3 whitespace-nowrap tnum">
                            {doc.doc_date}
                          </td>
                          <td className="py-2 pr-3">
                            <a className="underline"
                              style={{ color: 'var(--series-cost)' }}
                              href={abs(`/docs/${doc.doc_pdf}`)}>{doc.doc_title}</a>
                            <span className="block text-[12px]"
                              style={{ color: 'var(--text-muted)' }}>{doc.stage}</span>
                          </td>
                          <td className="py-2 pr-3 text-right tnum">{doc.reductions}</td>
                          <td className="py-2 pr-3 text-right tnum">{doc.restorations}</td>
                          <td className="py-2 pr-3 text-right tnum">{doc.with_amount}</td>
                          <td className="py-2 pr-3 text-right tnum">{doc.with_fte}</td>
                          <td className="py-2">
                            {doc.doc_date === cy.operative_date ? (
                              <Tag tone="var(--series-cost)">adopted</Tag>
                            ) : null}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                {cy.operative_conditional ? (
                  <p className="text-[13px] leading-relaxed mt-3"
                    style={{ color: 'var(--text-secondary)' }}>
                    The adopted list for this cycle is the one conditional on{' '}
                    <strong>{cy.operative_conditional}</strong>. That is not an editorial
                    choice: the School Committee published both, and the ballot decided
                    which one applied.
                  </p>
                ) : null}
              </div>
            )
          })}
        </div>

        {/* --------------------------------------------------------- case one */}
        <H2 id="fy2020">Case one &mdash; the list that changed three times in{' '}
          {num(a.weeks_between)} weeks</H2>
        <Body>
          {fyLabel(2020)} is the clearest thing in the register, because the whole cycle is
          in the archive. The February update names a gap and no positions. The{' '}
          {a.march_date} list names {num(a.named_march)} positions at{' '}
          {num(a.march_schools)} schools, each with the district&rsquo;s own account of
          what losing it would do. Weeks later, after the Town Manager raised the target, a
          memo dated {a.memo_date} recommends spending the extra money on two of them. By
          the budget hearing on {a.final_date} the reduced column is down to{' '}
          {num(a.named_april)}, and the athletic trainer has moved to the other side of the
          slide.
        </Body>

        <div className="grid gap-4 mt-6"
          style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 19rem), 1fr))' }}>
          {a.withdrawn.map(w => (
            <div key={w.printed} className="card p-4 avoid-break">
              <p className="text-[11px] font-semibold uppercase tracking-widest"
                style={{ color: 'var(--text-muted)' }}>{school(w.school)}</p>
              <p className="text-[15.5px] font-bold leading-snug mt-1">{w.printed}</p>
              <p className="text-[13.5px] leading-relaxed mt-2"
                style={{ color: 'var(--text-secondary)' }}>
                &ldquo;{w.consequence}&rdquo;
              </p>
              <p className="text-[11.5px] mt-2" style={{ color: 'var(--text-muted)' }}>
                {a.march_date} list, page {w.page} &mdash; and absent from the{' '}
                {a.final_date} list
              </p>
            </div>
          ))}
        </div>

        <H3>What the memo said, three weeks after the list</H3>
        {a.restored_by_memo.map(r => (
          <div key={r.printed} className="card p-4 mt-3 max-w-2xl avoid-break">
            <p className="text-[15px] leading-relaxed">
              &ldquo;{r.printed}&rdquo;
            </p>
            <p className="text-[12px] mt-2" style={{ color: 'var(--text-muted)' }}>
              Superintendent&rsquo;s Budget Recommendations, {a.memo_date} &mdash;{' '}
              {school(r.school)}
            </p>
          </div>
        ))}

        <H3>What the state&rsquo;s teacher counts show for the year afterwards</H3>
        <div className="mt-3 overflow-x-auto">
          <table className="w-full max-w-3xl text-[13.5px] border-collapse">
            <thead>
              <tr className="text-left" style={{ color: 'var(--text-muted)' }}>
                <th className="py-1.5 pr-3 font-semibold">what the list said</th>
                <th className="py-1.5 pr-3 font-semibold">the state&rsquo;s series</th>
                <th className="py-1.5 pr-3 font-semibold text-right">
                  {fyLabel(a.lhs_foreign.before_fy)}
                </th>
                <th className="py-1.5 pr-3 font-semibold text-right">
                  {fyLabel(a.lhs_foreign.after_fy)}
                </th>
                <th className="py-1.5 font-semibold text-right">change</th>
              </tr>
            </thead>
            <tbody>
              {[
                { label: 'Withdrawn — high school foreign language', s: a.lhs_foreign },
                { label: 'Kept — middle school foreign language', s: a.lms_foreign },
              ].map(({ label, s }) => (
                <tr key={s.org} className="border-t" style={{ borderColor: 'var(--grid)' }}>
                  <td className="py-2 pr-3">{label}</td>
                  <td className="py-2 pr-3" style={{ color: 'var(--text-secondary)' }}>
                    {s.subject}, {s.org}
                  </td>
                  <td className="py-2 pr-3 text-right tnum">{s.before}</td>
                  <td className="py-2 pr-3 text-right tnum">{s.after}</td>
                  <td className="py-2 text-right tnum font-semibold"
                    style={{ color: s.change < 0 ? 'var(--status-bad)' : 'var(--status-good)' }}>
                    {s.change > 0 ? '+' : ''}{s.change}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <Body>
          And the librarian, in the district&rsquo;s own book rather than the
          state&rsquo;s: the restated <code>{a.primary_librarian.label}</code> line is
          printed at zero in every year before {fyLabel(a.primary_librarian.first_funded_fy)}{' '}
          and carries{' '}
          {usd(a.primary_librarian.points.find(
            p => p.fy === a.primary_librarian.first_funded_fy)!.value)}{' '}
          in it &mdash; the year the{' '}
          {fte(a.withdrawn.find(w => w.school === 'primary')?.fte)} FTE reduction was
          recommended and then withdrawn.
        </Body>
        <NotShown>
          That the other five reductions on the March list were carried out. This compares
          two lists the district published and sets a state series beside them; it does not
          observe a single post. The foreign language figures are the state&rsquo;s
          apportionment of teaching time by subject, which moves when a timetable moves,
          and the librarian line is the district restating its own book rather than an
          accounting record.
        </NotShown>

        {/* --------------------------------------------------------- case two */}
        <H2 id="fy2025">Case two &mdash; the year a ballot chose between two cut lists</H2>
        <Body>
          Before the {b.ballot.date} election the School Committee published both lists on
          one page: {num(b.without)} positions cut without an override and{' '}
          {num(b.with_override)} with one. The override passed, {num(b.ballot.yes)} to{' '}
          {num(b.ballot.no)}. So {num(b.saved)} positions came off the list by vote &mdash;
          and the {num(b.with_override)} that stayed on it are, one for one, the posts the
          district&rsquo;s own budget update lists as cut because a federal grant had
          ended.
        </Body>
        <p className="text-[13px] leading-relaxed max-w-2xl mt-3"
          style={{ color: 'var(--text-muted)' }}>
          The document reconciles to itself: {b.reconciles}. One row on the longer list is
          not a position &mdash; &ldquo;{b.excluded_not_a_post}&rdquo; &mdash; and is
          excluded from both counts.
        </p>

        <div className="mt-6 overflow-x-auto">
          <table className="w-full max-w-3xl text-[13.5px] border-collapse">
            <thead>
              <tr className="text-left" style={{ color: 'var(--text-muted)' }}>
                <th className="py-1.5 pr-3 font-semibold">
                  cut &ldquo;due to loss of ESSER&rdquo;, page {b.pairs[0].esser_page}
                </th>
                <th className="py-1.5 pr-3 font-semibold">
                  still cut with the override, page {b.pairs[0].override_page}
                </th>
              </tr>
            </thead>
            <tbody>
              {b.pairs.map(p => (
                <tr key={p.esser} className="border-t"
                  style={{ borderColor: 'var(--grid)' }}>
                  <td className="py-2 pr-3">{p.esser}</td>
                  <td className="py-2 pr-3">{p.with_override}</td>
                </tr>
              ))}
              <tr className="border-t" style={{ borderColor: 'var(--grid)' }}>
                <td className="py-2 pr-3">{b.unpaired}</td>
                <td className="py-2 pr-3" style={{ color: 'var(--text-muted)' }}>
                  &mdash; not on the shorter list
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <p className="text-[12.5px] leading-relaxed max-w-2xl mt-3"
          style={{ color: 'var(--text-muted)' }}>
          The pairing between the two wordings is <strong>ours</strong>. The two documents
          describe the same posts in different words and neither states the correspondence,
          so both strings are printed side by side rather than merged, and a reader can
          disagree with any row of it.
        </p>
        <Maybe settle={<>
          The district&rsquo;s grant award and payroll charge detail, showing which fund
          paid each post in {fyLabel(2024)} and {fyLabel(2025)} &mdash; a Business Office
          record that is not published.
        </>}>
          The two lists line up so exactly that it is tempting to say the override was
          designed to buy back the town-funded posts and let the grant-funded ones go. That
          reading fits, and nothing here tests it: the same alignment is produced by any
          process that priced the general-fund posts first, and the documents state no
          rule at all.
        </Maybe>

        {/* --------------------------------------------------------- case three */}
        <H2 id="fy2026">Case three &mdash; the clearest confirmation, and the clearest
          contradiction, in one year</H2>
        <Body>
          The {fyLabel(2026)} list the School Committee approved names {num(c.approved)}{' '}
          positions and prints no dollar figure and no consequence against any of them. Two
          of its rows are the sharpest results on this page, and they point in opposite
          directions.
        </Body>
        <div className="grid gap-4 mt-6"
          style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 20rem), 1fr))' }}>
          <div className="card p-5 avoid-break"
            style={{ borderTop: '3px solid var(--status-good)' }}>
            <p className="text-[15.5px] font-bold leading-snug">&ldquo;{c.row.printed}&rdquo;</p>
            <p className="text-[13.5px] leading-relaxed mt-2"
              style={{ color: 'var(--text-secondary)' }}>
              {c.row.instrument} falls from <strong>{c.row.before}</strong> to{' '}
              <strong>{c.row.after}</strong> the following October &mdash; a change of{' '}
              {c.row.change}. One stated post, one FTE gone, in a series the district does
              not produce.
            </p>
          </div>
          {c.other_way.map(o => (
            <div key={o.printed} className="card p-5 avoid-break"
              style={{ borderTop: '3px solid var(--status-bad)' }}>
              <p className="text-[15.5px] font-bold leading-snug">&ldquo;{o.printed}&rdquo;</p>
              <p className="text-[13.5px] leading-relaxed mt-2"
                style={{ color: 'var(--text-secondary)' }}>
                {o.instrument} goes from <strong>{o.before}</strong> to{' '}
                <strong>{o.after}</strong> &mdash; up {o.change}. The whole
                district&rsquo;s teacher count fell by{' '}
                {Math.abs(c.district.change)} over the same year, so this is one subject
                rising inside a falling total.
              </p>
            </div>
          ))}
        </div>
        <NotShown>
          That the mathematics teacher was not cut. The state apportions teacher FTE by
          teaching assignment rather than by post, so a subject rises when timetables move
          toward it &mdash; one teacher taking two more mathematics sections shows up here
          and no post has been added. It equally does not show that the world language post
          was cut: a world language teacher&rsquo;s retirement was announced in the same
          month, and a retirement and a layoff produce the identical fall.
        </NotShown>
        <div className="mt-4 max-w-2xl"><Quote q={retirement} /></div>

        {/* --------------------------------------------------------- the outcomes */}
        <H2 id="outcomes">What the instruments show, across every adopted cut</H2>
        <Body>
          {num(t.operative)} reductions sit on the lists this town actually adopted.{' '}
          {num(t.not_yet)} are {fyLabel(2027)} and the school year they pay for is the one
          now running, so nothing can be said about them yet. Of the {num(t.measurable)}{' '}
          that are old enough, this is what a published series can and cannot reach.
        </Body>
        <div className="mt-6 space-y-2 max-w-3xl">
          {d.categories.by_verdict.map(v => (
            <div key={v.name} className="flex items-center gap-3">
              <div className="text-[13.5px] w-56 shrink-0"
                style={{ color: 'var(--text-secondary)' }}>{v.name}</div>
              <div className="flex-1 h-5 rounded overflow-hidden"
                style={{ background: 'var(--surface-2)' }}>
                <div className="h-full"
                  style={{ width: `${(v.n / t.operative) * 100}%`,
                    background: VERDICT_TONE[v.name] ?? 'var(--text-muted)' }} />
              </div>
              <div className="text-[13.5px] tnum w-10 text-right font-semibold">{v.n}</div>
            </div>
          ))}
        </div>
        <p className="text-[13px] leading-relaxed max-w-2xl mt-4"
          style={{ color: 'var(--text-muted)' }}>
          <strong>&ldquo;Does not resolve&rdquo; is not a failed cut.</strong> The state
          publishes FTE to one decimal place, so a movement under{' '}
          {d.definitions.tolerance} is the resolution of the instrument rather than a
          reading from it. A cut of {d.definitions.tolerance} FTE and no cut at all look
          the same in this series, and the page says so rather than choosing.
        </p>

        <div className="mt-8 overflow-x-auto">
          <table className="w-full text-[13px] border-collapse">
            <thead>
              <tr className="text-left" style={{ color: 'var(--text-muted)' }}>
                <th className="py-1.5 pr-3 font-semibold">cycle</th>
                <th className="py-1.5 pr-3 font-semibold text-right">named in writing</th>
                <th className="py-1.5 pr-3 font-semibold text-right">adopted cuts</th>
                <th className="py-1.5 pr-3 font-semibold text-right">moved with it</th>
                <th className="py-1.5 pr-3 font-semibold text-right">the other way</th>
                <th className="py-1.5 pr-3 font-semibold text-right">unresolved</th>
                <th className="py-1.5 pr-3 font-semibold text-right">cannot see</th>
                <th className="py-1.5 font-semibold text-right">too early</th>
              </tr>
            </thead>
            <tbody>
              {d.per_year.map(p => (
                <tr key={p.fy} className="border-t" style={{ borderColor: 'var(--grid)' }}>
                  <td className="py-2 pr-3 font-semibold">{fyLabel(p.fy)}</td>
                  <td className="py-2 pr-3 text-right tnum">{p.rows}</td>
                  <td className="py-2 pr-3 text-right tnum">{p.operative}</td>
                  <td className="py-2 pr-3 text-right tnum">{p.moved_with}</td>
                  <td className="py-2 pr-3 text-right tnum">{p.moved_other}</td>
                  <td className="py-2 pr-3 text-right tnum">{p.unresolved}</td>
                  <td className="py-2 pr-3 text-right tnum">{p.blind}</td>
                  <td className="py-2 text-right tnum">{p.not_yet}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <H2 id="schools">Where the cuts were named</H2>
        <div className="mt-5 grid gap-3"
          style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 13rem), 1fr))' }}>
          {d.categories.by_school.map(s => (
            <div key={s.name} className="card p-3.5 avoid-break">
              <div className="text-2xl font-bold tnum">{s.n}</div>
              <div className="text-[12.5px] mt-0.5" style={{ color: 'var(--text-secondary)' }}>
                reductions named for {school(s.name).toLowerCase()}
              </div>
            </div>
          ))}
        </div>
        <p className="text-[13px] leading-relaxed max-w-2xl mt-4"
          style={{ color: 'var(--text-muted)' }}>
          A position appearing on three documents in one cycle is three rows here, because
          the register keeps every list. The adopted-only counts are in the table above.
        </p>
      </Section>

      {/* --------------------------------------------------- 3. RAW (rule 7b) */}
      <Section kind="raw">
        <H2 id="register">The register</H2>
        <Body>
          Every row, with the string the document printed, the page it is on, and what an
          instrument shows where one reaches it. Nothing in the{' '}
          <em>as printed</em> column is our wording.
        </Body>

        <div className="flex flex-wrap items-center gap-2 mt-5 no-print">
          <button type="button" onClick={() => setOpenFy(null)}
            className="text-xs font-semibold px-2.5 py-1.5 rounded border min-h-[32px]"
            style={{ borderColor: openFy === null ? 'var(--series-cost)' : 'var(--grid)',
              color: openFy === null ? 'var(--series-cost)' : 'var(--text-secondary)',
              background: 'var(--surface-1)' }}>
            every cycle
          </button>
          {d.cycles.map(cy => (
            <button key={cy.fy} type="button" onClick={() => setOpenFy(cy.fy)}
              className="text-xs font-semibold px-2.5 py-1.5 rounded border min-h-[32px]"
              style={{ borderColor: openFy === cy.fy ? 'var(--series-cost)' : 'var(--grid)',
                color: openFy === cy.fy ? 'var(--series-cost)' : 'var(--text-secondary)',
                background: 'var(--surface-1)' }}>
              {fyLabel(cy.fy)}
            </button>
          ))}
          <label className="text-xs ml-2 inline-flex items-center gap-1.5"
            style={{ color: 'var(--text-secondary)' }}>
            <input type="checkbox" checked={onlyAdopted}
              onChange={e => setOnlyAdopted(e.target.checked)} />
            only the lists that were adopted
          </label>
        </div>

        <div className="mt-5 overflow-x-auto">
          <table className="w-full text-[12.5px] border-collapse">
            <thead>
              <tr className="text-left" style={{ color: 'var(--text-muted)' }}>
                <th className="py-1.5 pr-3 font-semibold">FY</th>
                <th className="py-1.5 pr-3 font-semibold">document</th>
                <th className="py-1.5 pr-3 font-semibold">as printed</th>
                <th className="py-1.5 pr-3 font-semibold">school</th>
                <th className="py-1.5 pr-3 font-semibold text-right">FTE</th>
                <th className="py-1.5 pr-3 font-semibold text-right">stated $</th>
                <th className="py-1.5 pr-3 font-semibold">what an instrument shows</th>
              </tr>
            </thead>
            <tbody>
              {shown.map((r, i) => (
                <tr key={`${r.doc_text}-${r.page}-${r.printed}-${i}`}
                  className="border-t align-top" style={{ borderColor: 'var(--grid)' }}>
                  <td className="py-2 pr-3 whitespace-nowrap">
                    {fyLabel(r.fy)}
                    {r.operative
                      ? <span className="block mt-1"><Tag tone="var(--series-cost)">adopted</Tag></span>
                      : null}
                  </td>
                  <td className="py-2 pr-3" style={{ color: 'var(--text-secondary)' }}>
                    <span className="whitespace-nowrap tnum">{r.doc_date}</span>
                    <span className="block text-[11.5px]"
                      style={{ color: 'var(--text-muted)' }}>
                      p.{r.page} &middot; {r.block}
                      {r.conditional_on ? ` · if ${r.conditional_on}` : ''}
                    </span>
                  </td>
                  <td className="py-2 pr-3">
                    <span className="font-medium">{r.printed}</span>
                    {r.direction !== 'reduction' ? (
                      <span className="ml-1.5"><Tag tone="var(--status-good)">{r.direction}</Tag></span>
                    ) : null}
                    {r.consequence ? (
                      <span className="block text-[11.5px] mt-1 max-w-xl"
                        style={{ color: 'var(--text-muted)' }}>
                        &ldquo;{r.consequence.length > 220
                          ? `${r.consequence.slice(0, 220)}…` : r.consequence}&rdquo;
                      </span>
                    ) : null}
                  </td>
                  <td className="py-2 pr-3" style={{ color: 'var(--text-secondary)' }}>
                    {school(r.school)}
                  </td>
                  <td className="py-2 pr-3 text-right tnum">{fte(r.fte)}</td>
                  <td className="py-2 pr-3 text-right tnum">
                    {r.amount === null ? '' : usd(r.amount)}
                  </td>
                  <td className="py-2 pr-3">
                    {r.direction === 'reduction' ? (
                      <>
                        <Tag tone={VERDICT_TONE[r.verdict] ?? 'var(--text-muted)'}>
                          {VERDICT_SHORT[r.verdict] ?? r.verdict}
                        </Tag>
                        {r.instrument ? (
                          <span className="block text-[11.5px] mt-1"
                            style={{ color: 'var(--text-muted)' }}>
                            {r.instrument}
                            {r.before !== null && r.before !== undefined
                              ? `: ${r.before} → ${r.after}` : ''}
                          </span>
                        ) : null}
                        {r.reason ? (
                          <span className="block text-[11.5px] mt-1 max-w-sm"
                            style={{ color: 'var(--text-muted)' }}>{r.reason}</span>
                        ) : null}
                      </>
                    ) : (
                      <span style={{ color: 'var(--text-muted)' }}>not a reduction</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="text-[12.5px] mt-3" style={{ color: 'var(--text-muted)' }}>
          {num(shown.length)} of {num(t.rows)} rows shown. The whole register is published
          at{' '}
          <a className="underline" style={{ color: 'var(--series-cost)' }}
            href={abs('/data/stated-cuts.csv')}>/data/stated-cuts.csv</a>{' '}
          and loaded into the database as <code>stated_cuts</code>.
        </p>

        {/* ------------------------------------------------------------ method */}
        <H2 id="method">How this was built, and where the judgement is</H2>
        <div className="grid gap-4 mt-5"
          style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 19rem), 1fr))' }}>
          <Insight n={1} headline="Nothing in the register is typed.">
            Every <em>as printed</em> string is read out of the extracted text of the named
            document at the named page, and the extractor refuses to write if any of them
            stops being present there. The school, the FTE and the amount are derived from
            that string by rules published in the payload.
          </Insight>
          <Insight n={2} headline="The instrument is one count, on one day, of one kind of job.">
            {d.definitions.instrument}, {fyLabel(d.span.instrument_first_fy)} to{' '}
            {fyLabel(d.span.instrument_last_fy)}. It counts teachers. A post cut in June and
            filled again in November does not appear in an October snapshot, which is
            precisely the reversal residents describe.
          </Insight>
          <Insight n={3} headline="Which subject a job title is, is our reading.">
            The mapping is short on purpose and matched on whole words: a title that does
            not plainly name a subject the state reports gets no subject rather than a
            guess, because a wrong subject produces a confident verdict where no subject
            produces an honest &ldquo;cannot see&rdquo;.
          </Insight>
          <Insight n={4} headline="Which list counts as adopted is our reading too, except once.">
            {d.definitions.operative}
          </Insight>
        </div>

        <H2 id="said">What the town said, in the same years</H2>
        <Body>
          Rule 15a: for every category this page says was cut, the meeting archive is
          searched for what people said about it in the same year. These are what came
          back.
        </Body>
        <div className="grid gap-4 mt-5"
          style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 20rem), 1fr))' }}>
          <Quote q={layoffs} />
          <Quote q={dispute} />
          {restores.map(q => <Quote key={q.key} q={q} />)}
        </div>
        <Coverage m={d.minutes} searched={d.searched} />

        <H2 id="documents">The documents this is read from</H2>
        <div className="mt-5 overflow-x-auto">
          <table className="w-full text-[13px] border-collapse">
            <thead>
              <tr className="text-left" style={{ color: 'var(--text-muted)' }}>
                <th className="py-1.5 pr-3 font-semibold">date</th>
                <th className="py-1.5 pr-3 font-semibold">document</th>
                <th className="py-1.5 pr-3 font-semibold text-right">rows</th>
                <th className="py-1.5 pr-3 font-semibold">sha256</th>
                <th className="py-1.5 font-semibold">our copy</th>
              </tr>
            </thead>
            <tbody>
              {d.documents.map(doc => (
                <tr key={doc.path} className="border-t"
                  style={{ borderColor: 'var(--grid)' }}>
                  <td className="py-2 pr-3 whitespace-nowrap tnum">{doc.doc_date}</td>
                  <td className="py-2 pr-3">
                    {doc.title}
                    <span className="block text-[11.5px]"
                      style={{ color: 'var(--text-muted)' }}>
                      {fyLabel(doc.fy)} &middot; {doc.stage} &middot;{' '}
                      {doc.path.split('/').pop()}
                    </span>
                  </td>
                  <td className="py-2 pr-3 text-right tnum">{doc.rows}</td>
                  <td className="py-2 pr-3 break-all text-[11px]"
                    style={{ color: 'var(--text-muted)' }}>
                    {doc.sha256.slice(0, 16)}&hellip;
                  </td>
                  <td className="py-2">
                    <a className="underline" style={{ color: 'var(--series-cost)' }}
                      href={abs(doc.docs_url)}>PDF</a>{' '}
                    &middot;{' '}
                    <a className="underline" style={{ color: 'var(--series-cost)' }}
                      href={abs(`/docs/${doc.text}`)}>text</a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <H2 id="gaps">What this cannot answer</H2>
        <div className="mt-5 space-y-4 max-w-3xl">
          {d.gaps.map(g => (
            <div key={g.what} className="card p-4 avoid-break">
              <p className="text-[15px] font-bold leading-snug">{g.what}</p>
              <p className="text-[13.5px] leading-relaxed mt-2"
                style={{ color: 'var(--text-secondary)' }}>{g.why}</p>
              {g.closes ? (
                <p className="text-[13px] leading-relaxed mt-2.5">
                  <strong>What would close it:</strong>{' '}
                  <span style={{ color: 'var(--text-secondary)' }}>{g.closes}</span>
                </p>
              ) : null}
            </div>
          ))}
        </div>

        <H2 id="control">What you would have had to see, and when</H2>
        <Body>
          The question a Finance Committee member arrives with is not what happened; it is
          what they would have had to be given, and by when, to have known. For this
          register the answer is one document and one date. {d.closes} Received in the
          autumn, after the October payroll settles and before the next budget cycle opens,
          it would turn every row on this page from a claim into a checkable fact &mdash;
          and it would answer the argument the Finance Committee and the School Committee
          had in January, which neither side could settle from anything published.
        </Body>
        <div className="mt-4 max-w-2xl"><Quote q={dispute} /></div>
        <Body>
          The one thing that would <em>not</em> settle it is another budget document. Every
          list in this register is a forward statement, and a ninth one would be a tenth
          claim rather than a first measurement.
        </Body>

        <H2 id="scope">This is the school side only</H2>
        <Body>
          The town side publishes its own reduction lists &mdash; the Finance
          Committee&rsquo;s report in the annual town meeting warrant sets them out line by
          line, with the amounts and the override tier that would restore each. They are not
          in this register, and the absence is a limit of scope rather than a finding about
          either side. Nothing here supports a comparison between what the schools cut and
          what the town cut, and a reader reaching for one is reaching past the data.
        </Body>

        <H2 id="not-established">What this does not establish</H2>
        <NotEstablished rows={d.not_established} closes={d.closes} />
      </Section>
    </ReportShell>
  )
}

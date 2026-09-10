import type { Tab } from '../routes'
import { useEffect, useState } from 'react'
import { abs } from '../lib/abs'
import { TableTwin, fy, money, share } from '../components/MinimumAidCharts'
import {
  Body, Conclusions, H3, Quote, Section, Stat, ReportShell,
} from '../components/report'
import type { Conclusion } from '../components/report'

const TAB: Tab = 'formula'
const DATA = '/data/ch70-formula.json'

/** How Chapter 70 actually works, in eight plain steps.
 *
 *  WHY IT IS A PAGE OF ITS OWN. `/why-we-only-get-minimum-aid` establishes Lunenburg's
 *  POSITION in this formula — the whole increase is the Legislature's floor, the town sits
 *  above the line at which the formula pays anything, the required contribution is a wealth
 *  calculation. This page answers the other question, which is how the machine works, and a
 *  reader who arrives with that one should not have to read twenty years of aid components
 *  to get it.
 *
 *  THE EIGHT STEPS ARE THE ARTEFACT AND THIS FILE DOES NOT TOUCH THEM. They are written in
 *  scripts/build_minimum_aid.py, where the comment above them records what they are: an
 *  explanation that took an hour of back-and-forth to reach, whose ORDER is the point
 *  because every step answers the question the previous one raises. They arrive here in the
 *  payload and are rendered verbatim. scripts/verify_ch70_formula.py asserts that the
 *  published list is identical, in order and in wording, to the one in that module.
 *
 *  THE `watch` LINE IS DRAWN AS THE TRAP IT IS. Each step carries one, and those lines are
 *  where every misreading in the original conversation actually happened — "it is a
 *  calculation, not money anybody sends", "enrolment is not in this step at all", "the
 *  formula is a FLOOR TEST, not a recalculation". A step whose warning is set in the same
 *  voice as its explanation has published the misreading along with the fix.
 *
 *  RULE 2. Not one figure is typed into this file. Everything arrives from the payload,
 *  written by scripts/build_ch70_formula.py, which computes it in the same process as the
 *  other page's generator so the two cannot state different numbers for one quantity.
 *
 *  RULE 7. The steps are how the formula is defined and DESE's own definitions are quoted
 *  at their cells. What is NOT established — what a large fall in enrolment would do — has
 *  its own section, its own threshold, and is stated as a limit rather than answered.
 *
 *  RULE 7b. Conclusions, then the steps and the categories, then the raw and the caveats.
 *
 *  NO D1 AT PAGE LOAD. One static file. */

type Said = {
  key: string; board: string; date: string; kind: string; quote: string; why: string
  cite: string; town: string
}

type Payload = {
  conclusions: Conclusion[]
  about: string
  not_this_page: string
  source: {
    path: string; sha256: string; bytes: number; url: string; docs_url: string
    filename: string; publisher: string; sheets: string[]; stage: string
  }
  fy: number; fy_first: number; fy_last: number; years: number
  how_it_works: { step: string; plain: string; watch: string }[]
  unlock: string
  three_numbers: { key: string; value: number; text: string; label: string; what: string }[]
  ratio: number
  aid: number; enrollment: number; increase: number
  foundation_aid_increment: number
  foundation_budget: number; required_local_contribution: number
  need: number; prior_aid: number; headroom: number; foundation_per_pupil: number
  definitions: { cell: string; term: string; text: string }[]
  reductions: { cell: string; term: string; text: string }[]
  cut_years: { fy: number; amount: number }[]
  threshold: {
    fy: number; enrollment: number; required_share: number; pupils_at_zero: number
    fall_pct: number; years_checked: number; first_fy: number; last_fy: number
    highest_share: number; highest_share_fy: number
    is_measurement: boolean; assumptions: string[]
  }
  said: Said[]
  searched: { term: string; documents: number }[]
  minutes: {
    held: number; searchable: number; unsearchable: number; image_scan: number
    searchable_share: number
  }
  gaps: { side: string; what: string; why: string; closes: string | null }[]
  not_established: string[]
}

const TITLE = 'How Chapter 70 actually works'

function Shell({ err, loading, standfirst, children }: {
  err?: string | null; loading?: boolean
  standfirst?: React.ReactNode; children?: React.ReactNode
}) {
  return (
    <ReportShell tab={TAB} dataUrl={DATA} title={TITLE} standfirst={standfirst}
      err={err} loading={loading}>{children}</ReportShell>
  )
}

/** One step, and the trap that goes with it.
 *
 *  The number is set large and quiet because the SEQUENCE is what a reader has to hold —
 *  each step answers the question the one above it raises, and a list that does not look
 *  ordered invites reading the interesting one first, which is exactly how this formula
 *  gets misunderstood.
 *
 *  `watch` is drawn as a warning and never as a continuation of `plain`. It is the
 *  correction to the reading a reader has just been tempted into. */
function Step({ n, step, plain, watch }: {
  n: number; step: string; plain: string; watch: string
}) {
  return (
    <div className="card p-5 avoid-break">
      <div className="flex items-baseline gap-3">
        <span className="text-[11px] font-bold tabular-nums"
          style={{ color: 'var(--text-muted)' }}>{String(n).padStart(2, '0')}</span>
        <p className="text-[17px] font-bold leading-snug">{step}</p>
      </div>
      <p className="text-[15px] leading-relaxed mt-2.5 max-w-2xl"
        style={{ color: 'var(--text-secondary)' }}>{plain}</p>
      <div className="mt-3.5 pl-3 border-l-[3px]"
        style={{ borderColor: 'var(--status-warning)' }}>
        <p className="text-[10.5px] font-semibold uppercase tracking-widest"
          style={{ color: 'var(--text-muted)' }}>Where people go wrong</p>
        <p className="text-[14px] leading-relaxed mt-1">{watch}</p>
      </div>
    </div>
  )
}

export function Ch70Formula() {
  const [d, setD] = useState<Payload | null>(null)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    let live = true
    fetch(DATA)
      .then(r => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then(j => { if (live) setD(j) })
      .catch(e => { if (live) setErr(String(e)) })
    return () => { live = false }
  }, [])

  if (err) return <Shell err={err} />
  if (!d) return <Shell loading />

  const T = d.threshold
  const rate = d.three_numbers[1]

  return (
    <Shell standfirst={<>
      Eight steps, in the order the questions arrive. Worked through with{' '}
      {fy(d.fy)}&rsquo;s own numbers.
    </>}>

      {/* ------------------------------------------------ 1. CONCLUSIONS (rule 7b) */}
      {/* NOT WRITTEN HERE. Every word and every figure comes out of this report's own
          payload, computed by the generator that computed the figures. */}
      <Section kind="conclusions" id="conclusions" title="If you read nothing else">
        <Conclusions rows={d.conclusions} />
      </Section>

      {/* The two pages, named as two questions. Placed here rather than at the top: a
          reader needs it before they start reading the steps and not before they know
          what the page is. Rule 7a — the thing first, the note about it after. */}
      <div className="card p-4 mt-10 max-w-3xl" style={{ borderLeft: '4px solid var(--axis)' }}>
        <p className="text-[11px] font-semibold uppercase tracking-widest mb-1.5"
          style={{ color: 'var(--text-muted)' }}>This page, and the other one</p>
        <p className="text-[14px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
          {d.not_this_page}{' '}
          <a className="underline" style={{ color: 'var(--series-cost)' }}
            href={abs('/why-we-only-get-minimum-aid')}>Why we only get minimum aid</a> is
          where the town sits in this formula. This page is the formula.
        </p>
      </div>

      {/* ------------------------------------------------------------ 2. THE STEPS */}
      <Section kind="categorical" id="steps" title="How it works, in eight steps">
        <Body>
          The one that unlocks the rest is number four: <strong>{d.unlock}</strong> Every
          confusing thing about what Lunenburg receives follows from that.
        </Body>
        {/* PERSONA REVIEW, readers 1 and 6. The first reader arrives certain that an
            unexplained number is somebody in town hiding something, and a page that
            explains a formula producing nothing can be read as a district that failed to
            apply for something. The sixth compares the two sides and would otherwise read
            "the schools get state aid" straight off this page. Both are answered by one
            fact stated plainly: none of the eight steps is a decision made here, and the
            money arrives as town revenue rather than as a payment to the district. */}
        <Body>
          None of these eight steps is a decision anybody in Lunenburg makes. The per-pupil
          rates are the state&rsquo;s, the floor is a line in the Legislature&rsquo;s
          budget, and the town&rsquo;s required share is worked out from property values
          and income. Nor is Chapter 70 a payment to the school district: it arrives as
          town revenue, and the town appropriates the school budget separately &mdash;{' '}
          <a className="underline" style={{ color: 'var(--series-cost)' }}
            href={abs('/state-aid')}>state aid</a> is where that route is set out.
        </Body>
        <div className="grid gap-4 mt-6"
          style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 24rem), 1fr))' }}>
          {d.how_it_works.map((s, i) => (
            <Step key={s.step} n={i + 1} step={s.step} plain={s.plain} watch={s.watch} />
          ))}
        </div>
      </Section>

      {/* ------------------------------------------------------ 3. THE THREE NUMBERS */}
      <Section kind="categorical" id="three"
        title={<>Three numbers, and two of them are {rate.text}</>}>
        <div className="grid gap-6 mt-6"
          style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 16rem), 1fr))' }}>
          {d.three_numbers.map(n => (
            <div key={n.key} className="avoid-break">
              <div className="text-3xl font-bold tracking-tight tnum">{n.text}</div>
              <div className="text-[13.5px] font-semibold leading-snug mt-1.5 max-w-[17rem]">
                {n.label}
              </div>
              <div className="text-[13px] leading-relaxed mt-1.5 max-w-[17rem]"
                style={{ color: 'var(--text-secondary)' }}>{n.what}</div>
            </div>
          ))}
        </div>
        <Body>
          The second and the third are the same figure in {fy(d.fy)} and they are not the
          same quantity. They coincide because minimum aid is the only component operating:
          the formula&rsquo;s own aid term paid {money(d.foundation_aid_increment)}, so the
          flat per-pupil increase is the only part of the build-up a pupil can move. In a
          year when the formula pays, they part company.
        </Body>
        <Body>
          The first is a third kind of figure again &mdash; {money(d.aid)} of aid over{' '}
          {d.enrollment.toLocaleString()} foundation pupils. Quoting it beside the other two
          is how a town comes to believe that each child arrives carrying{' '}
          {d.three_numbers[0].text} of state money, and each child does not.
        </Body>
      </Section>

      {/* PERSONA REVIEW, reader 4. The Finance Committee member's test is whether the
          page tells them one thing they could do differently next year, and on the first
          pass it did not: everything above is true and none of it reaches a budget cycle.
          This is the shortest honest answer, and it is derived rather than advised —
          the only quantity that moves the aid is one the town does not set and does not
          know while it is building its own budget. */}
      <div className="card p-5 mt-10 max-w-3xl"
        style={{ borderLeft: '4px solid var(--status-good)' }}>
        <p className="text-[11px] font-semibold uppercase tracking-widest mb-1.5"
          style={{ color: 'var(--text-muted)' }}>If you are building a budget</p>
        <p className="text-[14px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
          Forecasting Chapter 70 while the floor binds means forecasting one number: the
          per-pupil increase the Legislature votes. It was {rate.text} for {fy(d.fy)}. An
          enrollment projection does not help &mdash; it moves a term that is producing{' '}
          {money(d.foundation_aid_increment)} &mdash; and the rate is not settled when the
          town builds its own budget. The figure quoted at that point is an early-stage
          one, and{' '}
          <a className="underline" style={{ color: 'var(--series-cost)' }}
            href={abs('/why-we-only-get-minimum-aid#stage')}>the same year at two
          stages</a> shows how far apart the two have been.
        </p>
      </div>

      {/* ------------------------------------------------- 4. WHAT CAN REDUCE THE AID */}
      <Section kind="categorical" id="reduce" title="What can reduce Chapter 70 aid">
        <Body>
          Two provisions in DESE&rsquo;s own definitions decrease a district&rsquo;s aid.
          Neither of them is enrolment, for a district that runs its own schools.
        </Body>
        <div className="grid gap-4 mt-6"
          style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 22rem), 1fr))' }}>
          {d.reductions.map(r => (
            <div key={r.cell} className="card p-5 avoid-break">
              <p className="text-[15px] font-bold leading-snug">{r.term}</p>
              <p className="text-[11px] mt-1" style={{ color: 'var(--text-muted)' }}>
                <code>{r.cell}</code>
              </p>
              <p className="text-[14px] leading-relaxed mt-2.5"
                style={{ color: 'var(--text-secondary)' }}>&ldquo;{r.text}&rdquo;</p>
            </div>
          ))}
        </div>
        <Body>
          The first has run here. DESE&rsquo;s reduction column is populated for Lunenburg
          in{' '}
          {d.cut_years.map((c, i) => (
            <span key={c.fy}>
              {i ? (i === d.cut_years.length - 1 ? ' and ' : ', ') : ''}
              {fy(c.fy)} ({money(c.amount)})
            </span>
          ))}{' '}
          &mdash; the recession years, applied across the state &mdash; and in no year
          since. The second reduces aid to the level of the foundation budget for
          NON-OPERATING districts, which run no schools of their own and tuition their
          pupils elsewhere. Lunenburg runs schools.
        </Body>
      </Section>

      {/* ------------------------------------------------------- 5. DESE'S OWN WORDS */}
      <Section kind="categorical" id="definitions"
        title={<>DESE&rsquo;s own words for each term</>}>
        <Body>
          Every term the steps use, quoted from the workbook&rsquo;s <code>User Guide</code>{' '}
          sheet at the cell it appears in. Rule 13 of this project: quote the source, never
          your rendering of it &mdash; a rendered table is for reading and never for
          quoting, so the coordinate is printed beside each one.
        </Body>
        <TableTwin caption={`${d.source.filename}, sheet User Guide`}
          head={['Cell', 'Term', 'What DESE says it is']}
          rows={d.definitions.map(x => [x.cell, x.term, x.text])} />
      </Section>

      {/* ------------------------------------------------------- 6. WHERE IT STOPS */}
      <Section kind="raw" id="stops" title="Where this stops being true">
        <Body>
          <strong>Fewer students does not mean less aid &mdash; it means no increase.</strong>{' '}
          That was established AT THE MARGIN: one pupil, with everything else held at its{' '}
          {fy(T.fy)} value. It is not a rate that can be multiplied out, and the point where
          it stops is calculable.
        </Body>
        <div className="grid gap-6 mt-6"
          style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 15rem), 1fr))' }}>
          <Stat value={share(T.required_share)}>
            the required local contribution, as a share of the foundation budget in{' '}
            {fy(T.fy)}
          </Stat>
          <Stat value={Math.round(T.pupils_at_zero).toLocaleString()}>
            foundation pupils at which the two would meet and the formula&rsquo;s own
            subtraction would turn negative &mdash; a fall of {share(T.fall_pct)} from{' '}
            {T.enrollment.toLocaleString()}
          </Stat>
          <Stat value={`0 of ${T.years_checked}`}>
            published years in which it has happened. The highest the required share has
            been is {share(T.highest_share)}, in {fy(T.highest_share_fy)}
          </Stat>
        </div>
        <Body>
          The foundation budget moves with pupils. The required contribution does not, because
          it is worked out from property values and income. So the gap between them &mdash;
          step three, which is what aid is for &mdash; closes as pupils fall, and below about{' '}
          {Math.round(T.pupils_at_zero).toLocaleString()} pupils it goes the other way.{' '}
          <strong>Nothing in this archive models what the formula does from there.</strong>{' '}
          A district that far below its foundation budget would meet hold-harmless
          provisions, a different minimum aid rate and possibly legislation, none of which
          is in this workbook.
        </Body>
        <H3>What that calculation assumes</H3>
        <ul className="mt-3 space-y-2.5 max-w-2xl">
          {T.assumptions.map(a => (
            <li key={a} className="text-[14px] leading-relaxed pl-4 border-l-2"
              style={{ color: 'var(--text-secondary)', borderColor: 'var(--axis)' }}>{a}</li>
          ))}
        </ul>
      </Section>

      {/* --------------------------------------------------------- 7. WHAT THE TOWN SAID */}
      <Section kind="raw" id="said" title="What the town has said about it">
        <Body>
          Statements made in public, not measurements. Each is re-read out of the extracted
          minutes on every build and a miss stops it.
        </Body>
        <div className="grid gap-4 mt-6"
          style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 22rem), 1fr))' }}>
          {d.said.map(q => <Quote key={q.key} q={q} />)}
        </div>
        <H3>What was searched, and how much of the archive could be</H3>
        <TableTwin caption="sources/meetings/text — every board the town publishes"
          head={['Term', 'Documents that mention it']}
          rows={d.searched.map(s => [s.term, s.documents.toLocaleString()])}
          note={<><strong>{d.minutes.searchable.toLocaleString()} of{' '}
            {d.minutes.held.toLocaleString()} held documents can be searched at all{' '}
            ({share(d.minutes.searchable_share)}).</strong>{' '}
            {d.minutes.unsearchable.toLocaleString()} carry no text a search can match
            &mdash; {d.minutes.image_scan.toLocaleString()} of them image scans awaiting
            OCR. So an empty result is a statement about what can be read, never about what
            anybody said.</>} />
      </Section>

      {/* ------------------------------------------------------------- 8. THE LIMITS */}
      <Section kind="raw" id="cannot" title="What this cannot say">
        <div className="flex flex-col gap-3 mt-6 max-w-3xl">
          {d.not_established.map(n => (
            <div key={n} className="card p-4">
              <p className="text-[14px] leading-relaxed"
                style={{ color: 'var(--text-secondary)' }}>{n}</p>
            </div>
          ))}
        </div>

        <H3>The same limits, as rows in the register</H3>
        <Body>
          Each of these is a row in <code>money-gaps.csv</code>, which is what the records
          request to the Town reads and what{' '}
          <a className="underline" style={{ color: 'var(--series-cost)' }}
            href={abs('/what-we-cannot-answer')}>what we cannot answer</a> renders. A limit
          stated only in the prose of one page is invisible to everybody who did not read
          that page.
        </Body>
        <div className="flex flex-col gap-3 mt-5 max-w-3xl">
          {d.gaps.map(g => (
            <div key={g.what} className="card p-4">
              <p className="text-[11px] font-semibold uppercase tracking-widest mb-1.5"
                style={{ color: 'var(--text-muted)' }}>{g.side.replace(/_/g, ' ')}</p>
              <p className="text-[15px] font-bold leading-snug">{g.what}</p>
              <p className="text-[13.5px] leading-relaxed mt-2"
                style={{ color: 'var(--text-secondary)' }}>{g.why}</p>
              {g.closes && (
                <p className="text-[13.5px] leading-relaxed mt-2">
                  <strong>Closes:</strong> {g.closes}
                </p>
              )}
            </div>
          ))}
        </div>
      </Section>

      {/* ------------------------------------------------------------- 9. THE DOCUMENT */}
      <Section kind="raw" id="source" title="The document behind this">
        <Body>
          {d.source.publisher}. Our copy is{' '}
          <a className="underline break-all" style={{ color: 'var(--series-cost)' }}
            href={abs(d.source.docs_url)}>{d.source.filename}</a>{' '}
          ({(d.source.bytes / 1e6).toFixed(1)} MB), fetched from{' '}
          <a className="underline break-all" style={{ color: 'var(--series-cost)' }}
            href={d.source.url}>{d.source.url}</a>. Its sha256 is{' '}
          <code className="break-all">{d.source.sha256}</code>. Every figure worked through
          on this page is {d.source.stage}
        </Body>
        <Body>
          The payload this page draws is published whole at{' '}
          <a className="underline" style={{ color: 'var(--series-cost)' }}
            href={abs(DATA)}>{DATA}</a>. The twenty-year series behind it &mdash; the aid
          components term by term, the peer districts on the same per-pupil rate, and the
          wealth calculation behind the required contribution &mdash; is on{' '}
          <a className="underline" style={{ color: 'var(--series-cost)' }}
            href={abs('/why-we-only-get-minimum-aid')}>why we only get minimum aid</a>, and
          state aid as a whole, of which Chapter 70 is the largest part, is on{' '}
          <a className="underline" style={{ color: 'var(--series-cost)' }}
            href={abs('/state-aid')}>state aid</a>.
        </Body>
      </Section>
    </Shell>
  )
}

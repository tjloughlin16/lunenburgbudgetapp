import { LABEL, type Tab } from '../routes'
import { abs } from '../lib/abs'
import {
  Body, Conclusions, H2, H3, ReportShell, Section, Stat, useReport,
  type Conclusion,
} from '../components/report'

const TAB: Tab = 'addsup'
const DATA = '/data/what-it-all-adds-up-to.json'

/** ONE REPORT OVER ALL OF THEM.
 *
 *  WHAT IT IS FOR. TJ: "across all the drill-ins, I want to put together a sort of ONE
 *  REPORT TO RULE THEM ALL that captures the most important conclusions... The data is not
 *  to call out the school committee's faults. The point is to find insights in the data
 *  that we as a community might want to understand." Sixteen reports is sixteen visits and
 *  nobody makes sixteen visits.
 *
 *  NOT ONE WORD ON THIS PAGE IS WRITTEN HERE. Every claim, every figure, every caveat
 *  comes out of `/data/what-it-all-adds-up-to.json`, which `build_master_report.py`
 *  assembles by READING the payload of each report rather than by restating any of them.
 *  So this page cannot say something a report does not -- which is rule 2 carried from
 *  figures to the claims figures support, and it is the whole reason the architecture is
 *  this way round.
 *
 *  IT FAILS CLOSED, AND THAT IS ON THE PAGE. A routed report whose generator publishes no
 *  conclusions gets a named row in "What this page does not speak for", because a
 *  synthesis that quietly drops a report reads as coverage to every reader who cannot
 *  know what is missing.
 *
 *  RULE 7b, WHICH THIS PAGE IS THE PUREST CASE OF. Conclusions, then the same conclusions
 *  organised by report, then what is not here. There is no raw table because this page
 *  holds no raw data: every figure on it belongs to another report and links back to it.
 *
 *  THE PERSONA REVIEW, notes/process/PERSONAS.md, run against this page on 9 September
 *  2026. Six readers, one test each, and what each one changed:
 *
 *   1. THE RESIDENT WHO THINKS THE SCHOOLS ARE NOT STRAIGHT WITH THEM -- can they find
 *      the worst fact in thirty seconds? The order was AREA_TABS order, which opened the
 *      page on "Lunenburg spends below the state median" and read as advocacy. It now
 *      opens on special education, because the bar itself puts that subject second and
 *      `PARENT` says which reports sit behind it. And the fact this reader is looking for
 *      -- that $1,521,536 of the schools' health insurance is appropriated somewhere
 *      other than the schools -- is on a card of its own with the amount set large.
 *   2. THE SECOND-HAND READER -- one repeatable sentence off the first screen. Every
 *      claim is written to be that; the first is a count of children and a share, which
 *      survives being repeated at a kitchen table.
 *   3. THE RESIDENT CLOSE TO THE BOARDS -- mechanisms, never people. No conclusion on
 *      this page names a person or a decision; each says what a quantity did and what
 *      would explain it. That is enforced upstream, in conclusions.py, rather than
 *      checked here by reading.
 *   4. THE FINANCE COMMITTEE MEMBER -- one thing to do differently. Every claim carries
 *      what it does NOT show, and the limits are rows in /what-we-cannot-answer, which is
 *      the registry the records request is generated from. That link is on the page.
 *   5. THE SCHOOL COMMITTEE MEMBER -- is this FY25 again? Not this page's question, and
 *      it is not answered here: the closeout analyses answer it and are listed under the
 *      written documents, which is why that list is on the page rather than implied.
 *   6. THE SELECT BOARD MEMBER -- does it make a town-versus-school argument harder?
 *      Yes, and deliberately: the health insurance conclusion says the school
 *      appropriation understates what the town raises for schools, and the Monty Tech one
 *      says a child moving there moves part of the bill rather than adding to it.
 *
 *  RULE 7 IS DRAWN, NOT ONLY OBSERVED. A conclusion carrying `kind: 'hypothesis'` renders
 *  with the warning rule and its own label wherever it appears, because a measurement and
 *  an explanation for a measurement must never be set in the same voice. The counts of
 *  each are printed at the top so a reader knows the mix before reading any of it. */

type Row = {
  id: string; title: string; url: string; about: string
  generator: string | null; data: string | null
  conclusions: Conclusion[]; count: number
}

type Topic = {
  key: string; title: string; about: string
  reports: Row[]; conclusions: number
}

type Payload = {
  about: string
  reports: Row[]
  topics: Topic[]
  headlines: (Conclusion & { report: string; report_title: string; report_url: string })[]
  not_covered: { id: string; title: string; url: string; why: string }[]
  documents: { id: string; title: string; url: string; doc_url: string; words: number }[]
  totals: {
    reports: number; with_conclusions: number; without_conclusions: number
    conclusions: number; measured: number; hypothesis: number
    documents: number; document_words: number
  }
}

const L = (href: string, t: string) => (
  <a className="underline" style={{ color: 'var(--series-cost)' }} href={abs(href)}>{t}</a>
)

export function WhatItAllAddsUpTo() {
  const { d, err } = useReport<Payload>('what-it-all-adds-up-to.json')
  const title = LABEL[TAB]
  if (!d) return <ReportShell tab={TAB} title={title} err={err} loading={!err}
    dataUrl={DATA} />

  const t = d.totals

  return (
    <ReportShell tab={TAB} title={title} dataUrl={DATA}
      standfirst={`Every conclusion these reports reach, in one place — read out of the reports that computed them.`}>

      {/* ------------------------------------------------ conclusions (rule 7b, first) */}
      <Section kind="conclusions" id="headlines"
        title={`The ${t.with_conclusions} findings a resident should have first`}>
        <Body>
          One from each report &mdash; the one that report leads with. Everything else each
          of them establishes is further down, under its own heading.
        </Body>
        <Conclusions rows={d.headlines} collapse />
        <div className="grid gap-3 mt-6 sm:grid-cols-2 lg:grid-cols-4">
          {d.headlines.map(h => (
            <a key={h.report} href={abs(h.report_url)}
              className="card block p-3 min-h-[44px] text-[13px] font-semibold leading-snug
                         transition-opacity hover:opacity-90"
              style={{ color: 'var(--series-cost)' }}>{h.report_title} &rarr;</a>
          ))}
        </div>
      </Section>

      {/* ------------------------------------------------------- categorical (rule 7b) */}
      <Section kind="categorical" id="all" title="Everything each report establishes">
        <div className="flex flex-wrap gap-x-12 gap-y-6 mt-6">
          <Stat value={String(t.conclusions)}>
            conclusions, across {t.with_conclusions} of the {t.reports} reports in this
            area
          </Stat>
          <Stat value={String(t.measured)} tone="var(--series-cost)">
            of them measurements &mdash; arithmetic on a published figure
          </Stat>
          <Stat value={String(t.hypothesis)} tone="var(--status-warning)">
            offered as an explanation, with nothing here testing it
          </Stat>
          <Stat value={String(t.without_conclusions)}>
            reports this page does not yet speak for, named below
          </Stat>
        </div>
        <Body>
          A figure is a fact and an explanation for a figure is not. The two are drawn
          differently wherever they appear here, and never set in one voice &mdash; a
          conclusion marked as an explanation carries what would settle it.
        </Body>

        {/* BY SUBJECT, not by report. TJ: "the one big report needs to have categorical
            sections too... special education, finances, athletics, etc." The grouping is
            declared once, in scripts/conclusions.py, and build_reports_index.py refuses to
            write if a routed report is in neither that taxonomy nor its own -- two
            groupings over one set drift the moment nothing compares them. */}
        {d.topics.map(t => (
          <div key={t.key} className="mt-14">
            <H2 id={t.key}>{t.title}</H2>
            <p className="text-[15px] leading-relaxed max-w-2xl mt-2"
              style={{ color: 'var(--text-secondary)' }}>{t.about}</p>
            {t.reports.map(r => (
              <div key={r.id} className="mt-8">
                <H3>{L(r.url, r.title)}</H3>
                <Conclusions rows={r.conclusions} collapse reportUrl={r.url} />
              </div>
            ))}
          </div>
        ))}
      </Section>

      {/* -------------------------------------------------------------- raw (rule 7b) */}
      <Section kind="raw" id="not-here" title="What this page does not speak for">
        <Body>
          These reports are routed in this area and are not represented above. They are
          named rather than left out: a summary that quietly drops a report reads as
          coverage to anybody who cannot know what is missing.
        </Body>
        <div className="grid gap-3 mt-5 sm:grid-cols-2">
          {d.not_covered.map(h => (
            <div key={h.id} className="card p-4 avoid-break">
              <p className="text-[14.5px] font-bold leading-snug">
                {L(h.url, h.title)}
              </p>
              <p className="text-[13px] leading-relaxed mt-1.5"
                style={{ color: 'var(--text-secondary)' }}>{h.why}</p>
            </div>
          ))}
          {d.not_covered.length ? null : (
            <p className="text-[14px]" style={{ color: 'var(--text-secondary)' }}>
              Every report in this area is represented above.
            </p>
          )}
        </div>

        <H2 id="documents">And the analyses written as documents</H2>
        <Body>
          {t.documents} of them, {t.document_words.toLocaleString()} words, reaching
          conclusions in prose rather than in a published payload. Nothing on this page
          reads them, so this is not the whole of what this project has concluded &mdash;
          it is the whole of what has been computed in a form a program can check.
        </Body>
        <div className="grid gap-2 mt-5 sm:grid-cols-2 lg:grid-cols-3">
          {d.documents.map(a => (
            <a key={a.id} href={abs(a.url)}
              className="card block p-3 min-h-[44px] text-[13px] font-semibold leading-snug
                         transition-opacity hover:opacity-90"
              style={{ color: 'var(--series-cost)' }}>{a.title} &rarr;</a>
          ))}
        </div>

        <H2 id="method">How this page is built</H2>
        <Body>
          Each report&rsquo;s generator computes its own figures and writes the claims that
          rest on them into that report&rsquo;s published payload. This page reads those
          payloads. Nothing here is typed, which is why it cannot state something a report
          no longer supports &mdash; and why a report that changes its mind changes this
          page on the next build rather than leaving it behind.
        </Body>
        <Body>
          Every claim carries what it rests on and what it does not show. The limits are
          also rows in {L('/what-we-cannot-answer', 'what we cannot answer')}, which is the
          single registry the records request reads from. The index of every analysis this
          project has written, both kinds, is at {L('/reports', 'reports')}.
        </Body>
      </Section>
    </ReportShell>
  )
}

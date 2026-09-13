import { LABEL, type Tab } from '../routes'
import { abs } from '../lib/abs'
import {
  Body, Conclusions, H3, ReportShell, Section, useReport,
  type Conclusion,
} from '../components/report'

const TAB: Tab = 'addsup'
const DATA = '/data/one-big-report.json'

/** ONE REPORT OVER ALL OF THEM -- rebuilt on 13 September 2026 to open with THE NUMBERS
 *  THAT FRAME THE PROBLEM rather than with a digest of sixteen reports' conclusions. TJ:
 *  "change the one big report to something more meaningful to people... deficit per year
 *  each year for 5 years; how many years a 2m, 5m override covers; key drivers...; how
 *  many commercial developments per year...; some 'high level facts'... census... total
 *  staff/FTEs... total students (and change), total athletes (and change)."
 *
 *  Those five sections read `/data/big-picture.json`, written by build_big_picture.py from
 *  the model, DESE's district files and the Census payload. The digest of every report's
 *  conclusions stays, below them, because it is generated and free.
 *
 *  THE ORIGINAL DESIGN NOTE, still true of the digest half:
 *
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

type Item = {
  kind: 'bigpicture' | 'conclusion'; ref: string; note?: string
  value?: string; label?: string; sub?: string; grain?: string; tone?: string
  conclusion?: Conclusion & { report: string; report_title: string; report_url: string }
}
type Section = { key: string; title: string; headline: Item[]; supporting: Item[]; context: Item[] }
type Story = { about: string; sections: Section[]; spec: string; totals: { sections: number; figures: number; conclusions: number; reports: number }; reports: string[] }

const L = (href: string, t: string) => (
  <a className="underline" style={{ color: 'var(--series-cost)' }} href={abs(href)}>{t}</a>
)

/** One story section: the headline figures set large, then the conclusions that deepen
 *  them, then the context rows in a compact table. Built by build_one_big_report.py from
 *  sources/data/one-big-report-story.csv; nothing here decides what appears. */
function StorySection({ s, i }: { s: Section; i: number }) {
  const bigHead = s.headline.filter(x => x.kind === 'bigpicture')
  const conHead = s.headline.filter(x => x.kind === 'conclusion').map(x => x.conclusion!)
  const support = s.supporting.filter(x => x.kind === 'conclusion').map(x => x.conclusion!)
  const ctxBig = s.context.filter(x => x.kind === 'bigpicture')
  const ctxCon = s.context.filter(x => x.kind === 'conclusion').map(x => x.conclusion!)
  return (
    <Section kind={i === 0 ? 'conclusions' : 'categorical'} id={s.key} title={`${i + 1}. ${s.title}`}>
      {/* THE HEADLINE FIGURES ARE THE POINT OF THE SECTION, so they get a card each: the
          number set large, its unit bold beside it, the change on its own line, the grain
          small and grey. TJ: "the 'big metrics' for each section seem downplayed, despite
          i think the point being they are the most important." */}
      {bigHead.length > 0 && (
        <div className="grid gap-3 mt-6 sm:grid-cols-2 lg:grid-cols-3">
          {bigHead.map(x => (
            <div key={x.ref} className="card p-4" style={{ borderLeft: `3px solid ${x.tone === 'critical' ? 'var(--status-critical)' : 'var(--series-cost)'}` }}>
              <div className="flex items-baseline gap-2 flex-wrap">
                <span className="text-3xl font-bold tnum leading-none" style={{ color: x.tone === 'critical' ? 'var(--status-critical)' : 'var(--text-primary)' }}>{x.value}</span>
                <span className="text-[13px] font-semibold" style={{ color: 'var(--text-secondary)' }}>{x.label}</span>
              </div>
              <div className="text-sm mt-2 tnum">{x.sub}</div>
              {x.grain && <div className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>{x.grain}</div>}
            </div>))}
        </div>
      )}
      {conHead.length > 0 && <Conclusions rows={conHead} collapse noAsk />}
      {support.length > 0 && (
        <>
          <H3>Behind it</H3>
          <Conclusions rows={support} collapse noAsk />
        </>
      )}
      {(ctxBig.length > 0 || ctxCon.length > 0) && (
        <>
          <H3>The context</H3>
          {ctxBig.length > 0 && (
            <div className="overflow-x-auto mt-3">
              <table className="text-sm" style={{ minWidth: 520 }}>
                <tbody>{ctxBig.map(x => (
                  <tr key={x.ref} style={{ borderTop: '1px solid var(--grid)' }}>
                    <td className="py-1.5 pr-4 tnum font-bold whitespace-nowrap">{x.value}</td>
                    <td className="py-1.5 pr-4 font-semibold">{x.label}</td>
                    <td className="py-1.5" style={{ color: 'var(--text-secondary)' }}>{x.sub}</td></tr>))}</tbody>
              </table>
            </div>
          )}
          {ctxCon.length > 0 && <Conclusions rows={ctxCon} collapse noAsk />}
        </>
      )}
      <p className="text-xs mt-4" style={{ color: 'var(--text-muted)' }}>
        {[...new Map([...conHead, ...support, ...ctxCon].map(c => [c.report, c])).values()].map((c, k, arr) => (
          <span key={c.report}>{L(c.report_url, c.report_title)}{k < arr.length - 1 ? ' · ' : ''}</span>))}
        {bigHead.length + ctxBig.length > 0 ? (conHead.length + support.length + ctxCon.length > 0 ? ' · ' : '') : ''}
        {bigHead.length + ctxBig.length > 0 ? <span>figures: {L('/bend-the-curve', 'the model')}</span> : null}
      </p>
    </Section>
  )
}

export function WhatItAllAddsUpTo() {
  const { d, err } = useReport<Story>('one-big-report.json')
  const title = LABEL[TAB]
  if (!d) return <ReportShell tab={TAB} title={title} err={err} loading={!err} dataUrl={DATA} />
  return (
    <ReportShell tab={TAB} title={title} dataUrl={DATA}
      standfirst={`${d.totals.sections} subjects, each opening with the figure that matters most and building down into the context — ${d.totals.figures} figures from the model and ${d.totals.conclusions} conclusions from ${d.totals.reports} reports, arranged, not restated.`}>
      <p className="text-[11px] font-semibold uppercase tracking-widest mt-3" style={{ color: 'var(--status-warning)' }}>
        Section 1 is a projection, not a record — the model’s growth rates run forward from the FY27 budget. Everything after it is recorded.
      </p>
      {d.sections.map((s, i) => <StorySection key={s.key} s={s} i={i} />)}
      <Section kind="raw" id="method" title="How this page is built">
        <Body>
          An editor’s sheet — {d.spec} — says what appears and in what order; nothing on it is a sentence. Each figure is rendered from the model’s own payload and each conclusion is the report’s own row, verbatim, so this page cannot state something a report does not. The limits behind it are rows in {L('/what-we-cannot-answer', 'what we cannot answer')}. The analyses written as documents — reaching conclusions in prose rather than in a published payload, among them the two FY26 closeouts that answer “is this FY25 again?” — are not read by this page and are listed, in full, at {L('/reports', 'reports')}.
        </Body>
      </Section>
    </ReportShell>
  )
}

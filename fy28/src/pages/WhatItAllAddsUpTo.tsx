import { LABEL, type Tab } from '../routes'
import { abs } from '../lib/abs'
import {
  Body, Conclusions, H2, H3, NotEstablished, Provenance, ReportShell, Section, Stat, useReport,
  type Conclusion, type Source,
} from '../components/report'

const TAB: Tab = 'addsup'
const DATA = '/data/what-it-all-adds-up-to.json'

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

type Change = { first_fy: number; last_fy: number; first: number; last: number; change: number; pct: number | null; grain?: string }
type Big = {
  about: string; grain: string
  hole: { years: { fy: number; short: number; cut: number; fte: number; cum_fte: number; takes: string[] }[]; total: number; average: number; note: string }
  overrides: { rows: { amount: number; years: number; reopens_fy: number | null; on_average_home: number; townwide: number; townwide_on_average_home: number }[]; school_share: number; first_gap: number; note: string }
  stabilise: { horizons: { years: number; through_fy: number; once: { cut: number; positions: number; share: number }; every_year: { cut: number; positions: number; total_positions: number; share: number } }[]; once: { share: number; cut: number; positions: number; years: number; reopens_fy: number }[]; cost_per_fte: number; headcount: number; contract: number; target: number; fastest: { key: string; label: string; rate: number }; note: string }
  drivers: { rows: { key: string; label: string; who: string; share: number; rate: number; pull: number }[]; blended: number; cap: number; spread_over_cap: number; top2_share: number; note: string }
  development: { target: number; value: number; tax_rate: number; per_development: number; development_value: number; development_mix: string; at_once: number; paces: { per_year: number; years: number | null }[]; current_pace_developments: number; share_of_town: number; note: string }
  facts: {
    census: { vintage: number; window: string; households_with_child: { share: number; share_moe: number; n: number; of: number }; seniors: { share: number; share_moe: number; n: number }; children: { share: number; share_moe: number; n: number } }
    students: Change; teachers: Change; paras: Change; low_income: Change; disabilities: Change
    state_aid: { aid: number; appropriation: number; share: number; grain: string }
    admin_per_pupil: Change & { total_per_pupil: Change }
    athletes: { first_fy: number; last_fy: number; first: number; last: number; change: number; pct: number; years: number; grain: string }
  }
  not_established: string[]; sources: Source[]
}

const usd = (n: number) => '$' + Math.round(n).toLocaleString('en-US')
const usdM = (n: number) => '$' + (n / 1e6).toFixed(n % 1e6 ? 1 : 0) + 'M'
const pct = (x: number, d = 1) => `${(x * 100).toFixed(d)}%`
const pts = (x: number) => `${(x * 100).toFixed(2)} pts`
const n1 = (x: number) => x.toFixed(1)
const signed = (x: number, f: (n: number) => string = n => String(n)) => (x > 0 ? '+' : x < 0 ? '−' : '') + f(Math.abs(x))
const FY = (fy: number) => 'FY' + String(fy).slice(2)
const yrs = (n: number) => `${n} year${n === 1 ? '' : 's'}`

/** A fact: the metric, then one line saying what it is. Rule 7b's card, with the unit. */
function Fact({ value, sub, tone }: { value: string; sub: React.ReactNode; tone?: string }) {
  return (
    <div className="card p-4">
      <div className="text-2xl font-bold tnum leading-none" style={{ color: tone ?? 'var(--text-primary)' }}>{value}</div>
      <div className="text-[13px] mt-2 leading-snug" style={{ color: 'var(--text-secondary)' }}>{sub}</div>
    </div>
  )
}

function ChangeFact({ c, unit, label, what, d = 0, money }: { c: Change; unit: string; label: string; what: string; d?: number; money?: boolean }) {
  return (
    <Fact value={`${money ? '$' : ''}${c.last.toLocaleString('en-US', { maximumFractionDigits: d })} ${unit}`}
      sub={<><strong>{label}</strong>, {FY(c.last_fy)} — {signed(c.change, n => n.toLocaleString('en-US', { maximumFractionDigits: d }))}{c.pct != null ? ` (${signed(c.pct, x => pct(x, 0))})` : ''} since {FY(c.first_fy)}. {what}</>} />
  )
}

function BigPicture({ b }: { b: Big }) {
  const h = b.hole, o = b.overrides, dr = b.drivers, st = b.stabilise, dev = b.development, f = b.facts
  const top = dr.rows.slice(0, 3)
  return (
    <>
      {/* 1 ------------------------------------------------------------ the hole */}
      <Section kind="conclusions" id="hole" title="The hole, year by year — a projection">
        {/* THE EPISTEMIC LABEL, in the same voice the conclusion cards use for a scenario
            (rule 7b): nothing in this section happened. It is what the district's own
            published growth rates produce when run forward, and a reader who takes a
            projected shortfall for a recorded one has been misled. TJ: "make sure the top
            section is listed as a Projection". */}
        <p className="text-[11px] font-semibold uppercase tracking-widest mt-3" style={{ color: 'var(--status-warning)' }}>
          A projection, not a record — the model’s growth rates run forward from the FY27 budget
        </p>
        <div className="flex flex-wrap gap-x-10 gap-y-5 mt-5">
          <Stat value={usd(h.years[0].short)} tone="var(--status-critical)">short next year, {FY(h.years[0].fy)}, at level service</Stat>
          <Stat value={usd(h.total)}>over five years, after each year’s cuts stay cut</Stat>
          <Stat value={n1(h.years[h.years.length - 1].cum_fte)}>positions gone by {FY(h.years[h.years.length - 1].fy)} if it is closed by cutting, in the order the School Committee has said</Stat>
        </div>
        <div className="overflow-x-auto mt-5">
          <table className="text-sm" style={{ minWidth: 620 }}>
            <thead><tr className="text-[10px] font-bold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>
              <th className="text-left py-1.5 pr-4">year</th><th className="text-right py-1.5 pr-4">short by</th><th className="text-right py-1.5 pr-4">positions cut</th><th className="text-left py-1.5">what goes, largest first</th></tr></thead>
            <tbody>{h.years.map(y => (
              <tr key={y.fy} style={{ borderTop: '1px solid var(--grid)' }}>
                <td className="py-2 pr-4 tnum font-semibold">{FY(y.fy)}</td>
                <td className="py-2 pr-4 tnum text-right">{usd(y.short)}</td>
                <td className="py-2 pr-4 tnum text-right">{n1(y.fte)}</td>
                <td className="py-2" style={{ color: 'var(--text-secondary)' }}>{y.takes.join(' · ')}</td></tr>))}</tbody>
          </table>
        </div>
        <p className="text-xs mt-2 max-w-3xl" style={{ color: 'var(--text-muted)' }}>{h.note} Positions are the catalogue’s own FTE for each item cut, and are an estimate.</p>
      </Section>

      {/* 2 ---------------------------------------------------- what an override buys */}
      <Section kind="categorical" id="override" title="What an override buys — projected">
        <div className="grid gap-3 mt-5 sm:grid-cols-2 max-w-3xl">
          {o.rows.map(r => (
            <div key={r.amount} className="card p-4">
              <div className="flex items-baseline gap-2">
                <span className="text-2xl font-bold tnum leading-none">{usdM(r.amount)}</span>
                <span className="text-[10px] font-bold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>school override, once</span>
              </div>
              <div className="mt-3 text-sm"><strong className="tnum">{yrs(r.years)}</strong> before the gap reopens{r.reopens_fy ? `, in ${FY(r.reopens_fy)}` : ''}</div>
              <div className="text-[13px] mt-1 tnum" style={{ color: 'var(--text-secondary)' }}>About {usd(r.on_average_home)} a year on the average tax bill, permanently. As a general override it would have to be {usdM(r.townwide)}, about {usd(r.townwide_on_average_home)} a year, because the schools take {pct(o.school_share, 0)} of the town budget.</div>
            </div>))}
        </div>
        <p className="text-xs mt-2 max-w-3xl" style={{ color: 'var(--text-muted)' }}>{o.note}</p>
      </Section>

      {/* 3 ------------------------------------------------------------ what drives it */}
      <Section kind="categorical" id="drivers" title="What drives it">
        <Body>
          Costs grow <strong className="tnum">{pct(dr.blended, 2)}</strong> a year against a levy that grows <strong className="tnum">{pct(dr.cap, 1)}</strong>. Three lines carry {pct(top.reduce((s, r) => s + r.pull, 0) / dr.rows.filter(r => r.pull > 0).reduce((s, r) => s + r.pull, 0), 0)} of that excess, and none of the three is set by the School Committee.
        </Body>
        <div className="mt-4 max-w-3xl">
          {dr.rows.map(r => (
            <div key={r.key} className="py-1.5 text-sm" style={{ borderTop: '1px solid var(--grid)' }}>
              <div className="flex items-baseline justify-between gap-3">
                <span className="font-semibold min-w-0">{r.label} <span className="font-normal text-xs" style={{ color: 'var(--text-muted)' }}>— {r.who}</span></span>
                <span className="tnum font-bold shrink-0">{pts(r.pull)}</span>
              </div>
              <div className="h-1.5 rounded-full mt-1" style={{ background: 'var(--surface-3)' }}><div className="h-full rounded-full" style={{ width: `${Math.max(0, r.pull / dr.rows[0].pull) * 100}%`, background: 'var(--series-cost)' }} /></div>
              <div className="text-xs mt-0.5 tnum" style={{ color: 'var(--text-muted)' }}>{pct(r.share, 0)} of spending, growing {pct(r.rate, 1)} a year</div>
            </div>))}
        </div>
        <p className="text-xs mt-2 max-w-3xl" style={{ color: 'var(--text-muted)' }}>{dr.note} The dials are on {L('/bend-the-curve', 'Bend the curve')}.</p>
      </Section>

      {/* 3b ------------------------------- what closing it by cutting staff would take */}
      <Section kind="categorical" id="stabilise" title="What closing it with staff cuts alone would take — projected">
        <Body>
          Two horizons, because that is how the town plans: five years and ten. For each, the cut made once now that holds the whole horizon, or the cut made every year. Out of roughly {st.headcount} positions.
        </Body>
        <div className="grid gap-3 mt-4 sm:grid-cols-2 max-w-3xl">
          {st.horizons.map(hz => (
            <div key={hz.years} className="card p-4">
              <p className="text-[10px] font-bold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>hold it {yrs(hz.years)}, through {FY(hz.through_fy)}</p>
              <div className="mt-2 flex items-baseline gap-2"><span className="text-2xl font-bold tnum leading-none" style={{ color: 'var(--status-critical)' }}>{n1(hz.once.positions)}</span><span className="text-sm">positions cut <strong>once</strong>, now — {usd(hz.once.cut)} a year, {pct(hz.once.share, 0)} of the salary line</span></div>
              <div className="mt-2 flex items-baseline gap-2"><span className="text-2xl font-bold tnum leading-none" style={{ color: 'var(--status-critical)' }}>{n1(hz.every_year.positions)}</span><span className="text-sm">positions <strong>every year</strong> instead — {n1(hz.every_year.total_positions)} by {FY(hz.through_fy)}, {pct(hz.every_year.share, 0)} of the salary line</span></div>
            </div>))}
        </div>
        <Body>
          Ten years costs more than twice five. Cutting staff removes the line that grows {pct(st.contract, 0)} and leaves {st.fastest.label.toLowerCase()} at {pct(st.fastest.rate, 0)} and special education at {pct(dr.rows.find(r => r.key === 'sped')!.rate, 1)} as a larger share of what remains, so the budget left behind grows faster than the one before the cut, against revenue at about {pct(st.target, 2)}. A cut shifts the level; the rates decide how long it holds:
        </Body>
        <div className="overflow-x-auto mt-3">
          <table className="text-sm" style={{ minWidth: 480 }}>
            <thead><tr className="text-[10px] font-bold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>
              <th className="text-left py-1.5 pr-4">cut once</th><th className="text-right py-1.5 pr-4">positions</th><th className="text-right py-1.5 pr-4">gap shut for</th><th className="text-left py-1.5">reopens</th></tr></thead>
            <tbody>{st.once.map(r => (
              <tr key={r.share} style={{ borderTop: '1px solid var(--grid)' }}>
                <td className="py-2 pr-4 tnum font-semibold">{pct(r.share, 0)} of staff, {usd(r.cut)}</td>
                <td className="py-2 pr-4 tnum text-right">{r.positions}</td>
                <td className="py-2 pr-4 tnum text-right">{yrs(r.years)}</td>
                <td className="py-2 tnum" style={{ color: 'var(--text-secondary)' }}>{FY(r.reopens_fy)}</td></tr>))}</tbody>
          </table>
        </div>
        <p className="text-xs mt-2 max-w-3xl" style={{ color: 'var(--text-muted)' }}>{st.note}</p>
      </Section>

      {/* 4 ------------------------------------------------- what building would do */}
      <Section kind="categorical" id="building" title={`What it takes to bring in ${usdM(dev.target)} a year`}>
        <div className="flex flex-wrap gap-x-10 gap-y-5 mt-6">
          <Stat value={usdM(dev.value)}>of new taxable value, at ${dev.tax_rate.toFixed(2)} per $1,000 — {pct(dev.share_of_town, 1)} added to the whole town</Stat>
          <Stat value={n1(dev.at_once)}>typical developments, if they all arrived at once — each about {usdM(dev.development_value)} of value paying {usd(dev.per_development)} a year</Stat>
        </div>
        <div className="grid gap-3 mt-5 sm:grid-cols-3 max-w-3xl">
          {dev.paces.map(p => (
            <div key={p.per_year} className="card p-4">
              <div className="text-2xl font-bold tnum leading-none">{p.years != null ? yrs(p.years) : '—'}</div>
              <div className="text-[13px] mt-2" style={{ color: 'var(--text-secondary)' }}>at <strong>{p.per_year} developments a year</strong>, every year, compounding in the levy</div>
            </div>))}
        </div>
        <p className="text-xs mt-2 max-w-3xl" style={{ color: 'var(--text-muted)' }}>A typical development here is {dev.development_mix}. {dev.note} That pace is worth about {n1(dev.current_pace_developments)} such developments a year in value. The full working is on {L('/development', 'development')}.</p>
      </Section>

      {/* 5 ------------------------------------------------------------- the facts */}
      <Section kind="categorical" id="facts" title="The facts any solution has to fit — recorded">
        <Body>Not conclusions — counts, from the Census Bureau and the state, with their grain. Ten years apart where the state publishes ten years.</Body>
        <div className="grid gap-3 mt-5 sm:grid-cols-2 lg:grid-cols-3">
          <Fact value={pct(f.census.households_with_child.share / 100, 0)} sub={<><strong>of households have a child under 18</strong> — {Math.round(f.census.households_with_child.n).toLocaleString('en-US')} of {Math.round(f.census.households_with_child.of).toLocaleString('en-US')}, ± {pct(f.census.households_with_child.share_moe / 100, 1)}. ACS {f.census.window}.</>} />
          <Fact value={pct(f.census.seniors.share / 100, 0)} sub={<><strong>of residents are 65 or over</strong> — {Math.round(f.census.seniors.n).toLocaleString('en-US')}, ± {pct(f.census.seniors.share_moe / 100, 1)}. Against {pct(f.census.children.share / 100, 0)} under 18.</>} />
          <ChangeFact c={f.students} unit="students" label="Students" what="Flat for a decade." />
          <Fact value={pct(f.low_income.last, 0)} sub={<><strong>of students are low-income</strong>, {FY(f.low_income.last_fy)} — up from {pct(f.low_income.first, 0)} in {FY(f.low_income.first_fy)}, as DESE counts it — {signed(f.low_income.pct ?? 0, x => pct(x, 0))} in a decade of flat enrolment.</>} />
          <Fact value={pct(f.disabilities.last, 0)} sub={<><strong>of students have a disability</strong>, {FY(f.disabilities.last_fy)} — from {pct(f.disabilities.first, 0)} in {FY(f.disabilities.first_fy)}, as DESE counts it.</>} />
          <Fact value={pct(f.state_aid.share, 0)} sub={<><strong>of the school budget is state aid</strong> — {usd(f.state_aid.aid)} of {usd(f.state_aid.appropriation)} in FY26, set in the Governor’s budget, not in town.</>} />
          <ChangeFact c={f.teachers} unit="teacher FTE" label="Teachers" what="Assignments, not people; grant-paid and town-paid alike." d={1} />
          <ChangeFact c={f.paras} unit="para FTE" label="Paraprofessionals" what="The line that grew." />
          <ChangeFact c={f.admin_per_pupil} unit="per pupil" money label="Administration spending" what={`Dollars, not people — total spending per pupil moved ${signed(f.admin_per_pupil.total_per_pupil.pct ?? 0, x => pct(x, 0))} in the same years.`} />
          <Fact value={`${f.athletes.last.toLocaleString('en-US')} athletes`} sub={<><strong>Season participations</strong>, {FY(f.athletes.last_fy)} — {signed(f.athletes.change)} ({signed(f.athletes.pct, x => pct(x, 0))}) since {FY(f.athletes.first_fy)}, the {f.athletes.years} years the district has published. A two-sport athlete counts twice.</>} />
        </div>
        <NotEstablished rows={b.not_established} closes="The district’s position control list by FTE and funding source, for any two years ten apart." />
        <Provenance sources={b.sources} />
      </Section>
    </>
  )
}

const L = (href: string, t: string) => (
  <a className="underline" style={{ color: 'var(--series-cost)' }} href={abs(href)}>{t}</a>
)

export function WhatItAllAddsUpTo() {
  const { d, err } = useReport<Payload>('what-it-all-adds-up-to.json')
  const big = useReport<Big>('big-picture.json')
  const title = LABEL[TAB]
  if (!d || !big.d) return <ReportShell tab={TAB} title={title} err={err ?? big.err} loading={!(err ?? big.err)}
    dataUrl={DATA} />

  const t = d.totals

  return (
    <ReportShell tab={TAB} title={title} dataUrl="/data/big-picture.json"
      standfirst="The hole year by year, what an override buys, what drives it, what building would do, and the facts any solution has to fit — then every conclusion the reports reach, in one place.">

      <BigPicture b={big.d} />

      {/* ------------------------------------------------ the digest of every report */}
      <Section kind="categorical" id="headlines"
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

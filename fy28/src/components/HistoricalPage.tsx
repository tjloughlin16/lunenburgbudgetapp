import type { ReactNode } from 'react'
import {
  Bar, BarChart, CartesianGrid, Line, LineChart, ReferenceDot, ReferenceLine,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import { abs } from '../lib/abs'
import { HistoricalPopulation, HistoricalRosters } from './HistoricalCharts'

/* THE LUNENBURG HISTORICAL REPORT, AS A PAGE A RESIDENT WOULD SCROLL FOR FUN.
 *
 * TJ, 30 October 2026: *"can you make that historical report more FUN. it doesnt have to
 * use the same report stylings and such."* Rule 7h: the SHAPE is ours to choose, the
 * integrity is not. So:
 *
 *  - EVERY FIGURE COMES FROM /data/historical-report.json, which
 *    scripts/build_historical_report.py writes from the reports' own text and tables and
 *    refuses to write when a passage it quotes is no longer found. Nothing here computes a
 *    figure; where a derived one is shown (a span, a multiple, a share) it is read from the
 *    payload's registered conclusion figures, so the page and the markdown cannot disagree.
 *  - EVERY CARD CITES ITS EDITION AND PAGE, linked to the PDF at that page.
 *  - OUR READING IS LABELLED AS OURS, beside the thing it qualifies -- the revaluation
 *    coincidence, the run rule, the camp gloss, nominal dollars -- not in a preface.
 *
 * The markdown at /docs/analyses/historical-report.md carries the same figures for /docs,
 * the PDF and agents that run no JavaScript. */

type Cite = { edition: number; page: number; href: string; label?: string }
type Quote = Cite & { quote: string }
type Fig = { text: string; value: number; unit: string }
type Concl = { id: string; figures: Record<string, Fig> }
type Rate = Cite & { rate: number; printed: string }
type Entry = Cite & { name: string; role: string; group: string }
type Run = {
  name: string; first: number; last: number; span: number; seen: number; held: number
  first_entry: Entry; last_entry: Entry
}
type Half = { first: number; last: number; seen: number; first_entry: Entry; last_entry: Entry }

export type HistoricalPayload = {
  conclusions: Concl[]
  tax_rate: Rate[]
  tax_unread: number[]
  revaluations: Quote[]
  population: (Cite & { year: number; value: number; kind: string })[]
  population_conflicts: { year: number; kind: string; printed: (Cite & { value: number })[] }[]
  roster_names: { year: number; names: number }[]
  roster_runs: Run[]
  roster_shared: { name: string; naive_span: number; a: Half; b: Half } | null
  roster_rule: string
  first_aide: { first: Entry; last_fy: number; last_count: number }
  town_manager: (Quote & { what: string })[]
  charter_vote: Cite & { yes: number; no: number }
  then_and_now: {
    t1910: Cite & {
      years: number[]; rate: number[]; houses: number[]; poll: number[]; owners: number[]
      real_estate: number[]; camps: number; trailers: number; motor: number; farm: number
      landscape: Quote
    }
    treasurer: { years: number[]; payroll: number[]; population: number[]; permits: number[]
                 c1961: Cite; c1991: Cite }
    lunch: Cite & { total: number; cents: number }
    levy: { y0: number; y1: number; v0: number; v1: number; c0: Cite; c1: Cite }
  }
  did_you_know: {
    tie: {
      candidates: string[]
      march: Cite & { a: number; b: number; note: string }
      may: Cite & { a: number; b: number; blanks: number }
      board: Quote; rain: Quote
    }
    clerk: Cite & { rows: { year: number; births: number; marriages: number; deaths: number }[]
                    asof: string }
    office: {
      licences: Cite & { dogs: number; fish_game: number }
      prize: Quote
      settled: Cite & { year: number; incorporated: string }
      boston: Quote & { miles: number }
      elevation: Quote & { feet: number }
      jfk: Quote
    }
    prices: { student: (Cite & { cents: number })[]; adult: (Cite & { cents: number })[] }
    government: (Cite & { printed: string }) | null
    area: Cite & { sq_miles: number }
  }
  sources: { label: string; docs_url: string; filename: string; sha256: string; url: string }[]
  not_established: string[]
}

/* ---- small pieces --------------------------------------------------------------- */

const WORD = ['no', 'one', 'two', 'three', 'four', 'five', 'six']
const n = (v: number) => v.toLocaleString('en-US')
const money = (v: number) => '$' + v.toLocaleString('en-US', { maximumFractionDigits: 0 })
const rate = (v: number) => '$' + v.toFixed(2)

/** "1959 report, p. 4", linked to the PDF at that page. Every card carries one. */
function Src({ c, pre }: { c: Cite; pre?: string }) {
  const name = (c.label ?? `${c.edition}`).replace(' Annual Town Report', '')
  return (
    <a href={abs(c.href)} className="underline decoration-dotted underline-offset-2 whitespace-nowrap"
      style={{ color: 'var(--text-muted)' }}>
      {pre}{name} report, p.&nbsp;{c.page}
    </a>
  )
}

/** A note beside the thing it qualifies: what we did, what it does not show. */
function Ours({ children, kind = 'Our reading' }: { children: ReactNode; kind?: string }) {
  return (
    <p className="text-[12.5px] leading-snug mt-3 pl-3"
      style={{ color: 'var(--text-muted)', borderLeft: '2px solid var(--grid)' }}>
      <span className="font-semibold uppercase tracking-wider text-[10.5px] mr-1.5"
        style={{ color: 'var(--text-secondary)' }}>{kind}</span>{children}
    </p>
  )
}

function Section({ id, eyebrow, title, children }: {
  id: string; eyebrow: string; title: ReactNode; children: ReactNode
}) {
  return (
    <section id={id} className="mt-16 scroll-mt-[calc(var(--header-h)+1rem)]">
      <p className="text-[11px] font-bold uppercase tracking-[0.18em]"
        style={{ color: 'var(--series-revenue)' }}>{eyebrow}</p>
      <h2 className="text-[26px] sm:text-[30px] font-bold tracking-tight leading-tight mt-1 max-w-3xl">
        {title}
      </h2>
      {children}
    </section>
  )
}

function QuoteBox({ q, children }: { q: Quote; children?: ReactNode }) {
  return (
    <figure className="card p-4 mt-3 min-w-0">
      <blockquote className="font-serif text-[16px] leading-relaxed italic"
        style={{ color: 'var(--text-primary)' }}>
        “{q.quote.replace(/^"|"$/g, '')}”
      </blockquote>
      <figcaption className="text-[12px] mt-2">{children}<Src c={q} /></figcaption>
    </figure>
  )
}

const tick = { fontSize: 11, fill: 'var(--text-muted)' }
const tip = {
  background: 'var(--surface-1)', border: '1px solid var(--grid)', borderRadius: 8,
  fontSize: 12.5, color: 'var(--text-primary)', boxShadow: '0 2px 10px rgba(0,0,0,.12)',
}

/* ---- the page -------------------------------------------------------------------- */

export function HistoricalPage({ data: d, docUrl }: { data: HistoricalPayload; docUrl: string }) {
  const F = (id: string, k: string) =>
    d.conclusions.find(c => c.id === id)?.figures[k]?.text ?? ''
  const tn = d.then_and_now
  const t1 = tn.t1910
  const tr = tn.treasurer
  const dy = d.did_you_know
  const pop0 = d.population[0]
  const pop1 = d.population[d.population.length - 1]
  const lastRate = d.tax_rate[d.tax_rate.length - 1]
  const peak = d.tax_rate.reduce((a, b) => (b.rate > a.rate ? b : a))

  return (
    <div className="historical min-w-0">
      {/* THE HERO: then and now, in the town's own figures. */}
      <section className="mt-8 rounded-2xl p-5 sm:p-8 min-w-0"
        style={{ background: 'var(--surface-2)', border: '1px solid var(--grid)' }}>
        <p className="text-[11px] font-bold uppercase tracking-[0.18em]"
          style={{ color: 'var(--series-revenue)' }}>
          Lunenburg, then and now
        </p>
        <p className="text-[22px] sm:text-[28px] font-bold tracking-tight leading-tight mt-1 max-w-2xl">
          Settled {dy.office.settled.year}. Incorporated {dy.office.settled.incorporated}.
          Here is what the town printed about itself since.
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-6">
          <ThenNow label="people living here" a={n(pop0.value)} ay={pop0.year} b={n(pop1.value)}
            by={pop1.year} ca={pop0} cb={pop1}
            note={`on the same ${dy.area.sq_miles} square miles`} />
          <ThenNow label="dwelling houses the Assessors counted" a={n(t1.houses[0])}
            ay={t1.years[0]} b={n(t1.houses[1])} by={t1.years[1]} ca={t1} cb={t1}
            note={`plus ${n(t1.camps)} camps in ${t1.years[1]}, and none in ${t1.years[0]}`} />
          <ThenNow label="people on the town payroll" a={n(tr.payroll[0])} ay={tr.years[0]}
            b={n(tr.payroll[2])} by={tr.years[2]} ca={tr.c1961} cb={tr.c1991}
            note={`the Treasurer’s own then-and-now tables`} />
          <ThenNow label="tax rate per $1,000 of assessed value" a={rate(peak.rate)}
            ay={peak.edition} b={rate(lastRate.rate)} by={(lastRate.label ?? `${lastRate.edition}`).replace(' Annual Town Report', '')} ca={peak} cb={lastRate}
            note="the peak, and the latest report. The chart below says why it fell" />
        </div>
      </section>

      {/* 1910 AGAINST 1960: a ledger the Assessors printed, as two postcards. */}
      <Section id="fifty-years" eyebrow={`${t1.years[0]} against ${t1.years[1]}`}
        title="One Assessors’ table, two eras">
        <div className="grid grid-cols-2 gap-2 sm:gap-4 mt-5 min-w-0">
          {[0, 1].map(i => (
            <div key={i} className="rounded-xl p-3 sm:p-5 min-w-0"
              style={{
                background: i ? 'var(--surface-1)' : 'var(--surface-2)',
                border: `1px solid ${i ? 'var(--brand)' : 'var(--grid)'}`,
              }}>
              <div className="text-[34px] sm:text-[48px] font-black tracking-tight leading-none tnum"
                style={{ color: i ? 'var(--brand)' : 'var(--text-muted)' }}>{t1.years[i]}</div>
              <dl className="mt-3 grid grid-cols-1 md:grid-cols-2 gap-x-4 gap-y-2.5">
                <Row k="dwelling houses" v={n(t1.houses[i])} />
                <Row k="camps" v={i ? n(t1.camps) : 'None'} hot={!!i} />
                <Row k="trailers" v={i ? n(t1.trailers) : 'None'} hot={!!i} />
                <Row k="people paying a poll tax" v={n(t1.poll[i])} />
                <Row k="real estate, as valued" v={money(t1.real_estate[i])} />
                <Row k="tax rate per $1,000" v={i ? rate(t1.rate[i]) : '$' + t1.rate[i]} />
                <Row k="motor vehicle excise" v={i ? money(t1.motor) : 'None'} hot={!!i} />
              </dl>
            </div>
          ))}
        </div>
        <p className="text-[12px] mt-2"><Src c={t1} pre="The table: " /></p>
        <div className="grid sm:grid-cols-2 gap-4 mt-2 min-w-0">
          <div className="min-w-0">
            <p className="text-[15px] leading-relaxed mt-3 max-w-xl"
              style={{ color: 'var(--text-secondary)' }}>
              <strong style={{ color: 'var(--text-primary)' }}>{F('one-home-in-five-was-a-camp', 'share')}{' '}
              of homes were camps</strong> — {n(t1.camps)} of the{' '}
              {F('one-home-in-five-was-a-camp', 'homes')} the {t1.years[1]} column counts.
            </p>
            <Ours kind="A local gloss">
              The table does not define “camp”. A camp here is a seasonal house, not lived in
              year-round — local knowledge, not the Assessors’ words. No later report we hold
              prints the category.
            </Ours>
          </div>
          <div className="min-w-0">
            <p className="text-[13px] font-semibold mt-3" style={{ color: 'var(--text-secondary)' }}>
              The same page, answering the question residents kept asking:
            </p>
            <QuoteBox q={t1.landscape} />
          </div>
        </div>
      </Section>

      {/* THE SIGNATURE: the tax rate, with the town's own words at each cliff. */}
      <Section id="tax-rate" eyebrow="The signature chart"
        title={<>The rate hit {rate(peak.rate)}, then fell off a cliff {
          WORD[Number(F('the-rate-fell-because-the-town-revalued', 'n'))] ?? ''} times</>}>
        <p className="text-[15px] leading-relaxed mt-2 max-w-2xl" style={{ color: 'var(--text-secondary)' }}>
          The tax rate printed on the front of each report, per $1,000 of assessed value. Tap a
          point for its page.
        </p>
        <RateChart d={d} peak={peak} />
        <ol className="grid sm:grid-cols-3 gap-3 mt-4 min-w-0">
          {d.revaluations.map((r, i) => (
            <li key={r.edition} className="card p-3.5 min-w-0">
              <div className="flex items-center gap-2">
                <span className="inline-grid place-items-center w-6 h-6 rounded-full text-[12px] font-bold"
                  style={{ background: 'var(--series-revenue)', color: '#fff' }}>{i + 1}</span>
                <span className="text-[15px] font-bold tnum">{r.edition}</span>
              </div>
              <p className="font-serif italic text-[14.5px] leading-snug mt-2">“{r.quote}”</p>
              <p className="text-[12px] mt-2"><Src c={r} /></p>
            </li>
          ))}
        </ol>
        <Ours>
          Each cliff sits beside a report saying the town revalued property that year; the
          reports state the revaluation, and the rate falling with it is our reading of the
          coincidence. A rate set on property valued at a fraction of its worth does not
          compare with one set at full value, so a lower rate is not a lower tax bill.
          {d.tax_unread.length ? <> Not plotted, because their fact pages did not yield a rate
            to our reader: {d.tax_unread.join(', ')}.</> : null}
        </Ours>
      </Section>

      {/* THE TIE OF 1959. */}
      <Section id="the-tie" eyebrow={`${dy.tie.march.edition}`}
        title="The year the Selectman race tied">
        <div className="grid sm:grid-cols-2 gap-4 mt-5 min-w-0">
          <Ballot title="March, the town election" sub={dy.tie.march.note.replace(/^\*/, '')}
            names={dy.tie.candidates} votes={[dy.tie.march.a, dy.tie.march.b]} c={dy.tie.march} tie />
          <Ballot title="May, a special election" sub={`blanks: ${n(dy.tie.may.blanks)}`}
            names={dy.tie.candidates} votes={[dy.tie.may.a, dy.tie.may.b]} c={dy.tie.may} />
        </div>
        <div className="grid sm:grid-cols-2 gap-4 mt-1 min-w-0">
          <QuoteBox q={dy.tie.board}>The Selectmen, </QuoteBox>
          <QuoteBox q={{ ...dy.tie.rain, quote: dy.tie.rain.quote + '.' }}>And, same report, </QuoteBox>
        </div>
        <Ours kind="What it does not show">
          What the recount found. The report prints the original count and the special
          election, not the recount’s figures.
        </Ours>
      </Section>

      {/* THE ROAD TO A TOWN MANAGER. */}
      <Section id="town-manager" eyebrow={`${F('a-town-manager-took-thirty-three-years', 'n')} years`}
        title="The long road to a town manager">
        <ol className="relative mt-6 ml-3 min-w-0" style={{ borderLeft: '2px solid var(--grid)' }}>
          {d.town_manager.map((s, i) => (
            <li key={s.edition + s.what} className="relative pl-6 pb-6 last:pb-0 min-w-0">
              <span className="absolute -left-[9px] top-1 w-4 h-4 rounded-full"
                style={{
                  background: i === d.town_manager.length - 1 ? 'var(--brand)' : 'var(--surface-1)',
                  border: '2px solid var(--brand)',
                }} />
              <div className="text-[22px] font-black tracking-tight leading-none tnum"
                style={{ color: 'var(--brand)' }}>{s.edition}</div>
              <p className="text-[15px] font-semibold mt-1">{s.what}</p>
              <p className="font-serif italic text-[14.5px] leading-snug mt-1 break-words"
                style={{ color: 'var(--text-secondary)' }}>“{s.quote}”</p>
              <p className="text-[12px] mt-1"><Src c={s} /></p>
              {s.edition === d.charter_vote.edition ? <CharterVote v={d.charter_vote} /> : null}
            </li>
          ))}
        </ol>
        {dy.government ? (
          <Ours kind="Also">
            The fact page’s “type of government” line first reads “{dy.government.printed}”
            in the <Src c={dy.government} />.
          </Ours>
        ) : null}
      </Section>

      {/* LONGEST ON THE ROSTERS: a leaderboard drawn as careers on one time axis. */}
      <Section id="rosters" eyebrow="Leaderboard" title="Longest on the school rosters">
        <Leaderboard runs={d.roster_runs} names={d.roster_names} />
        <Ours kind="How a run is counted">
          {d.roster_rule} That threshold is ours. A run is the first and last roster a name is
          printed in — not a hire date, not a retirement, and a name is not a person.
        </Ours>
      </Section>

      {/* THE MYSTERY. */}
      {d.roster_shared ? <Mystery s={d.roster_shared} gap={F('one-name-two-careers', 'g')} /> : null}

      {/* THE TOWN CLERK'S DECADE. */}
      <Section id="clerk" eyebrow={`${dy.clerk.rows[0].year} to ${dy.clerk.rows[dy.clerk.rows.length - 1].year}`}
        title="The Town Clerk charted a decade of births">
        <p className="text-[15px] leading-relaxed mt-2 max-w-2xl" style={{ color: 'var(--text-secondary)' }}>
          {F('the-clerks-decade', 'a')} births recorded in {F('the-clerks-decade', 'ay')},{' '}
          {F('the-clerks-decade', 'b')} in {F('the-clerks-decade', 'by')}. The clerk’s own chart,
          printed in the {dy.clerk.edition} report; its last column is “{dy.clerk.asof}”.
        </p>
        <BirthsChart rows={dy.clerk.rows} />
        <p className="text-[12px] mt-1"><Src c={dy.clerk} pre="The chart: " /></p>
        <Ours kind="What it does not show">
          Why births rose. The chart is a count of what the office recorded and gives no cause.
        </Ours>
      </Section>

      {/* LUNCH. */}
      <Section id="lunch" eyebrow={`School lunch, ${tn.lunch.edition}`}
        title={<>{n(tn.lunch.total)} lunches, at {tn.lunch.cents}¢ each</>}>
        <div className="grid grid-cols-2 gap-3 mt-5 min-w-0">
          <PriceTag who="a student" p={dy.prices.student} />
          <PriceTag who="an adult" p={dy.prices.adult} />
        </div>
        <p className="text-[12px] mt-2">The {tn.lunch.edition} count: <Src c={tn.lunch} /></p>
        <Ours kind="How the prices were read">
          From the lunch tables’ own column headers. Only headers whose cent sign reads
          cleanly are used, so some years are missing rather than guessed.
        </Ours>
      </Section>

      {/* DID YOU KNOW. */}
      <Section id="did-you-know" eyebrow="Did you know" title="Odds and ends from the reports">
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3 mt-5 min-w-0">
          <Fact big={`${n(dy.office.licences.dogs)}`} unit="dog licences" c={dy.office.licences}>
            issued by the town office in {dy.office.licences.edition}, beside{' '}
            {n(dy.office.licences.fish_game)} fish and game licences.
          </Fact>
          <Fact big="Third prize" unit="for the town report itself" c={dy.office.prize}>
            “{dy.office.prize.quote.replace(/^Last year's efforts resulted in /, '…').replace(/"$/, '')}”
          </Fact>
          <Fact big="JFK" unit="on the list of senators" c={dy.office.jfk}>
            The {dy.office.jfk.edition} report’s list of representatives opens “{dy.office.jfk.quote}”.
          </Fact>
          <Fact big={`${dy.office.boston.miles} miles`} unit="to Boston" c={dy.office.boston}>
            “{dy.office.boston.quote}”, and Town Hall sits at about {dy.office.elevation.feet} feet
            above sea level.
          </Fact>
          <Fact big={`${d.first_aide.last_count}`} unit="paraprofessionals" c={d.first_aide.first}>
            on the {d.first_aide.last_fy} roster. The first aide on any roster we hold, in{' '}
            {d.first_aide.first.edition}: {d.first_aide.first.name}, “{d.first_aide.first.role}”.
          </Fact>
          <Fact big={F('the-levy-then-and-now', 'x')} unit={`the ${tn.levy.y0} tax levy, by FY${tn.levy.y1}`}
            c={tn.levy.c1}>
            {money(tn.levy.v0)} raised by taxation in {tn.levy.y0} (<Src c={tn.levy.c0} />);{' '}
            {money(tn.levy.v1)} levied in FY{tn.levy.y1}. Nominal dollars: no price index held
            here reaches back that far, so none is applied.
          </Fact>
          <Fact big={`${n(tr.permits[0])} → ${n(tr.permits[1])}`} unit="building permits a year"
            c={tr.c1991}>
            {tr.years[1]} against {tr.years[2]}, from the Treasurer’s then-and-now tables.
          </Fact>
          <Fact big={money(t1.farm)} unit="farm animal excise" c={t1}>
            collected in {t1.years[1]}. The {t1.years[0]} column prints “None”.
          </Fact>
        </div>
      </Section>

      {/* ACROSS THE YEARS: the two quieter series. */}
      <Section id="across-the-years" eyebrow="Across the years" title="People, and names on the rosters">
        <div className="grid lg:grid-cols-2 gap-6 mt-5 min-w-0">
          <div className="card p-4 min-w-0">
            <p className="text-[14px] font-bold">Population, by the year each census counted</p>
            <HistoricalPopulation data={d} alt="" />
            {d.population_conflicts.length ? (
              <Ours kind="Left off the chart">
                Years where two editions print two figures for the same count:{' '}
                {d.population_conflicts.map((c, i) => (
                  <span key={c.year}>{i ? '; ' : ''}{c.year} ({c.kind}){' '}
                    {c.printed.map((p, j) => (
                      <span key={p.edition}>{j ? ' or ' : ''}{n(p.value)} (<Src c={p} />)</span>
                    ))}
                  </span>
                ))}. We do not choose.
              </Ours>
            ) : null}
          </div>
          <div className="card p-4 min-w-0">
            <p className="text-[14px] font-bold">Distinct names printed in the school rosters</p>
            <HistoricalRosters data={d} alt="" />
            <Ours kind="What it is not">
              A count of printed names, not a staffing level: no roster states hours, and some
              years print only part of the district.
            </Ours>
          </div>
        </div>
      </Section>

      {/* THE LIMITS AND THE SOURCES, last. */}
      <Section id="limits" eyebrow="Honest limits" title="What these reports cannot tell us">
        <ul className="mt-4 space-y-2 max-w-2xl">
          {d.not_established.map(s => (
            <li key={s} className="text-[14.5px] leading-relaxed pl-4 relative"
              style={{ color: 'var(--text-secondary)' }}>
              <span className="absolute left-0" style={{ color: 'var(--series-revenue)' }}>•</span>{s}
            </li>
          ))}
        </ul>
        <details className="card p-4 mt-6">
          <summary className="cursor-pointer text-[14px] font-semibold">
            The {d.sources.length} reports quoted on this page
          </summary>
          <ul className="mt-3 space-y-1.5">
            {d.sources.map(s => (
              <li key={s.filename} className="text-[12.5px] leading-snug break-words"
                style={{ color: 'var(--text-muted)' }}>
                <a className="underline" style={{ color: 'var(--series-cost)' }}
                  href={abs(s.docs_url)}>{s.label}</a> — <code>{s.filename}</code>, sha256{' '}
                <code>{s.sha256.slice(0, 12)}…</code>
                {s.url ? <> · <a className="underline" href={s.url}>publisher’s copy</a></> : null}
              </li>
            ))}
          </ul>
        </details>
        <p className="text-[13px] mt-4" style={{ color: 'var(--text-muted)' }}>
          Every figure here is also in <a className="underline" style={{ color: 'var(--series-cost)' }}
            href={abs(docUrl)}>the full document</a>, with every table, generated by{' '}
          <code>scripts/build_historical_report.py</code>.
        </p>
      </Section>
    </div>
  )
}

/* ---- the pieces ------------------------------------------------------------------ */

function ThenNow({ label, a, ay, b, by, ca, cb, note }: {
  label: string; a: string; ay: number; b: string; by: number | string; ca: Cite; cb: Cite; note: string
}) {
  return (
    <div className="rounded-xl p-4 min-w-0" style={{ background: 'var(--surface-1)', border: '1px solid var(--grid)' }}>
      <div className="flex items-end gap-3 flex-wrap">
        <div className="min-w-0">
          <div className="text-[11px] font-semibold tnum" style={{ color: 'var(--text-muted)' }}>{ay}</div>
          <div className="text-[22px] font-bold tnum leading-none" style={{ color: 'var(--text-muted)' }}>{a}</div>
        </div>
        <div className="text-[20px] leading-none pb-0.5" aria-hidden style={{ color: 'var(--series-revenue)' }}>→</div>
        <div className="min-w-0">
          <div className="text-[11px] font-semibold tnum" style={{ color: 'var(--brand)' }}>{by}</div>
          <div className="text-[34px] font-black tracking-tight tnum leading-none" style={{ color: 'var(--brand)' }}>{b}</div>
        </div>
      </div>
      <p className="text-[14px] font-semibold mt-2">{label}</p>
      <p className="text-[12.5px] leading-snug mt-0.5" style={{ color: 'var(--text-muted)' }}>{note}</p>
      <p className="text-[11.5px] mt-1.5">
        <Src c={ca} />{ca.href !== cb.href ? <> · <Src c={cb} /></> : null}
      </p>
    </div>
  )
}

function Row({ k, v, hot }: { k: string; v: string; hot?: boolean }) {
  return (
    <div className="min-w-0">
      <dt className="text-[11px] sm:text-[12px] leading-tight" style={{ color: 'var(--text-muted)' }}>{k}</dt>
      <dd className="text-[16px] sm:text-[20px] font-bold tnum leading-tight break-words"
        style={hot ? { color: 'var(--series-revenue)' } : v === 'None'
          ? { color: 'var(--text-muted)', fontStyle: 'italic', fontWeight: 500 } : undefined}>{v}</dd>
    </div>
  )
}

function RateChart({ d, peak }: { d: HistoricalPayload; peak: Rate }) {
  return (
    <div className="card p-3 sm:p-4 mt-4 min-w-0">
      <div style={{ width: '100%', height: 340 }}>
        <ResponsiveContainer>
          <LineChart data={d.tax_rate} margin={{ top: 28, right: 14, left: -6, bottom: 4 }}>
            <CartesianGrid stroke="var(--grid)" vertical={false} />
            <XAxis dataKey="edition" type="number" domain={['dataMin', 'dataMax']}
              tickCount={7} allowDecimals={false} tick={tick} />
            <YAxis tickFormatter={(v: number) => `$${v}`} width={46} tick={tick} />
            <Tooltip contentStyle={tip} labelFormatter={l => `${l} report`}
              formatter={(v, _n, p: { payload?: Rate }) =>
                [`${rate(Number(v))} per $1,000 — p. ${p.payload?.page}`, 'printed rate']} />
            {d.revaluations.map((r, i) => (
              <ReferenceLine key={r.edition} x={r.edition} stroke="var(--series-revenue)"
                strokeDasharray="4 3"
                label={{ value: `${i + 1}`, position: 'top', fontSize: 13, fontWeight: 700,
                         fill: 'var(--series-revenue)' }} />
            ))}
            <Line dataKey="rate" type="linear" stroke="var(--brand)" strokeWidth={2.5}
              dot={{ r: 2.5 }} isAnimationActive={false} />
            <ReferenceDot x={peak.edition} y={peak.rate} r={5} fill="var(--brand)" stroke="none"
              label={{ value: `${rate(peak.rate)} peak`, position: 'right', fontSize: 12,
                       fontWeight: 700, fill: 'var(--brand)' }} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

function Ballot({ title, sub, names, votes, c, tie }: {
  title: string; sub: string; names: string[]; votes: number[]; c: Cite; tie?: boolean
}) {
  const max = Math.max(...votes)
  return (
    <div className="card p-4 min-w-0">
      <p className="text-[13px] font-bold uppercase tracking-wider" style={{ color: 'var(--text-secondary)' }}>{title}</p>
      <p className="text-[12px]" style={{ color: 'var(--text-muted)' }}>{sub}</p>
      <div className="mt-3 space-y-3">
        {names.map((nm, i) => (
          <div key={nm} className="min-w-0">
            <div className="flex justify-between gap-2 text-[14px]">
              <span className="font-semibold truncate">{nm}</span>
              <span className="font-bold tnum">{n(votes[i])}</span>
            </div>
            <div className="h-3 rounded-full mt-1" style={{ background: 'var(--surface-2)' }}>
              <div className="h-3 rounded-full" style={{
                width: `${(100 * votes[i]) / max}%`,
                background: tie ? 'var(--series-revenue)' : i === 0 ? 'var(--brand)' : 'var(--text-muted)',
              }} />
            </div>
          </div>
        ))}
      </div>
      {tie ? <p className="text-[22px] font-black tracking-tight mt-3" style={{ color: 'var(--series-revenue)' }}>A tie, on the first count.</p> : null}
      <p className="text-[12px] mt-2"><Src c={c} /></p>
    </div>
  )
}

function CharterVote({ v }: { v: HistoricalPayload['charter_vote'] }) {
  const tot = v.yes + v.no
  return (
    <div className="card p-3 mt-3 max-w-md min-w-0">
      <p className="text-[12.5px] font-semibold">The charter question at the town election</p>
      <div className="flex h-6 rounded-md overflow-hidden mt-2 text-[12px] font-bold tnum">
        <div className="grid place-items-center" style={{ width: `${(100 * v.yes) / tot}%`, background: 'var(--brand)', color: 'var(--surface-1)' }}>
          Yes {n(v.yes)}</div>
        <div className="grid place-items-center" style={{ width: `${(100 * v.no) / tot}%`, background: 'var(--text-muted)', color: 'var(--surface-1)' }}>
          No {n(v.no)}</div>
      </div>
      <p className="text-[12px] mt-1.5"><Src c={v} /></p>
    </div>
  )
}

function Leaderboard({ runs, names }: { runs: Run[]; names: { year: number }[] }) {
  const y0 = names[0].year
  const y1 = names[names.length - 1].year
  const pct = (y: number) => (100 * (y - y0)) / (y1 - y0)
  return (
    <ol className="mt-5 space-y-3">
      {runs.map((r, i) => (
        <li key={r.name} className="card p-3.5 min-w-0">
          <div className="flex items-start gap-3">
            <span className="text-[26px] font-black leading-none tnum w-7 shrink-0"
              style={{ color: i === 0 ? 'var(--series-revenue)' : 'var(--text-muted)' }}>{i + 1}</span>
            <div className="min-w-0 flex-1">
              <div className="flex items-baseline justify-between gap-2 flex-wrap">
                <span className="text-[16px] font-bold">{r.name}</span>
                <span className="text-[14px] tnum" style={{ color: 'var(--text-secondary)' }}>
                  <strong className="text-[20px]" style={{ color: 'var(--text-primary)' }}>{r.span}</strong> years
                  · {r.first}–{r.last}
                </span>
              </div>
              <div className="relative h-2.5 rounded-full mt-2" style={{ background: 'var(--surface-2)' }}>
                <div className="absolute h-2.5 rounded-full" style={{
                  left: `${pct(r.first)}%`, width: `${pct(r.last) - pct(r.first)}%`,
                  background: i === 0 ? 'var(--series-revenue)' : 'var(--brand)',
                }} />
              </div>
              <div className="flex justify-between text-[10.5px] tnum mt-0.5" style={{ color: 'var(--text-muted)' }}>
                <span>{y0}</span><span>{y1}</span>
              </div>
              <p className="text-[12.5px] leading-snug mt-1.5 break-words" style={{ color: 'var(--text-secondary)' }}>
                First: “{r.first_entry.role || r.first_entry.group}” (<Src c={r.first_entry} />).
                Last: “{r.last_entry.role || r.last_entry.group}” (<Src c={r.last_entry} />).
                Printed in {r.seen} of the {r.held} rosters we hold for those years.
              </p>
            </div>
          </div>
        </li>
      ))}
    </ol>
  )
}

function Mystery({ s, gap }: { s: NonNullable<HistoricalPayload['roster_shared']>; gap: string }) {
  const half = (h: Half, tone: string) => (
    <div className="rounded-xl p-4 min-w-0" style={{ background: 'var(--surface-1)', border: `1px solid ${tone}` }}>
      <div className="text-[22px] font-black tnum leading-none" style={{ color: tone }}>{h.first}–{h.last}</div>
      <p className="text-[14px] font-semibold mt-2 break-words">
        “{h.last_entry.role || h.last_entry.group || h.first_entry.role || h.first_entry.group}”
      </p>
      <p className="text-[12px] mt-1" style={{ color: 'var(--text-muted)' }}>
        printed on {h.seen} rosters · <Src c={h.first_entry} /> · <Src c={h.last_entry} />
      </p>
    </div>
  )
  return (
    <Section id="mystery" eyebrow="A roster mystery" title={<>One name, two careers: {s.name}</>}>
      <div className="grid sm:grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] gap-3 items-center mt-5 min-w-0">
        {half(s.a, 'var(--brand)')}
        <div className="text-center py-1">
          <div className="text-[40px] font-black leading-none" style={{ color: 'var(--series-revenue)' }}>?</div>
          <div className="text-[12px]" style={{ color: 'var(--text-muted)' }}>absent from {gap} rosters</div>
        </div>
        {half(s.b, 'var(--subj-3)')}
      </div>
      <p className="text-[15px] leading-relaxed mt-4 max-w-2xl" style={{ color: 'var(--text-secondary)' }}>
        Matched on the name alone, this would top the leaderboard at {s.naive_span} years.
        Whether the cafeteria’s cook and the name under Phys.&nbsp;Ed. are one person, no
        report says.
      </p>
      <Ours kind="Why it is split">
        Same name is not same person. That is why a run on this page breaks on a long absence.
      </Ours>
    </Section>
  )
}

function BirthsChart({ rows }: { rows: { year: number; births: number; marriages: number; deaths: number }[] }) {
  return (
    <div className="card p-3 sm:p-4 mt-4 min-w-0">
      <div style={{ width: '100%', height: 240 }}>
        <ResponsiveContainer>
          <BarChart data={rows} margin={{ top: 18, right: 8, left: -18, bottom: 0 }}>
            <CartesianGrid stroke="var(--grid)" vertical={false} />
            <XAxis dataKey="year" tick={tick} interval={0} tickFormatter={(y: number) => `’${String(y).slice(2)}`} />
            <YAxis tick={tick} width={44} />
            <Tooltip contentStyle={tip} labelFormatter={l => `${l}`}
              formatter={(v, _n, p: { payload?: { marriages: number; deaths: number } }) =>
                [`${v} births · ${p.payload?.marriages} marriages · ${p.payload?.deaths} deaths`, 'recorded']} />
            <Bar dataKey="births" fill="var(--brand)" radius={[4, 4, 0, 0]} isAnimationActive={false}
              label={{ position: 'top', fontSize: 10.5, fill: 'var(--text-muted)' }} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

function PriceTag({ who, p }: { who: string; p: (Cite & { cents: number })[] }) {
  const a = p[0]
  const b = p[p.length - 1]
  return (
    <div className="rounded-xl p-4 min-w-0" style={{ background: 'var(--surface-1)', border: '1px dashed var(--series-revenue)' }}>
      <p className="text-[12px] font-semibold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>
        lunch for {who}</p>
      <div className="flex items-baseline gap-2 mt-1 flex-wrap tnum">
        <span className="text-[30px] font-black" style={{ color: 'var(--text-muted)' }}>{a.cents}¢</span>
        <span aria-hidden style={{ color: 'var(--series-revenue)' }}>→</span>
        <span className="text-[30px] font-black" style={{ color: 'var(--series-revenue)' }}>{b.cents}¢</span>
      </div>
      <p className="text-[12px] mt-1" style={{ color: 'var(--text-muted)' }}>
        {a.edition} → {b.edition}
      </p>
      <p className="text-[11.5px] mt-1"><Src c={a} /> · <Src c={b} /></p>
    </div>
  )
}

function Fact({ big, unit, c, children }: { big: string; unit: string; c: Cite; children: ReactNode }) {
  return (
    <div className="card p-4 min-w-0 flex flex-col">
      <div className="text-[28px] font-black tracking-tight leading-none tnum" style={{ color: 'var(--brand)' }}>{big}</div>
      <div className="text-[13px] font-semibold mt-1">{unit}</div>
      <p className="text-[13.5px] leading-snug mt-2 flex-1 break-words" style={{ color: 'var(--text-secondary)' }}>{children}</p>
      <p className="text-[11.5px] mt-2"><Src c={c} /></p>
    </div>
  )
}

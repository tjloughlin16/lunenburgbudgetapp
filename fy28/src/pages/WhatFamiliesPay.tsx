import { useEffect, useMemo, useState } from 'react'
import { abs } from '../lib/abs'
import { TableTwin } from '../components/StateAidCharts'
import {
  BothReadings, Choice, LadderExhibit, SEASON, YEAR, money,
} from '../components/FamilyFeeCharts'

/** What a Lunenburg family actually pays for school in a year.
 *
 *  WHY THIS PAGE EXISTS. Residents say two things at meetings. One: parents should pay
 *  more, because they are the ones using the schools. Two: parents already pay a great
 *  deal, athletes' families especially. Both are claims about a number, so somebody asked
 *  this site to compute the number for families of one, two, three and four children.
 *
 *  THE ANSWER IS NOT A NUMBER, AND THAT IS THE PAGE. The family cap states no period, six
 *  fees the district sells have no published amount, and the ladder of per-child rates
 *  stops at the third child. So every total here is a FLOOR with an open band above it,
 *  and the band is a COUNT OF NAMED FEES rather than a dollar guess (rule 7).
 *
 *  SHAPE (rule 7b): conclusions, then the model and the organised data, then the raw and
 *  the caveats. A reader who stops after the first screen carries away the cap ambiguity
 *  and the five-children exhibit, which is the argument that needs no data at all.
 *
 *  RULE 7 IS THE HARD PART HERE, and it is the cap. That the two readings differ is a
 *  MEASUREMENT. That the per-season reading is implausible is an INFERENCE — from the cap
 *  being unreachable by family size — and it is labelled as one every time it appears. The
 *  page never says what the cap means, because nothing published says.
 *
 *  RULE 8. The fees were set in public by roll call and the schedule is the district's own.
 *  Nothing here says anybody set a wrong fee. What it says is that the archive cannot pin
 *  the cap's period and six fees carry no amount — and one email closes both.
 *
 *  RULE 2. Not one figure is typed into this file. Rates arrive from
 *  /data/what-families-pay.json; scenarios are looked up from the grid the generator
 *  computed, so the page and the verifier cannot disagree about arithmetic.
 *
 *  NO D1 AT PAGE LOAD. One static file. */

type Ladder = {
  fy: number; level: string; kind: string; rates: number[]; stops_after: number
  pct: number | null; ratio: number | null; ratio_exact: boolean; source: string | null
}
type Cell = {
  children: number; sports: number; seasons: number[]; uncapped: number
  per_season: number; per_year: number; spread: number
  unknown_child_rates: number; inferred_child_rates: number
  computable: boolean; fully_published: boolean
}
type Tier = {
  available: boolean; flat: number | null; source: string | null; source_ref: string | null
  grid: Cell[]; max_spread: number; season_cap_ever_binds: boolean
  uncomputable: { children: number; sports: number }[]
  inferred: { children: number; sports: number }[]
}
type BusTier = {
  amount: number | null; status: string; source: string; source_file: string | null
  source_ref: string | null
}
type Cap = {
  fy: number; school_year: string; amount: number; level: string; unit: string
  unit_status: string; unit_basis: string; unit_quote: string | null
  source: string; source_file: string | null; source_ref: string | null; verified: string
  ladder: number[]; ladder_sum: number | null; ladder_complete: boolean
  headroom: number | null
}
type Payload = {
  generated_by: string; source: string
  seasons: number; max_children: number; max_sports: number
  tiers: string[]
  default: { fy: number; level: string; children: number; sports: number; tier: string
    bus: boolean }
  schedule: {
    fy: number; school_year: string; level: string; item: string; amount: number
    unit: string; unit_status: string; unit_basis: string; unit_quote: string
    set_on: string; source: string; source_file: string; source_ref: string
    verified: string; confirming: boolean
  }[]
  caps: Cap[]
  cap_stated: number[]
  cap_unstated: number[]
  ladder_exhibit: {
    fy: number; level: string; cap: number; seasons: number; published_steps: number
    ratio: number; ratio_pct: number; flat_rate: number; reaches_cap: boolean
    rule: string; assumption_rule: string; assumption_flat: string
    rows: {
      children: number; published: boolean; footing: string
      rate_by_rule: number; rate_flat: number
      cumulative_by_rule: number; cumulative_flat: number; under_cap: boolean
      headroom_by_rule: number; headroom_flat: number
    }[]
  }
  years: {
    fy: number; cap: Cap | null
    levels: Record<string, { ladder: Ladder; reduced: number | null
      reduced_status: string; tiers: Record<string, Tier> }>
    bus: Record<string, BusTier>
  }[]
  max_spread: number
  max_spread_at: { fy: number; level: string; tier: string; children: number; sports: number }
  published_spread: number
  published_spread_at: { fy: number; level: string; tier: string; children: number
    sports: number }
  season_cap_binds_anywhere: boolean
  fourth_child: {
    fy: number; level: string; published_steps: number; by_rule: number; flat: number
    uncomputable: { children: number; sports: number }[]
    inferred: { children: number; sports: number }[]
  }
  unpriced: {
    fy: string | null; category: string; unit: string; item: string; status: string
    source: string; source_ref: string | null
  }[]
  unpriced_count: number
  unpriced_portal: number
  faq: { cite: string; quotes: string[]; title: string }
  said: { key: string; board: string; date: string; who: string; quote: string; why: string
    cite: string; town: string }[]
  gaps: { side: string; what: string; why: string; closes: string | null }[]
  related: { id: string; title: string; why: string; words: number; updated: string
    url: string; pdf: string | null }[]
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

/** A claim the page makes, with the one thing it rests on. */
function Insight({ tone, headline, children }: {
  tone: string; headline: React.ReactNode; children: React.ReactNode
}) {
  return (
    <div className="card p-5" style={{ borderTop: `3px solid ${tone}` }}>
      <p className="text-[16px] font-bold leading-snug">{headline}</p>
      <div className="text-[13.5px] leading-relaxed mt-2"
        style={{ color: 'var(--text-secondary)' }}>{children}</div>
    </div>
  )
}

/** The badge that says how a figure is footed. It is on every rate on this page, because
 *  "published", "produced by a published rule" and "nothing says" are the three states the
 *  whole page is about (rule 3). */
function Footing({ status }: { status: string }) {
  const stated = status === 'stated' || status === 'published'
  const none = status === 'not established' || status === 'not published'
    || status === 'unknown'
  return (
    <span className="text-[10px] font-bold uppercase tracking-widest whitespace-nowrap"
      style={{ color: none ? SEASON : stated ? 'var(--text-secondary)' : YEAR }}>
      {status}
    </span>
  )
}

const fyLabel = (n: number) => `FY${n}`

export function WhatFamiliesPay() {
  const [d, setD] = useState<Payload | null>(null)
  const [err, setErr] = useState(false)

  useEffect(() => {
    fetch(abs('/data/what-families-pay.json'))
      .then(r => (r.ok ? r.json() : Promise.reject(new Error(String(r.status)))))
      .then(setD).catch(() => setErr(true))
  }, [])

  const [fy, setFy] = useState<number | null>(null)
  const [level, setLevel] = useState<string | null>(null)
  const [tier, setTier] = useState<string | null>(null)
  const [children, setChildren] = useState<number | null>(null)
  const [sports, setSports] = useState<number | null>(null)
  const [bus, setBus] = useState<boolean | null>(null)

  useEffect(() => {
    if (!d) return
    setFy(v => v ?? d.default.fy)
    setLevel(v => v ?? d.default.level)
    setTier(v => v ?? d.default.tier)
    setChildren(v => v ?? d.default.children)
    setSports(v => v ?? d.default.sports)
    setBus(v => v ?? d.default.bus)
  }, [d])

  const year = useMemo(
    () => (d && fy !== null ? d.years.find(y => y.fy === fy) ?? null : null), [d, fy])
  const lv = year && level ? year.levels[level] : null
  const tierData = lv && tier ? lv.tiers[tier] : null
  const cell = useMemo(() => (
    tierData && children !== null && sports !== null
      ? tierData.grid.find(g => g.children === children && g.sports === sports) ?? null
      : null), [tierData, children, sports])

  const busAmount = useMemo(() => {
    if (!year || !bus || children === null || tier === null) return 0
    const key = tier === 'waived' ? 'qualifying families'
      : children === 1
        ? (tier === 'reduced' ? 'one student, reduced' : 'one student')
        : (tier === 'reduced' ? 'two or more, reduced' : 'two or more students')
    return year.bus[key]?.amount ?? null
  }, [year, bus, children, tier])

  if (err) {
    return (
      <div className="mx-auto max-w-4xl px-5 py-12">
        <h1 className="text-3xl font-bold">What a family pays</h1>
        <Body>The fee data did not load. It is a single static file at{' '}
          <a className="underline" href={abs('/data/what-families-pay.json')}>
            /data/what-families-pay.json</a>.</Body>
      </div>
    )
  }
  if (!d || fy === null || !year || !lv || !tierData) {
    return <div className="mx-auto max-w-4xl px-5 py-12 text-[15px]"
      style={{ color: 'var(--text-muted)' }}>Loading the fee schedule…</div>
  }

  const lx = d.ladder_exhibit
  const stated = d.caps.filter(c => c.unit_status === 'stated')
  const unstated = d.caps.filter(c => c.unit_status !== 'stated')
  const cap27 = d.caps.find(c => c.fy === lx.fy)!
  const last = lx.rows[lx.rows.length - 1]
  const capNow = year.cap

  return (
    <div className="mx-auto max-w-4xl px-5 py-10">
      <h1 className="text-3xl sm:text-4xl font-bold tracking-tight">
        What a family actually pays
      </h1>
      <p className="text-[15px] leading-relaxed max-w-2xl mt-3"
        style={{ color: 'var(--text-secondary)' }}>
        Every school fee a Lunenburg household can be charged, priced for one, two, three
        and four children — and the three places where the published record runs out.
      </p>

      {/* ---------------------------------------------------------------- 1. conclusions */}
      <H2 id="what-this-establishes">What this establishes</H2>

      <div className="grid gap-3 mt-5 sm:grid-cols-2">
        <Insight tone={SEASON} headline={
          <>The family cap states no period, and the two readings differ by{' '}
            {money(d.published_spread)} for a family of{' '}
            {d.published_spread_at.children} with {d.published_spread_at.sports} sports
            each.</>}>
          The cap it replaced said which: the {d.faq.title} prints{' '}
          <em>“{stated[0].source_ref}”</em>. The {fyLabel(unstated[0].fy)} one was set by
          roll call with the words <em>“{unstated[0].source_ref}”</em> and nothing else.
          Read per season and read per year, {money(unstated[0].amount)} is a different
          bill for the same family.
        </Insight>

        <Insight tone={YEAR} headline={
          <>{last.children} children, one sport each, in a single season come to{' '}
            {money(last.cumulative_by_rule)} — still under the{' '}
            {money(lx.cap)} cap.</>}>
          On the more expensive of the two ways of carrying the ladder past the third
          child it is {money(last.cumulative_flat)}, and that is under the cap too. So a
          per-season cap is unreachable by family size alone. <strong>That makes a
          per-season reading implausible — an inference, not a measurement.</strong>{' '}
          Nothing published states the period.
        </Insight>

        <Insight tone={SEASON} headline={
          <>{d.unpriced_portal} fees the district sells have no published amount.</>}>
          They are on the district’s own payment portal by name — and the portal renders
          in JavaScript and serves no amounts. So every total on this page is a{' '}
          <strong>floor</strong>, drawn with a band above it that has no top. A family
          cannot compute what a school year costs, and neither can the town while it
          argues about who should pay.
        </Insight>

        <Insight tone={YEAR} headline={
          <>The rates are one rule, and it stops being published at the third child.</>}>
          {money(lx.rows[0].rate_by_rule)} × {lx.ratio} is exactly{' '}
          {money(lx.rows[1].rate_by_rule)}, and × {lx.ratio} again is exactly{' '}
          {money(lx.rows[2].rate_by_rule)} — the {lx.ratio_pct}% sibling discount the
          committee voted, compounding. A fourth child follows at{' '}
          {money(d.fourth_child.by_rule)} <em>if</em> it keeps compounding. No document
          says it does, and none states a fourth-child rate.
        </Insight>
      </div>

      <NotShown>
        <p>
          <strong>Nothing here says any family is over- or under-paying.</strong> It states
          what is published, what is not, and what a scenario comes to under each reading.
          Whether that is too much or too little is the argument, and this page is the
          arithmetic under it.
        </p>
        <p className="mt-2.5">
          <strong>It is also not a measure of what the schools cost.</strong> A fee is
          money in; the budget lines it offsets are already net of it. What a family pays
          and what the town is spared are different questions and only the first is
          answered here.
        </p>
        <p className="mt-2.5">
          <strong>And no growth rate is computed across the caps.</strong>{' '}
          {money(stated[0].amount)} and {money(unstated[0].amount)} are not like for like:
          one states a period, the other states none, and one is recorded against{' '}
          {stated[0].level} and the other against {unstated[0].level}. Dividing them would
          produce a rise that is partly a rise and partly a change of unit.
        </p>
      </NotShown>

      {/* -------------------------------------------------- 2. the exhibit and the model */}
      <H2 id="the-cap">The cap, and the arithmetic that argues about its period</H2>
      <Body>
        One sport each, one season, adding a child at a time — against the{' '}
        {fyLabel(lx.fy)} cap. Columns past the third child are hatched because no document
        publishes a rate for them; the hatched extension is the difference between the two
        ways of carrying the ladder on, and the conclusion holds on either.
      </Body>

      <LadderExhibit rows={lx.rows} cap={lx.cap} />

      <TableTwin
        caption={`${fyLabel(lx.fy)} high school athletics, one sport each, one season`}
        head={['Children', 'This child pays', 'Running total',
          'If the discount stops', 'Under the cap?']}
        rows={lx.rows.map(r => [
          `${r.children}${r.published ? '' : ' *'}`,
          money(r.rate_by_rule),
          money(r.cumulative_by_rule),
          money(r.cumulative_flat),
          r.under_cap ? `yes — ${money(r.headroom_flat)} to spare` : 'no',
        ])}
        note={<>
          * not published. {lx.rule}. Two ways of carrying it past the third child are
          shown: {lx.assumption_rule} (the running total), and {lx.assumption_flat} (the
          fourth column). Neither is published; the page reports both because the
          conclusion has to survive the choice between them.
        </>} />

      <div className="card p-5 mt-6 max-w-2xl" style={{ borderLeft: `4px solid ${YEAR}` }}>
        <p className="text-[11px] font-semibold uppercase tracking-widest mb-1.5"
          style={{ color: 'var(--text-muted)' }}>
          Measured, and then inferred — the line between them
        </p>
        <p className="text-[14px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
          <strong>Measured:</strong> under a per-season reading the cap does not bind in
          any scenario on this page{d.season_cap_binds_anywhere ? '' : ' at all'}. Under a
          per-year reading it binds at {d.published_spread_at.children} children with{' '}
          {d.published_spread_at.sports} sports each, and the same family pays{' '}
          {money(d.published_spread)} less.
        </p>
        <p className="text-[14px] leading-relaxed mt-2.5"
          style={{ color: 'var(--text-secondary)' }}>
          <strong>Inferred, and this is the part nothing tests:</strong> a cap no ordinary
          family can reach is not doing what a cap does, so the arithmetic makes the
          per-season reading hard to believe. That is an argument, not a finding.{' '}
          <strong>No document in this archive states the period</strong>, and the one that
          would is the district’s fee schedule as published to families.
        </p>
      </div>

      <H3>What each cap’s own source says about its period</H3>
      <TableTwin
        head={['Year', 'Cap', 'Applies to', 'Period', 'How we know', 'The words']}
        rows={d.caps.map(c => [
          `${fyLabel(c.fy)} (${c.school_year})`,
          money(c.amount),
          c.level,
          c.unit,
          c.unit_status,
          c.source_ref ?? '— source not held —',
        ])}
        note={<>
          The {fyLabel(stated[0].fy)} cap equals its own ladder exactly:{' '}
          {stated[0].ladder.map(money).join(' + ')} = {money(stated[0].ladder_sum!)}, the
          printed cap. A cap set at the sum of the ladder binds the moment a fourth child
          appears. The {fyLabel(cap27.fy)} cap sits {money(cap27.headroom!)} above the same
          sum, so whatever it is doing, it is not that.
        </>} />

      {/* ------------------------------------------------------------ 3. the calculator */}
      <H2 id="your-family">Your family, both readings</H2>
      <Body>
        Set the household. Every figure is looked up from the schedule, and anything the
        archive does not publish is shown as unknown rather than estimated.
      </Body>

      <div className="grid gap-3 mt-6 sm:grid-cols-2">
        <Choice label="Year" value={fy} setValue={setFy}
          options={d.years.map(y => ({ value: y.fy, label: fyLabel(y.fy) }))}
          note={`${fyLabel(d.years[0].fy)} is the year now running and the only account of
                 it is an email to families this archive does not hold.
                 ${fyLabel(d.years[1].fy)} is the last year published in full.`} />

        <Choice label="School" value={level!} setValue={setLevel}
          options={[
            { value: 'HS', label: 'High school' },
            { value: 'MS', label: 'Middle school' },
          ]}
          note={lv.ladder.kind === 'not published'
            ? `No ${level === 'MS' ? 'middle school' : 'high school'} rate is published for
               ${fyLabel(fy)}. Everything below is unknown.`
            : `A high school student may play only one sport a season — the ${d.faq.title}
               says so — which is what makes a season fee also a per-sport fee there. It
               states no such rule for middle school.`} />

        <Choice label="Children" value={children!} setValue={setChildren}
          options={Array.from({ length: d.max_children }, (_, i) => ({
            value: i + 1, label: String(i + 1),
          }))}
          note="The question as it was asked: families of one, two, three and four." />

        <Choice label="Sports each, over the year" value={sports!} setValue={setSports}
          options={Array.from({ length: d.max_sports + 1 }, (_, i) => ({
            value: i, label: String(i),
          }))}
          note={`There are ${d.seasons} seasons, and a child plays at most one sport in
                 each.`} />

        <Choice label="What the family pays" value={tier!} setValue={setTier}
          options={d.tiers.map(t => ({
            value: t,
            label: t === 'full' ? 'Full fee' : t === 'reduced' ? 'Reduced fee' : 'Waived',
            disabled: !lv.tiers[t].available,
            why: lv.tiers[t].available ? undefined
              : `No ${t} rate is published for ${fyLabel(fy)} ${level}`,
          }))}
          note={tier === 'full'
            ? 'The ladder, first child down to third.'
            : tier === 'reduced'
              ? `A flat ${money(tierData.flat ?? 0)} a child a season — no sibling ladder
                 is published for it. This is the half of the argument that usually goes
                 unsaid: the same three athletes cost this family far less.`
              : 'Waived to zero. ' + (lv.tiers.waived.source ?? '')} />

        <Choice label="Bus" value={bus ? 1 : 0} setValue={v => setBus(v === 1)}
          options={[{ value: 1, label: 'Takes the bus' }, { value: 0, label: 'Does not' }]}
          note="Charged per family for the year, not per child — and the town said so in
                those words when it set it." />
      </div>

      {cell && cell.computable ? (
        <BothReadings
          perSeason={cell.per_season} perYear={cell.per_year}
          bus={bus ? busAmount : 0}
          unpricedCount={d.unpriced_portal}
          capBinds={capNow ? Math.max(...cell.seasons) > capNow.amount : false} />
      ) : (
        <div className="card p-5 mt-5" style={{ borderLeft: `4px solid ${SEASON}` }}>
          <p className="text-[15px] font-bold">This family cannot be priced.</p>
          <p className="text-[14px] leading-relaxed mt-2"
            style={{ color: 'var(--text-secondary)' }}>
            {lv.ladder.kind === 'not published'
              ? `No ${level === 'MS' ? 'middle school' : 'high school'} rate is published
                 for ${fyLabel(fy)}.`
              : `The published ladder names ${lv.ladder.stops_after} children and stops,
                 and nothing states a rate beyond that.`}{' '}
            That is the finding, not a failure of the page — and it is registered below.
          </p>
        </div>
      )}

      {cell && cell.computable && !cell.fully_published && (
        <p className="text-[12.5px] mt-3 max-w-2xl" style={{ color: SEASON }}>
          One or more rates in this scenario are produced by the rule the published rates
          follow rather than stated in a document. Set the family to{' '}
          {lv.ladder.stops_after} children or fewer for a total in which every rate is
          published.
        </p>
      )}

      <H3>The same thing as a table, every family size and every number of sports</H3>
      <TableTwin
        caption={`${fyLabel(fy)} ${level === 'HS' ? 'high school' : 'middle school'},`
          + ` ${tier} fee — athletics only, before the bus`}
        head={['Children', 'Sports each', 'Before any cap', 'Cap read per season',
          'Cap read per year', 'Difference']}
        rows={tierData.grid.filter(g => g.sports > 0).map(g => [
          `${g.children}${g.fully_published ? '' : ' *'}`,
          g.sports,
          g.computable ? money(g.uncapped) : '—',
          g.computable ? money(g.per_season) : '—',
          g.computable ? money(g.per_year) : '—',
          g.computable ? (g.spread > 0 ? money(g.spread) : '—') : 'not published',
        ])}
        note={<>
          * includes at least one rate produced by the rule rather than published. Rows
          reading “not published” are the family sizes this archive cannot price at all.
          The widest difference between the two readings where every rate is published is{' '}
          {money(d.published_spread)}.
        </>} />

      <NotShown>
        <p>
          <strong>A season is not a sport, and the town’s own word is “per student”.</strong>{' '}
          No document here states these fees as a charge per sport. The {d.faq.title}
          {' '}heads them <em>“{d.faq.quotes[2]}”</em>, and per sport and per season coincide
          at the high school only because the same document says{' '}
          <em>“{d.faq.quotes[0]}”</em>. It states no such rule for middle school, so a
          middle school family playing two sports in one season is priced here on an
          assumption.
        </p>
        <p className="mt-2.5">
          <strong>Nor does it show what any family actually paid.</strong> These are
          schedules. Nothing published counts how many children play, in which tier, or
          how many families reached the cap under either reading.
        </p>
      </NotShown>

      {/* --------------------------------------------------------- 4. what has no price */}
      <H2 id="no-price">The fees with no published amount</H2>
      <Body>
        Each of these is established as existing and not as costing anything. They are the
        band above every total on this page, and the reason it has no top.
      </Body>
      <TableTwin
        head={['Fee', 'Where it appears', 'State']}
        rows={d.unpriced.map(u => [u.item, u.source.split('—')[0].trim(), u.status])} />

      {/* -------------------------------------------------------------- 5. what was said */}
      <H2 id="said">What was said in the room</H2>
      <Body>
        Found by searching the meeting archive, and each quote checked against the file it
        is attributed to on every build.
      </Body>
      <div className="grid gap-3 mt-5">
        {d.said.map(s => (
          <div key={s.key} className="card p-5">
            <p className="text-[15px] leading-relaxed italic">“{s.quote}”</p>
            <p className="text-[12.5px] mt-2" style={{ color: 'var(--text-muted)' }}>
              {s.who} · {s.board}, {s.date} ·{' '}
              <a className="underline" href={abs(s.cite)}>the text we hold</a> ·{' '}
              <a className="underline" href={s.town} rel="noreferrer">the town’s copy</a>
            </p>
            <p className="text-[13.5px] leading-relaxed mt-2.5"
              style={{ color: 'var(--text-secondary)' }}>{s.why}</p>
          </div>
        ))}
      </div>

      {/* ------------------------------------------------------------------- 6. the raw */}
      <H2 id="raw">Every rate, with its source and what its period rests on</H2>
      <TableTwin
        head={['Year', 'Level', 'Fee', 'Amount', 'Period', 'How we know', 'Checked']}
        rows={d.schedule.map(r => [
          r.school_year, r.level, r.item.replace(/_/g, ' '), money(r.amount),
          r.unit, r.unit_status, r.verified,
        ])}
        note={<>
          The period column used to be one constant string on every row — including the
          family cap, where “per student per sport” means nothing. It is now read off each
          source: <strong>stated</strong> where the document names the period,{' '}
          <strong>structural</strong> where the document’s own construction fixes it, and{' '}
          <strong>not established</strong> where nothing does.{' '}
          <a className="underline" href={abs('/data/athletic-fee-schedule.csv')}>
            the schedule as a CSV</a>.
        </>} />

      <H3>The bus, {fyLabel(fy)}</H3>
      <TableTwin
        head={['Tier', 'Amount', 'State', 'The words']}
        rows={Object.entries(year.bus).map(([k, b]) => [
          k, b.amount === null ? 'not published' : money(b.amount), b.status,
          b.source_ref ?? '—',
        ])}
        note="Per family for the year, not per child." />

      {/* ---------------------------------------------------------------- 7. the gaps */}
      <H2 id="gaps">What this page could not answer</H2>
      <Body>
        Each one is a row in the gap register, so it appears on{' '}
        <a className="underline" href={abs('/what-we-cannot-answer')}>
          what we cannot answer</a> and in{' '}
        <a className="underline" href={abs('/api/money_gaps.json')}>the API</a> as well as
        here. Every one closes on a document somebody could send.
      </Body>
      <div className="grid gap-3 mt-5">
        {d.gaps.map(g => (
          <div key={g.what} className="card p-5">
            <div className="flex items-baseline justify-between gap-3 flex-wrap">
              <p className="text-[15px] font-bold">{g.what}</p>
              <Footing status={g.side} />
            </div>
            <p className="text-[13.5px] leading-relaxed mt-2"
              style={{ color: 'var(--text-secondary)' }}>{g.why}</p>
            {g.closes && (
              <p className="text-[13px] leading-relaxed mt-2.5">
                <span className="font-semibold">Closes with: </span>
                <span style={{ color: 'var(--text-secondary)' }}>{g.closes}</span>
              </p>
            )}
          </div>
        ))}
      </div>

      {/* ------------------------------------------------------------------ 8. related */}
      <H2 id="related">Read next</H2>
      <div className="grid gap-2.5 mt-5">
        {d.related.map(r => (
          <a key={r.id} href={abs(r.url)}
            className="card block px-4 py-4 min-h-[44px] transition-opacity hover:opacity-90">
            <p className="text-[14.5px] font-bold">{r.title}</p>
            <p className="text-[13px] leading-snug mt-1"
              style={{ color: 'var(--text-secondary)' }}>{r.why}</p>
          </a>
        ))}
      </div>

      <p className="text-[12px] mt-12" style={{ color: 'var(--text-muted)' }}>
        Generated by <code>{d.generated_by}</code> from {d.source}. Published as{' '}
        <a className="underline" href={abs('/data/what-families-pay.json')}>
          /data/what-families-pay.json</a>.
      </p>
    </div>
  )
}

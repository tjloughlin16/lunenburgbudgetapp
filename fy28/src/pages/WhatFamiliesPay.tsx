import type { Tab } from '../routes'
import { useEffect, useMemo, useState } from 'react'
import { abs } from '../lib/abs'
import { TableTwin } from '../components/StateAidCharts'
import {
  BothReadings, Choice, HouseholdBill, LadderExhibit, SEASON, YEAR, money,
} from '../components/FamilyFeeCharts'
import type { Bill, BillRow, ChargeDef } from '../components/FamilyFeeCharts'
import {
  Conclusions,
  Body, H2, H3, Insight, NotShown,
  ReportShell,
} from '../components/report'
import type { Conclusion } from '../components/report'

const TAB: Tab = 'families'
const DATA = '/data/what-families-pay.json'
const TITLE = 'What a family pays'

/** What a Lunenburg family actually pays for school in a year.
 *
 *  WHY THIS PAGE EXISTS. Residents say two things at meetings. One: parents should pay
 *  more, because they are the ones using the schools. Two: parents already pay a great
 *  deal. Both are claims about a number, and the number is what a HOUSEHOLD hands over in
 *  a year to have children in the schools -- not what any one fee is.
 *
 *  THE TABLE IS THE PAGE (rule 7a). A reader sets their own household at the top and reads
 *  a yearly figure off it. Everything explaining how to read it -- the bands, the cap, the
 *  ladder, the provenance -- comes after, because a reader arrives for the figure.
 *
 *  THIS PAGE USED TO BE ABOUT ATHLETICS, and that was the defect. Athletics is the fee with
 *  a schedule, a roll-call vote and four years of minutes behind it, so it filled the page
 *  -- which is a fact about what the district PUBLISHES, not about what a family PAYS. It
 *  is one row now, and it keeps its detail in a drill-in below.
 *
 *  AND THE PAGE NO LONGER LEADS ON THE CAP'S AMBIGUITY. That the $1,500 family cap states
 *  no period is true, evidenced and registered -- and it is a defect in a document rather
 *  than something a household needs in order to plan. It is a footnote on the athletics
 *  row, beside the figure it qualifies (rule 7a again), and a row in `money_gaps`. Rule 8:
 *  findings arrive as what this means for planning, never as what anybody got wrong.
 *
 *  FOUR BANDS, AND THE TOTAL IS A FLOOR. `priced`, `carried` (charged, last set in public
 *  in an earlier year), `unpriced` (charged, no amount published anywhere) and `no charge`.
 *  Nothing estimates an unpriced row -- rule 7, the amounts are not in the archive, so a
 *  guess would be a proxy standing in for the thing. They are a COUNT with a named remedy
 *  each, which is the argument for going and getting them.
 *
 *  RULE 8 CUTS BOTH WAYS HERE, and the meals row is why it is in the table at full size:
 *  the record shows the state and the district taking a real cost OFF a household, and a
 *  page that only found fees going up would not be being believed, it would be being used.
 *
 *  RULE 11, POINTED AT HOUSEHOLDS. Every figure is money a family hands over. It is not
 *  what the thing costs, and it does not reduce the appropriation one-for-one -- several of
 *  these budget lines are recorded already net of the fee.
 *
 *  RULE 2. Not one figure is typed into this file. Every amount, label, note and request
 *  arrives from /data/what-families-pay.json, and each household is LOOKED UP from a bill
 *  the generator priced rather than computed here -- so the page and the verifier cannot
 *  disagree about arithmetic.
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
  conclusions: Conclusion[]
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
  tier_contrast: {
    fy: number; level: string; children: number; sports: number
    full: number; reduced: number; waived: number; flat: number | null
    ratio: number | null; full_published: boolean
    source: string | null; source_ref: string | null
  }
  household: {
    default: { fy: number; level: string; children: number; sports: number; tier: string
      bus: boolean; activities: boolean; parking: boolean }
    options: { fy: number[]; level: string[]; children: number[]; sports: number[]
      tier: string[] }
    bands: string[]
    band_meaning: Record<string, string>
    standing: BillRow[]
    charge_defs: Record<string, ChargeDef>
    bills: Record<string, Bill>
    lead: Bill & { key: string }
    unpriced_named: number
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
  search_note: string
  coverage: { board: string; since: string; scope: number; searched: number
    unsearchable: number; not_held: number; pct: number }
  gaps: { side: string; what: string; why: string; closes: string | null }[]
  related: { id: string; title: string; why: string; words: number; updated: string
    url: string; pdf: string | null }[]
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
  // A string rather than a flag, so the shell can print WHY the fetch failed --
  // every other report on the site does, and the shell states it in one voice.
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    // RELATIVE, and abs() only on hrefs. `abs` writes the site name in front of a file
    // path so a program can follow the link; using it on a FETCH points the page at
    // production, which 404s for any file not deployed yet and renders the error state
    // into the prerender. Same-origin here, like every other page.
    fetch('/data/what-families-pay.json')
      .then(r => (r.ok ? r.json() : Promise.reject(new Error(String(r.status)))))
      .then(setD).catch(e => setErr(String(e)))
  }, [])

  const [fy, setFy] = useState<number | null>(null)
  const [level, setLevel] = useState<string | null>(null)
  const [tier, setTier] = useState<string | null>(null)
  const [children, setChildren] = useState<number | null>(null)
  const [sports, setSports] = useState<number | null>(null)
  const [bus, setBus] = useState<boolean | null>(null)
  const [activities, setActivities] = useState<boolean | null>(null)
  const [parking, setParking] = useState<boolean | null>(null)

  useEffect(() => {
    if (!d) return
    setFy(v => v ?? d.default.fy)
    setLevel(v => v ?? d.default.level)
    setTier(v => v ?? d.default.tier)
    setChildren(v => v ?? d.default.children)
    setSports(v => v ?? d.default.sports)
    setBus(v => v ?? d.default.bus)
    setActivities(v => v ?? d.household.default.activities)
    setParking(v => v ?? d.household.default.parking)
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

  // THE BILL IS LOOKED UP, NEVER COMPUTED (rule 2). The generator priced every household
  // a reader can describe and the key is built the same way in both places, so the page
  // and the verifier cannot disagree about arithmetic.
  const bill = useMemo(() => {
    if (!d || fy === null || level === null || children === null || sports === null
      || tier === null || bus === null || activities === null || parking === null) {
      return null
    }
    const k = `${fy}|${level}|${children}|${sports}|${tier}|${bus ? 1 : 0}`
      + `|${activities ? 1 : 0}|${parking ? 1 : 0}`
    return d.household.bills[k] ?? null
  }, [d, fy, level, children, sports, tier, bus, activities, parking])

  if (err) return <ReportShell tab={TAB} title={TITLE} dataUrl={DATA} err={err} />
  if (!d || fy === null || !year || !lv || !tierData) return <ReportShell tab={TAB} title={TITLE} dataUrl={DATA} loading />

  // WHAT A SECOND CHILD ADDS, taken from two priced households rather than from
  // arithmetic in this file. `one` and `two` differ in exactly one input, so the
  // difference on each row is what that one child costs on that fee.
  const hb = d.household.bills
  const bk = (n: number, on: boolean) =>
    `${d.household.default.fy}|HS|${n}|1|full|${on ? 1 : 0}|0|0`
  const amt = (k: string, id: string) =>
    hb[k]?.rows.find(r => r.id.split(':')[0] === id)?.amount ?? 0
  const secondChild = {
    sport: (amt(bk(2, false), 'athletics') ?? 0) - (amt(bk(1, false), 'athletics') ?? 0),
    bus: (amt(bk(2, true), 'bus') ?? 0) - (amt(bk(1, true), 'bus') ?? 0),
  }

  const lx = d.ladder_exhibit
  const stated = d.caps.filter(c => c.unit_status === 'stated')
  const unstated = d.caps.filter(c => c.unit_status !== 'stated')
  const cap27 = d.caps.find(c => c.fy === lx.fy)!
  const capNow = year.cap
  const ct = d.tier_contrast

  return (
    <ReportShell tab={TAB} dataUrl={DATA}
      title={<>
        What a family actually pays
      </>}
      standfirst={<>
        Set your household and read the year off the table: every charge a Lunenburg family
        meets to have children in school, over and above what it pays in property tax.
      </>}
    >


      {/* ------------------------------------------------ 1. CONCLUSIONS (rule 7b) */}
      {/* NOT WRITTEN HERE. Every word and every figure comes out of this report's own
          payload, computed by the generator that computed the figures -- see
          scripts/conclusions.py. The same rows appear on /what-it-all-adds-up-to, read
          from the same file, so the two cannot drift apart. */}
      <H2 id="conclusions">If you read nothing else</H2>
      <Conclusions rows={d.conclusions} />

      {/* ============================================================ 1. THE TABLE.
          Rule 7a: the page is called what a family pays, so the bill is the page. The
          controls sit directly above it because setting your own household IS how a
          reader gets their number, and every word explaining the bands comes after. */}
      <H2 id="the-bill">Set your household, and read the year off the table</H2>

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
                those words when it set it. Grades 7-12 are all charged; K-6 only inside
                two miles." />

        <Choice label="Clubs and student activities"
          value={activities ? 1 : 0} setValue={v => setActivities(v === 1)}
          options={[{ value: 1, label: 'At least one' }, { value: 0, label: 'None' }]}
          note="The School Committee voted this fee to its current amount on 7 May 2025.
                The motion names an amount and no period, so whether it is charged once a
                year, once a term or once per activity is not established." />

        <Choice label="Drives to the high school"
          value={parking ? 1 : 0} setValue={v => setParking(v === 1)}
          options={[{ value: 1, label: 'Yes' }, { value: 0, label: 'No' }]}
          note="The figure is a resident stating in public comment what they paid, not a
                schedule. The district's payment portal sells a parking permit and prints
                no amount." />
      </div>


      <div className="mt-6">
        {bill ? (
          <HouseholdBill
            bill={bill}
            standing={d.household.standing}
            defs={d.household.charge_defs}
            bandMeaning={d.household.band_meaning}
            summary={<>
              {children} child{children === 1 ? '' : 'ren'} at the{' '}
              {level === 'HS' ? 'high school' : 'middle school'} in {fyLabel(fy)}
              {sports! > 0
                ? <>, {sports} season{sports === 1 ? '' : 's'} of sport each</>
                : <>, playing no sport</>}
              {bus ? ', riding the bus' : ', not riding the bus'}
              {activities ? ', in at least one club' : ''}
              {parking && level === 'HS' ? ', one of them driving to school' : ''}
              {tier !== 'full' ? ` — at the ${tier} fee` : ''}.{' '}
              {money(bill.floor)} of that is an amount a document states for{' '}
              {fyLabel(fy)}. It is a floor: {d.household.unpriced_named} further charges
              this family can meet have no published amount at all, and they are listed
              under the total rather than guessed at.
            </>} />
        ) : (
          <div className="card p-5" style={{ borderLeft: `4px solid ${SEASON}` }}>
            <p className="text-[15px] font-bold">This household cannot be priced.</p>
            <p className="text-[14px] leading-relaxed mt-2"
              style={{ color: 'var(--text-secondary)' }}>
              No rate is published for this combination of year, school and fee tier. That
              is the finding rather than a failure of the page, and it is registered below.
            </p>
          </div>
        )}
      </div>

      {/* ------------------------------------------------ 2. what it means */}
      <H2 id="what-this-establishes">What this establishes</H2>

      <Body>
        What the table says, in sentences a reader could repeat at a meeting. Every figure
        is the model’s, looked up rather than typed.
      </Body>

      <div className="grid gap-3 mt-5 sm:grid-cols-2">
        <Insight tone={YEAR} headline={
          <>Two children at the high school, one sport each, riding the bus and in a club
            pay {money(d.household.lead.floor_carried)} for the year.</>}>
          {money(d.household.lead.floor)} of that is an amount a document states for{' '}
          {fyLabel(d.household.default.fy)}; the rest is a fee that was voted in public and
          has not been restated since. That is the answer to the question this page is
          named after, and it is a floor rather than a bill — see the row below it.
        </Insight>

        <Insight tone={SEASON} headline={
          <>A second child costs {money(secondChild.sport)} more in athletics and{' '}
            {money(secondChild.bus)} more on the bus.</>}>
          The two fees are built differently and a household feels the difference. The bus
          is charged <strong>per family</strong> for the year however many children ride,
          so the second child adds {money(secondChild.bus)}; athletics is charged per child
          per season, so the second child adds {money(secondChild.sport)} even after the
          sibling discount. Which fee a town raises decides which families pay for it.
        </Insight>

        <Insight tone={SEASON} headline={
          <>{d.household.unpriced_named} charges a Lunenburg family can meet have no
            published amount anywhere.</>}>
          Six of them are products the district’s own payment portal sells by name —
          preschool, extended day, field trips, device repair, afterschool activities, a
          parking permit — and the portal renders in JavaScript and serves no amounts. So
          the total above is a floor with an open band over it. Each one is listed with the
          single document that would price it, because a gap with a named remedy is a
          records request and a gap without one is a complaint.
        </Insight>

        <Insight tone={'var(--text-muted)'} headline={
          <>School meals cost a family nothing, and that is a real reduction in the
            household bill.</>}>
          Massachusetts funds universal free school meals and the district takes the
          programme — its own minutes record it choosing between the two schemes that
          deliver them, noting that <em>“Our students would not see any difference”</em>. A
          family with two children eating at school every day is not billed for it. What
          sits outside the programme — à la carte items, snacks, second meals — is charged,
          and no price list for that is published.
        </Insight>
      </div>

      <div className="card p-5 mt-3" style={{ borderTop: `3px solid ${YEAR}` }}>
        <p className="text-[16px] font-bold leading-snug">
          The same {ct.children} athletes cost one family {money(ct.full)} a year and
          another {money(ct.reduced)}. Both families are “parents”.
        </p>
        <div className="text-[13.5px] leading-relaxed mt-2"
          style={{ color: 'var(--text-secondary)' }}>
          <p>
            {fyLabel(ct.fy)} high school, {ct.children} children with {ct.sports} sport
            each — the full ladder against the reduced fee a qualifying family pays,{' '}
            {money(ct.flat ?? 0)} a child a season. A family whose fee is waived pays{' '}
            {money(ct.waived)}. That is a factor of {ct.ratio} between two households in
            the same school, and the argument this page answers is usually made without
            either figure in it.
          </p>
          <p className="mt-2.5">
            <strong>It can only be shown for {fyLabel(ct.fy)}.</strong>{' '}
            {fyLabel(d.years[0].fy)} publishes no reduced rate, no waived rate and no
            middle school rate — so for the year now running, the cheaper half of this
            comparison cannot be computed at all. That is registered below.
          </p>
        </div>
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
      <H3>The sibling ladder, and where it stops being published</H3>
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
      <H2 id="athletics-detail">Athletics, in detail — the one fee with a schedule</H2>
      <Body>
        Athletics is one row of the table above and the only charge here with a published
        schedule, a recorded vote and a sibling ladder behind it. That is a fact about what
        the district publishes rather than about what a household pays, and it is why this
        section is longer than the others — not because it is the largest thing a family
        is charged. It reprices the household you set above, both ways the family cap can
        be read.
      </Body>

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
          One or more rates in this scenario are not stated in any document.{' '}
          {lv.ladder.kind === 'percentage'
            ? 'They follow from the sibling discount the School Committee voted, which is '
              + 'published as a rule even though the resulting rate is not written down.'
            : 'They follow from the ratio the published rates happen to follow, which is '
              + 'an inference: nothing says the ladder continues past where it stops.'}{' '}
          Set the family to {lv.ladder.stops_after} children or fewer for a total in which
          every rate is published outright.
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
          * includes at least one rate not stated in any document.{' '}
          {lv.ladder.kind === 'percentage'
            ? `In ${fyLabel(fy)} it is produced by a rule that WAS voted — the
               ${100 - lv.ladder.ratio! * 100}% sibling discount — so the rate follows from
               something published even though no document names it.`
            : `In ${fyLabel(fy)} it is produced by the ratio the three published rates
               happen to follow. Nothing says the ladder continues, so that is an
               inference and it is marked as one.`}{' '}
          Rows reading “not published” are the family sizes this archive cannot price at
          all. The widest difference between the two readings where every rate is
          published is {money(d.published_spread)}.
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

      {/* ------------------------------------------------ what would complete the number */}
      <H2 id="to-complete">What would make this number complete</H2>
      <Body>
        The total above is a floor because these charges are real and unpriced. This is the
        list of things to ask for, in the form the answer has to take — a schedule, a rate,
        a period. It is not a list of what anybody failed to publish; it is what would turn
        a floor into a bill, and most of it is one document each.
      </Body>
      <div className="grid gap-2.5 mt-5">
        {d.household.standing.filter(r => r.band === 'unpriced').map(r => {
          const def = d.household.charge_defs[r.id]
          return (
            <div key={r.id} className="card p-4">
              <p className="text-[14px] font-bold">{def.label}</p>
              <p className="text-[12.5px] leading-snug mt-1"
                style={{ color: 'var(--text-muted)' }}>{def.basis}</p>
              <p className="text-[13px] leading-relaxed mt-2">
                <span className="font-semibold">Ask for: </span>
                <span style={{ color: 'var(--text-secondary)' }}>{def.request}</span>
              </p>
            </div>
          )
        })}
      </div>

      <H3>Every rate in the register with no amount attached</H3>
      <Body>
        The same thing as the register holds it, including the rates that are not a
        household bill at all — a contract cost-of-living figure and a facilities hire
        schedule are here because the register is one list.
      </Body>
      <TableTwin
        head={['Fee', 'Where it appears', 'State']}
        rows={d.unpriced.map(u => [u.item, u.source.split('—')[0].trim(), u.status])} />

      {/* -------------------------------------------------------------- 5. what was said */}
      <H2 id="said">What was said in the room</H2>
      <Body>{d.search_note}</Body>
      <p className="text-[13px] leading-relaxed mt-3 max-w-2xl"
        style={{ color: 'var(--text-secondary)' }}>
        <strong>Searched: {d.coverage.searched} of the {d.coverage.scope}{' '}
        {d.coverage.board} documents published since {d.coverage.since}
        {' '}({d.coverage.pct}%).</strong>{' '}
        {d.coverage.unsearchable > 0
          ? `${d.coverage.unsearchable} are held and cannot be read — scans without a text
             layer — and ${d.coverage.not_held} the town lists are not held at all.`
          : d.coverage.not_held > 0
            ? `${d.coverage.not_held} the town lists are not held at all.`
            : 'None is a scan we cannot read, and none the town lists is missing.'}
      </p>
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
    </ReportShell>
  )
}

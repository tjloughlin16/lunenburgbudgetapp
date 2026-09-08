import { useEffect, useMemo, useState } from 'react'
import { abs } from '../lib/abs'
import { usd } from '../model/engine'
import { TableTwin, fy, share } from '../components/StateAidCharts'
import {
  Asymmetry, ChoiceIn, Dial, LOSS, PerGrade, SAVE, Sensitivity,
  type FundYear, type Grade,
} from '../components/LeavingCharts'

/** If students leave — what school choice would cost Lunenburg.
 *
 *  WHY THIS PAGE EXISTS. A member of the Select Board put a scenario to an AI assistant and
 *  sent it to this site: a 40% school choice transfer rate among athletes, who are 45% of
 *  the high school, and what that does to Chapter 70 and to school choice money. It was
 *  sound reasoning on the documents that are easy to find. This page runs the same scenario
 *  against the whole archive and lets the reader move every input.
 *
 *  RULE 8. Not an audit of anybody's arithmetic. The scenario's premise checks out on two
 *  independent tests and the page says so first, before it says anything else. The two
 *  places the fuller data lands differently are presented as what they are — things the
 *  published documents show that a public search would not surface.
 *
 *  SHAPE (rule 7b). Conclusions, then the model and the organised data, then the raw and
 *  the caveats. A reader who stops after the first screen carries away the asymmetry, which
 *  is the finding that survives every setting of every dial.
 *
 *  RULE 3 IS THE DIFFICULTY HERE, not rule 1. Almost nothing on this page is a
 *  measurement of a transfer, because nobody has measured one. So every input is badged
 *  `measured`, `statute` or `assumed`, the assumed ones are dials, and the page never
 *  presents a net figure without the range around it.
 *
 *  RULE 2. Not one figure is typed into this file. The measured ones arrive from
 *  /data/if-students-leave.json; the scenario ones are computed here from those.
 *
 *  NO D1 AT PAGE LOAD. One static file. */

type Basis = [string, string]

type Payload = {
  generated_by: string
  source: string
  enrolment: {
    fy: number; page: string; document: string
    headings: string[]; headings_raw: string
    status: string; status_means: string; checks: string[]
    hs_resident: number; hs_choice_in: number; hs_total: number
    district_resident: number; district_choice_in: number; district_total: number
    grades: { grade: string; resident: number; choice_in: number; total: number }[]
    schools: { school: string; resident: number; choice_in: number; total: number }[]
    choice_in_outside_hs: number
  }
  premise: {
    fy: number; hs_participations: number
    seasons: { season: string; participations: number }[]
    biggest_season: string; biggest_season_participations: number
    implied_athletes: number; implied_athletes_exact: number; per_athlete: number
    biggest_season_share: number; participation_share: number
    verdict: string; verdict_note: string
  }
  formula: {
    source: string; sheet: string; row: number; fy: number; as_of: string | null
    cells: Record<string, string>; headings: Record<string, string>
    enrollment: number; foundation: number; required: number; aid: number; nss: number
    gap: number; above_gap: number; above_gap_share_of_aid: number
    foundation_per_pupil: number; aid_per_pupil: number
    operating_districts: number; districts_above_gap: number
    districts_above_gap_share: number
    appropriation: number; appropriation_per_pupil: number
    appropriation_denominator: string
  }
  choice_in: {
    fund_series: (FundYear & {
      edition: string; page: string; fund: string; status: string
      forward: number | null; disbursements: number | null; derived: string | null
    })[]
    usable_years: number[]; status: string[]; status_means: string
    arithmetic_checks: number; chain_checks: number
    first: FundYear; last: FundYear; peak: FundYear
    receipts_change: number; receipts_pct: number
    cherry_sheet: { fy: number; amount: number }[]
    cherry_line: number; cherry_source: string
    implied_from_cherry: { fy: number; amount: number; students: number }[]
  }
  scenario: {
    defaults: {
      athlete_share: number; transfer_rate: number; tuition: number
      aid_response: number; avoidable_share: number
    }
    basis: Record<string, Basis>
    hs_resident: number; athletes: number; leavers: number
    per_grade: Grade[]; biggest_grade_loss: number
    foundation_per_pupil: number; appropriation_per_pupil: number
    foundation_reduction: number; tuition_out: number
    aid_loss: number; aid_loss_upper: number
    max_avoidable: number; avoided: number
    net_cost: number; net_cost_upper: number
    break_even_avoidable_share: number; break_even_upper: number
    fee: { fy: number; amount: number; school_year: string | null; source: string | null }
    participations_lost: number; fees_lost: number | null
  }
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

function Insight({ n, headline, children }: {
  n: number; headline: React.ReactNode; children: React.ReactNode
}) {
  return (
    <div className="card p-5">
      <div className="text-[11px] font-semibold uppercase tracking-widest mb-2"
        style={{ color: 'var(--text-muted)' }}>Finding {n}</div>
      <p className="text-[17px] font-bold leading-snug">{headline}</p>
      <div className="text-[14px] leading-relaxed mt-2.5"
        style={{ color: 'var(--text-secondary)' }}>{children}</div>
    </div>
  )
}

function Said({ q }: { q: Payload['said'][number] }) {
  return (
    <div className="card p-4">
      <p className="text-[11px] font-semibold uppercase tracking-widest mb-2"
        style={{ color: 'var(--text-muted)' }}>{q.board} &middot; {q.date}</p>
      <blockquote className="text-[15px] leading-relaxed italic">
        &ldquo;{q.quote}&rdquo;
      </blockquote>
      <p className="text-[12px] mt-1.5" style={{ color: 'var(--text-muted)' }}>{q.who}</p>
      <p className="text-[13.5px] leading-relaxed mt-2.5"
        style={{ color: 'var(--text-secondary)' }}>{q.why}</p>
      <p className="text-[12px] mt-2.5">
        <a className="underline" style={{ color: 'var(--series-cost)' }} href={abs(q.cite)}>
          the minutes, as text
        </a>
        {' · '}
        <a className="underline" style={{ color: 'var(--series-cost)' }} href={abs(q.town)}>
          the town&rsquo;s own copy
        </a>
      </p>
    </div>
  )
}

const pctLabel = (x: number) => `${(x * 100).toFixed(0)}%`

export function IfStudentsLeave() {
  const [d, setD] = useState<Payload | null>(null)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    let live = true
    fetch('/data/if-students-leave.json')
      .then(r => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then(j => { if (live) setD(j) })
      .catch(e => { if (live) setErr(String(e)) })
    return () => { live = false }
  }, [])

  if (err) {
    return (
      <div className="mx-auto max-w-6xl px-5 pt-14 pb-16">
        <h1 className="text-3xl font-bold tracking-tight">If students leave</h1>
        <div className="card p-5 mt-8" style={{ borderLeft: '4px solid var(--status-warning)' }}>
          <p className="text-[15px] font-bold mb-1">The model did not load</p>
          <p className="text-[13.5px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
            {err}. Nothing on this page is typed into it, so with the file missing there is
            nothing to show rather than something stale. The underlying figures are
            published at{' '}
            <a className="underline" style={{ color: 'var(--series-cost)' }}
              href={abs('/data/if-students-leave.json')}>/data/if-students-leave.json</a>.
          </p>
        </div>
      </div>
    )
  }

  if (!d) {
    return (
      <div className="mx-auto max-w-6xl px-5 pt-14 pb-16">
        <h1 className="text-3xl font-bold tracking-tight">If students leave</h1>
        <p className="mt-4 text-[15px]" style={{ color: 'var(--text-muted)' }}>
          Loading the measured inputs&hellip;
        </p>
      </div>
    )
  }
  return <Page d={d} />
}

function Page({ d }: { d: Payload }) {
  const E = d.enrolment
  const P = d.premise
  const F = d.formula
  const C = d.choice_in
  const S = d.scenario
  const D = S.defaults

  const [athleteShare, setAthleteShare] = useState(D.athlete_share)
  const [transferRate, setTransferRate] = useState(D.transfer_rate)
  const [tuition, setTuition] = useState(D.tuition)
  const [aidResponse, setAidResponse] = useState(D.aid_response)
  const [avoidable, setAvoidable] = useState(D.avoidable_share)

  /** The scenario, recomputed. The same arithmetic the generator runs at the defaults —
   *  which is why the generator runs it at all: a reader who moves nothing must see the
   *  scenario exactly as it was put to this site, and the page must not be the only place
   *  that knows how to compute it. */
  const m = useMemo(() => {
    const athletes = Math.round(athleteShare * E.hs_resident)
    const leavers = Math.round(transferRate * athletes)
    const foundationReduction = leavers * F.foundation_per_pupil
    const tuitionOut = leavers * tuition
    const aidLoss = aidResponse * foundationReduction
    const maxAvoidable = leavers * F.appropriation_per_pupil
    const avoided = avoidable * maxAvoidable
    const grades: Grade[] = E.grades.map(g => {
      const n = leavers * g.resident / E.hs_resident
      return {
        grade: g.grade, resident: g.resident, leaving: n,
        remaining: g.resident - n,
        share: g.resident ? n / g.resident : 0,
      }
    })
    const curve = Array.from({ length: 21 }, (_, i) => {
      const a = i / 20
      return {
        avoidable: a,
        hold: tuitionOut - a * maxAvoidable,
        full: tuitionOut + foundationReduction - a * maxAvoidable,
      }
    })
    const breakEven = maxAvoidable > 0 ? (tuitionOut + aidLoss) / maxAvoidable : null
    return {
      athletes, leavers, foundationReduction, tuitionOut, aidLoss, maxAvoidable, avoided,
      grades, curve, breakEven,
      net: tuitionOut + aidLoss - avoided,
      participationsLost: leavers * P.per_athlete,
      feesLost: leavers * P.per_athlete * S.fee.amount,
      perGradeMax: grades.length ? Math.max(...grades.map(g => g.leaving)) : 0,
    }
  }, [athleteShare, transferRate, tuition, aidResponse, avoidable, E, F, P, S])

  const moved = athleteShare !== D.athlete_share || transferRate !== D.transfer_rate
    || tuition !== D.tuition || aidResponse !== D.aid_response
    || avoidable !== D.avoidable_share

  const resetAll = () => {
    setAthleteShare(D.athlete_share); setTransferRate(D.transfer_rate)
    setTuition(D.tuition); setAidResponse(D.aid_response); setAvoidable(D.avoidable_share)
  }

  const fund = C.fund_series

  return (
    <div className="mx-auto max-w-6xl px-5 pt-14 pb-16">
      <p className="text-xs font-semibold uppercase tracking-widest mb-3"
        style={{ color: 'var(--text-muted)' }}>The money</p>
      <h1 className="text-4xl sm:text-5xl font-bold tracking-tight leading-[1.05] max-w-3xl">
        The money leaves in one year. The cost does not.
      </h1>
      <p className="mt-5 text-lg leading-relaxed max-w-2xl"
        style={{ color: 'var(--text-secondary)' }}>
        A scenario put to this site has {share(D.transfer_rate)} of Lunenburg&rsquo;s
        athletes transferring out under school choice &mdash; {S.leavers} students out of
        the {E.hs_resident} the town printed for its high school. Set the dials yourself:
        every input below is a dial because not one of them has been measured.
      </p>

      <div className="mt-10 flex flex-wrap gap-x-12 gap-y-6">
        <Stat value={String(m.leavers)} tone={LOSS}>
          students leaving, at the settings currently on this page &mdash; out of{' '}
          {E.hs_resident} resident high school students the town printed for {fy(E.fy)}
        </Stat>
        <Stat value={usd(m.tuitionOut + m.aidLoss)} tone={LOSS}>
          leaves the town in the first year: sending tuition, plus whatever Chapter 70 does
        </Stat>
        <Stat value={usd(m.avoided)} tone={SAVE}>
          stops being spent &mdash; which is a decision somebody has to take, not a
          consequence of the students going
        </Stat>
        <Stat value={m.perGradeMax.toFixed(0)}>
          students from the largest grade &mdash; the loss spread over four grades, which
          is why nothing closes on its own
        </Stat>
      </div>

      {/* ------------------------------------------------------------ 1. THE CONCLUSIONS */}
      <H2 id="findings">What this page establishes</H2>
      <Body>
        Four claims. The first is about the scenario as it was put; the rest are about what
        the town&rsquo;s and the state&rsquo;s own documents show once you have all of them.
      </Body>

      <div className="grid gap-4 mt-6"
        style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 20rem), 1fr))' }}>
        <Insight n={1} headline={
          <>The scenario&rsquo;s premise holds. {share(D.athlete_share)} of the high school
            playing sports is, if anything, low.</>
        }>
          Two independent tests, neither of which is a headcount. At {share(D.athlete_share)}{' '}
          of {E.hs_resident} the scenario implies {P.implied_athletes} athletes playing{' '}
          {P.per_athlete} sports each &mdash; an ordinary number. And the district&rsquo;s
          largest single season in {fy(P.fy)}, {P.biggest_season}, records{' '}
          {P.biggest_season_participations.toFixed(0)} high school participations on its
          own, which is {share(P.biggest_season_share)} of the student body in one season.
        </Insight>
        <Insight n={2} headline={
          <>Revenue goes at once and in full. Cost goes only where somebody decides it
            goes.</>
        }>
          {m.leavers} students spread across four grades is {m.perGradeMax.toFixed(0)} out
          of the largest one. No section closes, no building is heated less and no contract
          ends because of that, so the town keeps very nearly all of the cost while the
          tuition assessment and any aid change land immediately. This is the finding that
          holds at every setting of every dial on this page.
        </Insight>
        <Insight n={3} headline={
          <>Chapter 70 aid is already {usd(F.above_gap)} above foundation minus the required
            local contribution &mdash; so it is not that subtraction that is setting it.</>
        }>
          DESE&rsquo;s own FY{String(F.fy).slice(2)} row for Lunenburg: a foundation budget
          of {usd(F.foundation)} less a required contribution of {usd(F.required)} leaves{' '}
          {usd(F.gap)}, against aid of {usd(F.aid)}. {F.districts_above_gap} of the{' '}
          {F.operating_districts} operating districts in the same sheet are in the same
          position. Multiplying foundation dollars per pupil by students lost is therefore
          an <strong>upper bound on the foundation effect</strong> rather than a prediction
          of the aid loss &mdash; which is why the aid dial opens at zero and goes to 100%.
        </Insight>
        <Insight n={4} headline={
          <>Even if aid never moves, the town has to stop spending{' '}
            {share(S.break_even_avoidable_share)} of a student&rsquo;s appropriation just to
            break even.</>
        }>
          At {usd(F.appropriation_per_pupil)} per pupil, {m.leavers} students carry{' '}
          {usd(m.maxAvoidable)} of appropriation with them at most. Sending tuition alone
          is {usd(m.tuitionOut)}. If Chapter 70 fell by the whole foundation reduction the
          break-even would be {share(S.break_even_upper)} of per-pupil spending, which is
          more than exists to cut.
        </Insight>
      </div>

      <NotShown>
        <p>
          <strong>Nobody has measured a single Lunenburg student choicing out.</strong> This
          is a scenario, not a forecast, and no part of it is evidence that any student will
          leave or has left. The archive holds thirteen years of school choice money coming
          IN and not one figure for money going out.
        </p>
        <p className="mt-2.5">
          It also does not show that {share(D.athlete_share)} of the high school are
          athletes. A participation is not a child &mdash; {fy(P.fy)}&rsquo;s{' '}
          {P.hs_participations.toFixed(0)} high school participations are{' '}
          {share(P.participation_share)} of the entire student body, which is the proof
          that column is counting something other than people.
        </p>
      </NotShown>

      {/* ------------------------------------------------------------------- 2. THE MODEL */}
      <H2 id="model">The model &mdash; move anything you disagree with</H2>
      <Body>
        The dials open on the scenario as it was put to this site. Every one of them is an
        assumption; the badge on each says what kind, and the measured figures they run
        against are further down with the cell each came out of.
      </Body>

      {moved && (
        <p className="text-[12.5px] mt-3">
          <button onClick={resetAll} className="underline font-semibold"
            style={{ color: 'var(--series-cost)' }}>
            reset every dial to the scenario as it was put
          </button>
        </p>
      )}

      <div className="grid gap-4 mt-6"
        style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 15rem), 1fr))' }}>
        <Dial label="Share of the high school who are athletes"
          value={athleteShare} setValue={setAthleteShare} min={0} max={1} step={0.01}
          format={pctLabel} tone={LOSS} reset={D.athlete_share}
          basis={S.basis.athlete_share[0]} note={S.basis.athlete_share[1]} />
        <Dial label="Share of those athletes who transfer out"
          value={transferRate} setValue={setTransferRate} min={0} max={1} step={0.01}
          format={pctLabel} tone={LOSS} reset={D.transfer_rate}
          basis={S.basis.transfer_rate[0]} note={S.basis.transfer_rate[1]} />
        <Dial label="School choice tuition, per student"
          value={tuition} setValue={setTuition} min={0} max={25000} step={250}
          format={usd} tone={LOSS} reset={D.tuition}
          basis={S.basis.tuition[0]} note={S.basis.tuition[1]} />
        <Dial label="How much of the foundation reduction reaches Chapter 70 aid"
          value={aidResponse} setValue={setAidResponse} min={0} max={1} step={0.01}
          format={pctLabel} tone={LOSS} reset={D.aid_response}
          basis={S.basis.aid_response[0]} note={S.basis.aid_response[1]} />
        <Dial label="Share of a student’s appropriation the district stops spending"
          value={avoidable} setValue={setAvoidable} min={0} max={1} step={0.01}
          format={pctLabel} tone={SAVE} reset={D.avoidable_share}
          basis={S.basis.avoidable_share[0]} note={S.basis.avoidable_share[1]} />
      </div>

      <H3>What it costs the town, at these settings</H3>
      <Asymmetry items={[
        {
          label: <>School choice tuition the town is assessed for {m.leavers} students</>,
          amount: m.tuitionOut, hue: LOSS,
          note: <>{m.leavers} &times; {usd(tuition)}. Assessed rather than appropriated:
            it sits inside the Cherry Sheet assessments the FY2027 Town Meeting booklet
            takes off the top, and no document in this archive breaks it out.</>,
        },
        {
          label: <>Chapter 70 aid, at {share(aidResponse)} of the foundation reduction</>,
          amount: m.aidLoss, hue: LOSS,
          note: <>The foundation budget falls {usd(m.foundationReduction)} &mdash;{' '}
            {m.leavers} &times; {usd(F.foundation_per_pupil)} per pupil, cell{' '}
            <code>{F.cells.foundation}</code> over <code>{F.cells.enrollment}</code>.
            Whether any of that reaches the aid is the open question of this page.</>,
        },
        {
          label: <>Spending the district stops, at {share(avoidable)} of per-pupil
            appropriation</>,
          amount: m.avoided, hue: SAVE,
          note: <>Up to {usd(m.maxAvoidable)} at {usd(F.appropriation_per_pupil)} a pupil.
            {' '}{F.appropriation_denominator}</>,
        },
        {
          label: <><strong>Net cost to the town, per year</strong></>,
          amount: m.net, hue: m.net > 0 ? LOSS : SAVE,
          note: <>The first two, less the third. It repeats every year those students stay
            away, and it compounds if they are followed.</>,
        },
      ]} />

      <H3>The whole range, not one number</H3>
      <Body>
        The single input the answer is most sensitive to is the one nothing measures: how
        much a district stops spending when students go. Both curves below are drawn across
        every value of it, at the two ends of the aid question.
      </Body>
      <Sensitivity curve={m.curve} breakEven={m.breakEven} />
      <TableTwin
        caption="Net cost to the town, by how much spending the district avoids"
        head={['Spending avoided', 'If Chapter 70 does not move', 'If aid falls in full']}
        rows={m.curve.filter((_, i) => i % 4 === 0).map(r => [
          share(r.avoidable), usd(r.hold), usd(r.full)])}
        note={<>Break-even at the current aid setting is{' '}
          {m.breakEven != null && m.breakEven <= 1
            ? <>{share(m.breakEven)} of a student&rsquo;s appropriation</>
            : <>beyond 100% of a student&rsquo;s appropriation &mdash; the town cannot get
              there by not spending</>}.</>} />

      <H3>Where the students would come from</H3>
      <Body>
        The scenario&rsquo;s students are spread across the four grades in proportion to how
        big each grade actually is, printed on the same page as the total. Grade{' '}
        {E.grades[0].grade} is the smallest, so it loses the fewest.
      </Body>
      <PerGrade grades={m.grades} />
      <TableTwin
        caption={`High school, FY${String(E.fy).slice(2)} annual town report, printed page ${E.page}`}
        head={['Grade', 'Lunenburg resident students', 'School choice students', 'Total',
               'Leaving, in this scenario', 'Left in the grade']}
        rows={E.grades.map((g, i) => [
          g.grade, g.resident, g.choice_in, g.total,
          m.grades[i].leaving.toFixed(1), m.grades[i].remaining.toFixed(1)])}
        note={<>The first three columns are the report&rsquo;s own, headed{' '}
          <code>{E.headings_raw}</code>. The last two are this scenario.</>} />

      <Maybe settle={<>the district&rsquo;s own staffing and section plan by grade &mdash;
        the document behind the School Committee&rsquo;s April 2025 discussion of each
        grade, its size and its potential seats &mdash; which would state the class sizes at
        which a section is added or removed.</>}>
        <p>
          At about {m.perGradeMax.toFixed(0)} students out of a grade, one class section per
          grade is the largest reduction the arithmetic alone could support, and it would
          need every one of those students to have been in the same courses. Whether any
          section could actually be removed depends on how they distribute across a
          timetable, and nothing published says.
        </p>
      </Maybe>

      {/* ------------------------------------------------ 3. THE ORGANISED, MEASURED DATA */}
      <H2 id="measured">What is measured, and where each figure comes from</H2>
      <Body>
        Four inputs above are assumptions. These are not &mdash; each is one row or one cell
        of one document, with the coordinate, and each is checked against something else
        before this page will build.
      </Body>

      <H3>The children: the FY{String(E.fy).slice(2)} annual town report, printed page {E.page}</H3>
      <Body>
        The report prints its own column headings, which matters: in the database this table
        is stored as <code>v1</code>, <code>v2</code>, <code>v3</code> with no column
        meaning, and <code>v1</code> means only <em>the first figure column of this page</em>.
        The page itself calls it <code>{E.headings[1]}</code>.
      </Body>
      <TableTwin
        head={['', ...E.headings.slice(1)]}
        rows={[...E.schools.map(s => [s.school, s.resident, s.choice_in, s.total]),
               ['All Schools Total', E.district_resident, E.district_choice_in,
                E.district_total]]}
        note={<>Extract status <code>{E.status}</code>. {E.status_means} What is established
          instead is the table&rsquo;s own arithmetic, asserted by the generator before this
          page will build: {E.checks.join('; ')}.</>} />
      <Body>
        Every one of the {E.district_choice_in} school choice students the town counted is
        in the high school &mdash; {E.choice_in_outside_hs} anywhere else. Lunenburg is a
        net receiver at exactly the grades this scenario is about.
      </Body>

      <H3>The athletes: the district&rsquo;s athletics workbook, FY{String(P.fy).slice(2)}</H3>
      <TableTwin
        head={['Season', 'High school participations', 'As a share of the high school']}
        rows={[...P.seasons.map(s => [s.season, s.participations.toFixed(0),
                                      share(s.participations / E.hs_resident)]),
               ['All three seasons', P.hs_participations.toFixed(0),
                share(P.participation_share)]]}
        note={<>{P.verdict_note}</>} />
      <NotShown>
        A participation is not a child. One student playing three seasons is three of them,
        which is why the year&rsquo;s total exceeds the entire student body. Nothing
        published is an unduplicated count of Lunenburg athletes, and this page never
        multiplies one as though it were.
      </NotShown>

      <H3>
        The formula: DESE&rsquo;s FY{String(F.fy).slice(2)} Chapter 70 district summary,
        row {F.row}
      </H3>
      <TableTwin
        head={['Cell', 'As DESE heads the column', 'Lunenburg']}
        rows={[
          [F.cells.enrollment, F.headings.D6, F.enrollment.toLocaleString()],
          [F.cells.foundation, F.headings.E6, usd(F.foundation)],
          [F.cells.required, F.headings.F6, usd(F.required)],
          [F.cells.aid, F.headings.G6, usd(F.aid)],
          [F.cells.nss, F.headings.H6, usd(F.nss)],
        ]}
        note={<><code>{F.cells.required}</code> + <code>{F.cells.aid}</code> ={' '}
          <code>{F.cells.nss}</code> exactly, which is the identity the sheet states about
          itself and the generator asserts. Sheet <code>{F.sheet}</code> of{' '}
          <a className="underline" style={{ color: 'var(--series-cost)' }}
            href={abs('/docs/' + F.source.replace('sources/', ''))}>{F.source}</a>
          {F.as_of ? `, as of ${F.as_of}` : ''}. The same five figures are carried
          independently in <code>model/taxbase.py</code> and the two are compared before
          this page will build.</>} />

      <div className="card p-5 mt-6 max-w-3xl"
        style={{ borderLeft: `4px solid ${LOSS}` }}>
        <p className="text-[11px] font-semibold uppercase tracking-widest mb-2"
          style={{ color: 'var(--text-muted)' }}>The subtraction that is not doing the work</p>
        <p className="text-[15px] leading-relaxed">
          {usd(F.foundation)} &minus; {usd(F.required)} = <strong>{usd(F.gap)}</strong>.
          Chapter 70 aid is <strong>{usd(F.aid)}</strong> &mdash; {usd(F.above_gap)} more,
          or {share(F.above_gap_share_of_aid)} of the aid.{' '}
          {F.districts_above_gap} of the {F.operating_districts} operating districts on the
          same sheet ({share(F.districts_above_gap_share)}) are in the same position.
        </p>
        <p className="text-[14px] leading-relaxed mt-3" style={{ color: 'var(--text-secondary)' }}>
          So a model that removes foundation dollars per pupil and reduces aid by the same
          amount is assuming a relationship these numbers do not currently display. That is
          not a flaw in anybody&rsquo;s reasoning &mdash; it is a fact that only shows up if
          you have the district summary open at the right row.
        </p>
      </div>

      <Maybe settle={<>DESE&rsquo;s FY{String(F.fy).slice(2)} preliminary Chapter 70 aid
        calculation for Lunenburg &mdash; the per-district worksheet that states the
        foundation aid, minimum aid and hold-harmless components separately. This archive
        holds the summary, which publishes the result of the calculation and not the
        calculation.</>}>
        <p>
          Chapter 70 carries minimum aid and hold-harmless provisions, and they are the
          obvious reason aid would sit above the foundation gap. Nothing in this archive
          applies them to Lunenburg, and the sheet does not say which provision produced
          this row. What is established is the {usd(F.above_gap)}; the mechanism is a
          hypothesis, and so is any claim about what aid would do in a year enrolment fell.
        </p>
      </Maybe>

      <H3>School choice money, the way Lunenburg currently sees it &mdash; coming in</H3>
      <Body>
        The town has a School Choice revolving fund and its annual reports have printed it
        for thirteen years. It holds tuition for students who choose <em>into</em> Lunenburg
        &mdash; the opposite direction to this scenario, and the only direction anybody
        publishes.
      </Body>
      <ChoiceIn series={fund} cherry={C.cherry_sheet} />
      <TableTwin
        caption="The School Choice revolving fund, as the annual town reports print it"
        head={['FY', 'Balance forward', 'Receipts', 'Disbursements', 'Carried forward',
               'Printed page']}
        rows={fund.map(r => [
          fy(r.fy),
          r.forward != null ? usd(r.forward) : '—',
          r.receipts != null && r.usable ? usd(r.receipts) : '—',
          r.disbursements != null ? usd(r.disbursements) : '—',
          r.carried != null ? usd(r.carried) + (r.derived ? ' *' : '') : '—',
          r.page,
        ])}
        note={<>Status <code>{C.status.join('`, `')}</code>. {C.status_means} The generator
          checks {C.arithmetic_checks} rows against their own arithmetic and{' '}
          {C.chain_checks} year-to-year balances across separately published reports, and
          refuses to write if any fails. An asterisk marks a carried balance the row itself
          implies where the extract captured only three of the four printed columns.</>} />
      <Body>
        Receipts into the fund moved from {usd(C.first.receipts ?? 0)} in{' '}
        {fy(C.first.fy)} to {usd(C.last.receipts ?? 0)} in {fy(C.last.fy)} &mdash;{' '}
        {share(Math.abs(C.receipts_pct))} lower, having peaked at{' '}
        {usd(C.peak.receipts ?? 0)} in {fy(C.peak.fy)}. The cherry sheet&rsquo;s own{' '}
        <code>School Choice Receiving</code> line, on line {C.cherry_line} of the FY2027
        Town Meeting booklet, gives{' '}
        {C.cherry_sheet.map((r, i) => (
          <span key={r.fy}>{i ? ', ' : ''}{usd(r.amount)} for {fy(r.fy)}</span>
        ))}.
      </Body>
      <NotShown>
        <p>
          <strong>These two series are not the same quantity and are not differenced here.</strong>{' '}
          One is cash the town&rsquo;s fund received in a closed fiscal year; the other is
          the state&rsquo;s estimate for a year not yet closed. This archive holds no Cherry
          Sheet for any year, so the figure a Finance Committee member quoted in January
          2026 can be reported as said and cannot be checked against the document it names.
        </p>
        <p className="mt-2.5">
          Dividing the cherry sheet line by the assumed tuition gives{' '}
          {C.implied_from_cherry.map((r, i) => (
            <span key={r.fy}>{i ? ', ' : ''}{r.students} students in {fy(r.fy)}</span>
          ))} &mdash; against the {E.district_choice_in} the town counted in {fy(E.fy)}.
          That is two assumptions stacked and it is shown only because it lands near a
          count the town printed. It is not a headcount and must not be quoted as one.
        </p>
      </NotShown>

      {/* -------------------------------------------------------- 4. WHAT THE TOWN SAID */}
      <H2 id="said">What the town said about this, in its own meetings</H2>
      <Body>
        Found by searching the meeting archive &mdash; every board, 2025 onward. Each quote
        is checked against the file it is attributed to before this page will build.
      </Body>
      <div className="grid gap-4 mt-6"
        style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 21rem), 1fr))' }}>
        {d.said.map(q => <Said key={q.key + q.date} q={q} />)}
      </div>

      {/* -------------------------------------------------------------- 5. THE CAVEATS */}
      <H2 id="limits">What this page does not show</H2>

      <div className="grid gap-4 mt-6"
        style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 20rem), 1fr))' }}>
        {[
          ['It is a scenario, not a forecast.',
           'Nothing here predicts that any student will transfer. Every dial is an input '
           + 'somebody chose, and the page exists so a reader can choose differently.'],
          ['Nobody has measured how many Lunenburg students choice out.',
           'Enrolment falls for many reasons — families moving, smaller birth cohorts, '
           + 'charter schools, school choice — and a fall in enrolment is not a count of '
           + 'departures.'],
          ['Participations are not students.',
           'The 45% is tested against a participation count and bounded by it, not '
           + 'measured from it. No unduplicated athlete roster is published.'],
          ['Chapter 70 is a formula this project cannot reproduce.',
           'The archive holds DESE’s summary, which publishes the result. What aid would '
           + 'actually be in a year enrolment fell needs the calculation, and that is a '
           + 'different document.'],
          ['A budget line is net, and it is dollars.',
           'The per-pupil appropriation here is what the town raises after aid, divided by '
           + 'a count. It is not what educating a child costs, and grants, fees and '
           + 'revolving funds are in documents this one does not read.'],
          ['The tuition rate is statute, not a measurement of Lunenburg.',
           'It is higher for special education, and this archive holds no document stating '
           + 'either rate. Every dollar figure on this page moves with that dial.'],
        ].map(([h, b]) => (
          <div key={h} className="card p-4">
            <p className="text-[14px] font-bold leading-snug">{h}</p>
            <p className="text-[13.5px] leading-relaxed mt-2"
              style={{ color: 'var(--text-secondary)' }}>{b}</p>
          </div>
        ))}
      </div>

      <H3>And the same limits, in the register</H3>
      <Body>
        A limit written on one page is invisible to everyone who did not read that page. All
        of these are rows in the gap register, which is what{' '}
        <a className="underline" style={{ color: 'var(--series-cost)' }}
          href={abs('/what-we-cannot-answer')}>the gaps page</a>, the records request and{' '}
        <a className="underline" style={{ color: 'var(--series-cost)' }}
          href={abs('/api/money_gaps.json')}>the API</a> all read.
      </Body>
      <div className="grid gap-3 mt-5">
        {d.gaps.map(g => (
          <div key={g.what} className="pl-4" style={{ borderLeft: '3px solid var(--grid)' }}>
            <p className="text-[10.5px] font-semibold uppercase tracking-widest"
              style={{ color: 'var(--text-muted)' }}>{g.side.replace(/_/g, ' ')}</p>
            <p className="text-[14px] font-bold mt-0.5">{g.what}</p>
            <p className="text-[13px] leading-relaxed mt-1"
              style={{ color: 'var(--text-secondary)' }}>{g.why}</p>
            {g.closes && (
              <p className="text-[13px] leading-relaxed mt-1.5">
                <span className="font-semibold">Closes with:</span>{' '}
                <span style={{ color: 'var(--text-secondary)' }}>{g.closes}</span>
              </p>
            )}
          </div>
        ))}
      </div>

      {/* ----------------------------------------------------------------- 6. THE RAW */}
      <H2 id="raw">The data behind this page</H2>
      <Body>
        Everything above is computed from one static file, written by one script that
        refuses to write if any of eleven checks fails.
      </Body>
      <ul className="mt-4 text-[14px] leading-relaxed list-disc pl-5 max-w-2xl"
        style={{ color: 'var(--text-secondary)' }}>
        <li>
          <a className="underline" style={{ color: 'var(--series-cost)' }}
            href={abs('/data/if-students-leave.json')}>/data/if-students-leave.json</a>{' '}
          &mdash; every measured figure on this page, with its coordinate
        </li>
        <li>
          <a className="underline" style={{ color: 'var(--series-cost)' }}
            href={abs('/docs/' + F.source.replace('sources/', ''))}>{F.source}</a> &mdash;
          DESE&rsquo;s FY{String(F.fy).slice(2)} Chapter 70 district summary
        </li>
        <li>
          <a className="underline" style={{ color: 'var(--series-cost)' }}
            href={abs('/data/athletics.json')}>/data/athletics.json</a> &mdash; the
          participation counts and the fee schedule
        </li>
        <li>
          <a className="underline" style={{ color: 'var(--series-cost)' }}
            href={abs('/data/money_gaps.json')}>/data/money_gaps.json</a> &mdash; the gap
          register, in full
        </li>
        <li><code>{d.generated_by}</code> &mdash; the generator, and its refusals</li>
      </ul>

      <H3>The athletics fund loses fees too, and that is a different pot</H3>
      <Body>
        At the {fy(S.fee.fy)} high school fee of {usd(S.fee.amount)},{' '}
        {m.leavers} athletes taking {P.per_athlete} sports each is{' '}
        {m.participationsLost.toFixed(0)} participations and {usd(m.feesLost)} that does not
        reach the athletics revolving fund. That is not the town&rsquo;s general fund and
        the two must not be added: the fund also stops incurring some of the cost of those
        athletes, and{' '}
        <a className="underline" style={{ color: 'var(--series-cost)' }}
          href={abs('/what-sports-cost')}>what a sport actually costs</a> is not
        established. The fee is from {S.fee.source}.
      </Body>

      <H2 id="related">Related analyses</H2>
      <div className="grid gap-3 mt-5">
        {d.related.map(r => (
          <a key={r.id} href={abs(r.url)}
            className="card block px-4 py-4 min-h-[44px] transition-opacity hover:opacity-90">
            <span className="flex items-baseline gap-2 flex-wrap">
              <span className="text-[15px] font-bold leading-tight"
                style={{ color: 'var(--series-cost)' }}>{r.title} &rarr;</span>
              <span className="text-[10.5px] font-semibold uppercase tracking-wider tnum"
                style={{ color: 'var(--text-muted)' }}>
                {r.words.toLocaleString()} words &middot; {r.updated}
              </span>
            </span>
            <span className="block text-[13.5px] mt-1.5 leading-snug"
              style={{ color: 'var(--text-secondary)' }}>{r.why}</span>
          </a>
        ))}
      </div>

      <p className="text-[12px] mt-12 max-w-2xl" style={{ color: 'var(--text-muted)' }}>
        Generated by <code>{d.generated_by}</code> from {d.source}
      </p>
    </div>
  )
}

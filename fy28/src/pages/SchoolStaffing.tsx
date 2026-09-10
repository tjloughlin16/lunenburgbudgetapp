import type { Tab } from '../routes'
import { abs } from '../lib/abs'
import { useEffect, useState } from 'react'
import {
  PeerRatio, StaffAgainstEnrollment, TableTwin, WindowedSeries, SchoolPanels,
  SubjectMovement,
  fy, num, pct,
  type NamedWindow,
} from '../components/StaffingCharts'
import type { Composition, Peer, State } from '../lib/staffing'
import {
  Conclusions, Coverage, Grain, NotEstablished, Provenance, Quote, MoreReports,
  Body, H2, NotShown, Stat,
  ReportShell,
} from '../components/report'
import type { Base, Conclusion } from '../components/report'

/** The frame this report is drawn in. See components/report.tsx.
 *  TITLE is the report's NAME, used before the payload arrives; the h1 the
 *  reader lands on is the finding, which needs the data to state. */
const TAB: Tab = 'staffing'
const DATA = '/data/school-staffing.json'
const TITLE = 'School staffing'

/** Did school staffing go up? — the window, and why the answer depends on it.
 *
 *  WHY THIS PAGE EXISTS.
 *
 *  Two town bodies are publicly disagreeing about whether the schools have added staff,
 *  and both are quoting true numbers. The state's teacher FTE series has two peaks and no
 *  trend, so the SIGN of the answer is a property of the years somebody picks. This page
 *  refuses to pick for the reader: the window is a control, the three named windows are
 *  each chosen by a rule that is nobody's argument, and the count of how many spans give
 *  each answer is on the page.
 *
 *  ONE INSTRUMENT, DELIBERATELY. Everything here is DESE's published full-time-equivalent
 *  count — the district total, the same total split by school and by what is taught, and
 *  the enrolment it is set against. No rosters and no dollars, because those answer
 *  different questions and have their own pages:
 *
 *    /who-works-in-each-school — the names the town printed, the people the state counted,
 *      and why a roster is not a census.
 *    /the-paraprofessionals — the biggest single change in who the schools employ, and the
 *      budget lines underneath it.
 *
 *  RULE 7. "Teacher FTE fell 17 posts" is a measurement. Every reason anybody offers for
 *  it is a hypothesis. Each section states what the data shows and, in its own box, what
 *  it does not.
 *
 *  RULE 2. Not one figure is typed into this file. Every number arrives from
 *  /data/school-staffing.json, including the counts inside sentences.
 *
 *  NO D1 AT PAGE LOAD. One static file. */

type Payload = Base & {
  conclusions: Conclusion[]
  generated_by: string
  source: string
  composition: Composition
  state: State
  peers: Peer[]
}

export function SchoolStaffing() {
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

  if (err) return <ReportShell tab={TAB} title={TITLE} dataUrl={DATA} err={err} />

  if (!d) return <ReportShell tab={TAB} title={TITLE} dataUrl={DATA} loading />

  const st = d.state
  const w = st.change_over_roster_years
  const teachFte = w.teacher_fte!
  const pupils = w.pupils_in_district!
  const perPupil = w.teachers_per_100!
  const lastTeach = st.ranks.teachers[st.ranks.teachers.length - 1]
  const yearsLast = st.ranks.teachers.filter(r => r.rank === r.of).length

  /* ---- the composition series. Nothing here computes a FIGURE; these are lookups and
     orderings of rows the generator already derived (rule 2). */
  const comp = d.composition
  const ew = comp.every_window
  const NAMED: NamedWindow[] = [
    { key: 'charted', label: 'The charted years', ...comp.windows.charted },
    { key: 'recent', label: 'Since the last peak', ...comp.windows.recent },
    { key: 'whole', label: 'Every published year', ...comp.windows.whole },
  ].map(w => ({ key: w.key, label: w.label, first_fy: w.first_fy, last_fy: w.last_fy,
    why: w.why }))
  const subWindow = comp.subjects.windows[0]
  const worstSchool = comp.schools.biggest_fall
  const whole = comp.windows.whole
  const charted = comp.windows.charted

  return (
    <ReportShell tab={TAB} dataUrl={DATA}
      title={<>
        Did staffing go up? {ew.fell} of {ew.pairs} published spans say it fell.
      </>}
      standfirst={<>
        Both sides of this argument are quoting true numbers &mdash; the same series rises
        over {ew.rose} of those spans. The sign is a property of the window, not of the
        town.
      </>}
    >

      <Grain>{d.grain}</Grain>

      <div className="mt-10 flex flex-wrap gap-x-12 gap-y-6">
        <Stat value={`${ew.fell} of ${ew.pairs}`} tone="var(--series-cost)">
          pairs of published years over which the state counts <em>fewer</em> teachers at
          the end than the start &mdash; {ew.rose} of them count more
        </Stat>
        <Stat value={`${charted.change > 0 ? '+' : charted.change < 0 ? '−' : ''}${Math.abs(charted.change).toFixed(1)} FTE`}>
          over {fy(charted.first_fy)}&ndash;{fy(charted.last_fy)} &mdash; the span of the
          staffing chart the Tri-Board was shown, read off the minutes
        </Stat>
        <Stat value={`${whole.change > 0 ? '+' : whole.change < 0 ? '−' : ''}${Math.abs(whole.change).toFixed(1)} FTE`}
          tone={whole.change >= 0 ? 'var(--series-revenue)' : 'var(--series-cost)'}>
          over {fy(whole.first_fy)}&ndash;{fy(whole.last_fy)} &mdash; every year the state
          has published, the same series
        </Stat>
        {/* THE STANDING, NOT THE STREAK. This box read `1 years` for a while, because
            the run is counted off DESE's comparison set and DESE changed who is in it —
            charter districts entered and the unbroken run collapsed to a single year. A
            streak that can be reset by somebody else's filing is not a stat box. The
            rank, with the count of districts REPORTING IN THAT YEAR beside it, is. */}
        <Stat value={`${lastTeach.rank} of ${lastTeach.of}`}>
          where Lunenburg sits for teachers per hundred pupils in {fy(lastTeach.fy)}, among
          the districts on DESE&rsquo;s own comparison sheet &mdash; last in{' '}
          {yearsLast} of the {st.ranks.teachers.length} years it has published
        </Stat>
        <Stat value={pct(pupils.pct!)} tone="var(--series-cost)">
          in-district enrollment, {fy(pupils.first_fy)}&ndash;{fy(pupils.last_fy)}, against{' '}
          {pct(teachFte.pct!)} for teacher FTE over the same years
        </Stat>
      </div>

      {/* ------------------------------------------------ 1. CONCLUSIONS (rule 7b) */}
      {/* NOT WRITTEN HERE. Every word and every figure comes out of this report's own
          payload, computed by the generator that computed the figures -- see
          scripts/conclusions.py. The same rows appear on /what-it-all-adds-up-to, read
          from the same file, so the two cannot drift apart. */}
      <H2 id="conclusions">If you read nothing else</H2>
      <Conclusions rows={d.conclusions} />

      {/* ================================================== TRENDS OVER TIME
          The centre of this page, and the answer to the question two town bodies are
          publicly disagreeing about. The window is the reader's to move; the page does
          not pick one for them and then argue from it. */}
      <H2 id="over-time">Did staffing go up? That depends entirely on the years you pick</H2>
      <Body>
        Teacher FTE, every year the state has published. Over the {ew.pairs} pairs of those
        years, the count is <em>lower</em> at the end in {ew.fell} of them and higher in{' '}
        {ew.rose}. The series has two peaks and no trend, so the sign of the answer is a
        property of the window rather than of the town &mdash; which is why the window
        below is a control rather than a choice we made for you.
      </Body>
      <div className="mt-6">
        <WindowedSeries rows={comp.district} windows={NAMED} />
      </div>
      <TableTwin caption="Teacher FTE, and the two denominators, every published year"
        head={['Year', 'Teacher FTE', 'Pupils', 'Per 100 pupils', 'High needs',
          'Per 100 high needs']}
        rows={comp.district.map(r => [
          fy(r.fy), num(r.fte, 1),
          r.students === null ? '—' : r.students.toLocaleString(),
          r.per_100_students === null ? '—' : num(r.per_100_students, 2),
          r.high_needs === null ? '—' : r.high_needs.toLocaleString(),
          r.per_100_high_needs === null ? '—' : num(r.per_100_high_needs, 2)])} />

      <div className="grid gap-3 mt-6 sm:grid-cols-2 lg:grid-cols-3">
        {NAMED.map(w => {
          const win = comp.windows[w.key]
          return (
            <div key={w.key} className="card p-4">
              <p className="text-[13px] font-bold">{w.label}</p>
              <p className="text-2xl font-bold tnum mt-1"
                style={{ color: win.change >= 0 ? 'var(--series-revenue)' : 'var(--series-cost)' }}>
                {win.change > 0 ? '+' : win.change < 0 ? '−' : ''}
                {Math.abs(win.change).toFixed(1)} FTE
              </p>
              <p className="text-[12.5px] mt-1" style={{ color: 'var(--text-secondary)' }}>
                {fy(win.first_fy)}&ndash;{fy(win.last_fy)} &middot; {num(win.first, 1)} to{' '}
                {num(win.last, 1)} &middot; {win.up} of {win.steps} year-steps rise
              </p>
              <p className="text-[12px] mt-1.5" style={{ color: 'var(--text-muted)' }}>
                {w.why}.
              </p>
            </div>
          )
        })}
      </div>

      <Body>
        Those three are not a menu of opinions. Each one is picked by a rule that is
        nobody&rsquo;s argument: every year the state has published; the span of the chart
        the Tri-Board was actually shown, read off the minutes; and the latest local
        maximum in the series to the latest year. Any other pair of years is one you can
        set above, and the shaded band will tell you what it gives.
      </Body>

      <div className="grid gap-3 mt-6 lg:grid-cols-3">
        {d.said.filter(q => ['chair-staffing-up', 'composition-not-headcount',
          'need-has-risen'].includes(q.key)).map(q => <Quote key={q.key} q={q} />)}
      </div>

      <NotShown>
        <p>
          <strong>That any of these windows is the right one.</strong> The chart is drawn
          from a single series and the arithmetic is the same in every direction. What the
          page establishes is that a chart starting in one year rather than another is an
          argument, and that the remedy is to print the span on it.
        </p>
        <p className="mt-2.5">
          <strong>Who paid for any of it.</strong> The federal ESSER money arrived and
          ended inside this window &mdash; thirteen positions, by the Finance
          Committee&rsquo;s own account. DESE counts grant-funded staff exactly like staff
          the town appropriates, so both events are invisible in this line. See{' '}
          <a className="underline" style={{ color: 'var(--series-cost)' }}
            href={abs('/when-grants-end')}>what happens when a grant stops</a>.
        </p>
      </NotShown>

      {/* ================================================== by school */}
      <H2 id="by-school">Which building the movement is in</H2>
      <Body>
        The same FTE, split by school, from {fy(comp.schools.era)} onward. It starts there
        because {comp.eras.why_school.charAt(0).toLowerCase() + comp.eras.why_school.slice(1)}{' '}
        The schools sum to the district total in every year: the largest disagreement
        across the whole run is {num(Math.abs(comp.schools.worst.difference), 1)} FTE, in{' '}
        {fy(comp.schools.worst.fy)}.
      </Body>
      <SchoolPanels rows={comp.schools.rows} from={comp.schools.era} />
      <Body>
        <strong>{worstSchool.name} carries most of it.</strong>{' '}
        {worstSchool.since_era && <>
          {num(worstSchool.since_era.first, 1)} teacher FTE in{' '}
          {fy(worstSchool.since_era.first_fy)} to {num(worstSchool.since_era.last, 1)} in{' '}
          {fy(worstSchool.since_era.last_fy)}, with {worstSchool.since_era.up} of{' '}
          {worstSchool.since_era.steps} year-steps rising.
        </>}{' '}
        {comp.schools.steady.length > 0 && <>
          {comp.schools.steady.length} of the open schools move less than a whole FTE over
          the same years: {comp.schools.steady.join(', ')}.
        </>}
      </Body>
      <TableTwin caption={`Every school, ${fy(comp.schools.era)} onward`}
        head={['School', 'Grades', 'First year', 'FTE then', 'Latest year', 'FTE now',
          'Change', 'Steps that rose']}
        rows={comp.schools.rows.filter(r => r.since_era).map(r => [
          r.name, r.grades || '—', fy(r.since_era!.first_fy), num(r.since_era!.first, 1),
          fy(r.since_era!.last_fy), num(r.since_era!.last, 1),
          `${r.since_era!.change > 0 ? '+' : r.since_era!.change < 0 ? '−' : ''}${Math.abs(r.since_era!.change).toFixed(1)}`,
          `${r.since_era!.up} of ${r.since_era!.steps}`])} />

      <NotShown>
        <p>
          <strong>Why a school gained or lost.</strong> A building&rsquo;s FTE moves with
          its roll, with the grades it holds, with how a district apportions a teacher who
          works in two buildings, and with decisions. Nothing here separates them, and the
          FY2017 reconfiguration is the reason this panel does not run back to FY2008.
        </p>
      </NotShown>

      {/* ================================================== by subject */}
      <H2 id="by-subject">A flat total hiding a recomposition</H2>
      <Body>
        The same teachers, split by what they teach, over {fy(subWindow.first_fy)} to{' '}
        {fy(subWindow.last_fy)} &mdash; {subWindow.why}. The net across{' '}
        {subWindow.subjects} subjects is {num(subWindow.net, 1)} FTE. The{' '}
        <em>gross</em> is {num(subWindow.gross, 1)}: {num(subWindow.up, 1)} added to
        subjects that grew and {num(Math.abs(subWindow.down), 1)} taken from those that
        shrank. A total that barely moves is not a district that barely moved.
      </Body>
      <div className="mt-6">
        <SubjectMovement rows={subWindow.rows} first_fy={subWindow.first_fy}
          last_fy={subWindow.last_fy} />
      </div>
      <TableTwin caption={`Every subject, ${fy(subWindow.first_fy)} to ${fy(subWindow.last_fy)}`}
        head={['Subject', `FTE in ${fy(subWindow.first_fy)}`,
          `FTE in ${fy(subWindow.last_fy)}`, 'Change']}
        rows={subWindow.rows.map(r => [
          r.subject, num(r.first, 1), num(r.last, 1),
          `${r.change > 0 ? '+' : r.change < 0 ? '−' : ''}${Math.abs(r.change).toFixed(1)}`])} />
      <Body>
        A subject losing FTE is not the same fact as a subject losing a class.{' '}
        <a className="underline" style={{ color: 'var(--series-cost)' }}
          href={abs('/what-courses-actually-ran')}>Which classes actually ran</a> counts
        sections rather than staff, and finds the two moving together in eight subjects out
        of ten and disagreeing in mathematics. The two pages deliberately do not difference
        one against the other.
      </Body>
      {d.said.filter(q => q.key === 'cuts-by-subject' || q.key === 'one-music-teacher')
        .length > 0 && (
        <div className="grid gap-3 mt-6 lg:grid-cols-2">
          {d.said.filter(q => ['cuts-by-subject', 'one-music-teacher'].includes(q.key))
            .map(q => <Quote key={q.key} q={q} />)}
        </div>
      )}

      {/* ================================================== 2. teachers against enrollment */}
      <H2 id="enrollment">Enrollment fell. The teaching count did not follow it.</H2>
      <Body>
        Over the same years the town was printing rosters, in-district enrollment moved{' '}
        {pct(pupils.pct!)} &mdash; from {num(pupils.first, 1)} FTE pupils to{' '}
        {num(pupils.last, 1)} &mdash; while teacher FTE moved {pct(teachFte.pct!)}. Teachers
        per 100 pupils therefore rose {pct(perPupil.pct!)}, from {num(perPupil.first, 2)} to{' '}
        {num(perPupil.last, 2)}.
      </Body>
      <Body>
        <strong>That still leaves Lunenburg near the bottom of its group.</strong> It ranks{' '}
        {lastTeach.rank} of the {lastTeach.of} districts DESE put on the sheet in{' '}
        {fy(lastTeach.fy)} &mdash; the highest of them reports{' '}
        {num(lastTeach.highest_value, 2)} against Lunenburg&rsquo;s{' '}
        {num(lastTeach.value, 2)} &mdash; and it has been last of the reporting districts
        in {yearsLast} of the {st.ranks.teachers.length} years published. A ratio rising
        and a ratio being low are not in tension: both are true here. Who is on that sheet
        is DESE&rsquo;s decision and it changes, so the count of districts travels with
        every rank on this page.
      </Body>
      <div className="grid gap-4 mt-6 lg:grid-cols-2">
        <StaffAgainstEnrollment rows={st.points} />
        <PeerRatio peers={d.peers} field="teachers_per_100"
          unit="Teacher FTE per 100 in-district pupils" subject="Lunenburg" />
      </div>
      <TableTwin caption="Lunenburg, as the state published it"
        head={['Year', 'Teacher FTE', 'Para FTE', 'In-district pupils', 'Teachers per 100',
          'Paras per 100']}
        rows={st.points.map(p => [fy(p.fy), num(p.teacher_fte, 1), num(p.para_fte, 1),
          num(p.pupils_in_district, 1), num(p.teachers_per_100, 2), num(p.paras_per_100, 2)])} />

      <NotShown>
        <p>
          <strong>Whether a staffing level was chosen.</strong> A district cannot shed a
          teacher for every departing child: sections, grade spans and required subjects
          set a floor that has nothing to do with the enrollment total. A ratio moving is
          the arithmetic of a falling denominator at least as much as it is a decision.
        </p>
        <p className="mt-2.5">
          <strong>What a teacher is here.</strong> DESE&rsquo;s definition, applied by
          DESE. It is not the district&rsquo;s payroll, not the contract&rsquo;s bargaining
          unit, and not the names the town prints on a roster &mdash; which are counted,
          separately and never against this series, on{' '}
          <a className="underline" style={{ color: 'var(--series-cost)' }}
            href={abs('/who-works-in-each-school')}>who works in each school</a>.
        </p>
      </NotShown>


      {/* ------------------------------------------------ the other two staffing pages */}
      {/* RULE 7b: LINK, DO NOT DUPLICATE. The finding this page reaches -- that the sign
          is a property of the window -- is what the other two need available, not
          restated. */}
      <H2 id="next">The same staff, counted two other ways</H2>
      <div className="grid gap-3 mt-5 lg:grid-cols-2">
        <a className="card px-4 py-3.5 block" href={abs('/who-works-in-each-school')}>
          <p className="text-[14.5px] font-bold">Who works in each school</p>
          <p className="text-[13px] mt-1" style={{ color: 'var(--text-secondary)' }}>
            The names the town printed, building by building, beside the people and the
            posts the state counts in the same buildings. Headcount is a different
            quantity from FTE and this page is FTE throughout.
          </p>
        </a>
        <a className="card px-4 py-3.5 block" href={abs('/the-paraprofessionals')}>
          <p className="text-[14.5px] font-bold">The paraprofessionals</p>
          <p className="text-[13px] mt-1" style={{ color: 'var(--text-secondary)' }}>
            The biggest single change in who Lunenburg&rsquo;s schools employ, the
            general-education half that grew while the special-education half halved, and
            the budget lines underneath.
          </p>
        </a>
      </div>

      {/* ------------------------------------------------------ rule 15a, with its denominator */}
      <H2 id="said">What the town said about this, and how much of the archive could be read</H2>
      <Body>
        Every quote on this page is re-read out of the archive on each build and the build
        refuses to write if one is no longer verbatim there. These are the terms searched
        &mdash; in the town&rsquo;s vocabulary rather than ours, which is why{' '}
        <em>adjustment counselor</em> and <em>reduction in force</em> are on the list
        despite returning nothing.
      </Body>
      <Coverage m={d.minutes} searched={d.searched} />

      {/* ------------------------------------------------------------- what it cannot say */}
      <H2 id="cannot">What this page cannot say</H2>
      <NotEstablished rows={d.not_established} closes={d.closes} />

      {/* ------------------------------------------------------------------ rule 12 */}
      <H2 id="documents">The documents behind this</H2>
      <Provenance sources={d.sources} />

      {/* ------------------------------------------------------------------ where it came from */}
      <H2 id="sources">Where every figure on this page comes from</H2>
      <div className="grid gap-2.5 mt-5 max-w-3xl">
        <div className="card px-4 py-3.5">
          <p className="text-[14px] font-bold">The state&rsquo;s FTE and enrollment</p>
          <p className="text-[12.5px] mt-1" style={{ color: 'var(--text-secondary)' }}>
            {st.points.length} years, {fy(st.first_fy)}&ndash;{fy(st.last_fy)}, LEA{' '}
            {st.lea}, {d.peers.length} districts. Every measure reconciles against
            DESE&rsquo;s own printed totals ({Object.entries(st.reconciles)
              .map(([k, n]) => `${n} ${k || 'not checkable'}`).join(', ')}).
          </p>
          <p className="text-[12px] mt-1.5" style={{ color: 'var(--text-muted)' }}>
            {st.docs.join(', ')}
          </p>
        </div>
        <div className="card px-4 py-3.5">
          <p className="text-[14px] font-bold">The window matrix</p>
          <p className="text-[12.5px] mt-1" style={{ color: 'var(--text-secondary)' }}>
            Every ordered pair of the {ew.years.length} published years, computed rather
            than sampled: {ew.pairs} of them, {ew.fell} falling, {ew.rose} rising,{' '}
            {ew.flat} flat. The build refuses to write unless the three account for every
            pair.
          </p>
        </div>
        <div className="card px-4 py-3.5">
          <p className="text-[14px] font-bold">This page&rsquo;s own data file</p>
          <p className="text-[12.5px] mt-1" style={{ color: 'var(--text-secondary)' }}>
            Everything above is read at build time from{' '}
            <code>{d.source}</code> by <code>{d.generated_by}</code> and served as one static
            file. Nothing is typed into a sentence.
          </p>
          <p className="text-[12px] mt-1.5">
            <a className="underline" style={{ color: 'var(--series-cost)' }}
              href={abs('/data/school-staffing.json')}>/data/school-staffing.json</a>
          </p>
        </div>
      </div>

      <MoreReports here={TAB} />
    </ReportShell>
  )
}

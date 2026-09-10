import type { Tab } from '../routes'
import { useEffect, useState } from 'react'
import { abs } from '../lib/abs'
import { Basis } from '../components/Basis'
import {
  Caption, FULL, Legend, Quadrant, QuadrantKey, RAN, RanAgainstFull,
  SectionsOverTime, SubjectChange, SubjectChips, SubjectDetail, SubjectsOverTime,
  TableTwin, ThreeInstruments, n0, n1, pct1, signed, syLong,
  type Band, type Era, type EraSubject, type Point, type QuadRow,
  type Subject,
} from '../components/CourseCharts'
import {
  Body, Conclusions, Coverage, Grain, H2, H3, MoreReports, NotEstablished, NotShown,
  Provenance, Quote, ReportShell, Stat,
} from '../components/report'
import type { Conclusion, Said, Source, Minutes } from '../components/report'

const TAB: Tab = 'courses'
const DATA = '/data/course-offerings.json'

/** WHAT LUNENBURG'S SCHOOLS ACTUALLY TAUGHT — how many classes ran, in what, year by
 *  year.
 *
 *  WHY THIS PAGE EXISTS AND WHY IT IS NOT /school-staffing AGAIN. The town has argued for
 *  three budget cycles about whether the cuts narrowed what children can take, and every
 *  measurement anybody brought to that argument counted PEOPLE. Teacher FTE is a real
 *  quantity and it cannot tell four Spanish sections from two. DESE's class-size
 *  collection counts the sections, so a subject with none is a subject nobody ran. This
 *  is the first page here that measures what was TAUGHT rather than who was employed.
 *
 *  RULE 7 IS THE HARDEST THING ABOUT THIS PAGE AND IT IS DRAWN THROUGHOUT. Fewer sections
 *  is a measurement. That a child lost an opportunity is a claim needing separate
 *  evidence — and the district's own principal supplied the competing reading in
 *  public: courses are whittled away after student choices are entered. So a fall can be
 *  fewer children choosing. That quote is on the page, at the top of the section it
 *  qualifies, rather than in a footnote.
 *
 *  RULE 13, STRUCTURALLY. `Lunenburg High` is grades 8-12 for four of these fifteen years
 *  and grades 9-12 for the other eleven, and this page knows that because DESE prints a
 *  count per GRADE per school — not because anybody read the school's name. Every
 *  long chart shades the other era and splits its series into separate dataKeys, so a
 *  line through the break is not expressible.
 *
 *  RULE 7a. The thing first. The high school's own series is the top of the page; the
 *  reason the elementary schools are absent comes after, beside the elementary section.
 *
 *  RULE 7b. Conclusions, then the organised categorical data, then the raw and the
 *  caveats.
 *
 *  RULE 8. Not an audit. The gap in the record is registered rather than complained
 *  about, and the district gets its credit: a student described a new elective being
 *  added in the same cycle as the cut list.
 *
 *  RULE 2. Not one figure is typed into this file. Everything arrives from
 *  /data/course-offerings.json, written by scripts/build_course_offerings.py and
 *  recomputed from the CSV by a second route in scripts/verify_course_offerings.py.
 *
 *  NO D1 AT PAGE LOAD. Static files. */

type LangPoint = {
  sy: number; sections: number; avg: number; students: number
  school_students: number | null; share: number | null
}

type Instruments = {
  org: string; first_sy: number; last_sy: number; years: number
  subjects: QuadRow[]; compared: number; steps_readable: boolean
  quadrants: { quadrant: string; subjects: string[]; count: number }[]
  on_the_line: string[]
  spread_thinner: string[]
  fewer_teachers_more_classes: string[]
  fuller: string[]; emptier: string[]; one_step: string[]
}

type Participation = {
  org: string; first_sy: number; last_sy: number; years: number
  denominator: {
    years: { sy: number; all_students: number; enrolled: number; gap: number }[]
    worst_gap: number; bound: number; what: string
  }
  subjects: {
    subj: string; short: string
    points: { sy: number; students: number; share: number; sections: number
              avg: number }[]
    first_share: number; last_share: number; share_change: number
    first_students: number; last_students: number
    sections_first: number; sections_last: number; sections_change: number
    avg_first: number; avg_last: number
    step: number; step_from_sy: number; step_to_sy: number; one_step: boolean
    spikes: number[]
  }[]
  movers: string[]; fell: string[]; rose: string[]; held: string[]
  one_step: { short: string; from_sy: number; to_sy: number; step: number }[]
  spiked: { short: string; years: number[] }[]
}

type Payload = {
  about: string
  grain: string
  generated_by: string
  window: { first_sy: number; last_sy: number; years: number; why: string }
  first_sy: number
  last_sy: number
  eras: Era[]
  configurations: { sy: number; schools: { name: string; span: string; students: number }[] }[]
  rollups: {
    ch74_rows: number; cells: number
    district_residual: { sy: number; sections: number; students: number; schools: number }[]
  }
  implausible: { sy: number; org: string; avg: number; sections: number; students: number }[]
  implausible_cell: {
    sy: number; org: string; subj: string; sections: number; avg: number
    students: number; school_students: number
  }
  seats_tolerance: number
  high_school: Point[]
  district: Point[]
  middle: Point[]
  high_school_subjects: Subject[]
  middle_subjects: Subject[]
  district_subjects: Subject[]
  language: {
    high: LangPoint[]; middle: LangPoint[]
    high_first: LangPoint; high_last: LangPoint
    middle_first: LangPoint; middle_last: LangPoint
    middle_low: LangPoint; middle_peak: LangPoint
    middle_prior_at_this_level: number[]
    middle_recovered: boolean
    middle_run: number[]
    middle_step: {
      sy: number; from_sy: number; from_sections: number; to_sections: number
      from_share: number; to_share: number; from_students: number; to_students: number
      years_at_this_level: number
    }
  }
  headline: {
    first: Point; last: Point
    sections_change: number; students_change: number
    gainers: number; losers: number; zeroed: string[]
    biggest_gain: string | null; biggest_loss: string | null
  }
  fte: {
    first_sy: number; last_sy: number; agree: number; compared: number; disagree: number
    disagreeing: string[]
    biggest_line: string
    biggest_disagreement: {
      subj: string; fte_change: number; sections_change: number
      first_avg: number; last_avg: number; first_students: number; last_students: number
      fte_first: number; fte_last: number; is_largest_line: boolean
    }
    subjects: {
      subj: string; fte_first: number; fte_last: number; fte_change: number
      sections_first: number; sections_last: number; sections_change: number
      agrees: boolean; fte_beyond: number | null; fte_beyond_change: number | null
    }[]
  }
  fte_beyond: { sy: number; subjects: { subj: string; fte: number }[] }
  instruments: Instruments
  fte_rollup: { worst: number; at: [number, string] | null; tolerance: number
                subject_years: number }
  schools: {
    name: string; org_code: string
    eras: { span: string; first_sy: number; last_sy: number }[]
    window: { span: string; first_sy: number; last_sy: number; years: number } | null
    stability: {
      swing: number; from_sy: number; to_sy: number
      from_sections: number; to_sections: number; students_swing: number
      trendable: boolean; bound: number
      sections: { sy: number; sections: number; students: number; avg: number }[]
    } | null
    subjects: Subject[] | null
    instruments: Instruments | null
    participation: Participation | null
    excluded: string | null
  }[]
  decomposition: {
    subj: string; short: string
    district: QuadRow
    parts: {
      org: string; trendable: boolean
      fte_first: number; fte_last: number; fte_change: number
      sections_first: number; sections_last: number; sections_change: number
      avg_first: number; avg_last: number; avg_change: number
    }[]
    fte_sum: number; sections_sum: number
    gained: { org: string; fte_change: number; sections_change: number; avg_last: number }
    lost: { org: string; fte_change: number; sections_change: number
            avg_first: number; avg_last: number }
  }
  reorganisation: {
    boundaries: number[]
    eras: { org: string; runs: { span: string; first_sy: number; last_sy: number }[] }[]
    flagged: { org: string; from_sy: number; to_sy: number; from_sections: number
               to_sections: number; avg?: number; at_boundary: boolean }[]
    flagged_count: number; at_boundary: number; away_from_boundary: number
    clusters_on_reorganisation: boolean
  }
  bands: Band[]
  era_series: {
    org: string; bands: Band[]; subjects: EraSubject[]
    first_sy: number; last_sy: number
    units: { fte: string; seats: string; participation: string }
  }
  grade8_staffing: {
    years: number[]
    grade_6_8: { fy: number; fte: number; total: number }[]
    first: number; last: number; zero_years: number[]; noise_bound: number
    total_before: number | null; total_during: number; total_after: number | null
  }
  grade8_shift: {
    grade8_era: number; grade8_first_sy: number; grade8_last_sy: number
    grade8_span: string; current_span: string; count: number
    subjects: {
      subj: string; short: string; first_sy: number; last_sy: number
      end_to_end: number; era_values: number[]; into: number; out_of: number
      grade8_first_sy: number; grade8_last_sy: number
      since: { first_sy: number; last_sy: number; participation: number
               covid: boolean }[]
      since_change: number
    }[]
  }
  miscellaneous: {
    subj: string; short: string; first_sy: number; last_sy: number
    sections_first: number; sections_last: number; sections_change: number
    share_first: number; share_last: number; share_change: number
    avg_first: number; avg_last: number
    students_first: number; students_last: number
    seats_first: number; seats_last: number
    per_student_first: number | null; per_student_last: number | null
    spikes: number[]
  }
  retired: {
    subj: string; last_sy: number; last_sections: number; last_students: number
    years_since: number; ran_years: number[]; in_reliable_years: boolean
  }[]
  computer_science: {
    nine_to_twelve_years: number[]
    high: { sy: number; sections: number }[]
    high_all: { sy: number; sections: number; students: number }[]
    middle: { sy: number; sections: number }[]
    hs_sections: number; hs_year: number; hs_students: number; middle_years: number
    ran_first: number; ran_last: number; ran_years: number[]
  }
  curriculum: {
    rows: number; with_product: number; blank: number
    subjects: { subject: string; rows: number; with_product: number }[]
    products: string[]; reported_subjects: string[]
  }
  sources: Source[]
  said: (Said & { section: string })[]
  searched: { term: string; documents: number }[]
  minutes: Minutes
  gaps: { side: string; what: string; why: string; closes: string }[]
  not_established: string[]
  closes: string
  differently: string
  conclusions: Conclusion[]
}

const TITLE = 'What courses actually ran'

function A({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <a className="underline" style={{ color: 'var(--series-cost)' }} href={href}>{children}</a>
  )
}

function Shell({ err, loading, standfirst, children }: {
  err?: string | null; loading?: boolean
  standfirst?: React.ReactNode; children?: React.ReactNode
}) {
  return (
    <ReportShell tab={TAB} dataUrl={DATA} title={TITLE} standfirst={standfirst}
      err={err} loading={loading}>{children}</ReportShell>
  )
}

export function CourseOfferings() {
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
  return <Report d={d} />
}

/** Split out so the chart state below can use hooks — a component that returns early
 *  while loading cannot also hold them. */
function Report({ d }: { d: Payload }) {
  // WHICH SUBJECTS THE READER IS LOOKING AT. Five is the cap because five is what the
  // palette was validated for; a sixth choice pushes the oldest out rather than
  // introducing a hue nothing checked.
  const defaults = d.schools.find(s0 => s0.name === 'Lunenburg High')
    ?.participation?.movers.slice(0, 5) ?? []
  const [chosen, setChosen] = useState<string[]>(defaults)
  const [focus, setFocus] = useState<string>(
    d.decomposition.subj)
  const toggle = (name: string) => setChosen(c =>
    c.includes(name) ? c.filter(x => x !== name)
      : (c.length >= 5 ? [...c.slice(1), name] : [...c, name]))

  const W = d.window
  const H = d.headline
  const KEEP = '9–12'

  // Everything below is derived from the payload at render time. Nothing is typed, and
  // scripts/verify_course_offerings.py recomputes each of these from the CSV, because
  // no generator publishes them and nothing else here would notice one going wrong.
  const subs = d.high_school_subjects
  const gained = subs.filter(s => s.change > 0).sort((a, b) => b.change - a.change)
  const lostSec = subs.filter(s => s.change < 0).sort((a, b) => a.change - b.change)
  const flat = subs.filter(s => s.change === 0)
  const fl = subs.find(s => s.subj === 'Foreign Language')
  const misc = subs.find(s => s.subj === 'Miscellaneous')
  const L = d.language
  const IC = d.implausible_cell
  const mostSaid = [...d.searched].sort((a, b) => b.documents - a.documents)[0]
  const neverSaid = d.searched.filter(t => t.documents === 0)
  const ml = d.middle_subjects.find(s => s.subj === 'Foreign Language')
  const cs = d.computer_science
  const otherEra = d.eras.find(e => e.span !== KEEP)
  const window912 = d.high_school.filter(p => p.sy >= W.first_sy && p.sy <= W.last_sy)
  const seatsFirst = window912[0]
  const seatsLast = window912[window912.length - 1]
  const I = d.instruments
  const DEC = d.decomposition
  const ES = d.era_series
  const G8 = d.grade8_shift
  const MISC = d.miscellaneous
  const BANDS = d.bands
  const CURRENT = BANDS[BANDS.length - 1].span
  const g8band = BANDS[G8.grade8_era]
  const G8S = d.grade8_staffing
  const hsPart = d.schools.find(s0 => s0.name === 'Lunenburg High')?.participation ?? null
  const drawable = d.schools.filter(s0 => s0.instruments)
  const notDrawable = d.schools.filter(s0 => !s0.instruments)
  const others = d.schools.filter(s0 => s0.instruments && s0.name !== 'Lunenburg High')
  const eraSubjects = ES.subjects
  const shown = chosen
    .map(name => eraSubjects.find(x => x.short === name))
    .filter((x): x is EraSubject => Boolean(x))
  const focused = eraSubjects.find(x => x.subj === focus) ?? null
  const beyond = d.fte.subjects
    .filter(s => s.fte_beyond_change !== null && s.fte_beyond_change !== 0)
    .sort((a, b) => Math.abs(b.fte_beyond_change!) - Math.abs(a.fte_beyond_change!))

  const subjRow = (s: Subject) => [
    s.subj, n0(s.first), n0(s.last), signed(s.change),
    n1(s.first_avg), n1(s.last_avg), n0(s.first_students), n0(s.last_students),
  ]
  const subjHead = ['Subject', `Sections ${syLong(W.first_sy)}`,
                    `Sections ${syLong(W.last_sy)}`, 'Change',
                    `Class size ${syLong(W.first_sy)}`, `Class size ${syLong(W.last_sy)}`,
                    `Students ${syLong(W.first_sy)}`, `Students ${syLong(W.last_sy)}`]

  return (
    <Shell standfirst={<>
      How many classes ran in each subject, {syLong(W.first_sy)} to {syLong(W.last_sy)}:
      more of them at Lunenburg High than {W.years - 1} years ago, for the same number of
      children &mdash; and fewer of those children taking a language.
    </>}>

      {/* ---------------------------------------------------------- 1. THE THING FIRST */}
      <div className="grid gap-6 mt-9"
        style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 15rem), 1fr))' }}>
        <Stat value={n0(H.last.sections)}>
          course sections ran at Lunenburg High in {syLong(H.last.sy)} &mdash;{' '}
          {signed(H.sections_change)} on {syLong(H.first.sy)}, for{' '}
          {signed(H.students_change)} students
        </Stat>
        <Stat value={n1(H.last.avg)}>
          students to a class, down from {n1(H.first.avg)}. More classes for the same
          children means smaller ones
        </Stat>
        <Stat value={`${gained.length} up, ${lostSec.length} down`}>
          subjects that gained and lost sections over the {W.years} years.{' '}
          {flat.length} were unchanged
        </Stat>
        <Stat value={fl ? signed(fl.change) : '—'}>
          sections in {H.biggest_loss}, the subject that lost most &mdash;{' '}
          {fl ? <>{n0(fl.first)} to {n0(fl.last)}</> : null}
        </Stat>
        <Stat value={n0(cs.hs_sections)}>
          computer science sections at the high school across the{' '}
          {cs.nine_to_twelve_years.length} years it held only grades 9&ndash;12
        </Stat>
        <Stat value={pct1(L.middle_last.share ?? 0)}>
          of Lunenburg Middle School took a world language in{' '}
          {syLong(L.middle_last.sy)}, against{' '}
          {pct1(L.middle_step.from_share)} in {syLong(L.middle_step.from_sy)} &mdash; the
          lowest share in the {L.middle.length} years the school has existed
        </Stat>
      </div>

      <Grain>{d.grain}</Grain>

      {/* -------------------------------------------------- 1. CONCLUSIONS (rule 7b) */}
      {/* NOT WRITTEN HERE. Every word and every figure comes out of this report's own
          payload, computed by the generator that computed the figures -- see
          scripts/conclusions.py. The same rows appear on /what-it-all-adds-up-to, read
          from the same file, so the two cannot drift apart. */}
      <H2 id="conclusions">If you read nothing else</H2>
      <Conclusions rows={d.conclusions} />

      {/* ====================================================================
          2. WHAT A STAFFING CHANGE DID TO WHAT RAN — the two visuals this page
          was rebuilt around, immediately under the conclusions.

          RULE 7a. The chart is the section; the prose that qualifies it comes after
          it, and the key comes after the dots it is a key to. */}
      <H2 id="instruments">Where the staffing changes landed on the timetable</H2>
      <Body>
        <Basis level="cross-checked">two DESE files that never see each other &mdash;
          teacher FTE by subject, and the count of classes that ran in it</Basis>
      </Body>
      <Body>
        <A href={abs('/school-staffing')}>School staffing</A> measures these same schools
        with the instrument this town&rsquo;s argument has used for years: full-time
        equivalents the state publishes by subject. Over the years both files cover the
        two move the same way in {n0(d.fte.agree)} of {n0(d.fte.compared)} subjects
        &mdash; and the useful part of this chart is the ones that do not.
      </Body>
      <Quadrant rows={I.subjects.filter(r => !r.on_the_line)} />
      <QuadrantKey />
      <Caption>
        Every subject the district staffs and teaches, {syLong(I.first_sy)} to{' '}
        {syLong(I.last_sy)} &mdash; {I.years} years, district-wide. Horizontal is the
        change in teacher FTE, in full-time posts; vertical is the change in sections,
        in classes that ran. A subject at {n1(DEC.district.fte_change)} and{' '}
        {signed(DEC.district.sections_change)} lost{' '}
        {n1(Math.abs(DEC.district.fte_change))} posts and gained{' '}
        {n0(DEC.district.sections_change)} classes.{' '}
        <strong>The two lower-left and upper-right corners are a subject moving one
        way on both instruments.</strong> The other two are where they disagree, and
        that is what neither file can show on its own.
        {I.on_the_line.length ? <> {I.on_the_line.join(' and ')}{' '}
          {I.on_the_line.length > 1 ? 'are' : 'is'} not drawn: one instrument did not
          move at all, so there is no corner to be in.</> : null}
      </Caption>
      <Body>
        <strong>The fill is the third instrument, and it is a test rather than a
        decoration.</strong> A subject with fewer teachers and more classes is
        consistent with the same people spread thinner &mdash; but only if the classes
        got FULLER. {I.spread_thinner.length === 0 ? <>
          Not one subject in that corner did.{' '}
          {I.fewer_teachers_more_classes.join(' and ')} lost teachers and gained
          classes, and the classes got SMALLER, so the spread-thinner reading is
          refuted by the district&rsquo;s own third measurement rather than by
          anything argued here.</> : <>
          {I.spread_thinner.join(' and ')} did, and{' '}
          {I.fewer_teachers_more_classes.filter(x => !I.spread_thinner.includes(x))
            .join(' and ') || 'nothing else in that corner'} did not.</>}
      </Body>
      <TableTwin caption="Every subject, both instruments and the third"
        head={['Subject', `FTE ${syLong(I.first_sy)}`, `FTE ${syLong(I.last_sy)}`,
               'Change', `Sections ${syLong(I.first_sy)}`,
               `Sections ${syLong(I.last_sy)}`, 'Change', 'Class size', 'Where it lands']}
        rows={I.subjects.map(r => [
          r.subj, n1(r.fte_first), n1(r.fte_last),
          (r.fte_change > 0 ? '+' : r.fte_change < 0 ? '−' : '') + n1(Math.abs(r.fte_change)),
          n0(r.sections_first), n0(r.sections_last), signed(r.sections_change),
          `${n1(r.avg_first)} → ${n1(r.avg_last)}`,
          r.quadrant ?? r.axis ?? '—'])}
        note={<><strong>These are two ends and not a trend, and at district level that is
          all they can be.</strong> The district total is the sum of five schools, two of
          which report section counts that double and halve between adjacent years, so the
          years BETWEEN these two carry those swings and nothing here reads them. Both
          ends are ordinary years at all five schools, which is what makes the endpoint
          comparison stand. The year-by-year moves are in the school tables below, where
          the counts can be read. Class size is DESE&rsquo;s own average and it is a third
          quantity again: not what ran and not who was employed.</>} />

      <H3>The district figure, and which building it happened in</H3>
      <Body>
        A subject&rsquo;s teacher FTE is a district total, and a total is what two
        schools moving in opposite directions looks like when nobody splits it.{' '}
        {DEC.subj} is the clearest case in the file: the district figure is{' '}
        {n1(DEC.district.fte_change)} posts, and underneath it{' '}
        {DEC.gained.org} is up {n1(DEC.gained.fte_change)} while {DEC.lost.org} is down{' '}
        {n1(Math.abs(DEC.lost.fte_change))}. The four schools add to the district figure
        exactly, on both instruments, and the generator refuses to write if they stop
        doing so.
      </Body>
      <TableTwin caption={`${DEC.subj}, by building`}
        head={['', `FTE ${syLong(I.first_sy)}`, `FTE ${syLong(I.last_sy)}`, 'Change',
               'Sections', 'Change', 'Class size']}
        rows={[
          ...DEC.parts.map(pt => [
            pt.org + (pt.trendable ? '' : ' *'),
            n1(pt.fte_first), n1(pt.fte_last),
            (pt.fte_change > 0 ? '+' : pt.fte_change < 0 ? '−' : '')
              + n1(Math.abs(pt.fte_change)),
            `${n0(pt.sections_first)} → ${n0(pt.sections_last)}`,
            signed(pt.sections_change),
            `${n1(pt.avg_first)} → ${n1(pt.avg_last)}`]),
          ['The four together', n1(DEC.parts.reduce((a, x) => a + x.fte_first, 0)),
           n1(DEC.parts.reduce((a, x) => a + x.fte_last, 0)),
           (DEC.fte_sum > 0 ? '+' : '−') + n1(Math.abs(DEC.fte_sum)),
           '', signed(DEC.sections_sum), ''],
          ['The district, as DESE files it', n1(DEC.district.fte_first),
           n1(DEC.district.fte_last),
           (DEC.district.fte_change > 0 ? '+' : '−')
             + n1(Math.abs(DEC.district.fte_change)),
           `${n0(DEC.district.sections_first)} → ${n0(DEC.district.sections_last)}`,
           signed(DEC.district.sections_change),
           `${n1(DEC.district.avg_first)} → ${n1(DEC.district.avg_last)}`],
        ]}
        note={<>* marks a school whose section counts this page does not trend &mdash;{' '}
          the reason is below, under the elementary schools. Its figures are here so the
          identity can be seen to close, and no line is drawn through them.</>} />

      <H3>The year one instrument can see and the other cannot</H3>
      <Body>
        The teacher file runs to {syLong(d.fte_beyond.sy)} and the class-size collection
        stops at {syLong(d.fte.last_sy)}. So the FTE moves in that last year have no
        section count beside them, and nothing here differences the two: they are
        different quantities at different stages, and a line drawn through both would be
        the mistake this whole site is built to avoid.
      </Body>
      <TableTwin caption={`Teacher FTE in ${syLong(d.fte_beyond.sy)}, with no section count to set beside it`}
        head={['Subject', `FTE ${syLong(d.fte.last_sy)}`,
               `FTE ${syLong(d.fte_beyond.sy)}`, 'Change']}
        rows={beyond.map(s => [s.subj, n1(s.fte_last), n1(s.fte_beyond!),
          (s.fte_beyond_change! > 0 ? '+' : '−') + n1(Math.abs(s.fte_beyond_change!))])}
        note={<>Only the subjects that moved are listed. This is the year in which the
          largest changes <A href={abs('/school-staffing')}>school staffing</A> reports
          actually happen, which is why that page and this one can both be right about a
          subject and appear to disagree.</>} />

      <H3>The same chart, school by school</H3>
      <Body>
        Each school on its own window and its own axes. They come out the same span
        here &mdash; {syLong(drawable[0]?.window?.first_sy ?? 0)} to{' '}
        {syLong(drawable[0]?.window?.last_sy ?? 0)} &mdash; because the SY
        {BANDS[G8.grade8_era + 1]?.first_sy} reset is what starts every one of them,
        and that is a fact about the buildings rather than a choice made here.
      </Body>
      <div className="grid gap-8 mt-6 md:grid-cols-2">
        {drawable.map(s0 => (
          <div key={s0.name}>
            <p className="text-[13px] font-semibold" style={{ color: 'var(--text-primary)' }}>
              {s0.name}
            </p>
            <p className="text-[12px]" style={{ color: 'var(--text-muted)' }}>
              grades {s0.window?.span} · {syLong(s0.window?.first_sy ?? 0)}&ndash;
              {syLong(s0.window?.last_sy ?? 0)} · {s0.instruments?.compared} subjects
              with both instruments
            </p>
            <Quadrant rows={s0.instruments!.subjects.filter(r => !r.on_the_line)}
              height={300} compact />
            <TableTwin head={['Subject', 'ΔFTE', 'Δsections', 'Class size',
                              'Where it lands', 'Biggest single year']}
              rows={s0.instruments!.subjects.map(r => [
                r.short,
                (r.fte_change > 0 ? '+' : r.fte_change < 0 ? '−' : '')
                  + n1(Math.abs(r.fte_change)),
                signed(r.sections_change),
                `${n1(r.avg_first)} → ${n1(r.avg_last)}`,
                r.quadrant ?? r.axis ?? '—',
                `${signed(r.step)} ${syLong(r.step_from_sy)}→${syLong(r.step_to_sy)}`])}
              note={s0.instruments!.one_step.length
                ? <><strong>{s0.instruments!.one_step.join(', ')}</strong>{' '}
                  {s0.instruments!.one_step.length > 1 ? 'each moved' : 'moved'} further
                  in a single year than across the whole window, so the net figure is the
                  residue of a step rather than a drift.</>
                : <>No subject here moved further in one year than across the whole
                  window.</>} />
          </div>
        ))}
      </div>
      <Caption>
        {drawable.map(s0 => s0.name).join(' and ')} only.{' '}
        {notDrawable.map(s0 => s0.name).join(' and ')} are not drawn, for reasons
        measured rather than asserted &mdash; see below.
      </Caption>

      {/* ====================================================================
          3. HOW MANY CHILDREN GOT IN — the third instrument, and the one that
          answers whether provision narrowed for STUDENTS rather than on paper. */}
      <H2 id="participation">How many children got into each subject</H2>
      <Body>
        <Basis level="cross-checked">the share against DESE&rsquo;s separate
          enrolment-by-grade count for the same school and year</Basis>
      </Body>
      <SubjectsOverTime subjects={shown} bands={BANDS} current={CURRENT}
        metric="participation" />
      <SubjectChips all={eraSubjects} chosen={chosen} onToggle={toggle} max={5} />
      <Caption>
        Lunenburg High, {syLong(ES.first_sy)} to {syLong(ES.last_sy)} &mdash;{' '}
        {ES.last_sy - ES.first_sy + 1} years. Each line is the share of the school that
        took anything in that subject area, over the school&rsquo;s own student count.
        Pick up to five. <strong>The darker band is a different school.</strong>{' '}
        Lunenburg High held grades {G8.grade8_span} from {syLong(G8.grade8_first_sy)} to{' '}
        {syLong(G8.grade8_last_sy)}, because Thomas C Passios had closed and every
        remaining school moved up one grade band until the new building opened. Nothing
        about what a ninth to twelfth grader was offered changed at either end of it.
      </Caption>

      <H3>The same subjects, but the classes rather than the children</H3>
      <SubjectsOverTime subjects={shown} bands={BANDS} current={CURRENT}
        metric="sections" height={260} />
      <Caption>
        The same five, counted as classes that RAN. These are two different questions
        and they do not have to agree: a subject can gain classes and lose takers, which
        means more and smaller groups, and one subject here does exactly that.
      </Caption>
      <TableTwin caption={`Every subject at Lunenburg High, ${syLong(ES.last_sy)}`}
        head={['Subject', `Share ${syLong(hsPart!.first_sy)}`,
               `Share ${syLong(hsPart!.last_sy)}`, 'Change',
               'Sections', 'Change', 'Class size', 'Biggest single year']}
        rows={[...hsPart!.subjects]
          .sort((a, b) => b.last_share - a.last_share)
          .map(r => [
            r.subj, pct1(r.first_share), pct1(r.last_share),
            `${r.share_change > 0 ? '+' : r.share_change < 0 ? '−' : ''}${
              (Math.abs(r.share_change) * 100).toFixed(1)} pts`,
            `${n0(r.sections_first)} → ${n0(r.sections_last)}`,
            signed(r.sections_change),
            `${n1(r.avg_first)} → ${n1(r.avg_last)}`,
            `${r.step > 0 ? '+' : '−'}${(Math.abs(r.step) * 100).toFixed(0)} pts ${
              syLong(r.step_from_sy)}→${syLong(r.step_to_sy)}`])}
        note={<><strong>A share, not a count.</strong> Enrolment at the high school
          fell from {n0(d.high_school[0].students)} to{' '}
          {n0(d.high_school[d.high_school.length - 1].students)} over the file, so a raw
          count of children falls with the school whether or not provision changed. The
          denominator is {hsPart!.denominator.what} &mdash; the two agree to within{' '}
          {pct1(hsPart!.denominator.worst_gap)} in every year of the window.{' '}
          {hsPart!.spiked.length ? <>{hsPart!.spiked.map(x =>
            `${x.short} in ${x.years.map(y => syLong(y)).join(' and ')}`).join('; ')}{' '}
            stands more than fifteen points off both neighbouring years; it is marked
            rather than averaged in.</> : null}</>} />

      <H3>The bucket with no subject in its name</H3>
      <Body>
        A resident asked the question this section exists for: whether children are being
        offered thinner work and taking it &mdash; a filler bucket swelling while the
        subjects around it shrink. {MISC.subj} is that bucket, and the two instruments
        say different things about it. <strong>Its classes went from{' '}
        {n0(MISC.sections_first)} to {n0(MISC.sections_last)}. The share of the school in
        one went from {pct1(MISC.share_first)} to {pct1(MISC.share_last)}.</strong> More
        groups, the same children, and the groups got smaller &mdash;{' '}
        {n1(MISC.avg_first)} students to {n1(MISC.avg_last)}.
      </Body>
      <Body>
        {n0(MISC.seats_last)} student places ran in it in {syLong(MISC.last_sy)} among{' '}
        {n0(MISC.students_last)} different children, so a child in one is in about{' '}
        {MISC.per_student_last} of them. Groups of under five are the shape of
        small-group support rather than of a room somebody is parked in &mdash;{' '}
        <em>and that is a reading, not a finding.</em> DESE files no course name against
        any of them, so academic support, an elective, directed study and a study hall
        all fit these numbers equally. What would separate them is the district&rsquo;s
        own Program of Studies, which exists and is not published.
      </Body>
      <TableTwin caption={`${MISC.subj} at Lunenburg High, year by year`}
        head={['Year', 'Sections', 'Students in it', 'Share of the school',
               'Students to a class', 'Student places']}
        rows={(hsPart!.subjects.find(r => r.subj === MISC.subj)?.points ?? []).map(pt => [
          syLong(pt.sy), n0(pt.sections), n0(pt.students), pct1(pt.share),
          n1(pt.avg), n0(Math.round(pt.sections * pt.avg))])}
        note={<>Student places are sections times the average class. They are not
          children: one child fills several, which is the whole of the difference
          between the second column and the third.</>} />

      <Body>
        <strong>And the district has said, in public, that it expects more of
        them.</strong> A resident asked the School Committee about extra-large study
        halls in the FY26 budget and was answered directly. That is the school year
        AFTER the last one this file covers, so it is a statement of what the district
        expected rather than a measurement of what happened &mdash; and it does not say
        the Miscellaneous rows are study halls. Nothing published says what they are, and
        groups averaging {n1(MISC.avg_last)} are not what a large study hall looks like.
        Both of those are true at once.
      </Body>
      <div className="grid gap-4 mt-4 md:grid-cols-2">
        {d.said.filter(q => q.section === 'misc').map(q => <Quote key={q.key} q={q} />)}
      </div>

      <H3>When grade 8 was in this building</H3>
      <Body>
        {G8.count} subjects move by more than ten points of participation into{' '}
        {syLong(G8.grade8_first_sy)}&ndash;{syLong(G8.grade8_last_sy)} and more than ten
        points back out of them. An eighth grade that all takes a subject &mdash; or none
        of which takes it &mdash; moves a school&rsquo;s share that far by arriving,
        without one thing changing about what anybody else was offered.{' '}
        <strong>That is why nothing on this page is read across {syLong(g8band.first_sy)}{' '}
        or {syLong(g8band.last_sy + 1)}</strong>, and why every trend here is read inside
        an era.
      </Body>
      <Body>
        <strong>And the arrival is visible in a second state file that does not know
        about the first.</strong> DESE publishes teaching FTE by grade band as well as
        enrolment by grade, collected separately and for a different purpose. Lunenburg
        High staffs {G8S.first} to {G8S.last} full-time posts against the grades 6&ndash;8
        band in each of those {G8S.years.length} years, and zero in every one of the
        other {G8S.zero_years.length} the file covers. The school&rsquo;s total teaching
        FTE goes from {n1(G8S.total_before ?? 0)} before to an average of{' '}
        {n1(G8S.total_during)} during and {n1(G8S.total_after ?? 0)} after. Two files
        agreeing is what makes the boundary an assertion here rather than a reading, and
        the generator refuses to write if they stop.
      </Body>
      <TableTwin caption="The subjects that moved when the grades did"
        head={['Subject', ...BANDS.map(b => `${syLong(b.first_sy)}–${syLong(b.last_sy)}${
          b.covid ? ' *' : ''}`), 'Into', 'Back out', `Since ${syLong(g8band.last_sy + 1)}`]}
        rows={G8.subjects.map(r => [
          r.subj, ...r.era_values.map(v => pct1(v)),
          `${r.into > 0 ? '+' : '−'}${(Math.abs(r.into) * 100).toFixed(0)} pts`,
          `${r.out_of > 0 ? '+' : '−'}${(Math.abs(r.out_of) * 100).toFixed(0)} pts`,
          `${r.since_change > 0 ? '+' : r.since_change < 0 ? '−' : ''}${
            (Math.abs(r.since_change) * 100).toFixed(0)} pts`])}
        note={<>Each cell is the average share across the era, not a single year.{' '}
          <strong>The last column is the comparison this page actually makes</strong>:
          what the subject has done since grade 8 left, at one configuration throughout.
          * marks the pandemic era &mdash; that boundary is not in the data. The other
          three are read off DESE&rsquo;s enrolment-by-grade counts; this one we
          asserted, and a reader is free to disagree with it.</>} />

      {/* ====================================================================
          4. THREE INSTRUMENTS ON ONE SUBJECT — matching a staffing change to what
          happened to students, which is the thing no single file can do. */}
      <H2 id="three">One subject, three instruments, five eras</H2>
      <Body>
        What was staffed, how much room ran, and how many children got in &mdash; three
        DESE series for the same subject at the same school, averaged inside each era.
        <strong> Four readings this separates and no single file can:</strong> staffing
        down with places and takers down; staffing down with takers holding, which is a
        change absorbed; staffing down with places UP, which is more and smaller groups;
        and staffing flat with takers falling, which is not a staffing story at all.
        Which of those a subject shows is a measurement. Why it shows it is not, and
        nothing below says why.
      </Body>
      <div className="flex flex-wrap gap-1.5 mt-5">
        {eraSubjects.map(s0 => (
          <button key={s0.short} type="button" onClick={() => setFocus(s0.subj)}
            aria-pressed={s0.subj === focus}
            className="text-[12px] px-2 py-1 rounded-full border transition-colors"
            style={{
              borderColor: s0.subj === focus ? RAN : 'var(--grid)',
              color: s0.subj === focus ? RAN : 'var(--text-secondary)',
              background: s0.subj === focus ? 'var(--surface-2)' : 'transparent',
              fontWeight: s0.subj === focus ? 600 : 400,
            }}>{s0.short}</button>
        ))}
      </div>
      {focused ? (
        <>
          <ThreeInstruments subject={focused} bands={BANDS} />
          <Caption>
            {focused.subj} at Lunenburg High. Each bar is the average across the era
            below it, over {BANDS.map(b => b.years).join(', ')} years respectively.{' '}
            <strong>The grey bar is the era the school held grades{' '}
            {G8.grade8_span}</strong>, and nothing should be read across it. Teacher FTE
            is posts; student places are sections times the average class and are not a
            count of children; the share is over the school&rsquo;s own student count.
            {focused.has_fte ? null : <> DESE files no teacher FTE against this subject
              area in any year, so the first panel is empty rather than zero.</>}
          </Caption>
          <TableTwin caption={`${focused.subj}, era by era`}
            head={['Era', 'High school grades', 'Teacher FTE', 'Student places',
                   'Sections', 'Students to a class', 'Share of the school']}
            rows={focused.eras.map((e, i) => [
              `${syLong(e.first_sy)}–${syLong(e.last_sy)}${e.covid ? ' *' : ''}`,
              BANDS[i]?.span ?? '—',
              e.fte === null ? '—' : e.fte.toFixed(2),
              n0(e.seats), n1(e.sections), n1(e.avg), pct1(e.participation)])}
            note={<>* the pandemic era, the one boundary here that is ours rather than
              the state&rsquo;s. Every figure is a mean across the era&rsquo;s own
              years; the year-by-year figures for every subject are in the table
              above.</>} />
        </>
      ) : null}



      <H2 id="subjects">Which subjects gained sections, and which lost them</H2>
      <SubjectChange subjects={subs} />
      <Caption>
        Change in sections at Lunenburg High, {syLong(W.first_sy)} to{' '}
        {syLong(W.last_sy)} &mdash; {W.years} years, one grade span throughout. Ranked by
        the size of the move rather than the size of the subject: a large subject that did
        not move is not the finding. {flat.length} subjects are not drawn because they did
        not change.
      </Caption>
      <TableTwin caption="Every subject at Lunenburg High" head={subjHead}
        rows={subs.map(subjRow)}
        note={<>Sections are what RAN. Class size is DESE&rsquo;s own average. Students
          is the count of DISTINCT children who took the subject &mdash; not seats, and
          not the sum of the classes.</>} />

      <H3>The same, school by school</H3>
      <Body>
        Each school over its own window rather than a common one. Forcing four schools
        onto one span would either throw years away or straddle a reorganisation, and
        both are worse than four charts with four spans printed on them.
      </Body>
      <div className={others.length > 1
        ? 'grid gap-8 mt-6 md:grid-cols-2' : 'mt-6 max-w-3xl'}>
        {others.map(s0 => (
          <div key={s0.name}>
            <p className="text-[13px] font-semibold" style={{ color: 'var(--text-primary)' }}>
              {s0.name}
            </p>
            <p className="text-[12px]" style={{ color: 'var(--text-muted)' }}>
              grades {s0.window?.span} · {syLong(s0.window?.first_sy ?? 0)}&ndash;
              {syLong(s0.window?.last_sy ?? 0)} · {s0.window?.years} years, one grade
              span throughout
            </p>
            <SubjectChange subjects={s0.subjects!} height={300} />
            <TableTwin head={['Subject', 'Sections', 'Change', 'Class size']}
              rows={s0.subjects!.map(r => [
                r.subj, `${n0(r.first)} → ${n0(r.last)}`, signed(r.change),
                `${n1(r.first_avg)} → ${n1(r.last_avg)}`])} />
          </div>
        ))}
      </div>
      <div className="mt-6 max-w-2xl">
        <p className="text-[11px] font-semibold uppercase tracking-widest mb-2"
          style={{ color: 'var(--text-muted)' }}>
          The schools that carry no chart, and why
        </p>
        <ul className="text-[12.5px] leading-relaxed space-y-2"
          style={{ color: 'var(--text-muted)' }}>
          {notDrawable.map(s0 => (
            <li key={s0.name}>
              <span style={{ color: 'var(--text-secondary)', fontWeight: 600 }}>
                {s0.name}</span> &mdash; {s0.excluded}.
            </li>
          ))}
        </ul>
        <p className="text-[12.5px] leading-relaxed mt-3"
          style={{ color: 'var(--text-muted)' }}>
          <strong>The bound is measured rather than chosen.</strong> The two schools
          drawn here swing at most{' '}
          {drawable.map(s0 => pct1(s0.stability!.swing)).join(' and ')} in a year; these
          swing{' '}
          {notDrawable.filter(s0 => s0.stability)
            .map(s0 => pct1(s0.stability!.swing)).join(' and ')}. The year-by-year
          evidence is under the elementary schools below.
        </p>
      </div>

      <H2 id="mechanism">How a course stops running, in the district&rsquo;s own words</H2>
      <Body>
        <strong>Read this against every chart above and every chart below.</strong> A
        section that did not run may be a section nobody chose rather than a section
        anybody cut, and the person who builds the schedule has said so in public.
        Nothing measured on this page separates the two &mdash; not the section counts,
        not the staffing comparison, and not the share of the school taking a subject.
        What the record also holds, in the same paragraph, is the school choosing what
        to ADD.
      </Body>
      <div className="grid gap-4 mt-6 md:grid-cols-2">
        {d.said.filter(q => q.section === 'mechanism').map(q => <Quote key={q.key} q={q} />)}
      </div>

      {/* ------------------------------------------- 2. THE ORGANISED CATEGORICAL DATA */}
      <H2 id="high-school">The high school, year by year</H2>
      <Body>
        <Basis level="cross-checked">the section counts against teacher FTE from a
          separate DESE file, and the grade span of the school against DESE&rsquo;s own
          enrolment-by-grade counts</Basis>
      </Body>
      <RanAgainstFull points={d.high_school} eras={d.eras} keep={KEEP} />
      <Legend items={[
        { tone: RAN, label: 'sections that ran (left axis)' },
        { tone: FULL, label: 'average class size (right axis)' },
        { tone: FULL, label: `average class size while the school held grades ${otherEra?.span ?? ''}`, dash: true },
      ]} />
      <Caption>
        {d.high_school.length} school years, {syLong(d.first_sy)} to {syLong(d.last_sy)}.
        <strong> The shaded band is a different school.</strong> Lunenburg High held
        grades {otherEra?.span} from {syLong(otherEra?.first_sy ?? 0)} to{' '}
        {syLong(otherEra?.last_sy ?? 0)}, so a section count inside it is not comparable
        with one outside it &mdash; which is why the dashed line does not join the solid
        one. Everything this page concludes rests on {syLong(W.first_sy)} to{' '}
        {syLong(W.last_sy)}: {W.why}.
      </Caption>
      <TableTwin caption="Lunenburg High, every measured year"
        head={['Year', 'Grades', 'Sections', 'Average class', 'Students',
               'Seats', 'Seats per student']}
        rows={d.high_school.map(p => {
          const era = d.eras.find(e => p.sy >= e.first_sy && p.sy <= e.last_sy)
          return [syLong(p.sy), era?.span ?? '—', n0(p.sections), n1(p.avg),
                  n0(p.students), n0(p.seats ?? 0),
                  p.seats_per_student === null || p.seats_per_student === undefined
                    ? '—' : p.seats_per_student.toFixed(2)]
        })}
        note={<><strong>Seats per student is the closest thing here to
          &ldquo;how many classes a child takes&rdquo;</strong>, and it barely moves
          inside the window: {seatsFirst?.seats_per_student?.toFixed(2)} in{' '}
          {syLong(W.first_sy)} and {seatsLast?.seats_per_student?.toFixed(2)} in{' '}
          {syLong(W.last_sy)}. It is <em>seats</em> and not children: a seat is one
          student in one class, and the same child fills several. Sections times the
          average class size, which reconciles with the sum of the subjects&rsquo; own to
          within {pct1(d.seats_tolerance)} in every year.</>} />

      <H3>Did anything stop altogether</H3>
      <Body>
        {d.retired.length} subjects ran district-wide at some point and have run nothing
        since. They are small &mdash; the largest ran{' '}
        {n0(Math.max(...d.retired.map(r => r.last_sections)))} sections in its last year
        &mdash; and the vocational and technical areas are where they cluster, which is
        where a narrowing would show first if there were one.
      </Body>
      <TableTwin caption="Subjects that ran, and have not since"
        head={['Subject', 'Last year it ran', 'Sections then', 'Students then',
               'Years since', 'Year we can rely on?']}
        rows={d.retired.map(r => [r.subj, syLong(r.last_sy), n0(r.last_sections),
          n0(r.last_students), n0(r.years_since),
          r.in_reliable_years ? 'yes' : 'no — see below'])}
        note={<>A subject whose last year is {syLong(d.first_sy)} is a different claim
          from one whose last year is later: {syLong(d.first_sy)} is the first year of
          this collection and the year one Lunenburg school reports an average class size
          of {n0(d.implausible[0].avg)}. &ldquo;It stopped&rdquo; and &ldquo;it was never
          recorded properly&rdquo; fit that year equally well, and this table marks which
          rows sit in it rather than choosing.</>} />
      <NotShown>
        <p>
          <strong>That any of these was cut.</strong> A subject running one or two
          sections is a subject one teacher&rsquo;s timetable can carry or drop, and a
          retirement, a schedule and a decision all look identical here. Nor is a district
          total the whole story: Lunenburg&rsquo;s vocational students go to{' '}
          <A href={abs('/monty-tech')}>Monty Tech</A>, which is a different school and a
          different page, and every Chapter 74 row in this file is zero.
        </p>
      </NotShown>

      <NotShown>
        <p>
          <strong>That a subject with fewer sections offered less.</strong> A section is
          what ran, and what ran is two things at once: what the schedule offered and what
          students chose. The district&rsquo;s own account of that mechanism is on this
          page, in its own words, and it qualifies every chart here rather than this one.
        </p>
        <p className="mt-2.5">
          <strong>And nothing here is a course.</strong> DESE files sections by subject
          AREA. A named elective ending inside a subject whose total rose is invisible to
          this file, which is exactly what a student described to the School Committee in
          the quotes above.
        </p>
      </NotShown>

      {fl ? (
        <>
          <H2 id="language">Foreign language &mdash; the one subject that narrowed on
            every instrument</H2>
          <Body>
            It is also the only subject on this page that residents came to a meeting
            about, which is why it is separated from the others. Nothing in the section
            counts says a language matters more than mathematics; what says so is the
            record below.
          </Body>

          <H3>Lunenburg High</H3>
          <SubjectDetail subject={fl} students={d.high_school} />
          <Legend items={[
            { tone: RAN, label: 'sections that ran (left axis)' },
            { tone: FULL, label: 'share of the school taking a language (right axis)' },
          ]} />
          <Caption>
            {fl.points.length} school years, one grade span throughout. Sections fell from{' '}
            {n0(fl.first)} to {n0(fl.last)} and the share of the school taking a language
            from {pct1(L.high_first.share ?? 0)} to {pct1(L.high_last.share ?? 0)}. The
            average class went from {n1(fl.first_avg)} students to {n1(fl.last_avg)}{' '}
            &mdash; fewer classes, and fuller ones.
          </Caption>

          <H3>Lunenburg Middle School</H3>
          {ml ? <SubjectDetail subject={ml} students={d.middle} /> : null}
          <Legend items={[
            { tone: RAN, label: 'sections that ran (left axis)' },
            { tone: FULL, label: 'share of the school taking a language (right axis)' },
          ]} />
          <Caption>
            {L.middle.length} school years &mdash; the whole life of the school, which
            opened in {syLong(L.middle[0].sy)}.{' '}
            <strong>Read the dip before reading the fall.</strong> The school was at{' '}
            {n0(L.middle_step.to_sections)} sections once before, in{' '}
            {L.middle_prior_at_this_level.map(syLong).join(' and ')}, and came back above
            it &mdash; so one low year is not a subject ending. It has now been there
            for {L.middle_step.years_at_this_level} years, at the lowest share in the
            file: {pct1(L.middle_low.share ?? 0)} in {syLong(L.middle_low.sy)}.
          </Caption>
          <TableTwin caption="Foreign language, both schools"
            head={['Year', 'High school sections', 'Students', 'Share of the school',
                   'Middle school sections', 'Students', 'Share of the school']}
            rows={L.high.map(p => {
              const m = L.middle.find(x => x.sy === p.sy)
              return [syLong(p.sy), n0(p.sections), n0(p.students),
                      p.share === null ? '—' : pct1(p.share),
                      m ? n0(m.sections) : '—', m ? n0(m.students) : '—',
                      m && m.share !== null ? pct1(m.share) : '—']
            })}
            note={<>Share is the count of DISTINCT children who took a language over the
              school&rsquo;s own count of distinct children &mdash; both out of the same
              file and the same row family, so it is not a ratio across two instruments.
              It is not a share of children who COULD take one: the file carries no grades
              inside a school, and a language need not be offered in every grade of
              one.</>} />

          <H3>What was said about it</H3>
          <div className="grid gap-4 mt-4 md:grid-cols-2">
            {d.said.filter(q => q.section === 'language').map(q => (
              <Quote key={q.key} q={q} />
            ))}
          </div>

          <NotShown>
            <p>
              <strong>Whether a child who wanted a language could not get one.</strong>{' '}
              Sections falling and students choosing it falling are the same measurement
              seen twice, and this file cannot separate them. What it does establish is
              that all three quantities &mdash; sections, students and district teacher
              FTE &mdash; moved the same way in this subject and in no other.
            </p>
            <p className="mt-2.5">
              <strong>And the Principal&rsquo;s largest class of 31 is not in this
              file.</strong> It describes September of the school year after the last one
              measured here. It is quoted because it is the only place in the readable
              archive where somebody in the district connects the two quantities this page
              keeps apart &mdash; not because it extends the series.
            </p>
          </NotShown>
        </>
      ) : null}

      <H2 id="computing">Computer science at the high school</H2>
      <Body>
        The subject ran {n0(cs.ran_first)} to {n0(cs.ran_last)} sections a year in{' '}
        {cs.ran_years.map(syLong).join(', ')} &mdash; the {cs.ran_years.length} years
        grade 8 was housed in the building. In the {cs.nine_to_twelve_years.length} years the school held
        only grades 9&ndash;12 it ran {n0(cs.hs_sections)}: {n0(cs.hs_students)} students,
        in {syLong(cs.hs_year)}. Lunenburg Middle School has run it in every one of its{' '}
        {n0(cs.middle_years)} years.
      </Body>
      <TableTwin caption="Computer and Information Sciences, sections that ran"
        head={['Year', 'Lunenburg High sections', 'Students in them',
               'Grades at the high school', 'Lunenburg Middle School sections']}
        rows={cs.high_all.map(p => {
          const era = d.eras.find(e => p.sy >= e.first_sy && p.sy <= e.last_sy)
          const ms = cs.middle.find(x => x.sy === p.sy)
          return [syLong(p.sy), n0(p.sections), n0(p.students), era?.span ?? '—',
                  ms ? n0(ms.sections) : '—']
        })}
        note={<>Blank at the middle school means the school did not exist that year: it
          opened in {syLong(cs.middle[0].sy)}, when the district reorganised its
          buildings. <strong>Read the grade column across the high school
          column.</strong> The years with five to eight sections are the years the
          building held grade 8, and the students in them come within a dozen of the
          grade-8 cohort each year &mdash; which is a correspondence and not a proof
          that they were the same course.</>} />
      <NotShown>
        <p>
          <strong>That nobody in Lunenburg teaches computing to a ninth-grader.</strong>{' '}
          This is what DESE recorded under one subject heading. A high school that files a
          fifth of its sections as <em>Miscellaneous</em> could be teaching it under that,
          and nothing published would say so.
        </p>
      </NotShown>

      {misc ? (
        <>
          <H2 id="miscellaneous">The fifth of the high school with no named subject</H2>
          <Body>
            {n0(misc.last)} of Lunenburg High&rsquo;s {n0(H.last.sections)} sections in{' '}
            {syLong(W.last_sy)} &mdash; {pct1(misc.last / H.last.sections)} &mdash; are
            filed under <em>Miscellaneous</em>, averaging {n1(misc.last_avg)} students,
            taken by {n0(misc.last_students)} distinct children. It is also the single
            largest mover on the page: {n0(misc.first)} sections in {syLong(W.first_sy)}.
          </Body>
          <TableTwin caption="Miscellaneous at Lunenburg High"
            head={['Year', 'Sections', 'Average class', 'Students', 'Share of all sections']}
            rows={misc.points.map(p => {
              const school = d.high_school.find(x => x.sy === p.sy)
              return [syLong(p.sy), n0(p.sections), n1(p.avg), n0(p.students),
                      school ? pct1(p.sections / school.sections) : '—']
            })} />
          <NotShown>
            <p>
              <strong>What any of them is.</strong> The category carries no course names.
              Reading small groups as enrichment and reading them as remediation fit the
              same number equally well, and this page chooses neither. The one public
              account of a section this size is the student quoted above, describing a new
              elective with four on the register and eight on the first day.
            </p>
          </NotShown>
        </>
      ) : null}

      {/* --------------------------------------------- 3. THE RAW, AND WHAT IT CANNOT SAY */}
      <H2 id="schools">Which schools these are, and why the name is not the school</H2>
      <Body>
        Lunenburg reorganised its buildings twice inside this period. Reading a school
        name as a fixed thing is the single easiest way to produce a false trend here, so
        the grade span of every school in every year is taken from DESE&rsquo;s own
        enrolment-by-grade counts rather than from anything anybody wrote down.
      </Body>
      <TableTwin caption="Every Lunenburg school, every year, as the state counted it"
        head={['Year', 'Schools, with the grades each held and its enrolment']}
        rows={d.configurations.map(c => [
          syLong(c.sy),
          c.schools.map(s => `${s.name} (${s.span}, ${n0(s.students)})`).join(' · '),
        ])} />

      <H2 id="eras">The five eras, and where their boundaries come from</H2>
      <Body>
        Three of the boundaries are events. Thomas C Passios closed after{' '}
        {syLong(BANDS[0].last_sy)} and every remaining school moved up one grade band,
        which put grade 8 in the high school building for four years; the new
        middle-school and high-school building opened in {syLong(g8band.last_sy + 1)} and
        the structure reset to what it had been. Both are read off DESE&rsquo;s own
        enrolment-by-grade counts, which a reader can check.{' '}
        <strong>The fourth is the pandemic, and that one is ours.</strong> Nothing in the
        class-size file marks those years; we asserted the boundary, it is marked as
        asserted wherever it appears, and a reader is free to disagree with it.
      </Body>
      <TableTwin caption="The eras, and the schools reporting in each"
        head={['Era', 'Years', 'High school grades', 'Boundary', 'Schools reporting']}
        rows={BANDS.map(b => [
          `${syLong(b.first_sy)}–${syLong(b.last_sy)}`, b.years, b.span,
          b.covid ? 'ours — the pandemic'
            : b.first_asserted || b.last_asserted ? 'one end ours, one the state’s'
              : 'DESE’s enrolment-by-grade counts',
          (b.schools ?? []).join(' · ')])}
        note={<>A boundary read off the state&rsquo;s own grade counts is a fact about
          the buildings. The pandemic boundary is a judgement, and the difference is
          printed rather than blurred.</>} />
      <TableTwin caption="Every school, its own configuration history"
        head={['School', 'Grade spans, and the years it held each']}
        rows={d.reorganisation.eras.map(e => [
          e.org,
          e.runs.map(r => `${r.span} (${syLong(r.first_sy)}–${syLong(r.last_sy)})`)
            .join(' · ')])}
        note={<><strong>Turkey Hill Middle and Turkey Hill Elementary School are two
          different schools</strong>, with different grades, different buildings and
          different codes at the state. So are Thomas C Passios and anything that came
          after it: it closed, and it did not become something else. Every row here is
          grouped on the state&rsquo;s org CODE rather than on the name, because the
          names move &mdash; one school is filed under two spellings in consecutive
          years.</>} />
      <Body>
        <strong>The reorganisation is not why the elementary records are unreadable.</strong>{' '}
        {d.reorganisation.flagged_count} school-years in this file are flagged &mdash; a
        total section count that moves more than a third in a year, or an average class
        size no school can have &mdash; and {d.reorganisation.away_from_boundary} of them
        fall in years nothing changed about the buildings. The{' '}
        {d.reorganisation.at_boundary === 1 ? 'one that does' : `${d.reorganisation.at_boundary} that do`}{' '}
        is the high school in {syLong(g8band.first_sy)}, which is grade 8 arriving and is
        a real event rather than a defect. Whatever is wrong with the elementary coding,
        the tidy explanation is not it.
      </Body>
      <TableTwin caption="The flagged school-years, against the boundaries"
        head={['School', 'Years', 'Sections', 'At a boundary']}
        rows={d.reorganisation.flagged.map(f => [
          f.org,
          f.from_sy === f.to_sy ? syLong(f.from_sy)
            : `${syLong(f.from_sy)} → ${syLong(f.to_sy)}`,
          f.from_sy === f.to_sy
            ? `${n0(f.from_sections)}, averaging ${n1(f.avg ?? 0)}`
            : `${n0(f.from_sections)} → ${n0(f.to_sections)}`,
          f.at_boundary ? 'yes' : 'no'])} />

      <H2 id="elementary">Why the two elementary schools are not on this page</H2>
      <Body>
        Their section counts swing by a factor of two between adjacent years with no
        matching change in enrolment, and{' '}
        {d.implausible.length} school-years report an average class size no primary school
        can have:{' '}
        {d.implausible.map((r, i) => (
          <span key={r.sy}>{i ? '; ' : ''}{n1(r.avg)} at {r.org} in {syLong(r.sy)}</span>
        ))}. A self-contained classroom&rsquo;s subject coding is not stable enough to
        trend, so this page does not trend it. The high school, where a section IS a
        course and where course choice actually exists, is intact in every measured year.
      </Body>
      <div className="card p-4 mt-5 max-w-2xl avoid-break"
        style={{ borderLeft: '4px solid var(--status-warning)' }}>
        <p className="text-[11px] font-semibold uppercase tracking-widest mb-1.5"
          style={{ color: 'var(--text-muted)' }}>
          One cell, rather than a sentence about instability
        </p>
        <p className="text-[14px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
          {syLong(IC.sy)}, {IC.org}, <em>{IC.subj}</em>:{' '}
          <strong>{n0(IC.sections)} sections averaging {n0(IC.avg)} students</strong>,
          against a school of {n0(IC.school_students)}. That is not a class of{' '}
          {n0(IC.avg)} children. It is what a self-contained elementary classroom looks
          like when the same children are coded into one subject row, and it is why
          nothing on this page is drawn from an elementary series.
        </p>
      </div>
      <TableTwin caption="The two schools this page will not trend, year by year"
        head={['School', ...(notDrawable.find(x => x.stability)?.stability?.sections
          .map(x => syLong(x.sy)) ?? [])]}
        rows={notDrawable.filter(x => x.stability).flatMap(x => [
          [`${x.name} — sections`, ...x.stability!.sections.map(y => n0(y.sections))],
          [`${x.name} — students`, ...x.stability!.sections.map(y => n0(y.students))],
        ])}
        note={<><strong>This is the evidence for the exclusion rather than an assertion
          of it.</strong> A school is drawn on this page if its total section count never
          moves more than {pct1(notDrawable[0]?.stability?.bound ?? 0)} in a year. The
          two that are drawn move at most{' '}
          {drawable.map(s0 => pct1(s0.stability!.swing)).join(' and ')}; these two move{' '}
          {notDrawable.filter(x => x.stability).map(x => pct1(x.stability!.swing)).join(' and ')},
          in years their own enrolment moved{' '}
          {notDrawable.filter(x => x.stability)
            .map(x => pct1(x.stability!.students_swing)).join(' and ')}. The bound sits
          in the gap between the two clusters, and the generator refuses to write if that
          gap closes.</>} />

      <SectionsOverTime points={d.district} eras={d.eras} keep={KEEP} />
      <Caption>
        The DISTRICT total, {d.district.length} school years &mdash; every school added
        together, which is the series this page does not read. The swings are the
        elementary schools: {syLong(d.implausible[0].sy)} and{' '}
        {syLong(d.implausible[d.implausible.length - 1].sy)} are the two years above,
        and the years either side of them move by more than any enrolment change can
        account for. The shaded band is the four years the high school held a different
        grade span, which is a second reason nothing here may be read as one line.
      </Caption>
      <TableTwin caption="The district and each school, sections that ran"
        head={['Year', 'District', 'Lunenburg High', 'Lunenburg Middle School',
               'District students']}
        rows={d.district.map(p => {
          const hs = d.high_school.find(x => x.sy === p.sy)
          const ms = d.middle.find(x => x.sy === p.sy)
          return [syLong(p.sy), n0(p.sections), hs ? n0(hs.sections) : '—',
                  ms ? n0(ms.sections) : '—', n0(p.students)]
        })}
        note={<>The district row is a ROLLUP of its schools and is never summed with them.
          It equals the sum of the schools in every year but{' '}
          {d.rollups.district_residual.map(r => syLong(r.sy)).join(', ')}, where it
          exceeds them by{' '}
          {d.rollups.district_residual.map(r => n0(r.sections)).join(', ')} sections
          &mdash; classes the file records for the district and attributes to no school.
          Both rollups on this page, the district over its schools and the total subject
          over its {d.rollups.cells} cells, are recomputed on every build and the
          generator refuses to write if either stops holding.</>} />

      <H2 id="curriculum">What a parent can look up, which is a different question</H2>
      <Body>
        Lunenburg files a curriculum return with DESE: {n0(d.curriculum.rows)} rows, eight
        subjects by grade, with the published curriculum product named against each.{' '}
        <strong>{n0(d.curriculum.with_product)} of those rows name one</strong> &mdash;
        {' '}{d.curriculum.reported_subjects.join(' and ')} in the middle grades, and{' '}
        {d.curriculum.products.join(', ')} are the products.
      </Body>
      <TableTwin caption="The curriculum return, by subject"
        head={['Subject', 'Rows', 'Rows naming a product']}
        rows={d.curriculum.subjects.map(s => [s.subject, n0(s.rows), n0(s.with_product)])} />
      <NotShown>
        <p>
          <strong>This is a fact about REPORTING and not about provision.</strong>{' '}
          DESE&rsquo;s curriculum collection is voluntary, so a blank is a row nobody
          filled in &mdash; never a subject nobody teaches. Lunenburg plainly teaches
          science; {n0(d.curriculum.blank)} rows naming no product does not say otherwise
          and this page does not suggest it. What the count bounds is what a parent
          choosing a school, or a resident checking what a budget buys, can look up
          without asking anybody.
        </p>
      </NotShown>

      <H2 id="searched">What the town said about this, and how much of the archive could
        be read</H2>
      <Coverage m={d.minutes} searched={d.searched} />
      <Body>
        Note what the counts show anyway. <strong>The most-said of these in the readable
        archive is <em>{mostSaid.term}</em>, in {n0(mostSaid.documents)} documents.</strong>{' '}
        {neverSaid.length ? <>And {neverSaid.length === 1 ? 'one term matches' : `${neverSaid.length} of them match`}{' '}
          nothing at all &mdash; {neverSaid.map(t => <em key={t.term}>{t.term}</em>)
            .reduce((a, b) => <>{a}, {b}</>)} &mdash; which includes the subject this page
          finds has run once at the high school in {cs.nine_to_twelve_years.length} years.
          That is a statement about what can be read, never about what was said.</> : null}
      </Body>

      <H2 id="differently">One thing that could be done differently next year</H2>
      <div className="card p-5 mt-6 max-w-3xl"
        style={{ borderLeft: '4px solid var(--series-cost)' }}>
        <p className="text-[15px] leading-relaxed">{d.differently}</p>
      </div>

      <H2 id="cannot">What this page cannot say</H2>
      <NotEstablished rows={d.not_established} closes={d.closes} />

      <H3>The same limits, as rows in the register</H3>
      <Body>
        Each of these is a row in <code>money-gaps.csv</code>, which is what the records
        request to the Town reads and what{' '}
        <A href={abs('/what-we-cannot-answer')}>what we cannot answer</A> renders. A limit
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
            <p className="text-[13.5px] leading-relaxed mt-2">
              <strong>Closes:</strong> {g.closes}
            </p>
          </div>
        ))}
      </div>

      <H2 id="source">The documents behind this</H2>
      <Provenance sources={d.sources} />
      <Body>
        The payload this page draws is published whole at{' '}
        <A href={abs(DATA)}>{DATA}</A>, and the rows behind it &mdash;{' '}
        <code>dese_class_size</code>, <code>dese_teacher_subject</code> and{' '}
        <code>dese_enrollment</code> &mdash; can be queried directly from{' '}
        <A href={abs('/database')}>the database</A>. Every figure here is recomputed from
        the extracted CSV by a second route in{' '}
        <code>scripts/verify_course_offerings.py</code>.
      </Body>

      <MoreReports here={TAB} />
    </Shell>
  )
}

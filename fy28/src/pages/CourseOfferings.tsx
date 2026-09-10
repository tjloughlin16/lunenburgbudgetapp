import type { Tab } from '../routes'
import { useEffect, useState } from 'react'
import { abs } from '../lib/abs'
import { Basis } from '../components/Basis'
import {
  Caption, FULL, Legend, RAN, RanAgainstFull, SectionsOverTime, SubjectChange,
  SubjectDetail, TableTwin, n0, n1, pct1, signed, syLong,
  type Era, type Point, type Subject,
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
  const BD = d.fte.biggest_disagreement
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

      <H2 id="mechanism">How a course stops running, in the district&rsquo;s own words</H2>
      <Body>
        <strong>This is above the charts rather than below them because it changes what
        they mean.</strong> A section that did not run may be a section nobody chose
        rather than a section anybody cut, and the person who builds the schedule has said
        so in public. Nothing measured on this page separates the two. What the record
        also holds, in the same paragraph, is the school choosing what to ADD.
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
          students chose. The district&rsquo;s own account of that mechanism is above the
          chart on purpose, so it is read before the chart rather than after it.
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

      <H2 id="fte">Sections against teacher FTE &mdash; two instruments, one question</H2>
      <Body>
        <A href={abs('/school-staffing')}>School staffing</A> measures the same schools
        with a different instrument: full-time equivalents the state publishes by subject.
        That measure has carried the argument about course offerings in this town for
        years, and the useful question is whether it was pointing the right way. Over the
        years both files cover &mdash; {syLong(d.fte.first_sy)} to{' '}
        {syLong(d.fte.last_sy)}, district-wide &mdash; the two move the same way in{' '}
        {n0(d.fte.agree)} of {n0(d.fte.compared)} subjects.
      </Body>
      <TableTwin caption="Teacher FTE and sections, district-wide"
        head={['Subject', `FTE ${syLong(d.fte.first_sy)}`, `FTE ${syLong(d.fte.last_sy)}`,
               'Change', `Sections ${syLong(d.fte.first_sy)}`,
               `Sections ${syLong(d.fte.last_sy)}`, 'Change', 'Same direction']}
        rows={d.fte.subjects.map(s => [
          s.subj, n1(s.fte_first), n1(s.fte_last),
          (s.fte_change > 0 ? '+' : s.fte_change < 0 ? '−' : '') + n1(Math.abs(s.fte_change)),
          n0(s.sections_first), n0(s.sections_last), signed(s.sections_change),
          s.agrees ? 'yes' : 'no'])}
        note={<><strong>{BD.subj} is the disagreement worth reading</strong>
          {BD.is_largest_line ? <>, and it is the largest line in the comparison</> : null}:
          its teacher FTE fell {n1(Math.abs(BD.fte_change))} while its sections rose by{' '}
          {n0(BD.sections_change)} and its average class went from {n1(BD.first_avg)}{' '}
          students to {n1(BD.last_avg)}. Fewer teachers, more classes, smaller ones
          &mdash; all three at once, and a page carrying only the FTE would have reported
          a subject contracting. The other is{' '}
          {d.fte.disagreeing.filter(x => x !== BD.subj).join(' and ')}, which moves by a
          fraction of a post. DESE uses one subject vocabulary for both files, so this is
          a join on the publisher&rsquo;s own names rather than on ours; the generator
          refuses to write unless every compared subject is present in both.</>} />

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

import type { Tab } from '../routes'
import { abs } from '../lib/abs'
import type { Base } from '../components/report'
import {
  Body, Conclusions, Coverage, Grain, H2, H3, Insight, MoreReports, NotEstablished,
  NotShown, Provenance, Quote, Shell, Stat, useReport,
} from '../components/report'
import type { Tier } from '../components/ClassSizeTable'
import { Clause, ScenarioTable, TableTwin } from '../components/ClassSizeTable'

const TAB: Tab = 'classsize'

/** THE CLASS-SIZE RULE: a page that quotes a STATUTE rather than measuring this town,
 *  which is a different grain from every other report in this area and is why it sits in
 *  a section of its own on /reports.
 *
 *  WHY IT EXISTS. Residents argue about paraprofessional staffing constantly, and the
 *  rule the argument is actually about was in nobody's published record for Lunenburg
 *  until 603 CMR 28.00 was ingested. Not one searchable document in the meeting archive
 *  contains the phrase "603 CMR" or "substantially separate" -- the page COMPUTES both
 *  counts and the denominator beside them rather than stating any of the three, because
 *  a zero typed into a sentence is the one thing here that can be silently wrong. So this
 *  is not a finding about the district; it is the rule everybody is arguing around, put
 *  somewhere they can read it.
 *
 *  THE ONE THING THIS PAGE MUST NOT DO, and every design decision here follows from it:
 *  IT MUST NOT COMPUTE A REQUIRED NUMBER OF PARAPROFESSIONALS FOR LUNENBURG. The
 *  regulation binds INSTRUCTIONAL GROUPS. Nothing published says how many groups this
 *  district runs, how large each is, or how its substantially separate students are
 *  divided among them -- and the same count of children is lawful at very different
 *  staffing levels depending on the answer. That limit is a registered row in
 *  money-gaps.csv and the page quotes the row rather than paraphrasing it, because rule
 *  7c says the registry outranks the page. `verify_sped_regulation.py` asserts that the
 *  payload contains none of the phrasings such a claim would take.
 *
 *  RULE 8. This is not a compliance audit and must not read as one. Nothing here
 *  establishes that Lunenburg is over- or under-staffed, and the page says so in those
 *  words rather than leaving a reader to infer it.
 *
 *  RULE 7. The regulation is a statutory fact. Every sentence about what Lunenburg does
 *  with it is a separate claim needing separate evidence, and there is a heading between
 *  the two so a reader can see where one stops.
 *
 *  RULE 2. Not one figure is typed into this file -- not a group size, not a threshold,
 *  not a count. Every one arrives from sped-regulation.json, which parsed it out of the
 *  sentence in the regulation that states it. This is a page people will quote at
 *  meetings, and a class-size number nothing recomputes is the worst thing this site
 *  could publish. */

type Clause = { cite: string; title: string; text: string }

type Payload = Base & {
  fy: number
  clauses: Record<string, Clause>
  tiers: Tier[]
  young: Tier[]
  midyear_extra: number
  age_months: number
  threshold_pct: number
  sub_cap: number
  sub_aide_cap: number
  part_cap: number
  codes: { code: string; label: string; definition: string; element: string }[]
  code_ages: { this: string; other: string }
  code_values: { code: string; description: string }[]
  placement: {
    fy: number; total: number; named: number; unnamed: number
    rows: { label: string; count: number; pct: number }[]
    sub: { label: string; count: number; pct: number }
  }
  gap: { side: string; what: string; why: string }
  gaps_also: { side: string; what: string; why: string }[]
}

const L = (href: string, t: string) => (
  <a className="underline" style={{ color: 'var(--series-cost)' }} href={abs(href)}>{t}</a>
)

export function ClassSize() {
  const { d, err } = useReport<Payload>('sped-regulation.json')
  const title = 'How many students one special education group may have'
  if (!d) return <Shell tab={TAB} title={title} err={err} loading={!err} />

  const cl = d.clauses
  const subDef = d.codes.find(c => c.code === '40')
  const topTier = d.tiers.reduce((a, b) => (b.aides > a.aides ? b : a))
  // DESE's own screen-reader expansion of `CMR`, present in some clauses and not others.
  // Detected rather than assumed, so the note explaining it disappears if DESE stops.
  const expanded = Object.values(cl).some(
    c => c.text.includes('Code of Massachusetts Regulations'))
  const found = (term: string) => d.searched.find(s => s.term === term)
  const silent = d.searched.filter(s => s.documents === 0).map(s => s.term)

  return (
    <Shell tab={TAB} title={title} dataUrl="/data/sped-regulation.json"
      standfirst={`The state sets it: ${d.sub_cap} to one certified special educator in a substantially separate setting, ${d.sub_aide_cap} with an aide. Here is the rule, and here is what it cannot tell you about Lunenburg.`}>

      {/* THE RATIO FIRST. Rule 7a: this is what people are asking for, so nothing stands
          in front of it -- not the caveats, not the method, not an explanation of how the
          page is organised. The qualifications are real and they come next. */}
      <div className="flex flex-wrap gap-x-12 gap-y-6 mt-8">
        <Stat value={`${d.sub_cap} to 1`} tone="var(--fund-school)">
          students to one certified special educator, substantially separate
          ({cl['28.06(6)(d)'].cite})
        </Stat>
        <Stat value={`${d.sub_aide_cap} to 1`} tone="var(--series-cost)">
          with a certified special educator <em>and an aide</em> &mdash; same clause
        </Stat>
        <Stat value={`${d.part_cap} to 1`}>
          the highest the rule ever goes, and only where the group is outside general
          education {d.threshold_pct}% of the schedule or less
        </Stat>
      </div>

      <Grain>
        <strong>This is not a general class-size rule.</strong>{' '}
        {cl['28.06(6)'].cite} opens by naming what it governs: eligible students aged five
        and older receiving special education services outside the general education
        environment. A general education classroom is not a group it speaks to.{' '}
        <strong>And it binds an instructional GROUP</strong>, while everything DESE
        publishes about Lunenburg counts <strong>children</strong>. Nothing joins the two,
        which is why this page stops where it does &mdash; and nothing on it is a
        compliance finding about anybody.
      </Grain>

      {/* ------------------------------------------------ 1. CONCLUSIONS (rule 7b) */}
      <H2 id="conclusions">If you read nothing else</H2>
      <Conclusions rows={d.conclusions} />

      {/* ------------------------------------------- 2. THE RULE, AS A TABLE (rule 7b) */}
      <H2 id="table">What the rule permits, group by group</H2>
      <Body>
        Every tier the regulation names, for students aged five and older. Read the two
        staff columns before the student column: the certified special educator is{' '}
        <strong>one, in every single row</strong>. What buys a larger group is an aide.
      </Body>
      <ScenarioTable rows={d.tiers}
        caption="603 CMR 28.06(6)(c) and (d), parsed from the sentences that state them" />
      <Body>
        The two settings are not the same rule, and the difference runs the way most
        people do not expect. A group outside general education{' '}
        {d.threshold_pct}% of the schedule <em>or less</em> reaches {d.part_cap} students
        with {topTier.aides} aides. A substantially separate group &mdash; <em>more</em>
        than{' '}
        {d.threshold_pct}% &mdash; stops at {d.sub_aide_cap}. The more separate the room,
        the lower the ceiling.
      </Body>
      <Clause {...cl['28.06(6)(c)']} />
      <Clause {...cl['28.06(6)(d)']} />

      <H2 id="qualifications">What travels with those numbers</H2>
      <div className="grid gap-4 mt-5 md:grid-cols-2">
        <Insight n={1} headline="They are maximums, and smaller is expected">
          The same clause that sets the sizes says districts are &ldquo;expected to
          exercise judgment in determining appropriate group size and supports for smaller
          instructional groups serving students with complex special needs&rdquo;. A group
          at the maximum is the ceiling, not the standard.
        </Insight>
        <Insight n={2} headline="An IEP can require smaller, or one-to-one, regardless">
          {cl['28.06(6)(b)'].cite} requires the size and composition of a grouping to be
          compatible with the methods and goals in each student&rsquo;s own plan. No
          class-size rule predicts a plan that calls for one-to-one support, and nothing
          in the tiers above overrides one.
        </Insight>
        <Insight n={3} headline={`A group at maximum may take ${d.midyear_extra} more, mid-year, by decision`}>
          {cl['28.06(6)(e)'].cite}, and it carries conditions: the additional students
          must have compatible instructional needs and then be able to receive services in
          their neighbourhood school; the Administrator of Special Education must notify
          the Department <em>and the parents of every member of the group</em> in writing,
          with reasons; the increase lasts only for the year it starts in; and the district
          must take all steps necessary to bring the group back within the sizes for later
          years.
        </Insight>
        <Insight n={4} headline={`No group may span more than ${d.age_months} months of age`}>
          {cl['28.06(6)(f)'].cite}. This is a real constraint on reaching the sizes above:
          a district cannot combine children into one group of {d.sub_aide_cap} simply
          because the total permits it. A wider range may be approved on written request to
          the Department.
        </Insight>
      </div>
      <Clause {...cl['28.06(6)(b)']} />
      <Clause {...cl['28.06(6)(e)']} />
      {expanded && (
        <p className="text-[12.5px] leading-relaxed max-w-2xl mt-3"
          style={{ color: 'var(--text-muted)' }}>
          The clauses above are quoted exactly as DESE publishes them, which is why some
          read &ldquo;603 <span className="italic">Code of Massachusetts Regulations</span>{' '}
          CMR&rdquo;. That expansion is in DESE&rsquo;s own page, in a span its markup
          hides from sighted readers and reads aloud to screen readers. Tidying it here
          would be this site quoting its rendering of the regulation instead of the
          regulation.
        </p>
      )}
      <NotShown>
        What an <strong>aide</strong> is. The regulation uses the word and never defines
        it. {cl['28.02(3)'].cite} defines the certified special educator, in full, and
        there is no matching definition of the other. The word{' '}
        <em>paraprofessional</em> appears in 603 CMR 28.00 only in the staff-training
        clauses, one of which names &ldquo;teachers, paraprofessionals, and teacher
        assistants&rdquo; as three separate things. DESE&rsquo;s staffing files and the
        district&rsquo;s budget lines say paraprofessional. Those are the words two
        different documents use, and nothing here establishes that they name the same job.
      </NotShown>
      <Clause {...cl['28.02(3)']} />
      <Clause {...cl['28.03(1)(a)']} />

      <H2 id="young">Young children are a different rule again</H2>
      <Body>
        Three- and four-year-olds are governed by {cl['28.06(7)(e)'].cite} and{' '}
        {cl['28.06(7)(f)'].cite}, which set class sizes rather than group sizes and say{' '}
        <em>teacher</em> where the clauses above say <em>certified special educator</em>.
        The rows are printed as the regulation words them and are not folded into the
        table above.
      </Body>
      <TableTwin
        caption="603 CMR 28.06(7)(e) and (f)"
        head={['the setting', 'class size, at most', 'students with disabilities, at most',
          'the staff the clause names', 'where it says so']}
        rows={d.young.map(y => [y.setting, y.students,
          y.swd_cap == null ? '\u2014 (the clause states a floor, not a cap)' : y.swd_cap,
          y.staff, y.cite])} />
      <Clause {...cl['28.06(7)(e)']} />
      <Clause {...cl['28.06(7)(f)']} />
      <NotShown>
        A cap on students with disabilities in the substantially separate preschool row.
        {' '}{cl['28.06(7)(f)'].cite} runs the other way: it defines such a programme as
        one in which more than half the children have disabilities, and caps the class
        rather than that share. Writing a number in that column would be this page
        inverting a floor into a ceiling.
      </NotShown>

      <H2 id="approved">And a school the district places a child into</H2>
      <Body>
        A programme approved by the Department under 603 CMR 28.09 does not get its own
        sizes: {cl['28.06(6)(g)'].cite} holds it to the substantially separate tiers, and{' '}
        {cl['28.09(7)(e)'].cite} says the same thing from the approval side, adding that
        the Department may impose tighter limits where the population requires more
        specialised services.
      </Body>
      <Clause {...cl['28.06(6)(g)']} />
      <Clause {...cl['28.09(7)(e)']} />

      {/* ---------------------------------- 3. LUNENBURG'S OWN COUNTS, kept separate */}
      <H2 id="lunenburg">What Lunenburg publishes beside it</H2>
      <Body>
        Everything above is the state&rsquo;s rule and applies to every district. This
        section is the town&rsquo;s own published counts, and the heading is here so that
        the line between the two is visible rather than inferred.
      </Body>
      <TableTwin
        caption={`DESE’s placement breakdown for Lunenburg, FY${d.placement.fy}`}
        head={['placement DESE reports', 'children', 'share of all students with disabilities']}
        rows={[
          ...d.placement.rows.map(r => [r.label, r.count, `${r.pct.toFixed(1)}%`]),
          ['In none of the four printed categories', d.placement.unnamed,
            `${(100 * d.placement.unnamed / d.placement.total).toFixed(1)}%`],
          ['Total students with disabilities', d.placement.total, '100.0%'],
        ]} />

      <H3>Do DESE&rsquo;s labels mean what the regulation means?</H3>
      <Body>
        On the axis, yes, and this is the only reason the two halves of this page can be
        set beside each other at all. DESE counts placements on element{' '}
        {d.codes[0].element} of its student information return, and the handbook defines
        each value as a percentage of time outside the general education classroom &mdash;
        the same quantity {cl['28.06(6)(d)'].cite} keys on.
      </Body>
      <TableTwin
        caption="element DOE034, as DESE’s SIMS data handbook defines it"
        head={['code', 'the label DESE prints', 'what the handbook says it means']}
        rows={d.codes.map(c => [c.code, c.label, c.definition])} />
      <Body>
        So {subDef ? `“${subDef.label}”` : 'the substantially separate label'} and{' '}
        {cl['28.06(6)(d)'].cite} both turn on the same {d.threshold_pct}% threshold. That
        is where the correspondence ends.
      </Body>
      <NotShown>
        That the two count the same population, or the same kind of thing. The regulation
        governs eligible students <strong>aged five and older</strong> and puts three- and
        four-year-olds under a separate clause; {d.codes[0].element} covers ages{' '}
        {d.code_ages.this} and a different element covers ages {d.code_ages.other}. Those
        splits are not the same line. And DESE labels a{' '}
        <strong>child</strong> while the regulation binds a <strong>group</strong> &mdash;
        the difference this whole page turns on.
      </NotShown>
      <NotShown>
        That the four printed categories divide the town&rsquo;s{' '}
        {d.placement.total} students between them. They account for{' '}
        {d.placement.named}, leaving {d.placement.unnamed} in none of them. The breakdown
        is in-district only: {d.codes[0].element} allows{' '}
        {d.code_values.length} placements and the published file prints four of them.
        Adding the four and treating the total as their sum is the mistake the row above
        exists to prevent.
      </NotShown>
      <TableTwin
        caption={`every placement ${d.codes[0].element} allows`}
        head={['code', 'what the handbook calls it',
          'named identically in the published breakdown']}
        rows={d.code_values.map(v => [v.code, v.description,
          d.placement.rows.some(r => v.description.startsWith(r.label)) ? 'yes' : '—'])} />
      <NotShown>
        Which code each of the other printed categories is. The published breakdown labels
        one row &ldquo;Separate School in District&rdquo; and the handbook has no value of
        that name; matching it to a code would be this page inferring a correspondence
        neither document states. The three marked above are marked because the two
        documents use the same words, and no further mapping is attempted.
      </NotShown>

      {/* ------------------------------------- 4. THE THING THIS PAGE REFUSES TO DO */}
      <H2 id="cannot">Why no staffing number follows from any of this</H2>
      <Body>
        This is the question everybody arrives with, and the honest answer is that the
        published record cannot carry it. The rule binds groups. Lunenburg publishes
        children. {d.placement.sub.count} children could be four groups or seven &mdash;
        needing very different staffing &mdash; and both are lawful.
      </Body>
      <div className="card p-5 mt-5 max-w-2xl avoid-break"
        style={{ borderLeft: '4px solid var(--status-warning)' }}>
        <p className="text-[11px] font-semibold uppercase tracking-widest mb-1.5"
          style={{ color: 'var(--text-muted)' }}>
          Registered gap &middot; {d.gap.side.replace(/_/g, ' ')}
        </p>
        <p className="text-[15px] font-bold leading-snug">{d.gap.what}</p>
        <p className="text-[13.5px] leading-relaxed mt-2.5"
          style={{ color: 'var(--text-secondary)' }}>{d.gap.why}</p>
        <p className="text-[12.5px] mt-3" style={{ color: 'var(--text-muted)' }}>
          One row in {L('/what-we-cannot-answer', 'what we cannot answer')}, quoted here
          rather than restated &mdash; so the page and the registry cannot drift apart.
        </p>
      </div>
      <Body>
        Writing this page found {d.gaps_also.length} more, and both are now rows in the
        same registry rather than sentences only this page carries:
      </Body>
      <ul className="mt-2 space-y-3 max-w-2xl">
        {d.gaps_also.map(g => (
          <li key={g.what} className="text-[14px] leading-relaxed pl-4 border-l-2"
            style={{ borderColor: 'var(--axis)' }}>
            <strong>{g.what}</strong>
            <span className="block mt-1" style={{ color: 'var(--text-secondary)' }}>
              {g.why}
            </span>
          </li>
        ))}
      </ul>
      <NotShown>
        Anything about whether Lunenburg is over-staffed or under-staffed. Nothing on this
        page supports either reading, and this is not an audit. The job here is to give
        the argument residents are already having a copy of the rule it is about.
      </NotShown>

      {/* ------------------------------------------------------ 5. RAW (rule 7b) */}
      <H2 id="said">What the town said about this</H2>
      <Body>
        <strong>Lunenburg does not argue in the regulation&rsquo;s words.</strong> The
        town says <em>class size</em> and <em>paras</em>; it does not say{' '}
        {silent.map((t, i) => (
          <span key={t}>{i ? ' or ' : ''}&ldquo;{t}&rdquo;</span>
        ))} &mdash; not one of those appears in a single searchable meeting document. That
        is a fact about vocabulary and not about attention: {found('class size')?.documents}{' '}
        documents discuss class size and {found('paraprofessional')?.documents} discuss
        paraprofessionals.
      </Body>
      <Coverage m={d.minutes} searched={d.searched} />
      <div className="grid gap-4 mt-5 md:grid-cols-2">
        {d.said.map(q => <Quote key={q.key} q={q} />)}
      </div>
      <NotShown>
        That any of those quotes can be read against the tiers above. Not one of them
        names an instructional group, a setting, or a percentage of a school schedule
        &mdash; and the kindergarten figure is a general education classroom, which{' '}
        {cl['28.06(6)'].cite} does not govern at all. They are here because they are the
        argument this page is trying to give better inputs to.
      </NotShown>
      <NotShown>
        <strong>That the pull-out account above describes a breach of anything.</strong>{' '}
        {cl['28.02(3)'].cite}, printed earlier on this page, says a certified special
        educator may provide, design <em>or supervise</em> special education services
        &mdash; so a service delivered by somebody the educator supervises is contemplated
        by the regulation rather than excluded by it. What is established is that a
        teacher said this at a public meeting. Nothing published says how many students
        district-wide, which posts, or what supervision was in place, and this page makes
        no finding about any of it.
      </NotShown>

      <H2 id="sources">The documents</H2>
      <Provenance sources={d.sources} />

      <H2 id="limits">What this report cannot answer</H2>
      <NotEstablished rows={d.not_established} closes={d.closes} />

      <H2 id="other">The other reports</H2>
      <MoreReports here={TAB} />
    </Shell>
  )
}

import type { Tab } from '../routes'
import { abs } from '../lib/abs'
import { useEffect, useState } from 'react'
import { usd } from '../model/engine'
import {
  PeerRatio, IndexedPair, TableTwin, ParaSplit,
  fy, num, pct,
} from '../components/StaffingCharts'
import {
  longestRun, type Dollars, type Peer, type SpedStaffing, type State,
} from '../lib/staffing'
import {
  Conclusions, Coverage, Grain, NotEstablished, Provenance, MoreReports,
  Body, H2, Maybe, NotShown, Stat,
  ReportShell,
} from '../components/report'
import type { Base, Conclusion } from '../components/report'

const TAB: Tab = 'parastaff'
const DATA = '/data/the-paraprofessionals.json'
const TITLE = 'The paraprofessionals'

/** The paraprofessionals — the biggest single change in who Lunenburg's schools employ.
 *
 *  WHY THIS PAGE EXISTS. Everything else about school staffing here moves slowly or moves
 *  both ways. This one line moves in one direction and further than anything else in the
 *  archive: Lunenburg went from the FEWEST paraprofessionals per pupil of the districts on
 *  the state's own comparison sheet to the MOST. Two DESE files that count them disagree
 *  about direction, and the district's budget for special education paraprofessionals
 *  rose while the FTE the state codes to special education more than halved.
 *
 *  THE CAVEAT THAT IS THIS PAGE'S OWN IS RULE 11. A budget line is NET — what the town has
 *  to raise after grants, circuit breaker reimbursement, fees and revolving funds have
 *  paid their share. So a line rising because a grant that had been paying for these
 *  people ENDED looks identical, on the page, to a line rising because the district added
 *  staff. That is not a footnote here: this project's own in-district special education
 *  escalator is built on this line.
 *
 *  AND THE TWO QUANTITIES ARE NEVER DIVIDED. Dollars over FTE looks like a cost per
 *  employee and is not one, twice over: the numerator excludes every fund but the general
 *  fund, and the denominator counts the staff those other funds pay for.
 *
 *  RULE 2. Not one figure is typed into this file.
 *
 *  NO D1 AT PAGE LOAD. One static file. */

type Payload = Base & {
  conclusions: Conclusion[]
  generated_by: string
  source: string
  dollars: Dollars
  sped_staffing: SpedStaffing
  state: State
  peers: Peer[]
}

export function TheParaprofessionals() {
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
  const lastPara = st.ranks.paras[st.ranks.paras.length - 1]
  const worstParaRank = longestRun(st.ranks.paras, r => r.rank === r.of)
  const topPara = [...st.ranks.paras].sort((a, b) => b.value - a.value)[0]
  const lowPara = [...st.ranks.paras].sort((a, b) => a.value - b.value)[0]
  const paraFte = st.change_over_roster_years.para_fte!

  const paraPanel = d.dollars.panels.find(p => p.key === 'sped_para')!
  const teachPanel = d.dollars.panels.find(p => p.key === 'sped_teacher')!
  const cw = d.dollars.sped_common_window
  const cwPara = cw.panels.find(p => p.key === 'sped_para')!
  const cwTeach = cw.panels.find(p => p.key === 'sped_teacher')!
  const otherPanels = d.dollars.panels.filter(p => !p.key.startsWith('sped_'))
  const recon = d.dollars.reconciled[0]
  const negCell = recon?.disagree[0]

  const sp = d.sped_staffing

  return (
    <ReportShell tab={TAB} dataUrl={DATA}
      title={<>
        Fewest paraprofessionals per pupil in the group, then the most.
      </>}
      standfirst={<>
        {num(lowPara.value, 2)} per hundred in-district pupils in {fy(lowPara.fy)},{' '}
        {num(topPara.value, 2)} in {fy(topPara.fy)} &mdash; the largest move any staffing
        line in this archive makes.
      </>}
    >

      <Grain>{d.grain}</Grain>

      <div className="mt-10 flex flex-wrap gap-x-12 gap-y-6">
        <Stat value={`${num(lastPara.value, 2)} per 100`} tone="var(--series-revenue)">
          paraprofessional FTE for every hundred in-district pupils in{' '}
          {fy(lastPara.fy)} &mdash; the
          {lastPara.rank === 1 ? ' highest' : ` ${lastPara.rank}th highest`} of the{' '}
          {lastPara.of} districts on DESE&rsquo;s own comparison sheet
        </Stat>
        <Stat value={pct(paraFte.pct!)} tone="var(--series-revenue)">
          paraprofessional FTE, {fy(paraFte.first_fy)}&ndash;{fy(paraFte.last_fy)} &mdash;
          from {num(paraFte.first, 1)} posts to {num(paraFte.last, 1)}
        </Stat>
        <Stat value={`${num(sp.implied.change, 1)} FTE`} tone="var(--series-revenue)">
          of paraprofessional post the state does <em>not</em> code to special education,
          added between {fy(sp.first_fy)} and {fy(sp.last_fy)}
        </Stat>
        <Stat value={`${num(sp.special_education.last, 1)} FTE`} tone="var(--series-cost)">
          of paraprofessional post coded to special education in {fy(sp.last_fy)}, down
          from {num(sp.special_education.first, 1)} in {fy(sp.first_fy)}
        </Stat>
        <Stat value={pct(cwPara.change!.pct!)} tone="var(--series-revenue)">
          special education paraprofessional <em>spending</em>,{' '}
          {fy(cw.first_fy)}&ndash;{fy(cw.last_fy)}, against {pct(cwTeach.change!.pct!)} for
          special education teachers over the same years
        </Stat>
      </div>

      <H2 id="conclusions">If you read nothing else</H2>
      <Conclusions rows={d.conclusions} />

      {/* ================================================== 1. the paraprofessional shift */}
      <H2 id="paras">Lunenburg went from the fewest paraprofessionals per pupil to the most</H2>
      <Body>
        DESE publishes paraprofessional FTE for Lunenburg and for every district on its own
        comparison sheet. In {fy(lowPara.fy)} Lunenburg reported {num(lowPara.value, 2)} per
        100 in-district pupils &mdash; the lowest of the {lowPara.of}, and below every one of
        them. It was last of {worstParaRank[0]?.of} for{' '}
        {worstParaRank.length} straight years, {fy(worstParaRank[0]?.fy)} to{' '}
        {fy(worstParaRank[worstParaRank.length - 1]?.fy)}. In {fy(topPara.fy)} it reported{' '}
        {num(topPara.value, 2)}, the highest of the group.
      </Body>
      <Body>
        <strong>The V is Lunenburg&rsquo;s alone.</strong> No comparison district falls
        below {num(Math.min(...d.peers.filter(p => !p.is_lunenburg)
          .flatMap(p => p.points.map(q => q.paras_per_100).filter((v): v is number => v !== null))), 2)}{' '}
        in any year of the series. That rules out a change in how the state counts
        paraprofessionals, which would have moved every district at once. It does not rule
        out a change in how Lunenburg reports them.
      </Body>
      <div className="mt-6"><PeerRatio peers={d.peers} field="paras_per_100"
        unit="Paraprofessional FTE per 100 in-district pupils" subject="Lunenburg" /></div>
      <TableTwin caption="Lunenburg, per year"
        head={['Year', 'Para FTE', 'Per 100 pupils', 'Rank', 'Highest in group']}
        rows={st.ranks.paras.map(r => {
          const p = st.points.find(q => q.fy === r.fy)!
          return [fy(r.fy), num(p.para_fte, 1), num(r.value, 2),
            `${r.rank} of ${r.of}`, `${r.highest} ${num(r.highest_value, 2)}`]
        })} />

      <NotShown>
        <p>
          <strong>Whether any of this is about children.</strong> An FTE count is staff. It
          is not a count of students with disabilities, of one-to-one assignments, or of
          hours delivered. Two districts with the same ratio can be doing entirely
          different things.
        </p>
        <p className="mt-2.5">
          <strong>Who pays.</strong> DESE&rsquo;s FTE count includes staff paid from grants,
          circuit breaker reimbursement and revolving funds. The town&rsquo;s budget lines
          do not. So the FTE series and the dollar series below are not two views of one
          number and must not be divided into each other.
        </p>
        <p className="mt-2.5">
          <strong>That the trough is real.</strong> {fy(st.trough.fy)}&rsquo;s{' '}
          {num(st.trough.para_fte, 1)} FTE is what the state published. Whether Lunenburg
          employed that few paraprofessionals, or classified them somewhere else that year,
          is not decidable from this sheet.
        </p>
      </NotShown>

      <Maybe settle={<>
        DESE&rsquo;s staffing report broken out by funding source, and the district&rsquo;s
        End of Year Financial Report, which separates spending by fund. Both would say
        whether the rise is posts added or grant-funded posts moving onto the general fund.
        Neither is currently in this archive.
      </>}>
        <p>
          A district that cuts paraprofessional posts in a hard budget year and rebuilds
          them afterwards would produce exactly this shape. So would a district that kept
          the same people and changed which fund or which category they were reported
          under. So would one whose special education population changed. The three fit the
          same seventeen numbers equally well, and this series cannot separate them.
        </p>
      </Maybe>

      {/* ================================================== general ed vs special ed */}
      <H2 id="gen-ed-sped">
        General education and special education &mdash; the paraprofessional count splits
      </H2>
      <Body>
        Two of the state&rsquo;s files count Lunenburg&rsquo;s paraprofessionals over{' '}
        {fy(sp.first_fy)}&ndash;{fy(sp.last_fy)}, and they move in opposite directions. All
        programmes: {num(sp.all_programmes.first, 1)} full-time equivalents to{' '}
        {num(sp.all_programmes.last, 1)}. Coded to special education:{' '}
        {num(sp.special_education.first, 1)} to {num(sp.special_education.last, 1)} &mdash;
        falling at every one of the {sp.special_education.steps} year-steps, over a group of
        children that went from {sp.swd.first.toLocaleString()} to{' '}
        {sp.swd.last.toLocaleString()}.
      </Body>
      <div className="mt-6"><ParaSplit rows={sp.rows} /></div>
      <Body>
        <strong>And here is the thing this page has to say out loud, because it holds both
        halves.</strong> Over almost exactly these years the district&rsquo;s{' '}
        <em>budget</em> for special education paraprofessionals rose{' '}
        {pct(cwPara.change!.pct!)} &mdash; that section is further down this page &mdash;
        while the paraprofessional FTE the state codes to special education more than
        halved. Those two facts are not in contradiction and they are also not divisible:
        the budget line is a net general-fund appropriation and the FTE is a state coding
        of assignments, so dividing one by the other would produce a cost per employee that
        is wrong twice over. What can be said is that the money and the coded staffing move
        in opposite directions, and that nothing published says why.
      </Body>
      <TableTwin caption="Both counts, and the difference between them"
        head={['Year', 'All programmes (FTE)', 'Special education (FTE)',
          'The difference', 'Children on a plan']}
        rows={sp.rows.map(r => [fy(r.fy), num(r.all_programmes, 1),
          num(r.special_education, 1), num(r.implied, 1),
          r.swd === null ? '—' : r.swd.toLocaleString()])} />

      <NotShown>
        <p>
          <strong>That anybody was reassigned.</strong> {sp.two_files.warning} A district
          moving paraprofessionals onto general education assignments, the same people
          being recoded, and DESE changing what its special education staff table counts
          all produce this shape, and this archive cannot separate them.
        </p>
        <p className="mt-2.5">
          <strong>Whether the teaching side split the same way.</strong> It cannot be read
          here. DESE&rsquo;s programme-area file reports a fall in Lunenburg&rsquo;s
          special education TEACHER FTE that no staffing decision produces, while the
          district total holds flat. That is a{' '}
          <a className="underline" style={{ color: 'var(--series-cost)' }}
            href={abs('/what-we-cannot-answer')}>registered gap</a> rather than a finding,
          and it is drawn &mdash; rather than hidden &mdash; on{' '}
          <a className="underline" style={{ color: 'var(--series-cost)' }}
            href={abs('/who-works-in-each-school')}>who works in each school</a>, beside
          the other two ways the state splits teaching posts.
        </p>
        <p className="mt-2.5">
          <strong>Who pays for any of them.</strong> Rule of this whole page: DESE counts
          staff on grants, circuit breaker reimbursement and revolving funds exactly like
          staff the town appropriates, and the budget line the town votes is net of all of
          them. A line rising because a grant ended looks identical to a line rising
          because the district grew &mdash; and the district&rsquo;s own special education
          paraprofessional line is what this project&rsquo;s in-district escalator rests
          on.
        </p>
      </NotShown>
      {/* ================================================== 3. the dollars */}
      <H2 id="dollars">
        Inside special education, the money went to paraprofessionals, not to teachers
      </H2>
      <Body>
        Two panels of five budget lines each, read from the district&rsquo;s own documents
        at the {d.dollars.stage} stage across their whole run, over the{' '}
        {cw.last_fy - cw.first_fy + 1} years both of them cover. Special education
        paraprofessional lines moved {pct(cwPara.change!.pct!)} &mdash; from{' '}
        {usd(cwPara.change!.first)} to {usd(cwPara.change!.last)}. Special education teacher
        lines moved {pct(cwTeach.change!.pct!)}, from {usd(cwTeach.change!.first)} to{' '}
        {usd(cwTeach.change!.last)}.
      </Body>
      <div className="mt-6">
        <IndexedPair series={[
          { key: cwPara.key, label: cwPara.label, points: cwPara.points },
          { key: cwTeach.key, label: cwTeach.label, points: cwTeach.points },
        ]} />
      </div>
      <TableTwin caption={`Both panels, ${d.dollars.stage} stage, as printed`}
        head={['Year', cwPara.label, cwTeach.label]}
        rows={cwPara.points.map(p => [
          fy(p.fy), usd(p.dollars),
          usd(cwTeach.points.find(q => q.fy === p.fy)?.dollars ?? 0)])} />
      <p className="text-[12px] mt-3 max-w-2xl" style={{ color: 'var(--text-muted)' }}>
        The paraprofessional panel runs from {fy(paraPanel.first_fy)} and the teacher panel
        from {fy(teachPanel.first_fy)}; the comparison above uses only the{' '}
        {cw.last_fy - cw.first_fy + 1} years both cover. Reading a{' '}
        {paraPanel.last_fy - paraPanel.first_fy + 1}-year percentage against a{' '}
        {teachPanel.last_fy - teachPanel.first_fy + 1}-year one is the like-for-like error
        wearing a different coat.
      </p>

      <NotShown>
        <p>
          <strong>That anybody was hired.</strong> A budget line is dollars. It is not a
          post, not a person and not an hour. The line rising and the line paying more for
          the same people are the same number on the page.
        </p>
        <p className="mt-2.5">
          <strong>What special education cost.</strong> These are <em>net</em> general-fund
          lines. Circuit breaker reimbursement, IDEA grant money and revolving funds pay for
          real staff and appear in none of them, so a year where a grant ended looks
          identical to a year where the district added people.
        </p>
        <p className="mt-2.5">
          <strong>That the two panels are comparable in kind.</strong> They are two sets of
          five lines from the same workbook, which makes them comparable as budget lines. It
          does not make a paraprofessional dollar and a teacher dollar the same unit of
          anything.
        </p>
      </NotShown>

      {/* the other panels */}
      <H2 id="other-lines">Three more staffing lines, for scale</H2>
      <Body>
        The same treatment for every other staffing panel where a fixed set of lines reports
        in every year of its run. Each is read at the {d.dollars.stage} stage; none of them
        is a headcount.
      </Body>
      <div className="grid gap-2.5 mt-6 max-w-3xl">
        {[paraPanel, teachPanel, ...otherPanels].map(p => (
          <div key={p.key} className="card px-4 py-3.5">
            <div className="flex items-baseline justify-between gap-3 flex-wrap">
              <span className="text-[14.5px] font-bold">{p.label}</span>
              <span className="text-[14px] tnum font-bold"
                style={{ color: (p.change?.pct ?? 0) >= 0 ? 'var(--series-revenue)' : 'var(--series-cost)' }}>
                {pct(p.change!.pct!)}
              </span>
            </div>
            <p className="text-[12.5px] mt-1" style={{ color: 'var(--text-secondary)' }}>
              {usd(p.change!.first)} in {fy(p.change!.first_fy)} to {usd(p.change!.last)} in{' '}
              {fy(p.change!.last_fy)} &middot; {p.lines} lines &middot; from{' '}
              <code style={{ color: 'var(--text-muted)' }}>{p.source}</code>
              {p.years_dropped.length > 0 && (
                <> &middot; {p.years_dropped.length} earlier year
                  {p.years_dropped.length === 1 ? '' : 's'} dropped, because not every line
                  in the panel reports in {p.years_dropped.length === 1 ? 'it' : 'them'}
                </>
              )}
            </p>
          </div>
        ))}
      </div>

      {/* ================================================== the raw, and the defect */}
      <H2 id="quality">What is wrong with this data, stated</H2>
      <Body>
        Found by a rule in the generator rather than written down, so the figures move when
        the extraction improves instead of going quietly stale.
      </Body>

      {negCell && (
        <div className="card p-4 mt-4 max-w-2xl" style={{ borderLeft: '4px solid var(--status-bad)' }}>
          <p className="text-[14.5px] font-bold mb-1.5">
            Two extracts of the same cell disagree, in {fy(negCell.fy)}, by {usd(Math.abs(negCell.difference))}
          </p>
          <p className="text-[13.5px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
            The paraprofessional dollars can be reached two ways in this database: by summing
            the five line keys in <code>{recon.a}</code>, or by reading{' '}
            <code>{recon.b}</code>&rsquo;s own total column. They agree in {recon.agree} of{' '}
            {recon.years} years, {fy(recon.first_fy)}&ndash;{fy(recon.last_fy)}, and differ in{' '}
            {fy(negCell.fy)}: {usd(negCell.a)} against {usd(negCell.b)}. The difference is
            exactly twice that year&rsquo;s ACE line, which is what a flipped sign produces.
            The workbook itself prints a negative there &mdash; cell{' '}
            <code>sheet1!D340 = −157,886.32</code> in the FY27 projection workbook, read
            directly &mdash; so this page draws the <code>{recon.a}</code> route and reports
            the disagreement rather than choosing quietly.
          </p>
          <p className="text-[13.5px] leading-relaxed mt-2.5" style={{ color: 'var(--text-secondary)' }}>
            <strong>A negative on a salary line is itself worth knowing about.</strong> It is
            almost certainly a year-end reclassification rather than money coming back, but
            that is a guess: the document prints a figure and no explanation, and the
            {' '}{fy(negCell.fy)} paraprofessional total on the chart above is lower than the
            year&rsquo;s real spending by however much moved.
          </p>
        </div>
      )}

      {/* ------------------------------------------------ the other two staffing pages */}
      <H2 id="next">The same staff, counted two other ways</H2>
      <div className="grid gap-3 mt-5 lg:grid-cols-2">
        <a className="card px-4 py-3.5 block" href={abs('/school-staffing')}>
          <p className="text-[14.5px] font-bold">Did staffing go up?</p>
          <p className="text-[13px] mt-1" style={{ color: 'var(--text-secondary)' }}>
            Teacher FTE over a window you move yourself. The sign of that answer is a
            property of the years somebody picks, and the count of how many spans give
            each answer is on the page.
          </p>
        </a>
        <a className="card px-4 py-3.5 block" href={abs('/who-works-in-each-school')}>
          <p className="text-[14.5px] font-bold">Who works in each school</p>
          <p className="text-[13px] mt-1" style={{ color: 'var(--text-secondary)' }}>
            The names the town printed, building by building, and the one place the
            difference between a person and a post has a number attached to it.
          </p>
        </a>
      </div>

      {/* ------------------------------------------------------ rule 15a, with its denominator */}
      <H2 id="said">What the town said about this, and how much of the archive could be read</H2>
      <Body>
        Every quote used anywhere in this staffing work is re-read out of the archive on
        each build and the build refuses to write if one is no longer verbatim there. These
        are the terms searched &mdash; in the town&rsquo;s vocabulary rather than ours.
      </Body>
      <Coverage m={d.minutes} searched={d.searched} />

      <H2 id="cannot">What this page cannot say</H2>
      <NotEstablished rows={d.not_established} closes={d.closes} />

      <H2 id="documents">The documents behind this</H2>
      <Provenance sources={d.sources} />

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
          <p className="text-[14px] font-bold">The special education staff table</p>
          <p className="text-[12.5px] mt-1" style={{ color: 'var(--text-secondary)' }}>
            {sp.rows.length} years, {fy(sp.first_fy)}&ndash;{fy(sp.last_fy)}. Nothing in
            that file&rsquo;s headers says which column holds the FTE; the only thing that
            establishes it is that the printed rate reproduces from the two, which is
            recomputed on every build &mdash; {sp.reproduces.checked} rows checked,{' '}
            {sp.reproduces.failed} not published because they did not reproduce.
          </p>
        </div>
        <div className="card px-4 py-3.5">
          <p className="text-[14px] font-bold">The dollars</p>
          <p className="text-[12.5px] mt-1" style={{ color: 'var(--text-secondary)' }}>
            {d.dollars.panels.length} panels, {d.dollars.stage} stage throughout. Each panel
            is a fixed set of lines reporting in every year of its run, so a sum across years
            measures the lines and not the coverage.
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
              href={abs('/data/the-paraprofessionals.json')}>/data/the-paraprofessionals.json</a>
          </p>
        </div>
      </div>

      <div className="card p-4 mt-8 max-w-2xl" style={{ borderLeft: '4px solid var(--axis)' }}>
        <p className="text-[11px] font-semibold uppercase tracking-widest mb-1.5"
          style={{ color: 'var(--text-muted)' }}>The one number nobody publishes</p>
        <p className="text-[14px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
          Which fund pays which post. The town publishes names without FTE or funding; the
          state publishes FTE without funding; the budget publishes dollars net of every
          fund but one. Any question of the form &ldquo;did the town take on staff a grant
          used to pay for&rdquo; needs all three joined, and no document in this archive
          joins them.
        </p>
      </div>

      <MoreReports here={TAB} />
    </ReportShell>
  )
}

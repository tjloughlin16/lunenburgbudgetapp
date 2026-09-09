import { abs } from '../lib/abs'
import { usd } from '../model/engine'
import { H2, Body, ReportShell, useReport } from '../components/report'
import type { Tab } from '../routes'

const TAB: Tab = 'sped'
import { fy } from '../components/SpedCharts'

/** THE FOUR DOORS. A chooser, not a chapter.
 *
 *  WHY THIS PAGE IS FOUR DOORS AND NOT ONE ESSAY. `notes/QUEUE.md` item 10: "Four reports,
 *  not one. Keep them apart. Merging them into one narrative is how a proxy becomes a
 *  fact." An essay that introduced all four would BE that narrative — the reader would
 *  arrive at the cost figure holding the student count, and dividing one by the other is
 *  the single most likely wrong thing anybody will do with this material.
 *
 *  So this page carries one number per door, each labelled with the unit it is in, and the
 *  note explaining why they do not combine sits BELOW the doors rather than above them —
 *  rule 7a: the thing first, the key to it after.
 *
 *  RULE 2. The four figures are read from the four payloads, not typed. If a payload is
 *  missing its door still renders, with no number rather than a stale one. */

type Students = { last: { fy: number; swd: number; share_pct: number } }
type Leaving = {
  fy_first: number
  last: { fy: number; elsewhere: number; elsewhere_pct: number }
}
type Cost = {
  cb_first: { fy: number }; cb_last: { fy: number }
  last: { fy: number; total: number; gen_fund: number }
}
type Route = {
  counts: { fy: number }[]
  pooled: { start: string; cohort: number; out_of_district: number; ood_pct: number }[]
}

function Door({ href, name, unit, figure, caption, children }: {
  href: string; name: string; unit: string; figure?: string; caption?: string
  children: React.ReactNode
}) {
  return (
    <a href={abs(href)} className="card block p-5 min-h-[44px] transition-opacity hover:opacity-90">
      <span className="block text-[11px] font-semibold uppercase tracking-widest"
        style={{ color: 'var(--text-muted)' }}>counts {unit}</span>
      <span className="block text-[18px] font-bold leading-snug mt-1.5"
        style={{ color: 'var(--series-cost)' }}>{name} &rarr;</span>
      {figure && (
        <span className="block text-3xl font-bold tracking-tight tnum mt-3">{figure}</span>
      )}
      {caption && (
        <span className="block text-[12.5px] leading-snug mt-1"
          style={{ color: 'var(--text-muted)' }}>{caption}</span>
      )}
      <span className="block text-[13.5px] leading-relaxed mt-3"
        style={{ color: 'var(--text-secondary)' }}>{children}</span>
    </a>
  )
}

export function SpecialEducationHub() {
  const s = useReport<Students>('sped-students.json').d
  const l = useReport<Leaving>('sped-leaving.json').d
  const c = useReport<Cost>('sped-cost.json').d
  const r = useReport<Route>('sped-route.json').d
  const sub = r?.pooled.find(p => /Separate/.test(p.start))

  return (
    <ReportShell tab={TAB} title="Special education"
      standfirst={<>
        Four questions. Three of them have an answer in this archive, the fourth has
        none &mdash; and they do not combine with each other.
      </>}
    >

      <div className="grid gap-4 mt-8 md:grid-cols-2">
        <Door href="/how-many-students-are-on-an-iep" unit="children"
          name="How many students are on an IEP"
          figure={s ? String(s.last.swd) : undefined}
          caption={s ? `${fy(s.last.fy)} · ${s.last.share_pct.toFixed(1)}% of enrollment` : undefined}>
          The count the state publishes, in district and out, with the one staffing figure
          in DESE&rsquo;s file that reproduces from its own arithmetic &mdash; and the two
          that do not.
        </Door>
        <Door href="/where-students-go-instead" unit="children — with no disability flag"
          name="Do children with an IEP leave at a different rate"
          figure="no"
          caption="DESE publishes no disability status with the enrollment it publishes">
          The count of children who leave exists, is measured, and is a{' '}
          <strong>general</strong> figure &mdash; {l ? l.last.elsewhere : 'every one'} of
          Lunenburg&rsquo;s resident children are educated by another district, and DESE
          does not say which of them has a plan. So the special education version of this
          question has no answer here at all. The measurement itself is a report of its
          own, outside these four, because merged into a special education narrative
          &ldquo;{l ? l.last.elsewhere : ''} children left&rdquo; becomes &ldquo;
          {l ? l.last.elsewhere : ''} special education children left&rdquo; in one
          retelling.
        </Door>
        <Door href="/what-special-education-costs" unit="dollars"
          name="What it costs, and what comes back"
          figure={c ? usd(c.last.total) : undefined}
          caption={c ? `${fy(c.last.fy)} out-of-district tuition, all funds · the budget line said ${usd(c.last.gen_fund)}` : undefined}>
          Out-of-district tuition split by the fund that paid it, circuit breaker
          reimbursement{c ? ` from FY${c.cb_first.fy} to FY${c.cb_last.fy}` : ''}, and the
          check that establishes what the budget line actually is.
        </Door>
        <Door href="/who-ends-up-out-of-district" unit="placements"
          name="The route out of district"
          figure={sub ? `${sub.out_of_district} of ${sub.cohort}` : undefined}
          caption={sub ? `children who started in a substantially separate classroom and are now out of district` : undefined}>
          A cohort followed from where its placement started, the town&rsquo;s own count
          back to {r && r.counts.length ? `FY${r.counts[0].fy}` : 'the start of the record'},
          and the two published counts that do not always agree.
        </Door>
      </div>

      <H2 id="apart">Why they are four and not one</H2>
      <Body>
        Because each is measured in a different unit, by a different publisher, on a
        different census. A student is not a dollar. A placement is not a cost. A resident
        who transfers out is not established to have an individual education programme at
        all. The one arithmetic operation a reader will reach for &mdash; a cost per
        student &mdash; would take a numerator from one return and a denominator from
        another, and this project has already had to retract sentences built exactly that
        way.
      </Body>
      <Body>
        So the four have four addresses, four payloads and no shared figure. Each states
        the unit it counts at the top, and each carries its own list of what it cannot
        answer. The single registry of those limits is{' '}
        <a className="underline" style={{ color: 'var(--series-cost)' }}
          href={abs('/what-we-cannot-answer')}>what we cannot answer</a>.
      </Body>

      <H2 id="elsewhere">The parts of this that live elsewhere</H2>
      <Body>
        Special education is roughly a quarter of the school budget on every basis this
        project has tested, so it turns up on pages that are not about it.{' '}
        <a className="underline" style={{ color: 'var(--series-cost)' }}
          href={abs('/bend-the-curve')}>Bend the curve</a> carries the in-district
        escalator and the classification behind it &mdash; there is no account code for
        special education, so that classification is ours and it says so.{' '}
        <a className="underline" style={{ color: 'var(--series-cost)' }}
          href={abs('/when-grants-end')}>When a grant ends</a> measures the fund split on
        the paraprofessional function, which is the one thing that would settle whether the
        escalator is growth or grant money unwinding.{' '}
        <a className="underline" style={{ color: 'var(--series-cost)' }}
          href={abs('/if-students-leave')}>If students leave</a> is the school-choice
        SCENARIO, priced on an assumption; the report here is the measurement with no dials.
      </Body>
    </ReportShell>
  )
}

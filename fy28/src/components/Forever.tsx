import { useState } from 'react'
import { usd, usdShort } from '../model/engine'
import {
  DEFAULT_SCENARIO, DEFAULT_RATES, LEVY_CAP, STATE_AID,
  longRunTarget, salaryRateToBalance, workforceShrink, HEADCOUNT,
  aidGrowthToSustain, aidSchedule, ch70OnlyGrowth, type Bucket,
} from '../model/rates'

const pct = (x: number, d = 2) => `${(x * 100).toFixed(d)}%`
const S = DEFAULT_SCENARIO
const TARGET = longRunTarget(S)
const CONTRACT_RATE = DEFAULT_RATES.salaries

/** Health rates worth asking the question at: today's, and the ones a serious plan-design
 *  or insurer change might actually reach. */
const HEALTH_STEPS = [0.09, 0.07, 0.06, 0.05, 0.04, LEVY_CAP]

/** What balance forever requires, rather than what gets through next April.
 *
 *  Everything else on this site is about a budget year or a six-year projection. This is
 *  the question underneath all of them: if nothing dramatic changes, what set of numbers
 *  is actually stable — and it has exactly one answer, which is that the weighted average
 *  of everything the district buys has to grow no faster than the town's revenue, forever.
 *
 *  Since four of the six lines are effectively fixed by contract, law or the market, that
 *  makes salaries the residual. So the honest form of the question is not "can we hold
 *  salaries to 2½%" but "given what health insurance does, what is left for salaries" —
 *  and then, because a salary LINE and a salary RATE are different things, what that means
 *  in people. It is a harder set of numbers than anybody quotes, and it does not improve
 *  by being left unsaid. */
export function HealthSalaryTrade() {
  const [othersAtCap, setOthersAtCap] = useState(false)

  const ratesFor = (health: number): Record<Bucket, number> => othersAtCap
    ? { ...DEFAULT_RATES, health, transport: LEVY_CAP, sped: LEVY_CAP, sped_tuition: LEVY_CAP,
        utilities: LEVY_CAP, other: LEVY_CAP }
    : { ...DEFAULT_RATES, health }

  const rows = HEALTH_STEPS.map(health => {
    const salary = salaryRateToBalance(ratesFor(health), TARGET)
    const w = workforceShrink(Math.max(salary, 0), CONTRACT_RATE)
    return { health, salary, ...w, impossible: salary <= 0 }
  })

  return (
    <div>
      <div className="card p-4">
        <div className="flex flex-wrap items-baseline justify-between gap-3 mb-1">
          <h4 className="text-[14px] font-bold">
            What health insurance does decides what is left for salaries
          </h4>
          <label className="flex items-center gap-2 text-[12px] cursor-pointer"
            style={{ color: 'var(--text-secondary)' }}>
            <input type="checkbox" checked={othersAtCap}
              onChange={e => setOthersAtCap(e.target.checked)} />
            Also hold transport, special education and utilities to {pct(LEVY_CAP, 1)}
          </label>
        </div>
        <p className="text-[12px] mb-3" style={{ color: 'var(--text-secondary)' }}>
          Salaries are two thirds of the budget, so whatever the other lines do, salaries
          are what absorbs it. The last two columns assume the bargained increase stays
          at {pct(CONTRACT_RATE, 1)} and the line is held down by employing fewer people
          instead &mdash; which is one of the two ways to get there, and the one nobody
          says out loud.
        </p>

        <table className="stack w-full text-[13px] tnum">
          <caption className="sr-only">
            Salary growth rate required for permanent balance at each health insurance
            growth rate, and the workforce reduction that implies
          </caption>
          <thead>
            <tr className="text-left" style={{ color: 'var(--text-muted)' }}>
              <th className="font-semibold py-1.5">If health grows</th>
              <th className="font-semibold py-1.5 text-right">Salaries must grow</th>
              <th className="font-semibold py-1.5 text-right">Positions shed, year one</th>
              <th className="font-semibold py-1.5 text-right">Workforce after 20 years</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(r => (
              <tr key={r.health} className="border-t" style={{ borderColor: 'var(--grid)' }}>
                <td className="rowhead py-2 font-semibold">
                  {pct(r.health, 1)}
                  {r.health === DEFAULT_RATES.health && (
                    <span className="text-[11px] font-normal ml-1.5"
                      style={{ color: 'var(--text-muted)' }}>today</span>
                  )}
                </td>
                <td data-label="Salaries must grow" className="py-2 text-right font-semibold"
                  style={{ color: r.salary < 0.015 ? 'var(--status-critical)'
                    : r.salary < 0.025 ? 'var(--status-warning)' : 'var(--status-good)' }}>
                  {pct(r.salary)}
                </td>
                <td data-label="Positions shed, year one" className="py-2 text-right">
                  {r.positionsPerYear.toFixed(1)}
                </td>
                <td data-label="Workforce after 20 years" className="py-2 text-right font-semibold">
                  &minus;{pct(r.after20, 0)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        <p className="text-[12px] mt-3 pt-3 border-t leading-relaxed"
          style={{ borderColor: 'var(--grid)' }}>
          <strong>So: yes.</strong> Leaving health insurance where it is and balancing on
          headcount alone costs about{' '}
          <strong>{pct(rows[0].after20, 0)} of the workforce over twenty years</strong>{' '}
          &mdash; {rows[0].positionsPerYear.toFixed(1)} positions in the first year and
          more every year after, since it is a percentage. Getting insurance to{' '}
          {pct(0.04, 1)} brings that to {pct(rows[4].after20, 0)}
          {othersAtCap ? '' : ', and holding the four small lines to the cap as well brings it lower again'}.
          There is no version of this where the number is small.
        </p>
      </div>

      {/* ---- the same number, read the other way ----
       *
       * This card used to sit beside a four-line checklist of combinations that hold for
       * thirty years. The routes board above does that job properly now — priced, with
       * who has to agree to each — so the checklist went rather than say the same thing
       * twice and less well. */}
      <div className="card p-4 mt-4">
        <h4 className="text-[14px] font-bold mb-2">Or nobody loses a job</h4>
        <div className="grid gap-x-5 gap-y-2 lg:grid-cols-2">
          <p className="text-[13px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
            A salary <em>line</em> and a salary <em>rate</em> are different things, and the
            table above only shows one way to reconcile them. The other is that the
            salary rate itself lands at that number: everyone keeps their job, and with
            insurance at {pct(0.04, 1)} the scale rises {pct(rows[4].salary)} a year
            instead of {pct(CONTRACT_RATE, 1)}. Against inflation that is roughly flat pay,
            permanently, for roughly {HEADCOUNT} people &mdash; and it is bargained, three
            years at a time, by people who can decline.
          </p>
          <p className="text-[13px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
            Any mix of the two works, and that is the point of the board above rather than
            a footnote to it: every option that reaches is a mixture of things nobody wants
            to do, and a mixture asks less of each person than any single one of them does
            on its own. What does not work is neither.
          </p>
        </div>
      </div>
    </div>
  )
}

/** What the state would have to do instead — the only route where nobody in Lunenburg
 *  gives anything up. It deserves a number rather than a wish, and the number is large. */
export function StateAid() {
  const aidRate = aidGrowthToSustain(S)
  const sched = aidRate === null ? [] : aidSchedule(S, aidRate, 10)
  const tenYear = sched.reduce((s, r) => s + r.extra, 0)

  return (
    <div>
      <div className="grid gap-3 sm:grid-cols-3 mb-4">
        <Stat label="All state aid today" value={usdShort(STATE_AID.total)}
          sub={`${pct(STATE_AID.shareOfTownRevenue, 0)} of town revenue. Chapter 70 school aid is ${usdShort(STATE_AID.chapter70)} of it — ${pct(STATE_AID.ch70Share, 0)} — and covers ${pct(STATE_AID.shareOfSchoolBudget, 0)} of the school budget.`} />
        <Stat label="It is assumed to grow" value={pct(S.stateAidGrowth, 1)}
          sub="Below the rate of almost everything it pays for" />
        <Stat label="It would have to grow" value={aidRate === null ? 'no rate works' : pct(aidRate)}
          tone="critical"
          sub="Every year, forever, with nothing else in this model changing" />
      </div>

      {aidRate !== null && (
        <div className="card p-4">
          <table className="stack w-full text-[13px] tnum">
            <caption className="sr-only">
              State aid required for permanent balance against the amount assumed
            </caption>
            <thead>
              <tr className="text-left" style={{ color: 'var(--text-muted)' }}>
                <th className="font-semibold py-1.5">Year</th>
                <th className="font-semibold py-1.5 text-right">All state aid, as assumed</th>
                <th className="font-semibold py-1.5 text-right">All state aid, required</th>
                <th className="font-semibold py-1.5 text-right">Extra from the state</th>
              </tr>
            </thead>
            <tbody>
              {sched.slice(0, 6).map(r => (
                <tr key={r.fy} className="border-t" style={{ borderColor: 'var(--grid)' }}>
                  <td className="rowhead py-1.5 font-semibold">FY{r.fy}</td>
                  <td data-label="All state aid, as assumed" className="py-1.5 text-right">{usd(r.atBase)}</td>
                  <td data-label="All state aid, required" className="py-1.5 text-right">{usd(r.atRate)}</td>
                  <td data-label="Extra from the state" className="py-1.5 text-right font-semibold"
                    style={{ color: 'var(--status-critical)' }}>{usd(r.extra)}</td>
                </tr>
              ))}
              <tr className="border-t-2" style={{ borderColor: 'var(--text-primary)' }}>
                <td className="rowhead py-1.5 font-bold">Ten years</td>
                <td className="py-1.5" /><td className="py-1.5" />
                <td data-label="Extra, ten-year total" className="py-1.5 text-right font-bold">
                  {usd(tenYear)}
                </td>
              </tr>
            </tbody>
          </table>
          <p className="text-[12px] mt-3 leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
            The state would have to put in an extra <strong>{usd(sched[0].extra)}</strong>{' '}
            next year, <strong>{usd(sched[5].extra)}</strong> by FY{sched[5].fy}, and{' '}
            <strong>{usd(tenYear)}</strong> over the decade &mdash; and then keep
            compounding at {pct(aidRate)} indefinitely. Chapter 70 has not behaved like
            that in any recent year, and a town spending{' '}
            {usdShort(STATE_AID.aboveFoundation)} above its foundation budget is not where
            the formula sends its money.
          </p>
          <p className="text-[12px] mt-2 leading-relaxed" style={{ color: 'var(--text-muted)' }}>
            These figures are the whole cherry sheet, because the projection carries state
            aid as one line and grows it as one. Chapter 70 is{' '}
            {pct(STATE_AID.ch70Share, 0)} of it, and the remaining{' '}
            {usdShort(STATE_AID.other)} — charter reimbursement, transport, lottery — is
            not money the state would move for this reason. So if the increase had to come
            from <strong>Chapter 70 alone</strong>, it would have to grow{' '}
            <strong>{pct(ch70OnlyGrowth(aidRate))}</strong> a year rather than{' '}
            {pct(aidRate)}.
          </p>
          <p className="text-[12px] mt-2 leading-relaxed" style={{ color: 'var(--text-muted)' }}>
            The reason any of these rates is so high is that aid is only{' '}
            {pct(STATE_AID.shareOfTownRevenue, 0)} of the town&rsquo;s revenue. Fixing a
            blended cost rate of nearly 5% by moving a quarter of the revenue means moving
            that quarter very hard. Worth asking the delegation for; not worth planning
            around.
          </p>
        </div>
      )}
    </div>
  )
}

function Stat({ label, value, sub, tone }: {
  label: string; value: string; sub: string; tone?: 'critical'
}) {
  return (
    <div className="card p-4">
      <p className="text-[11px] font-semibold uppercase tracking-widest mb-1.5"
        style={{ color: 'var(--text-muted)' }}>{label}</p>
      <p className="text-2xl font-bold tnum leading-none" style={{
        color: tone === 'critical' ? 'var(--status-critical)' : 'var(--text-primary)' }}>
        {value}
      </p>
      <p className="text-xs mt-2 leading-relaxed" style={{ color: 'var(--text-secondary)' }}>{sub}</p>
    </div>
  )
}

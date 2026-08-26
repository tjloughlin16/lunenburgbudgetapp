import { usdShort } from '../model/engine'
import {
  CANNOT_SKIP, INSURANCE_CASE, BASELINE_BLENDED, DEFAULT_SCENARIO, DEFAULT_RATES,
  LEVY_CAP, buildRateToHold, buildScale, decadeWorth, longRunTarget, HEADCOUNT,
} from '../model/rates'

const pct = (x: number, d = 2) => `${(x * 100).toFixed(d)}%`
const TARGET = longRunTarget(DEFAULT_SCENARIO)
const SPREAD = BASELINE_BLENDED - TARGET

/** Every package upstairs moves at least two lines. This is why.
 *
 *  The board used to make this argument by listing single levers as though they were
 *  options, which spent most of the page demonstrating that things do not work and left a
 *  reader with nothing to do. The demonstration is still needed — "insurance alone is
 *  never enough" is exactly the sentence that gets misheard as "insurance is a sideshow",
 *  and somebody has to say which of the two it is — but it belongs underneath the menu as
 *  analysis rather than on it as a choice.
 *
 *  Two findings, and they are not symmetrical. Salaries cannot be worked around at all:
 *  the line is two thirds of the budget, so growing at 4% it consumes the entire
 *  revenue rate on its own and every other line in the budget would have to grow at
 *  nothing. Insurance can be worked around, at roughly five times the building for the
 *  identical outcome. Neither finishes the job alone, and neither can be left out of it. */
export function WhyCombination() {
  const sal = CANNOT_SKIP.salaries
  const ins = CANNOT_SKIP.health
  const [today, better] = INSURANCE_CASE
  const insWorth = decadeWorth({ ...DEFAULT_RATES, health: 0.04 })
  const salWorth = decadeWorth({ ...DEFAULT_RATES, salaries: LEVY_CAP })
  const buildAlone = buildRateToHold(DEFAULT_RATES)

  return (
    <div>
      <div className="mb-4">
        <h3 className="text-xl sm:text-2xl font-bold tracking-tight leading-tight">
          Why every one of them moves at least two lines
        </h3>
        <p className="text-[14px] leading-relaxed mt-2 max-w-3xl"
          style={{ color: 'var(--text-secondary)' }}>
          Not one of the packages above pulls a single lever, and that is not a stylistic
          choice. The spread that has to be closed is{' '}
          <strong>{(SPREAD * 100).toFixed(2)} points</strong> &mdash; costs compound at{' '}
          {pct(BASELINE_BLENDED)} and the town&rsquo;s revenue settles at {pct(TARGET)}.
          Here is what each line can do about that on its own, which is the part that gets
          argued about at meetings and has never been written down.
        </p>
      </div>

      <div className="grid gap-3 lg:grid-cols-2 items-start">
        {/* ---- the one that cannot be worked around at all ---- */}
        <div className="card p-4 sm:p-5">
          <p className="text-[11px] font-semibold uppercase tracking-widest"
            style={{ color: 'var(--status-critical)' }}>Cannot be left out</p>
          <h4 className="text-[16px] font-bold mt-0.5 mb-2">Staff salaries</h4>
          <p className="text-[13px] leading-relaxed">
            The line is <strong>{pct(sal.weight, 1)} of the budget</strong>, so growing at
            4% it consumes <strong className="tnum">{pct(sal.consumes)}</strong> of
            the {pct(TARGET)} the town has to spend &mdash; the whole of it, before a
            single bus, teacher&rsquo;s premium, out-of-district placement or box of paper
            is bought.
          </p>
          <p className="text-[13px] leading-relaxed mt-2"
            style={{ color: 'var(--text-secondary)' }}>
            That is not a judgement about pay, it is a share of a budget. Hold{' '}
            <em>every other line</em> to the levy cap &mdash; insurance included, which
            nobody has ever proposed &mdash; and the blend is still{' '}
            <strong className="tnum">{pct(sal.blendedOthersAtCap)}</strong>. Freeze every
            other line at zero growth outright and it comes to exactly{' '}
            <strong className="tnum">{pct(sal.blendedOthersFrozen)}</strong>: dead level,
            nothing to spare, and the town still starts the period behind.
          </p>
          <p className="text-[13px] leading-relaxed mt-2"
            style={{ color: 'var(--text-secondary)' }}>
            There is no arrangement of the other five lines that reaches the bar while
            salaries go on rising 4%. It can be paid around &mdash; with{' '}
            {sal.buildingsIfOthersAtCap === null ? 'nothing available'
              : `${sal.buildingsIfOthersAtCap.toFixed(0)} new buildings a year, for ever`}{' '}
            &mdash; and it cannot be left out.
          </p>
          <Worth label="What holding salaries to the levy cap is worth on its own"
            w={salWorth} tail={`Pinned to the cap with nothing else touched, salaries still
              leave the curves diverging — which is the other half of the same finding.`} />
        </div>

        {/* ---- the one that can be, expensively ---- */}
        <div className="card p-4 sm:p-5">
          <p className="text-[11px] font-semibold uppercase tracking-widest"
            style={{ color: 'var(--status-warning)' }}>Can be, at five times the price</p>
          <h4 className="text-[16px] font-bold mt-0.5 mb-2">Health insurance</h4>
          <p className="text-[13px] leading-relaxed">
            The highest-leverage line in the budget relative to its size, and still only{' '}
            <strong>{pct(ins.weight, 1)} of it</strong>. Taking five points off
            it &mdash; 9% to 4%, which is a serious plan-design change or the state
            GIC &mdash; takes <strong className="tnum">
            {((DEFAULT_RATES.health - 0.04) * ins.weight * 100).toFixed(2)} points</strong>{' '}
            off a blend that has to come down {(SPREAD * 100).toFixed(2)}. So it cannot
            finish, and it is nobody&rsquo;s sideshow.
          </p>
          <p className="text-[13px] leading-relaxed mt-2"
            style={{ color: 'var(--text-secondary)' }}>
            Unlike salaries it <em>can</em> be skipped. Here is the price of skipping
            it, for the identical outcome &mdash; salaries at the levy cap,
            the four small lines held, holding for a generation:
          </p>
          <div className="grid grid-cols-2 gap-2 mt-2">
            <Side label="Insurance left at 9%" v={today.buildings === null ? '—'
              : `${today.buildings.toFixed(0)} buildings a year`}
              sub={today.build === null ? '' : `${usdShort(today.build)} of new growth a year`}
              tone="critical" />
            <Side label="Insurance at 4%" v={better.buildings === null ? '—'
              : `${better.buildings.toFixed(0)} buildings a year`}
              sub={better.build === null ? '' : `${usdShort(better.build)} of new growth a year`}
              tone="good" />
          </div>
          <p className="text-[12px] leading-relaxed mt-2" style={{ color: 'var(--text-muted)' }}>
            Same salaries, same small lines, same thirty years &mdash;{' '}
            {today.build && better.build
              ? `${(today.build / better.build).toFixed(1)}× the building` : 'far more building'}{' '}
            to avoid asking the question. Or, read as pay rather than as construction: with
            insurance at 9% the salary growth that balances is{' '}
            <strong className="tnum">{pct(today.salary)}</strong>; with insurance at 4% it
            is <strong className="tnum">{pct(better.salary)}</strong>. Five points of
            premium is worth{' '}
            <strong className="tnum">
              {((better.salary - today.salary) * 100).toFixed(2)} points
            </strong>{' '}
            of everybody&rsquo;s pay, or about{' '}
            {(today.positionsPerYear - better.positionsPerYear).toFixed(1)} positions a
            year of the {HEADCOUNT} the line pays for.
          </p>
          <Worth label="And what it is worth even where it changes nothing else"
            w={insWorth} tail={`It never shuts the gap for a single April on its own, and
              it is still the most valuable uncontested move on this page: it touches no
              classroom and reopens no contract.`} />
        </div>
      </div>

      <div className="card p-4 sm:p-5 mt-3">
        <h4 className="text-[15px] font-bold mb-2">And the two that ask nothing of anybody here</h4>
        <p className="text-[13px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
          <strong>Development on its own.</strong> Leave every cost rate exactly where it
          is and a flat build rate can still hold the line for thirty years &mdash; at{' '}
          {buildAlone === null ? 'no rate that exists'
            : <>{usdShort(buildAlone)} of new growth a year, which is{' '}
              <strong>{buildScale(buildAlone).buildingsPerYear.toFixed(0)} new buildings a
              year, one every {buildScale(buildAlone).everyDays} days, without
              stopping</strong>, against the {buildScale(buildAlone).existingCount}{' '}
              commercial properties the town has accumulated since it was founded</>}. It
          is a real answer and an implausible one, and it ends badly rather than gently:
          nothing touched the cost rate, so when the money stops covering the divergence
          the divergence is still running at full speed. Every package above uses
          development the other way round &mdash; as the last mile after the rates have
          done the work, which is why they need tens of buildings rather than hundreds.
        </p>
        <p className="text-[13px] leading-relaxed mt-2" style={{ color: 'var(--text-secondary)' }}>
          <strong>The state.</strong> Chapter 70 could carry the whole increase without
          anybody in Lunenburg giving anything up, and the arithmetic of what that would
          take has a section of its own below. The short version: it is worth asking the
          delegation for and it is not worth planning around, and it gets worse before it
          gets better &mdash; all state aid is under a quarter of what the town collects,
          so a large rate on a small base takes decades to catch a smaller rate on the
          whole cost base.
        </p>
      </div>
    </div>
  )
}

function Worth({ label, w, tail }: {
  label: string
  w: ReturnType<typeof decadeWorth>
  tail: string
}) {
  return (
    <div className="mt-3 rounded-lg p-3" style={{ background: 'var(--surface-3)' }}>
      <p className="text-[11px] font-semibold uppercase tracking-widest mb-1"
        style={{ color: 'var(--text-muted)' }}>{label}</p>
      <p className="text-[13px] leading-relaxed">
        <strong>{usdShort(w.removed)} out of the next ten years</strong> &mdash;{' '}
        {usdShort(w.firstYear)} of it next April, and by FY37 the gap is {usdShort(w.gapAtDecade)}{' '}
        instead of {usdShort(w.baselineAtDecade)},{' '}
        <strong>{(w.smallerBy * 100).toFixed(0)}% smaller</strong>.{' '}
        <span style={{ color: 'var(--text-secondary)' }}>{tail}</span>
      </p>
    </div>
  )
}

function Side({ label, v, sub, tone }: {
  label: string; v: string; sub: string; tone: 'critical' | 'good'
}) {
  return (
    <div className="rounded-lg p-2.5" style={{ background: 'var(--surface-3)' }}>
      <p className="text-[11px] font-semibold" style={{ color: 'var(--text-muted)' }}>
        {label}
      </p>
      <p className="text-[15px] font-bold leading-snug mt-0.5" style={{
        color: tone === 'critical' ? 'var(--status-critical)' : 'var(--status-good)' }}>
        {v}
      </p>
      <p className="text-[11px] mt-0.5" style={{ color: 'var(--text-muted)' }}>{sub}</p>
    </div>
  )
}

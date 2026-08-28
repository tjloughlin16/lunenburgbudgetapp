import { MODEL, usd } from '../model/engine'
import { Note } from './primitives'

/** Special education, and what it does to the rate.
 *
 *  This section exists because of the fifth rule this project works by: follow magnitude,
 *  not actionability. Special education is about a fifth of the budget and had no section
 *  at all, while athletics -- 1.7% -- had three, because "the district must place a child
 *  where the plan requires" reads like nothing to model. That reasoning is wrong. A line
 *  nobody controls still sets the size of the problem.
 *
 *  What it must NOT become is a page about cutting special education. Every figure here
 *  is about the RATE and about which parts of it can repeat. Nothing on it is a lever.
 *
 *  And it carries an argument against a number this project itself published, which is
 *  the reason the last block is as long as it is. */

const S = MODEL.sped
const pct = (v: number, d = 2) => `${(v * 100).toFixed(d)}%`
const LEVY_CAP = 0.025

export function TheOneOff() {
  const y = S.year
  return (
    <>
      <div className="grid gap-3 sm:grid-cols-3">
        <Card label="The district's published rate" value={pct(y.published)}
          sub={`FY26 to FY27 level service — the same staff, the same programs and the
                same children, one year older.`} />
        <Card label="With one line held flat" value={pct(y.underlying)} tone="critical"
          sub={`The same arithmetic with out-of-district tuition left where FY26 had it.`} />
        <Card label="What that line is worth" value={`${(y.bend * 100).toFixed(2)} pts`}
          sub={`The distance between the two. For scale, the whole gap to the levy cap at
                the published rate is ${((y.published - LEVY_CAP) * 100).toFixed(2)} points.`} />
      </div>

      <Note>
        Out-of-district tuition is what Lunenburg pays other schools to educate children
        whose plans it cannot deliver itself. It was budgeted{' '}
        <strong>{usd(y.tuition_fy26)}</strong> for FY26 and{' '}
        <strong>{usd(y.tuition_fy27)}</strong> for FY27 — down {usd(-y.tuition_change)},{' '}
        {pct(-y.tuition_rate, 0)}, in one year.
        <br /><br />
        <strong style={{ color: 'var(--text-primary)' }}>That fall can happen once.</strong>{' '}
        Placements can be brought home; there is no second {pct(-y.tuition_rate, 0)},
        because there is not another {usd(-y.tuition_change)} left in the line to lose. It
        is a <em>level</em> change — it drops the cost once and leaves the angle of the
        curve alone. The published {pct(y.published)} therefore describes a year that
        cannot repeat, and the rate a resident should plan against is{' '}
        {pct(y.underlying)}.
      </Note>
    </>
  )
}

/** The year, decomposed. The whole point is that it is two entries, not a trend. */
export function TheTrade() {
  const d = [...S.decomposition].sort((a, b) => (b.fy27 - b.fy26) - (a.fy27 - a.fy26))
  const tuition = S.year.tuition_change
  const rows = [...d.map(r => ({ label: r.label, from: r.fy26, to: r.fy27 })),
                { label: 'Out-of-district tuition', from: S.year.tuition_fy26,
                  to: S.year.tuition_fy27 }]
    .sort((a, b) => Math.abs(b.to - b.from) - Math.abs(a.to - a.from))
  const big = Math.max(...rows.map(r => Math.abs(r.to - r.from)))

  return (
    <>
      <div className="card p-4">
        {rows.map(r => {
          const ch = r.to - r.from
          const up = ch >= 0
          return (
            <div key={r.label} className="py-2.5 border-b last:border-b-0"
              style={{ borderColor: 'var(--grid)' }}>
              <div className="flex items-baseline justify-between gap-3">
                <p className="text-[13.5px] font-semibold">{r.label}</p>
                <p className="text-[13.5px] font-bold tnum shrink-0" style={{
                  color: up ? 'var(--status-critical)' : 'var(--status-good)' }}>
                  {up ? '+' : '−'}{usd(Math.abs(ch))}
                </p>
              </div>
              {/* Both directions off a shared centre line, so the two big entries read as
                  opposing rather than as two large bars that happen to be near each
                  other. Everything else is visibly nothing. */}
              <div className="relative h-1.5 rounded-full mt-1.5 mb-1"
                style={{ background: 'var(--surface-3)' }}>
                <div className="absolute inset-y-0" style={{
                  left: up ? '50%' : `${50 - (Math.abs(ch) / big) * 50}%`,
                  width: `${(Math.abs(ch) / big) * 50}%`,
                  background: up ? 'var(--status-critical)' : 'var(--status-good)' }} />
              </div>
              <p className="text-[11px] tnum" style={{ color: 'var(--text-muted)' }}>
                {usd(r.from)} → {usd(r.to)}
                {r.from ? ` · ${ch >= 0 ? '+' : ''}${pct(r.to / r.from - 1, 1)}` : ''}
              </p>
            </div>
          )
        })}
      </div>

      <Note>
        <strong style={{ color: 'var(--text-primary)' }}>What the budget shows.</strong>{' '}
        Two lines moved in opposite directions by nearly the same amount in the same year:
        paraprofessionals {usd(S.decomposition.find(x => x.id === 'paras')!.fy27
          - S.decomposition.find(x => x.id === 'paras')!.fy26)} up, purchased placements{' '}
        {usd(-tuition)} down. Teachers are flat, therapists are near flat, substitutes are
        identical to the dollar.
        <br /><br />
        <strong style={{ color: 'var(--text-primary)' }}>What it does not show.</strong>{' '}
        That any child moved, that the two decisions were connected, or that one caused
        the other. The tuition line may simply have been budgeted too high for years. A
        budget records dollars against a line; it never records people, and nobody
        publishes how many children are placed out of district.
        <br /><br />
        <strong style={{ color: 'var(--text-primary)' }}>What the district said it
        meant to do.</strong> Its own FY27 presentation to the Finance Committee states
        that <em>“investing in internal staff is significantly more cost-effective than
        tuition and transportation for OOD placements.”</em> That is evidence of intent.
        It is not evidence of outcome, and the two are not the same thing.
      </Note>
    </>
  )
}

/** The rate, and the argument against the number this project used to publish. */
export function TheRate() {
  const used = S.range.find(r => r.used)!
  const whole = S.range.find(r => r.id === 'whole')!
  const paras = S.decomposition.find(r => r.id === 'paras')!
  const step = paras.fy27 - paras.fy26
  const yearRise = S.decomposition.reduce((s, r) => s + (r.fy27 - r.fy26), 0)

  return (
    <>
      <div className="card p-4 mb-4">
        {S.range.map(r => (
          <div key={r.id} className="py-3 border-b last:border-b-0"
            style={{ borderColor: 'var(--grid)' }}>
            <div className="flex items-baseline justify-between gap-3">
              <p className="text-[13.5px] font-semibold">
                {r.label}
                {r.used && <span className="ml-2 text-[10px] font-bold uppercase
                                            tracking-widest px-1.5 py-0.5 rounded"
                  style={{ background: 'var(--series-cost)', color: 'var(--surface-1)' }}>
                  used</span>}
              </p>
              <p className="text-[15px] font-bold tnum shrink-0"
                style={{ color: r.used ? 'var(--series-cost)' : 'var(--text-secondary)' }}>
                {pct(r.rate)}
              </p>
            </div>
            <p className="text-[12px] leading-relaxed mt-1"
              style={{ color: 'var(--text-muted)' }}>{r.what}</p>
          </div>
        ))}
      </div>

      <Note>
        <strong style={{ color: 'var(--text-primary)' }}>Why not simply use what the line
        did?</strong> Because {pct(whole.rate)} is not a growth rate. It is one hiring
        decision. Paraprofessionals rose {pct(paras.fy27 / paras.fy26 - 1, 1)} in FY27 —{' '}
        {usd(step)} — which is <strong>{pct(step / yearRise, 0)} of the whole year’s
        increase in special education</strong>, because every other part of the line fell
        that year. Take the aides out and the rest grew{' '}
        {pct(S.range.find(r => r.id === 'ex_paras')!.rate)} a year across the two budgets,
        below the {pct(LEVY_CAP, 1)} levy cap.
        <br /><br />
        Those aides were hired. Their cost is already inside the {usd(S.base)} this model
        starts from. Escalating that amount at {pct(whole.rate)} would say the district
        hires {pct(paras.fy27 / paras.fy26 - 1, 0)} more aides again next year, and again
        the year after — which is the same error as reading the district’s{' '}
        {pct(S.year.published)} as a recurring rate, pointed the other way. A one-time
        step belongs in the amount, not in the angle.
        <br /><br />
        <strong style={{ color: 'var(--text-primary)' }}>What this rate assumes, and it is
        not nothing.</strong> That the FY27 hiring was a step rather than the first year of
        a climb. If more aides are needed every year — because more children arrive
        requiring one, or because the children here require more — then{' '}
        {pct(used.rate)} is too low and this model understates the gap. Nothing in a budget
        column can settle that. A budget shows dollars per line and never shows people, and
        the district does not publish staff counts. That is why the whole range is printed
        above rather than only the number we chose.
      </Note>

      <Note>
        <strong style={{ color: 'var(--text-primary)' }}>There is no special education
        contract.</strong> These staff are paid under the same agreements as everybody
        else — professional staff on the teachers’ contract, aides on the
        paraprofessionals’. There is no special education bargaining unit and no special
        education pay rate, so describing this line with a single number of its own risks
        implying its staff receive larger increases than other staff. They do not.
        <div className="mt-3 space-y-1.5">
          {S.units.map(u => (
            <div key={u.id} className="flex items-baseline justify-between gap-3
                                       text-[12px]">
              <span style={{ color: 'var(--text-secondary)' }}>{u.label}</span>
              <span className="flex-1 border-b border-dotted mx-1 translate-y-[-3px]"
                style={{ borderColor: 'var(--grid)' }} />
              <span className="tnum shrink-0" style={{ color: 'var(--text-muted)' }}>
                {pct(u.share, 0)} of the line · {pct(u.rate, 1)} · {u.basis}
              </span>
            </div>
          ))}
        </div>
        <div className="mt-3 text-[12px]" style={{ color: 'var(--text-muted)' }}>
          The bus contract is the one input nobody publishes a rate for, so it is measured
          — and the measurement moves the blend. At the district’s own transport assumption
          of {pct(S.transportRates.districtAssumption, 0)} the blend is{' '}
          {pct(blendAt(S.transportRates.districtAssumption))}; at the most recent year,{' '}
          {pct(S.transportRates.recent, 1)}, it is {pct(used.rate)}; at the two-year rate
          of {pct(S.transportRates.twoYear, 1)} it is{' '}
          {pct(blendAt(S.transportRates.twoYear))}. The middle one is used.
        </div>
      </Note>
    </>
  )
}

/** The blend with the bus line priced differently — so the page can show its own
 *  sensitivity instead of asserting that the chosen figure is the only one available. */
function blendAt(transportRate: number): number {
  return S.units.reduce((sum, u) =>
    sum + u.share * (u.id === 'transport' ? transportRate : u.rate), 0)
}

/** The one line whose value nobody can check, priced at every plausible level.
 *
 *  Deliberately a table and not a slider. A control would invite a reader to choose the
 *  number that suits the argument they already hold, and the honest position is that
 *  nobody outside the district knows which of these is right. */
export function TuitionRisk() {
  const r = S.tuitionRisk
  return (
    <>
      <div className="card overflow-x-auto">
        <table className="w-full text-[13px]">
          <thead>
            <tr className="border-b" style={{ borderColor: 'var(--grid)' }}>
              <th className="text-left font-semibold px-4 py-2.5">If the FY28 line is</th>
              <th className="text-right font-semibold px-4 py-2.5 tnum">Tuition</th>
              <th className="text-right font-semibold px-4 py-2.5 tnum">FY28 gap</th>
              <th className="text-right font-semibold px-4 py-2.5 tnum">Against the model</th>
            </tr>
          </thead>
          <tbody>
            {r.map((s, i) => (
              <tr key={s.id} className="border-b last:border-b-0"
                style={{ borderColor: 'var(--grid)' }}>
                <td className="px-4 py-2.5">{s.label}</td>
                <td className="px-4 py-2.5 text-right tnum">{usd(s.tuition)}</td>
                <td className="px-4 py-2.5 text-right tnum font-semibold">{usd(s.gap)}</td>
                <td className="px-4 py-2.5 text-right tnum" style={{
                  color: i ? 'var(--status-critical)' : 'var(--text-muted)' }}>
                  {i ? `+${usd(s.delta)}` : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <Note>
        None of these is a forecast. They are the cost of being wrong about one line, and
        the spread — {usd(r[r.length - 1].delta)} between the budgeted figure and a return
        to where FY26 had it — is wider than any other single assumption in this model.
        <br /><br />
        There is no slider here on purpose. A control would let a reader pick the number
        that suits the argument they arrived with, and the honest position is that nobody
        outside the district can know which of these is right. What would settle it is the
        FY28 tuition line when the district publishes it, and the count of children placed
        out of district — which is not published at all, in any year.
      </Note>
    </>
  )
}

/** Every year the state publishes, because three chosen from eight is a decision. */
export function StudentCounts() {
  const s = S.students
  if (!s.length) return null
  const max = Math.max(...s.map(d => d.n))
  const first = s[0], last = s[s.length - 1]
  const low = s.reduce((a, b) => (b.n < a.n ? b : a))
  return (
    <>
      <div className="card p-4">
        <div className="flex items-end gap-1.5" style={{ height: 132 }}>
          {s.map(d => (
            <div key={d.fy} className="flex-1 flex flex-col items-center justify-end h-full">
              <span className="text-[10px] tnum mb-1"
                style={{ color: 'var(--text-muted)' }}>{d.n}</span>
              <div className="w-full rounded-t" style={{
                height: `${(d.n / max) * 100}%`,
                background: d.fy === low.fy ? 'var(--status-good)' : 'var(--series-cost)',
                opacity: d.fy === low.fy ? 1 : 0.75 }} />
              <span className="text-[10px] tnum mt-1"
                style={{ color: 'var(--text-muted)' }}>{`’${String(d.fy).slice(2)}`}</span>
            </div>
          ))}
        </div>
        <p className="text-[11px] mt-2" style={{ color: 'var(--text-muted)' }}>
          Students with disabilities as of 1 October, from the state’s own report. All{' '}
          {s.length} published years. The low point, FY{low.fy}, is marked.
        </p>
      </div>
      <Note>
        Over the whole series the count{' '}
        {last.n < first.n ? 'fell' : 'rose'}{' '}
        {Math.abs(Math.round((last.n / first.n - 1) * 1000) / 10)}% — FY{first.fy}{' '}
        {first.n} to FY{last.fy} {last.n} — and the share of enrollment is close to where
        it started, {first.pct}% against {last.pct}%. Measured from the FY{low.fy} low of{' '}
        {low.n} it is up {Math.round((last.n / low.n - 1) * 1000) / 10}%.
        <br /><br />
        <strong style={{ color: 'var(--text-primary)' }}>Which is why the whole series is
        drawn.</strong> Any three of these years can be chosen to show a rise or a fall,
        and this project has no business doing that to a reader. What the series does not
        settle is <em>intensity</em>: the district’s own FY27 presentation shows
        sub-separate placements — the most intensive end — rising over the same period, on
        totals that do not reconcile with the state’s. The two count different things and
        cannot be squared from anything published.
      </Note>
    </>
  )
}

function Card({ label, value, sub, tone }: {
  label: string; value: string; sub: string; tone?: 'critical'
}) {
  return (
    <div className="card p-4">
      <p className="text-[11px] font-semibold uppercase tracking-widest mb-1.5"
        style={{ color: 'var(--text-muted)' }}>{label}</p>
      <p className="text-3xl font-bold tnum leading-none" style={{
        color: tone === 'critical' ? 'var(--status-critical)' : 'var(--text-primary)' }}>
        {value}
      </p>
      <p className="text-xs mt-2 leading-relaxed"
        style={{ color: 'var(--text-secondary)' }}>{sub}</p>
    </div>
  )
}

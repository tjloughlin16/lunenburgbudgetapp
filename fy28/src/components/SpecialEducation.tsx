import { MODEL, usd } from '../model/engine'
import { Disclose, Note } from './primitives'

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
const T = S.tuitionTrend
const P = S.paraTrend
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
        <strong style={{ color: 'var(--text-primary)' }}>That fall is a level change, not
        a rate.</strong> It drops the cost once and leaves the angle of the curve alone, so
        the published {pct(y.published)} describes a year whose arithmetic does not carry
        forward. The rate a resident should plan against is {pct(y.underlying)}.
        <br /><br />
        <strong style={{ color: 'var(--text-primary)' }}>What it is not is unprecedented.</strong>{' '}
        An earlier version of this page said there could be no second{' '}
        {pct(-y.tuition_rate, 0)}. Eleven budgets say otherwise: this line fell{' '}
        {pct(-T.biggestFall[0], 1)} in FY{T.biggestFall[1] % 100} and then rose{' '}
        {pct(T.biggestRise[0], 0)} in FY{T.biggestRise[1] % 100}. It has been as low as{' '}
        {usd(T.low)} and as high as {usd(T.high)}, and {usd(y.tuition_fy27)} is{' '}
        {pct(-T.vsMean, 0)} <em>below</em> its eleven-budget average of {usd(T.mean)} —
        an ordinary year for this line rather than a floor. The section below draws the
        whole series.
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
        <strong style={{ color: 'var(--text-primary)' }}>A contract sets what one person
        is paid. It says nothing about how many people are employed — and on this line,
        that is where the movement is.</strong>{' '}
        Both bargained groups here have run away from their agreements, in opposite
        directions. Special education teachers are on a contract giving 3.5% and their line
        has grown {pct(S.professionalTrend.cagr, 2)} across {S.professionalTrend.n}{' '}
        budgets — headcount drifting down. The paras are on a contract giving{' '}
        {pct(2 / 100, 1)} and their line has grown {pct(P.cagr, 1)}.
        <div className="mt-3 grid gap-3 sm:grid-cols-3">
          <MiniStat label="Paras, FY{P.firstFy} to FY{P.lastFy}"
            value={`${P.ratio.toFixed(2)}×`}
            sub={`${usd(P.first)} to ${usd(P.last)}`} />
          <MiniStat label="Compound rate" value={pct(P.cagr, 1)}
            sub={`${P.up} of ${P.n - 1} years up. Stays between ${pct(P.cagrLow, 1)} and
                  ${pct(P.cagrByStart[P.cagrByStart.length - 2].rate, 1)} wherever you
                  start it.`} />
          <MiniStat label="Is it a trend?" value={`R² ${P.r2.toFixed(2)}`}
            sub="Near 1 means the years explain the amount. This is a climb, not a scatter." />
        </div>
        <div className="mt-3">
          That is <em>headcount</em>, and no pay settlement reaches it. Escalating the paras
          at their {pct(2 / 100, 1)} contract would assume the district stops adding them —
          which it has not done in {P.n - 1} of the last {P.n} budgets.
        </div>
      </Note>

      <Note>
        <strong style={{ color: 'var(--text-primary)' }}>This page argued the opposite a
        day ago, and the correction is worth stating rather than quietly editing.</strong>{' '}
        This line was escalated at {pct(S.range.find(r => r.id === 'contracts_only')!.rate)}{' '}
        — the settlements alone — on the argument that FY27’s{' '}
        {pct(S.decomposition.find(d => d.id === 'paras')!.fy27
          / S.decomposition.find(d => d.id === 'paras')!.fy26 - 1, 0)} increase in paras was
        a one-time step whose cost already sat in the amount the model starts from. That
        argument was sound. Its premise was false.
        <br /><br />
        With two budget years there is no way to tell a step from a climb — they look
        identical. The archive now reaches back {P.n} budgets, and it is a climb: the FY27
        rise is the steepest year of a trend that has been running since FY{P.firstFy % 100},
        not a departure from one. The rate went from{' '}
        {pct(S.range.find(r => r.id === 'contracts_only')!.rate)} to {pct(used.rate)}, and
        the projected gap went up rather than down.
      </Note>

      <Note>
        <strong style={{ color: 'var(--text-primary)' }}>What this rate still assumes.</strong>{' '}
        That the climb continues at roughly the rate it has held. That is an assumption and
        not a measurement, and nothing in a budget column can test it: a budget shows
        dollars per line and never shows people, and the district does not publish staff
        counts. What can be said is narrower and firmer — that pricing this line at the pay
        settlements alone has been wrong in every one of the last {P.n - 1} budgets.
        <br /><br />
        The buses are the weakest input. There is no published vendor escalator, so the
        figure is measured, and over {S.transportTrend.n} budgets it fits far less
        convincingly than the paras do — R² of {S.transportTrend.r2.toFixed(2)} against{' '}
        {P.r2.toFixed(2)}. It is {pct(S.transportTrend.cagr, 1)} because that is the least
        bad number available, not because the line is well behaved. It is{' '}
        {pct(S.units[2].share, 0)} of the total.
      </Note>

      <Note>
        <strong style={{ color: 'var(--text-primary)' }}>There is no special education
        contract.</strong> These staff are paid under the same agreements as everybody
        else — professional staff on the teachers’ contract, paras on the
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
          Only the first of those is a contract rate. The paras and the buses are measured,
          because no agreement says how many people a district employs or what a bus vendor
          will charge at renewal — and a rate copied from a settlement for a line that does
          not follow one is a number with a citation and no meaning.
        </div>
      </Note>
    </>
  )
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

function MiniStat({ label, value, sub }: {
  label: string; value: string; sub: string
}) {
  return (
    <div>
      <p className="text-[11px] font-semibold uppercase tracking-widest"
        style={{ color: 'var(--text-muted)' }}>{label}</p>
      <p className="text-xl font-bold tnum leading-none mt-0.5">{value}</p>
      <p className="text-[11.5px] mt-1 leading-relaxed"
        style={{ color: 'var(--text-secondary)' }}>{sub}</p>
    </div>
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

/** Every budget line counted as special education, and the two that were not.
 *
 *  This exists because somebody asked how the figure was calculated, and the honest
 *  answer was that they could not find out. Special education has no account code of its
 *  own: two of the groups the district reports carry both kinds of cost, so any total for
 *  it is somebody's classification rather than a published quantity. This one is ours,
 *  which under rule 3 means it has to be visible enough to argue with.
 *
 *  Open by default would bury the argument above it under fifty-six rows. Closed with the
 *  count and the total on the outside is a promise that the working is here, which is the
 *  part that matters -- a reader who wants it opens it, and one who does not can still see
 *  that it exists. */
export function WhatCounts() {
  const c = S.classified
  const named = c.counted.filter(l => l.basis === 'name')
  return (
    <>
      <Note>
        <strong style={{ color: 'var(--text-primary)' }}>There is no account code for
        special education.</strong> The state’s chart of accounts does not have one, and
        two of the groups the district reports carry both kinds of cost at once — 2330 is
        paraprofessionals, general education and special education together, and 3300 is
        transportation, where the special education runs sit beside the yellow buses. So
        every figure on this page rests on a classification somebody made. This one is
        ours, and it has two parts:
        <br /><br />
        <strong style={{ color: 'var(--text-primary)' }}>One.</strong> {c.groups.length}{' '}
        function groups are special education outright, and every line inside them counts
        — {c.byGroup} lines.{' '}
        <strong style={{ color: 'var(--text-primary)' }}>Two.</strong> Inside the mixed
        groups, a line counts when the district’s own label for it says special education
        — {c.byName} lines, of which one, special education transportation, is most of the
        money.
        <br /><br />
        They come to <strong>{usd(c.total)}</strong>, which is the amount every projection
        on this page starts from. The list is below and it adds up; the underlying file is{' '}
        <a href="/data/budget-lines.csv" className="font-semibold"
          style={{ color: 'var(--series-cost)' }}>published as a spreadsheet</a>, with a
        column marking which lines these are, so the sum can be checked without taking our
        word for any of it.
      </Note>

      <Disclose title={`Every line counted — ${c.counted.length} of them, ${usd(c.total)}`}
        sub="The district’s own group and line names, and which of the two rules caught each">
        <div className="overflow-x-auto">
          <table className="w-full text-[12px]">
            <thead>
              <tr className="border-b" style={{ borderColor: 'var(--grid)' }}>
                <th className="text-left font-semibold px-3 py-2">Function group</th>
                <th className="text-left font-semibold px-3 py-2">Line</th>
                <th className="text-right font-semibold px-3 py-2 tnum">FY27</th>
                <th className="text-left font-semibold px-3 py-2">Counted because</th>
              </tr>
            </thead>
            <tbody>
              {c.counted.map((l, i) => (
                <tr key={i} className="border-b last:border-b-0"
                  style={{ borderColor: 'var(--grid)' }}>
                  <td className="px-3 py-1.5" style={{ color: 'var(--text-muted)' }}>
                    {l.group}</td>
                  <td className="px-3 py-1.5">{l.item}</td>
                  <td className="px-3 py-1.5 text-right tnum">{usd(l.amount)}</td>
                  <td className="px-3 py-1.5" style={{ color: 'var(--text-muted)' }}>
                    {l.basis === 'group' ? 'the group is special education'
                      : 'the district’s own name for the line'}</td>
                </tr>
              ))}
              <tr className="font-bold">
                <td className="px-3 py-2" colSpan={2}>Total</td>
                <td className="px-3 py-2 text-right tnum">{usd(c.total)}</td>
                <td />
              </tr>
            </tbody>
          </table>
        </div>
      </Disclose>

      <Note>
        <strong style={{ color: 'var(--text-primary)' }}>And what was deliberately left
        out.</strong> A classification is defined as much by its edges as by its middle.
        <div className="mt-3 space-y-3">
          {c.excluded.map(e => (
            <div key={e.group}>
              <div className="flex items-baseline justify-between gap-3">
                <p className="text-[12.5px] font-semibold">{e.group}</p>
                <p className="text-[12px] tnum shrink-0" style={{ color: 'var(--text-muted)' }}>
                  FY25 {usd(e.fy25)} · FY26 {usd(e.fy26)} · FY27 {usd(e.amount)}
                </p>
              </div>
              <p className="text-[12px] leading-relaxed"
                style={{ color: 'var(--text-secondary)' }}>{e.why}</p>
            </div>
          ))}
        </div>
        <div className="mt-3 text-[12px]" style={{ color: 'var(--text-muted)' }}>
          The general education paras are worth a second look. They are budgeted at nothing
          from FY26 onward, so in FY27 that boundary costs nothing either way — but they
          were {usd(c.excluded[0].fy25)} in FY25, which is the base year of the two-year
          rates above. A boundary can be irrelevant in the year you show and matter in the
          year you are comparing against.
        </div>
      </Note>

      <div className="mt-4 text-[12px] leading-relaxed"
        style={{ color: 'var(--text-muted)' }}>
        The eight groups taken whole: {c.groups.join(' · ')}.
        The {named.length} lines caught by name: {named.map(l => l.item).join(' · ')}.
      </div>
    </>
  )
}

/** Eleven budgets for one line, and the reason no rate is drawn through them.
 *
 *  This exists because the model escalated this line at 8% a year on no stated basis at
 *  all, and the archive turned out to reach far enough back to ask what it had really
 *  done. The answer is that it has done nothing in particular, very loudly -- and a chart
 *  is the only honest way to say that, because a single number cannot.
 *
 *  The R-squared is on the page deliberately. It is the one figure that turns "we could
 *  not find a trend" into "there is no trend", and a reader who wants to check that we
 *  did not simply give up can. */
export function TuitionHistory() {
  const h = S.tuitionHistory
  if (!h.length) return null
  const max = Math.max(...h.map(d => d.total))
  const spread = S.tuitionTrend.cagrByStart.map(c => c.rate)

  return (
    <>
      <div className="card p-4">
        <div className="flex items-end gap-1.5" style={{ height: 160 }}>
          {h.map(d => {
            const extreme = d.total === T.low || d.total === T.high
            return (
              <div key={d.fy}
                className="flex-1 flex flex-col items-center justify-end h-full">
                <span className="text-[9.5px] tnum mb-1"
                  style={{ color: 'var(--text-muted)' }}>
                  {Math.round(d.total / 1000)}k
                </span>
                <div className="w-full rounded-t" style={{
                  height: `${(d.total / max) * 100}%`,
                  background: extreme ? 'var(--status-critical)' : 'var(--series-cost)',
                  opacity: extreme ? 1 : 0.7 }} />
                <span className="text-[9.5px] tnum mt-1"
                  style={{ color: 'var(--text-muted)' }}>
                  {`’${String(d.fy).slice(2)}`}
                </span>
              </div>
            )
          })}
        </div>
        {/* The mean as a stated number rather than a drawn line: a rule across bars
            reads as a target, and this is not one. */}
        <p className="text-[11px] mt-2" style={{ color: 'var(--text-muted)' }}>
          Budgeted out-of-district tuition, {h.length} budgets, one budget stage held
          constant throughout. Average {usd(T.mean)}. The extremes are marked.
        </p>
      </div>

      <div className="grid gap-3 sm:grid-cols-3 mt-4">
        <Card label="The range it has run in" value={`${T.ratio.toFixed(2)}×`}
          sub={`${usd(T.low)} in FY${T.lowFy % 100} to ${usd(T.high)} in FY${T.highFy % 100}.`} />
        <Card label="Direction" value={`${T.up} up · ${T.down} down`}
          sub={`A straight line through the ${T.n} has an R² of ${T.r2.toFixed(2)} — for
                practical purposes, no relationship between the year and the amount.`} />
        <Card label="Where FY27 sits" value={pct(T.vsMean, 0)}
          sub={`Against the ${T.n}-budget average of ${usd(T.mean)}. Not a floor, and not
                an outlier — an ordinary year for this line.`} />
      </div>

      <Note>
        <strong style={{ color: 'var(--text-primary)' }}>So this line is held flat, and the
        absence of a rate is the point.</strong> It used to be escalated at 8% a year, which
        had no stated basis; the back-test flagged it as the worst-calibrated assumption in
        the model. The obvious repair is to measure the rate instead — and the measurement
        will not hold still:
        <div className="mt-3 grid gap-x-6 gap-y-1 sm:grid-cols-2 text-[12px] tnum">
          {S.tuitionTrend.cagrByStart.map(c => (
            <div key={c.fy} className="flex justify-between">
              <span style={{ color: 'var(--text-secondary)' }}>
                starting from FY{c.fy % 100}
              </span>
              <span style={{ color: 'var(--text-muted)' }}>{pct(c.rate, 2)} a year</span>
            </div>
          ))}
        </div>
        <div className="mt-3">
          The same line, the same endpoint, {pct(Math.min(...spread), 1)} to{' '}
          {pct(Math.max(...spread), 1)} depending only on which year you start counting.
          A figure that moves that far on an arbitrary choice is not a measurement, and
          publishing one would repeat the error corrected further up this page. What is
          known about this line is its range, so the range is what gets published — priced,
          below, at every level it has actually reached.
        </div>
      </Note>
    </>
  )
}

/** The two lines whose rates are measured rather than taken from a contract.
 *
 *  Drawn rather than asserted, because the difference between them is the whole argument
 *  and it is visible at a glance: the paras climb, the buses wander. The R-squared under
 *  each is the number that turns "it looks like a trend" into a claim somebody can check,
 *  and it is why one of these lines is escalated at what it has done and the other is
 *  used with a warning. */
export function MeasuredLines() {
  const sets = [
    { id: 'prof', title: 'Special education teachers',
      series: S.professionalSeries, t: S.professionalTrend,
      contract: `Their contract gives ${pct(S.leaRate, 1)} a year.`,
      verdict: 'Below contract, and a good fit. Headcount here has drifted down, so the '
             + 'contract rate would overstate it.' },
    { id: 'paras', title: 'Special education paraprofessionals',
      series: S.paraSeries, t: S.paraTrend,
      contract: `Their contract gives ${pct(S.afscmeRate, 1)} a year.`,
      verdict: 'A trend, and a strong one. Escalated at what it has done.' },
    { id: 'transport', title: 'Special education transportation',
      series: S.transportSeries, t: S.transportTrend,
      contract: 'A vendor contract with no published escalator.',
      verdict: 'A weak fit. Used because it is the least bad figure available, and it is '
             + 'the smallest of the three components.' },
  ]
  return (
    <div className="grid gap-4 md:grid-cols-3">
      {sets.map(({ id, title, series, t, contract, verdict }) => {
        if (!series?.length) return null
        const max = Math.max(...series.map(d => d.total))
        return (
          <div key={id} className="card p-4">
            <p className="text-[13.5px] font-semibold">{title}</p>
            <p className="text-[11.5px] mb-3" style={{ color: 'var(--text-muted)' }}>
              {contract}
            </p>
            <div className="flex items-end gap-1" style={{ height: 110 }}>
              {series.map(d => (
                <div key={d.fy}
                  className="flex-1 flex flex-col items-center justify-end h-full">
                  <div className="w-full rounded-t" style={{
                    height: `${(d.total / max) * 100}%`,
                    background: 'var(--series-cost)',
                    opacity: d.stage === 'proposed' ? 0.55 : 0.85 }} />
                  <span className="text-[9px] tnum mt-1"
                    style={{ color: 'var(--text-muted)' }}>
                    {`’${String(d.fy).slice(2)}`}
                  </span>
                </div>
              ))}
            </div>
            <div className="grid grid-cols-3 gap-2 mt-3 text-center">
              <div>
                <p className="text-[15px] font-bold tnum">{pct(t.cagr, 1)}</p>
                <p className="text-[10px]" style={{ color: 'var(--text-muted)' }}>a year</p>
              </div>
              <div>
                <p className="text-[15px] font-bold tnum">{t.r2.toFixed(2)}</p>
                <p className="text-[10px]" style={{ color: 'var(--text-muted)' }}>R²</p>
              </div>
              <div>
                <p className="text-[15px] font-bold tnum">{t.up}/{t.n - 1}</p>
                <p className="text-[10px]" style={{ color: 'var(--text-muted)' }}>years up</p>
              </div>
            </div>
            <p className="text-[11.5px] mt-3 leading-relaxed"
              style={{ color: 'var(--text-secondary)' }}>{verdict}</p>
          </div>
        )
      })}
    </div>
  )
}

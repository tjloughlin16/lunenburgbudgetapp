import { usd, usdShort } from '../model/engine'
import {
  DEFAULT_SCENARIO, DEFAULT_RATES, LEVY_CAP, ALL_CUTS,
  run, blendedOf, longRunRevenueGrowth, overrideTreadmill, overrideForYears,
  type Scenario,
} from '../model/rates'

const YEARS = 10
const pct = (x: number, d = 2) => `${(x * 100).toFixed(d)}%`

interface Case {
  label: string; sub: string; kind: 'level' | 'slope' | 'both'; s: Scenario
  /** Something about this option a reader would otherwise reasonably get wrong. */
  note?: string
}

const rates = (o: Partial<typeof DEFAULT_RATES>) => ({ ...DEFAULT_RATES, ...o })

/** The same six futures the board can produce, fixed in place so the argument does not
 *  depend on the reader having found the right slider.
 *
 *  Ordered to make one point in sequence: the two things everybody proposes are levels
 *  and both expire; the rate changes do not expire but leave a residue; the last row is
 *  the combination, which is the only one that ends the problem. */
const CASES: Case[] = [
  { label: 'Do nothing', sub: 'The projection as it stands', kind: 'level',
    s: DEFAULT_SCENARIO },
  { label: 'Cut everything nameable', kind: 'level',
    sub: `Every sport, the band, clubs, art, 60% of technology and every lawful `
      + `administrative line — ${usdShort(ALL_CUTS)} at once`,
    s: { ...DEFAULT_SCENARIO, cut: ALL_CUTS } },
  { label: 'Pass one override', kind: 'level',
    sub: `${usdShort(1_250_000)}, school-only, so the schools keep all of it`,
    // The surplus in the covered years is a fair thing to ask about, and the answer is
    // not "it is wasted": an override raises a ceiling, it does not compel collection.
    note: 'An override raises the levy limit; it does not oblige the town to collect it. '
      + 'In a year the schools need less than it raises, the town can levy under the limit '
      + '— Lunenburg has left as much as $53,706 unlevied — or appropriate the difference '
      + 'elsewhere. The override then compounds at 2½% like the rest of the limit, which '
      + 'is why it falls behind a gap growing faster than that.',
    s: { ...DEFAULT_SCENARIO, overrideLevy: 1_250_000 } },
  { label: 'Bend health insurance', sub: 'From 9% a year to 4%', kind: 'slope',
    s: { ...DEFAULT_SCENARIO, rates: rates({ health: 0.04 }) } },
  { label: 'Bend salaries and health', kind: 'slope',
    sub: 'Settle at 2½% and get insurance to 4% — the two lines that are 82% of the budget',
    s: { ...DEFAULT_SCENARIO, rates: rates({ salaries: LEVY_CAP, health: 0.04 }) } },
  { label: 'Both, plus one cut', kind: 'both',
    sub: `The same two rates, and ${usdShort(400_000)} taken out once`,
    s: { ...DEFAULT_SCENARIO, cut: 400_000,
         rates: rates({ salaries: LEVY_CAP, health: 0.04 }) } },
]

/** First year back in deficit, or null if it never returns inside the horizon. */
const failsIn = (r: ReturnType<typeof run>) => r.find(y => y.gap > 0)?.fy ?? null

export function LevelVsSlope() {
  const rows = CASES.map(c => {
    const r = run(YEARS, c.s)
    const blended = blendedOf(c.s.rates)
    // The long-run revenue rate, not today's: new growth is a fixed dollar amount, so its
    // contribution decays and comparing against year one flatters every row here.
    const rev = longRunRevenueGrowth(r)
    /** Consecutive years funded from the start — the question every one of these cards
     *  is really being asked, and the one three sampled columns could not answer. */
    const funded = r.findIndex(y => y.gap > 0)
    return { ...c, r, blended, rev, fails: failsIn(r), widening: blended > rev + 0.0002,
             funded: funded === -1 ? r.length : funded }
  })

  return (
    <div>
      <div className="grid gap-3 lg:grid-cols-2 items-start">
        {rows.map(row => (
          <div key={row.label} className="card p-4">
            <div className="flex items-baseline justify-between gap-3">
              <h3 className="text-[15px] font-bold leading-snug">{row.label}</h3>
              <Kind kind={row.kind} />
            </div>
            <p className="text-[12px] mt-1" style={{ color: 'var(--text-secondary)' }}>
              {row.sub}
            </p>

            {/* Every year, not three of them.
                This was three boxes at FY28, FY30 and FY33, which hid FY29 — so a $1.25M
                override that funds two years looked like it funded one, and the card
                could not answer the question it exists to answer. Same squares and same
                words as the board above. */}
            <ol className="grid grid-cols-10 gap-0.5 mt-3"
              aria-label="Whether each year is funded">
              {row.r.map(y => (
                <li key={y.fy} className="rounded-sm text-center py-1"
                  title={y.gap > 0 ? `FY${y.fy}: short by ${usd(y.gap)}` : `FY${y.fy}: funded`}
                  style={{ background: y.gap > 0 ? 'var(--status-critical)' : 'var(--status-good)',
                           color: '#fff' }}>
                  <span className="block text-[9px] font-bold leading-none">{y.fy}</span>
                  <span className="sr-only">
                    {y.gap > 0 ? `not funded, short by ${usd(y.gap)}` : 'funded'}
                  </span>
                </li>
              ))}
            </ol>

            <p className="text-[12px] mt-2 font-semibold">
              {row.funded === 0
                ? <span style={{ color: 'var(--status-critical)' }}>
                    Short in every year, starting with {usdShort(row.r[0].gap)} next year
                  </span>
                : row.funded === row.r.length
                  ? <span style={{ color: 'var(--status-good)' }}>
                      Funded in all {row.r.length} years
                    </span>
                  : <span>
                      <span style={{ color: 'var(--status-good)' }}>
                        Funded for {row.funded} {row.funded === 1 ? 'year' : 'years'}
                      </span>
                      <span style={{ color: 'var(--text-secondary)' }}>, then short again
                        from FY{row.fails} — {usdShort(row.r[row.r.length - 1].gap)} by
                        FY{row.r[row.r.length - 1].fy}</span>
                    </span>}
            </p>

            {row.note && (
              <p className="text-[11px] leading-relaxed mt-2 pl-2.5"
                style={{ borderLeft: '2px solid var(--status-warning)',
                         color: 'var(--text-secondary)' }}>
                {row.note}
              </p>
            )}

            <p className="text-[12px] mt-3 pt-2.5 border-t leading-relaxed"
              style={{ borderColor: 'var(--grid)' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Cost growth </span>
              <strong className="tnum">{pct(row.blended)}</strong>
              <span style={{ color: 'var(--text-secondary)' }}> against revenue </span>
              <strong className="tnum">{pct(row.rev)}</strong>
              {' — '}
              {row.widening
                ? <span style={{ color: 'var(--status-critical)' }}>
                    still widening{row.fails ? `, back in deficit by FY${row.fails}` : ''}
                  </span>
                : row.fails
                  ? <span style={{ color: 'var(--status-warning)' }}>
                      held, and a small residue returns in FY{row.fails}
                    </span>
                  : <span style={{ color: 'var(--status-good)' }}>
                      held, and funded for {YEARS} years
                    </span>}
            </p>
          </div>
        ))}
      </div>
    </div>
  )
}

const Kind = ({ kind }: { kind: Case['kind'] }) => {
  const m = {
    level: { word: 'Changes the amount', color: 'var(--status-critical)' },
    slope: { word: 'Changes the direction', color: 'var(--series-cost)' },
    both: { word: 'Both', color: 'var(--status-good)' },
  }[kind]
  return (
    <span className="text-[10px] font-bold uppercase tracking-wider whitespace-nowrap shrink-0"
      style={{ color: m.color }}>{m.word}</span>
  )
}

/** What "just pass an override" actually commits the town to.
 *
 *  An override is heard as one ballot question. Because it lifts the base once and the
 *  base then grows at 2½% while costs grow at nearly 5%, the arithmetic asks for a fresh
 *  one every spring, forever.
 *
 *  Sized as a school-only question, which is the honest way to put it: an override may be
 *  written for a single department, and then the schools keep every dollar. The townwide
 *  column beside it is the same job done by a general override — nearly twice the money
 *  for the same result here, because the schools take only their share of it — and that
 *  is the shape of the ask the town actually voted on and lost. Printed as a tax bill,
 *  which is the form a voter meets it in. */
export function OverrideTreadmill() {
  const t = overrideTreadmill(run(6, DEFAULT_SCENARIO))
  const total = t.reduce((s, r) => s + r.onAverageHome, 0)
  return (
    <div className="card p-4">
      <table className="stack w-full text-[13px] tnum">
        <caption className="sr-only">
          The override that would have to pass in each year to hold services level
        </caption>
        <thead>
          <tr className="text-left" style={{ color: 'var(--text-muted)' }}>
            <th className="font-semibold py-1.5">Year</th>
            <th className="font-semibold py-1.5 text-right">School-only ballot</th>
            <th className="font-semibold py-1.5 text-right">On the average home</th>
            <th className="font-semibold py-1.5 text-right">If it were townwide</th>
          </tr>
        </thead>
        <tbody>
          {t.map(r => (
            <tr key={r.fy} className="border-t" style={{ borderColor: 'var(--grid)' }}>
              <td className="rowhead py-1.5 font-semibold">FY{r.fy}</td>
              <td data-label="School-only ballot" className="py-1.5 text-right">{usd(r.levy)}</td>
              <td data-label="On the average home" className="py-1.5 text-right font-semibold">
                ${r.onAverageHome}
              </td>
              <td data-label="If it were townwide" className="py-1.5 text-right"
                style={{ color: 'var(--text-muted)' }}>
                {usd(r.townwide)} · ${r.townwideOnAverageHome}
              </td>
            </tr>
          ))}
          <tr className="border-t-2" style={{ borderColor: 'var(--text-primary)' }}>
            <td className="rowhead py-1.5 font-bold">Six years</td>
            <td className="py-1.5" />
            <td data-label="Added to the average bill" className="py-1.5 text-right font-bold">
              +${total} a year
            </td>
            <td className="py-1.5" />
          </tr>
        </tbody>
      </table>
      <p className="text-[12px] mt-3 leading-relaxed" style={{ color: 'var(--text-muted)' }}>
        These are smaller than the year-on-year growth in the gap shown earlier, and
        deliberately so: last year&rsquo;s override is still there and has itself grown
        2&frac12;%, so each row is only the new money needed on top of it.
      </p>
      <p className="text-[12px] mt-2 leading-relaxed" style={{ color: 'var(--text-muted)' }}>
        Each row is a separate vote, and each one is permanent &mdash; the tax column
        accumulates. A <strong>school-only</strong> question gives the schools every dollar
        it raises. The last column is the same job done by a general override covering all
        departments: it has to be nearly twice the size, and costs the average homeowner
        nearly twice as much, to leave the schools in the same place. That is the shape of
        the ask Lunenburg put on the ballot and lost.
      </p>
    </div>
  )
}

/** The other way to do it: one vote, sized to last.
 *
 *  The treadmill above is honest and incomplete on its own. An override is not a one-off
 *  payment — it lifts the levy limit permanently and compounds at 2½% — so a big enough
 *  one genuinely does cover years rather than a year, and a page that only showed the
 *  treadmill would be arguing rather than informing.
 *
 *  Setting the two side by side is the fair version, and the price of the second is the
 *  thing worth seeing: each extra year costs more than the last, because the override
 *  compounds at 2½% and the gap compounds at nearly 5% from a base already larger. */
export function OverrideSizing() {
  const base = run(12, DEFAULT_SCENARIO)
  const rows = [1, 2, 3, 5, 8, 10].map(y => ({
    years: y,
    ...overrideForYears(y),
    /* The binding year is the LAST one covered, and its running total is the number the
     * override has to reach. Shown because "5 years costs $2,949,209" is otherwise a
     * figure out of nowhere: it is FY32's $3,255,375 divided by four years of compounding
     * at the cap, and the table should say so rather than make a reader ask. */
    throughFy: base[y - 1].fy,
    thatYearsGap: base[y - 1].gap,
  }))
  return (
    <div className="card p-4">
      <h3 className="text-[15px] font-bold">Or one vote, sized to last</h3>
      <p className="text-[12px] mt-1 mb-3" style={{ color: 'var(--text-secondary)' }}>
        An override is not a one-off payment. It raises the levy limit permanently and
        compounds at 2&frac12;% a year like the rest of it, so a large enough one really
        does cover years rather than a year. This is what each length costs.
      </p>
      <table className="stack w-full text-[13px] tnum">
        <caption className="sr-only">
          Size of a single school override required to cover a given number of years
        </caption>
        <thead>
          <tr className="text-left" style={{ color: 'var(--text-muted)' }}>
            <th className="font-semibold py-1.5">To cover</th>
            <th className="font-semibold py-1.5 text-right">Through</th>
            <th className="font-semibold py-1.5 text-right">
              The ballot question
              <span className="block text-[10px] font-normal"
                style={{ color: 'var(--text-muted)' }}>voted in FY28</span>
            </th>
            <th className="font-semibold py-1.5 text-right">
              Worth by then
              <span className="block text-[10px] font-normal"
                style={{ color: 'var(--text-muted)' }}>after compounding at 2&frac12;%</span>
            </th>
            <th className="font-semibold py-1.5 text-right">That year&rsquo;s gap</th>
            <th className="font-semibold py-1.5 text-right">On the average home, every year</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(r => (
            <tr key={r.years} className="border-t" style={{ borderColor: 'var(--grid)' }}>
              <td className="rowhead py-1.5 font-semibold">
                {r.years} {r.years === 1 ? 'year' : 'years'}
              </td>
              <td data-label="Through" className="py-1.5 text-right">FY{r.throughFy}</td>
              <td data-label="The ballot question, voted in FY28"
                className="py-1.5 text-right font-semibold">{usd(r.levy)}</td>
              <td data-label="Worth by then" className="py-1.5 text-right"
                style={{ color: 'var(--series-cost)' }}>
                {usd(Math.round(r.levy * (1 + LEVY_CAP) ** (r.years - 1)))}
              </td>
              <td data-label="That year&rsquo;s gap" className="py-1.5 text-right">
                {usd(r.thatYearsGap)}
              </td>
              <td data-label="On the average home, every year"
                className="py-1.5 text-right font-semibold">${r.onAverageHome}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="text-[13px] mt-3 leading-relaxed">
        <strong>Why {usdShort(rows[3].levy)} covers a {usdShort(rows[3].thatYearsGap)}{' '}
        gap.</strong> Because {usd(rows[3].levy)} is what the ballot says in FY28, not what
        it delivers in FY{rows[3].throughFy}. The levy limit it lifted compounds at
        2&frac12;% like the rest of the limit, so by FY{rows[3].throughFy} that same
        override is handing the schools{' '}
        {usd(Math.round(rows[3].levy * (1 + LEVY_CAP) ** 4))} &mdash; which is
        FY{rows[3].throughFy}&rsquo;s gap to the dollar. Read the last two columns of any
        row and they match; that is the sizing rule, not a coincidence.
      </p>
      <p className="text-[12px] mt-2 leading-relaxed" style={{ color: 'var(--text-muted)' }}>
        Run the model at exactly {usd(rows[3].levy)} and FY{rows[3].throughFy} lands with
        nothing to spare. Two thousand dollars less and it fails.
      </p>
      <p className="text-[12px] mt-2 leading-relaxed" style={{ color: 'var(--text-muted)' }}>
        Each extra year costs more than the last: the override compounds at 2&frac12;% and
        the gap compounds at nearly 5% from a base that is already bigger. The two rates
        never cross, so <strong>no override of any size holds forever</strong> — buying a
        decade costs {usd(rows[rows.length - 1].onAverageHome)} a year on the average home,
        and FY{38} arrives anyway. That is the same rate problem the rest of this page is
        about, met from the revenue side.
      </p>
    </div>
  )
}

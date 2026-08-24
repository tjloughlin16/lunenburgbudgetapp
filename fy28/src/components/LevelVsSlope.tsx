import { usd, usdShort } from '../model/engine'
import {
  DEFAULT_SCENARIO, DEFAULT_RATES, LEVY_CAP, ALL_CUTS,
  run, blendedOf, longRunRevenueGrowth, overrideTreadmill, type Scenario,
} from '../model/rates'

const YEARS = 10
const pct = (x: number, d = 2) => `${(x * 100).toFixed(d)}%`

interface Case { label: string; sub: string; kind: 'level' | 'slope' | 'both'; s: Scenario }

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
    return { ...c, r, blended, rev, fails: failsIn(r), widening: blended > rev + 0.0002 }
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

            <dl className="grid grid-cols-3 gap-2 mt-3 text-center">
              {[0, 2, 5].map(i => (
                <div key={i} className="rounded-lg py-2" style={{ background: 'var(--surface-3)' }}>
                  <dt className="text-[10px] font-semibold uppercase tracking-wider"
                    style={{ color: 'var(--text-muted)' }}>FY{row.r[i].fy}</dt>
                  <dd className="text-[15px] font-bold tnum mt-0.5" style={{
                    color: row.r[i].gap > 0 ? 'var(--status-critical)' : 'var(--status-good)',
                  }}>
                    {row.r[i].gap > 0 ? usdShort(row.r[i].gap) : 'clear'}
                  </dd>
                </div>
              ))}
            </dl>

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
                      held, and clear for {YEARS} years
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

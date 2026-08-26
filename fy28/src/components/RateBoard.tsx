import { useEffect, useMemo, useState } from 'react'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from 'recharts'
import { usd, usdShort } from '../model/engine'
import {
  RATE_LINES, DEFAULT_RATES, DEFAULT_SCENARIO, CUT_OPTIONS, LEVY_CAP,
  blendedOf, run, revenueGrowthOf, longRunRevenueGrowth, verdictOf, consequenceOf,
  overrideStops,
  type Bucket, type Package, type Scenario, type Verdict,
} from '../model/rates'

const YEARS = 12
const pct = (x: number, d = 2) => `${(x * 100).toFixed(d)}%`

/** The board where the two kinds of fix are put side by side and made to argue.
 *
 *  The left column only changes levels: it cuts real, named, painful things and it
 *  passes an override. The right column only changes rates. Both columns print the
 *  blended cost growth underneath them, and the left one never moves — that refusal is
 *  the entire teaching device, and it is why the columns are laid out as a pair rather
 *  than as one list of controls. */
export function RateBoard({ stickyTop = 'top-12', defaultPinned = true, seed = null }: {
  /** How far down the pinned block sits. The walkthrough puts a sticky room heading above
   *  it, so the board has to clear that rather than stack underneath it. */
  stickyTop?: string
  /** Off inside the walkthrough: a sticky room heading plus a pinned chart plus the site
   *  header is more than half a phone screen before any controls are visible. */
  defaultPinned?: boolean
  /** One of the packages, sent here from the board that names them.
   *
   *  Reading that a package holds and watching its curve go flat are different kinds of
   *  knowing, and the second one is the reason this page exists. The nonce is what lets
   *  the same package be sent twice after the reader has dragged something. */
  seed?: { route: Package; nonce: number } | null
} = {}) {
  const [rates, setRates] = useState<Record<Bucket, number>>({ ...DEFAULT_RATES })
  const [cuts, setCuts] = useState<Set<string>>(new Set())
  const [overrideLevy, setOverrideLevy] = useState(0)
  const [newGrowth, setNewGrowth] = useState(DEFAULT_SCENARIO.newGrowth)
  /* Not a control on this board — the only thing that sets it is option one, whose whole
   * point is that it moves the revenue line and nothing else. Carried anyway so that
   * loading that option shows what it actually does rather than showing nothing. */
  const [stateAidGrowth, setStateAidGrowth] = useState(DEFAULT_SCENARIO.stateAidGrowth)
  const [loaded, setLoaded] = useState<Package | null>(null)
  // The controls are long and the chart is the feedback, so by default the chart follows
  // you down the page. Pinning is a preference, not a mode — some readers want the whole
  // curve and the table space back.
  const [pinned, setPinned] = useState(defaultPinned)

  const cut = CUT_OPTIONS.filter(c => cuts.has(c.id)).reduce((s, c) => s + c.amount, 0)
  const scenario: Scenario = useMemo(
    () => ({ rates, newGrowth, cut, overrideLevy, stateAidGrowth, feeRevenue: 0 }),
    [rates, newGrowth, cut, overrideLevy, stateAidGrowth])

  const years = useMemo(() => run(YEARS, scenario), [scenario])
  /* Recomputed only when something OTHER than the override moves, so dragging the
   * override itself does not make its own tick marks jump around underneath it. */
  const stops = useMemo(
    () => overrideStops({ rates, newGrowth, cut, overrideLevy: 0, stateAidGrowth,
                          feeRevenue: 0 }),
    [rates, newGrowth, cut, stateAidGrowth])
  const stopIndex = stops.findIndex(st => st.levy === overrideLevy) + 1
  const atStop = stopIndex > 0 ? stops[stopIndex - 1] : null
  const baseline = useMemo(() => run(YEARS, DEFAULT_SCENARIO), [])
  const blended = blendedOf(rates)
  const revGrowth = revenueGrowthOf(newGrowth)
  const longRun = longRunRevenueGrowth(years)
  const verdict = verdictOf(years, blended)
  const touched = cut > 0 || overrideLevy > 0
    || newGrowth !== DEFAULT_SCENARIO.newGrowth
    || stateAidGrowth !== DEFAULT_SCENARIO.stateAidGrowth
    || (Object.keys(rates) as Bucket[]).some(k => rates[k] !== DEFAULT_RATES[k])

  const reset = () => {
    setRates({ ...DEFAULT_RATES }); setCuts(new Set())
    setOverrideLevy(0); setNewGrowth(DEFAULT_SCENARIO.newGrowth)
    setStateAidGrowth(DEFAULT_SCENARIO.stateAidGrowth); setLoaded(null)
  }

  /* Loading a package replaces the whole scenario rather than merging into it: a
   * half-applied package is not one of the packages, and would be scored as though it
   * were. */
  useEffect(() => {
    if (!seed) return
    const { rates: r, newGrowth: ng, stateAidGrowth: aid } = seed.route.scenario
    setRates({ ...r }); setNewGrowth(ng); setStateAidGrowth(aid)
    setOverrideLevy(0); setCuts(new Set()); setLoaded(seed.route)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [seed?.nonce])

  return (
    <div>
      {loaded && (
        <div className="card p-3 mb-3 flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1"
          style={{ borderColor: 'var(--series-cost)' }}>
          <p className="text-[13px] leading-snug">
            <span className="font-bold">
              {loaded.forEver ? 'Holds for ever' : `Holds ${loaded.horizon} years`}: {loaded.label}
            </span>{' '}
            <span style={{ color: 'var(--text-secondary)' }}>
              is loaded into the controls below. Drag anything and it becomes yours instead.
            </span>
          </p>
          <button onClick={reset} className="text-[12px] font-semibold shrink-0"
            style={{ color: 'var(--series-cost)' }}>Clear it</button>
        </div>
      )}
      <Verdicts verdict={verdict} blended={blended} revGrowth={revGrowth}
        longRun={longRun} years={years} cut={cut} overrideLevy={overrideLevy} />

      <div className={pinned ? `sticky z-20 ${stickyTop} -mx-1 px-1 pb-2` : ''}
        style={pinned ? { background: 'var(--surface-2)' } : undefined}>
        <YearStatus years={years} compact={pinned} />
        <Curves years={years} baseline={baseline} touched={touched} compact={pinned}
          pinned={pinned} onTogglePin={() => setPinned(p => !p)} />
      </div>

      <div className="grid gap-4 lg:grid-cols-2 items-start mt-4">
        {/* ---- the level column: everything people actually propose ---- */}
        <div className="card p-4">
          <p className="text-[11px] font-semibold uppercase tracking-widest"
            style={{ color: 'var(--text-muted)' }}>One-time fixes</p>
          <h3 className="text-[15px] font-bold mt-0.5">Cut things, or pass an override</h3>
          <p className="text-[12px] mt-1 mb-3" style={{ color: 'var(--text-secondary)' }}>
            These change the <strong>amount</strong>. Take all of them and watch the number
            at the bottom of this column stay exactly where it is.
          </p>

          <div className="space-y-2">
            {CUT_OPTIONS.map(c => (
              <label key={c.id}
                className="flex items-start gap-2.5 p-2.5 rounded-lg cursor-pointer"
                style={{ background: cuts.has(c.id) ? 'var(--surface-3)' : 'transparent' }}>
                <input type="checkbox" checked={cuts.has(c.id)} className="mt-0.5"
                  onChange={() => setCuts(prev => {
                    const n = new Set(prev)
                    if (n.has(c.id)) n.delete(c.id); else n.add(c.id)
                    return n
                  })} />
                <span className="min-w-0 flex-1">
                  <span className="flex items-baseline justify-between gap-2">
                    <span className="text-[13px] font-medium leading-snug">{c.label}</span>
                    <span className="text-[13px] font-semibold tnum shrink-0">
                      {usdShort(c.amount)}
                    </span>
                  </span>
                  <span className="block text-[11px] mt-0.5" style={{ color: 'var(--text-muted)' }}>
                    {c.sub}
                  </span>
                </span>
              </label>
            ))}
          </div>

          <div className="mt-3 pt-3 border-t" style={{ borderColor: 'var(--grid)' }}>
            {/* Indexed over the stops rather than over dollars: the only override amounts
                worth landing on are the ones that fund through a particular year, and a
                slider that can stop at $2,300,000 invites the question "and that buys?" */}
            <Slider label="A one-time override" value={stopIndex}
              min={0} max={stops.length} step={1}
              onChange={i => setOverrideLevy(i === 0 ? 0 : stops[i - 1].levy)}
              display={atStop ? `${usd(atStop.levy)}` : 'None'} />
            <p className="text-[11px] mt-0.5" style={{ color: 'var(--text-muted)' }}>
              {atStop
                ? <>Funds through <strong>FY{atStop.fy}</strong> &mdash; {atStop.years}{' '}
                    {atStop.years === 1 ? 'year' : 'years'}. A school-only question, so the
                    schools keep every dollar; the townwide ask that failed covered every
                    department, which is why it had to be so much larger to do the same
                    work here.</>
                : <>Each notch is the smallest override that funds through one more year,
                    given everything else set on this page. Cut something first and they
                    all get smaller.</>}
            </p>
            <p className="text-[11px] mt-0.5" style={{ color: 'var(--text-muted)' }}>
              A school-only question, so the schools keep every dollar. The townwide ask
              that failed covered every department, which is why it had to be so much
              larger to do the same work here.
            </p>
          </div>

          <p className="text-[12px] mt-3 pt-3 border-t" style={{ borderColor: 'var(--grid)' }}>
            <span style={{ color: 'var(--text-secondary)' }}>Found once: </span>
            <strong className="tnum">{usd(cut + overrideLevy)}</strong>
          </p>
          <p className="text-[13px] mt-1">
            <span style={{ color: 'var(--text-secondary)' }}>Cost growth rate: </span>
            <strong className="tnum" style={{ color: 'var(--status-critical)' }}>
              {pct(blended)}
            </strong>
            <span className="text-[12px]" style={{ color: 'var(--text-muted)' }}>
              {' '}— unchanged by anything in this column
            </span>
          </p>
        </div>

        {/* ---- the slope column ---- */}
        <div className="card p-4">
          <p className="text-[11px] font-semibold uppercase tracking-widest"
            style={{ color: 'var(--text-muted)' }}>Growth rates</p>
          <h3 className="text-[15px] font-bold mt-0.5">Change what things grow at</h3>
          <p className="text-[12px] mt-1 mb-3" style={{ color: 'var(--text-secondary)' }}>
            These change the <strong>direction</strong>. The number beside each line is how
            much of the budget it is &mdash; that, not the rate, decides how much moving it
            is worth.
          </p>

          <div className="space-y-3">
            {RATE_LINES.map(l => (
              <div key={l.key}>
                <Slider
                  label={l.label}
                  hint={`${pct(l.weight, 1)} of the budget`}
                  value={rates[l.key]} min={0} max={0.12} step={0.0025}
                  onChange={v => setRates(r => ({ ...r, [l.key]: v }))}
                  display={pct(rates[l.key], 2)}
                  changed={rates[l.key] !== DEFAULT_RATES[l.key]}
                  was={pct(DEFAULT_RATES[l.key], 1)} />
                <p className="text-[11px] mt-0.5" style={{ color: 'var(--text-muted)' }}>
                  Holding it to {pct(LEVY_CAP, 1)} moves the blend{' '}
                  <strong>{(l.swing * 100).toFixed(2)} pts</strong> · {l.controlledBy}
                </p>
                <Consequence bucket={l.key} rate={rates[l.key]} />
              </div>
            ))}
          </div>

          <div className="mt-3 pt-3 border-t" style={{ borderColor: 'var(--grid)' }}>
            <Slider label="New commercial growth, every year" value={newGrowth}
              min={0} max={2_500_000} step={50_000} onChange={setNewGrowth}
              display={`${usdShort(newGrowth)} a year`}
              changed={newGrowth !== DEFAULT_SCENARIO.newGrowth}
              was={usdShort(DEFAULT_SCENARIO.newGrowth)} />
            <p className="text-[11px] mt-0.5" style={{ color: 'var(--text-muted)' }}>
              The only revenue rate the town owns. The levy itself is locked at{' '}
              {pct(LEVY_CAP, 1)} by Proposition 2&frac12; and no vote here changes that.
            </p>
          </div>

          <p className="text-[13px] mt-3 pt-3 border-t" style={{ borderColor: 'var(--grid)' }}>
            <span style={{ color: 'var(--text-secondary)' }}>Cost growth rate: </span>
            <strong className="tnum" style={{
              color: blended > longRun ? 'var(--status-critical)' : 'var(--status-good)',
            }}>{pct(blended)}</strong>
            <span className="text-[12px]" style={{ color: 'var(--text-muted)' }}>
              {' '}vs revenue at {pct(revGrowth)} today, {pct(longRun)} long-run
            </span>
          </p>
        </div>
      </div>

      {touched && (
        <button onClick={reset} className="text-[12px] font-semibold mt-4"
          style={{ color: 'var(--series-cost)' }}>
          Reset everything to the projection &rarr;
        </button>
      )}
    </div>
  )
}

/* ------------------------------------------------------------------ */

/** The three states, said in a sentence. `held` is the one nobody explains. */
function Verdicts({ verdict, blended, revGrowth, longRun, years, cut, overrideLevy }: {
  verdict: Verdict; blended: number; revGrowth: number; longRun: number
  years: ReturnType<typeof run>; cut: number; overrideLevy: number
}) {
  // How much bigger the hole actually gets, read straight off the two squares above.
  //
  // This was the spread times the first year's cost, which is a rate approximation and
  // matched nothing else on the page: it applies the spread to the COST base while
  // revenue grows on the appropriation, so it printed $531,297 next to a $613,238 gap and
  // a $509,515 shortfall and invited exactly the question it got. A difference between
  // two numbers the reader can see is worth more than a more elegant derivation.
  const widening = Math.round(years[1].gap - years[0].gap)
  const map: Record<Verdict, { tone: string; head: string; body: string }> = {
    widening: {
      tone: 'var(--status-critical)',
      head: `Still widening — ${usd(widening)} bigger in FY${years[1].fy} than in `
        + `FY${years[0].fy}`,
      body: `Costs grow ${pct(blended)}. Revenue grows ${pct(revGrowth)} today, but that `
        + `decays to ${pct(longRun)} by FY${years[years.length - 1].fy} as a flat `
        + `new-growth figure becomes a smaller share of a bigger town — so `
        + `${pct(longRun)} is the rate that actually has to be beaten. While it is not, `
        + `the hole grows every year no matter what you take out of it, and every `
        + `one-time fix buys about twelve months.`,
    },
    held: {
      tone: 'var(--status-warning)',
      head: 'Held — the hole has stopped growing',
      body: `Costs now grow ${pct(blended)}, under the ${pct(longRun)} the town's revenue `
        + `settles at. There is still ${usdShort(years[0].gap)} to find in `
        + `FY${years[0].fy}, but it is a fixed amount now rather than a widening one — so `
        + `a one-time cut or a single override closes it and it stays closed. That order `
        + `is the whole thing: the same cut, made before the rate was fixed, buys a year.`,
    },
    solved: {
      tone: 'var(--status-good)',
      head: 'Sustainable',
      body: `Costs grow ${pct(blended)}, under the ${pct(longRun)} revenue settles at, `
        + `and there is no gap in any of the next ${years.length} years`
        + `${cut || overrideLevy ? ' — with the one-time money you found doing the rest' : ''}.`,
    },
  }
  const v = map[verdict]
  return (
    <div className="card p-4 sm:p-5 mb-4" style={{ borderColor: v.tone, borderWidth: 2 }}>
      <p className="text-[17px] sm:text-xl font-bold" style={{ color: v.tone }}>{v.head}</p>
      <p className="text-[14px] leading-relaxed mt-1.5">{v.body}</p>
    </div>
  )
}

/** Every year the chart covers, each one funded or not.
 *
 *  Was five squares against a twelve-year chart, which needed a cutoff line on the chart
 *  to explain the mismatch. Covering the same span instead removes the question: the
 *  squares and the curve are the same years, read two ways, and the strip is the index to
 *  the chart above it.
 *
 *  Deliberately small. It is the pinned element, so every pixel it takes is a pixel of
 *  controls the reader cannot see at the same time as the result — the year and the glyph
 *  carry it, and the amount appears only where there is room for it.
 *
 *  Never colour alone: glyph, amount where it fits, and full text for a screen reader. */
function YearStatus({ years, compact }: {
  years: ReturnType<typeof run>; compact?: boolean
}) {
  return (
    <div className={compact ? 'mb-2' : 'mb-3'}>
      <ol className="grid grid-cols-6 sm:grid-cols-12 gap-1"
        aria-label="Whether each year is funded">
        {years.map(y => {
          const short = y.gap > 0
          return (
            <li key={y.fy} className="rounded text-center py-1 px-0.5"
              title={short ? `FY${y.fy}: short by ${usd(y.gap)}` : `FY${y.fy}: funded`}
              style={{ background: short ? 'var(--status-critical)' : 'var(--status-good)',
                       color: '#fff' }}>
              <p className="text-[10px] font-bold leading-none opacity-90">FY{y.fy}</p>
              <p className="text-[11px] font-bold leading-none mt-0.5" aria-hidden="true">
                {short ? '\u2715' : '\u2713'}
              </p>
              <p className="hidden sm:block text-[10px] font-semibold tnum leading-none mt-0.5
                            truncate" aria-hidden="true">
                {short ? usdShort(y.gap) : 'ok'}
              </p>
              <span className="sr-only">
                {short ? `not funded, short by ${usd(y.gap)}` : 'funded'}
              </span>
            </li>
          )
        })}
      </ol>
      {!compact && (
        <p className="text-[12px] mt-2" style={{ color: 'var(--text-secondary)' }}>
          A green check means the year is <strong>funded</strong> &mdash; what the schools
          buy costs no more than the town can give them. Red means it is not, and by how
          much. Same years as the chart. Turning the first square green is easy; keeping
          the last one green is the hard part, and it is the difference between the two
          columns below.
        </p>
      )}
    </div>
  )
}

/** Cost against revenue, over long enough that an angle is visible as an angle. */
function Curves({ years, baseline, touched, compact, pinned, onTogglePin }: {
  years: ReturnType<typeof run>; baseline: ReturnType<typeof run>; touched: boolean
  compact?: boolean; pinned: boolean; onTogglePin: () => void
}) {
  const data = years.map((y, i) => ({
    fy: `FY${y.fy}`, cost: y.cost, revenue: y.revenue, base: baseline[i].cost,
  }))
  const lo = Math.min(...data.map(d => Math.min(d.revenue, d.cost))) * 0.97
  const hi = Math.max(...data.map(d => Math.max(d.base, d.cost))) * 1.02
  return (
    <div className={`card ${compact ? 'p-3' : 'p-4'}`}>
      <div className="flex items-center justify-end -mb-1">
        <button onClick={onTogglePin} aria-pressed={pinned}
          className="text-[11px] font-semibold px-2 py-1 rounded"
          style={{ color: pinned ? 'var(--series-cost)' : 'var(--text-muted)' }}>
          {pinned ? '\u25BC Unpin chart' : '\u25B2 Pin chart'}
        </button>
      </div>
      <div style={{ width: '100%', height: compact ? 168 : 300 }}>
        <ResponsiveContainer>
          <LineChart data={data} margin={{ top: 8, right: 12, bottom: 4, left: 4 }}>
            <CartesianGrid stroke="var(--grid)" vertical={false} />
            <XAxis dataKey="fy" tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
              stroke="var(--axis)" tickLine={false} interval="preserveStartEnd" />
            <YAxis domain={[lo, hi]} width={58}
              tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
              stroke="var(--axis)" tickLine={false} axisLine={false}
              tickFormatter={v => usdShort(v as number)} />
            <Tooltip
              contentStyle={{ background: 'var(--surface-1)', border: '1px solid var(--grid)',
                              borderRadius: 10, fontSize: 12 }}
              formatter={(v, n) => [usd(v as number),
                n === 'cost' ? 'Cost of today’s services'
                  : n === 'revenue' ? 'Revenue available' : 'Cost, as projected']} />
            <Legend verticalAlign="top" height={30} iconType="plainline"
              wrapperStyle={{ fontSize: 12, color: 'var(--text-secondary)' }}
              formatter={v => v === 'cost' ? 'Cost of today’s services'
                : v === 'revenue' ? 'Revenue available' : 'Cost, as projected'} />
            {touched && (
              <Line type="monotone" dataKey="base" stroke="var(--axis)" strokeWidth={1.5}
                strokeDasharray="4 4" dot={false} isAnimationActive={false} />
            )}
            <Line type="monotone" dataKey="cost" stroke="var(--series-cost)"
              strokeWidth={2.5} dot={false} isAnimationActive={false} />
            <Line type="monotone" dataKey="revenue" stroke="var(--series-revenue)"
              strokeWidth={2.5} dot={false} isAnimationActive={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
      {!compact && (
        <p className="text-[12px] mt-2" style={{ color: 'var(--text-muted)' }}>
          Cutting drops the blue line and leaves its angle alone, so it climbs back to the
          orange one at the same speed it did before. Changing a rate changes the angle.
        </p>
      )}
    </div>
  )
}

/** What the slider just did, in jobs, pay or coverage.
 *
 *  Appears only once a rate has been moved, because it is a statement about a change
 *  rather than about the budget. A percentage is not a proposal until somebody says what
 *  it costs the people inside it, and this is the only place on the site that does. */
function Consequence({ bucket, rate }: { bucket: Bucket; rate: number }) {
  const c = consequenceOf(bucket, rate)
  if (!c) return null
  return (
    <div className="mt-1.5 pl-2.5 text-[11px] leading-relaxed"
      style={{ borderLeft: '2px solid var(--series-cost)' }}>
      <p style={{ color: 'var(--text-primary)' }}>{c.text}</p>
      {c.limit && <p className="mt-0.5" style={{ color: 'var(--status-warning)' }}>{c.limit}</p>}
    </div>
  )
}

function Slider({ label, hint, value, min, max, step, onChange, display, changed, was }: {
  label: string; hint?: string; value: number; min: number; max: number; step: number
  onChange: (n: number) => void; display: string; changed?: boolean; was?: string
}) {
  return (
    <div>
      <div className="flex items-baseline justify-between gap-2">
        <label className="text-[13px] font-medium">
          {label}
          {hint && <span className="text-[11px] ml-1.5" style={{ color: 'var(--text-muted)' }}>
            {hint}</span>}
        </label>
        <span className="text-[13px] font-semibold tnum shrink-0"
          style={{ color: changed ? 'var(--series-cost)' : 'var(--text-primary)' }}>
          {display}
          {changed && was && (
            <span className="text-[11px] font-normal ml-1"
              style={{ color: 'var(--text-muted)' }}>was {was}</span>
          )}
        </span>
      </div>
      <input type="range" min={min} max={max} step={step} value={value}
        aria-label={label}
        onChange={e => onChange(Number(e.target.value))}
        className="w-full mt-1" />
    </div>
  )
}

import { useId, useState } from 'react'
import { usd, usdShort } from '../model/engine'
import {
  PACKAGES, HORIZONS, DEFAULT_RATES, DEFAULT_SCENARIO, LEVY_CAP, FOREVER_BAR, TODAY_GAP,
  buildScale, cutInThings, overrideOnAverageHome, longRunTarget, FEE_CEILING,
  STATE_AID_TRADE, STATE_AID, type Package,
} from '../model/rates'
import { ALREADY_CUT } from '../model/walk'
import { MODEL } from '../model/engine'

const pct = (x: number, d = 2) => `${(x * 100).toFixed(d)}%`
const TARGET = longRunTarget(DEFAULT_SCENARIO)

/** How many packages need nothing beyond the rates, and how many need less than one
 *  position's worth. Counted rather than asserted, so the sentence cannot drift away from
 *  the board underneath it. */
const needsNothing = (p: Package) =>
  (p.firstYears.cut ?? 1) < 1000
  && (p.firstYears.build ?? 0) - DEFAULT_SCENARIO.newGrowth < 1000
const FREE = PACKAGES.filter(needsNothing).length
const TINY = PACKAGES.filter(p => !needsNothing(p)
  && (p.firstYears.cut ?? Infinity) < 89_096).length
/** The three cheapest overrides on the board, which are the answer to "how big would the
 *  ballot question have to be" and are all a fraction of the one the town has refused. */
/* Above a threshold, not above zero: the solver bisects, so a package that needs no
 * override at all comes back a fraction of a cent above it rather than at it. */
const SHOWCASE = PACKAGES.filter(p => (p.firstYears.overrideTownwide ?? 0) > 1000)
  .sort((a, b) => (a.firstYears.overrideTownwide ?? 0) - (b.firstYears.overrideTownwide ?? 0))
  .slice(0, 3)
  .sort((a, b) => b.horizon - a.horizon)
const SPARE_PAY = PACKAGES.find(p => p.id === 'thirty-spare-pay')

/** Sending a package to one of the two boards.
 *
 *  A card can say a package holds and a reader can still not believe it, which is fair —
 *  this whole site is built on the idea that being shown beats being told. So each one
 *  can be dropped straight into the two pages that make it concrete: the curve, where the
 *  lines either cross or do not, and the budget builder, where the same package turns
 *  into named things next April. */
export type LoadPackage = (pkg: Package, to: 'curve' | 'adjust') => void

/** The combinations that hold, arranged by how long they hold for.
 *
 *  What was here before was seven single levers, five of which did not work. It answered
 *  a question nobody had — it takes a lot of room to demonstrate that pulling one lever
 *  is not enough, and a reader who wants to know what to *do* finishes it with nothing to
 *  do. A menu should be things somebody could order.
 *
 *  So every card is a package that keeps the gap shut for the horizon it is filed under,
 *  and the bands are horizons rather than verdicts, because five quiet years is a smaller
 *  ask than thirty and a town is entitled to know what the smaller ask costs. Within each
 *  band the cards differ in who is asked for what, which is the real decision — and the
 *  comparison makes its own argument without anybody having to assert it: sharing costs a
 *  fraction of what sparing either side costs, at every horizon, every time. */
export function Packages({ onLoad }: { onLoad?: LoadPackage } = {}) {
  return (
    <div>
      <div className="mb-4">
        <p className="text-xs font-semibold uppercase tracking-widest mb-2"
          style={{ color: 'var(--text-muted)' }}>The options</p>
        <h3 className="text-xl sm:text-2xl font-bold tracking-tight leading-tight">
          What actually holds, and for how long
        </h3>
        <p className="text-[14px] leading-relaxed mt-2 max-w-3xl"
          style={{ color: 'var(--text-secondary)' }}>
          Every package below keeps the gap shut for the number of years it is filed
          under &mdash; no cuts, no override cycle, nothing to come back to. They are
          grouped by how long they last rather than by how good they are, because{' '}
          <strong>five quiet years is a smaller ask than thirty and the town is entitled
          to know what the smaller ask costs</strong>. Within each band the packages differ
          in who is asked for what, which is the only part of this that is a decision
          rather than arithmetic.
        </p>
      </div>

      <div className="card p-4 sm:p-5 mb-5">
        <p className="text-[15px] leading-relaxed">
          <strong>Every package has two halves, and it needs both.</strong> The rates are
          what stops the gap growing: the weighted average of everything the district buys
          has to come under <strong className="tnum">{pct(TARGET)}</strong>, the rate the
          town&rsquo;s revenue settles at &mdash; or under{' '}
          <strong className="tnum">{pct(FOREVER_BAR, 1)}</strong>, the levy cap itself, for
          a package that never expires.
        </p>
        <p className="text-[13px] leading-relaxed mt-2" style={{ color: 'var(--text-secondary)' }}>
          Fixing a rate does not refund the year the town is already behind in, though, and
          FY28 starts {usd(TODAY_GAP)} short. So each package also names what covers the
          early years, and there are four ways to do it: <strong>build, pass one override,
          raise user fees, or cut once</strong>. They are alternatives rather than a list
          &mdash; any one of them does it, and <strong>three of the four take nothing out
          of a classroom</strong>. The cut is flagged and listed last on every card,
          because a list of four that contains a cut reads as four cuts, and it is not.
        </p>
      </div>

      {/* The question the whole section exists to answer, answered before the cards
          rather than left to be inferred from ten of them. */}
      <div className="card p-4 sm:p-5 mb-5" style={{ borderColor: 'var(--status-good)' }}>
        <h4 className="text-[16px] font-bold mb-2">
          Does any of this mean more cuts? No &mdash; not one of them.
        </h4>
        <p className="text-[13px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
          Every package below can be covered without cutting anything. The cut is one of
          four interchangeable ways to pay for the first years, and the other three &mdash;
          building, an override, or user fees &mdash; take nothing out of a
          classroom.{' '}
          <strong>{FREE} of the {PACKAGES.length} needs nothing at all</strong>, and{' '}
          {TINY} more need less than one position&rsquo;s worth, which is attrition rather
          than a cut list.
        </p>
        <p className="text-[13px] leading-relaxed mt-2" style={{ color: 'var(--text-secondary)' }}>
          And the override is not the large one people are picturing, provided the package
          shares the change. Lunenburg rejected a{' '}
          {usdShort(MODEL.facts.overrideQ1.amount)} override &mdash;{' '}
          {usd(Math.round(MODEL.facts.tier1TaxIncrease))} a year on the average home,{' '}
          {MODEL.facts.overrideQ1.yes} to {MODEL.facts.overrideQ1.no}. Against that:
        </p>
        <ul className="grid gap-2 sm:grid-cols-3 mt-2">
          {SHOWCASE.map(p => (
            <li key={p.id} className="rounded-lg p-2.5" style={{ background: 'var(--surface-3)' }}>
              <p className="text-xl font-bold tnum leading-none"
                style={{ color: 'var(--status-good)' }}>
                {usd(overrideOnAverageHome(p.firstYears.overrideTownwide ?? 0))}
                <span className="text-[12px] font-normal"> a year</span>
              </p>
              <p className="text-[12px] leading-snug mt-1">
                on the average home, for{' '}
                <strong>{p.forEver ? 'good' : `${p.horizon} quiet years`}</strong>
              </p>
              <p className="text-[11px] leading-snug mt-0.5" style={{ color: 'var(--text-muted)' }}>
                {p.label} &mdash; {usdShort(p.firstYears.overrideTownwide ?? 0)} townwide
              </p>
            </li>
          ))}
        </ul>
        <p className="text-[12px] leading-relaxed mt-2" style={{ color: 'var(--text-muted)' }}>
          What costs real money is sparing one side entirely. Leaving pay alone for a
          generation needs{' '}
          {usd(overrideOnAverageHome(SPARE_PAY?.firstYears.overrideTownwide ?? 0))} a year
          on the average home &mdash; several times the override the town has already
          turned down. Possible without a cut is not the same as easy without a cut, and
          the difference between those two columns is entirely about how widely the change
          is shared.
        </p>
      </div>

      {HORIZONS.map(band => (
        <section key={band.h} className="mb-7">
          <div className="flex flex-wrap items-baseline gap-x-3 gap-y-0.5">
            <h4 className="text-[17px] font-bold">{band.title}</h4>
            <p className="text-[13px]" style={{ color: 'var(--text-secondary)' }}>
              {band.sub}
            </p>
          </div>
          <div className="space-y-3 mt-3">
            {PACKAGES.filter(p => p.horizon === band.h).map(p => (
              <PackageCard key={p.id} pkg={p} onLoad={onLoad} />
            ))}
          </div>
        </section>
      ))}

      <StateAidTrade />

      <div className="card p-4 sm:p-5 mt-3">
        <h4 className="text-[15px] font-bold mb-2">The pattern, in case it is not obvious</h4>
        <p className="text-[13px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
          Read down the first band. Sharing the change between salaries and insurance
          buys five years for a fraction of what either side costs on its own &mdash; and
          the two sparing packages cost almost exactly the same as each other, which is the
          clearest evidence on this page that those two lines are interchangeable as
          arithmetic and only different as politics. Then read down the bands: the same
          rates held for longer do not need salaries held any lower, they need more of the
          head start bought up front. And at the bottom, the one package that never
          reopens needs no cheque, no override and no building &mdash; only the two rates,
          moved further than anybody has yet proposed moving them.
        </p>
      </div>
    </div>
  )
}

function PackageCard({ pkg: p, onLoad }: { pkg: Package; onLoad?: LoadPackage }) {
  const f = p.firstYears
  const extraBuild = (f.build ?? 0) - DEFAULT_SCENARIO.newGrowth
  const free = (f.cut ?? 1) < 1000 && extraBuild < 1000
  return (
    <article className="card p-4 sm:p-5">
      <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
        <h5 className="text-[16px] font-bold leading-snug">{p.label}</h5>
        <span className="flex items-baseline gap-2.5 shrink-0">
          {p.ch70 !== null && (
            <span className="text-[10px] font-bold uppercase tracking-widest whitespace-nowrap"
              style={{ color: 'var(--status-warning)' }}>
              <span aria-hidden="true">◇ </span>Needs the State House
            </span>
          )}
          <span className="inline-flex items-center gap-1.5 text-[12px] font-bold"
            style={{ color: 'var(--status-good)' }}>
            <span aria-hidden="true">✓</span>
            {p.forEver ? 'Never reopens' : `Holds ${p.horizon} years`}
          </span>
        </span>
      </div>
      <p className="text-[13px] leading-snug mt-1" style={{ color: 'var(--text-secondary)' }}>
        {p.angle}
      </p>

      <div className="grid gap-4 sm:gap-5 sm:grid-cols-2 mt-3">
        {/* ---- half one: the rates, which are what stop it growing ---- */}
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-widest mb-1.5"
            style={{ color: 'var(--text-muted)' }}>The rates</p>
          <dl className="text-[13px]">
            <Rate k="Salaries" was={DEFAULT_RATES.salaries} now={p.rates.salaries} />
            <Rate k="Health insurance" was={DEFAULT_RATES.health} now={p.rates.health} />
            <Rate k="Transport, special education, utilities, supplies"
              was={null} now={LEVY_CAP} note="held to the levy cap" />
            {p.ch70 !== null && (
              <Rate k="Chapter 70, at the State House"
                was={STATE_AID.ch70Assumed} now={p.ch70}
                note="not the town’s to decide" />
            )}
          </dl>
          <p className="text-[12px] leading-relaxed mt-2 pt-2 border-t"
            style={{ borderColor: 'var(--grid)', color: 'var(--text-secondary)' }}>
            <strong className="tnum" style={{ color: 'var(--text-primary)' }}>
              Costs grow {pct(p.blended)}
            </strong>
            {/* Three different reasons a package does or does not expire, and they are
                not interchangeable. Branching on `forEver` alone claimed the state
                packages were under the levy cap, which they are nowhere near: they never
                reopen because aid is compounding faster than the gap, which is a promise
                somebody else has to keep. */}
            {p.blended <= FOREVER_BAR + 0.0002
              ? <> &mdash; under the {pct(FOREVER_BAR, 1)} levy cap, which is why nothing
                  has to keep going right afterwards.</>
              : p.ch70 !== null
              ? <> &mdash; well above the {pct(TARGET)} the town&rsquo;s own revenue
                  settles at. It never reopens because state aid is compounding faster
                  than the gap, which is a promise somebody outside this town has to go
                  on keeping.</>
              : <> &mdash; still above the {pct(TARGET)} the town&rsquo;s revenue settles
                  at, which is why this one has a horizon rather than no end date.</>}
          </p>
        </div>

        {/* ---- half two: the early years, which are a level and not a rate ---- */}
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-widest mb-1.5"
            style={{ color: 'var(--text-muted)' }}>
            {free ? 'And nothing else' : 'And any ONE of these four, once'}
          </p>
          {free ? (
            <p className="text-[13px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
              No cut, no override, and no more building than the town already does. The
              rates alone carry it.
            </p>
          ) : (
            <>
              <ul className="text-[13px]">
                <Option n={1} k="Build" v={f.buildings === null || extraBuild < 1000 ? null
                  : `${f.buildings.toFixed(0)} buildings a year`}
                  sub={f.build === null ? 'no build rate reaches this horizon'
                    : `${usdShort(f.build)} of new growth a year against `
                      + `${usdShort(DEFAULT_SCENARIO.newGrowth)} today — nobody in a `
                      + 'classroom pays for this one'} />
                <Option n={2} k="Pass one override"
                  v={f.overrideTownwide === null ? null : usdShort(f.overrideTownwide)}
                  sub={f.overrideTownwide === null
                    ? 'no override of any size reaches this horizon'
                    : `townwide — about ${usd(overrideOnAverageHome(f.overrideTownwide))} a `
                      + 'year on the average home, permanently. Written for the schools '
                      + `alone it is ${usdShort(f.override ?? 0)}`} />
                <Option n={3} k="Raise user fees"
                  v={f.fees === null ? null : usdShort(f.fees)}
                  sub={f.fees === null
                    ? `out of reach — every fee at the level that raises the most brings in `
                      + `${usdShort(FEE_CEILING.total)} a year in total, and a fee is flat `
                      + `where a cut compounds`
                    : `${((f.feeShareOfCeiling ?? 0) * 100).toFixed(0)}% of everything the `
                      + `three fees could ever raise (${usdShort(FEE_CEILING.total)}): `
                      + FEE_CEILING.each.map(e => `${e.name.toLowerCase()} `
                        + `${e.currentFee ? `from ${usd(e.currentFee)}` : 'from nothing'} `
                        + `toward ${usd(e.peakFee ?? 0)}`).join(', ')} />
                <Option n={4} k="Cut once, and keep it cut"
                  tone={cutHurts(f.cut) ? 'critical' : undefined}
                  flag={cutHurts(f.cut) ? 'costs positions' : undefined}
                  v={f.cut === null ? null : usdShort(f.cut)} sub={cutMeans(f.cut)} last />
              </ul>
              {/* Said out loud, and the cut put last, because a list of three that
                  contains a cut reads as a list of three cuts — and because a page whose
                  whole purpose is to end the cutting should not open every card with one. */}
              <p className="text-[12px] leading-snug mt-2 pt-2 border-t"
                style={{ borderColor: 'var(--grid)', color: 'var(--text-secondary)' }}>
                <strong>Any one of the four does it</strong>, and the first three cost
                nobody a job. {cutHurts(f.cut)
                  ? <>The fourth is flagged and listed last for a reason &mdash; but note
                      what makes it different from the cuts the town keeps making:{' '}
                      <strong>with the rates fixed first, it is the last one</strong>.
                      Today&rsquo;s cuts buy twelve months because the rates underneath
                      them never moved.</>
                  : <>The fourth is small enough here to find in attrition.</>}
              </p>
            </>
          )}
        </div>
      </div>

      <dl className="text-[13px] leading-relaxed mt-3 pt-3 border-t"
        style={{ borderColor: 'var(--grid)' }}>
        <dt className="text-[11px] font-semibold uppercase tracking-widest"
          style={{ color: 'var(--text-muted)' }}>Who has to say yes</dt>
        <dd className="mt-0.5" style={{ color: 'var(--text-secondary)' }}>{p.whoSaysYes}</dd>
      </dl>
      <p className="text-[13px] leading-relaxed mt-2" style={{ color: 'var(--text-secondary)' }}>
        {p.note}
      </p>

      {extraBuild > 1000 && f.build !== null && <BuildScale newGrowth={f.build} />}

      {onLoad && (
        <div className="flex flex-wrap gap-x-4 gap-y-1 mt-4 pt-3 border-t"
          style={{ borderColor: 'var(--grid)' }}>
          <button onClick={() => onLoad(p, 'curve')}
            className="text-[12px] font-semibold" style={{ color: 'var(--series-cost)' }}>
            See this package on the curve &rarr;
          </button>
          <button onClick={() => onLoad(p, 'adjust')}
            className="text-[12px] font-semibold" style={{ color: 'var(--series-cost)' }}>
            Load it into the budget builder &rarr;
          </button>
        </div>
      )}
    </article>
  )
}

/** What the State House is worth to a package, which is not what it is worth alone.
 *
 *  Chapter 70 on its own does nothing here and the site says so at length elsewhere: aid
 *  ramps and the hole does not wait, so at any growth rate you like the town is short next
 *  April. That finding is true and it has been quietly doing the wrong work — it reads as
 *  "the state cannot help", when what it means is "the state cannot finish".
 *
 *  Set beside a package the arithmetic inverts. The same local agreement that needs a
 *  three-hundred-thousand-dollar cheque at today's aid growth needs nothing at all if
 *  Chapter 70 grows at a rate that a good year already looks like — because the package
 *  has already flattened the curve, and aid only has to cover the head start. It is the
 *  cheapest thing on this page for the town and the only one nobody here can vote for. */
function StateAidTrade() {
  const { reference, rows } = STATE_AID_TRADE
  return (
    <div className="card p-4 sm:p-5 mb-3">
      <p className="text-[11px] font-semibold uppercase tracking-widest"
        style={{ color: 'var(--text-muted)' }}>The one nobody here can vote for</p>
      <h4 className="text-[16px] font-bold mt-0.5 mb-2">
        And what the state does changes every number above
      </h4>
      <p className="text-[13px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
        Chapter 70 cannot fix this on its own &mdash; aid ramps and the gap does not wait,
        so at any growth rate at all the town is still short next April. What it can do is
        make the local ask disappear. Here is the <strong>{reference.label.toLowerCase()}</strong>{' '}
        package from the {reference.horizon}-year band, priced at each rate state aid might
        grow at. All state aid is {pct(STATE_AID.shareOfTownRevenue, 0)} of what the town
        collects and Chapter 70 is {pct(STATE_AID.ch70Share, 0)} of that, so both rates are
        shown: the delegation is asked for the first, and the projection moves the second.
      </p>
      <table className="stack w-full text-[13px] tnum mt-3">
        <caption className="sr-only">
          What the {reference.label} package needs at each rate of state aid growth
        </caption>
        <thead>
          <tr className="text-left" style={{ color: 'var(--text-muted)' }}>
            <th className="font-semibold py-1.5">If Chapter 70 grows</th>
            <th className="font-semibold py-1.5">All state aid</th>
            <th className="font-semibold py-1.5 text-right">The package then needs</th>
            <th className="font-semibold py-1.5 text-right">Or holds free for</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(r => {
            const solved = r.freeYears >= 30
            return (
              <tr key={r.aid} className="border-t" style={{ borderColor: 'var(--grid)' }}>
                <td className="rowhead py-2 font-semibold">
                  {pct(r.ch70, 1)}
                  {r.aid === STATE_AID_TRADE.baseline && (
                    <span className="text-[11px] font-normal ml-1.5"
                      style={{ color: 'var(--text-muted)' }}>what is assumed today</span>
                  )}
                </td>
                <td data-label="All state aid" className="py-2">{pct(r.aid, 1)}</td>
                <td data-label="The package then needs" className="py-2 text-right font-semibold"
                  style={{ color: solved ? 'var(--status-good)'
                    : r.cut === null ? 'var(--text-muted)' : 'var(--text-primary)' }}>
                  {solved ? 'nothing at all' : r.cut === null ? '—' : usdShort(r.cut)}
                </td>
                <td data-label="Or holds free for" className="py-2 text-right"
                  style={{ color: solved ? 'var(--status-good)' : 'var(--text-secondary)' }}>
                  {r.freeYears === 0 ? 'not on its own'
                    : r.freeYears >= 60 ? 'ever' : `${r.freeYears} years`}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
      <p className="text-[12px] leading-relaxed mt-3 pt-3 border-t"
        style={{ borderColor: 'var(--grid)' }}>
        <strong>Read the fourth row.</strong> With Chapter 70 at{' '}
        {pct(rows[3].ch70, 1)} &mdash; not a rescue, a decent year &mdash; that package
        holds with <strong>no cut, no override, no fee and no extra building at all</strong>.
        The town still has to make the local agreement: the state is what removes the
        cheque, not what removes the decision. Which is the honest form of the ask to take
        to the delegation, and a great deal more persuasive than asking them to fix it.
      </p>
    </div>
  )
}

/** Whether a package's cut is big enough to be worth alarming somebody about.
 *
 *  Two of the packages need a cheque of seventeen and fifty-six thousand dollars, which is
 *  a fifth of a position and half of one. Painting those red would spend the reader's
 *  alarm on nothing and leave none for the four-and-a-half-million one. One position is
 *  the threshold because one position is a person. */
const cutHurts = (cut: number | null) => cut !== null && cut >= 89_096

/** A cut, said in the only units anybody can check it against.
 *
 *  "Cut once" was the label and it was doing real damage: it reads as a bad month, when
 *  what the model means is a reduction adopted in one budget that stays out of every
 *  budget after it — which is exactly why it works at all, since money that never comes
 *  back never gets its raise either.
 *
 *  Three comparisons, and the third is the one that decides whether a number is a plan.
 *  Everything the district could cut outside a classroom — every sport, the band and the
 *  clubs, most of technology, and every administrator the law allows it to lose — comes
 *  to a little over a million and a half. Past that the arithmetic is still fine and
 *  there is nothing left to take it from, so the balance comes out of teaching whatever
 *  anybody intended. A card that prints $4.65M without saying so is not being honest
 *  about what it is proposing. */
function cutMeans(amount: number | null): string {
  if (amount === null) return 'no cut of any size reaches this horizon'
  const c = cutInThings(amount)
  const vsLast = amount / ALREADY_CUT.cost
  const scale = c.positions < 1
    ? `less than one position — ${(c.shareOfBudget * 100).toFixed(1)}% of the school budget`
    : `about ${c.positions.toFixed(0)} positions at ${usd(89_096)} each, gone and staying gone`

  const context = c.beyondDiscretionary
    ? `That is more than every sport, club, band, most of technology and every `
      + `administrator the law allows, combined (${usdShort(c.discretionaryTotal)}). `
      + `The balance has to come out of classrooms.`
    : vsLast > 0.85 && vsLast < 1.2
      ? `About the size of the cut the town made for FY${27} — ${usdShort(ALREADY_CUT.cost)} `
        + `and ${ALREADY_CUT.fte} positions — done once more and left in place.`
      : `${(c.shareOfDiscretionary * 100).toFixed(0)}% of everything the district could cut `
        + `outside a classroom (${usdShort(c.discretionaryTotal)}: every sport, the band `
        + `and clubs, most of technology, every administrator the law allows).`

  return `Not a lean year — a reduction adopted once that stays out of the budget for `
    + `good: ${scale}. ${context}`
}

/** One rate, with what it is today beside it — a package is a set of changes, and a
 *  number on its own does not say whether it is one. */
function Rate({ k, was, now, note }: {
  k: string; was: number | null; now: number; note?: string
}) {
  const moved = was !== null && Math.abs(was - now) > 1e-9
  return (
    <div className="flex items-baseline justify-between gap-3 py-1 border-b last:border-b-0"
      style={{ borderColor: 'var(--grid)' }}>
      <dt className="leading-snug min-w-0">{k}</dt>
      <dd className="tnum font-semibold shrink-0 text-right">
        {moved && (
          <span className="font-normal" style={{ color: 'var(--text-muted)' }}>
            {pct(was, 1)} <span aria-hidden="true">&rarr;</span>{' '}
          </span>
        )}
        <span style={{ color: moved ? 'var(--status-good)' : 'var(--text-primary)' }}>
          {pct(now, 1)}
        </span>
        {(note || !moved) && (
          <span className="block text-[11px] font-normal" style={{ color: 'var(--text-muted)' }}>
            {note ?? 'unchanged'}
          </span>
        )}
      </dd>
    </div>
  )
}

function Option({ n, k, v, sub, last, tone, flag }: {
  /** Numbered, because "any one of these" was being read as "all of these": a list of
   *  three things a package needs, rather than three ways of doing the same one thing.
   *  A number in front of each is the cheapest possible way to say they are a choice. */
  n: number
  k: string; v: string | null; sub: string; last?: boolean
  /** Marked where the choice costs somebody their job, so it is never mistaken for a
   *  neutral third of a list. Color is never the only signal — the flag says it too. */
  tone?: 'critical'
  flag?: string
}) {
  const color = v === null ? 'var(--text-muted)'
    : tone === 'critical' ? 'var(--status-critical)' : 'var(--text-primary)'
  return (
    <li className={`py-1.5 ${last ? '' : 'border-b'}`} style={{ borderColor: 'var(--grid)' }}>
      <span className="flex items-baseline justify-between gap-3">
        <span className="leading-snug min-w-0">
          <span className="text-[10px] font-bold uppercase tracking-widest mr-1.5"
            style={{ color: 'var(--series-cost)' }}>Option {n}</span>
          {k}
          {flag && v !== null && (
            <span className="ml-1.5 text-[10px] font-bold uppercase tracking-widest
                             whitespace-nowrap"
              style={{ color: 'var(--status-critical)' }}>
              <span aria-hidden="true">&#9888; </span>{flag}
            </span>
          )}
        </span>
        <span className="font-bold tnum shrink-0" style={{ color: color }}>
          {v ?? 'not possible'}
        </span>
      </span>
      <span className="block text-[11px] leading-snug mt-0.5"
        style={{ color: tone === 'critical' && v !== null
          ? 'var(--status-critical)' : 'var(--text-muted)' }}>{sub}</span>
    </li>
  )
}

/** How much building a package is actually asking for.
 *
 *  A build rate in levy dollars is unarguable, which is the problem: dollars a year sound
 *  like a budget line rather than like a construction program. In buildings, against
 *  the best year the town has ever had and against everything commercial it has
 *  accumulated in its entire history, the ask sizes itself.
 *
 *  Collapsed by default. The card already asks a reader to hold a set of rates, three
 *  alternative cheques and a paragraph of who-says-yes; a fourth block of figures
 *  arriving unbidden is where a card stops being read. The one line that survives the
 *  collapse is the one that sizes the ask. */
function BuildScale({ newGrowth }: { newGrowth: number }) {
  const b = buildScale(newGrowth)
  const heavy = b.timesBest >= 2
  const [open, setOpen] = useState(false)
  const panel = useId()

  return (
    <div className="mt-3 pt-3 border-t" style={{ borderColor: 'var(--grid)' }}>
      <button onClick={() => setOpen(o => !o)} aria-expanded={open} aria-controls={panel}
        className="w-full flex flex-wrap items-baseline justify-between gap-x-3 gap-y-0.5
                   text-left">
        <span className="text-[11px] font-semibold uppercase tracking-widest"
          style={{ color: 'var(--text-muted)' }}>
          How much building that is
        </span>
        <span className="text-[11px] font-semibold shrink-0"
          style={{ color: 'var(--series-cost)' }}>{open ? 'Hide' : 'Show'}</span>
        <span className="w-full text-[13px] leading-snug">
          <strong style={{ color: heavy ? 'var(--status-critical)' : 'var(--text-primary)' }}>
            {b.buildingsPerYear.toFixed(0)} new buildings a year, one every {b.everyDays}{' '}
            {b.everyDays === 1 ? 'day' : 'days'}
          </strong>
          <span style={{ color: 'var(--text-secondary)' }}>
            {' '}&mdash; {b.timesToday.toFixed(1)}× today&rsquo;s build rate, and{' '}
            {b.timesBest.toFixed(1)}× the best year the town has ever had.
          </span>
        </span>
      </button>

      {open && <div id={panel} className="mt-3">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Scale v={`${b.timesToday.toFixed(1)}×`} k="today’s build rate"
            sub={`${usdShort(b.newGrowth)} a year against ${usdShort(DEFAULT_SCENARIO.newGrowth)}`}
            heavy={heavy} />
          <Scale v={`${b.timesBest.toFixed(1)}×`} k="the best year the town has ever had"
            sub={`FY${b.bestFy} added ${usdShort(b.bestAmount)}`} heavy={heavy} />
          <Scale v={b.buildingsPerYear.toFixed(0)} k="new buildings a year, every year"
            sub={`one every ${b.everyDays} days — ${b.developments.toFixed(0)} developments’ worth`}
            heavy={heavy} />
          <Scale v={`${b.buildingsInFive}`} k="new buildings over five years"
            sub={`the town has ${b.existingCount} commercial properties in total, worth `
              + `${usdShort(b.existingBase)}, accumulated since it was founded`}
            heavy={heavy} />
        </div>

        <div className="mt-3 rounded-lg overflow-hidden" style={{ background: 'var(--surface-3)' }}>
          <p className="text-[12px] font-semibold px-3 pt-2.5 pb-1">
            What {b.developments.toFixed(0)} developments a year is, in actual buildings
          </p>
          <ul>
            {b.each.map((e, i) => (
              <li key={e.short}
                className="flex items-baseline justify-between gap-3 px-3 py-1.5"
                style={{ borderTop: i ? '1px solid var(--grid)' : undefined }}>
                <span className="text-[12px] leading-snug min-w-0">
                  {e.short}
                  <span className="ml-1.5 text-[11px]" style={{ color: 'var(--text-muted)' }}>
                    {usdShort(e.unit)} each
                  </span>
                </span>
                <span className="text-[12px] font-semibold tnum shrink-0">
                  {e.perYear.toFixed(1)}
                  <span className="font-normal text-[11px]"> a year</span>
                </span>
              </li>
            ))}
            <li className="flex items-baseline justify-between gap-3 px-3 py-1.5"
              style={{ borderTop: '1px solid var(--grid)' }}>
              <span className="text-[12px] font-semibold">Every year</span>
              <span className="text-[12px] font-bold tnum shrink-0">
                {b.buildingsPerYear.toFixed(0)}
                <span className="font-normal text-[11px]"> buildings</span>
              </span>
            </li>
          </ul>
        </div>
        <p className="text-[11px] mt-1.5" style={{ color: 'var(--text-muted)' }}>
          A &ldquo;development&rdquo; here is {usdShort(3_005_000)} of mixed new value,
          which is more than one building &mdash; so the building count runs about{' '}
          {(b.buildingsPerYear / b.developments).toFixed(1)}× the development count. Same
          mix and same archetype the development page uses.
        </p>
      </div>}
    </div>
  )
}

function Scale({ v, k, sub, heavy }: {
  v: string; k: string; sub: string; heavy: boolean
}) {
  return (
    <div className="rounded-lg p-2.5" style={{ background: 'var(--surface-3)' }}>
      <p className="text-xl font-bold tnum leading-none"
        style={{ color: heavy ? 'var(--status-critical)' : 'var(--text-primary)' }}>{v}</p>
      <p className="text-[12px] font-medium leading-snug mt-1">{k}</p>
      <p className="text-[11px] leading-snug mt-0.5" style={{ color: 'var(--text-muted)' }}>
        {sub}
      </p>
    </div>
  )
}

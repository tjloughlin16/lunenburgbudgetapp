import { useMemo } from 'react'
import {
  ComposedChart, Line, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer,
} from 'recharts'
import {
  MODEL, project, runCascade, usd, usdShort, type Assumptions,
} from '../model/engine'

const A = MODEL.assumptions
const T = MODEL.taxBase
const LEVY_CAP = 0.025

const BUCKETS: { key: keyof Assumptions; label: string; note: string }[] = [
  { key: 'salaries', label: 'Salaries', note: 'Collectively bargained' },
  { key: 'health', label: 'Health insurance', note: 'Set by the insurance market' },
  { key: 'transport', label: 'Transportation', note: 'Contracted, fuel-exposed' },
  { key: 'sped_tuition', label: 'Out-of-district SPED', note: 'Set by law and by placement' },
  { key: 'utilities', label: 'Utilities', note: 'Market' },
  { key: 'other', label: 'Everything else', note: 'The only genuinely discretionary part' },
]

/** Why the gap reopens every year, and what it would actually take to stop it.
 *
 *  Every other part of this tool answers "what do we do about FY28". This one answers the
 *  question underneath it: why is there an FY28 problem at all, and why did closing FY27
 *  not fix it. The answer is two growth rates, and it is the single most important fact
 *  in the whole projection. */
export function Structural() {
  const base = useMemo(() => project(15, A), [])
  const expense = MODEL.expenseBase as Record<string, number>
  const total = Object.values(expense).reduce((s, v) => s + v, 0)
  const blended = BUCKETS.reduce(
    (s, b) => s + (expense[b.key] / total) * (A[b.key] as number), 0)
  const maxRate = Math.max(...BUCKETS.map(b => A[b.key] as number))

  /** Years fully covered by ONE override — a permanent lift that then grows with the
   *  appropriation, which is what a single ballot question actually buys. */
  const singleOverride = (x: number) => {
    let lift = x
    for (let i = 0; i < base.length; i++) {
      if (base[i].deficit - lift > 0) return i
      lift *= 1 + base[i].growthRate
    }
    return base.length
  }
  /** Years fully covered by building at a sustained rate, forever. */
  const sustained = (value: number) => {
    const d = project(15, { ...A, new_growth: (value * T.rate) / 1000 })
    const i = d.findIndex(y => y.deficit > 0)
    return i === -1 ? 15 : i
  }
  const mix = T.archetypes.find(a => a.id === 'mix')?.value ?? 3_005_000
  const bentHealth = project(10, { ...A, health: 0.04 })

  // Cutting does not slow the gap — it converts a compounding number into a recurring
  // one, and spends the program catalog doing it. The cascade uses the School
  // Committee's own revealed ranking; a different ranking changes what is lost, not the
  // arithmetic.
  const casc = useMemo(
    () => runCascade(MODEL.presets.school_committee.order, A, 10), [])
  // The projection's "deficit" is NOT that year's fresh shortfall — it is the total
  // permanent new revenue that must be in place by then, because level service is
  // measured against a revenue line that never rose. The fresh amount is the year-on-year
  // increment, net of the growth the previously-funded money already provides.
  const funding = base.slice(0, 10).map((y, i) => ({
    fy: y.fy,
    cumulative: y.deficit,
    fresh: Math.round(i === 0
      ? y.deficit
      : y.deficit - base[i - 1].deficit * (1 + y.growthRate)),
  }))
  const exhausted = casc.find(y => y.unclosed > 0)
  const cutting = casc.filter(y => y.cutTotal > 0)
  const recurring = cutting.reduce((s2, y) => s2 + y.deficit, 0) / cutting.length
  const cumCut = casc.reduce((s2, y) => s2 + y.cutTotal, 0)
  const cumFte = casc[casc.length - 1].cumFte

  // The gap is a rate; the cuts are a stock. Holding one flat is what makes the other
  // climb, and that inverse is the thing residents actually live through.
  // The denominator has to be what the cascade can ACTUALLY reach. Counting the school
  // nurse, special education above the legal minimum and SPED paraprofessionals — which
  // are mandate 'legal' and never cut — inflated it by $439,203 and quietly understated
  // how complete the damage is.
  const pool = MODEL.programs
    .filter(p => (p.status === 'funded' || p.status === 'restoring')
      && p.mandate !== 'legal')
    .reduce((s2, p) => s2 + p.cost * (p.repeatable ?? 1), 0)
  const degradation = casc.map((y, i) => ({
    fy: y.fy,
    gap: Math.round(y.deficit),
    spent: Math.round(casc.slice(0, i + 1).reduce((s2, c) => s2 + c.cutTotal, 0)),
    pct: Math.round((casc.slice(0, i + 1).reduce((s2, c) => s2 + c.cutTotal, 0) / pool) * 100),
  }))
  const atWall = degradation[(exhausted
    ? casc.findIndex(y => y.unclosed > 0) : 5)] ?? degradation[5]
  const atWallPct = atWall.pct
  // What the funded route costs a homeowner: the whole accumulated levy increase, spread
  // over the tax base, on an average assessment.
  const billImpact = Math.round(
    (T.avgHomeValue * ((base[9].deficit * 1000) / T.totalValue)) / 1000)

  // The floor. Only a sliver of a school budget is ever genuinely on the table: the
  // catalogue this tool can cut is 14.8% of the appropriation, and a piece of even that
  // is legally mandated. Everything else — core teaching, most special education,
  // transport, utilities, benefits — is never offered as a cut by anyone.
  const approp = MODEL.fy27.lps_appropriation + MODEL.fy27.stm_appropriation
  const inCatalogue = MODEL.programs
    .filter(p => p.status === 'funded' || p.status === 'restoring')
    .reduce((s2, p) => s2 + p.cost * (p.repeatable ?? 1), 0)
  const mandatedItems = MODEL.programs
    .filter(p => (p.status === 'funded' || p.status === 'restoring')
      && p.mandate === 'legal')
  // Legally required and NOT currently funded — the sharpest fact on this page.
  const mandatedUnfunded = MODEL.programs
    .filter(p => p.status === 'unfunded' && p.mandate === 'legal')
  const contractItems = MODEL.programs
    .filter(p => (p.status === 'funded' || p.status === 'restoring')
      && p.mandate === 'contract')
  const expenseTotal = Object.values(expense).reduce((a, b) => a + b, 0)
  const mandatedInCatalogue = mandatedItems
    .reduce((s2, p) => s2 + p.cost * (p.repeatable ?? 1), 0)
  const floor = approp - inCatalogue + mandatedInCatalogue
  // Discretionary share of the budget, year by year, as the cuts land.
  const budgetMix = casc.map((y, i) => {
    const left = Math.max(0, inCatalogue - mandatedInCatalogue
      - casc.slice(0, i + 1).reduce((s2, c) => s2 + c.cutTotal, 0))
    const budget = base[i].levelService
    return {
      fy: y.fy,
      discretionary: +((left / budget) * 100).toFixed(1),
      locked: +(100 - (left / budget) * 100).toFixed(1),
    }
  })

  return (
    <div>
      {/* ---- the two rates ---- */}
      <div className="grid gap-3 sm:grid-cols-3 mb-8">
        <div className="card p-5">
          <p className="text-[11px] font-semibold uppercase tracking-widest mb-1"
            style={{ color: 'var(--text-muted)' }}>School costs rise</p>
          <p className="text-4xl font-bold tnum leading-none"
            style={{ color: 'var(--status-critical)' }}>{(blended * 100).toFixed(2)}%</p>
          <p className="text-[12px] mt-2" style={{ color: 'var(--text-secondary)' }}>
            a year, blended across everything the district buys
          </p>
        </div>
        <div className="card p-5">
          <p className="text-[11px] font-semibold uppercase tracking-widest mb-1"
            style={{ color: 'var(--text-muted)' }}>Revenue may rise</p>
          <p className="text-4xl font-bold tnum leading-none">2.50%</p>
          <p className="text-[12px] mt-2" style={{ color: 'var(--text-secondary)' }}>
            a year, by Proposition 2&frac12;, plus whatever is newly built
          </p>
        </div>
        <div className="card p-5" style={{ background: 'var(--surface-3)' }}>
          <p className="text-[11px] font-semibold uppercase tracking-widest mb-1"
            style={{ color: 'var(--text-muted)' }}>Which leaves</p>
          <p className="text-4xl font-bold tnum leading-none"
            style={{ color: 'var(--status-critical)' }}>
            {((blended - LEVY_CAP) * 100).toFixed(2)}
            <span className="text-lg font-normal"> pts</span>
          </p>
          <p className="text-[12px] mt-2" style={{ color: 'var(--text-secondary)' }}>
            short every year, compounding. Nobody overspent — these are simply two
            different numbers.
          </p>
        </div>
      </div>

      {/* ---- where the 4.94% comes from ---- */}
      <h3 className="text-sm font-bold mb-1">Where the {(blended * 100).toFixed(2)}% comes from</h3>
      <p className="text-[13px] mb-4 max-w-3xl" style={{ color: 'var(--text-secondary)' }}>
        The bar is each item&rsquo;s growth rate; the number beside it is how much of the
        budget it is. The dotted line is the 2&frac12;% the town&rsquo;s revenue is allowed
        to grow. Only one line on this list sits under it, and it is the smallest.
      </p>
      <ul className="space-y-2 mb-8">
        {BUCKETS.map(b => {
          const rate = A[b.key] as number
          const shareOf = expense[b.key] / total
          return (
            <li key={b.key} className="flex items-center gap-3">
              <span className="w-40 sm:w-52 shrink-0 text-[13px]">
                {b.label}
                <span className="block text-[10px]" style={{ color: 'var(--text-muted)' }}>
                  {b.note}
                </span>
              </span>
              <span className="flex-1 relative h-5 rounded"
                style={{ background: 'var(--surface-3)' }}>
                <span className="absolute inset-y-0 left-0 rounded"
                  style={{ width: `${(rate / maxRate) * 100}%`,
                           background: rate > LEVY_CAP ? 'var(--status-critical)'
                             : 'var(--status-good)' }} />
                <span className="absolute inset-y-0 border-l-2 border-dashed"
                  style={{ left: `${(LEVY_CAP / maxRate) * 100}%`,
                           borderColor: 'var(--text-primary)' }} aria-hidden="true" />
              </span>
              <span className="w-24 shrink-0 text-right text-[13px] tnum">
                {(rate * 100).toFixed(0)}%
                <span className="block text-[10px]" style={{ color: 'var(--text-muted)' }}>
                  {(shareOf * 100).toFixed(0)}% of budget
                </span>
              </span>
            </li>
          )
        })}
      </ul>

      {/* ---- the two scenarios, kept apart on purpose ---- */}
      <h3 className="text-sm font-bold mb-1">
        Two ways to live with 2.44 points, priced separately
      </h3>
      <p className="text-[13px] mb-5 max-w-3xl" style={{ color: 'var(--text-secondary)' }}>
        A gap is not something a town can have &mdash; Massachusetts budgets must balance,
        so every year it is either funded or cut. Those are two genuinely different futures
        and mixing them on one chart made both unreadable. Here they are apart. Notice that
        the <em>fresh</em> pain is almost identical either way, around{' '}
        {usdShort(recurring)} a year. What differs completely is what accumulates.
      </p>
      <div className="grid gap-4 lg:grid-cols-2 mb-8">
        <Scenario
          title="If we fund it every year"
          lead={usdShort(funding[9].cumulative)}
          leadNote={`of permanent new revenue in place by FY${funding[9].fy}`}
          body={<>Each year the town finds the fresh shortfall &mdash;{' '}
            {usd(funding[0].fresh)} in FY{funding[0].fy}, rising to{' '}
            {usd(funding[9].fresh)} by FY{funding[9].fy} &mdash; and that money stays in
            the base, growing 2&frac12;% a year with everything else. Nothing is lost, so
            the fresh ask never explodes. What accumulates is the <strong>tax
            side</strong>: {usdShort(funding[9].cumulative)} a year of revenue that does
            not exist today, which is about{' '}
            <strong>{usd(billImpact)} a year on the average tax bill</strong>.</>}
          chart={<FundingChart rows={funding} />}
          rows={[
            ['Fresh money, FY' + funding[0].fy, usd(funding[0].fresh)],
            ['Fresh money, FY' + funding[9].fy, usd(funding[9].fresh)],
            ['Total in place by FY' + funding[9].fy, usd(funding[9].cumulative)],
          ]} />
        <Scenario
          title="If we cut it every year"
          lead={`${atWallPct}%`}
          leadNote={`of every cuttable program gone by FY${exhausted?.fy ?? 33}`}
          tone="var(--status-critical)"
          body={<>Each year the district cuts the fresh shortfall instead &mdash; about{' '}
            {usdShort(recurring)}. Because a cut permanently lowers the base, the ask does
            not grow either. What accumulates here is the <strong>service side</strong>:{' '}
            {usd(cumCut)} of programs and {cumFte} positions &mdash;{' '}
            <strong>every discretionary thing in the catalogue</strong>. Unlike revenue the
            list is finite, and it is empty in FY{exhausted?.fy ?? 33}, after which the gap
            reopens with nothing left to close it.</>}
          chart={<Degradation rows={degradation} />}
          rows={[
            ['Fresh cuts each year', usdShort(recurring)],
            ['Programs gone by FY' + (exhausted?.fy ?? 33), `${usd(cumCut)} — all of them`],
            ['Unclosed by FY' + funding[9].fy, usd(casc[9].unclosed)],
          ]} />
      </div>

      {/* ---- the inverse: flat gap, falling services ---- */}
      <h3 className="text-sm font-bold mb-1">
        The gap stays the same size. The district does not.
      </h3>
      <p className="text-[13px] mb-4 max-w-3xl" style={{ color: 'var(--text-secondary)' }}>
        Whichever way it is settled, the fresh ask stays about the same size every year.
        That is what makes the cutting route so misleading: closing the same gap annually
        does not shrink the gap, it shrinks the school district. The shortfall is a{' '}
        <em>rate</em>, so it renews; the cuts are a <em>stock</em>, so they accumulate.
      </p>
      <div className="grid gap-3 sm:grid-cols-3 mb-8">
        <div className="card p-4">
          <p className="text-[11px] font-semibold uppercase tracking-widest mb-1"
            style={{ color: 'var(--text-muted)' }}>Cut by FY{atWall.fy}</p>
          <p className="text-2xl font-bold tnum leading-none"
            style={{ color: 'var(--status-critical)' }}>{atWall.pct}%</p>
          <p className="text-[12px] mt-1.5" style={{ color: 'var(--text-secondary)' }}>
            of every program the model is able to cut &mdash; the whole{' '}
            {usd(pool)} of it, with only legally mandated staff left standing
          </p>
        </div>
        <div className="card p-4">
          <p className="text-[11px] font-semibold uppercase tracking-widest mb-1"
            style={{ color: 'var(--text-muted)' }}>Against a gap of</p>
          <p className="text-2xl font-bold tnum leading-none">{usdShort(atWall.gap)}</p>
          <p className="text-[12px] mt-1.5" style={{ color: 'var(--text-secondary)' }}>
            that year &mdash; so you will have given up{' '}
            <strong>{(atWall.spent / atWall.gap).toFixed(1)}&times; the size of the
            problem</strong> and still have the problem
          </p>
        </div>
        <div className="card p-4" style={{ background: 'var(--surface-3)' }}>
          <p className="text-[11px] font-semibold uppercase tracking-widest mb-1"
            style={{ color: 'var(--text-muted)' }}>And it never closes</p>
          <p className="text-2xl font-bold tnum leading-none"
            style={{ color: 'var(--status-critical)' }}>FY{atWall.fy + 1}</p>
          <p className="text-[12px] mt-1.5" style={{ color: 'var(--text-secondary)' }}>
            opens with a gap like every year before it, only now there is nothing left on
            the list to close it with
          </p>
        </div>
      </div>

      {/* ---- the floor: what can never be cut at all ---- */}
      <h3 className="text-sm font-bold mb-1">
        What must always be funded, no matter what
      </h3>
      <p className="text-[13px] mb-4 max-w-3xl" style={{ color: 'var(--text-secondary)' }}>
        The reason the cut list runs out so fast is that it was never very long. Almost all
        of a school budget is not available to cut in the first place, and what the cutting
        route really does is spend the small part that is.
      </p>
      <div className="grid gap-3 sm:grid-cols-3 mb-4">
        <div className="card p-4">
          <p className="text-[11px] font-semibold uppercase tracking-widest mb-1"
            style={{ color: 'var(--text-muted)' }}>Never on the table</p>
          <p className="text-2xl font-bold tnum leading-none"
            style={{ color: 'var(--status-warning)' }}>
            {((floor / approp) * 100).toFixed(0)}%
          </p>
          <p className="text-[12px] mt-1.5" style={{ color: 'var(--text-secondary)' }}>
            {usd(floor)} of the {usd(approp)} appropriation — core teaching staff, most
            special education, transport, utilities and benefits, plus the mandated items
            below
          </p>
        </div>
        <div className="card p-4">
          <p className="text-[11px] font-semibold uppercase tracking-widest mb-1"
            style={{ color: 'var(--text-muted)' }}>Genuinely discretionary</p>
          <p className="text-2xl font-bold tnum leading-none">
            {(((inCatalogue - mandatedInCatalogue) / approp) * 100).toFixed(0)}%
          </p>
          <p className="text-[12px] mt-1.5" style={{ color: 'var(--text-secondary)' }}>
            {usd(inCatalogue - mandatedInCatalogue)} — every athletic team, club, library,
            elective, art supply and administrative line this tool offers, added together
          </p>
        </div>
        <div className="card p-4" style={{ background: 'var(--surface-3)' }}>
          <p className="text-[11px] font-semibold uppercase tracking-widest mb-1"
            style={{ color: 'var(--text-muted)' }}>Mandated by law, in the catalogue</p>
          <p className="text-2xl font-bold tnum leading-none">{usd(mandatedInCatalogue)}</p>
          <p className="text-[12px] mt-1.5" style={{ color: 'var(--text-secondary)' }}>
            The only mandated items this tool prices individually. Named in full below.
          </p>
        </div>
      </div>

      {/* ---- name them, because "87% is mandated" is not a checkable claim ---- */}
      <div className="grid gap-3 lg:grid-cols-2 mb-4">
        <div className="card p-4">
          <h4 className="text-[13px] font-bold mb-2">
            The mandated services this model names
          </h4>
          <ul className="space-y-2.5">
            {mandatedItems.map(p => (
              <li key={p.id} className="flex gap-2.5">
                <span aria-hidden="true" className="shrink-0 text-[13px]"
                  style={{ color: 'var(--status-warning)' }}>⚖</span>
                <span className="flex-1 min-w-0">
                  <span className="flex items-baseline justify-between gap-2">
                    <span className="text-[13px] font-medium">{p.name}</span>
                    <span className="text-[13px] tnum font-bold shrink-0">
                      {usd(p.cost * (p.repeatable ?? 1))}
                    </span>
                  </span>
                  <span className="block text-[11px] leading-relaxed"
                    style={{ color: 'var(--text-secondary)' }}>
                    {p.fte > 0 && (
                      <span className="tnum">{p.fte * (p.repeatable ?? 1)} FTE · </span>
                    )}
                    {p.impact}
                  </span>
                </span>
              </li>
            ))}
            {mandatedUnfunded.map(p => (
              <li key={p.id} className="flex gap-2.5 pt-2.5 border-t"
                style={{ borderColor: 'var(--grid)' }}>
                <span aria-hidden="true" className="shrink-0 text-[13px]"
                  style={{ color: 'var(--status-critical)' }}>✕</span>
                <span className="flex-1 min-w-0">
                  <span className="flex items-baseline justify-between gap-2">
                    <span className="text-[13px] font-medium">{p.name}</span>
                    <span className="text-[13px] tnum font-bold shrink-0"
                      style={{ color: 'var(--status-critical)' }}>
                      {usd(p.cost * (p.repeatable ?? 1))}
                    </span>
                  </span>
                  <span className="block text-[11px] leading-relaxed"
                    style={{ color: 'var(--status-critical)' }}>
                    <strong>Legally required and not currently funded.</strong> {p.impact}
                  </span>
                </span>
              </li>
            ))}
          </ul>
          <p className="text-[11px] leading-relaxed mt-3 pt-2 border-t"
            style={{ color: 'var(--text-muted)', borderColor: 'var(--grid)' }}>
            Also effectively fixed: {contractItems.length} collectively bargained lines
            worth {usd(contractItems.reduce((a, p) => a + p.cost * (p.repeatable ?? 1), 0))}{' '}
            &mdash; {contractItems.map(p => p.name.replace(/ \(.*\)$/, '')).join(' and ')}.
            Cuttable in principle, only by reopening a contract.
          </p>
        </div>

        <div className="card p-4">
          <h4 className="text-[13px] font-bold mb-1">
            And the rest of the {((floor / approp) * 100).toFixed(0)}%, honestly
          </h4>
          <p className="text-[12px] leading-relaxed mb-3"
            style={{ color: 'var(--text-secondary)' }}>
            <strong>This model does not itemise it.</strong> The{' '}
            {usd(approp - inCatalogue)} outside the catalogue is a residual &mdash; the
            appropriation less everything the tool prices &mdash; not a list anybody has
            published as &ldquo;untouchable&rdquo;. Its shape, from the district&rsquo;s
            own expense base:
          </p>
          <ul className="space-y-1.5">
            {Object.entries(expense).sort((a, b) => b[1] - a[1]).map(([k, v]) => (
              <li key={k} className="flex items-center gap-2.5">
                <span className="w-32 shrink-0 text-[12px] capitalize">
                  {k.replace('sped_tuition', 'SPED tuition').replace('_', ' ')}
                </span>
                <span className="flex-1 h-3 rounded" style={{ background: 'var(--surface-3)' }}>
                  <span className="block h-full rounded"
                    style={{ width: `${(v / expenseTotal) * 100}%`,
                             background: 'var(--status-warning)', opacity: 0.6 }} />
                </span>
                <span className="w-24 shrink-0 text-right text-[12px] tnum">
                  {usdShort(v)}
                </span>
              </li>
            ))}
          </ul>
          <p className="text-[11px] leading-relaxed mt-3"
            style={{ color: 'var(--text-muted)' }}>
            Salaries are two thirds of it, and the catalogue reaches only a slice of those
            &mdash; the teachers, paraprofessionals and custodians it names. The rest is
            staff nobody has proposed cutting, plus health insurance, transport and
            out-of-district tuition, which are set by contract, by the insurance market, or
            by law. Treat {((floor / approp) * 100).toFixed(0)}% as &ldquo;never put on a
            cut list&rdquo;, which is what it is, rather than as a legal finding.
          </p>
        </div>
      </div>

      <p className="text-[13px] mb-3 max-w-3xl" style={{ color: 'var(--text-secondary)' }}>
        So the budget starts barely flexible and ends completely rigid. Every year of
        cutting converts discretionary spending into mandatory spending &mdash; not by
        adding mandates, but by removing everything else around them.
      </p>
      <LockChart rows={budgetMix} />
      <p className="text-[11px] mt-1 mb-8" style={{ color: 'var(--text-muted)' }}>
        A budget that is {budgetMix[0].locked.toFixed(0)}% locked in FY{budgetMix[0].fy}{' '}
        is {budgetMix[5].locked.toFixed(0)}% locked by FY{budgetMix[5].fy}. At that point every dollar the
        district spends is a dollar it has no choice about, and the only remaining
        responses are an override or cutting things nobody has ever put on a list &mdash;
        classroom teachers, and the mandated services themselves.
      </p>

      {/* ---- how to read the number, because it is easy to read it wrong ---- */}
      <div className="card p-5 mb-8">
        <h3 className="text-sm font-bold mb-2">
          How to read &ldquo;{usdShort(base[9].deficit)} by FY{base[9].fy}&rdquo;
        </h3>
        <div className="grid gap-4 md:grid-cols-3 text-[13px] leading-relaxed"
          style={{ color: 'var(--text-secondary)' }}>
          <div>
            <p className="text-[11px] font-bold uppercase tracking-widest mb-1"
              style={{ color: 'var(--text-muted)' }}>It is an annual figure</p>
            <p>
              Not a running total. In FY{base[9].fy} alone, running FY27&rsquo;s services
              would cost {usd(base[9].levelService)} against {usd(base[9].available)} of
              revenue. The next year it starts again, larger.
            </p>
          </div>
          <div>
            <p className="text-[11px] font-bold uppercase tracking-widest mb-1"
              style={{ color: 'var(--text-muted)' }}>It is in future dollars</p>
            <p>
              {usdShort(base[9].deficit)} of FY{base[9].fy} money, ten fiscal years out.
              In today&rsquo;s purchasing power that is roughly{' '}
              <strong>{usd(Math.round(base[9].deficit / Math.pow(1 + LEVY_CAP, 10)))}</strong>{' '}
              &mdash; still enormous, but not as enormous as it looks.
            </p>
          </div>
          <div>
            <p className="text-[11px] font-bold uppercase tracking-widest mb-1"
              style={{ color: 'var(--status-critical)' }}>Nobody will ever see it</p>
            <p>
              Massachusetts budgets must balance, so this shortfall never appears on a
              statement. It is not a prediction of a deficit &mdash; it is{' '}
              <strong>the annual price, in FY{base[9].fy}, of still having what the
              district has today</strong>.
            </p>
          </div>
        </div>
        <p className="text-[13px] leading-relaxed mt-4 pt-4 border-t"
          style={{ borderColor: 'var(--grid)' }}>
          <strong>What you would actually see in FY{base[9].fy}</strong> is that figure
          paid in two currencies instead of one: about <strong>{usd(cumCut)}</strong> of
          programs and {cumFte} staff positions already gone, so the district is no longer
          buying them &mdash; plus roughly <strong>{usdShort(casc[9].unclosed)}</strong>{' '}
          still unfunded in that year, with nothing left on the list to cut. The two do not
          add exactly to {usdShort(base[9].deficit)}, because a cut made early also stops
          inflating; cutting sooner is worth more than cutting later.
        </p>
      </div>

      {/* ---- the three ways out ---- */}
      <h3 className="text-sm font-bold mb-1">The three ways out, honestly sized</h3>
      <p className="text-[13px] mb-4 max-w-3xl" style={{ color: 'var(--text-secondary)' }}>
        A gap that grows needs a remedy that grows. Anything that arrives once gets
        overtaken &mdash; the only question is how long that takes.
      </p>
      <div className="grid gap-3 md:grid-cols-3">
        <Way title="Pass an override"
          lead={`${singleOverride(613_238)} year`}
          sub={`what one ${usd(613_238)} override buys`}
          body={<>An override permanently raises the levy limit, and that lift then grows
            2&frac12;% a year &mdash; slower than the gap. So one ballot question is not a
            fix, it is a postponement, and the next one has to be bigger.</>}
          rows={[[`${usd(613_238)} once`, `${singleOverride(613_238)} year`],
                 [`${usd(3_000_000)} once`, `${singleOverride(3_000_000)} years`],
                 [`${usd(5_000_000)} once`, `${singleOverride(5_000_000)} years`]]} />

        <Way title="Build commercial"
          lead={`${sustained(150e6)}+ years`}
          sub="at $150M of new value a year, sustained"
          body={<>It genuinely works &mdash; at a scale that would remake the town. $150M a
            year is <strong>97% of Lunenburg&rsquo;s entire existing commercial base, added
            every year</strong>. After a decade the commercial base would be 10.7&times;
            what it is now.</>}
          rows={[[`${usdShort(106.9e6)}/yr · ${Math.round(106.9e6 / mix)} builds`, `${sustained(106.9e6)} years`],
                 [`${usdShort(130e6)}/yr · ${Math.round(130e6 / mix)} builds`, `${sustained(130e6)} years`],
                 [`${usdShort(150e6)}/yr · ${Math.round(150e6 / mix)} builds`, `${sustained(150e6)}+ years`]]} />

        <Way title="Bend the cost curve"
          lead={usdShort(base[9].deficit - bentHealth[9].deficit)}
          sub="off the FY37 gap, from health insurance alone"
          body={<>The one remedy that is neither a tax nor a cut: change the growth rates
            themselves. Health insurance is 15% of the budget growing at 9%. Holding it to
            4% takes the FY37 gap from {usdShort(base[9].deficit)} to{' '}
            {usdShort(bentHealth[9].deficit)} &mdash; it does not close it, but it nearly
            halves it, and it makes everything else smaller.</>}
          rows={[['Health at 6%', usdShort(project(10, { ...A, health: 0.06 })[9].deficit)],
                 ['Health at 4%', usdShort(bentHealth[9].deficit)],
                 ['Unchanged, 9%', usdShort(base[9].deficit)]]} />
      </div>

      <div className="card p-5 mt-4" style={{ background: 'var(--surface-3)' }}>
        <p className="text-[13px] leading-relaxed">
          <strong>Put together:</strong> holding health to 4%, building at{' '}
          {usdShort(106.9e6)} a year, and passing {usd(613_238)} of override covers the
          whole fifteen years. Any one of them alone does not. That is the honest shape of
          the problem &mdash; not a single decision anybody can take at a Town Meeting, but
          three sustained ones. Cutting is not a fourth option so much as what happens
          while none of them is chosen: it holds the line for about{' '}
          {cutting.length} years, at {cumFte} staff positions and {usd(cumCut)} of
          programs, and then there is nothing left to cut and the arithmetic resumes.
        </p>
      </div>
    </div>
  )
}

/** A flat gap beside a climbing loss. The inverse nobody names out loud. */
function Degradation({ rows }: {
  rows: { fy: number; gap: number; spent: number; pct: number }[]
}) {
  return (
    <div style={{ width: '100%', height: 240 }}>
      <ResponsiveContainer>
        <ComposedChart data={rows} margin={{ top: 8, right: 8, bottom: 4, left: 4 }}>
          <CartesianGrid stroke="var(--grid)" vertical={false} />
          <XAxis dataKey="fy" tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
            stroke="var(--axis)" tickLine={false} tickFormatter={v => `FY${v}`} />
          <YAxis yAxisId="left" width={56}
            tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
            stroke="var(--axis)" tickLine={false} axisLine={false}
            tickFormatter={v => usdShort(v as number)} />
          <YAxis yAxisId="right" orientation="right" width={44} domain={[0, 100]}
            tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
            stroke="var(--axis)" tickLine={false} axisLine={false}
            tickFormatter={v => `${v}%`} />
          <Tooltip
            contentStyle={{ background: 'var(--surface-1)', border: '1px solid var(--grid)',
                            borderRadius: 10, fontSize: 12, color: 'var(--text-primary)' }}
            labelFormatter={v => `FY${v}`}
            formatter={(v, n) => n === 'pct'
              ? [`${v}% of everything cuttable`, 'Given up, cumulative']
              : [usd(v as number), 'Gap that year']} />
          <Legend verticalAlign="top" height={26}
            wrapperStyle={{ fontSize: 11, color: 'var(--text-secondary)' }}
            formatter={v => v === 'pct'
              ? 'Services given up, cumulative' : 'The gap, each year'} />
          <Bar yAxisId="right" dataKey="pct" fill="var(--status-critical)"
            fillOpacity={0.35} isAnimationActive={false} />
          <Line yAxisId="left" type="monotone" dataKey="gap" stroke="var(--series-cost)"
            strokeWidth={2} dot={false} isAnimationActive={false} />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}

/** Discretionary spending as a share of the budget, collapsing year by year. */
function LockChart({ rows }: {
  rows: { fy: number; discretionary: number; locked: number }[]
}) {
  return (
    <div style={{ width: '100%', height: 220 }}>
      <ResponsiveContainer>
        <ComposedChart data={rows} margin={{ top: 8, right: 12, bottom: 4, left: 4 }}
          stackOffset="expand">
          <CartesianGrid stroke="var(--grid)" vertical={false} />
          <XAxis dataKey="fy" tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
            stroke="var(--axis)" tickLine={false} tickFormatter={v => `FY${v}`} />
          <YAxis width={44} tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
            stroke="var(--axis)" tickLine={false} axisLine={false}
            tickFormatter={v => `${Math.round((v as number) * 100)}%`} />
          <Tooltip
            contentStyle={{ background: 'var(--surface-1)', border: '1px solid var(--grid)',
                            borderRadius: 10, fontSize: 12, color: 'var(--text-primary)' }}
            labelFormatter={v => `FY${v}`}
            formatter={(v, n) => [`${(v as number).toFixed(1)}%`,
              n === 'locked' ? 'Cannot be cut' : 'Still discretionary']} />
          <Legend verticalAlign="top" height={26} iconType="square"
            wrapperStyle={{ fontSize: 11, color: 'var(--text-secondary)' }}
            formatter={v => v === 'locked' ? 'Cannot be cut' : 'Still discretionary'} />
          <Bar dataKey="locked" stackId="a" fill="var(--status-warning)"
            fillOpacity={0.45} isAnimationActive={false} />
          <Bar dataKey="discretionary" stackId="a" fill="var(--series-cost)"
            isAnimationActive={false} />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}

/** One future, priced on its own terms. */
function Scenario({ title, lead, leadNote, body, chart, rows, tone }: {
  title: string; lead: string; leadNote: string
  body: React.ReactNode; chart: React.ReactNode
  rows: [string, string][]; tone?: string
}) {
  return (
    <div className="card p-5 flex flex-col">
      <h4 className="text-[15px] font-bold mb-2">{title}</h4>
      <p className="text-3xl font-bold tnum leading-none"
        style={{ color: tone ?? 'var(--series-cost)' }}>{lead}</p>
      <p className="text-[11px] mt-1 mb-3" style={{ color: 'var(--text-muted)' }}>
        {leadNote}
      </p>
      <p className="text-[13px] leading-relaxed mb-4"
        style={{ color: 'var(--text-secondary)' }}>{body}</p>
      <div className="flex-1">{chart}</div>
      <dl className="mt-3 pt-3 border-t space-y-1.5" style={{ borderColor: 'var(--grid)' }}>
        {rows.map(([k, v]) => (
          <div key={k} className="flex items-baseline justify-between gap-3 text-[12px]">
            <dt style={{ color: 'var(--text-secondary)' }}>{k}</dt>
            <dd className="font-bold tnum shrink-0">{v}</dd>
          </div>
        ))}
      </dl>
    </div>
  )
}

/** Fresh money each year against the permanent total it builds up to. */
function FundingChart({ rows }: {
  rows: { fy: number; cumulative: number; fresh: number }[]
}) {
  return (
    <div style={{ width: '100%', height: 240 }}>
      <ResponsiveContainer>
        <ComposedChart data={rows} margin={{ top: 8, right: 8, bottom: 4, left: 4 }}>
          <CartesianGrid stroke="var(--grid)" vertical={false} />
          <XAxis dataKey="fy" tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
            stroke="var(--axis)" tickLine={false} tickFormatter={v => `FY${v}`} />
          <YAxis width={52} tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
            stroke="var(--axis)" tickLine={false} axisLine={false}
            tickFormatter={v => usdShort(v as number)} />
          <Tooltip
            contentStyle={{ background: 'var(--surface-1)', border: '1px solid var(--grid)',
                            borderRadius: 10, fontSize: 12, color: 'var(--text-primary)' }}
            labelFormatter={v => `FY${v}`}
            formatter={(v, n) => [usd(v as number),
              n === 'fresh' ? 'Fresh money that year' : 'Permanent revenue in place']} />
          <Legend verticalAlign="top" height={26}
            wrapperStyle={{ fontSize: 11, color: 'var(--text-secondary)' }}
            formatter={v => v === 'fresh' ? 'Fresh money that year' : 'Permanent total'} />
          <Bar dataKey="cumulative" fill="var(--series-cost)" fillOpacity={0.3}
            isAnimationActive={false} />
          <Line type="monotone" dataKey="fresh" stroke="var(--series-cost)"
            strokeWidth={2} dot={false} isAnimationActive={false} />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}

function Way({ title, lead, sub, body, rows }: {
  title: string; lead: string; sub: string
  body: React.ReactNode; rows: [string, string][]
}) {
  return (
    <div className="card p-5 flex flex-col">
      <h4 className="text-[13px] font-bold mb-2">{title}</h4>
      <p className="text-3xl font-bold tnum leading-none"
        style={{ color: 'var(--series-cost)' }}>{lead}</p>
      <p className="text-[11px] mt-1 mb-3" style={{ color: 'var(--text-muted)' }}>{sub}</p>
      <p className="text-[12px] leading-relaxed flex-1"
        style={{ color: 'var(--text-secondary)' }}>{body}</p>
      <dl className="mt-3 pt-3 border-t space-y-1.5" style={{ borderColor: 'var(--grid)' }}>
        {rows.map(([k, v]) => (
          <div key={k} className="flex items-baseline justify-between gap-3 text-[12px]">
            <dt style={{ color: 'var(--text-secondary)' }}>{k}</dt>
            <dd className="font-bold tnum shrink-0">{v}</dd>
          </div>
        ))}
      </dl>
    </div>
  )
}

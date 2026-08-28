import { useMemo, useState } from 'react'
import {
  BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer,
} from 'recharts'
import { MODEL, usd, usdShort, COST_GROWTH_BLENDED } from '../model/engine'
import { Section, Note } from '../components/primitives'
import { GrowthCalculator } from '../components/TaxBase'
import { TaxBaseMix } from '../components/TaxBaseMix'

const T = MODEL.taxBase

/** Development, modeled properly.
 *
 *  The adjustments page needs one commercial dial and a straight answer about what it is
 *  worth against the gap. Everything else about development — what a build rate produces
 *  year after year, what housing does on both sides of the ledger, and how the two move
 *  the balance between homeowners and business — is a different question, and crowding it
 *  into a panel there made both jobs worse. */
export function Development({ commercial, setCommercial, homes, setHomes, gap, share }: {
  commercial: number; setCommercial: (n: number) => void
  homes: number; setHomes: (n: number) => void
  gap: number
  /** Fraction of new-growth revenue that reaches the school gap. */
  share: number
}) {
  return (
    <div>
      <div className="mx-auto max-w-6xl px-5 pt-12 pb-2">
        <p className="text-xs font-semibold uppercase tracking-widest mb-3"
          style={{ color: 'var(--text-muted)' }}>The revenue side, modeled</p>
        <h1 className="text-3xl sm:text-4xl font-bold tracking-tight leading-[1.1] max-w-3xl">
          What building changes
        </h1>
        <p className="mt-4 text-[15px] leading-relaxed max-w-2xl"
          style={{ color: 'var(--text-secondary)' }}>
          &ldquo;We need more development&rdquo; is the most common answer to the school
          budget, and it is not wrong &mdash; but almost nobody in town has seen the
          arithmetic. Build commercial and residential at whatever rate you think is
          realistic, and watch what each does to the town&rsquo;s revenue, to the school
          gap, and to the share of the tax bill homeowners carry.
        </p>
        <Note>
          Nothing on this page changes the adjustments page except the commercial rate,
          which is the same control in both places. Housing is modeled here only.
        </Note>
      </div>

      <Section id="findings" eyebrow="The short version"
        title="What development actually does"
        lede={<>Six findings, before any of the mechanics below. Each one links to the part
          of this page that shows the arithmetic. The short version of the short version:
          development is real money and it does not lower your bill, and the two facts are
          the same fact.</>}>
        <Findings gap={gap} share={share} />
      </Section>

      <Section id="commercial" eyebrow="Commercial" title="What a build rate produces"
        lede={<>Set how much new commercial value the town adds each year. New growth joins
          the levy limit permanently, so the effect accumulates &mdash; but only the
          {' '}{(share * 100).toFixed(0)}% of it that follows the schools&rsquo; share of
          town revenue reaches this gap.</>}>
        <GrowthCalculator gap={gap} newValue={commercial} setNewValue={setCommercial}
          share={share} />
        <div className="mt-8">
          <YearByYear value={commercial} share={share} gap={gap} />
        </div>
      </Section>

      <Section id="residential" eyebrow="Residential"
        title="What housing does to both sides of the ledger"
        lede={<>A home pays taxes and sends children. Under a single tax rate the first is
          fixed by assessment and the second is not, which is why housing can add revenue
          and still make the school budget harder.</>}>
        <Residential homes={homes} setHomes={setHomes} />
      </Section>

      <Section id="bills" eyebrow="The homeowner's question"
        title="How would we actually lower the bill?"
        lede={<>Start from the thing nobody says out loud: bills rise about{' '}
          <strong>2&frac12;% a year on their own</strong>, so a bill that is merely flat in
          ten years is already a win. Anything below today&rsquo;s {usd(T.avgHomeBill)} has
          to overcome that first. Set a target and pull the four levers the town actually
          controls.</>}>
        <PlainAnswer commercial={commercial} homes={homes} gap={gap} share={share} />

        <h3 className="text-lg font-bold mt-12 mb-1">Why the schools still run a gap</h3>
        <p className="text-[13px] mb-4 max-w-3xl" style={{ color: 'var(--text-secondary)' }}>
          The obvious objection to all of this: if the town keeps growing and collecting
          more every year, how is there a shortfall at all?
        </p>
        <WhyTheGap gap={gap} share={share} />

        <h3 className="text-lg font-bold mt-12 mb-1">Or pull the levers yourself</h3>
        <p className="text-[13px] mb-4 max-w-3xl" style={{ color: 'var(--text-secondary)' }}>
          The same model with every control exposed, if you want to try a combination the
          recipe above would not have picked.
        </p>
        <BillModel commercial={commercial} homes={homes} gap={gap} share={share} />
      </Section>

      <Section id="mix" eyebrow="The balance"
        title="Who carries the tax bill, over time"
        lede={<>Lunenburg has one tax rate, so a class&rsquo;s share of the taxable base is
          exactly its share of the tax bill. Both sliders above feed this.</>}>
        <TaxBaseMix commercialPerYear={commercial} homesPerYear={homes} />
      </Section>
    </div>
  )
}

/* ------------------------------------------------------------------ */

/** New growth compounds, so a constant build rate is not a constant revenue line. */
function YearByYear({ value, share, gap }: {
  value: number; share: number; gap: number
}) {
  const annual = (value * T.rate) / 1000
  const rows = useMemo(() => {
    const out: { year: number; added: number; town: number; schools: number }[] = []
    let town = 0
    for (let i = 1; i <= 10; i++) {
      town = town * (1 + T.levyGrowth) + annual
      out.push({ year: i, added: Math.round(annual), town: Math.round(town),
                 schools: Math.round(town * share) })
    }
    return out
  }, [annual, share])

  const yr10 = rows[9]
  const closes = rows.find(r => r.schools >= gap)

  return (
    <div>
      <h3 className="text-sm font-bold mb-1">Year by year, at this rate</h3>
      <p className="text-[13px] mb-4 max-w-3xl" style={{ color: 'var(--text-secondary)' }}>
        Each year&rsquo;s building stays on the tax roll and the whole accumulated lift
        rises 2.5% a year on top, so the line bends upward even though the build rate is
        flat. This is what makes development a real answer over a decade and a poor one
        for next April.
      </p>

      <div className="grid gap-3 sm:grid-cols-3 mb-4">
        <Fig label="Added to the levy each year" value={usd(annual)}
          sub={`${usdShort(value)} of new value at $${T.rate} per $1,000`} />
        <Fig label="Reaching the schools, year 10" value={usd(yr10.schools)}
          sub={`${(yr10.schools / gap * 100).toFixed(0)}% of today's ${usd(gap)} gap`} />
        <Fig label="Year the schools' share covers the gap"
          value={closes ? `Year ${closes.year}` : 'Not within 10'}
          tone={closes ? 'var(--status-good)' : 'var(--status-critical)'}
          sub={closes ? `at ${usd(closes.schools)} a year` : 'against today’s gap, which itself grows'} />
      </div>

      <div style={{ width: '100%', height: 260 }}>
        <ResponsiveContainer>
          <BarChart data={rows} margin={{ top: 8, right: 12, bottom: 4, left: 4 }}>
            <CartesianGrid stroke="var(--grid)" vertical={false} />
            <XAxis dataKey="year" tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
              stroke="var(--axis)" tickLine={false} tickFormatter={v => `yr ${v}`} />
            <YAxis width={56} tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
              stroke="var(--axis)" tickLine={false} axisLine={false}
              tickFormatter={v => usdShort(v as number)} />
            <Tooltip
              contentStyle={{ background: 'var(--surface-1)', border: '1px solid var(--grid)',
                              borderRadius: 10, fontSize: 12, color: 'var(--text-primary)' }}
              labelFormatter={v => `Year ${v}`}
              formatter={(v, n) => [usd(v as number),
                n === 'schools' ? 'Reaches the schools' : 'Stays with the town']} />
            <Legend verticalAlign="top" height={28} iconType="square"
              wrapperStyle={{ fontSize: 12, color: 'var(--text-secondary)' }}
              formatter={v => v === 'schools' ? 'Reaches the schools' : 'Stays with the town'} />
            <Bar dataKey="schools" stackId="a" fill="var(--series-cost)"
              isAnimationActive={false} />
            <Bar dataKey="town" stackId="b" fill="var(--surface-3)"
              isAnimationActive={false} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <Note>
        The two bars are the same money counted two ways: the whole levy lift, and the
        portion of it that follows the schools&rsquo; share of town revenue. Ten years of
        building at this rate leaves the town collecting {usd(yr10.town)} a year more than
        it does today, of which {usd(yr10.schools)} is the schools&rsquo;.
      </Note>
    </div>
  )
}

/* ------------------------------------------------------------------ */

/** Housing: revenue in, students out. */
function Residential({ homes, setHomes }: {
  homes: number; setHomes: (n: number) => void
}) {
  // Student yield per new home is NOT published for Lunenburg. It is the one number here
  // the reader has to supply, so it is a control rather than a constant, and the
  // break-even point is marked so the assumption can be judged against something.
  const [yieldPer, setYieldPer] = useState(0.5)

  const count = homes / T.avgHomeValue
  const breakEven = T.schoolShareOfBill / T.localCostPerPupil

  const townRevenue = (homes * T.rate) / 1000
  const schoolRevenue = count * T.schoolShareOfBill
  const students = count * yieldPer
  const schoolCost = students * T.localCostPerPupil
  const net = schoolRevenue - schoolCost

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <div className="card p-5">
        <div className="flex items-baseline justify-between gap-3 mb-1">
          <label htmlFor="homerate" className="text-[13px] font-medium">
            New homes built per year
          </label>
          <span className="text-xl font-bold tnum">
            {Math.round(count)}
            <span className="text-[11px] font-normal ml-1" style={{ color: 'var(--text-muted)' }}>
              = {usdShort(homes)}
            </span>
          </span>
        </div>
        <input id="homerate" type="range" min={0} max={60_000_000} step={1_000_000}
          value={homes} onChange={e => setHomes(Number(e.target.value))} className="w-full" />
        <p className="text-[10px] mb-4" style={{ color: 'var(--text-muted)' }}>
          At the town&rsquo;s {usd(T.avgHomeValue)} average assessment. Defaulted to{' '}
          {usdShort(T.fy23NewValue)} — the whole of FY23 new growth, which was effectively
          all housing.
        </p>

        <div className="flex items-baseline justify-between gap-3 mb-1">
          <label htmlFor="yield" className="text-[13px] font-medium">
            Schoolchildren per new home
          </label>
          <span className="text-xl font-bold tnum">{yieldPer.toFixed(2)}</span>
        </div>
        <input id="yield" type="range" min={0} max={1.5} step={0.05} value={yieldPer}
          onChange={e => setYieldPer(Number(e.target.value))} className="w-full" />
        <div className="relative h-7">
          <button onClick={() => setYieldPer(Math.round(breakEven * 20) / 20)}
            className="absolute top-0 text-[10px] leading-tight text-center hover:opacity-70"
            style={{ left: `${(breakEven / 1.5) * 100}%`, transform: 'translateX(-50%)',
                     color: 'var(--status-good)' }}>
            <span className="block w-px h-1.5 mb-0.5 mx-auto"
              style={{ background: 'var(--status-good)' }} aria-hidden="true" />
            <span className="whitespace-nowrap font-semibold">
              {breakEven.toFixed(2)} breaks even
            </span>
          </button>
        </div>
        <p className="text-[11px] mt-1" style={{ color: 'var(--status-serious)' }}>
          <strong>This is the one figure you have to supply.</strong> Lunenburg does not
          publish a student yield per new home, and it swings the answer more than anything
          else on this page. A home breaks even at {breakEven.toFixed(2)} children; above
          that it costs the schools more than it pays them.
        </p>
      </div>

      <div className="card p-5">
        <h3 className="text-sm font-bold mb-4">What that housing does, each year</h3>
        <dl className="space-y-2.5 text-[13px]">
          <Row k="Tax revenue to the town" v={usd(townRevenue)} />
          <Row k="Of which reaches the schools" v={usd(schoolRevenue)} />
          <Row k="Schoolchildren it brings" v={students.toFixed(1)} />
          <Row k="School cost it creates"
            v={usd(schoolCost)} />
        </dl>
        <p className="text-3xl font-bold tnum mt-4 pt-4 border-t"
          style={{ borderColor: 'var(--grid)',
                   color: net >= 0 ? 'var(--status-good)' : 'var(--status-critical)' }}>
          {net >= 0 ? '+' : ''}{usd(net)}
          <span className="text-sm font-normal" style={{ color: 'var(--text-secondary)' }}>
            {' '}to the schools, per year of building
          </span>
        </p>
        <p className="text-[13px] leading-relaxed mt-3" style={{ color: 'var(--text-secondary)' }}>
          {net >= 0
            ? <>At {yieldPer.toFixed(2)} children a home, this housing pays the schools more
              than it costs them. It still adds to the town&rsquo;s revenue either way
              &mdash; the question is only whether the school side comes out ahead.</>
            : <>At {yieldPer.toFixed(2)} children a home, this housing costs the schools{' '}
              <strong>{usd(Math.abs(net))}</strong> a year more than it pays them, and every
              year of building adds another layer. <strong>A commercial building of the same
              assessed value pays the same tax and sends nobody.</strong></>}
        </p>
        <Note>
          School cost per pupil is the {usd(MODEL.fy27.lps_appropriation)} appropriation less{' '}
          {usd(T.ch70.aid)} of Chapter 70 aid over {T.enrollment} students ={' '}
          {usd(T.localCostPerPupil)}. A home&rsquo;s school taxes are{' '}
          {usd(T.schoolShareOfBill)} — {(T.schoolShareOfBudget * 100).toFixed(0)}% of the{' '}
          {usd(T.avgHomeBill)} average bill. State aid does rise with enrollment, but far
          more slowly than local cost.
        </Note>
      </div>
    </div>
  )
}

/** Why growth and a shortfall coexist. The question every resident asks second. */
function WhyTheGap({ gap, share }: { gap: number; share: number }) {
  const grow = MODEL.assumptions
  const items = [
    {
      n: '2½%',
      head: 'The town’s revenue is capped. The schools’ costs are not.',
      body: `Proposition 2½ lets the levy rise 2½% a year plus new construction. School `
        + `costs do not observe that limit: salaries rise ${(grow.salaries * 100).toFixed(0)}%, `
        + `health insurance ${(grow.health * 100).toFixed(0)}%, out-of-district special `
        + `education tuition ${(grow.sped_tuition * 100).toFixed(0)}%. A budget growing `
        + `2½% against costs growing 4–9% falls behind every single year, and the shortfall `
        + `compounds. That is the whole gap — it is not overspending, it is two different `
        + `growth rates.`,
    },
    {
      n: `${(share * 100).toFixed(0)}¢`,
      head: 'Only about half of new growth reaches the schools.',
      body: `New construction lifts the TOWN’s levy limit. The schools then receive their `
        + `share of total town revenue — roughly ${(share * 100).toFixed(0)}¢ in every `
        + `dollar. The rest funds fire, police, DPW and everything else the town does. So `
        + `a new business worth $43,000 a year in taxes is worth about $23,000 to the `
        + `schools.`,
    },
    {
      n: '9%',
      head: 'There is very little commercial base to grow from.',
      body: `Commercial, industrial and personal property is about 9% of Lunenburg’s tax `
        + `base — roughly ${MODEL.taxBase.businesses} parcels averaging `
        + `${usd(MODEL.taxBase.avgCommercialValue)}. Growing a small number quickly still `
        + `produces a small number. Meanwhile the town’s actual new growth has been `
        + `falling: $481,000 in FY2018 down to $234,000 in FY2023.`,
    },
    {
      n: '↔',
      head: 'And lowering bills and funding schools are the same money.',
      body: `The only way development lowers an existing tax bill is if the town declines `
        + `to collect the new growth. Declining it is exactly what removes it from the `
        + `schools. You can spend a dollar of new growth once — on a lower bill or on a `
        + `classroom, not both.`,
    },
  ]
  return (
    <div className="grid gap-3 md:grid-cols-2">
      {items.map(i => (
        <div key={i.head} className="card p-4">
          <div className="flex items-baseline gap-3 mb-1">
            <span className="text-xl font-bold tnum shrink-0"
              style={{ color: 'var(--series-cost)' }}>{i.n}</span>
            <h4 className="text-[13px] font-bold">{i.head}</h4>
          </div>
          <p className="text-[12px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
            {i.body}
          </p>
        </div>
      ))}
      <div className="card p-4 md:col-span-2"
        style={{ background: 'var(--surface-3)' }}>
        <p className="text-[13px] leading-relaxed">
          <strong>So the honest position is this.</strong> Commercial growth is worth
          pursuing — it is permanent, it does not raise anyone&rsquo;s bill, and over a
          decade it compounds into real money. It is simply too small and too slow to be
          the answer to a {usd(gap)} hole that reopens and widens every year. Treat it as
          the ten-year strategy it is, and settle FY28 with the fees, savings and cuts on
          the Adjust page.
        </p>
      </div>
    </div>
  )
}

/** The conclusions, stated before the sliders rather than discovered inside them. */
function Findings({ gap, share }: { gap: number; share: number }) {
  const g = MODEL.assumptions
  const p1 = (n: number) => `${(n * 100).toFixed(0)}%`
  const mix = T.archetypes.find(a => a.id === 'mix')?.value ?? 3_005_000
  const oneDev = (mix * T.rate) / 1000
  const closesAt = T.currentNewGrowthValue
    + ((gap / share) * 1000) / T.rate
  const breakEven = T.schoolShareOfBill / T.localCostPerPupil

  const items = [
    {
      n: 1, anchor: 'bills', figure: '$0',
      head: 'A new business does not lower your tax bill.',
      body: `Proposition 2½ lets the town collect 2½% more each year PLUS the taxes on `
        + `anything newly built. The town takes the extra, so the rate does not move and `
        + `neither does your bill. New business is not a discount on your taxes — it is `
        + `money the town gets without raising them. The only way it reaches your bill is `
        + `if the town refuses to collect it, and Lunenburg has left $3.12 on the table in `
        + `a year.`,
    },
    {
      n: 2, anchor: 'commercial', figure: usd(oneDev),
      head: 'One typical development pays about $43,000 a year — and roughly half of it is the town’s, not the schools’.',
      body: `A $${(mix / 1e6).toFixed(1)}M commercial building pays ${usd(oneDev)} in `
        + `property tax. New growth lifts the TOWN's levy limit, and the schools receive `
        + `their share of town revenue — about ${(share * 100).toFixed(0)}¢ in the dollar, `
        + `or ${usd(oneDev * share)} of it. The rest funds fire, police, DPW and everything `
        + `else. That is ${((oneDev * share) / gap * 100).toFixed(1)}% of next year's `
        + `school gap, per building.`,
    },
    {
      n: 3, anchor: 'commercial', figure: `${Math.round(closesAt / mix)}/yr`,
      head: 'Closing the school gap with growth alone needs about four times the town’s historical pace.',
      body: `${usdShort(closesAt)} of new commercial value every year — roughly `
        + `${Math.round(closesAt / mix)} developments or `
        + `${Math.round(closesAt / T.avgCommercialValue)} businesses — against a town that `
        + `has 234 commercial parcels in total and whose actual new growth has been FALLING, `
        + `from $481,000 in FY2018 to $234,000 in FY2023. And that rate only holds the line `
        + `to about FY32 before costs outrun it again.`,
    },
    {
      n: 4, anchor: 'residential', figure: breakEven.toFixed(2),
      head: 'Housing pays for itself only below 0.36 children per home.',
      body: `A home pays ${usd(T.schoolShareOfBill)} a year toward schools — `
        + `${(T.schoolShareOfBudget * 100).toFixed(0)}% of its ${usd(T.avgHomeBill)} bill. `
        + `One student costs the levy ${usd(T.localCostPerPupil)}. So a new house breaks `
        + `even at ${breakEven.toFixed(2)} schoolchildren and costs money above that. A `
        + `commercial building of the same assessed value pays the same tax and sends `
        + `nobody.`,
    },
    {
      n: 5, anchor: 'mix', figure: '92.7%',
      head: 'Homeowners carry almost the whole tax base, and the share is moving the wrong way.',
      body: `One tax rate means a class's share of the base is its share of the bill. `
        + `Homes are ${(T.fy23.residentialShare * 100).toFixed(1)}% of it, business `
        + `${(T.fy23.cipShare * 100).toFixed(1)}%. Carry on at the town's recent pace — `
        + `essentially all of new growth residential, while commercial value actually FELL `
        + `0.25% and industrial 3.2% — and business's share drops to about 6.7% in ten `
        + `years. Even the maximum legal split rate only moves residential bills about 4%, `
        + `because there is so little business to shift onto.`,
    },
    {
      n: 6, anchor: 'bills',
      figure: `${((COST_GROWTH_BLENDED - 0.025) * 100).toFixed(2)} pts`,
      head: 'The gap is a growth-rate problem, so it reopens every year no matter what is built.',
      body: `School costs rise ${(COST_GROWTH_BLENDED * 100).toFixed(2)}% a year blended `
        + `— salaries ${p1(g.salaries)}, health insurance ${p1(g.health)}, in-district `
        + `special education ${p1(g.sped)} — while the levy is capped at 2½%. That `
        + `${((COST_GROWTH_BLENDED - 0.025) * 100).toFixed(2)}-point difference compounds `
        + `into ${usd(gap)} next year, and keeps compounding. `
        + `A dollar of new growth can be spent once: on a lower tax bill or on a classroom. `
        + `There is no version where a large bill cut and a funded school budget both `
        + `happen.`,
    },
  ]

  return (
    <ol className="grid gap-3 md:grid-cols-2">
      {items.map(c => (
        <li key={c.n}>
          <a href={`#${c.anchor}`}
            className="card p-5 h-full flex flex-col hover:opacity-90 transition-opacity">
            <div className="flex items-baseline justify-between gap-3 mb-2">
              <span className="text-[11px] font-bold tnum tracking-widest"
                style={{ color: 'var(--text-muted)' }}>
                {String(c.n).padStart(2, '0')}
              </span>
              <span className="text-lg font-bold tnum shrink-0"
                style={{ color: 'var(--status-critical)' }}>{c.figure}</span>
            </div>
            <h3 className="text-[15px] font-bold leading-snug mb-2">{c.head}</h3>
            <p className="text-[13px] leading-relaxed flex-1"
              style={{ color: 'var(--text-secondary)' }}>{c.body}</p>
            <span className="text-[11px] font-semibold mt-3"
              style={{ color: 'var(--series-cost)' }}>See the working &rarr;</span>
          </a>
        </li>
      ))}
    </ol>
  )
}

interface Policy {
  keep: number; split: boolean; debtOff: boolean; levyCut: number
}

/** The average bill in ten years under a given policy. Shared by the recipe and the
 *  full model so the two can never disagree. */
function billIn10(p: Policy, newTotal: number): number {
  const ngRev = (newTotal * T.rate) / 1000
  let levy = T.levy
  let base = T.totalValue
  for (let i = 1; i <= 10; i++) {
    if (i === 1) levy -= p.levyCut + (p.debtOff ? MODEL.fy27.excluded_debt : 0)
    levy = levy * (1 + T.levyGrowth) + ngRev * (p.keep / 100)
    base += newTotal
    const rate = (levy * 1000) / base
    const resRate = p.split ? T.splitRate.residential * (rate / T.rate) : rate
    if (i === 10) return (T.avgHomeValue * resRate) / 1000
  }
  return T.avgHomeBill
}

/** Work backwards from a target bill to the cheapest recipe that reaches it.
 *
 *  Levers are applied in order of what they cost the schools: the split rate costs
 *  nothing, retiring excluded debt is already scheduled, declining new growth costs the
 *  schools their share of it, and cutting the levy costs the most. Each is used only as
 *  far as it is needed. */
function solve(targetBill: number, newTotal: number) {
  const steps: { id: string; label: string; detail: string; bill: number }[] = []
  const p: Policy = { keep: 100, split: false, debtOff: false, levyCut: 0 }
  const baseline = billIn10(p, newTotal)

  const done = () => billIn10(p, newTotal) <= targetBill
  if (done()) return { steps, baseline, final: baseline, reached: true, policy: p }

  p.split = true
  steps.push({ id: 'split', label: 'Adopt the maximum split tax rate',
    detail: `Homes drop to ${usd(T.splitRate.residential)} per $1,000 and business rises to `
      + `${usd(T.splitRate.commercial)}. The town loses nothing — it moves about `
      + `${usd(T.splitRate.avgCommercialIncrease)} a year onto the average business.`,
    bill: billIn10(p, newTotal) })
  if (done()) return { steps, baseline, final: billIn10(p, newTotal), reached: true, policy: p }

  p.debtOff = true
  steps.push({ id: 'debt', label: 'Retire the excluded debt and add none',
    detail: `${usd(MODEL.fy27.excluded_debt)} of the levy is debt voters excluded for `
      + 'specific projects. It leaves the bill when those are paid off — but only if the '
      + 'town does not vote new ones in behind them.',
    bill: billIn10(p, newTotal) })
  if (done()) return { steps, baseline, final: billIn10(p, newTotal), reached: true, policy: p }

  // How much new growth must be declined — find the highest keep% that still reaches it.
  let keep = 100
  while (keep > 0 && billIn10({ ...p, keep }, newTotal) > targetBill) keep -= 5
  p.keep = Math.max(0, keep)
  const declined = ((newTotal * T.rate) / 1000) * (1 - p.keep / 100)
  if (declined > 0) {
    steps.push({ id: 'growth', label: `Decline ${100 - p.keep}% of all new growth revenue`,
      detail: `The town would refuse ${usd(declined)} a year it is entitled to collect, `
        + 'every year, and let the bigger tax base lower the rate instead. Lunenburg has '
        + 'never done this — it left $3.12 on the table in FY2020.',
      bill: billIn10(p, newTotal) })
  }
  if (done()) return { steps, baseline, final: billIn10(p, newTotal), reached: true, policy: p }

  // Whatever is left has to come out of the town budget.
  let lo = 0, hi = 40_000_000
  for (let i = 0; i < 40; i++) {
    const mid = (lo + hi) / 2
    if (billIn10({ ...p, levyCut: mid }, newTotal) > targetBill) lo = mid
    else hi = mid
  }
  p.levyCut = hi
  steps.push({ id: 'cut', label: `Cut ${usd(p.levyCut)} from the town budget, permanently`,
    detail: `That is ${((p.levyCut / MODEL.fy27.omnibus) * 100).toFixed(0)}% of everything `
      + `Lunenburg spends — schools, fire, police, roads and all — against a school `
      + `appropriation of ${usd(MODEL.fy27.lps_appropriation)}.`,
    bill: billIn10(p, newTotal) })

  const final = billIn10(p, newTotal)
  return { steps, baseline, final, reached: final <= targetBill + 1, policy: p }
}

/** The recipe, in sentences. */
function PlainAnswer({ commercial, homes, gap, share }: {
  commercial: number; homes: number; gap: number; share: number
}) {
  const [saving, setSaving] = useState(1000)
  const newTotal = commercial + homes
  const target = T.avgHomeBill - saving
  const r = useMemo(() => solve(target, newTotal), [target, newTotal])

  const declined = ((newTotal * T.rate) / 1000) * (1 - r.policy.keep / 100)
  const schoolsLose = (declined + r.policy.levyCut) * share

  return (
    <div>
      <div className="card p-5 mb-4">
        <div className="flex items-baseline justify-between gap-3 mb-1">
          <label htmlFor="saving" className="text-[13px] font-medium">
            How much lower do you want the average tax bill?
          </label>
          <span className="text-2xl font-bold tnum">
            &minus;{usd(saving)}
            <span className="text-[11px] font-normal ml-1.5"
              style={{ color: 'var(--text-muted)' }}>
              {usd(T.avgHomeBill)} &rarr; {usd(target)}
            </span>
          </span>
        </div>
        <input id="saving" type="range" min={0} max={4000} step={100} value={saving}
          onChange={e => setSaving(Number(e.target.value))} className="w-full" />
        <p className="text-[11px]" style={{ color: 'var(--text-muted)' }}>
          Measured against today&rsquo;s bill, ten years out. Left alone, the bill would be{' '}
          <strong>{usd(r.baseline)}</strong> by then, because the levy rises 2&frac12;% a
          year whatever anyone does.
        </p>
      </div>

      <div className="card p-5">
        <h3 className="text-base font-bold mb-1">
          To pay {usd(saving)} less than today, Lunenburg would have to:
        </h3>
        {r.steps.length === 0 ? (
          <p className="text-[13px]" style={{ color: 'var(--text-secondary)' }}>
            Nothing at all — the bill already lands below that on its own. Move the slider
            further.
          </p>
        ) : (
          <ol className="mt-3 space-y-3">
            {r.steps.map((st, i) => (
              <li key={st.id} className="flex gap-3">
                <span className="shrink-0 w-6 h-6 rounded-full flex items-center justify-center
                  text-[11px] font-bold" style={{ background: 'var(--surface-3)' }}>
                  {i + 1}
                </span>
                <span className="flex-1 min-w-0">
                  <span className="flex items-baseline justify-between gap-3">
                    <span className="text-[14px] font-semibold">{st.label}</span>
                    <span className="text-[12px] tnum shrink-0"
                      style={{ color: 'var(--text-muted)' }}>
                      bill &rarr; {usd(st.bill)}
                    </span>
                  </span>
                  <span className="block text-[12px] leading-relaxed mt-0.5"
                    style={{ color: 'var(--text-secondary)' }}>{st.detail}</span>
                </span>
              </li>
            ))}
          </ol>
        )}

        <div className="grid gap-3 sm:grid-cols-3 mt-5 pt-4 border-t"
          style={{ borderColor: 'var(--grid)' }}>
          <Fig label="Bill in ten years" value={usd(r.final)}
            tone={r.reached ? 'var(--status-good)' : 'var(--status-critical)'}
            sub={`${usd(T.avgHomeBill)} today, ${usd(r.baseline)} if nothing changes`} />
          <Fig label="The schools lose" value={usd(schoolsLose)}
            tone={schoolsLose > 0 ? 'var(--status-critical)' : 'var(--text-primary)'}
            sub="every year, from revenue the town declines or cuts" />
          <Fig label="School gap becomes" value={usd(gap + schoolsLose)}
            tone={schoolsLose > 0 ? 'var(--status-critical)' : 'var(--text-primary)'}
            sub={`from ${usd(gap)} today — to be closed by cuts, fees or an override`} />
        </div>

        <p className="text-[13px] leading-relaxed mt-4 pt-4 border-t"
          style={{ color: 'var(--text-secondary)', borderColor: 'var(--grid)' }}>
          <strong>The trade, in one sentence.</strong> {saving === 0
            ? 'Ask for nothing and nothing changes: the bill still rises 2½% a year.'
            : schoolsLose > 0
              ? <>Every dollar off a tax bill past the first {usd(r.steps[0]?.bill
                  ? T.avgHomeBill - r.steps[0].bill : 0)} comes out of what the town
                collects, and about {(share * 100).toFixed(0)}&cent; in each of those
                dollars was the schools&rsquo;. There is no version of this where the bill
                falls a lot and the school budget is unaffected.</>
              : <>This much is free — the split rate and retiring excluded debt move money
                without the town collecting less. Past this point it stops being free.</>}
        </p>
      </div>
    </div>
  )
}

/** What it would actually take to lower a homeowner's bill.
 *
 *  Every other page here is about the school budget. This one is about the other half of
 *  the argument, and it has to be as honest: bills rise 2.5% a year on their own, so the
 *  levers are measured against that trajectory rather than against today. Three of the
 *  four cost the town revenue, and the fourth is capped by arithmetic. */
function BillModel({ commercial, homes, gap, share }: {
  commercial: number; homes: number; gap: number; share: number
}) {
  const [target, setTarget] = useState(20)
  const [keep, setKeep] = useState(100)
  const [split, setSplit] = useState(false)
  const [levyCut, setLevyCut] = useState(0)
  const [debtOff, setDebtOff] = useState(false)

  const newTotal = commercial + homes
  const ngRev = (newTotal * T.rate) / 1000
  const excluded = MODEL.fy27.excluded_debt

  const rows = useMemo(() => {
    const out: { year: number; nothing: number; policy: number; target: number }[] = []
    let levy = T.levy
    let base = T.totalValue
    for (let i = 1; i <= 10; i++) {
      if (i === 1) levy -= levyCut + (debtOff ? excluded : 0)
      levy = levy * (1 + T.levyGrowth) + ngRev * (keep / 100)
      base += newTotal
      const rate = (levy * 1000) / base
      const resRate = split ? T.splitRate.residential * (rate / T.rate) : rate
      out.push({
        year: i,
        nothing: Math.round(T.avgHomeBill * Math.pow(1 + T.levyGrowth, i)),
        policy: Math.round((T.avgHomeValue * resRate) / 1000),
        target: Math.round(T.avgHomeBill * (1 - target / 100)),
      })
    }
    return out
  }, [keep, split, levyCut, debtOff, newTotal, ngRev, target])

  const yr10 = rows[9]
  const vsToday = (yr10.policy / T.avgHomeBill - 1) * 100
  const vsNothing = (yr10.policy / yr10.nothing - 1) * 100
  const hit = yr10.policy <= yr10.target
  // What the homeowner saving costs: revenue the town never collects.
  const forgone = ngRev * (1 - keep / 100) + levyCut + (debtOff ? 0 : 0)
  const schoolsLose = forgone * share

  return (
    <div>
      <div className="grid gap-4 lg:grid-cols-2 mb-4">
        <div className="card p-5">
          <div className="flex items-baseline justify-between gap-3 mb-1">
            <label htmlFor="tgt" className="text-[13px] font-medium">
              Target: bill below today&rsquo;s, in ten years
            </label>
            <span className="text-xl font-bold tnum">
              &minus;{target}%
              <span className="text-[11px] font-normal ml-1"
                style={{ color: 'var(--text-muted)' }}>= {usd(yr10.target)}</span>
            </span>
          </div>
          <input id="tgt" type="range" min={0} max={50} step={5} value={target}
            onChange={e => setTarget(Number(e.target.value))} className="w-full mb-1" />
          <p className="text-[11px] mb-4" style={{ color: 'var(--text-muted)' }}>
            Doing nothing puts the bill at <strong>{usd(yr10.nothing)}</strong> by then, so
            a {target}% cut off today is really a{' '}
            <strong>{(100 - (yr10.target / yr10.nothing) * 100).toFixed(0)}% cut off the
            trajectory</strong>.
          </p>

          <div className="pt-3 border-t" style={{ borderColor: 'var(--grid)' }}>
            <div className="flex items-baseline justify-between gap-3 mb-1">
              <label htmlFor="keep2" className="text-[13px] font-medium">
                1 &middot; Levy this share of new growth
              </label>
              <span className="text-sm font-bold tnum">{keep}%</span>
            </div>
            <input id="keep2" type="range" min={0} max={100} step={5} value={keep}
              onChange={e => setKeep(Number(e.target.value))} className="w-full" />
            <p className="text-[10px] mb-3" style={{ color: 'var(--text-muted)' }}>
              Growth raises what the town <em>may</em> collect, not what it must. Declining
              it is the only mechanism that lowers an existing bill through development.
              Lunenburg has left essentially nothing on the table &mdash; $3.12 in FY2020.
            </p>

            <div className="flex items-baseline justify-between gap-3 mb-1">
              <label htmlFor="cut" className="text-[13px] font-medium">
                2 &middot; Cut from the levy, permanently
              </label>
              <span className="text-sm font-bold tnum">{usdShort(levyCut)}</span>
            </div>
            <input id="cut" type="range" min={0} max={10_000_000} step={250_000}
              value={levyCut} onChange={e => setLevyCut(Number(e.target.value))}
              className="w-full" />
            <p className="text-[10px] mb-3" style={{ color: 'var(--text-muted)' }}>
              Out of a {usdShort(MODEL.fy27.omnibus)} town budget. Halving the average bill
              this way alone would take {usd(T.levy / 2)} &mdash; 36% of everything the town
              does.
            </p>

            <label className="flex items-start gap-2.5 cursor-pointer mb-2">
              <input type="checkbox" checked={split}
                onChange={e => setSplit(e.target.checked)}
                className="mt-0.5 shrink-0" style={{ accentColor: 'var(--series-cost)' }} />
              <span>
                <span className="block text-[13px] font-medium">
                  3 &middot; Adopt the maximum split tax rate
                </span>
                <span className="block text-[10px]" style={{ color: 'var(--text-muted)' }}>
                  The only lever that costs the town nothing. Worth about{' '}
                  {usd(T.avgHomeBill - (T.avgHomeValue * T.splitRate.residential) / 1000)} —
                  capped because business is only{' '}
                  {(T.fy23.cipShare * 100).toFixed(1)}% of the base. The average business
                  pays {usd(T.splitRate.avgCommercialIncrease)} more.
                </span>
              </span>
            </label>

            <label className="flex items-start gap-2.5 cursor-pointer">
              <input type="checkbox" checked={debtOff}
                onChange={e => setDebtOff(e.target.checked)}
                className="mt-0.5 shrink-0" style={{ accentColor: 'var(--series-cost)' }} />
              <span>
                <span className="block text-[13px] font-medium">
                  4 &middot; Let excluded debt roll off
                </span>
                <span className="block text-[10px]" style={{ color: 'var(--text-muted)' }}>
                  {usd(excluded)} of the levy is debt voters excluded for specific projects.
                  When they are paid off it leaves the bill permanently — worth about{' '}
                  {usd((T.avgHomeValue * (excluded / T.totalValue)))} a year. It is the one
                  lever that arrives on its own schedule, not the town&rsquo;s.
                </span>
              </span>
            </label>
          </div>
        </div>

        <div className="card p-5">
          <h3 className="text-sm font-bold mb-3">Where the average bill lands</h3>
          <div className="grid grid-cols-2 gap-3 mb-4">
            <div>
              <p className="text-3xl font-bold tnum leading-none"
                style={{ color: hit ? 'var(--status-good)' : 'var(--status-critical)' }}>
                {usd(yr10.policy)}
              </p>
              <p className="text-[11px] mt-1" style={{ color: 'var(--text-secondary)' }}>
                in ten years — {vsToday >= 0 ? '+' : ''}{vsToday.toFixed(0)}% vs today
              </p>
            </div>
            <div>
              <p className="text-3xl font-bold tnum leading-none"
                style={{ color: 'var(--text-primary)' }}>
                {vsNothing.toFixed(0)}%
              </p>
              <p className="text-[11px] mt-1" style={{ color: 'var(--text-secondary)' }}>
                below doing nothing ({usd(yr10.nothing)})
              </p>
            </div>
          </div>

          <dl className="space-y-2 text-[13px] pt-3 border-t" style={{ borderColor: 'var(--grid)' }}>
            <Row k="Target bill" v={usd(yr10.target)} />
            <Row k="Revenue the town gives up, per year" v={usd(forgone)} />
            <Row k="Of which the schools lose" v={usd(schoolsLose)} />
            <Row k="School gap it leaves" v={usd(gap + schoolsLose)} />
          </dl>

          <p className="text-[13px] leading-relaxed mt-4 pt-3 border-t"
            style={{ color: 'var(--text-secondary)', borderColor: 'var(--grid)' }}>
            {hit
              ? <><strong style={{ color: 'var(--status-good)' }}>Target reached.</strong>{' '}
                It costs {usd(forgone)} a year of town revenue, {usd(schoolsLose)} of it the
                schools&rsquo;, on top of a gap that is already {usd(gap)}. That is the
                trade — this page does not pretend there is a version without one.</>
              : <><strong style={{ color: 'var(--status-critical)' }}>Short of the
                target.</strong> Every lever is pulled as far as it is set and the bill
                still lands at {usd(yr10.policy)} against a {usd(yr10.target)} target. The
                arithmetic that makes this hard: the levy rises 2&frac12;% a year by right,
                business is only {(T.fy23.cipShare * 100).toFixed(1)}% of the base so
                shifting onto it is capped near 5%, and everything else means the town
                collecting less.</>}
          </p>
        </div>
      </div>

      <div style={{ width: '100%', height: 280 }}>
        <ResponsiveContainer>
          <LineChart data={rows} margin={{ top: 8, right: 12, bottom: 4, left: 4 }}>
            <CartesianGrid stroke="var(--grid)" vertical={false} />
            <XAxis dataKey="year" tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
              stroke="var(--axis)" tickLine={false} tickFormatter={v => `yr ${v}`} />
            <YAxis width={56} tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
              stroke="var(--axis)" tickLine={false} axisLine={false}
              tickFormatter={v => usdShort(v as number)} />
            <Tooltip
              contentStyle={{ background: 'var(--surface-1)', border: '1px solid var(--grid)',
                              borderRadius: 10, fontSize: 12, color: 'var(--text-primary)' }}
              labelFormatter={v => `Year ${v}`}
              formatter={(v, n) => [usd(v as number),
                n === 'policy' ? 'Your policy' : n === 'target' ? 'Your target' : 'If nothing changes']} />
            <Legend verticalAlign="top" height={28} iconType="plainline"
              wrapperStyle={{ fontSize: 12, color: 'var(--text-secondary)' }}
              formatter={v => v === 'policy' ? 'Your policy'
                : v === 'target' ? 'Your target' : 'If nothing changes'} />
            <Line type="monotone" dataKey="nothing" stroke="var(--series-revenue)"
              strokeWidth={2} dot={false} isAnimationActive={false} />
            <Line type="monotone" dataKey="policy" stroke="var(--series-cost)"
              strokeWidth={2} dot={false} isAnimationActive={false} />
            <Line type="monotone" dataKey="target" stroke="var(--status-good)"
              strokeWidth={2} strokeDasharray="5 4" dot={false} isAnimationActive={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <Note>
        The average home is assumed to appreciate in line with the town, which is what makes
        this a bill chart rather than an assessment chart: if every property doubles and the
        levy is unchanged, the rate halves and nobody&rsquo;s bill moves. Split-rate figures
        scale the state&rsquo;s published maximum-shift rates for Lunenburg
        ({usd(T.splitRate.residential)} residential, {usd(T.splitRate.commercial)} business).
        <strong> There is no peer comparison here yet</strong> — the model has no tax rates
        for neighbouring towns, so &ldquo;competitive with nearby towns&rdquo; needs a
        source before this page can answer it.
      </Note>
    </div>
  )
}

function Fig({ label, value, sub, tone }: {
  label: string; value: string; sub: string; tone?: string
}) {
  return (
    <div className="card p-4">
      <p className="text-[11px] font-semibold uppercase tracking-widest mb-1"
        style={{ color: 'var(--text-muted)' }}>{label}</p>
      <p className="text-xl font-bold tnum leading-none"
        style={{ color: tone ?? 'var(--text-primary)' }}>{value}</p>
      <p className="text-[11px] mt-1.5" style={{ color: 'var(--text-secondary)' }}>{sub}</p>
    </div>
  )
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex items-baseline justify-between gap-3">
      <dt style={{ color: 'var(--text-secondary)' }}>{k}</dt>
      <dd className="font-bold tnum">{v}</dd>
    </div>
  )
}

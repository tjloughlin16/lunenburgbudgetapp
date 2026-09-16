import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from 'recharts'
import { MODEL, usdShort } from '../model/engine'

const T = MODEL.taxBase
const F = T.base
const signedPct = (x: number) => `${x >= 0 ? 'rose' : 'fell'} ${Math.abs(x).toFixed(x % 1 === 0 ? 0 : 1)}%`
// The latest certified step, by class, read off the state's series -- never typed.
const STEP = Object.fromEntries(T.valueByClass.map(v => [v.cls, v])) as Record<string, (typeof T.valueByClass)[number]>
const RES_STEP = STEP['Residential'], COM_STEP = STEP['Commercial'], IND_STEP = STEP['Industrial']
// What the town actually added in the anchor year, split as the assessors certified it.
const NEW_RES = F.newGrowthResidentialValue
const NEW_CIP = F.newGrowthValue - F.newGrowthResidentialValue
const NEW_RES_SHARE = NEW_RES / F.newGrowthValue

/** Who owns the tax base, and where it is heading.
 *
 *  Lunenburg has ONE tax rate, so a class's share of the taxable base is exactly its
 *  share of the tax bill. Homeowners currently carry 92.7% of it. The intuition that
 *  commercial growth shifts that burden is right in principle — but only if commercial
 *  value grows faster than residential, and it has been doing the opposite.
 *
 *  Appreciation is deliberately not modeled: if both classes appreciate at the same
 *  rate it cancels out of a share calculation entirely. What moves the mix is new
 *  construction in each class, which is what this chart takes as its two inputs. When
 *  homes appreciate FASTER than commercial — as they did in FY23, 23% against a fall —
 *  the mix shifts toward homeowners no matter what gets built. The note below states
 *  the latest certified step from the data, whichever way it went. */
export function TaxBaseMix({ commercialPerYear, homesPerYear, setHomesPerYear }: {
  commercialPerYear: number
  homesPerYear: number
  /** Omitted when another control on the page already owns the housing rate. */
  setHomesPerYear?: (n: number) => void
}) {

  const years = Array.from({ length: 11 }, (_, i) => {
    const res = F.residentialValue + homesPerYear * i
    const cip = F.cipValue + commercialPerYear * i
    return {
      year: i,
      residential: +((res / (res + cip)) * 100).toFixed(2),
      commercial: +((cip / (res + cip)) * 100).toFixed(2),
    }
  })
  const now = years[0]
  const end = years[10]
  const rising = end.commercial > now.commercial

  // What the town has actually been doing, for contrast.
  const actual = (() => {
    const res = F.residentialValue + NEW_RES * 10
    const cip = F.cipValue + NEW_CIP * 10
    return ((cip / (res + cip)) * 100).toFixed(1)
  })()

  return (
    <div>
      <div className="grid gap-4 md:grid-cols-3 mb-4">
        <Stat label="Homeowners pay now" value={`${now.residential.toFixed(1)}%`}
          sub={`${usdShort(F.residentialValue)} of the ${usdShort(F.totalValue)} taxable base`} />
        <Stat label="Business pays now" value={`${now.commercial.toFixed(1)}%`}
          sub={`${usdShort(F.cipValue)} — commercial, industrial and personal property`} />
        <Stat label="Business in year 10" value={`${end.commercial.toFixed(1)}%`}
          tone={rising ? 'var(--status-good)' : 'var(--status-critical)'}
          sub={rising
            ? `up ${(end.commercial - now.commercial).toFixed(1)} points at this build rate`
            : `down ${(now.commercial - end.commercial).toFixed(1)} points at this build rate`} />
      </div>

      {setHomesPerYear && <div className="card p-4 mb-4">
        <label htmlFor="homes" className="flex items-baseline justify-between gap-3 mb-1">
          <span className="text-[13px] font-medium">
            New homes built per year
            <span className="block text-[11px] font-normal" style={{ color: 'var(--text-muted)' }}>
              the other half of the mix — commercial comes from the slider above
            </span>
          </span>
          <span className="text-sm font-bold tnum shrink-0">
            {usdShort(homesPerYear)}
            <span className="text-[11px] font-normal ml-1" style={{ color: 'var(--text-muted)' }}>
              ≈ {Math.round(homesPerYear / T.avgHomeValue)} homes
            </span>
          </span>
        </label>
        <input id="homes" type="range" min={0} max={60_000_000} step={1_000_000}
          value={homesPerYear} onChange={e => setHomesPerYear(Number(e.target.value))}
          className="w-full" />
        <p className="text-[10px] mt-0.5" style={{ color: 'var(--text-muted)' }}>
          Defaulted to {usdShort(NEW_RES)} &mdash; the residential part of the town&rsquo;s FY{F.fy} new growth,
          {(NEW_RES_SHARE * 100).toFixed(0)}% of the {usdShort(F.newGrowthValue)} the assessors certified that year.
        </p>
      </div>}

      <div style={{ width: '100%', height: 240 }}>
        <ResponsiveContainer>
          <AreaChart data={years} margin={{ top: 8, right: 12, bottom: 4, left: 4 }}
            stackOffset="expand">
            <CartesianGrid stroke="var(--grid)" vertical={false} />
            <XAxis dataKey="year" tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
              stroke="var(--axis)" tickLine={false}
              tickFormatter={v => v === 0 ? 'now' : `yr ${v}`} />
            <YAxis width={44} tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
              stroke="var(--axis)" tickLine={false} axisLine={false}
              tickFormatter={v => `${Math.round((v as number) * 100)}%`} />
            <Tooltip
              contentStyle={{ background: 'var(--surface-1)', border: '1px solid var(--grid)',
                              borderRadius: 10, fontSize: 12, color: 'var(--text-primary)' }}
              labelFormatter={v => v === 0 ? 'Today' : `Year ${v}`}
              formatter={(v, n) => [`${(v as number).toFixed(1)}%`,
                n === 'residential' ? 'Homeowners' : 'Business']} />
            <Legend verticalAlign="top" height={28} iconType="square"
              wrapperStyle={{ fontSize: 12, color: 'var(--text-secondary)' }}
              formatter={v => v === 'residential' ? 'Homeowners' : 'Business'} />
            <Area type="monotone" dataKey="residential" stackId="1"
              stroke="var(--series-revenue)" fill="var(--series-revenue)"
              fillOpacity={0.75} isAnimationActive={false} />
            <Area type="monotone" dataKey="commercial" stackId="1"
              stroke="var(--series-cost)" fill="var(--series-cost)"
              fillOpacity={0.85} isAnimationActive={false} />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      <p className="text-[13px] leading-relaxed mt-3 pt-3 border-t"
        style={{ color: 'var(--text-secondary)', borderColor: 'var(--grid)' }}>
        <strong>Yes &mdash; but only if business outgrows housing{Number(actual) > now.commercial ? ', and at the latest certified pace it just does' : ', and at the latest certified pace it does not'}.</strong>{' '}
        Lunenburg has a single tax rate, so a class&rsquo;s share of the taxable base is
        exactly its share of the tax bill. Homeowners carry{' '}
        <strong>{now.residential.toFixed(1)}%</strong> of it. Carry on at the town&rsquo;s
        latest certified pace &mdash; {usdShort(F.newGrowthValue)} of new value in FY{F.fy}, {(NEW_RES_SHARE * 100).toFixed(0)}% of it housing &mdash;
        and business&rsquo;s share {Number(actual) > now.commercial ? <>edges <em>up</em></> : <><em>falls</em></>} to
        about <strong>{actual}%</strong> in ten years{Number(actual) > now.commercial ? ', a shift of well under a point' : '. Homeowners end up carrying more, not less'}.
      </p>
      <p className="text-[12px] leading-relaxed mt-2" style={{ color: 'var(--text-muted)' }}>
        Two things this chart does not do. It ignores appreciation, because if homes and
        businesses appreciate at the same rate it cancels out of a share calculation
        &mdash; and they do not always: in FY{RES_STEP.toFy} residential value {signedPct(RES_STEP.pct)}
        while commercial {signedPct(COM_STEP.pct)} and industrial {signedPct(IND_STEP.pct)}, and a year
        where homes outrun business pushes the mix toward homeowners regardless of what
        gets built (FY23 was one: homes up 23%, every other class down). And a smaller share is not a smaller bill: Proposition 2&frac12; sets
        what the town collects, so a shifting mix changes who owes what portion of a
        growing total, not what lands in your mailbox.
      </p>
    </div>
  )
}

function Stat({ label, value, sub, tone }: {
  label: string; value: string; sub: string; tone?: string
}) {
  return (
    <div className="card p-4">
      <p className="text-[11px] font-semibold uppercase tracking-widest mb-1"
        style={{ color: 'var(--text-muted)' }}>{label}</p>
      <p className="text-2xl font-bold tnum leading-none"
        style={{ color: tone ?? 'var(--text-primary)' }}>{value}</p>
      <p className="text-[11px] mt-1.5" style={{ color: 'var(--text-secondary)' }}>{sub}</p>
    </div>
  )
}

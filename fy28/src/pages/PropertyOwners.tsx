import { Bar, BarChart, CartesianGrid, ComposedChart, ErrorBar, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { FullVersion } from '../components/FullVersion'
import type { Tab } from '../routes'
import { Conclusions, Grain, H2, MoreReports, NotEstablished, Provenance, ReportShell, Stat, useReport } from '../components/report'
import type { Conclusion, Source } from '../components/report'

const TAB: Tab = 'owners'
const DATA = '/data/property-owners.json'

/** LUNENBURG'S HOMES AND THE TAX BILL. Beside Lunenburg by the numbers, in The town.
 *
 *  REFOCUSED on 13 September 2026. It began as "who owns the homes" -- TJ's question about
 *  being taxed out of a house bought decades ago -- and he redirected it the same day:
 *  "refocus on overall properties in lunenburg, not just ownership. your table of tax rates
 *  over time compared to median prices is a critical component. rates dropped, values went
 *  up, so residents feel 'higher taxes'. So the top level conclusion should be something
 *  like total homes, rates dropping, values going up... not the breakdown of home
 *  ownership." So: the homes, the bill over every year DLS publishes, the neighbours; then,
 *  lower, how long the owners have been here and what a long-held home pays.
 *
 *  The Census asks when the household ARRIVED; the assessor records the last DEED. Two
 *  tables, never added together. Rule 7b: conclusions, then the tables, then what is not
 *  established. */

type Band = { label: string; households: number; moe: number; share: number; share_moe: number }
type Vintage = { vintage: number; window: string; owners: number; owners_moe: number; bands: Band[]; before_2010: { households: number; moe: number; share: number }; since_1980s: { households: number; moe: number; share: number }; median_moved_in: number }
type DeedBand = { label: string; homes: number; share: number; median_value: number; median_bill: number; nominal_share: number | null; median_sale_price: number | null; arm_length: number }
type Payload = {
  about: string; grain: string
  tenure: { households: number; households_moe: number; owners: number; owners_moe: number; renters: number; renters_moe: number; owner_share: number; window: string }
  census: Record<string, Vintage>
  parcels: { fy: number; rate: number; parcels: number; single_family: number; median_value: number; median_bill: number; bands: DeedBand[]; held: { years: number; homes: number; share: number }[]; nominal: { deeds: number; share: number }; owner_in_town: { homes: number; share: number }; oldest_deed: number; earliest_band_bill_ratio: number }
  bills: {
    rows: { fy: number; parcels: number; value: number; bill: number; rate: number; bill_pct_income: number | null; rank: number | null }[]
    first_fy: number; last_fy: number; span: number; span_from_fy: number
    ten: { value_change: number; rate_change: number; bill_change: number; value_from: number; value_to: number; rate_from: number; rate_to: number; bill_from: number; bill_to: number }
    since_first: { value_change: number; rate_change: number; bill_change: number }
    neighbours: { town: string; parcels: number; value: number; bill: number; rate: number; bill_pct_income: number | null; income_per_capita: number | null; rank: number | null }[]
    position: number; of: number; statewide_rank: number | null; statewide_of: number; bill_pct_income: number | null; neighbour_median_bill: number
  }
  conclusions: Conclusion[]; not_established: string[]; sources: Source[]
}

const n0 = (n: number) => Math.round(n).toLocaleString('en-US')
const usd = (n: number) => '$' + Math.round(n).toLocaleString('en-US')
const pct = (x: number, d = 0) => `${(x * 100).toFixed(d)}%`
const FY = (fy: number) => 'FY' + String(fy).slice(2)
const AXIS = { fontSize: 11, fill: 'var(--text-muted)' }

function Box({ children }: { children: React.ReactNode }) {
  return <div className="card p-2.5 text-[12px]" style={{ minWidth: 180 }}>{children}</div>
}

export function PropertyOwners() {
  const { d, err } = useReport<Payload>('property-owners.json')
  const c = d?.census['2023']
  return (
    <ReportShell tab={TAB}
      title={d ? `${n0(d.bills.rows[d.bills.rows.length - 1].parcels)} homes; in ten years the value up ${pct(d.bills.ten.value_change)}, the rate down ${pct(-d.bills.ten.rate_change)}, the bill up ${pct(d.bills.ten.bill_change)}` : 'Lunenburg’s homes and the tax bill'}
      standfirst={d && c ? <>What the average single-family home in Lunenburg is worth and pays, every year the state has published, and against ten neighbours — then who has owned the homes how long, and what a house bought decades ago pays today.</> : undefined}
      err={err} loading={!d && !err} dataUrl={DATA}>
      {d && <Report d={d} />}
    </ReportShell>
  )
}

function Report({ d }: { d: Payload }) {
  const c23 = d.census['2023'], c18 = d.census['2018']
  const p = d.parcels, b = d.bills
  const byLabel18 = Object.fromEntries(c18.bands.map(x => [x.label, x]))
  return (
    <>
      <section data-section="conclusions" data-short="">
        {/* THE DENOMINATOR FIRST, then the two things that changed, then the neighbours. TJ:
            "we need the total homes first to understand other context." */}
        <div className="flex flex-wrap gap-x-10 gap-y-5 mt-8">
          <Stat value={n0(d.bills.rows[d.bills.rows.length - 1].parcels)}>single-family homes, {FY(b.last_fy)} — on {n0(p.parcels)} parcels of every kind; {pct(d.tenure.owner_share)} of the town’s {n0(d.tenure.households)} households own their home</Stat>
          <Stat value={pct(b.ten.bill_change)} tone="var(--series-cost)">more on the average home’s bill in ten years — {usd(b.ten.bill_from)} to {usd(b.ten.bill_to)} — while its value rose {pct(b.ten.value_change)} and the rate fell {pct(-b.ten.rate_change)}</Stat>
          <Stat value={usd(d.bills.rows[d.bills.rows.length - 1].bill)}>the average bill, {FY(b.last_fy)}: {b.position}th of {b.of} nearby towns and cities, {b.statewide_rank}th of {b.statewide_of} statewide</Stat>
        </div>
        <Grain>{d.grain}</Grain>
        <Conclusions rows={d.conclusions} />
      </section>
      {/* Everything below the short version is behind the fold -- see components/FullVersion.tsx. */}
      <FullVersion>

      <section data-section="categorical">
        <H2>The average home, every year the state has published</H2>
        <p className="text-sm max-w-3xl" style={{ color: 'var(--text-secondary)' }}>
          Proposition 2½ caps how fast the town’s total levy can grow; the rate is whatever divides that levy into the year’s total value. So when values rise the rate falls — and the bill on the average home does neither, it follows the levy. The dark bars are the bill; the line is the effective rate, bill ÷ value per $1,000.
        </p>
        <div style={{ width: '100%', height: 300 }} className="mt-4 avoid-break">
          <ResponsiveContainer>
            <ComposedChart data={b.rows.map(r => ({ fy: FY(r.fy), bill: r.bill, rate: r.rate, value: r.value }))} margin={{ top: 8, right: 8, left: 0, bottom: 4 }}>
              <CartesianGrid stroke="var(--grid)" vertical={false} />
              <XAxis dataKey="fy" tick={AXIS} stroke="var(--axis)" interval={4} />
              <YAxis yAxisId="bill" tick={AXIS} stroke="var(--axis)" tickFormatter={(v: number) => '$' + Math.round(v / 1000) + 'k'} />
              <YAxis yAxisId="rate" orientation="right" tick={AXIS} stroke="var(--axis)" tickFormatter={(v: number) => '$' + v.toFixed(0)} domain={[0, 'auto']} />
              <Tooltip content={({ active, payload, label }) => active && payload?.length ? (() => { const r = payload[0].payload as { bill: number; rate: number; value: number }; return <Box><p className="font-bold">{label}</p><p>average home {usd(r.value)}</p><p>bill {usd(r.bill)} · rate ${r.rate.toFixed(2)}</p></Box> })() : null} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Bar yAxisId="bill" dataKey="bill" name="average single-family bill" fill="var(--series-cost)" radius={[2, 2, 0, 0]} isAnimationActive={false} />
              <Line yAxisId="rate" type="monotone" dataKey="rate" name="effective rate, per $1,000" stroke="var(--text-primary)" strokeWidth={2} dot={false} isAnimationActive={false} />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
        <div className="overflow-x-auto mt-4">
          <table className="text-sm" style={{ minWidth: 640 }}>
            <thead><tr className="text-[10px] font-bold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>
              <th className="text-left py-1.5 pr-4">year</th><th className="text-right py-1.5 px-2">homes</th><th className="text-right py-1.5 px-2">average value</th><th className="text-right py-1.5 px-2">rate per $1,000</th><th className="text-right py-1.5 px-2">average bill</th><th className="text-right py-1.5 px-2">bill as % of income</th><th className="text-right py-1.5 pl-2">rank of 351</th></tr></thead>
            <tbody>{[...b.rows].reverse().map(r => (
              <tr key={r.fy} style={{ borderTop: '1px solid var(--grid)', fontWeight: r.fy === b.last_fy || r.fy === b.span_from_fy ? 600 : 400 }}>
                <td className="py-1 pr-4 tnum">{FY(r.fy)}</td>
                <td className="py-1 px-2 text-right tnum">{n0(r.parcels)}</td>
                <td className="py-1 px-2 text-right tnum">{usd(r.value)}</td>
                <td className="py-1 px-2 text-right tnum">${r.rate.toFixed(2)}</td>
                <td className="py-1 px-2 text-right tnum">{usd(r.bill)}</td>
                <td className="py-1 px-2 text-right tnum" style={{ color: 'var(--text-secondary)' }}>{r.bill_pct_income != null ? pct(r.bill_pct_income, 1) : '—'}</td>
                <td className="py-1 pl-2 text-right tnum" style={{ color: 'var(--text-muted)' }}>{r.rank ?? '—'}</td></tr>))}</tbody>
          </table>
        </div>
        <p className="text-xs mt-1 max-w-3xl" style={{ color: 'var(--text-muted)' }}>DLS Average Single-Family Tax Bill, {FY(b.first_fy)}–{FY(b.last_fy)}. “Homes” is the state’s count of single-family parcels; the rate is derived, bill ÷ value, and for a single-rate town equals the rate set — {FY(b.last_fy)}: ${b.rows[b.rows.length - 1].rate.toFixed(2)}. Bill as a share of DOR income per capita, where the state computed it. Bold rows are the two ends of the ten-year change above.</p>

        <H2>Against the neighbours, {FY(b.last_fy)}</H2>
        <div className="overflow-x-auto mt-4">
          <table className="text-sm" style={{ minWidth: 600 }}>
            <thead><tr className="text-[10px] font-bold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>
              <th className="text-left py-1.5 pr-4">town</th><th className="text-right py-1.5 px-2">homes</th><th className="text-right py-1.5 px-2">average value</th><th className="text-right py-1.5 px-2">rate</th><th className="text-right py-1.5 px-2">average bill</th><th className="text-right py-1.5 px-2">bill as % of income</th><th className="text-right py-1.5 pl-2">rank of {b.statewide_of}</th></tr></thead>
            <tbody>{b.neighbours.map(r => (
              <tr key={r.town} style={{ borderTop: '1px solid var(--grid)', fontWeight: r.town === 'Lunenburg' ? 700 : 400 }}>
                <td className="py-1.5 pr-4">{r.town}</td>
                <td className="py-1.5 px-2 text-right tnum">{n0(r.parcels)}</td>
                <td className="py-1.5 px-2 text-right tnum">{usd(r.value)}</td>
                <td className="py-1.5 px-2 text-right tnum">${r.rate.toFixed(2)}</td>
                <td className="py-1.5 px-2 text-right tnum">{usd(r.bill)}</td>
                <td className="py-1.5 px-2 text-right tnum" style={{ color: 'var(--text-secondary)' }}>{r.bill_pct_income != null ? pct(r.bill_pct_income, 1) : '—'}</td>
                <td className="py-1.5 pl-2 text-right tnum" style={{ color: 'var(--text-muted)' }}>{r.rank ?? '—'}</td></tr>))}</tbody>
          </table>
        </div>
        <p className="text-xs mt-1 max-w-3xl" style={{ color: 'var(--text-muted)' }}>Sorted by the bill. A higher bill is not a higher rate: Harvard and Groton tax at lower rates than Lunenburg on homes worth far more. The share-of-income column is the one that compares what the bill asks of the people paying it.</p>

        <H2>How long the owners have been here — the Census</H2>
        <p className="text-sm max-w-3xl" style={{ color: 'var(--text-secondary)' }}>
          Owner-occupied households by the year the householder moved in. A five-year sample: the margins are real, and the two windows do not overlap, which is what makes the comparison permissible.
        </p>
        {/* THE HISTOGRAM, oldest on the left so time reads left to right, with the margin
            drawn on every bar -- a sample's bar without its whisker is a count it is not. */}
        <div style={{ width: '100%', height: 260 }} className="mt-4 avoid-break">
          <ResponsiveContainer>
            <BarChart data={[...c23.bands].reverse().map(x => ({ label: x.label, households: x.households, moe: x.moe, share: x.share }))} margin={{ top: 8, right: 8, left: 0, bottom: 4 }}>
              <CartesianGrid stroke="var(--grid)" vertical={false} />
              <XAxis dataKey="label" tick={AXIS} stroke="var(--axis)" interval={0} />
              <YAxis tick={AXIS} stroke="var(--axis)" />
              <Tooltip cursor={{ fill: 'var(--surface-3)' }} content={({ active, payload }) => active && payload?.length ? (() => { const r = payload[0].payload as { label: string; households: number; moe: number; share: number }; return <Box><p className="font-bold">moved in {r.label}</p><p>{n0(r.households)} ± {n0(r.moe)} owner households</p><p style={{ color: 'var(--text-muted)' }}>{pct(r.share)} of owners</p></Box> })() : null} />
              <Bar dataKey="households" fill="var(--series-cost)" radius={[2, 2, 0, 0]} isAnimationActive={false}>
                <ErrorBar dataKey="moe" width={4} strokeWidth={1.5} stroke="var(--text-muted)" />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
        <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>Owner households by the year they moved in, {c23.window}; the whisker is the margin of error.</p>
        <div className="overflow-x-auto mt-4">
          <table className="text-sm" style={{ minWidth: 560 }}>
            <thead><tr className="text-[10px] font-bold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>
              <th className="text-left py-1.5 pr-4">moved in</th><th className="text-right py-1.5 px-2">households</th><th className="text-right py-1.5 px-2">± margin</th><th className="text-right py-1.5 px-2">share</th><th className="text-right py-1.5 pl-4" style={{ color: 'var(--text-muted)' }}>{c18.window}</th></tr></thead>
            <tbody>{c23.bands.map((x, i) => (
              <tr key={x.label} style={{ borderTop: '1px solid var(--grid)' }}>
                <td className="py-1.5 pr-4 font-semibold">{x.label}</td>
                <td className="py-1.5 px-2 text-right tnum">{n0(x.households)}</td>
                <td className="py-1.5 px-2 text-right tnum" style={{ color: 'var(--text-muted)' }}>{n0(x.moe)}</td>
                <td className="py-1.5 px-2 text-right tnum">{pct(x.share)}</td>
                <td className="py-1.5 pl-4 text-right tnum" style={{ color: 'var(--text-muted)' }}>{(() => { const o = c18.bands[i]; return o ? `${pct(o.share)} (${o.label})` : '' })()}</td></tr>))}
              <tr style={{ borderTop: '2px solid var(--grid)' }} className="font-bold">
                <td className="py-1.5 pr-4">all owner households</td><td className="py-1.5 px-2 text-right tnum">{n0(c23.owners)}</td><td className="py-1.5 px-2 text-right tnum" style={{ color: 'var(--text-muted)' }}>{n0(c23.owners_moe)}</td><td className="py-1.5 px-2 text-right tnum">100%</td><td className="py-1.5 pl-4 text-right tnum" style={{ color: 'var(--text-muted)' }}>{n0(c18.owners)}</td></tr>
            </tbody>
          </table>
        </div>
        <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>ACS B25038, {c23.window}; the older window’s bands are cut at different years, so they are shown beside, not under. Median year the owner moved in: {c23.median_moved_in} ({c18.window}: {c18.median_moved_in}). {byLabel18['1989 or earlier'] ? `Households in the house since the 1980s: ${n0(byLabel18['1989 or earlier'].households)} then, ${n0(c23.since_1980s.households)} now.` : ''}</p>

        <H2>How long the homes have been held — the assessor, and what each pays</H2>
        <p className="text-sm max-w-3xl" style={{ color: 'var(--text-secondary)' }}>
          Every single-family parcel in the {FY(p.fy)} assessing file — {n0(p.single_family)} of {n0(p.parcels)} parcels — by the year of its last recorded deed, with the median assessed value and the bill at the {FY(p.fy)} rate of ${p.rate.toFixed(2)}. A deed is not an arrival: {pct(p.nominal.share)} of them record a price under $1,000 — a trust, an estate, a family transfer — so the newest band is overstated and every older band is a floor.
        </p>
        <div style={{ width: '100%', height: 260 }} className="mt-4 avoid-break">
          <ResponsiveContainer>
            <BarChart data={[...p.bands].reverse().map(x => ({ label: x.label, homes: x.homes, bill: x.median_bill, share: x.share }))} margin={{ top: 8, right: 8, left: 0, bottom: 4 }}>
              <CartesianGrid stroke="var(--grid)" vertical={false} />
              <XAxis dataKey="label" tick={AXIS} stroke="var(--axis)" interval={0} />
              <YAxis tick={AXIS} stroke="var(--axis)" />
              <Tooltip cursor={{ fill: 'var(--surface-3)' }} content={({ active, payload }) => active && payload?.length ? (() => { const r = payload[0].payload as { label: string; homes: number; bill: number; share: number }; return <Box><p className="font-bold">last deed {r.label}</p><p>{n0(r.homes)} homes · {pct(r.share)}</p><p style={{ color: 'var(--text-muted)' }}>median bill {usd(r.bill)}</p></Box> })() : null} />
              <Bar dataKey="homes" fill="var(--text-secondary)" radius={[2, 2, 0, 0]} isAnimationActive={false} />
            </BarChart>
          </ResponsiveContainer>
        </div>
        <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>Single-family homes by the year of their last recorded deed, {FY(p.fy)} assessing file — a count, so no whisker; but the newest bar holds every nominal transfer, which is why the table beside it carries that share.</p>
        <div className="overflow-x-auto mt-4">
          <table className="text-sm" style={{ minWidth: 680 }}>
            <thead><tr className="text-[10px] font-bold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>
              <th className="text-left py-1.5 pr-4">last deed</th><th className="text-right py-1.5 px-2">homes</th><th className="text-right py-1.5 px-2">share</th><th className="text-right py-1.5 px-2">median value</th><th className="text-right py-1.5 px-2">median bill</th><th className="text-right py-1.5 px-2">median sale price</th><th className="text-right py-1.5 pl-2">nominal deeds</th></tr></thead>
            <tbody>{p.bands.map(x => (
              <tr key={x.label} style={{ borderTop: '1px solid var(--grid)' }}>
                <td className="py-1.5 pr-4 font-semibold">{x.label}</td>
                <td className="py-1.5 px-2 text-right tnum">{n0(x.homes)}</td>
                <td className="py-1.5 px-2 text-right tnum">{pct(x.share)}</td>
                <td className="py-1.5 px-2 text-right tnum">{usd(x.median_value)}</td>
                <td className="py-1.5 px-2 text-right tnum font-semibold">{usd(x.median_bill)}</td>
                <td className="py-1.5 px-2 text-right tnum" style={{ color: 'var(--text-secondary)' }}>{x.median_sale_price != null ? usd(x.median_sale_price) : '—'}</td>
                <td className="py-1.5 pl-2 text-right tnum" style={{ color: 'var(--text-muted)' }}>{x.nominal_share != null ? pct(x.nominal_share) : '—'}</td></tr>))}
              <tr style={{ borderTop: '2px solid var(--grid)' }} className="font-bold">
                <td className="py-1.5 pr-4">all single-family</td><td className="py-1.5 px-2 text-right tnum">{n0(p.single_family)}</td><td className="py-1.5 px-2 text-right tnum">100%</td><td className="py-1.5 px-2 text-right tnum">{usd(p.median_value)}</td><td className="py-1.5 px-2 text-right tnum">{usd(p.median_bill)}</td><td></td><td className="py-1.5 pl-2 text-right tnum" style={{ color: 'var(--text-muted)' }}>{pct(p.nominal.share)}</td></tr>
            </tbody>
          </table>
        </div>
        <p className="text-xs mt-1 max-w-3xl" style={{ color: 'var(--text-muted)' }}>Median sale price is of the arm’s-length deeds in the band only. The bill is value × rate before any exemption or abatement. Held at least {p.held.map(h => `${h.years} years: ${n0(h.homes)} homes (${pct(h.share)})`).join(' · ')} — floors, for the reason above. {pct(p.owner_in_town.share)} of single-family owners give a Lunenburg mailing address. Oldest deed on file: {p.oldest_deed}.</p>

      </section>

      <section data-section="raw">
        <NotEstablished rows={d.not_established} closes="Census PUMS microdata for the PUMA containing Lunenburg — tenure, year moved in and income per household, at the cost of covering several towns at once." />
        <Provenance sources={d.sources} />
      </section>
      </FullVersion>
      <MoreReports here={TAB} />
    </>
  )
}

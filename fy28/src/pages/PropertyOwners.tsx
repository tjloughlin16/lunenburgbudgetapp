import { Bar, BarChart, CartesianGrid, ErrorBar, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { Tab } from '../routes'
import { Conclusions, Grain, H2, MoreReports, NotEstablished, Provenance, ReportShell, Stat, useReport } from '../components/report'
import type { Conclusion, Source } from '../components/report'

const TAB: Tab = 'owners'
const DATA = '/data/property-owners.json'

/** WHO OWNS THE HOMES, FOR HOW LONG, AND WHAT THE BILL HAS DONE. Beside Lunenburg by the
 *  numbers, in The town. TJ, 13 September 2026: "to confirm if people are being taxed out
 *  from purchasing half a century ago". Two sources that measure different things -- the
 *  Census asks when the household ARRIVED; the assessor records the last DEED -- kept in
 *  two tables and never added together. Rule 7b: conclusions, then the tables, then what
 *  is not established. */

type Band = { label: string; households: number; moe: number; share: number; share_moe: number }
type Vintage = { vintage: number; window: string; owners: number; owners_moe: number; bands: Band[]; before_2010: { households: number; moe: number; share: number }; since_1980s: { households: number; moe: number; share: number }; median_moved_in: number }
type DeedBand = { label: string; homes: number; share: number; median_value: number; median_bill: number; nominal_share: number | null; median_sale_price: number | null; arm_length: number }
type Payload = {
  about: string; grain: string
  tenure: { households: number; households_moe: number; owners: number; owners_moe: number; renters: number; renters_moe: number; owner_share: number; window: string }
  census: Record<string, Vintage>
  parcels: { fy: number; rate: number; parcels: number; single_family: number; median_value: number; median_bill: number; bands: DeedBand[]; held: { years: number; homes: number; share: number }[]; nominal: { deeds: number; share: number }; owner_in_town: { homes: number; share: number }; oldest_deed: number; earliest_band_bill_ratio: number }
  bills: { rows: { fy: number; rate: number; value: number; bill: number }[]; first_fy: number; last_fy: number; missing_fy: number[]; value_change: number; rate_change: number; bill_change: number }
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
      title={d && c ? `${pct(c.before_2010.share)} of Lunenburg’s homeowners moved in before 2010 — and their bill is ${pct(d.parcels.earliest_band_bill_ratio)} of a newcomer’s` : 'Who owns the homes'}
      standfirst={d && c ? <>{n0(c.before_2010.households)} of {n0(c.owners)} owner households have been in the house since before 2010, on the Census sample; the assessor’s own file puts the median bill on a home last deeded before 1986 at {usd(d.parcels.bands[d.parcels.bands.length - 1].median_bill)} — a house bought decades ago is taxed on what it is worth now.</> : undefined}
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
      <section data-section="conclusions">
        {/* THE DENOMINATOR FIRST. TJ: "we need the total homes first to understand other
            context." Every share below is a share of one of these three numbers. */}
        <div className="flex flex-wrap gap-x-10 gap-y-5 mt-8">
          <Stat value={n0(d.tenure.households)}>occupied homes in Lunenburg, {d.tenure.window} — {n0(d.tenure.owners)} owned ({pct(d.tenure.owner_share)}), {n0(d.tenure.renters)} rented; a Census sample, ± {n0(d.tenure.households_moe)}</Stat>
          <Stat value={n0(p.single_family)}>single-family homes on the assessor’s {FY(p.fy)} rolls, of {n0(p.parcels)} parcels — a count, no margin</Stat>
        </div>
        <div className="flex flex-wrap gap-x-10 gap-y-5 mt-6 pt-6" style={{ borderTop: '1px solid var(--grid)' }}>
          <Stat value={pct(c23.before_2010.share)} tone="var(--series-cost)">of owner households moved in before 2010 — {n0(c23.before_2010.households)} ± {n0(c23.before_2010.moe)}</Stat>
          <Stat value={usd(p.bands[p.bands.length - 1].median_bill)}>median {FY(p.fy)} bill on a home last deeded before 1986; {usd(p.bands[0].median_bill)} on one deeded since 2021</Stat>
          <Stat value={pct(b.bill_change)}>more on the average home’s bill, {FY(b.first_fy)}–{FY(b.last_fy)}, while its value rose {pct(b.value_change)} and the rate fell {pct(-b.rate_change)}</Stat>
        </div>
        <Grain>{d.grain}</Grain>
        <Conclusions rows={d.conclusions} />
      </section>

      <section data-section="categorical">
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

        <H2>What the average home’s bill has done</H2>
        <div className="overflow-x-auto mt-4">
          <table className="text-sm" style={{ minWidth: 480 }}>
            <thead><tr className="text-[10px] font-bold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>
              <th className="text-left py-1.5 pr-4">year</th><th className="text-right py-1.5 px-2">rate per $1,000</th><th className="text-right py-1.5 px-2">average single-family value</th><th className="text-right py-1.5 pl-2">average bill</th></tr></thead>
            <tbody>{b.rows.map(r => (
              <tr key={r.fy} style={{ borderTop: '1px solid var(--grid)' }}>
                <td className="py-1.5 pr-4 font-semibold tnum">{FY(r.fy)}</td>
                <td className="py-1.5 px-2 text-right tnum">${r.rate.toFixed(2)}</td>
                <td className="py-1.5 px-2 text-right tnum">{usd(r.value)}</td>
                <td className="py-1.5 pl-2 text-right tnum font-semibold">{usd(r.bill)}</td></tr>))}</tbody>
          </table>
        </div>
        <p className="text-xs mt-1 max-w-3xl" style={{ color: 'var(--text-muted)' }}>{b.missing_fy.length ? `${b.missing_fy.map(FY).join(' and ')} are not held — the town’s classification hearings for those years are not in the archive. ` : ''}Proposition 2½ caps how fast the levy grows, not the bill on any one house; as values rise the rate falls, and who pays more depends on whose value rose most. Nearby towns’ bills are not shown, for the reason below.</p>
      </section>

      <section data-section="raw">
        <NotEstablished rows={d.not_established} closes="The Division of Local Services’ Average Single Family Tax Bill report, every town, FY2003 to date — pulled by hand from the DLS Gateway, since it refuses a script." />
        <Provenance sources={d.sources} />
        <MoreReports here={TAB} />
      </section>
    </>
  )
}

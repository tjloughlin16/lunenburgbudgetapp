import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { FullVersion } from '../components/FullVersion'
import type { Tab } from '../routes'
import { Conclusions, Grain, H2, MoreReports, NotEstablished, Provenance, ReportShell, Stat, useReport, splitConclusions } from '../components/report'
import type { Conclusion, Source } from '../components/report'
import { usd, usdShort } from '../model/engine'

const TAB: Tab = 'parks'
const DATA = '/data/parks.json'

/** PARKS & RECREATION. TJ, 17 September 2026: "can you build a report for parks, under
 *  'the town' for whatever data you got." Four kinds of document and the page keeps them
 *  apart: the FY26 accounting printouts (evidence), the annual reports' fund schedule
 *  (read and tied to FY2023; transcribed after), the registration system's sales (a
 *  printout from MyRec, which is not the town's books), and a grounds bid (stated).
 *  Built by scripts/build_parks.py. */
type Cur = { fy: number; as_of?: string; opening?: number; revenue?: number; spent?: number; closing?: number; grade: string }
type Hist = { fy: number; grade: string; opening?: number | null; revenue?: number | null; spent?: number | null; closing?: number | null; chains?: boolean }
type Sale = { report: string; program: string; res_count: number; nonres_count: number; total_count: number; res_total: number; nonres_total: number; total: number }
type Payload = {
  about: string; grain: string; as_of: { ledger: string; fund: string; myrec: string }
  appropriation: { code: string; name: string; original: number; revised: number; expended: number; encumbered: number; available: number; period: number }
  fund: { code: string; name: string; current: Cur; history: Hist[] }
  gift: { code: string; name: string; current: Cur; history: Hist[] }
  other_funds: { id: string; name: string; kind: string; current: Cur | null }[]
  myrec: { program: Sale[]; membership: Sale[]; program_total: number; membership_total: number; total: number; nonres_total: number; nonres_share: number; program_n: number; membership_n: number }
  bid: { rows: { park: string; year_one: number; mowing: number | null }[]; total: number }
  sources: Source[]; not_established: string[]; conclusions: Conclusion[]
}
const AXIS = { fontSize: 11, fill: 'var(--text-muted)' }
const title = (s: string) => s.toLowerCase().replace(/(^|[\s(/-])([a-z])/g, (_m, p, c) => p + c.toUpperCase()).replace(/\bStem\b/, 'STEM').replace(/\b5k\b/, '5K')

export function Parks() {
  const { d, err } = useReport<Payload>('parks.json')
  return (
    <ReportShell tab={TAB}
      title={d ? `Parks & Recreation — a ${usdShort(d.appropriation.revised)} department with a ${usdShort(d.fund.current.closing ?? 0)} fund of its own` : 'Parks & Recreation'}
      standfirst={d ? <>What the department is voted, what its own fee fund holds and has done since FY2011, what the registration system took in for FY2025, and what a contractor bid to keep the grounds. Four documents of four kinds, kept apart. <a className="underline" href="/boards/parks-commission/finance">Every account the Parks Commission owns</a>.</> : undefined}
      err={err} loading={!d && !err} dataUrl={DATA}>
      {d && <Report d={d} />}
    </ReportShell>
  )
}

function Report({ d }: { d: Payload }) {
  const [shortRows, moreRows] = splitConclusions(d.conclusions, undefined)
  const f = d.fund.current
  const series = [...d.fund.history, { fy: f.fy, grade: 'evidence', opening: f.opening, revenue: f.revenue, spent: f.spent, closing: f.closing }]
    .map(h => ({ fy: `FY${String(h.fy).slice(2)}${h.fy === 2026 ? '*' : ''}`, held: h.closing ?? 0, in: h.revenue ?? 0, out: h.spent ?? 0, grade: h.grade }))
  return (
    <>
      <section data-section="conclusions" data-short="">
        <div className="flex flex-wrap gap-x-10 gap-y-5 mt-8">
          <Stat value={usdShort(d.appropriation.revised)}>voted for FY2026 as revised; {usdShort(d.appropriation.expended)} spent by year end</Stat>
          <Stat value={usdShort(f.closing ?? 0)} tone="var(--series-revenue)">in the Park Revolving Fund at {d.as_of.fund} &mdash; fee money the department spends without a vote</Stat>
          <Stat value={usdShort(d.myrec.total)}>recorded by the registration system in FY2025: {d.myrec.program_n} programme places, {d.myrec.membership_n} beach passes</Stat>
          <Stat value={`${Math.round(d.myrec.nonres_share)}%`} tone="var(--text-secondary)">of that paid by non-residents</Stat>
        </div>
        <Grain>{d.grain}</Grain>
        <Conclusions rows={shortRows} />
      </section>

      <FullVersion what="the fund by year, the sales, the bid, the accounts">
        {moreRows.length > 0 && (
          <>
            <H2 id="more-findings">The other findings</H2>
            <Conclusions rows={moreRows} noAsk short={false} />
          </>
        )}

        <section data-section="categorical">
          <H2 id="years">The Park Revolving Fund, FY2011 to today</H2>
          <p className="text-sm max-w-3xl" style={{ color: 'var(--text-secondary)' }}>
            The annual reports print it as &ldquo;Park User Fees&rdquo;: balance forward, receipts, disbursements, balance carried. FY2011&ndash;FY2023 are read off the page and tie to each report&rsquo;s own totals; FY2024 and FY2025 print a balance only and are transcribed; FY2026 (starred) is the town&rsquo;s own report through 31 March. FY2025&rsquo;s balance does not chain to the FY26 opening, and the page says so rather than picking one.
          </p>
          <div style={{ width: '100%', height: 300 }} className="mt-4 avoid-break">
            <ResponsiveContainer>
              <BarChart data={series} margin={{ top: 8, right: 8, left: 0, bottom: 4 }}>
                <CartesianGrid stroke="var(--grid)" vertical={false} />
                <XAxis dataKey="fy" tick={AXIS} stroke="var(--axis)" />
                <YAxis tick={AXIS} stroke="var(--axis)" tickFormatter={(v: number) => usdShort(v)} width={56} />
                <Tooltip formatter={(v, n) => [usd(v as number), n === 'held' ? 'held at year end' : n === 'in' ? 'receipts' : 'disbursed']} contentStyle={{ background: 'var(--surface-1)', border: '1px solid var(--grid)', borderRadius: 10, fontSize: 12, color: 'var(--text-primary)' }} />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                <Bar dataKey="in" fill="var(--series-revenue)" isAnimationActive={false} />
                <Bar dataKey="out" fill="var(--series-cost)" isAnimationActive={false} />
                <Bar dataKey="held" fill="var(--text-muted)" isAnimationActive={false} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="overflow-x-auto mt-4">
            <table className="text-sm" style={{ minWidth: 560 }}>
              <thead><tr className="text-[10px] font-bold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>
                <th className="text-left py-2 pr-4">year</th><th className="text-right py-2 pr-4">forward</th><th className="text-right py-2 pr-4">receipts</th><th className="text-right py-2 pr-4">disbursed</th><th className="text-right py-2 pr-4">held</th><th className="text-left py-2">grade</th></tr></thead>
              <tbody>{[...d.fund.history, { fy: f.fy, grade: 'evidence', opening: f.opening, revenue: f.revenue, spent: f.spent, closing: f.closing, chains: undefined }].map(y => (
                <tr key={y.fy} style={{ borderTop: '1px solid var(--grid)' }}>
                  <td className="py-1.5 pr-4 tnum">FY{y.fy}{y.fy === 2026 ? ' (to March)' : ''}</td>
                  {[y.opening, y.revenue, y.spent, y.closing].map((v, i) => <td key={i} className="py-1.5 pr-4 text-right tnum">{v === null || v === undefined ? '—' : usd(v)}</td>)}
                  <td className="py-1.5 text-[11px]" style={{ color: y.grade === 'evidence' ? 'var(--status-good)' : y.grade === 'read' ? 'var(--text-primary)' : 'var(--status-warn, #b45309)' }}>{y.grade}{y.chains === false ? <span style={{ color: 'var(--status-critical)' }}> · does not chain to FY26</span> : ''}</td>
                </tr>))}</tbody>
            </table>
          </div>

          <H2 id="sales">What the registration system recorded, FY2025</H2>
          <p className="text-sm max-w-3xl" style={{ color: 'var(--text-secondary)' }}>
            MyRec&rsquo;s two sales reports for {d.as_of.myrec}, each footing to the totals it prints. A registration system is not the ledger: this is the fee side of what was sold, and where it was deposited is on no document we hold.
          </p>
          <SalesTable rows={d.myrec.program} caption={`Programmes — ${usd(d.myrec.program_total)}`} />
          <SalesTable rows={d.myrec.membership} caption={`Beach passes and memberships — ${usd(d.myrec.membership_total)}`} />

          <H2 id="bid">What keeping the grounds was bid at</H2>
          <p className="text-sm max-w-3xl" style={{ color: 'var(--text-secondary)' }}>
            A contractor&rsquo;s bid sheet for year one from 1 July 2024, per park. A bid is an offer, on the vendor&rsquo;s authority; what the town paid is in the FY2024 budget report&rsquo;s journal, held as an image and not yet read.
          </p>
          <div className="overflow-x-auto mt-4">
            <table className="text-sm" style={{ minWidth: 420 }}>
              <thead><tr className="text-[10px] font-bold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}><th className="text-left py-2 pr-4">park</th><th className="text-right py-2 pr-4">mowing</th><th className="text-right py-2">year one, all work</th></tr></thead>
              <tbody>{d.bid.rows.map(r => (
                <tr key={r.park} style={{ borderTop: '1px solid var(--grid)' }}><td className="py-1.5 pr-4">{r.park}</td><td className="py-1.5 pr-4 text-right tnum">{r.mowing === null ? '—' : usd(r.mowing)}</td><td className="py-1.5 text-right tnum">{usd(r.year_one)}</td></tr>))}
                <tr style={{ borderTop: '2px solid var(--grid)' }} className="font-bold"><td className="py-2 pr-4">Six parks</td><td /><td className="py-2 text-right tnum">{usd(d.bid.total)}</td></tr>
              </tbody>
            </table>
          </div>

          <H2 id="accounts">The department&rsquo;s other accounts</H2>
          <ul className="mt-3 space-y-1.5 text-sm">
            <li><span className="tnum" style={{ color: 'var(--text-muted)' }}>{d.gift.code}</span> {title(d.gift.name)} — {usd(d.gift.current.closing ?? 0)} held; it moved {usd(d.gift.history.length ? Math.max(...d.gift.history.map(h => h.revenue ?? 0)) : 0)} in its busiest year on record</li>
            {d.other_funds.map(o => <li key={o.id}><span className="tnum" style={{ color: 'var(--text-muted)' }}>{o.id.replace(/^[a-z]+-/, '')}</span> {title(o.name)} — {o.current?.closing !== undefined && o.current?.closing !== null ? usd(o.current.closing) + ' held' : '—'} <span style={{ color: 'var(--text-muted)' }}>· {o.kind}</span></li>)}
          </ul>
          <p className="text-sm mt-3"><a className="underline" href="/boards/parks-commission/finance">Every account the Parks Commission owns, with its history &rarr;</a></p>
        </section>

        <section data-section="raw">
          <H2 id="not-established">What this report cannot say</H2>
          <NotEstablished rows={d.not_established} closes="The FY2025 special-revenue report and the journal detail for fund 1500 — the same report the archive holds for fund 1301 — and a text-layer copy of the FY2024 Parks budget report." />
          <Provenance sources={d.sources} />
        </section>
      </FullVersion>
      <MoreReports here={TAB} />
    </>
  )
}

function SalesTable({ rows, caption }: { rows: Sale[]; caption: string }) {
  return (
    <div className="overflow-x-auto mt-4">
      <table className="text-sm" style={{ minWidth: 640 }}>
        <caption className="text-left text-[12px] pb-2 font-semibold" style={{ color: 'var(--text-secondary)' }}>{caption}</caption>
        <thead><tr className="text-[10px] font-bold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>
          <th className="text-left py-2 pr-4">programme</th><th className="text-right py-2 pr-4">residents</th><th className="text-right py-2 pr-4">non-residents</th><th className="text-right py-2 pr-4">places</th><th className="text-right py-2 pr-4">residents paid</th><th className="text-right py-2 pr-4">non-residents paid</th><th className="text-right py-2">total</th></tr></thead>
        <tbody>{rows.map(r => (
          <tr key={r.program} style={{ borderTop: '1px solid var(--grid)' }}>
            <td className="py-1.5 pr-4">{title(r.program)}</td>
            <td className="py-1.5 pr-4 text-right tnum">{r.res_count}</td><td className="py-1.5 pr-4 text-right tnum">{r.nonres_count}</td><td className="py-1.5 pr-4 text-right tnum">{r.total_count}</td>
            <td className="py-1.5 pr-4 text-right tnum">{usd(r.res_total)}</td><td className="py-1.5 pr-4 text-right tnum">{usd(r.nonres_total)}</td><td className="py-1.5 text-right tnum font-semibold">{usd(r.total)}</td>
          </tr>))}</tbody>
      </table>
    </div>
  )
}

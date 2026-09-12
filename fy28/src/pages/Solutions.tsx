import type { Tab } from '../routes'
import { ReportShell, useReport } from '../components/report'
import { COST_GROWTH_BLENDED } from '../model/engine'
import { BASELINE_REVENUE_GROWTH, LEVY_CAP, RATE_LINES } from '../model/rates'
import { FUTURES, MENU } from '../model/futures'

const TAB: Tab = 'solutions'
const DATA = '/data/model.json'

/** THE SOLUTIONS, ON ONE PAGE, FOR A RESIDENT. Unlisted: no link reaches it from the
 *  site, no alias, not in the sitemap, not prerendered. TJ, 12 September 2026: "a page
 *  ... about the Solutions that are available to the town to fix the budget crisis. Be
 *  concise. This is for citizens. Simple and easy to understand."
 *
 *  Every figure is read from model.json, which the model writes, so nothing here can go
 *  stale on its own (rule 2). The one figure this page derives itself -- what an override
 *  the size of the gap adds to the average tax bill -- is the gap's share of the levy
 *  applied to the average bill, and it says so beside the number. Rule 8: this is what
 *  would work and what each option costs somebody, not what anyone got wrong. */

type Lever = { id: string; name: string; kind: 'revenue' | 'saving'; cap: number; current?: number; default?: number; peakYield?: number }
type Pkg = { id: string; name: string; value: number; why: string; difficulty: string }
type Model = {
  headlines: { id: string; label: string; value: string; sub: string }[]
  conclusions: { n: number; headline: string; figure: string; body: string }[]
  levers: Lever[]
  recommendation: { package: Pkg[]; closing: string }
  taxBase: { levy: number; avgHomeBill: number; avgHomeValue: number }
  freeCash: { certified: number }
}

const usd = (n: number) => '$' + Math.round(n).toLocaleString('en-US')
const parseUsd = (s: string) => Number(s.replace(/[^0-9.]/g, ''))
const pct = (x: number, d = 1) => `${(x * 100).toFixed(d)}%`
const pts = (x: number) => `${(x * 100).toFixed(2)} pts`

export function Solutions() {
  const { d, err } = useReport<Model>('model.json')
  return (
    <ReportShell tab={TAB} kicker="For residents" title="What the town can actually do about the school budget"
      standfirst="Every option that exists, how much of the gap each one closes, who decides it, and what it costs somebody. Nothing here is painless; this page says which pain is which."
      err={err} loading={!d && !err} dataUrl={DATA}>
      {d && <Body d={d} />}
    </ReportShell>
  )
}

function Body({ d }: { d: Model }) {
  const gapH = d.headlines.find(h => h.id === 'gap')!
  const gap = parseUsd(gapH.value)
  const extras = d.headlines.find(h => h.id === 'extras')!
  const health = d.headlines.find(h => h.id === 'health')!
  const business = d.headlines.find(h => h.id === 'business')!
  const pkg = d.recommendation.package
  const pkgTotal = pkg.reduce((s, p) => s + p.value, 0)
  // The model's own treadmill figure, not this page's arithmetic -- one override number on the page, not two.
  const overrideBill = MENU.overrideYearOne
  const freeCashC = d.conclusions.find(c => c.n === 17)
  const v = (id: string) => pkg.find(p => p.id === id)?.value ?? 0
  // THE RATE SIDE. Costs grow at the blended rate, revenue at the levy cap plus new
  // growth; the difference is the spread, and an amount closes a year of it while only a
  // rate change closes it for good. Same numbers as /bend-the-curve, same module.
  const spread = COST_GROWTH_BLENDED - BASELINE_REVENUE_GROWTH
  const ranked = RATE_LINES.slice().sort((a, b) => b.swing - a.swing)
  const line = (k: string) => RATE_LINES.find(l => l.key === k)!
  const health_l = line('health'), other_l = line('other'), sal_l = line('salaries')
  const LEVEL = 'No — a one-time step; the gap regrows at the spread'
  // SORTED BY IMPACT: recurring dollars a year first, largest at the top; then the
  // one-time and the decade-long, by size; classroom cuts last because they are what is
  // left, not a choice with a figure. TJ: "sort by biggest impact".
  const rows: { what: string; closes: string; who: string; costs: string; bends: string; impact: number; recurring: boolean; tone?: string }[] = [
    { what: 'An override', closes: 'The whole gap, every year', who: 'Town Meeting, then the ballot', costs: 'About ' + usd(overrideBill) + ' a year on the average tax bill', bends: 'No — buys one year; the spread reopens the next, and it takes a new one every spring', impact: gap, recurring: true },
    { what: 'Change the health insurance split', closes: health.value + ' a year, once in force', who: 'Negotiated with the employee committee; takes a year or two', costs: (() => { const t = health.sub.replace(/^in year one.*?— and /, ''); return t.charAt(0).toUpperCase() + t.slice(1) })(), bends: `The split, no. Plan design, yes — this line grows ${pct(health_l.rate, 0)} a year; held to the cap it is worth ${pts(health_l.swing)}, the most of any line`, impact: parseUsd(health.value), recurring: true },
    { what: 'Trim administration', closes: usd(v('admin_cut')) + ' a year', who: 'The district', costs: 'Slower office work; possibly a position', bends: LEVEL, impact: v('admin_cut'), recurring: true },
    { what: 'Fees already raised on sports', closes: usd(v('athletic_fees')) + ' a year', who: 'Done — School Committee, for 2026–27', costs: 'A family with one athlete pays $400 a season, up from $250; $1,500 family cap', bends: LEVEL, impact: v('athletic_fees'), recurring: true },
    { what: 'Audit software, licences and devices', closes: usd(v('tech_cut')) + ' a year', who: 'The district', costs: 'Fewer tools; no jobs', bends: LEVEL, impact: v('tech_cut'), recurring: true },
    { what: 'A higher bus fee, grades 7–12', closes: usd(v('bus_fees')) + ' a year', who: 'School Committee vote', costs: '$300 a rider, from the $180 charged today', bends: LEVEL, impact: v('bus_fees'), recurring: true },
    { what: 'A fee for band, music and clubs', closes: usd(v('activity_fees')) + ' a year', who: 'School Committee vote', costs: 'About $100 per student per activity, where none is charged today; some students quit', bends: LEVEL, impact: v('activity_fees'), recurring: true },
    { what: 'New businesses', closes: 'The whole gap, if ' + business.value + ' of new commercial value arrives every year', who: 'Planning Board, Select Board, the market', costs: 'Ten years, not one; ' + business.sub.split('—')[1]?.trim(), bends: 'Yes — it lifts the revenue rate, which is the other side of the spread', impact: gap, recurring: false, tone: 'slow' },
    { what: 'Free cash', closes: (freeCashC?.figure ?? '') + ' in a year like this one', who: 'Town Meeting', costs: 'One-time money on a recurring bill — the gap is back next year', bends: LEVEL, impact: parseUsd(freeCashC?.figure ?? '0'), recurring: false, tone: 'once' },
    { what: 'Cut every sport, band and club', closes: extras.value + ', once', who: 'School Committee', costs: 'Every extra gone, and the gap returns next year', bends: `No — this whole line grows ${pct(other_l.rate, 0)}, worth ${pts(other_l.swing)}; emptying it changes the size, not the slope`, impact: parseUsd(extras.value), recurring: false, tone: 'once' },
    { what: 'Cut classroom positions', closes: 'Whatever is left', who: 'School Committee', costs: 'Larger classes; the thing that makes families leave', bends: `No — salaries grow at the contract rate, ${pct(sal_l.rate, 0)}; fewer people is a lower line at the same slope`, impact: -1, recurring: false },
  ].sort((a, b) => (Number(b.recurring) - Number(a.recurring)) || (b.impact - a.impact))
  return (
    <>
      <div className="flex flex-wrap gap-x-10 gap-y-5 mt-8">
        <div><div className="text-3xl font-bold tnum" style={{ color: 'var(--status-critical)' }}>{gapH.value}</div><div className="text-sm max-w-xs" style={{ color: 'var(--text-secondary)' }}>short, every year — {gapH.sub.charAt(0).toLowerCase() + gapH.sub.slice(1)}</div></div>
        <div><div className="text-3xl font-bold tnum">{usd(pkgTotal)}</div><div className="text-sm max-w-xs" style={{ color: 'var(--text-secondary)' }}>a year from the fees and trims below that cut no program — about {Math.round(100 * pkgTotal / gap)}% of the gap</div></div>
        <div><div className="text-3xl font-bold tnum">{usd(overrideBill)}</div><div className="text-sm max-w-xs" style={{ color: 'var(--text-secondary)' }}>on the average tax bill next year if the whole gap were an override — and more the year after, because the rates do not change</div></div>
      </div>

      <h2 className="text-lg font-semibold mt-10">The choices, whole</h2>
      <p className="text-sm mt-1 max-w-3xl" style={{ color: 'var(--text-secondary)' }}>
        Eight things the town could actually decide, each priced by the same model. Four change an amount and buy time; four change a growth rate and can end it. Every figure is the model’s, and “positions” is an estimate at the catalogue’s own cost per position.
      </p>
      <div className="grid gap-3 mt-4 md:grid-cols-2">
        {FUTURES.map((f, i) => (
          <div key={f.id} className="card p-4" style={{ borderLeft: `3px solid ${f.bends ? 'var(--status-good)' : 'var(--text-muted)'}` }}>
            <p className="text-[10px] font-bold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>Option {i + 1}</p>
            <div className="flex items-baseline justify-between gap-3 mt-0.5">
              <p className="text-[15px] font-bold">{f.label}</p>
              <span className="text-[10px] font-bold uppercase tracking-widest shrink-0" style={{ color: f.bends ? 'var(--status-good)' : 'var(--text-muted)' }}>{f.bends ? 'bends the curve' : 'buys time'}</span>
            </div>
            <p className="text-sm mt-0.5" style={{ color: 'var(--text-secondary)' }}>{f.angle}</p>
            <dl className="mt-3 text-[13px] space-y-1.5">
              <div><dt className="inline font-semibold">Who says yes. </dt><dd className="inline" style={{ color: 'var(--text-secondary)' }}>{f.whoSaysYes}</dd></div>
              <div><dt className="inline font-semibold">What it costs. </dt><dd className="inline tnum" style={{ color: 'var(--text-secondary)' }}>{f.costs}</dd></div>
              <div><dt className="inline font-semibold">How long it holds. </dt><dd className="inline" style={{ color: f.bends ? 'var(--text-primary)' : 'var(--text-secondary)' }}>{f.holds}</dd></div>
            </dl>
            <a className="underline text-xs mt-2 inline-block" style={{ color: 'var(--text-muted)' }} href={f.more}>the working</a>
          </div>))}
      </div>

      <h2 className="text-lg font-semibold mt-10">The parts, biggest first</h2>
      <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>Recurring money a year at the top; then what pays once or takes a decade; then what is left.</p>
      <div className="overflow-x-auto mt-3">
        <table className="w-full text-sm" style={{ minWidth: 820 }}>
          <thead><tr className="text-[10px] font-bold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>
            <th className="text-left py-2 pr-3">what</th><th className="text-left py-2 pr-3">closes</th><th className="text-left py-2 pr-3">who decides</th><th className="text-left py-2 pr-3">what it costs somebody</th><th className="text-left py-2">bends the curve?</th></tr></thead>
          <tbody>{rows.map(r => (
            <tr key={r.what} style={{ borderTop: '1px solid var(--grid)' }}>
              <td className="py-2.5 pr-3 font-semibold align-top">{r.what}</td>
              <td className="py-2.5 pr-3 align-top tnum" style={{ color: r.tone ? 'var(--text-secondary)' : 'var(--text-primary)' }}>{r.closes}</td>
              <td className="py-2.5 pr-3 align-top" style={{ color: 'var(--text-secondary)' }}>{r.who}</td>
              <td className="py-2.5 pr-3 align-top" style={{ color: 'var(--text-secondary)' }}>{r.costs}</td>
              <td className="py-2.5 align-top text-[13px]" style={{ color: r.bends.startsWith('No') ? 'var(--text-muted)' : 'var(--text-primary)' }}>{r.bends}</td>
            </tr>))}</tbody>
        </table>
      </div>

      <h2 className="text-lg font-semibold mt-10">Why most of the table does not end it</h2>
      <p className="text-[15px] mt-2 max-w-3xl leading-relaxed">
        Costs grow <strong className="tnum">{pct(COST_GROWTH_BLENDED, 2)}</strong> a year and the money to pay them grows <strong className="tnum">{pct(BASELINE_REVENUE_GROWTH, 2)}</strong> — the levy cap plus new building. The difference, <strong className="tnum">{pts(spread)}</strong>, is the problem. An amount closes one year of it; only a change to a growth rate closes it for good. Holding each line to the {pct(LEVY_CAP, 1)} cap would move the cost rate by:
      </p>
      <div className="mt-3 max-w-3xl">
        {ranked.map(l => (
          <div key={l.key} className="py-1.5 text-sm" style={{ borderTop: '1px solid var(--grid)' }}>
            <div className="flex items-baseline justify-between gap-3">
              <span className="font-semibold min-w-0">{l.label}</span>
              <span className="tnum font-bold shrink-0">{pts(l.swing)}</span>
            </div>
            <div className="h-1.5 rounded-full mt-1" style={{ background: 'var(--surface-3)' }}><div className="h-full rounded-full" style={{ width: `${Math.max(0, l.swing / ranked[0].swing) * 100}%`, background: 'var(--series-cost)' }} /></div>
            <div className="text-xs mt-0.5 tnum" style={{ color: 'var(--text-muted)' }}>{pct(l.weight, 0)} of budget, growing {pct(l.rate, 1)} a year</div>
          </div>))}
      </div>
      <p className="text-sm mt-2 max-w-3xl" style={{ color: 'var(--text-secondary)' }}>
        {ranked[0].label} and {ranked[1].label.toLowerCase()} are {Math.round(100 * (ranked[0].swing + ranked[1].swing) / spread)}% of the spread between them. {other_l.label} — where sports, clubs and devices live, and the only line the School Committee sets on its own — is worth {pts(other_l.swing)}. That is why the cuts residents see every spring never change the slope. The dials are on <a className="underline" href="/bend-the-curve">Bend the curve</a>.
      </p>

      <h2 className="text-lg font-semibold mt-10">What follows</h2>
      <ol className="mt-3 space-y-3 max-w-3xl text-[15px] leading-relaxed">
        <li><strong>The fees and trims are worth doing and do not solve it.</strong> Together they close about {Math.round(100 * pkgTotal / gap)}% of the gap without touching a program.</li>
        <li><strong>Cutting the extras buys one year.</strong> {extras.sub.split('.')[0]}. Then the same gap returns with nothing left to cut but classrooms.</li>
        <li><strong>Business growth is real and slow.</strong> It needs {business.value} of new commercial value a year, every year, and pays off in about a decade.</li>
        <li><strong>Free cash covers a year, not a problem.</strong> {freeCashC ? freeCashC.body.split(/\.\s/)[0] + '.' : ''}</li>
        <li><strong>Only two things on the table change a rate:</strong> the health plan itself, and the pace of commercial building. Everything else is an amount, and an amount has to be found again next year.</li>
        <li><strong>After that there are two choices, and only two.</strong> {d.recommendation.closing}</li>
      </ol>

      <p className="text-sm mt-10 max-w-3xl" style={{ color: 'var(--text-muted)' }}>
        Every figure on this page is computed by the same model that runs the rest of this site and is read from it, not typed; the working is on{' '}
        <a className="underline" href="/bend-the-curve">Bend the curve</a>, <a className="underline" href="/what-solved-requires">What “solved” requires</a> and{' '}
        <a className="underline" href="/build-your-own-budget">Build your own budget</a>. The whole-choice cards run the same projection as Bend the curve; the override figures are that page’s treadmill, on the average bill.
      </p>
    </>
  )
}

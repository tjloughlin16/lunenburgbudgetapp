import type { Tab } from '../routes'
import { ReportShell, useReport } from '../components/report'

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
  const overrideBill = d.taxBase.avgHomeBill * (gap / d.taxBase.levy)
  const freeCashC = d.conclusions.find(c => c.n === 17)
  const v = (id: string) => pkg.find(p => p.id === id)?.value ?? 0
  // SORTED BY IMPACT: recurring dollars a year first, largest at the top; then the
  // one-time and the decade-long, by size; classroom cuts last because they are what is
  // left, not a choice with a figure. TJ: "sort by biggest impact".
  const rows: { what: string; closes: string; who: string; costs: string; impact: number; recurring: boolean; tone?: string }[] = [
    { what: 'An override', closes: 'The whole gap, every year', who: 'Town Meeting, then the ballot', costs: 'About ' + usd(overrideBill) + ' a year on the average tax bill', impact: gap, recurring: true },
    { what: 'Change the health insurance split', closes: health.value + ' a year, once in force', who: 'Negotiated with the employee committee; takes a year or two', costs: (() => { const t = health.sub.replace(/^in year one.*?— and /, ''); return t.charAt(0).toUpperCase() + t.slice(1) })(), impact: parseUsd(health.value), recurring: true },
    { what: 'Trim administration', closes: usd(v('admin_cut')) + ' a year', who: 'The district', costs: 'Slower office work; possibly a position', impact: v('admin_cut'), recurring: true },
    { what: 'Fees already raised on sports', closes: usd(v('athletic_fees')) + ' a year', who: 'Done — School Committee, for 2026–27', costs: 'A family with one athlete pays $400 a season, up from $250; $1,500 family cap', impact: v('athletic_fees'), recurring: true },
    { what: 'Audit software, licences and devices', closes: usd(v('tech_cut')) + ' a year', who: 'The district', costs: 'Fewer tools; no jobs', impact: v('tech_cut'), recurring: true },
    { what: 'A higher bus fee, grades 7–12', closes: usd(v('bus_fees')) + ' a year', who: 'School Committee vote', costs: '$300 a rider, from the $180 charged today', impact: v('bus_fees'), recurring: true },
    { what: 'A fee for band, music and clubs', closes: usd(v('activity_fees')) + ' a year', who: 'School Committee vote', costs: 'About $100 per student per activity, where none is charged today; some students quit', impact: v('activity_fees'), recurring: true },
    { what: 'New businesses', closes: 'The whole gap, if ' + business.value + ' of new commercial value arrives every year', who: 'Planning Board, Select Board, the market', costs: 'Ten years, not one; ' + business.sub.split('—')[1]?.trim(), impact: gap, recurring: false, tone: 'slow' },
    { what: 'Free cash', closes: (freeCashC?.figure ?? '') + ' in a year like this one', who: 'Town Meeting', costs: 'One-time money on a recurring bill — the gap is back next year', impact: parseUsd(freeCashC?.figure ?? '0'), recurring: false, tone: 'once' },
    { what: 'Cut every sport, band and club', closes: extras.value + ', once', who: 'School Committee', costs: 'Every extra gone, and the gap returns next year', impact: parseUsd(extras.value), recurring: false, tone: 'once' },
    { what: 'Cut classroom positions', closes: 'Whatever is left', who: 'School Committee', costs: 'Larger classes; the thing that makes families leave', impact: -1, recurring: false },
  ].sort((a, b) => (Number(b.recurring) - Number(a.recurring)) || (b.impact - a.impact))
  return (
    <>
      <div className="flex flex-wrap gap-x-10 gap-y-5 mt-8">
        <div><div className="text-3xl font-bold tnum" style={{ color: 'var(--status-critical)' }}>{gapH.value}</div><div className="text-sm max-w-xs" style={{ color: 'var(--text-secondary)' }}>short, every year — {gapH.sub.charAt(0).toLowerCase() + gapH.sub.slice(1)}</div></div>
        <div><div className="text-3xl font-bold tnum">{usd(pkgTotal)}</div><div className="text-sm max-w-xs" style={{ color: 'var(--text-secondary)' }}>a year from the fees and trims below that cut no program — about {Math.round(100 * pkgTotal / gap)}% of the gap</div></div>
        <div><div className="text-3xl font-bold tnum">{usd(overrideBill)}</div><div className="text-sm max-w-xs" style={{ color: 'var(--text-secondary)' }}>a year on the average tax bill if the rest were an override — our arithmetic: the gap’s share of the levy, applied to the {usd(d.taxBase.avgHomeBill)} average bill</div></div>
      </div>

      <h2 className="text-lg font-semibold mt-10">Everything on the table, biggest first</h2>
      <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>Recurring money a year at the top; then what pays once or takes a decade; then what is left.</p>
      <div className="overflow-x-auto mt-3">
        <table className="w-full text-sm" style={{ minWidth: 640 }}>
          <thead><tr className="text-[10px] font-bold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>
            <th className="text-left py-2 pr-3">what</th><th className="text-left py-2 pr-3">closes</th><th className="text-left py-2 pr-3">who decides</th><th className="text-left py-2">what it costs somebody</th></tr></thead>
          <tbody>{rows.map(r => (
            <tr key={r.what} style={{ borderTop: '1px solid var(--grid)' }}>
              <td className="py-2.5 pr-3 font-semibold align-top">{r.what}</td>
              <td className="py-2.5 pr-3 align-top tnum" style={{ color: r.tone ? 'var(--text-secondary)' : 'var(--text-primary)' }}>{r.closes}</td>
              <td className="py-2.5 pr-3 align-top" style={{ color: 'var(--text-secondary)' }}>{r.who}</td>
              <td className="py-2.5 align-top" style={{ color: 'var(--text-secondary)' }}>{r.costs}</td>
            </tr>))}</tbody>
        </table>
      </div>

      <h2 className="text-lg font-semibold mt-10">What follows</h2>
      <ol className="mt-3 space-y-3 max-w-3xl text-[15px] leading-relaxed">
        <li><strong>The fees and trims are worth doing and do not solve it.</strong> Together they close about {Math.round(100 * pkgTotal / gap)}% of the gap without touching a program.</li>
        <li><strong>Cutting the extras buys one year.</strong> {extras.sub.split('.')[0]}. Then the same gap returns with nothing left to cut but classrooms.</li>
        <li><strong>Business growth is real and slow.</strong> It needs {business.value} of new commercial value a year, every year, and pays off in about a decade.</li>
        <li><strong>Free cash covers a year, not a problem.</strong> {freeCashC ? freeCashC.body.split(/\.\s/)[0] + '.' : ''}</li>
        <li><strong>After that there are two choices, and only two.</strong> {d.recommendation.closing}</li>
      </ol>

      <p className="text-sm mt-10 max-w-3xl" style={{ color: 'var(--text-muted)' }}>
        Every figure on this page is computed by the same model that runs the rest of this site and is read from it, not typed; the working is on{' '}
        <a className="underline" href="/bend-the-curve">Bend the curve</a>, <a className="underline" href="/what-solved-requires">What “solved” requires</a> and{' '}
        <a className="underline" href="/build-your-own-budget">Build your own budget</a>. The override figure is this page’s own arithmetic and is labelled as such.
      </p>
    </>
  )
}

import type { Assumptions as A } from '../model/engine'
import { MODEL, usd } from '../model/engine'

const PCT: { key: keyof A; label: string; note: string; max: number
              more?: string }[] = [
  { key: 'salaries', label: 'Salary growth', note: 'Contractual steps, lanes and cost-of-living', max: 0.08 },
  { key: 'health', label: 'Health insurance', note: 'District assumed 9% building FY27', max: 0.18 },
  { key: 'transport', label: 'Transportation', note: 'District assumed 10% building FY27', max: 0.15 },
  { key: 'sped', label: 'Special education, in district', note: 'No published rate exists; measured across eight to eleven of the district’s own budgets', max: 0.15, more: '/bend-the-curve#sped' },
  { key: 'sped_tuition', label: 'Out-of-district tuition', note: 'Eleven budgets show no trend at all, so the model holds it flat', max: 0.20, more: '/bend-the-curve#sped' },
  { key: 'utilities', label: 'Utilities', note: 'Electricity rose 19% in FY27', max: 0.15 },
  { key: 'other', label: 'All other expenses', note: 'Supplies, contracts, materials', max: 0.08 },
  { key: 'state_aid_growth', label: 'State aid growth', note: 'Chapter 70 and other cherry-sheet aid', max: 0.06 },
]

export function AssumptionsPanel({ a, setA, leverTotal }: {
  a: A; setA: (a: A) => void; leverTotal: number
}) {
  const set = (k: keyof A, v: number) => setA({ ...a, [k]: v })
  return (
    <div className="grid gap-6 md:grid-cols-2">
      <div className="card p-5">
        <h3 className="text-sm font-bold mb-4">Cost and revenue growth</h3>
        <ul className="space-y-4">
          {PCT.map(({ key, label, note, max, more }) => (
            <li key={key}>
              <div className="flex items-baseline justify-between mb-1">
                <label htmlFor={`a-${key}`} className="text-[13px] font-medium">{label}</label>
                <span className="text-sm font-bold tnum">
                  {((a[key] as number) * 100).toFixed(1)}%
                </span>
              </div>
              <input id={`a-${key}`} type="range" min={0} max={max} step={0.0025}
                value={a[key] as number}
                onChange={e => set(key, Number(e.target.value))}
                className="w-full" />
              <p className="text-[11px]" style={{ color: 'var(--text-muted)' }}>
                {note}
                {more && <>{' '}
                  <a href={more} className="font-semibold"
                    style={{ color: 'var(--series-cost)' }}>how we got it &rarr;</a>
                </>}
              </p>
            </li>
          ))}
        </ul>
      </div>

      <div className="card p-5">
        <h3 className="text-sm font-bold mb-4">Levers the town could pull</h3>
        <ul className="space-y-5">
          <li>
            <div className="flex items-baseline justify-between mb-1">
              <label htmlFor="a-override" className="text-[13px] font-medium">
                An FY28 override, if one passed
              </label>
              <span className="text-sm font-bold tnum">{usd(a.override_amount)}</span>
            </div>
            <input id="a-override" type="range" min={0} max={2_500_000} step={50_000}
              value={a.override_amount}
              onChange={e => set('override_amount', Number(e.target.value))}
              className="w-full" />
            <p className="text-[11px]" style={{ color: 'var(--text-muted)' }}>
              For scale: the $2.4M town-wide override rejected in May 2026 would have sent
              $1.6M to the schools and added about $507 a year to the average tax bill.
            </p>
          </li>
          <li>
            <div className="flex items-baseline justify-between mb-1">
              <span className="text-[13px] font-medium">
                Fees, savings and efficiencies
              </span>
              <span className="text-sm font-bold tnum"
                style={{ color: leverTotal > 0 ? 'var(--status-good)' : 'var(--text-muted)' }}>
                {usd(leverTotal)}
              </span>
            </div>
            <p className="text-[11px]" style={{ color: 'var(--text-muted)' }}>
              Set on the <a href="#levers" className="underline">Close the gap</a> tab, not
              here &mdash; there used to be a second fee slider on this panel and it was
              only ever a way to disagree with yourself. Whatever you set there feeds
              straight into this projection and shrinks the hole the cut line has to close.
              Lunenburg already charges $400 for a first child ($300 second, $225 third,
              $1,500 family cap), raising an estimated{' '}
              {usd(MODEL.currentFees.estimatedAthleticRevenue)}; only an increase above
              that is new money.
            </p>
          </li>
          <li>
            <div className="flex items-baseline justify-between mb-1">
              <label htmlFor="a-new-growth" className="text-[13px] font-medium">
                New growth added to the levy each year
              </label>
              <span className="text-sm font-bold tnum">{usd(a.new_growth)}</span>
            </div>
            <input id="a-new-growth" type="range" min={0} max={1_200_000} step={25_000}
              value={a.new_growth}
              onChange={e => set('new_growth', Number(e.target.value))}
              className="w-full" />
            <p className="text-[11px]" style={{ color: 'var(--text-muted)' }}>
              New construction and development. The town budgeted $400,000 for FY27.
              This is the only way the levy grows faster than 2.5% without an override.
            </p>
          </li>
        </ul>
        <button
          onClick={() => setA({ ...MODEL.assumptions })}
          className="mt-5 px-3 py-1.5 rounded-lg text-xs font-semibold border"
          style={{ borderColor: 'var(--grid)', color: 'var(--text-secondary)' }}>
          Reset to published assumptions
        </button>
      </div>
    </div>
  )
}

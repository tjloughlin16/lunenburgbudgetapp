import { useState } from 'react'
import { MODEL, usd } from '../model/engine'

const T = MODEL.taxBase

/** Three futures for one homeowner: nothing, growth, or an override. */
export function TaxpayerView({ newValue, gap }: { newValue: number; gap: number }) {
  const [home, setHome] = useState(T.avgHomeValue)

  const baseLevy = T.levy * (1 + T.levyGrowth)
  const growthRevenue = (newValue * T.rate) / 1000

  const rateNothing = (baseLevy / T.totalValue) * 1000
  const rateGrowth = ((baseLevy + growthRevenue) / (T.totalValue + newValue)) * 1000
  const rateOverride = ((baseLevy + gap) / T.totalValue) * 1000

  const bill = (r: number) => (home * r) / 1000
  const today = (home * T.rate) / 1000

  const SCENARIOS = [
    { key: 'nothing', label: 'Nothing changes',
      sub: 'No new growth, no override', rate: rateNothing,
      schools: 0, tone: 'var(--text-muted)' },
    { key: 'growth', label: 'Business growth',
      sub: `${usd(newValue)} of new commercial value`, rate: rateGrowth,
      schools: growthRevenue, tone: 'var(--series-cost)' },
    { key: 'override', label: 'An override instead',
      sub: `Raising the full ${usd(gap)} from existing taxpayers`, rate: rateOverride,
      schools: gap, tone: 'var(--status-critical)' },
  ]
  const maxBill = Math.max(...SCENARIOS.map(s => bill(s.rate)))

  return (
    <div className="card p-5">
      <div className="flex flex-wrap items-end justify-between gap-4 mb-5">
        <div>
          <h3 className="text-sm font-bold mb-1">What it means for your tax bill</h3>
          <p className="text-[12px]" style={{ color: 'var(--text-secondary)' }}>
            Your bill today at the FY26 rate of ${T.rate.toFixed(2)}:{' '}
            <strong>{usd(today)}</strong>
          </p>
        </div>
        <div>
          <label htmlFor="homeval" className="text-[11px] block mb-1"
            style={{ color: 'var(--text-muted)' }}>Your home&rsquo;s assessed value</label>
          <input id="homeval" type="number" min={0} step={25_000} value={home}
            onChange={e => setHome(Math.max(0, Number(e.target.value)))}
            className="w-40 px-2 py-1.5 rounded-lg border text-sm tnum"
            style={{ borderColor: 'var(--grid)', background: 'var(--surface-2)',
                     color: 'var(--text-primary)' }} />
        </div>
      </div>

      <ul className="space-y-4">
        {SCENARIOS.map(s => {
          const b = bill(s.rate)
          const delta = b - today
          return (
            <li key={s.key}>
              <div className="flex flex-wrap items-baseline justify-between gap-2 mb-1">
                <span>
                  <span className="text-[13px] font-bold">{s.label}</span>
                  <span className="text-[11px] ml-2" style={{ color: 'var(--text-muted)' }}>
                    {s.sub}
                  </span>
                </span>
                <span className="text-sm shrink-0">
                  <span className="font-bold tnum">{usd(b)}</span>
                  <span className="tnum ml-2" style={{ color: 'var(--text-secondary)' }}>
                    {delta >= 0 ? '+' : ''}{usd(delta)} vs today
                  </span>
                </span>
              </div>
              <div className="h-3 rounded-full overflow-hidden"
                style={{ background: 'var(--surface-3)' }}>
                <div className="h-full rounded-full"
                  style={{ width: `${(b / maxBill) * 100}%`, background: s.tone }} />
              </div>
              <p className="text-[11px] mt-1" style={{ color: 'var(--text-muted)' }}>
                Rate ${s.rate.toFixed(2)} · schools get{' '}
                {s.schools > 0 ? `${usd(s.schools)} more` : 'nothing more'}
                {s.schools > 0 && ` — ${((s.schools / gap) * 100).toFixed(0)}% of the gap`}
              </p>
            </li>
          )
        })}
      </ul>

      <div className="mt-5 pt-4 border-t" style={{ borderColor: 'var(--grid)' }}>
        <p className="text-[15px] font-bold leading-snug mb-2">
          Business growth does not lower your tax bill. It stops it going up.
        </p>
        <p className="text-[13px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
          {usd(newValue)} of new commercial value changes your bill by{' '}
          <strong>{usd(bill(rateGrowth) - bill(rateNothing))}</strong> a year &mdash;
          essentially nothing. New construction adds taxable value and tax revenue in almost
          the same proportion, so the rate barely moves. What it does instead is hand the
          town <strong>{usd(growthRevenue)}</strong> it did not have, which is{' '}
          <strong>{((growthRevenue / gap) * 100).toFixed(0)}%</strong> of the school gap
          raised from buildings rather than from you. Closing that same gap by override
          would cost this property{' '}
          <strong style={{ color: 'var(--status-critical)' }}>
            {usd(bill(rateOverride) - bill(rateNothing))} a year
          </strong>
          , every year, permanently.
        </p>
      </div>
    </div>
  )
}

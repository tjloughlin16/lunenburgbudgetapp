import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer, Cell,
} from 'recharts'
import { MODEL } from '../model/engine'

const B = MODEL.business
const S = B.summary

const LABEL: Record<string, string> = {
  other_uncategorized: 'Uncategorised', construction_trades: 'Construction & trades',
  automotive_transport: 'Automotive & transport', health_wellness: 'Health & wellness',
  food_beverage: 'Food & drink', arts_creative: 'Arts & creative',
  technology_consulting: 'Technology & consulting', agriculture: 'Agriculture',
  retail: 'Retail', personal_services: 'Personal services',
}

/** Registrations are healthy; commercial square footage is not. */
export function BusinessFormation() {
  const data = B.formationHistory
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <div className="card p-5">
        <h3 className="text-sm font-bold mb-1">New business registrations each year</h3>
        <p className="text-[12px] mb-4" style={{ color: 'var(--text-secondary)' }}>
          Certificates filed with the Town Clerk. The COVID-era surge peaked at{' '}
          {S.peakNew} in {S.peakYear} and has fallen {Math.abs(S.declineFromPeak)}% since —
          though still well above the 2018&ndash;19 baseline of about 33.
        </p>
        <div style={{ width: '100%', height: 220 }}>
          <ResponsiveContainer>
            <BarChart data={data} margin={{ top: 8, right: 8, bottom: 4, left: 4 }}>
              <CartesianGrid stroke="var(--grid)" vertical={false} />
              <XAxis dataKey="year" tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
                stroke="var(--axis)" tickLine={false} />
              <YAxis width={36} tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
                stroke="var(--axis)" tickLine={false} axisLine={false} />
              <Tooltip
                contentStyle={{ background: 'var(--surface-1)', border: '1px solid var(--grid)',
                                borderRadius: 10, fontSize: 12, color: 'var(--text-primary)' }}
                formatter={(v, n) => [v as number,
                  n === 'new' ? 'New registrations' : 'Renewals']} />
              <Legend verticalAlign="top" height={26} iconType="square"
                wrapperStyle={{ fontSize: 11, color: 'var(--text-secondary)' }}
                formatter={v => v === 'new' ? 'New registrations' : 'Renewals'} />
              <Bar dataKey="new" fill="var(--series-cost)" radius={[3, 3, 0, 0]}
                isAnimationActive={false}>
                {data.map(d => (
                  <Cell key={d.year}
                    fill={d.partial ? 'var(--text-muted)' : 'var(--series-cost)'} />
                ))}
              </Bar>
              <Bar dataKey="renewals" fill="var(--series-revenue)" radius={[3, 3, 0, 0]}
                isAnimationActive={false} />
            </BarChart>
          </ResponsiveContainer>
        </div>
        <p className="text-[11px] mt-2" style={{ color: 'var(--text-muted)' }}>
          {data.at(-1)!.year} is a partial year (grey). Records before 2018 are incomplete,
          because certificates run four years and older ones drop off the file.
        </p>
      </div>

      <div className="card p-5">
        <h3 className="text-sm font-bold mb-4">Where those businesses actually are</h3>
        <p className="text-4xl font-bold tnum leading-none mb-1">{S.activeCertificates}</p>
        <p className="text-[12px] mb-5" style={{ color: 'var(--text-secondary)' }}>
          active business certificates on file today
        </p>

        {[['On a residential street', S.onResidentialStreet, 'var(--status-critical)'],
          ['On a commercial corridor', S.onCorridor, 'var(--series-cost)']].map(
          ([label, n, color]) => (
            <div key={label as string} className="mb-3">
              <div className="flex items-baseline justify-between gap-3 mb-1">
                <span className="text-[13px] font-medium">{label as string}</span>
                <span className="text-sm font-bold tnum shrink-0">
                  {n as number}{' '}
                  <span className="font-normal" style={{ color: 'var(--text-muted)' }}>
                    {(((n as number) / S.activeCertificates) * 100).toFixed(0)}%
                  </span>
                </span>
              </div>
              <div className="h-3 rounded-full overflow-hidden"
                style={{ background: 'var(--surface-3)' }}>
                <div className="h-full rounded-full"
                  style={{ width: `${((n as number) / S.activeCertificates) * 100}%`,
                           background: color as string }} />
              </div>
            </div>
          ))}

        <dl className="space-y-1.5 text-[13px] mt-5 pt-4 border-t"
          style={{ borderColor: 'var(--grid)' }}>
          <Row k="In trades needing commercial premises"
            v={`${S.needsPremises} (${S.needsPremisesPct}%)`} />
          <Row k="Addresses hosting more than one business" v={String(S.multiTenantAddresses)} />
          <Row k="Businesses at those shared addresses" v={String(S.businessesAtMultiTenant)} />
        </dl>

        <p className="text-[13px] leading-relaxed mt-4 pt-3 border-t font-medium"
          style={{ borderColor: 'var(--grid)' }}>
          Lunenburg is not short of businesses. It is short of buildings. A consultant
          working from a spare room files the same certificate as a warehouse &mdash; and
          pays residential tax.
        </p>
      </div>
    </div>
  )
}

export function BusinessCategories() {
  const max = Math.max(...B.categories.map(c => c.count))
  return (
    <div className="card p-5">
      <h3 className="text-sm font-bold mb-4">What kind of businesses they are</h3>
      <ul className="space-y-2.5">
        {B.categories.map(c => (
          <li key={c.category}>
            <div className="flex items-baseline justify-between gap-3 mb-1">
              <span className="text-[13px]">{LABEL[c.category] ?? c.category}</span>
              <span className="text-sm font-bold tnum shrink-0">{c.count}</span>
            </div>
            <div className="h-2 rounded-full overflow-hidden"
              style={{ background: 'var(--surface-3)' }}>
              <div className="h-full rounded-full"
                style={{ width: `${(c.count / max) * 100}%`, background: 'var(--series-cost)' }} />
            </div>
          </li>
        ))}
      </ul>
      <p className="text-[12px] leading-relaxed mt-4 pt-3 border-t"
        style={{ borderColor: 'var(--grid)', color: 'var(--text-secondary)' }}>
        Construction trades, automotive and consulting dominate &mdash; work done from a
        van, a laptop or a home office. Food, drink and retail, the categories that put up
        a taxable building, are a small minority.
      </p>
      <p className="text-[11px] mt-3" style={{ color: 'var(--text-muted)' }}>
        A business certificate is a d/b/a filing under M.G.L. c.110 §5, required of sole
        proprietors and partnerships. Corporations and LLCs register with the state instead,
        so they are not all counted here. These are registrations, not employment or floor
        space, and they are a different universe from the {MODEL.taxBase.businesses}{' '}
        establishments the Census counts. Source: Town Clerk records.
      </p>
    </div>
  )
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex items-baseline justify-between gap-3">
      <dt className="min-w-0" style={{ color: 'var(--text-secondary)' }}>{k}</dt>
      <dd className="font-semibold tnum text-right">{v}</dd>
    </div>
  )
}

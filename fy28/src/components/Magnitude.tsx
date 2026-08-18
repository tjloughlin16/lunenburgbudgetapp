import { MODEL, usd, usdShort, type YearResult } from '../model/engine'

/** The scale mismatch, at the largest size the page allows. */
export function Magnitude({ years }: { years: YearResult[] }) {
  const extrasTotal = MODEL.extras.reduce((s, e) => s + e.total, 0)
  const gaps = years.map(y => y.deficit)
  const avg = gaps.reduce((a, b) => a + b, 0) / gaps.length
  const total = gaps.reduce((a, b) => a + b, 0)
  const maxGap = Math.max(...gaps)

  // How far the one-time saving stretches across the years, in order.
  let left = extrasTotal
  const covered = gaps.map(g => {
    const c = Math.min(left, g); left -= c
    return c / g
  })

  return (
    <div>
      <div className="grid gap-6 lg:grid-cols-2 items-start">
        {/* ---- what everyone says to cut ---- */}
        <div className="card p-6">
          <p className="text-[11px] font-semibold uppercase tracking-widest mb-2"
            style={{ color: 'var(--text-muted)' }}>
            Everything people say to cut
          </p>
          <p className="text-5xl sm:text-6xl font-bold tnum leading-none mb-1">
            {usd(extrasTotal)}
          </p>
          <p className="text-[13px] mb-2" style={{ color: 'var(--text-secondary)' }}>
            Every sport, every band, every club, every art supply in the district &mdash;
            all of it, gone. Once.
          </p>
          <p className="text-[12px] mb-6" style={{ color: 'var(--text-muted)' }}>
            Bars below show each category as a share of that {usd(extrasTotal)}.
          </p>

          <ul className="space-y-4">
            {MODEL.extras.map(e => (
              <li key={e.cat}>
                <div className="flex items-baseline justify-between gap-3 mb-1.5">
                  <span className="text-[13px] font-medium">{e.label}</span>
                  <span className="text-lg font-bold tnum shrink-0">{usd(e.total)}</span>
                </div>
                <p className="text-[11px] tnum mb-1" style={{ color: 'var(--text-muted)' }}>
                  {((e.total / extrasTotal) * 100).toFixed(0)}% of the {usd(extrasTotal)}{' '}
                  total below
                </p>
                <div className="h-3 rounded-full overflow-hidden"
                  style={{ background: 'var(--surface-3)' }}>
                  <div className="h-full rounded-full"
                    style={{ width: `${(e.total / extrasTotal) * 100}%`,
                             background: 'var(--series-cost)' }} />
                </div>
                <p className="text-[11px] mt-1" style={{ color: 'var(--text-muted)' }}>
                  {e.items.join(' · ')}
                </p>
              </li>
            ))}
          </ul>
        </div>

        {/* ---- the hole, every year ---- */}
        <div className="card p-6">
          <p className="text-[11px] font-semibold uppercase tracking-widest mb-2"
            style={{ color: 'var(--text-muted)' }}>
            The hole &mdash; and it comes back every year
          </p>
          <p className="text-5xl sm:text-6xl font-bold tnum leading-none mb-1"
            style={{ color: 'var(--status-critical)' }}>
            {usd(avg)}
          </p>
          <p className="text-[13px] mb-6" style={{ color: 'var(--text-secondary)' }}>
            Average gap per year, FY{years[0].fy}&ndash;FY{years.at(-1)!.fy}.
            Five-year total: <strong>{usd(total)}</strong>.
          </p>

          <ul className="space-y-4">
            {years.map((y, i) => (
              <li key={y.fy}>
                <div className="flex items-baseline justify-between gap-3 mb-1.5">
                  <span className="text-[13px] font-medium">FY{y.fy}</span>
                  <span className="text-lg font-bold tnum shrink-0"
                    style={{ color: 'var(--status-critical)' }}>{usd(y.deficit)}</span>
                </div>
                <div className="h-3 rounded-full overflow-hidden flex gap-0.5"
                  style={{ background: 'var(--surface-3)',
                           width: `${(y.deficit / maxGap) * 100}%` }}>
                  <div className="h-full"
                    style={{ width: `${covered[i] * 100}%`, background: 'var(--series-cost)' }} />
                  <div className="h-full flex-1"
                    style={{ background: 'var(--status-critical)' }} />
                </div>
                <p className="text-[11px] mt-1" style={{ color: 'var(--text-muted)' }}>
                  {'Bar length is this year’s gap relative to the largest year. '}
                  {covered[i] >= 1
                    ? 'Covered by cutting all the extras — this year only'
                    : covered[i] > 0
                    ? `${(covered[i] * 100).toFixed(0)}% covered by what is left of the extras`
                    : 'Nothing left to cut from the extras — this comes out of classrooms'}
                </p>
              </li>
            ))}
          </ul>
        </div>
      </div>

      {/* ---- the sentence ---- */}
      <div className="card p-6 mt-4" style={{ borderColor: 'var(--status-critical)' }}>
        <p className="text-xl sm:text-2xl font-bold leading-snug">
          Cutting every sport, every band and every club in Lunenburg covers{' '}
          <span style={{ color: 'var(--status-critical)' }}>
            {((extrasTotal / total) * 100).toFixed(0)}% of the next five years
          </span>{' '}
          &mdash; and you can only do it once.
        </p>
        <p className="text-[14px] leading-relaxed mt-3" style={{ color: 'var(--text-secondary)' }}>
          {usd(extrasTotal)} against {usdShort(total)} of accumulated shortfall. It roughly
          covers FY{years[0].fy} alone. From FY{years[1].fy} onward there is nothing left in
          that column, and every dollar has to come out of classrooms, support staff and
          special education instead. That is the whole argument on one line.
        </p>
      </div>
    </div>
  )
}

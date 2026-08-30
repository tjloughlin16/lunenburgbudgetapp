import { MODEL, usd } from '../model/engine'
import { CONVERTIBLE } from '../model/capital'

const CAP = MODEL.freeCash.capital

/** Defer capital projects, and put what they cost against the school gap.
 *
 *  This is the free cash argument with the assumption taken out of it. The rate board has
 *  to guess what the Capital Planning Committee would stop, and reports a range because
 *  nothing published says — here the reader stops things themselves, so there is no
 *  behaviour to model. The lumpiness that makes the board's figure a range is just the
 *  price list on this card.
 *
 *  Two things it must never let a reader do, both of which would invent money:
 *
 *  - **Pick the ring-fenced projects.** $594,000 of the programme is the Vehicle Use
 *    Special Purpose Stabilization Fund, restricted to vehicles and equipment. Not
 *    spending it there does not release it to anything else. Those rows are shown, and
 *    disabled, because a reader who cannot see them will assume we forgot the fire truck.
 *  - **Treat it as recurring.** Capital money is one-time. The page applies it to FY28 and
 *    adds it straight back in FY29, and the card says so above the list rather than in a
 *    footnote. */
export function CapitalLever({ picked, setPicked }: {
  picked: Set<number>
  setPicked: (s: Set<number>) => void
}) {
  if (!CAP) return null

  const funded = [...CAP.items].filter(i => i.funded).sort((a, b) => a.rank - b.rank)
  const total = CONVERTIBLE
    .filter(i => picked.has(i.rank))
    .reduce((s, i) => s + i.cost, 0)

  const toggle = (rank: number, on: boolean) => {
    const next = new Set(picked)
    if (on) next.add(rank)
    else next.delete(rank)
    setPicked(next)
  }

  return (
    <div className="card p-4">
      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 mb-1">
        <h3 className="text-[13px] font-bold">Defer capital projects</h3>
        {total > 0 && (
          <span className="text-[13px] font-bold tnum"
            style={{ color: 'var(--status-good)' }}>{usd(total)}</span>
        )}
      </div>
      <p className="text-[12px] leading-relaxed mb-2" style={{ color: 'var(--text-secondary)' }}>
        The FY27 capital programme is {usd(CAP.programmeTotal)}, and free cash pays{' '}
        {usd(CAP.plannedFromFreeCash)} of it &mdash; the largest single source. Stop a
        project and that money is available for something else.{' '}
        <strong>It is one-time money.</strong> It closes part of FY28 and the same hole
        returns in FY29, with the project still unbuilt. There is already{' '}
        {usd(CAP.queueValue)} of ranked work below the funding line, so nothing here gains
        slack &mdash; this moves a queue, it does not shorten it.
      </p>
      <ul>
        {funded.map(i => {
          const locked = i.funding === 'stabilization'
          const on = picked.has(i.rank)
          return (
            <li key={i.rank} className="border-b last:border-0"
              style={{ borderColor: 'var(--grid)' }}>
              <label className={`flex items-center gap-2.5 py-2 ${locked ? '' : 'cursor-pointer'}`}>
                <input type="checkbox" checked={on} disabled={locked}
                  aria-label={locked
                    ? `${i.project} — funded from restricted money, cannot be redirected`
                    : `Defer ${i.project}`}
                  onChange={e => toggle(i.rank, e.target.checked)}
                  className="shrink-0 disabled:opacity-30"
                  style={{ accentColor: 'var(--status-good)' }} />
                <span className="tnum shrink-0 w-5 text-right text-[11px] font-semibold"
                  style={{ color: 'var(--text-muted)' }}>{i.rank}</span>
                <span className="flex-1 min-w-0">
                  <span className="block text-[12px] leading-snug"
                    style={{ textDecoration: on ? 'line-through' : 'none',
                             color: locked ? 'var(--text-muted)'
                               : on ? 'var(--text-muted)' : 'var(--text-primary)' }}>
                    {i.project}
                  </span>
                  <span className="block text-[10px]" style={{ color: 'var(--text-muted)' }}>
                    {i.dept}
                    {locked && <span style={{ color: 'var(--status-warning)' }}>
                      {' '}&middot; vehicle stabilization money &mdash; restricted to
                      vehicles and equipment, so deferring it frees nothing for the schools
                    </span>}
                  </span>
                </span>
                <span className="text-[12px] tnum shrink-0"
                  style={{ color: locked ? 'var(--text-muted)'
                    : on ? 'var(--status-good)' : 'var(--text-secondary)' }}>
                  {usd(i.cost)}
                </span>
              </label>
            </li>
          )
        })}
      </ul>
      <p className="text-[10.5px] leading-relaxed mt-2.5"
        style={{ color: 'var(--text-muted)' }}>
        Ranks and costs are the Capital Planning Committee&rsquo;s own, from the FY27
        capital plan voted at the 2026 Annual Town Meeting. That programme is already
        appropriated &mdash; this shows what a capital programme contains and what
        deferring one costs, not a list of live choices. The FY28 plan is not published.
      </p>
    </div>
  )
}

import { MODEL, usd, yearCut, type YearResult } from '../model/engine'
import { StatusBadge } from './primitives'

/** Landmark programs people actually ask about: "what year do we lose X?" */
const LANDMARKS = [
  { id: 'athletics_remaining', label: 'All school sports' },
  { id: 'hs_music_program', label: 'High school band & chorus' },
  { id: 'hs_electives_ap', label: 'Advanced Placement courses' },
  { id: 'libraries', label: 'Staffed school libraries' },
  { id: 'core_teachers_more', label: 'Further classroom teacher cuts' },
  { id: 'guidance_partial', label: 'Guidance counselling capacity' },
]

export function Landmarks({ years }: { years: YearResult[] }) {
  // Soonest loss first; anything that survives the projection goes last.
  const ranked = LANDMARKS
    .map(l => ({ ...l, fy: yearCut(years, l.id) }))
    .sort((a, b) => (a.fy ?? Infinity) - (b.fy ?? Infinity))

  return (
    <div className="grid gap-2.5 sm:grid-cols-2 lg:grid-cols-3">
      {ranked.map(l => {
        const fy = l.fy
        return (
          <div key={l.id} className="card p-4">
            <p className="text-[13px] font-medium leading-snug mb-2">{l.label}</p>
            {fy ? (
              <>
                <p className="text-2xl font-bold tnum leading-none"
                  style={{ color: 'var(--status-critical)' }}>FY{fy}</p>
                <p className="text-[11px] mt-1" style={{ color: 'var(--text-secondary)' }}>
                  {fy === 28 ? 'Next school year' : `${fy - 27} years from now`}
                </p>
              </>
            ) : (
              <>
                <p className="text-2xl font-bold leading-none"
                  style={{ color: 'var(--status-good)' }}>Survives</p>
                <p className="text-[11px] mt-1" style={{ color: 'var(--text-secondary)' }}>
                  Still funded through FY{years.at(-1)?.fy}
                </p>
              </>
            )}
          </div>
        )
      })}
    </div>
  )
}

export function Timeline({ years }: { years: YearResult[] }) {
  return (
    <ol className="space-y-4">
      {years.map(y => (
        <li key={y.fy} className="card p-5">
          <div className="flex flex-wrap items-baseline justify-between gap-3 mb-3 pb-3 border-b"
            style={{ borderColor: 'var(--grid)' }}>
            <h3 className="text-lg font-bold">FY{y.fy}</h3>
            <div className="flex gap-5 text-xs">
              <span>
                <span style={{ color: 'var(--text-muted)' }}>Gap </span>
                <strong className="tnum" style={{ color: 'var(--status-critical)' }}>
                  {usd(y.deficit)}
                </strong>
              </span>
              <span>
                <span style={{ color: 'var(--text-muted)' }}>Cut </span>
                <strong className="tnum">{usd(y.cutTotal)}</strong>
              </span>
              <span>
                <span style={{ color: 'var(--text-muted)' }}>Positions lost to date </span>
                <strong className="tnum">{y.cumFte.toFixed(1)}</strong>
              </span>
            </div>
          </div>

          {y.cuts.length === 0 ? (
            <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
              No further cuts required this year.
            </p>
          ) : (
            <ul className="space-y-1.5">
              {y.cuts.map(c => (
                <li key={c.id} className="flex items-start gap-3 text-sm">
                  <span className="flex-1 min-w-0">
                    <span className="font-medium"
                      style={{
                        textDecoration: c.blocked ? 'none' : 'line-through',
                        opacity: c.blocked ? 1 : 0.7,
                      }}>{c.name}</span>
                    <span className="block text-xs leading-snug mt-0.5"
                      style={{ color: 'var(--text-secondary)' }}>{c.impact}</span>
                    <span className="block text-[10px] uppercase tracking-wider font-semibold mt-0.5"
                      style={{ color: 'var(--text-muted)' }}>
                      {MODEL.categories[c.cat]?.label}
                      {c.source === 'EST' && ' · our estimate'}
                    </span>
                  </span>
                  <span className="text-right shrink-0">
                    <span className="block font-bold tnum">{usd(c.cost)}</span>
                    <StatusBadge kind={c.blocked ? 'mandated' : 'cut'} />
                  </span>
                </li>
              ))}
            </ul>
          )}

          {y.unclosed > 0 && (
            <p className="text-sm font-semibold mt-4 pt-3 border-t"
              style={{ color: 'var(--status-critical)', borderColor: 'var(--grid)' }}>
              {usd(y.unclosed)} of this year&rsquo;s gap cannot be closed — everything
              legally cuttable is already gone. Closing it would require cutting services
              the district is required by law to provide.
            </p>
          )}
        </li>
      ))}
    </ol>
  )
}

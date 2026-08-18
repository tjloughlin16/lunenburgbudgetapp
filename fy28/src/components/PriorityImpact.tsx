import { MODEL, usd, yearCut, type YearResult } from '../model/engine'

const WATCH = [
  { id: 'athletics_remaining', label: 'School sports' },
  { id: 'hs_music_program', label: 'Band & chorus' },
  { id: 'hs_electives_ap', label: 'AP courses' },
  { id: 'libraries', label: 'Libraries' },
  { id: 'core_teachers_more', label: 'More teachers' },
  { id: 'reading_spec_ps', label: 'Reading specialists' },
]

/** Shown directly under the ranking, so the consequence of a reorder is immediate. */
export function PriorityImpact({ years }: { years: YearResult[] }) {
  const fy28 = years[0]
  const cuts = fy28.cuts.filter(c => !c.blocked)
  const last = years.at(-1)!.fy

  return (
    <div className="card p-5 mt-6">
      <h3 className="text-sm font-bold mb-1">What this ranking does</h3>
      <p className="text-[13px] mb-4" style={{ color: 'var(--text-secondary)' }}>
        Updates as you reorder. These are the results the rest of this page is built on.
      </p>

      <div className="grid gap-5 md:grid-cols-2">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-widest mb-2"
            style={{ color: 'var(--status-critical)' }}>
            Cut first, in FY28 — {usd(fy28.cutTotal)}
          </p>
          <ul className="space-y-1">
            {cuts.map(c => (
              <li key={c.id} className="flex justify-between gap-3 text-[13px]">
                <span style={{ color: 'var(--text-secondary)' }}>{c.name}</span>
                <span className="tnum shrink-0" style={{ color: 'var(--text-muted)' }}>
                  {usd(c.cost)}
                </span>
              </li>
            ))}
            {cuts.length === 0 && (
              <li className="text-[13px]" style={{ color: 'var(--text-secondary)' }}>
                Nothing — no gap to close in FY28 under your assumptions.
              </li>
            )}
          </ul>
        </div>

        <div>
          <p className="text-[10px] font-bold uppercase tracking-widest mb-2"
            style={{ color: 'var(--text-muted)' }}>The year each thing goes</p>
          <ul className="grid grid-cols-2 gap-x-4 gap-y-1.5">
            {WATCH
              .map(w => ({ ...w, fy: yearCut(years, w.id) }))
              .sort((a, b) => (a.fy ?? Infinity) - (b.fy ?? Infinity))
              .map(w => {
              const fy = w.fy
              return (
                <li key={w.id} className="flex justify-between gap-2 text-[13px]">
                  <span style={{ color: 'var(--text-secondary)' }}>{w.label}</span>
                  <span className="font-bold tnum shrink-0" style={{
                    color: fy ? 'var(--status-critical)' : 'var(--status-good)' }}>
                    {fy ? `FY${fy}` : 'safe'}
                  </span>
                </li>
              )
            })}
          </ul>
          <p className="text-[11px] mt-3" style={{ color: 'var(--text-muted)' }}>
            &ldquo;Safe&rdquo; means still funded through FY{last} — not that it is
            protected for good.
          </p>
        </div>
      </div>
    </div>
  )
}

/** A compact reminder of the active ranking, for use further down the page. */
export function ActiveRanking({ order, presetName }: {
  order: string[]; presetName: string | null
}) {
  return (
    <p className="text-[12px] mb-4 px-3 py-2 rounded-lg border"
      style={{ borderColor: 'var(--grid)', background: 'var(--surface-1)',
               color: 'var(--text-secondary)' }}>
      <span className="font-semibold" style={{ color: 'var(--text-primary)' }}>
        Your ranking:
      </span>{' '}
      {presetName ? <>{presetName} — </> : <>custom — </>}
      protecting <strong>{MODEL.categories[order[0]]?.label}</strong> longest, cutting{' '}
      <strong>{MODEL.categories[order.at(-1)!]?.label}</strong> first.{' '}
      <a href="#priorities" style={{ color: 'var(--series-cost)' }}>Change it</a>
    </p>
  )
}

/** THE DEFINING IMAGE OF /boards/compared: every ranked board as one bar, the share of
 *  its meetings with minutes posted, best to worst, the three budget boards picked out.
 *  TJ, 17 September 2026: "put a chart that visualizes and compares the % across
 *  boards ... in the header of the page (like we did for the development). This one
 *  doesn't need to be conceptual. its just the defining image."
 *
 *  Plain elements rather than a chart library: thirty-one labelled bars read better as
 *  a list than as axes, it prerenders to real HTML, and the figure and the count sit on
 *  each bar so no bar is a bare number (rule 7b). Full width, like the growth drawing. */
type Row = { slug: string; name: string; the_three: boolean; meetings: number; with_minutes: number; share: number; rank?: number }

export function BoardBars({ rows, fys }: { rows: Row[]; fys: number[] }) {
  const tone = (s: number) => (s >= 90 ? 'var(--status-good)' : s >= 60 ? 'var(--text-secondary)' : 'var(--status-critical)')
  return (
    <figure className="mt-6" style={{ width: '100vw', marginLeft: 'calc(50% - 50vw)' }}>
      <div className="mx-auto px-4 sm:px-6" style={{ maxWidth: 1100 }}>
        <figcaption className="text-[11px] font-semibold uppercase tracking-widest mb-3" style={{ color: 'var(--text-muted)' }}>
          Meetings with minutes posted, FY{fys[0]}&ndash;FY{fys[fys.length - 1]} &middot; every board with twenty or more meetings, best to worst
        </figcaption>
        <ol className="space-y-[3px]">
          {rows.map(r => (
            <li key={r.slug} className="flex items-center gap-2 sm:gap-3">
              <a href={`/boards/${r.slug}`}
                className={`shrink-0 text-right truncate text-[11.5px] sm:text-[12.5px] ${r.the_three ? 'font-bold' : ''}`}
                style={{ width: '38%', maxWidth: 280, color: r.the_three ? 'var(--text-primary)' : 'var(--text-secondary)' }}>
                {r.name}
              </a>
              <div className="flex-1 min-w-0 h-[18px] sm:h-[20px] rounded-sm relative overflow-hidden" style={{ background: 'var(--surface-3)' }}>
                <div className="h-full rounded-sm" style={{ width: `${r.share}%`, background: tone(r.share), opacity: r.the_three ? 1 : 0.6 }} />
                <span className="absolute inset-y-0 flex items-center text-[11px] tnum whitespace-nowrap px-1.5"
                  style={{ left: `${Math.min(r.share, 82)}%`, color: 'var(--text-primary)' }}>
                  <strong>{Math.round(r.share)}%</strong>&nbsp;<span style={{ color: 'var(--text-muted)' }}>{r.with_minutes} of {r.meetings}</span>
                </span>
              </div>
            </li>
          ))}
        </ol>
      </div>
    </figure>
  )
}

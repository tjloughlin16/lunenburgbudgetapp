import { MODEL } from '../model/engine'

/** Where a finding's working is shown.
 *
 *  Most of them live further down the same page, so a bare `#anchor` is right. Some do
 *  not: the special education argument is on Bend the Curve, because it is an argument
 *  about the rate rather than about the situation. An anchor containing a slash is taken
 *  as a full address so a finding can point at whichever page actually shows its
 *  working, instead of the site pretending everything is in one place. */
const hrefFor = (anchor: string) => anchor.includes('/') ? anchor : `#${anchor}`

/** The findings, stated up front so they don't get lost in the mechanics below. */
/** The six numbers, as large as the page allows, before any prose. */
export function Headlines() {
  const tone = (t: string) => t === 'critical' ? 'var(--status-critical)'
    : t === 'good' ? 'var(--status-good)' : 'var(--text-primary)'
  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 mb-10">
      {MODEL.headlines.map(h => (
        <a key={h.id} href={hrefFor(h.anchor)}
          className="card p-5 flex flex-col hover:opacity-90 transition-opacity">
          <p className="text-[11px] font-semibold uppercase tracking-widest mb-2 leading-tight"
            style={{ color: 'var(--text-muted)' }}>{h.label}</p>
          <p className="text-4xl font-bold tnum leading-none mb-2"
            style={{ color: tone(h.tone) }}>{h.value}</p>
          <p className="text-[12px] leading-relaxed flex-1"
            style={{ color: 'var(--text-secondary)' }}>{h.sub}</p>
        </a>
      ))}
    </div>
  )
}

export function Conclusions() {
  return (
    <div>
      <Headlines />
      <p className="text-xl sm:text-2xl font-bold leading-snug max-w-4xl mb-8">
        {MODEL.headline}
      </p>
      <ol className="grid gap-3 md:grid-cols-2">
        {MODEL.conclusions.map(c => (
          <li key={c.n}>
            <a href={hrefFor(c.anchor)}
              className="card p-5 h-full flex flex-col hover:opacity-90 transition-opacity block">
              <div className="flex items-baseline justify-between gap-3 mb-2">
                <span className="text-[11px] font-bold tnum tracking-widest"
                  style={{ color: 'var(--text-muted)' }}>
                  {String(c.n).padStart(2, '0')}
                </span>
                <span className="text-lg font-bold tnum shrink-0"
                  style={{ color: 'var(--status-critical)' }}>{c.figure}</span>
              </div>
              <h3 className="text-[15px] font-bold leading-snug mb-2">{c.headline}</h3>
              <p className="text-[13px] leading-relaxed flex-1"
                style={{ color: 'var(--text-secondary)' }}>{c.body}</p>
              <span className="text-[11px] font-semibold mt-3"
                style={{ color: 'var(--series-cost)' }}>See the working &rarr;</span>
            </a>
          </li>
        ))}
      </ol>
    </div>
  )
}

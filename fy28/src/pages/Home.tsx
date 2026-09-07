import type { Area, Tab } from '../routes'
import { AREA_HOME, AREA_LABEL, pathFor } from '../routes'

/** The front page: four doors and nothing else.
 *
 *  For its whole life the root served the walkthrough, which made this site one corridor —
 *  the right shape when the only thing here was an argument about FY28, and the wrong shape
 *  now that the archive behind it has grown into documents, datasets and a queryable API.
 *
 *  IT SHOWS ONLY THE TOP LEVEL, and that took three attempts to get right.
 *
 *  The first version had a paragraph per door and two lines under every link. The second
 *  cut the prose but kept the links, so the page still listed eighteen destinations — a
 *  chooser with a sitemap stapled to it, which is the same failure in a smaller font. TJ:
 *  "too many buttons... ONLY show the top level subpages."
 *
 *  A chooser is a fork in a road, not a directory. Its whole job is one decision, and every
 *  extra target on the page is a decision it did not ask for. What is inside an area is the
 *  area's business — the header bar draws it the moment you are in one.
 *
 *  Two rules that are easy to break on a landing page of all places:
 *
 *   - **No figure is typed into this copy.** This is where "3,877 documents" gets written
 *     down once and quietly stops being true. (CLAUDE.md rule 2.)
 *   - **A door describes what exists.** "The money" is mostly not built and says so in
 *     those words. (Rule 7: an intention is not an outcome.)
 */

const DOORS: { area: Area; who: string; note?: string }[] = [
  { area: 'crisis', who: 'Why the budget keeps breaking, and what would fix it' },
  { area: 'money', who: 'How the town’s money actually moves',
    note: 'Being built' },
  { area: 'data', who: 'Every table, and query it yourself' },
  { area: 'agents', who: 'Pointing an assistant at this, or you are one' },
]

export function Home({ onJump }: { onJump: (t: Tab) => void }) {
  return (
    <div className="mx-auto max-w-3xl px-5 pb-20">
      <header className="pt-10 pb-6">
        <h1 className="text-[27px] sm:text-4xl font-bold tracking-tight leading-[1.1]">
          The <span style={{ color: 'var(--brand)' }}>Lunenburg</span> Budget Project
        </h1>
        <p className="mt-2.5 text-[15px] leading-snug"
          style={{ color: 'var(--text-secondary)' }}>
          An independent tool for residents. Pick your depth.
        </p>
      </header>

      {/* One column, always. Four rows on a phone is the whole page; two columns would
          make the fourth door share a line with the third and stop being a list of
          four things. The row is the hit target, not the words in it. */}
      <div className="grid gap-2.5">
        {DOORS.map(d => (
          <button key={d.area} onClick={() => onJump(AREA_HOME[d.area])}
            className="card px-4 py-4 text-left w-full min-h-[64px]
                       transition-opacity hover:opacity-90">
            <span className="flex items-baseline gap-2 flex-wrap">
              <span className="text-[17px] font-bold leading-tight">
                {AREA_LABEL[d.area]}
              </span>
              {d.note && (
                <span className="text-[10.5px] font-semibold uppercase tracking-wider"
                  style={{ color: 'var(--status-warning)' }}>{d.note}</span>
              )}
            </span>
            <span className="block text-[13.5px] mt-1 leading-snug"
              style={{ color: 'var(--text-secondary)' }}>{d.who}</span>
          </button>
        ))}
      </div>

      <p className="mt-8 pt-4 border-t text-[12.5px] leading-snug"
        style={{ borderColor: 'var(--grid)', color: 'var(--text-muted)' }}>
        The walkthrough used to be at this address and is now at{' '}
        <code>{pathFor('walk')}</code>. Every other address is unchanged.
      </p>
    </div>
  )
}

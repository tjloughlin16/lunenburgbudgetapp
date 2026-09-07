import type { Area, Tab } from '../routes'
import { AREA_HOME, AREA_LABEL } from '../routes'

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
 *   - **A door describes what exists.** "The money" carried a `Being built` flag while its
 *     front page said so too; it now opens on a real page that hands over five published
 *     reference documents and the list of what the records cannot answer, so the flag came
 *     off. A door may promise only what is behind it. (Rule 7: an intention is not an
 *     outcome.)
 */

/** `quiet` marks a door that is not for a resident. It is smaller and in the muted
 *  colour rather than the brand one, so the eye sorts it out of the set of three before
 *  reading it — the three above are choices about the town, and this one is plumbing. */
const DOORS: { area: Area; who: string; note?: string; quiet?: boolean
  /** A door that opens a generated FILE rather than a route. `The database` is the
   *  schema page — 74 tables with a live query box — which is a published document, not
   *  a React page. It used to open the rate register, which is a good document about
   *  fees and a baffling front door for a database: it greets you with athletic fees.
   *  Landing on the thing the area is named after is worth leaving the app for. */
  href?: string }[] = [
  { area: 'crisis', who: 'Why the budget keeps breaking, and what would fix it' },
  { area: 'money', who: 'Where every dollar comes from, and where the trail goes cold' },
  { area: 'data', who: 'Every table, what it holds, and a query box',
    href: '/reference/schema.html' },
  { area: 'agents', who: 'Pointing an assistant at this, or you are one',
    quiet: true },
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
        {DOORS.map(d => d.href ? (
          <a key={d.area} href={d.href}
            className="card px-4 py-4 text-left w-full min-h-[64px] block
                       transition-opacity hover:opacity-90">
            <span className="text-[17px] font-bold leading-tight block">
              {AREA_LABEL[d.area]}
            </span>
            <span className="block text-[13.5px] mt-1 leading-snug"
              style={{ color: 'var(--text-muted)' }}>{d.who}</span>
          </a>
        ) : (
          <button key={d.area} onClick={() => onJump(AREA_HOME[d.area])}
            className={'card text-left w-full transition-opacity hover:opacity-90 ' +
              (d.quiet ? 'px-4 py-3 min-h-[52px] mt-1.5' : 'px-4 py-4 min-h-[64px]')}
            style={d.quiet ? { background: 'transparent' } : undefined}>
            <span className="flex items-baseline gap-2 flex-wrap">
              <span className={d.quiet
                ? 'text-[14.5px] font-bold leading-tight'
                : 'text-[17px] font-bold leading-tight'}
                style={d.quiet ? { color: 'var(--text-secondary)' } : undefined}>
                {AREA_LABEL[d.area]}
              </span>
              {d.note && (
                <span className="text-[10.5px] font-semibold uppercase tracking-wider"
                  style={{ color: 'var(--status-warning)' }}>{d.note}</span>
              )}
            </span>
            <span className={d.quiet
              ? 'block text-[12.5px] mt-0.5 leading-snug'
              : 'block text-[13.5px] mt-1 leading-snug'}
              style={{ color: 'var(--text-muted)' }}>{d.who}</span>
          </button>
        ))}
      </div>

      {/* The "the walkthrough moved" note was here and is gone. It explained a
          change to somebody who had not seen the old page and could not have missed it,
          on the one page whose job is to be four choices. Every old address still
          resolves — `walk`, `walkthrough`, `start` and `start-here` are all aliases —
          so nobody arrives at a dead link and needs telling. */}

    </div>
  )
}

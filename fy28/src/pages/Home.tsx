import type { Area, Tab } from '../routes'
import { AREA_LABEL, AREA_TABS, LABEL, pathFor } from '../routes'

/** The front page: a chooser, not a chapter.
 *
 *  For its whole life the root served the walkthrough, which made this site one corridor —
 *  the right shape when the only thing here was an argument about FY28, and the wrong shape
 *  now that the archive behind it has grown into documents, datasets and a queryable API.
 *
 *  THE DOORS ARE DERIVED, NOT LISTED. `AREA_TABS` in routes.ts decides what is in an area,
 *  and the header bar reads the same map. A hand-kept list here would be a second copy of
 *  the site's structure, and the two would disagree the first time a page moved — which is
 *  precisely the bug the old header had, with `trail.unshift('walk')` encoding "the root is
 *  the walkthrough" in a place the router could not see.
 *
 *  WRITTEN FOR A PHONE, which is the whole of its design. The first version carried a
 *  paragraph per door and two lines under every link — roughly 700 words before a thumb
 *  reached anything tappable. A chooser's job is to be got past: every word between
 *  arriving and tapping delays the page somebody actually wants, and on a phone it is also
 *  a scroll. One line per door, three or four words per link.
 *
 *  Two rules that are easy to break on a landing page of all places:
 *
 *   - **No figure is typed into this copy.** This is where "3,877 documents" gets written
 *     down once and quietly stops being true. (CLAUDE.md rule 2.)
 *   - **A door describes what exists.** "The money" is mostly not built and says so in
 *     those words. (Rule 7: an intention is not an outcome.)
 */

/** One line per area, and a link out to anything published as a file rather than a route.
 *  `sources` appears in no door: it is global chrome, because it backs all four. */
const DOORS: {
  area: Area
  who: string
  building?: string
  files?: { href: string; label: string; what: string }[]
}[] = [
  { area: 'crisis', who: 'Why it keeps breaking, and what would fix it' },
  {
    area: 'money',
    who: 'How the town’s money actually moves',
    building: 'The flow diagrams and structural findings are published as reference pages ' +
      'below. They have not been written into the site properly yet.',
    files: [
      { href: '/reference/school-money-flow.html', label: 'School money flow',
        what: 'Every dollar in and out, FY2026' },
      { href: '/reference/town-money-flow.html', label: 'Town money flow',
        what: 'The whole town, same model' },
      { href: '/reference/who-decides.html', label: 'Who decides',
        what: 'Where each dollar lands' },
      { href: '/reference/LEDGER-STRUCTURE.md', label: 'The ledger',
        what: 'How it is built and named' },
    ],
  },
  {
    area: 'data',
    who: 'Query it yourself',
    files: [
      { href: '/reference/schema.html', label: 'The database',
        what: 'Every table, and what it holds' },
      { href: '/reference/MONEY-NODES.md', label: 'Money nodes',
        what: 'Every input and output' },
    ],
  },
  { area: 'agents', who: 'Pointing an assistant at this, or you are one' },
]

export function Home({ onJump }: { onJump: (t: Tab) => void }) {
  return (
    <div className="mx-auto max-w-5xl px-5 pb-16">
      <header className="pt-9 pb-7">
        <h1 className="text-[27px] sm:text-4xl font-bold tracking-tight leading-[1.1]">
          The <span style={{ color: 'var(--brand)' }}>Lunenburg</span> Budget Project
        </h1>
        <p className="mt-2.5 text-[15px] leading-snug"
          style={{ color: 'var(--text-secondary)' }}>
          Four ways in. Pick your depth.
        </p>
      </header>

      {DOORS.map(d => (
        <section key={d.area} className="border-t pt-5 pb-6"
          style={{ borderColor: 'var(--grid)' }}>
          <h2 className="text-[19px] font-bold tracking-tight">{AREA_LABEL[d.area]}</h2>
          <p className="text-[13.5px] mt-0.5" style={{ color: 'var(--text-muted)' }}>
            {d.who}
          </p>

          {d.building && (
            <p className="mt-3 text-[13px] leading-snug card p-3"
              style={{ color: 'var(--text-secondary)' }}>
              <strong style={{ color: 'var(--status-warning)' }}>Being built.</strong>{' '}
              {d.building}
            </p>
          )}

          {/* One column on a phone, two once there is room. The whole row is the hit
              target — a link-sized tap area on a touch screen is a design defect. */}
          <div className="grid gap-2 sm:grid-cols-2 mt-3.5">
            {AREA_TABS[d.area].map(id => (
              <button key={d.area + id} onClick={() => onJump(id)}
                className="card px-3.5 py-3 text-left w-full min-h-[44px]
                           transition-opacity hover:opacity-90">
                <span className="text-[14.5px] font-bold block leading-tight">
                  {LABEL[id]}
                </span>
                <span className="block text-[12.5px] mt-0.5 leading-snug tnum"
                  style={{ color: 'var(--text-muted)' }}>{pathFor(id)}</span>
              </button>
            ))}
            {/* Real files, not routes — an <a> rather than a router jump, because these are
                generated pages served as themselves. */}
            {(d.files ?? []).map(f => (
              <a key={f.href} href={f.href}
                className="card px-3.5 py-3 text-left w-full min-h-[44px] block
                           transition-opacity hover:opacity-90">
                <span className="text-[14.5px] font-bold block leading-tight">{f.label}</span>
                <span className="block text-[12.5px] mt-0.5 leading-snug"
                  style={{ color: 'var(--text-secondary)' }}>{f.what}</span>
              </a>
            ))}
          </div>
        </section>
      ))}

      <p className="border-t pt-4 text-[12.5px] leading-snug"
        style={{ borderColor: 'var(--grid)', color: 'var(--text-muted)' }}>
        The walkthrough used to be at this address and is now at{' '}
        <code>{pathFor('walk')}</code>. Every other address is unchanged.
      </p>
    </div>
  )
}

import type { Tab } from '../routes'
import { LABEL, pathFor } from '../routes'

/** The front page: a chooser, not a chapter.
 *
 *  For its whole life the root served the walkthrough, which made this site one curated
 *  corridor — the right shape when the only thing here was an argument about FY28, and the
 *  wrong shape now that the archive behind it has grown into documents, datasets and a
 *  queryable API. So: doors. A reader picks their depth before they pick a page.
 *
 *  WRITTEN FOR A PHONE, WHICH IS THE WHOLE OF ITS DESIGN.
 *
 *  The first version of this page carried a paragraph on every door AND a two-line
 *  description under every link — about 700 words before a thumb reached anything
 *  tappable. TJ: "too wordy. think phone first."
 *
 *  A chooser's job is to be got past. Every word between arriving and tapping is a word
 *  that delays the page somebody actually wants, and on a phone it is also a scroll. So
 *  each door is a title, ONE line saying who it is for, and its links. The links carry
 *  three or four words, not a sentence — enough to tell two apart, which is all a menu
 *  owes anyone. Anything longer belongs on the page it describes.
 *
 *  Two rules that are easy to break on a landing page of all places:
 *
 *   - **No figure is typed into this copy.** This is where "3,877 documents" gets written
 *     down once and quietly stops being true. Counts belong on the pages that derive
 *     them. (CLAUDE.md rule 2.)
 *   - **A door describes what exists.** "The money" is mostly not built and says so, in
 *     those words. (Rule 7: an intention is not an outcome.)
 */

type Door = {
  key: string
  title: string
  who: string
  items: { id: Tab; what: string }[]
  /** Said out loud on a door still being built, rather than implied by a thin list. */
  building?: string
}

const DOORS: Door[] = [
  {
    key: 'budget',
    title: 'Understanding the budget',
    who: 'Why it keeps breaking, and what would fix it',
    items: [
      { id: 'walk', what: 'Start here. Assumes nothing' },
      { id: 'solved', what: 'What actually keeps the gap shut' },
      { id: 'curve', what: 'Why cuts do not bend the curve' },
      { id: 'adjust', what: 'Move the dials yourself' },
      { id: 'answers', what: 'Questions people actually ask' },
      { id: 'deeper', what: 'The override, priorities, the rest' },
    ],
  },
  {
    key: 'money',
    title: 'The money',
    who: 'How the town’s money actually moves',
    building: 'The flow diagrams and structural findings exist in the repository and do ' +
      'not have addresses here yet. Nothing has been written ahead of them.',
    items: [
      { id: 'reports', what: 'The analyses, with their workings' },
    ],
  },
  {
    key: 'data',
    title: 'The data',
    who: 'If you do not believe a number',
    items: [
      { id: 'sources', what: 'Every document, hashed' },
      { id: 'reports', what: 'What we wrote, kept separate' },
      { id: 'rates', what: 'Every rate, and who set it' },
    ],
  },
  {
    key: 'agents',
    title: 'For AI assistants',
    who: 'Pointing an assistant at this, or you are one',
    items: [
      { id: 'ask', what: 'The prompt to paste' },
      { id: 'agents', what: 'Every machine-readable address' },
    ],
  },
]

export function Home({ onJump }: { onJump: (t: Tab) => void }) {
  return (
    <div className="mx-auto max-w-5xl px-5 pb-16">
      <header className="pt-9 pb-7">
        <h1 className="text-[27px] sm:text-4xl font-bold tracking-tight leading-[1.1]">
          The <span style={{ color: 'var(--brand)' }}>Lunenburg</span> Budget Project
        </h1>
        <p className="mt-2.5 text-[15px] leading-snug" style={{ color: 'var(--text-secondary)' }}>
          Four ways in. Pick your depth.
        </p>
      </header>

      {DOORS.map(d => (
        <section key={d.key} className="border-t pt-5 pb-6"
          style={{ borderColor: 'var(--grid)' }}>
          <h2 className="text-[19px] font-bold tracking-tight">{d.title}</h2>
          <p className="text-[13.5px] mt-0.5" style={{ color: 'var(--text-muted)' }}>{d.who}</p>

          {d.building && (
            <p className="mt-3 text-[13px] leading-snug card p-3"
              style={{ color: 'var(--text-secondary)' }}>
              <strong style={{ color: 'var(--status-warning)' }}>Not built yet.</strong>{' '}
              {d.building}
            </p>
          )}

          {/* One column on a phone, two once there is room. The whole row is the hit
              target — a link-sized tap area on a touch screen is a design defect. */}
          <div className="grid gap-2 sm:grid-cols-2 mt-3.5">
            {d.items.map(it => (
              <button key={d.key + it.id} onClick={() => onJump(it.id)}
                className="card px-3.5 py-3 text-left w-full transition-opacity
                           hover:opacity-90 min-h-[44px]">
                <span className="text-[14.5px] font-bold block leading-tight">
                  {LABEL[it.id]}
                </span>
                <span className="block text-[12.5px] mt-0.5 leading-snug"
                  style={{ color: 'var(--text-secondary)' }}>{it.what}</span>
              </button>
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

import { useEffect, useState } from 'react'
import { Go } from '../lib/nav'
import { track } from '../lib/track'
import { useReport } from '../components/report'
import { Inline } from '../lib/inline'
import { type BlogPayload } from './Blog'
import type { Tab } from '../routes'
import { AREA_HOME, AREA_LABEL } from '../routes'
import { usdShort } from '../model/engine'
import { LEVEL_SERVICE } from '../model/walk'
import { DEFAULT_SCENARIO, nextYear, run } from '../model/rates'
import { BoardsThisWeek, BoardsStrip } from '../components/BoardsThisWeek'
import { RecentMeetings } from '../components/RecentMeetings'

/** The front page: the top-level doors and nothing else.
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

/** RECENT MEETINGS -- what we have for each, whatever that is. Replaces "What was said",
 *  which drew only the meetings that had our minutes and so could not show last night's
 *  meeting until its minutes were written. See components/RecentMeetings.tsx. */
function HomeRecentMeetings() {
  const { d } = useReport<{ counts: { meetings: number } }>('recording-minutes.json')
  return (
    <section aria-label="Recent meetings">
      <div className="flex items-baseline justify-between gap-3 mb-2">
        <h2 className="text-[13px] font-bold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>Recent meetings</h2>
        <Go to="recorded" className="text-[12px] underline"
          style={{ color: 'var(--series-cost)' }}>{d ? `all ${d.counts.meetings} with our minutes` : 'our minutes'} &rarr;</Go>
      </div>
      <RecentMeetings days={7} min={3} compact />
      <p className="text-[11px] mt-1.5" style={{ color: 'var(--text-muted)' }}>The last seven days of the three boards, with whatever exists for each: the recording, the agenda, the town&rsquo;s minutes, ours. A headline appears once our minutes are written.</p>
    </section>
  )
}

/** THE DOORS, RANKED.
 *
 *  They were five equal cards. A resident reading five equal cards has no way to know
 *  that the first is the one they came for; the walk on 15 September 2026 put it plainly:
 *  "The four doors have no ranking." So the set now has a shape:
 *
 *    1. The crisis, first and heavier, carrying THE NUMBER -- the projected gap -- so
 *       the door has information scent before anybody opens it. The front page never
 *       stated the one figure most likely to make somebody click.
 *    2. What the town can do about it, beside the crisis. TJ: "The point of the crisis
 *       page is not just cost to the tax payers. It's also insight to the board leaders.
 *       Hard decisions need to be made. They are looking for the solutions. The crisis
 *       page is the context." Context, then the answer to it, as a pair.
 *    3. The money, and the reports -- for the reader with a question of their own.
 *    4. The database and the assistant door, quiet, in one row: plumbing, not choices
 *       about the town.
 *
 *  The gap figure is READ FROM THE MODEL (rule 2), labelled as a projection (rule 7),
 *  and it is the same `LEVEL_SERVICE.gap` the crisis page's first card shows. */
const GAP_NOW = usdShort(LEVEL_SERVICE.gap)
const GAP_NEXT = usdShort(run(2, DEFAULT_SCENARIO)[1].gap)

type Door = { to: Tab; label: string; who: string; figure?: string; figureNote?: string; quiet?: boolean }
const DOORS: Door[] = [
  { to: AREA_HOME.crisis, label: AREA_LABEL.crisis,
    who: 'Why the budget keeps breaking, from the beginning',
    figure: `${GAP_NOW} short`, figureNote: `projected for FY${nextYear().fy}, ${GAP_NEXT} the year after` },
  { to: 'solutions', label: 'Solutions: what the town can do',
    who: 'Every option, what it closes, who decides it, and what it costs somebody' },
  { to: AREA_HOME.money, label: AREA_LABEL.money,
    who: 'Where every dollar comes from, and where the trail goes cold' },
  // Split out of `money` on 8 September at TJ's suggestion. The money door had grown
  // thirteen tabs behind it, which is a sitemap rather than an area. Named for the FORM
  // and not the subject -- it was `School analysis` for an hour, which would have made
  // the town-side reports homeless the moment one was written.
  { to: AREA_HOME.analyses, label: AREA_LABEL.analyses,
    who: 'The reports: staffing, athletics, fees, and what each one cannot say' },
  { to: AREA_HOME.data, label: AREA_LABEL.data, who: 'Every table, and how to check a figure', quiet: true },
  { to: AREA_HOME.agents, label: AREA_LABEL.agents, who: 'Pointing an assistant at this, or you are one', quiet: true },
]

function DoorCard({ d, lead }: { d: Door; lead?: boolean }) {
  return (
    <Go to={d.to} onClick={() => track('door', d.to)}
      className={'card block transition-opacity hover:opacity-90 '
        + (d.quiet ? 'px-4 py-3 min-h-[52px]' : lead ? 'px-5 py-5 min-h-[88px]' : 'px-4 py-4 min-h-[64px]')}
      style={d.quiet ? { background: 'transparent' }
        : lead ? { borderLeft: '4px solid var(--status-critical)' } : undefined}>
      <span className="flex items-baseline justify-between gap-3 flex-wrap">
        <span className={d.quiet ? 'text-[14.5px] font-bold leading-tight'
          : lead ? 'text-[20px] font-bold leading-tight' : 'text-[17px] font-bold leading-tight'}
          style={d.quiet ? { color: 'var(--text-secondary)' } : undefined}>
          {d.label} <span aria-hidden="true">&rarr;</span>
        </span>
        {d.figure && (
          <span className="text-[19px] font-bold tnum leading-none" style={{ color: 'var(--status-critical)' }}>{d.figure}</span>
        )}
      </span>
      <span className={d.quiet ? 'block text-[12.5px] mt-0.5 leading-snug' : 'block text-[13.5px] mt-1 leading-snug'}
        style={{ color: 'var(--text-muted)' }}>{d.who}</span>
      {d.figureNote && (
        <span className="block text-[11.5px] mt-1.5 tnum" style={{ color: 'var(--text-muted)' }}>{d.figureNote}</span>
      )}
    </Go>
  )
}

/** The sections, as one block, so the phone and the laptop can place it differently
 *  without two copies of it. */
function Doors() {
  const [lead, second, ...rest] = DOORS
  const loud = rest.filter(d => !d.quiet)
  const quiet = rest.filter(d => d.quiet)
  return (
    <div>
      <h2 className="text-[13px] font-bold uppercase tracking-widest mb-2" style={{ color: 'var(--text-muted)' }}>Understand the budget</h2>
      <div className="grid gap-2.5">
        <DoorCard d={lead} lead />
        <DoorCard d={second} />
        {loud.map(d => <DoorCard key={d.to} d={d} />)}
        {/* The plumbing, in one row and quieter, so the eye sorts it out of the set before
            reading it. Two doors in one row is the ranking made visible: half the width,
            half the weight. */}
        <div className="grid gap-2.5 sm:grid-cols-2 mt-1">
          {quiet.map(d => <DoorCard key={d.to} d={d} />)}
        </div>
      </div>

      {/* A FIFTH THING, and deliberately not a fifth DOOR.
          A door is a place to go and read; this is an invitation to say something, which
          is a different act. So it sits under the set, smaller and quieter, where it
          reads as an offer rather than as an option competing with the doors. */}
      <Go to="askus"
        className="mt-5 w-full block text-left px-4 py-3 min-h-[44px] rounded-lg
                   transition-opacity hover:opacity-80"
        style={{ border: '1px dashed var(--grid)', background: 'transparent' }}>
        <span className="text-[14.5px] font-bold" style={{ color: 'var(--series-cost)' }}>
          Ask us a question &rarr;
        </span>
        <span className="block text-[12.5px] mt-0.5 leading-snug"
          style={{ color: 'var(--text-muted)' }}>
          About the budget, or anything on this site. A person reads every one.
        </span>
      </Go>
    </div>
  )
}

function BudgetFeedCard() {
  return (
    <section aria-label="The budget feed">
      <div className="flex items-baseline justify-between gap-3 mb-2">
        <h2 className="text-[13px] font-bold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>This year&rsquo;s budget, as it is built</h2>
        <a className="text-[12px] underline" href="/budget-feed" style={{ color: 'var(--series-cost)' }}>FY28 &rarr;</a>
      </div>
      {/* A door, not a note: the same card the doors use, with an arrow, so it reads as
          a place to go. TJ: "make sure it looks clickable to navigate to a page."
          THE HEADING SAYS WHAT IT IS. It was "The budget feed", which is our name for
          it and not a thing a resident has heard of -- no information scent. What it is:
          this year's budget, followed as it is built. */}
      <a href="/budget-feed" className="card px-4 py-4 block transition-opacity hover:opacity-90" style={{ borderLeft: '4px solid var(--series-cost)' }}>
        <span className="text-[17px] font-bold leading-tight block" style={{ color: 'var(--series-cost)' }}>The FY28 budget feed <span aria-hidden="true">&rarr;</span></span>
        <span className="block text-[13.5px] mt-1 leading-snug" style={{ color: 'var(--text-muted)' }}>From the first deficit figure to Town Meeting: what is decided, what is still on the table, what has only been said.</span>
      </a>
      <p className="text-[11px] mt-1.5" style={{ color: 'var(--text-muted)' }}>Past years: <a className="underline" href="/budget-feed/fy27">FY27</a> · <a className="underline" href="/budget-feed/fy26">FY26</a> · <a className="underline" href="/budget-feed/fy27-summer-governors-budget">the summer of 2026</a></p>
    </section>
  )
}

export function Home() {
  return (
    <div className="mx-auto max-w-5xl px-5 pb-20">
      <header className="pt-10 pb-6">
        <h1 className="text-[27px] sm:text-4xl font-bold tracking-tight leading-[1.1]">
          The <span style={{ color: 'var(--brand)' }}>Lunenburg</span> Budget Project
        </h1>
        {/* ONE LINE THAT SAYS WHAT THE PAGE IS. TJ, on a phone: "probably need some above
            the fold context to smooth it". Not a paragraph: the three things the page
            holds, in the order they appear below. */}
        <p className="mt-2.5 text-[15px] leading-snug"
          style={{ color: 'var(--text-secondary)' }}>
          An independent tool for residents: why the school budget keeps breaking, what the
          town can do about it, and what its boards are deciding this week.
        </p>
        {/* THE SEARCH BOX, ON THE FRONT PAGE. TJ, 11 September, on seeing /search: "We
            need to put an indicator on the home page that users can search." The
            indicator is the box itself: a text field is the one affordance on the web
            that needs no label, and a sentence saying "you can search" would be weaker
            than the thing. It is not a door -- it goes to nowhere in particular -- so it
            sits with the header, above the set, and stays narrow. */}
        <form className="mt-4 flex gap-2"
          onSubmit={e => {
            e.preventDefault()
            const q = (new FormData(e.currentTarget).get('q') as string || '').trim()
            window.location.assign('/search' + (q ? '?q=' + encodeURIComponent(q) : ''))
          }}>
          <input name="q" type="search" aria-label="Search everything this project holds"
            placeholder="Search the budgets, the minutes, the meetings…"
            className="flex-1 min-w-0 px-3 py-2 text-[15px] rounded-lg border"
            style={{ background: 'var(--surface-2)', borderColor: 'var(--grid)',
                     color: 'var(--text-primary)' }} />
          <button type="submit" className="px-3.5 py-2 text-sm font-semibold rounded-lg shrink-0"
            style={{ background: 'var(--series-cost)', color: '#fff' }}>Search</button>
        </form>
      </header>

      {/* TWO COLUMNS BY TEMPO. Left is the map -- the doors, which change monthly. Right
          is the live column -- this year's budget as it is built, this week, what was
          said -- which changes daily.

          THE PHONE ORDER CHANGED ON 15 SEPTEMBER 2026. It was the live column first, on
          the argument that somebody on a phone in the evening is there for tonight's
          meeting. The walk as a first-time resident found the cost of that: a newcomer
          scrolls past a feed and a meeting they have no context for to find "start
          here". The doors now come first everywhere; the meeting regular knows to scroll,
          the newcomer does not. The feed keeps its place at the top of the live column
          (TJ, 14 September: "on the home page the budget feed should be at the top of
          the right sidebar"). */}
      <div className="grid gap-10 lg:grid-cols-[minmax(0,1fr)_minmax(0,24rem)] lg:items-start">
      <Doors />
      <div className="space-y-8">
        <BudgetFeedCard />
        <section aria-label="Meetings this week">
          <div className="flex items-baseline justify-between gap-3 mb-2">
            <h2 className="text-[13px] font-bold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>This week in town</h2>
            <Go to="thisweek" className="text-[12px] underline"
              style={{ color: 'var(--series-cost)' }}>every board &rarr;</Go>
          </div>
          <div className="lg:hidden"><BoardsStrip days={7} /></div>
          <div className="hidden lg:block"><BoardsThisWeek days={7} compact /></div>
          {/* THE DOOR TO THE BOARD PAGES. A resident who came to see when the School
              Committee meets next is the one who wants everything about it. */}
          <p className="text-[12px] mt-2" style={{ color: 'var(--text-secondary)' }}>
            Each board in one place: <a className="underline" href="/boards/school-committee">School Committee</a> · <a className="underline" href="/boards/select-board">Select Board</a> · <a className="underline" href="/boards/finance-committee">Finance Committee</a> · <a className="underline" href="/boards">all boards</a>
          </p>
        </section>
        <HomeRecentMeetings />
        <HomeLatest />
      </div>
      </div>

      {/* The "the walkthrough moved" note was here and is gone. It explained a
          change to somebody who had not seen the old page and could not have missed it,
          on the one page whose job is to be four choices. Every old address still
          resolves — `walk`, `walkthrough`, `start` and `start-here` are all aliases —
          so nobody arrives at a dead link and needs telling. */}

    </div>
  )
}

/** THE NEWEST PUBLISHED POST, and the offer that stands when there is not one yet.
 *
 *  WHAT CHANGED AND WHY. This used to draw three CARDS, chosen by a rule: the most
 *  recently changed new finding, the first myth, the first did-you-know that fitted. All
 *  three were items nobody had decided to publish, and the front page of a public tool is
 *  not where unreviewed copy belongs. So it shows the newest post that is actually up --
 *  and the payload it reads holds nothing else.
 *
 *  A PIN, BECAUSE THE NEWEST IS NOT ALWAYS THE ONE THAT MATTERS THIS WEEK. An item may
 *  carry `**Pin** — yes` in the candidates file and it takes this slot. A pin promotes a
 *  post that is already up; it does not put one up, and a pin on an unpublished item is
 *  simply not there to find.
 *
 *  AND NOTHING RATHER THAN A PLACEHOLDER. With nothing published there is no post and
 *  none is invented -- the section draws its heading and the one line under it, and that
 *  is TJ's actual request here: *"we have to keep the current 'doors' we have. This
 *  should be a new column or something on the home page that gives them another way in"*,
 *  *"an easier door"*.
 *
 *  IT RENDERS NOTHING UNTIL THE PAYLOAD ARRIVES. The front page is four doors and an
 *  offer; an error box where the offer was would be a worse front page than one without
 *  it, and there is no fallback copy to show because there is no copy here (rule 2). */
function HomeLatest() {
  const { d } = useReport<BlogPayload>('blog.json')
  // IN DEV ONLY, fall back to the drafts payload so the section can be SEEN with real
  // content before anything is published. TJ: "whats going to show on the homepage when we
  // post blogs? Id like to see how it looks". `import.meta.env.DEV` is replaced with
  // `false` in the production bundle, so this branch and the fetch inside it are
  // eliminated -- an unpublished post cannot reach a built page through here.
  // `useReport` prefixes `/data/`, so the drafts payload is fetched directly. The whole
  // branch is eliminated from the production bundle by `import.meta.env.DEV`.
  const [draft, setDraft] = useState<BlogPayload | null>(null)
  useEffect(() => {
    if (!import.meta.env.DEV) return
    let live = true
    fetch('/blog-all.json').then(r => (r.ok ? r.json() : null))
      .then(j => { if (live) setDraft(j) }).catch(() => {})
    return () => { live = false }
  }, [])
  if (!d) return null
  const live = d.posts.filter(p => p.published)
  let post = live.find(p => p.slug === d.pinned) ?? live[0] ?? null
  let preview = false
  if (!post && import.meta.env.DEV && draft?.posts?.length) {
    post = draft.posts[0]
    preview = true
  }

  // NOTHING PUBLISHED MEANS NOTHING ON THE PAGE -- not a heading over an empty space.
  // A section that announces itself and then shows nothing reads as broken, and TJ read it
  // exactly that way: "we need to cut the 'worth knowing' section on the home page. i think
  // thats stale." It was not stale; it was empty, which looks the same and is worse,
  // because it is the front page telling a stranger that something here is not working.
  if (!post) return null

  return (
    <section>
      {preview ? (
        <p className="text-[11px] font-semibold uppercase tracking-widest mb-2"
          style={{ color: 'var(--status-warning)' }}>
          Local preview &mdash; nothing is published; this is draft {post.n}
        </p>
      ) : null}
      <h2 className="text-[17px] font-bold tracking-tight">Latest articles</h2>
      <p className="text-[13.5px] mt-1 leading-snug" style={{ color: 'var(--text-muted)' }}>
        One finding at a time, in about two minutes, with the report behind it.
      </p>

      {post ? (
        <a href={`/blog/${post.slug}`}
          className="card block p-5 mt-4 transition-opacity hover:opacity-90">
          <span className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
            <span className="text-[11px] font-semibold uppercase tracking-widest"
              style={{ color: 'var(--text-secondary)' }}>{post.label}</span>
            <span className="text-[12.5px]" style={{ color: 'var(--text-muted)' }}>
              {post.reading.minutes} min read
            </span>
            {post.vintage === null ? (
              <span className="text-[12.5px]" style={{ color: 'var(--status-bad)' }}>
                Year not established
              </span>
            ) : (
              <span className="text-[12.5px]" style={{ color: 'var(--text-muted)' }}>
                {post.vintage_span
                  ? `FY${post.vintage_span[0]}\u2013FY${post.vintage_span[1]}`
                  : `FY${post.vintage}`}
              </span>
            )}
          </span>
          <span className="block text-[19px] font-bold leading-snug mt-2">
            <Inline text={post.headline} />
          </span>
          {post.support ? (
            <span className="block text-[14px] leading-snug mt-2"
              style={{ color: 'var(--text-secondary)' }}>
              <Inline text={post.support.split('. ')[0] + '.'} />
            </span>
          ) : null}
          <span className="block text-[13.5px] font-semibold mt-3"
            style={{ color: 'var(--series-cost)' }}>Read the post &rarr;</span>
        </a>
      ) : null}

      {d.counts.published > 1 ? (
        <p className="text-[13.5px] font-semibold mt-4">
          <a className="underline" style={{ color: 'var(--series-cost)' }} href="/blog">
            All {d.counts.published} &rarr;
          </a>
        </p>
      ) : null}
    </section>
  )
}

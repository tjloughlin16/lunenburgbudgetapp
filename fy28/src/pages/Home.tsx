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
import { THE_THREE } from '../components/BoardsThisWeek'
import { pending } from '../components/RecentMeetings'
import { ListSection, Row } from '../components/GroupedList'
import { todayIso, daysAway, dayLabel, splitMeetings, meetingTitle } from '../lib/meetings'

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
type HomeUpcoming = { board_slug: string; date: string; file_id: string; body_as_printed?: string | null }
type HomeFeed = { as_of: string; upcoming: { meetings: HomeUpcoming[] } }
type HomeNotices = { upcoming: { board_slug: string; date: string; time?: string; hook?: string; one_line: string }[] }

/** One section of the live column, as data, so it can be drawn two ways: as its own
 *  grouped list on a wide screen, and as one tab of a SEGMENTED CONTROL on a phone. */
type Pane = { tab: string; title: string; all?: string; allHref?: string; label: string; rows: React.ReactNode }

/** The board's likely next meeting, from boards.json (meeting_cadence.py). */
type HomeLikely = { slug: string; likely_next?: { show: boolean; dates: string[]; time?: string | null; rule: string | null
  backtest: { made: number; exact: number } } | null }

function useThisWeek(): Pane | null {
  const feed = useReport<HomeFeed>('meeting-feed.json').d
  const notices = useReport<HomeNotices>('notices.json').d
  const boards = useReport<{ boards: HomeLikely[] }>('boards.json').d
  if (!feed) return null
  const rows: { name: string; m: HomeUpcoming; time?: string; line?: string }[] = []
  const quiet: string[] = []
  const likely: { name: string; slug: string; date: string; l: NonNullable<HomeLikely['likely_next']> }[] = []
  for (const [slug, name] of THE_THREE) {
    const ms = feed.upcoming.meetings
      .filter(m => m.board_slug === slug && m.date >= todayIso() && daysAway(m.date) <= 7)
      .sort((a, b) => a.date.localeCompare(b.date))
    // NOTHING POSTED: the board's likely next meeting, if it falls this week and clears our
    // threshold (TJ, 19 October 2026) -- drawn as an estimate, never as a notice. A board
    // with ANY future posting gets none, the rule the board pages keep.
    const posted = feed.upcoming.meetings.some(m => m.board_slug === slug && m.date >= todayIso())
    const l = boards?.boards.find(x => x.slug === slug)?.likely_next
    const guess = !posted && l?.show ? l.dates.find(x => x >= todayIso()) : undefined
    if (guess && daysAway(guess) <= 7) { likely.push({ name, slug, date: guess, l: l! }); continue }
    if (!ms.length) quiet.push(name)
    for (const m of ms) {
      const p = notices?.upcoming.find(u => u.board_slug === m.board_slug && u.date === m.date)
      rows.push({ name, m, time: p?.time && p.time !== 'not stated' ? p.time : undefined, line: p?.hook || p?.one_line })
    }
  }
  rows.sort((a, b) => a.m.date.localeCompare(b.m.date))
  return {
    tab: 'This week', title: 'This week in town', all: 'Every board', allHref: '/this-week', label: 'Meetings this week',
    rows: <>
      {rows.map(({ name, m, time, line }) => (
        <Row key={m.file_id} href={`/this-week#m-${m.board_slug}-${m.date}`} accent
          eyebrow={dayLabel(m.date, feed.as_of) + (time ? ` · ${time}` : '')}
          title={meetingTitle(name, m.body_as_printed)} sub={line} />
      ))}
      {likely.map(({ name, slug, date, l }) => (
        <Row key={`likely-${slug}`} href={`/boards/${slug}`} estimate tag="our estimate"
          eyebrow={`Likely ${dayLabel(date, feed.as_of)}${l.time ? ` · ${l.time}` : ''}`}
          title={name}
          sub={`Nothing posted yet. It usually meets ${l.rule?.startsWith('every') ? l.rule : `on the ${l.rule}`}; this guess was right ${l.backtest.exact} of ${l.backtest.made} times last year.`} />
      ))}
      {quiet.length > 0 && <Row title={`${quiet.join(' and ')}: nothing posted this week`} muted />}
    </>,
  }
}

function useThreads(): Pane | null {
  const { d } = useReport<{ threads: { status: string; is_new: boolean; label: string; id: string; generated?: string }[] }>('threads.json')
  if (!d) return null
  // A GENERATED thread (a town meeting, a warrant article) is not counted here, as /threads
  // does not count it: the meeting has its own line above this list (TownMeetingNow).
  const open = d.threads.filter(t => t.status === 'open' && !t.generated)
  return {
    tab: 'Threads', title: 'Open threads', all: `All ${open.length}`, allHref: '/threads', label: 'Open threads',
    rows: open.slice(0, 3).map(t => (
      <Row key={t.id} href={`/threads/${t.id}`} title={t.label} tag={t.is_new ? 'new' : undefined} />
    )),
  }
}

// `body_as_printed`: the town files some other bodies' agendas under a board -- the School
// Advisory Councils sit under School Committee -- so the title is what the agenda calls itself.
type HomeRecent = {
  date: string; ours?: { slug: string; headline?: string; votes?: number } | null
  video_url?: string | null; captions_disabled?: boolean; body_as_printed?: string | null
  record?: { video?: { likely_none?: boolean } } | null
}
type HomeBoards = { boards: { slug: string; name: string; the_three?: boolean; meetings: HomeRecent[] }[] }

const cap = (t: string) => t.charAt(0).toUpperCase() + t.slice(1)

function useRecentMeetings(): Pane | null {
  const { d } = useReport<HomeBoards>('boards.json')
  const idx = useReport<{ counts: { meetings: number } }>('recording-minutes.json').d
  if (!d) return null
  const rows = d.boards.filter(b => b.the_three)
    .flatMap(b => splitMeetings(b.meetings).past.map(r => ({ board: b.name, slug: b.slug, r })))
    .sort((a, b) => b.r.date.localeCompare(a.r.date)).slice(0, 3)
  const when = (iso: string) => {
    const [y, m, dd] = iso.split('-').map(Number)
    return new Date(y, m - 1, dd).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })
  }
  return {
    tab: 'Past meetings', title: 'Recent meetings', all: idx ? `All ${idx.counts.meetings}` : 'All',
    allHref: '/what-was-said', label: 'Recent meetings',
    rows: rows.map(({ board, slug, r }) => (
      <Row key={slug + r.date}
        href={r.ours ? `/meeting-minutes/${r.ours.slug}` : `/boards/${slug}`}
        eyebrow={when(r.date) + (r.ours && typeof r.ours.votes === 'number'
          ? ` · ${r.ours.votes} vote${r.ours.votes === 1 ? '' : 's'}` : '')}
        title={meetingTitle(board, r.body_as_printed)} sub={r.ours?.headline ?? cap(pending(r))} />
    )),
  }
}

/** THE LIVE COLUMN: three sections, drawn two ways.
 *
 *  Wide screen: three grouped lists, stacked -- there is room, and a sidebar is scanned.
 *  Phone: ONE card with a segmented control on top. TJ, 13 October 2026, on the stacked
 *  version: "it's a lot of scrolling across different sections with big panels". Three
 *  sections become one, the page gets shorter by two cards, and every row is still one
 *  tap away. The first tab is the one that changes week to week. */
function HomeLive() {
  const panes = [useThisWeek(), useRecentMeetings(), useThreads()].filter((p): p is Pane => !!p)
  const [i, setI] = useState(0)
  if (!panes.length) return null
  const cur = panes[Math.min(i, panes.length - 1)]
  return (
    <>
      <div className="hidden lg:block space-y-8">
        {panes.map(p => (
          <ListSection key={p.tab} title={p.title} all={p.all} allHref={p.allHref} label={p.label}>{p.rows}</ListSection>
        ))}
      </div>
      <section className="lg:hidden" aria-label="In town">
        <div role="tablist" aria-label="In town" className="flex p-0.5 mb-2 rounded-lg"
          style={{ background: 'var(--surface-3)' }}>
          {panes.map((p, k) => {
            const on = p === cur
            return (
              <button key={p.tab} role="tab" aria-selected={on} type="button"
                onClick={() => setI(k)}
                className="flex-1 min-h-[36px] rounded-md text-[13px] font-semibold transition-colors"
                style={on
                  ? { background: 'var(--surface-1)', color: 'var(--text-primary)', boxShadow: '0 1px 2px rgba(0,0,0,.12)' }
                  : { color: 'var(--text-muted)' }}>
                {p.tab}
              </button>
            )
          })}
        </div>
        <ul role="tabpanel" className="card overflow-hidden" style={{ padding: 0 }}>{cur.rows}</ul>
        {cur.all && cur.allHref && (
          <a href={cur.allHref} className="mt-1.5 block text-right px-1 text-[13px] font-semibold"
            style={{ color: 'var(--series-cost)' }}>
            {cur.all} <span aria-hidden>&rsaquo;</span>
          </a>
        )}
      </section>
    </>
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
/** THE FRONT PAGE SEARCH BOX, OFF. TJ, 19 September 2026: "lets 'hide' the search bar for
 *  now. I want to try that. Maybe search is too prominent right now. we DO have the
 *  magnifying glass in the header." And, on seeing it commented out: "dont CUT it. just
 *  hide for now."
 *
 *  So it is a flag, not a comment block and not a deletion. The component below stays
 *  live, typechecked and rendered by one word — an experiment you can reverse without
 *  reading a diff to find out what was removed.
 *
 *  The box went in on 11 September for a good reason: "We need to put an indicator on the
 *  home page that users can search", and a text field is the one affordance on the web
 *  that needs no label. What changed is not the argument but the page around it — the
 *  header carries a magnifying glass on every page, so the indicator exists without
 *  spending the front page's most valuable inches on a tool. */
const SHOW_SEARCH = false

const GAP_NOW = usdShort(LEVEL_SERVICE.gap)
const GAP_NEXT = usdShort(run(2, DEFAULT_SCENARIO)[1].gap)

type Door = { to: Tab; href?: string; label: string; who: string; figure?: string; figureNote?: string; quiet?: boolean }
const DOORS: Door[] = [
  // THE HUB, NOT THE WALKTHROUGH, since 18 October 2026: /crisis is the Budget crisis hub
  // (scripts/topic_registry/crisis.py), which is a topic page and has no Tab of its own --
  // so this door carries its address. `to` still names the area for the click count.
  { to: AREA_HOME.crisis, href: '/crisis', label: AREA_LABEL.crisis,
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
  // The reports door left this list on 13 October 2026 for a block of its own -- see
  // <ReportsShelf />. TJ: "it doesnt look like a swath of info on the home page".
  { to: AREA_HOME.data, label: AREA_LABEL.data, who: 'Every table, and how to check a figure', quiet: true },
  { to: AREA_HOME.agents, label: AREA_LABEL.agents, who: 'Pointing an assistant at this, or you are one', quiet: true },
]

function DoorCard({ d, lead, sub }: { d: Door; lead?: boolean; sub?: boolean }) {
  return (
    <DoorLink d={d}
      className={'card block transition-opacity hover:opacity-90 '
        + (d.quiet ? 'px-4 py-3 min-h-[52px]' : lead ? 'px-5 py-5 min-h-[88px]'
          : sub ? 'px-3.5 py-2.5 min-h-[44px]' : 'px-4 py-4 min-h-[64px]')}
      style={d.quiet ? { background: 'transparent' }
        : lead ? { borderLeft: '4px solid var(--status-critical)' } : undefined}>
      <span className="flex items-baseline justify-between gap-3 flex-wrap">
        <span className={d.quiet ? 'text-[14.5px] font-bold leading-tight'
          : lead ? 'text-[20px] font-bold leading-tight'
          : sub ? 'text-[15px] font-bold leading-tight' : 'text-[17px] font-bold leading-tight'}
          style={d.quiet ? { color: 'var(--text-secondary)' } : undefined}>
          {d.label} <span aria-hidden="true">&rarr;</span>
        </span>
        {d.figure && (
          <span className="text-[19px] font-bold tnum leading-none" style={{ color: 'var(--status-critical)' }}>{d.figure}</span>
        )}
      </span>
      <span className={d.quiet || sub ? 'block text-[12.5px] mt-0.5 leading-snug' : 'block text-[13.5px] mt-1 leading-snug'}
        style={{ color: 'var(--text-muted)' }}>{d.who}</span>
      {d.figureNote && (
        <span className="block text-[11.5px] mt-1.5 tnum" style={{ color: 'var(--text-muted)' }}>{d.figureNote}</span>
      )}
    </DoorLink>
  )
}

/** A door with an `href` is a plain link -- a topic hub has an address and no Tab, and Go
 *  would route its click to the Tab instead. */
function DoorLink({ d, children, ...rest }: { d: Door; children: React.ReactNode }
  & React.AnchorHTMLAttributes<HTMLAnchorElement>) {
  const click = () => track('door', d.to)
  return d.href
    ? <a href={d.href} onClick={click} {...rest}>{children}</a>
    : <Go to={d.to} onClick={click} {...rest}>{children}</Go>
}

type Shelf = { id: string; shelf: string; path: string; area: string; order: number; ready: boolean
  groups: { topics: string[] }[] }
type Shelves = { categories: Shelf[]; areas: { id: string; title: string }[]; topics: Record<string, { ready: boolean }> }

/** REPORTS: TOWN AND SCHOOLS -- the largest thing this site holds, drawn as what it is.
 *
 *  It was one door among five ("Analysis: Town and Schools"), the same size as the door to
 *  the database. TJ, 13 October 2026: "we probably need to call it 'Reports: Town and
 *  Schools' or something that screams that there is a ton of data, and pull it out of the
 *  inline list and make it sort of one of the main things people land in". So it is its
 *  own block: the count first (the breadth IS the message), then every subject as a link,
 *  grouped the way /reports groups them. Read from topics.json, the file /reports and every
 *  hub read, so a new subject appears here the day it is built and the count cannot drift. */
function ReportsShelf() {
  const { d } = useReport<Shelves>('topics.json')
  const cats = (d?.categories ?? []).filter(c => c.ready).length
  const pages = d ? Object.values(d.topics).filter(t => t.ready).length : null
  // ONE BUTTON, NOT A LIST. The first version drew all sixteen subjects as chips under the
  // count; TJ, on a phone: "SUPER overwhelming... we need a Reports button that just
  // suggests its a deeper page". The depth is said by the count and drawn by the two
  // offset sheets behind the card -- a stack, the shape of "there is more under this".
  return (
    <div className="relative mb-2.5 mr-2" style={{ marginTop: 2 }}>
      <span aria-hidden className="absolute inset-0 rounded-[10px]"
        style={{ transform: 'translate(8px, 8px)', background: 'var(--surface-2)', border: '1px solid var(--grid)' }} />
      <span aria-hidden className="absolute inset-0 rounded-[10px]"
        style={{ transform: 'translate(4px, 4px)', background: 'var(--surface-2)', border: '1px solid var(--grid)' }} />
      <Go to={AREA_HOME.analyses} onClick={() => track('door', AREA_HOME.analyses)}
        className="card relative block px-5 py-5 min-h-[88px] transition-opacity hover:opacity-95"
        style={{ borderLeft: '4px solid var(--brand)' }}>
        <span className="flex items-baseline justify-between gap-3 flex-wrap">
          <span className="text-[20px] font-bold leading-tight">
            Reports: Town and Schools <span aria-hidden="true">&rarr;</span>
          </span>
          {pages != null && (
            <span className="text-[19px] font-bold tnum leading-none" style={{ color: 'var(--brand)' }}>
              {pages} reports
            </span>
          )}
        </span>
        <span className="block text-[13.5px] mt-1 leading-snug" style={{ color: 'var(--text-muted)' }}>
          {cats ? `${cats} subjects, schools and town. ` : ''}Each one a short page with its chart and its sources.
        </span>
      </Go>
    </div>
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
        {/* SOLUTIONS AND THE MONEY HANG FROM THE CRISIS. TJ, 13 October 2026: "put the
            SOLUTIONS and the money as big sub bullets under 'budget crisis'". They are the
            two follow-on questions to the gap -- what can be done, where the money goes --
            so they are drawn as its children: indented under it, on a rule in its colour.
            Reports is a different kind of door and stands on its own after them. */}
        <div className="grid gap-2 ml-4 pl-3" style={{ borderLeft: '2px solid var(--status-critical)' }}>
          <DoorCard d={second} sub />
          {loud.map(d => <DoorCard key={d.to} d={d} sub />)}
        </div>
        <div className="mt-2"><ReportsShelf /></div>
      </div>

      <div className="grid gap-2.5 mt-3">
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

/** WHAT THE TOWN IS DECIDING NOW — the door to /threads.
 *
 *  IT SAYS "OPEN THREADS", WHICH IS OUR WORD, AND THAT IS A DELIBERATE EXCEPTION.
 *  READING-FLOW warns against "a door without scent" and this project made that mistake
 *  once already by labelling a door "the budget feed". The difference here is that the
 *  destination teaches the word: every card on /threads is one, they are drawn as threads
 *  at the foot of the page, and "open" carries the state on its own. TJ, 19 September
 *  2026, having read the alternatives: "Lets just call it 'Open Threads'".
 *
 *  It sits in the live column under the budget feed, which is the right relation between
 *  them: the budget season is the one matter that always exists and is itemised every
 *  year, and these are the ones that come and go. */

function BudgetFeedCard() {
  return (
    <ListSection title={"This year\u2019s budget"} all="Past years" allHref="/budget-feed/fy27" label="The budget feed">
      <Row href="/budget-feed" accent eyebrow="Being built now" title="The FY28 budget feed"
        sub="What is decided, what is still on the table, what has only been said." />
    </ListSection>
  )
}

/** A TOWN MEETING, FROM THE DAY IT IS KNOWN UNTIL A WEEK AFTER IT. TJ, 21 October 2026:
 *  "once a town meeting thread upcoming has been identified (boards have started discussing
 *  it or the warrant opens), a link on the home page for a week after the town meeting
 *  should show up ... ABOVE the board 'this week' list". Known = the Select Board called it
 *  or its warrant opened, whichever the record shows first (build_town_meetings.py); the
 *  line goes by itself TM_AFTER_DAYS after the meeting. Nothing when no meeting is near. */
const TM_AFTER_DAYS = 7
type TmWarrant = { meeting: string; date: string; kind: string; status: string; called_on?: string
  warrant_opens?: string; warrant_closes?: string; articles?: unknown[] }
function TownMeetingNow() {
  const { d } = useReport<{ threads: { id: string; kind?: string; label: string; warrant?: TmWarrant }[] }>('threads.json')
  if (!d) return null
  const today = todayIso()
  const live = d.threads.filter(t => {
    const w = t.kind === 'town-meeting' ? t.warrant : undefined
    if (!w?.date) return false
    const known = [w.called_on, w.warrant_opens].filter((x): x is string => !!x).sort()[0]
    return !!known && known <= today && daysAway(w.date) >= -TM_AFTER_DAYS
  }).sort((a, b) => (a.warrant!.date < b.warrant!.date ? -1 : 1))
  if (!live.length) return null
  return (
    <ListSection title="Town Meeting" label="Town Meeting">
      {live.map(t => {
        const w = t.warrant!
        const n = w.articles?.length ?? 0
        const away = daysAway(w.date)
        const kind = w.kind === 'annual' ? 'Annual Town Meeting' : 'Special Town Meeting'
        const sub = away >= 0
          ? `${away === 0 ? 'Today' : away === 1 ? 'Tomorrow' : `In ${away} days`} \u00b7 ${n} article${n === 1 ? '' : 's'} so far \u00b7 where each one stands`
          : `Held \u00b7 how each of the ${n} articles was voted`
        return <Row key={t.id} href={`/threads/${t.id}`} eyebrow={dayLabel(w.date)} title={kind} sub={sub} accent />
      })}
    </ListSection>
  )
}

type Hottest = {
  as_of: string; window_days: number
  threads: { id: string; label: string; short: string; hook?: string; meetings: number; boards: number; days_since_last: number }[]
}

/** 🔥 HOT IN TOWN -- one line above everything, and nothing at all when nothing is hot.
 *
 *  TJ, 19 October 2026: *"a sort of thin headline to dynamically call out the HOTTEST topic
 *  in town ... dont make it a big bubble block like the reports and crisis. just something
 *  to attract people to click"*; *"it should be populated and removed when there is no hot
 *  topic"*. So: no card, no figure, a line of links.
 *
 *  THE PICK IS NOT MADE HERE. `hottest` in threads.json is computed by build_threads.py from
 *  the same rule as the 🔥 badge on /threads, and the daily refresh rebuilds it. The counts
 *  that make each one hot are in its tooltip -- the badge's own words.
 *
 *  A WEEK-OLD FIRE IS NOT NEWS. `hot` is relative to the day the payload was built, so if
 *  the refresh stops the strip removes itself rather than going on calling stale talk hot. */
const HOT_SHOWN = 3
function HotInTown() {
  const { d } = useReport<{ hottest?: Hottest }>('threads.json')
  const h = d?.hottest
  if (!h || !h.threads.length) return null
  const age = (Date.parse(todayIso()) - Date.parse(h.as_of)) / 86400000
  if (!(age <= 7)) return null
  const shown = h.threads.slice(0, HOT_SHOWN)
  const more = h.threads.length - shown.length
  return (
    <p className="text-[13.5px] leading-snug mb-5 flex flex-wrap items-baseline gap-x-2 gap-y-1">
      <span className="text-[11px] font-bold uppercase tracking-widest shrink-0"
        style={{ color: 'var(--status-critical)' }}>
        <span aria-hidden="true">🔥</span> Hot in town
      </span>
      {shown.map((t, i) => (
        <span key={t.id}>
          <a href={`/threads/${t.id}`} onClick={() => track('door', 'hot:' + t.id)}
            className="font-semibold underline decoration-1 underline-offset-2"
            title={`${t.label}: ${t.meetings} meetings across ${t.boards} boards in the last ${h.window_days} days`}>
            {t.short}
          </a>
          {/* THE HOOK -- "$1M–$4M to demolish" -- where the thread has a checked callout. */}
          {t.hook ? <span style={{ color: 'var(--text-secondary)' }}>: {t.hook}</span> : null}
          {i < shown.length - 1 || more > 0
            ? <span aria-hidden="true" style={{ color: 'var(--text-muted)' }}> ·</span> : null}
        </span>
      ))}
      {more > 0 ? (
        <a href="/threads" className="underline decoration-1 underline-offset-2"
          style={{ color: 'var(--text-muted)' }}>{more} more</a>
      ) : null}
    </p>
  )
}

/** NEW FROM DESE -- a grant newly open to districts, or an award list that names Lunenburg
 *  or a comparison district. One thin line, like Hot in town, and nothing when there is none.
 *
 *  TJ, 23 October 2026: *"if a grant shows up that's new, or an award, we need to call that on
 *  the homepage too, as sort of a notification."* The detection is NOT made here:
 *  watch_grants.py reads the held DESE snapshots, freezes each notice the day it is first
 *  seen, and build_notices.py publishes the live ones with an `expires` date. The page drops a
 *  notice past that date itself, so a stopped refresh cannot leave an old grant called new. */
type GrantNotice = { kind: 'grant' | 'award'; first_seen: string; expires: string; text: string
  href: string; source_url: string }
const GRANTS_SHOWN = 3
/** The day OUR fetcher landed it -- DESE prints no posting date for either kind. */
const shortDate = (iso: string) => {
  const [y, m, dd] = iso.split('-').map(Number)
  return new Date(y, m - 1, dd).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}
function NewFromDese() {
  const { d } = useReport<{ grants?: GrantNotice[] }>('notices.json')
  const live = (d?.grants ?? []).filter(n => n.expires >= todayIso())
  if (!live.length) return null
  const shown = live.slice(0, GRANTS_SHOWN)
  return (
    <div className="text-[13.5px] leading-snug mb-5">
      <span className="text-[11px] font-bold uppercase tracking-widest"
        style={{ color: 'var(--brand)' }}>New from the state</span>
      <ul className="mt-1 space-y-1">
        {shown.map(n => (
          <li key={n.kind + n.href + n.text}>
            <a href={n.href} onClick={() => track('door', 'dese:' + n.kind)}
              className="font-semibold underline decoration-1 underline-offset-2">{n.text}</a>
            <span className="text-[12px]" style={{ color: 'var(--text-muted)' }}>
              {' '}· we found it {shortDate(n.first_seen)} · <a href={n.source_url} target="_blank"
                rel="noreferrer" className="underline">DESE</a>
            </span>
          </li>
        ))}
      </ul>
      {live.length > shown.length && (
        <a href="/grants-open-to-lunenburg" className="text-[12.5px] underline"
          style={{ color: 'var(--text-muted)' }}>{live.length - shown.length} more</a>
      )}
    </div>
  )
}

export function Home() {
  return (
    <div className="mx-auto max-w-5xl px-5 pb-20">
      <header className="pt-10 pb-6">
        <HotInTown />
        <NewFromDese />
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
        {/* THE GROUP, UNDER THE STANDFIRST. It has been a sentence, a chip, a quiet link,
            a filled button in the title row, and is now a plain link near where it
            started — each move answering a real objection, and the last one only possible
            because THE SEARCH BOX IS GONE. What made this awkward was never the styling:
            it was sitting an inch from another button and reading as a second submit.
            With no form on the page there is nothing left to be mistaken for, so it needs
            no weight of its own to stay distinct.

            TJ: "No bold background. But use 'Join us on facebook'". The mark and the words
            both take Facebook's blue, which says where it goes without a filled block
            shouting it. */}
        <a href="https://www.facebook.com/share/g/1DvbEb9wnW/"
          target="_blank" rel="noreferrer noopener"
          className="mt-3 inline-flex items-center gap-1.5 text-[14px] font-semibold"
          style={{ color: '#1877F2' }}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
            <path d="M22 12.06C22 6.5 17.52 2 12 2S2 6.5 2 12.06C2 17.08 5.66 21.24 10.44 22v-7.03H7.9v-2.91h2.54V9.85c0-2.52 1.49-3.91 3.77-3.91 1.09 0 2.24.2 2.24.2v2.46h-1.26c-1.24 0-1.63.78-1.63 1.57v1.89h2.78l-.44 2.91h-2.34V22C18.34 21.24 22 17.08 22 12.06z"/>
          </svg>
          Join us on Facebook
        </a>

        {/* THE SEARCH BOX, ON THE FRONT PAGE. TJ, 11 September, on seeing /search: "We
            need to put an indicator on the home page that users can search." The
            indicator is the box itself: a text field is the one affordance on the web
            that needs no label, and a sentence saying "you can search" would be weaker
            than the thing. It is not a door -- it goes to nowhere in particular -- so it
            sits with the header, above the set, and stays narrow. */}
        {SHOW_SEARCH && (
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
        )}
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
      {/* WHO MADE THIS, ABOVE THE DOORS. TJ: "a very very short top section above
          understand the budget but below FB link for ABOUT. Just a sentence or two, then
          link to about. You were right. we need that."

          TWO SENTENCES AND A LABEL, and the sentences earn their place where the link's
          did not: a reader deciding whether to trust four doors into a town's finances is
          owed who built them before they pick one. That is descriptive by nature, which is
          the test READING-FLOW sets. The LINK stays a label. */}
      {/* ONE GRID CHILD, NOT TWO. This section and <Doors /> are the left column
          together, and leaving them as separate children of a two-column grid put
          "Who made this" in column one, the doors in column TWO, and everything after
          them on row two -- which starts below the taller of the pair. On a desktop that
          was ~400px of dead space under four lines of text, and the live column ended up
          on the left, which is the opposite of what it is for. */}
      <div>
      <section aria-label="Who made this" className="mb-7 max-w-2xl">
        {/* The label the other sections have. Without it this read as loose text floating
            above the doors rather than a part of the page. "Who made this" rather than
            "About this project", so the heading and the link underneath are not the same
            four words twice. */}
        <h2 className="text-[13px] font-bold uppercase tracking-widest mb-2"
          style={{ color: 'var(--text-muted)' }}>Who made this</h2>
        <p className="text-[14px] leading-snug" style={{ color: 'var(--text-secondary)' }}>
          This is built by one resident, from the town's and the district's own documents —
          what they publish, and what comes back from records requests. Every figure is
          meant to be traceable to the page it came from.
        </p>
        <a className="mt-1.5 inline-block text-[13px] font-semibold underline"
          href="/about" style={{ color: 'var(--series-cost)' }}>About this project</a>
      </section>

      <Doors />
      </div>

      <div className="space-y-8">
        {/* A DIFFERENT KIND OF SECTION, AND IT SAYS SO. TJ, 13 October 2026: the doors are
            things to read once; everything below is what changes week to week. Without a
            heading of its own the column read as more doors. A rule and a bigger title
            mark the change of register; the small labels under it stay as they were. */}
        <header className="border-t pt-6 lg:border-t-0 lg:pt-0" style={{ borderColor: 'var(--grid)' }}>
          <h2 className="text-[22px] font-bold tracking-tight leading-tight">Stay informed</h2>
          <p className="text-[14px] mt-0.5" style={{ color: 'var(--text-secondary)' }}>
            What the boards are deciding, this week and lately.
          </p>
        </header>
        <BudgetFeedCard />
        <TownMeetingNow />
        <HomeLive />
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
        /* SOMETHING TO READ: A RULE ACROSS THE TOP, no left edge.
         *
         * The third member of the card system TJ asked for on 25 September 2026 -- *"esp
         * beteween upcoming meetings and recent, and then diff for reports"*. The EDGE'S
         * POSITION carries the kind, so the three stay apart in greyscale and for a reader
         * who cannot separate the hues:
         *
         *   a meeting you can still attend   LEFT edge, blue   (BoardsThisWeek)
         *   a meeting that has happened      no edge, tinted   (RecentMeetings)
         *   something to read                TOP rule          (here)
         *
         * `report.tsx` already uses a top rule for a card that has no headline figure, so
         * this is the existing vocabulary rather than a fourth idea. */
        <a href={`/blog/${post.slug}`}
          className="card block p-5 mt-4 transition-opacity hover:opacity-90"
          style={{ borderTop: '3px solid var(--series-revenue)' }}>
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

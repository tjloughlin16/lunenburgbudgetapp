import { useEffect, useMemo, useState } from 'react'
import { threadIdFromPath, type Tab } from '../routes'
import { Body, H2, H3, NotShown, ReportShell, Stat, useReport } from '../components/report'
import { meetingTitle } from '../lib/meetings'
import { Basis, type Level } from '../components/Basis'
import { Note } from '../components/primitives'
import { ThreadRibbons } from '../components/ThreadRibbons'
import { ThreadsHero } from '../components/ThreadsHero'
import { ThreadKind, KINDS, KIND_LABEL } from '../components/ThreadKind'
import { HotBadge, ThreadHeat, Tangled, type Heat } from '../components/ThreadHeat'
import { DynamicThread } from '../components/DynamicThread'

const TAB: Tab = 'threads'
const DATA = 'threads.json'

/** THREADS — a matter tracked across meetings and boards to a decision.
 *
 *  `/threads` is the landing page; `/threads/<id>` is one thread. The design is
 *  notes/process/THREADS-MODEL.md; the payload is scripts/build_threads.py. Nothing about
 *  a vote is written here or in the registry — a closure is a reference and the motion,
 *  the outcome and the tally are resolved from the record (§18).
 *
 *  TWO THINGS THIS PAGE MUST NOT DO, both of which it would do by default:
 *
 *  1. SHOW A CAPTION-DERIVED TALLY AS THOUGH IT WERE THE CLERK'S. Every closure states
 *     its basis. `ours` is our minutes of a recording, written by a model from machine
 *     captions that mishear numbers; `official` is the Town Clerk's printed proceedings.
 *     The first carries its caveat visibly, every time, however short the card gets.
 *  2. PUT `lapsed` NEXT TO `resolved`. A matter nobody decided is not a matter that was
 *     settled, and mixing them is the single most misleading thing here (§14c). */

type Closure = {
  basis: 'official' | 'ours'; source: string; meeting: string; date: string; article: string
  result: string; amount_as_printed: string; quote: string; fincom: string; select_board: string
  document: string; page: string; caveat: string
}
/** `source`: `town` is the town's own minutes, with the sentence quoted from them; `ours` is
 *  our minutes of the recording, from machine captions, cited to the second. */
type Item = {
  kind: string; text: string; outcome: string; t: number | null; video_url: string
  source?: 'town' | 'ours' | 'caption'; quote?: string; doc_url?: string; town_url?: string
}
/** An upcoming (or just-past) agenda item matched to this thread by build_agenda_threads.py. */
type OnAgenda = {
  board: string; board_slug: string; date: string; body_as_printed: string; upcoming: boolean
  line: string; parent: string; by: 'words' | 'board'; agenda_url: string; agenda_doc: string
}
type Item2 = Item & { board: string; board_slug: string; date: string }
type Stop = { board: string; board_slug: string; date: string; items: Item[] }
type Thread = {
  id: string; label: string; question: string; kind: string; groups: string; tags: string
  boards: string; started: string; closes: string; status: string; resolved_on: string; caveat: string
  reports: { title: string; url: string }[]
  /** Reports the meetings asked for that would serve this thread (build_suggested_reports.py).
   *  `status: 'new'` is not written yet; `exists` has a page. `how`: the model named this thread,
   *  the thread's own words found it, or both. */
  reports_needed?: ReportNeeded[]
  heat: Heat; stage: string; tangled: boolean; is_new: boolean; registered_on: string
  hot?: boolean
  stands: { vote: Item2 | null; decision: Item2 | null; any: Item2 | null }
  momentum: { meetings: number; boards: number; votes: number; days_since_last: number; span_days: number; meetings_last_90: number; board_meetings_since: number; meetings_last_30?: number; boards_last_30?: number }
  closure: Closure | null; chronology: Stop[]; meetings: number; boards_touched: number
  first_seen: string; last_moved: string; weight: number
  /** A person's call that this leads the page, in this order (threads.csv `pin`). */
  pin: number | null
  on_agenda?: OnAgenda[]
}
type ReportNeeded = {
  title: string; slug: string; status: 'new' | 'exists'; url: string; question: string; how: string
  meetings: { date: string; board: string; fiscal_year: string; question_then: string; watch_at: string; at: string; our_minutes: string }[]
}
type Declined = { candidate: string; declined_on: string; reason: string; revisit_if: string; note: string }
type Payload = {
  about: string
  coverage: {
    rank_basis: string; meetings_readable: number; boards_readable: number
    town_meeting_readable: number; official_town_meeting_years: string[]
    agendas_as_of?: string
    dated_in_the_future_and_excluded: { board: string; date: string; file: string }[]
  }
  threads: Thread[]; declined: Declined[]
}

/** THE GROUPS ARE THE READER'S, NOT OURS (§14c). `rule / money / service / contract /
 *  project / asset / office` is how we decided something was a thread; a resident asks
 *  whether it is about their kid's school or their tax bill. Unknown slugs are humanised
 *  rather than dropped, so a new group appears the day it appears in the CSV — the rule
 *  money_gaps uses for `side`. */
/** COLOUR PER GROUP, in the order the palette was validated in. TJ: "i think each category
 *  should get a color." The order below is not cosmetic — `--thread-1..5` passed the six
 *  checks *as a sequence*, so a group takes its slot and slots are never cycled. A sixth
 *  group added to the CSV gets no colour until a sixth step is validated, which is the
 *  honest failure: an unvalidated hue that happens to look fine is how --subj-4 and
 *  --subj-5 ended up indistinguishable in dark mode.
 *
 *  It is NEVER the only signal. The section heading names the group in words, the glyph
 *  carries the KIND as a shape, and the standing line carries the state. */
const GROUP_TONE: Record<string, string> = {
  'what-i-pay': 'var(--thread-1)',
  schools: 'var(--thread-2)',
  'how-the-town-runs': 'var(--thread-3)',
  buildings: 'var(--thread-4)',
  'water-sewer-roads': 'var(--thread-5)',
}
export const toneOf = (t: { groups: string }) =>
  GROUP_TONE[groupsOf(t as Thread)[0] ?? ''] ?? 'var(--text-muted)'

const GROUP: Record<string, string> = {
  schools: 'Schools and my kids',
  'what-i-pay': 'What I pay',
  buildings: 'Town land and buildings',
  'water-sewer-roads': 'Water, sewer, roads and trash',
  'how-the-town-runs': 'How the town runs',
}
const groupLabel = (g: string) => GROUP[g] ?? g.replace(/-/g, ' ').replace(/^./, c => c.toUpperCase())
const groupsOf = (t: Thread) => (t.groups || '').split(';').map(s => s.trim()).filter(Boolean)
const fyOf = (iso: string) => (iso ? (Number(iso.slice(0, 4)) + (Number(iso.slice(5, 7)) >= 7 ? 1 : 0)) : 0)

const since = (iso: string) => {
  if (!iso) return ''
  const d = Math.round((Date.now() - Date.parse(iso + 'T12:00:00Z')) / 86400000)
  if (d < 1) return 'today'
  if (d === 1) return 'yesterday'
  if (d < 31) return `${d} days ago`
  if (d < 365) return `${Math.round(d / 30)} months ago`
  return `${(d / 365).toFixed(1)} years ago`
}
// en-US, like every other date on this site. This page shipped with en-GB ("18 Sep 2026")
// against a Massachusetts town's own convention everywhere else.
const pretty = (iso: string) =>
  iso ? new Date(iso + 'T12:00:00Z').toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) : ''
const prettyShort = (iso: string) =>
  iso ? new Date(iso + 'T12:00:00Z').toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) : ''
/** WHERE IT LAST CAME UP. TJ: 'we should also show the last meeting these were discussed
 *  in — "last discussed the Select Board, Sept 18"'. A relative time says how stale a
 *  matter is; the board and the date say where to go and what to look up, which is the
 *  thing a resident can act on. The chronology is ascending, so the last stop is the end. */
const lastStop = (t: Thread) => t.chronology.length ? t.chronology[t.chronology.length - 1] : null

const muted = { color: 'var(--text-muted)' } as const
const secondary = { color: 'var(--text-secondary)' } as const

/** THE EPISTEMIC LABEL, AND IT USES THE SITE'S ONE SCALE.
 *
 *  This page first shipped its own two-state badge — THE CLERK'S RECORD against AS HEARD —
 *  in colours (`--ok`, `--warn`, `--border`) that do not exist in this stylesheet, so every
 *  hardcoded fallback was what actually rendered: three off-palette values that ignore the
 *  theme. components/Basis.tsx already carries the scale and says why there may only be
 *  one: "two copies of a scale is two scales."
 *
 *  THE MAPPING, and it is deliberately conservative. `stated` is *a document says so and
 *  nothing independent checks it*, which is exactly our minutes of a recording. The Clerk's
 *  printed proceedings are `cross-checked` ONLY where we also hold a recording of the same
 *  meeting and the two can be set against each other; where the report is the only record,
 *  it is authoritative and still unchecked, so it stays `stated`. Overstating the Clerk is
 *  the same failure as overstating the captions, pointed the other way.
 *
 *  The specific source rides along as the note, so the distinction TJ needs is never lost
 *  to the scale being coarse. */
function levelOf(c: Closure, ourMeetingDates: Set<string>): Level {
  if (c.basis !== 'official') return 'stated'
  return ourMeetingDates.has(c.date) ? 'cross-checked' : 'stated'
}

function ClosureBasis({ c, ours }: { c: Closure; ours: Set<string> }) {
  return (
    <Basis level={levelOf(c, ours)}>
      {c.basis === 'official' ? 'the Town Clerk’s printed record' : 'our minutes — figures as heard'}
    </Basis>
  )
}

function Standing({ t }: { t: Thread }) {
  if (t.status === 'resolved' && t.closure) {
    return <>Settled at {t.closure.meeting}, {prettyShort(t.closure.date)} — {t.closure.result || 'outcome not recorded'}</>
  }
  if (t.status === 'lapsed') return <>Went quiet — last discussed {since(t.last_moved)}</>
  if (!t.last_moved) return <>Nothing in the readable record yet</>
  /* "LAST MOVED" PRESUPPOSES AN EARLIER MOVE. On a thread with one meeting there is no
     "last" — there is a beginning, and saying it moved last week implies a history the
     reader will look for and not find. So a single-meeting thread says when it STARTED,
     and one that started long ago says that nothing has happened since, which is the
     whole of what is known about it. */
  const at = lastStop(t)
  const where = at ? <> the {at.board}, {prettyShort(at.date)}</> : null
  if (t.momentum.meetings <= 1) {
    return t.heat === 'raised once'
      ? <>Open — raised at{where}, {since(t.last_moved)}, and nothing since</>
      : <>Open — started at{where}, {since(t.last_moved)}</>
  }
  return <>Open — last discussed at{where}, {since(t.last_moved)}</>
}

function Card({ t, onGo, ours }: { t: Thread; onGo: (id: string) => void; ours: Set<string> }) {
  return (
    <li className="avoid-break" style={{
      padding: '10px 0 10px 10px', borderTop: '1px solid var(--grid)',
      // a 3px edge in the group's colour, so a row is placeable before it is read
      boxShadow: `inset 3px 0 0 ${toneOf(t)}`,
    }}>
      <div className="flex items-baseline gap-2 flex-wrap">
        <span className="flex items-baseline gap-1.5 min-w-0">
          <ThreadKind kind={t.kind} tone={toneOf(t)} />
          <a href={`/threads/${t.id}`} onClick={e => { e.preventDefault(); onGo(t.id) }}
            style={{ fontWeight: 600, textDecoration: 'none' }}>{t.label}</a>
          {t.pin != null && (
            <span className="ml-2 text-[10px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded align-middle"
              title="Pinned: chosen to lead this page, whatever moved most recently"
              style={{ background: 'var(--series-cost)', color: '#fff' }}>Top</span>
          )}
        </span>
        {t.is_new ? (
          <span className="text-[10px] font-bold uppercase tracking-widest px-1.5 py-0.5 rounded shrink-0"
            style={{ background: toneOf(t), color: 'var(--surface-1)' }}>New</span>
        ) : null}
        <HotBadge hot={t.hot} momentum={t.momentum} />
        <ThreadHeat heat={t.heat} tone={toneOf(t)} momentum={t.momentum} />
        {t.closure ? <ClosureBasis c={t.closure} ours={ours} /> : null}
      </div>
      <div style={{ ...secondary, fontSize: 13, marginTop: 2 }}><Standing t={t} /></div>
      {/* NEXT ON AN AGENDA, where one is posted: the reason to open the thread today. */}
      {(() => {
        const next = (t.on_agenda ?? []).find(a => a.date >= localToday())
        return next ? (
          <div style={{ fontSize: 13, marginTop: 2, color: 'var(--series-cost)', fontWeight: 600 }}>
            On the agenda: {weekday(next.date)}, {meetingTitle(next.board, next.body_as_printed)}
          </div>
        ) : null
      })()}
      {t.status !== 'resolved' && t.stands.vote ? (
        <div style={{ ...secondary, fontSize: 13, marginTop: 2 }}>
          Last vote: <strong>{t.stands.vote.outcome || 'outcome not recorded'}</strong>{' '}
          — {t.stands.vote.text.length > 96 ? t.stands.vote.text.slice(0, 95) + '…' : t.stands.vote.text}
        </div>
      ) : null}
      <div style={{ ...muted, fontSize: 13, marginTop: 2 }}>{t.question}</div>
      {/* THE COUNTS THE HEAT WORD WAS READ OFF, so the summary is checkable (rule 7). */}
      <div style={{ ...muted, fontSize: 12, marginTop: 3 }}>
        {t.momentum.boards} {t.momentum.boards === 1 ? 'board' : 'boards'} ·{' '}
        {t.momentum.meetings} {t.momentum.meetings === 1 ? 'meeting' : 'meetings'} ·{' '}
        {t.momentum.votes} {t.momentum.votes === 1 ? 'vote' : 'votes'} · {t.stage}
        {/* The groups, in words: the page lists a thread once, so the card says where else
            it belongs rather than the page repeating it there. */}
        {groupsOf(t).length ? <> · {groupsOf(t).map(groupLabel).join(', ')}</> : null}
      </div>
      {(t.heat === 'stale' || t.heat === 'slowing' || t.heat === 'raised once')
        && t.momentum.board_meetings_since >= 2 ? (
        <div style={{ ...muted, fontSize: 12, marginTop: 3 }}>
          {t.momentum.boards === 1 ? 'that board has' : 'those boards have'} met{' '}
          {t.momentum.board_meetings_since} times since without returning to it
        </div>
      ) : null}
      {t.tangled ? (
        <div style={{ marginTop: 3 }}>
          <Tangled boards={t.momentum.boards} meetings={t.momentum.meetings} />
        </div>
      ) : null}
    </li>
  )
}

function Landing({ d, onGo, ours }: { d: Payload; onGo: (id: string) => void; ours: Set<string> }) {
  const [group, setGroup] = useState<string | null>(null)
  const open = d.threads.filter(t => t.status === 'open')
  const resolved = d.threads.filter(t => t.status === 'resolved')
  const lapsed = d.threads.filter(t => t.status === 'lapsed')

  /* EVERY THREAD APPEARS ONCE. TJ, 11 October 2026: "threads page duplicates threads
     multiple times." It did -- 41 cards for 21 threads. A pinned thread showed in Top AND
     under each of its groups; a new one in Newly raised, What is moving now AND each group.
     The earlier fix (open threads only in the groups) halved it and kept "a thread in two
     groups appears in both, because that is what belonging means" -- which is true of a
     FILTER and false of a list. So the groups are a filter now, never a second listing:
     each open thread sits in exactly one of Top / Newly raised / Still open, and a chip
     narrows all three at once. The card names its groups, so nothing is lost by listing it
     once. "What is moving now" is gone because Still open is already ranked by recency --
     its first four WERE that section, printed twice. */
  const groups = useMemo(() => {
    const m = new Map<string, number>()
    for (const t of open) for (const g of groupsOf(t)) m.set(g, (m.get(g) ?? 0) + 1)
    return [...m.entries()].sort((a, b) => b[1] - a[1])
  }, [d])
  const byFy = useMemo(() => {
    const m = new Map<number, Thread[]>()
    for (const t of resolved) {
      const fy = fyOf(t.closure?.date || t.resolved_on)
      m.set(fy, [...(m.get(fy) ?? []), t])
    }
    return [...m.entries()].sort((a, b) => b[0] - a[0])
  }, [d])
  const inGroup = (t: Thread) => !group || groupsOf(t).includes(group)
  // PINNED LEAD, in pin order -- a person's call (threads.csv `pin`). TJ, 10 October 2026:
  // *"Track turf field is now the TOP thread ;) need to have a way to make them important
  // and ordered"*.
  const pinned = open.filter(t => t.pin != null && inGroup(t)).sort((a, b) => (a.pin ?? 0) - (b.pin ?? 0))
  const newly = open.filter(t => t.is_new && t.pin == null && inGroup(t))
  const rest = open.filter(t => !t.is_new && t.pin == null && inGroup(t))

  return (
    <>
      <ThreadsHero />

      {/* THE FILTER SITS ABOVE EVERYTHING IT FILTERS, so a reader who knows what they want
          narrows the page before reading it, and one who does not reads it ranked (§14c). */}
      <div className="flex flex-wrap gap-1.5 mb-3">
        {groups.map(([g, n]) => {
          const on = group === g
          return (
            <button key={g} type="button" aria-pressed={on}
              onClick={() => setGroup(on ? null : g)}
              className="text-[13px] px-2.5 py-1 rounded-full border cursor-pointer"
              style={{
                borderColor: on ? GROUP_TONE[g] ?? 'var(--grid)' : 'var(--grid)',
                background: on ? GROUP_TONE[g] ?? 'var(--text-primary)' : 'transparent',
                color: on ? 'var(--surface-1)' : 'inherit',
              }}>
              <span className="inline-block w-2 h-2 rounded-full mr-1.5 align-middle"
                style={{ background: on ? 'var(--surface-1)' : GROUP_TONE[g] ?? 'var(--text-muted)' }} />
              {groupLabel(g)} <span className="opacity-60">{n}</span></button>
          )
        })}
      </div>

      {pinned.length ? (
        <>
          <H2>Top threads</H2>
          <ul className="list-none p-0 m-0 mb-4">
            {pinned.map(t => <Card key={t.id} t={t} onGo={onGo} ours={ours} />)}
          </ul>
        </>
      ) : null}

      {/* NEWLY RAISED, ABOVE THE REST. TJ: "when a NEW thread is identified, it should
          show up at the top of the threads page with a big label as NEW" — and then, on
          seeing the first cut: "'new' threads means new in existence. not new to us ;)".
          What is new is the MATTER, not our filing of it. */}
      {newly.length ? (
        <>
          <H2>Newly raised</H2>
          <Body>{newly.length === 1 ? 'This first came' : 'These first came'} up in the last two
            months, and {newly.length === 1 ? 'is' : 'are'} still open.</Body>
          <ul className="list-none p-0 m-0 mb-4">
            {newly.map(t => <Card key={t.id} t={t} onGo={onGo} ours={ours} />)}
          </ul>
        </>
      ) : null}

      {rest.length ? (
        <>
          <H2>{pinned.length || newly.length ? 'Everything else still open' : 'Still open'}</H2>
          <ul className="list-none p-0 m-0">
            {rest.map(t => <Card key={t.id} t={t} onGo={onGo} ours={ours} />)}
          </ul>
          <p className="text-[12px] mt-1.5" style={muted}>Ordered by {d.coverage.rank_basis}.</p>
        </>
      ) : null}
      {group && !pinned.length && !newly.length && !rest.length
        ? <Body>Nothing open in {groupLabel(group)}.</Body> : null}

      {/* Resolved grows forever, so it is grouped by fiscal year first — "what did Town
          Meeting settle in FY26" is the question people bring to an archive (§14c). */}
      <H2>Settled</H2>
      {byFy.length === 0 ? <Body>Nothing settled yet in the readable record.</Body> : null}
      {byFy.map(([fy, ts]) => (
        <div key={fy} className="mb-3">
          <H3>FY{fy}</H3>
          <ul className="list-none p-0 m-0">
            {ts.map(t => <Card key={t.id} t={t} onGo={onGo} ours={ours} />)}
          </ul>
        </div>
      ))}

      {lapsed.length > 0 ? (
        <>
          <H2>Went quiet</H2>
          <Body>Nobody decided these. They are not settled — they stopped being discussed,
            and some stopped only because the record did.</Body>
          <ul className="list-none p-0 m-0">
            {lapsed.map(t => <Card key={t.id} t={t} onGo={onGo} ours={ours} />)}
          </ul>
        </>
      ) : null}

      <H2>What we looked at and did not open</H2>
      <Body>A candidate rejected is recorded with its reason, so <em>we looked and said
        no</em> stays distinguishable from <em>nobody looked</em>.</Body>
      <ul className="text-[13px] pl-4.5 list-disc" style={secondary}>
        {d.declined.map((x, i) => (
          <li key={i} className="mb-1">
            <strong>{x.candidate}</strong> — {x.reason}
            {x.revisit_if && x.revisit_if !== 'never'
              ? <span style={muted}> · revisit if {x.revisit_if}</span> : null}
          </li>
        ))}
      </ul>

      {/* THE KEY COMES AFTER THE THING IT IS A KEY TO (rule 7a) — explaining the glyphs
          before a reader has seen one is explaining a legend to somebody who has not seen
          the map. */}
      <H2>The glyphs</H2>
      <ul className="list-none p-0 m-0 grid gap-1.5 text-[13px]"
        style={{ gridTemplateColumns: 'repeat(auto-fill,minmax(230px,1fr))', ...secondary }}>
        {KINDS.map(k => (
          <li key={k} className="flex items-center gap-2">
            <ThreadKind kind={k} tone="var(--text-muted)" />{KIND_LABEL[k]}
          </li>
        ))}
      </ul>

      {/* THE CHART LIVES AT THE FOOT. TJ: "keep that chart, put it at the bottom maybe."
          It is the right call for a reason worth keeping: every thread is already listed
          above with its standing in words, so the ribbons are a SECOND pass over the same
          twenty — the shape of the year rather than the way in. A reader who wants one
          thread has it before they reach this; a reader who wants the pattern finds it
          where patterns belong, after the particulars. */}
      <H2>All {d.threads.length}, across time</H2>
      <ThreadRibbons
        rows={d.threads.map(t => ({
          id: t.id, label: t.label, status: t.status, kind: t.kind, tone: toneOf(t),
          first: t.first_seen, last: t.last_moved,
          dates: t.chronology.map(c => c.date),
        }))}
        onGo={onGo} />

      {/* THE DENOMINATOR, ON THE PAGE AND NOT ONLY IN THE PAYLOAD (§7). A thread that went
          quiet because the RECORD went quiet is not a thread where nothing happened. */}
      <Note>
        Tracked through {d.coverage.meetings_readable} meetings across{' '}
        {d.coverage.boards_readable} boards that left a record we can read, including{' '}
        {d.coverage.town_meeting_readable} Town Meetings. The Town Clerk’s printed record of
        what Town Meeting voted is held for FY{d.coverage.official_town_meeting_years[0]}–FY
        {d.coverage.official_town_meeting_years.slice(-1)[0]}; more recent votes are ours,
        from machine captions, until that year’s annual report is published.
      </Note>
    </>
  )
}

/** ONE THREAD, READ TO CATCH UP BEFORE A MEETING.
 *
 *  TJ, 15 October 2026: *"make sure the threads have all the relevant information, like what
 *  has been said so people can use the thread as a way to catch up on the topic before the
 *  meeting. The thread view probably needs a rethink. its not easy to understand yet."*
 *
 *  WHAT WAS HARD, measured on /threads/turf-field-study and /threads/stormwater-fee before
 *  this rewrite:
 *   1. The first thing under the title was our own instrumentation -- a kind glyph, a heat
 *      word ("picking up"), and a count line ending in "voted on, not decided". Metadata
 *      before the matter.
 *   2. "Where it stands" was the last vote unless a later DECISION existed, so the turf
 *      thread led with a School Committee note about its own future agendas while the
 *      Select Board holding the article off the warrant sat further down.
 *   3. "What happens next" printed the closure criterion -- a definition of done, not a
 *      step -- and no thread could say which meeting was next.
 *   4. "Meeting by meeting" was one flat bulleted dump: 179 bullets on the stormwater thread,
 *      every kind of line in the same voice, nothing saying which record a line came from,
 *      and nothing quoted from a document, because the town's own minutes were not read.
 *
 *  THE ORDER NOW (rule 7a, 7b; THREADS-MODEL §8 and §14d): the question, then the latest
 *  thing that moved and the last vote, then the next meeting it is on an agenda for, then
 *  the counts, then what was said, newest first, meeting by meeting, each line labelled with
 *  the record it came from. What it does not show, the reading and the coverage come last.
 *  A settled thread leads with how it ended and tells its story start to finish. */
const KIND_WORD: Record<string, string> = {
  vote: 'Vote', decision: 'Decided', budget: 'Money discussed', topic: 'Discussed',
  contention: 'Disputed', comment: 'Public comment', safety: 'Safety concern raised', condition: 'Condition set',
}
const KIND_RANK: Record<string, number> = { vote: 0, decision: 1, safety: 2, condition: 1, contention: 2, budget: 3, topic: 4, comment: 5 }
const hms = (t: number) => {
  const h = Math.floor(t / 3600), m = Math.floor((t % 3600) / 60), s = t % 60
  return (h ? `${h}:${String(m).padStart(2, '0')}` : `${m}`) + `:${String(s).padStart(2, '0')}`
}
const localToday = () => {
  const n = new Date()
  return `${n.getFullYear()}-${String(n.getMonth() + 1).padStart(2, '0')}-${String(n.getDate()).padStart(2, '0')}`
}
const weekday = (iso: string) =>
  new Date(iso + 'T12:00:00Z').toLocaleDateString('en-US', { weekday: 'long', month: 'short', day: 'numeric' })

/** Which record a line came from, said on the line. Rule 7 and CLAUDE.md "Searching what
 *  the town said": our notes from a recording are a finding aid written from machine
 *  captions, and are never set in the same voice as the town's own minutes. */
function Cite({ it }: { it: Item }) {
  const link = { color: 'var(--series-cost)' }
  if (it.source === 'town') {
    return (
      <span className="text-[12px]" style={muted}>
        the town&rsquo;s minutes
        {it.doc_url ? <> · <a className="underline" style={link} href={it.doc_url}>our copy</a></> : null}
        {it.town_url ? <> · <a className="underline" style={link} href={it.town_url} target="_blank" rel="noreferrer">the town&rsquo;s</a></> : null}
      </span>
    )
  }
  // A MOMENT A PERSON PICKED OUT (sources/data/thread-moments.csv): the quote is the machine
  // captions word for word, checked at build -- a finding aid, so it says so and links the second.
  if (it.source === 'caption') {
    return (
      <span className="text-[12px]" style={muted}>
        quoted from the recording&rsquo;s machine captions, which mishear
        {it.video_url && it.t != null ? <> · <a className="underline" style={link}
          href={`${it.video_url}&t=${it.t}s`} target="_blank" rel="noreferrer">watch at {hms(it.t)}</a></> : null}
      </span>
    )
  }
  return (
    <span className="text-[12px]" style={muted}>
      our notes from the recording, as heard
      {it.video_url && it.t != null ? <> · <a className="underline" style={link}
        href={`${it.video_url}&t=${it.t}s`} target="_blank" rel="noreferrer">watch at {hms(it.t)}</a></> : null}
    </span>
  )
}

function Line({ it }: { it: Item }) {
  const vote = it.kind === 'vote'
  return (
    <li className="py-2 border-t first:border-t-0" style={{ borderColor: 'var(--grid)' }}>
      <span className="block text-[10.5px] font-bold uppercase tracking-widest"
        style={{ color: vote ? 'var(--series-cost)' : (it.kind === 'contention' || it.kind === 'safety' || it.kind === 'condition') ? 'var(--status-critical)' : 'var(--text-muted)' }}>
        {KIND_WORD[it.kind] ?? it.kind}{vote && it.outcome ? ` — ${it.outcome}` : ''}
      </span>
      <span className="block text-[14.5px] leading-snug mt-0.5" style={{ fontWeight: vote ? 600 : 400 }}>{it.text}</span>
      {it.quote ? (
        <span className="block text-[13px] leading-snug mt-1 pl-2.5"
          style={{ ...secondary, borderLeft: '2px solid var(--grid)' }}>&ldquo;{it.quote}&rdquo;</span>
      ) : null}
      <span className="block mt-0.5"><Cite it={it} /></span>
    </li>
  )
}

/** One meeting: the board and date, then its lines -- votes first, then decisions, then
 *  what was discussed -- the town's record before ours where both exist. */
function Stop({ c }: { c: Stop }) {
  const items = [...c.items].sort((a, b) =>
    (KIND_RANK[a.kind] ?? 9) - (KIND_RANK[b.kind] ?? 9) || Number(a.source !== 'town') - Number(b.source !== 'town'))
  return (
    <li className="card px-4 py-3 avoid-break">
      <div className="flex flex-wrap items-baseline gap-x-2">
        <span className="text-[15px] font-bold">{pretty(c.date)}</span>
        <a href={`/boards/${c.board_slug}`} className="text-[14px] font-semibold underline decoration-dotted">{c.board}</a>
      </div>
      <ul className="list-none p-0 m-0 mt-1">
        {items.map((it, j) => <Line key={j} it={it} />)}
      </ul>
    </li>
  )
}

/** THE LATEST THING THAT MOVED: the most recent meeting, and its weightiest line -- a vote,
 *  else a decision, else what it was discussed under. Quoted, never summarised. */
function latest(t: Thread) {
  const at = lastStop(t)
  if (!at) return null
  const top = [...at.items].sort((a, b) => (KIND_RANK[a.kind] ?? 9) - (KIND_RANK[b.kind] ?? 9))[0]
  return { stop: at, it: top }
}
function lastVote(t: Thread) {
  for (const c of [...t.chronology].reverse()) {
    const v = c.items.filter(i => i.kind === 'vote')
    if (v.length) return { stop: c, it: v[v.length - 1] }
  }
  return null
}

function NextOnAgenda({ t, asOf }: { t: Thread; asOf: string }) {
  const today = localToday()
  const ahead = (t.on_agenda ?? []).filter(a => a.date >= today)
  // Just past, newest first: an agenda whose minutes are not out yet is still news.
  const past = (t.on_agenda ?? []).filter(a => a.date < today).reverse()
  const days = new Map<string, OnAgenda[]>()
  for (const a of ahead) days.set(a.board_slug + a.date, [...(days.get(a.board_slug + a.date) ?? []), a])
  return (
    <div className="card p-4 mt-5 max-w-2xl" style={{ borderLeft: '4px solid var(--series-cost)' }}>
      <p className="text-[11px] font-bold uppercase tracking-widest" style={{ color: 'var(--series-cost)' }}>
        Next on an agenda
      </p>
      {days.size === 0 ? (
        <p className="text-[14px] mt-1" style={secondary}>
          Not on any agenda posted for the next four weeks (agendas read {pretty(asOf) || 'recently'}).
          Boards post agendas about two days before they meet.
        </p>
      ) : (
        <ul className="list-none p-0 m-0 mt-1 space-y-2.5">
          {[...days.values()].map(rows => {
            const a = rows[0]
            return (
              <li key={a.board_slug + a.date}>
                <span className="block text-[15px] font-bold">{weekday(a.date)} · {meetingTitle(a.board, a.body_as_printed)}</span>
                {rows.map((r, i) => (
                  <span key={i} className="block text-[13.5px] leading-snug mt-0.5" style={secondary}>
                    &ldquo;{r.line.length > 220 ? r.line.slice(0, 218) + '…' : r.line}&rdquo;
                    {r.by === 'board' ? <span style={muted}> — this board&rsquo;s own subject</span> : null}
                  </span>
                ))}
                <span className="block text-[12px] mt-0.5">
                  <a className="underline" style={{ color: 'var(--series-cost)' }} href={a.agenda_url} target="_blank" rel="noreferrer">the agenda</a>
                  {' · '}<a className="underline" style={{ color: 'var(--series-cost)' }} href={`/this-week#m-${a.board_slug}-${a.date}`}>this week</a>
                </span>
              </li>
            )
          })}
        </ul>
      )}
      {past.length ? (
        <div className="mt-2.5">
          <p className="text-[11px] font-bold uppercase tracking-widest" style={muted}>On a recent agenda</p>
          <ul className="list-none p-0 m-0 mt-0.5">
            {past.map((a, i) => (
              <li key={i} className="text-[13px] leading-snug mt-1" style={secondary}>
                <span className="font-semibold">{prettyShort(a.date)}, {meetingTitle(a.board, a.body_as_printed)}:</span>{' '}
                &ldquo;{a.line.length > 140 ? a.line.slice(0, 138) + '…' : a.line}&rdquo;{' '}
                <a className="underline text-[12px]" style={{ color: 'var(--series-cost)' }} href={a.agenda_url} target="_blank" rel="noreferrer">agenda</a>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      <p className="text-[11.5px] mt-2" style={muted}>
        Quoted from the posted agenda. An agenda lists what may be discussed, not what will be decided.
      </p>
    </div>
  )
}

function One({ t, d, onGo, ours }: { t: Thread; d: Payload; onGo: (id: string | null) => void; ours: Set<string> }) {
  const [all, setAll] = useState(false)
  const settled = t.status === 'resolved'
  // Newest first while it is forming; start to finish once it is formed (§14d).
  const chron = settled ? t.chronology : [...t.chronology].reverse()
  const SHOW = 6
  const shown = all ? chron : chron.slice(0, SHOW)
  const now = latest(t)
  const vote = lastVote(t)
  const votes = t.chronology.flatMap(c => c.items.filter(i => i.kind === 'vote').map(i => ({ c, i }))).reverse()
  const townN = t.chronology.filter(c => c.items.some(i => i.source === 'town')).length
  const oursN = t.chronology.filter(c => c.items.some(i => i.source !== 'town')).length
  return (
    <>
      <p style={{ margin: '0 0 10px' }}>
        <a href="/threads" onClick={e => { e.preventDefault(); onGo(null) }}
          style={{ fontSize: 13 }}>← everything the town is deciding</a>
      </p>

      {/* THE STATUS, ONE LINE. Open or settled, where it last came up, and -- only where it
          is earned -- the hot badge, whose counts are in its own label. */}
      <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-[14px]" style={secondary}>
        <span><Standing t={t} /></span>
        <HotBadge hot={t.hot} momentum={t.momentum} />
      </div>

      {settled && t.closure ? (
        <div className="card p-4 mt-4 max-w-2xl" style={{ borderLeft: `4px solid ${toneOf(t)}` }}>
          <p className="text-[11px] font-bold uppercase tracking-widest" style={muted}>How it ended</p>
          <p className="text-[16px] font-bold mt-1">{t.closure.result || 'Outcome not recorded'}</p>
          <p className="text-[13.5px] mt-0.5" style={secondary}>
            {t.closure.meeting}, {pretty(t.closure.date)}{t.closure.article ? `, article ${t.closure.article}` : ''}{' '}
            <ClosureBasis c={t.closure} ours={ours} />
          </p>
          <p className="text-[13.5px] leading-snug mt-2 pl-2.5" style={{ ...secondary, borderLeft: '2px solid var(--grid)' }}>
            &ldquo;{t.closure.quote}&rdquo;</p>
          {t.closure.fincom || t.closure.select_board ? (
            <p className="text-[12.5px] mt-1.5" style={muted}>
              Finance Committee: {t.closure.fincom || '—'} · Select Board: {t.closure.select_board || '—'}</p>
          ) : null}
          {t.closure.caveat ? <Note>{t.closure.caveat}</Note> : null}
        </div>
      ) : (
        <>
          {/* WHERE IT STANDS: the latest meeting's weightiest line, and the last vote if it
              is a different thing. Each quoted from the record and cited, never paraphrased. */}
          <div className="card p-4 mt-4 max-w-2xl" style={{ borderLeft: `4px solid ${toneOf(t)}` }}>
            <p className="text-[11px] font-bold uppercase tracking-widest" style={muted}>Where it stands</p>
            {now ? (
              <>
                <p className="text-[12.5px] mt-1" style={muted}>Latest: {now.stop.board}, {pretty(now.stop.date)}</p>
                <p className="text-[15px] leading-snug mt-0.5" style={{ fontWeight: 600 }}>
                  {now.it.kind === 'vote' ? `${now.it.outcome || 'Voted'}: ` : ''}{now.it.text}</p>
                <Cite it={now.it} />
                {vote && vote.it !== now.it ? (
                  <>
                    <p className="text-[12.5px] mt-3" style={muted}>Last vote: {vote.stop.board}, {pretty(vote.stop.date)}</p>
                    <p className="text-[14.5px] leading-snug mt-0.5">
                      <strong>{vote.it.outcome || 'outcome not recorded'}</strong> — {vote.it.text}</p>
                    <Cite it={vote.it} />
                  </>
                ) : null}
                {!vote ? <p className="text-[12.5px] mt-2" style={muted}>No vote on this in the record we can read.</p> : null}
              </>
            ) : <p className="text-[14px] mt-1" style={secondary}>Nothing in the readable record yet.</p>}
          </div>
          <NextOnAgenda t={t} asOf={d.coverage.agendas_as_of ?? ''} />
        </>
      )}

      {/* THE COUNTS, each with its unit (rule 7b: never a bare number). */}
      <div className="flex flex-wrap gap-x-10 gap-y-4 mt-6">
        <Stat value={String(t.meetings)}>{t.meetings === 1 ? 'meeting has' : 'meetings have'} taken it up</Stat>
        <Stat value={String(t.boards_touched)}>{t.boards_touched === 1 ? 'board' : 'different boards'}</Stat>
        <Stat value={String(t.momentum.votes)}>{t.momentum.votes === 1 ? 'vote' : 'votes'} taken on it</Stat>
        {t.first_seen ? <Stat value={prettyShort(t.first_seen)}>first came up, {t.first_seen.slice(0, 4)}</Stat> : null}
      </div>

      <H2>{settled ? 'How it got there, meeting by meeting' : 'What has been said, newest first'}</H2>
      <p className="text-[13px] mt-0 mb-3 max-w-2xl" style={muted}>
        Every line names its record: <strong>the town&rsquo;s minutes</strong>, quoted, or{' '}
        <strong>our notes from the recording</strong>, written from machine captions that can mishear
        numbers and names — check the video at the second given.
      </p>
      {chron.length === 0 ? <Body>Nothing in the readable record yet.</Body> : (
        <ol className="list-none p-0 m-0 space-y-2.5 max-w-2xl">
          {shown.map((c, i) => <Stop key={i} c={c} />)}
        </ol>
      )}
      {chron.length > SHOW ? (
        <button type="button" onClick={() => setAll(a => !a)}
          className="mt-2 text-[13.5px] font-semibold" style={{ color: 'var(--series-cost)' }}>
          {all ? 'Show fewer' : `Show the ${chron.length - SHOW} ${settled ? 'later' : 'earlier'} meetings`}
        </button>
      ) : null}

      {votes.length > 1 ? (
        <>
          <H2>Every vote, newest first</H2>
          <ul className="list-none p-0 m-0 max-w-2xl">
            {votes.map(({ c, i }, k) => (
              <li key={k} className="py-1.5 border-t first:border-t-0 text-[14px] leading-snug" style={{ borderColor: 'var(--grid)' }}>
                <span className="font-semibold">{prettyShort(c.date)}, {c.board}:</span>{' '}
                <strong>{i.outcome || 'outcome not recorded'}</strong> — {i.text}{' '}
                <span className="text-[12px]" style={muted}>({i.source === 'town' ? 'the town’s minutes' : 'our notes, as heard'})</span>
              </li>
            ))}
          </ul>
        </>
      ) : null}

      {t.reports?.length ? (
        <>
          <H2>Read further</H2>
          <ul className="m-0 mb-2 p-0 list-none">
            {t.reports.map(r => (
              <li key={r.url} className="mb-1">
                <a href={r.url} className="font-semibold text-[15px]" style={{ color: 'var(--series-cost)' }}>
                  {r.title} &rarr;</a>
              </li>
            ))}
          </ul>
        </>
      ) : null}

      {/* REPORTS SERVE THREADS. TJ, 15 October 2026: "reports should assist threads." The
          questions the meetings on this matter asked that a page of numbers would answer --
          each with the meeting that asked it, in its own words, because a question raised two
          years ago reads differently from one raised last week. */}
      {t.reports_needed?.length ? (
        <>
          <H2>Reports this thread needs</H2>
          <ul className="m-0 mb-2 p-0 list-none max-w-2xl">
            {t.reports_needed.map(r => (
              <li key={r.slug} className="py-2 border-t first:border-t-0" style={{ borderColor: 'var(--grid)' }}>
                <div className="text-[15px] font-semibold">
                  {r.url ? <a href={r.url} style={{ color: 'var(--series-cost)' }}>{r.title} &rarr;</a> : r.title}
                  {' '}<span className="text-[12px] font-normal" style={muted}>
                    {r.status === 'new' ? 'not written yet' : 'answered on this page'}
                    {' · asked at '}{r.meetings.length} meeting{r.meetings.length === 1 ? '' : 's'}
                  </span>
                </div>
                <ul className="m-0 mt-1 p-0 list-none">
                  {r.meetings.map((m, k) => (
                    <li key={k} className="text-[14px] leading-snug mt-1">
                      <span className="font-semibold">{prettyShort(m.date)}, {m.board}</span>{' '}
                      <span className="text-[12px]" style={muted}>({m.fiscal_year})</span>: {m.question_then}{' '}
                      <a href={m.watch_at} className="text-[12px] underline" style={muted}>watch at {m.at}</a>
                      {' · '}<a href={m.our_minutes} className="text-[12px] underline" style={muted}>our notes</a>
                    </li>
                  ))}
                </ul>
              </li>
            ))}
          </ul>
          <p className="text-[12px] max-w-2xl mt-0" style={muted}>
            Suggested from our notes of each recording: questions the meeting asked that a page laying out the
            numbers would answer. A suggestion, not a finding.
          </p>
        </>
      ) : null}

      <NotShown>
        {t.caveat ? <p>{t.caveat}</p> : null}
        <p className={t.caveat ? 'mt-2' : ''}>
          {settled ? 'It closed when ' : 'It closes when '}<strong>{t.closes}</strong>. A board discussing a
          thing is not the board that decides it, and an agenda item is not a decision.
        </p>
        <p className="mt-2">
          Found by this thread&rsquo;s own words in {t.meetings} of the {d.coverage.meetings_readable.toLocaleString()} meetings
          we can read — {townN} through the town&rsquo;s minutes, {oursN} through our notes of a recording.
          A meeting that discussed it in other words is missing; a thread can only follow meetings that left a record.
        </p>
      </NotShown>

      {/* THE READING, AFTER THE THING IT READS (rule 7a): the heat word and its counts. */}
      <p className="text-[12.5px] mt-4 flex flex-wrap items-center gap-x-2 gap-y-1" style={muted}>
        <ThreadKind kind={t.kind} size={14} tone={toneOf(t)} />
        {(t.kind || '').split(';').filter(Boolean).map(k => KIND_LABEL[k] ?? k).join(' · ')}
        <span>·</span><ThreadHeat heat={t.heat} tone={toneOf(t)} momentum={t.momentum} />
        <span>· {t.stage}</span>
        {t.tangled ? <><span>·</span><Tangled boards={t.momentum.boards} meetings={t.momentum.meetings} /></> : null}
      </p>
    </>
  )
}

export function Threads() {
  const { d, err } = useReport<Payload>(DATA)
  const [id, setId] = useState<string | null>(() => threadIdFromPath(window.location.pathname))
  /* THE BACK BUTTON, WHICH DID NOT WORK. Going /threads → /threads/kids-kingdom → Back
     changed the address and left the thread on screen.
     App.tsx does listen for `popstate`, but all it does is `setTab(tabFromPath(...))` —
     and both ends of this navigation ARE the threads tab, so React bails out of a state
     update to an identical value and nothing re-renders. A router that keys only on the
     tab cannot see a move inside one. So this page listens for itself.
     Two ends: the id is pushed by `go`, and read back here on pop, so forward works too. */
  useEffect(() => {
    const onPop = () => setId(threadIdFromPath(window.location.pathname))
    window.addEventListener('popstate', onPop)
    return () => window.removeEventListener('popstate', onPop)
  }, [])
  const go = (next: string | null) => {
    const to = next ? `/threads/${next}` : '/threads'
    if (window.location.pathname === to) return   // no dead entries on the stack
    window.history.pushState({}, '', to)
    setId(next)
    window.scrollTo(0, 0)
  }
  const t = d && id ? d.threads.find(x => x.id === id) ?? null : null
  // AN ADDRESS THAT NAMES NOTHING SAYS SO. `/threads/does-not-exist` silently rendered the
  // landing page, so the URL claimed a thread that is not there — and a thread that was
  // renamed or never created looks identical to one that exists. Say which.
  const missing = !!(d && id && !t)
  // ...UNLESS IT NAMES A SEARCH. `/threads/<slug>?q=<words>` is a thread built from a search
  // (components/DynamicThread). The words travel in `q`, because a slug drops quotes and
  // punctuation; without `q` the slug's own words are searched.
  const q = typeof window !== 'undefined' ? new URLSearchParams(window.location.search).get('q') : null
  const dynamic = missing ? (q?.trim() || (id ?? '').replace(/-/g, ' ')) : ''
  // The meeting dates we hold a recording for, so a closure can say whether the Clerk's
  // record has anything to be set against.
  const ours = useMemo(
    () => new Set((d?.threads ?? []).flatMap(x => x.chronology.map(c => c.date))), [d])
  const open = d ? d.threads.filter(x => x.status === 'open').length : 0
  const settled = d ? d.threads.filter(x => x.status === 'resolved').length : 0

  return (
    <ReportShell
      tab={TAB}
      title={t ? t.label : dynamic ? `${dynamic}: every dated mention` : 'What the town is deciding now'}
      standfirst={t ? t.question : dynamic ? 'A thread built from a search, not one somebody curated.'
        : `${open} things still open, ${settled} settled. Each one tracked across every board that touched it.`}
      err={err}
      loading={!d}
      dataUrl={`/data/${DATA}`}
      sourceUrl="/notes/process/THREADS-MODEL.md"
      meta={<a className="underline" href={t ? `/feeds/threads/${t.id}.xml` : '/feeds/threads.xml'}>
        {t ? 'Follow this thread by feed' : 'Follow every thread by feed'}
      </a>}
    >
      {d && missing ? <DynamicThread term={dynamic} /> : null}
      {d && !missing ? (t ? <One t={t} d={d} onGo={go} ours={ours} /> : <Landing d={d} onGo={go} ours={ours} />) : null}
    </ReportShell>
  )
}

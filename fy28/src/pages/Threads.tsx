import { useEffect, useMemo, useState } from 'react'
import { threadIdFromPath, type Tab } from '../routes'
import { Body, H2, H3, ReportShell, useReport } from '../components/report'
import { Basis, type Level } from '../components/Basis'
import { Note } from '../components/primitives'
import { ThreadRibbons } from '../components/ThreadRibbons'
import { ThreadsHero } from '../components/ThreadsHero'
import { ThreadKind, KINDS, KIND_LABEL } from '../components/ThreadKind'
import { ThreadHeat, Tangled, type Heat } from '../components/ThreadHeat'

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
type Item = { kind: string; text: string; outcome: string; t: number | null; video_url: string }
type Item2 = Item & { board: string; board_slug: string; date: string }
type Stop = { board: string; board_slug: string; date: string; items: Item[] }
type Thread = {
  id: string; label: string; question: string; kind: string; groups: string; tags: string
  boards: string; started: string; closes: string; status: string; resolved_on: string; caveat: string
  heat: Heat; stage: string; tangled: boolean; is_new: boolean; registered_on: string
  stands: { vote: Item2 | null; decision: Item2 | null; any: Item2 | null }
  momentum: { meetings: number; boards: number; votes: number; days_since_last: number; span_days: number; meetings_last_90: number; board_meetings_since: number }
  closure: Closure | null; chronology: Stop[]; meetings: number; boards_touched: number
  first_seen: string; last_moved: string; weight: number
}
type Declined = { candidate: string; declined_on: string; reason: string; revisit_if: string; note: string }
type Payload = {
  about: string
  coverage: {
    rank_basis: string; meetings_readable: number; boards_readable: number
    town_meeting_readable: number; official_town_meeting_years: string[]
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
        </span>
        {t.is_new ? (
          <span className="text-[10px] font-bold uppercase tracking-widest px-1.5 py-0.5 rounded shrink-0"
            style={{ background: toneOf(t), color: 'var(--surface-1)' }}>New</span>
        ) : null}
        <ThreadHeat heat={t.heat} tone={toneOf(t)} momentum={t.momentum} />
        {t.closure ? <ClosureBasis c={t.closure} ours={ours} /> : null}
      </div>
      <div style={{ ...secondary, fontSize: 13, marginTop: 2 }}><Standing t={t} /></div>
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

  /* EACH SECTION MEANS ONE THING, which the first cut did not manage. The groups listed
     every thread including the settled ones, so a settled thread appeared under its group
     AND under Settled, and the top band's four appeared a third time. Three sightings of
     one row reads as a bug however deliberate it is.
     The groups now browse the OPEN threads only -- what is live is what a group is for --
     and Settled owns the archive. A thread in two groups still appears in both, because
     that is what belonging to two groups means, and the chip counts say so. */
  const groups = useMemo(() => {
    const m = new Map<string, Thread[]>()
    for (const t of open) for (const g of groupsOf(t)) m.set(g, [...(m.get(g) ?? []), t])
    return [...m.entries()].sort((a, b) => b[1].length - a[1].length)
  }, [d])
  const byFy = useMemo(() => {
    const m = new Map<number, Thread[]>()
    for (const t of resolved) {
      const fy = fyOf(t.closure?.date || t.resolved_on)
      m.set(fy, [...(m.get(fy) ?? []), t])
    }
    return [...m.entries()].sort((a, b) => b[0] - a[0])
  }, [d])
  const filtered = group ? open.filter(t => groupsOf(t).includes(group)) : null
  const newly = d.threads.filter(t => t.is_new)

  return (
    <>
      <ThreadsHero />

      {/* RANK FIRST, THEN GROUPS (§14c). A rank serves the reader who does not know what
          they are looking for; a group serves the reader who does. Group first and the
          most important matter in town sits third inside a collapsed section. */}
      {/* NEWLY OPENED, ABOVE EVERYTHING. TJ: "when a NEW thread is identified, it should
          show up at the top of the threads page with a big label as NEW". A returning
          reader's first question is what they have not seen, and that is a different
          question from what is moving — a thread can be new and quiet, or old and busy. */}
      {newly.length ? (
        <>
          <H2>Newly followed</H2>
          <Body>We started tracking {newly.length === 1 ? 'this' : 'these'} in the last two weeks.
            Some have been running far longer — what is new is that we are following {newly.length === 1 ? 'it' : 'them'}.</Body>
          <ul className="list-none p-0 m-0 mb-4">
            {newly.map(t => <Card key={t.id} t={t} onGo={onGo} ours={ours} />)}
          </ul>
        </>
      ) : null}

      <H2>What is moving now</H2>
      <ul className="list-none p-0 m-0">
        {open.slice(0, 4).map(t => <Card key={t.id} t={t} onGo={onGo} ours={ours} />)}
      </ul>
      <p className="text-[12px] mt-1.5" style={muted}>Ordered by {d.coverage.rank_basis}.</p>

      <H2>Everything still open</H2>
      <div className="flex flex-wrap gap-1.5 mb-3">
        {groups.map(([g, ts]) => {
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
              {groupLabel(g)} <span className="opacity-60">{ts.length}</span></button>
          )
        })}
      </div>
      {filtered
        ? <ul className="list-none p-0 m-0">
            {filtered.map(t => <Card key={t.id} t={t} onGo={onGo} ours={ours} />)}
          </ul>
        : groups.map(([g, ts]) => (
            <div key={g} className="mb-3.5">
              <H3>{groupLabel(g)}</H3>
              <ul className="list-none p-0 m-0">
                {ts.map(t => <Card key={t.id} t={t} onGo={onGo} ours={ours} />)}
              </ul>
            </div>
          ))}

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
      <H2>All twenty, across time</H2>
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

/** ONE THREAD. The order flips on status (§14d): an open thread's most valuable line is
 *  WHAT HAPPENS NEXT, because it is the only thing a resident can act on; a settled one's
 *  is HOW IT ENDED. Putting the chronology first on either is writing the page in the
 *  order it was built. */
function One({ t, d, onGo, ours }: { t: Thread; d: Payload; onGo: (id: string | null) => void; ours: Set<string> }) {
  /* THE ORDER FLIPS ON STATUS, like the sections above it (§14d). An OPEN thread is read
     for what just happened, so it runs newest first. A SETTLED one is a story with an
     ending, and a story is told start to finish — "the chronology, start to finish" is
     what the model says and what the first cut did not do, reversing both. */
  const chron = t.status === 'resolved' ? t.chronology : [...t.chronology].reverse()
  return (
    <>
      <p style={{ margin: '0 0 14px' }}>
        <a href="/threads" onClick={e => { e.preventDefault(); onGo(null) }}
          style={{ fontSize: 13 }}>← everything the town is deciding</a>
      </p>

      <div className="flex items-center gap-3 flex-wrap mb-3 text-[13px]" style={secondary}>
        <span className="flex items-center gap-2">
          <ThreadKind kind={t.kind} size={18} tone={toneOf(t)} />
          {(t.kind || '').split(';').filter(Boolean).map(k => KIND_LABEL[k] ?? k).join(' · ')}
        </span>
        <ThreadHeat heat={t.heat} tone={toneOf(t)} momentum={t.momentum} />
      </div>
      {/* WHERE IT HAS GOT TO, in the counts rather than an adjective. */}
      <p className="text-[13px] m-0 mb-4" style={muted}>
        {t.momentum.boards} {t.momentum.boards === 1 ? 'board' : 'boards'} ·{' '}
        {t.momentum.meetings} {t.momentum.meetings === 1 ? 'meeting' : 'meetings'} ·{' '}
        {t.momentum.votes} {t.momentum.votes === 1 ? 'vote' : 'votes'} · {t.stage}
        {t.momentum.span_days >= 45 ? ` · ran ${Math.round(t.momentum.span_days / 30)} months` : ''}
        {t.tangled ? <> · <Tangled boards={t.momentum.boards} meetings={t.momentum.meetings} /></> : null}
      </p>

      {t.status === 'resolved' && t.closure ? (
        <>
          <H2>How it ended</H2>
          <Body>
            <strong>{t.closure.result || 'Outcome not recorded'}</strong> — {t.closure.meeting},{' '}
            {pretty(t.closure.date)}{t.closure.article ? `, article ${t.closure.article}` : ''}.{' '}
            <ClosureBasis c={t.closure} ours={ours} />
          </Body>
          <blockquote style={{
            margin: '8px 0', padding: '8px 12px', borderLeft: '3px solid var(--grid)',
            fontSize: 14, ...secondary,
          }}>{t.closure.quote}</blockquote>
          {t.closure.fincom || t.closure.select_board ? (
            <Body><span style={{ ...muted, fontSize: 13 }}>
              Finance Committee: {t.closure.fincom || '—'} · Select Board: {t.closure.select_board || '—'}
            </span></Body>
          ) : null}
          {t.closure.caveat ? <Note>{t.closure.caveat}</Note> : null}
        </>
      ) : (
        <>
          <H2>Where it stands</H2>
          {(() => {
            /* THE LAST THING THAT MOVED, not the last time it was mentioned. A vote if one
               was taken, else the decision the board recorded, else the topic it was last
               discussed under — and the board, the date and the second in the recording,
               so the reader can check it rather than take it. */
            const v = t.stands.vote, dcn = t.stands.decision, any = t.stands.any
            const top = v && (!dcn || v.date >= dcn.date) ? v : (dcn ?? any)
            if (!top) return <Body><Standing t={t} /></Body>
            const isVote = top.kind === 'vote'
            return (
              <>
                <Body>
                  {isVote ? <strong>{top.outcome || 'outcome not recorded'} — </strong> : null}
                  {top.text}
                </Body>
                <p className="text-[13px] m-0 mb-2" style={muted}>
                  {isVote ? 'Voted at' : top.kind === 'decision' ? 'Decided at' : 'Discussed at'}{' '}
                  the {top.board}, {pretty(top.date)}
                  {top.video_url && top.t != null ? (
                    <> · <a href={`${top.video_url}&t=${top.t}s`} target="_blank" rel="noreferrer">watch</a></>
                  ) : null}
                  {!v ? ' · no vote has been taken on this' : null}
                </p>
              </>
            )
          })()}
          <H2>What happens next</H2>
          <Body>
            This closes when <strong>{t.closes}</strong>.
            {t.status === 'lapsed'
              ? ' Nothing is currently scheduled, and it has not been discussed in some time.'
              : ''}
          </Body>
        </>
      )}

      {t.caveat ? (
        <>
          <H2>What this does not show</H2>
          <Body><span style={secondary}>{t.caveat}</span></Body>
        </>
      ) : null}

      <H2>Meeting by meeting</H2>
      <Body><span style={{ ...muted, fontSize: 13 }}>
        Tracked through {t.meetings} {t.meetings === 1 ? 'meeting' : 'meetings'} across{' '}
        {t.boards_touched} {t.boards_touched === 1 ? 'board' : 'boards'}, out of{' '}
        {d.coverage.meetings_readable} meetings we can read. A thread can only be followed
        through meetings that left a record.
      </span></Body>
      {chron.map((c, i) => (
        <div key={i} className="avoid-break" style={{ margin: '0 0 10px' }}>
          <div style={{ fontWeight: 600, fontSize: 14 }}>
            {pretty(c.date)} · {c.board}
          </div>
          <ul style={{ margin: '2px 0 0', paddingLeft: 18, fontSize: 14 }}>
            {c.items.map((it, j) => (
              <li key={j} style={{ marginBottom: 3 }}>
                {it.kind === 'vote' ? <strong>Vote: </strong> : null}
                {it.text}
                {it.outcome ? <span style={secondary}> → {it.outcome}</span> : null}
                {it.video_url && it.t != null ? (
                  <> <a href={`${it.video_url}&t=${it.t}s`} target="_blank" rel="noreferrer"
                    style={{ fontSize: 12 }}>watch</a></>
                ) : null}
              </li>
            ))}
          </ul>
        </div>
      ))}
      {chron.length === 0 ? <Body>Nothing in the readable record yet.</Body> : null}
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
  // The meeting dates we hold a recording for, so a closure can say whether the Clerk's
  // record has anything to be set against.
  const ours = useMemo(
    () => new Set((d?.threads ?? []).flatMap(x => x.chronology.map(c => c.date))), [d])
  const open = d ? d.threads.filter(x => x.status === 'open').length : 0
  const settled = d ? d.threads.filter(x => x.status === 'resolved').length : 0

  return (
    <ReportShell
      tab={TAB}
      title={t ? t.label : missing ? 'No such thread' : 'What the town is deciding now'}
      standfirst={t ? t.question : missing ? undefined
        : `${open} things still open, ${settled} settled. Each one tracked across every board that touched it.`}
      err={err}
      loading={!d}
      dataUrl={`/data/${DATA}`}
      sourceUrl="/notes/process/THREADS-MODEL.md"
      meta={<a className="underline" href={t ? `/feeds/threads/${t.id}.xml` : '/feeds/threads.xml'}>
        {t ? 'Follow this thread by feed' : 'Follow every thread by feed'}
      </a>}
    >
      {d && missing ? (
        <Body>
          There is no thread at this address. It may have been renamed, or it may never
          have been opened — <a href="/threads" onClick={e => { e.preventDefault(); go(null) }}>
          see everything the town is deciding</a>.
        </Body>
      ) : null}
      {d && !missing ? (t ? <One t={t} d={d} onGo={go} ours={ours} /> : <Landing d={d} onGo={go} ours={ours} />) : null}
    </ReportShell>
  )
}

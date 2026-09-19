import { useMemo, useState } from 'react'
import { threadIdFromPath, type Tab } from '../routes'
import { Body, H2, H3, ReportShell, useReport } from '../components/report'
import { Basis, type Level } from '../components/Basis'
import { Note } from '../components/primitives'

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
type Stop = { board: string; board_slug: string; date: string; items: Item[] }
type Thread = {
  id: string; label: string; question: string; kind: string; groups: string; tags: string
  boards: string; started: string; closes: string; status: string; resolved_on: string; caveat: string
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
const pretty = (iso: string) =>
  iso ? new Date(iso + 'T12:00:00Z').toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' }) : ''

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
    return <>Settled {pretty(t.closure.date)} — {t.closure.result || 'outcome not recorded'}</>
  }
  if (t.status === 'lapsed') return <>Went quiet — last discussed {since(t.last_moved)}</>
  if (!t.last_moved) return <>Nothing in the readable record yet</>
  return <>Open — last moved {since(t.last_moved)}, {t.boards_touched === 1 ? 'one board' : `${t.boards_touched} boards`}</>
}

function Card({ t, onGo, ours }: { t: Thread; onGo: (id: string) => void; ours: Set<string> }) {
  return (
    <li className="avoid-break" style={{ padding: '10px 0', borderTop: '1px solid var(--grid)' }}>
      <a href={`/threads/${t.id}`} onClick={e => { e.preventDefault(); onGo(t.id) }}
        style={{ fontWeight: 600, textDecoration: 'none' }}>{t.label}</a>
      {t.closure ? <span className="ml-2"><ClosureBasis c={t.closure} ours={ours} /></span> : null}
      <div style={{ ...secondary, fontSize: 13, marginTop: 2 }}><Standing t={t} /></div>
      <div style={{ ...muted, fontSize: 13, marginTop: 2 }}>{t.question}</div>
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

  return (
    <>
      {/* RANK FIRST, THEN GROUPS (§14c). A rank serves the reader who does not know what
          they are looking for; a group serves the reader who does. Group first and the
          most important matter in town sits third inside a collapsed section. */}
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
                borderColor: 'var(--grid)',
                background: on ? 'var(--text-primary)' : 'transparent',
                color: on ? 'var(--surface-1)' : 'inherit',
              }}>{groupLabel(g)} <span className="opacity-60">{ts.length}</span></button>
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
          <Body><strong><Standing t={t} /></strong></Body>
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
  const go = (next: string | null) => {
    window.history.pushState({}, '', next ? `/threads/${next}` : '/threads')
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

import { useMemo, useState } from 'react'
import { threadIdFromPath, type Tab } from '../routes'
import { Body, H2, H3, ReportShell, useReport } from '../components/report'

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
  boards: string; started: string; closes: string; status: string; resolved_on: string; note: string
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

/** THE EPISTEMIC LABEL, AND IT SURVIVES EVERY TRIM (rule 7b). A reader who takes a
 *  caption-derived tally for the Clerk's record has been misled, which is worse than any
 *  sentence cut to make room. */
function Basis({ c }: { c: Closure }) {
  const official = c.basis === 'official'
  return (
    <span style={{
      fontSize: 11, fontWeight: 600, letterSpacing: '.02em', padding: '1px 6px', borderRadius: 4,
      border: '1px solid', borderColor: official ? 'var(--ok, #2f7d4f)' : 'var(--warn, #9a6b00)',
      color: official ? 'var(--ok, #2f7d4f)' : 'var(--warn, #9a6b00)', whiteSpace: 'nowrap',
    }}>
      {official ? 'THE CLERK’S RECORD' : 'AS HEARD — MACHINE CAPTIONS'}
    </span>
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

function Card({ t, onGo }: { t: Thread; onGo: (id: string) => void }) {
  return (
    <li className="avoid-break" style={{ padding: '10px 0', borderTop: '1px solid var(--border, #e5e5e5)' }}>
      <a href={`/threads/${t.id}`} onClick={e => { e.preventDefault(); onGo(t.id) }}
        style={{ fontWeight: 600, textDecoration: 'none' }}>{t.label}</a>
      {t.closure ? <span style={{ marginLeft: 8 }}><Basis c={t.closure} /></span> : null}
      <div style={{ ...secondary, fontSize: 13, marginTop: 2 }}><Standing t={t} /></div>
      <div style={{ ...muted, fontSize: 13, marginTop: 2 }}>{t.question}</div>
    </li>
  )
}

function Landing({ d, onGo }: { d: Payload; onGo: (id: string) => void }) {
  const [group, setGroup] = useState<string | null>(null)
  const open = d.threads.filter(t => t.status === 'open')
  const resolved = d.threads.filter(t => t.status === 'resolved')
  const lapsed = d.threads.filter(t => t.status === 'lapsed')
  const groups = useMemo(() => {
    const m = new Map<string, Thread[]>()
    for (const t of d.threads) for (const g of groupsOf(t)) m.set(g, [...(m.get(g) ?? []), t])
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
  const shown = group ? d.threads.filter(t => groupsOf(t).includes(group)) : null

  return (
    <>
      {/* RANK FIRST, THEN GROUPS (§14c). A rank serves the reader who does not know what
          they are looking for; a group serves the reader who does. Group first and the
          most important matter in town sits third inside a collapsed section. */}
      <H2>What is moving now</H2>
      <ul style={{ listStyle: 'none', padding: 0, margin: '0 0 6px' }}>
        {open.slice(0, 4).map(t => <Card key={t.id} t={t} onGo={onGo} />)}
      </ul>
      <Body><span style={{ ...muted, fontSize: 12 }}>Ordered by {d.coverage.rank_basis}.</span></Body>

      <H2>By what it is about</H2>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, margin: '0 0 12px' }}>
        {groups.map(([g, ts]) => (
          <button key={g} onClick={() => setGroup(group === g ? null : g)}
            style={{
              fontSize: 13, padding: '4px 10px', borderRadius: 999, cursor: 'pointer',
              border: '1px solid var(--border, #ddd)',
              background: group === g ? 'var(--text-primary, #222)' : 'transparent',
              color: group === g ? 'var(--bg, #fff)' : 'inherit',
            }}>{groupLabel(g)} <span style={{ opacity: .6 }}>{ts.length}</span></button>
        ))}
      </div>
      {shown
        ? <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
            {shown.map(t => <Card key={t.id} t={t} onGo={onGo} />)}
          </ul>
        : groups.map(([g, ts]) => (
            <div key={g} style={{ marginBottom: 14 }}>
              <H3>{groupLabel(g)}</H3>
              <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
                {ts.map(t => <Card key={t.id} t={t} onGo={onGo} />)}
              </ul>
            </div>
          ))}

      {/* Resolved grows forever, so it is grouped by fiscal year first — "what did Town
          Meeting settle in FY26" is the question people bring to an archive (§14c). */}
      <H2>Settled</H2>
      {byFy.length === 0 ? <Body>Nothing settled yet in the readable record.</Body> : null}
      {byFy.map(([fy, ts]) => (
        <div key={fy} style={{ marginBottom: 12 }}>
          <H3>FY{fy}</H3>
          <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
            {ts.map(t => <Card key={t.id} t={t} onGo={onGo} />)}
          </ul>
        </div>
      ))}

      {lapsed.length > 0 ? (
        <>
          <H2>Went quiet</H2>
          <Body>Nobody decided these. They are not settled — they stopped being discussed,
            and some stopped only because the record did.</Body>
          <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
            {lapsed.map(t => <Card key={t.id} t={t} onGo={onGo} />)}
          </ul>
        </>
      ) : null}

      <H2>What we looked at and did not open</H2>
      <Body>A candidate rejected is recorded with its reason, so <em>we looked and said
        no</em> stays distinguishable from <em>nobody looked</em>.</Body>
      <ul style={{ fontSize: 13, ...secondary, paddingLeft: 18 }}>
        {d.declined.map((x, i) => (
          <li key={i} style={{ marginBottom: 4 }}>
            <strong>{x.candidate}</strong> — {x.reason}
            {x.revisit_if && x.revisit_if !== 'never'
              ? <span style={muted}> · revisit if {x.revisit_if}</span> : null}
          </li>
        ))}
      </ul>
    </>
  )
}

/** ONE THREAD. The order flips on status (§14d): an open thread's most valuable line is
 *  WHAT HAPPENS NEXT, because it is the only thing a resident can act on; a settled one's
 *  is HOW IT ENDED. Putting the chronology first on either is writing the page in the
 *  order it was built. */
function One({ t, d, onGo }: { t: Thread; d: Payload; onGo: (id: string | null) => void }) {
  const chron = [...t.chronology].reverse()
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
            <Basis c={t.closure} />
          </Body>
          <blockquote style={{
            margin: '8px 0', padding: '8px 12px', borderLeft: '3px solid var(--border, #ddd)',
            fontSize: 14, ...secondary,
          }}>{t.closure.quote}</blockquote>
          {t.closure.fincom || t.closure.select_board ? (
            <Body><span style={{ ...muted, fontSize: 13 }}>
              Finance Committee: {t.closure.fincom || '—'} · Select Board: {t.closure.select_board || '—'}
            </span></Body>
          ) : null}
          {t.closure.caveat ? (
            <Body><span style={{ ...muted, fontSize: 13 }}>{t.closure.caveat}</span></Body>
          ) : null}
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

      {t.note ? (
        <>
          <H2>What this does not show</H2>
          <Body><span style={secondary}>{t.note}</span></Body>
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
  const open = d ? d.threads.filter(x => x.status === 'open').length : 0
  const settled = d ? d.threads.filter(x => x.status === 'resolved').length : 0

  return (
    <ReportShell
      tab={TAB}
      title={t ? t.label : 'What the town is deciding now'}
      standfirst={t
        ? t.question
        : `${open} things still open, ${settled} settled. Each one tracked across every board that touched it.`}
      err={err}
      loading={!d}
      dataUrl={`/data/${DATA}`}
      sourceUrl="/notes/process/THREADS-MODEL.md"
    >
      {d ? (t ? <One t={t} d={d} onGo={go} /> : <Landing d={d} onGo={go} />) : null}
    </ReportShell>
  )
}

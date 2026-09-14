import { useState } from 'react'
import { boardSlugFromPath, type Tab } from '../routes'
import { Body, H2, ReportShell, useReport } from '../components/report'

const TAB: Tab = 'boards'
const DATA = '/data/boards.json'

/** THE BOARDS, ONE PAGE EACH. TJ, 14 September 2026: "pages specifically built for each
 *  board, committee so we can see upcoming, recent, meeting minutes, etc all in one place
 *  for them, including all votes in recency order. We can also build budget season
 *  expected timelines from past timelines."
 *
 *  /boards is the index; /boards/<slug> is one board. Everything is a JOIN over payloads
 *  other generators wrote (build_boards.py); nothing on these pages is written here. The
 *  three budget boards come first and carry the most; every other board gets the same
 *  page with whatever the town has posted for it. */

type Upcoming = { date: string; days_away: number; agenda_url: string; hook?: string | null; time?: string | null; where?: string | null; attend?: string | null; important?: unknown; items?: { agenda_line: string; why_it_matters?: string; important?: boolean }[] | null }
type Recent = { date: string; agenda_url?: string | null; agenda_doc?: string | null; minutes_url?: string | null; minutes_doc?: string | null; video_url?: string | null; transcript: boolean; captions_disabled: boolean; ours?: { slug: string; headline?: string | null; digest?: string | null; votes?: number; reconciled?: boolean; discrepancies?: number } | null }
type Vote = { date: string; t?: number | null; motion?: string; outcome?: string; procedural: boolean; moved_by?: string | null; page: string; video_url: string }
type Cal = { key: string; label: string; cycles: { fy: number; dates: string[] }[]; earliest: string; latest: string; typical_first: string; typical_last: string; meetings: number }
type Page = { url: string; source: 'town' | 'district'; overview: string; charter_ref: string; meets: string; members: string[]; facebook: string | null; facebook_scope: string; mirror: string; fetched_at: string; charter_url: string }
type Board = {
  slug: string; name: string; the_three: boolean; page?: Page | null
  counts: { agendas: number; minutes: number; recordings: number; transcripts: number; captions_disabled: number; our_minutes: number; votes: number; first: string | null; last: string | null }
  upcoming: Upcoming[]; recent: Recent[]; votes: Vote[]
  time_by_tag: { tag: string; label: string; seconds: number; share: number | null }[]; time_meetings: number; time_span_s: number
  calendar: Cal[]; calendar_cycles: number[]
  urls: { minutes_text: string; what_was_said: string; this_week: string }
}
type Payload = { about: string; as_of: string; boards: Board[]; the_three: string[]; cycles: number }

const n0 = (n: number) => n.toLocaleString('en-US')
const pct = (x: number) => `${Math.round(x * 100)}%`
const hours = (s: number) => `${(s / 3600).toFixed(1)} h`
const FY = (fy: number) => 'FY' + String(fy).slice(2)
const dateText = (d: string) => new Date(d + 'T12:00:00').toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' })
const mmdd = (d: string) => new Date(d + 'T12:00:00').toLocaleDateString('en-US', { month: 'short', day: 'numeric' })

export function Boards() {
  const { d, err } = useReport<Payload>('boards.json')
  const slug = boardSlugFromPath(window.location.pathname)
  const b = d && slug ? d.boards.find(x => x.slug === slug) : null
  if (!d) return <ReportShell tab={TAB} title={slug ? 'A board' : 'The boards'} err={err} loading={!err} dataUrl={DATA} />
  if (slug && !b) {
    return (
      <ReportShell tab={TAB} title="No such board" dataUrl={DATA}>
        <Body>The address <code>/boards/{slug}</code> names no board. The index is <a className="underline" href="/boards">/boards</a>.</Body>
      </ReportShell>
    )
  }
  return b ? <BoardPage b={b} d={d} /> : <Index d={d} />
}

function Index({ d }: { d: Payload }) {
  const three = d.boards.filter(b => b.the_three)
  const rest = d.boards.filter(b => !b.the_three)
  const Card = ({ b }: { b: Board }) => (
    <a href={`/boards/${b.slug}`} className="card block p-4 transition-opacity hover:opacity-90">
      <p className="text-[15px] font-bold leading-snug" style={{ color: 'var(--series-cost)' }}>{b.name} &rarr;</p>
      <p className="text-xs mt-1.5 tnum" style={{ color: 'var(--text-secondary)' }}>
        {b.upcoming.length ? <span className="font-semibold" style={{ color: 'var(--text-primary)' }}>next {mmdd(b.upcoming[0].date)} · </span> : null}
        {n0(b.counts.agendas)} agendas · {n0(b.counts.minutes)} minutes · {n0(b.counts.recordings)} recordings{b.counts.our_minutes ? ` · ${n0(b.counts.our_minutes)} of ours, ${n0(b.counts.votes)} votes` : ''}
      </p>
    </a>
  )
  return (
    <ReportShell tab={TAB} title="The boards — each one, in one place"
      standfirst={`${d.boards.length} boards and committees the town posts for. What is coming, what happened, every vote we have minutes for, where the time goes, and when budget season lands — one page each.`}
      dataUrl={DATA}>
      <H2>The three that set the school budget</H2>
      <div className="grid gap-3 mt-4 sm:grid-cols-3">{three.map(b => <Card key={b.slug} b={b} />)}</div>
      <H2>Every other board</H2>
      <div className="grid gap-3 mt-4 sm:grid-cols-2 lg:grid-cols-3">{rest.map(b => <Card key={b.slug} b={b} />)}</div>
      <p className="text-xs mt-6" style={{ color: 'var(--text-muted)' }}>As of {d.as_of}. Counts are what the town has posted to its AgendaCenter and its YouTube channel, plus the minutes this project has written from the recordings.</p>
    </ReportShell>
  )
}

function BoardPage({ b, d }: { b: Board; d: Payload }) {
  const [allVotes, setAllVotes] = useState(false)
  const substantive = b.votes.filter(v => !v.procedural)
  const shown = allVotes ? b.votes : substantive
  const c = b.counts
  return (
    <ReportShell tab={TAB} title={b.name}
      standfirst={<>{c.first ? `Posted since ${c.first.slice(0, 4)}: ` : ''}{n0(c.agendas)} agendas, {n0(c.minutes)} sets of minutes, {n0(c.recordings)} recordings{c.our_minutes ? `, ${n0(c.our_minutes)} meetings with our minutes and ${n0(c.votes)} votes on the record` : ''}. <a className="underline" href="/boards">All boards</a>.</>}
      dataUrl={DATA}>

      {/* ------------------------------------------------------- what it is, and links */}
      {b.page && (
        <div className="card p-4 mt-6 max-w-3xl">
          <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm">
            <a className="underline font-semibold" href={b.page.url}>{b.page.source === 'district' ? 'the district’s page for this board' : 'the town’s page for this board'} ↗</a>
            {b.page.facebook && <a className="underline" href={b.page.facebook}>{b.page.facebook_scope === 'board' ? 'its Facebook page' : 'the town’s Facebook page'} ↗</a>}
            <a className="underline" href={b.page.charter_url}>the Charter and bylaws ↗</a>
            <a className="underline" href={b.page.mirror} style={{ color: 'var(--text-muted)' }}>our copy, {b.page.fetched_at}</a>
          </div>
          {b.page.overview ? (
            <blockquote className="text-sm mt-3 leading-relaxed" style={{ color: 'var(--text-secondary)', borderLeft: '3px solid var(--grid)', paddingLeft: 12 }}>
              {b.page.overview.split('\n').map((p, i) => <p key={i} className={i ? 'mt-2' : ''}>{p}</p>)}
            </blockquote>
          ) : (
            <p className="text-sm mt-3" style={{ color: 'var(--text-muted)' }}>The {b.page.source === 'district' ? 'district’s' : 'town’s'} page lists the members and the meetings and carries no statement of what the board is for; the Charter and bylaws do.</p>
          )}
          <div className="grid gap-x-8 gap-y-2 mt-3 sm:grid-cols-2 text-sm">
            {b.page.charter_ref && <div><span className="text-[10px] font-bold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>established by</span><div>{b.page.charter_ref}</div></div>}
            {b.page.meets && <div><span className="text-[10px] font-bold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>meets</span><div style={{ whiteSpace: 'pre-line' }}>{b.page.meets}</div></div>}
            {b.page.members.length > 0 && <div className="sm:col-span-2"><span className="text-[10px] font-bold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>members, as posted</span><ul className="mt-0.5">{b.page.members.map((m, i) => <li key={i}>{m}</li>)}</ul></div>}
          </div>
          {b.page.facebook_scope !== 'board' && <p className="text-xs mt-3" style={{ color: 'var(--text-muted)' }}>No Facebook page of its own is linked from this board’s page; the town’s is. Facebook cannot be searched by script, so a page that exists unlinked would not be found here.</p>}
        </div>
      )}

      {/* ---------------------------------------------------------------- upcoming */}
      <H2>Coming up</H2>
      {b.upcoming.length === 0 ? (
        <p className="text-sm mt-2" style={{ color: 'var(--text-secondary)' }}>No agenda posted for a future date, as of {d.as_of}. Agendas usually appear two days before a meeting.</p>
      ) : b.upcoming.map(u => (
        <div key={u.date} className="card p-4 mt-3">
          <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
            <span className="font-bold">{dateText(u.date)}</span>
            {u.time && <span className="text-xs px-2 py-0.5 rounded" style={{ background: 'var(--surface-3)' }}>{u.time}</span>}
            {u.where && <span className="text-xs px-2 py-0.5 rounded" style={{ background: 'var(--surface-3)' }}>{u.where}</span>}
            {u.attend && <span className="text-xs px-2 py-0.5 rounded" style={{ background: 'var(--surface-3)' }}>{u.attend}</span>}
            <span className="text-xs" style={{ color: 'var(--text-muted)' }}>in {u.days_away} day{u.days_away === 1 ? '' : 's'}</span>
          </div>
          {u.hook && <p className="text-[15px] mt-2">{u.hook}</p>}
          {u.items && u.items.length > 0 && (
            <details className="mt-2 text-sm">
              <summary className="cursor-pointer" style={{ color: 'var(--text-secondary)' }}>The agenda, item by item</summary>
              <ul className="mt-2 space-y-1.5">{u.items.map((it, i) => (
                <li key={i} style={{ fontWeight: it.important ? 600 : 400 }}>{it.agenda_line}{it.why_it_matters ? <span style={{ color: 'var(--text-muted)' }}> — {it.why_it_matters}</span> : null}</li>))}</ul>
            </details>
          )}
          <a className="text-xs underline mt-2 inline-block" style={{ color: 'var(--text-muted)' }} href={u.agenda_url}>the posted agenda</a>
        </div>
      ))}

      {/* ------------------------------------------------------------------ recent */}
      <H2>Recent meetings</H2>
      <div className="overflow-x-auto mt-3">
        <table className="text-sm w-full" style={{ minWidth: 720 }}>
          <thead><tr className="text-[10px] font-bold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>
            <th className="text-left py-1.5 pr-3">date</th><th className="text-left py-1.5 pr-3">agenda</th><th className="text-left py-1.5 pr-3">official minutes</th><th className="text-left py-1.5 pr-3">recording</th><th className="text-left py-1.5">our minutes</th></tr></thead>
          <tbody>{b.recent.map(r => (
            <tr key={r.date} style={{ borderTop: '1px solid var(--grid)' }}>
              <td className="py-2 pr-3 tnum font-semibold whitespace-nowrap align-top">{mmdd(r.date)} {r.date.slice(0, 4)}</td>
              <td className="py-2 pr-3 align-top">{r.agenda_doc ? <a className="underline" href={r.agenda_doc}>agenda</a> : <span style={{ color: 'var(--text-muted)' }}>—</span>}</td>
              <td className="py-2 pr-3 align-top">{r.minutes_doc ? <a className="underline" href={r.minutes_doc}>minutes</a> : <span style={{ color: 'var(--text-muted)' }}>not yet</span>}</td>
              <td className="py-2 pr-3 align-top">{r.video_url ? <a className="underline" href={r.video_url}>video</a> : <span style={{ color: 'var(--text-muted)' }}>—</span>}{r.video_url && r.captions_disabled ? <span className="text-xs" style={{ color: 'var(--text-muted)' }}> · no captions</span> : r.video_url && !r.transcript ? <span className="text-xs" style={{ color: 'var(--text-muted)' }}> · no transcript yet</span> : null}</td>
              <td className="py-2 align-top">{r.ours ? <><a className="underline font-semibold" href={`/what-was-said/${r.ours.slug}`}>{r.ours.headline || 'our minutes'}</a><span className="text-xs" style={{ color: 'var(--text-muted)' }}> · {r.ours.votes ?? 0} votes{r.ours.reconciled ? (r.ours.discrepancies ? ` · ${r.ours.discrepancies} difference${r.ours.discrepancies === 1 ? '' : 's'} from the official minutes` : ' · agrees with the official minutes') : ''}</span></> : r.transcript ? <span className="text-xs" style={{ color: 'var(--text-muted)' }}>transcript held; minutes not yet written</span> : <span style={{ color: 'var(--text-muted)' }}>—</span>}</td>
            </tr>))}</tbody>
        </table>
      </div>
      <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>The last {b.recent.length} dates the town posted anything for this board. Every agenda and set of minutes, as text: <a className="underline" href={b.urls.minutes_text}>{b.urls.minutes_text}</a>.</p>

      {/* ------------------------------------------------------------------- votes */}
      {b.votes.length > 0 && (
        <>
          <H2>Every vote on the record, newest first</H2>
          <p className="text-sm mt-1" style={{ color: 'var(--text-secondary)' }}>
            From our minutes of the recordings — {n0(substantive.length)} substantive, {n0(b.votes.length - substantive.length)} procedural (accepting minutes, adjourning).
            <button className="underline ml-2" onClick={() => setAllVotes(!allVotes)}>{allVotes ? 'hide procedural' : 'show all'}</button>
          </p>
          <div className="overflow-x-auto mt-3">
            <table className="text-sm w-full" style={{ minWidth: 760 }}>
              <thead><tr className="text-[10px] font-bold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>
                <th className="text-left py-1.5 pr-3">date</th><th className="text-left py-1.5 pr-3">motion</th><th className="text-left py-1.5 pr-3">outcome</th><th className="text-left py-1.5">in the video</th></tr></thead>
              <tbody>{shown.map((v, i) => (
                <tr key={i} style={{ borderTop: '1px solid var(--grid)', color: v.procedural ? 'var(--text-muted)' : undefined }}>
                  <td className="py-1.5 pr-3 tnum whitespace-nowrap align-top">{mmdd(v.date)} {v.date.slice(0, 4)}</td>
                  <td className="py-1.5 pr-3 align-top" style={{ minWidth: 320 }}>{v.motion}{v.moved_by ? <span className="text-xs" style={{ color: 'var(--text-muted)' }}> — moved by {v.moved_by}</span> : null}</td>
                  <td className="py-1.5 pr-3 align-top font-semibold" style={{ maxWidth: 220, color: (v.outcome || '').startsWith('pass') ? 'var(--status-good)' : (v.outcome || '').startsWith('fail') ? 'var(--status-critical)' : 'var(--text-muted)' }}>{v.outcome}</td>
                  <td className="py-1.5 align-top whitespace-nowrap"><a className="underline" href={v.video_url}>{v.t != null ? `${Math.floor(v.t / 60)}:${String(v.t % 60).padStart(2, '0')}` : 'video'}</a> · <a className="underline" href={v.page}>minutes</a></td>
                </tr>))}</tbody>
            </table>
          </div>
          <p className="text-xs mt-1 max-w-3xl" style={{ color: 'var(--text-muted)' }}>Written by a language model from machine captions: a motion is as heard, an outcome “not audible” is a finding about the recording. Where the town has published minutes, those are the record; ours link to the second in the video so anyone can check.</p>
        </>
      )}

      {/* -------------------------------------------------------------------- time */}
      {b.time_by_tag.length > 0 && (
        <>
          <H2>Where this board’s time goes</H2>
          <p className="text-sm mt-1" style={{ color: 'var(--text-secondary)' }}>{hours(b.time_span_s)} of discussion across the {b.time_meetings} recorded meetings we have minutes for, by topic. A topic can overlap another, so the shares can sum past 100%.</p>
          <div className="mt-3 max-w-3xl">{b.time_by_tag.map(t => (
            <div key={t.tag} className="py-1.5 text-sm" style={{ borderTop: '1px solid var(--grid)' }}>
              <div className="flex items-baseline justify-between gap-3"><span className="font-semibold">{t.label}</span><span className="tnum shrink-0">{hours(t.seconds)}{t.share != null ? ` · ${pct(t.share)}` : ''}</span></div>
              <div className="h-1.5 rounded-full mt-1" style={{ background: 'var(--surface-3)' }}><div className="h-full rounded-full" style={{ width: `${(t.seconds / b.time_by_tag[0].seconds) * 100}%`, background: 'var(--series-cost)' }} /></div>
            </div>))}</div>
        </>
      )}

      {/* ---------------------------------------------------------------- calendar */}
      {b.calendar.length > 0 && (
        <>
          <H2>When budget season lands on this board</H2>
          <p className="text-sm mt-1 max-w-3xl" style={{ color: 'var(--text-secondary)' }}>Measured from this board’s own posted agendas over the last {b.calendar_cycles.length} budget cycles (July to June): the dates each subject appeared. The “expect” column is the typical first and last date across those cycles — a scheduled subject, not a decision.</p>
          <div className="overflow-x-auto mt-3">
            <table className="text-sm" style={{ minWidth: 640 }}>
              <thead><tr className="text-[10px] font-bold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>
                <th className="text-left py-1.5 pr-4">subject</th><th className="text-left py-1.5 pr-4">expect</th>{b.calendar_cycles.map(fy => <th key={fy} className="text-left py-1.5 pr-3">{FY(fy)}</th>)}</tr></thead>
              <tbody>{b.calendar.map(cl => (
                <tr key={cl.key} style={{ borderTop: '1px solid var(--grid)' }}>
                  <td className="py-2 pr-4 font-semibold align-top">{cl.label}</td>
                  <td className="py-2 pr-4 align-top whitespace-nowrap tnum">{cl.typical_first}{cl.typical_first !== cl.typical_last ? ` → ${cl.typical_last}` : ''}</td>
                  {b.calendar_cycles.map(fy => { const cy = cl.cycles.find(x => x.fy === fy); return <td key={fy} className="py-2 pr-3 align-top text-xs tnum" style={{ color: 'var(--text-secondary)' }}>{cy ? cy.dates.map(mmdd).join(', ') : '—'}</td> })}
                </tr>))}</tbody>
            </table>
          </div>
          <p className="text-xs mt-1 max-w-3xl" style={{ color: 'var(--text-muted)' }}>A cycle is named for the fiscal year it builds: {FY(b.calendar_cycles[b.calendar_cycles.length - 1])} is the budget being built now. Read off the agenda text with a word search, so a subject named differently on an agenda is missed and one mentioned in passing is counted.</p>
        </>
      )}

      <p className="text-xs mt-8" style={{ color: 'var(--text-muted)' }}>This week’s listing for this board: <a className="underline" href={b.urls.this_week}>this week</a>. All recorded meetings with our minutes: <a className="underline" href={b.urls.what_was_said}>what was said</a>. As of {d.as_of}.</p>
    </ReportShell>
  )
}

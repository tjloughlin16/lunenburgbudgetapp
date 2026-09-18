import type { Tab } from '../routes'
import { ReportShell, useReport, H2, MoreReports } from '../components/report'
import { BoardsThisWeek, THE_THREE, daysFromToday, todayIso } from '../components/BoardsThisWeek'

const TAB: Tab = 'thisweek'
const FEED = 'meeting-feed.json'
const NEW = 'whats-new.json'

/** THIS WEEK IN TOWN: what is coming, and what just appeared.
 *
 *  QUEUE item 12. Every figure on this page is an ANNOUNCEMENT, not a measurement — what
 *  our watchers could see on the town's website and channel on the day they looked. The
 *  payloads say so in their own `category` field and the page says so at the top, because
 *  a wrong meeting date beside a budget figure teaches a reader the wrong lesson about
 *  the budget figure.
 *
 *  `first_seen` is OUR crawl date, never the town's posting date — the AgendaCenter
 *  publishes none — so a lag is an upper bound and is named that way.
 *
 *  Rule 7a: the thing first. The next seven days, then what was just posted, then our
 *  minutes of the recordings, then the caveats. */

type Upcoming = { agenda_url: string; board: string; board_slug: string; date: string; days_away: number; file_id: string }
type Announced = { board: string; board_slug: string; first_seen: string; kind: string; meeting_date: string; url: string; days_after_meeting_upper_bound: number | null }
type Awaiting = { agenda_url: string; board: string; board_slug: string; date: string; days_since_meeting: number }
type Feed = {
  as_of: string
  as_of_means: string
  first_seen_means: string
  upcoming: { count: number; horizon_days: number; meetings: Upcoming[]; next_7_days: Upcoming[]; basis: string }
  announced: { count: number; items: Announced[]; basis: string }
  awaiting_minutes: { count: number; meetings: Awaiting[]; oldest: unknown; window_days: number; basis: string }
  recent: { window_days: number; count: number; meetings: Recent[] }
  runs: { ran: string; new_agendas: number; new_minutes: number; boards_listed: number }[]
}
type Video = { first_seen: string; video_id: string; title: string; url: string; uploaded: string }
type Ours = { written: string; board: string; board_slug: string; date: string; url: string; votes: number }
type FeedItem = { first_seen: string; source: string; kind: string; published: string; title: string; link: string }
type Recent = { board: string; board_slug: string; date: string; last_activity: string
  agenda: { url: string; first_seen: string } | null
  minutes: { url: string; first_seen: string; days_after_meeting_upper_bound: number | null; ocr: boolean } | null
  recording: { url: string; uploaded: string; first_seen: string; captions_disabled: boolean } | null
  transcript: { fetched: string } | null
  our_minutes: { url: string; written: string; headline: string; votes: number } | null
  official_votes: number | null
  complete: number; complete_of: number; complete_pct: number; missing: string[]; part_of: string | null }
type WhatsNew = {
  as_of: string
  window_days: number
  feeds?: FeedItem[]
  documents?: { first_seen: string; folder: string; label: string; upstream: string; url: string }[]
  feed_sources?: { watched: number; without_a_feed: string[] }
  videos: Video[]
  our_minutes: Ours[]
  transcripts: { board_slug: string; date: string; video_id: string; fetched: string }[]
  counts: Record<string, number>
}

/** THE ARTIFACT COLUMNS. TJ, 18 September 2026: "align the 'Recent activity' artifacts to
 *  the right. Show gaps as gaps (grayed out / n/a) but all recording links line up
 *  vertically." So every row draws the same five slots in the same order, and a slot we
 *  hold nothing for is drawn muted rather than skipped -- which is what makes the gaps
 *  legible down the column instead of invisible. */
const SLOTS = ['agenda', 'minutes', 'recording', 'transcript', 'our minutes'] as const
const cell = 'block text-[11px] text-center rounded px-1 py-0.5 border whitespace-nowrap'

function Slot({ label, href, title, tone, had }: { label: string; href?: string | null; title?: string; tone?: string; had: boolean }) {
  const style = had
    ? { borderColor: tone ?? 'var(--grid)', color: tone ?? 'var(--text-primary)' }
    : { borderColor: 'transparent', color: 'var(--text-muted)', opacity: 0.55 }
  return href && had
    ? <a className={cell} style={style} href={href} title={title} target={href.startsWith('http') ? '_blank' : undefined} rel="noreferrer">{label}</a>
    : <span className={cell} style={style} title={title}>{had ? label : '—'}</span>
}

function ActivityRow({ a }: { a: Recent }) {
  const ours = a.our_minutes
  // The vote count is a MEASURE of the meeting, not a label on a link: the town's
  // minutes are the record where they exist, ours where they do not.
  const votes = a.official_votes ?? (ours ? ours.votes : null)
  return (
    <li className="card p-3">
      <div className="sm:flex sm:items-start sm:gap-4">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap gap-x-3 items-baseline">
            <a className="font-semibold hover:underline" href={`/boards/${a.board_slug}`}>{a.board}</a>
            <span style={{ color: 'var(--text-secondary)' }}>{longDate(a.date)}</span>
            <span className="text-[11px] tnum" title={`The record of this meeting: ${a.complete} of ${a.complete_of} — the town's listing, agenda, minutes and recording, and our transcript, minutes and reading of its votes.${a.missing.length ? ' Missing: ' + a.missing.join(', ') + '.' : ''}`}
              style={{ color: a.complete_pct >= 85 ? 'var(--status-good)' : a.complete_pct >= 50 ? 'var(--text-muted)' : 'var(--status-critical)' }}>{a.complete}/{a.complete_of} of the record</span>
            {votes !== null && <span className="text-[11px] tnum" style={{ color: 'var(--text-muted)' }} title={a.official_votes != null ? 'Votes read from the town’s minutes' : 'Substantive votes in our minutes of the recording'}>{votes} vote{votes === 1 ? '' : 's'}</span>}
          </div>
          {/* THE SUMMARY TITLE, where our minutes exist: what the meeting did, on the row. */}
          {ours && ours.headline && (
            <p className="text-[13.5px] mt-1 leading-snug">{ours.headline}{' '}
              <a className="text-[11.5px] underline" style={{ color: 'var(--text-muted)' }} href={ours.url}>our minutes</a></p>
          )}
        </div>
        {/* Right, and the same five slots on every row so the eye can run down a column. */}
        <div className="grid grid-cols-5 gap-1 mt-2 sm:mt-0 sm:w-[21rem] sm:shrink-0">
          <Slot label="agenda" had={Boolean(a.agenda)} href={a.agenda?.url} title={a.agenda ? 'The agenda the town posted' : 'No agenda in the town’s listing'} />
          <Slot label="minutes" had={Boolean(a.minutes)} href={a.minutes?.url} tone="var(--status-good)"
            title={a.minutes ? `The town’s minutes${a.minutes.days_after_meeting_upper_bound != null ? `, seen within ${a.minutes.days_after_meeting_upper_bound} days of the meeting` : ''}${a.minutes.ocr ? '; read here by OCR' : ''}` : 'The town has posted no minutes for this meeting'} />
          <Slot label="video" had={Boolean(a.recording)} href={a.recording?.url} tone="var(--series-revenue, #b5540f)"
            title={a.recording ? (a.recording.captions_disabled ? 'On the town’s channel; captions are disabled' : 'On the town’s channel') : 'This board’s meetings are not recorded'} />
          <Slot label="captions" had={Boolean(a.transcript)} tone="var(--text-secondary)"
            title={a.transcript ? 'We hold machine captions of the recording' : 'No captions held'} />
          <Slot label="ours" had={Boolean(ours)} href={ours?.url} tone="var(--series-cost)"
            title={ours ? 'Our minutes, written from the recording' : 'We have not written minutes for this meeting'} />
        </div>
      </div>
    </li>
  )
}

function longDate(iso: string) {
  const [y, m, d] = iso.split('-').map(Number)
  return new Date(y, m - 1, d).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })
}

export function ThisWeek() {
  const feed = useReport<Feed>(FEED)
  const fresh = useReport<WhatsNew>(NEW)
  const f = feed.d, n = fresh.d
  if (!f) {
    return <ReportShell tab={TAB} title="This week in town" err={feed.err} loading={!feed.err} dataUrl={'/data/' + FEED} />
  }
  // By the reader's clock, not the payload's: a page read two days after its build must not
  // list a meeting that has happened as coming up (the 'tomorrow' that was today, 15 Sep).
  const week = f.upcoming.meetings.filter(m => m.date >= todayIso() && daysFromToday(m.date) < 7)
  const later = f.upcoming.meetings.filter(m => m.date >= todayIso() && daysFromToday(m.date) >= 7)
  return (
    <ReportShell tab={TAB} kicker="This week" title="This week in town"
      standfirst={`Meetings coming up, and what the town has posted for recent ones — as seen on ${f.as_of}.`}
      dataUrl={'/data/' + FEED}>

      <H2>Select Board, Finance Committee, School Committee</H2>
      <BoardsThisWeek days={14} />

      <H2>Upcoming meetings</H2>
      {(() => {
        const three = new Set(THE_THREE.map(t => t[0]))
        const others = week.filter(m => !three.has(m.board_slug))
        return others.length === 0
          ? <p className="text-sm" style={{ color: 'var(--text-muted)' }}>No other agenda posted for the next seven days.</p>
          : <ul className="text-sm space-y-1">
              {others.map(m => (
                <li key={m.file_id} className="flex flex-wrap gap-x-3 items-baseline">
                  <span className="tnum text-xs w-24 shrink-0" style={{ color: 'var(--text-secondary)' }}>{longDate(m.date)}</span>
                  <span>{m.board}</span>
                  <a className="text-xs underline" style={{ color: 'var(--text-muted)' }} href={m.agenda_url} target="_blank" rel="noreferrer">agenda</a>
                </li>
              ))}
            </ul>
      })()}
      {later.length > 0 && (
        <p className="text-xs mt-3" style={{ color: 'var(--text-muted)' }}>
          And within {f.upcoming.horizon_days} days: {later.map((m, i) => <span key={m.file_id}>{i ? '; ' : ''}{m.board} <a className="underline" href={m.agenda_url} target="_blank" rel="noreferrer">{longDate(m.date)}</a></span>)}.
        </p>
      )}

      {/* RECENT ACTIVITY, ONE ROW PER MEETING. TJ, 18 September 2026: "combine these 2
          sections, plus 'What happened — from the recordings' into one 'recent activity',
          showing each event and then each artifact that has been provided for the event."
          The row is the meeting; the chips are what exists for it -- the town's agenda,
          minutes and recording, our transcript and our minutes -- and where our minutes
          exist the headline sits on the row with the summary one click down. */}
      <H2>Recent activity</H2>
      {f.recent.meetings.length === 0
        ? <p className="text-sm" style={{ color: 'var(--text-muted)' }}>Nothing posted for a recent meeting in the last {f.recent.window_days} days.</p>
        : <>
            {/* The column labels once, over the list, rather than on every row. */}
            <div className="hidden sm:flex justify-end mb-1 pr-3">
              <div className="grid grid-cols-5 gap-1 w-[21rem]">
                {SLOTS.map(name => <span key={name} className="text-[9.5px] uppercase tracking-wide text-center" style={{ color: 'var(--text-muted)' }}>{name === 'our minutes' ? 'ours' : name}</span>)}
              </div>
            </div>
            <ol className="space-y-2">
              {f.recent.meetings.map(a => <ActivityRow key={a.board_slug + a.date} a={a} />)}
            </ol>
          </>}
      {f.awaiting_minutes.count > 0 && (
        <p className="text-xs mt-3" style={{ color: 'var(--text-muted)' }}>
          {f.awaiting_minutes.count} meetings in the last {f.awaiting_minutes.window_days} days have an agenda and no minutes yet.
          {' '}<a className="underline" href="/meeting-minutes">Our minutes from the recordings</a> cover some of them.
        </p>
      )}

      {n && (
        <>
          {/* FROM THE TOWN, AND THE COMMUNITY. QUEUE 13 and 14: link and attribute, never
              republish. The unsourced feeds are counted rather than hidden -- a youth
              league that only posts on Facebook is a gap, and a gap is shown. */}
          <H2>Notices from the town</H2>
          {(n.feeds || []).length === 0
            ? <p className="text-sm" style={{ color: 'var(--text-muted)' }}>Nothing new from the town&rsquo;s feeds in the last {n.window_days} days.</p>
            : <ul className="space-y-1.5">
                {(n.feeds || []).map(f => (
                  <li key={f.link} className="text-sm flex flex-wrap gap-x-3 items-baseline">
                    <span className="tnum text-xs w-24 shrink-0" style={{ color: 'var(--text-secondary)' }}>{f.published}</span>
                    <a className="underline" style={{ color: 'var(--series-cost)' }} href={f.link} target="_blank" rel="noreferrer">{f.title}</a>
                    <span className="text-xs" style={{ color: 'var(--text-muted)' }}>{f.source}</span>
                  </li>
                ))}
              </ul>}
          {(n.documents || []).length > 0 && (
            <>
              <h3 className="text-sm font-semibold mt-4">New documents</h3>
              <ul className="space-y-1.5 mt-1">
                {(n.documents || []).map(d => (
                  <li key={d.upstream} className="text-sm flex flex-wrap gap-x-3 items-baseline">
                    <span className="tnum text-xs w-24 shrink-0" style={{ color: 'var(--text-secondary)' }}>{d.first_seen}</span>
                    <a className="underline" style={{ color: 'var(--series-cost)' }} href={d.url}>{d.label}</a>
                    <span className="text-xs" style={{ color: 'var(--text-muted)' }}>{d.folder.replace(/-/g, ' ')} · <a className="underline" href={d.upstream} target="_blank" rel="noreferrer">publisher&rsquo;s copy</a></span>
                  </li>
                ))}
              </ul>
            </>
          )}
          {n.feed_sources && n.feed_sources.without_a_feed.length > 0 && (
            <p className="text-xs mt-2" style={{ color: 'var(--text-muted)' }}>
              {n.feed_sources.watched} feed{n.feed_sources.watched === 1 ? '' : 's'} watched. Not yet watchable, because they publish only on Facebook or by email: {n.feed_sources.without_a_feed.join(', ')}.
            </p>
          )}

        </>
      )}

      <div className="card p-4 mt-10 max-w-3xl">
        <p className="text-[10.5px] font-bold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>What this page is, and is not</p>
        <p className="text-sm mt-1" style={{ color: 'var(--text-secondary)' }}>
          An announcement, not a measurement: what our watchers could see on the town&rsquo;s
          website and YouTube channel on {f.as_of}. {f.first_seen_means} {f.as_of_means}
        </p>
        {f.runs.length > 0 && (
          <p className="text-xs mt-2" style={{ color: 'var(--text-muted)' }}>
            Last crawl {f.runs[f.runs.length - 1].ran}: {f.runs[f.runs.length - 1].boards_listed} boards listed,{' '}
            {f.runs[f.runs.length - 1].new_agendas} new agendas and {f.runs[f.runs.length - 1].new_minutes} new minutes seen.
          </p>
        )}
      </div>
      <MoreReports here={TAB} />
    </ReportShell>
  )
}

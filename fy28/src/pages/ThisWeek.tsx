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
  official_votes: number | null }
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

const chip = 'text-[11px] px-1.5 py-0.5 rounded border'
function ActivityRow({ a }: { a: Recent }) {
  const ours = a.our_minutes
  return (
    <li className="card p-3">
      <div className="flex flex-wrap gap-x-3 gap-y-1 items-baseline">
        <span className="font-semibold"><a className="hover:underline" href={`/boards/${a.board_slug}`}>{a.board}</a></span>
        <span style={{ color: 'var(--text-secondary)' }}>{longDate(a.date)}</span>
        <span className="flex flex-wrap gap-1.5">
          {a.agenda && <a className={chip} style={{ borderColor: 'var(--grid)' }} href={a.agenda.url} target="_blank" rel="noreferrer">agenda</a>}
          {a.minutes && <a className={chip} style={{ borderColor: 'var(--status-good)', color: 'var(--status-good)' }} href={a.minutes.url} target="_blank" rel="noreferrer">town&rsquo;s minutes{typeof a.minutes.days_after_meeting_upper_bound === 'number' ? ` · within ${a.minutes.days_after_meeting_upper_bound} days` : ''}{a.official_votes ? ` · ${a.official_votes} vote${a.official_votes === 1 ? '' : 's'}` : ''}</a>}
          {a.recording && <a className={chip} style={{ borderColor: 'var(--series-revenue, #b5540f)', color: 'var(--series-revenue, #b5540f)' }} href={a.recording.url} target="_blank" rel="noreferrer">&#9654; recording{a.recording.captions_disabled ? ' · captions off' : ''}</a>}
          {a.transcript && !ours && <span className={chip} style={{ borderColor: 'var(--grid)', color: 'var(--text-muted)' }}>transcript · minutes pending</span>}
          {ours && <a className={chip} style={{ borderColor: 'var(--series-cost)', color: 'var(--series-cost)' }} href={ours.url}>our minutes{ours.votes ? ` · ${ours.votes} vote${ours.votes === 1 ? '' : 's'}` : ''}</a>}
          {!a.minutes && !a.recording && !ours && <span className="text-[11px]" style={{ color: 'var(--text-muted)' }}>agenda only so far</span>}
        </span>
      </div>
      {ours && ours.headline && (
        <p className="text-sm mt-1.5 font-medium">{ours.headline} <a className="text-xs underline font-normal" style={{ color: 'var(--text-muted)' }} href={ours.url}>read our minutes</a></p>
      )}
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

      <H2>Every other board this week</H2>
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
        : <ol className="space-y-2">
            {f.recent.meetings.map(a => <ActivityRow key={a.board_slug + a.date} a={a} />)}
          </ol>}
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

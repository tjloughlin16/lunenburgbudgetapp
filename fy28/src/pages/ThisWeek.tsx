import type { Tab } from '../routes'
import { ReportShell, useReport, H2, MoreReports } from '../components/report'

const TAB: Tab = 'thisweek'
const FEED = 'meeting-feed.json'
const NEW = 'whats-new.json'
const NOTICES = 'notices.json'

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
  runs: { ran: string; new_agendas: number; new_minutes: number; boards_listed: number }[]
}
type Video = { first_seen: string; video_id: string; title: string; url: string; uploaded: string }
type Ours = { written: string; board: string; board_slug: string; date: string; url: string; votes: number }
type PreviewItem = { agenda_line: string; why_it_matters: string; kind: string; vote_expected?: boolean }
type Upcoming2 = { board: string; board_slug: string; date: string; days_away: number; when: string; where: string; how_to_attend: string; one_line: string; items: PreviewItem[]; nothing_of_note: boolean; agenda_url: string }
type Retro = { board: string; board_slug: string; date: string; url: string; summary: string; votes: number; transfers: number; tags: string[]; has_official_minutes: boolean }
type Notices = { as_of: string; upcoming: Upcoming2[]; retro: Retro[] }
type WhatsNew = {
  as_of: string
  window_days: number
  videos: Video[]
  our_minutes: Ours[]
  transcripts: { board_slug: string; date: string; video_id: string; fetched: string }[]
  counts: Record<string, number>
}

function longDate(iso: string) {
  const [y, m, d] = iso.split('-').map(Number)
  return new Date(y, m - 1, d).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })
}

export function ThisWeek() {
  const feed = useReport<Feed>(FEED)
  const fresh = useReport<WhatsNew>(NEW)
  const notices = useReport<Notices>(NOTICES)
  const f = feed.d, n = fresh.d, nt = notices.d
  const previewFor = (m: Upcoming) => nt?.upcoming.find(u => u.board_slug === m.board_slug && u.date === m.date)
  if (!f) {
    return <ReportShell tab={TAB} title="This week in town" err={feed.err} loading={!feed.err} dataUrl={'/data/' + FEED} />
  }
  const week = f.upcoming.next_7_days
  const later = f.upcoming.meetings.filter(m => !week.some(w => w.file_id === m.file_id))
  const minutes = f.announced.items.filter(i => i.kind === 'minutes')
  const agendas = f.announced.items.filter(i => i.kind === 'agenda' && i.meeting_date < f.as_of)
  return (
    <ReportShell tab={TAB} kicker="This week" title="This week in town"
      standfirst={`Meetings coming up, minutes just posted, recordings just published — as seen on ${f.as_of}.`}
      dataUrl={'/data/' + FEED}>

      <H2>Coming up</H2>
      {week.length === 0
        ? <p className="text-sm" style={{ color: 'var(--text-muted)' }}>No agenda posted for the next seven days.</p>
        : <ol className="space-y-2">
            {week.map(m => {
              const p = previewFor(m)
              return (
                <li key={m.file_id} className="card p-3">
                  <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
                    <span className="tnum text-xs font-semibold whitespace-nowrap w-24" style={{ color: 'var(--text-secondary)' }}>{longDate(m.date)}</span>
                    <span className="text-sm font-semibold flex-1 min-w-[12rem]">{m.board}</span>
                    <a className="text-xs underline" style={{ color: 'var(--series-cost)' }} href={m.agenda_url} target="_blank" rel="noreferrer">agenda</a>
                  </div>
                  {/* WHAT IS ON IT, for the three boards TJ watches: quoted from the agenda,
                      never a prediction. An agenda lists what MAY be discussed. */}
                  {p && (
                    <div className="mt-2 pl-0 sm:pl-[6.75rem]">
                      <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>{p.one_line}</p>
                      <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>{p.when}{p.where && p.where !== 'not stated' ? ` · ${p.where}` : ''}{p.how_to_attend ? ` · ${p.how_to_attend.split('.')[0]}` : ''}</p>
                      {p.items.length > 0 && (
                        <ul className="mt-2 space-y-1">
                          {p.items.map((it, i) => (
                            <li key={i} className="text-sm flex gap-2 items-baseline">
                              <span className="text-[10px] font-bold uppercase tracking-widest whitespace-nowrap w-16"
                                style={{ color: it.vote_expected ? 'var(--series-cost)' : 'var(--text-muted)' }}>{it.vote_expected ? 'vote' : it.kind}</span>
                              <span><span className="font-medium">{it.agenda_line.replace(/^[a-z0-9]+\.\s*/i, '')}</span>
                                <span className="text-xs" style={{ color: 'var(--text-muted)' }}> — {it.why_it_matters}</span></span>
                            </li>
                          ))}
                        </ul>
                      )}
                      <p className="text-[11px] mt-1.5" style={{ color: 'var(--text-muted)' }}>Items quoted from the agenda; an agenda lists what may be discussed, not what will be decided.</p>
                    </div>
                  )}
                </li>
              )
            })}
          </ol>}
      {later.length > 0 && (
        <p className="text-xs mt-3" style={{ color: 'var(--text-muted)' }}>
          And within {f.upcoming.horizon_days} days: {later.map((m, i) => <span key={m.file_id}>{i ? '; ' : ''}{m.board} <a className="underline" href={m.agenda_url} target="_blank" rel="noreferrer">{longDate(m.date)}</a></span>)}.
        </p>
      )}

      <H2>Minutes just posted</H2>
      {minutes.length === 0
        ? <p className="text-sm" style={{ color: 'var(--text-muted)' }}>None seen in the last two weeks.</p>
        : <ol className="space-y-1.5">
            {minutes.map(i => (
              <li key={i.url} className="text-sm flex flex-wrap gap-x-3 items-baseline">
                <span className="font-semibold">{i.board}</span>
                <span style={{ color: 'var(--text-secondary)' }}>meeting of {longDate(i.meeting_date)}</span>
                <a className="text-xs underline" style={{ color: 'var(--series-cost)' }} href={i.url} target="_blank" rel="noreferrer">minutes</a>
                {typeof i.days_after_meeting_upper_bound === 'number' && (
                  <span className="text-xs" style={{ color: 'var(--text-muted)' }}>posted within {i.days_after_meeting_upper_bound} days of the meeting</span>
                )}
              </li>
            ))}
          </ol>}
      {f.awaiting_minutes.count > 0 && (
        <p className="text-xs mt-3" style={{ color: 'var(--text-muted)' }}>
          {f.awaiting_minutes.count} meetings in the last {f.awaiting_minutes.window_days} days have an agenda and no minutes yet.
          {' '}<a className="underline" href="/what-was-said">Our minutes from the recordings</a> cover some of them.
        </p>
      )}

      {n && (
        <>
          <H2>Recordings just published</H2>
          {n.videos.length === 0
            ? <p className="text-sm" style={{ color: 'var(--text-muted)' }}>Nothing new on the town&rsquo;s channel in the last {n.window_days} days.</p>
            : <ol className="space-y-1.5">
                {n.videos.map(v => (
                  <li key={v.video_id} className="text-sm flex flex-wrap gap-x-3 items-baseline">
                    <span className="tnum text-xs w-24" style={{ color: 'var(--text-secondary)' }}>{v.uploaded}</span>
                    <a className="underline" style={{ color: 'var(--series-revenue, #b5540f)' }} href={v.url} target="_blank" rel="noreferrer">&#9654; {v.title}</a>
                  </li>
                ))}
              </ol>}

          <H2>What happened — from the recordings</H2>
          {!nt || nt.retro.length === 0
            ? <p className="text-sm" style={{ color: 'var(--text-muted)' }}>No recent meeting has our minutes yet.</p>
            : <ol className="space-y-2">
                {nt.retro.map(o => (
                  <li key={o.url} className="card p-3">
                    <div className="flex flex-wrap gap-x-3 items-baseline">
                      <a className="font-semibold underline" style={{ color: 'var(--series-cost)' }} href={o.url}>{o.board}, {longDate(o.date)}</a>
                      <span className="text-xs" style={{ color: 'var(--text-muted)' }}>{o.votes} substantive vote{o.votes === 1 ? '' : 's'} · {o.transfers} transfer{o.transfers === 1 ? '' : 's'}{o.has_official_minutes ? '' : ' · no official minutes yet'}</span>
                    </div>
                    <p className="text-sm mt-1" style={{ color: 'var(--text-secondary)' }}>{o.summary}</p>
                  </li>
                ))}
              </ol>}
        </>
      )}

      {agendas.length > 0 && (
        <>
          <H2>Agendas posted for past meetings</H2>
          <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
            {agendas.map((i, j) => <span key={i.url}>{j ? '; ' : ''}{i.board} <a className="underline" href={i.url} target="_blank" rel="noreferrer">{longDate(i.meeting_date)}</a></span>)}.
          </p>
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

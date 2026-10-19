import { useState } from 'react'
import { BoardNav } from '../components/BoardNav'
import { RecordCell, type RecordStatus } from '../components/RecordCell'
import { boardSlugFromPath, boardSpokeFromPath, type BoardSpoke, type Tab } from '../routes'
import { Body, H2, ReportShell, useReport } from '../components/report'
import { BoardGoals } from '../components/BoardGoals'
import { JobsLink } from '../components/JobPostings'
import { TransfersLink } from './BoardTransfers'
import { useOrgCharts } from '../lib/orgChartLink'
import { Subscribe, useFeedLink } from '../components/Subscribe'
import { JoinLinks, type Join } from '../components/BoardsThisWeek'
import { daysAway as daysFromToday, splitMeetings, meetingTitle, meetingBody, todayIso } from '../lib/meetings'

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

/* ONE TYPE FOR A MEETING, past or to come. There were two -- `Upcoming` and `Recent` --
 * because the generator split them against the BUILD date, and a meeting could therefore
 * belong to neither: the Finance Committee's 24 September meeting was `upcoming` in a
 * payload built the 23rd and filtered out of it on the 25th, while never being in `recent`.
 * The payload now carries one dated list and ../lib/meetings.ts decides which is which from
 * the reader's clock, so the shift happens without a deploy. */
type Meeting = {
  date: string
  agenda_url?: string | null; agenda_doc?: string | null
  minutes_url?: string | null; minutes_doc?: string | null
  video_url?: string | null; transcript: boolean; captions_disabled: boolean
  ours?: { slug: string; headline?: string | null; digest?: string | null; votes?: number; reconciled?: boolean; discrepancies?: number } | null
  // STATUS, for the table to colour -- meeting_records.status()/our_minutes_status(),
  // the same rules the backlog-depth chart and the board records pages read. 'n/a' is
  // never a stand-in for 'missing': it means the record was never going to exist (the
  // board doesn't record, or this is before its first recording).
  record?: {
    due: string | null
    video: { status: RecordStatus; url?: string | null; reason?: string | null; likely_none?: boolean }
    minutes: { status: RecordStatus; url?: string | null; reason?: string | null }
    transcript: { status: RecordStatus; captions_disabled: boolean; reason?: string | null }
    our_minutes: { state: 'posted' | 'pending' | 'needs-video' | 'n/a'; reason?: string | null }
  } | null
  // Written before the meeting by write_agenda_preview.py, so only ever present on one that
  // has not happened yet -- carried on the row rather than in a separate list.
  body_as_printed?: string | null
  join?: Join | null; hook?: string | null; time?: string | null; where?: string | null
  attend?: string | null; important?: unknown
  items?: { agenda_line: string; why_it_matters?: string; important?: boolean }[] | null
}
/* THE LIKELY NEXT MEETING -- OUR ESTIMATE, from scripts/meeting_cadence.py by way of
 * build_boards.py. A rhythm read off the dates the board has met, backtested over the last
 * year; `show` is true only where that backtest cleared a threshold WE chose. `dates` are
 * the next few rule dates after the build, so the page can roll forward past one that has
 * gone by without a rebuild. */
type LikelyNext = {
  show: boolean; reason: string | null; rule: string | null; weekday?: string; time?: string | null
  dates: string[]; explained?: number; of?: number; last_met?: string | null; as_of: string
  backtest: { made: number; exact: number; week: number }
  threshold: { min_predictions: number; min_exact_share: number }
}
type Score = { fy: number; minutes: { meetings: number; have: number }; recordings: { meetings: number; have: number } }
type Vote = { date: string; t?: number | null; motion?: string; outcome?: string; procedural: boolean; moved_by?: string | null; page: string | null; video_url: string | null
  source: 'minutes' | 'recording' | 'both'; quote?: string | null; conflict?: string | null; minutes_doc?: string | null; minutes_url?: string | null }
type Cal = { key: string; label: string; cycles: { fy: number; dates: string[] }[]; earliest: string; latest: string; typical_first: string; typical_last: string; meetings: number }
type Page = { url: string; source: 'town' | 'district'; overview: string; charter_ref: string; meets: string; members: string[]; facebook: string | null; facebook_scope: string; mirror: string; fetched_at: string; charter_url: string }
type Board = {
  slug: string; name: string; the_three: boolean; page?: Page | null
  about_itself?: { key: string; label: string; school_year: string; url: string; upstream: string; sha256: string; text: string }[]
  scorecard?: { this: Score; last: Score; minutes_lag_days: number; video_lag_days: number }
  finance?: { accounts: number; funds: number; related: number } | null
  // THE CHART THAT NAMES ITS PEOPLE, from `body-crosswalk.csv` by way of build_boards.py.
  // A list, because two charts can sit behind one board -- the Board of Assessors is drawn
  // once as the board and once as the office that staffs it.
  people?: { unit: string; chart_url: string; fy: string; named: number; years: number }[] | null
  // HOW THIS BODY HAS ANSWERED THE TOWN'S ANNUAL CALL FOR A REPORT, from the contents
  // page of each annual report — the only place the town records it. Absent where the
  // town never listed the body at all, which is not the same as a body that declined.
  annual_report?: {
    filed: number; said_none: number; of_years: number
    first: string; last: string; years_filed: string[]; years_said_none: string[]
  } | null
  likely_next?: LikelyNext | null
  join?: { weekday?: string; weekday_share?: number; meetings_sampled?: number; time?: string | null; place?: string | null; zoom?: boolean; cable?: boolean; agendas_read?: number; open_seats?: number; open_seats_fy?: string; open_seats_filled_by?: string } | null
  counts: { agendas: number; minutes: number; recordings: number; transcripts: number; captions_disabled: number; our_minutes: number; official_votes_read: number; votes: number; vote_conflicts: number; first: string | null; last: string | null }
  meetings: Meeting[]; votes: Vote[]
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
  const sp = boardSpokeFromPath(window.location.pathname)
  const slug = sp?.slug ?? boardSlugFromPath(window.location.pathname)
  const b = d && slug ? d.boards.find(x => x.slug === slug) : null
  useFeedLink(slug ? (b ? `/feeds/${b.slug}.xml` : null) : '/feeds/all.xml', b ? `${b.name} — Lunenburg Budget Project` : 'Every board — Lunenburg Budget Project')
  if (!d) return <ReportShell tab={TAB} title={slug ? 'A board' : 'The boards'} err={err} loading={!err} dataUrl={DATA} />
  if (slug && !b) {
    return (
      <ReportShell tab={TAB} title="No such board" dataUrl={DATA}>
        <Body>The address <code>/boards/{slug}</code> names no board. The index is <a className="underline" href="/boards">/boards</a>.</Body>
      </ReportShell>
    )
  }
  return b ? <BoardPage b={b} d={d} spoke={sp?.spoke ?? null} /> : <Index d={d} />
}

function Index({ d }: { d: Payload }) {
  const three = d.boards.filter(b => b.the_three)
  const rest = d.boards.filter(b => !b.the_three)
  const openTotal = d.boards.reduce((n, b) => n + (b.join?.open_seats ?? 0), 0)
  const openBoards = d.boards.filter(b => (b.join?.open_seats ?? 0) > 0).length
  const Card = ({ b }: { b: Board }) => (
    <a href={`/boards/${b.slug}`} className="card block p-4 transition-opacity hover:opacity-90">
      <p className="text-[15px] font-bold leading-snug" style={{ color: 'var(--series-cost)' }}>{b.name} &rarr;</p>
      <p className="text-xs mt-1.5 tnum" style={{ color: 'var(--text-secondary)' }}>
        {splitMeetings(b.meetings).upcoming[0]
          ? <span className="font-semibold" style={{ color: 'var(--text-primary)' }}>next {mmdd(splitMeetings(b.meetings).upcoming[0].date)} · </span>
          : likelyDate(b, [])
            /* OUR ESTIMATE, never in the posted meeting's voice: the amber underline and the
               word "likely", and the tag says whose guess it is. */
            ? <span style={{ color: 'var(--text-primary)' }}><span style={{ borderBottom: '2px solid var(--status-warning)' }}>likely {mmdd(likelyDate(b, [])!)}</span> <span style={kicker}>(our estimate)</span> · </span> : null}
        {n0(b.counts.agendas)} agendas · {n0(b.counts.minutes)} minutes · {n0(b.counts.recordings)} recordings{b.counts.our_minutes ? ` · ${n0(b.counts.our_minutes)} of ours, ${n0(b.counts.votes)} votes` : ''}
      </p>
    </a>
  )
  return (
    <ReportShell tab={TAB} title="The boards — each one, in one place"
      standfirst={`${d.boards.length} boards and committees the town posts for. What is coming, what happened, every vote we have minutes for, where the time goes, and when budget planning lands — one page each.`}
      dataUrl={DATA}>
      {/* OPEN SEATS FIRST. TJ, 22 September 2026: "put the link to open spots here". Of
          everything on this index it is the only line that asks the reader to DO
          something, and a resident who came here wondering how to get involved should not
          have to read sixty cards to find out they can. */}
      {openTotal > 0 && (
        <p className="text-[14px] mt-5 max-w-3xl">
          <a className="font-semibold underline" style={{ color: 'var(--series-cost)' }} href="/board-records/board-open-seats">
            {openTotal === 1 ? 'One open seat on a town board' : `${openTotal} open seats across ${openBoards} town boards`} &rarr;
          </a>
          <span style={{ color: 'var(--text-secondary)' }}> &mdash; the boards with a chair going spare, and when the filled ones come up.</span>
        </p>
      )}
      <p className="text-[14px] mt-5 max-w-3xl">
        <a className="font-semibold underline" style={{ color: 'var(--series-cost)' }} href="/board-records">Board records &rarr;</a>
        <span style={{ color: 'var(--text-secondary)' }}> &mdash; every board beside the others on what the record measures, starting with which meetings got minutes.</span>
      </p>
      <Subscribe path="/feeds/all.xml" what="any board posts or changes an agenda, or a meeting’s recording, transcript and our minutes are all in — each board’s own page has a feed of its own" />
      <H2>The three that set the school budget</H2>
      <div className="grid gap-3 mt-4 sm:grid-cols-3">{three.map(b => <Card key={b.slug} b={b} />)}</div>
      <H2>Every other board</H2>
      <div className="grid gap-3 mt-4 sm:grid-cols-2 lg:grid-cols-3">{rest.map(b => <Card key={b.slug} b={b} />)}</div>
      <p className="text-xs mt-6" style={{ color: 'var(--text-muted)' }}>As of {d.as_of}. Counts are what the town has posted to its AgendaCenter and its YouTube channel, plus the minutes this project has written from the recordings.</p>
    </ReportShell>
  )
}

/** THE TOWN'S DESCRIPTION, SHORT. TJ, 17 September 2026, on the Parks page: "insanely
 *  long ... keep it short and put info in a collapsible panel if too long." The first
 *  paragraph stands, clipped to about eighty words at a sentence end; the rest of what
 *  the town wrote -- usually the board's full charge -- is one click away, as printed. */
const LEAD_WORDS = 80
function Overview({ text, who }: { text: string; who: string }) {
  const paras = text.split('\n').map(p => p.trim()).filter(Boolean)
  let lead = paras[0] ?? ''
  let rest = paras.slice(1)
  const words = lead.split(/\s+/)
  if (words.length > LEAD_WORDS) {
    const cut = words.slice(0, LEAD_WORDS).join(' ')
    const end = Math.max(cut.lastIndexOf('. '), cut.lastIndexOf('; '))
    const head = end > cut.length * 0.4 ? cut.slice(0, end + 1) : cut + '…'
    rest = [lead.slice(head.replace(/…$/, '').length).trim(), ...rest].filter(Boolean)
    lead = head
  }
  return (
    <blockquote className="text-sm mt-3 leading-relaxed" style={{ color: 'var(--text-secondary)', borderLeft: '3px solid var(--grid)', paddingLeft: 12 }}>
      <p>{lead}</p>
      {rest.length > 0 && (
        <details className="mt-2">
          <summary className="cursor-pointer text-[12.5px] underline" style={{ color: 'var(--text-muted)' }}>The rest of what {who} says about it ({rest.join(' ').split(/\s+/).length} more words)</summary>
          {rest.map((p, i) => <p key={i} className="mt-2">{p}</p>)}
        </details>
      )}
    </blockquote>
  )
}


/** THE POSTING RECORD, AS A CHIP. TJ, 17 September 2026: "put the percentages of the
 *  current fiscal year of minutes and video postings on each board's page ... '66% minutes
 *  FY27' ... (in nice designs...)" -- and, on the first version, "those metrics are far too
 *  central on the board page. I was expecting a sort of sidebar progress report or small
 *  chip." The sidebar is gone; the chip is now a small card on the overview, beside the
 *  other things a reader checks rather than reads. Each chip leads with the current fiscal
 *  year once it has three meetings old enough to count, and with last year until then,
 *  because "0% minutes FY27" in September is one July meeting whose minutes are simply due. */
function Chip({ what, sc, title }: { what: 'minutes' | 'recordings'; sc: { this: Score; last: Score }; title: string }) {
  const lead = sc.this[what].meetings >= 3 ? sc.this : sc.last
  const other = lead === sc.this ? sc.last : sc.this
  const L = lead[what], O = other[what]
  const p = L.meetings ? Math.round(100 * L.have / L.meetings) : null
  const tone = p === null ? 'var(--text-muted)' : p >= 90 ? 'var(--status-good)' : p >= 60 ? 'var(--text-primary)' : 'var(--status-critical)'
  return (
    <div className="mt-2" title={title}>
      <div className="flex items-baseline justify-between gap-2">
        <span className="text-[12px]" style={{ color: 'var(--text-secondary)' }}>{what === 'minutes' ? 'minutes posted' : 'on YouTube'} · FY{String(lead.fy).slice(2)}{lead === sc.this ? ' so far' : ''}</span>
        <span className="text-[15px] font-bold tnum" style={{ color: tone }}>{p === null ? '—' : `${p}%`}</span>
      </div>
      <div className="h-1 rounded-full mt-1 overflow-hidden" style={{ background: 'var(--surface-3)' }}>
        <div className="h-full rounded-full" style={{ width: `${p ?? 0}%`, background: tone }} />
      </div>
      <p className="text-[11px] mt-0.5 tnum" style={{ color: 'var(--text-muted)' }}>
        {L.meetings ? `${L.have} of ${L.meetings} meetings` : 'none old enough yet'}{O.meetings ? ` · FY${String(other.fy).slice(2)}${other === sc.this ? ' so far' : ''} ${O.have} of ${O.meetings}` : ''}
      </p>
    </div>
  )
}

/* ============================================================== the pieces
 * Each spoke is one of these at full length, and the overview is several of them cut short
 * with a link to the spoke. One component per thing, so the overview and its spoke cannot
 * come to disagree about how a meeting or a vote is drawn. */

const kicker = { color: 'var(--text-muted)' } as const
const Kicker = ({ children }: { children: React.ReactNode }) =>
  <p className="text-[10.5px] font-bold uppercase tracking-widest" style={kicker}>{children}</p>
const More = ({ href, children }: { href: string; children: React.ReactNode }) =>
  <a className="inline-block text-[13px] font-semibold underline mt-2" style={{ color: 'var(--series-cost)' }} href={href}>{children} &rarr;</a>

/** AN OPEN SEAT. TJ, 22 September 2026: "on each board page, if it has open spot, show that
 *  'One Open Board Seat Available'". The only thing on the page a reader can act on today,
 *  and perishable -- so it says which annual report it came from rather than implying it is
 *  live. */
function SeatBanner({ b }: { b: Board }) {
  const j = b.join
  const n = j?.open_seats ?? 0
  if (!n) return null
  return (
    <a href="/board-records/board-open-seats" className="card p-3 block no-underline" style={{ borderColor: 'var(--series-cost)', borderWidth: 2 }}>
      <p className="text-[15px] font-bold leading-snug" style={{ color: 'var(--series-cost)' }}>
        {n === 1 ? 'One open board seat available' : `${n} open board seats available`}
      </p>
      <p className="text-[12px] mt-1" style={{ color: 'var(--text-secondary)' }}>
        The town printed {n === 1 ? 'a vacancy' : 'vacancies'} on this board in its FY{j?.open_seats_fy} annual
        report. {j?.open_seats_filled_by === 'elected'
          ? 'This is an elected seat — filled at the annual town election, third Saturday in May.'
          : 'This is an appointed seat — filled by the Select Board.'} See every open seat in town →
      </p>
    </a>
  )
}

/** THE ESTIMATE, OR NOTHING. A posting always wins: any meeting on the calendar for today
 *  or later and there is no estimate at all (rule 3 -- our guess never sits where the
 *  town's notice should). Otherwise the first rule date still to come on the READER'S
 *  clock, so a static page built days ago rolls forward rather than naming a date gone by. */
/** "the 1st and 3rd Wednesday of the month", but "every other Monday" -- no article. */
const ruleText = (r: string | null) => !r ? '' : r.startsWith('every') ? r : `the ${r}`

function likelyDate(b: Board, upcoming: Meeting[]): string | null {
  const l = b.likely_next
  if (upcoming.length || !l?.show) return null
  const today = todayIso()
  return l.dates.find(x => x >= today) ?? null
}

/** LIKELY NEXT MEETING -- styled as every estimate on this site is: the amber edge and the
 *  "our estimate" tag (report.tsx's Maybe and the ladder's estimate tile). The metric is
 *  the date; one line for the rhythm; one for how often it has been right. The method sits
 *  in the expansion (rule 7b). */
function LikelyCard({ b, date }: { b: Board; date: string }) {
  const l = b.likely_next!
  const bt = l.backtest
  const pctT = Math.round(l.threshold.min_exact_share * 100)
  const away = daysFromToday(date)
  return (
    <div className="card p-4" style={{ borderLeft: '4px solid var(--status-warning)' }}>
      <Kicker>Likely next meeting &middot; our estimate</Kicker>
      <p className="text-[17px] font-bold leading-snug mt-1">{dateText(date)}{l.time ? <span className="font-normal">, usually {l.time}</span> : null}
        <span className="text-[12.5px] font-normal ml-2" style={kicker}>{away === 0 ? 'today' : away === 1 ? 'tomorrow' : `in ${away} days`}</span></p>
      <p className="text-[13px] mt-1" style={{ color: 'var(--text-secondary)' }}>It usually meets {l.rule?.startsWith('every') ? '' : 'on '}{ruleText(l.rule)}. Nothing is posted yet.</p>
      <p className="text-[13px] mt-0.5" style={{ color: 'var(--text-secondary)' }}>This guess would have been right {bt.exact} of {bt.made} times over the last year.</p>
      <details className="mt-2 text-[12.5px]" style={{ color: 'var(--text-secondary)' }}>
        <summary className="cursor-pointer" style={kicker}>How this is worked out</summary>
        <p className="mt-1.5">Read off the dates this board has met, not from anything it published. {l.explained} of its {l.of} meetings in the year to {l.as_of} fell on that pattern{l.last_met ? `; the last was ${dateText(l.last_met)}` : ''}.</p>
        <p className="mt-1.5">The test: after each meeting in the last year we named the next date from what was known that day. The board met on the date named {bt.exact} of {bt.made} times, and its actual next meeting came within a week of it {bt.week} times.</p>
        <p className="mt-1.5">We show an estimate only when both are at least {pctT}% over at least {l.threshold.min_predictions} tries, and the board has met recently. That threshold is our choice, not a rule anybody published. A posted agenda always replaces this card; the Open Meeting Law requires notice 48 hours ahead, not counting weekends and holidays. Worked out as of {l.as_of}.</p>
      </details>
    </div>
  )
}

/** HOW TO JOIN. TJ, 17 September 2026: "if someone wants to join live, what info do they
 *  need to know?" -- the weekday and time first and large, then the room, then whether
 *  there is a Zoom and a broadcast. Read off the last few agendas (build_boards.how_to_join),
 *  not the board's boilerplate. */
function JoinCard({ b, next }: { b: Board; next: Meeting | undefined }) {
  const j = b.join
  if (!j?.weekday && !next) return null
  return (
    <div className="card p-4">
      <Kicker>Next meeting</Kicker>
      {next
        ? <p className="text-[17px] font-bold leading-snug mt-1">{dateText(next.date)}{next.time ? `, ${next.time}` : ''}
            <span className="text-[12.5px] font-normal ml-2" style={kicker}>{daysFromToday(next.date) === 0 ? 'today' : daysFromToday(next.date) === 1 ? 'tomorrow' : `in ${daysFromToday(next.date)} days`}</span></p>
        : <p className="text-[14px] mt-1" style={{ color: 'var(--text-secondary)' }}>Nothing on the calendar yet.</p>}
      {/* The body actually meeting, where the agenda names another -- the town files its
          school advisory councils and sub-committees here. See meetingTitle(). */}
      {next?.body_as_printed && meetingTitle(b.name, next.body_as_printed) !== b.name && (
        <p className="text-[14px] font-semibold mt-1" style={{ color: 'var(--series-cost)' }}>{meetingTitle(b.name, next.body_as_printed)}</p>
      )}
      {next?.hook && <p className="text-[14px] mt-1.5">{next.hook}</p>}
      {next && <JoinLinks j={next.join} />}
      {j?.weekday && (
        <p className="text-[12.5px] mt-2" style={{ color: 'var(--text-secondary)' }}>
          {/* An absent share means we do not know how consistent the day is, which is `Usually`. */}
          Meets {(j.weekday_share ?? 0) >= 0.6 ? `${j.weekday}s` : `usually ${j.weekday}s`}{j.time ? `, ${j.time}` : ''}{j.place ? ` · ${j.place}` : ''}
          {j.zoom ? ' · hybrid, Zoom link on each agenda' : ''}{j.cable ? ' · broadcast live on public access' : ''}
        </p>
      )}
      {next && (next.agenda_url
        ? <a className="text-xs underline mt-2 inline-block" style={kicker} href={next.agenda_url}>the posted agenda</a>
        : <span className="text-xs mt-2 inline-block" style={kicker}>No agenda posted yet.</span>)}
    </div>
  )
}

function UpcomingCard({ b, u }: { b: Board; u: Meeting }) {
  return (
    <div className="card p-4 mt-3">
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <span className="font-bold">{dateText(u.date)}</span>
        {/* The body actually meeting, where the agenda names another. See meetingTitle(). */}
        {u.body_as_printed && meetingTitle(b.name, u.body_as_printed) !== b.name
          ? <span className="text-[13px] font-semibold" style={{ color: 'var(--series-cost)' }}>{meetingTitle(b.name, u.body_as_printed)}</span>
          : null}
        {u.time && <span className="text-xs px-2 py-0.5 rounded" style={{ background: 'var(--surface-3)' }}>{u.time}</span>}
        {u.where && <span className="text-xs px-2 py-0.5 rounded" style={{ background: 'var(--surface-3)' }}>{u.where}</span>}
        {u.attend && <span className="text-xs px-2 py-0.5 rounded" style={{ background: 'var(--surface-3)' }}>{u.attend}</span>}
        <span className="text-xs" style={kicker}>{daysFromToday(u.date) === 0 ? 'today' : daysFromToday(u.date) === 1 ? 'tomorrow' : `in ${daysFromToday(u.date)} days`}</span>
      </div>
      {u.hook && <p className="text-[15px] mt-2">{u.hook}</p>}
      <JoinLinks j={u.join} />
      {u.items && u.items.length > 0 && (
        <details className="mt-2 text-sm">
          <summary className="cursor-pointer" style={{ color: 'var(--text-secondary)' }}>The agenda, item by item</summary>
          <ul className="mt-2 space-y-1.5">{u.items.map((it, i) => (
            <li key={i} style={{ fontWeight: it.important ? 600 : 400 }}>{it.agenda_line}{it.why_it_matters ? <span style={kicker}> — {it.why_it_matters}</span> : null}</li>))}</ul>
        </details>
      )}
      {/* A meeting can be known before its agenda is posted, now that the list comes from
          the meeting register rather than from the documents we hold. */}
      {u.agenda_url
        ? <a className="text-xs underline mt-2 inline-block" style={kicker} href={u.agenda_url}>the posted agenda</a>
        : <span className="text-xs mt-2 inline-block" style={kicker}>No agenda posted yet.</span>}
    </div>
  )
}

function RecentTable({ rows, board }: { rows: Meeting[]; board: string }) {
  return (
    <div className="overflow-x-auto mt-3">
      <table className="text-sm w-full" style={{ minWidth: 720 }}>
        <thead><tr className="text-[10px] font-bold uppercase tracking-widest" style={kicker}>
          {/* COLUMNS IN THE ORDER WE WANT THEM USED -- our minutes, the recording, the
              agenda, the town's minutes (TJ, 17 September 2026). */}
          <th className="text-left py-1.5 pr-3">date</th><th className="text-left py-1.5 pr-3">our minutes</th><th className="text-left py-1.5 pr-3">recording</th><th className="text-left py-1.5 pr-3">agenda</th><th className="text-left py-1.5">official minutes</th></tr></thead>
        <tbody>{rows.map(r => (
          <tr key={r.date} style={{ borderTop: '1px solid var(--grid)' }}>
            <td className="py-2 pr-3 tnum font-semibold whitespace-nowrap align-top">{mmdd(r.date)} {r.date.slice(0, 4)}
              {/* Which body met, where it is not the board itself -- a council or a
                * sub-committee the town files under this board's agendas. */}
              {r.body_as_printed && meetingBody(board, r.body_as_printed) !== board &&
                <span className="block text-xs font-normal whitespace-normal" style={{ ...kicker, maxWidth: 160 }}>{meetingBody(board, r.body_as_printed)}</span>}</td>
            <td className="py-2 pr-3 align-top">
              {r.ours ? <><a className="font-semibold" href={`/meeting-minutes/${r.ours.slug}`} style={{ color: 'var(--series-cost)' }}>{r.ours.headline || 'our minutes'}</a><span className="text-xs" style={kicker}> · {r.ours.votes ?? 0} votes{r.ours.reconciled ? (r.ours.discrepancies ? ` · ${r.ours.discrepancies} difference${r.ours.discrepancies === 1 ? '' : 's'} from the official minutes` : ' · agrees with the official minutes') : ''}</span></>
                : r.record?.our_minutes.state === 'pending' ? <span title="in our queue" style={kicker}>pending</span>
                : r.record?.our_minutes.state === 'n/a' ? <span title={r.record.our_minutes.reason || undefined} style={kicker}>n/a</span>
                : <span title="written from the recording" style={kicker}>needs video</span>}
            </td>
            <td className="py-2 pr-3 align-top">
              {r.record ? <RecordCell status={r.record.video.status} due={r.record.due} url={r.record.video.url} label="video" reason={r.record.video.reason} likely_none={r.record.video.likely_none} /> : (r.video_url ? <a className="underline" href={r.video_url}>video</a> : <span style={kicker}>—</span>)}
              {r.record?.video.status === 'posted' && (r.captions_disabled ? <span className="text-xs" style={kicker}> · no captions</span> : !r.transcript ? <span className="text-xs" style={kicker}> · no transcript yet</span> : null)}
            </td>
            <td className="py-2 pr-3 align-top">{r.agenda_doc ? <a className="underline" href={r.agenda_doc}>agenda</a> : <span style={kicker}>—</span>}</td>
            <td className="py-2 align-top">{r.record ? <RecordCell status={r.record.minutes.status} due={r.record.due} url={r.minutes_doc} label="minutes" /> : (r.minutes_doc ? <a className="underline" href={r.minutes_doc}>minutes</a> : <span style={kicker}>not yet</span>)}</td>
          </tr>))}</tbody>
      </table>
    </div>
  )
}

function VotesTable({ votes }: { votes: Vote[] }) {
  return (
    <div className="overflow-x-auto mt-3">
      <table className="text-sm w-full" style={{ minWidth: 760 }}>
        <thead><tr className="text-[10px] font-bold uppercase tracking-widest" style={kicker}>
          <th className="text-left py-1.5 pr-3">date</th><th className="text-left py-1.5 pr-3">motion</th><th className="text-left py-1.5 pr-3">outcome</th><th className="text-left py-1.5 pr-3">record</th><th className="text-left py-1.5">check it</th></tr></thead>
        <tbody>{votes.map((v, i) => (
          <tr key={i} style={{ borderTop: '1px solid var(--grid)', color: v.procedural ? 'var(--text-muted)' : undefined }}>
            <td className="py-1.5 pr-3 tnum whitespace-nowrap align-top">{mmdd(v.date)} {v.date.slice(0, 4)}</td>
            <td className="py-1.5 pr-3 align-top" style={{ minWidth: 320 }}>{v.motion}{v.moved_by ? <span className="text-xs" style={kicker}> — moved by {v.moved_by}</span> : null}
              {v.quote && <span className="block text-[11px] mt-0.5 italic" style={kicker}>&ldquo;{v.quote}&rdquo;</span>}
              {v.conflict && <span className="block text-[11px] mt-0.5 font-semibold" style={{ color: 'var(--status-critical)' }}>The two records disagree: {v.conflict}.</span>}</td>
            <td className="py-1.5 pr-3 align-top font-semibold" style={{ maxWidth: 220, color: (v.outcome || '').startsWith('pass') ? 'var(--status-good)' : (v.outcome || '').startsWith('fail') ? 'var(--status-critical)' : 'var(--text-muted)' }}>{v.outcome}</td>
            <td className="py-1.5 pr-3 align-top text-[11px] whitespace-nowrap" style={kicker}>{v.source === 'both' ? 'minutes + recording' : v.source === 'minutes' ? 'the minutes' : 'the recording only'}</td>
            <td className="py-1.5 align-top whitespace-nowrap text-[12.5px]">
              {v.minutes_doc && <a className="underline" href={v.minutes_url || v.minutes_doc}>the minutes</a>}
              {v.minutes_doc && v.video_url ? ' · ' : ''}
              {v.video_url && <a className="underline" href={v.video_url}>{v.t != null ? `video ${Math.floor(v.t / 60)}:${String(v.t % 60).padStart(2, '0')}` : 'video'}</a>}
              {v.page ? <> · <a className="underline" href={v.page}>ours</a></> : null}
            </td>
          </tr>))}</tbody>
      </table>
    </div>
  )
}

function TimeBars({ b, limit }: { b: Board; limit?: number }) {
  const rows = limit ? b.time_by_tag.slice(0, limit) : b.time_by_tag
  return (
    <div className="mt-3 max-w-3xl">{rows.map(t => (
      <div key={t.tag} className="py-1.5 text-sm" style={{ borderTop: '1px solid var(--grid)' }}>
        <div className="flex items-baseline justify-between gap-3"><span className="font-semibold">{t.label}</span><span className="tnum shrink-0">{hours(t.seconds)}{t.share != null ? ` · ${pct(t.share)}` : ''}</span></div>
        <div className="h-1.5 rounded-full mt-1" style={{ background: 'var(--surface-3)' }}><div className="h-full rounded-full" style={{ width: `${(t.seconds / b.time_by_tag[0].seconds) * 100}%`, background: 'var(--series-cost)' }} /></div>
      </div>))}</div>
  )
}

/** WHAT THIS BOARD IS DECIDING -- the open threads it has been a stop on. A thread is a
 *  matter tracked across boards to a decision (pages/Threads.tsx); a board's share of one
 *  is any meeting of its in the thread's chronology. Read off threads.json, so a thread
 *  that reaches this board appears here the day the thread does. */
type ThreadLite = { id: string; label: string; status: string; last_moved: string; chronology: { board_slug: string; date: string }[] }
function Deciding({ b }: { b: Board }) {
  const { d } = useReport<{ threads: ThreadLite[] }>('threads.json')
  if (!d) return null
  const mine = d.threads
    .filter(t => t.status === 'open' && t.chronology.some(c => c.board_slug === b.slug))
    .map(t => ({ t, here: t.chronology.filter(c => c.board_slug === b.slug).map(c => c.date).sort().slice(-1)[0] }))
    .sort((x, y) => y.here.localeCompare(x.here))
  if (!mine.length) return null
  return (
    <section aria-labelledby="deciding">
      <H2 id="deciding">What it is deciding</H2>
      <p className="text-sm mt-1" style={{ color: 'var(--text-secondary)' }}>Open matters, tracked across every board, that have come up at this one.</p>
      <ul className="list-none p-0 m-0 mt-2">{mine.map(({ t, here }) => (
        <li key={t.id} className="py-2" style={{ borderTop: '1px solid var(--grid)' }}>
          <a className="font-semibold" href={`/threads/${t.id}`} style={{ color: 'var(--series-cost)' }}>{t.label}</a>
          <span className="text-[12.5px] ml-2" style={kicker}>here last {mmdd(here)} {here.slice(0, 4)}</span>
        </li>))}</ul>
      <More href="/threads">Every matter the town is deciding</More>
    </section>
  )
}

/** ITS RECORD -- how well this board keeps the record, in one card. */
function RecordCard({ b }: { b: Board }) {
  const sc = b.scorecard
  const ar = b.annual_report
  if (!sc && !ar) return null
  return (
    <div className="card p-4">
      <Kicker>Its record</Kicker>
      {sc && <>
        <Chip what="minutes" sc={sc} title={`Of meetings with a posted agenda, those with minutes on the town’s Agenda Center. Meetings in the last ${sc.minutes_lag_days} days are not counted: minutes are approved at the next meeting.`} />
        <Chip what="recordings" sc={sc} title={`Of meetings with a posted agenda, those with a recording on the town’s YouTube channel. Meetings in the last ${sc.video_lag_days} days are not counted.`} />
      </>}
      {ar && (
        <p className="text-[12px] mt-2" style={{ color: 'var(--text-secondary)' }}>
          {/* The town's own words, off the contents page of each annual report. */}
          Annual report filed in {ar.filed} of the {ar.of_years} years the town asked
          {ar.said_none > 0 ? <>; &ldquo;No&nbsp;Report&nbsp;Submitted&rdquo; {ar.said_none} time{ar.said_none === 1 ? '' : 's'}</> : null}.
        </p>
      )}
      <a className="block text-[12px] underline mt-2" style={kicker} href="/board-records/board-minutes-posted">compared with every board &rarr;</a>
    </div>
  )
}

/* ============================================================== the page */

const SPOKE_LABEL: Record<BoardSpoke, string> = {
  meetings: 'meetings', votes: 'votes', time: 'where the time goes', schedule: 'budget schedule', about: 'about',
}

function BoardPage({ b, d, spoke }: { b: Board; d: Payload; spoke: BoardSpoke | null }) {
  // ONE SPLIT, decided from the reader's clock (../lib/meetings.ts), so a meeting moves from
  // upcoming to past without a deploy.
  const { upcoming, past } = splitMeetings(b.meetings)
  const c = b.counts
  const title = spoke ? `${b.name} — ${SPOKE_LABEL[spoke]}` : b.name
  const standfirst = spoke ? undefined
    : <>{c.first ? `Posted since ${c.first.slice(0, 4)}: ` : ''}{n0(c.agendas)} agendas, {n0(c.minutes)} sets of minutes, {n0(c.recordings)} recordings{c.our_minutes ? `, ${n0(c.our_minutes)} meetings with our minutes and ${n0(c.votes)} votes on the record` : ''}.</>
  return (
    <ReportShell tab={TAB} title={title} standfirst={standfirst} dataUrl={DATA}>
      <BoardNav slug={b.slug} current={spoke ?? 'overview'} />
      {spoke === null && <OverviewTab b={b} upcoming={upcoming} past={past} />}
      {spoke === 'meetings' && <MeetingsTab b={b} d={d} upcoming={upcoming} past={past} />}
      {spoke === 'votes' && <VotesTab b={b} />}
      {spoke === 'time' && <TimeTab b={b} />}
      {spoke === 'schedule' && <ScheduleTab b={b} />}
      {spoke === 'about' && <AboutTab b={b} />}
      <p className="text-xs mt-8" style={kicker}>As of {d.as_of}. <a className="underline" href="/boards">All boards</a>.</p>
    </ReportShell>
  )
}

/** THE OVERVIEW IS A DASHBOARD. TJ, 11 October 2026: *"I'm thinking their main page is more
 *  like a dashboard, which shows the main conclusions, maybe recency ... but we gotta
 *  surface the links a little bit more prominently."* In the order a resident asks: what
 *  can I do (a seat, the next meeting), what is it deciding, what did it do lately, where
 *  does its time go, and how well does it keep the record. Each section is the top of a
 *  tab and says so. Written conclusions per board are phase two. */
function OverviewTab({ b, upcoming, past }: { b: Board; upcoming: Meeting[]; past: Meeting[] }) {
  const lately = past.slice(0, 3)
  const recentVotes = b.votes.filter(v => !v.procedural).slice(0, 5)
  return (
    <>
      <div className="grid gap-3 mt-5 md:grid-cols-2 items-start">
        <div className="space-y-3">
          <SeatBanner b={b} />
          <JoinCard b={b} next={upcoming[0]} />
          {likelyDate(b, upcoming) && <LikelyCard b={b} date={likelyDate(b, upcoming)!} />}
          {upcoming.length > 1 && <More href={`/boards/${b.slug}/meetings`}>{upcoming.length - 1} more coming up</More>}
        </div>
        <RecordCard b={b} />
      </div>

      {/* Job postings and transfers, for the boards that have any; each renders nothing
          otherwise. See components/JobPostings.tsx and pages/BoardTransfers.tsx. */}
      <JobsLink slug={b.slug} />
      <TransfersLink slug={b.slug} />

      <Deciding b={b} />

      <H2 id="recent">Lately</H2>
      {lately.length ? <RecentTable rows={lately} board={b.name} /> : <Body>No meetings on the record yet.</Body>}
      <More href={`/boards/${b.slug}/meetings`}>Every meeting</More>

      {recentVotes.length > 0 && <>
        <H2 id="votes">Latest votes</H2>
        <VotesTable votes={recentVotes} />
        <More href={`/boards/${b.slug}/votes`}>All {n0(b.votes.length)} votes</More>
      </>}

      {b.time_by_tag.length > 0 && <>
        <H2 id="time">Where its time goes</H2>
        <p className="text-sm mt-1" style={{ color: 'var(--text-secondary)' }}>The top topics across the {b.time_meetings} recorded meetings we have minutes for.</p>
        <TimeBars b={b} limit={5} />
        <More href={`/boards/${b.slug}/time`}>Every topic</More>
      </>}

      {/* WHAT THE BOARD SAID IT WOULD DO -- the frame the meetings and votes are read against. */}
      <BoardGoals slug={b.slug} />
      <Subscribe path={`/feeds/${b.slug}.xml`} what={`the ${b.name} posts or changes an agenda, or a meeting’s recording, transcript and our minutes are all in`} />
    </>
  )
}

function MeetingsTab({ b, d, upcoming, past }: { b: Board; d: Payload; upcoming: Meeting[]; past: Meeting[] }) {
  return (
    <>
      <H2 id="up">Coming up</H2>
      {upcoming.length === 0
        ? <>
            <p className="text-sm mt-2" style={{ color: 'var(--text-secondary)' }}>Nothing on the calendar for a future date. The site was last updated {d.as_of}; a meeting noticed since then appears when it is next built.</p>
            {likelyDate(b, upcoming)
              ? <div className="mt-3 max-w-xl"><LikelyCard b={b} date={likelyDate(b, upcoming)!} /></div>
              : b.likely_next && !b.likely_next.show && b.likely_next.backtest.made > 0
                ? <p className="text-xs mt-1" style={kicker}>No estimate of the next date: {b.likely_next.reason}{b.likely_next.rule ? ` (its closest pattern, ${ruleText(b.likely_next.rule)}, would have been right ${b.likely_next.backtest.exact} of ${b.likely_next.backtest.made} times over the last year)` : ''}.</p>
                : null}
          </>
        : upcoming.map(u => <UpcomingCard key={u.date} b={b} u={u} />)}
      <H2 id="recent">Every meeting, newest first</H2>
      {past.length ? <RecentTable rows={past} board={b.name} /> : <Body>No meetings on the record yet.</Body>}
      <p className="text-xs mt-1" style={kicker}>{n0(past.length)} meetings, by today&rsquo;s date rather than the day the site was built &mdash; so a meeting moves here on its own. Which are missing a record: <a className="underline" href={`/boards/${b.slug}/records`}>missing records</a>. For a program, every agenda and set of minutes as one text file: <a className="underline" href={b.urls.minutes_text}>{b.urls.minutes_text}</a>.</p>
    </>
  )
}

function VotesTab({ b }: { b: Board }) {
  const [all, setAll] = useState(false)
  const substantive = b.votes.filter(v => !v.procedural)
  return (
    <>
      <p className="text-sm mt-5 max-w-3xl" style={{ color: 'var(--text-secondary)' }}>
        From the town&rsquo;s minutes ({n0(b.counts.official_votes_read)} of {n0(b.counts.minutes)} sets read) and our minutes of the recordings ({n0(b.counts.our_minutes)}), joined per meeting: {n0(substantive.length)} substantive, {n0(b.votes.length - substantive.length)} procedural (accepting minutes, adjourning). Where both records have a vote the town&rsquo;s wording stands{b.counts.vote_conflicts ? <>; <strong style={{ color: 'var(--status-critical)' }}>{n0(b.counts.vote_conflicts)} disagree on the outcome</strong> and say so</> : '; none disagree on the outcome'}.
        <button className="underline ml-2" onClick={() => setAll(!all)}>{all ? 'hide procedural' : 'show procedural too'}</button>
      </p>
      <VotesTable votes={all ? b.votes : substantive} />
      <p className="text-xs mt-1 max-w-3xl" style={kicker}>The town&rsquo;s minutes are the record: a vote from them carries the minutes&rsquo; own words, checked verbatim. A vote from the recording only was written by a language model from machine captions &mdash; a motion as heard, and “not audible” a finding about the recording &mdash; and links to the second in the video.</p>
    </>
  )
}

function TimeTab({ b }: { b: Board }) {
  return (
    <>
      <p className="text-sm mt-5 max-w-3xl" style={{ color: 'var(--text-secondary)' }}>{hours(b.time_span_s)} of discussion across the {b.time_meetings} recorded meetings we have minutes for, by topic. A topic can overlap another, so the shares can sum past 100%.</p>
      <TimeBars b={b} />
    </>
  )
}

function ScheduleTab({ b }: { b: Board }) {
  return (
    <>
      <p className="text-sm mt-5 max-w-3xl" style={{ color: 'var(--text-secondary)' }}>Measured from this board’s own posted agendas over the last {b.calendar_cycles.length} budget cycles (July to June): the dates each subject appeared. The “expect” column is the typical first and last date across those cycles — a scheduled subject, not a decision.</p>
      <div className="overflow-x-auto mt-3">
        <table className="text-sm" style={{ minWidth: 640 }}>
          <thead><tr className="text-[10px] font-bold uppercase tracking-widest" style={kicker}>
            <th className="text-left py-1.5 pr-4">subject</th><th className="text-left py-1.5 pr-4">expect</th>{b.calendar_cycles.map(fy => <th key={fy} className="text-left py-1.5 pr-3">{FY(fy)}</th>)}</tr></thead>
          <tbody>{b.calendar.map(cl => (
            <tr key={cl.key} style={{ borderTop: '1px solid var(--grid)' }}>
              <td className="py-2 pr-4 font-semibold align-top">{cl.label}</td>
              <td className="py-2 pr-4 align-top whitespace-nowrap tnum">{cl.typical_first}{cl.typical_first !== cl.typical_last ? ` → ${cl.typical_last}` : ''}</td>
              {b.calendar_cycles.map(fy => { const cy = cl.cycles.find(x => x.fy === fy); return <td key={fy} className="py-2 pr-3 align-top text-xs tnum" style={{ color: 'var(--text-secondary)' }}>{cy ? cy.dates.map(mmdd).join(', ') : '—'}</td> })}
            </tr>))}</tbody>
        </table>
      </div>
      <p className="text-xs mt-1 max-w-3xl" style={kicker}>A cycle is named for the fiscal year it builds: {FY(b.calendar_cycles[b.calendar_cycles.length - 1])} is the budget being built now. Read off the agenda text with a word search, so a subject named differently on an agenda is missed and one mentioned in passing is counted.</p>
    </>
  )
}

/** ABOUT -- what the board is, as the town and its own documents say. Everything here was
 *  the top of the old page or the sidebar's infobox: the description, the members, the
 *  charter, the broadcast schedule, the committee's own rules, the annual-report record. */
function AboutTab({ b }: { b: Board }) {
  const p = b.page
  const charts = useOrgCharts(b.slug)
  const ar = b.annual_report
  return (
    <>
      {p && (
        <div className="card p-4 mt-6 max-w-3xl">
          {p.overview
            ? <Overview text={p.overview} who={p.source === 'district' ? 'the district' : 'the town'} />
            : <p className="text-sm" style={kicker}>The {p.source === 'district' ? 'district’s' : 'town’s'} page lists the members and the meetings and carries no statement of what the board is for; the Charter and bylaws do.</p>}
        </div>
      )}
      <div className="grid gap-3 mt-4 md:grid-cols-2 max-w-3xl items-start">
        {p && (
          <div className="card p-4 text-[13px]" style={{ color: 'var(--text-secondary)' }}>
            {p.members.length > 0 && <><Kicker>Members, as posted</Kicker><ul className="mt-1 space-y-0.5">{p.members.map((m, i) => <li key={i}>{m}</li>)}</ul></>}
            {p.charter_ref && <div className="mt-3"><Kicker>Established by</Kicker><p className="mt-0.5">{p.charter_ref}</p></div>}
            {p.meets && <div className="mt-3"><Kicker>Broadcast and rebroadcast, as the {p.source === 'district' ? 'district' : 'town'} states it</Kicker><p className="mt-0.5 text-[12px]" style={{ whiteSpace: 'pre-line' }}>{p.meets}</p></div>}
            <p className="text-[11px] mt-3" style={kicker}>From <a className="underline" href={p.mirror}>our copy</a> of the page, {p.fetched_at}.</p>
          </div>
        )}
        <div className="card p-4 text-[13px]">
          <Kicker>Its pages elsewhere</Kicker>
          <ul className="mt-1 space-y-1">
            {p && <li><a className="underline" href={p.url}>{p.source === 'district' ? 'The district’s page' : 'The town’s page'} ↗</a></li>}
            {p?.facebook && p.facebook_scope === 'board' && <li><a className="underline" href={p.facebook}>Facebook ↗</a></li>}
            {p && <li><a className="underline" href={p.charter_url}>Charter &amp; bylaws ↗</a></li>}
            {charts.map(c => <li key={c.chart_url}><a className="underline" href={c.chart_url}>Org chart{charts.length > 1 ? `: ${c.unit}` : ''}</a></li>)}
          </ul>
          {p?.facebook_scope !== 'board' && p && <p className="text-xs mt-2" style={kicker}>No Facebook page of its own is linked from the board’s page.</p>}
        </div>
      </div>
      {ar && (
        <p className="text-[13px] mt-4 max-w-3xl" style={{ color: 'var(--text-secondary)' }}>
          <strong>Annual report:</strong>{' '}
          {ar.filed === 0
            ? <>has filed none in the {ar.of_years} years the town has asked{ar.said_none > 0 && <>, and the contents page printed “No&nbsp;Report&nbsp;Submitted” beside it {ar.said_none} time{ar.said_none === 1 ? '' : 's'}</>}.</>
            : <>filed in {ar.filed} of the {ar.of_years} years the town has asked, FY{ar.first}–FY{ar.last}{ar.said_none > 0 && <>; the contents page printed “No&nbsp;Report&nbsp;Submitted” beside it {ar.said_none} time{ar.said_none === 1 ? '' : 's'} ({ar.years_said_none.map(y => `FY${y}`).join(', ')})</>}.</>}
          {' '}<span style={kicker}>The town’s own words, off the contents page of each annual report.</span>
        </p>
      )}
      {/* THE COMMITTEE'S OWN RULES FOR ITSELF, shown in full. TJ, 17 September 2026: "post
          the new 'operating procedures' directly on the school committee page in the app for
          reference. It's quite interesting." */}
      {(b.about_itself ?? []).filter(x => x.key === 'protocols').map(x => (
        <div key={x.key} className="card p-4 mt-6 max-w-3xl">
          <Kicker>The committee&rsquo;s own rules for itself{x.school_year ? ` · ${x.school_year}` : ''}</Kicker>
          <h3 className="text-[16px] font-bold mt-1">{x.label}</h3>
          <p className="text-xs mt-1" style={kicker}>As the committee posted it: <a className="underline" href={x.url}>the PDF</a> · <a className="underline" href={x.upstream} rel="noreferrer">the district&rsquo;s copy</a>. Reproduced here in full for reference; the PDF is the record.</p>
          {x.text && <div className="text-[13.5px] leading-relaxed mt-3 whitespace-pre-line" style={{ color: 'var(--text-secondary)' }}>{x.text}</div>}
        </div>
      ))}
      {(b.about_itself ?? []).filter(x => x.key === 'calendar').map(x => (
        <p key={x.key} className="text-sm mt-3" style={{ color: 'var(--text-secondary)' }}>The committee&rsquo;s <a className="underline" href={x.url}>{x.school_year} meeting calendar</a>, as posted.</p>
      ))}
    </>
  )
}

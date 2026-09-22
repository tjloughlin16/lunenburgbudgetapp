import { useState } from 'react'
import { boardSlugFromPath, type Tab } from '../routes'
import { Body, H2, ReportShell, useReport } from '../components/report'
import { BoardGoals } from '../components/BoardGoals'
import { Subscribe, useFeedLink } from '../components/Subscribe'
import { JoinLinks, daysFromToday, todayIso, type Join } from '../components/BoardsThisWeek'

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

type Upcoming = { date: string; days_away: number; agenda_url: string; join?: Join | null; hook?: string | null; time?: string | null; where?: string | null; attend?: string | null; important?: unknown; items?: { agenda_line: string; why_it_matters?: string; important?: boolean }[] | null }
type Score = { fy: number; minutes: { meetings: number; have: number }; recordings: { meetings: number; have: number } }
type Recent = { date: string; agenda_url?: string | null; agenda_doc?: string | null; minutes_url?: string | null; minutes_doc?: string | null; video_url?: string | null; transcript: boolean; captions_disabled: boolean; ours?: { slug: string; headline?: string | null; digest?: string | null; votes?: number; reconciled?: boolean; discrepancies?: number } | null }
type Vote = { date: string; t?: number | null; motion?: string; outcome?: string; procedural: boolean; moved_by?: string | null; page: string | null; video_url: string | null
  source: 'minutes' | 'recording' | 'both'; quote?: string | null; conflict?: string | null; minutes_doc?: string | null; minutes_url?: string | null }
type Cal = { key: string; label: string; cycles: { fy: number; dates: string[] }[]; earliest: string; latest: string; typical_first: string; typical_last: string; meetings: number }
type Page = { url: string; source: 'town' | 'district'; overview: string; charter_ref: string; meets: string; members: string[]; facebook: string | null; facebook_scope: string; mirror: string; fetched_at: string; charter_url: string }
type Board = {
  slug: string; name: string; the_three: boolean; page?: Page | null
  about_itself?: { key: string; label: string; school_year: string; url: string; upstream: string; sha256: string; text: string }[]
  scorecard?: { this: Score; last: Score; minutes_lag_days: number; video_lag_days: number }
  finance?: { accounts: number; funds: number; related: number } | null
  join?: { weekday?: string; weekday_share?: number; meetings_sampled?: number; time?: string | null; place?: string | null; zoom?: boolean; cable?: boolean; agendas_read?: number; open_seats?: number; open_seats_fy?: string; open_seats_filled_by?: string } | null
  counts: { agendas: number; minutes: number; recordings: number; transcripts: number; captions_disabled: number; our_minutes: number; official_votes_read: number; votes: number; vote_conflicts: number; first: string | null; last: string | null }
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
  useFeedLink(slug ? (b ? `/feeds/${b.slug}.xml` : null) : '/feeds/all.xml', b ? `${b.name} — Lunenburg Budget Project` : 'Every board — Lunenburg Budget Project')
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
  const openTotal = d.boards.reduce((n, b) => n + (b.join?.open_seats ?? 0), 0)
  const openBoards = d.boards.filter(b => (b.join?.open_seats ?? 0) > 0).length
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
      standfirst={`${d.boards.length} boards and committees the town posts for. What is coming, what happened, every vote we have minutes for, where the time goes, and when budget planning lands — one page each.`}
      dataUrl={DATA}>
      {/* OPEN SEATS FIRST. TJ, 22 September 2026: "put the link to open spots here". Of
          everything on this index it is the only line that asks the reader to DO
          something, and a resident who came here wondering how to get involved should not
          have to read sixty cards to find out they can. */}
      {openTotal > 0 && (
        <p className="text-[14px] mt-5 max-w-3xl">
          <a className="font-semibold underline" style={{ color: 'var(--series-cost)' }} href="/analysis/open-seats">
            {openTotal === 1 ? 'One open seat on a town board' : `${openTotal} open seats across ${openBoards} town boards`} &rarr;
          </a>
          <span style={{ color: 'var(--text-secondary)' }}> &mdash; the boards with a chair going spare, and when the filled ones come up.</span>
        </p>
      )}
      <p className="text-[14px] mt-5 max-w-3xl">
        <a className="font-semibold underline" style={{ color: 'var(--series-cost)' }} href="/boards/compared">The boards, compared &rarr;</a>
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

/** THE SIDEBAR. TJ, on the first draft: "the design is overwhelming. We need a sidebar with
 *  all the main links, as a sort of floating button holder." On a wide screen it is a
 *  sticky column beside the page: where to jump on this page, then where else to go for
 *  this board. On a phone it is a floating button at the bottom right that opens the same
 *  list as a sheet, so the links are one tap away without taking the top of the page. */
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

function Sidebar({ b, open, setOpen }: { b: Board; open: boolean; setOpen: (v: boolean) => void }) {
  const jump: [string, string, boolean][] = [
    ['#up', 'Upcoming meetings', true], ['#recent', 'Recent meetings', true], ['#votes', 'Votes', b.votes.length > 0],
    ['#time', 'Time tracking', b.time_by_tag.length > 0], ['#calendar', 'Budget schedule', b.calendar.length > 0],
  ]
  const p = b.page
  // For THIS board only -- TJ: "'This week', 'meeting minutes' and 'all boards' are not
  // specific to the current board." Those go in a third group, named for what they are.
  const own: [string, string][] = [
    ...(p ? [[p.url, p.source === 'district' ? 'District page ↗' : 'Town page ↗'] as [string, string]] : []),
    ...(p?.facebook && p.facebook_scope === 'board' ? [[p.facebook, 'Facebook ↗'] as [string, string]] : []),
    ...(b.counts.our_minutes ? [[`${b.urls.what_was_said}#${b.slug}`, 'Its meeting minutes'] as [string, string]] : []),
    ...(b.finance ? [[`/boards/${b.slug}/finance`, `Finance — ${b.finance.accounts} account${b.finance.accounts === 1 ? '' : 's'}`] as [string, string]] : []),
    ...(p ? [[p.charter_url, 'Charter & bylaws ↗'] as [string, string]] : []),
  ]
  const elsewhere: [string, string][] = [
    ['/this-week', 'This week, all boards'],
    [b.urls.what_was_said, 'All meeting minutes'],
    ['/boards', 'All boards'],
  ]
  const Btn = ({ href, children, strong }: { href: string; children: React.ReactNode; strong?: boolean }) => (
    <a href={href} onClick={() => setOpen(false)}
      className="block px-3 py-2 rounded-lg text-[13px] font-semibold transition-opacity hover:opacity-80"
      style={{ background: strong ? 'var(--text-primary)' : 'var(--surface-3)', color: strong ? 'var(--surface-1)' : 'var(--text-primary)' }}>{children}</a>
  )
  // THE INFOBOX: the facts about the board and its posting record, in a card UNDER the
  // links. TJ: "scrolling sidebar isn't my favorite" -- nothing scrolls inside anything.
  const sc = b.scorecard
  const facts = sc || (p && (p.charter_ref || p.meets || p.members.length > 0)) ? (
    <div className="card p-3 text-[12.5px]" style={{ color: 'var(--text-secondary)' }}>
      {sc && (
        <div className="pb-3 mb-1" style={{ borderBottom: '1px solid var(--grid)' }}>
          <p className="text-[10px] font-bold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>Posting record</p>
          <Chip what="minutes" sc={sc} title={`Of meetings with a posted agenda, those with minutes on the town’s Agenda Center. Meetings in the last ${sc.minutes_lag_days} days are not counted: minutes are approved at the next meeting.`} />
          <Chip what="recordings" sc={sc} title={`Of meetings with a posted agenda, those with a recording on the town’s YouTube channel. Meetings in the last ${sc.video_lag_days} days are not counted.`} />
          <a className="block text-[10.5px] underline mt-1.5" style={{ color: 'var(--text-muted)' }} href="/boards/compared">compared with every board &rarr;</a>
        </div>
      )}
      {p && p.charter_ref && <><p className="text-[10px] font-bold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>Established by</p><p className="mt-0.5">{p.charter_ref}</p></>}
      {p && p.meets && <><p className="text-[10px] font-bold uppercase tracking-widest mt-3" style={{ color: 'var(--text-muted)' }}>Broadcast and rebroadcast, as the {p.source === 'district' ? 'district' : 'town'} states it</p><p className="mt-0.5 text-[11.5px]" style={{ whiteSpace: 'pre-line', color: 'var(--text-muted)' }}>{p.meets}</p></>}
      {p && p.members.length > 0 && <><p className="text-[10px] font-bold uppercase tracking-widest mt-3" style={{ color: 'var(--text-muted)' }}>Members, as posted</p><ul className="mt-0.5 space-y-0.5">{p.members.map((m, i) => <li key={i}>{m}</li>)}</ul></>}
      {p && <p className="text-[11px] mt-3" style={{ color: 'var(--text-muted)' }}>From <a className="underline" href={p.mirror}>our copy</a> of the page, {p.fetched_at}.</p>}
    </div>
  ) : null
  // HOW TO JOIN, ABOVE EVERYTHING. TJ, 17 September 2026: "if someone wants to join
  // live, what info do they need to know?" -- the weekday and time first and large, then
  // the room, then whether there is a Zoom and a broadcast. Read off the last few agendas
  // (build_boards.how_to_join), not the board's boilerplate; the rebroadcast schedule is
  // context and stays in the infobox below.
  const j = b.join
  const next = b.upcoming[0]
  // AN OPEN SEAT GOES ABOVE EVERYTHING ELSE ON THE PAGE. TJ, 22 September 2026: "on each
  // board page, if it has open spot, show that 'One Open Board Seat Available'". It is the
  // only thing here a reader can act on today, and it is perishable -- so it says which
  // annual report it came from rather than implying it is live.
  const openSeats = j?.open_seats ?? 0
  const seatBanner = openSeats > 0 ? (
    <a href="/analysis/open-seats" className="card p-3 mb-4 block no-underline"
       style={{ borderColor: 'var(--series-cost)', borderWidth: 2 }}>
      <p className="text-[15px] font-bold leading-snug" style={{ color: 'var(--series-cost)' }}>
        {openSeats === 1 ? 'One open board seat available' : `${openSeats} open board seats available`}
      </p>
      <p className="text-[12px] mt-1" style={{ color: 'var(--text-secondary)' }}>
        The town printed {openSeats === 1 ? 'a vacancy' : 'vacancies'} on this board in its FY{j?.open_seats_fy} annual
        report. {j?.open_seats_filled_by === 'elected'
          ? 'This is an elected seat — filled at the annual town election, third Saturday in May.'
          : 'This is an appointed seat — filled by the Select Board.'} See every open seat in town →
      </p>
    </a>
  ) : null
  const joinBlock = j && j.weekday ? (
    <div className="card p-3 mb-4">
      <p className="text-[10px] font-bold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>When it meets</p>
      <p className="text-[15px] font-bold leading-snug mt-1">
        {/* THE GUARD ABOVE TESTS `j.weekday`, NOT `j.weekday_share`. A board with a
            weekday and no share is possible in the payload, and under the strict build
            that is an error rather than a runtime surprise -- an absent share means we
            do not know how consistent the day is, which is `Usually`. */}
        {(j.weekday_share ?? 0) >= 0.6 ? `${j.weekday}s` : `Usually ${j.weekday}s`}{j.time ? `, ${j.time}` : ''}
      </p>
      {j.place && <p className="text-[12.5px] mt-1" style={{ color: 'var(--text-secondary)' }}>{j.place}</p>}
      {(j.zoom || j.cable) && (
        <p className="text-[12px] mt-1" style={{ color: 'var(--text-secondary)' }}>
          {j.zoom ? 'Hybrid — a Zoom link is on each agenda' : ''}{j.zoom && j.cable ? ' · ' : ''}{j.cable ? 'broadcast live on the public access channel' : ''}
        </p>
      )}
      {next && <p className="text-[12.5px] mt-2"><strong>Next:</strong> {dateText(next.date)}</p>}
      <p className="text-[10.5px] mt-1.5" style={{ color: 'var(--text-muted)' }}>From the last {j.agendas_read} agendas; check the agenda for the meeting you mean.</p>
    </div>
  ) : null
  const body = (
    <>
      {seatBanner}
      {joinBlock}
      <p className="text-[10px] font-bold uppercase tracking-widest px-1" style={{ color: 'var(--text-muted)' }}>On this page</p>
      <div className="mt-1.5 space-y-1.5">{jump.filter(j => j[2]).map(([h, l]) => <Btn key={h} href={h}>{l}</Btn>)}</div>
      {own.length > 0 && <>
        <p className="text-[10px] font-bold uppercase tracking-widest px-1 mt-4" style={{ color: 'var(--text-muted)' }}>For this board</p>
        <div className="mt-1.5 space-y-1.5">{own.map(([h, l], i) => <Btn key={h} href={h} strong={i === 0}>{l}</Btn>)}</div>
      </>}
      <p className="text-[10px] font-bold uppercase tracking-widest px-1 mt-4" style={{ color: 'var(--text-muted)' }}>Elsewhere</p>
      <div className="mt-1.5 space-y-1.5">{elsewhere.map(([h, l]) => <Btn key={h} href={h}>{l}</Btn>)}</div>
    </>
  )
  return (
    <>
      {/* wide: sticky column */}
      {/* LINKS FIRST, then the board's facts and its posting record under them (TJ,
          17 September 2026: "LINKS first, then the sort of 'metadata' under it"). Both
          in one sticky block, so the links stay put and the facts do not slide under
          them as the page scrolls. */}
      <aside className="hidden lg:block" style={{ width: 240 }}>
        <div className="sticky" style={{ top: 72 }}>
          {body}
          {facts && <div className="mt-4">{facts}</div>}
        </div>
      </aside>
      {/* phone: floating button and sheet */}
      <div className="lg:hidden no-print">
        <button onClick={() => setOpen(!open)} aria-expanded={open}
          className="fixed z-40 rounded-full px-4 py-2.5 text-[13px] font-bold shadow-lg"
          style={{ right: 16, bottom: 16, background: 'var(--text-primary)', color: 'var(--surface-1)' }}>
          {open ? 'Close' : 'Links'}
        </button>
        {open && (
          <div className="fixed z-30 inset-x-0 bottom-0 card p-4 rounded-b-none" style={{ maxHeight: '70vh', overflowY: 'auto', paddingBottom: 72, boxShadow: '0 -8px 24px rgba(0,0,0,.12)' }}>{body}{facts && <div className="mt-4">{facts}</div>}</div>
        )}
      </div>
    </>
  )
}

/** THE SCORECARD, AS TWO CHIPS IN THE SIDEBAR. TJ, 17 September 2026: "put the
 *  percentages of the current fiscal year of minutes and video postings on each
 *  board's page ... '66% minutes FY27' ... (in nice designs...)" -- and, on the first
 *  version, "those metrics are far too central on the board page. I was expecting a
 *  sort of sidebar progress report or small chip." So: a percentage, a hairline bar
 *  and the counts, in the infobox. Each chip leads with the current fiscal year once
 *  it has three meetings old enough to count, and with last year until then, because
 *  "0% minutes FY27" in September is one July meeting whose minutes are simply due. */
function Chip({ what, sc, title }: { what: 'minutes' | 'recordings'; sc: { this: Score; last: Score }; title: string }) {
  const lead = sc.this[what].meetings >= 3 ? sc.this : sc.last
  const other = lead === sc.this ? sc.last : sc.this
  const L = lead[what], O = other[what]
  const p = L.meetings ? Math.round(100 * L.have / L.meetings) : null
  const tone = p === null ? 'var(--text-muted)' : p >= 90 ? 'var(--status-good)' : p >= 60 ? 'var(--text-primary)' : 'var(--status-critical)'
  return (
    <div className="mt-2" title={title}>
      <div className="flex items-baseline justify-between gap-2">
        <span className="text-[11px]" style={{ color: 'var(--text-muted)' }}>{what === 'minutes' ? 'minutes posted' : 'on YouTube'} · FY{String(lead.fy).slice(2)}{lead === sc.this ? ' so far' : ''}</span>
        <span className="text-[15px] font-bold tnum" style={{ color: tone }}>{p === null ? '—' : `${p}%`}</span>
      </div>
      <div className="h-1 rounded-full mt-1 overflow-hidden" style={{ background: 'var(--surface-3)' }}>
        <div className="h-full rounded-full" style={{ width: `${p ?? 0}%`, background: tone }} />
      </div>
      <p className="text-[10.5px] mt-0.5 tnum" style={{ color: 'var(--text-muted)' }}>
        {L.meetings ? `${L.have} of ${L.meetings}` : 'none old enough yet'}{O.meetings ? ` · FY${String(other.fy).slice(2)}${other === sc.this ? ' so far' : ''} ${O.have} of ${O.meetings}` : ''}
      </p>
    </div>
  )
}

function BoardPage({ b, d }: { b: Board; d: Payload }) {
  const [open, setOpen] = useState(false)
  const [allVotes, setAllVotes] = useState(false)
  const substantive = b.votes.filter(v => !v.procedural)
  const shown = allVotes ? b.votes : substantive
  const c = b.counts
  return (
    <ReportShell tab={TAB} title={b.name}
      standfirst={<>{c.first ? `Posted since ${c.first.slice(0, 4)}: ` : ''}{n0(c.agendas)} agendas, {n0(c.minutes)} sets of minutes, {n0(c.recordings)} recordings{c.our_minutes ? `, ${n0(c.our_minutes)} meetings with our minutes and ${n0(c.votes)} votes on the record` : ''}. <a className="underline" href="/boards">All boards</a>.</>}
      dataUrl={DATA}>
     <div className="lg:flex lg:gap-8 lg:items-start">
     <div className="min-w-0 flex-1">

      {/* ------------------------------------------------------- what it is */}
      {b.page && (
        <div className="card p-4 mt-6 max-w-3xl">
          {b.page.overview ? (
            <Overview text={b.page.overview} who={b.page.source === 'district' ? 'the district' : 'the town'} />
          ) : (
            <p className="text-sm mt-3" style={{ color: 'var(--text-muted)' }}>The {b.page.source === 'district' ? 'district’s' : 'town’s'} page lists the members and the meetings and carries no statement of what the board is for; the Charter and bylaws do.</p>
          )}
          {b.page.facebook_scope !== 'board' && <p className="text-xs mt-2" style={{ color: 'var(--text-muted)' }}>No Facebook page of its own is linked from the board’s page.</p>}
        </div>
      )}

      {/* WHAT THE BOARD SAID IT WOULD DO, near the top because it is the frame every
          other section on this page is read against: the meetings, the votes and the
          minutes are how a board got on with what it committed to. */}
      <BoardGoals slug={b.slug} />

      {/* THE COMMITTEE'S OWN RULES FOR ITSELF, shown in full. TJ, 17 September 2026:
          "post the new 'operating procedures' directly on the school committee page in
          the app for reference. It's quite interesting." From the district's meetings
          page, as the crawler files it; the PDF and the district's copy are linked. */}
      {(b.about_itself ?? []).filter(d => d.key === 'protocols').map(d => (
        <div key={d.key} className="card p-4 mt-6 max-w-3xl">
          <p className="text-[11px] font-semibold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>The committee&rsquo;s own rules for itself{d.school_year ? ` · ${d.school_year}` : ''}</p>
          <h3 className="text-[16px] font-bold mt-1">{d.label}</h3>
          <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>
            As the committee posted it: <a className="underline" href={d.url}>the PDF</a> · <a className="underline" href={d.upstream} rel="noreferrer">the district&rsquo;s copy</a>. Reproduced here in full for reference; the PDF is the record.
          </p>
          {d.text && (
            <div className="text-[13.5px] leading-relaxed mt-3 whitespace-pre-line" style={{ color: 'var(--text-secondary)' }}>{d.text}</div>
          )}
        </div>
      ))}
      {(b.about_itself ?? []).filter(d => d.key === 'calendar').map(d => (
        <p key={d.key} className="text-sm mt-3" style={{ color: 'var(--text-secondary)' }}>
          The committee&rsquo;s <a className="underline" href={d.url}>{d.school_year} meeting calendar</a>, as posted.
        </p>
      ))}

      {b.scorecard && (
        /* Phone only: the sidebar's two chips as one line, since the infobox is behind the Links button there. */
        <p className="lg:hidden text-[12px] mt-3 tnum" style={{ color: 'var(--text-secondary)' }}>
          {(['minutes', 'recordings'] as const).map((w, i) => {
            const sc = b.scorecard!
            const lead = sc.this[w].meetings >= 3 ? sc.this : sc.last
            const L = lead[w]; const pc = L.meetings ? Math.round(100 * L.have / L.meetings) : null
            return <span key={w}>{i ? ' · ' : ''}<strong style={{ color: pc === null ? 'var(--text-muted)' : pc >= 90 ? 'var(--status-good)' : pc >= 60 ? 'var(--text-primary)' : 'var(--status-critical)' }}>{pc === null ? '—' : `${pc}%`}</strong> {w === 'minutes' ? 'minutes posted' : 'on YouTube'}, FY{String(lead.fy).slice(2)}{lead === sc.this ? ' so far' : ''} ({L.have} of {L.meetings})</span>
          })}
          {' · '}<a className="underline" href="/boards/compared">compared</a>
        </p>
      )}
      <p className="text-[13px] mt-4"><a className="underline font-semibold" style={{ color: 'var(--series-cost)' }} href="/boards/compared">How the {b.name} compares with the other boards &rarr;</a></p>
      {/* THE FINANCE TAB. TJ, 17 September 2026: "Every board should have a 'Finance' tab". */}
      {b.finance && <p className="text-[13px] mt-2"><a className="underline font-semibold" style={{ color: 'var(--series-revenue)' }} href={`/boards/${b.slug}/finance`}>Finance: the {b.finance.accounts} account{b.finance.accounts === 1 ? '' : 's'} the {b.name} owns{b.finance.funds ? `, ${b.finance.funds} of them funds` : ''} &rarr;</a></p>}
      <Subscribe path={`/feeds/${b.slug}.xml`} what={`the ${b.name} posts or changes an agenda, or a meeting’s recording, transcript and our minutes are all in`} />

      {/* ---------------------------------------------------------------- upcoming */}
      <H2 id="up">Upcoming meetings</H2>
      {b.upcoming.length === 0 ? (
        <p className="text-sm mt-2" style={{ color: 'var(--text-secondary)' }}>No agenda posted for a future date, as of {d.as_of}. Agendas usually appear two days before a meeting.</p>
      ) : b.upcoming.filter(u => u.date >= todayIso()).map(u => (
        <div key={u.date} className="card p-4 mt-3">
          <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
            <span className="font-bold">{dateText(u.date)}</span>
            {u.time && <span className="text-xs px-2 py-0.5 rounded" style={{ background: 'var(--surface-3)' }}>{u.time}</span>}
            {u.where && <span className="text-xs px-2 py-0.5 rounded" style={{ background: 'var(--surface-3)' }}>{u.where}</span>}
            {u.attend && <span className="text-xs px-2 py-0.5 rounded" style={{ background: 'var(--surface-3)' }}>{u.attend}</span>}
            <span className="text-xs" style={{ color: 'var(--text-muted)' }}>{daysFromToday(u.date) === 0 ? 'today' : daysFromToday(u.date) === 1 ? 'tomorrow' : `in ${daysFromToday(u.date)} days`}</span>
          </div>
          {u.hook && <p className="text-[15px] mt-2">{u.hook}</p>}
          <JoinLinks j={u.join} />
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
      <H2 id="recent">Recent meetings</H2>
      <div className="overflow-x-auto mt-3">
        <table className="text-sm w-full" style={{ minWidth: 720 }}>
          <thead><tr className="text-[10px] font-bold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>
            {/* COLUMNS IN THE ORDER WE WANT THEM USED -- our minutes, the recording, the
                agenda, the town's minutes (TJ, 17 September 2026). */}
            <th className="text-left py-1.5 pr-3">date</th><th className="text-left py-1.5 pr-3">our minutes</th><th className="text-left py-1.5 pr-3">recording</th><th className="text-left py-1.5 pr-3">agenda</th><th className="text-left py-1.5">official minutes</th></tr></thead>
          <tbody>{b.recent.map(r => (
            <tr key={r.date} style={{ borderTop: '1px solid var(--grid)' }}>
              <td className="py-2 pr-3 tnum font-semibold whitespace-nowrap align-top">{mmdd(r.date)} {r.date.slice(0, 4)}</td>
              <td className="py-2 pr-3 align-top">{r.ours ? <><a className="font-semibold" href={`/meeting-minutes/${r.ours.slug}`} style={{ color: 'var(--series-cost)' }}>{r.ours.headline || 'our minutes'}</a><span className="text-xs" style={{ color: 'var(--text-muted)' }}> · {r.ours.votes ?? 0} votes{r.ours.reconciled ? (r.ours.discrepancies ? ` · ${r.ours.discrepancies} difference${r.ours.discrepancies === 1 ? '' : 's'} from the official minutes` : ' · agrees with the official minutes') : ''}</span></> : r.transcript ? <span className="text-xs" style={{ color: 'var(--text-muted)' }}>transcript held; minutes not yet written</span> : <span style={{ color: 'var(--text-muted)' }}>—</span>}</td>
              <td className="py-2 pr-3 align-top">{r.video_url ? <a className="underline" href={r.video_url}>video</a> : <span style={{ color: 'var(--text-muted)' }}>—</span>}{r.video_url && r.captions_disabled ? <span className="text-xs" style={{ color: 'var(--text-muted)' }}> · no captions</span> : r.video_url && !r.transcript ? <span className="text-xs" style={{ color: 'var(--text-muted)' }}> · no transcript yet</span> : null}</td>
              <td className="py-2 pr-3 align-top">{r.agenda_doc ? <a className="underline" href={r.agenda_doc}>agenda</a> : <span style={{ color: 'var(--text-muted)' }}>—</span>}</td>
              <td className="py-2 align-top">{r.minutes_doc ? <a className="underline" href={r.minutes_doc}>minutes</a> : <span style={{ color: 'var(--text-muted)' }}>not yet</span>}</td>
            </tr>))}</tbody>
        </table>
      </div>
      <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>The last {b.recent.length} dates the town posted anything for this board. For a program, every agenda and set of minutes as one text file: <a className="underline" href={b.urls.minutes_text}>{b.urls.minutes_text}</a>.</p>

      {/* ------------------------------------------------------------------- votes */}
      {b.votes.length > 0 && (
        <>
          <H2 id="votes">Votes, newest first</H2>
          <p className="text-sm mt-1" style={{ color: 'var(--text-secondary)' }}>
            From the town&rsquo;s minutes ({n0(b.counts.official_votes_read)} of {n0(b.counts.minutes)} sets read) and our minutes of the recordings ({n0(b.counts.our_minutes)}), joined per meeting: {n0(substantive.length)} substantive, {n0(b.votes.length - substantive.length)} procedural (accepting minutes, adjourning). Where both records have a vote the town&rsquo;s wording stands{b.counts.vote_conflicts ? <>; <strong style={{ color: 'var(--status-critical)' }}>{n0(b.counts.vote_conflicts)} disagree on the outcome</strong> and say so</> : '; none disagree on the outcome'}.
            <button className="underline ml-2" onClick={() => setAllVotes(!allVotes)}>{allVotes ? 'hide procedural' : 'show all'}</button>
          </p>
          <div className="overflow-x-auto mt-3">
            <table className="text-sm w-full" style={{ minWidth: 760 }}>
              <thead><tr className="text-[10px] font-bold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>
                <th className="text-left py-1.5 pr-3">date</th><th className="text-left py-1.5 pr-3">motion</th><th className="text-left py-1.5 pr-3">outcome</th><th className="text-left py-1.5 pr-3">record</th><th className="text-left py-1.5">check it</th></tr></thead>
              <tbody>{shown.map((v, i) => (
                <tr key={i} style={{ borderTop: '1px solid var(--grid)', color: v.procedural ? 'var(--text-muted)' : undefined }}>
                  <td className="py-1.5 pr-3 tnum whitespace-nowrap align-top">{mmdd(v.date)} {v.date.slice(0, 4)}</td>
                  <td className="py-1.5 pr-3 align-top" style={{ minWidth: 320 }}>{v.motion}{v.moved_by ? <span className="text-xs" style={{ color: 'var(--text-muted)' }}> — moved by {v.moved_by}</span> : null}
                    {v.quote && <span className="block text-[11px] mt-0.5 italic" style={{ color: 'var(--text-muted)' }}>&ldquo;{v.quote}&rdquo;</span>}
                    {v.conflict && <span className="block text-[11px] mt-0.5 font-semibold" style={{ color: 'var(--status-critical)' }}>The two records disagree: {v.conflict}.</span>}</td>
                  <td className="py-1.5 pr-3 align-top font-semibold" style={{ maxWidth: 220, color: (v.outcome || '').startsWith('pass') ? 'var(--status-good)' : (v.outcome || '').startsWith('fail') ? 'var(--status-critical)' : 'var(--text-muted)' }}>{v.outcome}</td>
                  <td className="py-1.5 pr-3 align-top text-[11px] whitespace-nowrap" style={{ color: 'var(--text-muted)' }}>{v.source === 'both' ? 'minutes + recording' : v.source === 'minutes' ? 'the minutes' : 'the recording only'}</td>
                  <td className="py-1.5 align-top whitespace-nowrap text-[12.5px]">
                    {v.minutes_doc && <a className="underline" href={v.minutes_url || v.minutes_doc}>the minutes</a>}
                    {v.minutes_doc && v.video_url ? ' · ' : ''}
                    {v.video_url && <a className="underline" href={v.video_url}>{v.t != null ? `video ${Math.floor(v.t / 60)}:${String(v.t % 60).padStart(2, '0')}` : 'video'}</a>}
                    {v.page ? <> · <a className="underline" href={v.page}>ours</a></> : null}
                  </td>
                </tr>))}</tbody>
            </table>
          </div>
          <p className="text-xs mt-1 max-w-3xl" style={{ color: 'var(--text-muted)' }}>The town&rsquo;s minutes are the record: a vote from them carries the minutes&rsquo; own words, checked verbatim. A vote from the recording only was written by a language model from machine captions &mdash; a motion as heard, and “not audible” a finding about the recording &mdash; and links to the second in the video. Both records are read as they arrive and joined here, whichever came first.</p>
        </>
      )}

      {/* -------------------------------------------------------------------- time */}
      {b.time_by_tag.length > 0 && (
        <>
          <H2 id="time">Time tracking</H2>
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
          <H2 id="calendar">Budget schedule</H2>
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

      <p className="text-xs mt-8" style={{ color: 'var(--text-muted)' }}>As of {d.as_of}.</p>
     </div>
     <Sidebar b={b} open={open} setOpen={setOpen} />
     </div>
    </ReportShell>
  )
}

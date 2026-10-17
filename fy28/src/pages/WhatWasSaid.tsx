import type { Tab } from '../routes'
import { RecentMeetings } from '../components/RecentMeetings'
import { recordedSlugFromPath } from '../routes'
import { useShareMeta } from '../lib/title'
import { ReportShell, useReport, H2, Body, MoreReports } from '../components/report'

const TAB: Tab = 'recorded'
const DATA = '/data/recording-minutes.json'
const FILE = 'recording-minutes.json'

/** Where a meeting's full minutes are published: one file per board and calendar year
 *  (scripts/build_recording_minutes.py, shard_path). Derived from the slug itself, so a
 *  meeting page fetches its own board-year and never the index -- until 13 October 2026 it
 *  fetched every meeting in one 22 MB file to show one. */
function shardFile(slug: string) {
  const [board, rest] = slug.split('/')
  return `recording-minutes/${board}/${rest.slice(0, 4)}.json`
}

/** WHAT WAS SAID: our minutes of recorded meetings.
 *
 *  231 meetings in this town have no surviving record but the video, 162 of them School
 *  Committee. `write_recording_minutes.py` reads our machine captions of each recording
 *  and writes minutes in a fixed shape -- votes, transfers, budget items, decisions,
 *  topics with resolutions -- and this renders them.
 *
 *  TWO DERIVED LAYERS STAND BETWEEN THIS PAGE AND THE MEETING, and the page never lets a
 *  reader forget it. Every item is a link to the video at its second: the citation is
 *  the recording, never this page. A figure is shown AS HEARD, in its own style, because
 *  a caption model hears "fifteen hundred", "$1,500" and "$50" alike. Where the town
 *  published minutes for the same meeting they are linked first, as the record; ours
 *  are a finding aid to the recording.
 *
 *  Rule 7b: the page opens with what the meeting settled -- the summary and the votes --
 *  then the money, then the whole meeting in order, then what the captions could not
 *  carry. */

type Vote = { t: number; motion: string; outcome: string; procedural: boolean; moved_by?: string }
type BudgetItem = { t: number; topic: string; what_was_said: string; figures_as_heard?: string[] }
type Transfer = { t: number; description: string; amount_as_heard?: string; outcome: string }
type Decision = { t: number; decision: string }
type Topic = { t_start: number; t_end: number; topic: string; resolution: string; tags?: string[] }
/** `posted_name` is the board's posted roster where the hearing could be matched to it
 *  unambiguously, and within the member's current term; `matched_by` says how. See
 *  scripts/build_recording_minutes.py. The heard form is always kept. */
type Attendee = { name_as_heard: string; role: string; remote?: boolean; posted_name?: string; posted_role?: string; matched_by?: string }
type Comment = { t: number; topic: string; speaker_as_heard?: string; stated_role?: string }
type Minutes = {
  summary: string
  attendees?: Attendee[]
  public_comment?: Comment[]
  tags?: string[]
  votes: Vote[]
  budget_items: BudgetItem[]
  transfers: Transfer[]
  decisions: Decision[]
  topics: Topic[]
  not_audible: string[]
  confidence: 'high' | 'moderate' | 'low'
  /** Absent on minutes written before 15 October 2026: not looked for. */
  documents_mentioned?: DocHeard[]
  suggested_reports?: Suggested[]
}
/** A document or exhibit the captions refer to. The name is a CANDIDATE, as heard. */
type DocHeard = { t: number; name_as_heard: string; kind: string; shown?: boolean; words_as_heard: string }
/** A report the discussion shows a need for; `existing` names a page that already answers it. */
type Suggested = { slug: string; title: string; question: string; t: number; words_as_heard: string; data_in_play: string[]; existing: string }
type DocPrinted = { name: string; quote: string }
/** reconcile_minutes.compare_documents. Each side is null when it was NEVER LOOKED FOR --
 *  which is not an empty list and must not render as one (rule 13c). */
type Documents = {
  recording: DocHeard[] | null
  minutes_published: boolean
  minutes: { printed: boolean; heading: string; listed: DocPrinted[]; in_text: DocPrinted[]; doc_url?: string; minutes_url?: string } | null
  compared: { t: number; name_as_heard: string; kind: string; status: string; found: 'list' | 'text' | 'none'; minutes_name: string | null }[] | null
  unheard: string[] | null
}
type TownDoc = { kind: string; url: string; text_url: string; path: string }
type Finding = { kind: 'agree' | 'caption_error' | 'discrepancy' | 'only_in_ours' | 'only_in_official'; about: string; t?: number; ours: string; official: string; official_reading?: string; note: string }
type Reconciliation = { official: { url: string; text_url: string }; coverage: string; summary: string; counts: Record<string, number>; findings: Finding[]; written: { at: string } }
type Digest = { what_happened: { line: string; t: number }[]; why_it_matters: string[]; watch_next: string[]; written: { at: string } }
type Meeting = {
  slug: string
  digest?: Digest | null
  reconciliation?: Reconciliation | null
  // A MEETING POSTED TWICE (scripts/merge_recording_minutes.py). Both recordings are valid;
  // `labels` tags this page's items whose moment the other recording LACKS, by list and index,
  // and `missing_here` is what only the other recording has -- content cut from this one.
  recorded_twice?: {
    role: string
    others: { video_id: string; role: string }[]
    labels: Record<string, Record<string, string>>
    missing_here: { list: string; text: string; outcome: string; t: number | null; video_id: string; role: string }[]
  } | null
  documents?: Documents | null
  discrepancies?: number
  caption_errors?: number
  board_slug: string
  board: string
  date: string
  video_id: string
  video_url: string
  headline?: string
  summary: string
  confidence: string
  tags: string[]
  time_by_tag_s?: Record<string, number>
  topics_span_s?: number
  recording: { duration_s: number; duration: string; words_approx: number } | null
  counts: Record<string, number>
  town_published: TownDoc[]
  has_official_minutes: boolean
  source: { transcript: string; sha256: string; caption_lines: number; segments: number }
  written: { by: string; model: string; at: string; cost_usd: number | null }
  minutes: Minutes
}
/** What the index carries per meeting. The minutes themselves, the reconciliation and the
 *  digest are in the meeting's shard, at `data`. */
type IndexMeeting = Pick<Meeting, 'slug' | 'board_slug' | 'board' | 'date' | 'video_id' | 'video_url' | 'headline'
  | 'confidence' | 'tags' | 'recording' | 'counts' | 'town_published' | 'has_official_minutes'
  | 'discrepancies' | 'caption_errors' | 'written'> & { reconciled: boolean; data: string }
type Shard = { warning: string; board_slug: string; board: string; year: string; meetings: Meeting[] }
type BoardTime = { board: string; meetings: number; topics_span_s: number; by_tag_s: Record<string, number> }
type Payload = {
  warning: string
  what: string
  tags: Record<string, number>
  time_by_board: Record<string, BoardTime>
  time_note: string
  counts: { meetings: number; boards: number; without_official_minutes: number }
  boards: Record<string, { board: string; meetings: number; without_official_minutes: number }>
  meetings: IndexMeeting[]
}

function hms(s: number) {
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), x = s % 60
  return (h ? h + ':' : '') + String(m).padStart(h ? 2 : 1, '0') + ':' + String(x).padStart(2, '0')
}

function longDate(iso: string) {
  const [y, m, d] = iso.split('-').map(Number)
  return new Date(y, m - 1, d).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })
}

/** The timestamp, as the link it is. Every citation on the page goes through this. */
function At({ url, t }: { url: string; t: number }) {
  return (
    <a className="tnum text-xs font-semibold underline whitespace-nowrap" href={`${url}&t=${t}s`}
      target="_blank" rel="noreferrer" title="Open the recording at this moment"
      style={{ color: 'var(--series-revenue, #b5540f)' }}>&#9654; {hms(t)}</a>
  )
}

/** A figure as the captions rendered it: visibly not a figure from a document. */
function Heard({ s }: { s: string }) {
  return <span className="tnum px-1 rounded text-[12px]"
    style={{ background: 'var(--surface-3)', color: 'var(--text-secondary)', fontStyle: 'italic' }}
    title="As heard by the caption model. Not a figure from a document.">{s}</span>
}

export function WhatWasSaid() {
  const slug = recordedSlugFromPath(window.location.pathname)
  return slug ? <MeetingAt slug={slug} /> : <IndexAt />
}

function IndexAt() {
  const { d, err } = useReport<Payload>(FILE)
  if (!d) {
    return <ReportShell tab={TAB} title="What was said" err={err} loading={!err} dataUrl={DATA} />
  }
  return <Index d={d} />
}

function MeetingAt({ slug }: { slug: string }) {
  const file = shardFile(slug)
  const { d, err } = useReport<Shard>(file)
  // No shard for that board and year: the address names no meeting we hold. (A missing
  // file is a 404 in production and the app shell, which does not parse, under vite.)
  const missing = Boolean(err && /HTTP 404|JSON|Unexpected token/i.test(err))
  if (!d && !missing) {
    return <ReportShell tab={TAB} title="What was said" err={err} loading={!err} dataUrl={`/data/${file}`} />
  }
  // A date-only address: the one recording of that day, or the choice of them.
  const meetings = d ? d.meetings : []
  const byDay = /^([a-z0-9-]+)\/([0-9]{4}-[0-9]{2}-[0-9]{2})$/.exec(slug)
  const sameDay = byDay ? meetings.filter(x => x.board_slug === byDay[1] && x.date === byDay[2]) : []
  if (byDay && sameDay.length > 1) {
    return (
      <ReportShell tab={TAB} title={`${sameDay[0].board}, ${sameDay[0].date} — two recordings`} dataUrl={DATA}
        standfirst="This meeting was recorded in parts. Each has its own minutes.">
        <ul className="mt-6 space-y-2">{sameDay.map(x => (
          <li key={x.slug}><a className="underline font-semibold" style={{ color: 'var(--series-cost)' }} href={`/meeting-minutes/${x.slug}`}>{x.headline || x.slug}</a></li>))}</ul>
      </ReportShell>
    )
  }
  const m = meetings.find(x => x.slug === slug) ?? sameDay[0]
  if (!m) {
    return (
      <ReportShell tab={TAB} title="No minutes at this address" dataUrl={DATA}
        standfirst="Every recording with minutes is listed on the index.">
        <Body>The address <code>/meeting-minutes/{slug}</code> names no meeting. The index is{' '}
          <a className="underline" style={{ color: 'var(--series-cost)' }} href="/meeting-minutes">here</a>.</Body>
      </ReportShell>
    )
  }
  return <MeetingPage m={m} warning={d!.warning} dataUrl={`/data/${file}`} />
}

function Index({ d }: { d: Payload }) {
  const tag = new URL(window.location.href).searchParams.get('tag') || ''
  const shown = tag ? d.meetings.filter(m => m.tags.includes(tag)) : d.meetings
  const boards = Object.entries(d.boards).sort((a, b) => b[1].meetings - a[1].meetings)
    .filter(([slug]) => shown.some(m => m.board_slug === slug))
  return (
    <ReportShell tab={TAB} title="Meeting minutes, written from the recordings"
      standfirst="Our minutes of every recorded meeting we have processed — votes, transfers, budget items and decisions, each linked to the second in the video. One board at a time: open the board you want."
      dataUrl={DATA}>
      <p className="mt-6 text-sm" style={{ color: 'var(--text-secondary)' }}>
        <strong>{d.counts.meetings}</strong> meetings across <strong>{d.counts.boards}</strong> boards,{' '}
        <strong>{d.counts.without_official_minutes}</strong> of them with no minutes published by the town.
      </p>
      <Caveat warning={d.warning} />
      {/* TOPICS, as a controlled list -- TJ: "TOPICS flagged. athletics. primary school."
          One tag means one thing across every board, so a reader can follow athletics
          from the School Committee to the Select Board. Counts are meetings, not
          mentions. */}
      <p className="mt-6 text-xs" style={{ color: 'var(--text-muted)' }}>By topic — the number is meetings that touched it:</p>
      <p className="mt-1 flex flex-wrap gap-1.5">
        {tag && <a href="/meeting-minutes" className="px-2 py-0.5 text-xs rounded border font-semibold"
          style={{ borderColor: 'var(--text-primary)', color: 'var(--text-primary)' }}>all meetings ×</a>}
        {Object.entries(d.tags).map(([t, n]) => (
          <a key={t} href={`/meeting-minutes?tag=${t}`} className="px-2 py-0.5 text-xs rounded border"
            style={{ borderColor: t === tag ? 'var(--series-cost)' : 'var(--grid)', color: 'var(--series-cost)',
                     background: t === tag ? 'var(--surface-3)' : 'transparent' }}>{t.replace(/-/g, ' ')} <span className="tnum" style={{ color: 'var(--text-muted)' }}>{n}</span></a>
        ))}
      </p>
      {tag && <p className="mt-3 text-sm" style={{ color: 'var(--text-secondary)' }}><strong>{shown.length}</strong> meeting{shown.length === 1 ? '' : 's'} touched <strong>{tag.replace(/-/g, ' ')}</strong>.</p>}

      {/* WHERE THE TIME GOES. TJ: "How much time does that committee talk about X?" --
          "then we can figure out where boards are spending their time". Each topic's
          span from the captions' timestamps, summed by tag per board. A topic with two
          tags is credited to both, so the bars do not sum to the meeting; the share is
          of all topic time. Derived twice over and labelled so. */}
      {/* THE THING FIRST: the meetings that have happened and have no minutes yet,
          above everything else, because the most recent meeting is the one a reader
          came for and until 16 September it was the one this page could not show. */}
      {!tag && (
        <section className="mt-8" aria-label="Recent meetings">
          <H2>The last two weeks, whatever we have</H2>
          <RecentMeetings days={14} min={3} />
        </section>
      )}
      {!tag && d.time_by_board && (
        <section className="mt-8">
          <H2>Where the time goes</H2>
          <p className="text-xs mb-3" style={{ color: 'var(--text-muted)' }}>{d.time_note}</p>
          <div className="grid gap-4 sm:grid-cols-3">
            {Object.entries(d.time_by_board).map(([slug, b]) => {
              const top = Object.entries(b.by_tag_s).slice(0, 7)
              const max = top.length ? top[0][1] : 1
              const h = (s: number) => `${Math.floor(s / 3600)}h${String(Math.floor((s % 3600) / 60)).padStart(2, '0')}`
              return (
                <div key={slug} className="card p-3">
                  <p className="text-sm font-semibold">{b.board}</p>
                  <p className="text-xs" style={{ color: 'var(--text-muted)' }}>{b.meetings} meeting{b.meetings === 1 ? '' : 's'} · {h(b.topics_span_s)} of topics</p>
                  <ul className="mt-2 space-y-1">
                    {top.map(([t, sec]) => (
                      <li key={t} className="text-xs">
                        <div className="flex justify-between gap-2">
                          <a className="underline" href={`/meeting-minutes?tag=${t}`} style={{ color: 'var(--series-cost)' }}>{t.replace(/-/g, ' ')}</a>
                          <span className="tnum" style={{ color: 'var(--text-secondary)' }}>{h(sec)} · {Math.round(100 * sec / (b.topics_span_s || 1))}%</span>
                        </div>
                        <div className="h-1.5 rounded mt-0.5" style={{ background: 'var(--surface-3)' }}>
                          <div className="h-1.5 rounded" style={{ width: `${Math.round(100 * sec / max)}%`, background: 'var(--series-cost)' }} />
                        </div>
                      </li>
                    ))}
                  </ul>
                </div>
              )
            })}
          </div>
        </section>
      )}
      {/* ONE BOARD AT A TIME, COLLAPSED. TJ: "Each board needs to be collapsible and
          collapsed by default. Took me a minute to realize what it was showing." A filter
          by topic opens every board, because a reader who asked for a topic wants the
          meetings, not a list of headings. */}
      {boards.map(([slug, b]) => (
        <details key={slug} id={slug} className="mt-4 card px-4 py-3" style={{ scrollMarginTop: 80 }} open={Boolean(tag) || window.location.hash === `#${slug}`}>
          <summary className="cursor-pointer flex flex-wrap items-baseline gap-x-3 gap-y-0.5">
            <span className="text-xl font-bold tracking-tight">{b.board}</span>
            <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
              {shown.filter(m => m.board_slug === slug).length} meeting{shown.filter(m => m.board_slug === slug).length === 1 ? '' : 's'} · {b.without_official_minutes} with no official minutes · <a className="underline" href={`/boards/${slug}`}>the board’s page</a>
            </span>
          </summary>
          <ol className="space-y-3 mt-3">
            {shown.filter(m => m.board_slug === slug).map(m => (
              <li key={m.slug} className="card p-4">
                <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
                  <a className="font-semibold underline" href={`/meeting-minutes/${m.slug}`}
                    style={{ color: 'var(--series-cost)' }}>{longDate(m.date)}</a>
                  <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
                    {m.recording ? `${m.recording.duration} long · ` : ''}{m.counts.votes} vote{m.counts.votes === 1 ? '' : 's'} · {m.counts.transfers} transfer{m.counts.transfers === 1 ? '' : 's'} · {m.counts.budget_items} budget item{m.counts.budget_items === 1 ? '' : 's'} · {m.counts.public_comment} public comment{m.counts.public_comment === 1 ? '' : 's'}
                    {!m.has_official_minutes && <> · <span style={{ color: 'var(--series-revenue, #b5540f)' }}>no official minutes</span></>}
                    {m.reconciled && <> · checked against the town&rsquo;s minutes{m.discrepancies ? <span style={{ color: 'var(--series-revenue, #b5540f)' }}>: {m.discrepancies} difference{m.discrepancies === 1 ? '' : 's'} flagged</span> : ', no substantive differences'}</>}
                  </span>
                </div>
                <p className="text-sm mt-1 font-medium">{m.headline}</p>
                <p className="mt-1.5 flex flex-wrap gap-1">
                  {m.tags.map(t => <a key={t} href={`/meeting-minutes?tag=${t}`} className="px-1.5 py-0.5 text-[10.5px] rounded"
                    style={{ background: 'var(--surface-3)', color: 'var(--text-secondary)' }}>{t.replace(/-/g, ' ')}</a>)}
                </p>
              </li>
            ))}
          </ol>
        </details>
      ))}
      <MoreReports here={TAB} />
    </ReportShell>
  )
}

function Caveat({ warning }: { warning: string }) {
  return (
    <div className="card p-4 mt-4 max-w-3xl" style={{ borderLeft: '4px solid var(--series-revenue, #b5540f)' }}>
      <p className="text-[10.5px] font-bold uppercase tracking-widest" style={{ color: 'var(--series-revenue, #b5540f)' }}>
        These are ours, and they are not the record
      </p>
      <p className="text-sm mt-1" style={{ color: 'var(--text-secondary)' }}>{warning}</p>
    </div>
  )
}

/** DOCUMENTS AND EXHIBITS. The Open Meeting Law, M.G.L. c.30A s.22(a), asks minutes to
 *  carry "a list of documents and other exhibits used at the meeting". Two columns: what the
 *  town's minutes print, and what the recording refers to. THREE STATES on each side, and the
 *  page keeps them apart: not looked for (a file read before 15 October 2026), looked and
 *  none, and the list. A side never looked at is never drawn as an empty list. */
function DocumentsAndExhibits({ d, published, u }: { d: Documents | null; published: boolean; u: string }) {
  const muted = { color: 'var(--text-muted)' }
  const label = 'text-[10.5px] font-bold uppercase tracking-widest'
  const town = !published
    ? <p className="text-sm" style={muted}>The town has not published minutes for this meeting.</p>
    : !d || d.minutes === null
      ? <p className="text-sm" style={muted}>Not yet read for a documents list.</p>
      : <>
          {d.minutes.printed
            ? <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>The minutes print a list{d.minutes.heading ? <>, headed <q>{d.minutes.heading}</q></> : null}{d.minutes.listed.length ? ':' : ', with nothing under it.'}</p>
            : <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>The minutes print no list of documents and exhibits.</p>}
          {d.minutes.listed.length > 0 && (
            <ul className="mt-1 list-disc pl-5 space-y-0.5 text-sm">
              {d.minutes.listed.map((x, i) => <li key={i} title={`“${x.quote}”`}>{x.name}</li>)}
            </ul>
          )}
          {d.minutes.in_text.length > 0 && (
            <>
              <p className="text-xs mt-2" style={muted}>Named in the running text, not in a list:</p>
              <ul className="mt-1 list-disc pl-5 space-y-0.5 text-sm" style={{ color: 'var(--text-secondary)' }}>
                {d.minutes.in_text.map((x, i) => <li key={i} title={`“${x.quote}”`}>{x.name}</li>)}
              </ul>
            </>
          )}
        </>
  const byT = new Map((d?.compared || []).map(c => [c.t + '|' + c.name_as_heard, c]))
  const heard = !d || d.recording === null
    ? <p className="text-sm" style={muted}>Not yet looked for in the recording.</p>
    : d.recording.length === 0
      ? <p className="text-sm" style={muted}>No document was heard referred to.</p>
      : <ul className="space-y-1">
          {d.recording.map((x, i) => {
            const c = byT.get(x.t + '|' + x.name_as_heard)
            return (
              <li key={i} className="text-sm flex flex-wrap gap-x-2 items-baseline">
                <At url={u} t={x.t} />
                <span title={`as heard: “${x.words_as_heard}”`}><em>{x.name_as_heard}</em></span>
                <span className="text-xs" style={muted}>{x.kind}{x.shown ? ', shown' : ''}</span>
                {c && <span className="text-xs" style={{ color: c.found === 'list' ? 'var(--series-cost)' : 'var(--text-muted)' }}>· {c.status}{c.minutes_name && c.found !== 'none' ? ` (“${c.minutes_name}”)` : ''}</span>}
              </li>
            )
          })}
        </ul>
  return (
    <>
      <H2>Documents and exhibits</H2>
      <div className="grid sm:grid-cols-2 gap-x-8 gap-y-4 max-w-4xl">
        <div><p className={label} style={muted}>The town&rsquo;s minutes</p><div className="mt-1">{town}</div></div>
        <div><p className={label} style={muted}>Heard in the recording</p><div className="mt-1">{heard}</div></div>
      </div>
      {d && d.unheard && d.unheard.length > 0 && (
        <p className="text-xs mt-2" style={muted}>In the minutes&rsquo; list and not identified in the recording: {d.unheard.join('; ')}.</p>
      )}
      <p className="text-xs mt-2 max-w-3xl" style={muted}>
        State law asks minutes to list the documents and exhibits used at a meeting (M.G.L. c.30A &sect;22(a)). Names from the recording are the caption model&rsquo;s hearing; the two sides are matched by name, by script, so a document named two different ways can be missed. A place to look, not a finding.
      </p>
    </>
  )
}

/** Lost content, said on the item: "missing from the edited video". */
function Lost({ text }: { text?: string }) {
  if (!text) return null
  return <span className="text-[11px] font-semibold px-1.5 py-0.5 rounded whitespace-nowrap"
    style={{ background: 'var(--surface-3)', color: 'var(--status-critical)' }}>{text}</span>
}

const LIST_WORD: Record<string, string> = {
  votes: 'vote', decisions: 'decision', budget_items: 'money item', transfers: 'transfer',
  contention: 'dispute', concerns_and_conditions: 'concern', public_comment: 'public comment', topics: 'topic',
}

/** THIS MEETING WAS POSTED TWICE. Leads the page: it changes what a reader should trust. */
function PostedTwice({ m }: { m: Meeting }) {
  const rt = m.recorded_twice
  if (!rt) return null
  const here = rt.missing_here.length
  const tagged = Object.values(rt.labels).reduce((n, x) => n + Object.keys(x).length, 0)
  const other = (v: string) => `/meeting-minutes/${m.board_slug}/${m.date}-${v}`
  return (
    <div className="card p-4 mt-4 max-w-3xl" style={{ borderLeft: '4px solid var(--status-critical)' }}>
      <p className="text-[10.5px] font-bold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>Posted twice</p>
      <p className="text-sm mt-1">
        The town posted this meeting more than once. These are our minutes of <strong>{rt.role}</strong>; see also{' '}
        {rt.others.map((o, i) => <span key={o.video_id}>{i ? ', ' : ''}<a className="underline" href={other(o.video_id)}>{o.role}</a></span>)}.
        {' '}Both are valid, and we read both.
        {here > 0 && <> <strong>{here} item{here === 1 ? ' is' : 's are'} missing from this recording</strong> &mdash; the moment is not in it at all &mdash; and listed below.</>}
        {tagged > 0 && <> {tagged} item{tagged === 1 ? '' : 's'} here {tagged === 1 ? 'is' : 'are'} missing from the other recording, and tagged.</>}
        {here === 0 && tagged === 0 && <> Neither recording is missing anything the other has.</>}
      </p>
    </div>
  )
}

function MissingHere({ m }: { m: Meeting }) {
  const rt = m.recorded_twice
  if (!rt || rt.missing_here.length === 0) return null
  return (
    <>
      <H2>Missing from this recording</H2>
      <p className="text-sm max-w-3xl" style={{ color: 'var(--text-secondary)' }}>
        Heard only in {[...new Set(rt.missing_here.map(x => x.role))].join(' and ')}: the moment is not in this video.
        Each links to the second it was said there.
      </p>
      <ol className="space-y-2 mt-2">
        {rt.missing_here.map((x, i) => (
          <li key={i} className="card p-3 flex flex-wrap gap-x-3 gap-y-1 items-baseline">
            {x.t != null ? <At url={`https://www.youtube.com/watch?v=${x.video_id}`} t={x.t} /> : null}
            <span className="text-xs font-bold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>{LIST_WORD[x.list] ?? x.list}</span>
            <span className="text-sm flex-1 min-w-[16rem]">{x.text}</span>
            {x.outcome ? <span className="text-xs font-bold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>{x.outcome}</span> : null}
          </li>
        ))}
      </ol>
    </>
  )
}

function MeetingPage({ m, warning, dataUrl }: { m: Meeting; warning: string; dataUrl: string }) {
  const mm = m.minutes
  // THE LINK PREVIEW: the headline and the summary, so a meeting shared on Facebook says
  // what happened at it rather than what the site is (lib/title.ts).
  useShareMeta(m.headline ? `${m.headline}. ${m.summary}` : m.summary, 'article')
  const votes = mm.votes.filter(v => !v.procedural)
  const procedural = mm.votes.filter(v => v.procedural)
  const official = m.town_published.filter(x => x.kind === 'minutes')
  const agendas = m.town_published.filter(x => x.kind === 'agenda')
  const u = m.video_url
  // A transfer is also a budget item to the model; it has its own table above, so it is
  // not listed twice.
  const transferAt = new Set(mm.transfers.map(t => t.t))
  const money = mm.budget_items.filter(b => !transferAt.has(b.t))
  return (
    <ReportShell tab={TAB} kicker="What was said" title={`${m.board}, ${longDate(m.date)}`}
      dataUrl={dataUrl}
      meta={<span className="text-xs" style={{ color: 'var(--text-muted)' }}>
        <a className="underline" href={u} target="_blank" rel="noreferrer">the recording</a>
        {m.recording ? <>{' · '}{m.recording.duration} long, about {m.recording.words_approx.toLocaleString()} words spoken</> : null}
        {' · '}captions carried this meeting {mm.confidence === 'high' ? 'well' : mm.confidence === 'moderate' ? 'moderately well' : 'poorly'}
      </span>}>

      <PostedTwice m={m} />

      {/* THE RECORD FIRST, where one exists. Ours are the finding aid. */}
      {(official.length > 0 || agendas.length > 0) && (
        <p className="mt-4 text-sm" style={{ color: 'var(--text-secondary)' }}>
          The town published{' '}
          {official.map((x, i) => <span key={x.url}>{i ? ', ' : ''}<a className="underline font-semibold" style={{ color: 'var(--series-cost)' }} href={x.url} target="_blank" rel="noreferrer">minutes</a> (<a className="underline" href={x.text_url}>text</a>)</span>)}
          {official.length > 0 && agendas.length > 0 && ' and '}
          {agendas.map((x, i) => <span key={x.url}>{i ? ', ' : ''}<a className="underline" style={{ color: 'var(--series-cost)' }} href={x.url} target="_blank" rel="noreferrer">an agenda</a></span>)}
          {' '}for this meeting.{official.length > 0 ? ' Those minutes are the record; what follows is a guide to the recording.' : ' No minutes have been published; the recording is the only record, and what follows is a guide to it.'}
        </p>
      )}
      {m.town_published.length === 0 && (
        <p className="mt-4 text-sm" style={{ color: 'var(--text-secondary)' }}>
          The town has published neither minutes nor an agenda for this meeting. The recording is the only record, and what follows is a guide to it.
        </p>
      )}

      {/* THE DIGEST, FIRST. QUEUE 12a: "the digests ARE the product". What happened,
          each line linked to its second; why it matters, which is judgement and says so
          by its heading; what to watch. In the site's voice. */}
      {m.digest ? (
        <div className="card p-4 mt-6 max-w-3xl" style={{ borderLeft: '4px solid var(--series-cost)' }}>
          <p className="text-[10.5px] font-bold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>The short version</p>
          <ol className="mt-2 space-y-1.5">
            {m.digest.what_happened.map((w, i) => (
              <li key={i} className="text-[15px] leading-snug flex gap-3 items-baseline"><At url={u} t={w.t} /><span>{w.line}</span></li>
            ))}
          </ol>
          <p className="text-[10.5px] font-bold uppercase tracking-widest mt-4" style={{ color: 'var(--text-muted)' }}>Why it matters — our reading</p>
          <ul className="mt-1 space-y-1">
            {m.digest.why_it_matters.map((x, i) => <li key={i} className="text-sm" style={{ color: 'var(--text-secondary)' }}>{x}</li>)}
          </ul>
          {m.digest.watch_next.length > 0 && (
            <>
              <p className="text-[10.5px] font-bold uppercase tracking-widest mt-4" style={{ color: 'var(--text-muted)' }}>Watch next</p>
              <ul className="mt-1 space-y-1">
                {m.digest.watch_next.map((x, i) => <li key={i} className="text-sm" style={{ color: 'var(--text-secondary)' }}>{x}</li>)}
              </ul>
            </>
          )}
        </div>
      ) : <Body>{mm.summary}</Body>}
      {m.tags.length > 0 && (
        <p className="mt-2 flex flex-wrap gap-1">
          {m.tags.map(t => <a key={t} href={`/meeting-minutes?tag=${t}`} className="px-1.5 py-0.5 text-[11px] rounded"
            style={{ background: 'var(--surface-3)', color: 'var(--text-secondary)' }}>{t.replace(/-/g, ' ')}</a>)}
        </p>
      )}

      {(mm.attendees || []).length > 0 && (() => {
        // THE POSTED NAME WHERE IT IS KNOWN. This line printed "Manny Gilman's (member)"
        // on a public page about a real elected official, with the caveat after it. A
        // name the build matched to the board's posted roster is shown as posted, with
        // the heard form on hover; the rest stay as heard and are marked so. The caveat
        // sits beside the names it qualifies rather than after them.
        const list = mm.attendees || []
        const matched = list.filter(a => a.posted_name).length
        return (
          <p className="mt-4 text-sm" style={{ color: 'var(--text-secondary)' }}>
            <span className="font-semibold" style={{ color: 'var(--text-primary)' }}>Present: </span>
            {list.map((a, i) => (
              <span key={i}>{i ? '; ' : ''}
                {a.posted_name
                  ? <span title={`heard as “${a.name_as_heard}”; matched to the posted roster by ${a.matched_by}`}>{a.posted_name}</span>
                  : <span title="As heard by the caption model; not matched to a posted roster"><em>{a.name_as_heard}</em></span>}
                {' '}<span style={{ color: 'var(--text-muted)' }}>({a.role}{a.remote ? ', remote' : ''})</span>
              </span>))}.
            <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
              {' '}{matched ? `${matched} of ${list.length} matched to the board’s posted roster; the rest, in italics, are` : 'Names are'} the caption model&rsquo;s hearing and may be wrong.
            </span>
          </p>
        )
      })()}

      <H2>Votes</H2>
      {votes.length === 0
        ? <p className="text-sm" style={{ color: 'var(--text-muted)' }}>No substantive votes heard. {procedural.length} procedural.</p>
        : <ol className="space-y-2">
            {votes.map((v, i) => (
              <li key={i} className="card p-3 flex flex-wrap gap-x-3 gap-y-1 items-baseline">
                <At url={u} t={v.t} />
                <span className="text-sm flex-1 min-w-[16rem]">{v.motion}{v.moved_by ? <span style={{ color: 'var(--text-muted)' }}> — moved by {v.moved_by}, as heard</span> : null}</span>
                <Lost text={m.recorded_twice?.labels?.votes?.[String(mm.votes.indexOf(v))]} />
                <span className="text-xs font-bold uppercase tracking-widest whitespace-nowrap"
                  style={{ color: v.outcome.startsWith('pass') ? 'var(--series-cost)' : v.outcome === 'not audible' ? 'var(--text-muted)' : 'var(--series-revenue, #b5540f)' }}>{v.outcome}</span>
              </li>
            ))}
          </ol>}
      {procedural.length > 0 && votes.length > 0 && (
        <p className="text-xs mt-2" style={{ color: 'var(--text-muted)' }}>
          And {procedural.length} procedural: {procedural.map((v, i) => <span key={i}>{i ? '; ' : ''}{v.motion.toLowerCase()} (<At url={u} t={v.t} />)</span>)}.
        </p>
      )}

      <MissingHere m={m} />

      {/* AGAINST THE TOWN'S MINUTES. Two records of one meeting; neither is the referee.
          TJ: "if there truly is a difference in what was documented vs what we think,
          that's a flag. but if its just our recording reading being wrong or
          mistranslated, thats what this is intending to fix." Caption errors show the
          official reading beside the as-heard one; discrepancies are flagged with the
          second of video and left for a person. */}
      {m.reconciliation && (() => {
        const rc = m.reconciliation!
        const disc = rc.findings.filter(f => f.kind === 'discrepancy')
        const fixes = rc.findings.filter(f => f.kind === 'caption_error')
        const onlyO = rc.findings.filter(f => f.kind === 'only_in_official')
        const onlyU = rc.findings.filter(f => f.kind === 'only_in_ours')
        return (
          <>
            <H2>Against the town&rsquo;s minutes</H2>
            <p className="text-sm max-w-3xl" style={{ color: 'var(--text-secondary)' }}>
              The town published <a className="underline font-semibold" style={{ color: 'var(--series-cost)' }} href={rc.official.url} target="_blank" rel="noreferrer">minutes</a> (<a className="underline" href={rc.official.text_url}>text</a>) for this meeting; ours were compared item by item.{' '}
              <strong>{rc.counts.agree || 0} agree</strong>, <strong>{fixes.length}</strong> caption error{fixes.length === 1 ? '' : 's'} resolved by the official reading, <strong style={disc.length ? { color: 'var(--series-revenue, #b5540f)' } : undefined}>{disc.length} substantive difference{disc.length === 1 ? '' : 's'}</strong>. The town&rsquo;s minutes are {rc.coverage === 'full' ? 'a full record' : rc.coverage === 'partial' ? 'a partial record' : 'a summary'}.
            </p>
            {disc.length > 0 && (
              <ol className="mt-3 space-y-2">
                {disc.map((f, i) => (
                  <li key={i} className="card p-3" style={{ borderLeft: '4px solid var(--series-revenue, #b5540f)' }}>
                    <div className="flex flex-wrap gap-x-3 items-baseline">
                      <span className="text-[10.5px] font-bold uppercase tracking-widest" style={{ color: 'var(--series-revenue, #b5540f)' }}>differs</span>
                      <span className="text-sm font-semibold">{f.about}</span>
                      {typeof f.t === 'number' && <At url={u} t={f.t} />}
                    </div>
                    <div className="grid sm:grid-cols-2 gap-x-6 gap-y-1 mt-1.5 text-sm">
                      <p><span className="text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>recording </span><span style={{ color: 'var(--text-secondary)' }}>{f.ours.replace(/^\[t=\d+\]\s*/, '') || '—'}</span></p>
                      <p><span className="text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>town&rsquo;s minutes </span><span style={{ color: 'var(--text-secondary)' }}>{f.official ? `“${f.official}”` : '—'}</span></p>
                    </div>
                    <p className="text-xs mt-1.5" style={{ color: 'var(--text-muted)' }}>{f.note}</p>
                  </li>
                ))}
              </ol>
            )}
            {fixes.length > 0 && (
              <details className="mt-3">
                <summary className="text-sm cursor-pointer" style={{ color: 'var(--series-cost)' }}>{fixes.length} caption error{fixes.length === 1 ? '' : 's'} the town&rsquo;s minutes resolve</summary>
                <ul className="mt-2 space-y-1.5 text-sm">
                  {fixes.map((f, i) => (
                    <li key={i} className="flex flex-wrap gap-x-2 items-baseline">
                      <span className="font-medium">{f.about}:</span>
                      <Heard s={f.ours.replace(/^\[t=\d+\]\s*/, '')} />
                      <span style={{ color: 'var(--text-muted)' }}>&rarr;</span>
                      <span className="font-semibold">{f.official_reading || f.official}</span>
                      {typeof f.t === 'number' && <At url={u} t={f.t} />}
                    </li>
                  ))}
                </ul>
              </details>
            )}
            {(onlyO.length > 0 || onlyU.length > 0) && (
              <details className="mt-2">
                <summary className="text-sm cursor-pointer" style={{ color: 'var(--series-cost)' }}>In one record only: {onlyU.length} from the recording, {onlyO.length} from the town&rsquo;s minutes</summary>
                <ul className="mt-2 space-y-1 text-sm" style={{ color: 'var(--text-secondary)' }}>
                  {onlyU.map((f, i) => <li key={'u' + i}>Recording only — <span className="font-medium">{f.about}</span>: {f.ours.replace(/^\[t=\d+\]\s*/, '')} {typeof f.t === 'number' && <At url={u} t={f.t} />}</li>)}
                  {onlyO.map((f, i) => <li key={'o' + i}>Town&rsquo;s minutes only — <span className="font-medium">{f.about}</span>: “{f.official}”</li>)}
                </ul>
              </details>
            )}
            <p className="text-xs mt-2" style={{ color: 'var(--text-muted)' }}>Compared {rc.written.at.slice(0, 10)}. Neither record is treated as the referee: a caption error is the same fact heard badly; a difference is for a person to check at the timestamp.</p>
          </>
        )
      })()}

      {mm.transfers.length > 0 && (
        <>
          <H2>Transfers</H2>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm" style={{ minWidth: 480 }}>
              <thead><tr className="text-[10px] font-bold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>
                <th className="py-1.5 pr-3">at</th><th className="py-1.5 pr-3">what moved</th><th className="py-1.5 pr-3">amount, as heard</th><th className="py-1.5">outcome</th>
              </tr></thead>
              <tbody>
                {mm.transfers.map((t, i) => (
                  <tr key={i} style={{ borderTop: '1px solid var(--grid)' }}>
                    <td className="py-2 pr-3 align-top"><At url={u} t={t.t} /></td>
                    <td className="py-2 pr-3 align-top">{t.description}</td>
                    <td className="py-2 pr-3 align-top">{t.amount_as_heard ? <Heard s={t.amount_as_heard} /> : <span style={{ color: 'var(--text-muted)' }}>not heard</span>}</td>
                    <td className="py-2 align-top text-xs" style={{ color: 'var(--text-secondary)' }}>{t.outcome} <Lost text={m.recorded_twice?.labels?.transfers?.[String(i)]} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      <H2>The money</H2>
      {money.length === 0
        ? <p className="text-sm" style={{ color: 'var(--text-muted)' }}>Nothing touching money was heard beyond the transfers.</p>
        : <ol className="space-y-2">
            {money.map((b, i) => (
              <li key={i} className="card p-3">
                <div className="flex flex-wrap gap-x-3 items-baseline">
                  <At url={u} t={b.t} />
                  <span className="text-sm font-semibold">{b.topic}</span>
                  <Lost text={m.recorded_twice?.labels?.budget_items?.[String(mm.budget_items.indexOf(b))]} />
                </div>
                <p className="text-sm mt-1" style={{ color: 'var(--text-secondary)' }}>{b.what_was_said}</p>
                {b.figures_as_heard && b.figures_as_heard.length > 0 && (
                  <p className="mt-1 flex flex-wrap gap-1.5 items-center text-xs" style={{ color: 'var(--text-muted)' }}>
                    as heard:{b.figures_as_heard.map((f, j) => <Heard key={j} s={f} />)}
                  </p>
                )}
              </li>
            ))}
          </ol>}

      {mm.decisions.length > 0 && (
        <>
          <H2>Settled without a vote</H2>
          <ul className="space-y-1.5">
            {mm.decisions.map((x, i) => (
              <li key={i} className="text-sm flex gap-3 items-baseline"><At url={u} t={x.t} /><span>{x.decision}</span><Lost text={m.recorded_twice?.labels?.decisions?.[String(i)]} /></li>
            ))}
          </ul>
        </>
      )}

      <DocumentsAndExhibits d={m.documents ?? null} published={m.has_official_minutes} u={u} />

      {(mm.public_comment || []).length > 0 && (
        <>
          <H2>Public comment</H2>
          <ol className="space-y-2">
            {(mm.public_comment || []).map((c, i) => (
              <li key={i} className="text-sm flex gap-3 items-baseline">
                <At url={u} t={c.t} />
                <span><span style={{ color: 'var(--text-secondary)' }}>{c.topic}</span>
                  {(c.speaker_as_heard || c.stated_role) && <span className="text-xs" style={{ color: 'var(--text-muted)' }}> — {c.speaker_as_heard ? `${c.speaker_as_heard}, as heard` : 'a speaker'}{c.stated_role ? `, ${c.stated_role}` : ''}</span>}
                </span>
                <Lost text={m.recorded_twice?.labels?.public_comment?.[String(i)]} />
              </li>
            ))}
          </ol>
        </>
      )}

      {/* WHERE THIS MEETING'S TIME WENT. TJ: "show the breakdown of time per meeting on
          the individual meeting minutes page". Same derivation as the board-level view:
          topic spans from the captions, credited to each of a topic's tags. */}
      {m.time_by_tag_s && Object.keys(m.time_by_tag_s).length > 0 && (
        <>
          <H2>Where the time went</H2>
          <p className="text-xs mb-2" style={{ color: 'var(--text-muted)' }}>
            Minutes of recording by subject, from the topic spans below. A topic with two subjects counts toward both.
          </p>
          <ul className="grid gap-x-8 gap-y-1 sm:grid-cols-2 max-w-3xl">
            {Object.entries(m.time_by_tag_s).slice(0, 10).map(([t, sec]) => {
              const max = Object.values(m.time_by_tag_s!)[0] || 1
              const span = m.topics_span_s || m.recording?.duration_s || 1
              return (
                <li key={t} className="text-xs">
                  <div className="flex justify-between gap-2">
                    <a className="underline" href={`/meeting-minutes?tag=${t}`} style={{ color: 'var(--series-cost)' }}>{t.replace(/-/g, ' ')}</a>
                    <span className="tnum" style={{ color: 'var(--text-secondary)' }}>{Math.round(sec / 60)} min · {Math.round(100 * sec / span)}%</span>
                  </div>
                  <div className="h-1.5 rounded mt-0.5" style={{ background: 'var(--surface-3)' }}>
                    <div className="h-1.5 rounded" style={{ width: `${Math.round(100 * sec / max)}%`, background: 'var(--series-cost)' }} />
                  </div>
                </li>
              )
            })}
          </ul>
        </>
      )}

      <H2>The whole meeting, in order</H2>
      <ol className="space-y-1">
        {mm.topics.map((t, i) => (
          <li key={i} className="text-sm flex flex-wrap gap-x-3 gap-y-0.5 items-baseline py-1" style={{ borderTop: '1px solid var(--grid)' }}>
            <At url={u} t={t.t_start} />
            <span className="flex-1 min-w-[14rem]">{t.topic}</span>
            <Lost text={m.recorded_twice?.labels?.topics?.[String(i)]} />
            <span className="text-xs" style={{ color: 'var(--text-muted)' }}>{t.resolution} · {hms(t.t_end - t.t_start)} long{(t.tags || []).length ? ' · ' + t.tags!.map(x => x.replace(/-/g, ' ')).join(', ') : ''}</span>
          </li>
        ))}
      </ol>

      <H2>What the captions could not carry</H2>
      {mm.not_audible.length === 0
        ? <p className="text-sm" style={{ color: 'var(--text-muted)' }}>Nothing was flagged.</p>
        : <ul className="list-disc pl-5 space-y-1 text-sm" style={{ color: 'var(--text-secondary)' }}>
            {mm.not_audible.map((x, i) => <li key={i}>{x}</li>)}
          </ul>}

      {mm.suggested_reports && mm.suggested_reports.length > 0 && (
        <>
          <H2>Reports this meeting suggests</H2>
          <p className="text-xs mb-2" style={{ color: 'var(--text-muted)' }}>
            Our reading of the discussion: questions where numbers were in play and a page laying them out would have helped. Every meeting&rsquo;s suggestions are merged into one register.
          </p>
          <ul className="space-y-1.5">
            {mm.suggested_reports.map((x, i) => (
              <li key={i} className="text-sm flex flex-wrap gap-x-3 items-baseline">
                <At url={u} t={x.t} />
                <span className="font-semibold">{x.title}</span>
                <span style={{ color: 'var(--text-secondary)' }}>{x.question}</span>
                {x.existing && <span className="text-xs" style={{ color: 'var(--text-muted)' }}>already answered: <code>{x.existing}</code></span>}
              </li>
            ))}
          </ul>
        </>
      )}

      <Caveat warning={warning} />
      <p className="text-xs mt-3" style={{ color: 'var(--text-muted)' }}>
        Written {m.written.at.slice(0, 10)} by <code>{m.written.by}</code> ({m.written.model}) from{' '}
        <code>{m.source.transcript}</code> — {m.source.segments.toLocaleString()} caption segments, sha256 <code>{m.source.sha256.slice(0, 12)}…</code>.
        {' '}<a className="underline" href="/meeting-minutes">All recorded meetings</a>.
      </p>
      <MoreReports here={TAB} />
    </ReportShell>
  )
}

import type { Tab } from '../routes'
import { recordedSlugFromPath } from '../routes'
import { ReportShell, useReport, H2, Body, MoreReports } from '../components/report'

const TAB: Tab = 'recorded'
const DATA = '/data/recording-minutes.json'
const FILE = 'recording-minutes.json'

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
type Attendee = { name_as_heard: string; role: string; remote?: boolean }
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
}
type TownDoc = { kind: string; url: string; text_url: string; path: string }
type Meeting = {
  slug: string
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
type BoardTime = { board: string; meetings: number; topics_span_s: number; by_tag_s: Record<string, number> }
type Payload = {
  warning: string
  what: string
  tags: Record<string, number>
  time_by_board: Record<string, BoardTime>
  time_note: string
  counts: { meetings: number; boards: number; without_official_minutes: number }
  boards: Record<string, { board: string; meetings: number; without_official_minutes: number }>
  meetings: Meeting[]
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
  const { d, err } = useReport<Payload>(FILE)
  if (!d) {
    return <ReportShell tab={TAB} title="What was said" err={err} loading={!err} dataUrl={DATA} />
  }
  if (slug) {
    const m = d.meetings.find(x => x.slug === slug)
    if (!m) {
      return (
        <ReportShell tab={TAB} title="No minutes at this address" dataUrl={DATA}
          standfirst="Every recording with minutes is listed on the index.">
          <Body>The address <code>/what-was-said/{slug}</code> names no meeting. The index is{' '}
            <a className="underline" style={{ color: 'var(--series-cost)' }} href="/what-was-said">here</a>.</Body>
        </ReportShell>
      )
    }
    return <MeetingPage m={m} warning={d.warning} />
  }
  return <Index d={d} />
}

function Index({ d }: { d: Payload }) {
  const tag = new URL(window.location.href).searchParams.get('tag') || ''
  const shown = tag ? d.meetings.filter(m => m.tags.includes(tag)) : d.meetings
  const boards = Object.entries(d.boards).sort((a, b) => b[1].meetings - a[1].meetings)
    .filter(([slug]) => shown.some(m => m.board_slug === slug))
  return (
    <ReportShell tab={TAB} title="What was said, meeting by meeting"
      standfirst="Our minutes of the recorded meetings — votes, transfers, budget items and decisions, each linked to the second of the video."
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
        {tag && <a href="/what-was-said" className="px-2 py-0.5 text-xs rounded border font-semibold"
          style={{ borderColor: 'var(--text-primary)', color: 'var(--text-primary)' }}>all meetings ×</a>}
        {Object.entries(d.tags).map(([t, n]) => (
          <a key={t} href={`/what-was-said?tag=${t}`} className="px-2 py-0.5 text-xs rounded border"
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
                          <a className="underline" href={`/what-was-said?tag=${t}`} style={{ color: 'var(--series-cost)' }}>{t.replace(/-/g, ' ')}</a>
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
      {boards.map(([slug, b]) => (
        <section key={slug} className="mt-8">
          <H2>{b.board}</H2>
          <p className="text-xs mb-3" style={{ color: 'var(--text-muted)' }}>
            {b.meetings} meeting{b.meetings === 1 ? '' : 's'}; {b.without_official_minutes} with no official minutes
          </p>
          <ol className="space-y-3">
            {shown.filter(m => m.board_slug === slug).map(m => (
              <li key={m.slug} className="card p-4">
                <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
                  <a className="font-semibold underline" href={`/what-was-said/${m.slug}`}
                    style={{ color: 'var(--series-cost)' }}>{longDate(m.date)}</a>
                  <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
                    {m.recording ? `${m.recording.duration} long · ` : ''}{m.counts.votes} vote{m.counts.votes === 1 ? '' : 's'} · {m.counts.transfers} transfer{m.counts.transfers === 1 ? '' : 's'} · {m.counts.budget_items} budget item{m.counts.budget_items === 1 ? '' : 's'} · {m.counts.public_comment} public comment{m.counts.public_comment === 1 ? '' : 's'}
                    {!m.has_official_minutes && <> · <span style={{ color: 'var(--series-revenue, #b5540f)' }}>no official minutes</span></>}
                  </span>
                </div>
                <p className="text-sm mt-1 font-medium">{m.headline || m.summary}</p>
                <p className="mt-1.5 flex flex-wrap gap-1">
                  {m.tags.map(t => <a key={t} href={`/what-was-said?tag=${t}`} className="px-1.5 py-0.5 text-[10.5px] rounded"
                    style={{ background: 'var(--surface-3)', color: 'var(--text-secondary)' }}>{t.replace(/-/g, ' ')}</a>)}
                </p>
              </li>
            ))}
          </ol>
        </section>
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

function MeetingPage({ m, warning }: { m: Meeting; warning: string }) {
  const mm = m.minutes
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
      dataUrl={DATA}
      meta={<span className="text-xs" style={{ color: 'var(--text-muted)' }}>
        <a className="underline" href={u} target="_blank" rel="noreferrer">the recording</a>
        {m.recording ? <>{' · '}{m.recording.duration} long, about {m.recording.words_approx.toLocaleString()} words spoken</> : null}
        {' · '}captions carried this meeting {mm.confidence === 'high' ? 'well' : mm.confidence === 'moderate' ? 'moderately well' : 'poorly'}
      </span>}>

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

      <Body>{mm.summary}</Body>
      {m.tags.length > 0 && (
        <p className="mt-2 flex flex-wrap gap-1">
          {m.tags.map(t => <a key={t} href={`/what-was-said?tag=${t}`} className="px-1.5 py-0.5 text-[11px] rounded"
            style={{ background: 'var(--surface-3)', color: 'var(--text-secondary)' }}>{t.replace(/-/g, ' ')}</a>)}
        </p>
      )}

      {(mm.attendees || []).length > 0 && (
        <p className="mt-4 text-sm" style={{ color: 'var(--text-secondary)' }}>
          <span className="font-semibold" style={{ color: 'var(--text-primary)' }}>Present, as heard: </span>
          {(mm.attendees || []).map((a, i) => <span key={i}>{i ? '; ' : ''}{a.name_as_heard} <span style={{ color: 'var(--text-muted)' }}>({a.role}{a.remote ? ', remote' : ''})</span></span>)}.
          <span className="text-xs" style={{ color: 'var(--text-muted)' }}> Names are the caption model's hearing and may be wrong.</span>
        </p>
      )}

      <H2>Votes</H2>
      {votes.length === 0
        ? <p className="text-sm" style={{ color: 'var(--text-muted)' }}>No substantive votes heard. {procedural.length} procedural.</p>
        : <ol className="space-y-2">
            {votes.map((v, i) => (
              <li key={i} className="card p-3 flex flex-wrap gap-x-3 gap-y-1 items-baseline">
                <At url={u} t={v.t} />
                <span className="text-sm flex-1 min-w-[16rem]">{v.motion}{v.moved_by ? <span style={{ color: 'var(--text-muted)' }}> — moved by {v.moved_by}, as heard</span> : null}</span>
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
                    <td className="py-2 align-top text-xs" style={{ color: 'var(--text-secondary)' }}>{t.outcome}</td>
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
              <li key={i} className="text-sm flex gap-3 items-baseline"><At url={u} t={x.t} /><span>{x.decision}</span></li>
            ))}
          </ul>
        </>
      )}

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
                    <a className="underline" href={`/what-was-said?tag=${t}`} style={{ color: 'var(--series-cost)' }}>{t.replace(/-/g, ' ')}</a>
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
            <span className="text-xs whitespace-nowrap" style={{ color: 'var(--text-muted)' }}>{t.resolution} · {hms(t.t_end - t.t_start)} long{(t.tags || []).length ? ' · ' + t.tags!.map(x => x.replace(/-/g, ' ')).join(', ') : ''}</span>
          </li>
        ))}
      </ol>

      <H2>What the captions could not carry</H2>
      {mm.not_audible.length === 0
        ? <p className="text-sm" style={{ color: 'var(--text-muted)' }}>Nothing was flagged.</p>
        : <ul className="list-disc pl-5 space-y-1 text-sm" style={{ color: 'var(--text-secondary)' }}>
            {mm.not_audible.map((x, i) => <li key={i}>{x}</li>)}
          </ul>}

      <Caveat warning={warning} />
      <p className="text-xs mt-3" style={{ color: 'var(--text-muted)' }}>
        Written {m.written.at.slice(0, 10)} by <code>{m.written.by}</code> ({m.written.model}) from{' '}
        <code>{m.source.transcript}</code> — {m.source.segments.toLocaleString()} caption segments, sha256 <code>{m.source.sha256.slice(0, 12)}…</code>.
        {' '}<a className="underline" href="/what-was-said">All recorded meetings</a>.
      </p>
      <MoreReports here={TAB} />
    </ReportShell>
  )
}

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
type Topic = { t_start: number; t_end: number; topic: string; resolution: string }
type Minutes = {
  summary: string
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
  summary: string
  confidence: string
  counts: Record<string, number>
  town_published: TownDoc[]
  has_official_minutes: boolean
  source: { transcript: string; sha256: string; caption_lines: number; segments: number }
  written: { by: string; model: string; at: string; cost_usd: number | null }
  minutes: Minutes
}
type Payload = {
  warning: string
  what: string
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
  const boards = Object.entries(d.boards).sort((a, b) => b[1].meetings - a[1].meetings)
  return (
    <ReportShell tab={TAB} title="What was said, meeting by meeting"
      standfirst="Our minutes of the recorded meetings — votes, transfers, budget items and decisions, each linked to the second of the video."
      dataUrl={DATA}>
      <p className="mt-6 text-sm" style={{ color: 'var(--text-secondary)' }}>
        <strong>{d.counts.meetings}</strong> meetings across <strong>{d.counts.boards}</strong> boards,{' '}
        <strong>{d.counts.without_official_minutes}</strong> of them with no minutes published by the town.
      </p>
      <Caveat warning={d.warning} />
      {boards.map(([slug, b]) => (
        <section key={slug} className="mt-8">
          <H2>{b.board}</H2>
          <p className="text-xs mb-3" style={{ color: 'var(--text-muted)' }}>
            {b.meetings} meeting{b.meetings === 1 ? '' : 's'}; {b.without_official_minutes} with no official minutes
          </p>
          <ol className="space-y-3">
            {d.meetings.filter(m => m.board_slug === slug).map(m => (
              <li key={m.slug} className="card p-4">
                <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
                  <a className="font-semibold underline" href={`/what-was-said/${m.slug}`}
                    style={{ color: 'var(--series-cost)' }}>{longDate(m.date)}</a>
                  <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
                    {m.counts.votes} vote{m.counts.votes === 1 ? '' : 's'} · {m.counts.transfers} transfer{m.counts.transfers === 1 ? '' : 's'} · {m.counts.budget_items} budget item{m.counts.budget_items === 1 ? '' : 's'}
                    {!m.has_official_minutes && <> · <span style={{ color: 'var(--series-revenue, #b5540f)' }}>no official minutes</span></>}
                  </span>
                </div>
                <p className="text-sm mt-1" style={{ color: 'var(--text-secondary)' }}>{m.summary}</p>
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

      <H2>The whole meeting, in order</H2>
      <ol className="space-y-1">
        {mm.topics.map((t, i) => (
          <li key={i} className="text-sm flex flex-wrap gap-x-3 gap-y-0.5 items-baseline py-1" style={{ borderTop: '1px solid var(--grid)' }}>
            <At url={u} t={t.t_start} />
            <span className="flex-1 min-w-[14rem]">{t.topic}</span>
            <span className="text-xs whitespace-nowrap" style={{ color: 'var(--text-muted)' }}>{t.resolution} · {hms(t.t_end - t.t_start)} long</span>
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

import { useState } from 'react'
import type { Tab } from '../routes'
import { boardRecordsSlugFromPath } from '../routes'
import { Body, Grain, H2, ReportShell, Stat, useReport } from '../components/report'
import { RecordCell, judged, type RecordStatus } from '../components/RecordCell'

const TAB: Tab = 'boards'
const DATA = '/data/board-records.json'

/** A BOARD'S MISSING RECORDS. TJ, 7 October 2026: "every board should have a link that
 *  shows its missing data. and list every meeting, and the table of which data is
 *  missing (youtube, official minutes, etc)." Approved first for the Parks Commission as
 *  an email (`notes/outbound/drafts/PARKS-COMMISSION-MISSING-RECORDINGS.md`) and here
 *  generalised to every board.
 *
 *  ONE DEFINITION, SHARED. Every status below comes from `scripts/meeting_records.py`
 *  by way of `build_board_records.py` -- the same module the backlog-depth chart and the
 *  Recent-meetings table on each board's own page read. 'n/a' is never a stand-in for
 *  'missing': it means the record was never going to exist (the board does not record,
 *  or this date is before its first recording), and it carries a short reason instead of
 *  the bold red MISSING.
 *
 *  AND MISSING WAITS FOR THE WINDOW. An absent record is "not available" until the Open
 *  Meeting Law's window for approving minutes closes (`due`, see `RecordCell`), and is
 *  judged on the reader's clock -- so the counts are taken HERE, from the rows, not from
 *  the payload's build-day totals. */
type Rec = {
  date: string
  due: string | null
  agenda: { posted: boolean; url: string | null }
  video: { status: RecordStatus; url: string | null; reason: string | null }
  minutes: { status: RecordStatus; url: string | null; reason: string | null }
  transcript: { status: RecordStatus; captions_disabled: boolean; reason: string | null }
}
type BoardRec = { board_slug: string; board: string; meetings: number; records: Rec[] }
type Payload = {
  grain: string
  as_of: { agendas_and_minutes: string | null; youtube: string | null }
  boards: BoardRec[]
  not_established: string[]
}

const mmdd = (d: string) => new Date(d + 'T12:00:00').toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' })

const PARTS = ['video', 'minutes', 'transcript'] as const
const isMissing = (r: Rec) => PARTS.some(k => judged(r[k].status, r.due) === 'missing')
const isWaiting = (r: Rec) => !isMissing(r) && PARTS.some(k => judged(r[k].status, r.due) === 'not-available')

export function BoardRecords() {
  const slug = boardRecordsSlugFromPath(window.location.pathname) ?? ''
  const { d, err } = useReport<Payload>('board-records.json')
  const b = d?.boards.find(x => x.board_slug === slug)
  const [showAll, setShowAll] = useState(false)
  if (!d) return <ReportShell tab={TAB} title="Missing records" err={err} loading={!err} dataUrl={DATA} />
  if (!b) {
    return (
      <ReportShell tab={TAB} title="No such board" dataUrl={DATA}>
        <Body>The address <code>/boards/{slug}/records</code> names no board with a meeting in the register. <a className="underline" href="/boards">All boards</a>.</Body>
      </ReportShell>
    )
  }
  const byYear = new Map<string, Rec[]>()
  for (const r of b.records) {
    const y = r.date.slice(0, 4)
    if (!byYear.has(y)) byYear.set(y, [])
    byYear.get(y)!.push(r)
  }
  const years = [...byYear.keys()].sort().reverse().map(year => {
    const rs = byYear.get(year)!
    return { year, meetings: rs.length, missing: rs.filter(isMissing).length, waiting: rs.filter(isWaiting).length }
  })
  const missing = b.records.filter(isMissing).length
  const waiting = b.records.filter(isWaiting).length
  return (
    <ReportShell tab={TAB} title={`${b.board} — missing records`}
      standfirst={<>{missing} of {b.meetings} meetings this board has held are missing a recording, its official minutes, or a transcript{waiting ? `; ${waiting} more are not available yet, still inside the window for approving minutes` : ''}. <a className="underline" href={`/boards/${slug}`}>&larr; the {b.board}&rsquo;s page</a>.</>}
      dataUrl={DATA}>
      <Grain>{d.grain}</Grain>
      <div className="mt-6 flex flex-wrap gap-x-12 gap-y-6">
        <Stat value={`${missing} of ${b.meetings}`} tone={missing ? 'var(--status-critical)' : 'var(--status-good)'}>
          meetings held are missing something
        </Stat>
        {waiting > 0 && <Stat value={`${waiting} of ${b.meetings}`}>meetings not available yet, still inside the window for approving minutes</Stat>}
      </div>
      <p className="text-[13px] mt-5">
        <button className="underline font-semibold" style={{ color: 'var(--series-cost)' }}
          onClick={() => setShowAll(!showAll)}>{showAll ? 'show gaps only' : 'show every meeting'}</button>
      </p>
      {years.map(yc => {
        const rows = (byYear.get(yc.year) ?? []).filter(r => showAll || isMissing(r) || isWaiting(r))
        if (!showAll && yc.missing + yc.waiting === 0) return null
        return (
          <div key={yc.year}>
            <H2 id={`y${yc.year}`}>{yc.year}: {yc.missing} of {yc.meetings} meetings missing something{yc.waiting ? `, ${yc.waiting} not available yet` : ''}</H2>
            {rows.length === 0 ? (
              <p className="text-sm mt-2" style={{ color: 'var(--text-secondary)' }}>Nothing missing.</p>
            ) : (
              <div className="overflow-x-auto mt-3">
                <table className="text-sm w-full" style={{ minWidth: 640 }}>
                  <thead><tr className="text-[10px] font-bold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>
                    <th className="text-left py-1.5 pr-3">meeting</th><th className="text-left py-1.5 pr-3">YouTube recording</th>
                    <th className="text-left py-1.5 pr-3">official minutes</th><th className="text-left py-1.5">transcript</th></tr></thead>
                  <tbody>{rows.map(r => (
                    <tr key={r.date} style={{ borderTop: '1px solid var(--grid)' }}>
                      <td className="py-1.5 pr-3 align-top whitespace-nowrap">{r.agenda.url ? <a className="underline" href={r.agenda.url}>{mmdd(r.date)}</a> : mmdd(r.date)}</td>
                      <td className="py-1.5 pr-3 align-top"><RecordCell {...r.video} due={r.due} label="posted" /></td>
                      <td className="py-1.5 pr-3 align-top"><RecordCell {...r.minutes} due={r.due} label="posted" /></td>
                      <td className="py-1.5 align-top"><RecordCell {...r.transcript} due={r.due} label="posted" /></td>
                    </tr>))}</tbody>
                </table>
              </div>
            )}
          </div>
        )
      })}
      {years.every(yc => yc.missing + yc.waiting === 0) && !showAll && (
        <p className="text-sm mt-4" style={{ color: 'var(--text-secondary)' }}>Nothing missing in any year on record.</p>
      )}
      <H2>What this does not show</H2>
      <ul className="mt-2 space-y-1.5 text-sm max-w-2xl" style={{ color: 'var(--text-secondary)' }}>
        {d.not_established.map((n, i) => <li key={i}>{n}</li>)}
      </ul>
      <p className="text-xs mt-6" style={{ color: 'var(--text-muted)' }}>
        Checked against the town&rsquo;s AgendaCenter (agendas and minutes, {d.as_of.agendas_and_minutes ?? 'unknown'}) and every
        upload on the Lunenburg Access YouTube channel (as of {d.as_of.youtube ?? 'unknown'}).
      </p>
    </ReportShell>
  )
}

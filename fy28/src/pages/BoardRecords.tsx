import { useState } from 'react'
import type { Tab } from '../routes'
import { boardRecordsSlugFromPath } from '../routes'
import { Body, Grain, H2, ReportShell, Stat, useReport } from '../components/report'

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
 *  the bold red MISSING. */
type Status = 'posted' | 'missing' | 'n/a'
type Rec = {
  date: string
  agenda: { posted: boolean; url: string | null }
  video: { status: Status; url: string | null; reason: string | null }
  minutes: { status: 'posted' | 'missing'; url: string | null }
  transcript: { status: Status; captions_disabled: boolean; reason: string | null }
  missing: boolean
}
type YearCount = { year: string; meetings: number; missing: number }
type BoardRec = { board_slug: string; board: string; meetings: number; missing: number; years: YearCount[]; records: Rec[] }
type Payload = {
  grain: string
  as_of: { agendas_and_minutes: string | null; youtube: string | null }
  boards: BoardRec[]
  not_established: string[]
}

const mmdd = (d: string) => new Date(d + 'T12:00:00').toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' })

function Cell({ s, label }: { s: { status: Status; url?: string | null; reason?: string | null }; label: string }) {
  if (s.status === 'posted') return s.url ? <a className="underline" href={s.url}>{label}</a> : <span>{label}</span>
  if (s.status === 'missing') return <strong style={{ color: 'var(--status-critical)' }}>MISSING</strong>
  return <span title={s.reason || undefined} style={{ color: 'var(--text-muted)' }}>n/a</span>
}

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
  return (
    <ReportShell tab={TAB} title={`${b.board} — missing records`}
      standfirst={<>{b.missing} of {b.meetings} meetings this board has held are missing a recording, its official minutes, or a transcript. <a className="underline" href={`/boards/${slug}`}>&larr; the {b.board}&rsquo;s page</a>.</>}
      dataUrl={DATA}>
      <Grain>{d.grain}</Grain>
      <div className="mt-6 flex flex-wrap gap-x-12 gap-y-6">
        <Stat value={`${b.missing} of ${b.meetings}`} tone={b.missing ? 'var(--status-critical)' : 'var(--status-good)'}>
          meetings held are missing something
        </Stat>
      </div>
      <p className="text-[13px] mt-5">
        <button className="underline font-semibold" style={{ color: 'var(--series-cost)' }}
          onClick={() => setShowAll(!showAll)}>{showAll ? 'show gaps only' : 'show every meeting'}</button>
      </p>
      {b.years.map(yc => {
        const rows = (byYear.get(yc.year) ?? []).filter(r => showAll || r.missing)
        if (!showAll && yc.missing === 0) return null
        return (
          <div key={yc.year}>
            <H2 id={`y${yc.year}`}>{yc.year}: {yc.missing} of {yc.meetings} meetings missing something</H2>
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
                      <td className="py-1.5 pr-3 align-top"><Cell s={r.video} label="posted" /></td>
                      <td className="py-1.5 pr-3 align-top"><Cell s={r.minutes} label="posted" /></td>
                      <td className="py-1.5 align-top"><Cell s={r.transcript} label="posted" /></td>
                    </tr>))}</tbody>
                </table>
              </div>
            )}
          </div>
        )
      })}
      {b.years.every(yc => yc.missing === 0) && !showAll && (
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

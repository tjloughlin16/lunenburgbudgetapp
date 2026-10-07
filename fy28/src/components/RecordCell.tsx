import { todayIso } from '../lib/meetings'

/** WHAT A MEETING'S RECORD SHOWS, judged on the reader's clock. One cell, used by the
 *  Recent-meetings table on every board page and by every board's missing-records page,
 *  so the two cannot disagree about a word.
 *
 *  NOT AVAILABLE, THEN MISSING. TJ, 7 October 2026: *"Only use the word MISSING when
 *  anything goes beyond that timeline. Before that, call it 'not available'."* The
 *  timeline is the Open Meeting Law's window for approving minutes -- the later of 30
 *  days and the board's next three meetings (940 CMR 29.11) -- and the payload carries
 *  its close as `due` (`scripts/meeting_records.py`, `due_dates`). The payload's own
 *  verdict was reached on the day it was built; this one is reached today, so a meeting
 *  turns MISSING the day its window closes, without a deploy.
 *
 *  NOT PROVIDED is a record somebody has EXPLAINED will never exist -- "we met at the Town
 *  Beach" (`sources/data/meeting-record-explanations.csv`). It is not a gap, and the
 *  explanation is printed in the cell rather than hidden in a tooltip, because it is the
 *  answer a reader would otherwise have to ask for. */
export type RecordStatus = 'posted' | 'not-provided' | 'not-available' | 'missing' | 'n/a'

export function judged(status: RecordStatus, due: string | null | undefined, today = todayIso()): RecordStatus {
  if (status !== 'missing' && status !== 'not-available') return status
  return due && today > due ? 'missing' : 'not-available'
}

/** A link when posted; bold MISSING in `--status-critical` once the window has closed;
 *  muted "not available" inside it, with the date it closes; muted "n/a" with a short
 *  reason when the record was never going to exist. Never a bare dash -- a dash does not
 *  say which of those it is. */
export function RecordCell({ status, due, url, label, reason }: {
  status: RecordStatus; due?: string | null; url?: string | null; label: string; reason?: string | null
}) {
  const s = judged(status, due)
  if (s === 'posted') return url ? <a className="underline" href={url}>{label}</a> : <span>{label}</span>
  if (s === 'missing') return <strong style={{ color: 'var(--status-critical)' }}>MISSING</strong>
  if (s === 'not-provided') {
    return <span style={{ color: 'var(--text-secondary)' }}>not provided <span className="text-xs" style={{ color: 'var(--text-muted)' }}>&mdash; {reason}</span></span>
  }
  if (s === 'not-available') {
    const why = due ? `Inside the window for approving minutes; MISSING after ${due}` : 'Inside the window for approving minutes: the board has not yet held three more meetings'
    return <span title={why} style={{ color: 'var(--text-muted)' }}>not available</span>
  }
  return <span title={reason || undefined} style={{ color: 'var(--text-muted)' }}>n/a</span>
}

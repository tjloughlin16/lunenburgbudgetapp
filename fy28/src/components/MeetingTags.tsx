import { useReport } from './report'
import { judged, type RecordStatus } from './RecordCell'
import { todayIso } from '../lib/meetings'

/** MEETING TAGS: short, safe flags on a meeting. TJ, 13 November 2026: "TAGS on the meetings
 *  ... not to suggest legal violations. just sort of 'helpful' flags."
 *
 *  Every tag states something MEASURED about the online record, a script decides it, and it
 *  reads the same whether or not anything was wrong -- so the chips are neutral in colour, never
 *  the red of MISSING. The detail (the hover title) says what was measured, and every timing
 *  tag says it is about the ONLINE copy: the official notice may be the paper at Town Hall.
 *
 *  Two kinds, judged in two places:
 *    from the agenda (scripts/meeting_tags.py, in boards.json `tags`): amended agenda, late
 *      addition, short notice, emergency meeting, executive session, cancelled;
 *    after the meeting (here, on the reader's clock, from `record` -- RecordCell's `judged`):
 *      minutes not posted, no recording. TJ: "those are post-meeting labels. silly to show
 *      before hand." So they never appear for a meeting dated today or later, and minutes
 *      only once the approval window has closed. */

export type Tag = { key: string; label: string; detail: string }
type Rec = { due?: string | null; video?: { status: RecordStatus; likely_none?: boolean }; minutes?: { status: RecordStatus } }
type Row = { date: string; tags?: Tag[] | null; record?: Rec | null }
type Boards = { boards: { slug: string; meetings: Row[] }[] }

function daysSince(iso: string, today = todayIso()): number {
  const [y, m, d] = iso.split('-').map(Number), [ty, tm, td] = today.split('-').map(Number)
  return Math.round((Date.UTC(ty, tm - 1, td) - Date.UTC(y, m - 1, d)) / 86400000)
}

export function allTags(r: Row, today = todayIso()): Tag[] {
  const out = [...(r.tags ?? [])]
  if (r.date < today && r.record) {
    if (r.record.minutes && judged(r.record.minutes.status, r.record.due, today) === 'missing') {
      const n = daysSince(r.date, today)
      out.push({ key: 'minutes-not-posted', label: `Minutes not posted · ${n} days`,
        detail: 'no minutes for this meeting on the town website, and the window for approving them has closed; the law requires minutes to exist and be available on request, not to be online' })
    }
    if (r.record.video && !r.record.video.likely_none && judged(r.record.video.status, r.record.due, today) === 'missing') {
      out.push({ key: 'no-recording', label: 'No recording', detail: 'no recording of this meeting has been posted' })
    }
  }
  return out
}

export function MeetingTags({ row, className = '' }: { row: Row; className?: string }) {
  const tags = allTags(row)
  if (!tags.length) return null
  return (
    <span className={`inline-flex flex-wrap gap-1 ${className}`}>
      {tags.map(t => (
        <span key={t.key} title={t.detail}
          className="px-1.5 py-0.5 rounded text-[10.5px] font-semibold uppercase tracking-wider whitespace-nowrap"
          style={{ border: '1px solid var(--grid)', color: 'var(--text-secondary)' }}>
          {t.label}
        </span>
      ))}
    </span>
  )
}

/** Tags for a meeting listed by a feed that does not carry them (the upcoming feeds), looked
 *  up in boards.json by board and date. */
export function useMeetingRows(): (slug: string, date: string) => Row | undefined {
  const { d } = useReport<Boards>('boards.json')
  const idx = new Map<string, Row>()
  for (const b of d?.boards ?? []) for (const m of b.meetings) idx.set(b.slug + '|' + m.date, m)
  return (slug, date) => idx.get(slug + '|' + date)
}

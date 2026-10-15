import { useReport } from './report'

/** WHICH THREADS ARE ON AN AGENDA — one payload, read wherever an agenda is shown.
 *
 *  TJ, 15 October 2026: *"for upcoming minutes and agendas, i want to try to take whats in
 *  the agenda, match them to threads, show the threads"*. The matching is
 *  scripts/build_agenda_threads.py, with each thread's OWN patterns -- the same rule that
 *  puts a minute on a thread -- so nothing here decides anything; it renders the payload.
 *
 *  AN AGENDA IS NOT A DECISION (rule 7). A link here says the thread's words are on the
 *  agenda. It never says what the board will do, and the label says "on the agenda". */

export type AgendaItem = {
  n: number; line: string; parent: string; procedural: boolean
  threads: { id: string; label: string; by: 'words' | 'board' }[]
}
export type AgendaMeeting = {
  board: string; board_slug: string; date: string; file_id: string; body_as_printed: string
  upcoming: boolean; agenda_url: string; agenda_doc: string; items: AgendaItem[]; threads: string[]
}
export type AgendaThreads = {
  as_of: string; counts: Record<string, number>; meetings: AgendaMeeting[]
}

export function useAgendaThreads() {
  return useReport<AgendaThreads>('agenda-threads.json')
}

export function meetingFor(d: AgendaThreads | null, board_slug: string, date: string, file_id?: string) {
  if (!d) return null
  return d.meetings.find(m => m.board_slug === board_slug && m.date === date && (!file_id || m.file_id === file_id))
    ?? d.meetings.find(m => m.board_slug === board_slug && m.date === date) ?? null
}

/** The matched items of one meeting, as `agenda line → thread`. Nothing renders where no
 *  item matched -- a meeting with no thread on it is the common case and needs no box. */
export function AgendaThreadLinks({ m, compact = false }: { m: AgendaMeeting | null; compact?: boolean }) {
  if (!m) return null
  const hits = m.items.filter(it => it.threads.length > 0)
  if (!hits.length) return null
  // One line per thread: the thread, then the agenda lines that put it there.
  const byThread = new Map<string, { label: string; lines: string[] }>()
  for (const it of hits) for (const t of it.threads) {
    const row = byThread.get(t.id) ?? { label: t.label, lines: [] }
    row.lines.push(it.line)
    byThread.set(t.id, row)
  }
  return (
    <div className={compact ? 'mt-1.5' : 'mt-2'}>
      <p className="text-[10.5px] font-bold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>
        Threads on this agenda
      </p>
      <ul className="mt-1 space-y-1">
        {[...byThread.entries()].map(([id, r]) => (
          <li key={id} className="text-[13px] leading-snug">
            <a href={`/threads/${id}`} className="font-semibold underline" style={{ color: 'var(--series-cost)' }}
              onClick={e => e.stopPropagation()}>{r.label} &rarr;</a>
            {!compact && (
              <span className="text-[12px]" style={{ color: 'var(--text-muted)' }}>
                {' '}— on the agenda as &ldquo;{r.lines[0].length > 110 ? r.lines[0].slice(0, 108) + '…' : r.lines[0]}&rdquo;
                {r.lines.length > 1 ? ` and ${r.lines.length - 1} more item${r.lines.length === 2 ? '' : 's'}` : ''}
              </span>
            )}
          </li>
        ))}
      </ul>
    </div>
  )
}

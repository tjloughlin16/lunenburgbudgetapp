import { useEffect, useMemo, useState } from 'react'
import { Body, H3 } from './report'

/** A THREAD BUILT FROM A SEARCH, at /threads/<slug>?q=<words>.
 *
 *  TJ, 10 October 2026: *"be able to create a DYNAMIC thread via search. So if a user searches
 *  for a term, there should be a button that says 'create thread' and it brings them to a
 *  /threads/SEARCHTERM, and it dynamically builds a thread based on the available
 *  chronological information."*
 *
 *  WHAT IT IS, AND WHAT IT IS NOT. A curated thread (notes/process/THREADS-MODEL.md) is a
 *  MATTER someone decided to follow: a question, the boards that touch it, what would close
 *  it, and a standing line read from the record. This is none of that. It is every DATED
 *  mention of some words, in date order -- the minutes and agendas the town published, our
 *  notes from the recordings, and the machine captions -- grouped by meeting. It cannot say
 *  how the matter stands, and it says so above the first entry rather than below the last.
 *
 *  THE WORDS ARE MATCHED, NOT THE TOPIC. A meeting that discussed the thing in other words is
 *  missing; a meeting that used the words about something else is present. Rule 7: a list of
 *  mentions is not a history of a decision.
 *
 *  ONE CALL. /api/search with `sort=newest` and `per=` the most it allows, over the dated
 *  kinds only, laid out oldest first. A kind that hit its cap says so -- the oldest mentions
 *  are the ones a cap drops, and a timeline that silently starts late reads as a matter that
 *  started late. */

type Hit = {
  corpus: 'minutes' | 'recorded' | 'transcript' | 'job'
  title: string; board: string | null; board_slug: string | null; date: string; kind: string
  cite_url: string; start_s: number | null; snippet: string
}
type Count = { hits: number; capped: boolean; holds: number }
type Payload = { results: Record<string, Hit[]>; counts: Record<string, Count>; perCorpus: number; error?: string; message?: string }

const KINDS: Hit['corpus'][] = ['minutes', 'recorded', 'transcript', 'job']
const PER = 60
const LABEL: Record<Hit['corpus'], string> = {
  minutes: 'Town record', recorded: 'Our notes from the video', transcript: 'Machine captions', job: 'Job posting',
}
const TONE: Record<Hit['corpus'], string> = {
  minutes: 'var(--text-secondary)', recorded: 'var(--series-revenue, #b5540f)',
  transcript: 'var(--series-revenue, #b5540f)', job: 'var(--status-good)',
}
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
const day = (iso: string) => { const [y, m, d] = iso.split('-').map(Number); return `${d} ${MONTHS[m - 1]} ${y}` }

export const threadSlug = (q: string) =>
  q.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 80)

function Snip({ s }: { s: string }) {
  return <>{s.split(/(‹[^›]*›)/g).map((p, i) => p.startsWith('‹')
    ? <mark key={i} style={{ background: 'var(--surface-3)', color: 'inherit', fontWeight: 600 }}>{p.slice(1, -1)}</mark>
    : <span key={i}>{p}</span>)}</>
}

export function DynamicThread({ term }: { term: string }) {
  const [p, setP] = useState<Payload | null>(null)
  const [err, setErr] = useState('')
  useEffect(() => {
    let live = true
    setP(null); setErr('')
    fetch(`/api/search?q=${encodeURIComponent(term)}&corpus=${KINDS.join(',')}&sort=newest&per=${PER}&match=together`)
      .then(r => r.json()).then((j: Payload) => {
        if (!live) return
        if (j.error) setErr(j.message || j.error); else setP(j)
      }).catch(e => live && setErr(String(e)))
    return () => { live = false }
  }, [term])

  // ONE STOP PER MEETING: a board on a date, holding whatever of the three records mention it.
  const stops = useMemo(() => {
    if (!p) return []
    const m = new Map<string, { date: string; board: string; hits: Hit[] }>()
    for (const k of KINDS) for (const h of p.results[k] ?? []) {
      if (!/^\d{4}-\d{2}-\d{2}$/.test(h.date)) continue
      const key = `${h.date}|${h.board_slug || h.board || ''}`
      if (!m.has(key)) m.set(key, { date: h.date, board: h.board || h.board_slug || '', hits: [] })
      m.get(key)!.hits.push(h)
    }
    return [...m.values()].sort((a, b) => a.date.localeCompare(b.date) || a.board.localeCompare(b.board))
  }, [p])
  const capped = p ? KINDS.filter(k => p.counts[k]?.capped || (p.counts[k]?.hits ?? 0) > (p.results[k]?.length ?? 0)) : []
  const boards = new Set(stops.map(s => s.board))

  return (
    <>
      <div className="card p-4 mt-6 max-w-3xl" style={{ borderLeft: '4px solid var(--status-warning)' }}>
        <p className="text-[11px] font-bold uppercase tracking-widest" style={{ color: 'var(--status-warning)' }}>
          Built automatically from a search
        </p>
        <p className="text-[13.5px] mt-1" style={{ color: 'var(--text-secondary)' }}>
          Every dated mention of <strong>{term}</strong> &mdash; the words together, within a few words of each other &mdash; in the town&rsquo;s minutes and agendas, our notes from the
          recordings and the machine captions, oldest first. It matches the <em>words</em>, not the subject: a meeting
          that discussed this in other words is missing, and one that used the words about something else is here.
          It does not say how anything stands. <a className="underline" href={`/search?q=${encodeURIComponent(term)}`}>Search it</a> for
          the documents too, which carry no date.
        </p>
      </div>

      {err && <Body>The search behind this thread could not run: {err}</Body>}
      {!p && !err && (
        <p role="status" className="mt-6 text-[14px] flex items-center gap-3">
          <span aria-hidden="true" className="search-spinner inline-block rounded-full"
            style={{ width: 20, height: 20, border: '3px solid var(--grid)', borderTopColor: 'var(--series-cost)' }} />
          Building the thread from every dated record&hellip;
        </p>
      )}

      {p && (
        <>
          <p className="text-[14px] mt-5 max-w-3xl" style={{ color: 'var(--text-secondary)' }}>
            {stops.length === 0
              ? <>Nothing dated mentions <strong>{term}</strong>.</>
              : <><strong>{stops.length} meeting{stops.length === 1 ? '' : 's'}</strong> across {boards.size} board{boards.size === 1 ? '' : 's'}, from {day(stops[0].date)} to {day(stops[stops.length - 1].date)}.</>}
            {capped.length > 0 && <> The newest {PER} of each kind are shown, so the earliest mentions may be missing ({capped.map(k => LABEL[k].toLowerCase()).join(', ')}).</>}
          </p>
          <ol className="mt-4 max-w-3xl">
            {stops.map((s, i) => (
              <li key={i} className="relative pl-5 pb-4" style={{ borderLeft: '2px solid var(--grid)' }}>
                <span aria-hidden="true" className="absolute -left-[6px] top-1.5 w-[10px] h-[10px] rounded-full"
                  style={{ background: 'var(--series-cost)' }} />
                {/* THE MEETING HEADING OPENS THE MEETING -- our page for it where we wrote one,
                    else the town's own record. TJ: "every mention needs to be clickable to see
                    the raw info.. i cant click a school committee meeting". */}
                <H3>
                  {(() => {
                    const m = s.hits.find(h => h.corpus === 'recorded') ?? s.hits.find(h => h.corpus === 'minutes') ?? s.hits.find(h => h.corpus === 'transcript')
                    return m
                      ? <a href={m.cite_url} className="underline decoration-1 underline-offset-2"
                          target={m.corpus !== 'recorded' ? '_blank' : undefined} rel="noreferrer">{day(s.date)}</a>
                      : day(s.date)
                  })()}{' '}
                  <span className="font-normal" style={{ color: 'var(--text-muted)' }}>· {s.board}</span>
                </H3>
                <ul className="mt-1 space-y-1.5">
                  {s.hits.map((h, j) => {
                    const external = h.corpus === 'minutes' || h.corpus === 'transcript'
                    const open = h.corpus === 'transcript' ? 'watch at this moment'
                      : h.corpus === 'recorded' ? 'our notes on this meeting'
                      : h.corpus === 'job' ? 'the posting' : `the ${h.kind || 'document'}`
                    return (
                      <li key={j}>
                        {/* THE WHOLE MENTION IS THE LINK, to the record it was read from. */}
                        <a href={h.cite_url} target={external ? '_blank' : undefined} rel="noreferrer"
                          className="block rounded px-2 py-1 -mx-2 text-[13.5px] leading-relaxed no-underline hover:bg-[var(--surface-3)]">
                          <span className="text-[10.5px] font-bold uppercase tracking-wider mr-2"
                            style={{ color: TONE[h.corpus] }}>{h.corpus === 'minutes' && h.kind ? h.kind : LABEL[h.corpus]}</span>
                          <span style={{ color: 'var(--text-secondary)' }}><Snip s={h.snippet} /></span>
                          <span className="text-[12px] ml-1.5 underline whitespace-nowrap" style={{ color: 'var(--series-cost)' }}>
                            {open}{external ? ' \u2197' : ' \u2192'}
                          </span>
                        </a>
                      </li>
                    )
                  })}
                </ul>
              </li>
            ))}
          </ol>
          <p className="text-xs mt-2 max-w-3xl" style={{ color: 'var(--text-muted)' }}>
            Town record = minutes or an agenda the town published. Our notes and machine captions come from the
            meeting videos: they locate a moment and do not settle what was said.
          </p>
        </>
      )}
    </>
  )
}

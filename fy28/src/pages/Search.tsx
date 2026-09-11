import { useEffect, useMemo, useRef, useState } from 'react'
import type { Tab } from '../routes'
import { ReportShell, Body } from '../components/report'

const TAB: Tab = 'search'
const API = '/api/search'
const VOCAB = '/data/search-vocabulary.json'

/** SEARCH EVERYTHING, AND SAY HOW MUCH WAS SEARCHED.
 *
 *  TJ, 11 September 2026: "People need to be able to find things once we start pushing
 *  people here." A stranger from Facebook who searches for the one thing they care about
 *  and finds nothing concludes the site does not have it. So this searches every corpus
 *  the project holds -- the site's pages, the published posts, the archive's documents
 *  page by page, the town's minutes, and our transcripts of the recordings -- and it
 *  shows, on every search including an empty one, how much of each was searched.
 *
 *  THE TWO THINGS THIS PAGE MUST NEVER BLUR (QUEUE item 18, constraints 1 and 2):
 *
 *   - A TRANSCRIPT HIT IS NOT A DOCUMENT. It is our machine rendering of a recording, it
 *     is cited as the video at a timestamp, and it is drawn so that is obvious without a
 *     caveat: its own colour, its own label, a play glyph, a timestamp instead of a page.
 *     A caption model hears "fifteen hundred", "$1,500" and "$50" alike.
 *   - TWO DENOMINATORS, ALWAYS VISIBLE. "3 of 8,919 minutes" and "12 of 82,000 minutes of
 *     recording" are different sentences, and merging them has been wrong here twice.
 *
 *  THE VOCABULARY PROBLEM (constraint 3). A resident types OUR words -- "foreign
 *  language", "reduction in force" -- and the archive holds the town's: "French",
 *  "layoff". A null result on a public search reads as "the town never discussed it".
 *  So a search that finds little offers the archive's own terms for what was typed, from
 *  a curated list, and never a semantically similar passage: similar is the one thing
 *  this project does not publish. */

type Hit = {
  corpus: Corpus
  doc_key: string
  title: string
  board: string | null
  board_slug: string | null
  date: string
  kind: string
  cite_url: string
  source_url: string | null
  start_s: number | null
  chars: number
  rank: number
  snippet: string
  matched: string[]
}
type Corpus = 'post' | 'page' | 'source' | 'minutes' | 'transcript'
type Count = { hits: number; capped: boolean; holds: number }
type Payload = {
  q: string
  expression: string
  index: { built: string | null; holds: Record<Corpus, number> }
  counts: Partial<Record<Corpus, Count>>
  results: Partial<Record<Corpus, Hit[]>>
  rowsRead?: number
  ms?: number
  error?: string
  message?: string
}
type Vocab = Record<string, { try: string[]; note: string }>

const ORDER: Corpus[] = ['post', 'page', 'source', 'minutes', 'transcript']
const NAME: Record<Corpus, string> = {
  post: 'Blog posts',
  page: 'Pages on this site',
  source: 'Documents in the archive',
  minutes: 'Minutes and agendas the town published',
  transcript: 'Recordings — our transcripts',
}
const UNIT: Record<Corpus, [string, string]> = {
  post: ['post', 'posts'],
  page: ['page', 'pages'],
  source: ['document page', 'document pages'],
  minutes: ['document', 'documents'],
  transcript: ['minute of recording', 'minutes of recording'],
}
const WHAT: Record<Corpus, string> = {
  post: 'What this project has published, one finding at a time.',
  page: 'The analyses and reference pages here.',
  source: 'Budgets, annual reports and state files, cited to the page.',
  minutes: 'What the town itself published. A record.',
  transcript: 'Machine captions of meeting videos — ours, not the town’s. They locate a moment; they do not settle what was said.',
}

const BOARDS: [string, string][] = [
  ['', 'Every board'],
  ['school-committee', 'School Committee'],
  ['select-board', 'Select Board'],
  ['finance-committee', 'Finance Committee'],
  ['planning-board', 'Planning Board'],
  ['capital-planning-committee', 'Capital Planning'],
  ['board-of-assessors', 'Board of Assessors'],
]

function hms(s: number) {
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), x = s % 60
  return (h ? h + ':' : '') + String(m).padStart(h ? 2 : 1, '0') + ':' + String(x).padStart(2, '0')
}

function fmt(n: number) { return n.toLocaleString('en-US') }

/** The snippet, with FTS5's markers turned into <mark>. */
function Snippet({ s }: { s: string }) {
  const parts = s.split(/(‹[^›]*›)/g)
  return (
    <span>
      {parts.map((p, i) => p.startsWith('‹')
        ? <mark key={i} className="rounded px-0.5" style={{ background: 'var(--accent-soft, #fbe7a1)', color: 'inherit' }}>{p.slice(1, -1)}</mark>
        : <span key={i}>{p}</span>)}
    </span>
  )
}

export default function Search() {
  const initial = useMemo(() => {
    const u = new URL(window.location.href)
    return { q: u.searchParams.get('q') || '', board: u.searchParams.get('board') || '', since: u.searchParams.get('since') || '' }
  }, [])
  const [q, setQ] = useState(initial.q)
  const [board, setBoard] = useState(initial.board)
  const [since, setSince] = useState(initial.since)
  const [asked, setAsked] = useState(initial.q)
  const [data, setData] = useState<Payload | null>(null)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [vocab, setVocab] = useState<Vocab>({})
  const box = useRef<HTMLInputElement>(null)

  useEffect(() => { fetch(VOCAB).then(r => r.json()).then(setVocab).catch(() => {}) }, [])
  useEffect(() => { if (!initial.q) box.current?.focus() }, [initial.q])

  useEffect(() => {
    const u = new URL(window.location.href)
    if (asked) u.searchParams.set('q', asked); else u.searchParams.delete('q')
    if (board) u.searchParams.set('board', board); else u.searchParams.delete('board')
    if (since) u.searchParams.set('since', since); else u.searchParams.delete('since')
    window.history.replaceState(null, '', u.pathname + u.search)
    let alive = true
    setErr(null)
    setBusy(true)
    const params = new URLSearchParams({ q: asked })
    if (board) params.set('board', board)
    if (since) params.set('since', since)
    fetch(`${API}?${params}`)
      .then(async r => {
        const j = await r.json() as Payload
        if (!alive) return
        if (j.error) setErr(j.message || j.error)
        setData(j)
      })
      .catch(e => { if (alive) setErr(String(e)) })
      .finally(() => { if (alive) setBusy(false) })
    return () => { alive = false }
  }, [asked, board, since])

  const total = data ? ORDER.reduce((n, c) => n + (data.counts[c]?.hits || 0), 0) : 0
  const suggestions = useMemo(() => {
    const key = asked.trim().toLowerCase().replace(/^"|"$/g, '')
    if (!key) return null
    const v = vocab[key]
    return v ? v : null
  }, [asked, vocab])

  return (
    <ReportShell tab={TAB} kicker="Find it" title="Search everything this project holds"
      standfirst="Pages, posts, documents, minutes, and our transcripts of the recordings." noPrint>

      <form className="mt-6 flex flex-wrap gap-3 items-center"
        onSubmit={e => { e.preventDefault(); setAsked(q.trim()) }}>
        <input ref={box} value={q} onChange={e => setQ(e.target.value)}
          placeholder='A word, or a "phrase in quotes"'
          aria-label="Search"
          className="px-3 py-2 text-base rounded border w-full sm:w-[28rem]"
          style={{ background: 'var(--surface-2)', borderColor: 'var(--grid)', color: 'var(--text-primary)' }} />
        <button type="submit" className="px-4 py-2 text-sm font-semibold rounded"
          style={{ background: 'var(--series-cost)', color: '#fff' }}>Search</button>
        <select value={board} onChange={e => setBoard(e.target.value)} aria-label="Board"
          className="px-2 py-2 text-sm rounded border"
          style={{ background: 'var(--surface-2)', borderColor: 'var(--grid)', color: 'var(--text-primary)' }}>
          {BOARDS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
        </select>
        <label className="text-xs inline-flex items-center gap-2" style={{ color: 'var(--text-secondary)' }}>
          since
          <input type="date" value={since} onChange={e => setSince(e.target.value)}
            className="px-2 py-1 text-sm rounded border"
            style={{ background: 'var(--surface-2)', borderColor: 'var(--grid)', color: 'var(--text-primary)' }} />
        </label>
      </form>
      <p className="text-xs mt-2" style={{ color: 'var(--text-muted)' }}>
        The board and date filters apply to minutes and recordings. Words are matched as
        stems — <em>budget</em> also finds <em>budgets</em> and <em>budgeting</em>; each hit
        shows the words that actually matched.
      </p>

      {err && (
        <div className="card p-4 mt-6" style={{ borderColor: 'var(--series-cost)' }}>
          <p className="font-semibold">The search could not run.</p>
          <p className="text-sm mt-1" style={{ color: 'var(--text-secondary)' }}>{err}</p>
          <p className="text-sm mt-2" style={{ color: 'var(--text-secondary)' }}>
            Nothing has been lost: every document is still at its own address under{' '}
            <a className="underline" href="/sources">Sources</a>, and the minutes are at{' '}
            <a className="underline" href="/minutes">/minutes</a>.
          </p>
        </div>
      )}

      {data && asked && !err && (
        <>
          <p className="mt-6 text-sm" style={{ color: 'var(--text-secondary)' }}>
            {busy ? 'Searching…' : total === 0
              ? <>Nothing matched <strong>{asked}</strong>.</>
              : <><strong>{fmt(total)}{ORDER.some(c => data.counts[c]?.capped) ? '+' : ''}</strong> hits for <strong>{asked}</strong>, by where they are.</>}
          </p>

          {!busy && total === 0 && (
            <div className="card p-4 mt-4 max-w-3xl">
              <p className="font-semibold">That does not mean nobody said it.</p>
              <p className="text-sm mt-1" style={{ color: 'var(--text-secondary)' }}>
                The town&rsquo;s documents use the town&rsquo;s words, which are often not the
                ones we use here.
                {suggestions ? <> For <em>{asked}</em> the archive tends to say:</> : <> Try
                the name of the thing rather than the category &mdash; <em>French</em> rather than
                <em> foreign language</em>, <em>layoff</em> rather than <em>reduction in force</em>.</>}
              </p>
              {suggestions && (
                <p className="mt-2 flex flex-wrap gap-2">
                  {suggestions.try.map(t => (
                    <button key={t} type="button" onClick={() => { setQ(t); setAsked(t) }}
                      className="px-2 py-1 text-sm rounded border"
                      style={{ borderColor: 'var(--grid)', color: 'var(--series-cost)' }}>{t}</button>
                  ))}
                </p>
              )}
              {suggestions?.note && <p className="text-xs mt-2" style={{ color: 'var(--text-muted)' }}>{suggestions.note}</p>}
            </div>
          )}

          {!busy && total > 0 && suggestions && (
            <p className="text-sm mt-2 flex flex-wrap gap-2 items-center" style={{ color: 'var(--text-secondary)' }}>
              The archive also says:
              {suggestions.try.filter(t => t.toLowerCase() !== asked.toLowerCase()).map(t => (
                <button key={t} type="button" onClick={() => { setQ(t); setAsked(t) }}
                  className="px-2 py-0.5 text-sm rounded border"
                  style={{ borderColor: 'var(--grid)', color: 'var(--series-cost)' }}>{t}</button>
              ))}
            </p>
          )}

          {ORDER.map(c => {
            const hits = data.results[c] || []
            const count = data.counts[c]
            if (!count) return null
            return (
              <section key={c} className="mt-8" aria-label={NAME[c]}>
                <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
                  <h2 className="text-lg font-semibold" style={c === 'transcript' ? { color: 'var(--series-revenue, #b5540f)' } : undefined}>
                    {c === 'transcript' && <span aria-hidden="true">&#9654;&nbsp;</span>}{NAME[c]}
                  </h2>
                  <span className="text-sm tnum" style={{ color: 'var(--text-secondary)' }}>
                    {fmt(count.hits)}{count.capped ? '+' : ''} of {fmt(count.holds)} {count.holds === 1 ? UNIT[c][0] : UNIT[c][1]} searched
                  </span>
                </div>
                <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>{WHAT[c]}</p>
                {hits.length === 0 && (
                  <p className="text-sm mt-2" style={{ color: 'var(--text-muted)' }}>No hits here.</p>
                )}
                <ol className="mt-3 space-y-3">
                  {hits.map(h => <Result key={h.doc_key} h={h} />)}
                </ol>
                {count.hits > hits.length && (
                  <p className="text-xs mt-2" style={{ color: 'var(--text-muted)' }}>
                    Showing the {hits.length} best-ranked of {fmt(count.hits)}{count.capped ? '+' : ''}.
                    {count.capped && ' The count stopped at the cap, so ranking is within the first rows found rather than across everything; add a board or a date to narrow it.'}
                  </p>
                )}
              </section>
            )
          })}

          <p className="text-xs mt-10" style={{ color: 'var(--text-muted)' }}>
            Index built {data.index.built ? data.index.built.slice(0, 10) : 'unknown'}, holding{' '}
            {ORDER.map((c, i) => <span key={c}>{i ? ' · ' : ''}{fmt(data.index.holds[c] || 0)} {UNIT[c][1]}</span>)}.
            {typeof data.rowsRead === 'number' && <> This search read {fmt(data.rowsRead)} rows in {data.ms} ms.</>}
          </p>
        </>
      )}

      {!asked && (
        <div className="mt-8 max-w-3xl">
          <Body>
            Five places are searched at once, each against its own count, because they are
            not the same kind of thing. A page of the district&rsquo;s budget is a record; a
            transcript of a School Committee video is our machine&rsquo;s hearing of a
            recording, and it is shown in its own colour with a timestamp so nobody mistakes
            one for the other. {'​'}
          </Body>
          <ul className="mt-3 text-sm space-y-1" style={{ color: 'var(--text-secondary)' }}>
            {ORDER.map(c => <li key={c}><strong style={{ color: 'var(--text-primary)' }}>{NAME[c]}.</strong> {WHAT[c]}</li>)}
          </ul>
          <p className="text-sm mt-4" style={{ color: 'var(--text-secondary)' }}>
            Try{' '}
            {['helmets', '"class size"', 'paraprofessional', 'override', 'circuit breaker'].map((t, i) => (
              <span key={t}>{i ? ', ' : ''}<button type="button" className="underline" style={{ color: 'var(--series-cost)' }}
                onClick={() => { setQ(t); setAsked(t) }}>{t}</button></span>
            ))}.
          </p>
        </div>
      )}
    </ReportShell>
  )
}

function Result({ h }: { h: Hit }) {
  const isT = h.corpus === 'transcript'
  const where = isT
    ? `${h.board || h.board_slug}, ${h.date} — at ${hms(h.start_s || 0)}`
    : h.corpus === 'minutes' ? `${h.kind || 'document'}${h.source_url ? '' : ''}`
    : h.corpus === 'source' ? (h.board || '')
    : h.corpus === 'post' ? `published ${h.date}` : ''
  return (
    <li className="card p-3" style={isT ? { borderLeft: '4px solid var(--series-revenue, #b5540f)' } : undefined}>
      <div className="flex flex-wrap items-baseline gap-x-2">
        <a className="font-semibold underline" href={h.cite_url} target={isT || h.corpus === 'source' ? '_blank' : undefined} rel="noreferrer"
          style={{ color: isT ? 'var(--series-revenue, #b5540f)' : 'var(--series-cost)' }}>
          {isT ? <><span aria-hidden="true">&#9654; </span>{h.title}</> : h.title}
        </a>
        {where && <span className="text-xs" style={{ color: 'var(--text-muted)' }}>{where}</span>}
      </div>
      <p className="text-sm mt-1 leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
        <Snippet s={h.snippet} />
      </p>
      <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>
        {isT
          ? <>Opens the video about a minute before these words. A transcript is a finding aid: what was said is on the recording, not here.</>
          : h.matched.length ? <>matched: {h.matched.join(', ')}</> : null}
        {h.source_url && !isT && <> · <a className="underline" href={h.source_url} target="_blank" rel="noreferrer">publisher&rsquo;s copy</a></>}
      </p>
    </li>
  )
}

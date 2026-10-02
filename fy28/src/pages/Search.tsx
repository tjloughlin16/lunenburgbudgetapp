import { useEffect, useMemo, useRef, useState } from 'react'
import type { Tab } from '../routes'
import { track } from '../lib/track'
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
 *  WHAT KIND OF THING, FIRST. THE BOARD AND THE DATE LAST.
 *
 *  TJ, 2 October 2026: *"The UX is very hard to use. I think we need content-type filters
 *  and labels and such. For instance, i tried to find the landscaping contract, which i
 *  believe we have, and i couldnt find it and didnt know why i had to select a board and
 *  date."*
 *
 *  He was right, and the page was telling him so in the worst possible place. The only two
 *  controls it offered were a BOARD and a DATE -- and a line of small print underneath
 *  admitted that both apply only to minutes and recordings. So a resident hunting a
 *  purchase order was asked for the two things a purchase order does not have, and the
 *  disclosure was a footnote rather than a label. Rule 7a: the caveat goes beside what it
 *  qualifies.
 *
 *  Three changes follow from that, and they are the whole of this page's controls:
 *
 *   - THE PRIMARY CONTROL IS WHAT KIND OF THING IT IS, with the count for the query on it.
 *     `Documents 127 · Minutes & agendas 391 · Meeting recordings 1,639 · On this site 32`
 *     is the single line that answers "where is the contract": four of these, go there.
 *     It is drawn from the counts the API already returns for every corpus on every call,
 *     so filtering is instant and costs no further rows read.
 *   - BOARD AND DATE ARE SCOPED WHERE THEY SIT. They are behind a disclosure that names
 *     the kinds they narrow, they are disabled while a kind they cannot narrow is
 *     selected, and when they ARE set the page says out loud which kinds they excluded --
 *     because `date >= '2025-07-01'` silently drops every document in the archive, each of
 *     which carries no date at all.
 *   - EVERY RESULT CARRIES A BADGE SAYING WHAT IT IS. Not only transcripts. A single
 *     highlighted kind reads as decoration; a badge on every card makes `MACHINE
 *     TRANSCRIPT` one of a set, and a reader cannot take it for a document by default.
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
 *  CAPTIONS STAY IN THE DEFAULT, AND ARE RANKED LAST. 92% of the index is machine
 *  captions, which is why a document search felt lost in it -- but taking them out of the
 *  default would be worse than the crowding. The meeting register counts meetings whose
 *  ONLY surviving record is a recording, most of them School Committee, and a search that
 *  silently skipped those would answer "nobody said it" about meetings it had no way to
 *  read. That is the exact failure `search_minutes.py` prints a denominator to prevent.
 *  So nothing is withdrawn: the sections are REORDERED so documents and minutes lead,
 *  recordings come last, and one click gets a reader either on its own.
 *
 *  THE VOCABULARY PROBLEM (constraint 3). A resident types OUR words -- "foreign
 *  language", "landscaping" -- and the archive holds the town's: "French", "grounds". A
 *  null result on a public search reads as "the town never discussed it". So a search
 *  offers the archive's own terms for what was typed, from a curated list, and never a
 *  semantically similar passage: similar is the one thing this project does not publish.
 *  It now offers them whether or not the search found anything, because "landscaping"
 *  finds 2,189 things and none of them is the grounds contract. */

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
  via?: 'text' | 'topic'
}
type Corpus = 'post' | 'page' | 'recorded' | 'source' | 'minutes' | 'transcript'
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

/** DOCUMENTS AND MINUTES FIRST, RECORDINGS LAST. The order this page renders in, and the
 *  reason it changed: `post, page, recorded, source, minutes, transcript` put the
 *  archive's own documents FOURTH, under three sections of things we wrote. */
const ORDER: Corpus[] = ['source', 'minutes', 'page', 'post', 'recorded', 'transcript']

/** THE KINDS A RESIDENT THINKS IN -- four of them, named in their words and not ours.
 *
 *  `corpus` is a word from linguistics and `source` could be read as source code, as the
 *  original of something, or as a citation; neither belongs on a surface a reader uses
 *  (rule 7b forbids insider vocabulary). So the groupings are named for the artifact a
 *  person came looking for -- a document, the minutes, the recording, a page here -- and
 *  `Documents` says in its own hint that minutes are NOT in it, because minutes are
 *  documents too and that is the one ambiguity these four words have.
 *
 *  Four chips over six corpora, because `post`/`page` are one thing to a reader (written
 *  here) and `recorded`/`transcript` are one place to look (the video). They stay SEPARATE
 *  SECTIONS underneath: our minutes of a recording and the machine captions of it are
 *  derived to different depths and must not be summed or merged. */
const GROUPS: { id: string; label: string; hint: string; corpora: Corpus[] }[] = [
  { id: 'documents', label: 'Documents', corpora: ['source'],
    hint: 'Budgets, contracts, purchase orders, annual reports and state files, cited to the page. Not minutes.' },
  { id: 'minutes', label: 'Minutes & agendas', corpora: ['minutes'],
    hint: 'What the town published before and after a meeting. A record.' },
  { id: 'recordings', label: 'Meeting recordings', corpora: ['recorded', 'transcript'],
    hint: 'Machine captions of the videos, and our own notes written from them. A finding aid, never the record.' },
  { id: 'site', label: 'On this site', corpora: ['page', 'post'],
    hint: 'The analyses, the board and meeting pages, and the posts written by this project.' },
]
/** The kinds a board or a date can narrow at all: only these rows carry either. */
const DATED: Corpus[] = ['minutes', 'recorded', 'transcript']
const groupOf = (c: Corpus) => GROUPS.find(g => g.corpora.includes(c))!

const NAME: Record<Corpus, string> = {
  post: 'Blog posts',
  page: 'Pages on this site',
  recorded: 'What was said — our notes from the recordings',
  source: 'Documents in the archive',
  minutes: 'Minutes and agendas the town published',
  transcript: 'Meeting recordings — machine captions',
}
const UNIT: Record<Corpus, [string, string]> = {
  post: ['post', 'posts'],
  page: ['page', 'pages'],
  recorded: ['meeting', 'meetings'],
  source: ['document page', 'document pages'],
  minutes: ['document', 'documents'],
  transcript: ['minute of recording', 'minutes of recording'],
}
const WHAT: Record<Corpus, string> = {
  post: 'What this project has published, one finding at a time.',
  page: 'The analyses and reference pages here.',
  recorded: 'Our notes on recorded meetings, written from the captions: votes, transfers, topics. Each links to the video by the second.',
  source: 'Budgets, contracts, annual reports and state files, cited to the page.',
  minutes: 'What the town itself published. A record.',
  transcript: 'Machine captions of meeting videos — ours, not the town’s. They locate a moment; they do not settle what was said.',
}
/** WHAT THIS ONE RESULT IS, ON THE CARD. Keyed on `corpus` and never on `kind`: a hit
 *  matched through the affinity table arrives with `kind` overwritten to `page`, so a
 *  badge read off `kind` would call a document a page. */
function badge(h: Hit): string {
  switch (h.corpus) {
    case 'source': return 'Document'
    case 'minutes': return h.kind === 'agenda' ? 'Agenda' : 'Minutes'
    case 'transcript': return 'Machine transcript'
    case 'recorded': return 'Our notes from the video'
    case 'post': return 'Post'
    default: return 'Page on this site'
  }
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
    const t = u.searchParams.get('type') || ''
    return {
      q: u.searchParams.get('q') || '',
      board: u.searchParams.get('board') || '',
      since: u.searchParams.get('since') || '',
      type: GROUPS.some(g => g.id === t) ? t : '',
    }
  }, [])
  const [q, setQ] = useState(initial.q)
  const [board, setBoard] = useState(initial.board)
  const [since, setSince] = useState(initial.since)
  const [type, setType] = useState(initial.type)
  const [asked, setAsked] = useState(initial.q)
  const [data, setData] = useState<Payload | null>(null)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [vocab, setVocab] = useState<Vocab>({})
  const box = useRef<HTMLInputElement>(null)

  useEffect(() => { fetch(VOCAB).then(r => r.json()).then(setVocab).catch(() => {}) }, [])
  useEffect(() => { if (!initial.q) box.current?.focus() }, [initial.q])

  // The narrowing a board or a date cannot do. `source` rows carry the archive FOLDER in
  // `board_slug` and no date at all, and `page`/`post` carry neither -- so the API's
  // `board_slug = ?` and `date >= ?` do not narrow those kinds, they REMOVE them. That is
  // the whole of TJ's confusion, and the page now says it rather than leaving a reader to
  // conclude the archive holds no contracts.
  const narrowed = Boolean(board || since)
  const typeIsDated = !type || GROUPS.find(g => g.id === type)!.corpora.some(c => DATED.includes(c))

  useEffect(() => {
    const u = new URL(window.location.href)
    if (asked) u.searchParams.set('q', asked); else u.searchParams.delete('q')
    if (board) u.searchParams.set('board', board); else u.searchParams.delete('board')
    if (since) u.searchParams.set('since', since); else u.searchParams.delete('since')
    if (type) u.searchParams.set('type', type); else u.searchParams.delete('type')
    window.history.replaceState(null, '', u.pathname + u.search)
  }, [asked, board, since, type])

  useEffect(() => {
    let alive = true
    setErr(null)
    setBusy(true)
    // ONE CALL, EVERY KIND, ALWAYS. The `corpus=` parameter is deliberately not sent: the
    // chips need a count for every kind in order to say "4 of these are documents", and
    // asking for one kind would return one count. So the kind filter is applied to what is
    // RENDERED, which makes it instant and costs no further rows read against D1.
    const params = new URLSearchParams({ q: asked })
    if (board) params.set('board', board)
    if (since) params.set('since', since)
    // For about half a minute after a deploy the static site is live before the API
    // function is, and /api/search answers with the page's own HTML. TJ hit exactly that
    // (15 Sep: "Unexpected token '<', '<!doctype'"). Read the body as text, and if it is
    // not JSON, wait a few seconds and try once more before saying anything.
    const ask = (attempt: number): Promise<Payload> => fetch(`${API}?${params}`).then(async r => {
      const text = await r.text()
      try { return JSON.parse(text) as Payload }
      catch {
        if (attempt < 2) return new Promise(res => setTimeout(res, 4000)).then(() => ask(attempt + 1))
        throw new Error('The site was just updated and the search is still coming back up — try again in a moment.')
      }
    })
    ask(0)
      .then(j => {
        if (!alive) return
        if (j.error) setErr(j.message || j.error)
        setData(j)
      })
      .catch(e => { if (alive) setErr(e instanceof Error ? e.message : String(e)) })
      .finally(() => { if (alive) setBusy(false) })
    return () => { alive = false }
  }, [asked, board, since])

  const total = data ? ORDER.reduce((n, c) => n + (data.counts[c]?.hits || 0), 0) : 0
  const groupCount = (gid: string) => {
    const g = GROUPS.find(x => x.id === gid)!
    return {
      hits: g.corpora.reduce((n, c) => n + (data?.counts[c]?.hits || 0), 0),
      capped: g.corpora.some(c => data?.counts[c]?.capped),
    }
  }
  const shown: Corpus[] = type ? GROUPS.find(g => g.id === type)!.corpora : ORDER
  // PAGES SOMEBODY MARKED AS BEING ABOUT THIS, lifted above the sections.
  //
  // An affinity hit is the answer to the vocabulary problem and it was arriving buried:
  // "landscaping" pins /parks-and-recreation, which holds the grounds bid and links the
  // purchase order -- and it sat third, under 127 pages of zoning bylaw that happen to
  // use the word. Curation only pays if it is read.
  //
  // It keeps its own heading and its own sentence rather than being merged into the
  // ranking, because it is OURS: somebody typed those words against that page, and a
  // reader has to be able to tell that from the document having said them. Rule 7, for a
  // search result.
  const topic = shown.flatMap(c => (data?.results[c] || []).filter(h => h.via === 'topic'))
  // A search that found nothing is the most useful thing analytics can tell this site:
  // a question the archive did not answer. The term, not the person (lib/track.ts).
  useEffect(() => {
    if (data && asked && !busy && !err && total === 0) track('search_zero', asked.slice(0, 100))
  }, [data, asked, busy, err, total])
  const suggestions = useMemo(() => {
    const key = asked.trim().toLowerCase().replace(/^"|"$/g, '')
    if (!key) return null
    return vocab[key] || null
  }, [asked, vocab])

  const chip = (active: boolean): React.CSSProperties => ({
    borderColor: active ? 'var(--series-cost)' : 'var(--grid)',
    background: active ? 'var(--series-cost)' : 'var(--surface-2)',
    color: active ? '#fff' : 'var(--text-primary)',
  })

  return (
    <ReportShell tab={TAB} kicker="Find it" title="Search everything this project holds"
      standfirst="Documents, minutes, meeting recordings and the pages here — in one box." noPrint>

      <form className="mt-6 flex flex-wrap gap-2 items-center"
        onSubmit={e => { e.preventDefault(); setAsked(q.trim()) }}>
        <input ref={box} value={q} onChange={e => setQ(e.target.value)}
          placeholder='A word, or a "phrase in quotes"'
          aria-label="Search"
          className="px-3 py-2 text-base rounded border w-full sm:w-[26rem] min-w-0"
          style={{ background: 'var(--surface-2)', borderColor: 'var(--grid)', color: 'var(--text-primary)' }} />
        <button type="submit" className="px-4 py-2 text-sm font-semibold rounded"
          style={{ background: 'var(--series-cost)', color: '#fff' }}>Search</button>
      </form>

      {/* WHAT KIND OF THING, AND HOW MANY OF EACH. The primary control, directly under the
          box, with the count for the live query on every chip -- so "where is the
          contract" is answered by reading one line rather than by scrolling past a
          thousand captions. */}
      {asked && data && !err && (
        <div className="mt-3">
          <div className="flex flex-wrap gap-2" role="group" aria-label="What kind of thing">
            <button type="button" onClick={() => setType('')} aria-pressed={!type}
              className="px-3 py-1.5 text-sm rounded-full border font-semibold" style={chip(!type)}>
              Everything <span className="tnum font-normal opacity-80">{fmt(total)}{ORDER.some(c => data.counts[c]?.capped) ? '+' : ''}</span>
            </button>
            {GROUPS.map(g => {
              const { hits, capped } = groupCount(g.id)
              const active = type === g.id
              return (
                <button key={g.id} type="button" aria-pressed={active}
                  onClick={() => setType(active ? '' : g.id)}
                  disabled={hits === 0 && !active}
                  title={g.hint}
                  className="px-3 py-1.5 text-sm rounded-full border font-semibold disabled:opacity-45"
                  style={chip(active)}>
                  {g.label} <span className="tnum font-normal opacity-80">{fmt(hits)}{capped ? '+' : ''}</span>
                </button>
              )
            })}
          </div>
          {type && (
            <p className="text-xs mt-2 max-w-2xl" style={{ color: 'var(--text-secondary)' }}>
              {GROUPS.find(g => g.id === type)!.hint}
            </p>
          )}
          {/* WHY A CHIP SAYS ZERO. Beside the chip, not at the foot of the results: a
              greyed `Documents 0` under a board filter reads as "the archive holds no
              contracts about this", and that misreading is the whole of the report this
              page was rebuilt from. */}
          {narrowed && (
            <p className="text-xs mt-2 max-w-2xl" style={{ color: 'var(--text-secondary)' }}>
              A board or a date is set, so only minutes, agendas and recordings are being
              searched — documents and site pages carry neither and were left out.{' '}
              <button type="button" className="underline" style={{ color: 'var(--series-cost)' }}
                onClick={() => { setBoard(''); setSince('') }}>Clear it</button> to search everything.
            </p>
          )}
        </div>
      )}

      {/* BOARD AND DATE, WITH THEIR LIMIT ON THE LABEL. They narrow three kinds and remove
          the other three, so they sit behind a disclosure that names the three, and they
          are disabled while a kind they cannot narrow is the one being looked at. */}
      {asked && <details className="mt-3" open={narrowed}>
        <summary className="text-sm cursor-pointer" style={{ color: 'var(--series-cost)' }}>
          Narrow by board or date
          <span className="ml-1 text-xs" style={{ color: 'var(--text-muted)' }}>
            — minutes, agendas and recordings only{narrowed ? ' · on' : ''}
          </span>
        </summary>
        <div className="mt-2 flex flex-wrap gap-3 items-center">
          <select value={board} onChange={e => setBoard(e.target.value)} aria-label="Board"
            disabled={!typeIsDated}
            className="px-2 py-2 text-sm rounded border disabled:opacity-45"
            style={{ background: 'var(--surface-2)', borderColor: 'var(--grid)', color: 'var(--text-primary)' }}>
            {BOARDS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select>
          <label className="text-xs inline-flex items-center gap-2" style={{ color: 'var(--text-secondary)' }}>
            since
            <input type="date" value={since} onChange={e => setSince(e.target.value)}
              disabled={!typeIsDated}
              className="px-2 py-1 text-sm rounded border disabled:opacity-45"
              style={{ background: 'var(--surface-2)', borderColor: 'var(--grid)', color: 'var(--text-primary)' }} />
          </label>
          {narrowed && (
            <button type="button" onClick={() => { setBoard(''); setSince('') }}
              className="px-2 py-1 text-xs rounded border"
              style={{ borderColor: 'var(--grid)', color: 'var(--series-cost)' }}>clear</button>
          )}
        </div>
        <p className="text-xs mt-2 max-w-2xl" style={{ color: 'var(--text-muted)' }}>
          {typeIsDated
            ? <>A document in the archive carries no board and no date — a purchase order is filed by how it reached us, not by who met about it. So these two do not narrow documents or the pages here: they <strong>remove</strong> them from the results.</>
            : <>{GROUPS.find(g => g.id === type)!.label} carry no board and no date, so neither of these applies. Choose <em>Everything</em> to use them.</>}
        </p>
      </details>}

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
              : <><strong>{fmt(total)}{ORDER.some(c => data.counts[c]?.capped) ? '+' : ''}</strong> hits for <strong>{asked}</strong>
                  {type
                    ? <> — showing the <strong>{fmt(groupCount(type).hits)}{groupCount(type).capped ? '+' : ''}</strong> in {GROUPS.find(g => g.id === type)!.label.toLowerCase()}.</>
                    : <>, by what kind of thing they are.</>}</>}
          </p>

          {/* THE TOWN'S WORD FOR YOURS, WHETHER OR NOT ANYTHING WAS FOUND. A search for
              "landscaping" returns 2,189 hits and not one of them is the grounds
              contract, because the town calls it GROUNDS. A suggestion shown only on zero
              results is a suggestion that never fires on exactly the queries that need
              it most -- the ones that find plenty of the wrong thing. */}
          {!busy && suggestions && (
            <div className="card p-3 mt-3 max-w-3xl">
              <p className="text-sm">
                <strong>The town may call it something else.</strong>{' '}
                <span style={{ color: 'var(--text-secondary)' }}>
                  For <em>{asked}</em> the archive tends to say:
                </span>
              </p>
              <p className="mt-2 flex flex-wrap gap-2">
                {suggestions.try.filter(t => t.toLowerCase() !== asked.toLowerCase()).map(t => (
                  <button key={t} type="button" onClick={() => { setQ(t); setAsked(t) }}
                    className="px-2 py-1 text-sm rounded border"
                    style={{ borderColor: 'var(--grid)', color: 'var(--series-cost)' }}>{t}</button>
                ))}
              </p>
              {suggestions.note && <p className="text-xs mt-2" style={{ color: 'var(--text-muted)' }}>{suggestions.note}</p>}
            </div>
          )}

          {!busy && total === 0 && !suggestions && (
            <div className="card p-4 mt-4 max-w-3xl">
              <p className="font-semibold">That does not mean nobody said it.</p>
              <p className="text-sm mt-1" style={{ color: 'var(--text-secondary)' }}>
                The town&rsquo;s documents use the town&rsquo;s words, which are often not the
                ones we use here. Try the name of the thing rather than the category
                &mdash; <em>French</em> rather than <em>foreign language</em>,{' '}
                <em>grounds</em> rather than <em>landscaping</em>.
              </p>
            </div>
          )}

          {/* SECTIONS WITH HITS, THEN ONE LINE FOR THE REST. The page used to open a
              search for "paraprofessional" with "Blog posts -- 0 of 0 posts searched --
              No hits here", an empty section leading 624 hits. The denominator still
              matters -- a null result must be readable as "not in what could be
              searched" -- so the corpora with nothing are summed into one line under the
              results rather than each getting a heading over an empty space. */}
          {!busy && topic.length > 0 && (
            <section className="mt-8" aria-label="Pages about this">
              <h2 className="text-lg font-semibold">Pages about this</h2>
              <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>
                Marked by hand as being about <em>{asked}</em>. The word itself may not
                appear on them — that is the point of the list.
              </p>
              <ol className="mt-3 space-y-3">{topic.map(h => <Result key={h.doc_key} h={h} />)}</ol>
            </section>
          )}

          {shown.filter(c => (data.results[c] || []).some(h => h.via !== 'topic')).map(c => {
            const hits = (data.results[c] || []).filter(h => h.via !== 'topic')
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

          {/* THE KINDS WITH NOTHING, AND -- SEPARATELY -- THE KINDS A NARROWING REMOVED.
              Those are different sentences. "Nothing in the documents" is a fact about
              the archive; "documents were excluded because you set a date" is a fact
              about the controls, and reading the second as the first is what sent TJ
              looking for a contract that is there. */}
          {shown.some(c => data.counts[c] && !(data.results[c] || []).some(h => h.via !== 'topic')) && (
            <p className="text-sm mt-6" style={{ color: 'var(--text-muted)' }}>
              Nothing in{' '}
              {shown.filter(c => data.counts[c] && !(data.results[c] || []).some(h => h.via !== 'topic'))
                .map((c, i, arr) => { const n = data.counts[c]!.holds; return <span key={c}>{i ? (i === arr.length - 1 ? ' or ' : ', ') : ''}{NAME[c].toLowerCase()} ({fmt(n)} {n === 1 ? UNIT[c][0] : UNIT[c][1]} searched)</span> })}.
            </p>
          )}

          <p className="text-xs mt-10 max-w-3xl" style={{ color: 'var(--text-muted)' }}>
            Words are matched as stems — <em>budget</em> also finds <em>budgets</em> and{' '}
            <em>budgeting</em> — and each hit shows the words that actually matched.
            Index built {data.index.built ? data.index.built.slice(0, 10) : 'unknown'}, holding{' '}
            {ORDER.map((c, i) => <span key={c}>{i ? ' · ' : ''}{fmt(data.index.holds[c] || 0)} {UNIT[c][1]}</span>)}.
            {typeof data.rowsRead === 'number' && <> This search read {fmt(data.rowsRead)} rows in {data.ms} ms.</>}
          </p>
        </>
      )}

      {!asked && (
        <div className="mt-6 max-w-3xl">
          <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
            Try{' '}
            {['landscaping', 'helmets', '"class size"', 'paraprofessional', 'override', 'circuit breaker'].map((t, i) => (
              <span key={t}>{i ? ', ' : ''}<button type="button" className="underline" style={{ color: 'var(--series-cost)' }}
                onClick={() => { setQ(t); setAsked(t) }}>{t}</button></span>
            ))}.
          </p>
          <ul className="mt-5 text-sm space-y-2" style={{ color: 'var(--text-secondary)' }}>
            {GROUPS.map(g => (
              <li key={g.id}>
                <strong style={{ color: 'var(--text-primary)' }}>{g.label}.</strong> {g.hint}{' '}
                <span className="tnum" style={{ color: 'var(--text-muted)' }}>
                  {g.corpora.filter(c => data?.index.holds[c]).map((c, i) => (
                    <span key={c}>{i ? ' · ' : ''}{fmt(data!.index.holds[c])} {UNIT[c][1]} searched</span>
                  ))}
                </span>
              </li>
            ))}
          </ul>
          <Body>
            Each kind keeps its own count, because they are not the same kind of thing. A
            page of the district&rsquo;s budget is a record; a transcript of a School Committee
            video is our machine&rsquo;s hearing of a recording, and it is shown in its own
            colour with a timestamp so nobody mistakes one for the other. {'​'}
          </Body>
        </div>
      )}
    </ReportShell>
  )
}

function Result({ h }: { h: Hit }) {
  const isT = h.corpus === 'transcript'
  const g = groupOf(h.corpus)
  const where = isT
    ? `${h.board || h.board_slug}, ${h.date} — at ${hms(h.start_s || 0)}`
    : h.corpus === 'minutes' ? `${h.board || h.board_slug || ''}${h.date ? ', ' + h.date : ''}`
    : h.corpus === 'source' ? (h.board || '')
    : h.corpus === 'post' ? `published ${h.date}` : ''
  return (
    <li className="card p-3" style={isT ? { borderLeft: '4px solid var(--series-revenue, #b5540f)' } : undefined}>
      <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
        {/* A BADGE ON EVERY CARD, NOT ONLY ON THE CAPTIONS. One highlighted kind reads as
            emphasis; a badge on all of them reads as a classification, which is the only
            way `Machine transcript` tells a reader what it is rather than that it is
            special. */}
        <span className="text-[10px] font-bold uppercase tracking-widest px-1.5 py-0.5 rounded shrink-0"
          style={isT
            ? { background: 'var(--series-revenue, #b5540f)', color: '#fff' }
            : { border: '1px solid var(--grid)', color: 'var(--text-muted)' }}>
          {badge(h)}
        </span>
        <a className="font-semibold underline" href={h.cite_url} target={isT || h.corpus === 'source' ? '_blank' : undefined} rel="noreferrer"
          style={{ color: isT ? 'var(--series-revenue, #b5540f)' : 'var(--series-cost)' }}>
          {isT ? <><span aria-hidden="true">&#9654; </span>{h.title}</> : h.title}
        </a>
        {where && <span className="text-xs" style={{ color: 'var(--text-muted)' }}>{where}</span>}
      </div>
      <p className="text-sm mt-1 leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
        {h.via === 'topic'
          ? <><span className="text-[10.5px] font-bold uppercase tracking-widest mr-1.5"
                style={{ color: 'var(--text-muted)' }}>matched by topic</span>
              <span className="text-xs">this page is about: <Snippet s={h.snippet} /></span></>
          : <Snippet s={h.snippet} />}
      </p>
      <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>
        {isT
          ? <>Opens the video about a minute before these words. A transcript is a finding aid: what was said is on the recording, not here.</>
          : h.matched.length ? <>matched: {h.matched.join(', ')}</> : null}
        {h.source_url && !isT && <> · <a className="underline" href={h.source_url} target="_blank" rel="noreferrer">publisher&rsquo;s copy</a></>}
      </p>
      <span className="sr-only">{g.label}</span>
    </li>
  )
}

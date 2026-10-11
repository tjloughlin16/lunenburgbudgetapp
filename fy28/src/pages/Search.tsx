import { useEffect, useMemo, useRef, useState } from 'react'
import type { Tab } from '../routes'
import { track } from '../lib/track'
import { ReportShell, Body } from '../components/report'

const TAB: Tab = 'search'
const API = '/api/search'
const VOCAB = '/data/search-vocabulary.json'
const BOARDS_URL = '/data/search-boards.json'

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
 *  finds 2,189 things and none of them is the grounds contract.
 *
 *  THE ORDER IS A CONTROL, IT IS NEWEST-FIRST BY DEFAULT, AND IT IS PER SECTION.
 *
 *  TJ, 2 October 2026: *"need sort order. newest first by default. relevance next?"*
 *
 *  The fact that shapes it: **0 of 11,928 document rows in the index carry a date, and 0 of
 *  1,233 site pages. Not one.** Only minutes (11,020), our notes from the recordings (558)
 *  and the machine captions (279,142) have one. So a GLOBAL newest-first would hand a
 *  reader hundreds of recent minutes and file every document in the archive underneath them
 *  -- including the Parks grounds bid this page was rebuilt to surface -- and it would do it
 *  SILENTLY. That is the same misreading as the date filter: `date >= '2025-07-01'` removes
 *  every document, and a greyed `Documents 0` reads as *the town never published one*.
 *
 *  So the order is applied PER SECTION -- AND THEREFORE SO IS THE CONTROL.
 *
 *  The first build of this put a global `Sort: [Newest first] [Relevance]` row under the
 *  chips. TJ: *"dont you think its too many primary CTAs in the same area?"* Two reasons it
 *  was wrong, and the second is the one that matters:
 *
 *   - FOUR CONTROL CLUSTERS ABOVE THE RESULTS, of which one is genuinely primary. The chips
 *     are not really a control at all, they are the ANSWER -- `Documents 132` says where the
 *     thing is before anybody clicks -- and a refinement almost nobody touches cannot carry
 *     the same weight.
 *   - A GLOBAL CONTROL THAT APPLIES TO SOME SECTIONS IS THE BOARD/DATE MISTAKE AGAIN, one
 *     row higher. A general-looking control that silently does nothing to what the reader
 *     came for is the whole confusion this page was rebuilt to remove.
 *
 *  So it is small, muted, right-aligned furniture on each section heading, where it cannot
 *  misstate its own scope:
 *
 *   - A DATED SECTION gets the toggle -- `newest first · relevance`, both visible, because
 *     there are only two and a select would hide the choice. Newest is the default.
 *   - AN UNDATED SECTION gets the FACT AND NOT A DISABLED CONTROL: `by relevance — these
 *     carry no date`. A greyed-out toggle invites a reader to wonder what they did wrong;
 *     a sentence answers them.
 *   - EVERY HEADING SAYS WHICH ORDER IT IS IN either way, so nobody has to infer it.
 *   - `sort=` IS IN THE URL beside `type=`, always and explicitly, so a pasted link means
 *     the same thing after the default moves. One parameter binds all the dated sections;
 *     the undated ones cannot vary, so there is nothing for it to say about them.
 *
 *  It is a server parameter rather than a client sort because the API returns the 12
 *  BEST-RANKED rows per corpus. Sorting those twelve by date gives "the newest of the most
 *  relevant twelve", which for 391 matching minutes is not the newest minutes and would be
 *  labelled as though it were. It costs nothing: `sort=newest` changes only the OUTER
 *  `ORDER BY` of a query whose inner subselect already read those rows, so rows read -- what
 *  D1 bills -- is unchanged. */

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
type Corpus = 'post' | 'page' | 'job' | 'person' | 'recorded' | 'source' | 'minutes' | 'transcript'
type Count = { hits: number; capped: boolean; holds: number }
type Payload = {
  q: string
  expression: string
  /** Set when the exact words found nothing and the API searched again for words that
   *  START with them -- `kim` reaching Kimberly. The page must say so: these are not
   *  exact matches, and a reader quoting one should know. */
  widened?: { from: string; to: string } | null
  index: { built: string | null; holds: Record<Corpus, number> }
  counts: Partial<Record<Corpus, Count>>
  sort?: Sort
  sortedBy?: Partial<Record<Corpus, 'date' | 'rank'>>
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
const ORDER: Corpus[] = ['job', 'person', 'source', 'minutes', 'page', 'post', 'recorded', 'transcript']
/* JOBS AND PEOPLE GO FIRST, and that is not a ranking of importance. Both are small and
 * exact: a name or a job title matches a handful of rows that ARE the answer, where the same
 * word in the minutes is a mention. TJ, 10 October 2026: *"I'm looking for a job posting for
 * the school and can't find it."* It was in the archive, fetched daily, and unreachable. */

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
/** `short` is the chip's own label, and it exists because of the GRID. Four equal cells at
 *  half of 400px leave about 150px of content, and `Minutes & agendas` and `Meeting
 *  recordings` both wrap in that -- which makes one cell two lines tall and the row ragged
 *  again, the exact thing the grid is for. So the chip carries the short word and `label`
 *  carries the full one wherever there is room for it: the hint list, the sentence above the
 *  results, the screen-reader line on every card. Shortening the label everywhere would
 *  have cost `agendas`, and an agenda is not a set of minutes. */
const GROUPS: { id: string; label: string; short: string; hint: string; corpora: Corpus[] }[] = [
  { id: 'documents', label: 'Documents', short: 'Documents', corpora: ['source'],
    hint: 'Budgets, contracts, purchase orders, annual reports and state files, cited to the page. Not minutes.' },
  { id: 'minutes', label: 'Minutes & agendas', short: 'Minutes', corpora: ['minutes'],
    hint: 'What the town published before and after a meeting — minutes and agendas both. A record.' },
  { id: 'recordings', label: 'Meeting recordings', short: 'Recordings', corpora: ['recorded', 'transcript'],
    hint: 'Machine captions of the videos, and our own notes written from them. A finding aid, never the record.' },
  { id: 'site', label: 'On this site', short: 'This site', corpora: ['page', 'post'],
    hint: 'The analyses, the board and meeting pages, and the posts written by this project.' },
  { id: 'jobs', label: 'Job postings', short: 'Jobs', corpora: ['job'],
    hint: 'Openings at the town (its own job board) and the school district (SchoolSpring), checked daily since October 2026. Ones no longer listed stay here and say so. All of them: /jobs.' },
  { id: 'people', label: 'People', short: 'People', corpora: ['person'],
    hint: 'Every name on the org charts — the town reports’ rosters since FY2011 and today’s staff directories — with each role and year. One name is not proven to be one person.' },
]
/** The kinds a board or a date can narrow at all: only these rows carry either. */
const DATED: Corpus[] = ['minutes', 'recorded', 'transcript']
/** The kinds that can be put in date order. One more than DATED: a job posting carries the
 *  date it was posted, but no board, so it can be sorted and cannot be narrowed by board. */
const SORTABLE: Corpus[] = [...DATED, 'job']

/** THE TWO ORDERS, AND THE DEFAULT. `newest` first because that is what a reader asks of a
 *  record; `relevance` kept because it is the only order the undated nine tenths of the
 *  index has, and because a search for a word wants the best match for it. */
type Sort = 'newest' | 'relevance'
const SORTS: { id: Sort; label: string }[] = [
  { id: 'newest', label: 'newest first' },
  { id: 'relevance', label: 'relevance' },
]

/** THE ORDER, ON THE HEADING OF THE SECTION IT ORDERS.
 *
 *  WHETHER THERE IS A TOGGLE AT ALL turns on whether this CORPUS HAS DATES, and the first
 *  build got that wrong by reading the API's `sortedBy` -- the order the rows actually came
 *  back in. In relevance mode every corpus comes back by rank, so all six sections printed
 *  `by relevance — these carry no date` and the minutes, which are dated to the day, lost
 *  the switch that would have got a reader back. `sortedBy` says what happened; `dated`
 *  says what is POSSIBLE, and only the second may decide whether a control exists.
 *
 *  `by` is still read, as the assertion that the API did what the heading claims: a dated
 *  section showing `newest first` whose rows came back by rank would be the page lying
 *  about its own order, so it says `by relevance` instead. */
function Order({ dated, by, set }: {
  dated: boolean; by?: 'date' | 'rank'; set: (s: Sort) => void
}) {
  if (!dated) return (
    <span className="text-xs sm:ml-auto" style={{ color: 'var(--text-muted)' }}>
      by relevance — these carry no date
    </span>
  )
  const live: Sort = by === 'date' ? 'newest' : 'relevance'
  return (
    <span className="text-xs sm:ml-auto inline-flex items-center gap-1.5" role="group" aria-label="Order these">
      {SORTS.map((o, i) => (
        <span key={o.id} className="inline-flex items-center gap-1.5">
          {i > 0 && <span aria-hidden="true" style={{ color: 'var(--grid)' }}>·</span>}
          {live === o.id
            ? <span aria-current="true" style={{ color: 'var(--text-secondary)' }}>{o.label}</span>
            : <button type="button" onClick={() => set(o.id)} className="underline"
                style={{ color: 'var(--series-cost)' }}>{o.label}</button>}
        </span>
      ))}
    </span>
  )
}
const groupOf = (c: Corpus) => GROUPS.find(g => g.corpora.includes(c))!

const NAME: Record<Corpus, string> = {
  post: 'Blog posts',
  page: 'Pages on this site',
  job: 'Job postings — the town and the schools',
  person: 'People on the org charts',
  recorded: 'What was said — our notes from the recordings',
  source: 'Documents in the archive',
  minutes: 'Minutes and agendas the town published',
  transcript: 'Meeting recordings — machine captions',
}
const UNIT: Record<Corpus, [string, string]> = {
  post: ['post', 'posts'],
  page: ['page', 'pages'],
  job: ['posting', 'postings'],
  person: ['name', 'names'],
  recorded: ['meeting', 'meetings'],
  source: ['document page', 'document pages'],
  minutes: ['document', 'documents'],
  transcript: ['minute of recording', 'minutes of recording'],
}
/** THE SECTION'S OWN SENTENCE -- PRINTED ONLY WHERE IT IS LOAD-BEARING, OR ASKED FOR.
 *
 *  It used to print on every section, which at 400px put three lines of furniture between a
 *  heading and the first result: the denominator, the order, and this. Two of the three had
 *  to stay. This one is per-section prose a returning reader has already read, and the chip
 *  for every kind carries the same sentence as its hint -- shown under the chips the moment
 *  a reader filters to that kind.
 *
 *  SO IT PRINTS UNCONDITIONALLY FOR EXACTLY THE TWO KINDS THAT ARE OURS. `transcript` is a
 *  caption model's hearing of a recording and `recorded` is our notes written off those
 *  captions; a reader who takes either for the record has been misled, and that warning is
 *  not furniture. Both sections render LAST, so neither costs a line above the first result.
 *  Every other kind shows it when that kind is the one being looked at. */
const WHAT_ALWAYS: Corpus[] = ['recorded', 'transcript']
const WHAT: Record<Corpus, string> = {
  post: 'What this project has published, one finding at a time.',
  page: 'The analyses and reference pages here.',
  job: 'The town’s and the school district’s postings. An open one links to the employer’s page, to apply; one no longer listed links to its history on /jobs. Leaving the listing is not the same as being filled.',
  person: 'A name as the org charts print it, with every role and year. The same name in two decades may be two people.',
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
    case 'job': return h.title.startsWith('No longer listed') ? 'Job, closed' : 'Job opening'
    case 'person': return 'Person'
    default: return 'Page on this site'
  }
}

type BoardOpt = { slug: string; label: string; meetings: number; first: string; last: string }

/** EVERY BOARD, FROM `/data/search-boards.json`, WHICH IS GENERATED FROM THE INDEX.
 *
 *  This was a hardcoded list of SIX. Fifty-one boards the archive holds minutes for could
 *  not be selected at all -- Parks Commission among them, with 186 meetings in the dated
 *  corpora (193 in the meeting register, which counts dates with no searchable document), and
 *  a reader looking for what the Parks Commission said about its budget had no way to ask.
 *  TJ: *"the search board drop-down doesn't have all..it's a limited set."*
 *
 *  The six below remain as a FALLBACK for the one case that matters: the payload failing to
 *  load. A control that empties is worse than a control that is short, because a reader
 *  cannot tell an empty filter from a filter that found nothing.
 */
const BOARDS_FALLBACK: BoardOpt[] = [
  { slug: 'select-board', label: 'Select Board', meetings: 0, first: '', last: '' },
  { slug: 'school-committee', label: 'School Committee', meetings: 0, first: '', last: '' },
  { slug: 'finance-committee', label: 'Finance Committee', meetings: 0, first: '', last: '' },
  { slug: 'planning-board', label: 'Planning Board', meetings: 0, first: '', last: '' },
  { slug: 'capital-planning-committee', label: 'Capital Planning Committee', meetings: 0, first: '', last: '' },
  { slug: 'board-of-assessors', label: 'Board of Assessors', meetings: 0, first: '', last: '' },
]

/** How many to show above the A-Z list. Fifty-seven options in one flat menu is a wall;
 *  the five busiest boards are most of what anybody asks for, and the rest is findable
 *  alphabetically rather than by scanning a frequency order nobody can predict. */
const BUSIEST = 5

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
      sort: (u.searchParams.get('sort') === 'relevance' ? 'relevance' : 'newest') as Sort,
    }
  }, [])
  const [q, setQ] = useState(initial.q)
  const [board, setBoard] = useState(initial.board)
  const [since, setSince] = useState(initial.since)
  const [type, setType] = useState(initial.type)
  const [sort, setSort] = useState<Sort>(initial.sort)
  const [asked, setAsked] = useState(initial.q)
  const [data, setData] = useState<Payload | null>(null)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [vocab, setVocab] = useState<Vocab>({})
  const [boards, setBoards] = useState<BoardOpt[]>(BOARDS_FALLBACK)
  const box = useRef<HTMLInputElement>(null)

  useEffect(() => { fetch(VOCAB).then(r => r.json()).then(setVocab).catch(() => {}) }, [])
  useEffect(() => {
    fetch(BOARDS_URL).then(r => r.json())
      .then((b: BoardOpt[]) => { if (Array.isArray(b) && b.length) setBoards(b) })
      .catch(() => {})   // keep the fallback; never empty the control
  }, [])
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
    // Written even when it is the default: a shared link should keep its meaning if the
    // default ever moves, which is not true of a parameter that is only present when set.
    if (asked) u.searchParams.set('sort', sort); else u.searchParams.delete('sort')
    window.history.replaceState(null, '', u.pathname + u.search)
  }, [asked, board, since, type, sort])

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
    // The order is the API's business, not this page's: it returns the twelve BEST-RANKED
    // rows per corpus, so sorting those twelve here would produce "the newest of the most
    // relevant twelve" and call it newest first. It costs no extra rows read -- only the
    // outer ORDER BY of a query that already read them changes.
    params.set('sort', sort)
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
  }, [asked, board, since, sort])

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
    /* THE BOX IS THE PAGE, SO IT STARTS NEAR THE TOP. Rule 7a, measured rather than
       argued: at a true 400px the old header -- a two-line H1 and a three-line standfirst
       saying the same thing again -- put the input 280px down and the first result 726px
       down, on a screen that shows about 850. A search page that opens with five lines
       about searching is the four-page correction this file already carries, applied to
       the one page where the thing is a text field. */
    <ReportShell tab={TAB} kicker="Find it" title="Search everything"
      standfirst="Documents, minutes, recordings and this site." noPrint>

      {/* THE BUTTON SITS IN THE ROW, NOT UNDER IT. `w-full` on the input pushed a
          full-width blue button onto a line of its own, for a tap almost nobody makes --
          the form submits on Enter. */}
      <form className="mt-4 sm:mt-6 flex gap-2 items-center"
        onSubmit={e => { e.preventDefault(); setAsked(q.trim()) }}>
        <input ref={box} value={q} onChange={e => setQ(e.target.value)}
          placeholder='A word, or a "phrase in quotes"'
          aria-label="Search"
          className="px-3 py-2 text-base rounded border flex-1 sm:flex-none sm:w-[26rem] min-w-0"
          style={{ background: 'var(--surface-2)', borderColor: 'var(--grid)', color: 'var(--text-primary)' }} />
        <button type="submit" className="px-4 py-2 text-sm font-semibold rounded shrink-0"
          style={{ background: 'var(--series-cost)', color: '#fff' }}>Search</button>
      </form>

      {/* WHAT KIND OF THING, AND HOW MANY OF EACH -- IN A GRID, BECAUSE THE COUNTS ARE THE
          POINT OF IT.

          TJ, 2 October 2026: *"shouldn't the filter buttons be more.... strictly organized?
          they are just wrapped which looks haphazard"*. Wrapped flex put `Everything` and
          `Documents` on one line and then gave each remaining chip a line of its own, every
          one a different width -- four ragged rows for five chips at 400px, and a rag reads
          as nobody having decided anything.
          
          But the structural fault is the one worth fixing: THESE WERE NEVER FIVE OF A KIND.
          `Everything` is not a content type, it is the absence of a filter, and laying it
          out as a peer of the four types is what the rag was a picture of. So the four types
          get a strict two-column grid (1fr 1fr) that becomes three columns on a wider
          screen -- six types since Jobs and People joined, so 2x3 and then 3x2, both even --
          and the reset is a quiet line that only exists while there is something to reset.
          
          EQUAL CELLS ARE WHAT MAKES THE NUMBERS READABLE. The counts are right-aligned in
          cells of identical width, so `where is it?` is answered by reading a column of four
          figures rather than four figures scattered across four x positions -- which is the
          whole reason the count is on the chip. A zero keeps its cell for the same reason:
          an empty cell in an even grid IS the statement that the archive holds nothing of
          that kind for this query, and it now costs no line at all. */}
      {asked && data && !err && (
        <div className="mt-3">
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2" role="group" aria-label="What kind of thing">
            {GROUPS.map(g => {
              const { hits, capped } = groupCount(g.id)
              const active = type === g.id
              return (
                <button key={g.id} type="button" aria-pressed={active}
                  onClick={() => setType(active ? '' : g.id)}
                  disabled={hits === 0 && !active}
                  title={g.hint}
                  className="w-full px-3 py-1.5 text-sm rounded-full border font-semibold disabled:opacity-45 flex items-baseline justify-between gap-2 whitespace-nowrap"
                  style={chip(active)}>
                  <span>{g.short}</span>
                  <span className="tnum font-normal opacity-80">{fmt(hits)}{capped ? '+' : ''}</span>
                </button>
              )
            })}
          </div>
          {type && (
            <p className="text-sm mt-2">
              <button type="button" onClick={() => setType('')} className="underline"
                style={{ color: 'var(--series-cost)' }}>
                Clear — show all {fmt(total)}{ORDER.some(c => data.counts[c]?.capped) ? '+' : ''}
              </button>
            </p>
          )}
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
            — {boards.length} boards; minutes, agendas and recordings only{narrowed ? ' · on' : ''}
          </span>
        </summary>
        <div className="mt-2 flex flex-wrap gap-3 items-center">
          <select value={board} onChange={e => setBoard(e.target.value)} aria-label="Board"
            disabled={!typeIsDated}
            className="px-2 py-2 text-sm rounded border disabled:opacity-45"
            style={{ background: 'var(--surface-2)', borderColor: 'var(--grid)', color: 'var(--text-primary)' }}>
            <option value="">Every board</option>
            {/* THE BUSIEST FIVE, THEN A-Z. The count is MEETINGS on record, which is what
                tells a reader whether an empty result means `nobody said it` or `we hold
                one meeting for this body`. Both groups are rendered from the same list, so
                a board cannot appear in one and not the other. */}
            {boards.length > BUSIEST && (
              <optgroup label="Most on record">
                {boards.slice(0, BUSIEST).map(b => (
                  <option key={b.slug} value={b.slug}>
                    {b.label}{b.meetings ? ` (${fmt(b.meetings)})` : ''}
                  </option>
                ))}
              </optgroup>
            )}
            <optgroup label={boards.length > BUSIEST ? 'Every board, A\u2013Z' : 'Boards'}>
              {[...boards].sort((a, b) => a.label.localeCompare(b.label)).map(b => (
                <option key={b.slug} value={b.slug}>
                  {b.label}{b.meetings ? ` (${fmt(b.meetings)})` : ''}
                </option>
              ))}
            </optgroup>
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
            : <>{GROUPS.find(g => g.id === type)!.label} cannot be narrowed by board or date here, so neither of these applies. Choose <em>Everything</em> to use them.</>}
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
          <p className="mt-4 sm:mt-6 text-sm" style={{ color: 'var(--text-secondary)' }}>
            {busy ? 'Searching…' : total === 0
              ? <>Nothing matched <strong>{asked}</strong>.</>
              : type
                ? <><strong>{fmt(groupCount(type).hits)}{groupCount(type).capped ? '+' : ''}</strong> of {fmt(total)}{ORDER.some(c => data.counts[c]?.capped) ? '+' : ''} hits for <strong>{asked}</strong> are {GROUPS.find(g => g.id === type)!.label.toLowerCase()}.</>
                : <><strong>{fmt(total)}{ORDER.some(c => data.counts[c]?.capped) ? '+' : ''}</strong> hits for <strong>{asked}</strong>.</>}
          </p>
          {data.widened && total > 0 && !busy && (
            <p className="text-xs mt-1 max-w-2xl" style={{ color: 'var(--text-muted)' }}>
              No exact match for every word, so these are words that <strong>start with</strong> what you typed &mdash; <em>kim</em> finds Kimberly. Check the highlighted word before quoting a result.
            </p>
          )}

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
            <section className="mt-6 sm:mt-8" aria-label="Pages about this">
              <div className="flex flex-wrap items-baseline gap-x-3">
                <h2 className="text-lg font-semibold">Pages about this</h2>
                <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
                  by relevance — a marking carries no date
                </span>
              </div>
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
              <section key={c} className="mt-6 sm:mt-8" aria-label={NAME[c]}>
                <div className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
                  <h2 className="text-lg font-semibold" style={c === 'transcript' ? { color: 'var(--series-revenue, #b5540f)' } : undefined}>
                    {c === 'transcript' && <span aria-hidden="true">&#9654;&nbsp;</span>}{NAME[c]}
                  </h2>
                  <span className="text-sm tnum" style={{ color: 'var(--text-secondary)' }}>
                    {fmt(count.hits)}{count.capped ? '+' : ''} of {fmt(count.holds)} {count.holds === 1 ? UNIT[c][0] : UNIT[c][1]} searched
                  </span>
                  {/* THE ORDER, AND THE SWITCH FOR IT, ON THIS SECTION'S OWN HEADING --
                      quiet furniture rather than a button, because it refines what one
                      reader in fifty asked for and the chips above it are the answer. */}
                  <Order dated={SORTABLE.includes(c)} by={data.sortedBy?.[c]} set={setSort} />
                </div>
                {(WHAT_ALWAYS.includes(c) || (type && GROUPS.find(g => g.id === type)!.corpora.includes(c))) && (
                  <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>{WHAT[c]}</p>
                )}
                <ol className="mt-3 space-y-3">
                  {hits.map(h => <Result key={h.doc_key} h={h} />)}
                </ol>
                {count.hits > hits.length && (
                  <p className="text-xs mt-2" style={{ color: 'var(--text-muted)' }}>
                    Showing {data.sortedBy?.[c] === 'date' ? `the ${hits.length} newest` : `the ${hits.length} best-ranked`} of {fmt(count.hits)}{count.capped ? '+' : ''}.
                    {count.capped && ' The count stopped at the cap, so the order — whichever of the two it is — is within the first rows found rather than across everything; add a board or a date to narrow it.'}
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
    : h.corpus === 'post' ? `published ${h.date}`
    : h.corpus === 'job' ? `${h.board || ''} · posted ${h.date} · ${h.kind}`
    : h.corpus === 'person' ? h.kind : ''
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
        <a className="font-semibold underline" href={h.cite_url} target={isT || h.corpus === 'source' || (h.corpus === 'job' && !h.cite_url.includes('lunenburgbudgetproject.org')) ? '_blank' : undefined} rel="noreferrer"
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
        {h.source_url && !isT && <> · <a className="underline" href={h.source_url} target="_blank" rel="noreferrer">{h.corpus === 'job' ? 'our copy of the posting' : <>publisher&rsquo;s copy</>}</a></>}
      </p>
      <span className="sr-only">{g.label}</span>
    </li>
  )
}

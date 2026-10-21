/** A TOWN MEETING'S STATUS BOARD — every article on its warrant and where each one stands.
 *
 *  TJ, 20–21 October 2026: the meeting's thread is "a STATUS BOARD of every warrant article and
 *  its latest stage … so people can see how things came to conclusions", and an article that was
 *  only placed and recommended "can be summed up without a full thread, as long as there is a
 *  link to the details of the article (which the town posts online)".
 *
 *  The payload is `warrant` on a generated thread (scripts/build_town_meetings.py). Nothing here
 *  decides a stage or a result: each row says what the record holds, and a result heard in a
 *  recording says so beside it (rule 7). The rule that promotes an article to its own thread is
 *  ours, and its words are printed under the board (rule 3). */

export type WarrantArticle = {
  article: number | ''; title: string; title_from: string; amount: string; sponsor: string
  stage: string; fincom: string; select_board: string
  result: string; result_basis: '' | 'official' | 'ours'; result_amount: string; result_ref: string
  details: string; details_town: string; details_page: number | ''
  clerk_doc: string; clerk_page: string
  amended: boolean; divided: boolean; put_off: boolean
  promoted: boolean; promoted_why: string; thread: string; numbered_by: string; money: number
  /** Figures a person checked in the recording (sources/data/heard-figures.csv). */
  heard?: { figure: string; value: number; what: string; board: string; date: string; listen: string
    verified_by: string; verified_on: string; note: string }[]
}
export type Warrant = {
  meeting: string; date: string; kind: 'annual' | 'special'; status: string
  called_on: string; warrant_opens: string; warrant_closes: string; warrant_signed: string
  warrant_doc: string; warrant_town_url: string; notice_doc: string; notice_town_url: string
  signals: string[]
  /** From the legal notice, as printed (build_town_meetings.notice_when_where). */
  time?: string; place?: string
  /** Posted agendas that take up this meeting's business before it, and decisions that
   *  announced a date (ours, from the recording). Upcoming meetings only. */
  next?: { date: string; board: string; time: string; hearing: boolean; item: string; doc?: string
    town_url?: string; announced?: string; source?: string; video_url?: string; t?: string | number }[]
  rule: { meetings: number; boards: number; routine_per_board: number; divided_share: number; text: string }
  articles: WarrantArticle[]
}

const muted = { color: 'var(--text-muted)' } as const
const secondary = { color: 'var(--text-secondary)' } as const
const link = { color: 'var(--series-cost)' } as const

const pretty = (iso: string) =>
  iso ? new Date(iso + 'T12:00:00Z').toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) : ''
const long = (iso: string) =>
  new Date(iso + 'T12:00:00Z').toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' })

/** A warrant prints its titles in capitals. Read in sentence case, keeping what is an acronym
 *  or carries a figure: "FISCAL YEAR 2027 OMNIBUS BUDGET" -> "Fiscal year 2027 omnibus budget". */
const ACRONYMS = new Set(['FY', 'PEG', 'OPEB', 'SAP', 'ADA', 'MBTA', 'DPW', 'CPA', 'EDC', 'COA', 'MGL', 'II', 'III',
  'LMHS', 'TC', 'PACC', 'MART', 'IBPO', 'AFSCME', 'STM', 'ATM', 'BTFC', 'APDC', 'US', 'MSBA', 'LED'])
const PROPER = new Set(['lunenburg', 'massachusetts', 'whalom', 'passios', 'ritter', 'brooks', 'marshall', 'fitchburg', 'montachusett', 'chapter'])
export function plainTitle(s: string) {
  const letters = s.replace(/[^A-Za-z]/g, '')
  if (!letters || letters.replace(/[^A-Z]/g, '').length < letters.length * 0.7) return s.charAt(0).toUpperCase() + s.slice(1)
  const out = s.toLowerCase().replace(/[a-z0-9’'.]+/g, w => {
    const up = w.toUpperCase()
    if (ACRONYMS.has(up.replace(/[’'.]/g, '')) || /\d/.test(w)) return up
    return PROPER.has(w) ? w.charAt(0).toUpperCase() + w.slice(1) : w
  })
  return out.charAt(0).toUpperCase() + out.slice(1)
}

const STAGE_TONE: Record<string, string> = {
  'Proposed': 'var(--text-muted)', 'Placed on the warrant': 'var(--series-revenue)',
  'On the warrant': 'var(--series-revenue)', 'Recommended': 'var(--series-revenue)',
  'Voted': 'var(--series-cost)', 'Kept off the warrant': 'var(--status-critical)',
}
const RESULT_WORD: Record<string, string> = {
  'passed': 'Passed', 'failed': 'Failed', 'passed over': 'Passed over', 'postponed': 'Postponed',
  'amended and passed': 'Amended and passed', 'not clear in the record': 'Outcome not clear in the record',
}

function Chip({ tone, filled, children }: { tone: string; filled?: boolean; children: React.ReactNode }) {
  return (
    <span className="inline-flex items-center px-1.5 py-[1px] rounded text-[10.5px] font-bold uppercase tracking-wider whitespace-nowrap"
      style={filled ? { background: tone, color: '#fff' } : { border: `1px solid ${tone}`, color: tone }}>{children}</span>
  )
}

function Row({ a, onGo }: { a: WarrantArticle; onGo: (id: string) => void }) {
  const go = (id: string) => (e: React.MouseEvent) => { e.preventDefault(); onGo(id) }
  return (
    <li className="py-3 border-t first:border-t-0 avoid-break"
      style={{ borderColor: 'var(--grid)', ...(a.promoted ? { boxShadow: 'inset 3px 0 0 var(--series-cost)', paddingLeft: 10 } : {}) }}>
      <div className="flex items-baseline gap-x-2 gap-y-1 flex-wrap">
        <span className="text-[12px] font-semibold tnum shrink-0" style={muted}>
          {a.article === '' ? 'No number yet' : `Article ${a.article}`}
        </span>
        {a.stage ? <Chip tone={STAGE_TONE[a.stage] ?? 'var(--text-muted)'} filled={a.stage === 'Voted'}>{a.stage}</Chip> : null}
        {a.result ? (
          <span className="text-[13px] font-semibold" style={{ color: a.result === 'failed' ? 'var(--status-critical)' : 'var(--series-cost)' }}>
            {RESULT_WORD[a.result] ?? a.result}
            <span className="font-normal" style={muted}>
              {a.result_basis === 'ours' ? ' · as heard in the recording' : a.result_basis === 'official' ? ' · the Town Clerk’s record' : ''}
            </span>
          </span>
        ) : null}
      </div>
      <div className="flex items-baseline justify-between gap-3 mt-0.5">
        <span className="text-[15px] leading-snug font-semibold min-w-0" style={{ overflowWrap: 'anywhere' }}>{plainTitle(a.title) || 'Title not in what we hold'}</span>
        {a.amount || a.result_amount ? (
          <span className="text-[14px] font-bold tnum shrink-0">{a.amount || a.result_amount}</span>
        ) : null}
      </div>
      {/* A FIGURE FROM A RECORDING is shown only once somebody listened at the second cited,
          and it says where it was said, so a reader can hear it too (rule 13). */}
      {a.heard?.length ? (
        <ul className="list-none p-0 m-0 mt-1 space-y-0.5">
          {a.heard.map((h, i) => (
            <li key={i} className="text-[13.5px] leading-snug">
              <span className="font-bold tnum">{h.figure}</span> <span style={secondary}>{h.what}</span>
              <span className="text-[12px]" style={muted}> · said at the {h.board}, {pretty(h.date)} · checked in the recording · <a className="underline" style={link} href={h.listen} target="_blank" rel="noreferrer">listen</a></span>
            </li>
          ))}
        </ul>
      ) : null}
      {a.sponsor ? <div className="text-[12.5px] mt-0.5" style={muted}>Put forward by {a.sponsor === 'citizen petition' ? 'a citizens’ petition' : a.sponsor}</div> : null}
      {a.fincom || a.select_board ? (
        <div className="text-[13px] leading-snug mt-1" style={{ ...secondary, overflowWrap: 'anywhere' }}>
          {a.fincom ? <div><span className="font-semibold">Finance Committee:</span> {a.fincom}</div> : null}
          {a.select_board ? <div><span className="font-semibold">Select Board:</span> {a.select_board}</div> : null}
        </div>
      ) : null}
      {a.amended || a.divided || a.put_off ? (
        <div className="flex flex-wrap gap-1.5 mt-1.5">
          {a.amended ? <Chip tone="var(--status-warning)">Amendment taken up</Chip> : null}
          {a.divided ? <Chip tone="var(--status-warning)">Divided vote</Chip> : null}
          {a.put_off ? <Chip tone="var(--status-warning)">Postponed or referred</Chip> : null}
        </div>
      ) : null}
      {a.promoted ? (
        <div className="text-[13px] leading-snug mt-1.5">
          <span className="font-semibold" style={link}>Followed closely</span>
          <span style={secondary}> — {a.promoted_why}.</span>
        </div>
      ) : null}
      <div className="text-[12.5px] mt-1.5 flex flex-wrap gap-x-3 gap-y-0.5">
        {a.thread ? (
          <a className="underline font-semibold" style={link} href={`/threads/${a.thread}`} onClick={go(a.thread)}>
            {a.promoted ? 'Its own thread →' : 'Followed in a thread →'}</a>
        ) : null}
        {a.details ? (
          <a className="underline" style={link} href={`${a.details}${a.details_page ? `#page=${a.details_page}` : ''}`}>
            Read the article{a.details_page ? ` (page ${a.details_page})` : ''}</a>
        ) : null}
        {a.details_town ? <a className="underline" style={link} href={a.details_town} target="_blank" rel="noreferrer">the town’s copy</a> : null}
        {a.clerk_doc ? (
          <a className="underline" style={link} href={`${a.clerk_doc}${a.clerk_page ? `#page=${a.clerk_page}` : ''}`}>
            the Clerk’s record{a.clerk_page ? ` (page ${a.clerk_page})` : ''}</a>
        ) : null}
        {a.result_basis === 'ours' && a.result_ref ? (
          <a className="underline" style={link} href={a.result_ref} target="_blank" rel="noreferrer">watch the vote</a>
        ) : null}
      </div>
    </li>
  )
}

const short = (iso: string) =>
  new Date(iso + 'T12:00:00Z').toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })

/** WHAT HAPPENS NEXT. TJ, 21 October 2026, reviewing this page for a Facebook post: the dates
 *  a resident can act on -- a public hearing tomorrow, the Select Board's recommendations --
 *  were buried in the timeline. A posted agenda is the town's; an announcement is OURS, from
 *  the recording, and says so with the second to check it at. */
function Next({ w }: { w: Warrant }) {
  const n = w.next ?? []
  if (w.status !== 'upcoming' || !n.length) return null
  return (
    <section className="mt-8 max-w-2xl" aria-label="What happens next">
      <h2 className="text-xl font-bold tracking-tight mb-2">What happens next</h2>
      <ol className="list-none p-0 m-0 space-y-2">
        {n.map((x, i) => (
          <li key={i} className="card p-3" style={x.hearing ? { borderLeft: '4px solid var(--series-revenue)' } : undefined}>
            <p className="text-[12px] font-bold uppercase tracking-wider" style={muted}>
              {short(x.date)}{x.time ? ` · ${x.time}` : ''} · {x.board}
            </p>
            <p className="text-[15px] font-semibold leading-snug mt-0.5">
              {x.hearing ? 'Public hearing: ' : ''}{x.item}
            </p>
            {x.hearing ? <p className="text-[13px] mt-0.5" style={secondary}>A public hearing is where residents can speak before the board decides.</p> : null}
            <p className="text-[12.5px] mt-1 flex flex-wrap gap-x-3" style={muted}>
              {x.announced
                ? <span>Announced at the {x.board} on {pretty(x.announced)}; from our notes of the recording{x.video_url ? <> · <a className="underline" style={link} href={`${x.video_url}${x.t ? `&t=${x.t}s` : ''}`} target="_blank" rel="noreferrer">hear it</a></> : null}. The agenda is not posted yet.</span>
                : <>{x.doc ? <a className="underline" style={link} href={x.doc}>The agenda</a> : null}
                    {x.town_url ? <a className="underline" style={link} href={x.town_url} target="_blank" rel="noreferrer">on the town’s site</a> : null}</>}
            </p>
          </li>
        ))}
        <li className="card p-3" style={{ borderLeft: '4px solid var(--series-cost)' }}>
          <p className="text-[12px] font-bold uppercase tracking-wider" style={muted}>
            {short(w.date)}{w.time ? ` · ${w.time}` : ''}
          </p>
          <p className="text-[15px] font-semibold leading-snug mt-0.5">Town Meeting votes{w.place ? `, at the ${w.place}` : ''}</p>
        </li>
      </ol>
    </section>
  )
}

/** THE MEETING, THEN EVERY ARTICLE (rule 7a: the thing first). */
export function TownMeetingBoard({ w, onGo }: { w: Warrant; onGo: (id: string) => void }) {
  const voted = w.articles.filter(a => a.result).length
  const closely = w.articles.filter(a => a.promoted).length
  const days = Math.round((Date.parse(w.date + 'T12:00:00Z') - Date.now()) / 86400000)
  const kind = w.kind === 'annual' ? 'Annual Town Meeting' : 'Special Town Meeting'
  // KEPT OFF IS NOT ON. An article the Select Board voted not to place is listed apart, after
  // the warrant, so nobody reads it as something Town Meeting will vote on.
  const off = w.articles.filter(a => a.stage === 'Kept off the warrant')
  const on = w.articles.filter(a => a.stage !== 'Kept off the warrant')
  const provisional = on.some(a => a.numbered_by)
  const upcoming = w.status === 'upcoming'
  return (
    <>
      <div className="card p-4 mt-4 max-w-2xl" style={{ borderLeft: '4px solid var(--series-cost)' }}>
        <p className="text-[11px] font-bold uppercase tracking-widest" style={muted}>
          {w.status === 'upcoming' ? 'Coming up' : 'Held'}
        </p>
        <p className="text-[17px] font-bold mt-1">{kind} · {long(w.date)}{w.time ? `, ${w.time}` : ''}</p>
        {w.place ? <p className="text-[14px] mt-0.5" style={secondary}>{w.place}</p> : null}
        {w.status === 'upcoming' && days >= 0 ? (
          <p className="text-[14px] mt-0.5" style={secondary}>{days === 0 ? 'Today' : `In ${days} day${days === 1 ? '' : 's'}`}</p>
        ) : null}
        <ul className="list-none p-0 m-0 mt-2 text-[13.5px] leading-snug space-y-0.5" style={secondary}>
          {w.called_on ? <li>Called by the Select Board on {pretty(w.called_on)}</li> : null}
          {w.warrant_opens || w.warrant_closes ? (
            <li>Warrant open for articles{w.warrant_opens ? ` from ${pretty(w.warrant_opens)}` : ''}{w.warrant_closes ? ` to ${pretty(w.warrant_closes)}` : ''}</li>
          ) : null}
          {w.warrant_signed ? <li>Warrant signed {pretty(w.warrant_signed)}</li> : null}
          {!w.warrant_doc ? (
            <li style={muted}>{w.status === 'upcoming' ? 'The warrant has not been posted yet.' : 'We do not hold the warrant for this meeting.'}</li>
          ) : null}
        </ul>
        {upcoming ? (
          <p className="text-[13.5px] leading-snug mt-2">
            The <span className="font-semibold">warrant</span> is the list of questions, called articles, that Town
            Meeting will vote on. Registered voters decide each one at the meeting.
          </p>
        ) : null}
        <p className="text-[12.5px] mt-2 flex flex-wrap gap-x-3">
          {w.warrant_doc ? <a className="underline" style={link} href={w.warrant_doc}>The warrant</a> : null}
          {w.warrant_town_url ? <a className="underline" style={link} href={w.warrant_town_url} target="_blank" rel="noreferrer">the warrant on the town’s site</a> : null}
          {w.notice_doc ? <a className="underline" style={link} href={w.notice_doc}>The legal notice</a> : null}
        </p>
      </div>

      <Next w={w} />

      {/* THE COUNTS SAY SOMETHING FOR AN UPCOMING MEETING TOO: "0 with a vote" before the
          meeting reads as nothing happened. Before it: on the warrant and kept off. After it:
          voted, and followed closely. */}
      <div className="flex flex-wrap gap-x-10 gap-y-4 mt-6">
        {(upcoming
          ? [[on.length, `on the warrant so far${on.length - on.filter(a => a.article !== '').length ? `, ${on.length - on.filter(a => a.article !== '').length} not yet numbered` : ''}`],
             [off.length, 'kept off by the Select Board']]
          : [[w.articles.length, w.articles.length === 1 ? 'article' : 'articles'],
             [voted, `${voted === 1 ? 'article' : 'articles'} with a vote in the record we hold`],
             [closely, 'followed closely — see the rule below the list']]
        ).map(([n, label]) => (
          <div key={String(label)}>
            <div className="text-3xl font-bold tracking-tight tnum">{n}</div>
            <div className="text-[13px] leading-snug mt-1 max-w-[15rem]" style={secondary}>{label}</div>
          </div>
        ))}
      </div>

      <h2 className="text-2xl font-bold tracking-tight mt-10 mb-1 max-w-3xl">Every article, and where it stands</h2>
      <p className="text-[13px] mt-0 mb-2 max-w-2xl" style={muted}>
        Articles followed closely first, then the largest sums, then by number.
        {provisional ? ' Known so far from the Select Board’s votes: the posted warrant may renumber or reword them.' : ''}
      </p>
      {on.length === 0 ? (
        <p className="text-[15px]" style={secondary}>No article in the record we hold yet.</p>
      ) : (
        <ul className="list-none p-0 m-0 max-w-2xl">
          {on.map((a, i) => <Row key={`${a.article}-${i}`} a={a} onGo={onGo} />)}
        </ul>
      )}
      {off.length ? (
        <>
          <h3 className="text-lg font-bold tracking-tight mt-8 mb-1 max-w-3xl">Kept off the warrant</h3>
          <p className="text-[13px] mt-0 mb-2 max-w-2xl" style={muted}>
            The Select Board voted not to place {off.length === 1 ? 'this article' : 'these articles'}, so Town Meeting will not vote on {off.length === 1 ? 'it' : 'them'}.
          </p>
          <ul className="list-none p-0 m-0 max-w-2xl">
            {off.map((a, i) => <Row key={`off-${a.article}-${i}`} a={a} onGo={onGo} />)}
          </ul>
        </>
      ) : null}
      <p className="text-[12.5px] leading-snug mt-3 max-w-2xl" style={muted}>
        <span className="font-semibold">Which articles are followed closely.</span> {w.rule.text}
      </p>
    </>
  )
}

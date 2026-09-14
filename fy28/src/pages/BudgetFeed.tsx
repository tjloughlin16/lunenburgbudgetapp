import { useState, type ReactElement } from 'react'
import { feedSeasonFromPath, type Tab } from '../routes'
import { H2, ReportShell, useReport } from '../components/report'
import { JoinLinks, type Join } from '../components/BoardsThisWeek'

const TAB: Tab = 'budgetfeed'
const DATA = '/data/budget-feed.json'

/** THE BUDGET FEED. TJ, 14 September 2026: "a single page that pulls all the meetings
 *  together across all boards and data into a single page... once budget season hits,
 *  this will be the hottest page of all latest and greatest content. but now, it
 *  auto-captures anything that is budget related too."
 *
 *  Four parts, each a filter over what the other generators hold (build_budget_feed.py):
 *  what is coming, where the cycle stands, what was said, what was posted. The recent
 *  discussion is grouped BY MEETING and collapsed, because 500 budget-tagged lines in
 *  ninety days is a wall, and a wall is what this site keeps being told not to build. */

type Upcoming = { board: string; board_slug: string; date: string; days_away: number; agenda_url: string; markers: string[]; hook?: string | null; time?: string | null; where?: string | null; attend?: string | null; join?: Join | null; items: { agenda_line: string; why_it_matters?: string; important?: boolean }[]; board_page: string }
type Window = { board: string; board_slug: string; typical_first: string; typical_last: string; earliest: string; latest: string; cycles: number; this_cycle: string[] }
type Stage = { stage: string; key: string; windows: Window[]; status: 'past' | 'now' | 'underway' | 'ahead'; typical_first: string; typical_last: string }
type Entry = { kind: string; board: string; board_slug: string; date: string; page: string; text?: string | null; detail?: string | null; tags?: string[]; figures?: string[]; markers?: string[]; t?: number | null; video_url?: string; minutes?: number }
type Statement = { board: string; board_slug: string; date: string; page: string; kind: string; scope: string; fiscal_year: number | null; amount_as_heard: string | null; statement: string; who: string; status: string; t: number; video_url: string }
type Cut = { board: string; board_slug: string; date: string; page: string; item: string; scope: string; fiscal_year: number | null; amount_as_heard: string | null; fte_as_heard: string | null; status: string; who: string; t: number; video_url: string; key: string }
type State = { meetings_read: number; first_date: string | null; last_date: string | null; latest: Record<string, Statement>; history: Record<string, Statement[]>; cuts: Cut[]; live_cuts: number; live_by_scope: Record<string, number>; log: { board: string; board_slug: string; date: string; page: string; added: string[]; changed: { item: string; was: string; now: string }[]; n_added: number; n_changed: number }[] }
type Payload = {
  about: string; as_of: string; cycle_fy: number; cycle_opens: string; cycle_closes: string; recent_days: number; state: State; seasons: { fy: number; path: string; label: string; live: boolean }[]
  answers: { question: string; label: string; answer: string; status: string; link?: string | null; basis?: string | null }[]
  episodes: { id: string; season_fy: string; kind: 'regular' | 'special'; label: string; opens: string; closes: string; about_fy: string; trigger: string; outcome: string; source: string; note: string; closed: boolean; state: State; answers: { label: string; answer: string; status: string; link?: string | null }[] | null }[]
  outcome: { closed: boolean; atm_date: string | null; election_date: string | null; headline: string; adopted: { amount: number; label: string; source: string } | null; questions: { date: string; election: string; question: string; type: string; amount: number | null; purpose: string; yes: number | null; no: number | null; total: number | null; registered: number | null; turnout_pct: number | null; result: string }[] }
  upcoming: Upcoming[]; calendar: Stage[]; entries: Entry[]
  documents: { first_seen: string; source: string; title: string; url: string }[]
  notices: { first_seen: string; source: string; published: string; title: string; link: string }[]
  counts: { upcoming: number; entries: number; boards: number; by_board: Record<string, number>; kinds: Record<string, number> }
}

const mmdd = (d: string) => new Date(d + 'T12:00:00').toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
const long = (d: string) => new Date(d + 'T12:00:00').toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' })
const ts = (t?: number | null) => t == null ? '' : `${Math.floor(t / 60)}:${String(t % 60).padStart(2, '0')}`
const FY = (fy: number) => 'FY' + String(fy).slice(2)
const STATUS: Record<Stage['status'], [string, string]> = {
  past: ['done for this cycle', 'var(--text-muted)'], now: ['in its window now', 'var(--status-good)'],
  underway: ['on agendas this cycle', 'var(--status-good)'], ahead: ['ahead', 'var(--text-secondary)'],
}

const SCOPE: Record<string, string> = { school: 'School', town: 'Town', both: 'Town and schools' }

/** THE LATEST ON THE RECORD. TJ: "School committee announced 10 cuts for a $2m deficit."
 *  For each scope and kind the most recent statement that carried a figure -- who said
 *  it by role, its status, the second in the video -- then the cut list as last stated
 *  and the meetings that changed it. Every figure is AS HEARD from captions; the second
 *  in the video is the record. */
/** THREE TIERS, BY WHO GETS THE LAST WORD. TJ, 14 September 2026: "1) Decided, final
 *  information -- how much was actually approved, voted, final, money gets appropriated
 *  (or not). 2) The context for how we got there. Many meetings and votes along the way;
 *  a board's vote doesn't make things final -- the School Committee voted 3-1 for $350k,
 *  and that got overwritten a few times to get to the $418k. That's part of the story,
 *  not the final situation. 3) Things proposed that never made it to a vote of the
 *  citizens, Town Meeting, or maybe even other boards -- part of the story, but mostly
 *  just utterances."
 *
 *  FINAL is what Town Meeting and the ballot did, from the registries, or the episode's
 *  recorded outcome; nothing a board voted is ever in it. THE STORY is every board vote
 *  in order, oldest first, with the ones a later vote overwrote greyed and pointed at
 *  what replaced them. SAID, NEVER VOTED is a count and a fold. */
const PLAIN: Record<string, string> = { deficit: 'gap', budget_total: 'budget', override: 'override', state_aid: 'state aid', free_cash: 'free cash', levy: 'levy' }
const plain = (s: Statement) => `${SCOPE[s.scope] || s.scope} ${PLAIN[s.kind] || s.kind}`.toLowerCase()
const keyOf = (s: Statement) => `${s.scope}/${s.kind}`

function Line({ amount, text, who, board, board_slug, date, video_url, t, muted, chip, chipColor, after }: { amount?: string | null; text: string; who?: string; board: string; board_slug: string; date: string; video_url?: string; t?: number | null; muted?: boolean; chip?: string; chipColor?: string; after?: string }) {
  return (
    <li className="pl-3 py-0.5" style={{ borderLeft: `2px solid ${muted ? 'var(--grid)' : (chipColor || 'var(--grid)')}`, color: muted ? 'var(--text-muted)' : undefined }}>
      {chip && <a className="text-[10px] font-bold uppercase tracking-wider mr-1.5" href={`/boards/${board_slug}`} style={{ color: muted ? 'var(--text-muted)' : chipColor }}>{chip}</a>}
      {amount && <span className="tnum font-bold" style={{ textDecoration: muted ? 'line-through' : undefined }}>{amount}</span>}{amount ? ' — ' : ''}{text}
      <span className="text-xs ml-1.5" style={{ color: 'var(--text-muted)' }}>{who ? `${who}, ` : ''}{chip ? null : <><a className="underline" href={`/boards/${board_slug}`}>{board}</a>, </>}{mmdd(date)}{video_url ? <> · <a className="underline tnum" href={video_url}>{ts(t) || 'video'}</a></> : null}</span>
      {after && <span className="text-xs ml-1.5 italic" style={{ color: 'var(--text-muted)' }}>{after}</span>}
    </li>
  )
}

function Tiers({ st, closed, decisions, outcome, finalText, finalNote, fy }: { st: State; closed: boolean; decisions: Entry[]; outcome?: Payload['outcome'] | null; finalText?: string | null; finalNote?: string | null; fy: number }) {
  const [showSaid, setShowSaid] = useState(!closed)
  const all = Object.values(st.history).flat()
  // Tier 2 -- every board vote, oldest first. A voted figure that a later vote on the same
  // thing replaced is greyed, struck, and points at what replaced it.
  const votedStatements = all.filter(x => x.status === 'voted')
  const latestVoted: Record<string, Statement> = {}
  for (const x of votedStatements) if (!latestVoted[keyOf(x)] || latestVoted[keyOf(x)].date <= x.date) latestVoted[keyOf(x)] = x
  const votedCuts = st.cuts.filter(c => c.status === 'voted')
  const votes = decisions.filter(e => (e.detail || '').toLowerCase().startsWith('pass'))
  type Row = { date: string; t: number; el: ReactElement }
  const story: Row[] = [
    ...votedStatements.map((x, i): Row => {
      const later = latestVoted[keyOf(x)]
      const superseded = later !== x && later.date > x.date
      return { date: x.date, t: x.t, el: <Line key={'s' + i} chip={`${x.board} vote`} chipColor="var(--series-cost)" muted={superseded} amount={x.amount_as_heard} text={`${x.statement} (${plain(x)})`} who={x.who} board={x.board} board_slug={x.board_slug} date={x.date} video_url={x.video_url} t={x.t} after={superseded ? `overwritten ${mmdd(later.date)}${later.amount_as_heard ? ` → ${later.amount_as_heard}` : ''}` : undefined} /> }
    }),
    ...votedCuts.map((c, i): Row => ({ date: c.date, t: c.t, el: <Line key={'c' + i} chip={`${c.board} vote`} chipColor="var(--series-cost)" amount={c.amount_as_heard || c.fte_as_heard && `${c.fte_as_heard} FTE` || null} text={`cut: ${c.item}`} who={c.who} board={c.board} board_slug={c.board_slug} date={c.date} video_url={c.video_url} t={c.t} /> })),
    ...votes.map((e, i): Row => ({ date: e.date, t: e.t || 0, el: <Line key={'v' + i} chip={`${e.board} vote`} chipColor="var(--series-cost)" text={`${e.text} — ${e.detail}`} board={e.board} board_slug={e.board_slug} date={e.date} video_url={e.video_url} t={e.t} /> })),
  ].sort((a, b) => a.date.localeCompare(b.date) || a.t - b.t)
  // Tier 3 -- said, proposed, argued; never voted anywhere. The latest figure per thing.
  const said = Object.values(st.latest).filter(x => x.status !== 'voted' && x.status !== 'withdrawn' && !latestVoted[keyOf(x)]).sort((a, b) => b.date.localeCompare(a.date))
  const saidCuts = st.cuts.filter(c => c.status === 'announced' || c.status === 'proposed')
  const gone = st.cuts.filter(c => c.status === 'restored' || c.status === 'withdrawn')
  const finalRows = outcome && outcome.closed ? (outcome.adopted ? 1 : 0) + outcome.questions.filter(q => q.yes != null).length : 0
  const hasFinal = finalRows > 0 || Boolean(finalText)
  return (
    <>
      {/* ---- tier 1: FINAL */}
      <div className="card p-4 mt-6" style={{ borderTop: `4px solid ${hasFinal ? 'var(--status-good)' : 'var(--grid)'}` }}>
        <p className="text-[10px] font-bold uppercase tracking-widest" style={{ color: hasFinal ? 'var(--status-good)' : 'var(--text-muted)' }}>Final</p>
        <p className="text-xs mt-0.5 mb-2" style={{ color: 'var(--text-muted)' }}>What Town Meeting and the ballot did. Money appropriated, or not. A board’s vote is never in this box.</p>
        {finalText && <p className="text-[15px] font-bold pl-3 mb-1" style={{ borderLeft: '2px solid var(--status-good)' }}>{finalText}</p>}
        {outcome && outcome.closed && (
          <ul className="text-[13.5px] space-y-1">
            {outcome.adopted && <li className="pl-3 py-0.5" style={{ borderLeft: '2px solid var(--status-good)' }}><span className="tnum font-bold">${outcome.adopted.amount.toLocaleString('en-US')}</span> — {outcome.adopted.label}<span className="text-xs ml-1.5" style={{ color: 'var(--text-muted)' }}>Annual Town Meeting, {outcome.atm_date ? mmdd(outcome.atm_date) : ''}</span></li>}
            {outcome.questions.filter(q => q.yes != null).map(q => <li key={q.question} className="pl-3 py-0.5" style={{ borderLeft: '2px solid var(--status-good)' }}><span className="tnum font-bold">{q.amount != null ? '$' + q.amount.toLocaleString('en-US') : ''}</span> — {q.type.replace('Proposition 2½ ', '')} <strong style={{ color: q.result === 'FAILED' ? 'var(--status-critical)' : 'var(--status-good)' }}>{q.result.toLowerCase()}</strong>, {q.yes!.toLocaleString('en-US')} to {q.no!.toLocaleString('en-US')}<span className="text-xs ml-1.5" style={{ color: 'var(--text-muted)' }}>{q.election}, {q.date.length > 7 ? mmdd(q.date) : q.date}</span></li>)}
          </ul>
        )}
        {finalNote && <p className="text-xs mt-2" style={{ color: 'var(--text-muted)' }}>{finalNote}</p>}
        {!hasFinal && <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>Nothing is final yet. Town Meeting appropriates the {FY(fy)} budget and the election decides any override; until then everything below is a board’s position or somebody’s proposal.</p>}
      </div>

      {/* ---- tier 2: THE STORY */}
      <div className="card p-4 mt-4" style={{ borderTop: '4px solid var(--series-cost)' }}>
        <p className="text-[10px] font-bold uppercase tracking-widest" style={{ color: 'var(--series-cost)' }}>{closed ? 'How it got there' : 'Where the boards stand, and how they got there'}</p>
        <p className="text-xs mt-0.5 mb-2" style={{ color: 'var(--text-muted)' }}>Every board vote, oldest first. A vote a later vote overwrote is struck through and points at what replaced it. None of this is final.</p>
        {story.length > 0 ? <ul className="text-[13.5px] space-y-1 mt-1">{story.map(r => r.el)}</ul>
          : <p className="text-sm" style={{ color: 'var(--text-muted)' }}>No board has voted on anything yet.</p>}
      </div>

      {/* ---- tier 3: SAID, NEVER VOTED */}
      {(said.length + saidCuts.length + gone.length) > 0 && (
        <div className="card p-4 mt-4" style={{ borderTop: '4px solid var(--grid)' }}>
          <p className="text-[10px] font-bold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>{closed ? 'Said, never voted' : 'Said, not voted — so far'}</p>
          <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>
            {said.length > 0 && `${said.length} figure${said.length === 1 ? '' : 's'} put on the record`}{said.length > 0 && saidCuts.length > 0 ? ', ' : ''}{saidCuts.length > 0 && `${saidCuts.length} cut${saidCuts.length === 1 ? '' : 's'} named`}{gone.length > 0 ? `, ${gone.length} restored or withdrawn` : ''} — proposed, argued, announced at a meeting, and never voted by anyone.{' '}
            <button className="underline" onClick={() => setShowSaid(!showSaid)}>{showSaid ? 'Hide' : 'Show'}</button>
          </p>
          {showSaid && (
            <ul className="text-[13.5px] space-y-1 mt-2" style={{ color: 'var(--text-secondary)' }}>
              {said.map((x, i) => <Line key={'s' + i} amount={x.amount_as_heard} text={`${x.statement} (${plain(x)})`} who={x.who} board={x.board} board_slug={x.board_slug} date={x.date} video_url={x.video_url} t={x.t} />)}
              {saidCuts.length > 0 && <li className="pl-3 py-0.5 mt-2" style={{ borderLeft: '2px solid var(--grid)' }}><strong>{saidCuts.length} cut{saidCuts.length === 1 ? '' : 's'} named, not voted:</strong> {saidCuts.slice(0, 10).map(c => c.item).join('; ')}{saidCuts.length > 10 ? ` … and ${saidCuts.length - 10} more` : ''}</li>}
              {gone.length > 0 && <li className="pl-3 py-0.5" style={{ borderLeft: '2px solid var(--grid)' }}><strong>Restored or withdrawn:</strong> {gone.map(c => c.item).join('; ')}</li>}
            </ul>
          )}
        </div>
      )}
      {story.length + said.length + saidCuts.length === 0 && !closed && <p className="text-sm mt-3" style={{ color: 'var(--text-muted)' }}>Nothing on the record yet. Figures, when they come, are as heard from machine captions; the second in the video is the record.</p>}
    </>
  )
}

/** ONE MEETING, WHAT WAS SAID, VISIBLE. TJ: "i would expect the actual statements and
 *  decisions related to the budget to show up here and not just be a link to the board
 *  page." So the lines are open, not behind a summary: the first eight, then a count. */
function MeetingRow({ m, kinds, official }: { m: { key: string; board: string; board_slug: string; date: string; page: string; entries: Entry[] }; kinds: Record<string, number>; official: boolean }) {
  const [all, setAll] = useState(false)
  const CAP = 8
  const rows = all ? m.entries : m.entries.slice(0, CAP)
  return (
    <div className="card px-4 py-3">
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-0.5">
        <span className="tnum text-[13px] font-semibold">{mmdd(m.date)} {m.date.slice(0, 4)}</span>
        <a className="font-semibold" href={`/boards/${m.board_slug}`} style={{ color: 'var(--series-cost)' }}>{m.board}</a>
        <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
          {official ? `the town’s ${m.entries[0].kind.replace('official ', '')} mentions ${m.entries[0].text}` : Object.entries(kinds).map(([k, n]) => `${n} ${k}${n === 1 ? '' : 's'}`).join(' · ')}
        </span>
        <a className="text-xs underline ml-auto" style={{ color: 'var(--text-muted)' }} href={m.page}>{official ? 'the document' : 'the full minutes'}</a>
      </div>
      {!official && <ul className="mt-2 space-y-1.5 text-[13.5px]">{rows.map((e, i) => (
        <li key={i} className="pl-3" style={{ borderLeft: `2px solid ${e.kind === 'vote' ? 'var(--series-cost)' : 'var(--grid)'}` }}>
          <span className="text-[10px] font-bold uppercase tracking-widest mr-2" style={{ color: e.kind === 'vote' ? 'var(--series-cost)' : 'var(--text-muted)' }}>{e.kind}</span>
          <span>{e.text}</span>
          {e.figures && e.figures.length > 0 && <span className="tnum" style={{ color: 'var(--text-secondary)' }}> — {e.figures.join(', ')} as heard</span>}
          {e.detail && <span style={{ color: 'var(--text-secondary)' }}> — {e.detail}</span>}
          {e.video_url && <a className="underline ml-2 tnum" style={{ color: 'var(--text-muted)' }} href={e.video_url}>{ts(e.t) || 'video'}</a>}
        </li>))}
        {m.entries.length > CAP && <li className="pl-3 text-xs"><button className="underline" onClick={() => setAll(!all)}>{all ? 'show fewer' : `show all ${m.entries.length}`}</button></li>}
      </ul>}
    </div>
  )
}

/** ONE EPISODE, on its own: the card, its figures and decisions, and the meetings inside its
 *  window. Reached from the season dropdown. */
function EpisodePage({ d, e, meetings }: { d: Payload; e: Payload['episodes'][number]; meetings: { key: string; board: string; board_slug: string; date: string; page: string; entries: Entry[] }[] }) {
  const st = e.state
  const decisions = d.entries.filter(x => x.kind === 'vote' && x.date >= e.opens && (!e.closes || x.date <= e.closes))
  return (
    <ReportShell tab={TAB} title={e.label}
      standfirst={`${e.closed ? 'Closed' : 'Under way'} — ${mmdd(e.opens)}${e.closes ? ` to ${mmdd(e.closes)}` : ' onward'}, outside the regular ${FY(Number(e.season_fy))} season. ${e.trigger}.`}
      dataUrl={DATA}>
      <label className="flex items-center gap-2 mt-4 text-sm max-w-full">
        <span style={{ color: 'var(--text-muted)' }}>Season</span>
        <select className="rounded-md px-2 py-1 text-sm min-w-0 max-w-full" style={{ background: 'var(--surface-3)', border: '1px solid var(--grid)' }}
          value={`/budget-feed/${e.id}`} onChange={ev => { window.location.href = ev.target.value }}>
          {d.seasons.map(s => <option key={s.path} value={s.path}>{s.label}</option>)}
        </select>
      </label>
      <Tiers st={st} closed={e.closed} decisions={decisions} fy={Number(e.about_fy || e.season_fy)} finalText={e.outcome || null} finalNote={e.note ? `${e.note}. Sources: ${e.source}.` : null} />
      <H2 id="recent">What was said, meeting by meeting</H2>
      <div className="mt-3 space-y-2">{meetings.map(m => {
        const kinds = m.entries.reduce((acc, x) => { acc[x.kind] = (acc[x.kind] || 0) + 1; return acc }, {} as Record<string, number>)
        return <MeetingRow key={m.key} m={m} kinds={kinds} official={m.entries.length === 1 && m.entries[0].kind.startsWith('official')} />
      })}</div>
      <p className="text-xs mt-8" style={{ color: 'var(--text-muted)' }}>The whole season: <a className="underline" href="/budget-feed">the budget feed</a>. As of {d.as_of}.</p>
    </ReportShell>
  )
}

export function BudgetFeed() {
  const seg = feedSeasonFromPath(window.location.pathname)
  const season = seg && /^fy\d{2}$/.test(seg) ? seg : null
  const episodeId = seg && !season ? seg : null
  const { d, err } = useReport<Payload>(season ? `budget-feed-${season}.json` : 'budget-feed.json')
  const [shown, setShown] = useState(20)
  if (!d) return <ReportShell tab={TAB} title="The budget feed" err={err} loading={!err} dataUrl={DATA} />
  // Group the entries by meeting, newest first.
  const meetings: { key: string; board: string; board_slug: string; date: string; page: string; entries: Entry[] }[] = []
  const byKey = new Map<string, number>()
  for (const e of d.entries) {
    const k = `${e.board_slug}|${e.date}`
    if (!byKey.has(k)) { byKey.set(k, meetings.length); meetings.push({ key: k, board: e.board, board_slug: e.board_slug, date: e.date, page: e.page, entries: [] }) }
    meetings[byKey.get(k)!].entries.push(e)
  }
  const episode = episodeId ? d.episodes.find(e => e.id === episodeId) : null
  if (episodeId && !episode) {
    return <ReportShell tab={TAB} title="No such episode" dataUrl={DATA}><p className="mt-6 text-sm">The address names no budget episode. <a className="underline" href="/budget-feed">The budget feed</a>.</p></ReportShell>
  }
  if (episode) return <EpisodePage d={d} e={episode} meetings={meetings.filter(m => m.date >= episode.opens && (!episode.closes || m.date <= episode.closes))} />
  return (
    <ReportShell tab={TAB} title={season ? `The budget feed, replayed — ${FY(d.cycle_fy)}, as of ${d.as_of}` : `The budget feed — ${FY(d.cycle_fy)}`}
      standfirst={`What the boards are doing to prepare for Town Meeting — the omnibus budget, the school budget above all, and the warrant. Meetings coming up, where the ${FY(d.cycle_fy)} cycle stands, ${season ? 'what was said through the season' : `what was said in the last ${d.recent_days} days`}, what was posted. Not every mention of money: the budget being built, and what will land on the warrant.`}
      dataUrl={season ? `/data/budget-feed-${season}.json` : DATA}>
      {season && <p className="text-[11px] font-semibold uppercase tracking-widest mt-3" style={{ color: 'var(--status-warning)' }}>A replay: what this page would have shown on {d.as_of}, built from the same records. The live feed is at <a className="underline" href="/budget-feed">/budget-feed</a>.</p>}
      {/* THE SEASON. TJ: "budget-feed probably should have a dropdown for each season." The
          list is in the payload -- the live cycle and every replay that has been built. */}
      <label className="flex items-center gap-2 mt-4 text-sm max-w-full">
        <span style={{ color: 'var(--text-muted)' }}>Season</span>
        <select className="rounded-md px-2 py-1 text-sm min-w-0 max-w-full" style={{ background: 'var(--surface-3)', border: '1px solid var(--grid)' }}
          value={(seg ? `/budget-feed/${seg}` : '/budget-feed')}
          onChange={e => { window.location.href = e.target.value }}>
          {d.seasons.map(s => <option key={s.path} value={s.path}>{s.label}</option>)}
        </select>
      </label>
      {/* THE SEASON, FOR A RESIDENT. TJ: "make it so easily digestible. The groupings and
          sections and layout have to be so simple." So: how it landed (if it has); then for
          each episode -- the regular season and any special one -- two lists, DECIDED and
          ON THE TABLE; then what is coming; then what is next on the calendar; then the
          meetings. No status vocabulary anywhere. */}
      {d.episodes.map(e => (
        <section key={e.id} className="mt-8">
          <div className="flex flex-wrap items-baseline gap-x-3">
            <h2 className="text-xl font-bold">{e.kind === 'regular' ? `The ${FY(Number(e.season_fy))} season` : e.label}</h2>
            <span className="text-xs" style={{ color: 'var(--text-muted)' }}>{e.closed ? 'closed' : 'under way'} · {mmdd(e.opens)}{e.closes ? ` → ${mmdd(e.closes)}` : ' →'}{e.kind === 'special' ? <> · <a className="underline" href={`/budget-feed/${e.id}`}>its own page</a></> : null}</span>
          </div>
          {e.kind === 'special' && <p className="text-sm mt-1 max-w-3xl" style={{ color: 'var(--text-secondary)' }}>{e.trigger}.</p>}
          <Tiers st={e.state} closed={e.closed} decisions={d.entries.filter(x => x.kind === 'vote' && x.date >= e.opens && (!e.closes || x.date <= e.closes))} outcome={e.kind === 'regular' ? d.outcome : null} fy={Number(e.about_fy || e.season_fy)}
            finalText={e.kind === 'special' ? (e.outcome || null) : (d.outcome.closed ? d.outcome.headline : null)}
            finalNote={e.kind === 'regular' && d.outcome.closed ? `Annual Town Meeting ${d.outcome.atm_date ? long(d.outcome.atm_date) : ''}; election ${d.outcome.election_date ? long(d.outcome.election_date) : ''}. Tallies from the town’s printed results; the appropriation from the adopted budget.` : null} />
        </section>
      ))}
      {d.episodes.length === 0 && <Tiers st={d.state} closed={d.outcome.closed} decisions={d.entries.filter(x => x.kind === 'vote')} outcome={d.outcome} fy={d.cycle_fy} finalText={d.outcome.closed ? d.outcome.headline : null} />}

      {/* ------------------------------------------------------------------ upcoming */}
      {!season && <H2 id="upcoming">Budget meetings coming up</H2>}
      {season ? null : d.upcoming.length === 0 ? <p className="text-sm mt-2" style={{ color: 'var(--text-secondary)' }}>No posted agenda carries a budget item, as of {d.as_of}.</p> : (
        <ol className="space-y-3 mt-3">{d.upcoming.map(u => (
          <li key={u.board_slug + u.date} className="card p-4">
            <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
              <a className="font-bold" href={u.board_page}>{u.board}</a>
              <span className="text-[13px] font-bold" style={{ color: 'var(--series-cost)' }}>{u.days_away === 0 ? 'Today' : u.days_away === 1 ? 'Tomorrow' : long(u.date)}</span>
              {u.time && <span className="text-xs px-2 py-0.5 rounded" style={{ background: 'var(--surface-3)' }}>{u.time}</span>}
              {u.where && <span className="text-xs px-2 py-0.5 rounded" style={{ background: 'var(--surface-3)' }}>{u.where}</span>}
              <span className="text-xs ml-auto" style={{ color: 'var(--text-muted)' }}>on the agenda: {u.markers.join(', ')}</span>
            </div>
            {u.hook && <p className="text-[14px] mt-1.5">{u.hook}</p>}
            {u.items.length > 0 && <ul className="mt-1.5 text-[13px] space-y-1" style={{ color: 'var(--text-secondary)' }}>{u.items.map((it, i) => <li key={i} style={{ fontWeight: it.important ? 600 : 400 }}>{it.agenda_line}{it.why_it_matters ? <span style={{ color: 'var(--text-muted)' }}> — {it.why_it_matters}</span> : null}</li>)}</ul>}
            <JoinLinks j={u.join} />
            <a className="text-xs underline mt-2 inline-block" style={{ color: 'var(--text-muted)' }} href={u.agenda_url}>the posted agenda</a>
          </li>))}</ol>
      )}

      {/* ------------------------------------------------------------------ calendar */}
      <H2 id="calendar">What’s next — the {FY(d.cycle_fy)} calendar</H2>
      <p className="text-sm mt-1 max-w-3xl" style={{ color: 'var(--text-secondary)' }}>The stages of a budget year in the order they come, each with the window measured off the budget boards’ own agendas over the last five cycles, and this cycle’s dates so far.</p>
      <div className="grid gap-3 mt-4 sm:grid-cols-2 lg:grid-cols-3">{d.calendar.map(s => (
        <div key={s.key} className="card p-4" style={{ borderLeft: `3px solid ${STATUS[s.status][1]}` }}>
          <p className="text-[10px] font-bold uppercase tracking-widest" style={{ color: STATUS[s.status][1] }}>{STATUS[s.status][0]}</p>
          <p className="text-[15px] font-bold mt-1">{s.stage}</p>
          <p className="text-sm tnum mt-1">typically {s.typical_first} → {s.typical_last}</p>
          <ul className="text-xs mt-2 space-y-1" style={{ color: 'var(--text-secondary)' }}>{s.windows.map(w => (
            <li key={w.board_slug}><a className="underline" href={`/boards/${w.board_slug}#calendar`}>{w.board}</a>: {w.typical_first} → {w.typical_last}{w.this_cycle.length ? <span style={{ color: 'var(--text-primary)' }}> · this cycle {w.this_cycle.map(mmdd).join(', ')}</span> : ''}</li>))}</ul>
        </div>))}</div>
      <p className="text-xs mt-2 max-w-3xl" style={{ color: 'var(--text-muted)' }}>A cycle runs July to June and is named for the budget it builds. “Typically” is the median first and last date the subject appeared on that board’s agenda; the raw dates per cycle are on each board’s page.</p>

      {/* -------------------------------------------------------------------- recent */}
      <H2 id="recent">Meeting by meeting, newest first</H2>
      <p className="text-sm mt-1 max-w-3xl" style={{ color: 'var(--text-secondary)' }}>One row per meeting; open it for what was said, each line linked to the second in the video. From our minutes where we have them, and from the town’s agendas and minutes where we do not.</p>
      <div className="mt-3 space-y-2">{meetings.slice(0, shown).map(m => {
        const kinds = m.entries.reduce((acc, e) => { acc[e.kind] = (acc[e.kind] || 0) + 1; return acc }, {} as Record<string, number>)
        const official = m.entries.length === 1 && m.entries[0].kind.startsWith('official')
        return (
          <MeetingRow key={m.key} m={m} kinds={kinds} official={official} />
        )
      })}</div>
      {meetings.length > shown && <button className="underline text-sm mt-3" onClick={() => setShown(shown + 20)}>show {Math.min(20, meetings.length - shown)} more of {meetings.length - shown}</button>}

      {/* --------------------------------------------------------------- documents */}
      {(d.notices.length > 0 || d.documents.length > 0) && (
        <>
          <H2 id="posted">Posted about the budget and Town Meeting</H2>
          <ul className="mt-3 space-y-1.5 text-sm">
            {d.notices.map((n, i) => <li key={'n' + i}><span className="tnum text-xs mr-2" style={{ color: 'var(--text-muted)' }}>{mmdd(n.published || n.first_seen)}</span><a className="underline" href={n.link}>{n.title}</a> <span className="text-xs" style={{ color: 'var(--text-muted)' }}>— {n.source}</span></li>)}
            {d.documents.map((x, i) => <li key={'d' + i}><span className="tnum text-xs mr-2" style={{ color: 'var(--text-muted)' }}>{mmdd(x.first_seen)}</span><a className="underline" href={x.url}>{x.title}</a> <span className="text-xs" style={{ color: 'var(--text-muted)' }}>— {x.source}</span></li>)}
          </ul>
        </>
      )}
      <p className="text-xs mt-8" style={{ color: 'var(--text-muted)' }}>Rebuilt every morning by the refresh. As of {d.as_of}.</p>
    </ReportShell>
  )
}

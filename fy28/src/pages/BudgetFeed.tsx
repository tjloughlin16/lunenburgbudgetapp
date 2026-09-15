import { useState, type ReactElement } from 'react'
import { feedSeasonFromPath, type Tab } from '../routes'
import { H2, ReportShell, useReport } from '../components/report'
import { JoinLinks, dayLabel, todayIso, type Join } from '../components/BoardsThisWeek'
import { SeasonBoard } from './SeasonBoard'

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
type Entry = { kind: string; board: string; board_slug: string; date: string; page: string; thread?: string; text?: string | null; detail?: string | null; tags?: string[]; figures?: string[]; markers?: string[]; t?: number | null; video_url?: string; minutes?: number }
type Statement = { board: string; board_slug: string; date: string; page: string; thread?: string; kind: string; scope: string; fiscal_year: number | null; amount_as_heard: string | null; statement: string; who: string; status: string; t: number; video_url: string }
type Cut = { board: string; board_slug: string; date: string; page: string; thread?: string; item: string; scope: string; fiscal_year: number | null; amount_as_heard: string | null; fte_as_heard: string | null; status: string; who: string; t: number; video_url: string; key: string }
type Warning = { board: string; board_slug: string; date: string; page: string; thread?: string; prediction: string; about: string; condition: string | null; scope: string; fiscal_year: number | null; who: string; t: number; video_url: string }
type CutGroup = { item: string; scope: string; status: string; mentions: number; first: string; last: string; who: string; utterance: boolean; thread?: string; voted: boolean; amount_as_heard: string | null; fte_as_heard: string | null; fte: number | null; kind: 'position' | 'program' | 'expense'; family: string | null; aftermath?: boolean; adopted?: boolean }
type State = { meetings_read: number; warnings?: Warning[]; cut_groups?: CutGroup[]; first_date: string | null; last_date: string | null; latest: Record<string, Statement>; history: Record<string, Statement[]>; cuts: Cut[]; live_cuts: number; live_by_scope: Record<string, number>; log: { board: string; board_slug: string; date: string; page: string; added: string[]; changed: { item: string; was: string; now: string }[]; n_added: number; n_changed: number }[] }
type Payload = {
  about: string; as_of: string; cycle_fy: number; cycle_opens: string; cycle_closes: string; recent_days: number; state: State; seasons: { fy: number; path: string; label: string; live: boolean }[]
  answers: { question: string; label: string; answer: string; status: string; link?: string | null; basis?: string | null }[]
  episodes: { id: string; season_fy: string; kind: 'regular' | 'special'; label: string; opens: string; closes: string; about_fy: string; trigger: string; outcome: string; source: string; note: string; closed: boolean; state: State; answers: { label: string; answer: string; status: string; link?: string | null }[] | null }[]
  outcome: { closed: boolean; atm_date: string | null; election_date: string | null; headline: string; adopted: { amount: number; label: string; source: string } | null; questions: { date: string; election: string; question: string; type: string; amount: number | null; purpose: string; yes: number | null; no: number | null; total: number | null; registered: number | null; turnout_pct: number | null; result: string }[] }
  upcoming: Upcoming[]; calendar: Stage[]; entries: Entry[]
  threads: { id: string; label: string; question: string; order: number; note: string }[]
  proposed_threads: { name: string; rows: number; meetings: number; first: string; last: string }[]
  documents: { first_seen: string; source: string; title: string; url: string }[]
  notices: { first_seen: string; source: string; published: string; title: string; link: string }[]
  counts: { upcoming: number; entries: number; boards: number; by_board: Record<string, number>; kinds: Record<string, number> }
}

const mmdd = (d: string) => new Date(d + 'T12:00:00').toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
const mmddyy = (d: string) => new Date(d + 'T12:00:00').toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: '2-digit' }).replace(', ', ' ’')
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
/** Every dollar figure in a string, as a number: "$2,400,000", "$3.3 million", "1.6 million dollars", "$418k". */
function amounts(text: string): number[] {
  const out: number[] = []
  const rx = /\$?\s?(\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)\s*(million|m\b|k\b|thousand)?/gi
  let m: RegExpExecArray | null
  while ((m = rx.exec(text))) {
    const n = parseFloat(m[1].replace(/,/g, ''))
    const u = (m[2] || '').toLowerCase()
    const v = u.startsWith('m') ? n * 1e6 : u ? n * 1e3 : n
    if (v >= 1000 && (m[0].includes('$') || u || m[1].includes(','))) out.push(v)
  }
  return out
}
function Line({ amount, text, who, board, board_slug, date, video_url, t, muted, quiet, chip, chipColor, after, landing }: { amount?: string | null; text: string; who?: string; board: string; board_slug: string; date: string; video_url?: string; t?: number | null; muted?: boolean; quiet?: boolean; chip?: string; chipColor?: string; after?: string; landing?: boolean }) {
  return (
    <li className="pl-3 py-0.5" style={{ borderLeft: `${landing ? '4px' : '2px'} solid ${landing ? 'var(--status-good)' : muted || quiet ? 'var(--grid)' : (chipColor || 'var(--grid)')}`, color: muted ? 'var(--text-muted)' : quiet ? 'var(--text-secondary)' : undefined, background: landing ? 'color-mix(in srgb, var(--status-good) 8%, transparent)' : undefined }}>
      {landing && <span className="text-[10px] font-bold uppercase tracking-wider mr-1.5" style={{ color: 'var(--status-good)' }} title="Carries the figure Town Meeting or the ballot ended on">✓ made it final ·</span>}
      {chip && <><a className="text-[10px] font-bold uppercase tracking-wider" href={`/boards/${board_slug}`} style={{ color: muted ? 'var(--text-muted)' : chipColor }}>{chip}</a><span className="text-[10px] font-bold uppercase tracking-wider tnum mr-1.5" style={{ color: 'var(--text-muted)' }}> · {quiet ? `${board}, ` : ''}{mmdd(date)}</span></>}
      {amount && <span className="tnum font-bold" style={{ textDecoration: muted ? 'line-through' : undefined }}>{amount}</span>}{amount ? ' — ' : ''}{text}
      <span className="text-xs ml-1.5" style={{ color: 'var(--text-muted)' }}>{who ? `${who}, ` : ''}{chip ? null : <><a className="underline" href={`/boards/${board_slug}`}>{board}</a>, {mmdd(date)}</>}{video_url ? <>{chip ? '' : ' · '}<a className="underline tnum" href={video_url}>{ts(t) || 'video'}</a></> : null}</span>
      {after && <span className="text-xs ml-1.5 italic" style={{ color: 'var(--text-muted)' }}>{after}</span>}
    </li>
  )
}

/** One thread, folded: its rows newest first, capped, the vote that made it final marked. */
function Thread({ th }: { th: { id: string; label: string; question: string; rows: { date: string; render: (landing: boolean) => ReactElement }[]; votes: number; landingAt: number; landed: (string | null)[] } }) {
  const [all, setAll] = useState(false)
  const CAP = 30
  const rows = all ? th.rows : th.rows.slice(0, CAP)
  return (
    <details className="mt-2">
      <summary className="cursor-pointer text-sm font-bold flex flex-wrap items-baseline gap-x-2"><span className="conc-chev inline-block transition-transform text-xs" aria-hidden="true" style={{ color: 'var(--text-muted)' }}>&#9656;</span>{th.label}<span className="text-xs font-normal" style={{ color: 'var(--text-muted)' }}>{th.rows.length} line{th.rows.length === 1 ? '' : 's'}, {th.votes} vote{th.votes === 1 ? '' : 's'}{th.landed.length > 0 ? ` · voted to ${th.landed.join(', ')}` : ''}{th.rows.length > 0 ? ` · ${mmdd(th.rows[th.rows.length - 1].date)} → ${mmdd(th.rows[0].date)}` : ''}</span>{th.landingAt >= 0 && <span className="text-[10px] font-bold uppercase tracking-wider" style={{ color: 'var(--status-good)' }}>✓ made final {mmdd(th.rows[th.landingAt].date)}</span>}</summary>
      {th.question && <p className="text-xs mt-1 pl-3" style={{ color: 'var(--text-muted)' }}>{th.question}</p>}
      <ul className="text-[13.5px] space-y-1 mt-1">{rows.map((r, i) => r.render(i === th.landingAt))}</ul>
      {th.rows.length > CAP && !all && <button className="text-xs underline mt-1 pl-3" style={{ color: 'var(--series-cost)' }} onClick={() => setAll(true)}>all {th.rows.length} lines</button>}
    </details>
  )
}

/** THE METRICS, under the season label. TJ, 14 September 2026: "I can't find where we
 *  list metrics like the total school deficit, total school cuts. I expect them to be
 *  right under the FY27 season label." One card per figure: the number, what it is, who
 *  last put it on the record and with what standing. Rule 7b: a metric and two lines.
 *  Staff outrank the chair, who outranks a member, who outranks a resident -- so the
 *  latest figure is the latest STAFF figure where staff gave one, and the card says so. */
function Metrics({ st, outcome }: { st: State; outcome?: Payload['outcome'] | null }) {
  const first = (k: string) => { const h = st.history[k] || []; return h.length ? h[h.length - 1] : null }
  const cards: { label: string; value: string; line: string; foot: string }[] = []
  for (const [scope, label] of [['school', 'School gap'], ['town', 'Town gap']] as const) {
    const x = st.latest[`${scope}/deficit`]
    if (!x) continue
    const f = first(`${scope}/deficit`)
    cards.push({ label, value: x.amount_as_heard || '—', line: `${x.status === 'voted' ? 'a board vote' : x.status === 'announced' ? 'stated, not voted' : 'proposed, not voted'} — ${x.who}, ${mmdd(x.date)}`, foot: f && f !== x && f.amount_as_heard ? `first put at ${f.amount_as_heard} (${mmdd(f.date)})` : '' })
  }
  // A closed season's override is what reached the ballot, tier by tier -- TJ: "for FY27 we
  // need to list the fact that there were two override tiers." A live season's is the asks.
  const qs = outcome && outcome.closed ? outcome.questions.filter(q => q.amount != null) : []
  if (qs.length) {
    const tier = (q: typeof qs[number]) => (q.purpose.match(/tier\s*(\d)/i) || [])[0] || q.question.replace(/\.\s*OVERRIDE.*$/i, '')
    cards.push({ label: qs.length > 1 ? `The override — ${qs.length} tiers on the ballot` : 'The override on the ballot', value: qs.map(q => '$' + q.amount!.toLocaleString('en-US')).join(' / '),
      line: qs.map(q => `${tier(q)}: $${q.amount!.toLocaleString('en-US')}${q.purpose.match(/\((.*?)\)/) ? ` (${q.purpose.match(/\((.*?)\)/)![1]})` : ''} — ${q.result.toLowerCase()}${q.yes != null ? `, ${q.yes.toLocaleString('en-US')} to ${q.no!.toLocaleString('en-US')}` : ''}`).join(' · '),
      foot: `${qs[0].election}, ${qs[0].date.length > 7 ? mmdd(qs[0].date) : qs[0].date}; tallies from the town’s printed results` })
  }
  for (const [scope, label] of (qs.length ? [] : [['school', 'School override ask'], ['town', 'Town override ask'], ['both', 'Override, town and schools']]) as ReadonlyArray<readonly [string, string]>) {
    const x = st.latest[`${scope}/override`]
    if (!x || (amounts(x.amount_as_heard || '')[0] || 0) < 100_000) continue   // an override is a sum; '$56.95 added to the tax bill' is its impact
    cards.push({ label, value: x.amount_as_heard || '—', line: `${x.status === 'voted' ? 'a board vote' : x.status === 'announced' ? 'stated, not voted' : 'proposed, not voted'} — ${x.who}, ${mmdd(x.date)}`, foot: '' })
  }
  // Cuts are counted as GROUPS -- the same cut said three ways is one cut -- and a cut named
  // only by residents is counted apart. cut_groups() in build_budget_feed.py.
  for (const [scope, label] of [['school', 'School cuts'], ['town', 'Town cuts']] as const) {
    const gs = (st.cut_groups || []).filter(g => g.scope === scope)
    const cs = gs.filter(g => !g.utterance), said = gs.length - cs.length
    if (!cs.length) continue
    // TJ: "when people hear 'cuts' they think FTEs." So positions first, with the FTE where
    // it was said, then programs, then expense lines -- never one undifferentiated count.
    const live = cs.filter(g => g.status !== 'restored' && g.status !== 'withdrawn')
    const pos = live.filter(g => g.kind === 'position'), prog = live.filter(g => g.kind === 'program'), exp = live.filter(g => g.kind === 'expense')
    // THE FTE IS SUMMED ONLY OVER WHAT WAS VOTED. TJ, on a card that said 19.5 FTE: "how did
    // you get 19.5 FTE cuts for the school?" It was every FTE named across four scenarios --
    // the same two primary teachers as '2.0 classroom teachers' in March and as '1st grade
    // teacher' + '2nd grade teacher' a week later. Scenarios are alternatives; their FTEs do
    // not add. One vote's list does.
    const votedPos = pos.filter(g => g.voted || g.adopted)
    const fteVoted = votedPos.reduce((a, g) => a + (g.fte || 0), 0)
    const voted = live.filter(g => g.voted).length, gone = cs.length - live.length
    const fams: string[] = []
    for (const g of [...prog].sort((a, b) => Number(b.voted) - Number(a.voted))) if (g.family && !fams.includes(g.family)) fams.push(g.family)
    const fmt = (f: number) => (f % 1 ? f.toFixed(1) : String(f))
    // No FTE sum here. TJ, 14 September: "I can't reconcile '8 positions (3 FTE)' and '11.5
    // FTE voted'" -- both were sums over caption-extracted groups, and the same season had
    // produced 19.5, 8.5, 11.5 and 3. The FTE for a season comes from the district's own
    // line-item budget and slides, recorded in sources/data/budget-seasons/<fy>.csv.
    void fteVoted; void fmt
    cards.push({ label, value: votedPos.length ? `${votedPos.length} position${votedPos.length === 1 ? '' : 's'} voted` : `${pos.length} position${pos.length === 1 ? '' : 's'} named`,
      line: [`${pos.length} position${pos.length === 1 ? '' : 's'} named across the scenarios (alternatives — not added up)`, exp.length ? `${exp.length} expense line${exp.length === 1 ? '' : 's'}` : '', fams.length ? `programs: ${fams.join(', ')}` : ''].filter(Boolean).join(' · '),
      foot: `${voted} voted, ${live.length - voted} not voted${gone ? `, ${gone} restored or withdrawn` : ''}${said ? ` · ${said} more named only by residents` : ''}` })
  }
  const warns = st.warnings || []
  if (warns.length) cards.push({ label: 'Early warnings', value: `${warns.length} on the record`, line: `predictions and threats with no figure yet — latest ${mmdd(warns[0].date)}: ${warns[0].about}`, foot: '' })
  if (!cards.length) return null
  return (
    <div className="grid gap-3 mt-4 sm:grid-cols-2 lg:grid-cols-3">
      {cards.map(c => (
        <div key={c.label} className="card px-3 py-2.5">
          <p className="text-[10px] font-bold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>{c.label}</p>
          <p className="text-xl font-bold tnum leading-tight mt-0.5">{c.value}</p>
          <p className="text-xs mt-1" style={{ color: 'var(--text-secondary)' }}>{c.line}</p>
          {c.foot && <p className="text-xs" style={{ color: 'var(--text-muted)' }}>{c.foot}</p>}
        </div>
      ))}
      <p className="text-[11px] sm:col-span-2 lg:col-span-3" style={{ color: 'var(--text-muted)' }}>Figures as heard from machine captions; the second in the video is the record. A stated figure is what somebody said, with their standing; it is not a vote and it is not final.</p>
    </div>
  )
}

/** WHAT WAS ACTUALLY CUT, AND WHAT WAS SAVED. TJ, 14 September 2026: "in the final
 *  section we need to list the actual cuts across all categories, like FTEs, expenses.
 *  WHAT was cut as the result? What was saved (if anything)?" The outcome decides which
 *  list applies: with an override failed, the cuts a board voted for the no-override
 *  budget stand; with one passed, they are avoided. A cut voted and later restored is
 *  what was saved. Rule 7: this is what the boards voted read against what the ballot
 *  did -- the town publishes no list of its own -- and the card says so. */
function FinalCuts({ st, outcome }: { st: State; outcome?: Payload['outcome'] | null }) {
  const gs = (st.cut_groups || []).filter(g => !g.utterance)
  // What stands: voted as a cut and not restored -- or, TJ: "middle school sports WERE
  // CUT" -- named by the district or a board in the sixty days after the ballot as the
  // no-override budget was adopted (aftermath), with nothing restoring it.
  const stands = gs.filter(g => (g.voted || g.adopted) && g.status !== 'restored' && g.status !== 'withdrawn')
  const afterN = stands.filter(g => g.adopted && !g.voted).length
  // SAVED means voted as a cut and later restored. TJ: middle school sports 'was cut then
  // saved -- but that happened in a different scenario, so that's not fair to say.' A cut
  // that was only ever floated in a scenario and dropped was never cut.
  const saved = gs.filter(g => g.voted && g.status === 'restored')
  if (!stands.length && !saved.length) return null
  const qs = outcome && outcome.closed ? outcome.questions : []
  const failed = qs.length > 0 && qs.every(q => q.result === 'FAILED'), passed = qs.length > 0 && qs.some(q => q.result !== 'FAILED')
  const name = (g: CutGroup) => g.item.replace(/\s*\(.*?\)\s*/g, ' ').trim()
  const Block = ({ title, xs, color }: { title: string; xs: CutGroup[]; color: string }) => {
    const by = (scope: string, kind: string) => xs.filter(g => g.scope === scope && g.kind === kind)
    return (
      <div className="mt-3">
        <p className="text-xs font-bold uppercase tracking-wider" style={{ color }}>{title}</p>
        {(['school', 'town'] as const).map(scope => {
          const pos = by(scope, 'position'), prog = by(scope, 'program'), exp = by(scope, 'expense')
          if (!pos.length && !prog.length && !exp.length) return null
          return (
            <div key={scope} className="text-[13px] mt-1.5 pl-3" style={{ borderLeft: `2px solid ${color}` }}>
              <p className="font-semibold">{SCOPE[scope]}: {[pos.length ? `${pos.length} position${pos.length === 1 ? '' : 's'}` : '', prog.length ? `${prog.length} program${prog.length === 1 ? '' : 's'}` : '', exp.length ? `${exp.length} expense line${exp.length === 1 ? '' : 's'}` : ''].filter(Boolean).join(' · ')}</p>
              {pos.length > 0 && <p style={{ color: 'var(--text-secondary)' }}><span className="text-[10px] font-bold uppercase tracking-wider mr-1" style={{ color: 'var(--text-muted)' }}>positions</span>{pos.map(g => `${name(g)}${g.fte ? ` (${g.fte} FTE)` : g.fte_as_heard ? ` (${g.fte_as_heard})` : ''}`).join('; ')}</p>}
              {prog.length > 0 && <p style={{ color: 'var(--text-secondary)' }}><span className="text-[10px] font-bold uppercase tracking-wider mr-1" style={{ color: 'var(--text-muted)' }}>programs</span>{prog.map(g => `${name(g)}${g.amount_as_heard ? ` (${g.amount_as_heard})` : ''}`).join('; ')}</p>}
              {exp.length > 0 && <p style={{ color: 'var(--text-secondary)' }}><span className="text-[10px] font-bold uppercase tracking-wider mr-1" style={{ color: 'var(--text-muted)' }}>expense lines</span>{exp.map(g => `${name(g)}${g.amount_as_heard ? ` (${g.amount_as_heard})` : ''}`).join('; ')}</p>}
            </div>
          )
        })}
      </div>
    )
  }
  return (
    <div className="mt-3 pt-3" style={{ borderTop: '1px solid var(--grid)' }}>
      <p className="text-sm font-bold">What that meant for the cuts</p>
      <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>
        {failed ? 'With the override failed, the cuts a board voted for the no-override budget stand. ' : passed ? 'With the override passed, the cuts voted for the no-override budget were avoided. ' : 'The cuts the boards voted stand. '}
        Read from the boards’ votes against the ballot{afterN ? `, and from the ${afterN} cut${afterN === 1 ? '' : 's'} the district named in the sixty days after it as the budget was adopted` : ''}; the town publishes no list of its own. Figures and FTEs as heard.
      </p>
      {stands.length > 0 && <Block title={passed ? 'Cuts avoided' : 'Cut'} xs={stands} color={passed ? 'var(--status-good)' : 'var(--status-critical)'} />}
      {saved.length > 0 && <Block title="Saved — voted as a cut, then restored" xs={saved} color="var(--status-good)" />}
    </div>
  )
}

function Tiers({ st, closed, decisions, outcome, finalText, finalNote, fy, meta }: { st: State; closed: boolean; decisions: Entry[]; outcome?: Payload['outcome'] | null; finalText?: string | null; finalNote?: string | null; fy: number; meta: Payload['threads'] }) {
  const all = Object.values(st.history).flat()
  // A voted gap or override that a later vote on the same thing replaced is greyed,
  // struck, and points at what replaced it. Only those two are ONE thing per scope: a
  // 'budget total' is many things -- the omnibus, the capital plan, a sewer fund article.
  const ONE_THING = new Set(['deficit', 'override'])
  const latestVoted: Record<string, Statement> = {}
  for (const x of all) if (x.status === 'voted' && ONE_THING.has(x.kind) && (!latestVoted[keyOf(x)] || latestVoted[keyOf(x)].date <= x.date)) latestVoted[keyOf(x)] = x
  const votes = decisions.filter(e => (e.detail || '').toLowerCase().startsWith('pass'))
  // THE THREADS. TJ: "there are a few 'balls' that get moved forward in these seasons --
  // warrant articles, deficit numbers, cuts... I would like to see the story of the warrant
  // articles; the story of the cuts, 'how did we land on cutting athletics'; the deficit
  // numbers, 'how did we land on $2.5m?!'" And then: "'the gap' doesn't explain anything
  // about how the deficit was discussed and identified, nor does the event list include
  // any PROPOSED CUTS early on. The story needs to tell why." So a thread carries the WHOLE
  // record about its thing -- every figure stated, every cut proposed, every vote -- newest
  // first. A vote is the strong line; what was said is the reason it happened.
  type Row = { date: string; t: number; thread: string; vote: boolean; nums: number[]; render: (landing: boolean) => ReactElement }
  // THE VOTE THAT MADE IT FINAL. TJ: "when something landed it into 'final' state, call
  // that out in this flow too -- that was the vote that made it final." The latest VOTE in
  // a thread whose figure is one Town Meeting or the ballot ended on. A figure match, not a
  // reading of the motion: the page says "carries the figure it ended on".
  const finals = [
    ...(outcome && outcome.closed ? [outcome.adopted?.amount, ...outcome.questions.map(q => q.amount)] : []),
    ...amounts(finalText || ''),
  ].filter((n): n is number => typeof n === 'number' && n > 0)
  const carriesFinal = (nums: number[]) => nums.some(n => finals.some(f => Math.abs(n - f) / f < 0.005))
  const saidChip = (status: string, who: string) => `${status === 'announced' ? 'stated' : status} · ${who}`
  const story: Row[] = [
    ...all.map((x, i): Row => {
      const voted = x.status === 'voted'
      const later = latestVoted[keyOf(x)]
      const superseded = voted && Boolean(later) && later !== x && later.date > x.date
      return { date: x.date, t: x.t, thread: x.thread || 'other', vote: voted, nums: amounts(x.amount_as_heard || ''), render: landing => <Line key={'s' + i} chip={voted ? `${x.board} vote` : saidChip(x.status, x.who)} chipColor={voted ? 'var(--series-cost)' : 'var(--text-muted)'} quiet={!voted} muted={(superseded || x.status === 'withdrawn') && !landing} landing={landing} amount={x.amount_as_heard} text={`${x.statement} (${plain(x)})`} board={x.board} board_slug={x.board_slug} date={x.date} video_url={x.video_url} t={x.t} after={superseded && !landing ? `overwritten ${mmdd(later.date)}${later.amount_as_heard ? ` → ${later.amount_as_heard}` : ''}` : undefined} /> }
    }),
    ...st.cuts.map((c, i): Row => {
      const voted = c.status === 'voted', gone = c.status === 'restored' || c.status === 'withdrawn'
      return { date: c.date, t: c.t, thread: c.thread || 'other', vote: voted, nums: voted ? amounts(c.amount_as_heard || '') : [], render: landing => <Line key={'c' + i} chip={voted ? `${c.board} vote` : gone ? `${c.status} · ${c.who}` : (c as Cut & { aftermath?: boolean }).aftermath ? `after the ballot · ${c.who}` : `proposed cut · ${c.who}`} chipColor={voted ? 'var(--series-cost)' : 'var(--text-muted)'} quiet={!voted} muted={gone} landing={landing} amount={c.amount_as_heard || c.fte_as_heard && `${c.fte_as_heard} FTE` || null} text={`${gone ? c.status + ': ' : 'cut: '}${c.item}`} board={c.board} board_slug={c.board_slug} date={c.date} video_url={c.video_url} t={c.t} /> }
    }),
    ...(st.warnings || []).map((w, i): Row => ({ date: w.date, t: w.t, thread: w.thread || 'other', vote: false, nums: [], render: () => <Line key={'w' + i} chip={`warned · ${w.who}`} chipColor="var(--status-warning)" quiet text={`${w.prediction}${w.condition ? ` — ${w.condition}` : ''} (${SCOPE[w.scope] || w.scope}: ${w.about})`} board={w.board} board_slug={w.board_slug} date={w.date} video_url={w.video_url} t={w.t} /> })),
    ...votes.map((e, i): Row => ({ date: e.date, t: e.t || 0, thread: e.thread || 'other', vote: true, nums: amounts(e.text || ''), render: landing => <Line key={'v' + i} chip={`${e.board} vote`} chipColor="var(--series-cost)" landing={landing} text={`${e.text} — ${e.detail}`} board={e.board} board_slug={e.board_slug} date={e.date} video_url={e.video_url} t={e.t} /> })),
  ].sort((a, b) => b.date.localeCompare(a.date) || b.t - a.t)   // newest first, TJ, 14 September
  const threads = meta.filter(th => story.some(r => r.thread === th.id)).map(th => {
    const rows = story.filter(r => r.thread === th.id)
    const landingAt = rows.findIndex(r => r.vote && carriesFinal(r.nums))   // newest first: the first hit is the latest such vote
    return { ...th, rows, votes: rows.filter(r => r.vote).length, landingAt, landed: Object.values(latestVoted).filter(x => x.thread === th.id).map(x => x.amount_as_heard).filter(Boolean) }
  })
  const finalRows = outcome && outcome.closed ? (outcome.adopted ? 1 : 0) + outcome.questions.filter(q => q.yes != null).length : 0
  const hasFinal = finalRows > 0 || Boolean(finalText)
  return (
    <>
      <Metrics st={st} outcome={outcome} />

      {/* ---- tier 1: FINAL */}
      <div className="card p-4 mt-4" style={{ borderTop: `4px solid ${hasFinal ? 'var(--status-good)' : 'var(--grid)'}` }}>
        <p className="text-[10px] font-bold uppercase tracking-widest" style={{ color: hasFinal ? 'var(--status-good)' : 'var(--text-muted)' }}>Final</p>
        <p className="text-xs mt-0.5 mb-2" style={{ color: 'var(--text-muted)' }}>What Town Meeting and the ballot did. Money appropriated, or not. A board’s vote is never in this box.</p>
        {finalText && <p className="text-[15px] font-bold pl-3 mb-1" style={{ borderLeft: '2px solid var(--status-good)' }}>{finalText}</p>}
        {outcome && outcome.closed && (
          <ul className="text-[13.5px] space-y-1">
            {outcome.adopted && <li className="pl-3 py-0.5" style={{ borderLeft: '2px solid var(--status-good)' }}><span className="tnum font-bold">${outcome.adopted.amount.toLocaleString('en-US')}</span> — {outcome.adopted.label}<span className="text-xs ml-1.5" style={{ color: 'var(--text-muted)' }}>Annual Town Meeting, {outcome.atm_date ? mmdd(outcome.atm_date) : ''}</span></li>}
            {outcome.questions.filter(q => q.yes != null).map(q => <li key={q.question} className="pl-3 py-0.5" style={{ borderLeft: '2px solid var(--status-good)' }}><span className="tnum font-bold">{q.amount != null ? '$' + q.amount.toLocaleString('en-US') : ''}</span> — {q.type.replace('Proposition 2½ ', '')} <strong style={{ color: q.result === 'FAILED' ? 'var(--status-critical)' : 'var(--status-good)' }}>{q.result.toLowerCase()}</strong>, {q.yes!.toLocaleString('en-US')} to {q.no!.toLocaleString('en-US')}<span className="text-xs ml-1.5" style={{ color: 'var(--text-muted)' }}>{q.election}, {q.date.length > 7 ? mmdd(q.date) : q.date}</span></li>)}
          </ul>
        )}
        {hasFinal && <FinalCuts st={st} outcome={outcome} />}
        {finalNote && <p className="text-xs mt-2" style={{ color: 'var(--text-muted)' }}>{finalNote}</p>}
        {!hasFinal && <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>Nothing is final yet. Town Meeting appropriates the {FY(fy)} budget and the election decides any override; until then everything below is a board’s position or somebody’s proposal.</p>}
      </div>

      {/* ---- tier 2 and 3 together: THE STORY, one thread per thing, votes strong and what was said as the why */}
      <div className="card p-4 mt-4" style={{ borderTop: '4px solid var(--series-cost)' }}>
        <p className="text-[10px] font-bold uppercase tracking-widest" style={{ color: 'var(--series-cost)' }}>{closed ? 'How it got there' : 'Where it stands, and how it got there'}</p>
        <p className="text-xs mt-0.5 mb-2" style={{ color: 'var(--text-muted)' }}>One story per thing the year’s planning moves forward, newest first. <span style={{ color: 'var(--series-cost)' }}>A board vote</span> is the strong line; what was stated or proposed, by whom, is the reason it happened; <span style={{ color: 'var(--status-warning)' }}>a warning</span> is preliminary language — a prediction with no figure yet. A vote a later vote overwrote is struck through. None of this is final.</p>
        {story.length > 0 ? threads.map(th => <Thread key={th.id} th={th} />)
          : <p className="text-sm" style={{ color: 'var(--text-muted)' }}>Nothing on the record yet. Figures, when they come, are as heard from machine captions; the second in the video is the record.</p>}
      </div>
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
      standfirst={`${e.closed ? 'Closed' : 'Under way'} — ${mmdd(e.opens)}${e.closes ? ` to ${mmdd(e.closes)}` : ' onward'}, outside the regular ${FY(Number(e.season_fy))} planning. ${e.trigger}.`}
      dataUrl={DATA}>
      <label className="flex items-center gap-2 mt-4 text-sm max-w-full">
        <span style={{ color: 'var(--text-muted)' }}>Budget year</span>
        <select className="rounded-md px-2 py-1 text-sm min-w-0 max-w-full" style={{ background: 'var(--surface-3)', border: '1px solid var(--grid)' }}
          value={`/budget-feed/${e.id}`} onChange={ev => { window.location.href = ev.target.value }}>
          {d.seasons.map(s => <option key={s.path} value={s.path}>{s.label}</option>)}
        </select>
      </label>
      <SeasonBoard fy={Number(e.about_fy || e.season_fy)} id={e.id} fallback={<Tiers st={st} closed={e.closed} decisions={decisions} meta={d.threads} fy={Number(e.about_fy || e.season_fy)} finalText={e.outcome || null} finalNote={e.note ? `${e.note}. Sources: ${e.source}.` : null} />} />
      <H2 id="recent">What was said, meeting by meeting</H2>
      <div className="mt-3 space-y-2">{meetings.map(m => {
        const kinds = m.entries.reduce((acc, x) => { acc[x.kind] = (acc[x.kind] || 0) + 1; return acc }, {} as Record<string, number>)
        return <MeetingRow key={m.key} m={m} kinds={kinds} official={m.entries.length === 1 && m.entries[0].kind.startsWith('official')} />
      })}</div>
      <p className="text-xs mt-8" style={{ color: 'var(--text-muted)' }}>The whole year’s planning: <a className="underline" href="/budget-feed">the budget feed</a>. As of {d.as_of}.</p>
    </ReportShell>
  )
}

export function BudgetFeed() {
  const seg = feedSeasonFromPath(window.location.pathname)
  const season = seg && /^fy\d{2}$/.test(seg) ? seg : null
  const episodeId = seg && !season ? seg : null
  const { d, err } = useReport<Payload>(season ? `budget-feed-${season}.json` : 'budget-feed.json')
  const [hasBoard, setHasBoard] = useState(false)
  const [recentOpen, setRecentOpen] = useState(false)   // a season file renders the board; the agenda-window calendar then has nothing to add
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
    <ReportShell tab={TAB} title={season ? `${FY(d.cycle_fy)} budget planning` : `The budget feed — ${FY(d.cycle_fy)}`}
      standfirst={season
        ? `Finished — closed at the election of ${long(d.cycle_closes)}. Every line below links to the meeting or the document it is read from.`
        : `One page that follows the town’s budget from the first deficit figure to Town Meeting — what is decided, what is still on the table, what has only been said — updated from every board’s meetings.`}
      dataUrl={season ? `/data/budget-feed-${season}.json` : DATA}>
      {/* THE SEASON. TJ: "budget-feed probably should have a dropdown for each season." The
          list is in the payload -- the live cycle and every replay that has been built. */}
      <label className="flex items-center gap-2 mt-4 text-sm max-w-full">
        <span style={{ color: 'var(--text-muted)' }}>Budget year</span>
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
            <h2 className="text-xl font-bold">{e.kind === 'regular' ? `${FY(Number(e.season_fy))} budget planning` : e.label}</h2>
            <span className="text-xs" style={{ color: 'var(--text-muted)' }}>{e.closed ? 'closed' : 'under way'} · {mmddyy(e.opens)}{e.closes ? ` → ${mmddyy(e.closes)}` : ' →'}{e.kind === 'special' ? <> · <a className="underline" href={`/budget-feed/${e.id}`}>its own page</a></> : null}</span>
          </div>
          {e.kind === 'special' && <p className="text-sm mt-1 max-w-3xl" style={{ color: 'var(--text-secondary)' }}>{e.trigger}.</p>}
          {/* THE STATUS BOARD, where a season file exists (sources/data/budget-seasons/<fy>.csv);
              the extraction-built tiers where it does not yet. */}
          {(() => {
            const tiers = <Tiers st={e.state} closed={e.closed} decisions={d.entries.filter(x => x.kind === 'vote' && x.date >= e.opens && (!e.closes || x.date <= e.closes))} outcome={e.kind === 'regular' ? d.outcome : null} meta={d.threads} fy={Number(e.about_fy || e.season_fy)}
              finalText={e.kind === 'special' ? (e.outcome || null) : (d.outcome.closed ? d.outcome.headline : null)}
              finalNote={e.kind === 'regular' && d.outcome.closed ? `Annual Town Meeting ${d.outcome.atm_date ? long(d.outcome.atm_date) : ''}; election ${d.outcome.election_date ? long(d.outcome.election_date) : ''}. Tallies from the town’s printed results; the appropriation from the adopted budget.` : null} />
            return e.kind === 'regular' ? <SeasonBoard fy={Number(e.season_fy)} fallback={tiers} onLoaded={() => setHasBoard(true)} /> : <SeasonBoard fy={Number(e.about_fy || e.season_fy)} id={e.id} fallback={tiers} />
          })()}
        </section>
      ))}
      {d.episodes.length === 0 && (
        <section className="mt-8">
          <div className="flex flex-wrap items-baseline gap-x-3">
            <h2 className="text-xl font-bold">{FY(d.cycle_fy)} budget planning</h2>
            <span className="text-xs" style={{ color: 'var(--text-muted)' }}>{d.outcome.closed ? 'closed' : 'under way'} · {mmddyy(d.cycle_opens)}{d.outcome.closed ? ` → ${mmddyy(d.cycle_closes)}` : ' →'}</span>
          </div>
          <SeasonBoard fy={d.cycle_fy} onLoaded={() => setHasBoard(true)}
            fallback={<Tiers st={d.state} closed={d.outcome.closed} decisions={d.entries.filter(x => x.kind === 'vote')} outcome={d.outcome} meta={d.threads} fy={d.cycle_fy} finalText={d.outcome.closed ? d.outcome.headline : null} />} />
        </section>
      )}

      {/* ------------------------------------------------------------------ upcoming */}
      {!season && <H2 id="upcoming">Budget meetings coming up</H2>}
      {season ? null : d.upcoming.filter(u => u.date >= todayIso()).length === 0 ? <p className="text-sm mt-2" style={{ color: 'var(--text-secondary)' }}>No posted agenda carries a budget item, as of {d.as_of}.</p> : (
        <ol className="space-y-3 mt-3">{d.upcoming.map(u => (
          <li key={u.board_slug + u.date} className="card p-4">
            <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
              <a className="font-bold" href={u.board_page}>{u.board}</a>
              <span className="text-[13px] font-bold" style={{ color: 'var(--series-cost)' }}>{dayLabel(u.date)}</span>
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
      {!hasBoard && <>
      {/* ONE ROW PER STAGE. TJ, 14 September: "the FY27 calendar is very hard to read."
          Nine cards each listing every board's every date was a wall. A table: the stage,
          when it typically runs, when it ran this cycle (first to last, how many meetings),
          and which boards -- the raw dates behind a fold. */}
      <H2 id="calendar">{d.outcome.closed ? `The ${FY(d.cycle_fy)} calendar, as it ran` : `What’s next — the ${FY(d.cycle_fy)} calendar`}</H2>
      <p className="text-sm mt-1 max-w-3xl" style={{ color: 'var(--text-secondary)' }}>The stages of a budget year in the order they come. “Typically” is measured off the budget boards’ own agendas over the last five cycles; “this cycle” is when the subject was actually on an agenda.</p>
      <div className="mt-4 overflow-x-auto">
        <table className="w-full text-sm" style={{ minWidth: 560 }}>
          <thead><tr className="text-[10px] uppercase tracking-widest text-left" style={{ color: 'var(--text-muted)' }}>
            <th className="py-1.5 pr-3 font-bold">Stage</th>{!d.outcome.closed && <th className="py-1.5 pr-3 font-bold">Status</th>}<th className="py-1.5 pr-3 font-bold">Typically</th><th className="py-1.5 pr-3 font-bold">This cycle</th><th className="py-1.5 font-bold">Boards</th>
          </tr></thead>
          <tbody>{d.calendar.map(s => {
            const dates = s.windows.flatMap(w => w.this_cycle).sort()
            return (
              <tr key={s.key} className="align-top" style={{ borderTop: '1px solid var(--grid)' }}>
                <td className="py-2 pr-3 font-semibold" style={{ borderLeft: `3px solid ${STATUS[s.status][1]}`, paddingLeft: 8 }}>{s.stage}</td>
                {!d.outcome.closed && <td className="py-2 pr-3 text-xs whitespace-nowrap" style={{ color: STATUS[s.status][1] }}>{STATUS[s.status][0]}</td>}
                <td className="py-2 pr-3 tnum whitespace-nowrap" style={{ color: 'var(--text-secondary)' }}>{s.typical_first} → {s.typical_last}</td>
                <td className="py-2 pr-3 tnum whitespace-nowrap">{dates.length ? <>{mmddyy(dates[0])}{dates.length > 1 ? ` → ${mmddyy(dates[dates.length - 1])}` : ''}<span className="text-xs" style={{ color: 'var(--text-muted)' }}> · {dates.length} meeting{dates.length === 1 ? '' : 's'}</span></> : <span style={{ color: 'var(--text-muted)' }}>—</span>}</td>
                <td className="py-2 text-xs" style={{ color: 'var(--text-secondary)' }}>
                  {s.windows.map((w, i) => <span key={w.board_slug}>{i > 0 ? ' · ' : ''}<a className="underline" href={`/boards/${w.board_slug}#calendar`}>{w.board}</a>{w.this_cycle.length ? <span className="tnum"> {w.this_cycle.length}</span> : ''}</span>)}
                  {dates.length > 0 && <details className="mt-1"><summary className="cursor-pointer" style={{ color: 'var(--text-muted)' }}>the dates</summary>
                    <ul className="mt-1 space-y-0.5">{s.windows.filter(w => w.this_cycle.length).map(w => <li key={w.board_slug} className="tnum">{w.board}: {w.this_cycle.map(mmddyy).join(', ')}</li>)}</ul></details>}
                </td>
              </tr>
            )
          })}</tbody>
        </table>
      </div>
      <p className="text-xs mt-2 max-w-3xl" style={{ color: 'var(--text-muted)' }}>A cycle runs July to June and is named for the budget it builds. “Typically” is the median first and last date the subject appeared on that board’s agenda; the raw dates per cycle are on each board’s page.</p>
      </>}

      {/* -------------------------------------------------------------------- recent */}
      {/* Under a finished season's board the raw log is folded to one line: the story is
          above; this is the record it was read from. */}
      {hasBoard && !recentOpen ? (
        <p className="text-sm mt-8" style={{ color: 'var(--text-secondary)' }}><button className="underline" onClick={() => setRecentOpen(true)}>Meeting by meeting</button> — the {d.entries.length.toLocaleString('en-US')} things said or voted about the budget across {d.counts.boards} boards’ meetings this year, each linked to the second in the video. The record the board above was read from.</p>
      ) : <>
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

      </>}
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

import { useState } from 'react'
import { feedSeasonFromPath, type Tab } from '../routes'
import { H2, ReportShell, Stat, useReport } from '../components/report'
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

const KIND: Record<string, string> = { deficit: 'deficit or gap', budget_total: 'budget total', override: 'override', state_aid: 'state aid', free_cash: 'free cash', levy: 'the levy' }
const SCOPE: Record<string, string> = { school: 'School', town: 'Town', both: 'Town and schools' }

/** THE LATEST ON THE RECORD. TJ: "School committee announced 10 cuts for a $2m deficit."
 *  For each scope and kind the most recent statement that carried a figure -- who said
 *  it by role, its status, the second in the video -- then the cut list as last stated
 *  and the meetings that changed it. Every figure is AS HEARD from captions; the second
 *  in the video is the record. */
const STATUS_LABEL = (status: string, closed: boolean) => closed ? 'final' : status === 'voted' ? 'voted' : status === 'restored' ? 'restored' : status === 'withdrawn' ? 'withdrawn' : 'preliminary'

function LatestState({ st, closed, decisions }: { st: State; closed: boolean; decisions: Entry[] }) {
  const [showAll, setShowAll] = useState(false)
  const pick = (kind: string) => Object.values(st.latest).filter(x => x.kind === kind)
  const deficits = pick('deficit'), totals = pick('budget_total')
  const proposals = Object.values(st.history).flat().filter(x => x.status === 'proposed' && x.kind !== 'deficit' && x.kind !== 'budget_total')
    .sort((a, b) => b.date.localeCompare(a.date)).slice(0, 8)
  const voted = Object.values(st.history).flat().filter(x => x.status === 'voted').sort((a, b) => b.date.localeCompare(a.date))
  const live = st.cuts.filter(c => c.status !== 'restored' && c.status !== 'withdrawn')
  const gone = st.cuts.filter(c => c.status === 'restored' || c.status === 'withdrawn')
  const shownCuts = showAll ? st.cuts : live
  const Card = ({ s, tone }: { s: Statement; tone?: string }) => (
    <div className="card p-4" style={{ borderLeft: `3px solid ${tone || 'var(--series-cost)'}` }}>
      <p className="text-[10px] font-bold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>{SCOPE[s.scope] || s.scope}{s.fiscal_year ? ` · FY${String(s.fiscal_year).slice(2)}` : ''} · <span style={{ color: tone || 'var(--series-cost)' }}>{STATUS_LABEL(s.status, closed)}</span></p>
      <p className="text-2xl font-bold tnum mt-1" style={{ color: tone || 'var(--text-primary)' }}>{s.amount_as_heard}</p>
      <p className="text-[13px] mt-1">{s.statement}</p>
      <p className="text-xs mt-1.5" style={{ color: 'var(--text-muted)' }}>{s.who}, {s.status} · <a className="underline" href={`/boards/${s.board_slug}`}>{s.board}</a>, {mmdd(s.date)} · <a className="underline tnum" href={s.video_url}>{ts(s.t)}</a></p>
    </div>
  )
  return (
    <>
      <H2 id="latest">{closed ? 'Where it ended' : 'Where it stands'}</H2>
      <p className="text-sm mt-1 max-w-3xl" style={{ color: 'var(--text-secondary)' }}>From {st.meetings_read} recorded meetings of the three budget boards{st.first_date ? ` since ${mmdd(st.first_date)}` : ''}. Figures are as heard from machine captions — the second in the video is the record. {closed ? 'The season has closed, so every figure here is final unless the town reopened it.' : 'Preliminary until voted; voted until Town Meeting; then final.'}</p>

      {(deficits.length > 0 || totals.length > 0) && (
        <>
          <p className="text-[10px] font-bold uppercase tracking-widest mt-5" style={{ color: 'var(--text-muted)' }}>The deficit, and the budget</p>
          <div className="grid gap-3 mt-2 sm:grid-cols-2 lg:grid-cols-3">
            {deficits.map(s => <Card key={'d' + s.scope} s={s} tone="var(--status-critical)" />)}
            {totals.map(s => <Card key={'t' + s.scope} s={s} />)}
          </div>
        </>
      )}
      {deficits.length === 0 && totals.length === 0 && <p className="text-sm mt-3" style={{ color: 'var(--text-muted)' }}>No deficit or budget total has been put on the record yet this season.</p>}

      {proposals.length > 0 && (
        <>
          <p className="text-[10px] font-bold uppercase tracking-widest mt-6" style={{ color: 'var(--text-muted)' }}>Proposals on the table</p>
          <ul className="mt-2 space-y-1.5 text-[13.5px]">{proposals.map((p, i) => (
            <li key={i} className="pl-3" style={{ borderLeft: '2px solid var(--grid)' }}><span className="tnum font-semibold">{p.amount_as_heard}</span> — {p.statement} <span className="text-xs" style={{ color: 'var(--text-muted)' }}>({KIND[p.kind] || p.kind}; {p.who}, {p.board}, {mmdd(p.date)}, <a className="underline" href={p.video_url}>{ts(p.t)}</a>)</span></li>))}</ul>
        </>
      )}

      <p className="text-[10px] font-bold uppercase tracking-widest mt-6" style={{ color: 'var(--text-muted)' }}>Stated impacts — the cuts named</p>
      <p className="text-sm mt-1 max-w-3xl" style={{ color: 'var(--text-secondary)' }}>
        <strong className="tnum">{live.length}</strong> named and standing{Object.keys(st.live_by_scope).length > 1 ? ` (${Object.entries(st.live_by_scope).map(([k, n]) => `${n} ${k}`).join(', ')})` : ''}{gone.length ? `; ${gone.length} restored or withdrawn` : ''}. Each row is the latest status of one named reduction.
        {gone.length > 0 && <button className="underline ml-2" onClick={() => setShowAll(!showAll)}>{showAll ? 'hide restored' : 'show restored too'}</button>}
      </p>
      {st.cuts.length === 0 ? <p className="text-sm mt-2" style={{ color: 'var(--text-muted)' }}>No cut has been named on the record yet this season.</p> : (
        <div className="overflow-x-auto mt-2">
          <table className="text-sm w-full" style={{ minWidth: 720 }}>
            <thead><tr className="text-[10px] font-bold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>
              <th className="text-left py-1.5 pr-3">cut</th><th className="text-left py-1.5 pr-3">scope</th><th className="text-right py-1.5 pr-3">amount, as heard</th><th className="text-right py-1.5 pr-3">FTE</th><th className="text-left py-1.5 pr-3">status</th><th className="text-left py-1.5">last stated</th></tr></thead>
            <tbody>{shownCuts.map((c, i) => (
              <tr key={i} style={{ borderTop: '1px solid var(--grid)', color: c.status === 'restored' || c.status === 'withdrawn' ? 'var(--text-muted)' : undefined }}>
                <td className="py-1.5 pr-3 align-top">{c.item}</td>
                <td className="py-1.5 pr-3 align-top">{c.scope}</td>
                <td className="py-1.5 pr-3 align-top text-right tnum whitespace-nowrap">{c.amount_as_heard || '—'}</td>
                <td className="py-1.5 pr-3 align-top text-right tnum">{c.fte_as_heard || '—'}</td>
                <td className="py-1.5 pr-3 align-top font-semibold" style={{ color: c.status === 'voted' ? 'var(--status-critical)' : c.status === 'restored' ? 'var(--status-good)' : undefined }}>{STATUS_LABEL(c.status, closed)}</td>
                <td className="py-1.5 align-top whitespace-nowrap"><a className="underline" href={`/boards/${c.board_slug}`}>{c.board}</a>, {mmdd(c.date)} · <a className="underline tnum" href={c.video_url}>{ts(c.t)}</a></td>
              </tr>))}</tbody>
          </table>
        </div>
      )}
      {st.log.length > 0 && (
        <ul className="mt-2 text-xs space-y-1" style={{ color: 'var(--text-secondary)' }}>{st.log.slice(0, 6).map((l, i) => (
          <li key={i}><span className="tnum mr-2" style={{ color: 'var(--text-muted)' }}>{mmdd(l.date)}</span><a className="underline" href={l.page}>{l.board}</a>: {l.n_added ? `${l.n_added} named` : ''}{l.n_added && l.n_changed ? ', ' : ''}{l.n_changed ? l.changed.map(c => `${c.item} ${c.was} → ${c.now}`).join('; ') : ''}</li>))}</ul>
      )}

      {(decisions.length > 0 || voted.length > 0) && (
        <>
          <p className="text-[10px] font-bold uppercase tracking-widest mt-6" style={{ color: 'var(--text-muted)' }}>Decisions — the votes on the budget, newest first</p>
          <ul className="mt-2 space-y-1.5 text-[13.5px]">
            {voted.map((v, i) => <li key={'s' + i} className="pl-3" style={{ borderLeft: '2px solid var(--series-cost)' }}><span className="tnum font-semibold">{v.amount_as_heard}</span> — {v.statement} <span className="text-xs" style={{ color: 'var(--text-muted)' }}>({v.board}, {mmdd(v.date)}, <a className="underline" href={v.video_url}>{ts(v.t)}</a>)</span></li>)}
            {decisions.slice(0, 15).map((e, i) => <li key={'v' + i} className="pl-3" style={{ borderLeft: '2px solid var(--series-cost)' }}>{e.text} <span className="font-semibold" style={{ color: (e.detail || '').startsWith('pass') ? 'var(--status-good)' : (e.detail || '').startsWith('fail') ? 'var(--status-critical)' : 'var(--text-muted)' }}>— {e.detail}</span> <span className="text-xs" style={{ color: 'var(--text-muted)' }}>({e.board}, {mmdd(e.date)}, <a className="underline" href={e.video_url}>{ts(e.t)}</a>)</span></li>)}
          </ul>
        </>
      )}
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
      <label className="inline-flex items-center gap-2 mt-4 text-sm">
        <span style={{ color: 'var(--text-muted)' }}>Season</span>
        <select className="rounded-md px-2 py-1 text-sm" style={{ background: 'var(--surface-3)', border: '1px solid var(--grid)' }}
          value={`/budget-feed/${e.id}`} onChange={ev => { window.location.href = ev.target.value }}>
          {d.seasons.map(s => <option key={s.path} value={s.path}>{s.label}</option>)}
        </select>
      </label>
      {e.outcome && (
        <div className="card p-4 mt-6" style={{ borderLeft: '4px solid var(--status-good)' }}>
          <p className="text-[10px] font-bold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>How it landed</p>
          <p className="text-xl font-bold mt-1">{e.outcome}</p>
          {e.note && <p className="text-xs mt-2" style={{ color: 'var(--text-muted)' }}>{e.note}. Sources: {e.source}.</p>}
        </div>
      )}
      <LatestState st={st} closed={e.closed} decisions={decisions} />
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
  const now = d.calendar.find(s => s.status === 'now' || s.status === 'underway')
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
      <label className="inline-flex items-center gap-2 mt-4 text-sm">
        <span style={{ color: 'var(--text-muted)' }}>Season</span>
        <select className="rounded-md px-2 py-1 text-sm" style={{ background: 'var(--surface-3)', border: '1px solid var(--grid)' }}
          value={(seg ? `/budget-feed/${seg}` : '/budget-feed')}
          onChange={e => { window.location.href = e.target.value }}>
          {d.seasons.map(s => <option key={s.path} value={s.path}>{s.label}</option>)}
        </select>
      </label>
      {/* HOW THE SEASON LANDED, first, on a finished season. TJ: "how it landed at town
          meeting vote, failing the override, should be clearly visible at the top." From
          the ballot-questions registry and the model, not from captions. */}
      {d.outcome.closed && (
        <div className="card p-4 mt-6" style={{ borderLeft: '4px solid var(--status-critical)' }}>
          <p className="text-[10px] font-bold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>How the {FY(d.cycle_fy)} season landed</p>
          <p className="text-2xl font-bold mt-1">{d.outcome.headline}</p>
          <div className="grid gap-x-8 gap-y-2 mt-3 sm:grid-cols-2 text-sm">
            {d.outcome.adopted && <div><span className="text-[10px] font-bold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>Annual Town Meeting, {d.outcome.atm_date ? long(d.outcome.atm_date) : ''}</span><div className="tnum"><strong>${d.outcome.adopted.amount.toLocaleString('en-US')}</strong> {d.outcome.adopted.label}</div></div>}
            {d.outcome.questions.filter(q => q.yes != null).map(q => (
              <div key={q.question}><span className="text-[10px] font-bold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>{q.election}, {q.date.length > 7 ? long(q.date) : q.date} — {q.question.toLowerCase()}</span>
                <div className="tnum"><strong>{q.amount != null ? '$' + q.amount.toLocaleString('en-US') : ''}</strong> {q.type.replace('Proposition 2½ ', '')} — <span style={{ color: q.result === 'FAILED' ? 'var(--status-critical)' : 'var(--status-good)' }}>{q.result.toLowerCase()}</span>, {q.yes!.toLocaleString('en-US')} yes to {q.no!.toLocaleString('en-US')} no{q.total && q.registered ? ` · ${q.total.toLocaleString('en-US')} of ${q.registered.toLocaleString('en-US')} voters (${q.turnout_pct}%)` : ''}</div></div>))}
            {d.outcome.questions.filter(q => q.yes == null).map(q => (
              <div key={q.question}><span className="text-[10px] font-bold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>{q.election}, {q.date} — {q.question.toLowerCase()}</span>
                <div className="tnum">{q.amount != null ? '$' + q.amount.toLocaleString('en-US') + ' ' : ''}{q.type.replace('Proposition 2½ ', '')} — {q.result.toLowerCase()}</div></div>))}
          </div>
          <p className="text-xs mt-3" style={{ color: 'var(--text-muted)' }}>Tallies from the town’s printed results, each reconciled to its total; the appropriation from the adopted budget. The season closed with the election on {d.outcome.election_date ? long(d.outcome.election_date) : ''}.</p>
        </div>
      )}
      {/* EPISODES. TJ: "the 418k was not a deficit... a spending plan. So your FY28 should
          probably be FY28-governors-budget or something, and be presented that way (which
          is different than how normal budget season works)." Each special episode -- the
          post-override cuts, the Governor's extra aid and its Special Town Meeting, the
          November STM -- is its own card with its trigger, its outcome and its own figures;
          the regular season's block follows, and says plainly when it has not opened. */}
      {d.episodes.filter(e => e.kind === 'special').map(e => {
        const st = e.state
        const keys = Object.keys(st.latest)
        const live = st.cuts.filter(c => c.status !== 'restored' && c.status !== 'withdrawn')
        return (
          <div key={e.id} className="card p-4 mt-6" style={{ borderLeft: `4px solid ${e.closed ? 'var(--text-muted)' : 'var(--series-cost)'}` }}>
            <p className="text-[10px] font-bold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>{e.closed ? 'Closed' : 'Under way'} · outside the regular season · {mmdd(e.opens)}{e.closes ? ` → ${mmdd(e.closes)}` : ' →'}</p>
            <p className="text-xl font-bold mt-1">{e.label}</p>
            <p className="text-sm mt-1.5" style={{ color: 'var(--text-secondary)' }}>{e.trigger}.{e.outcome ? <> <strong style={{ color: 'var(--text-primary)' }}>{e.outcome}.</strong></> : null}</p>
            {(keys.length > 0 || live.length > 0) && (
              <dl className="grid gap-x-8 gap-y-1.5 mt-3 sm:grid-cols-2 text-[13px]">
                {keys.map(k => { const x = st.latest[k]; return (
                  <div key={k} className="flex gap-3"><dt className="w-32 shrink-0 font-semibold">{SCOPE[x.scope] || x.scope} {KIND[x.kind] || x.kind}</dt>
                    <dd className="min-w-0"><span className="tnum font-semibold">{x.amount_as_heard}</span> — {x.statement} <span className="text-xs" style={{ color: 'var(--text-muted)' }}>({x.who}, {x.board}, {mmdd(x.date)}, <a className="underline" href={x.video_url}>{ts(x.t)}</a>)</span></dd></div>) })}
                {live.length > 0 && <div className="flex gap-3"><dt className="w-32 shrink-0 font-semibold">Cuts named</dt><dd className="min-w-0">{live.length} — {live.slice(0, 4).map(c => c.item).join('; ')}{live.length > 4 ? ' …' : ''}</dd></div>}
              </dl>
            )}
            {e.note && <p className="text-xs mt-2" style={{ color: 'var(--text-muted)' }}>{e.note}. Sources: {e.source}.</p>}
          </div>
        )
      })}

      {/* AT A GLANCE. The things people come here to know, as short labelled facts -- the
          deficit, the cuts, the status, what is next, the warrant -- each from the record
          or saying "not on the record yet". TJ: "just make sure all the info is on here
          clearly understandable." */}
      <div className="card p-4 mt-6">
        <p className="text-[10px] font-bold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>{d.outcome.closed ? `The ${FY(d.cycle_fy)} season — final` : d.episodes.some(e => e.kind === 'regular') ? `The ${FY(d.cycle_fy)} season, at a glance` : `The ${FY(d.cycle_fy)} season has not opened`}</p>
        {!d.outcome.closed && !d.episodes.some(e => e.kind === 'regular') && <p className="text-sm mt-1" style={{ color: 'var(--text-secondary)' }}>The regular cycle — the budget presented, heard and voted, then Town Meeting — typically opens in late October. What is on the record so far belongs to the episodes above; the figures below are the season’s whole record to date.</p>}
        <dl className="grid gap-x-8 gap-y-2.5 mt-2 sm:grid-cols-2 text-[13.5px]">
          {d.answers.map((a, i) => (
            <div key={i} className="flex gap-3">
              <dt className="w-32 shrink-0 font-semibold">{a.label}</dt>
              <dd className="min-w-0">
                <span>{a.answer}</span>
                {a.link && <a className="underline ml-1.5 text-xs" style={{ color: 'var(--text-muted)' }} href={a.link}>{a.link.startsWith('#') ? 'below' : a.link.startsWith('http') ? 'video' : 'more'}</a>}
                <span className="ml-1.5 text-[10px] font-bold uppercase tracking-widest" style={{ color: a.status === 'not yet' ? 'var(--text-muted)' : a.status === 'final' ? 'var(--status-good)' : 'var(--series-cost)' }}>{a.status}</span>
              </dd>
            </div>))}
        </dl>
      </div>
      <div className="flex flex-wrap gap-x-10 gap-y-5 mt-6">
        {!season && <Stat value={String(d.counts.upcoming)} tone="var(--series-cost)">budget meetings on the calendar, any board</Stat>}
        {!d.outcome.closed && <Stat value={now ? now.stage : 'Between stages'}>{now ? `where the ${FY(d.cycle_fy)} cycle stands — typically ${now.typical_first} to ${now.typical_last}` : `the ${FY(d.cycle_fy)} cycle, as of ${d.as_of}`}</Stat>}
        <Stat value={String(d.counts.boards)}>boards that discussed the budget or the warrant {season ? 'this season' : `in the last ${d.recent_days} days`} — {meetings.length} meetings, {d.counts.entries} things said</Stat>
      </div>

      {/* ------------------------------------------------------------- the latest */}
      <LatestState st={d.state} closed={d.outcome.closed} decisions={d.entries.filter(e => e.kind === 'vote')} />

      {/* ------------------------------------------------------------------ upcoming */}
      {/* A finished season has nothing coming up; the meetings after its end belong to the
          next cycle, so a replay skips this section. */}
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
      <H2 id="calendar">The {FY(d.cycle_fy)} budget calendar</H2>
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
      <H2 id="recent">What was said about the budget and the warrant, newest first</H2>
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

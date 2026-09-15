import { useEffect, useState, type ReactNode } from 'react'
import { useReport } from '../components/report'

/** THE SEASON AS A STATUS BOARD. notes/process/BUDGET-SEASON-MODEL.md, from TJ's account of
 *  how a season actually goes: "keeping citizens aligned on all those happenings -- to know
 *  what the current state of all that is along the way -- is critical." Six blocks, each
 *  with a NOW and its history; every row cites the event in our record or the document it
 *  is read from (build_budget_season.py fails if a citation is dead). The extraction feeds
 *  the row that cite it; this page reads only the season file. */

type Cite = { kind: 'meeting' | 'document' | 'ballot'; href: string; label: string; page?: string; board?: string; date?: string; t?: number }
type Row = { block: string; item: string; scope: string; status: string; figure: string; fte: number | null; date: string; who: string; why: string; evidence: string; note: string; cite: Cite | null }
type Line = { side: string; document: string; category: string; line: string; level_service: number | null; balanced: number | null; tier1_core: number | null; tier2_restoration: number | null; cut: number | null; tier1_restores: number | null; tier2_restores: number | null }
export type Season = { id: string; fy: number; source: string; rows: number; model: string; live?: boolean; as_of?: string | null; titles: Record<string, { title: string; sub: string }>; blocks: Record<'deficit' | 'proposals' | 'cuts' | 'override' | 'late' | 'final', Row[]>; lines: Line[] }

const mmdd = (d: string) => new Date(d + 'T12:00:00').toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
const usd = (n: number) => '$' + Math.round(n).toLocaleString('en-US')
const SCOPE: Record<string, string> = { school: 'Schools', town: 'Town', both: 'Town and schools' }

/** The family a resident would name -- the word that decides whether they show up. */
const FAMILIES: [string, RegExp][] = [
  ['Special education and intervention', /interventionist|intervention|mtss|special ed|cota|occupational|psycholog|guidance|counselor|bcba|bridge/i],
  ['Paraprofessionals and tutors', /paraprofessional|\bpara\b|tutor/i],
  ['Teachers', /teacher|classroom|grade|kindergarten/i],
  ['Athletics', /athletic|sport|\bcoach\b(?!.*specialist)|trainer|lacrosse|golf|\bski/i],
  ['Band and music', /band|music/i],
  ['Transportation', /transport/i],
  ['Administration', /principal|business manager|secretary|director|administrator|manager|clerk|admin/i],
  ['Custodial and facilities', /custod|facilit|maintenance|building|tcp|passios|grounds/i],
  ['Curriculum and technology', /curriculum|technology|computer|supplies|\bit\b|\btech\b/i],
  ['Fire', /\bfire\b/i], ['Police', /police|sro|school resource|patrol|sergeant|lobby/i],
  ['DPW and roads', /dpw|pavement|stormwater|road|recycling|line painting/i],
  ['Library', /librar/i], ['Council on Aging', /council on aging|coa\b|dietary/i],
  ['Parks and recreation', /park|recreation|beach|band concert/i],
]
const family = (r: Row) => {
  const m = r.item.match(/^Town — ([^—]+?) — /)      // a town row names its department first
  if (m) return m[1].trim()
  return (FAMILIES.find(([, rx]) => rx.test(r.item)) || ['Other'])[0] as string
}

function CiteLink({ c }: { c: Cite | null }) {
  if (!c) return null
  return <span className="text-xs ml-1.5" style={{ color: 'var(--text-muted)' }}>{c.kind === 'meeting' && c.page ? <><a className="underline" href={c.page}>{c.board}</a>, {c.date ? mmdd(c.date) : ''}{c.t ? <> · <a className="underline tnum" href={c.href}>{Math.floor(c.t / 60)}:{String(c.t % 60).padStart(2, '0')}</a></> : null}</> : <a className="underline" href={c.href}>{c.label}</a>}</span>
}

function Item({ r, muted }: { r: Row; muted?: boolean }) {
  return (
    <li className="pl-3 py-0.5 text-[13.5px]" style={{ borderLeft: '2px solid var(--grid)', color: muted ? 'var(--text-muted)' : undefined }}>
      <span className="font-semibold">{r.item.replace(/^Town — /, '').replace(/^(Fire|Police|DPW|Library|Council on Aging|Parks & Recreation|General Government|Universal) — /, '')}</span>{r.fte ? <span className="tnum"> · {r.fte} FTE</span> : ''}{r.figure ? <span className="tnum"> · {r.figure}</span> : ''}
      {r.why && <span style={{ color: 'var(--text-secondary)' }}> — {r.why}</span>}
      <CiteLink c={r.cite} />
      {r.note && !r.note.startsWith('internal:') && <span className="text-xs italic ml-1.5" style={{ color: 'var(--text-muted)' }}>{r.note}</span>}
    </li>
  )
}

function Block({ title, color, children, sub }: { title: string; color: string; sub?: string; children: ReactNode }) {
  return (
    <div className="card p-4 mt-4" style={{ borderTop: `4px solid ${color}` }}>
      <p className="text-[10px] font-bold uppercase tracking-widest" style={{ color }}>{title}</p>
      {sub && <p className="text-xs mt-0.5 mb-2" style={{ color: 'var(--text-muted)' }}>{sub}</p>}
      {children}
    </div>
  )
}

export function SeasonBoard({ fy, id, fallback, onLoaded }: { fy: number; id?: string; fallback: ReactNode; onLoaded?: () => void }) {
  const { d, err } = useReport<Season>(`budget-season-${id || 'fy' + String(fy).slice(2)}.json`)
  const [showLines, setShowLines] = useState(false)
  useEffect(() => { if (d && onLoaded) onLoaded() }, [d, onLoaded])
  if (err) return <>{fallback}</>     // no season file yet: the page built from the extraction
  if (!d) return null
  const b = d.blocks
  const T = (block: string, title: string, sub: string) => ({ title: d.titles?.[block]?.title || title, sub: d.titles?.[block]?.sub || sub })
  // A LIVE season: rows with status 'expected' are the moments that have not come yet, each
  // with when it usually does; 'warned' rows are predictions with no figure, straight from
  // the record. Both render as what they are and never as a figure.
  const expected = (block: keyof Season['blocks']) => b[block].filter(r => r.status === 'expected')
  const NotYet = ({ block }: { block: keyof Season['blocks'] }) => expected(block).length ? (
    <ul className="mt-2 space-y-1">{expected(block).map((r, i) => <li key={i} className="pl-3 py-0.5 text-[13.5px]" style={{ borderLeft: '2px dashed var(--grid)', color: 'var(--text-muted)' }}><span className="text-[10px] font-bold uppercase tracking-wider mr-1.5">not yet</span><span className="font-semibold" style={{ color: 'var(--text-secondary)' }}>{r.item}</span> — {r.why}{r.who ? <span className="text-xs"> · from {r.who}</span> : null}</li>)}</ul>
  ) : null
  const warned = b.cuts.filter(r => r.status === 'warned')
  const gap = (scope: string) => b.deficit.filter(r => r.scope === scope && r.status !== 'expected')
  // the school's figure first; failing that, any scope's -- an episode's 'started' can be the town's
  const moment = (scope: string, st: string) => gap(scope).find(r => r.status === st) || b.deficit.find(r => r.status === st)
  const town = moment('town', 'now'), both = moment('both', 'now')
  const cuts = b.cuts.filter(r => r.status !== 'expected' && r.status !== 'warned')
  const decided = cuts.filter(r => r.status === 'decided'), off = cuts.filter(r => r.status === 'came_off'), tierOnly = cuts.filter(r => r.status === 'tier_only')
  const byFamily = (xs: Row[]) => { const m = new Map<string, Row[]>(); for (const r of xs) { const f = family(r); m.set(f, [...(m.get(f) || []), r]) }; return [...m.entries()] }
  const fteOf = (xs: Row[]) => xs.reduce((a, r) => a + (r.fte || 0), 0)
  const finalBallot = b.final.filter(r => r.status === 'ballot'), appropriated = b.final.filter(r => r.status === 'appropriated'), took = b.final.filter(r => r.status === 'took_effect'), later = b.final.filter(r => r.status === 'restored_later')
  const schoolDecided = decided.filter(r => r.scope === 'school'), townDecided = decided.filter(r => r.scope === 'town')
  const started = moment('school', 'started'), corrected = moment('school', 'corrected'), toCut = moment('school', 'to_cut'), closed = moment('school', 'now')
  const summary = [
    started ? `the schools said they were ${started.figure} short in February` : '',
    corrected ? `then ${corrected.figure.split(' (')[0]} ${corrected.why.replace(/^corrected downward: /, 'once ').split(/[;:]/)[0]}` : '',
    finalBallot.some(q => q.figure) ? `${finalBallot.filter(q => q.figure).length} override question${finalBallot.filter(q => q.figure).length === 1 ? '' : 's'} ${finalBallot.filter(q => q.figure).every(q => /failed/i.test(q.why)) ? 'failed' : 'went to the ballot'}` : finalBallot.length ? 'no override question reached the ballot' : '',
    schoolDecided.length ? `${schoolDecided.length} cuts stood on the school side${fteOf(schoolDecided) ? ` (${fteOf(schoolDecided)} FTE where an FTE is printed)` : ''}` : '',
    townDecided.length ? `${townDecided.length} on the town side` : '',
  ].filter(Boolean).join('; ')
  const nextUp = d.live ? [...b.deficit, ...b.proposals, ...b.cuts, ...b.override, ...b.final].filter(r => r.status === 'expected' && (!d.as_of || r.date >= d.as_of)).sort((a, c) => a.date.localeCompare(c.date))[0] : undefined
  const onRecord = d.live ? [...b.deficit, ...b.cuts, ...b.override, ...b.late].filter(r => r.status !== 'expected').length : 0
  const liveLine = d.live ? `The ${'FY' + String(d.fy).slice(2)} budget is being built. No figure is on the record yet${onRecord ? `; ${onRecord} thing${onRecord === 1 ? '' : 's'} said so far ${onRecord === 1 ? 'is' : 'are'} below` : ''}. ${nextUp ? `Next up: ${nextUp.item.toLowerCase()} — ${nextUp.why.split(' — ')[0]}.` : ''}` : ''
  const oneLine = d.titles?.summary?.title || (d.live && !started ? liveLine : '')
  const lines = d.lines.filter(l => l.side === 'school' && (l.cut || 0) > 0).sort((a, c) => (c.cut || 0) - (a.cut || 0))

  return (
    <section className="mt-4">
      {d.live && <p className="text-[10px] font-bold uppercase tracking-widest" style={{ color: 'var(--status-good)' }}>Live — read from the record daily{d.as_of ? `, as of ${mmdd(d.as_of)}` : ''}</p>}
      <p className="text-[15px] max-w-3xl" style={{ color: 'var(--text-secondary)' }}>{oneLine || `FY${String(d.fy).slice(2)}: ${summary}.`}</p>

      {/* 1. the deficit -- the moments a resident heard, not a spreadsheet difference */}
      <Block title={T('deficit', 'The gap', '').title} color="var(--status-critical)" sub={T('deficit', '', 'The shortfall as staff put it on the record — the number people argued about, and every time it moved, with why.').sub}>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {[['Schools — as announced', started], ['Schools — corrected', corrected], ['Schools — left to cut on the night of the vote', toCut], ['Town and schools together', both]].map(([label0, r]) => r && typeof r !== 'string' ? (
            <div key={label0 as string}>
              <p className="text-[10px] font-bold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>{['Schools', 'Town', 'Town and schools together'].includes(r.item) ? label0 as string : r.item}</p>
              <p className="text-xl font-bold tnum leading-tight">{r.figure.split(' (')[0]}</p>
              <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>{r.why}</p>
              <p className="text-xs" style={{ color: 'var(--text-muted)' }}>{r.who}, {mmdd(r.date)}<CiteLink c={r.cite} /></p>
            </div>
          ) : null)}
        </div>
        {gap('school').length + gap('town').length + gap('both').length === 0 && expected('deficit').length === 0 && <p className="text-sm" style={{ color: 'var(--text-muted)' }}>No figure on the record yet.</p>}
        {gap('school').concat(gap('both')).filter(r => ['started', 'corrected', 'to_cut', 'now'].includes(r.status)).length === 0 && gap('school').length > 0 && <ul className="space-y-1">{gap('school').map((r, i) => <li key={i} className="pl-3 py-0.5 text-[13.5px]" style={{ borderLeft: '2px solid var(--status-critical)' }}><span className="tnum text-xs mr-2" style={{ color: 'var(--text-muted)' }}>{mmdd(r.date)}</span><span className="font-semibold">{r.item}</span>{r.figure ? <span className="tnum"> · {r.figure}</span> : ''} — {r.why} <span className="text-xs" style={{ color: 'var(--text-muted)' }}>({r.who})</span><CiteLink c={r.cite} /></li>)}</ul>}
        <NotYet block="deficit" />
        {closed && <p className="text-sm mt-3" style={{ color: 'var(--text-secondary)' }}><span className="font-semibold">{T('closed', 'How it closed', '').title}:</span> {closed.why}{closed.why.includes(closed.figure.split(' — ')[0]) ? '' : ` (${closed.figure.split(' — ')[0]})`}.<CiteLink c={closed.cite} /></p>}
        {town && town !== both && <p className="text-sm mt-1" style={{ color: 'var(--text-secondary)' }}><span className="font-semibold">The town side:</span> {town.figure.split(' (')[0]} — {town.why} ({town.who}, {mmdd(town.date)}).<CiteLink c={town.cite} /></p>}
        {b.deficit.filter(r => r.status !== 'expected').length > 1 && <details className="mt-3"><summary className="cursor-pointer text-xs underline" style={{ color: 'var(--series-cost)' }}>How the numbers moved — {b.deficit.filter(r => r.status !== 'expected').length} figures, three stories</summary>
          {(['school', 'both', 'town'] as const).map(scope => gap(scope).length ? (
            <div key={scope} className="mt-3">
              <p className="text-[10px] font-bold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>{SCOPE[scope]}</p>
              <ul className="mt-1 space-y-1">{gap(scope).map((r, i) => <li key={i} className="pl-3 py-0.5 text-[13.5px]" style={{ borderLeft: `2px solid ${['started', 'corrected', 'to_cut', 'now'].includes(r.status) ? 'var(--status-critical)' : 'var(--grid)'}` }}><span className="tnum text-xs mr-2" style={{ color: 'var(--text-muted)' }}>{mmdd(r.date)}</span><span className="font-bold tnum">{r.figure}</span> — {r.why} <span className="text-xs" style={{ color: 'var(--text-muted)' }}>({r.who})</span><CiteLink c={r.cite} />{r.note && !r.note.startsWith('internal:') && <span className="text-xs italic ml-1.5" style={{ color: 'var(--text-muted)' }}>{r.note}</span>}</li>)}</ul>
            </div>) : null)}
        </details>}
      </Block>

      {/* 2. the cuts */}
      <Block title={T('cuts', 'The cuts', '').title} color="var(--status-critical)" sub={T('cuts', '', 'What was cut, what came off the list, and what only an override tier would have cut — grouped the way a family looks for its own.').sub}>
        <div className="grid gap-4 lg:grid-cols-3">
          <div className="lg:col-span-2">
            {(decided.length > 0 || !d.live) && <p className="text-xs font-bold uppercase tracking-wider" style={{ color: 'var(--status-critical)' }}>{T('cuts.cut', 'Cut', '').title} — {decided.length}</p>}
            <NotYet block="cuts" />
            {(['school', 'town'] as const).map(scope => {
              const xs = decided.filter(r => r.scope === scope && !/^Town — Universal/.test(r.item))
              // The provenance most of a list shares is said once, under the heading, and the
              // rows that share it carry only their name -- 39 rows of 'on the approved list'
              // was a wall (FY26, read as a parent).
              const key = (r: Row) => `${r.why}|${r.cite?.href || ''}`
              const tally = new Map<string, number>(); for (const r of xs) tally.set(key(r), (tally.get(key(r)) || 0) + 1)
              const [commonKey, commonN] = [...tally.entries()].sort((a, b) => b[1] - a[1])[0] || ['', 0]
              const common = commonN >= 5 ? xs.find(r => key(r) === commonKey) : undefined
              const strip = (r: Row): Row => common && key(r) === commonKey ? { ...r, why: '', cite: null } : r
              const universal = decided.filter(r => r.scope === scope && /^Town — Universal/.test(r.item))
              const noFte = common ? xs.filter(r => r.fte == null && !r.figure && key(r) === commonKey).length : 0   // only meaningful for a printed list
              const notes = cuts.filter(r => r.scope === scope && r.status === 'note')
              if (!xs.length && notes.length) return <div key={scope} className="mt-2"><p className="text-[13px] font-semibold">{SCOPE[scope]}</p>{notes.map((r, i) => <p key={i} className="text-[13px]" style={{ color: 'var(--text-secondary)' }}>{r.item} — {r.why}<CiteLink c={r.cite} /></p>)}</div>
              return xs.length ? <div key={scope} className="mt-2"><p className="text-[13px] font-semibold">{SCOPE[scope]} — {xs.length}{fteOf(xs) ? `, ${fteOf(xs)} FTE where an FTE is printed` : ''}{noFte ? `; ${noFte} printed as whole positions` : ''}</p>
                {common && <p className="text-xs" style={{ color: 'var(--text-muted)' }}>{commonN} of these: {common.why}<CiteLink c={common.cite} /></p>}
                {byFamily(xs).map(([f, rows]) => <div key={f} className="mt-1"><p className="text-[10px] font-bold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>{f}</p><ul>{rows.map((r, i) => <Item key={i} r={strip(r)} />)}</ul></div>)}
                {universal.length > 0 && <details className="mt-2"><summary className="cursor-pointer text-xs underline" style={{ color: 'var(--text-muted)' }}>{universal.length} more the town cut in all three budgets — no override would have changed these</summary><ul className="mt-1">{universal.map((r, i) => <Item key={i} r={{ ...r, item: r.item.replace('Town — Universal — ', ''), why: '' }} muted />)}</ul></details>}</div> : null
            })}
          </div>
          <div>
            {(off.length > 0 || !d.live) && <p className="text-xs font-bold uppercase tracking-wider" style={{ color: 'var(--status-good)' }}>{T('cuts.off', 'Came off the list', '').title} — {off.length}</p>}
            <ul className="mt-2">{off.map((r, i) => <Item key={i} r={r} />)}</ul>
            {off.length === 0 && decided.length > 0 && <p className="text-sm" style={{ color: 'var(--text-muted)' }}>Nothing came off.</p>}
            {warned.length > 0 && <><p className="text-xs font-bold uppercase tracking-wider mt-5" style={{ color: 'var(--status-warning)' }}>Warned about — {warned.length}</p>
            <p className="text-xs" style={{ color: 'var(--text-muted)' }}>A prediction or a threat on the record, with no figure yet. Straight from the recording; nobody has confirmed it means a cut.</p>
            <ul className="mt-2">{warned.map((r, i) => <Item key={i} r={r} muted />)}</ul></>}
            {tierOnly.length > 0 && <><p className="text-xs font-bold uppercase tracking-wider mt-5" style={{ color: 'var(--text-muted)' }}>Only inside a tier — {tierOnly.length}</p>
            <ul className="mt-2">{tierOnly.map((r, i) => <Item key={i} r={r} muted />)}</ul></>}
          </div>
        </div>
        {lines.length > 0 && <p className="text-xs mt-3" style={{ color: 'var(--text-muted)' }}><button className="underline" onClick={() => setShowLines(!showLines)}>{showLines ? 'Hide' : 'Check against'} the district’s line-item budget</button> — every line where the balanced budget is below level service, footed to the document’s printed total: {lines.length} lines, {usd(lines.reduce((a, l) => a + (l.cut || 0), 0))} gross.</p>}
        {showLines && <div className="overflow-x-auto mt-2"><table className="text-xs" style={{ minWidth: 520 }}><thead><tr className="text-left" style={{ color: 'var(--text-muted)' }}><th className="pr-3 py-1">line</th><th className="pr-3 py-1 text-right">level service</th><th className="pr-3 py-1 text-right">balanced</th><th className="pr-3 py-1 text-right">cut</th><th className="pr-3 py-1 text-right">tier 1 restores</th><th className="py-1 text-right">tier 2 restores</th></tr></thead>
          <tbody>{lines.map((l, i) => <tr key={i} style={{ borderTop: '1px solid var(--grid)' }}><td className="pr-3 py-1">{l.line}</td><td className="pr-3 py-1 text-right tnum">{l.level_service != null ? usd(l.level_service) : ''}</td><td className="pr-3 py-1 text-right tnum">{l.balanced != null ? usd(l.balanced) : ''}</td><td className="pr-3 py-1 text-right tnum font-semibold">{usd(l.cut || 0)}</td><td className="pr-3 py-1 text-right tnum">{l.tier1_restores ? usd(l.tier1_restores) : '—'}</td><td className="py-1 text-right tnum">{l.tier2_restores ? usd(l.tier2_restores) : '—'}</td></tr>)}</tbody></table></div>}
      </Block>

      {/* 3. the proposals */}
      <Block title={T('proposals', 'The proposals', '').title} color="var(--series-cost)" sub={T('proposals', '', 'The budgets put on the table, side by side — the names change every year.').sub}>
        <NotYet block="proposals" />
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">{b.proposals.filter(r => r.status !== 'expected').map((r, i) => (
          <div key={i} className="px-3 py-2 rounded-md" style={{ background: 'var(--surface-3)' }}>
            <p className="text-[10px] font-bold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>{SCOPE[r.scope]}</p>
            <p className="font-bold">{r.item}</p>
            <p className="tnum text-lg">{r.figure}{r.fte ? <span className="text-xs ml-1" style={{ color: 'var(--text-muted)' }}>{r.fte} FTE</span> : null}</p>
            <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>{r.why}</p>
            {r.note && !r.note.startsWith('internal:') && <p className="text-xs italic" style={{ color: 'var(--text-muted)' }}>{r.note}</p>}
            <p className="text-xs"><CiteLink c={r.cite} /></p>
          </div>))}</div>
      </Block>

      {/* 4 + 5. the override track and the late moves */}
      <div className="grid gap-4 lg:grid-cols-2">
        <Block title={T('override', 'The override track', '').title} color="var(--series-cost)" sub={T('override', '', 'Whether one is filed, for how much, and where each board stands — step by step.').sub}>
          <ul>{b.override.filter(r => r.status !== 'expected').map((r, i) => <li key={i} className="pl-3 py-0.5 text-[13.5px]" style={{ borderLeft: `2px solid ${r.cite?.kind === 'ballot' ? 'var(--status-critical)' : 'var(--series-cost)'}` }}><span className="tnum text-xs mr-2" style={{ color: 'var(--text-muted)' }}>{mmdd(r.date)}</span><span className="font-semibold">{r.item}</span>{r.figure ? <span className="tnum"> · {r.figure}</span> : ''}{r.why ? <span style={{ color: 'var(--text-secondary)' }}> — {r.why}</span> : ''} <span className="text-xs" style={{ color: 'var(--text-muted)' }}>({r.who})</span><CiteLink c={r.cite} />{r.note && !r.note.startsWith('internal:') && <span className="text-xs italic ml-1.5" style={{ color: 'var(--text-muted)' }}>{r.note}</span>}</li>)}</ul>
          <NotYet block="override" />
        </Block>
        <Block title={T('late', 'Fees, free cash and other moves', '').title} color="var(--series-cost)" sub={T('late', '', 'What was charged or moved to close the gap — fees, free cash, transfers, new revenue.').sub}>
          <ul>{b.late.filter(r => r.status !== 'expected').map((r, i) => <Item key={i} r={r} />)}</ul>
          {b.late.filter(r => r.status !== 'expected').length === 0 && <p className="text-sm" style={{ color: 'var(--text-muted)' }}>None recorded.</p>}
          <NotYet block="late" />
        </Block>
      </div>

      {/* 6. final */}
      <Block title={T('final', 'Final — what Town Meeting and the ballot did, and what took effect', '').title} color="var(--status-good)" sub={T('final', '', '').sub || undefined}>
        <ul>{[...appropriated, ...finalBallot].map((r, i) => <li key={i} className="pl-3 py-0.5 text-[13.5px]" style={{ borderLeft: '2px solid var(--status-good)' }}>{r.figure ? <><span className="font-bold tnum">{r.figure}</span> — </> : null}<span className={r.figure ? '' : 'font-semibold'}>{r.item}</span>{r.why ? <span style={{ color: /failed/i.test(r.why) ? 'var(--status-critical)' : 'var(--text-secondary)' }}>, {r.why}</span> : ''} <span className="text-xs" style={{ color: 'var(--text-muted)' }}>{r.who}, {mmdd(r.date)}</span><CiteLink c={r.cite} /></li>)}</ul>
        {took.map((r, i) => <div key={i} className="mt-3 pl-3" style={{ borderLeft: '2px solid var(--status-critical)' }}><p className="text-[13.5px] font-semibold">{r.item}{r.fte ? <span className="tnum"> · {r.fte} FTE</span> : ''}{r.figure ? <span className="tnum"> · {r.figure}</span> : ''}</p><p className="text-xs" style={{ color: 'var(--text-secondary)' }}>{[r.why, r.note.startsWith('internal:') ? '' : r.note].filter(Boolean).join('. ')}<CiteLink c={r.cite} /></p></div>)}
        {appropriated.length + finalBallot.length + took.length + later.length === 0 && <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>Nothing is final yet. Town Meeting appropriates the budget and the election decides any override; until then everything above is a board’s position or somebody’s proposal.</p>}
        <NotYet block="final" />
        {later.map((r, i) => <div key={i} className="mt-3 pl-3" style={{ borderLeft: '2px solid var(--status-good)' }}><p className="text-[13.5px] font-semibold">{r.item}{r.figure ? <span className="tnum"> · {r.figure}</span> : ''}</p><p className="text-xs" style={{ color: 'var(--text-secondary)' }}>{[r.why, r.note.startsWith('internal:') ? '' : r.note].filter(Boolean).join('. ')}<CiteLink c={r.cite} /></p></div>)}
      </Block>
      <p className="text-xs mt-3" style={{ color: 'var(--text-muted)' }}>Every row above is a line in <a className="underline" href={`/${d.source.replace('sources/', 'docs/')}`}>{d.source}</a>, written from the district’s and the town’s own scenario documents and from our record of the meetings; each cites where it comes from. Figures and FTEs as the documents state them.</p>
    </section>
  )
}

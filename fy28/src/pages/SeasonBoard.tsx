import { Fragment, useEffect, useState, type ReactNode } from 'react'
import { useReport } from '../components/report'

/** THE SEASON AS A STATUS BOARD. notes/process/BUDGET-SEASON-MODEL.md, from TJ's account of
 *  how a season actually goes: "keeping citizens aligned on all those happenings -- to know
 *  what the current state of all that is along the way -- is critical." Six blocks, each
 *  with a NOW and its history; every row cites the event in our record or the document it
 *  is read from (build_budget_season.py fails if a citation is dead). The extraction feeds
 *  the row that cite it; this page reads only the season file. */

type Cite = { kind: 'meeting' | 'document' | 'ballot'; href: string; label: string; page?: string; board?: string; date?: string; t?: number }
type Row = { block: string; item: string; scope: string; status: string; figure: string; fte: number | null; date: string; who: string; why: string; evidence: string; note: string; cite: Cite | null; also?: Cite[] }
type Line = { side: string; document: string; category: string; line: string; level_service: number | null; balanced: number | null; tier1_core: number | null; tier2_restoration: number | null; cut: number | null; tier1_restores: number | null; tier2_restores: number | null }
type Moved = { by: number; approx: boolean; from_figure: string; from_version: string }
type Share = { figure: string; why: string; version: string; date: string; cite: Cite | null }
type Version = { n: number; item: string; scope: string; status: string; figure: string; date: string; who: string; why: string; note: string; cite: Cite | null; also: Cite[]
  gap: Row | null; gap_moved: Moved | null; closed: Row[]; path: Row[]; proposals: Row[]; cuts_added: Row[]; came_off: Row[]; warned: Row[]; notes: Row[]; late: Row[]; final: Row[]
  rise: number | null; on_table: number; off_so_far: number; school_share: Share | null }
type Coming = { item: string; scope: string; date: string; who: string; why: string; cite: Cite | null; version: boolean }
type Prop25 = { fy: number; prior_fy: number; prior_limit: number; step: number; new_growth: number | null; room: number | null; certified: boolean; floor: boolean; basis_fy?: number; basis_limit?: number; source: string }
export type Season = { id: string; fy: number; source: string; rows: number; model: string; live?: boolean; as_of?: string | null; titles: Record<string, { title: string; sub: string }>; blocks: Record<'deficit' | 'proposals' | 'cuts' | 'override' | 'late' | 'final', Row[]>; lines: Line[]
  versions?: Version[]; strands?: { override: Row[]; before: Row[]; coming: Coming[] } | null; prop25?: Prop25 | null }

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

/* ---------------------------------------------------------------------------------------
 * THE SEASON BY VERSION. notes/process/BUDGET-SEASON-MODEL.md §6. TJ, 20 November 2026: "we
 * need to consider VERSIONS... each version has new cuts, deficits, etc." One card per budget
 * put on the record -- a draft, a target, a vote, a scenarios document, the adopted budget --
 * newest first, each with the same parts: its figure and gap, what changed from the version
 * before, the cuts in it, the Prop 2½ step and its sources. The newest is open; older ones
 * fold to their headline and what changed. Everything here is computed by
 * build_budget_season.py from the season file; nothing is typed. */

const STATUS: Record<string, string> = { preliminary: 'draft', target: 'target', voted: 'voted', scenarios: 'scenarios', recommended: 'recommended', adopted: 'final' }

function headline(v: Version): { label: string; figure: string } | null {
  if (v.figure) return { label: v.rise != null ? 'over last year' : 'the figure', figure: v.figure }
  if (v.gap) return { label: v.gap.status === 'to_cut' ? 'left to cut' : v.gap.scope === 'both' ? 'the gap, town and schools' : 'the gap', figure: v.gap.figure.split(' (')[0] }
  const appr = v.final.find(r => r.status === 'appropriated')
  if (appr) return { label: appr.item.toLowerCase(), figure: appr.figure }
  if (v.closed[0]) return { label: 'how it closed', figure: v.closed[0].figure.split(' — ')[0] }
  if (v.path[0]) return { label: v.path[0].figure.replace(/^\$[\d,.]+\s*(million)?\s*/, '').split(' (')[0] || 'as stated', figure: (v.path[0].figure.match(/^\$[\d,.]+(\s*million)?/) || [v.path[0].figure])[0] }
  return null
}

/** What changed from the version before, in one line: the folded card's summary. */
function changedLine(v: Version): string {
  const bits: string[] = []
  if (v.gap_moved) bits.push(`gap ${v.gap_moved.by < 0 ? 'down' : 'up'} ${v.gap_moved.approx ? 'about ' : ''}${usd(Math.abs(v.gap_moved.by))}`)
  if (v.cuts_added.length) bits.push(`${v.cuts_added.length} cut${v.cuts_added.length === 1 ? '' : 's'}`)
  if (v.came_off.length) bits.push(`${v.came_off.length} came off`)
  if (v.proposals.length) bits.push(`${v.proposals.length} budget${v.proposals.length === 1 ? '' : 's'} side by side`)
  const ballot = v.final.filter(r => r.status === 'ballot' && r.figure)
  if (ballot.length) bits.push(`${ballot.length} override question${ballot.length === 1 ? '' : 's'} ${ballot.every(r => /failed/i.test(r.why)) ? 'failed' : 'voted'}`)
  return bits.join(' · ')
}

function Prop25Line({ p, v }: { p: Prop25; v: Version }) {
  const fy = (n: number) => 'FY' + n
  return (
    <div className="mt-3 px-3 py-2 rounded-md text-[13px]" style={{ background: 'var(--surface-3)' }}>
      <p className="text-[10px] font-bold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>Prop 2½ — what the levy can rise without an override</p>
      <p><span className="font-bold tnum">{p.floor ? 'at least ' : ''}{usd(p.step)}</span>{p.room != null ? <> plus <span className="tnum">{usd(p.new_growth || 0)}</span> new growth: <span className="font-bold tnum">{usd(p.room)}</span></> : ' plus new growth'}
        <span style={{ color: 'var(--text-secondary)' }}> — for the whole town, schools and town together. 2.5% of the {fy(p.prior_fy)} levy limit{p.floor ? `, which is not certified yet; this is the ${fy(p.basis_fy!)} limit (${usd(p.basis_limit!)}) grown by 2.5%` : ` (${usd(p.prior_limit)})`}.{p.room == null && !p.floor ? ` New growth for ${fy(p.fy)} is not in the state’s file yet.` : ''}</span></p>
      {v.rise != null && <p className="mt-1">This draft rises <span className="font-bold tnum">{usd(v.rise)}</span> over last year — against the whole town’s levy step above.</p>}
      {v.school_share ? <p className="mt-1">The schools’ share, as the Town Manager set it: <span className="font-bold tnum">{v.school_share.figure}</span> <span style={{ color: 'var(--text-secondary)' }}>— {v.school_share.why} ({mmdd(v.school_share.date)})</span><CiteLink c={v.school_share.cite} /></p>
        : <p className="mt-1 text-xs" style={{ color: 'var(--text-muted)' }}>No school share is shown: the Town Manager has not set the schools’ target in this season’s record by this point, and any split before then would be ours.</p>}
      <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>Our arithmetic on the <a className="underline" href={p.source}>state’s levy limit figures</a>. The levy is one part of the revenue; state aid and local receipts move separately.</p>
    </div>
  )
}

function VersionCard({ v, p, open, color }: { v: Version; p: Prop25 | null | undefined; open: boolean; color: string }) {
  const h = headline(v)
  const changed = changedLine(v)
  const byFam = (xs: Row[]) => { const m = new Map<string, Row[]>(); for (const r of xs) { const f = family(r); m.set(f, [...(m.get(f) || []), r]) }; return [...m.entries()] }
  const cut = v.cuts_added.filter(r => r.status !== 'tier_only'), tier = v.cuts_added.filter(r => r.status === 'tier_only')
  const dated = (r: Row) => <li key={r.item + r.date + r.figure} className="pl-3 py-0.5 text-[13.5px]" style={{ borderLeft: '2px solid var(--grid)' }}><span className="tnum text-xs mr-2" style={{ color: 'var(--text-muted)' }}>{mmdd(r.date)}</span>{r.scope !== v.scope ? <span className="text-[10px] font-bold uppercase tracking-wider mr-1" style={{ color: 'var(--text-muted)' }}>{SCOPE[r.scope]}</span> : null}<span className="font-bold tnum">{r.figure}</span>{r.item && !['Schools', 'Town', 'Town and schools together'].includes(r.item) ? <span className="font-semibold"> {r.item}</span> : null} — {r.why} <span className="text-xs" style={{ color: 'var(--text-muted)' }}>({r.who})</span><CiteLink c={r.cite} /></li>
  return (
    <details open={open} className="card mt-3" style={{ borderLeft: `4px solid ${color}` }}>
      <summary className="cursor-pointer list-none p-4">
        <div className="flex flex-wrap items-baseline gap-x-2">
          <span className="text-[10px] font-bold uppercase tracking-widest" style={{ color }}>Version {v.n} · {STATUS[v.status] || v.status}</span>
          <span className="text-xs" style={{ color: 'var(--text-muted)' }}>{v.who}, {mmdd(v.date)}</span>
        </div>
        <p className="font-bold text-[16px] leading-snug">{v.item}</p>
        {h && <p className="mt-0.5"><span className="text-xl font-bold tnum">{h.figure}</span> <span className="text-xs" style={{ color: 'var(--text-muted)' }}>{h.label}</span></p>}
        {changed && <p className="text-xs mt-0.5" style={{ color: 'var(--text-secondary)' }}>{changed}</p>}
      </summary>
      <div className="px-4 pb-4">
        <p className="text-[13.5px]" style={{ color: 'var(--text-secondary)' }}>{v.why}<CiteLink c={v.cite} />{v.also.map((c, i) => <CiteLink key={i} c={c} />)}</p>
        {v.note && !v.note.startsWith('internal:') && <p className="text-xs italic mt-1" style={{ color: 'var(--text-muted)' }}>{v.note}</p>}

        {(v.gap || v.gap_moved || v.path.length > 0 || v.closed.length > 0) && <>
          <p className="text-xs font-bold uppercase tracking-wider mt-3" style={{ color: 'var(--status-critical)' }}>The gap in this version</p>
          {v.gap_moved && <p className="text-[13.5px] mt-1">From <span className="tnum">{v.gap_moved.from_figure.split(' (')[0]}</span> ({v.gap_moved.from_version.replace(/^The /, 'the ')}) to <span className="tnum font-semibold">{v.gap!.figure.split(' (')[0]}</span>: <span className="font-semibold">{v.gap_moved.approx ? 'about ' : ''}{usd(Math.abs(v.gap_moved.by))} {v.gap_moved.by < 0 ? 'less' : 'more'}</span>.</p>}
          <ul className="mt-1 space-y-1">{[...(v.gap ? [v.gap] : []), ...v.path, ...v.closed].sort((a, c) => a.date.localeCompare(c.date)).map(dated)}</ul>
        </>}

        {v.proposals.length > 0 && <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 mt-3">{v.proposals.map((r, i) => (
          <div key={i} className="px-3 py-2 rounded-md" style={{ background: 'var(--surface-3)' }}>
            <p className="font-bold text-[13.5px]">{r.item}</p>
            <p className="tnum">{r.figure}</p>
            <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>{r.why}</p>
            <p className="text-xs"><CiteLink c={r.cite} /></p>
          </div>))}</div>}

        {(cut.length > 0 || v.came_off.length > 0 || tier.length > 0 || v.warned.length > 0) && <div className="grid gap-4 lg:grid-cols-3 mt-3">
          {cut.length > 0 && <div className="lg:col-span-2">
            <p className="text-xs font-bold uppercase tracking-wider" style={{ color: 'var(--status-critical)' }}>{v.status === 'adopted' ? 'Stood' : 'Cut in this version'} — {cut.length}{fteOf(cut) ? `, ${fteOf(cut)} FTE where printed` : ''}</p>
            {byFam(cut).map(([f, rows]) => <div key={f} className="mt-1"><p className="text-[10px] font-bold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>{f}</p><ul>{rows.map((r, i) => <Item key={i} r={r} />)}</ul></div>)}
          </div>}
          <div>
            {v.came_off.length > 0 && <><p className="text-xs font-bold uppercase tracking-wider" style={{ color: 'var(--status-good)' }}>Came off — {v.came_off.length}</p><ul className="mt-1">{v.came_off.map((r, i) => <Item key={i} r={r} />)}</ul></>}
            {tier.length > 0 && <><p className="text-xs font-bold uppercase tracking-wider mt-3" style={{ color: 'var(--text-muted)' }}>Only inside a tier — {tier.length}</p><ul className="mt-1">{tier.map((r, i) => <Item key={i} r={r} muted />)}</ul></>}
            {v.warned.length > 0 && <><p className="text-xs font-bold uppercase tracking-wider mt-3" style={{ color: 'var(--status-warning)' }}>Warned about — {v.warned.length}</p><p className="text-xs" style={{ color: 'var(--text-muted)' }}>A prediction on the record with no figure; nobody has confirmed it means a cut.</p><ul className="mt-1">{v.warned.map((r, i) => <Item key={i} r={r} muted />)}</ul></>}
          </div>
        </div>}
        {v.notes.map((r, i) => <p key={i} className="text-[13px] mt-2" style={{ color: 'var(--text-secondary)' }}>{r.item} — {r.why}<CiteLink c={r.cite} /></p>)}
        {v.on_table > cut.length && <p className="text-xs mt-2" style={{ color: 'var(--text-muted)' }}>{v.on_table} cuts on the list by this version, counting the versions before it{v.off_so_far ? `; ${v.off_so_far} came off along the way` : ''}.</p>}

        {v.late.length > 0 && <><p className="text-xs font-bold uppercase tracking-wider mt-3" style={{ color: 'var(--series-cost)' }}>Fees, free cash and other moves</p><ul className="mt-1">{v.late.map((r, i) => <Item key={i} r={r} />)}</ul></>}
        {v.final.length > 0 && <ul className="mt-3">{v.final.map((r, i) => <li key={i} className="pl-3 py-0.5 text-[13.5px]" style={{ borderLeft: '2px solid var(--status-good)' }}>{r.figure ? <><span className="font-bold tnum">{r.figure}</span> — </> : null}<span className={r.figure ? '' : 'font-semibold'}>{r.item}</span>{r.why ? <span style={{ color: /failed/i.test(r.why) ? 'var(--status-critical)' : 'var(--text-secondary)' }}>, {r.why}</span> : ''} <span className="text-xs" style={{ color: 'var(--text-muted)' }}>{r.who ? `${r.who}, ` : ''}{mmdd(r.date)}</span><CiteLink c={r.cite} /></li>)}</ul>}

        {p && <Prop25Line p={p} v={v} />}
      </div>
    </details>
  )
}

const fteOf = (xs: Row[]) => xs.reduce((a, r) => a + (r.fte || 0), 0)

function Versions({ d, oneLine }: { d: Season; oneLine: string }) {
  const vs = d.versions!, s = d.strands!
  const coming = d.live ? s.coming.filter(c => !d.as_of || c.date >= d.as_of) : []
  const next = coming.filter(c => c.version)
  return (
    <section className="mt-4">
      {d.live && <p className="text-[10px] font-bold uppercase tracking-widest" style={{ color: 'var(--status-good)' }}>Live — read from the record daily{d.as_of ? `, as of ${mmdd(d.as_of)}` : ''}</p>}
      {!d.live && oneLine && <p className="text-[15px] max-w-3xl" style={{ color: 'var(--text-secondary)' }}>{oneLine}</p>}
      {next.length > 0 && <div className="mt-2 px-3 py-2 rounded-md" style={{ border: '1px dashed var(--grid)' }}>
        <p className="text-[10px] font-bold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>Next versions expected</p>
        <ul>{next.map((c, i) => <li key={i} className="text-[13.5px]"><span className="font-semibold">{c.item}</span> <span style={{ color: 'var(--text-secondary)' }}>— {c.why.split(' — ')[0]}</span>{c.who ? <span className="text-xs" style={{ color: 'var(--text-muted)' }}> · from {c.who}</span> : null}</li>)}</ul>
      </div>}
      <p className="text-xs font-bold uppercase tracking-wider mt-4" style={{ color: 'var(--text-muted)' }}>FY{String(d.fy).slice(2)} · {vs.length} version{vs.length === 1 ? '' : 's'}, newest first</p>
      {vs.map((v, i) => <VersionCard key={v.n} v={v} p={d.prop25} open={i === 0} color={v.status === 'adopted' ? 'var(--status-good)' : v.scope === 'town' ? 'var(--series-cost)' : 'var(--status-critical)'} />)}

      {s.before.length > 0 && <details className="card mt-3 p-4"><summary className="cursor-pointer text-[13.5px] font-semibold">Before the first version — {s.before.length} thing{s.before.length === 1 ? '' : 's'} said on the record</summary>
        <ul className="mt-2">{s.before.map((r, i) => <Item key={i} r={r} muted={r.status === 'warned'} />)}</ul></details>}

      {s.override.length > 0 && <Block title={T0(d, 'override', 'The override track')} color="var(--series-cost)" sub="Not a version of the budget: whether one is filed, for how much, and where each board stands — step by step, across every version.">
        <ul>{s.override.map((r, i) => <li key={i} className="pl-3 py-0.5 text-[13.5px]" style={{ borderLeft: `2px solid ${r.cite?.kind === 'ballot' ? 'var(--status-critical)' : 'var(--series-cost)'}` }}><span className="tnum text-xs mr-2" style={{ color: 'var(--text-muted)' }}>{mmdd(r.date)}</span><span className="font-semibold">{r.item}</span>{r.figure ? <span className="tnum"> · {r.figure}</span> : ''}{r.why ? <span style={{ color: 'var(--text-secondary)' }}> — {r.why}</span> : ''} <span className="text-xs" style={{ color: 'var(--text-muted)' }}>({r.who})</span><CiteLink c={r.cite} /></li>)}</ul>
      </Block>}

      {coming.filter(c => !c.version).length > 0 && <Block title="Still to come" color="var(--text-muted)" sub="The moments that have not happened yet this season, with when they usually do.">
        <ul className="space-y-1">{coming.filter(c => !c.version).map((c, i) => <li key={i} className="pl-3 py-0.5 text-[13.5px]" style={{ borderLeft: '2px dashed var(--grid)', color: 'var(--text-muted)' }}><span className="font-semibold" style={{ color: 'var(--text-secondary)' }}>{c.item}</span> — {c.why}</li>)}</ul>
      </Block>}

      <p className="text-xs mt-3" style={{ color: 'var(--text-muted)' }}>Every version and every row is a line in <a className="underline" href={`/${d.source.replace('sources/', 'docs/')}`}>{d.source}</a>; each cites where it comes from. A row belongs to the newest version of its side on or before its date. Figures and FTEs as the documents state them; the Prop 2½ step and the changes between versions are our arithmetic.</p>
    </section>
  )
}

const T0 = (d: Season, block: string, title: string) => d.titles?.[block]?.title || title

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
  const sideWide = off.length + warned.length + tierOnly.length > decided.length
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
  // WHILE THE SCHOOLS ARE STILL DRAFTING, THEIR NEXT DRAFT IS WHAT IS NEXT. TJ, 20 November
  // 2026: "next up is the schools continued revisal draft, until its official proposal". The
  // town's target is an input to that draft, not the next thing a parent is waiting to read.
  const draftsLive = d.live && b.proposals.some(r => r.status !== 'expected' && r.scope === 'school')
  const nextDraft = draftsLive ? b.proposals.filter(r => r.status === 'expected' && r.scope === 'school' && /^Version/.test(r.item))[0] : undefined
  const nextUp = nextDraft || (d.live ? [...b.deficit, ...b.proposals, ...b.cuts, ...b.override, ...b.final].filter(r => r.status === 'expected' && (!d.as_of || r.date >= d.as_of)).sort((a, c) => a.date.localeCompare(c.date))[0] : undefined)
  const onRecord = d.live ? [...b.deficit, ...b.cuts, ...b.override, ...b.late].filter(r => r.status !== 'expected').length : 0
  // The schools' latest draft, once one is printed (FY28: Version 1, 18 Nov 2026). Until then
  // this line said "No figure is on the record yet" beside a card carrying the figure.
  const draft = d.live ? b.proposals.filter(r => r.status !== 'expected' && r.scope === 'school').sort((a, c) => c.date.localeCompare(a.date))[0] : undefined
  const liveLine = d.live ? `The ${'FY' + String(d.fy).slice(2)} budget is being built. ${draft ? `The schools' latest draft, ${draft.item} (${mmdd(draft.date)}): ${draft.figure}, ${draft.why.split(';')[0]}` : 'No figure is on the record yet'}${onRecord ? `; ${onRecord} thing${onRecord === 1 ? '' : 's'} said so far ${onRecord === 1 ? 'is' : 'are'} below` : ''}. ${nextUp ? `Next up: ${nextUp.item.toLowerCase()} — ${nextUp.why.split(' — ')[0]}.` : ''}` : ''
  const oneLine = d.titles?.summary?.title || (d.live && !started ? liveLine : '')
  const lines = d.lines.filter(l => l.side === 'school' && (l.cut || 0) > 0).sort((a, c) => (c.cut || 0) - (a.cut || 0))
  if (d.versions?.length) return <Versions d={d} oneLine={oneLine || `FY${String(d.fy).slice(2)}: ${summary}.`} />

  // NEWEST FIRST WHILE A SEASON IS LIVE. TJ, 20 November 2026: "this page should be NEWEST
  // FIRST order... so draft 1 should be at the top, THEN the previously discussed things." A
  // section moves up by the date of the latest thing on the record in it; a section with
  // nothing yet keeps its place below. A closed season keeps the story order.
  const latest = (rows: Row[]) => rows.filter(r => r.status !== 'expected').map(r => r.date).sort().pop() || ''
  const sectionDate: Record<string, string> = { deficit: latest(b.deficit), cuts: latest(b.cuts), proposals: latest(b.proposals), moves: latest([...b.override, ...b.late]), final: latest(b.final) }
  const sections: [string, ReactNode][] = [
    ['deficit', <Fragment key="deficit">
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
    </Fragment>],
    ['cuts', <Fragment key="cuts">
      <Block title={T('cuts', 'The cuts', '').title} color="var(--status-critical)" sub={T('cuts', '', 'What was cut, what came off the list, and what only an override tier would have cut — grouped the way a family looks for its own.').sub}>
        {/* TWO COLUMNS ONLY WHEN THE CUTS ARE THE LONGER SIDE. TJ, 26 October 2026: early in a
            season nothing is cut yet and 24 warnings filled the narrow side column, a strip the
            length of the page beside an empty wide one. The side lists go full width then. */}
        <div className={sideWide ? 'grid gap-4' : 'grid gap-4 lg:grid-cols-3'}>
          <div className={sideWide ? undefined : 'lg:col-span-2'}>
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
            <ul className={sideWide ? 'mt-2 sm:grid sm:grid-cols-2 sm:gap-x-6' : 'mt-2'}>{warned.map((r, i) => <Item key={i} r={r} muted />)}</ul></>}
            {tierOnly.length > 0 && <><p className="text-xs font-bold uppercase tracking-wider mt-5" style={{ color: 'var(--text-muted)' }}>Only inside a tier — {tierOnly.length}</p>
            <ul className="mt-2">{tierOnly.map((r, i) => <Item key={i} r={r} muted />)}</ul></>}
          </div>
        </div>
        {lines.length > 0 && <p className="text-xs mt-3" style={{ color: 'var(--text-muted)' }}><button className="underline" onClick={() => setShowLines(!showLines)}>{showLines ? 'Hide' : 'Check against'} the district’s line-item budget</button> — every line where the balanced budget is below level service, footed to the document’s printed total: {lines.length} lines, {usd(lines.reduce((a, l) => a + (l.cut || 0), 0))} gross.</p>}
        {showLines && <div className="overflow-x-auto mt-2"><table className="text-xs" style={{ minWidth: 520 }}><thead><tr className="text-left" style={{ color: 'var(--text-muted)' }}><th className="pr-3 py-1">line</th><th className="pr-3 py-1 text-right">level service</th><th className="pr-3 py-1 text-right">balanced</th><th className="pr-3 py-1 text-right">cut</th><th className="pr-3 py-1 text-right">tier 1 restores</th><th className="py-1 text-right">tier 2 restores</th></tr></thead>
          <tbody>{lines.map((l, i) => <tr key={i} style={{ borderTop: '1px solid var(--grid)' }}><td className="pr-3 py-1">{l.line}</td><td className="pr-3 py-1 text-right tnum">{l.level_service != null ? usd(l.level_service) : ''}</td><td className="pr-3 py-1 text-right tnum">{l.balanced != null ? usd(l.balanced) : ''}</td><td className="pr-3 py-1 text-right tnum font-semibold">{usd(l.cut || 0)}</td><td className="pr-3 py-1 text-right tnum">{l.tier1_restores ? usd(l.tier1_restores) : '—'}</td><td className="py-1 text-right tnum">{l.tier2_restores ? usd(l.tier2_restores) : '—'}</td></tr>)}</tbody></table></div>}
      </Block>
    </Fragment>],
    ['proposals', <Fragment key="proposals">
      <Block title={T('proposals', 'The proposals', '').title} color="var(--series-cost)" sub={T('proposals', '', 'The budgets put on the table, side by side — the names change every year.').sub}>
        <NotYet block="proposals" />
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">{b.proposals.filter(r => r.status !== 'expected').map((r, i) => (
          <div key={i} className="px-3 py-2 rounded-md" style={{ background: 'var(--surface-3)' }}>
            <p className="text-[10px] font-bold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>{SCOPE[r.scope]}</p>
            <p className="font-bold">{r.item}</p>
            <p className="tnum text-lg">{r.figure}{r.fte ? <span className="text-xs ml-1" style={{ color: 'var(--text-muted)' }}>{r.fte} FTE</span> : null}</p>
            <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>{r.why}</p>
            {r.note && !r.note.startsWith('internal:') && <p className="text-xs italic" style={{ color: 'var(--text-muted)' }}>{r.note}</p>}
            <p className="text-xs"><CiteLink c={r.cite} />{(r.also || []).map((c, j) => <CiteLink key={j} c={c} />)}</p>
          </div>))}</div>
      </Block>
    </Fragment>],
    ['moves', <Fragment key="moves">
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
    </Fragment>],
    ['final', <Fragment key="final">
      <Block title={T('final', 'Final — what Town Meeting and the ballot did, and what took effect', '').title} color="var(--status-good)" sub={T('final', '', '').sub || undefined}>
        <ul>{[...appropriated, ...finalBallot].map((r, i) => <li key={i} className="pl-3 py-0.5 text-[13.5px]" style={{ borderLeft: '2px solid var(--status-good)' }}>{r.figure ? <><span className="font-bold tnum">{r.figure}</span> — </> : null}<span className={r.figure ? '' : 'font-semibold'}>{r.item}</span>{r.why ? <span style={{ color: /failed/i.test(r.why) ? 'var(--status-critical)' : 'var(--text-secondary)' }}>, {r.why}</span> : ''} <span className="text-xs" style={{ color: 'var(--text-muted)' }}>{r.who}, {mmdd(r.date)}</span><CiteLink c={r.cite} /></li>)}</ul>
        {took.map((r, i) => <div key={i} className="mt-3 pl-3" style={{ borderLeft: '2px solid var(--status-critical)' }}><p className="text-[13.5px] font-semibold">{r.item}{r.fte ? <span className="tnum"> · {r.fte} FTE</span> : ''}{r.figure ? <span className="tnum"> · {r.figure}</span> : ''}</p><p className="text-xs" style={{ color: 'var(--text-secondary)' }}>{[r.why, r.note.startsWith('internal:') ? '' : r.note].filter(Boolean).join('. ')}<CiteLink c={r.cite} /></p></div>)}
        {appropriated.length + finalBallot.length + took.length + later.length === 0 && <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>Nothing is final yet. Town Meeting appropriates the budget and the election decides any override; until then everything above is a board’s position or somebody’s proposal.</p>}
        <NotYet block="final" />
        {later.map((r, i) => <div key={i} className="mt-3 pl-3" style={{ borderLeft: '2px solid var(--status-good)' }}><p className="text-[13.5px] font-semibold">{r.item}{r.figure ? <span className="tnum"> · {r.figure}</span> : ''}</p><p className="text-xs" style={{ color: 'var(--text-secondary)' }}>{[r.why, r.note.startsWith('internal:') ? '' : r.note].filter(Boolean).join('. ')}<CiteLink c={r.cite} /></p></div>)}
      </Block>
    </Fragment>],
  ]
  const ordered = d.live ? [...sections].sort((x, y) => (sectionDate[y[0]] || '').localeCompare(sectionDate[x[0]] || '')) : sections
  return (
    <section className="mt-4">
      {d.live && <p className="text-[10px] font-bold uppercase tracking-widest" style={{ color: 'var(--status-good)' }}>Live — read from the record daily{d.as_of ? `, as of ${mmdd(d.as_of)}` : ''}</p>}
      {/* A LIVE SEASON OPENS WITH THREE FACTS, NOT A SENTENCE. TJ, 20 November 2026, reading
          the one-line version ("The schools' latest draft, Version 1 ... ; 33 things said so far
          are below. Next up: ...") -- "this is hard to read". Three facts were sharing one run-on
          sentence, so each now gets a cell: the figure, what it is, where it came from. */}
      {d.live && !started && !d.titles?.summary?.title ? (
        <div className="grid gap-3 sm:grid-cols-2 max-w-3xl mt-1">
          <div className="px-3 py-2 rounded-md" style={{ background: 'var(--surface-3)' }}>
            <p className="text-[10px] font-bold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>The schools’ latest draft</p>
            {draft ? <>
              <p className="text-xl font-bold tnum leading-tight">{draft.figure}</p>
              <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>{draft.why.split(';')[0].replace(/, against (\S+) for (FY\d+)$/, ', up from $1 in $2')}</p>
              <p className="text-xs" style={{ color: 'var(--text-muted)' }}>{draft.item}, {mmdd(draft.date)}</p>
            </> : <p className="text-sm" style={{ color: 'var(--text-muted)' }}>No figure on the record yet</p>}
          </div>
          {nextUp && <div className="px-3 py-2 rounded-md" style={{ border: '1px dashed var(--grid)' }}>
            <p className="text-[10px] font-bold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>Next up</p>
            <p className="font-bold leading-tight">{nextUp.item}</p>
            <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>{nextUp.why.split(' — ')[0]}</p>
          </div>}
        </div>
      ) : <p className="text-[15px] max-w-3xl" style={{ color: 'var(--text-secondary)' }}>{oneLine || `FY${String(d.fy).slice(2)}: ${summary}.`}</p>}

      {ordered.map(([, el]) => el)}

      <p className="text-xs mt-3" style={{ color: 'var(--text-muted)' }}>Every row above is a line in <a className="underline" href={`/${d.source.replace('sources/', 'docs/')}`}>{d.source}</a>, written from the district’s and the town’s own scenario documents and from our record of the meetings; each cites where it comes from. Figures and FTEs as the documents state them.</p>
    </section>
  )
}

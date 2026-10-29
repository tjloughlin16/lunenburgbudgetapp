import { useCallback, useEffect, useMemo, useState } from 'react'
import { ReportShell, H2 } from '../components/report'
import { LineBody, type Data as LineData, type ExFile, type ExLine, type Row } from '../components/blocks/custom/fy-line-table'
import { FundBody, type Fund, type FundRow, type FundText } from '../components/blocks/custom/fy-source-table'
import { EgoWeb, type Ego } from '../components/blocks/custom/fy-ego-web'
import { MoveGroups, type MoveGroup } from '../components/blocks/custom/fy-fund-moves'
import { Chip } from '../components/blocks/custom/fy-shared'
import { useFyYear } from '../components/blocks/custom/fy-year'
import { GROUP_BASE, itemFromPath, loadIndex, type ItemIndex } from '../components/blocks/custom/fy-items'
import type { WebKind } from '../components/blocks/custom/fy-web-parts'
import { FundHistory, GroupCompare, LineBills, LineMemoCats, RatesTable, GroupCounts, GroupShifts, GroupSplit, LineHistory, PayerTraces, FundFlows, type FundFlow, type BillKinds, type Counts, type FundHist, type LineMemos, type LinePayees, type PayeeRates, type GroupMember, type GroupShift, type LineHist, type PayerTrace } from '../components/blocks/custom/fy-item-history'

/* ONE SCHOOL LINE OR ONE FUND, at its own address: /school-lines/<slug>, /school-funds/<slug>.
 *
 * TJ, 28 October 2026: *"i want people to be able to share urls to direct links for each fund,
 * school line ... And whats on there should be what shows up in the popup on the breakout pages
 * (expenses, payee, etc)."* So the body IS the popup's view (LineBody, FundBody -- one component,
 * two hosts), led by the item's own web and followed by its history across the journal's years.
 *
 * VISIBILITY IS THE PARENT'S. The FY breakdown page is a hidden draft -- on no shelf, not in
 * topics.json, so neither prerendered nor in the sitemap. These pages are the same: client-
 * rendered only (no static twin), noindex while mounted, and linked only from that page.
 *
 * Every figure is from /data/fy-breakdown/<line|fund>/<slug>.json, sliced by scripts/fy_items.py
 * from the files the breakdown page reads; every string from /data/fy-breakdown/index.json. */

type LineYear = { row: Row; funds: string[]; kinds: string[]; ex: ExLine | null; mv: ExFile['mv'][string] | null; web: Ego }
type LineItem = { slug: string; name: string; account: string; cat: string; years: Record<string, LineYear>; history: LineHist[]; payers: PayerTrace[]; payees: LinePayees; bill_kinds: BillKinds; memos?: LineMemos; rates?: PayeeRates[] }
type FundYear = { awards: { row: FundRow; body: Fund }[]; web: Ego; moves: MoveGroup[] }
type MovesFrame = { classes: { id: string; label: string }[]; text: Record<string, string> }
type FundItem = { slug: string; name: string; cat: string; group: string; years: Record<string, FundYear>; history: FundHist[]; flows?: FundFlow[] }

const muted = { color: 'var(--text-muted)' }, secondary = { color: 'var(--text-secondary)' }
const link = { color: 'var(--link, var(--thread-2))' }
/** noindex for as long as the page is mounted (as the employee pages do, pages/Person.tsx). */
function useNoIndex() {
  useEffect(() => {
    const m = document.createElement('meta')
    m.name = 'robots'
    m.content = 'noindex'
    document.head.appendChild(m)
    return () => { m.remove() }
  }, [])
}

/** ITS AWARDS, YEAR BY YEAR, AND THE COST MOVED BETWEEN THEM (TJ, 28 October 2026: "we also need
 *  to show that grant money is moved across years too"). Each year's awards side by side with what
 *  they spent, then every entry that re-booked cost from one of its awards to another -- the
 *  breakdown page's own groups, sliced by fy_items.py. Shown only where a programme has awards
 *  in more than one year. */
function AwardMoves({ h, ix, mv }: { h: FundHist[]; ix: ItemIndex; mv: MovesFrame }) {
  const t = ix.text
  if (!h.some(x => x.moves.length)) return null
  return (
    <section className="mt-10">
      <H2>{t.mv_awards_h}</H2>
      <p className="text-[13px] mb-3 max-w-3xl" style={secondary}>{t.mv_awards} {mv.text.what}</p>
      <div className="space-y-5">
        {h.map(x => (
          <div key={x.fy}>
            <p className="font-semibold text-[14px]">{x.fy}</p>
            <div className="flex flex-wrap gap-2 mt-1">
              {x.awards.map(a => (
                <span key={a.fund} className="rounded border px-2 py-1 text-[12.5px]" style={{ borderColor: 'var(--grid)' }}>
                  {a.name.split(' · ')[0].split(', ').slice(-1)[0]} <span style={muted}>· {a.fund}</span> <span className="tabular-nums font-semibold">{a.t}</span></span>))}
            </div>
            {x.moves.length ? <div className="mt-2"><MoveGroups groups={x.moves} classes={mv.classes} text={mv.text} /></div> : null}
          </div>))}
      </div>
    </section>)
}

function Sources({ ix }: { ix: ItemIndex }) {
  return (
    <section className="mt-10">
      <H2>{ix.text.sources}</H2>
      <p className="text-[13px] mb-2" style={secondary}>{ix.text.sources_note}</p>
      <ul className="text-[13px] space-y-1 list-disc pl-5">
        {ix.sources.map(s => <li key={s.href}><a className="underline" style={link} href={s.href}>{s.label}</a></li>)}
      </ul>
      <p className="text-[13px] mt-3"><a className="underline" style={link} href={ix.text.parent_href}>← {ix.text.parent}</a></p>
    </section>)
}

function Years({ years, fy, set }: { years: string[]; fy: string; set: (fy: string) => void }) {
  return (
    <div className="flex flex-wrap gap-1.5 mt-5">
      {years.map(y => <Chip key={y} on={y === fy} onClick={() => set(y)}>{y}</Chip>)}
    </div>)
}

function LinePage({ item, ix }: { item: LineItem; ix: ItemIndex }) {
  const years = useMemo(() => Object.keys(item.years).sort(), [item])
  const [fy, setFy] = useFyYear(years)
  const y = item.years[fy] ?? item.years[years[years.length - 1]]
  const d = useMemo(() => ({ ...(ix.frame.line as Omit<LineData, 'years'>), years: [] }) as LineData, [ix])
  // the line's own rows, in the shape the popup reads from the year's file
  const src = useCallback((f: string) => {
    const v = item.years[f]
    if (!v) return Promise.reject(new Error('no such year'))
    return Promise.resolve({ fy: f, funds: v.funds, kinds: v.kinds, lines: v.ex ? { [v.row.key]: v.ex } : {},
      mv: v.mv ? { [v.row.key]: v.mv } : {} } as ExFile)
  }, [item])
  const web = ix.frame.web as { kinds: { id: WebKind; label: string; means: string }[] }
  return (
    <ReportShell title={item.name} kicker={`${ix.text.k_line} · ${item.cat}`} dataUrl={`/data/fy-breakdown/line/${item.slug}.json`}
      standfirst={ix.text.line_what}
      meta={<div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1"><code className="text-[12px]" style={muted}>{item.account}</code>
        {(ix.groups ?? []).filter(g => g.members.includes(item.account)).map(g => (
          <a key={g.slug} href={`${GROUP_BASE}${g.slug}?fy=${encodeURIComponent(fy)}`} className="text-[13px] underline" style={link}>
            {ix.text.with_group} {g.name} →</a>))}</div>}>
      <Years years={years} fy={fy} set={setFy} />
      <section className="mt-6">
        <H2>{ix.text.web_h}</H2>
        <p className="text-[13px] mb-2 max-w-3xl" style={secondary}>{ix.text.web_line}</p>
        <EgoWeb ego={y.web} kinds={web.kinds} text={ix.text} fy={fy} />
        <p className="text-[12px] mt-2" style={muted}>{ix.text.web_ours}</p>
      </section>
      <section className="mt-10">
        <H2>{fy}</H2>
        <LineBody key={fy} r={y.row} d={d} fy={fy} src={src} bare />
      </section>
      <LineHistory h={item.history} ix={ix} />
      <LineBills payees={item.payees} kinds={item.bill_kinds} years={years} ix={ix} />
      <LineMemoCats m={item.memos} years={years} ix={ix} />
      <RatesTable rates={item.rates} ix={ix} />
      <PayerTraces p={item.payers} ix={ix} fy={fy} />
      <Sources ix={ix} />
    </ReportShell>)
}

function FundPage({ item, ix }: { item: FundItem; ix: ItemIndex }) {
  const years = useMemo(() => Object.keys(item.years).sort(), [item])
  const [fy, setFy] = useFyYear(years)
  const y = item.years[fy] ?? item.years[years[years.length - 1]]
  const [award, setAward] = useState(0)
  useEffect(() => setAward(0), [fy])
  const a = y.awards[Math.min(award, y.awards.length - 1)]
  const frame = ix.frame.fund as { text: FundText; columns: { id: string; label: string }[] }
  const mv = ix.frame.moves as MovesFrame
  const web = ix.frame.web as { kinds: { id: WebKind; label: string; means: string }[] }
  return (
    <ReportShell title={item.name} kicker={`${ix.text.k_fund} · ${item.cat}`} dataUrl={`/data/fy-breakdown/fund/${item.slug}.json`}
      standfirst={ix.text.fund_what}
      meta={(ix.groups ?? []).some(g => g.funds.includes(item.slug)) ? (
        <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1">
          {(ix.groups ?? []).filter(g => g.funds.includes(item.slug)).map(g => (
            <a key={g.slug} href={`${GROUP_BASE}${g.slug}?fy=${encodeURIComponent(fy)}`} className="text-[13px] underline" style={link}>
              {ix.text.paid_group} {g.name} →</a>))}
        </div>) : undefined}>
      <Years years={years} fy={fy} set={setFy} />
      <section className="mt-6">
        <H2>{ix.text.web_h}</H2>
        <p className="text-[13px] mb-2 max-w-3xl" style={secondary}>{ix.text.web_fund}</p>
        <EgoWeb ego={y.web} kinds={web.kinds} text={ix.text} fy={fy} />
        <p className="text-[12px] mt-2" style={muted}>{ix.text.web_ours}</p>
      </section>
      <section className="mt-10">
        <H2>{fy}</H2>
        {y.awards.length > 1 ? (
          <div className="mb-3">
            <p className="text-[13px] font-semibold mb-1">{ix.text.awards}</p>
            <div className="flex flex-wrap gap-1.5">
              {y.awards.map((w, i) => (
                <Chip key={w.row.key} on={i === award} onClick={() => setAward(i)}>
                  {w.row.name} <span className="tabular-nums font-semibold">{w.row.t.total}</span></Chip>))}
            </div>
          </div>) : null}
        <FundBody key={`${fy}${a.row.key}`} r={a.row} fy={fy} t={frame.text} F={a.body} bare={y.awards.length === 1} />
      </section>
      {y.moves.length ? (
        <section className="mt-10">
          <H2>{ix.text.mv_h}</H2>
          <p className="text-[13px] mb-3 max-w-3xl" style={secondary}>{mv.text.what} {mv.text.open}.</p>
          <MoveGroups groups={y.moves} classes={mv.classes} text={mv.text} />
        </section>) : null}
      <FundFlows f={item.flows} ix={ix} />
      <AwardMoves h={item.history} ix={ix} mv={mv} />
      <FundHistory h={item.history} ix={ix} cols={frame.columns} />
      <Sources ix={ix} />
    </ReportShell>)
}

type GroupRow = { fy: string; name: string; href: string; t: Record<'voted' | 'budget' | 'spent' | 'other' | 'all_in' | 'left', string>; n: { left: number } }
type GroupItem = { slug: string; name: string; what: string; cat: string; members: GroupMember[]
  history: LineHist[]; table: GroupRow[]; payers: PayerTrace[]; shifts: GroupShift[]; counts: Counts | null }

/** LINES READ TOGETHER, /school-groups/<slug> (TJ, 28 October 2026: "A specific sort of combined fund
 *  page? lets do that"). The line page's history and payer cards, summed over the group's lines, and
 *  each line beside the others every year -- so money moving between them shows as money moving,
 *  not as one line's cost changing. */
function GroupPage({ item, ix }: { item: GroupItem; ix: ItemIndex }) {
  const t = ix.text
  const years = useMemo(() => [...new Set(item.table.map(r => r.fy))].sort(), [item])
  const fy = years[years.length - 1]
  const cols = ['voted', 'budget', 'spent', 'other', 'all_in', 'left'] as const
  const head: Record<typeof cols[number], string> = { voted: t.voted, budget: t.budget, spent: t.spent, other: t.other, all_in: t.all_in, left: t.left }
  return (
    <ReportShell title={item.name} kicker={`${t.k_group} · ${item.cat}`} dataUrl={`/data/fy-breakdown/group/${item.slug}.json`}
      standfirst={item.what}
      meta={<p className="mt-3 text-[13px]"><span style={muted}>{t.members}:</span> {item.members.map((m, i) => (
        <span key={m.account}>{i ? ' · ' : ''}<a href={m.href} className="underline" style={link}>{m.name}</a></span>))}</p>}>
      {/* split, not summed: each line beside the other, the placements above the money */}
      <GroupCompare members={item.members} counts={item.counts} years={item.history.map(h => h.fy)} ix={ix} />
      {item.counts ? <GroupCounts c={item.counts} years={item.history.map(h => h.fy)} ix={ix} chart={false} /> : null}
      <RatesTable rates={item.members.flatMap(m => m.rates ?? [])} ix={ix} />
      <GroupSplit p={item.payers} ix={ix} />
      <GroupShifts rows={item.shifts} ix={ix} />
      <section className="mt-10">
        <H2>{t.each_h}</H2>
        <div className="overflow-x-auto">
          <table className="w-full text-[13px] tabular-nums">
            <thead><tr className="border-b" style={{ borderColor: 'var(--grid)' }}>
              <th className="text-left px-2 py-1.5">{t.year}</th><th className="text-left px-2 py-1.5" />
              {cols.map(c => <th key={c} className="text-right px-2 py-1.5 font-semibold">{head[c]}</th>)}</tr></thead>
            <tbody>
              {item.table.map((r, i) => (
                <tr key={`${r.fy}${r.href}`} className="border-b" style={{ borderColor: 'var(--grid)', borderTopWidth: i && item.table[i - 1].fy !== r.fy ? 2 : undefined }}>
                  <td className="px-2 py-1.5 font-semibold">{i && item.table[i - 1].fy === r.fy ? '' : r.fy}</td>
                  <td className="px-2 py-1.5 text-left"><a href={`${r.href}?fy=${encodeURIComponent(r.fy)}`} className="underline" style={link}>{r.name}</a></td>
                  {cols.map(c => <td key={c} className="px-2 py-1.5 text-right" style={c === 'left' && r.n.left < 0 ? { color: 'var(--thread-3)' } : undefined}>{r.t[c]}</td>)}
                </tr>))}
            </tbody>
          </table>
        </div>
      </section>
      <section className="mt-10"><H2>{t.both_h}</H2></section>
      <LineHistory h={item.history} ix={ix} bare />
      <PayerTraces p={item.payers} ix={{ ...ix, text: { ...t, payers_line: t.payers_group, trace_here: t.trace_here_group } }} fy={fy} />
      <Sources ix={ix} />
    </ReportShell>)
}

export function FyItem() {
  const at = itemFromPath(window.location.pathname)
  const [ix, setIx] = useState<ItemIndex | null>(null)
  const [item, setItem] = useState<LineItem | FundItem | GroupItem | null>(null)
  const [err, setErr] = useState(false)
  useNoIndex()
  useEffect(() => {
    if (!at) return
    let live = true
    Promise.all([loadIndex(), fetch(`/data/fy-breakdown/${at.kind}/${at.slug}.json`)
      .then(r => { if (!r.ok) throw new Error(String(r.status)); return r.json() })])
      .then(([i, it]) => { if (live) { setIx(i); setItem(it) } }, () => { if (live) { setErr(true); loadIndex().then(i => { if (live) setIx(i) }, () => {}) } })
    return () => { live = false }
  }, [at?.kind, at?.slug])  // eslint-disable-line react-hooks/exhaustive-deps
  if (!at || err) {
    return (
      <ReportShell title={ix?.text.not_found ?? ''} noPrint>
        {ix ? <p className="mt-4 text-[14px]"><a className="underline" style={link} href={ix.text.parent_href}>← {ix.text.parent}</a></p> : null}
      </ReportShell>)
  }
  if (!ix || !item) return <ReportShell title="" loading />
  return at.kind === 'line' ? <LinePage item={item as LineItem} ix={ix} />
    : at.kind === 'group' ? <GroupPage item={item as GroupItem} ix={ix} /> : <FundPage item={item as FundItem} ix={ix} />
}

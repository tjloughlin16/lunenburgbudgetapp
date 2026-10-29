/** WHAT OTHER FUNDS PAID FOR (fy-breakdown). TJ, 27 October 2026: "what the non-general fund paid
 *  for, in a table. so that we know per source what was paid for ... maybe we need a similar
 *  table for the other sources?"
 *
 *  The big table reads by school line; this one reads by FUND, for the page's year: every fund
 *  other than the school budget that spent on the schools, its spending in the six ways it can
 *  land, summing to everything it spent. A row opens a popup -- where its money went, what it
 *  bought (by its own account and by payee), every posting -- from
 *  /data/fy-breakdown/funds-<year>.json, fetched when a fund is opened.
 *  Every figure is formatted by scripts/build_fy_breakdown.py. */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { useFyYear } from './fy-year'
import { Bars, Chip, HeadTip, SortTable, WideScroll } from './fy-shared'
import { FUND_BASE, itemHrefs, useItemIndex } from './fy-items'
import { FundHistory, type FundHist } from './fy-item-history'
import { PopupActions } from './fy-item-link'
import { MoveGroups, type MoveGroup } from './fy-fund-moves'
import type { CustomProps } from './index'

type K = 'payee' | 'function' | 'later' | 'back' | 'capital' | 'between' | 'none' | 'total'
export type FundRow = { key: string; name: string; printed: string; program: string; cat: string; group: string; n: Record<K, number>; t: Record<K, string> }
type Year = { fy: string; rows: FundRow[]; total: string }
type Col = { id: K; label: string; means: string }
export type FundText = Record<'source' | 'category' | 'read' | 'tab_where' | 'tab_what' | 'tab_rows' | 'by_payee' | 'by_account' | 'went'
  | 'close' | 'loading' | 'failed' | 'none' | 'sum' | 'all_rows' | 'all_cats' | 'scroll' | 'filter'
  | 'c_memo' | 'c_to' | 'c_where' | 'c_amount' | 'c_date' | 'c_kind' | 'c_account' | 'all_kinds' | 'bought_note', string>
  & { tab_moves?: string; mv?: Record<string, string>; mv_classes?: { id: string; label: string }[] }
type T = FundText
export type FundData = { years: Year[]; columns: Col[]; groups: { id: string; label: string }[]; text: T }
type Data = FundData
type Pair = [string, string, number]
type Posting = [string, string, string, string, string, string, string, string, number]
export type Fund = { w: [string, string, string, number][]; b: [string, string, string, string, number][]; a: Pair[]; p: Pair[]; r: Posting[]
  /** cost re-booked between this fund and another this year, as the page's block groups it */
  mv?: MoveGroup[] }
type File = { fy: string; funds: Record<string, Fund> }

const muted = { color: 'var(--text-muted)' }, secondary = { color: 'var(--text-secondary)' }
const PAYER: Record<string, string> = { idea: 'var(--thread-2)', grants: 'var(--thread-5)', cb: 'var(--thread-4)',
  fees: 'var(--thread-3)', other: 'var(--thread-6, var(--text-secondary))' }
const FILES = new Map<string, Promise<File>>()
const load = (fy: string) => {
  if (!FILES.has(fy)) FILES.set(fy, fetch(`/data/fy-breakdown/funds-${fy.replace(/\D/g, '')}.json`)
    .then(r => { if (!r.ok) throw new Error(String(r.status)); return r.json() }))
  return FILES.get(fy)!
}

/** ONE FUND'S VIEW, two hosts: the popup on the breakdown page, and the fund's own page
 *  (/school-funds/<slug>), which passes the fund's postings in from its own file. */
export function FundBody({ r, fy, t, F, err = false, actions, bare = false, sticky = false, years }: {
  r: FundRow; fy: string; t: T; F: Fund | undefined; err?: boolean; actions?: React.ReactNode; bare?: boolean; sticky?: boolean
  /** the popup's "Across the years" tab; the fund's own page draws its history below instead */
  years?: { label: string; node: React.ReactNode } }) {
  const [tab, setTab] = useState<'where' | 'what' | 'rows' | 'moves' | 'years'>('where')
  const moves = !!(F?.mv?.length && t.mv && t.mv_classes)
  const pad = sticky ? 'px-4 sm:px-6' : ''
  return (<>
    <div className={sticky ? `sticky top-0 z-10 ${pad} pt-4 pb-3 border-b` : 'pb-3'} style={sticky ? { background: 'var(--surface-1, var(--bg))', borderColor: 'var(--grid)' } : undefined}>
      <div className="flex justify-between gap-4 items-start">
        <div>
          {bare ? null : <>
            <p className="text-[12px] uppercase tracking-wide" style={muted}>{fy} · {r.cat}</p>
            <h3 className="text-[19px] font-semibold leading-snug">{r.name}</h3>
          </>}
          <p className="text-[11.5px]" style={muted}>{r.printed}</p>
          <p className="text-[12.5px] mt-0.5" style={muted}>{r.program} · {r.t.total}</p>
        </div>
        {actions}
      </div>
      <div className="flex flex-wrap gap-1.5 mt-3">
        <Chip on={tab === 'where'} onClick={() => setTab('where')}>{t.tab_where}</Chip>
        <Chip on={tab === 'what'} onClick={() => setTab('what')}>{t.tab_what}</Chip>
        <Chip on={tab === 'rows'} onClick={() => setTab('rows')}>{t.tab_rows}</Chip>
        {moves ? <Chip on={tab === 'moves'} onClick={() => setTab('moves')}>{t.tab_moves}</Chip> : null}
        {years ? <Chip on={tab === 'years'} onClick={() => setTab('years')}>{years.label}</Chip> : null}
      </div>
    </div>
    <div className={`${pad} py-4`}>
      {tab === 'years' && years ? years.node
        : err ? <p className="text-[13px]" style={muted}>{t.failed}</p> : !F ? <p className="text-[13px]" style={muted}>{t.loading}</p>
        : tab === 'moves' && moves ? (
          <div className="max-w-3xl">
            <p className="text-[12.5px] mb-2" style={muted}>{t.mv!.what}</p>
            <MoveGroups groups={F.mv!} classes={t.mv_classes!} text={t.mv!} />
          </div>
        ) : tab === 'where' || tab === 'moves' ? (
          <div className="max-w-3xl"><Bars title={t.tab_where} items={F.w.map(([k, w, tx, v]) => ({ sub: k, label: w, text: tx, v }))} /></div>
        ) : tab === 'what' ? (
          <div className="space-y-6">
            {/* what it bought, in its own words: memo, who it was paid to, where it went */}
            <div>
              <p className="text-[12px] mb-1" style={muted}>{t.bought_note}</p>
              <SortTable filter={t.filter} count={t.all_rows} first={{ key: 'v', dir: -1 }}
                cols={[{ key: 'memo', label: t.c_memo, wide: true }, { key: 'to', label: t.c_to }, { key: 'where', label: t.c_where, wide: true }, { key: 'v', label: t.c_amount, right: true }]}
                rows={F.b.map(([memo, to, where, tx, v]) => ({ text: `${memo} ${to} ${where}`,
                  cells: { memo, to, where: <span style={where.startsWith('No school line') ? muted : secondary}>{where}</span>, v: tx },
                  sort: { memo, to, where, v } }))} />
            </div>
            <div className="grid gap-6 md:grid-cols-2">
              <Bars title={t.by_account} items={F.a.map(([l, tx, v]) => ({ label: l, text: tx, v }))} />
              <Bars title={t.by_payee} items={F.p.map(([l, tx, v]) => ({ label: l, text: tx, v }))} />
            </div>
          </div>
        ) : (
          <SortTable filter={t.filter} count={t.all_rows} first={{ key: 'date', dir: 1 }}
            pick={{ key: 'kind', values: [...new Set(F.r.map(x => x[2]))].sort() }} pickAll={t.all_kinds}
            cols={[{ key: 'date', label: t.c_date }, { key: 'kind', label: t.c_kind }, { key: 'to', label: t.c_to },
              { key: 'memo', label: t.c_memo, wide: true }, { key: 'account', label: t.c_account }, { key: 'where', label: t.c_where, wide: true },
              { key: 'v', label: t.c_amount, right: true }]}
            rows={F.r.map(x => ({ text: `${x[2]} ${x[3]} ${x[4]} ${x[5]} ${x[6]}`,
              cells: { date: <span className="whitespace-nowrap" style={secondary}>{x[1]}</span>, kind: <span className="whitespace-nowrap" style={muted}>{x[2]}</span>,
                to: x[3] || <span style={muted}>—</span>, memo: <span style={secondary}>{x[4]}</span>, account: <span style={secondary}>{x[5]}</span>,
                where: <span style={secondary}>{x[6]}</span>, v: x[7] },
              sort: { date: x[0], kind: x[2], to: x[3], memo: x[4], account: x[5], where: x[6], v: x[8] } }))} />)}
    </div>
  </>)
}

function FundView({ r, fy, t, onClose }: { r: FundRow; fy: string; t: T; onClose: () => void }) {
  const [file, setFile] = useState<File | null>(null)
  const [err, setErr] = useState(false)
  const box = useRef<HTMLDivElement>(null)
  const ix = useItemIndex()
  const hrefs = itemHrefs(ix)
  const page = hrefs.fund(r.key)
  // the programme's own page file carries its history across the journal's years
  const [hist, setHist] = useState<FundHist[] | null>(null)
  useEffect(() => { let live = true; load(fy).then(f => { if (live) setFile(f) }, () => { if (live) setErr(true) }); return () => { live = false } }, [fy])
  useEffect(() => {
    if (!page) return
    let live = true
    fetch(`/data/fy-breakdown/fund/${page.slice(FUND_BASE.length)}.json`).then(x => x.ok ? x.json() : null)
      .then((it: { history?: FundHist[] } | null) => { if (live && it?.history) setHist(it.history) }, () => {})
    return () => { live = false }
  }, [page])
  useEffect(() => {
    const key = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', key)
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    box.current?.focus()
    return () => { window.removeEventListener('keydown', key); document.body.style.overflow = prev }
  }, [onClose])
  return createPortal(
    <div className="fixed inset-0 z-50 flex items-start justify-center p-2 sm:p-6" style={{ background: 'rgba(0,0,0,0.45)' }} onClick={onClose}>
      <div ref={box} tabIndex={-1} role="dialog" aria-modal="true" aria-label={r.name}
        className="w-full max-w-6xl max-h-full overflow-y-auto rounded-lg shadow-xl outline-none"
        style={{ background: 'var(--surface-1, var(--bg))', border: '1px solid var(--grid)' }} onClick={e => e.stopPropagation()}>
        <FundBody r={r} fy={fy} t={t} F={file?.funds[r.key]} err={err} sticky
          years={hist && ix ? { label: ix.text.hist_h, node: <FundHistory h={hist} ix={ix} bare
            cols={(ix.frame.fund as { columns: { id: string; label: string }[] }).columns} /> } : undefined}
          actions={<PopupActions href={hrefs.fund(r.key)} fy={fy} close={t.close} onClose={onClose} />} />
      </div>
    </div>, document.body)
}

export default function FySourceTable({ data, alt }: CustomProps) {
  const d = data as Data
  const t = d.text
  const fys = useMemo(() => d.years.map(v => v.fy), [d])
  const [fy] = useFyYear(fys)
  const y = d.years[Math.max(0, fys.indexOf(fy))]
  const [grp, setGrp] = useState('')
  const [sort, setSort] = useState<{ k: K | 'cat'; dir: 1 | -1 }>({ k: 'total', dir: -1 })
  const [open, setOpen] = useState<string | null>(null)
  const close = useCallback(() => setOpen(null), [])
  const rows = useMemo(() => y.rows.filter(r => !grp || r.group === grp).sort((a, b) =>
    sort.k === 'cat' ? sort.dir * b.cat.localeCompare(a.cat) || b.n.total - a.n.total
      : sort.dir * (a.n[sort.k] - b.n[sort.k]) || a.name.localeCompare(b.name)), [y, grp, sort])
  const openRow = open ? y.rows.find(r => r.key === open) ?? null : null
  const head = (c: Col) => (
    <th key={c.id} className={`px-2 py-1.5 text-right align-bottom cursor-pointer select-none ${c.id === 'total' ? 'border-l' : ''}`}
      style={{ borderColor: 'var(--grid)' }} onClick={() => setSort(s => ({ k: c.id, dir: s.k === c.id ? (-s.dir as 1 | -1) : -1 }))}
      aria-sort={sort.k === c.id ? (sort.dir < 0 ? 'descending' : 'ascending') : 'none'}>
      <span className="block text-[15px] leading-none mb-1" style={muted}>{c.id === 'total' ? '=' : c.id === 'payee' ? ' ' : '+'}</span>
      <HeadTip label={c.label} means={c.means}><span className="font-semibold">{c.label}{sort.k === c.id ? (sort.dir < 0 ? ' ↓' : ' ↑') : ''}</span></HeadTip></th>)
  return (
    <figure aria-label={alt}>
      <p className="text-[14px] leading-snug max-w-3xl" style={secondary}>{t.read}</p>
      <div className="flex flex-wrap gap-1.5 items-center mt-3">
        <Chip on={!grp} onClick={() => setGrp('')}>{t.all_cats}</Chip>
        {d.groups.filter(g => y.rows.some(r => r.group === g.id)).map(g => (
          <Chip key={g.id} on={grp === g.id} onClick={() => setGrp(g.id)}>
            <span className="inline-block w-2 h-2 rounded-[1px] mr-1 align-middle" style={{ background: PAYER[g.id] }} />{g.label}</Chip>))}
      </div>
      <WideScroll cue={t.scroll}>
        <table className="w-full text-[13px] tabular-nums border-collapse">
          <thead>
            <tr className="border-b" style={{ borderColor: 'var(--grid)' }}>
              <th className="px-2 py-1.5 text-left align-bottom font-semibold">{t.source}</th>
              <th className="px-2 py-1.5 text-left align-bottom font-semibold cursor-pointer select-none"
                onClick={() => setSort(s => ({ k: 'cat', dir: s.k === 'cat' ? (-s.dir as 1 | -1) : -1 }))}>
                {t.category}{sort.k === 'cat' ? (sort.dir < 0 ? ' ↓' : ' ↑') : ''}</th>
              {d.columns.map(head)}
            </tr>
          </thead>
          <tbody>
            {rows.map(r => (
              <tr key={r.key} className="border-b cursor-pointer hover:bg-[var(--surface-2)]" style={{ borderColor: 'var(--grid)' }}
                onClick={() => setOpen(r.key)} aria-haspopup="dialog">
                <td className="px-2 py-1.5 text-left min-w-[14rem]"><span className="mr-1" style={muted}>↗</span>{r.name}
                  <span className="block pl-4 text-[11px]" style={muted}>{r.printed}</span></td>
                <td className="px-2 py-1.5 text-left min-w-[9rem]" style={secondary}>
                  <span className="inline-block w-2 h-2 rounded-[1px] mr-1.5 align-middle" style={{ background: PAYER[r.group] }} />{r.cat}</td>
                {d.columns.map(c => (
                  <td key={c.id} className={`px-2 py-1.5 text-right whitespace-nowrap ${c.id === 'total' ? 'border-l font-semibold' : ''}`}
                    style={{ borderColor: 'var(--grid)' }}>
                    {Math.abs(r.n[c.id]) < 0.5 ? <span style={muted}>·</span> : r.t[c.id]}</td>))}
              </tr>))}
            {!grp ? (
              <tr>
                <td className="px-2 py-1.5 font-semibold" colSpan={2 + d.columns.length - 1}>{t.sum}</td>
                <td className="px-2 py-1.5 text-right font-semibold border-l" style={{ borderColor: 'var(--grid)' }}>{y.total}</td>
              </tr>) : null}
          </tbody>
        </table>
      </WideScroll>
      {openRow ? <FundView r={openRow} fy={y.fy} t={t} onClose={close} /> : null}
    </figure>)
}

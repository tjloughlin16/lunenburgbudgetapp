/** WHO THE SCHOOLS PAID, AGAINST THE YEAR BEFORE (fy-breakdown). TJ, 28 October 2026: "a table that
 *  shows every vendor / payee paid for this FY, how much, and compared to just the previous year
 *  (as a diff), call out new payees, call out dropped/unpaid payees from the year before. and
 *  every payee becomes clickable to show what we bought from them, as well as the school lines
 *  they are associated to."
 *
 *  The page's year: every payee paid by invoice, from any school fund, against the year before,
 *  with the change, and NEW / NOT PAID THIS YEAR called out. A row opens what was bought from
 *  them, the lines and funds it was paid from, and every payment. A payee not paid this year
 *  opens on the year before. Everything is in /data/fy-breakdown/payees-<year>.json, fetched for
 *  the year shown, and formatted by scripts/fy_payees.py. */
import { useEffect, useMemo, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { useFyYear } from './fy-year'
import { Bars, Chip, SortTable, WideScroll } from './fy-shared'
import type { CustomProps } from './index'

type Pair4 = [string, string, string, number]
type Pay = [string, string, string, string, string, string, number]
type Row = { k: string; n: string; v: number; t: string; g: number; gt: string | null; gs: number | null; gp: string | null
  kt: string | null; ks: number | null; kp: string | null; pv: number | null; pt: string | null; dv: number | null; dt: string | null
  s: '' | 'new' | 'dropped'; c: number; of: number | null; l: Pair4[]; b: Pair4[]; r: Pay[] }
type File = { fy: number; prev: number | null; rows: Row[]; total: string }
type Year = { fy: string; prev: string | null; n: number; new: number; dropped: number; total: string; new_total: string; dropped_total: string
  gf: string; gf_share: string; kept: string; kept_share: string; back: string }
type Data = { years: Year[]; show: number; text: Record<string, string> }

const muted = { color: 'var(--text-muted)' }, secondary = { color: 'var(--text-secondary)' }
const UP = 'var(--thread-3)', DOWN = 'var(--thread-2)'
const FILES = new Map<string, Promise<File>>()
const load = (fy: string) => {
  if (!FILES.has(fy)) FILES.set(fy, fetch(`/data/fy-breakdown/payees-${fy.replace(/\D/g, '')}.json`)
    .then(r => { if (!r.ok) throw new Error(String(r.status)); return r.json() }))
  return FILES.get(fy)!
}

function Status({ s, t }: { s: Row['s']; t: Record<string, string> }) {
  if (!s) return null
  return (
    <span className="ml-1.5 inline-block px-1.5 py-px rounded text-[11px] font-semibold align-[1px] whitespace-nowrap"
      style={s === 'new' ? { background: 'color-mix(in srgb, var(--thread-3) 18%, transparent)', color: UP }
        : { background: 'var(--surface-2)', color: 'var(--text-muted)', border: '1px dashed var(--grid)' }}>
      {s === 'new' ? t.new : t.dropped}</span>)
}

function PayeeView({ r, y, t, onClose }: { r: Row; y: Year; t: Record<string, string>; onClose: () => void }) {
  const [tab, setTab] = useState<'what' | 'lines' | 'rows'>('what')
  const box = useRef<HTMLDivElement>(null)
  useEffect(() => {
    const key = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', key)
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    box.current?.focus()
    return () => { window.removeEventListener('keydown', key); document.body.style.overflow = prev }
  }, [onClose])
  // A payee not paid this year opens on the year before: what it used to be paid for
  const shownFy = r.of ? y.prev : y.fy
  return createPortal(
    <div className="fixed inset-0 z-50 flex items-start justify-center p-2 sm:p-6" style={{ background: 'rgba(0,0,0,0.45)' }} onClick={onClose}>
      <div ref={box} tabIndex={-1} role="dialog" aria-modal="true" aria-label={r.n}
        className="w-full max-w-5xl max-h-full overflow-y-auto rounded-lg shadow-xl outline-none"
        style={{ background: 'var(--surface-1, var(--bg))', border: '1px solid var(--grid)' }} onClick={e => e.stopPropagation()}>
        <div className="sticky top-0 z-10 px-4 sm:px-6 pt-4 pb-3 border-b" style={{ background: 'var(--surface-1, var(--bg))', borderColor: 'var(--grid)' }}>
          <div className="flex justify-between gap-4 items-start">
            <div>
              <p className="text-[12px] uppercase tracking-wide" style={muted}>{t.payee}</p>
              <h3 className="text-[19px] font-semibold leading-snug">{r.n}<Status s={r.s} t={t} /></h3>
              <p className="text-[13px] mt-1 tabular-nums">
                <span className="font-semibold">{y.fy} {r.t}</span>
                {r.gt !== null && r.gp !== null ? <span style={secondary}> · {r.gt} ({r.gp}) {t.gf_of}</span> : null}
                {r.kt !== null && r.kp !== null && r.kt !== r.gt ? <span style={secondary}> · {r.kt} ({r.kp}) {t.kept_of}, {t.ours}</span> : null}
                {r.pt !== null ? <span style={secondary}> · {y.prev} {r.pt}</span> : null}
                {r.dt !== null && r.dv ? <span className="font-semibold" style={{ color: r.dv > 0 ? UP : DOWN }}> · {r.dt}</span> : null}
              </p>
              {r.of ? <p className="text-[12.5px] mt-0.5" style={muted}>{t.shown_before} {y.prev}.</p> : null}
            </div>
            <button type="button" onClick={onClose} className="px-2.5 py-1 rounded border text-[13px]" style={{ borderColor: 'var(--grid)' }}>{t.close} ✕</button>
          </div>
          <div className="flex gap-1.5 mt-3">
            <Chip on={tab === 'what'} onClick={() => setTab('what')}>{t.tab_what}</Chip>
            <Chip on={tab === 'lines'} onClick={() => setTab('lines')}>{t.tab_lines}</Chip>
            <Chip on={tab === 'rows'} onClick={() => setTab('rows')}>{t.tab_rows} · {r.r.length}</Chip>
          </div>
        </div>
        <div className="px-4 sm:px-6 py-4">
          {tab === 'what' ? (
            <div>
              <p className="text-[12px] mb-1" style={muted}>{shownFy} · {t.what_note}</p>
              <SortTable filter={t.filter} count={t.rows_shown} first={{ key: 'v', dir: -1 }}
                cols={[{ key: 'memo', label: t.c_memo, wide: true }, { key: 'line', label: t.c_line, wide: true }, { key: 'v', label: t.c_amount, right: true }]}
                rows={r.b.map(([memo, line, tx, v]) => ({ text: `${memo} ${line}`, cells: { memo, line: <span style={secondary}>{line}</span>, v: tx },
                  sort: { memo, line, v } }))} />
            </div>
          ) : tab === 'lines' ? (
            <div className="max-w-3xl">
              <Bars title={`${shownFy} · ${t.tab_lines}`} items={r.l.map(([line, fund, tx, v]) => ({ label: line, sub: fund === t.school ? undefined : `${fund} ·`, text: tx, v }))} />
              <p className="text-[12px] mt-3" style={muted}>{t.lines_note}</p>
            </div>
          ) : (
            <SortTable filter={t.filter} count={t.rows_shown} first={{ key: 'date', dir: 1 }}
              cols={[{ key: 'date', label: t.c_date }, { key: 'memo', label: t.c_memo, wide: true }, { key: 'line', label: t.c_line, wide: true },
                { key: 'fund', label: t.c_fund }, { key: 'v', label: t.c_amount, right: true }]}
              rows={r.r.map(x => ({ text: `${x[2]} ${x[3]} ${x[4]}`,
                cells: { date: <span className="whitespace-nowrap" style={secondary}>{x[1]}</span>, memo: x[2], line: <span style={secondary}>{x[3]}</span>,
                  fund: <span style={muted}>{x[4]}</span>, v: x[5] },
                sort: { date: x[0], memo: x[2], line: x[3], fund: x[4], v: x[6] } }))} />)}
        </div>
      </div>
    </div>, document.body)
}

type Key = 'n' | 'v' | 'g' | 'gs' | 'ks' | 'pv' | 'dv' | 'c'
export default function FyPayees({ data, alt }: CustomProps) {
  const d = data as Data
  const t = d.text
  const fys = useMemo(() => d.years.map(v => v.fy), [d])
  const [fy] = useFyYear(fys)
  const y = d.years[Math.max(0, fys.indexOf(fy))]
  const [file, setFile] = useState<File | null>(null)
  const [err, setErr] = useState(false)
  const [only, setOnly] = useState<'' | 'new' | 'dropped'>('')
  const [q, setQ] = useState('')
  const [all, setAll] = useState(false)
  const [sort, setSort] = useState<{ key: Key; dir: 1 | -1 }>({ key: 'v', dir: -1 })
  const [view, setView] = useState<Row | null>(null)
  useEffect(() => {
    let live = true
    setFile(null); setErr(false)
    load(y.fy).then(f => { if (live) setFile(f) }, () => { if (live) setErr(true) })
    return () => { live = false }
  }, [y.fy])
  const rows = useMemo(() => {
    if (!file) return []
    const ql = q.trim().toLowerCase()
    const out = file.rows.filter(r => (!only || r.s === only) && (!ql || r.n.toLowerCase().includes(ql)
      || r.b.some(b => b[0].toLowerCase().includes(ql) || b[1].toLowerCase().includes(ql))))
    const val = (r: Row) => sort.key === 'n' ? r.n : sort.key === 'dv' ? Math.abs(r.dv ?? 0) : sort.key === 'gs' ? (r.gs ?? -1) : sort.key === 'ks' ? (r.ks ?? -1) : (r[sort.key] ?? 0)
    return out.sort((a, b) => {
      const x = val(a), z = val(b)
      return sort.dir * (typeof x === 'number' && typeof z === 'number' ? x - z : String(x).localeCompare(String(z)))
    })
  }, [file, only, q, sort])
  const shown = all || q || only ? rows : rows.slice(0, d.show)
  const head = (key: Key, label: string, right = true, means?: string) => (
    <th title={means} className={`px-2 py-1.5 font-semibold whitespace-nowrap cursor-pointer select-none ${right ? 'text-right' : 'text-left'}`}
      aria-sort={sort.key === key ? (sort.dir < 0 ? 'descending' : 'ascending') : 'none'}
      onClick={() => setSort(s => ({ key, dir: s.key === key ? (s.dir === 1 ? -1 : 1) : (right ? -1 : 1) }))}>
      {label}{sort.key === key ? (sort.dir < 0 ? ' ↓' : ' ↑') : ''}</th>)
  const num = 'px-2 py-1.5 text-right whitespace-nowrap tabular-nums'
  return (
    <figure aria-label={alt}>
      <p className="text-[13.5px]">
        <span className="font-semibold tabular-nums">{y.n}</span> <span style={secondary}>{t.paid_in} {y.fy}, {y.total}; {y.gf} ({y.gf_share}) {t.gf_of}, {y.kept} ({y.kept_share}) {t.kept_of}</span>
        {y.prev ? <>
          {' · '}<span className="font-semibold" style={{ color: UP }}>{y.new} {t.new_l}</span> <span style={secondary}>({y.new_total})</span>
          {' · '}<span className="font-semibold" style={muted}>{y.dropped} {t.dropped_l}</span> <span style={secondary}>({y.dropped_total} {t.in} {y.prev})</span>
        </> : <span style={muted}> · {t.no_prev}</span>}
      </p>
      <div className="flex flex-wrap gap-2 mt-2 items-center">
        <Chip on={only === ''} onClick={() => setOnly('')}>{t.every}</Chip>
        {y.prev ? <>
          <Chip on={only === 'new'} onClick={() => setOnly('new')}>{t.new}</Chip>
          <Chip on={only === 'dropped'} onClick={() => setOnly('dropped')}>{t.dropped}</Chip>
        </> : null}
        <input value={q} onChange={e => setQ(e.target.value)} placeholder={t.filter} aria-label={t.filter}
          className="w-full sm:w-72 px-2 py-1 rounded border text-[13px]"
          style={{ borderColor: 'var(--grid)', background: 'var(--surface-1)', color: 'var(--text-primary)' }} />
        <span className="text-[12.5px]" style={muted}>{t.open}</span>
      </div>
      {err ? <p className="text-[13px] mt-3" style={muted}>{t.failed}</p> : !file ? <p className="text-[13px] mt-3" style={muted}>{t.loading}</p> : (
        <WideScroll cue={t.payees}>
          <table className="w-full min-w-[900px] text-[13px] border-collapse">
            <thead>
              <tr className="border-b" style={{ borderColor: 'var(--grid)' }}>
                {head('n', t.payee, false)}{head('v', y.fy)}{head('g', t.gf)}{head('gs', t.gf_share)}{head('ks', t.kept_share, true, t.kept_means)}{y.prev ? <>{head('pv', y.prev)}{head('dv', t.change)}</> : null}{head('c', t.payments)}
              </tr>
            </thead>
            <tbody>
              {shown.map(r => (
                <tr key={r.k} className="border-b align-top cursor-pointer hover:bg-[var(--surface-2)]" style={{ borderColor: 'var(--grid)' }}
                  onClick={() => setView(r)} tabIndex={0} onKeyDown={e => { if (e.key === 'Enter') setView(r) }}>
                  <td className="px-2 py-1.5 min-w-[14rem]"><span className="underline decoration-dotted underline-offset-2">{r.n}</span><Status s={r.s} t={t} />
                    {r.l[0] ? <span className="block text-[11.5px]" style={muted}>{r.l[0][0]}{r.l.length > 1 ? ` · +${r.l.length - 1} ${t.more_lines}` : ''}</span> : null}</td>
                  <td className={num} style={r.v ? undefined : muted}>{r.t}</td>
                  <td className={num} style={secondary}>{r.gt ?? ''}</td>
                  <td className={num} style={secondary}>{r.gp ?? ''}</td>
                  <td className={num} style={{ color: 'var(--text-secondary)', background: 'var(--estimate-bg, color-mix(in srgb, var(--thread-4) 7%, transparent))' }}
                    title={r.kt ? `${r.kt} ${t.kept_of}` : undefined}>{r.kp ?? ''}</td>
                  {y.prev ? <>
                    <td className={num} style={secondary}>{r.pt}</td>
                    <td className={num} style={{ color: !r.dv ? 'var(--text-muted)' : r.dv > 0 ? UP : DOWN, fontWeight: 600 }}>{r.dv ? r.dt : '—'}</td>
                  </> : null}
                  <td className={num} style={secondary}>{r.c || ''}</td>
                </tr>))}
            </tbody>
          </table>
        </WideScroll>)}
      {file ? <p className="text-[12px] mt-1" style={muted}>
        <span className="inline-block w-3 h-3 align-[-2px] mr-1 rounded-sm" style={{ background: 'color-mix(in srgb, var(--thread-4) 14%, transparent)' }} />
        {t.kept_share}: {t.kept_means} {y.back} {t.back_l}.</p> : null}
      {file && !q && !only && rows.length > d.show ? (
        <button type="button" className="mt-2 text-[13px] underline" style={{ color: 'var(--link, var(--thread-2))' }}
          onClick={() => setAll(a => !a)}>{all ? t.show_fewer : `${t.show_all} ${rows.length}`}</button>) : null}
      <p className="text-[12px] mt-2" style={muted}>{t.grain}</p>
      {view ? <PayeeView r={view} y={y} t={t} onClose={() => setView(null)} /> : null}
    </figure>)
}

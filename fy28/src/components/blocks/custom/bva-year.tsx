/** LINE BY LINE, ONE YEAR (budget-against-actual). Follows the page's year picker (fy-year.ts).
 *
 *  What a year can show depends on the record that holds it, and the view says which in a banner
 *  at its top (TJ, 29 October 2026: graceful degradation by evidence):
 *   - a JOURNAL year (FY2023 on): the three flags, each with its rule and threshold (ours) and
 *     its lines, largest first, a line opening on its transfers and linking to its page; then
 *     every school line, voted to left.
 *   - a BUDGET-DOCUMENT year: each flag says it cannot be shown, rather than vanishing (rule 7c);
 *     then every line the documents print, budget against actual, with whether it is counted.
 *  Every string and figure is the payload's (scripts/build_budget_against_actual.py). */
import { useMemo, useState } from 'react'
import type { CustomProps } from './index'
import { useFyYear } from './fy-year'
import { itemHrefs, useItemIndex, withYear } from './fy-items'
import { Chip, HeadTip, WideScroll } from './fy-shared'

type Move = { date: string; memo: string; v: string; others: string[] }
type LRow = { name: string; account: string; cat: string; f: ('under' | 'over' | 'restart')[]
  n: Record<string, number>; t: Record<string, string>
  under?: { gap: string; covered: string; uncovered: string; n: number; recharged: string }
  over?: { unspent: string; out: string; left: string; n: number; recharged: string }
  restart?: { over: string; prior_spent: string; prior_budget: string; cut: boolean; above_budget: boolean
    thin: boolean; recharged: string; n: number }
  prior?: { spent: string; budget: string }; moves?: Move[] }
type BRow = { name: string; b: number; a: number; d: number; bt: string; at: string; dt: string; pt: string; why: string }
type Year = { fy: string; src: 'ledger' | 'books' | 'none'; rows: (LRow | BRow)[]
  counts?: Record<string, string>; new?: string | null; no_restart?: string | null
  totals?: { voted: string; spent: string; left: string }; counted?: string }
type Flag = { name: string; rule: string; means: string }
type Data = { years: Year[]; flags: Record<'under' | 'over' | 'restart', Flag> & { ours: string; why: string }
  text: Record<string, string> & { cols: Record<string, string>; means: Record<string, string>; books_cols: Record<string, string> } }

const muted = { color: 'var(--text-muted)' }
const link = { color: 'var(--link, var(--thread-2))' }
const KEYS = ['under', 'over', 'restart'] as const
const FIRST = 6
const TONE: Record<string, string> = { under: 'var(--thread-1)', over: 'var(--thread-2)', restart: 'var(--thread-4)' }

function Banner({ text, strong }: { text: string; strong: boolean }) {
  return (
    <p className={`text-[14px] leading-snug rounded px-3 py-2 ${strong ? 'font-semibold' : ''}`}
      style={{ background: strong ? 'var(--surface-3)' : 'transparent', borderLeft: `3px solid ${strong ? 'var(--text-secondary)' : 'var(--grid)'}` }}>{text}</p>)
}

function Figs({ items }: { items: [string, string][] }) {
  return (
    <span className="flex flex-wrap gap-x-3 gap-y-0.5 text-[12.5px] tabular-nums">
      {items.filter(([, v]) => v).map(([k, v]) => <span key={k}><span style={muted}>{k} </span><span className="font-semibold">{v}</span></span>)}
    </span>)
}

function FlagItem({ r, k, t, fy, href }: { r: LRow; k: typeof KEYS[number]; t: Data['text']; fy: string; href?: string }) {
  const [open, setOpen] = useState(false)
  const figs: [string, string][] = k === 'under' && r.under
    ? [[t.gap, r.under.gap], [t.covered, r.under.covered], [t.uncovered, r.under.uncovered], [t.recharged, r.under.recharged]]
    : k === 'over' && r.over
      ? [[t.unspent, r.over.unspent], [t.moved_out, r.over.out], [t.left_end, r.over.left], [t.recharged, r.over.recharged]]
      : r.restart ? [[t.over_by, r.restart.over], [t.prior_spent, r.restart.prior_spent], [t.prior_budget, r.restart.prior_budget]] : []
  const notes = k === 'restart' && r.restart ? [
    r.restart.cut ? t.cut : '', r.restart.above_budget ? t.above : t.below, r.restart.thin ? t.thin : ''].filter(Boolean) : []
  return (
    <li className="py-2 border-b" style={{ borderColor: 'var(--grid)' }}>
      <div className="flex flex-wrap justify-between gap-x-3">
        <span className="text-[13.5px]">
          {href ? <a href={withYear(href, fy)} className="underline" style={link}>{r.name}</a> : r.name}
          <span className="block text-[11.5px]" style={muted}>{r.cat} · {t.cols.voted} {r.t.voted} · {t.cols.spent} {r.t.spent}</span>
        </span>
        {r.moves?.length ? (
          <button type="button" className="text-[12px] underline self-start" style={link} aria-expanded={open}
            onClick={() => setOpen(o => !o)}>{t.transfers} ({r.moves.length})</button>) : null}
      </div>
      <div className="mt-1"><Figs items={figs} /></div>
      {notes.map(n => <p key={n} className="text-[12px] mt-0.5" style={muted}>{n}</p>)}
      {open && r.moves ? (
        <ul className="mt-1.5 space-y-1 text-[12px]">
          {r.moves.map((m, i) => (
            <li key={i} className="pl-2 border-l" style={{ borderColor: 'var(--grid)' }}>
              <span className="tabular-nums font-semibold">{m.v}</span> · {m.date} · <span style={muted}>{m.memo}</span>
              {m.others.length ? <span className="block" style={muted}>{t.other_side} {m.others.join(', ')}</span> : null}
            </li>))}
        </ul>) : null}
    </li>)
}

function FlagPanel({ k, y, d, href }: { k: typeof KEYS[number]; y: Year; d: Data; href: (a: string) => string | undefined }) {
  const [all, setAll] = useState(false)
  const t = d.text, f = d.flags[k]
  const rows = (y.rows as LRow[]).filter(r => r[k]).sort((a, b) => (b[k]!.n) - (a[k]!.n))
  const blocked = y.src !== 'ledger' ? (k === 'restart' ? t.not_shown_restart : t.not_shown) : k === 'restart' && y.no_restart ? y.no_restart : null
  return (
    <section className="rounded border p-3" style={{ borderColor: 'var(--grid)', borderTop: `3px solid ${TONE[k]}` }}>
      <p className="text-[15px] font-semibold">{f.name}
        {!blocked ? <span className="ml-2 tabular-nums">{y.counts?.[k]}</span> : null}
        {!blocked ? <span className="ml-1 text-[12px] font-normal" style={muted}>{t.lines_n} {t.flagged}</span> : null}</p>
      <p className="text-[12.5px] mt-1">{f.rule}</p>
      <p className="text-[12.5px] mt-1" style={muted}>{f.means}</p>
      {blocked ? <p className="text-[13px] mt-2 font-semibold" style={{ color: 'var(--text-secondary)' }}>{blocked}</p> : (
        <>
          <ul className="mt-2">{(all ? rows : rows.slice(0, FIRST)).map(r => (
            <FlagItem key={r.account} r={r} k={k} t={t} fy={y.fy} href={href(r.account)} />))}</ul>
          {rows.length > FIRST ? (
            <button type="button" className="mt-2 text-[12.5px] underline" style={link} onClick={() => setAll(a => !a)}>
              {all ? t.show_fewer : `${t.show_all} (${rows.length})`}</button>) : null}
          {k === 'restart' && y.new ? <p className="text-[12px] mt-2" style={muted}>{y.new}</p> : null}
        </>)}
    </section>)
}

type Sort = { key: string; dir: 1 | -1 }

function LedgerTable({ y, d, href }: { y: Year; d: Data; href: (a: string) => string | undefined }) {
  const t = d.text
  const [q, setQ] = useState('')
  const [only, setOnly] = useState(false)
  const [sort, setSort] = useState<Sort | null>(null)
  const cols = ['voted', 'transfers', 'carried', 'budget', 'spent', 'left']
  const rows = useMemo(() => {
    const ql = q.trim().toLowerCase()
    const out = (y.rows as LRow[]).filter(r => (!only || r.f.length) && (!ql || `${r.name} ${r.cat}`.toLowerCase().includes(ql)))
    if (!sort) return out
    return [...out].sort((a, b) => sort.dir * (sort.key === 'name' ? a.name.localeCompare(b.name)
      : sort.key === 'cat' ? a.cat.localeCompare(b.cat) : (a.n[sort.key] ?? 0) - (b.n[sort.key] ?? 0)))
  }, [y, q, only, sort])
  const head = (key: string, label: string, right: boolean, means?: string) => (
    <th key={key} className={`px-2 py-1 font-semibold whitespace-nowrap cursor-pointer select-none ${right ? 'text-right' : 'text-left'}`}
      onClick={() => setSort(s => ({ key, dir: s?.key === key ? (s.dir === 1 ? -1 : 1) : (right ? -1 : 1) }))}>
      {means ? <HeadTip label={label} means={means}>{label}</HeadTip> : label}{sort?.key === key ? (sort.dir < 0 ? ' ↓' : ' ↑') : ''}</th>)
  return (
    <div className="mt-6">
      <div className="flex flex-wrap gap-2 items-center">
        <input value={q} onChange={e => setQ(e.target.value)} placeholder={t.filter} aria-label={t.filter}
          className="w-full max-w-xs px-2 py-1 rounded border text-[13px]" style={{ borderColor: 'var(--grid)', background: 'var(--surface-1)', color: 'var(--text-primary)' }} />
        <Chip on={!only} onClick={() => setOnly(false)}>{t.every}</Chip>
        <Chip on={only} onClick={() => setOnly(true)}>{t.only}</Chip>
        <span className="text-[12px]" style={muted}>{rows.length} {t.lines_n} · {t.sort}</span>
      </div>
      <WideScroll cue={t.cols.flags}>
        <table className="w-full text-[12.5px] tabular-nums border-collapse min-w-[900px]">
          <thead>
            <tr className="border-b text-[12px]" style={{ borderColor: 'var(--grid)', color: 'var(--text-secondary)' }}>
              {head('name', t.cols.name, false)}{head('cat', t.cols.cat, false)}
              {cols.map(c => head(c, t.cols[c], true, t.means[c]))}
              <th className="px-2 py-1 text-left font-semibold">{t.cols.flags}</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(r => {
              const h = href(r.account)
              return (
                <tr key={r.account} className="border-b align-top" style={{ borderColor: 'var(--grid)' }}>
                  <td className="px-2 py-1 min-w-[14rem]">{h ? <a href={withYear(h, y.fy)} className="underline" style={link}>{r.name}</a> : r.name}</td>
                  <td className="px-2 py-1" style={muted}>{r.cat}</td>
                  {cols.map(c => <td key={c} className={`px-2 py-1 text-right whitespace-nowrap ${c === 'left' ? 'font-semibold' : ''}`}
                    style={c === 'left' && r.n.left < 0 ? { color: 'var(--thread-1)' } : undefined}>{r.t[c]}</td>)}
                  <td className="px-2 py-1 whitespace-nowrap">{r.f.map(k => (
                    <span key={k} className="inline-block mr-1 px-1.5 rounded text-[11px]" style={{ border: `1px solid ${TONE[k]}`, color: 'var(--text-primary)' }}>{d.flags[k].name}</span>))}</td>
                </tr>)
            })}
            {!q && !only && y.totals ? (
              <tr className="font-semibold">
                <td className="px-2 py-1">{t.total}</td><td />
                <td className="px-2 py-1 text-right">{y.totals.voted}</td><td colSpan={3} />
                <td className="px-2 py-1 text-right">{y.totals.spent}</td>
                <td className="px-2 py-1 text-right">{y.totals.left}</td><td />
              </tr>) : null}
          </tbody>
        </table>
      </WideScroll>
    </div>)
}

function BooksTable({ y, d }: { y: Year; d: Data }) {
  const t = d.text, c = t.books_cols
  const [sort, setSort] = useState<Sort>({ key: 'b', dir: -1 })
  const rows = useMemo(() => [...(y.rows as BRow[])].sort((a, b) => sort.dir * (sort.key === 'name' ? a.name.localeCompare(b.name)
    : sort.key === 'why' ? a.why.localeCompare(b.why) : sort.key === 'p' ? (a.b ? a.a / a.b : 0) - (b.b ? b.a / b.b : 0)
      : ((a as unknown as Record<string, number>)[sort.key] ?? 0) - ((b as unknown as Record<string, number>)[sort.key] ?? 0))), [y, sort])
  const head = (key: string, label: string, right: boolean) => (
    <th key={key} className={`px-2 py-1 font-semibold whitespace-nowrap cursor-pointer select-none ${right ? 'text-right' : 'text-left'}`}
      onClick={() => setSort(s => ({ key, dir: s.key === key ? (s.dir === 1 ? -1 : 1) : (right ? -1 : 1) }))}>
      {label}{sort.key === key ? (sort.dir < 0 ? ' ↓' : ' ↑') : ''}</th>)
  return (
    <div className="mt-6">
      <p className="text-[12.5px]" style={muted}>{y.counted} {t.books_counted} · {rows.length} {t.lines_n} · {t.no_link}</p>
      <div className="overflow-x-auto mt-2">
        <table className="w-full text-[12.5px] tabular-nums border-collapse min-w-[640px]">
          <thead>
            <tr className="border-b text-[12px]" style={{ borderColor: 'var(--grid)', color: 'var(--text-secondary)' }}>
              {head('name', c.name, false)}{head('b', c.b, true)}{head('a', c.a, true)}{head('d', c.d, true)}{head('p', c.p, true)}{head('why', c.why, false)}
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={i} className="border-b" style={{ borderColor: 'var(--grid)', opacity: r.why ? 0.6 : 1 }}>
                <td className="px-2 py-1">{r.name}</td>
                <td className="px-2 py-1 text-right">{r.bt}</td><td className="px-2 py-1 text-right">{r.at}</td>
                <td className="px-2 py-1 text-right">{r.dt}</td><td className="px-2 py-1 text-right font-semibold">{r.pt}</td>
                <td className="px-2 py-1 text-[12px]" style={muted}>{r.why || t.yes}</td>
              </tr>))}
          </tbody>
        </table>
      </div>
    </div>)
}

export default function BvaYear({ data, alt }: CustomProps) {
  const d = data as Data
  const t = d.text
  const all = useMemo(() => d.years.map(v => v.fy), [d])
  const [fy] = useFyYear(all)
  const y = d.years.find(v => v.fy === fy) ?? d.years[d.years.length - 1]
  const hrefs = itemHrefs(useItemIndex())
  return (
    <figure aria-label={alt}>
      <Banner text={y.src === 'ledger' ? t.banner_ledger : y.src === 'none' ? t.banner_none : t.banner_books} strong={y.src !== 'ledger'} />
      <div className="grid gap-3 mt-4 md:grid-cols-3">
        {KEYS.map(k => <FlagPanel key={`${y.fy}-${k}`} k={k} y={y} d={d} href={hrefs.line} />)}
      </div>
      <p className="text-[12px] mt-2" style={muted}>{d.flags.ours} {d.flags.why}</p>
      {y.src === 'ledger' ? <LedgerTable key={y.fy} y={y} d={d} href={hrefs.line} /> : <BooksTable key={y.fy} y={y} d={d} />}
    </figure>)
}

/** EVERY LINE, BUDGET AND COST (fy2026-breakdown): the school general fund's lines, one fiscal
 *  year at a time, as TWO SUMS read left to right --
 *
 *      the school budget:  Voted + Transfers + Carried = Budget
 *                          − Spent before moves + Moved to other funds − Moved back = Left
 *      what the line cost: Spent by the school budget + Moved to other funds
 *                          + Paid directly by other funds = Total spent, all funds
 *
 *  TJ, 26 October 2026, on what other funds do to Left: "money added from other funds REDUCES
 *  the general fund... depends how its done doesnt it?" It does, so the two ways are two
 *  columns. A journal entry MOVING cost onto a grant raises Left and is in both sums; a grant
 *  PAYING DIRECTLY leaves Left alone and is only in the second. Every circled amount opens, on
 *  hover, focus or tap, what is behind it: each entry, which fund, how much.
 *
 *  Click a line: both sums written out; every transfer in or out, with the lines on the other
 *  side -- exact where one side is a single line, flagged where the books do not pair
 *  many-to-many; and every other fund that paid toward it, with how it was matched.
 *  `?line=<account>` in the address opens that line (latest year).
 *  Every figure is formatted by scripts/build_fy_breakdown.py. */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import type { CustomProps } from './index'

type K = 'voted' | 'transfers' | 'carried' | 'budget' | 'before' | 'off' | 'on' | 'left' | 'spent' | 'direct' | 'total'
type Item = { title: string; sub: string; text: string }
type Move = { dir: 'in' | 'out'; date: string; memo: string; text: string; paired: boolean; others: { name: string; text: string }[] }
type Row = { name: string; account: string; key: string; cat: string; line: boolean; n: Record<K, number>; t: Record<K, string>
  spent_note?: string; chips: Record<'off' | 'on' | 'direct', Item[]>; chip_n: Partial<Record<'off' | 'on' | 'direct', string>>; payers: { payer: string; rule: string; how: string; text: string }[]; moves: Move[] }
type Year = { fy: string; rows: Row[]; unmatched: { payer: string; why: string; text: string }[]; unmatched_total: string }
type T = Record<'read' | 'all_cats' | 'show' | 'fewer' | 'sum' | 'moves' | 'nomoves' | 'shared' | 'into' | 'outof' | 'in_' | 'out'
  | 'payers' | 'none' | 'unmatched' | 'lines' | 'category' | 'between' | 'tab_summary' | 'tab_expenses' | 'close'
  | 'who_paid' | 'every_row' | 'by_payee' | 'every_fund' | 'loading' | 'failed' | 'recharges' | 'no_recharges'
  | 'ex_date' | 'ex_kind' | 'ex_payee' | 'ex_memo' | 'ex_ref' | 'ex_fund' | 'ex_amount' | 'ex_rows' | 'ex_note' | 'footing' | 'cost_sum' | 'other_funds' | 'chip_off' | 'chip_on' | 'chip_direct', string>
type Col = { id: string; key: K; label: string; op: string; group: string; means: string }
type Data = { years: Year[]; cats: string[]; groups: { id: string; label: string }[]; columns: Col[]; text: T }

// HEAD AND TAIL (TJ, 26 October 2026: "is there a way to show the TOP left and the BOTTOM left,
// on both ends of it on the same table?"). Sorted by any column, the table shows both ends --
// the largest and the smallest, which for Left is most under and most over -- and one row
// between them opens the middle.
const HEAD = 15, TAIL = 15
const GOOD = 'var(--status-good, var(--thread-5))', BAD = 'var(--status-bad, var(--thread-1))'
const tone = (v: number) => (v > 0.5 ? GOOD : v < -0.5 ? BAD : 'var(--text-muted)')
const muted = { color: 'var(--text-muted)' }, secondary = { color: 'var(--text-secondary)' }

function Chip({ on, onClick, children }: { on: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button type="button" onClick={onClick} aria-pressed={on}
      className="px-2.5 py-1 rounded-full text-[12.5px] border leading-tight"
      style={{ borderColor: on ? 'var(--text-secondary)' : 'var(--grid)', color: on ? 'var(--text-primary)' : 'var(--text-muted)',
        background: on ? 'var(--surface-2)' : 'transparent', fontWeight: on ? 600 : 400 }}>{children}</button>)
}

/** The row's sum, written out as a receipt. */
function Sum({ r, cols, title }: { r: Row; cols: Col[]; title: string }) {
  return (
    <div className="mb-3">
      <p className="font-semibold mb-1">{title}</p>
      {/* divs, not a table: the site adds download links to every <table> */}
      <div className="grid grid-cols-[1rem_auto_auto] gap-x-2 tabular-nums w-fit">
        {cols.map(c => {
          const total = c.op === '='
          const line = total ? { borderTop: '1px solid var(--grid)', paddingTop: 2 } : undefined
          return [
            <span key={`${c.id}o`} className="text-center" style={{ ...muted, ...line }}>{c.op}</span>,
            <span key={`${c.id}l`} style={{ fontWeight: total ? 600 : 400, ...line }}>{c.label}
              {(c.key === 'spent' || c.key === 'before') && r.spent_note ? <span className="block text-[12px]" style={muted}>{r.spent_note}</span> : null}</span>,
            <span key={`${c.id}v`} className="text-right" style={{ fontWeight: total ? 600 : 400, color: c.key === 'left' ? tone(r.n.left) : undefined, ...line }}>{r.t[c.key]}</span>,
          ]
        })}
      </div>
    </div>)
}

/** The row's two sums, written out as receipts. */
function Receipt({ r, d }: { r: Row; d: Data }) {
  return (
    <div className="text-[13px]">
      {d.groups.map(g => <Sum key={g.id} r={r} title={g.label} cols={d.columns.filter(c => c.group === g.id)} />)}
    </div>)
}

function Moves({ r, t }: { r: Row; t: T }) {
  return (
    <div className="text-[13px]">
      <p className="font-semibold mb-1">{t.moves}</p>
      {r.moves.length ? (
        <ul className="space-y-2">
          {r.moves.map((m, i) => (
            <li key={i}>
              <p className="flex justify-between gap-3">
                <span><span className="font-semibold" style={{ color: m.dir === 'in' ? GOOD : BAD }}>{m.dir === 'in' ? t.in_ : t.out}</span>
                  <span style={muted}> · {m.date} · “{m.memo}”</span></span>
                <span className="tabular-nums font-semibold" style={{ color: m.dir === 'in' ? GOOD : BAD }}>{m.dir === 'in' ? '+' : '−'}{m.text}</span></p>
              {!m.paired ? <p className="text-[12px] mt-0.5 pl-3" style={muted}>{t.shared}</p> : null}
              <ul className="mt-0.5 pl-3 border-l text-[12.5px]" style={{ borderColor: 'var(--grid)' }}>
                {m.others.map((o, j) => (
                  <li key={j} className="flex justify-between gap-3"><span style={secondary}>{m.paired ? (m.dir === 'in' ? t.into : t.outof) + ' ' : ''}{o.name}</span>
                    <span className="tabular-nums" style={secondary}>{o.text}</span></li>))}
              </ul>
            </li>))}
        </ul>) : <p style={muted}>{t.nomoves}</p>}
    </div>)
}

/** An amount as a chip: hover, focus or tap it for what is behind it (TJ, 26 October 2026: "i
 *  need to be able to see WHAT paid it and how much then"). A tap does not open the row.
 *
 *  The popover is PORTALLED to <body>. The wide table is moved out of the reading column with a
 *  transform, and a transformed ancestor becomes the containing block of anything `fixed` inside
 *  it -- so a popover placed in window coordinates landed inside the table's scroll box, clipped,
 *  and with only a few rows showing it was clipped away entirely. Leaving the chip closes it
 *  after a short delay, cancelled if the pointer reaches the popover, so it can be read. */
function ListChip({ text, title, items, count }: { text: string; title: string; items: Item[]; count?: string }) {
  const [hover, setHover] = useState(false)
  const [held, setHeld] = useState(false)
  const [at, setAt] = useState<{ top: number; left: number } | null>(null)
  const btn = useRef<HTMLButtonElement>(null)
  const timer = useRef<number | undefined>(undefined)
  const on = hover || held
  const enter = () => { window.clearTimeout(timer.current); setHover(true) }
  const leave = () => { window.clearTimeout(timer.current); timer.current = window.setTimeout(() => setHover(false), 180) }
  useEffect(() => () => window.clearTimeout(timer.current), [])
  useEffect(() => {
    if (!on || !btn.current) return
    const b = btn.current.getBoundingClientRect()
    const w = Math.min(320, window.innerWidth - 16)
    const below = window.innerHeight - b.bottom > 220 || b.top < 220
    setAt({ top: below ? b.bottom + 4 : Math.max(8, b.top - 4), left: Math.max(8, Math.min(b.right - w, window.innerWidth - w - 8)) })
    const close = () => { setHover(false); setHeld(false) }
    window.addEventListener('scroll', close, { passive: true, capture: true })
    return () => window.removeEventListener('scroll', close, { capture: true } as EventListenerOptions)
  }, [on])
  const above = at && btn.current ? at.top < btn.current.getBoundingClientRect().top : false
  return (
    <span className="inline-block" onMouseEnter={enter} onMouseLeave={leave}>
      <button ref={btn} type="button" aria-expanded={on}
        onClick={() => { setHover(false); setHeld(false) }}
        onFocus={enter} onBlur={() => { setHover(false); setHeld(false) }}
        className="px-2 py-0.5 rounded-full border tabular-nums leading-tight"
        style={{ borderColor: 'var(--text-muted)', background: on ? 'var(--surface-2)' : 'transparent', cursor: 'pointer' }}>
        {text}</button>
      {count ? <span className="block text-[11px] leading-tight mt-0.5 text-right" style={muted}>{count}</span> : null}
      {on && at ? createPortal(
        <span role="tooltip" onClick={e => e.stopPropagation()} onMouseEnter={enter} onMouseLeave={leave}
          className="fixed z-50 w-[320px] max-w-[calc(100vw-16px)] px-2.5 py-2 rounded text-left text-[12.5px] leading-snug shadow whitespace-normal"
          style={{ top: at.top, left: at.left, transform: above ? 'translateY(-100%)' : undefined,
            background: 'var(--surface-1)', border: '1px solid var(--grid)', color: 'var(--text-primary)', fontWeight: 400 }}>
          <span className="block font-semibold mb-1">{title}</span>
          {items.map((p, i) => (
            <span key={i} className="flex justify-between gap-3 py-0.5">
              <span>{p.title}<span className="block text-[12px]" style={muted}>{p.sub}</span></span>
              <span className="tabular-nums font-semibold">{p.text}</span></span>))}
        </span>, document.body) : null}
    </span>)
}

/** A column's definition, on hover or focus of its header, or a tap on the (i). Portalled for
 *  the same reason as ListChip. */
function HeadTip({ label, means, children }: { label: string; means: string; children: React.ReactNode }) {
  const [on, setOn] = useState(false)
  const [at, setAt] = useState<{ top: number; left: number } | null>(null)
  const el = useRef<HTMLSpanElement>(null)
  const timer = useRef<number | undefined>(undefined)
  const enter = () => { window.clearTimeout(timer.current); setOn(true) }
  const leave = () => { window.clearTimeout(timer.current); timer.current = window.setTimeout(() => setOn(false), 150) }
  useEffect(() => () => window.clearTimeout(timer.current), [])
  useEffect(() => {
    if (!on || !el.current) return
    const b = el.current.getBoundingClientRect()
    const w = Math.min(280, window.innerWidth - 16)
    setAt({ top: b.bottom + 6, left: Math.max(8, Math.min(b.right - w, window.innerWidth - w - 8)) })
    const close = () => setOn(false)
    window.addEventListener('scroll', close, { passive: true, capture: true })
    return () => window.removeEventListener('scroll', close, { capture: true } as EventListenerOptions)
  }, [on])
  return (
    <span ref={el} className="inline" onMouseEnter={enter} onMouseLeave={leave}>
      {children}
      <button type="button" aria-label={label} aria-expanded={on} className="ml-1 align-baseline text-[11px]" style={muted}
        onClick={e => { e.stopPropagation(); setOn(o => !o) }} onFocus={enter} onBlur={() => setOn(false)}>ⓘ</button>
      {on && at ? createPortal(
        <span role="tooltip" onMouseEnter={enter} onMouseLeave={leave}
          className="fixed z-50 w-[280px] max-w-[calc(100vw-16px)] px-2.5 py-2 rounded text-left text-[12.5px] leading-snug shadow whitespace-normal"
          style={{ top: at.top, left: at.left, background: 'var(--surface-1)', border: '1px solid var(--grid)', color: 'var(--text-primary)', fontWeight: 400 }}>
          <span className="block font-semibold mb-0.5">{label}</span>{means}</span>, document.body) : null}
    </span>)
}

/** ONE LINE, OPENED (TJ, 27 October 2026: "instead of hovering over the chips, or clicking a row
 *  and it expands, i want a popup that brings that line into a full drill in view ... and show
 *  all the journal entry rows for the line in 'expenses' tab"). Summary: both sums, the
 *  re-charges, what other funds paid from the start, the transfers. Expenses: every row, from
 *  /data/fy-breakdown/lines-<year>.json, fetched when a line opens; who paid at the top, each
 *  fund a filter; every row, or grouped by payee. */
type ExRow = [string, string, number, string, string, string, number, string, number]
type ExLine = { r: ExRow[]; t: [number, string, number][]; g: [string, number, number, string, number][] }
type ExFile = { fy: string; funds: string[]; kinds: string[]; lines: Record<string, ExLine> }
const FILES = new Map<string, Promise<ExFile>>()
const load = (fy: string) => {
  if (!FILES.has(fy)) FILES.set(fy, fetch(`/data/fy-breakdown/lines-${fy.replace(/\D/g, '')}.json`)
    .then(r => { if (!r.ok) throw new Error(String(r.status)); return r.json() }))
  return FILES.get(fy)!
}

function ItemList({ title, items, empty }: { title: string; items: Item[]; empty?: string }) {
  return (
    <div className="text-[13px]">
      <p className="font-semibold mb-1">{title}</p>
      {items.length ? (
        <ul className="space-y-1">
          {items.map((p, i) => (
            <li key={i} className="flex justify-between gap-3">
              <span>{p.title}<span className="block text-[12px]" style={muted}>{p.sub}</span></span>
              <span className="tabular-nums font-semibold">{p.text}</span></li>))}
        </ul>) : <p style={muted}>{empty}</p>}
    </div>)
}

function Expenses({ r, fy, t }: { r: Row; fy: string; t: T }) {
  const [file, setFile] = useState<ExFile | null>(null)
  const [err, setErr] = useState(false)
  const [fund, setFund] = useState<number | null>(null)
  const [grouped, setGrouped] = useState(false)
  useEffect(() => { let live = true; load(fy).then(f => { if (live) setFile(f) }, () => { if (live) setErr(true) }); return () => { live = false } }, [fy])
  if (err) return <p className="text-[13px]" style={muted}>{t.failed}</p>
  if (!file) return <p className="text-[13px]" style={muted}>{t.loading}</p>
  const L = file.lines[r.key]
  if (!L) return <p className="text-[13px]" style={muted}>{t.none}</p>
  const rows = L.r.filter(x => fund === null || x[6] === fund)
  const groups = L.g.filter(x => fund === null || x[1] === fund)
  const th = 'px-2 py-1.5 text-left font-semibold align-bottom'
  return (
    <div className="text-[13px]">
      <p className="font-semibold mb-1.5">{t.who_paid}</p>
      <div className="flex flex-wrap gap-1.5">
        <Chip on={fund === null} onClick={() => setFund(null)}>{t.every_fund}</Chip>
        {L.t.map(([f, text]) => (
          <Chip key={f} on={fund === f} onClick={() => setFund(v => (v === f ? null : f))}>
            {file.funds[f]} <span className="tabular-nums font-semibold">{text}</span></Chip>))}
      </div>
      <div className="flex gap-1.5 mt-3">
        <Chip on={!grouped} onClick={() => setGrouped(false)}>{t.every_row}</Chip>
        <Chip on={grouped} onClick={() => setGrouped(true)}>{t.by_payee}</Chip>
      </div>
      <div className="mt-2 overflow-x-auto">
        {/* divs would lose the column alignment; the site's download links on a table are fine here */}
        {grouped ? (
          <table className="w-full tabular-nums border-collapse">
            <thead><tr className="border-b" style={{ borderColor: 'var(--grid)' }}>
              <th className={th}>{t.ex_payee}</th><th className={th}>{t.ex_fund}</th>
              <th className={`${th} text-right`}>{t.ex_rows}</th><th className={`${th} text-right`}>{t.ex_amount}</th></tr></thead>
            <tbody>{groups.map((g, i) => (
              <tr key={i} className="border-b" style={{ borderColor: 'var(--grid)' }}>
                <td className="px-2 py-1">{g[0]}</td><td className="px-2 py-1" style={secondary}>{file.funds[g[1]]}</td>
                <td className="px-2 py-1 text-right" style={muted}>{g[2]}</td>
                <td className="px-2 py-1 text-right font-semibold whitespace-nowrap">{g[3]}</td></tr>))}</tbody>
          </table>
        ) : (
          <table className="w-full tabular-nums border-collapse">
            <thead><tr className="border-b" style={{ borderColor: 'var(--grid)' }}>
              <th className={th}>{t.ex_date}</th><th className={th}>{t.ex_kind}</th><th className={th}>{t.ex_payee}</th>
              <th className={th}>{t.ex_memo}</th><th className={th}>{t.ex_ref}</th><th className={th}>{t.ex_fund}</th>
              <th className={`${th} text-right`}>{t.ex_amount}</th></tr></thead>
            <tbody>{rows.map((x, i) => (
              <tr key={i} className="border-b align-top" style={{ borderColor: 'var(--grid)' }}>
                <td className="px-2 py-1 whitespace-nowrap" style={secondary}>{x[1]}</td>
                <td className="px-2 py-1">{file.kinds[x[2]]}</td>
                <td className="px-2 py-1 min-w-[11rem]">{x[3]}</td>
                <td className="px-2 py-1" style={secondary}>{x[4]}</td>
                <td className="px-2 py-1 font-mono text-[11.5px]" style={muted}>{x[5]}</td>
                <td className="px-2 py-1 whitespace-nowrap" style={secondary}>{file.funds[x[6]]}</td>
                <td className="px-2 py-1 text-right whitespace-nowrap font-semibold" style={{ color: x[8] < 0 ? BAD : undefined }}>{x[7]}</td></tr>))}</tbody>
          </table>)}
      </div>
      <p className="text-[12px] mt-2 max-w-3xl" style={muted}>{t.ex_note}</p>
    </div>)
}

function LineView({ r, d, fy, onClose }: { r: Row; d: Data; fy: string; onClose: () => void }) {
  const [tab, setTab] = useState<'summary' | 'expenses'>('summary')
  const box = useRef<HTMLDivElement>(null)
  useEffect(() => {
    const key = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', key)
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    box.current?.focus()
    return () => { window.removeEventListener('keydown', key); document.body.style.overflow = prev }
  }, [onClose])
  const t = d.text
  return createPortal(
    <div className="fixed inset-0 z-50 flex items-start justify-center p-2 sm:p-6" style={{ background: 'rgba(0,0,0,0.45)' }}
      onClick={onClose}>
      <div ref={box} tabIndex={-1} role="dialog" aria-modal="true" aria-label={r.name}
        className="w-full max-w-6xl max-h-full overflow-y-auto rounded-lg shadow-xl outline-none"
        style={{ background: 'var(--surface-1, var(--bg))', border: '1px solid var(--grid)' }}
        onClick={e => e.stopPropagation()}>
        <div className="sticky top-0 z-10 px-4 sm:px-6 pt-4 pb-3 border-b" style={{ background: 'var(--surface-1, var(--bg))', borderColor: 'var(--grid)' }}>
          <div className="flex justify-between gap-4 items-start">
            <div>
              <p className="text-[12px] uppercase tracking-wide" style={muted}>{fy} · {r.cat}</p>
              <h3 className="text-[19px] font-semibold leading-snug">{r.name}</h3>
              {r.account ? <p className="font-mono text-[11.5px] mt-0.5" style={muted}>{r.account}</p> : null}
            </div>
            <button type="button" onClick={onClose} className="px-2.5 py-1 rounded border text-[13px]" style={{ borderColor: 'var(--grid)' }}>{t.close} ✕</button>
          </div>
          <div className="flex gap-1.5 mt-3">
            <Chip on={tab === 'summary'} onClick={() => setTab('summary')}>{t.tab_summary}</Chip>
            <Chip on={tab === 'expenses'} onClick={() => setTab('expenses')}>{t.tab_expenses}</Chip>
          </div>
        </div>
        <div className="px-4 sm:px-6 py-4">
          {tab === 'summary' ? (
            <div className="grid gap-6 md:grid-cols-2">
              {r.line ? <Receipt r={r} d={d} /> : null}
              <div className="space-y-5">
                {r.line ? <ItemList title={t.recharges} empty={t.no_recharges} items={[
                  ...r.chips.off.map(x => ({ ...x, title: `${t.chip_off} ${x.title}` })),
                  ...r.chips.on.map(x => ({ ...x, title: `${t.chip_on} ${x.title}` }))]} /> : null}
                <ItemList title={t.chip_direct} items={r.chips.direct} empty={t.none} />
                {r.line ? <Moves r={r} t={t} /> : null}
              </div>
            </div>) : <Expenses r={r} fy={fy} t={t} />}
        </div>
      </div>
    </div>, document.body)
}

export default function FyLineTable({ data, alt }: CustomProps) {
  const d = data as Data
  const [yi, setYi] = useState(d.years.length - 1)
  const [cat, setCat] = useState<string>('')
  const [sort, setSort] = useState<{ k: string; dir: 1 | -1 }>({ k: 'left', dir: -1 })
  const [all, setAll] = useState(false)
  // `?line=<account>` opens that line, so one line can be linked to.
  const [open, setOpen] = useState<string | null>(() => {
    const a = typeof window === 'undefined' ? null : new URLSearchParams(window.location.search).get('line')
    const r = a ? d.years[d.years.length - 1].rows.find(x => x.account === a) : undefined
    return r ? `${r.account}|${r.name}|${r.cat}` : null
  })
  const y = d.years[yi]
  const openRow = open ? y.rows.find(r => `${r.account}|${r.name}|${r.cat}` === open) ?? null : null
  const close = useCallback(() => setOpen(null), [])
  const rows = useMemo(() => y.rows.filter(r => !cat || r.cat === cat)
    .sort((a, b) => {
      // by category: alphabetical, and within one category the line's Left, largest first, so
      // a category's biggest lines sit together
      if (sort.k === 'cat') return sort.dir * b.cat.localeCompare(a.cat) || b.n.left - a.n.left || a.name.localeCompare(b.name)
      const k = d.columns.find(c => c.id === sort.k)?.key ?? 'left'
      return sort.dir * (a.n[k] - b.n[k]) || a.name.localeCompare(b.name)
    }), [y, cat, sort, d.columns])
  const cut = !all && rows.length > HEAD + TAIL
  const shown = cut ? rows.filter((r, i) => i < HEAD || i >= rows.length - TAIL || `${r.account}|${r.name}|${r.cat}` === open) : rows
  const pos = new Map(rows.map((r, i) => [r, i]))
  const gapBefore = (ri: number) => cut && ri > 0 && pos.get(shown[ri])! !== pos.get(shown[ri - 1])! + 1
  const chipTitle = { off: d.text.chip_off, on: d.text.chip_on, direct: d.text.chip_direct }
  const cell = (r: Row, c: Col) => {
    const k = c.key
    if (!r.line && k !== 'direct' && k !== 'total') return '—'
    if ((k === 'off' || k === 'on' || k === 'direct') && r.chips[k].length && Math.abs(r.n[k]) >= 0.5)
      return <ListChip text={r.t[k]} title={chipTitle[k]} items={r.chips[k]} count={r.chip_n[k]} />
    return Math.abs(r.n[k]) < 0.5 && (k === 'off' || k === 'on' || k === 'direct') ? <span style={muted}>·</span> : r.t[k]
  }
  const firstCost = d.columns.findIndex(c => c.group !== d.columns[0].group)
  const head = (c: Col, i: number) => (
    <th key={c.id} className={`px-2 py-1.5 text-right align-bottom cursor-pointer select-none ${i === firstCost ? 'border-l' : ''}`}
      style={{ borderColor: 'var(--grid)' }}
      onClick={() => setSort(s => ({ k: c.id, dir: s.k === c.id ? (-s.dir as 1 | -1) : -1 }))}
      aria-sort={sort.k === c.id ? (sort.dir < 0 ? 'descending' : 'ascending') : 'none'}>
      <span className="block text-[15px] leading-none mb-1" style={muted}>{c.op || ' '}</span>
      <HeadTip label={c.label} means={c.means}><span className="font-semibold">{c.label}{sort.k === c.id ? (sort.dir < 0 ? ' ↓' : ' ↑') : ''}</span></HeadTip></th>)

  return (
    <figure aria-label={alt}>
      <p className="text-[14px] leading-snug max-w-3xl" style={secondary}>{d.text.read}</p>
      <p className="text-[12.5px] leading-snug max-w-3xl mt-1" style={muted}>{d.text.other_funds}</p>
      <div className="flex flex-wrap gap-1.5 items-center mt-3">
        {d.years.map((v, i) => <Chip key={v.fy} on={i === yi} onClick={() => { setYi(i); setOpen(null) }}>{v.fy}</Chip>)}
        <select value={cat} onChange={e => { setCat(e.target.value); setOpen(null) }}
          className="ml-1 px-2 py-1 rounded border text-[12.5px]" style={{ borderColor: 'var(--grid)', background: 'var(--surface-1)', color: 'var(--text-primary)' }}>
          <option value="">{d.text.all_cats}</option>
          {d.cats.map(c => <option key={c} value={c}>{c}</option>)}
        </select>
      </div>
      {/* WIDE (TJ, 26 October 2026: "make this a wide table"): out of the page's reading column
          to the window, less a gutter each side, centred on it -- the column is centred too */}
      <div className="mt-3 overflow-x-auto relative left-1/2 -translate-x-1/2 w-[calc(100vw-32px)] sm:w-[calc(100vw-64px)] max-w-[1800px]">
        <table className="w-full text-[13px] tabular-nums border-collapse">
          <thead>
            <tr>
              <th colSpan={2} />
              {d.groups.map((g, gi) => (
                <th key={g.id} colSpan={d.columns.filter(c => c.group === g.id).length}
                  className={`px-2 pt-1 text-center text-[12px] font-semibold uppercase tracking-wide border-b ${gi ? 'border-l' : ''}`}
                  style={{ ...muted, borderColor: 'var(--grid)' }}>{g.label}</th>))}
            </tr>
            <tr className="border-b" style={{ borderColor: 'var(--grid)' }}>
              <th className="px-2 py-1.5 text-left align-bottom font-semibold">{d.text.lines}</th>
              <th className="px-2 py-1.5 text-left align-bottom font-semibold cursor-pointer select-none"
                onClick={() => setSort(s => ({ k: 'cat', dir: s.k === 'cat' ? (-s.dir as 1 | -1) : -1 }))}
                aria-sort={sort.k === 'cat' ? (sort.dir < 0 ? 'ascending' : 'descending') : 'none'}>
                {d.text.category}{sort.k === 'cat' ? (sort.dir < 0 ? ' ↓' : ' ↑') : ''}</th>{d.columns.map(head)}</tr></thead>
          <tbody>
            {shown.map((r, ri) => {
              const key = `${r.account}|${r.name}|${r.cat}`
              return [
                gapBefore(ri) ? (
                  <tr key={`gap-${ri}`} className="border-b" style={{ borderColor: 'var(--grid)' }}>
                    <td colSpan={d.columns.length + 2} className="px-2 py-2 text-center">
                      <button type="button" className="text-[13px] underline" style={{ color: 'var(--link, var(--thread-2))' }}
                        onClick={() => setAll(true)}>⋯ {d.text.between} ⋯</button></td>
                  </tr>) : null,
                <tr key={key} className="border-b cursor-pointer hover:bg-[var(--surface-2)]" style={{ borderColor: 'var(--grid)' }}
                  onClick={() => setOpen(key)} aria-haspopup="dialog">
                  <td className="px-2 py-1.5 text-left min-w-[13rem]"><span className="mr-1" style={muted}>↗</span>
                    {r.name}</td>
                  <td className="px-2 py-1.5 text-left min-w-[9rem]" style={secondary}>{r.cat}</td>
                  {d.columns.map((c, i) => (
                    <td key={c.id} className={`px-2 py-1.5 text-right whitespace-nowrap ${i === firstCost ? 'border-l' : ''}`}
                      style={{ borderColor: 'var(--grid)', color: c.key === 'left' ? tone(r.n.left) : c.key === 'transfers' && r.n.transfers ? tone(r.n.transfers) : undefined,
                        fontWeight: c.op === '=' ? 600 : 400 }}>
                      {cell(r, c)}</td>))}
                </tr>,
              ]
            })}
          </tbody>
        </table>
      </div>
      {all && rows.length > HEAD + TAIL ? (
        <button type="button" className="mt-2 text-[13px] underline" style={{ color: 'var(--link, var(--thread-2))' }}
          onClick={() => setAll(false)}>{d.text.fewer}</button>) : null}
      <p className="text-[12.5px] mt-2" style={muted}>{d.text.footing}</p>
      {openRow ? <LineView r={openRow} d={d} fy={y.fy} onClose={close} /> : null}
      <details className="mt-4">
        <summary className="cursor-pointer text-[13.5px] font-semibold">{d.text.unmatched} · <span className="tabular-nums">{y.unmatched_total}</span></summary>
        <ul className="mt-2 text-[13px] max-w-2xl">
          {y.unmatched.map((u, i) => (
            <li key={i} className="flex justify-between gap-3 py-1 border-b" style={{ borderColor: 'var(--grid)' }}>
              <span>{u.payer} <span style={muted}>· {u.why}</span></span><span className="tabular-nums">{u.text}</span></li>))}
        </ul>
      </details>
    </figure>
  )
}

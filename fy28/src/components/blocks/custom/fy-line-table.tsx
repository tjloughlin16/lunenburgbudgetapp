/** EVERY LINE, BUDGET AND COST (fy-breakdown): the school general fund's lines, one fiscal
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
 *  `?line=<account>` in the address opens that line, in the page's year (`?fy=`).
 *  Every figure is formatted by scripts/build_fy_breakdown.py. */
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { useFyYear } from './fy-year'
import { HeadTip, WideScroll } from './fy-shared'
import { itemHrefs, useItemIndex } from './fy-items'
import { PopupActions } from './fy-item-link'
import type { CustomProps } from './index'
import { FLAG_TONE, type FlagKey } from './fy-flags'

type K = 'voted' | 'transfers' | 'carried' | 'budget' | 'before' | 'off' | 'on' | 'left' | 'spent' | 'direct' | 'total'
type Item = { title: string; sub: string; text: string }
type Move = { dir: 'in' | 'out'; date: string; memo: string; text: string; paired: boolean; others: { name: string; text: string }[] }
type Entry = { date: string; memo: string; journal: string; dir: 'in' | 'out'; text: string; others: { name: string; text: string }[] }
export type Row = { name: string; account: string; key: string; cat: string; line: boolean; n: Record<K, number>; t: Record<K, string>
  spent_note?: string; bw?: BW
  /** what it cost from every fund, less last year; null in the first year the journal holds */
  chg?: number | null; t_chg?: string
  /** the year's flags (scripts/line_flags.py), for the flag filter */
  flags?: FlagKey[]; chips: Record<'off' | 'on' | 'direct', Item[]>; chip_n: Partial<Record<'off' | 'on' | 'direct', string>> }
type BW = { walk: string; adj: number; adj_t: string; adj_pct: string; flag: boolean }
type Year = { fy: string; rows: Row[]; unmatched: { payer: string; why: string; text: string }[]; unmatched_total: string }
type T = Record<'line_chg' | 'line_chg_means' | 'read' | 'all_cats' | 'show' | 'fewer' | 'sum' | 'moves' | 'nomoves' | 'shared' | 'into' | 'outof' | 'in_' | 'out'
  | 'payers' | 'none' | 'unmatched' | 'lines' | 'category' | 'between' | 'tab_summary' | 'tab_expenses' | 'close'
  | 'who_paid' | 'every_row' | 'by_payee' | 'every_fund' | 'loading' | 'failed' | 'recharges' | 'no_recharges'
  | 'tab_analysis' | 'an_payee' | 'an_memo' | 'an_week' | 'an_note' | 'an_week_note' | 'an_recharge'
  | 'ex_date' | 'ex_kind' | 'ex_payee' | 'ex_memo' | 'ex_ref' | 'ex_fund' | 'ex_amount' | 'ex_rows' | 'ex_note' | 'tab_moves' | 'mv_transfers' | 'mv_transfers_def' | 'mv_recharges' | 'mv_recharges_def'
  | 'mv_entries' | 'mv_entries_def' | 'mv_none' | 'mv_with' | 'mv_in' | 'mv_out' | 'any_payee' | 'any_memo' | 'clear_filters' | 'an_click' | 'for_what' | 'paid_to' | 'footing' | 'cost_sum' | 'other_funds' | 'chip_off' | 'chip_on' | 'chip_direct' | 'scroll' | 'flag_any' | 'flag_filter', string>
type Col = { id: string; key: K; label: string; op: string; group: string; means: string }
export type Data = { years: Year[]; cats: string[]; groups: { id: string; label: string }[]; columns: Col[]; text: T
  flag_names?: Record<FlagKey, string> }

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

/** ONE LINE, OPENED (TJ, 27 October 2026: "instead of hovering over the chips, or clicking a row
 *  and it expands, i want a popup that brings that line into a full drill in view ... and show
 *  all the journal entry rows for the line in 'expenses' tab"). Summary: both sums, the
 *  re-charges, what other funds paid from the start, the transfers. Expenses: every row, from
 *  /data/fy-breakdown/lines-<year>.json, fetched when a line opens; who paid at the top, each
 *  fund a filter; every row, or grouped by payee. */
type ExRow = [string, string, number, string, string, string, number, string, number, string]
/** What the Expenses tab is narrowed to: a payee, a memo (as grouped), or neither. */
type Filter = { payee?: string; memo?: string }
type Bar = [string, string, [number, number][], string, string, [string, string, string][]]
type Wk = [string, string, [number, number][], string, string]
export type ExLine = { r: ExRow[]; t: [number, string, number][]; g: [string, number, number, string, number][]
  ap: Bar[]; am: Bar[]; aw: Wk[]; a0: string; a1: string }
// `mv`: a line's budget transfers (`m`) and the journal entries re-booking it between school
// lines (`j`), for the Transfers tab -- here rather than in the page payload, which they doubled
export type ExFile = { fy: string; funds: string[]; kinds: string[]; lines: Record<string, ExLine>; mv: Record<string, { m: Move[]; j: Entry[] }> }
const FILES = new Map<string, Promise<ExFile>>()
const load = (fy: string) => {
  if (!FILES.has(fy)) FILES.set(fy, fetch(`/data/fy-breakdown/lines-${fy.replace(/\D/g, '')}.json`)
    .then(r => { if (!r.ok) throw new Error(String(r.status)); return r.json() }))
  return FILES.get(fy)!
}
/** WHERE A LINE'S ROWS COME FROM: the year's file, on the breakdown page; on the line's own page
 *  (/school-lines/<slug>), its own file -- the same rows, sliced by scripts/fy_items.py. */
export type ExLoader = (fy: string) => Promise<ExFile>
const ExSource = createContext<ExLoader>(load)

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

function Expenses({ r, fy, t, filter, setFilter }: { r: Row; fy: string; t: T; filter: Filter; setFilter: (f: Filter) => void }) {
  const [file, setFile] = useState<ExFile | null>(null)
  const [err, setErr] = useState(false)
  const [fund, setFund] = useState<number | null>(null)
  const [grouped, setGrouped] = useState(false)
  const src = useContext(ExSource)
  useEffect(() => { let live = true; src(fy).then(f => { if (live) setFile(f) }, () => { if (live) setErr(true) }); return () => { live = false } }, [fy, src])
  if (err) return <p className="text-[13px]" style={muted}>{t.failed}</p>
  if (!file) return <p className="text-[13px]" style={muted}>{t.loading}</p>
  const L = file.lines[r.key]
  if (!L) return <p className="text-[13px]" style={muted}>{t.none}</p>
  const payeeOf = (x: ExRow) => x[3] || file.kinds[x[2]]
  const rows = L.r.filter(x => (fund === null || x[6] === fund) && (!filter.payee || payeeOf(x) === filter.payee)
    && (!filter.memo || x[9] === filter.memo))
  const groups = L.g.filter(x => (fund === null || x[1] === fund) && (!filter.payee || x[0] === filter.payee))
  const payees = Array.from(new Set(L.r.map(payeeOf))).sort()
  const memos = Array.from(new Set(L.r.map(x => x[9]).filter(Boolean))).sort()
  const sel = 'px-2 py-1 rounded border text-[12.5px] max-w-[16rem]'
  const selStyle = { borderColor: 'var(--grid)', background: 'var(--surface-1)', color: 'var(--text-primary)' }
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
        <select value={filter.payee ?? ''} onChange={e => setFilter({ ...filter, payee: e.target.value || undefined })}
          className={`${sel} ml-2`} style={selStyle} aria-label={t.ex_payee}>
          <option value="">{t.any_payee}</option>
          {payees.map(p => <option key={p} value={p}>{p}</option>)}
        </select>
        <select value={filter.memo ?? ''} onChange={e => setFilter({ ...filter, memo: e.target.value || undefined })}
          className={sel} style={selStyle} aria-label={t.ex_memo}>
          <option value="">{t.any_memo}</option>
          {memos.map(m => <option key={m} value={m}>{m}</option>)}
        </select>
        {filter.payee || filter.memo ? (
          <button type="button" className="text-[12.5px] px-2 py-0.5 rounded border" style={{ borderColor: 'var(--grid)' }}
            onClick={() => setFilter({})}>{t.clear_filters} ✕</button>) : null}
      </div>
      <div className="mt-2 overflow-x-auto">
        {/* divs would lose the column alignment; the site's download links on a table are fine here */}
        {/* the by-payee totals are per payee and fund only; with a memo picked, the rows */}
        {grouped && !filter.memo ? (
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

/** A fund's colour: the school budget first, then the series palette in the file's order. */
const FUND = ['var(--thread-1)', 'var(--thread-2)', 'var(--thread-5)', 'var(--thread-4)', 'var(--thread-3)', 'var(--thread-6, var(--thread-2))']
const fundColour = (f: number) => (f < 0 ? 'var(--text-muted)' : FUND[f % FUND.length])

function useFile(fy: string) {
  const [file, setFile] = useState<ExFile | null>(null)
  const [err, setErr] = useState(false)
  const src = useContext(ExSource)
  useEffect(() => { let live = true; src(fy).then(f => { if (live) setFile(f) }, () => { if (live) setErr(true) }); return () => { live = false } }, [fy, src])
  return { file, err }
}

/** Bars by payee or memo, each split by the fund that paid; one scale for the chart. */
function Bars({ title, bars, file, t, sub, onPick }: { title: string; bars: Bar[]; file: ExFile; t: T; sub: string; onPick: (k: string) => void }) {
  const max = Math.max(1, ...bars.map(b => b[2].reduce((a, [, v]) => a + Math.max(0, v), 0)))
  const used = Array.from(new Set(bars.flatMap(b => b[2].map(([f]) => f)))).sort((a, b) => a - b)
  return (
    <div>
      <p className="font-semibold mb-1.5">{title}</p>
      <Legend used={used} file={file} />
      <div className="divide-y" style={{ borderColor: 'var(--grid)' }}>
        {bars.map((b, i) => {
          const body = (
            <span className="grid grid-cols-[minmax(8rem,14rem)_1fr_auto] gap-x-3 items-start w-full text-left">
              <span className="text-[12.5px] leading-tight">{b[0]}<span className="block text-[11px]" style={muted}>{b[1]}</span></span>
              <span className="flex flex-col gap-1 pt-0.5">
                <span className="flex h-3.5 rounded-sm overflow-hidden" style={{ background: 'var(--surface-2)' }}>
                  {b[2].filter(([, v]) => v > 0).map(([f, v]) => (
                    <span key={f} title={file.funds[f]} style={{ width: `${(100 * v) / max}%`, background: fundColour(f) }} />))}
                </span>
                {b[5].length ? (
                  <span className="text-[11.5px] leading-snug" style={secondary}>
                    {b[5].map(([o, n, v], j) => (
                      <span key={j} className="block">{sub} <span style={{ color: 'var(--text-primary)' }}>{o}</span> · {n} · <span className="tabular-nums">{v}</span></span>))}
                  </span>) : null}
              </span>
              <span className="tabular-nums text-right text-[12.5px] font-semibold whitespace-nowrap">{b[3]}</span>
            </span>)
          return b[4] ? (
            <button key={i} type="button" onClick={() => onPick(b[4])} className="block w-full py-1.5 rounded hover:bg-[var(--surface-2)]"
              style={{ borderColor: 'var(--grid)' }}>{body}</button>
          ) : <div key={i} className="py-1.5" style={{ borderColor: 'var(--grid)' }}>{body}</div>
        })}
      </div>
      <p className="text-[11.5px] mt-1" style={muted}>{t.an_click}</p>
    </div>)
}

function Legend({ used, file, recharge }: { used: number[]; file: ExFile; recharge?: string }) {
  return (
    <div className="flex flex-wrap gap-x-3 gap-y-1 text-[12px] mb-1.5" style={secondary}>
      {used.map(f => (
        <span key={f} className="inline-flex items-center gap-1"><span className="inline-block w-2.5 h-2.5 rounded-sm" style={{ background: fundColour(f) }} />
          {f < 0 ? recharge : file.funds[f]}</span>))}
    </div>)
}

const MONTH = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

/** Every week, Monday to Sunday, from the line's first posting to 30 June: spending stacked by
 *  fund above the line, bills re-charged off the school budget below it. */
function Weeks({ L, file, t }: { L: ExLine; file: ExFile; t: T }) {
  const [hot, setHot] = useState<number | null>(null)
  const W = 900, H = 220, PAD = 8, AX = 18
  const day = (iso: string) => Date.parse(iso + 'T00:00:00Z') / 864e5
  const d0 = day(L.a0), d1 = day(L.a1) + 1
  const x = (iso: string) => PAD + ((day(iso) - d0) / (d1 - d0)) * (W - 2 * PAD)
  // above the line every positive amount; below it every negative one, re-charges and refunds
  const up = Math.max(1, ...L.aw.map(w => w[2].reduce((a, [f, v]) => a + (f >= 0 && v > 0 ? v : 0), 0)))
  const down = Math.max(0, ...L.aw.map(w => w[2].reduce((a, [f, v]) => a + (f < 0 || v < 0 ? Math.abs(v) : 0), 0)))
  const k = (H - AX - 2 * PAD) / (up + down)
  const zero = PAD + up * k
  const bw = Math.max(2, (7 / (d1 - d0)) * (W - 2 * PAD) - 1.5)
  const fyStart = x(`${Number(L.a1.slice(0, 4)) - 1}-07-01`)
  const months: string[] = []
  for (let m = new Date(L.a0 + 'T00:00:00Z'); m <= new Date(L.a1 + 'T00:00:00Z'); m.setUTCMonth(m.getUTCMonth() + 1, 1)) {
    months.push(new Date(Date.UTC(m.getUTCFullYear(), m.getUTCMonth(), 1)).toISOString().slice(0, 10))
  }
  const used = Array.from(new Set(L.aw.flatMap(w => w[2].map(([f]) => f)))).sort((a, b) => a - b)
  const w = hot === null ? null : L.aw[hot]
  return (
    <div>
      <p className="font-semibold mb-1.5">{t.an_week}</p>
      <Legend used={used} file={file} recharge={t.an_recharge} />
      <div className="relative">
        <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto block" onPointerLeave={() => setHot(null)}>
          <rect x={0} y={0} width={W} height={H} fill="transparent" onClick={() => setHot(null)} />
          <rect x={fyStart} y={PAD} width={W - PAD - fyStart} height={H - AX - 2 * PAD} fill="var(--surface-2)" opacity={0.5} />
          <line x1={PAD} x2={W - PAD} y1={zero} y2={zero} stroke="var(--grid)" />
          {months.filter(m => m >= L.a0).map(m => (
            <text key={m} x={x(m) + 2} y={H - 4} fontSize={11} fill="var(--text-muted)">{MONTH[Number(m.slice(5, 7)) - 1]}</text>))}
          {L.aw.map((wk, i) => {
            let top = zero, bot = zero
            return (
              <g key={wk[0]} opacity={hot === null || hot === i ? 1 : 0.35} style={{ cursor: 'pointer' }}
                onPointerEnter={e => { if (e.pointerType === 'mouse') setHot(i) }}
                onClick={() => setHot(h => (h === i ? null : i))}>
                <rect x={x(wk[0])} y={PAD} width={bw} height={H - AX - 2 * PAD} fill="transparent" />
                {wk[2].map(([f, v]) => {
                  const h = Math.abs(v) * k
                  if (f < 0 || v < 0) { const y0 = bot; bot += h; return <rect key={f} x={x(wk[0])} y={y0} width={bw} height={h} fill={fundColour(f)} /> }
                  top -= h
                  return <rect key={f} x={x(wk[0])} y={top} width={bw} height={h} fill={fundColour(f)} />
                })}
              </g>)
          })}
        </svg>
        {w ? (
          <div role="status" className="mt-2 sm:absolute sm:right-0 sm:top-0 sm:w-[260px] px-2.5 py-2 rounded text-[12.5px] leading-snug shadow"
            style={{ background: 'var(--surface-1)', border: '1px solid var(--grid)' }}>
            <p className="font-semibold">{w[1]}</p>
            <p className="tabular-nums font-semibold mt-0.5">{w[3]}</p>
            {w[4] ? <p className="tabular-nums" style={secondary}>{t.an_recharge}: {w[4]}</p> : null}
          </div>) : null}
      </div>
      <p className="text-[12px] mt-1.5" style={muted}>{t.an_week_note}</p>
    </div>)
}

function Analysis({ r, fy, t, pick }: { r: Row; fy: string; t: T; pick: (f: Filter) => void }) {
  const { file, err } = useFile(fy)
  if (err) return <p className="text-[13px]" style={muted}>{t.failed}</p>
  if (!file) return <p className="text-[13px]" style={muted}>{t.loading}</p>
  const L = file.lines[r.key]
  if (!L) return <p className="text-[13px]" style={muted}>{t.none}</p>
  return (
    <div className="text-[13px] space-y-7">
      {L.aw.length ? <Weeks L={L} file={file} t={t} /> : null}
      <Bars title={t.an_payee} bars={L.ap} file={file} t={t} sub={t.for_what} onPick={k => pick({ payee: k })} />
      {L.am.length ? <Bars title={t.an_memo} bars={L.am} file={file} t={t} sub={t.paid_to} onPick={k => pick({ memo: k })} /> : null}
      <p className="text-[12px] max-w-3xl" style={muted}>{t.an_note}</p>
    </div>)
}

/** TRANSFERS AND RE-CHARGES (TJ, 27 October 2026: "lets also make this SUPER clear... a new
 *  tab for transfers, moves, recharges"). Three kinds of entry that look alike in a ledger and
 *  do different things, each under its own one-line definition: a transfer moves BUDGET; a
 *  re-charge moves a BILL to another fund; a journal entry between school lines moves a bill
 *  to another line. */
function Section({ title, def, children }: { title: string; def: string; children: React.ReactNode }) {
  return (
    <section className="text-[13px]">
      <h4 className="text-[15px] font-semibold">{title}</h4>
      <p className="text-[12.5px] mt-0.5 mb-2 max-w-2xl" style={secondary}>{def}</p>
      {children}
    </section>)
}

function EntryList({ items, t }: { items: { dir: 'in' | 'out'; head: string; text: string; note?: string; others: { name: string; text: string }[] }[]; t: T }) {
  if (!items.length) return <p style={muted}>{t.mv_none}</p>
  return (
    <ul className="space-y-2.5">
      {items.map((m, i) => (
        <li key={i} className="pl-3 border-l-2" style={{ borderColor: m.dir === 'in' ? GOOD : BAD }}>
          <p className="flex justify-between gap-3">
            <span><span className="font-semibold" style={{ color: m.dir === 'in' ? GOOD : BAD }}>{m.dir === 'in' ? t.mv_in : t.mv_out}</span>
              <span style={secondary}> · {m.head}</span></span>
            <span className="tabular-nums font-semibold whitespace-nowrap" style={{ color: m.dir === 'in' ? GOOD : BAD }}>{m.dir === 'in' ? '+' : '−'}{m.text}</span></p>
          {m.note ? <p className="text-[12px] mt-0.5" style={muted}>{m.note}</p> : null}
          {m.others.length ? (
            <ul className="mt-0.5 text-[12.5px]">
              {m.others.map((o, j) => (
                <li key={j} className="flex justify-between gap-3"><span style={secondary}>{t.mv_with} {o.name}</span>
                  <span className="tabular-nums" style={secondary}>{o.text}</span></li>))}
            </ul>) : null}
        </li>))}
    </ul>)
}

function MovesTab({ r, fy, t }: { r: Row; fy: string; t: T }) {
  const { file, err } = useFile(fy)
  if (err) return <p className="text-[13px]" style={muted}>{t.failed}</p>
  if (!file) return <p className="text-[13px]" style={muted}>{t.loading}</p>
  const mv = file.mv[r.key] ?? { m: [], j: [] }
  const transfers = mv.m.map(m => ({ dir: m.dir, head: `${m.date} · “${m.memo}”`, text: m.text,
    note: m.paired ? undefined : t.shared, others: m.others }))
  const recharges = [
    ...r.chips.off.map(x => ({ dir: 'out' as const, head: x.sub, text: x.text, others: [{ name: x.title, text: x.text }] })),
    ...r.chips.on.map(x => ({ dir: 'in' as const, head: x.sub, text: x.text, others: [{ name: x.title, text: x.text }] }))]
  const entries = mv.j.map(e => ({ dir: e.dir, head: `${e.date} · “${e.memo}” · ${e.journal}`, text: e.text, others: e.others }))
  return (
    <div className="grid gap-7 max-w-4xl">
      <Section title={t.mv_transfers} def={t.mv_transfers_def}><EntryList items={transfers} t={t} /></Section>
      <Section title={t.mv_recharges} def={t.mv_recharges_def}><EntryList items={recharges} t={t} /></Section>
      <Section title={t.mv_entries} def={t.mv_entries_def}><EntryList items={entries} t={t} /></Section>
    </div>)
}

/** ONE LINE'S VIEW, two hosts: the popup on the breakdown page, and the line's own page
 *  (/school-lines/<slug>). `bare` leaves out the heading the page already prints; `actions` sits
 *  beside it (the popup's close button and link). */
export function LineBody({ r, d, fy, src = load, actions, bare = false, sticky = false, onTop }: {
  r: Row; d: Data; fy: string; src?: ExLoader; actions?: React.ReactNode; bare?: boolean; sticky?: boolean; onTop?: () => void }) {
  const [tab, setTab] = useState<'summary' | 'moves' | 'expenses' | 'analysis'>('summary')
  const [filter, setFilter] = useState<Filter>({})
  const t = d.text
  const pad = sticky ? 'px-4 sm:px-6' : ''
  return (
    <ExSource.Provider value={src}>
      <div className={`${sticky ? `sticky top-0 z-10 ${pad} pt-4 pb-3 border-b` : 'pb-3'}`} style={sticky ? { background: 'var(--surface-1, var(--bg))', borderColor: 'var(--grid)' } : undefined}>
        <div className="flex justify-between gap-4 items-start">
          <div>
            {bare ? null : <>
              <p className="text-[12px] uppercase tracking-wide" style={muted}>{fy} · {r.cat}</p>
              <h3 className="text-[19px] font-semibold leading-snug">{r.name}</h3>
              {r.account ? <p className="font-mono text-[11.5px] mt-0.5" style={muted}>{r.account}</p> : null}
            </>}
            {r.bw ? <p className="text-[12.5px] mt-1 tabular-nums" style={r.bw.flag ? { color: 'var(--thread-3)', fontWeight: 600 } : secondary}>{r.bw.flag ? '⚑ ' : ''}{r.bw.walk}</p> : null}
          </div>
          {actions}
        </div>
        <div className="flex flex-wrap gap-1.5 mt-3">
          <Chip on={tab === 'summary'} onClick={() => setTab('summary')}>{t.tab_summary}</Chip>
          {r.line ? <Chip on={tab === 'moves'} onClick={() => setTab('moves')}>{t.tab_moves}</Chip> : null}
          <Chip on={tab === 'expenses'} onClick={() => setTab('expenses')}>{t.tab_expenses}</Chip>
          <Chip on={tab === 'analysis'} onClick={() => setTab('analysis')}>{t.tab_analysis}</Chip>
        </div>
      </div>
      <div className={`${pad} py-4`}>
        {tab === 'summary' ? (
          <div className="grid gap-6 md:grid-cols-2">
            {r.line ? <Receipt r={r} d={d} /> : null}
            <div className="space-y-5">
              <ItemList title={t.chip_direct} items={r.chips.direct} empty={t.none} />
            </div>
          </div>) : tab === 'moves' ? <MovesTab r={r} fy={fy} t={t} /> : tab === 'expenses' ? <Expenses r={r} fy={fy} t={t} filter={filter} setFilter={setFilter} />
            : <Analysis r={r} fy={fy} t={t} pick={f => { setFilter(f); setTab('expenses'); onTop?.() }} />}
      </div>
    </ExSource.Provider>)
}

function LineView({ r, d, fy, onClose }: { r: Row; d: Data; fy: string; onClose: () => void }) {
  const box = useRef<HTMLDivElement>(null)
  const hrefs = itemHrefs(useItemIndex())
  useEffect(() => {
    const key = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', key)
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    box.current?.focus()
    return () => { window.removeEventListener('keydown', key); document.body.style.overflow = prev }
  }, [onClose])
  return createPortal(
    <div className="fixed inset-0 z-50 flex items-start justify-center p-2 sm:p-6" style={{ background: 'rgba(0,0,0,0.45)' }}
      onClick={onClose}>
      <div ref={box} tabIndex={-1} role="dialog" aria-modal="true" aria-label={r.name}
        className="w-full max-w-6xl max-h-full overflow-y-auto rounded-lg shadow-xl outline-none"
        style={{ background: 'var(--surface-1, var(--bg))', border: '1px solid var(--grid)' }}
        onClick={e => e.stopPropagation()}>
        <LineBody r={r} d={d} fy={fy} sticky onTop={() => box.current?.scrollTo({ top: 0 })}
          actions={<PopupActions href={r.line ? hrefs.line(r.account) : undefined} fy={fy} close={d.text.close} onClose={onClose} />} />
      </div>
    </div>, document.body)
}

export default function FyLineTable({ data, alt }: CustomProps) {
  const d = data as Data
  const fys = useMemo(() => d.years.map(v => v.fy), [d])
  const [fy] = useFyYear(fys)                     // the page's year (fy-year.ts)
  const yi = Math.max(0, fys.indexOf(fy))
  const [cat, setCat] = useState<string>('')
  const [fk, setFk] = useState<FlagKey | ''>('')
  const [sort, setSort] = useState<{ k: string; dir: 1 | -1 }>({ k: 'left', dir: -1 })
  const [all, setAll] = useState(false)
  // `?line=<account>` opens that line, so one line can be linked to.
  const [open, setOpen] = useState<string | null>(() => {
    const a = typeof window === 'undefined' ? null : new URLSearchParams(window.location.search).get('line')
    const r = a ? d.years[yi].rows.find(x => x.account === a) : undefined
    return r ? `${r.account}|${r.name}|${r.cat}` : null
  })
  const y = d.years[yi]
  const openRow = open ? y.rows.find(r => `${r.account}|${r.name}|${r.cat}` === open) ?? null : null
  const close = useCallback(() => setOpen(null), [])
  const rows = useMemo(() => y.rows.filter(r => (!cat || r.cat === cat) && (!fk || r.flags?.includes(fk)))
    .sort((a, b) => {
      // by category: alphabetical, and within one category the line's Left, largest first, so
      // a category's biggest lines sit together
      if (sort.k === 'cat') return sort.dir * b.cat.localeCompare(a.cat) || b.n.left - a.n.left || a.name.localeCompare(b.name)
      // THE CHANGE FROM LAST YEAR (TJ, 29 October 2026: "or putting another column into the 'every
      // line' table"), so the table sorts by it; a row with none sorts last either way
      if (sort.k === 'chg') return (a.chg == null ? 1 : 0) - (b.chg == null ? 1 : 0) || sort.dir * ((a.chg ?? 0) - (b.chg ?? 0)) || a.name.localeCompare(b.name)
      const k = d.columns.find(c => c.id === sort.k)?.key ?? 'left'
      return sort.dir * (a.n[k] - b.n[k]) || a.name.localeCompare(b.name)
    }), [y, cat, fk, sort, d.columns])
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
  const chg = y.rows.some(r => r.chg != null)
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
        <select value={cat} onChange={e => { setCat(e.target.value); setOpen(null) }}
          className="ml-1 px-2 py-1 rounded border text-[12.5px]" style={{ borderColor: 'var(--grid)', background: 'var(--surface-1)', color: 'var(--text-primary)' }}>
          <option value="">{d.text.all_cats}</option>
          {d.cats.map(c => <option key={c} value={c}>{c}</option>)}
        </select>
        {/* THE YEAR'S FLAGS (TJ, 29 October 2026): the lines a flag panel above lists, in this table */}
        {d.flag_names ? <>
          <span className="ml-2 text-[12.5px]" style={muted}>{d.text.flag_filter}:</span>
          <Chip on={!fk} onClick={() => { setFk(''); setOpen(null) }}>{d.text.flag_any}</Chip>
          {(['under', 'over', 'restart'] as FlagKey[]).map(k => (
            <Chip key={k} on={fk === k} onClick={() => { setFk(fk === k ? '' : k); setOpen(null) }}>
              <span className="inline-block w-2 h-2 rounded-full mr-1 align-middle" style={{ background: FLAG_TONE[k] }} />
              {d.flag_names![k]} <span className="tabular-nums">({y.rows.filter(r => r.flags?.includes(k)).length})</span></Chip>))}
        </> : null}
      </div>
      <WideScroll cue={d.text.scroll}>
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
                {d.text.category}{sort.k === 'cat' ? (sort.dir < 0 ? ' ↓' : ' ↑') : ''}</th>{d.columns.map(head)}
                {chg ? <th className="px-2 py-1.5 text-right align-bottom cursor-pointer select-none border-l" style={{ borderColor: 'var(--grid)' }}
                  onClick={() => setSort(s => ({ k: 'chg', dir: s.k === 'chg' ? (-s.dir as 1 | -1) : -1 }))}
                  aria-sort={sort.k === 'chg' ? (sort.dir < 0 ? 'descending' : 'ascending') : 'none'}>
                  <span className="block text-[15px] leading-none mb-1" style={muted}>{' '}</span>
                  <HeadTip label={d.text.line_chg} means={d.text.line_chg_means}><span className="font-semibold">{d.text.line_chg}{sort.k === 'chg' ? (sort.dir < 0 ? ' ↓' : ' ↑') : ''}</span></HeadTip></th> : null}</tr></thead>
          <tbody>
            {shown.map((r, ri) => {
              const key = `${r.account}|${r.name}|${r.cat}`
              return [
                gapBefore(ri) ? (
                  <tr key={`gap-${ri}`} className="border-b" style={{ borderColor: 'var(--grid)' }}>
                    <td colSpan={d.columns.length + 2 + (chg ? 1 : 0)} className="px-2 py-2 text-center">
                      <button type="button" className="text-[13px] underline" style={{ color: 'var(--link, var(--thread-2))' }}
                        onClick={() => setAll(true)}>⋯ {d.text.between} ⋯</button></td>
                  </tr>) : null,
                <tr key={key} className="border-b cursor-pointer hover:bg-[var(--surface-2)]" style={{ borderColor: 'var(--grid)' }}
                  onClick={() => setOpen(key)} aria-haspopup="dialog">
                  <td className="px-2 py-1.5 text-left min-w-[13rem]"><span className="mr-1" style={muted}>↗</span>
                    {r.name}
                    {/* the line's budget moved far from the vote (build_fy_breakdown.budget_walk) */}
                    {r.bw?.flag ? <span title={r.bw.walk} className="block mt-0.5 text-[11.5px] font-semibold" style={{ color: 'var(--thread-3)' }}>
                      ⚑ {r.bw.adj_t} {r.bw.adj_pct ? `(${r.bw.adj_pct})` : ''}</span> : null}
                    {r.flags?.length && d.flag_names ? <span className="block mt-0.5">{r.flags.map(k => (
                      <span key={k} className="inline-block mr-1 px-1.5 rounded text-[11px]" style={{ border: `1px solid ${FLAG_TONE[k]}` }}>{d.flag_names![k]}</span>))}</span> : null}</td>
                  <td className="px-2 py-1.5 text-left min-w-[9rem]" style={secondary}>{r.cat}</td>
                  {d.columns.map((c, i) => (
                    <td key={c.id} className={`px-2 py-1.5 text-right whitespace-nowrap ${i === firstCost ? 'border-l' : ''}`}
                      style={{ borderColor: 'var(--grid)', color: c.key === 'left' ? tone(r.n.left) : c.key === 'transfers' && r.n.transfers ? tone(r.n.transfers) : undefined,
                        fontWeight: c.op === '=' ? 600 : 400 }}>
                      {cell(r, c)}</td>))}
                  {chg ? <td className="px-2 py-1.5 text-right whitespace-nowrap border-l" style={{ borderColor: 'var(--grid)' }}>{r.t_chg || '—'}</td> : null}
                </tr>,
              ]
            })}
          </tbody>
        </table>
      </WideScroll>
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

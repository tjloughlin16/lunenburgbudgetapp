/** EVERY LINE, BUDGET TO LEFT (fy2026-breakdown): the school general fund's lines, one fiscal
 *  year at a time, as ONE SUM read left to right --
 *
 *      Voted  +  Moved in or out  +  Carried from last year  =  Budget  −  Spent  =  Left
 *
 *  -- and beside it a second sum, what the line cost from every fund: Spent by the school
 *  budget + Paid by grants and other funds = Total spent, all funds (TJ: the other-funds column
 *  "doesnt seem ADDITIVE", so it now adds into something). TJ, 26
 *  October 2026, on the first version: "the column labels are just confusing and i dont know
 *  how the math works out across columns". So the operators sit in the header, and every
 *  column is a posting the Town made, not a part of our own identity.
 *
 *  Click a line: the same sum written out; every transfer in or out, with the lines on the
 *  other side (TJ: "which funds transferred into each line ... or how much each transferred
 *  OUT to another") -- exact where one side is a single line, flagged where the books do not
 *  pair many-to-many; and every other fund that paid toward it, with how it was matched.
 *  `?line=<account>` in the address opens that line (latest year).
 *  Every figure is formatted by scripts/build_fy_breakdown.py. */
import { useEffect, useMemo, useRef, useState } from 'react'
import type { CustomProps } from './index'

type K = 'voted' | 'transfers' | 'carried' | 'budget' | 'spent' | 'left' | 'other' | 'total'
type Move = { dir: 'in' | 'out'; date: string; memo: string; text: string; paired: boolean; others: { name: string; text: string }[] }
type Row = { name: string; account: string; cat: string; line: boolean; n: Record<K, number>; t: Record<K, string>
  spent_note?: string; payers: { payer: string; rule: string; how: string; text: string }[]; moves: Move[] }
type Year = { fy: string; rows: Row[]; unmatched: { payer: string; why: string; text: string }[]; unmatched_total: string }
type T = Record<'read' | 'all_cats' | 'show' | 'fewer' | 'sum' | 'moves' | 'nomoves' | 'shared' | 'into' | 'outof' | 'in_' | 'out'
  | 'payers' | 'none' | 'unmatched' | 'lines' | 'footing' | 'cost_sum', string>
type Col = { id: string; key: K; label: string; op: string; group: string }
type Data = { years: Year[]; cats: string[]; groups: { id: string; label: string }[]; columns: Col[]; text: T }

const FIRST = 25
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
              {c.key === 'spent' && r.spent_note ? <span className="block text-[12px]" style={muted}>{r.spent_note}</span> : null}</span>,
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

function Payers({ r, t }: { r: Row; t: T }) {
  return (
    <div className="text-[13px]">
      <p className="font-semibold mb-1">{t.payers}</p>
      {r.payers.length ? (
        <ul className="space-y-1">
          {r.payers.map((p, i) => (
            <li key={i} className="flex justify-between gap-3">
              <span>{p.payer}<span className="block text-[12px]" style={muted}>{p.rule}: {p.how}</span></span>
              <span className="tabular-nums">{p.text}</span></li>))}
        </ul>) : <p style={muted}>{t.none}</p>}
    </div>)
}

/** The other-funds amount as a chip: hover, focus or tap it for WHAT paid and how much (TJ,
 *  26 October 2026: "i need to be able to see WHAT paid it and how much then"). A tap does not
 *  open the row. */
function OtherChip({ r, t }: { r: Row; t: T }) {
  const [hover, setHover] = useState(false)
  const [held, setHeld] = useState(false)
  const [at, setAt] = useState<{ top: number; right: number } | null>(null)
  const btn = useRef<HTMLButtonElement>(null)
  const on = hover || held
  // FIXED to the window, not absolute: the table scrolls sideways in its own box, which would
  // clip a popover under the last rows. Placed from the button when it opens; a scroll closes it.
  useEffect(() => {
    if (!on || !btn.current) return
    const b = btn.current.getBoundingClientRect()
    setAt({ top: b.bottom + 4, right: Math.max(8, window.innerWidth - b.right) })
    const close = () => { setHover(false); setHeld(false) }
    window.addEventListener('scroll', close, { passive: true, capture: true })
    return () => window.removeEventListener('scroll', close, { capture: true } as EventListenerOptions)
  }, [on])
  return (
    <span className="relative inline-block" onMouseEnter={() => setHover(true)} onMouseLeave={() => setHover(false)}>
      <button ref={btn} type="button" aria-expanded={on}
        onClick={e => { e.stopPropagation(); setHeld(h => !h) }}
        onFocus={() => setHover(true)} onBlur={() => { setHover(false); setHeld(false) }}
        className="px-2 py-0.5 rounded-full border tabular-nums leading-tight"
        style={{ borderColor: 'var(--text-muted)', background: on ? 'var(--surface-2)' : 'transparent', cursor: 'pointer' }}>
        {r.t.other}</button>
      {on && at ? (
        <span role="tooltip" onClick={e => e.stopPropagation()}
          className="fixed z-50 w-[300px] max-w-[80vw] px-2.5 py-2 rounded text-left text-[12.5px] leading-snug shadow whitespace-normal"
          style={{ top: at.top, right: at.right, background: 'var(--surface-1)', border: '1px solid var(--grid)', color: 'var(--text-primary)', fontWeight: 400 }}>
          <span className="block font-semibold mb-1">{t.payers}</span>
          {r.payers.map((p, i) => (
            <span key={i} className="flex justify-between gap-3 py-0.5">
              <span>{p.payer}<span className="block text-[12px]" style={muted}>{p.rule}: {p.how}</span></span>
              <span className="tabular-nums font-semibold">{p.text}</span></span>))}
        </span>) : null}
    </span>)
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
  const rows = useMemo(() => y.rows.filter(r => !cat || r.cat === cat)
    .sort((a, b) => { const k = d.columns.find(c => c.id === sort.k)?.key ?? 'left'; return sort.dir * (a.n[k] - b.n[k]) || a.name.localeCompare(b.name) }), [y, cat, sort, d.columns])
  const shown = all ? rows : rows.filter((r, i) => i < FIRST || `${r.account}|${r.name}|${r.cat}` === open)
  const firstCost = d.columns.findIndex(c => c.group !== d.columns[0].group)
  const head = (c: Col, i: number) => (
    <th key={c.id} className={`px-2 py-1.5 text-right align-bottom cursor-pointer select-none ${i === firstCost ? 'border-l' : ''}`}
      style={{ borderColor: 'var(--grid)' }}
      onClick={() => setSort(s => ({ k: c.id, dir: s.k === c.id ? (-s.dir as 1 | -1) : -1 }))}
      aria-sort={sort.k === c.id ? (sort.dir < 0 ? 'descending' : 'ascending') : 'none'}>
      <span className="block text-[15px] leading-none mb-1" style={muted}>{c.op || ' '}</span>
      <span className="font-semibold">{c.label}{sort.k === c.id ? (sort.dir < 0 ? ' ↓' : ' ↑') : ''}</span></th>)

  return (
    <figure aria-label={alt}>
      <p className="text-[14px] leading-snug max-w-3xl" style={secondary}>{d.text.read}</p>
      <div className="flex flex-wrap gap-1.5 items-center mt-3">
        {d.years.map((v, i) => <Chip key={v.fy} on={i === yi} onClick={() => { setYi(i); setOpen(null) }}>{v.fy}</Chip>)}
        <select value={cat} onChange={e => { setCat(e.target.value); setOpen(null) }}
          className="ml-1 px-2 py-1 rounded border text-[12.5px]" style={{ borderColor: 'var(--grid)', background: 'var(--surface-1)', color: 'var(--text-primary)' }}>
          <option value="">{d.text.all_cats}</option>
          {d.cats.map(c => <option key={c} value={c}>{c}</option>)}
        </select>
      </div>
      <div className="mt-3 overflow-x-auto">
        <table className="w-full text-[13px] tabular-nums border-collapse">
          <thead>
            <tr>
              <th />
              {d.groups.map((g, gi) => (
                <th key={g.id} colSpan={d.columns.filter(c => c.group === g.id).length}
                  className={`px-2 pt-1 text-center text-[12px] font-semibold uppercase tracking-wide border-b ${gi ? 'border-l' : ''}`}
                  style={{ ...muted, borderColor: 'var(--grid)' }}>{g.label}</th>))}
            </tr>
            <tr className="border-b" style={{ borderColor: 'var(--grid)' }}>
              <th className="px-2 py-1.5 text-left align-bottom font-semibold">{d.text.lines}</th>{d.columns.map(head)}</tr></thead>
          <tbody>
            {shown.map(r => {
              const key = `${r.account}|${r.name}|${r.cat}`
              const isOpen = open === key
              return [
                <tr key={key} className="border-b cursor-pointer hover:bg-[var(--surface-2)]" style={{ borderColor: 'var(--grid)' }}
                  onClick={() => setOpen(o => (o === key ? null : key))} aria-expanded={isOpen}>
                  <td className="px-2 py-1.5 text-left min-w-[14rem]"><span className="mr-1" style={muted}>{isOpen ? '▾' : '▸'}</span>
                    {r.name}<span className="block text-[11.5px]" style={muted}>{r.cat}</span></td>
                  {d.columns.map((c, i) => (
                    <td key={c.id} className={`px-2 py-1.5 text-right whitespace-nowrap ${i === firstCost ? 'border-l' : ''}`}
                      style={{ borderColor: 'var(--grid)', color: c.key === 'left' ? tone(r.n.left) : c.key === 'transfers' && r.n.transfers ? tone(r.n.transfers) : undefined,
                        fontWeight: c.op === '=' ? 600 : 400 }}>
                      {c.key === 'other' && r.payers.length ? <OtherChip r={r} t={d.text} />
                        : r.line || c.key === 'other' || c.key === 'total' ? r.t[c.key] : '—'}</td>))}
                </tr>,
                isOpen ? (
                  <tr key={`${key}-x`} className="border-b" style={{ borderColor: 'var(--grid)', background: 'var(--surface-1)' }}>
                    <td colSpan={d.columns.length + 1} className="px-3 py-3">
                      <div className="grid gap-5 lg:grid-cols-3 max-w-5xl">
                        {r.line ? <Receipt r={r} d={d} /> : null}
                        {r.line ? <Moves r={r} t={d.text} /> : null}
                        <Payers r={r} t={d.text} />
                      </div>
                      {r.account ? <p className="mt-3 font-mono text-[11.5px]" style={muted}>{r.account}</p> : null}
                    </td>
                  </tr>) : null,
              ]
            })}
          </tbody>
        </table>
      </div>
      {rows.length > FIRST ? (
        <button type="button" className="mt-2 text-[13px] underline" style={{ color: 'var(--link, var(--thread-2))' }}
          onClick={() => setAll(a => !a)}>{all ? d.text.fewer : d.text.show}</button>) : null}
      <p className="text-[12.5px] mt-2" style={muted}>{d.text.footing}</p>
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

/** EVERY LINE, IN FOUR PARTS (fy2026-breakdown): the school general fund's lines, one fiscal
 *  year at a time, sortable by what was left or by any of the four parts, filterable by
 *  category. Each row opens on its own waterfall -- voted, less what it cost from every fund,
 *  plus what other funds paid, plus transfers, plus another year's money, to what was left --
 *  and on the other funds that paid toward it, each with the rule that matched it.
 *
 *  Under the lines, the other funds' spending no rule matched to any line, by fund and why.
 *  Every figure is formatted by scripts/build_fy_breakdown.py. */
import { useMemo, useState } from 'react'
import type { CustomProps } from './index'

type K = 'voted' | 'cost' | 'gf' | 'above' | 'transfers' | 'other' | 'another' | 'left'
type Row = { name: string; account: string; cat: string; group: string; n: Record<K, number>; t: Record<K, string>
  payers: { payer: string; rule: string; text: string }[] }
type Year = { fy: string; rows: Row[]; unmatched: { payer: string; why: string; text: string }[]; unmatched_total: string }
type Data = { years: Year[]; cats: string[]; columns: { id: K; label: string }[]
  steps: Record<'voted' | 'cost' | 'other' | 'transfers' | 'another' | 'left', string>
  text: { all_cats: string; show: string; fewer: string; payers: string; none: string; unmatched: string; lines: string } }

const FIRST = 25

function Chip({ on, onClick, children }: { on: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button type="button" onClick={onClick} aria-pressed={on}
      className="px-2.5 py-1 rounded-full text-[12.5px] border leading-tight"
      style={{ borderColor: on ? 'var(--text-secondary)' : 'var(--grid)', color: on ? 'var(--text-primary)' : 'var(--text-muted)',
        background: on ? 'var(--surface-2)' : 'transparent', fontWeight: on ? 600 : 400 }}>{children}</button>)
}

const tone = (v: number) => (v > 0.5 ? 'var(--status-good, var(--thread-5))' : v < -0.5 ? 'var(--status-bad, var(--thread-1))' : 'var(--text-muted)')

/** One line's waterfall: each step a bar drawn from where the running total stood. */
function Waterfall({ r, steps }: { r: Row; steps: Data['steps'] }) {
  const seq: { k: keyof Data['steps']; v: number; t: string; total?: boolean }[] = [
    { k: 'voted', v: r.n.voted, t: r.t.voted, total: true },
    { k: 'cost', v: -r.n.cost, t: r.t.cost },
    { k: 'other', v: r.n.other, t: r.t.other },
    { k: 'transfers', v: r.n.transfers, t: r.t.transfers },
    { k: 'another', v: r.n.another, t: r.t.another },
    { k: 'left', v: r.n.left, t: r.t.left, total: true },
  ]
  let run = 0
  const spans = seq.map(s => {
    const a = s.total ? 0 : run, b = s.total ? s.v : run + s.v
    if (!s.total) run = b; else run = s.v
    return { ...s, lo: Math.min(a, b), hi: Math.max(a, b) }
  })
  const lo = Math.min(0, ...spans.map(s => s.lo)), hi = Math.max(1, ...spans.map(s => s.hi))
  const pct = (v: number) => `${(100 * (v - lo)) / (hi - lo)}%`
  return (
    <div className="space-y-1">
      {spans.map(s => (
        <div key={s.k} className="grid grid-cols-[minmax(0,11rem)_1fr_auto] gap-x-2 items-center text-[12.5px]">
          <span style={{ color: 'var(--text-secondary)' }}>{steps[s.k]}</span>
          <span className="relative h-3 rounded-sm" style={{ background: 'var(--surface-2)' }}>
            <span className="absolute top-0 bottom-0 w-px" style={{ left: pct(0), background: 'var(--grid)' }} />
            <span className="absolute top-0 bottom-0 rounded-sm" style={{ left: pct(s.lo), width: `calc(${pct(s.hi)} - ${pct(s.lo)})`,
              background: s.total ? 'var(--text-secondary)' : tone(s.v) }} />
          </span>
          <span className="tabular-nums text-right" style={{ fontWeight: s.total ? 600 : 400 }}>{s.t}</span>
        </div>))}
    </div>
  )
}

export default function FyLineTable({ data, alt }: CustomProps) {
  const d = data as Data
  const [yi, setYi] = useState(d.years.length - 1)
  const [cat, setCat] = useState<string>('')
  const [sort, setSort] = useState<{ k: K; dir: 1 | -1 }>({ k: 'left', dir: -1 })
  const [all, setAll] = useState(false)
  const [open, setOpen] = useState<string | null>(null)
  const y = d.years[yi]
  const rows = useMemo(() => y.rows.filter(r => !cat || r.cat === cat)
    .sort((a, b) => sort.dir * (a.n[sort.k] - b.n[sort.k]) || a.name.localeCompare(b.name)), [y, cat, sort])
  const shown = all ? rows : rows.slice(0, FIRST)
  const head = (c: { id: K; label: string }) => (
    <th key={c.id} className="px-2 py-1.5 text-right font-semibold whitespace-nowrap cursor-pointer select-none"
      onClick={() => setSort(s => ({ k: c.id, dir: s.k === c.id ? (-s.dir as 1 | -1) : -1 }))}
      aria-sort={sort.k === c.id ? (sort.dir < 0 ? 'descending' : 'ascending') : 'none'}>
      {c.label}{sort.k === c.id ? (sort.dir < 0 ? ' ↓' : ' ↑') : ''}</th>)

  return (
    <figure aria-label={alt}>
      <div className="flex flex-wrap gap-1.5 items-center">
        {d.years.map((v, i) => <Chip key={v.fy} on={i === yi} onClick={() => { setYi(i); setOpen(null) }}>{v.fy}</Chip>)}
        <select value={cat} onChange={e => { setCat(e.target.value); setOpen(null) }}
          className="ml-1 px-2 py-1 rounded border text-[12.5px]" style={{ borderColor: 'var(--grid)', background: 'var(--surface-1)', color: 'var(--text-primary)' }}>
          <option value="">{d.text.all_cats}</option>
          {d.cats.map(c => <option key={c} value={c}>{c}</option>)}
        </select>
      </div>
      <div className="mt-3 overflow-x-auto">
        <table className="w-full text-[13px] tabular-nums border-collapse">
          <thead><tr className="border-b" style={{ borderColor: 'var(--grid)' }}>
            <th className="px-2 py-1.5 text-left font-semibold">{d.text.lines}</th>{d.columns.map(head)}</tr></thead>
          <tbody>
            {shown.map(r => {
              const key = `${r.account}|${r.name}|${r.cat}`
              const isOpen = open === key
              return [
                <tr key={key} className="border-b cursor-pointer hover:bg-[var(--surface-2)]" style={{ borderColor: 'var(--grid)' }}
                  onClick={() => setOpen(o => (o === key ? null : key))} aria-expanded={isOpen}>
                  <td className="px-2 py-1.5 text-left min-w-[14rem]"><span className="mr-1" style={{ color: 'var(--text-muted)' }}>{isOpen ? '▾' : '▸'}</span>
                    {r.name}<span className="block text-[11.5px]" style={{ color: 'var(--text-muted)' }}>{r.cat}</span></td>
                  {d.columns.map(c => <td key={c.id} className="px-2 py-1.5 text-right whitespace-nowrap"
                    style={{ color: c.id === 'left' ? tone(r.n.left) : undefined, fontWeight: c.id === 'left' ? 600 : 400 }}>{r.t[c.id]}</td>)}
                </tr>,
                isOpen ? (
                  <tr key={`${key}-x`} className="border-b" style={{ borderColor: 'var(--grid)', background: 'var(--surface-1)' }}>
                    <td colSpan={d.columns.length + 1} className="px-3 py-3">
                      <div className="grid gap-4 sm:grid-cols-2 max-w-3xl">
                        <Waterfall r={r} steps={d.steps} />
                        <div className="text-[12.5px]">
                          <p className="font-semibold">{d.text.payers}</p>
                          {r.payers.length ? (
                            <ul className="mt-1 space-y-0.5">
                              {r.payers.map((p, i) => (
                                <li key={i} className="flex justify-between gap-3"><span>{p.payer} <span style={{ color: 'var(--text-muted)' }}>· {p.rule}</span></span>
                                  <span className="tabular-nums">{p.text}</span></li>))}
                            </ul>) : <p className="mt-1" style={{ color: 'var(--text-muted)' }}>{d.text.none}</p>}
                          {r.account ? <p className="mt-2 font-mono text-[11.5px]" style={{ color: 'var(--text-muted)' }}>{r.account}</p> : null}
                        </div>
                      </div>
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
      <details className="mt-4">
        <summary className="cursor-pointer text-[13.5px] font-semibold">{d.text.unmatched} · <span className="tabular-nums">{y.unmatched_total}</span></summary>
        <ul className="mt-2 text-[13px] max-w-2xl">
          {y.unmatched.map((u, i) => (
            <li key={i} className="flex justify-between gap-3 py-1 border-b" style={{ borderColor: 'var(--grid)' }}>
              <span>{u.payer} <span style={{ color: 'var(--text-muted)' }}>· {u.why}</span></span><span className="tabular-nums">{u.text}</span></li>))}
        </ul>
      </details>
    </figure>
  )
}
